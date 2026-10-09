#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The wake delay of the rate-window wait is not charged to the window budget.

``phase-6-finalize`` item 7a holds the wait a ``rate_window_await`` return hands
back. It waits for the claimed window to expire, then waits a jittered wake delay,
then dispatches the review step again. ``review_rate_window_timeout_seconds``
bounds the first of those waits only.

A wait that charges the delay to the budget cannot be satisfied with default
settings: a claim made without a stated reset time runs for as long as the default
budget, so the budget is always spent before a wake instant that lies a delay
later, and the hook reports a window as still open after it has expired.

This suite pins the document side: no ``rate-window wait`` call of the branch
carries both a grace period and the budget as its bound. The detector is exercised
against a synthetic branch in the charged shape first, so a detector that silently
reports nothing cannot make the real assertion pass.
"""

from __future__ import annotations

import re

from conftest import get_skill_dir

_FINALIZE_SKILL = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'SKILL.md'

_ITEM_7A_START = '  7a. Escalate-ask continuation hook'
_ITEM_7A_END = '  ### Loop-back Target Contract'
_AWAIT_BRANCH_START = '**`reason: rate_window_await` — hold the wait here'
_AWAIT_BRANCH_END = 'For `reason: re_review_timeout`, read the timeout policy'

_WINDOW_ITEM = '**Wait for the window.**'
_DELAY_ITEM = '**Wait the wake delay.**'
_WAKE_ITEM = '**Wake reached.**'
_EXHAUSTED_ITEM = '**Budget exhausted.**'

_BUDGET_BOUND = '{remaining_budget}'
_NO_GRACE = '0'

#: The wait verb as the script's own subcommand. Matching the bare words would also
#: take a logging call whose message mentions the wait for a wait call.
_WAIT_VERB = ':merge_lock rate-window wait '

_GRACE_ARG = re.compile(r'--grace-seconds\s+(\S+)')
_BOUND_ARG = re.compile(r'--wait-seconds\s+(\S+)')


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


def _wait_calls(text: str) -> list[tuple[str, str]]:
    """The ``(grace, bound)`` argument pair of every ``rate-window wait`` call in ``text``.

    A call starts on a line naming ``execute-script.py`` and runs on while the line
    ends in a backslash. A call that omits ``--grace-seconds`` waits no grace
    period, which is reported as ``0``.
    """
    calls: list[tuple[str, str]] = []
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
        command = ' '.join(current)
        current = None
        if _WAIT_VERB not in f'{command} ':
            continue
        grace = _GRACE_ARG.search(command)
        bound = _BOUND_ARG.search(command)
        calls.append((grace.group(1) if grace else _NO_GRACE, bound.group(1) if bound else ''))
    return calls


def _grace_charged_to_budget(calls: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """The calls that wait a grace period inside the window budget."""
    return [(grace, bound) for grace, bound in calls if grace != _NO_GRACE and bound == _BUDGET_BOUND]


def _await_branch() -> str:
    item = _between(_FINALIZE_SKILL.read_text(encoding='utf-8'), _ITEM_7A_START, _ITEM_7A_END)
    return _between(item, _AWAIT_BRANCH_START, _AWAIT_BRANCH_END)


#: One wait whose wake instant is the expiry plus the delay, bounded by the budget.
_SYNTHETIC_CHARGED_BRANCH = """\
      3. Start with `{remaining_budget}` = the envelope's `timeout_seconds`:

            python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock rate-window wait \\
              --plan-id {plan_id} --bot-kind {bot_kind} --pr-number {pr_number} \\
              --grace-seconds {delay_seconds} --wait-seconds {remaining_budget}
"""

#: The window waited inside the budget, the delay waited outside it.
_SYNTHETIC_SPLIT_BRANCH = """\
      3. Wait for the window:

            python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock rate-window wait \\
              --plan-id {plan_id} --bot-kind {bot_kind} --pr-number {pr_number} \\
              --grace-seconds 0 --wait-seconds {remaining_budget}

      4. Wait the delay:

            python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock rate-window wait \\
              --plan-id {plan_id} --bot-kind {bot_kind} --pr-number {pr_number} \\
              --grace-seconds {delay_seconds} --wait-seconds {remaining_delay}

            python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock rate-window release \\
              --plan-id {plan_id} --bot-kind {bot_kind}
"""


# ---------------------------------------------------------------------------
# The reader and the detector, against synthetic text
# ---------------------------------------------------------------------------


def test_the_call_reader_returns_each_wait_calls_grace_and_bound():
    assert _wait_calls(_SYNTHETIC_SPLIT_BRANCH) == [
        ('0', '{remaining_budget}'),
        ('{delay_seconds}', '{remaining_delay}'),
    ]


def test_the_call_reader_reads_an_omitted_grace_as_none_waited():
    call = 'python3 .plan/execute-script.py x:y:merge_lock rate-window wait --wait-seconds {remaining_budget}'

    assert _wait_calls(call) == [('0', '{remaining_budget}')]


def test_the_call_reader_ignores_a_logging_call_that_mentions_the_wait():
    """A message naming the wait is not a wait call, and carries no bound to judge."""
    log_call = (
        'python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \\\n'
        '  decision --plan-id {plan_id} --level INFO \\\n'
        '  --message "rate-window wait for {bot_kind} on pr {pr_number}: released the claim"'
    )

    assert _wait_calls(log_call) == []
    assert len(_wait_calls(log_call + '\n' + _SYNTHETIC_SPLIT_BRANCH)) == 2


def test_every_wait_call_of_the_branch_is_bounded():
    """No wait call omits ``--wait-seconds``: each one names the bound it is spent under."""
    calls = _wait_calls(_await_branch())

    assert calls, 'no rate-window wait call parsed out of the branch'
    assert all(bound for _grace, bound in calls), calls


def test_the_detector_reports_a_delay_waited_inside_the_budget():
    """Positive control: the shape whose budget its own default cannot satisfy is caught."""
    charged = _grace_charged_to_budget(_wait_calls(_SYNTHETIC_CHARGED_BRANCH))

    assert charged == [('{delay_seconds}', '{remaining_budget}')], charged


def test_the_detector_reports_nothing_for_a_delay_waited_outside_the_budget():
    assert _grace_charged_to_budget(_wait_calls(_SYNTHETIC_SPLIT_BRANCH)) == []


# ---------------------------------------------------------------------------
# phase-6-finalize item 7a: the real document
# ---------------------------------------------------------------------------


def test_the_await_branch_and_its_wait_calls_are_found():
    """Vacuity guard: an empty slice, or one with no wait call, proves nothing below."""
    branch = _await_branch()

    assert branch.strip(), f'the rate_window_await branch of item 7a not found in {_FINALIZE_SKILL}'
    assert _wait_calls(branch), 'no rate-window wait call parsed out of the branch'


def test_no_wait_call_charges_the_wake_delay_to_the_window_budget():
    assert _grace_charged_to_budget(_wait_calls(_await_branch())) == []


def test_the_window_is_waited_inside_the_budget_and_the_delay_outside_it():
    calls = _wait_calls(_await_branch())

    assert ('0', '{remaining_budget}') in calls, calls
    assert ('{delay_seconds}', '{remaining_delay}') in calls, calls
    assert len(calls) == 2, calls


def test_the_delay_wait_follows_the_window_wait_and_never_reaches_the_timeout():
    """Only the window wait can end in the budget-exhausted item."""
    branch = _await_branch()
    window_wait = _between(branch, _WINDOW_ITEM, _DELAY_ITEM)
    delay_wait = _between(branch, _DELAY_ITEM, _WAKE_ITEM)

    assert window_wait.strip(), 'the window-wait item of the branch not found'
    assert delay_wait.strip(), 'the wake-delay item of the branch not found'
    assert 'Go to item 6' in window_wait
    assert 'item 6' not in delay_wait.replace('no return of this item leads to item 6', '')
    assert 'no return of this item leads to item 6' in delay_wait
    assert '      6. ' + _EXHAUSTED_ITEM + ' Reached from item 3 only' in branch


def test_the_branch_states_what_the_budget_bounds_and_the_total():
    branch = _await_branch()

    assert 'is not charged to `review_rate_window_timeout_seconds`' in branch
    assert 'A window that expires within the budget always reaches the re-dispatch in item 5' in branch
    assert 'arises only when the window itself is still open when the budget is spent' in branch
    assert 'by `timeout_seconds` plus the `poll-delay` maximum' in branch
