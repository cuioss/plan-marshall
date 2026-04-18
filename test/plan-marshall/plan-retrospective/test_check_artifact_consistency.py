"""Tests for ``check-artifact-consistency.py``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _fixtures import setup_archived_plan, setup_broken_plan, setup_live_plan  # noqa: E402

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'scripts'
    / 'check-artifact-consistency.py'
)


def _check_by_name(checks: list, name: str) -> dict | None:
    for c in checks:
        if c.get('name') == name:
            return c
    return None


class TestHappyPath:
    def test_all_required_checks_pass(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['aspect'] == 'artifact_consistency'

        checks = data['checks']
        assert _check_by_name(checks, 'solution_outline_sections')['status'] == 'pass'
        assert _check_by_name(checks, 'deliverable_count')['status'] == 'pass'
        assert _check_by_name(checks, 'task_deliverable_match')['status'] == 'pass'
        assert _check_by_name(checks, 'metrics_generated')['status'] == 'pass'

    def test_affected_files_recall_calculated(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        data = result.toon()
        details = data['details']
        recall = details['affected_files_recall']
        assert int(recall['declared']) == 3
        assert int(recall['found']) == 3


class TestFaultInjection:
    def test_missing_metrics_and_deliverables_fail(self, tmp_path, monkeypatch):
        plan_id, _ = setup_broken_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        checks = data['checks']
        sections_check = _check_by_name(checks, 'solution_outline_sections')
        assert sections_check['status'] == 'fail'

        metrics_check = _check_by_name(checks, 'metrics_generated')
        assert metrics_check['status'] == 'fail'

        summary = data['summary']
        assert int(summary['failed']) >= 2
        findings = data['findings']
        assert len(findings) > 0

    def test_missing_solution_outline_emits_error(self, tmp_path, monkeypatch):
        plan_id = 'no-outline'
        base = tmp_path / 'base'
        base.mkdir()
        plan_dir = base / 'plans' / plan_id
        plan_dir.mkdir(parents=True)
        (plan_dir / 'tasks').mkdir()
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        checks = data['checks']
        present = _check_by_name(checks, 'solution_outline_present')
        assert present is not None
        assert present['status'] == 'fail'

    def test_malformed_references_json_fails_recall(self, tmp_path, monkeypatch):
        """A corrupt references.json must fail affected-files recall gracefully."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        (plan_dir / 'references.json').write_text('{ not valid', encoding='utf-8')

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        recall = _check_by_name(data['checks'], 'affected_files_recall')
        assert recall['status'] == 'fail'
        assert 'unreadable' in recall['message'].lower()

    def test_partial_recall_below_threshold_fails(self, tmp_path, monkeypatch):
        """When references.json covers <70% of declared files, recall fails."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        # Fixture declares 3 files in outline (foo, bar, baz). Drop two of
        # them so recall = 1/3 ≈ 33%, which is below the 70% threshold.
        # Production-shape: ``check-artifact-consistency.py`` consults
        # ``modified_files``, so the partial-recall fixture must use the same
        # key — using ``affected_files`` would yield a 0% recall instead of
        # the 33% the test description claims.
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['src/foo.py'], 'domains': []}),
            encoding='utf-8',
        )

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        recall = _check_by_name(data['checks'], 'affected_files_recall')
        assert recall['status'] == 'fail'
        details = data['details']['affected_files_recall']
        assert int(details['declared']) == 3
        assert int(details['found']) == 1


class TestArchivedMode:
    def test_archived_plan_checks_pass(self, tmp_path):
        archived = setup_archived_plan(tmp_path)
        result = run_script(
            SCRIPT_PATH, 'run', '--archived-plan-path', str(archived), '--mode', 'archived'
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert _check_by_name(data['checks'], 'deliverable_count')['status'] == 'pass'


class TestRegression:
    """Regression tests locking in the production-shape recall calculation.

    Before the fix, ``check_affected_files_recall`` consulted the legacy
    ``affected_files`` key in ``references.json`` and returned 0% recall
    against a production plan whose references were populated via
    ``modified_files``. These tests pin the computed ``recall_pct`` to the
    exact expected value so a regression to the old key name or a silent
    failure-path return is caught immediately.
    """

    def test_recall_pct_is_100_when_modified_files_matches_declared(self, tmp_path, monkeypatch):
        """Production-shape happy path: declared == modified_files → 100%.

        The happy-path fixture declares ``src/foo.py``, ``src/bar.py``,
        ``src/baz.py`` in the outline and populates the same three in
        ``references.json['modified_files']``. This test pins
        ``recall_pct`` to ``100.0`` so a regression to the old ``affected_files``
        lookup (which would yield ``0.0``) is caught.
        """
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        details = data['details']['affected_files_recall']
        assert int(details['declared']) == 3
        assert int(details['found']) == 3
        # recall_pct serializes as a float; parse_toon may return int or str
        # depending on payload shape, so coerce before comparing.
        assert float(details['recall_pct']) == 100.0, (
            f'Expected recall_pct == 100.0 when modified_files matches '
            f'declared, got {details["recall_pct"]}. This regression means '
            f'check-artifact-consistency is reading the wrong key again.'
        )

    def test_recall_fails_when_modified_files_empty(self, tmp_path, monkeypatch):
        """Failure-path sibling: declared present, modified_files empty → 0%.

        Complements the happy-path pin above: ensures the check still
        fails correctly (not a false-positive pass) when the references
        file is missing the ``modified_files`` entries entirely.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': [], 'domains': []}),
            encoding='utf-8',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        recall = _check_by_name(data['checks'], 'affected_files_recall')
        assert recall['status'] == 'fail'
        details = data['details']['affected_files_recall']
        assert int(details['declared']) == 3
        assert int(details['found']) == 0
        assert float(details['recall_pct']) == 0.0


# Suppress unused import warning (json kept for possible future use).
_ = json
