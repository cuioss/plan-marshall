# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for ``check-artifact-consistency.py``.

The existing ``test_check_artifact_consistency.py`` drives the script through
the ``run_script`` subprocess harness (which exercises the real argparse path
but does not count for in-process coverage) plus a handful of direct
``_resolve_footprint`` unit calls. This module complements it by calling
``cmd_run`` and the individual ``check_*`` analyzers IN-PROCESS against crafted
``tmp_path`` plan directories, asserting the structural verdicts each branch
produces — including the manifest-aware downgrade branch, the task/recall/
exact-match edge cases, and the ``resolve_plan_dir`` error paths that the
subprocess suite never reaches in-process.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module

# Unique module name so this in-process load never collides with the
# ``_check_artifact_under_test`` instance the sibling subprocess suite loads.
_cac = load_script_module(
    'plan-marshall', 'plan-retrospective', 'check-artifact-consistency.py', 'cac_behavior_mod'
)


# Markdown fragments shaped like the production solution_outline.md the
# retrospective parses. ``parse_document_sections`` lowercases ``## Heading``
# names, and ``extract_affected_files_per_deliverable`` collects bullets under
# each ``**Affected files:**`` block.
def _outline(
    deliverables: int = 1,
    affected: list[str] | None = None,
    *,
    annotation: str | None = None,
    empty_affected_heading: bool = False,
) -> str:
    """Build an outline fragment.

    ``annotation`` selects the ``Affected files:`` bullet form: ``None`` emits
    the plain backticked ``- `path``` form, a string emits the canonical
    annotated ``- `path` (annotation)`` form real outlines use.

    ``empty_affected_heading`` emits deliverable 1 with the
    ``**Affected files:**`` heading and NO bullets beneath it — the loud-fail
    shape. It is independent of the heading-absent shape (the default, where
    the deliverable carries no ``Affected files`` heading at all), so the two
    branches of the per-deliverable rule can be pinned separately.
    """
    suffix = f' ({annotation})' if annotation else ''
    parts = [
        '# Solution: Behavior',
        '',
        '## Summary',
        '',
        'A crafted plan.',
        '',
        '## Overview',
        '',
        'Overview prose.',
        '',
        '## Deliverables',
        '',
    ]
    for i in range(1, deliverables + 1):
        parts.append(f'### {i}. Deliverable {i}')
        parts.append('')
        if affected and i == 1:
            parts.append('**Affected files:**')
            parts.extend(f'- `{p}`{suffix}' for p in affected)
            parts.append('')
        elif empty_affected_heading and i == 1:
            # Heading present, zero bullets beneath it — the loud-fail shape.
            parts.append('**Affected files:**')
            parts.append('')
    return '\n'.join(parts) + '\n'


def _run_args(plan_dir: Path) -> Namespace:
    """Build the archived-mode ``argparse.Namespace`` ``cmd_run`` consumes."""
    return Namespace(
        command='run',
        plan_id=None,
        archived_plan_path=str(plan_dir),
        mode='archived',
    )


def _check(checks: list[dict], name: str) -> dict | None:
    return next((c for c in checks if c.get('name') == name), None)


class TestResolvePlanDir:
    """``resolve_plan_dir`` validates its mode/argument combinations."""

    def test_live_without_plan_id_raises(self):
        with pytest.raises(ValueError, match='--plan-id is required'):
            _cac.resolve_plan_dir('live', None, None)

    def test_archived_without_path_raises(self):
        with pytest.raises(ValueError, match='--archived-plan-path is required'):
            _cac.resolve_plan_dir('archived', None, None)

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match='Unknown mode'):
            _cac.resolve_plan_dir('frobnicate', 'p', None)

    def test_archived_returns_supplied_path(self, tmp_path):
        result = _cac.resolve_plan_dir('archived', None, str(tmp_path))
        assert result == tmp_path


class TestLoadReferences:
    """``_load_references`` is defensive: any read/parse error degrades to {}."""

    def test_missing_file_returns_empty(self, tmp_path):
        assert _cac._load_references(tmp_path) == {}

    def test_malformed_json_returns_empty(self, tmp_path):
        (tmp_path / 'references.json').write_text('{ not json', encoding='utf-8')
        assert _cac._load_references(tmp_path) == {}

    def test_non_dict_top_level_returns_empty(self, tmp_path):
        (tmp_path / 'references.json').write_text('[1, 2, 3]', encoding='utf-8')
        assert _cac._load_references(tmp_path) == {}

    def test_valid_dict_returned(self, tmp_path):
        (tmp_path / 'references.json').write_text(
            json.dumps({'modified_files': ['a.py']}), encoding='utf-8'
        )
        assert _cac._load_references(tmp_path) == {'modified_files': ['a.py']}


class TestSectionAndDeliverableChecks:
    def test_sections_pass_when_all_present(self):
        status, message = _cac.check_solution_outline_sections(_outline())
        assert status == 'pass'
        assert 'present' in message.lower()

    def test_sections_fail_lists_missing(self):
        content = '# Solution\n\n## Summary\n\nonly summary\n'
        status, message = _cac.check_solution_outline_sections(content)
        assert status == 'fail'
        assert 'overview' in message
        assert 'deliverables' in message

    def test_deliverable_count_fails_without_section(self):
        content = '# Solution\n\n## Summary\n\nno deliverables here\n'
        status, message, deliverables = _cac.check_deliverable_count(content)
        assert status == 'fail'
        assert deliverables == []

    def test_deliverable_count_fails_with_empty_section(self):
        content = '# Solution\n\n## Deliverables\n\nprose but no headings\n'
        status, _message, deliverables = _cac.check_deliverable_count(content)
        assert status == 'fail'
        assert deliverables == []

    def test_deliverable_count_passes_and_counts(self):
        status, message, deliverables = _cac.check_deliverable_count(_outline(deliverables=2))
        assert status == 'pass'
        assert len(deliverables) == 2
        assert '2 deliverables' in message


class TestExtractAffectedFiles:
    def test_collects_bullets_under_affected_block(self):
        files = _cac.extract_affected_files_per_deliverable(
            _outline(affected=['src/a.py', 'src/b.py'])
        )
        assert files == ['src/a.py', 'src/b.py']

    def test_collects_annotated_canonical_bullets_with_intent_stripped(self):
        """The canonical ``- `path` (intent)`` form extracts the bare path.

        The un-annotated case above is exactly why the pre-fix regex defect
        survived: its ``\\s*$`` anchor sat immediately after the closing
        backtick, so only un-annotated bullets ever matched.
        """
        files = _cac.extract_affected_files_per_deliverable(
            _outline(affected=['src/a.py', 'src/b.py'], annotation='write-replace')
        )
        assert files == ['src/a.py', 'src/b.py']

    def test_collects_bare_unbackticked_bullets(self):
        """The bare ``- path`` form remains supported — the fix is additive."""
        content = (
            '# Solution\n\n## Summary\n\ns\n\n## Overview\n\no\n\n## Deliverables\n\n'
            '### 1. One\n\n**Affected files:**\n- src/a.py\n- src/b.py\n'
        )
        assert _cac.extract_affected_files_per_deliverable(content) == ['src/a.py', 'src/b.py']

    def test_no_affected_block_yields_empty(self):
        assert _cac.extract_affected_files_per_deliverable(_outline()) == []


_ONE_DELIVERABLE = [{'number': '1', 'title': 'Deliverable 1'}]


class TestAffectedFilesRecall:
    """The declaration state is read per deliverable, so an empty declared set
    is discriminated by whether any deliverable actually carried the
    ``Affected files:`` heading: a heading that parsed to zero bullets is a
    ``fail`` naming that deliverable, while no deliverable declaring a section
    at all is a substantiated ``skip``.
    """

    def test_skip_when_outline_declares_no_deliverables(self, tmp_path):
        """Genuine no-deliverables outline → skip; nothing could be declared."""
        status, message, details = _cac.check_affected_files_recall(
            _outline(deliverables=0), tmp_path, []
        )
        assert status == 'skip'
        assert int(details['declared']) == 0
        assert int(details['deliverables']) == 0
        assert 'no deliverable declares' in message.lower()

    def test_fail_when_deliverables_present_but_nothing_parsed(self, tmp_path):
        """Heading present but zero bullets extracted → fail, not skip.

        This is the vacuous-skip defect: the deliverable declared an
        ``Affected files`` section yet the bullet parser produced nothing, so
        no coverage verdict is substantiated and the check must say so, naming
        the offending deliverable.
        """
        status, message, details = _cac.check_affected_files_recall(
            _outline(empty_affected_heading=True), tmp_path, _ONE_DELIVERABLE
        )
        assert status == 'fail'
        assert int(details['declared']) == 0
        assert int(details['deliverables']) == 1
        assert '1. Deliverable 1' in message
        assert details['unparseable_deliverables'] == [1]

    def test_skip_when_single_deliverable_declares_no_affected_section(self, tmp_path):
        """Heading absent on the only deliverable → skip, not a parse fail.

        Sibling of the loud-fail case above: a deliverable that never claimed
        to declare files has nothing to parse, so no parse failure is
        substantiated and the aggregate empty set is a genuine ``skip``.
        """
        status, message, details = _cac.check_affected_files_recall(
            _outline(), tmp_path, _ONE_DELIVERABLE
        )
        assert status == 'skip'
        assert int(details['declared']) == 0
        assert int(details['deliverables']) == 1
        assert 'unparseable_deliverables' not in details
        assert 'no deliverable declares' in message.lower()

    def test_pass_when_footprint_covers_declared(self, tmp_path):
        (tmp_path / 'references.json').write_text(
            json.dumps({'modified_files': ['src/a.py', 'src/b.py']}), encoding='utf-8'
        )
        status, _msg, details = _cac.check_affected_files_recall(
            _outline(affected=['src/a.py', 'src/b.py']), tmp_path, _ONE_DELIVERABLE
        )
        assert status == 'pass'
        assert int(details['found']) == 2
        assert float(details['recall_pct']) == 100.0

    def test_pass_when_annotated_bullets_cover_declared(self, tmp_path):
        """The canonical annotated bullet form yields the same recall verdict."""
        (tmp_path / 'references.json').write_text(
            json.dumps({'modified_files': ['src/a.py', 'src/b.py']}), encoding='utf-8'
        )
        status, _msg, details = _cac.check_affected_files_recall(
            _outline(affected=['src/a.py', 'src/b.py'], annotation='write-replace'),
            tmp_path,
            _ONE_DELIVERABLE,
        )
        assert status == 'pass'
        assert int(details['declared']) == 2
        assert int(details['found']) == 2

    def test_fail_when_recall_below_threshold(self, tmp_path):
        (tmp_path / 'references.json').write_text(
            json.dumps({'modified_files': ['src/a.py']}), encoding='utf-8'
        )
        status, _msg, details = _cac.check_affected_files_recall(
            _outline(affected=['src/a.py', 'src/b.py', 'src/c.py']), tmp_path, _ONE_DELIVERABLE
        )
        assert status == 'fail'
        assert int(details['found']) == 1
        assert sorted(details['missing']) == ['src/b.py', 'src/c.py']

    def test_fail_when_references_unreadable(self, tmp_path):
        (tmp_path / 'references.json').write_text('{ broken', encoding='utf-8')
        status, message, _details = _cac.check_affected_files_recall(
            _outline(affected=['src/a.py']), tmp_path, _ONE_DELIVERABLE
        )
        assert status == 'fail'
        assert 'unreadable' in message.lower()


class TestExactMatch:
    def test_pass_on_identical_non_empty_sets(self):
        status, _msg, outline_only, references_only = _cac.check_affected_files_exact_match(
            {'a', 'b'}, {'a', 'b'}
        )
        assert status == 'pass'
        assert outline_only == []
        assert references_only == []

    def test_inconclusive_on_both_empty(self):
        """Two empty sets are trivially equal and substantiate no verdict."""
        status, message, outline_only, references_only = _cac.check_affected_files_exact_match(
            set(), set()
        )
        assert status == 'inconclusive'
        assert 'substantiates no verdict' in message
        assert outline_only == []
        assert references_only == []

    def test_warn_when_only_one_side_empty(self):
        """A one-sided empty set is real drift, not an inconclusive comparison."""
        status, _msg, outline_only, references_only = _cac.check_affected_files_exact_match(
            {'a'}, set()
        )
        assert status == 'warn'
        assert outline_only == ['a']
        assert references_only == []

    def test_warn_and_surface_both_sides(self):
        status, _msg, outline_only, references_only = _cac.check_affected_files_exact_match(
            {'a', 'b'}, {'b', 'c'}
        )
        assert status == 'warn'
        assert outline_only == ['a']
        assert references_only == ['c']


class TestTaskDeliverableMatch:
    def test_skip_with_no_deliverables(self, tmp_path):
        status, _msg = _cac.check_task_deliverable_match([], tmp_path / 'tasks')
        assert status == 'skip'

    def test_fail_when_tasks_dir_missing(self, tmp_path):
        status, message = _cac.check_task_deliverable_match([{'n': '1'}], tmp_path / 'tasks')
        assert status == 'fail'
        assert 'directory missing' in message

    def test_fail_when_no_task_files(self, tmp_path):
        tasks = tmp_path / 'tasks'
        tasks.mkdir()
        status, message = _cac.check_task_deliverable_match([{'n': '1'}], tasks)
        assert status == 'fail'
        assert 'No TASK' in message

    def test_fail_when_deliverable_uncovered(self, tmp_path):
        tasks = tmp_path / 'tasks'
        tasks.mkdir()
        (tasks / 'TASK-001.json').write_text(json.dumps({'deliverable': 1}), encoding='utf-8')
        # Two deliverables declared but only deliverable 1 has a task.
        status, message = _cac.check_task_deliverable_match([{'n': '1'}, {'n': '2'}], tasks)
        assert status == 'fail'
        assert '[2]' in message

    def test_pass_when_all_covered(self, tmp_path):
        tasks = tmp_path / 'tasks'
        tasks.mkdir()
        (tasks / 'TASK-001.json').write_text(json.dumps({'deliverable': 1}), encoding='utf-8')
        (tasks / 'TASK-002.json').write_text(json.dumps({'deliverable': 2}), encoding='utf-8')
        status, message = _cac.check_task_deliverable_match([{'n': '1'}, {'n': '2'}], tasks)
        assert status == 'pass'
        assert 'All 2' in message

    def test_malformed_task_file_skipped_then_fails(self, tmp_path):
        tasks = tmp_path / 'tasks'
        tasks.mkdir()
        (tasks / 'TASK-001.json').write_text('{ corrupt', encoding='utf-8')
        # The corrupt file contributes no coverage, so deliverable 1 is missing.
        status, _message = _cac.check_task_deliverable_match([{'n': '1'}], tasks)
        assert status == 'fail'


class TestMetricsGenerated:
    def test_pass_when_present(self, tmp_path):
        (tmp_path / 'metrics.md').write_text('# Metrics\n', encoding='utf-8')
        status, _msg = _cac.check_metrics_generated(tmp_path)
        assert status == 'pass'

    def test_fail_when_absent(self, tmp_path):
        status, message = _cac.check_metrics_generated(tmp_path)
        assert status == 'fail'
        assert 'missing' in message


def _build_consistent_plan(plan_dir: Path, affected: list[str]) -> None:
    """Write a structurally-complete plan directory whose checks all pass."""
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'solution_outline.md').write_text(_outline(affected=affected), encoding='utf-8')
    (plan_dir / 'references.json').write_text(
        json.dumps({'modified_files': affected}), encoding='utf-8'
    )
    (plan_dir / 'metrics.md').write_text('# Metrics\n', encoding='utf-8')
    tasks = plan_dir / 'tasks'
    tasks.mkdir()
    (tasks / 'TASK-001.json').write_text(json.dumps({'deliverable': 1}), encoding='utf-8')


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
