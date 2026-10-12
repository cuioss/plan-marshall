#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The rate-window wait of ``phase-6-finalize`` item 7a is one kind of bounded call.

Item 7a holds the wait a ``rate_window_await`` return hands back. It waits until
the claimed window has expired plus the wake margin ``rate-window wait`` applies by
default, and then dispatches the review step again. The window is bounded by
``review_rate_window_timeout_seconds``; the margin is accounted outside that budget.

This suite pins the document side of that contract:

* the branch issues ONE kind of wait call, passing no ``--grace-seconds`` of its
  own so the verb's default margin applies, and every wait call names the bound it
  is spent under;
* the wake lands after the expiry by that margin, the margin is accounted outside
  the budget, and a window that fits the budget is never reported as a timeout;
* before the first wait call the claim's ``seconds_remaining`` is compared with the
  budget, and a window longer than the budget is escalated without waiting;
* a wait call that fails is not a timeout: it stops the run with nothing recorded
  and the claim left in place, and raises no ``rate_window_timeout``;
* ``rate_window_timeout`` has two entry paths: over budget before waiting, and the
  spent budget.

Each reader and detector is exercised against synthetic text first, so one that
silently reports nothing cannot make an assertion on the real document pass.
"""

from __future__ import annotations

import re

from conftest import get_skill_dir

_FINALIZE_SKILL = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'SKILL.md'

_ITEM_7A_START = '  7a. Escalate-ask continuation hook'
_ITEM_7A_END = '  ### Loop-back Target Contract'
_AWAIT_BRANCH_START = '**`reason: rate_window_await` — hold the wait here'
_AWAIT_BRANCH_END = 'For `reason: re_review_timeout`, read the timeout policy'

_COMPARISON = '**Before the first wait call, compare the window with the budget.**'
_SHOW_WAITING_ITEM = '1. Show the waiting state before the first wait call.'
_WINDOW_ITEM = '2. **Wait for the window.**'
_EXPIRED_ITEM = '3. **Window expired.**'
_TIMEOUT_ITEM = '4. **Window longer than the budget.**'
_FAILED_ITEM = '5. **Wait call failed.**'

_BUDGET_BOUND = '{remaining_budget}'
#: What a wait call that passes no ``--grace-seconds`` gets: the verb's default margin.
_DEFAULT_MARGIN = 'default'

#: The two claim verbs as the script's own subcommands. Matching the bare words
#: would also take a logging call whose message mentions the wait for a wait call.
_WAIT_VERB = ':merge_lock rate-window wait '
_RELEASE_VERB = ':merge_lock rate-window release '

_GRACE_ARG = re.compile(r'--grace-seconds\s+(\S+)')
_BOUND_ARG = re.compile(r'--wait-seconds\s+(\S+)')

#: Wording that states a pause of the caller's own after the window's expiry — a
#: drawn or passed delay, as opposed to the verb's own default margin.
_DELAY_WORDING = re.compile(r'wake[- ]delay|jitter|poll-delay|delay_seconds|--grace-seconds', re.IGNORECASE)


def _between(text: str, start: str, end: str) -> str:
    """Return ``text`` from the single ``start`` marker up to the next ``end`` marker.

    An absent marker returns the empty string, and so does a repeated ``start``.
    """
    if text.count(start) != 1:
        return ''
    begin = text.index(start)
    stop = text.find(end, begin)
    if stop == -1:
        return ''
    return text[begin:stop]


def _commands(text: str) -> list[str]:
    """Every ``execute-script.py`` invocation in ``text``, one string per call.

    A call starts on a line naming ``execute-script.py`` and runs on while the line
    ends in a backslash. Only the part before ``--message`` is kept, so a verb that
    a log message merely mentions is not read as part of a call.
    """
    calls: list[str] = []
    current: list[str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if current is None:
            if 'execute-script.py' not in stripped:
                continue
            current = []
        current.append(stripped.removesuffix('\\').strip())
        if stripped.endswith('\\'):
            continue
        calls.append(' '.join(current).split(' --message ', 1)[0] + ' ')
        current = None
    return calls


def _wait_calls(text: str) -> list[tuple[str, str]]:
    """The ``(grace, bound)`` argument pair of every ``rate-window wait`` call in ``text``.

    A call that omits ``--grace-seconds`` gets the verb's default margin, which is
    reported as ``default``. A call that omits ``--wait-seconds`` reports an empty
    bound.
    """
    calls: list[tuple[str, str]] = []
    for command in _commands(text):
        if _WAIT_VERB not in command:
            continue
        grace = _GRACE_ARG.search(command)
        bound = _BOUND_ARG.search(command)
        calls.append((grace.group(1) if grace else _DEFAULT_MARGIN, bound.group(1) if bound else ''))
    return calls


def _calls_outside_the_contract(calls: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """The wait calls that pass a margin of their own or name no bound."""
    return [(grace, bound) for grace, bound in calls if grace != _DEFAULT_MARGIN or not bound]


def _item_7a() -> str:
    return _between(_FINALIZE_SKILL.read_text(encoding='utf-8'), _ITEM_7A_START, _ITEM_7A_END)


def _await_branch() -> str:
    return _between(_item_7a(), _AWAIT_BRANCH_START, _AWAIT_BRANCH_END)


def _failed_item() -> str:
    """The wait-call-failed item, which runs to the end of the branch."""
    branch = _await_branch()
    return branch[branch.index(_FAILED_ITEM) :] if branch.count(_FAILED_ITEM) == 1 else ''


def _table_rows(text: str, lead: str) -> list[str]:
    """The markdown table rows of ``text`` whose first cell starts with ``lead``."""
    return [line.strip() for line in text.splitlines() if line.strip().startswith(f'| {lead}')]


#: One bounded wait on the default margin, then a release on the spent budget.
_SYNTHETIC_SINGLE_WAIT = """\
      2. Wait for the window:

            python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock rate-window wait \\
              --plan-id {plan_id} --bot-kind {bot_kind} --pr-number {pr_number} \\
              --wait-seconds {remaining_budget}

      4. Budget spent:

            python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock rate-window release \\
              --plan-id {plan_id} --bot-kind {bot_kind}
"""

#: A second wait that passes a delay of its own, and a third that names no bound.
_SYNTHETIC_GRACED_AND_UNBOUNDED = """\
            python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock rate-window wait \\
              --plan-id {plan_id} --bot-kind {bot_kind} --pr-number {pr_number} \\
              --grace-seconds {delay_seconds} --wait-seconds {remaining_delay}

            python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock rate-window wait \\
              --plan-id {plan_id} --bot-kind {bot_kind} --pr-number {pr_number}
"""


# ---------------------------------------------------------------------------
# The readers and the detectors, against synthetic text
# ---------------------------------------------------------------------------


def test_the_call_reader_returns_each_wait_calls_grace_and_bound():
    assert _wait_calls(_SYNTHETIC_SINGLE_WAIT) == [(_DEFAULT_MARGIN, '{remaining_budget}')]
    assert _wait_calls(_SYNTHETIC_GRACED_AND_UNBOUNDED) == [
        ('{delay_seconds}', '{remaining_delay}'),
        (_DEFAULT_MARGIN, ''),
    ]


def test_the_call_reader_ignores_a_logging_call_that_mentions_the_wait():
    """A message naming the wait is not a wait call, and carries no bound to judge."""
    log_call = (
        'python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \\\n'
        '  decision --plan-id {plan_id} --level INFO \\\n'
        '  --message "see plan-marshall:manage-locks:merge_lock rate-window wait --grace-seconds 5"'
    )

    assert _wait_calls(log_call) == []
    assert len(_wait_calls(log_call + '\n' + _SYNTHETIC_SINGLE_WAIT)) == 1


def test_the_detector_reports_a_graced_call_and_an_unbounded_call():
    """Positive control: both shapes the contract excludes are caught."""
    outside = _calls_outside_the_contract(_wait_calls(_SYNTHETIC_GRACED_AND_UNBOUNDED))

    assert outside == [('{delay_seconds}', '{remaining_delay}'), (_DEFAULT_MARGIN, '')], outside


def test_the_detector_reports_nothing_for_one_bounded_call_on_the_default_margin():
    assert _calls_outside_the_contract(_wait_calls(_SYNTHETIC_SINGLE_WAIT)) == []


def test_the_delay_wording_detector_finds_each_statement_of_a_pause():
    for statement in ('a wake delay follows', 'the wake-delay wait', 'the jittered wake', '`merge_lock poll-delay`'):
        assert _DELAY_WORDING.search(statement), statement
    assert _DELAY_WORDING.search(_SYNTHETIC_GRACED_AND_UNBOUNDED)
    assert not _DELAY_WORDING.search(_SYNTHETIC_SINGLE_WAIT)


def test_the_row_reader_takes_only_rows_that_lead_with_the_cell():
    rows = '| `a`, `b` | one |\n| `a` | two |\nprose naming | `a` |\n'

    assert _table_rows(rows, '`a`') == ['| `a`, `b` | one |', '| `a` | two |']
    assert _table_rows(rows, '`c`') == []


# ---------------------------------------------------------------------------
# phase-6-finalize item 7a: the real document
# ---------------------------------------------------------------------------


def test_the_await_branch_and_its_wait_call_are_found():
    """Vacuity guard: an empty slice, or one with no wait call, proves nothing below."""
    branch = _await_branch()

    assert branch.strip(), f'the rate_window_await branch of item 7a not found in {_FINALIZE_SKILL}'
    assert _wait_calls(branch), 'no rate-window wait call parsed out of the branch'


def test_the_branch_issues_one_kind_of_wait_call_bounded_by_the_budget():
    calls = _wait_calls(_await_branch())

    assert calls == [(_DEFAULT_MARGIN, _BUDGET_BOUND)], calls
    assert _calls_outside_the_contract(calls) == []


def test_item_7a_passes_no_delay_of_its_own():
    """The margin is the verb's default; the hook draws or passes no pause besides it."""
    item = _item_7a()

    assert item.strip(), f'item 7a not found in {_FINALIZE_SKILL}'
    assert _DELAY_WORDING.findall(item) == []


def test_the_branch_wakes_after_the_expiry_by_the_default_margin():
    branch = _await_branch()

    assert 'plus the wake margin `rate-window wait` applies by default has passed' in branch
    assert "The margin keeps the re-dispatch from racing the claim's own expiry" in branch
    assert 'publishes it as `grace_seconds`' in branch
    # The retired zero-margin statements are gone.
    assert 'Nothing is waited after the expiry' not in branch
    assert 'several plans waiting on the same bot may re-trigger it at the same moment' not in branch


def test_the_branch_accounts_the_margin_outside_the_budget():
    """A window that fits the budget is never a timeout, the margin notwithstanding."""
    branch = _await_branch()
    window_wait = _between(branch, _WINDOW_ITEM, _EXPIRED_ITEM)
    spent_rows = _table_rows(window_wait, '`timed_out: true`, `{remaining_budget}` zero or below')

    assert "The window is bounded by the envelope's `timeout_seconds`" in branch
    assert 'the margin is accounted OUTSIDE that budget' in branch
    assert 'A window that expires within the budget is therefore never reported as a timeout' in branch
    assert len(spent_rows) == 2, spent_rows
    [expired_row] = [row for row in spent_rows if '`expired: true`' in row]
    [open_row] = [row for row in spent_rows if '`expired: false`' in row]
    assert 'this is not a timeout' in expired_row, expired_row
    assert '`--wait-seconds {grace_seconds}`' in expired_row, expired_row
    assert 'item 4' not in expired_row, expired_row
    assert 'Go to item 4' in open_row, open_row


def test_a_window_longer_than_the_budget_is_escalated_before_any_wait():
    branch = _await_branch()

    assert branch.count(_COMPARISON) == 1, 'the pre-wait comparison is not stated once'
    comparison = _between(branch, _COMPARISON, _SHOW_WAITING_ITEM)
    assert comparison.strip(), 'the pre-wait comparison does not precede item 1'
    assert "When the envelope's `seconds_remaining` exceeds its `timeout_seconds`" in comparison
    assert 'Do not wait: go straight to item 4, on its over-budget entry path' in comparison
    # The comparison comes before the first wait call is issued.
    assert branch.index(_COMPARISON) < branch.index(_WAIT_VERB.strip())
    assert _wait_calls(comparison) == []


def test_the_wait_call_is_issued_with_the_hosts_maximum_per_call_timeout():
    window_wait = _between(_await_branch(), _WINDOW_ITEM, _EXPIRED_ITEM)

    assert window_wait.strip(), 'the window-wait item of the branch not found'
    assert _wait_calls(window_wait), 'the window-wait item issues no wait call'
    assert "Issue the Bash call with the host's maximum per-call timeout" in window_wait
    assert 'every re-issue lowers the budget by at least 1' in window_wait


def test_a_failed_wait_call_routes_to_its_own_item_and_not_to_the_timeout():
    window_wait = _between(_await_branch(), _WINDOW_ITEM, _EXPIRED_ITEM)
    error_rows = [line for line in window_wait.splitlines() if line.strip().startswith('| `status: error`')]

    assert len(error_rows) == 1, error_rows
    assert 'Go to item 5' in error_rows[0]
    assert 'item 4' not in error_rows[0]


def test_a_failed_wait_call_stops_with_nothing_recorded_and_the_claim_in_place():
    failed = _failed_item()

    assert failed.strip(), 'the wait-call-failed item of the branch not found'
    assert 'A failed call is not a timeout' in failed
    assert 'STOP' in failed
    assert 'Record nothing for `plan-marshall:automatic-review` and do NOT release the claim' in failed
    assert 'The claim is not leaked' in failed
    assert not any(_RELEASE_VERB in command for command in _commands(failed))
    assert not any(':manage-status mark-step-done ' in command for command in _commands(failed))


def test_the_release_reader_sees_the_release_the_timeout_item_issues():
    """Matched control: the absence above is about the item, not about the reader."""
    timeout = _between(_await_branch(), _TIMEOUT_ITEM, _FAILED_ITEM)

    assert timeout.strip(), 'the window-longer-than-the-budget item of the branch not found'
    assert any(_RELEASE_VERB in command for command in _commands(timeout))
    assert any(_RELEASE_VERB in command for command in _commands(_SYNTHETIC_SINGLE_WAIT))


def test_the_timeout_reason_has_two_entry_paths():
    """Over budget before waiting, and the spent budget — each with its own log line."""
    timeout = _between(_await_branch(), _TIMEOUT_ITEM, _FAILED_ITEM)

    assert 'The only place `rate_window_timeout` arises, reached on two entry paths' in timeout
    assert 'the **over-budget** path from the pre-wait comparison above, before any wait call' in timeout
    assert 'the **budget-spent** path from the budget-spent row of item 2' in timeout
    assert 'is longer than review_rate_window_timeout_seconds={timeout_seconds} — not waited' in timeout
    assert 'spent with the window still open — released the claim' in timeout
    assert '`timed_out: true`, the same `bot_kind`' in timeout
    # The retired single-path wording is gone.
    assert 'Reached only from the budget-spent row of item 2' not in timeout


def test_the_reason_list_names_both_entry_paths_of_the_timeout():
    item = _item_7a()
    [reason_line] = [
        line for line in item.splitlines() if line.strip().startswith('- **`reason: rate_window_timeout`**')
    ]

    assert "the claim's `seconds_remaining` already exceeds that budget before any wait" in reason_line
    assert 'the wait spent the budget while the window was still open' in reason_line
    assert 'on those two paths (item 4' in reason_line
