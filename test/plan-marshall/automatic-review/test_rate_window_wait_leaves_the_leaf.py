#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The rate-window wait is held by the main context, never by the dispatched step.

A review bot's rate window runs to an hour. The ``automatic-review`` step used to
wait it out itself: one ``rate-window check`` read, then a standalone ``sleep``
call, repeated until the window elapsed, and a second ``sleep`` for the jittered
wake delay. A dispatched step cannot hold such a pause, so the instruction was one
the step could not carry out.

The wait now belongs to the main context. After claiming the window the step
returns ``escalate_ask`` with the reason ``rate_window_await`` and stops;
``phase-6-finalize`` item 7a answers that reason by re-issuing the bounded
``merge_lock rate-window wait`` call and then dispatching the step again. It asks
the operator nothing.

This suite pins the document side of that contract in the two documents that carry
it. Every assertion runs against the real document text, and each reader is
exercised against a synthetic document first, so a reader that silently returns
nothing cannot make a real assertion pass.
"""

from __future__ import annotations

import re

from conftest import get_skill_dir

_AR_SKILL = get_skill_dir('plan-marshall', 'automatic-review') / 'SKILL.md'
_FINALIZE_SKILL = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'SKILL.md'

_RECOVERY_SECTION = 'Rate-limit refusal recovery'
_ESCALATE_SECTION = '`escalate_ask` return'
_TIMEOUT_SECTION = 'Timeout Contract'
_AWAIT_REASON = 'rate_window_await'

#: Where item 7a begins and ends in ``phase-6-finalize/SKILL.md``. The item is a
#: numbered entry of an indented loop body rather than a heading of its own, so it
#: is located by its opening line and by the heading that follows the loop.
_ITEM_7A_START = '  7a. Escalate-ask continuation hook'
_ITEM_7A_END = '  ### Loop-back Target Contract'

#: Where the non-asking branch of item 7a begins and ends.
_AWAIT_BRANCH_START = '**`reason: rate_window_await` — hold the wait here'
_AWAIT_BRANCH_END = 'For `reason: re_review_timeout`, read the timeout policy'

_HEADING = re.compile(r'^(#{1,6})\s+(.*)$')

#: A ``sleep`` written as a command: inside inline code (`` `sleep 60` ``,
#: `` `sleep {delay_seconds}` ``). A fenced command line is found by
#: :func:`_standalone_sleeps` instead, which knows which lines are fenced.
_INLINE_SLEEP_COMMAND = re.compile(r'`sleep(\s+[^`]*)?`')
_FENCED_SLEEP_COMMAND = re.compile(r'^\s*sleep(\s+\S.*)?$')


def _section(text: str, title: str) -> str:
    """Return the body of the first heading starting with ``title``.

    The section runs from its heading to the next heading of the same or a higher
    level, so the sub-headings of a section stay inside it. Lines inside a fenced
    code block are never read as headings.
    """
    body: list[str] = []
    level = 0
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith('```'):
            in_fence = not in_fence
        heading = None if in_fence else _HEADING.match(line)
        if level == 0:
            if heading and heading.group(2).startswith(title):
                level = len(heading.group(1))
            continue
        if heading and len(heading.group(1)) <= level:
            break
        body.append(line)
    return '\n'.join(body)


def _standalone_sleeps(text: str) -> list[str]:
    """Every ``sleep`` the text prescribes as a command to run.

    Two shapes count: a line of a fenced code block that is a ``sleep`` invocation,
    and a ``sleep`` invocation written as inline code. Prose that merely uses the
    word — "rather than sleeping through the stated time" — prescribes nothing and
    is not reported.
    """
    found: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence:
            if _FENCED_SLEEP_COMMAND.match(line):
                found.append(line.strip())
            continue
        found.extend(match.group(0) for match in _INLINE_SLEEP_COMMAND.finditer(line))
    return found


def _between(text: str, start: str, end: str) -> str:
    """Return ``text`` from the single ``start`` marker up to the next ``end`` marker.

    Each marker is counted before it is used, because ``str.index`` takes the first
    occurrence silently: an absent marker returns the empty string, and a repeated
    ``start`` marker returns the empty string too, rather than a slice of whichever
    copy came first.
    """
    if text.count(start) != 1:
        return ''
    begin = text.index(start)
    stop = text.find(end, begin)
    if stop == -1:
        return ''
    return text[begin:stop]


def _fenced_blocks(text: str) -> list[str]:
    """The bodies of the fenced code blocks in ``text``, in document order."""
    blocks: list[str] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if line.lstrip().startswith('```'):
            if current is None:
                current = []
            else:
                blocks.append('\n'.join(current))
                current = None
            continue
        if current is not None:
            current.append(line)
    return blocks


def _frontmatter_description(text: str, key: str) -> str:
    """Return the ``description`` line that follows ``- key: {key}`` in the frontmatter."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == f'- key: {key}':
            for follower in lines[index + 1 :]:
                stripped = follower.strip()
                if stripped.startswith('description:'):
                    return stripped
                if stripped.startswith('- key:'):
                    break
    return ''


def _item_7a() -> str:
    return _between(_FINALIZE_SKILL.read_text(encoding='utf-8'), _ITEM_7A_START, _ITEM_7A_END)


def _await_branch() -> str:
    return _between(_item_7a(), _AWAIT_BRANCH_START, _AWAIT_BRANCH_END)


_SYNTHETIC_DOC = """\
## Outer

### Rate-limit refusal recovery (opt-in)

Poll the claim rather than sleeping through the stated time.

#### Branch 3 — poll

Pace with a single `sleep {interval}` call.

```bash
# a shell comment that is not a heading
sleep 60
```

Still inside the section.

### Next section

```bash
sleep 5
```
"""


# ---------------------------------------------------------------------------
# The readers, against a synthetic document
# ---------------------------------------------------------------------------


def test_section_reader_keeps_sub_headings_and_stops_at_the_next_peer():
    section = _section(_SYNTHETIC_DOC, _RECOVERY_SECTION)

    assert 'Branch 3' in section
    assert 'Still inside the section.' in section
    assert 'Next section' not in section
    assert 'sleep 5' not in section


def test_section_reader_returns_empty_for_an_absent_title():
    assert _section(_SYNTHETIC_DOC, 'No such section') == ''


def test_sleep_detector_finds_both_command_shapes_and_ignores_prose():
    """Matched negative control: the detector finds the sleeps the real section must lack."""
    found = _standalone_sleeps(_section(_SYNTHETIC_DOC, _RECOVERY_SECTION))

    assert found == ['`sleep {interval}`', 'sleep 60'], found


def test_sleep_detector_reports_nothing_for_prose_alone():
    assert _standalone_sleeps('Poll the claim rather than sleeping through the stated time.') == []


def test_between_returns_empty_for_an_absent_or_repeated_start_marker():
    assert _between('alpha beta gamma', 'alpha', 'gamma') == 'alpha beta '
    assert _between('alpha beta gamma', 'missing', 'gamma') == ''
    assert _between('alpha alpha gamma', 'alpha', 'gamma') == ''
    assert _between('alpha beta gamma', 'alpha', 'missing') == ''


def test_fenced_block_reader_returns_each_block_body():
    assert _fenced_blocks(_SYNTHETIC_DOC) == ['# a shell comment that is not a heading\nsleep 60', 'sleep 5']


# ---------------------------------------------------------------------------
# automatic-review: the step stops after the claim and prescribes no sleep
# ---------------------------------------------------------------------------


def test_recovery_section_prescribes_no_standalone_sleep():
    """The whole recovery section — every branch — holds no ``sleep`` command."""
    section = _section(_AR_SKILL.read_text(encoding='utf-8'), _RECOVERY_SECTION)

    assert section.strip(), f'section "{_RECOVERY_SECTION}" not found in {_AR_SKILL}'
    assert '#### Branch 2' in section, 'the section was cut short: Branch 2 is not inside it'
    assert '#### Branch 5' in section, 'the section was cut short: Branch 5 is not inside it'
    assert _standalone_sleeps(section) == []


def test_the_claiming_branch_hands_the_wait_back():
    """Branch 2 returns ``rate_window_await`` and reads its own claim before claiming."""
    recovery = _section(_AR_SKILL.read_text(encoding='utf-8'), _RECOVERY_SECTION)
    branch = _section(recovery, 'Branch 2')

    assert branch.strip(), 'Branch 2 not found in the recovery section'
    assert f'reason: {_AWAIT_REASON}' in branch
    assert 'rate-window check' in branch
    assert 'rate-window claim' in branch
    assert 'mark-step-done' in branch


def test_the_re_entry_branch_consults_the_selector_with_the_held_attempt():
    """Branch 3 issues no claim and no wait; it re-consults with the observed window."""
    recovery = _section(_AR_SKILL.read_text(encoding='utf-8'), _RECOVERY_SECTION)
    branch = _section(recovery, 'Branch 3')
    commands = '\n'.join(_fenced_blocks(branch))

    assert branch.strip(), 'Branch 3 not found in the recovery section'
    assert 'recovery-action' in commands
    assert '--window-expired true' in commands
    assert '--attempts-remaining' in commands
    assert '--attempt-held true' in commands
    assert 'rate-window claim' not in commands
    assert 'rate-window wait' not in commands


def test_the_await_envelope_carries_the_wait_fields_and_no_prompt():
    """The ``rate_window_await`` return shape names the wait and offers nothing to pick."""
    section = _section(_AR_SKILL.read_text(encoding='utf-8'), _ESCALATE_SECTION)
    shapes = [block for block in _fenced_blocks(section) if f'reason: {_AWAIT_REASON}' in block]

    assert len(shapes) == 1, f'expected one {_AWAIT_REASON} return shape, found {len(shapes)}'
    shape = shapes[0]
    for field in ('bot_kind:', 'pr_number:', 'expires_at:', 'seconds_remaining:', 'rate_window_arming['):
        assert field in shape, f'{field} missing from the {_AWAIT_REASON} return shape'
    assert 'prompt_options' not in shape
    assert 'action:' not in shape


def test_an_asking_return_shape_does_carry_a_prompt():
    """Matched control: the shape reader sees ``prompt_options`` where one is declared."""
    section = _section(_AR_SKILL.read_text(encoding='utf-8'), _ESCALATE_SECTION)
    asking = [block for block in _fenced_blocks(section) if 'reason: refusal_structural' in block]

    assert len(asking) == 1, f'expected one refusal_structural return shape, found {len(asking)}'
    assert 'prompt_options' in asking[0]
    assert 'action: ask' in asking[0]


def test_the_step_budget_no_longer_covers_the_rate_window_wait():
    section = _section(_AR_SKILL.read_text(encoding='utf-8'), _TIMEOUT_SECTION)

    assert section.strip(), f'section "{_TIMEOUT_SECTION}" not found in {_AR_SKILL}'
    assert 'the optional rate-window await' not in section
    assert _AWAIT_REASON in section


def test_the_configurable_descriptions_name_the_hand_back():
    text = _AR_SKILL.read_text(encoding='utf-8')
    await_description = _frontmatter_description(text, 'review_rate_window_await')
    timeout_description = _frontmatter_description(text, 'review_rate_window_timeout_seconds')

    assert _AWAIT_REASON in await_description, await_description
    assert 'item 7a' in await_description, await_description
    assert 'item 7a' in timeout_description, timeout_description


# ---------------------------------------------------------------------------
# phase-6-finalize item 7a: the reason is listed and routed to a wait
# ---------------------------------------------------------------------------


def test_item_7a_and_its_await_branch_are_found():
    """Vacuity guard: every assertion below reads a slice, and an empty slice proves nothing."""
    assert _item_7a().strip(), f'item 7a not found in {_FINALIZE_SKILL}'
    assert _await_branch().strip(), f'the {_AWAIT_REASON} branch of item 7a not found in {_FINALIZE_SKILL}'


def test_item_7a_lists_the_reason_as_non_asking():
    """The reason list names ``rate_window_await`` and says no prompt fires for it."""
    bullets = [line for line in _item_7a().splitlines() if line.lstrip().startswith(f'- **`reason: {_AWAIT_REASON}`**')]

    assert len(bullets) == 1, f'expected one reason-list entry for {_AWAIT_REASON}, found {len(bullets)}'
    assert 'no `AskUserQuestion` fires' in bullets[0], bullets[0]


def test_item_7a_states_the_recounted_reason_total():
    item = _item_7a()

    assert 'Six escalation reasons' in item
    assert 'Five escalation reasons' not in item


def test_the_await_branch_routes_to_a_bounded_wait_and_a_re_dispatch():
    branch = _await_branch()
    commands = '\n'.join(
        line for line in branch.splitlines() if 'execute-script.py' in line or line.strip().startswith('--')
    )

    assert 'merge_lock poll-delay' in commands
    assert 'merge_lock rate-window wait' in commands
    assert '--grace-seconds {delay_seconds}' in commands
    assert '--wait-seconds {remaining_budget}' in commands
    assert 'Leave the step record ABSENT' in branch
    assert 'plan-marshall:automatic-review' in branch


def test_the_await_branch_asks_the_operator_nothing():
    """No prompt and no pause of its own: the script holds each bounded wait."""
    branch = _await_branch()

    assert 'AskUserQuestion' not in branch
    assert _standalone_sleeps(branch) == []


def test_an_asking_branch_of_item_7a_does_name_the_prompt():
    """Matched control: the absence above is about the branch, not about the reader."""
    item = _item_7a()

    assert 'AskUserQuestion' in item.replace(_await_branch(), '')


def test_the_await_branch_shows_a_waiting_state():
    """The work log names the bot and the expiry, and the title uses an existing state."""
    branch = _await_branch()

    assert '{bot_kind}' in branch
    assert '{expires_at}' in branch
    assert 'title-token set' in branch
    assert '--state lock-waiting' in branch
    assert 'title-token clear' in branch


def test_the_await_branch_bounds_the_total_wait_and_releases_on_exhaustion():
    branch = _await_branch()

    assert 'review_rate_window_timeout_seconds' in branch
    assert 'merge_lock rate-window release' in branch
    assert 'rate_window_timeout' in branch


def test_the_await_branch_names_its_termination_cause():
    branch = _await_branch()

    assert 'Item 5c stamps this return' in branch
    assert '`blocked_session_restart`' in branch
