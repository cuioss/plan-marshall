#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for review_completeness.py — the automatic-review step-done guard predicate.

Covers the three states the D3 guard distinguishes against the pr-comment findings
store, and the TRIAGE-STATE awareness of the ``complete`` verdict (``triage_ran``):

    complete   — every REQUIRED bot produced a fetched finding
    pending    — a bot has an unresolved (pending) finding; whether this blocks
                 ``complete`` depends on ``triage_ran`` AND on the bot being required
    unfetched  — a bot produced no finding at all (blocks only when required)

**The quorum is over ``required_bots`` ONLY.** An optional bot is classified and
reported for visibility but never gates ``complete`` — its silence is not a
failure. See ``automatic-review/standards/bot-participation-contract.md``.

``triage_ran=False`` (default, the FIND-only step) treats a ``pending`` finding as
the expected awaiting-triage state that does NOT block; only ``unfetched`` required
bots gate. ``triage_ran=True`` (triage has run) treats a still-``pending`` required
finding as a real incompleteness that blocks.

The store is seeded in-process via ``_findings_core.add_finding`` /
``resolve_finding`` under the ``plan_context`` PLAN_BASE_DIR sandbox, so
``check_completeness`` reads a real per-plan store rather than a stub.
"""

from __future__ import annotations

import sys

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import review_completeness as rc  # noqa: E402
import _findings_core as fc  # noqa: E402


def _seed(plan_id: str, bot_kind: str, resolution: str = 'pending') -> str:
    """File one pr-comment finding for ``bot_kind`` and optionally resolve it.

    Returns the finding's hash_id. When ``resolution`` is not ``pending`` the
    finding is immediately resolved to that value so it counts as handled.
    """
    result = fc.add_finding(
        plan_id,
        'pr-comment',
        title=f'{bot_kind} comment',
        detail=f'thread from {bot_kind}',
        bot_kind=bot_kind,
        kind='inline',
    )
    assert result['status'] == 'success', result
    hash_id: str = result['hash_id']
    if resolution != 'pending':
        resolved = fc.resolve_finding(plan_id, hash_id, resolution)
        assert resolved['status'] == 'success', resolved
    return hash_id


def test_pending_bot_does_not_block_pre_triage(plan_context):
    """Direction (a): pre-triage (``triage_ran=False``) a pending finding does NOT block.

    At the FIND-only step a fetched-but-pending finding is the expected
    awaiting-triage state, so the store is ``complete`` — no loop-back is
    manufactured. ``pending_bots`` is still reported for visibility.
    """
    plan_id = 'rc-pending-pre-triage'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='pending')

    result = rc.check_completeness(plan_id, ['coderabbit'])

    assert result['status'] == 'success'
    assert result['complete'] is True
    assert result['pending_bots'] == ['coderabbit']
    assert result['unfetched_bots'] == []


def test_pending_bot_blocks_after_triage(plan_context):
    """Direction (b): with ``triage_ran=True`` a still-pending finding IS incomplete.

    The SAME pending-only store that passed pre-triage loops back once triage has
    run — a finding still pending after triage is a genuine incompleteness.
    """
    plan_id = 'rc-pending-post-triage'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='pending')

    result = rc.check_completeness(plan_id, ['coderabbit'], triage_ran=True)

    assert result['status'] == 'success'
    assert result['complete'] is False
    assert result['pending_bots'] == ['coderabbit']
    assert result['unfetched_bots'] == []


def test_fully_resolved_is_complete(plan_context):
    """A required bot whose only finding is resolved reports complete."""
    plan_id = 'rc-resolved'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='fixed')

    result = rc.check_completeness(plan_id, ['coderabbit'])

    assert result['status'] == 'success'
    assert result['complete'] is True
    assert result['pending_bots'] == []
    assert result['unfetched_bots'] == []


def test_unfetched_bot_blocks(plan_context):
    """A required bot that produced no finding at all is unfetched → incomplete.

    Unfetched blocks in BOTH triage modes — it is a FIND-completeness gap (a
    review never surfaced), independent of whether triage has run.
    """
    plan_id = 'rc-unfetched'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='fixed')

    pre_triage = rc.check_completeness(plan_id, ['coderabbit', 'sourcery'])
    assert pre_triage['status'] == 'success'
    assert pre_triage['complete'] is False
    assert pre_triage['pending_bots'] == []
    assert pre_triage['unfetched_bots'] == ['sourcery']

    post_triage = rc.check_completeness(plan_id, ['coderabbit', 'sourcery'], triage_ran=True)
    assert post_triage['complete'] is False
    assert post_triage['unfetched_bots'] == ['sourcery']


def test_mixed_pending_and_unfetched(plan_context):
    """Pending and unfetched bots are surfaced on their own lists in enabled order."""
    plan_id = 'rc-mixed'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='pending')
    _seed(plan_id, 'sourcery', resolution='fixed')
    # pr-agent seeded with no finding at all → unfetched

    result = rc.check_completeness(plan_id, ['coderabbit', 'sourcery', 'pr-agent'])

    assert result['status'] == 'success'
    assert result['complete'] is False
    assert result['pending_bots'] == ['coderabbit']
    assert result['unfetched_bots'] == ['pr-agent']


def test_empty_store_all_unfetched(plan_context):
    """A store with no findings reports every required bot as unfetched (fail-closed)."""
    plan_id = 'rc-empty-store'
    plan_context.plan_dir_for(plan_id)

    result = rc.check_completeness(plan_id, ['coderabbit', 'pr-agent'])

    assert result['status'] == 'success'
    assert result['complete'] is False
    assert result['pending_bots'] == []
    assert result['unfetched_bots'] == ['coderabbit', 'pr-agent']


def test_empty_required_bots_is_vacuously_complete(plan_context):
    """No required bots means nothing to await — complete is vacuously true.

    An EMPTY ``required_bots`` is a legitimate configured state (the operator
    answered "none"), not a misconfiguration: the quorum is vacuously satisfied.
    """
    plan_id = 'rc-no-bots'
    plan_context.plan_dir_for(plan_id)

    result = rc.check_completeness(plan_id, [])

    assert result['status'] == 'success'
    assert result['complete'] is True
    assert result['pending_bots'] == []
    assert result['unfetched_bots'] == []


def test_silent_optional_bot_does_not_block(plan_context):
    """An OPTIONAL bot that produced nothing is reported but does NOT block.

    This is the core required-vs-optional asymmetry: an optional bot's silence is
    not a failure, so it can never hold the step open. The bot still appears on
    ``unfetched_bots`` for visibility — reporting and gating are separate concerns.
    """
    plan_id = 'rc-optional-silent'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='fixed')

    result = rc.check_completeness(plan_id, ['coderabbit'], optional_bots=['sourcery'])

    assert result['status'] == 'success'
    assert result['complete'] is True
    assert result['unfetched_bots'] == ['sourcery']


def test_silent_required_bot_blocks(plan_context):
    """The counterpart: a REQUIRED bot that produced nothing DOES block.

    Paired with ``test_silent_optional_bot_does_not_block`` against an otherwise
    identical store, so the assertion isolates the required/optional dial as the
    only difference — a silent bot blocks iff it is required.
    """
    plan_id = 'rc-required-silent'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='fixed')

    result = rc.check_completeness(plan_id, ['coderabbit', 'sourcery'])

    assert result['status'] == 'success'
    assert result['complete'] is False
    assert result['unfetched_bots'] == ['sourcery']


def test_pending_optional_bot_does_not_block_after_triage(plan_context):
    """An OPTIONAL bot still pending after triage does not block either.

    ``triage_ran=True`` escalates a still-pending finding to a real incompleteness
    — but only for a REQUIRED bot. An optional bot's pending finding is reported
    and ignored by the quorum.
    """
    plan_id = 'rc-optional-pending'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'sourcery', resolution='pending')

    result = rc.check_completeness(
        plan_id, [], optional_bots=['sourcery'], triage_ran=True
    )

    assert result['status'] == 'success'
    assert result['complete'] is True
    assert result['pending_bots'] == ['sourcery']


def test_bot_listed_both_required_and_optional_is_not_duplicated(plan_context):
    """A bot named in BOTH lists is classified once, as required.

    The de-dup keeps the reported lists clean and — because required wins — keeps
    the gating behaviour unambiguous for a contradictory configuration.
    """
    plan_id = 'rc-both-lists'
    plan_context.plan_dir_for(plan_id)

    result = rc.check_completeness(
        plan_id, ['sourcery'], optional_bots=['sourcery']
    )

    assert result['status'] == 'success'
    assert result['unfetched_bots'] == ['sourcery']
    assert result['complete'] is False


def test_cli_optional_bots_flag_does_not_gate(plan_context):
    """The ``--optional-bots`` CLI flag reports without gating.

    An empty store with only optional bots emits ``complete: true`` while still
    listing them under ``unfetched_bots``.
    """
    plan_id = 'rc-cli-optional'
    plan_context.plan_dir_for(plan_id)

    result = run_script(
        SCRIPT_PATH,
        'check',
        '--plan-id',
        plan_id,
        '--required-bots',
        '',
        '--optional-bots',
        'sourcery',
    )

    assert result.success, result.stderr
    assert 'complete: true' in result.stdout
    assert 'unfetched_bots[1]' in result.stdout
    assert 'sourcery' in result.stdout


def test_bot_with_multiple_findings_one_pending(plan_context):
    """A bot with several findings is classified pending if ANY is unresolved.

    Pre-triage (``triage_ran=False``) the pending finding does NOT block, so the
    store is complete; ``pending_bots`` still names the bot for visibility. With
    ``triage_ran=True`` the same store is incomplete (a real still-pending
    finding after triage).
    """
    plan_id = 'rc-multi'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='fixed')
    _seed(plan_id, 'coderabbit', resolution='pending')

    pre_triage = rc.check_completeness(plan_id, ['coderabbit'])
    assert pre_triage['complete'] is True
    assert pre_triage['pending_bots'] == ['coderabbit']

    post_triage = rc.check_completeness(plan_id, ['coderabbit'], triage_ran=True)
    assert post_triage['complete'] is False
    assert post_triage['pending_bots'] == ['coderabbit']


def test_cli_emits_toon_and_zero_exit(plan_context):
    """The check verb prints the documented TOON block and exits 0."""
    plan_id = 'rc-cli'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='pending')

    result = run_script(
        SCRIPT_PATH, 'check', '--plan-id', plan_id, '--required-bots', 'coderabbit,sourcery'
    )

    assert result.success, result.stderr
    assert 'status: success' in result.stdout
    assert 'complete: false' in result.stdout
    assert 'pending_bots[1]' in result.stdout
    assert 'coderabbit' in result.stdout
    assert 'unfetched_bots[1]' in result.stdout
    assert 'sourcery' in result.stdout


def test_cli_complete_emits_true(plan_context):
    """The clean path emits complete: true with no bot lists."""
    plan_id = 'rc-cli-clean'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='fixed')

    result = run_script(SCRIPT_PATH, 'check', '--plan-id', plan_id, '--required-bots', 'coderabbit')

    assert result.success, result.stderr
    assert 'complete: true' in result.stdout
    assert 'pending_bots' not in result.stdout
    assert 'unfetched_bots' not in result.stdout


def test_cli_triage_ran_flips_pending_to_incomplete(plan_context):
    """The ``--triage-ran`` CLI flag makes a pending-only store report incomplete.

    Without the flag (FIND-only default) a pending-only store is ``complete:
    true`` — pending awaits triage. Passing ``--triage-ran`` treats the same
    still-pending finding as a real incompleteness (``complete: false`` with the
    bot on ``pending_bots``).
    """
    plan_id = 'rc-cli-triage-ran'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='pending')

    pre = run_script(SCRIPT_PATH, 'check', '--plan-id', plan_id, '--required-bots', 'coderabbit')
    assert pre.success, pre.stderr
    assert 'complete: true' in pre.stdout

    post = run_script(
        SCRIPT_PATH, 'check', '--plan-id', plan_id, '--required-bots', 'coderabbit', '--triage-ran'
    )
    assert post.success, post.stderr
    assert 'complete: false' in post.stdout
    assert 'pending_bots[1]' in post.stdout
    assert 'coderabbit' in post.stdout


def test_load_failure_oserror_returns_structured_error(plan_context, monkeypatch):
    """A store I/O error (OSError) is caught and rendered as a load_failure payload."""
    plan_id = 'rc-oserror'
    plan_context.plan_dir_for(plan_id)

    def _raise(*_args, **_kwargs):
        raise OSError('store unreadable')

    monkeypatch.setattr(rc, 'query_findings', _raise)

    result = rc.check_completeness(plan_id, ['coderabbit'])

    assert result['status'] == 'error'
    assert result['error'] == 'load_failure'
    assert 'store unreadable' in result['detail']


def test_load_failure_valueerror_returns_structured_error(plan_context, monkeypatch):
    """A corrupt store (ValueError / JSONDecodeError) is caught as load_failure."""
    plan_id = 'rc-valueerror'
    plan_context.plan_dir_for(plan_id)

    def _raise(*_args, **_kwargs):
        raise ValueError('bad json')

    monkeypatch.setattr(rc, 'query_findings', _raise)

    result = rc.check_completeness(plan_id, ['coderabbit'])

    assert result['status'] == 'error'
    assert result['error'] == 'load_failure'
    assert 'bad json' in result['detail']


def test_cmd_check_load_failure_nonzero_exit(plan_context, monkeypatch, capsys):
    """cmd_check emits the error TOON branch and returns a non-zero exit code."""
    plan_id = 'rc-cmd-load-fail'
    plan_context.plan_dir_for(plan_id)

    def _raise(*_args, **_kwargs):
        raise OSError('store gone')

    monkeypatch.setattr(rc, 'query_findings', _raise)

    rc_exit = rc.main(['check', '--plan-id', plan_id, '--required-bots', 'coderabbit'])

    captured = capsys.readouterr()
    assert rc_exit == 1
    assert 'status: error' in captured.out
    assert 'error: load_failure' in captured.out
    assert 'detail:' in captured.out


def test_settled_bot_with_no_finding_not_unfetched(plan_context):
    """D4: a bot with 0 findings that IS settled is accounted-for → complete.

    A settled bot (posted an all-noise comment so it stored nothing, OR its review
    window closed) with no stored finding must NOT be reported as ``unfetched``,
    so the FIND-only store is ``complete: true`` — no infinite loop-back is
    manufactured on unchanged code.
    """
    plan_id = 'rc-settled-no-finding'
    plan_context.plan_dir_for(plan_id)
    # sourcery is enabled but filed no finding; it is settled (declined / all-noise).

    result = rc.check_completeness(plan_id, ['sourcery'], settled_bots=['sourcery'])

    assert result['status'] == 'success'
    assert result['complete'] is True
    assert result['pending_bots'] == []
    assert result['unfetched_bots'] == []


def test_unsettled_bot_with_no_finding_still_unfetched(plan_context):
    """D4: a bot with 0 findings that is NOT settled still blocks as unfetched.

    Without a settled signal the guard's fail-closed behavior is unchanged — a
    genuinely-awaited bot (nothing posted, review window open) with no finding
    reports ``unfetched`` and ``complete: false``.
    """
    plan_id = 'rc-unsettled-no-finding'
    plan_context.plan_dir_for(plan_id)
    # coderabbit is settled but sourcery is neither settled nor fetched.
    _seed(plan_id, 'coderabbit', resolution='fixed')

    result = rc.check_completeness(
        plan_id, ['coderabbit', 'sourcery'], settled_bots=['coderabbit']
    )

    assert result['status'] == 'success'
    assert result['complete'] is False
    assert result['pending_bots'] == []
    assert result['unfetched_bots'] == ['sourcery']


def test_settled_does_not_override_pending_under_triage_ran(plan_context):
    """D4: settled_bots does NOT mask a genuinely-pending finding once triage ran.

    A bot with a still-``pending`` finding is a real incompleteness under
    ``triage_ran=True`` regardless of whether it is also listed as settled — the
    settled signal only rescues a bot with ZERO stored findings, never one whose
    stored finding is still pending after triage. D2's post-triage semantics must
    not regress.
    """
    plan_id = 'rc-settled-pending-triage'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='pending')

    result = rc.check_completeness(
        plan_id, ['coderabbit'], triage_ran=True, settled_bots=['coderabbit']
    )

    assert result['status'] == 'success'
    assert result['complete'] is False
    assert result['pending_bots'] == ['coderabbit']
    assert result['unfetched_bots'] == []


def test_cli_settled_bots_flag_marks_bot_complete(plan_context):
    """D4: the ``--settled-bots`` CLI flag stops a fetch-less bot reporting unfetched.

    Without ``--settled-bots`` the empty store reports both required bots as
    unfetched (``complete: false``). Passing ``--settled-bots coderabbit,sourcery``
    accounts for both, so the check emits ``complete: true`` with no bot lists.
    """
    plan_id = 'rc-cli-settled'
    plan_context.plan_dir_for(plan_id)

    without = run_script(
        SCRIPT_PATH, 'check', '--plan-id', plan_id, '--required-bots', 'coderabbit,sourcery'
    )
    assert without.success, without.stderr
    assert 'complete: false' in without.stdout
    assert 'unfetched_bots[2]' in without.stdout

    with_settled = run_script(
        SCRIPT_PATH,
        'check',
        '--plan-id',
        plan_id,
        '--required-bots',
        'coderabbit,sourcery',
        '--settled-bots',
        'coderabbit,sourcery',
    )
    assert with_settled.success, with_settled.stderr
    assert 'complete: true' in with_settled.stdout
    assert 'unfetched_bots' not in with_settled.stdout


def test_cli_whitespace_in_required_bots_tolerated(plan_context):
    """Whitespace around comma-separated bot tokens is stripped."""
    plan_id = 'rc-cli-ws'
    plan_context.plan_dir_for(plan_id)
    _seed(plan_id, 'coderabbit', resolution='fixed')

    result = run_script(
        SCRIPT_PATH, 'check', '--plan-id', plan_id, '--required-bots', ' coderabbit , '
    )

    assert result.success, result.stderr
    assert 'complete: true' in result.stdout
