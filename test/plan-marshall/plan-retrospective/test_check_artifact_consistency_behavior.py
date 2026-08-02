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

    def test_inconclusive_when_footprint_unresolvable(self, tmp_path):
        """No footprint could be resolved → inconclusive, and NO percentage.

        A recall figure computed from an unresolved footprint is a confident
        claim about an input that was never measured; ``0%`` is the shape that
        defect takes.
        """
        status, message, details = _cac.check_affected_files_recall(
            _outline(affected=['src/a.py']), tmp_path, _ONE_DELIVERABLE
        )
        assert status == 'inconclusive'
        assert 'unmeasurable' in message
        assert details['footprint_resolved'] is False
        assert 'recall_pct' not in details

    def test_measured_verdict_when_footprint_resolved_to_empty(self, tmp_path):
        """Control: a present-but-empty ``modified_files`` still measures 0%.

        Without this the inconclusive sentinel could be satisfied by treating
        every empty footprint as unmeasurable, which would silence a genuine
        zero-coverage failure.
        """
        (tmp_path / 'references.json').write_text(
            json.dumps({'modified_files': []}), encoding='utf-8'
        )
        status, _msg, details = _cac.check_affected_files_recall(
            _outline(affected=['src/a.py']), tmp_path, _ONE_DELIVERABLE
        )
        assert status == 'fail'
        assert details['footprint_resolved'] is True
        assert float(details['recall_pct']) == 0.0


class TestFootprintResolvedPredicate:
    """``footprint_resolved`` is the ONE named guard over the resolution state.

    An inline truthiness check is NOT equivalent: ``not footprint`` is also true
    for a resolved-but-empty footprint, which is a measured result. The
    resolved-empty case below is what makes the two readings distinguishable.
    """

    def test_unresolved_sentinel_reads_unresolved(self):
        assert _cac.footprint_resolved(_cac.FOOTPRINT_UNRESOLVED) is False

    def test_resolved_empty_set_reads_resolved(self):
        assert _cac.footprint_resolved(set()) is True

    def test_resolved_non_empty_set_reads_resolved(self):
        assert _cac.footprint_resolved({'src/a.py'}) is True


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

    def test_inconclusive_when_footprint_unresolvable(self):
        """No right-hand side to compare against — never a confident ``warn``.

        The peer consumes the same resolver as the recall check, so an
        unresolvable footprint that silenced only recall would still be reported
        here as confident drift.
        """
        status, message, outline_only, references_only = _cac.check_affected_files_exact_match(
            {'a', 'b'}, _cac.FOOTPRINT_UNRESOLVED
        )
        assert status == 'inconclusive'
        assert 'could not be resolved' in message
        assert outline_only == []
        assert references_only == []


class TestSummarizeChecks:
    """Every emitted status lands in a bucket, and the buckets reconcile.

    A status counted by no bucket reads to a summary consumer as a check that
    does not exist — the same unmeasurable-rendered-as-absent shape the
    ``inconclusive`` footprint verdict removes.
    """

    def test_legacy_buckets_are_present_even_at_zero(self):
        assert _cac.summarize_checks([]) == {'passed': 0, 'failed': 0, 'skipped': 0}

    def test_legacy_statuses_count_under_their_established_names(self):
        checks = [
            {'name': 'a', 'status': 'pass'},
            {'name': 'b', 'status': 'pass'},
            {'name': 'c', 'status': 'fail'},
            {'name': 'd', 'status': 'skip'},
        ]
        summary = _cac.summarize_checks(checks)
        assert summary['passed'] == 2
        assert summary['failed'] == 1
        assert summary['skipped'] == 1

    def test_warn_info_and_inconclusive_each_get_a_bucket(self):
        """The hole was never ``inconclusive``-only — ``warn`` and ``info`` too."""
        checks = [
            {'name': 'a', 'status': 'warn'},
            {'name': 'b', 'status': 'info'},
            {'name': 'c', 'status': 'inconclusive'},
        ]
        summary = _cac.summarize_checks(checks)
        assert summary['warn'] == 1
        assert summary['info'] == 1
        assert summary['inconclusive'] == 1

    def test_a_status_introduced_later_is_counted_without_editing_the_map(self):
        """Buckets derive from the checks, so a new status cannot drop out."""
        checks = [{'name': 'a', 'status': 'not_yet_invented'}]
        summary = _cac.summarize_checks(checks)
        assert summary['not_yet_invented'] == 1
        assert sum(summary.values()) == len(checks)

    def test_buckets_reconcile_against_the_check_count(self):
        checks = [
            {'name': 'a', 'status': 'pass'},
            {'name': 'b', 'status': 'fail'},
            {'name': 'c', 'status': 'skip'},
            {'name': 'd', 'status': 'warn'},
            {'name': 'e', 'status': 'info'},
            {'name': 'f', 'status': 'inconclusive'},
        ]
        assert sum(_cac.summarize_checks(checks).values()) == len(checks)


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
    """``metrics_generated`` in-process, against the LIVE step registry.

    The sibling suite's ``TestMetricsGeneratedOrderingDerivedVerdict`` owns the
    matched positive/negative control pair over STUBBED orderings (producer-later
    → ``inconclusive``, producer-earlier → ``fail``, equal → ``fail``,
    unresolvable → ``inconclusive``, discovery failure → ``inconclusive``). This
    class deliberately does not restate any of that; it covers the complementary
    angle the stubs cannot — the verdict the check actually reaches for the
    in-process plan directory under the ordering the live registry declares.
    """

    #: The producer/consumer pair the absence verdict is derived from — the same
    #: two steps the production check resolves through discovery.
    _PRODUCER = 'default:record-metrics'
    _CONSUMER = 'plan-marshall:plan-retrospective'

    def test_pass_when_present(self, tmp_path):
        (tmp_path / 'metrics.md').write_text('# Metrics\n', encoding='utf-8')
        status, _msg = _cac.check_metrics_generated(tmp_path)
        assert status == 'pass'

    def test_absence_verdict_follows_the_live_step_ordering(self, tmp_path):
        """An absent metrics.md yields the verdict the LIVE ordering implies.

        Absence only substantiates "the producing step did not run" once that
        step has had its turn. ``default:record-metrics`` is ordered after the
        consuming ``plan-marshall:plan-retrospective``, so on a
        correctly-functioning run the artifact legitimately does not exist yet
        and the honest verdict is ``inconclusive`` — not the confident ``fail``
        this test used to pin.

        The expectation is DERIVED from the orders the live registry declares
        rather than restated as a literal, so a renumbering moves the test with
        the behaviour instead of leaving it stale again. The message assertion
        is what keeps it non-vacuous: an unconditional verdict cannot name the
        two orders it never resolved, and the sibling ``test_pass_when_present``
        above rules out an unconditional verdict in the other direction.
        """
        producer_order = _cac._resolve_step_order(self._PRODUCER)
        consumer_order = _cac._resolve_step_order(self._CONSUMER)
        assert isinstance(producer_order, int) and isinstance(consumer_order, int), (
            'Both orders must resolve from the live registry, or the derived '
            f'expectation below asserts nothing: producer={producer_order!r}, '
            f'consumer={consumer_order!r}'
        )

        status, message = _cac.check_metrics_generated(tmp_path)

        expected = 'inconclusive' if producer_order > consumer_order else 'fail'
        assert status == expected, (
            f'{self._PRODUCER} (order {producer_order}) against {self._CONSUMER} '
            f'(order {consumer_order}) implies {expected!r}; got {status!r} — {message}'
        )
        assert self._PRODUCER in message and self._CONSUMER in message, (
            f'The verdict must name the pair it was derived from: {message}'
        )
        assert str(producer_order) in message and str(consumer_order) in message, (
            'The verdict must name the ORDERS it was derived from — a check that '
            f'returned an unconditional status could not have resolved them: {message}'
        )


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
        # No references.json at all → neither resolution tier answers.
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


def _recall_verdict(result: dict) -> tuple[str, str]:
    """Return ``(check_status, finding_severity)`` for ``affected_files_recall``.

    The finding is paired to the check by the check's OWN message rather than by
    a substring literal, so the pairing survives a message rewording and can
    never latch onto the exact-match peer's finding by accident.
    """
    recall = _check(result['checks'], 'affected_files_recall')
    assert recall is not None, 'cmd_run must always emit the affected_files_recall check'
    severities = [f['severity'] for f in result['findings'] if f['message'] == recall['message']]
    assert len(severities) == 1, (
        f'Expected exactly one finding raised by affected_files_recall '
        f'({recall["message"]!r}), got {severities!r} from {result["findings"]!r}'
    )
    return recall['status'], severities[0]


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
        """No references.json at all → neither resolution tier answers."""
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
