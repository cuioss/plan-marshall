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

from _check_artifact_consistency_behavior_fixtures import _cac, _fr


class TestFootprintResolvedPredicate:
    """``footprint_resolved`` is the ONE named guard over the resolution state.

    An inline truthiness check is NOT equivalent: ``not footprint`` is also true
    for a resolved-but-empty footprint, which is a measured result. The
    resolved-empty case below is what makes the two readings distinguishable.
    """

    def test_unresolved_sentinel_reads_unresolved(self):
        assert _cac.footprint_resolved(_fr.FOOTPRINT_UNRESOLVED) is False

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
            {'a', 'b'}, _fr.FOOTPRINT_UNRESOLVED
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

    #: The producer/consumer pair the absence verdict is derived from — read
    #: from the module under test rather than restated as literals, so renaming
    #: a finalize step id moves the production check and this test together. A
    #: restated literal would leave the live-registry guards below asserting the
    #: OLD id and failing while naming the wrong cause.
    _PRODUCER = _cac._METRICS_PRODUCER_STEP
    _CONSUMER = _cac._METRICS_CONSUMER_STEP

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
