#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``automatic-review`` step routes a "nothing is unreviewed" reply as the producer does.

A bot can answer its re-review trigger with a ``no_unreviewed_commit`` reply. Two
statements in ``automatic-review/SKILL.md`` decide what the step does with it, and
each has to agree with code the step does not own:

- **Trigger B's exception.** ``github_pr fetch_findings`` credits a stale bot whose
  own reply is strictly newer than the merge-candidate commit on every call, with no
  configuration read. The step's rule that such a bot did not time out therefore
  carries no configuration condition either: a rule gated on the recovery opt-in
  disposes a bot as timed out for a HEAD the same pass's FIND call credits.
- **Branch 6's review state.** ``fetch_findings`` reports a bot's participation in
  three disjoint lists. The state the step forwards to ``recovery-action`` is read
  off all three, because the one state that posts — ``absent`` — is otherwise what a
  bot the producer could not decide falls into.

The readers and predicates are exercised against synthetic documents first, so a
reader that returns nothing cannot make an assertion on the real document pass.
"""

from __future__ import annotations

import importlib
import re

# ``github_ops`` is resolved first: importing ``github_re_review`` ahead of it closes
# an import cycle on a partially initialised module.
importlib.import_module('github_ops')

import github_re_review  # noqa: E402
import pytest  # noqa: E402

from conftest import get_skill_dir  # noqa: E402

_AR_SKILL = get_skill_dir('plan-marshall', 'automatic-review') / 'SKILL.md'

_TRIGGER_B_TITLE = 'Re-review after a loop-back fix commit (trigger B)'
_TIMEOUT_TITLE = 'On re-review timeout (trigger B)'
_BRANCH_6_TITLE = 'Branch 6'

_OPT_IN = 'review_rate_window_await'
_CONDITION = 'no_unreviewed_commit'

#: The exception's own first words, and the paragraph that follows the exception.
_EXCEPTION_START = '**One exception'
_EXCEPTION_END = 'The exception rests on a reply to THIS trigger'
#: What the exception tells the step to do. Everything between the sentence's
#: opening ``When`` and these words is the condition under which it applies.
_EXEMPTION_VERB = 'do NOT add the bot to'

_PART_2_START = '**Part 2'
_PART_2_END = 'Then consult the selector'
_PARTICIPATION_LISTS = (
    'participated_bots[]',
    'stale_participation_bots[]',
    'undecidable_participation_bots[]',
)
_STATE_BULLET = re.compile(r'^\s*- `([a-z_]+)` when\b')

_HEADING = re.compile(r'^(#{1,6})\s+(.*)$')


def _section(text: str, title: str) -> str:
    """Return the body of the first heading starting with ``title``.

    The section runs from its heading to the next heading of the same or a higher
    level. Lines inside a fenced code block are never read as headings.
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


def _between(text: str, start: str, end: str) -> str:
    """Return ``text`` from the first ``start`` up to the next ``end``, or ``''``."""
    begin = text.find(start)
    if begin == -1:
        return ''
    stop = text.find(end, begin)
    return text[begin:] if stop == -1 else text[begin:stop]


def _exemption_condition(block: str) -> str:
    """Return the condition under which ``block`` exempts a bot from the timed-out set.

    That is the text from the ``When`` opening the exempting sentence up to the
    exemption itself. A clause placed AFTER the exemption is not part of it.
    """
    end = block.find(_EXEMPTION_VERB)
    if end == -1:
        return ''
    start = block.rfind('When ', 0, end)
    return '' if start == -1 else block[start:end]


def _exemption_is_conditioned_on(block: str, knob: str) -> bool:
    """Whether the exemption in ``block`` applies only under a value of ``knob``."""
    return knob in _exemption_condition(block)


def _opt_in_off_arm(block: str) -> str:
    """Return the bullet of ``block`` that states what follows with the opt-in off."""
    for line in block.splitlines():
        if line.lstrip().startswith('- ') and f'`{_OPT_IN}` `false`' in line:
            return line
    return ''


def _state_bullets(part: str) -> dict[str, str]:
    """Return ``{state: bullet text}`` for every ``- `state` when`` bullet in ``part``.

    A bullet's text runs to the next state bullet, so its continuation lines and its
    nested bullets belong to it.

    Raises:
        AssertionError: when a state has two bullets. Keeping the later one would
            let a second, contradicting derivation of a state replace the first
            without any assertion on the mapping seeing it.
    """
    bullets: dict[str, list[str]] = {}
    current: str | None = None
    for line in part.splitlines():
        match = _STATE_BULLET.match(line)
        if match:
            current = match.group(1)
            assert current not in bullets, f'state `{current}` is derived by more than one bullet'
            bullets[current] = [line]
        elif current is not None:
            bullets[current].append(line)
    return {state: '\n'.join(lines) for state, lines in bullets.items()}


def _lists_read(part: str) -> set[str]:
    """The producer participation lists ``part`` names."""
    return {name for name in _PARTICIPATION_LISTS if name in part}


_SYNTHETIC_CONDITIONED = """\
### Re-review after a loop-back fix commit (trigger B)

   - **When `timed_out: true`**, add the bot to `{timed_out_bots}`.

     **One exception — the bot answered.** When the return carries a `no_unreviewed_commit` record, AND `review_rate_window_await` is `true`, do NOT add the bot to `{timed_out_bots}`.

     The exception rests on a reply to THIS trigger.
"""

_SYNTHETIC_UNCONDITIONED = """\
### Re-review after a loop-back fix commit (trigger B)

   - **When `timed_out: true`**, add the bot to `{timed_out_bots}`.

     **One exception — the bot answered.** When the return carries a `no_unreviewed_commit` record, do NOT add the bot to `{timed_out_bots}` — whatever `review_rate_window_await` is set to.

     - **With `review_rate_window_await` `true`**, go to the recovery.
     - **With `review_rate_window_await` `false`**, nothing is posted.

     The exception rests on a reply to THIS trigger.
"""

_SYNTHETIC_TWO_LIST_PART = """\
#### Branch 6 — synthetic

**Part 2 — after the count.**

  - `credited` when the bot is named in `participated_bots[]`.
  - `stale` when the bot is named only in `stale_participation_bots[]`.
  - `absent` when the bot is in neither list.

Then consult the selector with both.
"""

_SYNTHETIC_THREE_LIST_PART = """\
#### Branch 6 — synthetic

**Part 2 — after the count.**

  - `credited` when the bot is named in `participated_bots[]`.
  - `stale` when the bot is named only in `stale_participation_bots[]`.
  - `undecidable` when the producer could not decide it:
    - the bot is named in `undecidable_participation_bots[]`.
  - `absent` when the bot is named in none of the three lists.

Then consult the selector with both.
"""


def _exception(text: str) -> str:
    return _between(_section(text, _TRIGGER_B_TITLE), _EXCEPTION_START, _EXCEPTION_END)


def _part_2(text: str) -> str:
    return _between(_section(text, _BRANCH_6_TITLE), _PART_2_START, _PART_2_END)


def test_detector_reports_an_exemption_gated_on_the_opt_in():
    """Detector self-test: an opt-in named inside the condition is reported."""
    block = _exception(_SYNTHETIC_CONDITIONED)

    assert block, 'the synthetic exception was not read'
    assert _exemption_is_conditioned_on(block, _OPT_IN)


def test_detector_ignores_an_opt_in_named_after_the_exemption():
    """Matched control: the same knob, named after the exemption, is not a condition."""
    block = _exception(_SYNTHETIC_UNCONDITIONED)

    assert _OPT_IN in block
    assert _CONDITION in _exemption_condition(block)
    assert not _exemption_is_conditioned_on(block, _OPT_IN)


def test_exception_reader_stops_before_the_following_paragraph():
    block = _exception(_SYNTHETIC_UNCONDITIONED)

    assert block.startswith(_EXCEPTION_START)
    assert _EXCEPTION_END not in block
    assert _opt_in_off_arm(block).strip().startswith('- **With')


def test_exception_reader_returns_empty_when_the_exception_is_absent():
    """An absent exception reads as empty — the state the real assertions guard against."""
    assert _exception('### Re-review after a loop-back fix commit (trigger B)\n\nNo exception here.\n') == ''
    assert _exemption_condition('no exemption in this text') == ''


def test_trigger_b_exception_is_not_conditioned_on_the_recovery_opt_in():
    """The producer credits a covering reply unconditionally, so the step exempts it likewise."""
    block = _exception(_AR_SKILL.read_text(encoding='utf-8'))
    condition = _exemption_condition(block)

    assert block, f'the trigger-B exception was not found in {_AR_SKILL}'
    assert condition, 'the exception names no condition for its exemption'
    assert _CONDITION in condition, condition
    assert not _exemption_is_conditioned_on(block, _OPT_IN), condition


def test_trigger_b_exception_never_counts_the_replying_bot_as_timed_out():
    block = _exception(_AR_SKILL.read_text(encoding='utf-8'))

    assert block, f'the trigger-B exception was not found in {_AR_SKILL}'
    assert _EXEMPTION_VERB in block, 'the exception does not state the exemption'
    assert 'counts as timed out' not in block


def test_trigger_b_exception_with_the_opt_in_off_posts_nothing_and_leaves_the_bot_to_find():
    """With the recovery skipped, the producer's credit decides and an uncredited bot stays owed."""
    arm = _opt_in_off_arm(_exception(_AR_SKILL.read_text(encoding='utf-8')))

    assert arm, 'the exception states no arm for the opt-in being off'
    assert 'nothing is posted' in arm
    assert 'Producer: FIND' in arm
    assert 'participated_bots[]' in arm
    assert 'stale_participation_bots[]' in arm
    assert 'participation guard' in arm
    assert 'never passed as reviewed' in arm


def test_timeout_sub_block_excludes_the_replying_bot_from_its_timed_out_entry_path():
    """The sub-block's own statement of its entry paths says the same as the exception."""
    sub_block = _section(_AR_SKILL.read_text(encoding='utf-8'), _TIMEOUT_TITLE)
    entry_lines = [line for line in sub_block.splitlines() if line.startswith('- `timed_out: true` AND')]

    assert len(entry_lines) == 1, entry_lines
    assert _CONDITION in entry_lines[0]
    assert f'whether or not `{_OPT_IN}` is set' in entry_lines[0]


def test_state_reader_reports_a_part_that_reads_two_lists_only():
    """Detector self-test: a two-list derivation is missing the third list and a state."""
    part = _part_2(_SYNTHETIC_TWO_LIST_PART)

    assert part, 'the synthetic Part 2 was not read'
    assert _lists_read(part) == set(_PARTICIPATION_LISTS[:2])
    assert set(_state_bullets(part)) == {'credited', 'stale', 'absent'}


def test_state_reader_reports_a_part_that_reads_all_three_lists():
    """Matched control: the same reader sees the third list and its state when present."""
    part = _part_2(_SYNTHETIC_THREE_LIST_PART)
    bullets = _state_bullets(part)

    assert _lists_read(part) == set(_PARTICIPATION_LISTS)
    assert 'undecidable_participation_bots[]' in bullets['undecidable']
    assert 'undecidable_participation_bots[]' not in bullets['absent']


def test_state_reader_refuses_a_state_derived_by_two_bullets():
    """Detector self-test: a duplicated state bullet fails instead of the later one winning."""
    duplicated = _SYNTHETIC_THREE_LIST_PART.replace(
        '  - `absent` when the bot is named in none of the three lists.',
        '  - `absent` when the bot is named in none of the three lists.\n  - `absent` when the bot is in neither list.',
    )
    assert duplicated != _SYNTHETIC_THREE_LIST_PART, 'the synthetic part carries no absent bullet to duplicate'

    with pytest.raises(AssertionError, match='`absent` is derived by more than one bullet'):
        _state_bullets(_part_2(duplicated))


def test_branch_6_derives_the_review_state_from_all_three_participation_lists():
    part = _part_2(_AR_SKILL.read_text(encoding='utf-8'))

    assert part, f'Branch 6 Part 2 was not found in {_AR_SKILL}'
    assert _lists_read(part) == set(_PARTICIPATION_LISTS)


def test_branch_6_states_one_derivation_per_selector_state():
    """Every state the selector accepts has a derivation, and no other state is derived."""
    states = set(github_re_review.REVIEW_ON_RECORD_STATES)
    bullets = _state_bullets(_part_2(_AR_SKILL.read_text(encoding='utf-8')))

    assert states, 'the selector publishes no review-on-record state'
    assert set(bullets) == states


def test_branch_6_reads_an_undecided_bot_as_undecidable_and_never_as_absent():
    """The posting state is derived only from a producer that read everything."""
    bullets = _state_bullets(_part_2(_AR_SKILL.read_text(encoding='utf-8')))
    undecidable = bullets[github_re_review.REVIEW_ON_RECORD_UNDECIDABLE]
    absent = bullets[github_re_review.REVIEW_ON_RECORD_ABSENT]

    assert 'undecidable_participation_bots[]' in undecidable
    assert 'merge_candidate_sha_resolved: false' in undecidable
    assert 'fetch_complete: false' in undecidable
    assert 'none of the three lists' in absent
    assert 'fetch_complete: true' in absent
    assert 'in neither list' not in absent


def test_branch_6_posts_nothing_on_an_undecidable_review_state():
    """The step's handling of the selector's answer for that state names no posting."""
    branch = _section(_AR_SKILL.read_text(encoding='utf-8'), _BRANCH_6_TITLE)
    handling = _between(branch, '- **`action: unmeasured`**', '\n- **`action:')

    assert handling, 'Branch 6 states no handling for an unmeasured result'
    assert 'review_state_undecidable' in handling
    assert 'Post nothing' in handling
    assert 're-review' not in handling
    assert 'holds the step open' in handling
