#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Trigger B of ``automatic-review`` reads its stale set from participation state.

Trigger B re-requests a bot review after a fix commit moved HEAD. A stale set
built from stored findings alone misses a bot whose only comment was filtered as
noise: no finding is stored for it, so it is never asked again although the
step-done guard reports it ``participated_stale``. The section therefore reads the
bots' participation state at the current HEAD — the producer's
``stale_participation_bots[]`` — and joins it with the stored-finding bots.

This suite pins the document side of that contract against the real text of
``automatic-review/SKILL.md``:

- the section forwards the producer's ``stale_participation_bots[]`` to
  ``review_completeness trigger-bot`` and triggers the bots that verb lists;
- the stored-finding commit is read BEFORE the producer call, which re-stamps it;
- every flag the documented ``trigger-bot`` call uses is one the live parser
  declares, so a flag the verb no longer has cannot stay in the document;
- a required bot whose participation is stale is triggered even with
  ``re_review_on_loopback`` off, and the knob's description and the guard's remedy
  text both say so.

The section reader and the predicate are exercised against synthetic documents
first, so a reader that silently returns nothing cannot make a real assertion pass.
"""

from __future__ import annotations

import re

import pytest

from conftest import get_skill_dir, load_script_module

rc = load_script_module('plan-marshall', 'automatic-review', 'review_completeness.py', register=False)

_AR_SKILL = get_skill_dir('plan-marshall', 'automatic-review') / 'SKILL.md'
_SECTION_TITLE = 'Re-review after a loop-back fix commit (trigger B)'
_GUARD_TITLE = 'Step-done participation guard'
_KNOB = 're_review_on_loopback'
_PARTICIPATION_FIELD = 'stale_participation_bots'
_PARTICIPATION_FLAG = '--stale-participation-bots'
_SELECTOR_CALL = 'review_completeness trigger-bot'
_STORED_FINDINGS_READ = 'manage-findings list'
_PRODUCER_CALL = 'fetch_findings --pr-number'
_RE_REVIEW_CALL = 'github_re_review re-review'

_FINALIZE_SKILL = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'SKILL.md'
_TIMED_OUT_ROW = '`reason: re_review_timeout`, `outcome: timed_out`'
_DECLINED_PLACEHOLDER = '{declined_bots}'

_HEADING = re.compile(r'^(#{1,6})\s+(.*)$')
_FLAG = re.compile(r'--[a-z][a-z-]*')


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


def _fenced_blocks(section: str) -> list[str]:
    """Return the body of every fenced code block in ``section``, in order."""
    blocks: list[str] = []
    current: list[str] | None = None
    for line in section.splitlines():
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


def _selector_call(section: str) -> str:
    """Return the fenced block that invokes the ``trigger-bot`` selector, or ``''``."""
    for block in _fenced_blocks(section):
        if _SELECTOR_CALL in block:
            return block
    return ''


def _reads_stale_set_from_participation(section: str) -> bool:
    """Whether ``section`` forwards the producer's participation field to the selector.

    Two things must hold: the section names the producer field it reads, and the
    selector call it documents carries the flag that field is forwarded on. Naming
    the field in prose alone is not reading it.
    """
    return _PARTICIPATION_FIELD in section and _PARTICIPATION_FLAG in _selector_call(section)


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


def _timed_out_detail_cells(text: str) -> list[str]:
    """Return the rendered-detail cell of every timed-out row of the detail table.

    A row is a table line whose first cell starts with the timed-out envelope
    selector; the returned cell is the second one — what the operator is shown.
    """
    cells: list[str] = []
    for line in text.splitlines():
        columns = [column.strip() for column in line.strip().strip('|').split('|')]
        if len(columns) == 2 and columns[0].startswith(_TIMED_OUT_ROW):
            cells.append(columns[1])
    return cells


def _declared_trigger_bot_flags(capsys: pytest.CaptureFixture[str]) -> set[str]:
    """The flags the live ``trigger-bot`` parser declares, read off its ``--help``."""
    with pytest.raises(SystemExit) as exit_info:
        rc.main(['trigger-bot', '--help'])
    assert exit_info.value.code == 0
    return set(_FLAG.findall(capsys.readouterr().out))


_SYNTHETIC_FROM_PARTICIPATION = """\
## Outer

### Re-review after a loop-back fix commit (trigger B)

Read `stale_participation_bots[]` from the producer.

```bash
# a shell comment that is not a heading
review_completeness trigger-bot --plan-id P --stale-participation-bots "x:inline"
```

Still inside the section.

### Next section

stale_participation_bots elsewhere is not this section's concern
"""

_SYNTHETIC_FROM_FINDINGS_ONLY = """\
### Re-review after a loop-back fix commit (trigger B)

The producer also reports `stale_participation_bots[]`, which this section ignores.

```bash
review_completeness trigger-bot --plan-id P --finding-bots x
```
"""


def test_section_reader_returns_the_whole_section_and_stops_at_the_next_heading():
    section = _section(_SYNTHETIC_FROM_PARTICIPATION, _SECTION_TITLE)

    assert 'Read `stale_participation_bots[]` from the producer.' in section
    assert 'Still inside the section.' in section
    assert 'Next section' not in section
    assert 'elsewhere' not in section


def test_section_reader_returns_empty_for_an_absent_title():
    """An absent section reads as empty — the state the real assertions guard against."""
    assert _section(_SYNTHETIC_FROM_PARTICIPATION, 'No such section') == ''


def test_predicate_holds_for_a_section_that_forwards_the_participation_field():
    section = _section(_SYNTHETIC_FROM_PARTICIPATION, _SECTION_TITLE)

    assert _reads_stale_set_from_participation(section)


def test_predicate_fails_for_a_section_that_only_mentions_the_field():
    """Matched negative control: naming the field in prose is not forwarding it."""
    section = _section(_SYNTHETIC_FROM_FINDINGS_ONLY, _SECTION_TITLE)

    assert _PARTICIPATION_FIELD in section
    assert not _reads_stale_set_from_participation(section)


def test_trigger_b_section_reads_the_stale_set_from_participation_state():
    """The real section forwards the producer's field to the selector."""
    section = _section(_AR_SKILL.read_text(encoding='utf-8'), _SECTION_TITLE)

    assert section.strip(), f'section "{_SECTION_TITLE}" not found in {_AR_SKILL}'
    assert _reads_stale_set_from_participation(section)


def test_trigger_b_section_joins_the_stored_finding_bots():
    """The stored-finding commit and HEAD are forwarded, so the selector can join them."""
    call = _selector_call(_section(_AR_SKILL.read_text(encoding='utf-8'), _SECTION_TITLE))

    assert '--reviewed-commit-sha' in call
    assert '--head-sha' in call
    assert '--required-bots' in call


def test_trigger_b_reads_the_stored_commit_before_the_producer_call_restamps_it():
    """The order is load-bearing: read afterwards, the stamp always equals HEAD."""
    section = _section(_AR_SKILL.read_text(encoding='utf-8'), _SECTION_TITLE)

    stored_read = section.find(_STORED_FINDINGS_READ)
    producer_call = section.find(_PRODUCER_CALL)
    selector_call = section.find(_SELECTOR_CALL)
    re_review_call = section.find(_RE_REVIEW_CALL)

    assert -1 not in (stored_read, producer_call, selector_call, re_review_call)
    assert stored_read < producer_call < selector_call < re_review_call


def test_trigger_b_selector_call_uses_only_flags_the_parser_declares(capsys):
    """A flag the verb no longer declares cannot stay in the documented call."""
    call = _selector_call(_section(_AR_SKILL.read_text(encoding='utf-8'), _SECTION_TITLE))
    documented = set(_FLAG.findall(call))
    declared = _declared_trigger_bot_flags(capsys)

    assert documented, 'the documented trigger-bot call names no flag at all'
    assert declared, 'the trigger-bot parser declared no flag — nothing to compare against'
    assert documented <= declared, f'documented but not declared: {sorted(documented - declared)}'


def test_trigger_b_triggers_the_bots_the_selector_lists():
    """The section consumes both returned lists and calls the registry per listed bot."""
    section = _section(_AR_SKILL.read_text(encoding='utf-8'), _SECTION_TITLE)

    assert 'trigger_bots[]' in section
    assert 'required_stale_bots[]' in section
    assert 'once per bot' in section


def test_a_required_stale_bot_is_triggered_with_the_knob_off():
    """The knob's ``false`` row names the required stale bots, not an empty set."""
    section = _section(_AR_SKILL.read_text(encoding='utf-8'), _SECTION_TITLE)
    false_rows = [line for line in section.splitlines() if line.lstrip().startswith('| `false`')]

    assert len(false_rows) == 1, false_rows
    assert 'required_stale_bots[]' in false_rows[0]


def test_knob_description_names_the_required_stale_bot_exception():
    description = _frontmatter_description(_AR_SKILL.read_text(encoding='utf-8'), _KNOB)

    assert description, f'no frontmatter description found for {_KNOB}'
    assert 'participated_stale' in description
    assert 'REQUIRED' in description


def test_guard_remedy_text_says_the_loop_back_leads_to_the_trigger():
    """The guard's ``participated_stale`` remedy points at trigger B, knob off included."""
    guard = _section(_AR_SKILL.read_text(encoding='utf-8'), _GUARD_TITLE)
    remedy_lines = [line for line in guard.splitlines() if 'A required bot on `participated_stale`' in line]

    assert guard.strip(), f'section "{_GUARD_TITLE}" not found in {_AR_SKILL}'
    assert len(remedy_lines) == 1, remedy_lines
    assert 'trigger B' in remedy_lines[0]
    assert f'even when `{_KNOB}` is `false`' in remedy_lines[0]


_SYNTHETIC_TIMEOUT_ROW_ONLY = """\
| Envelope | `{outcome_detail}` renders as |
|----------|-------------------------------|
| `reason: re_review_timeout`, `outcome: timed_out` | `re-review timed out` |
| `reason: re_review_timeout`, `outcome: declined` | `DECLINED by {declined_bots}` |
"""


def test_detail_cell_reader_ignores_the_decline_row():
    """Matched negative control: a decline row naming the bots is not a timed-out row."""
    cells = _timed_out_detail_cells(_SYNTHETIC_TIMEOUT_ROW_ONLY)

    assert cells == ['`re-review timed out`']
    assert not any(_DECLINED_PLACEHOLDER in cell for cell in cells)


def test_finalize_hook_names_the_declined_bots_on_a_timed_out_pass():
    """A pass that asked several bots can time out AND carry declines.

    The escalation hook renders one detail line for the operator. With a single
    timed-out row that line drops every bot that declined on the same pass, so the
    operator is offered a longer wait for a bot that will only decline again.
    """
    cells = _timed_out_detail_cells(_FINALIZE_SKILL.read_text(encoding='utf-8'))

    assert len(cells) == 2, cells
    assert sum(_DECLINED_PLACEHOLDER in cell for cell in cells) == 1, cells
