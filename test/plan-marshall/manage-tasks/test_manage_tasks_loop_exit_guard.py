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
from toon_parser import serialize_toon

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
        _write_manifest(plan_context.plan_dir_for('guard-plan-25'), steps=['verify:module-tests'])

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
        """The pre-dispatch queue-peek call site keeps its exact previous shape.

        The namespace carries the parser's own defaults for every predicate flag
        (``None`` for the two integers, ``False`` for the store_true), because
        that is what the real CLI produces — a namespace with the attributes
        ABSENT would pass for the wrong reason.
        """
        result = cmd_loop_exit_guard(
            Namespace(
                plan_id='guard-peek',
                consumed_tokens=None,
                completed_tasks_delta=None,
                verification_handback=False,
                pending_verify_steps=None,
                provisional_cause=None,
            )
        )

        assert 'classification' not in result
        assert 'predicate_holds' not in result

    def test_cli_peek_without_predicate_flags_emits_no_classification(self, plan_context):
        """The real CLI path: a bare queue peek must not enter the mode either."""
        add_basic_task(plan_id='guard-cli-peek', title='One', deliverable=1, steps=['src/X.java'])

        result = run_script(SCRIPT_PATH, 'loop-exit-guard', '--plan-id', 'guard-cli-peek')

        assert result.returncode == 0
        assert 'classification:' not in result.stdout
        assert 'predicate_holds:' not in result.stdout


class TestTheHandbackExemptionCoversOnlyTheOwedTaskItNames:
    """A hand-back is decided by what it names, never by its mere presence.

    The two statements the shipped workflow carried — "a hand-back never reaches
    the predicate" and "never weaken the no-progress rule for a genuine stall" —
    reconcile only when the exemption is scoped to the owed task the hand-back
    names. A non-owed task that stalled in the same dispatch is still decided by
    the predicate, and a hand-back naming a step id the manifest does not carry
    exempts nothing at all.
    """

    _TOKENS = 536031
    _STEP = 'verify:module-tests'

    def test_a_stall_beside_a_handback_is_classified_error(self, plan_context):
        """One owed task handed back, one non-owed task stalled → the stall decides."""
        plan_id = 'guard-handback-beside-stall'
        _owed_task(plan_id, number=1)
        add_basic_task(plan_id=plan_id, title='Stalled non-owed', deliverable=2, steps=['src/Stalled.java'])
        cmd_update(_update_ns(plan_id=plan_id, number=2, status='in_progress'))
        _write_manifest(plan_context.plan_dir_for(plan_id), steps=[self._STEP])

        result = cmd_loop_exit_guard(
            _ns_with_predicate(
                plan_id,
                consumed_tokens=self._TOKENS,
                completed_tasks_delta=0,
                verification_handback=True,
                pending_verify_steps=self._STEP,
            )
        )

        assert result['verification_handback_valid'] is True
        assert result['predicate_in_progress_count'] == 1
        assert result['predicate_holds'] is True
        assert result['classification'] == 'error'
        assert result['classification_reason'] == 'no_progress_predicate_holds_beside_handback'

    def test_a_handback_alone_stays_the_handback_cause(self, plan_context):
        """Only the owed task is in flight → the prescribed hand-back classifies."""
        plan_id = 'guard-handback-alone'
        _owed_task(plan_id, number=1)
        _write_manifest(plan_context.plan_dir_for(plan_id), steps=[self._STEP])

        result = cmd_loop_exit_guard(
            _ns_with_predicate(
                plan_id,
                consumed_tokens=self._TOKENS,
                completed_tasks_delta=0,
                verification_handback=True,
                pending_verify_steps=self._STEP,
            )
        )

        assert result['verification_handback_valid'] is True
        assert result['classification'] == 'verification_handback'
        assert result['classification_reason'] == 'declared_orchestrator_build_handback'

    def test_a_handback_naming_a_step_outside_the_manifest_does_not_exempt(self, plan_context):
        """The manifest's composed list is the authority for what a hand-back may name."""
        plan_id = 'guard-handback-unknown-step'
        _owed_task(plan_id, number=1)
        _write_manifest(plan_context.plan_dir_for(plan_id), steps=['verify:quality-gate'])

        result = cmd_loop_exit_guard(
            _ns_with_predicate(
                plan_id,
                consumed_tokens=self._TOKENS,
                completed_tasks_delta=0,
                verification_handback=True,
                pending_verify_steps=self._STEP,
            )
        )

        assert result['verification_handback_valid'] is False
        assert result['classification'] == 'voluntary_checkpoint'
        assert result['classification_reason'] == 'no_progress_predicate_false'


class TestCompletedTasksDeltaHasAStatedSourceAndNoZeroDefault:
    """An absent delta is undecidable, and the done count travels on the call."""

    def test_consumed_tokens_without_the_delta_is_a_named_error(self, plan_context):
        """A delta nobody supplied is not a delta of zero."""
        add_basic_task(plan_id='guard-delta-absent', title='Mid', deliverable=1, steps=['src/Mid.java'])
        cmd_update(_update_ns(plan_id='guard-delta-absent', number=1, status='in_progress'))

        result = cmd_loop_exit_guard(
            _ns_with_predicate('guard-delta-absent', consumed_tokens=536031, completed_tasks_delta=None)
        )

        assert result['status'] == 'error'
        assert result['error'] == 'no_progress_not_decidable'
        assert '--completed-tasks-delta' in result['message']
        assert 'classification' not in result

    def test_the_delta_without_consumed_tokens_is_the_same_named_error(self, plan_context):
        """The pair is required in both directions — neither input defaults."""
        add_basic_task(plan_id='guard-tokens-absent', title='Mid', deliverable=1, steps=['src/Mid.java'])
        cmd_update(_update_ns(plan_id='guard-tokens-absent', number=1, status='in_progress'))

        result = cmd_loop_exit_guard(
            _ns_with_predicate('guard-tokens-absent', consumed_tokens=None, completed_tasks_delta=0)
        )

        assert result['status'] == 'error'
        assert result['error'] == 'no_progress_not_decidable'
        assert '--consumed-tokens' in result['message']

    def test_a_supplied_delta_keeps_a_progressing_dispatch_out_of_error(self, plan_context):
        """A non-owed task in progress with a completed task is progress, not a stall.

        The control for the absent-delta case above: the SAME queue shape with the
        delta supplied is decided by the predicate's second conjunct, so the
        dispatch is not `error`. Only the missing input turns it undecidable.
        """
        add_basic_task(plan_id='guard-delta-supplied', title='Mid', deliverable=1, steps=['src/Mid.java'])
        cmd_update(_update_ns(plan_id='guard-delta-supplied', number=1, status='in_progress'))

        result = cmd_loop_exit_guard(
            _ns_with_predicate('guard-delta-supplied', consumed_tokens=536031, completed_tasks_delta=1)
        )

        assert result['predicate_in_progress_count'] == 1
        assert result['predicate_completed_tasks_delta'] == 1
        assert result['predicate_holds'] is False
        assert result['classification'] == 'voluntary_checkpoint'

    def test_the_guard_reports_the_done_count_the_delta_is_measured_against(self, plan_context):
        """The delta's source is the done count this same call reports."""
        add_basic_task(plan_id='guard-done-count', title='Done one', deliverable=1, steps=['src/A.java'])
        add_basic_task(plan_id='guard-done-count', title='Still pending', deliverable=2, steps=['src/B.java'])
        cmd_finalize_step(_finalize_step_ns(plan_id='guard-done-count', task=1, step=1, outcome='done'))

        result = cmd_loop_exit_guard(_loop_exit_guard_ns(plan_id='guard-done-count'))

        assert result['done_count'] == 1


def _write_manifest(plan_dir, *, steps):
    """Write a minimal ``execution.toon`` carrying ``phase_5.verification_steps``."""
    plan_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        'manifest_version': 1,
        'plan_id': plan_dir.name,
        'phase_5': {'verification_steps': list(steps)},
        'phase_6': {'steps': []},
    }
    (plan_dir / 'execution.toon').write_text(serialize_toon(manifest), encoding='utf-8')


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
    _write_manifest(plan_context.plan_dir_for('guard-cli-b7'), steps=['verify:module-tests'])

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
