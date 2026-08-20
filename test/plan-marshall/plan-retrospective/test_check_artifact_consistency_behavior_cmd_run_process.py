# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for ``check-artifact-consistency.py``.

Scope: the whole-command run — which verdicts reach findings, at what severity, and
how the presence of a manifest downgrades a warning without forwarding an
inconclusive one.
"""


from __future__ import annotations

import json
from pathlib import Path

from _check_artifact_consistency_behavior_fixtures import (
    _build_consistent_plan,
    _cac,
    _check,
    _outline,
    _recall_verdict,
    _run_args,
)


class TestCmdRunInProcess:
    """``cmd_run`` aggregates every check into a structured verdict."""

    def test_fully_consistent_plan_all_pass(self, tmp_path):
        plan_dir = tmp_path / 'plan'
        _build_consistent_plan(plan_dir, ['src/a.py', 'src/b.py'])

        result = _cac.cmd_run(_run_args(plan_dir))

        assert result['status'] == 'success'
        assert result['aspect'] == 'artifact_consistency'
        checks = result['checks']
        assert _check(checks, 'solution_outline_sections')['status'] == 'pass'
        assert _check(checks, 'deliverable_count')['status'] == 'pass'
        assert _check(checks, 'task_deliverable_match')['status'] == 'pass'
        assert _check(checks, 'metrics_generated')['status'] == 'pass'
        assert result['summary']['failed'] == 0
        assert result['affected_files_exact_match']['status'] == 'pass'
        assert result['affected_files_exact_match']['manifest_present'] is False

    def test_missing_outline_surfaces_present_failure(self, tmp_path):
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()

        result = _cac.cmd_run(_run_args(plan_dir))

        present = _check(result['checks'], 'solution_outline_present')
        assert present is not None
        assert present['status'] == 'fail'
        assert any('solution_outline.md missing' in f['message'] for f in result['findings'])

    def test_both_empty_yields_inconclusive_and_recall_skip(self, tmp_path):
        """A plan whose only deliverable declares no ``Affected files`` section,
        with an empty footprint, reports ``affected_files_recall: skip`` — the
        deliverable never claimed to declare files, so there is no parse
        failure — while ``affected_files_exact_match`` stays ``inconclusive``:
        two empty sets substantiate no verdict, and that aggregate verdict must
        not regress to a vacuous ``pass``.
        """
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'solution_outline.md').write_text(_outline(), encoding='utf-8')
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': []}), encoding='utf-8'
        )
        (plan_dir / 'metrics.md').write_text('# Metrics\n', encoding='utf-8')
        tasks = plan_dir / 'tasks'
        tasks.mkdir()
        (tasks / 'TASK-001.json').write_text(json.dumps({'deliverable': 1}), encoding='utf-8')

        result = _cac.cmd_run(_run_args(plan_dir))

        recall = _check(result['checks'], 'affected_files_recall')
        assert recall['status'] == 'skip'
        exact = _check(result['checks'], 'affected_files_exact_match')
        assert exact['status'] == 'inconclusive'
        assert result['affected_files_exact_match']['status'] == 'inconclusive'
        assert any(
            f['severity'] == 'warning' and 'substantiates no verdict' in f['message']
            for f in result['findings']
        )

    def test_manifest_present_does_not_forward_inconclusive(self, tmp_path):
        """The manifest downgrade keys on ``warn`` only — an ``inconclusive``
        verdict is never absorbed into the ``info`` forwarding branch.
        """
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'solution_outline.md').write_text(_outline(), encoding='utf-8')
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': []}), encoding='utf-8'
        )
        (plan_dir / 'metrics.md').write_text('# Metrics\n', encoding='utf-8')
        tasks = plan_dir / 'tasks'
        tasks.mkdir()
        (tasks / 'TASK-001.json').write_text(json.dumps({'deliverable': 1}), encoding='utf-8')
        (plan_dir / 'execution.toon').write_text('plan_id: plan\n', encoding='utf-8')

        result = _cac.cmd_run(_run_args(plan_dir))

        exact = _check(result['checks'], 'affected_files_exact_match')
        assert exact['status'] == 'inconclusive'
        assert result['affected_files_exact_match']['manifest_present'] is True
        assert result['affected_files_exact_match']['forwarded_to_manifest'] is False

    def test_exact_match_warn_drives_warning_finding_without_manifest(self, tmp_path):
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'solution_outline.md').write_text(
            _outline(affected=['src/a.py', 'src/b.py']), encoding='utf-8'
        )
        # References list a different file → exact-match drift (warn).
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['src/a.py', 'src/c.py']}), encoding='utf-8'
        )
        (plan_dir / 'metrics.md').write_text('# Metrics\n', encoding='utf-8')
        tasks = plan_dir / 'tasks'
        tasks.mkdir()
        (tasks / 'TASK-001.json').write_text(json.dumps({'deliverable': 1}), encoding='utf-8')

        result = _cac.cmd_run(_run_args(plan_dir))

        exact = _check(result['checks'], 'affected_files_exact_match')
        assert exact['status'] == 'warn'
        assert result['affected_files_exact_match']['forwarded_to_manifest'] is False
        assert any(
            f['severity'] == 'warning' and 'mismatch' in f['message'].lower()
            for f in result['findings']
        )

    def test_unresolvable_footprint_yields_inconclusive_from_both_peers(self, tmp_path):
        """The deleted-worktree shape: no footprint resolves, so neither peer measures.

        ``cmd_run`` is the surface a summary consumer reads, so the assertions
        cover the whole path: both verdicts, both findings, and the summary
        bucket that keeps them countable.
        """
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'solution_outline.md').write_text(
            _outline(affected=['src/a.py', 'src/b.py']), encoding='utf-8'
        )
        # No references.json at all → no resolution tier answers (unresolvable).
        (plan_dir / 'metrics.md').write_text('# Metrics\n', encoding='utf-8')
        tasks = plan_dir / 'tasks'
        tasks.mkdir()
        (tasks / 'TASK-001.json').write_text(json.dumps({'deliverable': 1}), encoding='utf-8')

        result = _cac.cmd_run(_run_args(plan_dir))

        assert _check(result['checks'], 'affected_files_recall')['status'] == 'inconclusive'
        assert _check(result['checks'], 'affected_files_exact_match')['status'] == 'inconclusive'

        unresolvable = [
            f
            for f in result['findings']
            if f['severity'] == 'warning' and 'could not be resolved' in f['message']
        ]
        assert len(unresolvable) == 2, (
            f'Expected one warning finding per affected_files_* peer, got {result["findings"]}'
        )

        assert result['summary']['inconclusive'] == 2
        assert sum(result['summary'].values()) == len(result['checks'])

    def test_summary_reconciles_on_a_plan_that_emits_warn(self, tmp_path):
        """``warn`` is counted too — the repaired map covers every emitted status."""
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'solution_outline.md').write_text(
            _outline(affected=['src/a.py', 'src/b.py']), encoding='utf-8'
        )
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['src/a.py', 'src/c.py']}), encoding='utf-8'
        )
        (plan_dir / 'metrics.md').write_text('# Metrics\n', encoding='utf-8')
        tasks = plan_dir / 'tasks'
        tasks.mkdir()
        (tasks / 'TASK-001.json').write_text(json.dumps({'deliverable': 1}), encoding='utf-8')

        result = _cac.cmd_run(_run_args(plan_dir))

        assert result['summary']['warn'] == 1
        assert sum(result['summary'].values()) == len(result['checks'])

    def test_manifest_present_downgrades_warn_to_info(self, tmp_path):
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'solution_outline.md').write_text(
            _outline(affected=['src/a.py', 'src/b.py']), encoding='utf-8'
        )
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['src/a.py', 'src/c.py']}), encoding='utf-8'
        )
        (plan_dir / 'metrics.md').write_text('# Metrics\n', encoding='utf-8')
        tasks = plan_dir / 'tasks'
        tasks.mkdir()
        (tasks / 'TASK-001.json').write_text(json.dumps({'deliverable': 1}), encoding='utf-8')
        # The presence of execution.toon defers the drift to the manifest aspect.
        (plan_dir / 'execution.toon').write_text('plan_id: plan\n', encoding='utf-8')

        result = _cac.cmd_run(_run_args(plan_dir))

        exact = _check(result['checks'], 'affected_files_exact_match')
        assert exact['status'] == 'info'
        assert 'deferred to manifest aspect' in exact['message']
        top = result['affected_files_exact_match']
        assert top['manifest_present'] is True
        assert top['forwarded_to_manifest'] is True
        assert any(f['severity'] == 'info' for f in result['findings'])


class TestRecallFindingSeveritySplit:
    """A measured recall ``fail`` and an unmeasurable ``inconclusive`` reach the
    synthesizer at DIFFERENT severities.

    ``check_affected_files_recall`` returns ``fail`` for three MEASURED
    conditions (an ``Affected files`` heading that parsed to no bullet, an
    unreadable ``references.json``, and a recall percentage below the threshold)
    and ``inconclusive`` only for a genuinely unresolvable footprint. Routing
    both onto one severity erases exactly the measured-vs-unmeasurable
    distinction the check exists to preserve — the ``metrics_generated`` peer
    splits its own pair the same way.

    The matched pair below is what makes this non-vacuous: pinning only one
    branch would still pass if both collapsed onto that branch's severity, so
    the differ-assertion reads both verdicts from the same surface and compares
    them to each other rather than to a literal.
    """

    @staticmethod
    def _scaffold(plan_dir: Path, outline: str) -> None:
        """Write the non-recall artifacts every branch needs, minus references.json."""
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / 'solution_outline.md').write_text(outline, encoding='utf-8')
        (plan_dir / 'metrics.md').write_text('# Metrics\n', encoding='utf-8')
        tasks = plan_dir / 'tasks'
        tasks.mkdir()
        (tasks / 'TASK-001.json').write_text(json.dumps({'deliverable': 1}), encoding='utf-8')

    @classmethod
    def _measured_failure_plan(cls, plan_dir: Path) -> None:
        """Resolved footprint covering 1 of 3 declared files → measured 33% fail."""
        cls._scaffold(plan_dir, _outline(affected=['src/a.py', 'src/b.py', 'src/c.py']))
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['src/a.py']}), encoding='utf-8'
        )

    @classmethod
    def _unmeasurable_plan(cls, plan_dir: Path) -> None:
        """No references.json at all → no resolution tier answers (unresolvable)."""
        cls._scaffold(plan_dir, _outline(affected=['src/a.py', 'src/b.py', 'src/c.py']))

    def test_measured_recall_failure_emits_error_severity(self, tmp_path):
        plan_dir = tmp_path / 'plan'
        self._measured_failure_plan(plan_dir)

        status, severity = _recall_verdict(_cac.cmd_run(_run_args(plan_dir)))

        assert status == 'fail'
        assert severity == 'error'

    def test_unmeasurable_recall_emits_warning_severity(self, tmp_path):
        plan_dir = tmp_path / 'plan'
        self._unmeasurable_plan(plan_dir)

        status, severity = _recall_verdict(_cac.cmd_run(_run_args(plan_dir)))

        assert status == 'inconclusive'
        assert severity == 'warning'

    def test_unreadable_references_is_measured_and_emits_error_severity(self, tmp_path):
        """The second measured ``fail`` condition routes to ``error`` as well.

        Corrupt plan state is something the check MEASURED, not something it
        failed to measure, so it must not share the unmeasurable severity.
        """
        plan_dir = tmp_path / 'plan'
        self._scaffold(plan_dir, _outline(affected=['src/a.py']))
        (plan_dir / 'references.json').write_text('{ broken', encoding='utf-8')

        result = _cac.cmd_run(_run_args(plan_dir))
        status, severity = _recall_verdict(result)

        assert status == 'fail'
        assert 'unreadable' in _check(result['checks'], 'affected_files_recall')['message'].lower()
        assert severity == 'error'

    def test_the_two_severities_differ(self, tmp_path):
        """The anti-collapse assertion: one severity for both statuses fails here."""
        measured_dir = tmp_path / 'measured'
        self._measured_failure_plan(measured_dir)
        unmeasurable_dir = tmp_path / 'unmeasurable'
        self._unmeasurable_plan(unmeasurable_dir)

        measured_status, measured_severity = _recall_verdict(_cac.cmd_run(_run_args(measured_dir)))
        unmeasurable_status, unmeasurable_severity = _recall_verdict(
            _cac.cmd_run(_run_args(unmeasurable_dir))
        )

        assert measured_status != unmeasurable_status, (
            'The two plans must reach DIFFERENT recall statuses, or the severity '
            'comparison below asserts nothing'
        )
        assert measured_severity != unmeasurable_severity, (
            f'A measured recall {measured_status!r} and an unmeasurable '
            f'{unmeasurable_status!r} both emitted severity '
            f'{measured_severity!r} — the measured-vs-unmeasurable distinction '
            'has collapsed onto one severity'
        )
