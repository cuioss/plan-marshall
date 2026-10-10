#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The completion-aware poll of ``automatic-review`` instructs no sleep.

The poll used to be paced by the step itself: one ``bot_completion`` read, then a
standalone ``sleep`` call, repeated until the bound. A step that runs inside a
dispatched leaf cannot hold such a pause, so the instruction was one the step could
not carry out. The wait now lives in the script — ``bot_completion --wait-seconds``
— and the step only re-issues that bounded call.

This suite pins the document side of that contract: the section
"Completion-aware poll" of ``automatic-review/SKILL.md`` holds no sleep instruction
and names the bounded call instead. The assertions run against the real document
text, and the section reader is exercised against a synthetic document first so a
reader that silently returns nothing cannot make the real assertion pass.
"""

from __future__ import annotations

import re

from conftest import get_skill_dir

_AR_SKILL = get_skill_dir('plan-marshall', 'automatic-review') / 'SKILL.md'
_SECTION_TITLE = 'Completion-aware poll'
_POLL_TIMEOUT_KEY = 'review_completion_poll_timeout_seconds'

_HEADING = re.compile(r'^(#{1,6})\s+(.*)$')
_SLEEP_INSTRUCTION = re.compile(r'\bsleep\b', re.IGNORECASE)


def _section(text: str, title: str) -> str:
    """Return the body of the first heading starting with ``title``.

    The section runs from its heading to the next heading of the same or a higher
    level. Lines inside a fenced code block are never read as headings, so a shell
    comment in an example does not cut the section short.
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


_SYNTHETIC_DOC = """\
## Outer

#### Completion-aware poll (per enabled bot)

Poll the bot.

```bash
# a shell comment that is not a heading
sleep 30
```

Still inside the section.

### Next section

sleep elsewhere is not this section's concern
"""


def test_section_reader_returns_the_whole_section_and_stops_at_the_next_heading():
    """The reader keeps fenced lines, ignores a ``#`` comment in a fence, and stops in time."""
    section = _section(_SYNTHETIC_DOC, _SECTION_TITLE)

    assert 'Poll the bot.' in section
    assert 'sleep 30' in section
    assert 'Still inside the section.' in section
    assert 'Next section' not in section
    assert 'sleep elsewhere' not in section


def test_sleep_detector_fires_on_a_section_that_instructs_a_sleep():
    """Matched negative control: the detector finds the sleep the real section must lack."""
    assert _SLEEP_INSTRUCTION.search(_section(_SYNTHETIC_DOC, _SECTION_TITLE))


def test_section_reader_returns_empty_for_an_absent_title():
    """An absent section reads as empty — the state the real assertions guard against."""
    assert _section(_SYNTHETIC_DOC, 'No such section') == ''


def test_completion_aware_poll_section_holds_no_sleep_instruction():
    """The real section is present, names the bounded call, and instructs no sleep."""
    section = _section(_AR_SKILL.read_text(encoding='utf-8'), _SECTION_TITLE)

    assert section.strip(), f'section "{_SECTION_TITLE}" not found in {_AR_SKILL}'
    assert 'bot_completion' in section
    assert '--wait-seconds' in section
    assert not _SLEEP_INSTRUCTION.search(section)


def test_completion_aware_poll_section_records_an_unfinished_bot_beyond_the_log():
    """A bot unfinished at the bound is named in ``display_detail`` and the step record."""
    section = _section(_AR_SKILL.read_text(encoding='utf-8'), _SECTION_TITLE)

    assert 'timed_out' in section
    assert 'display_detail' in section
    assert 'mark-step-done' in section


def test_poll_timeout_frontmatter_description_names_the_bounded_call():
    """The configurable's description matches the section: a bounded call, no sleep."""
    description = _frontmatter_description(_AR_SKILL.read_text(encoding='utf-8'), _POLL_TIMEOUT_KEY)

    assert description, f'no frontmatter description found for {_POLL_TIMEOUT_KEY}'
    assert '--wait-seconds' in description
    assert not _SLEEP_INSTRUCTION.search(description)
