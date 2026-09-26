# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_decision_rules_fixtures import (
    PlanContext,
    _compose_ns,
    _restore_footprint_resolver,
    _seed_task_file,
    cmd_compose,
)


class TestEarlyTerminateTaskQueueGuard:
    """Rule 1 (early_terminate_analysis) requires the task queue to be empty.

    An analysis-only plan that produces zero affected files but still queues at
    least one deliverable task must NOT short-circuit phase-5 before that task
    runs. The composer reads ``tasks/TASK-*.json`` directly and ANDs the
    ``affected_files_count==0`` condition with "no pending or in-progress task".
    A genuine no-op plan, with no task files on disk, still early-terminates.
    """

    def test_early_terminate_when_task_queue_empty(self):
        """Case (i): analysis + affected_files=0 + task_queue empty → early_terminate=True."""
        with PlanContext('et-queue-empty'):
            # No tasks/TASK-*.json seeded — queue is empty.
            ns = _compose_ns(
                plan_id='et-queue-empty',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'early_terminate_analysis'
            assert result['phase_5']['early_terminate'] is True

    def test_falls_through_to_default_when_task_queue_non_empty(self):
        """Case (ii): analysis + affected_files=0 + task_queue pending → Rule 7 default."""
        with PlanContext('et-queue-pending'):
            _seed_task_file('et-queue-pending', task_number=1, status='pending')
            ns = _compose_ns(
                plan_id='et-queue-pending',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'default'
            assert result['phase_5']['early_terminate'] is False

    def test_rule_label_preserved_for_genuine_early_terminate(self):
        """Case (iii): the ``early_terminate_analysis`` rule label still appears for case (i)."""
        with PlanContext('et-queue-label'):
            ns = _compose_ns(
                plan_id='et-queue-label',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'early_terminate_analysis'

    def test_falls_through_when_task_queue_in_progress(self):
        """An in_progress task also blocks the short-circuit (symmetric to pending)."""
        with PlanContext('et-queue-inprogress'):
            _seed_task_file('et-queue-inprogress', task_number=1, status='in_progress')
            ns = _compose_ns(
                plan_id='et-queue-inprogress',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'default'
            assert result['phase_5']['early_terminate'] is False

    def test_done_tasks_do_not_block_short_circuit(self):
        """A queue containing ONLY done tasks does NOT block early_terminate."""
        with PlanContext('et-queue-done'):
            _seed_task_file('et-queue-done', task_number=1, status='done')
            ns = _compose_ns(
                plan_id='et-queue-done',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'early_terminate_analysis'
            assert result['phase_5']['early_terminate'] is True
