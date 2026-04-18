"""Tests for ``check-artifact-consistency.py``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _fixtures import (  # noqa: E402
    build_happy_plan_dir,
    setup_archived_plan,
    setup_broken_plan,
    setup_live_plan,
)

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
        (plan_dir / 'references.json').write_text(
            json.dumps({'affected_files': ['src/foo.py'], 'domains': []}),
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


def _outline_with_affected_files(files: list[str]) -> str:
    """Build a solution_outline.md string that declares ``files`` as a single
    deliverable's Affected files bullets. When ``files`` is empty the outline
    still contains a valid Deliverables section but no Affected files block.
    """
    bullets = ''.join(f'- `{p}`\n' for p in files)
    affected_block = '\n**Affected files:**\n' + bullets if files else ''
    return (
        '# Solution: ExactMatch\n'
        'plan_id: exact-match\n\n'
        '## Summary\n\n'
        'Exact-match fixture.\n\n'
        '## Overview\n\n'
        'Overview.\n\n'
        '## Deliverables\n\n'
        '### 1. Deliverable one\n'
        f'{affected_block}'
    )


def _setup_exact_match_plan(
    tmp_path: Path,
    monkeypatch,
    *,
    outline_files: list[str],
    references_files: list[str],
    plan_id: str = 'retro-exact-match',
) -> tuple[str, Path]:
    """Create a live plan whose outline and references.json are seeded with
    caller-supplied file lists. Reuses ``build_happy_plan_dir`` to keep the
    surrounding structural checks (metrics, tasks, status) green, then
    overwrites the two files the exact-match check consults.
    """
    base = tmp_path / 'base'
    base.mkdir()
    plan_dir = base / 'plans' / plan_id
    build_happy_plan_dir(plan_dir)

    # Overwrite outline with a variant whose deliverable count matches the
    # default tasks fixture (a single deliverable) so task_deliverable_match
    # does not go red and drown out the check under test.
    (plan_dir / 'solution_outline.md').write_text(
        _outline_with_affected_files(outline_files), encoding='utf-8'
    )
    # Trim tasks to a single deliverable to match the outline above.
    tasks_dir = plan_dir / 'tasks'
    for leftover in tasks_dir.glob('TASK-*.json'):
        leftover.unlink()
    (tasks_dir / 'TASK-001.json').write_text(
        json.dumps({'number': 1, 'deliverable': 1, 'status': 'done'}),
        encoding='utf-8',
    )

    # Overwrite references.json with the caller's list.
    (plan_dir / 'references.json').write_text(
        json.dumps({'affected_files': references_files, 'domains': []}),
        encoding='utf-8',
    )
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return plan_id, plan_dir


class TestAffectedFilesExactMatch:
    """Exercises the strict ``affected_files_exact_match`` top-level key.

    Each test verifies:
    - The key is present at the top level (peer to ``affected_files_recall``'s
      sibling in ``details``, NOT nested inside ``details``).
    - ``status`` matches the expected pass/warn outcome.
    - ``outline_only`` and ``references_only`` reflect the set difference.
    """

    def test_case_a_exact_match_passes(self, tmp_path, monkeypatch):
        """Outline and references declare identical files -> pass, empty lists."""
        files = ['src/foo.py', 'src/bar.py']
        plan_id, _ = _setup_exact_match_plan(
            tmp_path,
            monkeypatch,
            outline_files=files,
            references_files=files,
            plan_id='retro-exact-a',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert 'affected_files_exact_match' in data, (
            'affected_files_exact_match must be a top-level TOON key, '
            'peer to affected_files_recall'
        )
        exact = data['affected_files_exact_match']
        assert exact['status'] == 'pass'
        assert exact['outline_only'] == []
        assert exact['references_only'] == []

        check = _check_by_name(data['checks'], 'affected_files_exact_match')
        assert check is not None
        assert check['status'] == 'pass'

    def test_case_b_outline_superset_warns(self, tmp_path, monkeypatch):
        """Outline has files references lacks -> warn, populated outline_only."""
        plan_id, _ = _setup_exact_match_plan(
            tmp_path,
            monkeypatch,
            outline_files=['src/foo.py', 'src/bar.py', 'src/baz.py'],
            references_files=['src/foo.py'],
            plan_id='retro-exact-b',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert 'affected_files_exact_match' in data
        exact = data['affected_files_exact_match']
        assert exact['status'] == 'warn'
        assert exact['outline_only'] == ['src/bar.py', 'src/baz.py']
        assert exact['references_only'] == []

    def test_case_c_references_superset_warns(self, tmp_path, monkeypatch):
        """References has files outline lacks -> warn, populated references_only."""
        plan_id, _ = _setup_exact_match_plan(
            tmp_path,
            monkeypatch,
            outline_files=['src/foo.py'],
            references_files=['src/foo.py', 'src/bar.py', 'src/baz.py'],
            plan_id='retro-exact-c',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert 'affected_files_exact_match' in data
        exact = data['affected_files_exact_match']
        assert exact['status'] == 'warn'
        assert exact['outline_only'] == []
        assert exact['references_only'] == ['src/bar.py', 'src/baz.py']

    def test_case_d_disjoint_sets_warn(self, tmp_path, monkeypatch):
        """Outline and references share no files -> warn, both lists populated."""
        plan_id, _ = _setup_exact_match_plan(
            tmp_path,
            monkeypatch,
            outline_files=['src/foo.py', 'src/bar.py'],
            references_files=['src/alpha.py', 'src/beta.py'],
            plan_id='retro-exact-d',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert 'affected_files_exact_match' in data
        exact = data['affected_files_exact_match']
        assert exact['status'] == 'warn'
        assert exact['outline_only'] == ['src/bar.py', 'src/foo.py']
        assert exact['references_only'] == ['src/alpha.py', 'src/beta.py']

    def test_case_e_both_empty_passes(self, tmp_path, monkeypatch):
        """No outline files and no references files -> pass, empty lists."""
        plan_id, _ = _setup_exact_match_plan(
            tmp_path,
            monkeypatch,
            outline_files=[],
            references_files=[],
            plan_id='retro-exact-e',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert 'affected_files_exact_match' in data
        exact = data['affected_files_exact_match']
        assert exact['status'] == 'pass'
        assert exact['outline_only'] == []
        assert exact['references_only'] == []


# Suppress unused import warning (json kept for possible future use).
_ = json
