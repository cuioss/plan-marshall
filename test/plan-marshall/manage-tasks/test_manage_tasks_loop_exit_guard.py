#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for manage-tasks.py loop-exit-guard subcommand.

Split from test_manage_tasks.py: covers the script-level enforcement of the
phase-5-execute "unfinished > 0 → must continue" invariant. The predicate
is the union of `pending` AND `in_progress` task buckets, both of which
block clean exit. A pending-only predicate is too narrow — it lets a plan with
only in_progress work exit cleanly — which is why in_progress is in the
blocking set.

Contract:
  - pending > 0 OR in_progress > 0 → status: continue,
    {pending,in_progress}_count and {pending,in_progress}_ids reflect both
    axes.
  - pending == 0 AND in_progress == 0 → status: success, all four count/id
    fields present with zero values.

Behaviour parity is checked against `cmd_list --status pending` over the
same fixtures (both reads target the same on-disk machinery via
`get_all_tasks`).
"""

from argparse import Namespace

from conftest import run_script

from _manage_tasks_fixtures import (
    SCRIPT_PATH,
    _finalize_step_ns,
    _list_ns,
    _update_ns,
    add_basic_task,
    cmd_finalize_step,
    cmd_list,
    cmd_loop_exit_guard,
    cmd_update,
)


def _loop_exit_guard_ns(plan_id='test-plan'):
    """Build Namespace for cmd_loop_exit_guard (single --plan-id field)."""
    return Namespace(plan_id=plan_id)


def test_loop_exit_guard_continue_when_pending_tasks_remain(plan_context):
    """pending > 0 yields status: continue with pending_count and pending_ids set."""
    add_basic_task(
        plan_id='guard-continue',
        title='First',
        deliverable=1,
        steps=['src/main/java/File.java'],
    )
    add_basic_task(
        plan_id='guard-continue',
        title='Second',
        deliverable=2,
        steps=['src/main/java/File.java'],
    )

    result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-continue'))

    assert result['status'] == 'continue'
    assert result['plan_id'] == 'guard-continue'
    assert result['pending_count'] == 2
    assert sorted(result['pending_ids']) == [1, 2]
    assert result['in_progress_count'] == 0
    assert result['in_progress_ids'] == []
    assert 'pending' in result['message'].lower()


def test_loop_exit_guard_success_when_queue_empty(plan_context):
    """unfinished == 0 yields status: success with all four count/id fields zeroed."""
    result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-empty'))

    assert result['status'] == 'success'
    assert result['plan_id'] == 'guard-empty'
    assert result['pending_count'] == 0
    assert result['pending_ids'] == []
    assert result['in_progress_count'] == 0
    assert result['in_progress_ids'] == []


def test_loop_exit_guard_success_when_only_done_tasks_remain(plan_context):
    """All tasks done → status: success even when total > 0."""
    add_basic_task(
        plan_id='guard-all-done',
        title='Only',
        deliverable=1,
        steps=['src/main/java/File.java'],
    )
    cmd_finalize_step(_finalize_step_ns(plan_id='guard-all-done', task=1, step=1, outcome='done'))

    result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-all-done'))

    assert result['status'] == 'success'
    assert result['pending_count'] == 0
    assert result['pending_ids'] == []
    assert result['in_progress_count'] == 0
    assert result['in_progress_ids'] == []


def test_loop_exit_guard_ignores_blocked_and_failed_status(plan_context):
    """`blocked`/`failed` are terminal non-unfinished states — they do not block clean exit."""
    add_basic_task(
        plan_id='guard-mixed',
        title='Pending one',
        deliverable=1,
        steps=['src/main/java/A.java'],
    )
    add_basic_task(
        plan_id='guard-mixed',
        title='Will be failed',
        deliverable=2,
        steps=['src/main/java/B.java'],
    )
    cmd_finalize_step(_finalize_step_ns(plan_id='guard-mixed', task=2, step=1, outcome='failed', reason='intentional'))

    result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-mixed'))

    assert result['status'] == 'continue'
    assert result['pending_count'] == 1
    assert result['pending_ids'] == [1]
    assert result['in_progress_count'] == 0
    assert result['in_progress_ids'] == []


def test_loop_exit_guard_blocks_when_only_in_progress(plan_context):
    """in_progress > 0 with pending == 0 → status: continue (broadened predicate)."""
    add_basic_task(
        plan_id='guard-in-progress-only',
        title='Mid-flight',
        deliverable=1,
        steps=['src/main/java/Mid.java'],
    )
    cmd_update(_update_ns(plan_id='guard-in-progress-only', number=1, status='in_progress'))

    result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-in-progress-only'))

    assert result['status'] == 'continue'
    assert result['pending_count'] == 0
    assert result['pending_ids'] == []
    assert result['in_progress_count'] == 1
    assert result['in_progress_ids'] == [1]
    assert 'in_progress' in result['message'].lower()


def test_loop_exit_guard_emits_in_progress_fields_when_clean(plan_context):
    """status: success branch carries `in_progress_count: 0` and `in_progress_ids: []`."""
    result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-clean-fields'))

    assert result['status'] == 'success'
    assert result['pending_count'] == 0
    assert result['pending_ids'] == []
    assert 'in_progress_count' in result
    assert result['in_progress_count'] == 0
    assert 'in_progress_ids' in result
    assert result['in_progress_ids'] == []


def test_loop_exit_guard_blocks_when_pending_and_in_progress_both_present(plan_context):
    """Both buckets non-empty → status: continue, both counts > 0."""
    add_basic_task(
        plan_id='guard-both-buckets',
        title='Still pending',
        deliverable=1,
        steps=['src/main/java/P.java'],
    )
    add_basic_task(
        plan_id='guard-both-buckets',
        title='Mid-flight',
        deliverable=2,
        steps=['src/main/java/I.java'],
    )
    cmd_update(_update_ns(plan_id='guard-both-buckets', number=2, status='in_progress'))

    result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-both-buckets'))

    assert result['status'] == 'continue'
    assert result['pending_count'] == 1
    assert result['pending_ids'] == [1]
    assert result['in_progress_count'] == 1
    assert result['in_progress_ids'] == [2]
    assert 'pending' in result['message'].lower()
    assert 'in_progress' in result['message'].lower()


def test_loop_exit_guard_parity_with_list_status_pending(plan_context):
    """The guard's pending bucket reads the same on-disk state as `list --status pending`."""
    add_basic_task(plan_id='guard-parity', title='A', deliverable=1, steps=['src/A.java'])
    add_basic_task(plan_id='guard-parity', title='B', deliverable=2, steps=['src/B.java'])
    add_basic_task(plan_id='guard-parity', title='C', deliverable=3, steps=['src/C.java'])
    cmd_finalize_step(_finalize_step_ns(plan_id='guard-parity', task=1, step=1, outcome='done'))

    guard = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-parity'))
    listed = cmd_list(_list_ns(plan_id='guard-parity', status='pending'))

    listed_ids = sorted(row['number'] for row in listed['tasks_table'])
    assert guard['status'] == 'continue'
    assert guard['pending_count'] == len(listed_ids) == listed['counts']['pending']
    assert sorted(guard['pending_ids']) == listed_ids
    assert guard['in_progress_count'] == 0
    assert guard['in_progress_ids'] == []


def test_loop_exit_guard_cli_subcommand_registered(plan_context):
    """End-to-end subprocess invocation surfaces the guard via the CLI."""
    add_basic_task(plan_id='guard-cli', title='One', deliverable=1, steps=['src/X.java'])

    result = run_script(
        SCRIPT_PATH,
        'loop-exit-guard',
        '--plan-id',
        'guard-cli',
    )

    assert result.returncode == 0
    assert 'status: continue' in result.stdout
    assert 'pending_count: 1' in result.stdout
    assert 'in_progress_count: 0' in result.stdout


def _owed_task(plan_id: str, number: int = 1, title: str = 'Owed') -> None:
    """Create one task and close it with ``--verification-owed`` so it is held open."""
    add_basic_task(plan_id=plan_id, title=title, deliverable=1, steps=['src/Owed.java'])
    ns = _finalize_step_ns(plan_id=plan_id, task=number, step=1, outcome='done')
    ns.verification_owed = True
    cmd_finalize_step(ns)


class TestLoopExitGuardReportsOwedTasksSeparately:
    """An owed task blocks the clean exit but is reported as its own population."""

    def test_only_owed_task_continues_and_is_reported_by_id(self, plan_context):
        """The guard still says `continue`, and names the owed id separately."""
        _owed_task('guard-owed-only', number=1)

        result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-owed-only'))

        assert result['status'] == 'continue'
        assert result['pending_count'] == 0
        assert result['in_progress_count'] == 1
        assert result['in_progress_ids'] == [1]
        assert result['owed_count'] == 1
        assert result['owed_ids'] == [1]

    def test_a_clean_queue_reports_zero_owed_fields(self, plan_context):
        """Both branches carry the owed fields, so a caller needs no presence test."""
        result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-owed-clean'))

        assert result['status'] == 'success'
        assert result['owed_count'] == 0
        assert result['owed_ids'] == []


class TestNoProgressClassification:
    """The B7 predicate is evaluated by the verb, and the two exemptions hold."""

    #: The plan-25 shape: one owed task in progress, no completion, 536,031 tokens.
    _PLAN_25_TOKENS = 536031

    def test_plan_25_shape_is_the_handback_cause_not_error(self, plan_context):
        """One owed task + a declared hand-back classifies as `verification_handback`."""
        _owed_task('guard-plan-25', number=1)

        result = cmd_loop_exit_guard(
            _ns_with_predicate(
                'guard-plan-25',
                consumed_tokens=self._PLAN_25_TOKENS,
                completed_tasks_delta=0,
                verification_handback=True,
                pending_verify_steps='verify:module-tests',
            )
        )

        assert result['classification'] == 'verification_handback'
        assert result['classification_reason'] == 'declared_orchestrator_build_handback'
        assert result['predicate_in_progress_count'] == 0

    def test_unowned_in_progress_task_without_a_handback_is_still_error(self, plan_context):
        """Same delta and token count, no owed marker and no hand-back → `error`."""
        add_basic_task(plan_id='guard-genuine-stall', title='Mid', deliverable=1, steps=['src/Mid.java'])
        cmd_update(_update_ns(plan_id='guard-genuine-stall', number=1, status='in_progress'))

        result = cmd_loop_exit_guard(
            _ns_with_predicate(
                'guard-genuine-stall',
                consumed_tokens=self._PLAN_25_TOKENS,
                completed_tasks_delta=0,
            )
        )

        assert result['classification'] == 'error'
        assert result['predicate_holds'] is True
        assert result['predicate_consumed_tokens'] == self._PLAN_25_TOKENS

    def test_owed_task_never_counts_toward_the_predicate(self, plan_context):
        """The owed subtraction is independent of the hand-back discriminator."""
        _owed_task('guard-owed-predicate', number=1)

        result = cmd_loop_exit_guard(
            _ns_with_predicate(
                'guard-owed-predicate',
                consumed_tokens=self._PLAN_25_TOKENS,
                completed_tasks_delta=0,
            )
        )

        assert result['predicate_in_progress_count'] == 0
        assert result['predicate_holds'] is False
        assert result['classification'] == 'voluntary_checkpoint'

    def test_a_discriminator_without_handed_back_steps_is_not_a_handback(self, plan_context):
        """`verification_handback: true` with an empty list is malformed, not a hand-back."""
        add_basic_task(plan_id='guard-empty-handback', title='Mid', deliverable=1, steps=['src/Mid.java'])
        cmd_update(_update_ns(plan_id='guard-empty-handback', number=1, status='in_progress'))

        result = cmd_loop_exit_guard(
            _ns_with_predicate(
                'guard-empty-handback',
                consumed_tokens=self._PLAN_25_TOKENS,
                completed_tasks_delta=0,
                verification_handback=True,
            )
        )

        assert result['verification_handback_valid'] is False
        assert result['classification'] == 'error'

    def test_a_completed_task_keeps_the_voluntary_classification(self, plan_context):
        """The 50K threshold alone is not a stall: a delta ≥ 1 is progress."""
        _owed_task('guard-progress', number=1)

        result = cmd_loop_exit_guard(
            _ns_with_predicate(
                'guard-progress',
                consumed_tokens=self._PLAN_25_TOKENS,
                completed_tasks_delta=1,
            )
        )

        assert result['predicate_holds'] is False
        assert result['classification'] == 'voluntary_checkpoint'

    def test_no_progress_mode_is_opt_in(self, plan_context):
        """The pre-dispatch queue-peek call site keeps its exact previous shape."""
        result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-peek'))

        assert 'classification' not in result
        assert 'predicate_holds' not in result


def _ns_with_predicate(
    plan_id: str,
    *,
    consumed_tokens: int | None = None,
    completed_tasks_delta: int | None = None,
    verification_handback: bool = False,
    pending_verify_steps: str | None = None,
    provisional_cause: str | None = None,
):
    """Build a Namespace carrying the B7 predicate inputs."""
    ns = Namespace(
        plan_id=plan_id,
        consumed_tokens=consumed_tokens,
        completed_tasks_delta=completed_tasks_delta,
        verification_handback=verification_handback,
        pending_verify_steps=pending_verify_steps,
        provisional_cause=provisional_cause,
    )
    return ns


def test_loop_exit_guard_cli_accepts_the_b7_predicate_flags(plan_context):
    """The documented invocation parses end-to-end through the real executor surface."""
    _owed_task('guard-cli-b7', number=1)

    result = run_script(
        SCRIPT_PATH,
        'loop-exit-guard',
        '--plan-id',
        'guard-cli-b7',
        '--provisional-cause',
        'voluntary_checkpoint',
        '--consumed-tokens',
        '536031',
        '--completed-tasks-delta',
        '0',
        '--verification-handback',
        '--pending-verify-steps',
        'verify:module-tests',
    )

    assert result.returncode == 0
    assert 'classification: verification_handback' in result.stdout
    assert 'owed_count: 1' in result.stdout
