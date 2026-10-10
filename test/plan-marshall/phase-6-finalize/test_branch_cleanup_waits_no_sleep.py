#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The merge-lock admission loops of ``branch-cleanup`` instruct no sleep.

Both admission loops — the early-hold acquire in § "Acquire the Merge Mutex" and
the Pre-Merge Gate's § "FIFO poll/backoff loop" — used to pace ``merge_lock
acquire`` polls with a standalone foreground ``sleep {interval}`` the harness
refuses, so the ``merge_queue_wait_budget_seconds`` budget was unreachable. The
wait now lives in the script — ``merge_lock acquire --wait-seconds`` — and the
step only re-issues that bounded call.

This suite pins the document side of that contract: each loop names the bounded
call, holds no sleep instruction, and passes no removed ``--timeout`` flag to
``acquire``. The section reader and the detectors are exercised against a synthetic
document first, so a reader that silently returns nothing cannot make the real
assertions pass.
"""

from __future__ import annotations

import re

import pytest

from conftest import get_skill_dir

_BRANCH_CLEANUP = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'standards' / 'branch-cleanup.md'
_ADMISSION_LOOP_SECTIONS = ('Acquire the Merge Mutex', 'FIFO poll/backoff loop')

_HEADING = re.compile(r'^(#{1,6})\s+(.*)$')
_SLEEP_INSTRUCTION = re.compile(r'\bsleep\b', re.IGNORECASE)
# One acquire invocation: from the notation up to the end of its fenced block.
_ACQUIRE_INVOCATION = re.compile(r'merge_lock acquire\b.*?(?=^```)', re.DOTALL | re.MULTILINE)


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


def _acquire_invocations(section: str) -> list[str]:
    """Return every fenced ``merge_lock acquire`` invocation in ``section``."""
    return [match.group(0) for match in _ACQUIRE_INVOCATION.finditer(section)]


_SYNTHETIC_DOC = """\
## Outer

###### FIFO poll/backoff loop

Poll the lock.

```bash
# a shell comment that is not a heading
python3 .plan/execute-script.py plan-marshall:manage-locks:merge_lock acquire \\
  --plan-id {plan_id} --timeout 30
```

Pace the next poll with a single standalone `sleep {interval}` call.

###### Budget-exhaustion escalation

sleep elsewhere is not this section's concern
"""


def test_section_reader_returns_the_whole_section_and_stops_at_the_next_heading():
    """The reader keeps fenced lines, ignores a ``#`` comment in a fence, and stops in time."""
    section = _section(_SYNTHETIC_DOC, 'FIFO poll/backoff loop')

    assert 'Poll the lock.' in section
    assert '--timeout 30' in section
    assert 'Pace the next poll' in section
    assert 'Budget-exhaustion escalation' not in section
    assert 'sleep elsewhere' not in section


def test_detectors_fire_on_a_loop_that_sleeps_and_passes_the_removed_flag():
    """Matched negative control: the detectors find what the real loops must lack."""
    section = _section(_SYNTHETIC_DOC, 'FIFO poll/backoff loop')
    invocations = _acquire_invocations(section)

    assert _SLEEP_INSTRUCTION.search(section)
    assert len(invocations) == 1
    assert '--timeout' in invocations[0]
    assert '--wait-seconds' not in invocations[0]


def test_section_reader_returns_empty_for_an_absent_title():
    """An absent section reads as empty — the state the real assertions guard against."""
    assert _section(_SYNTHETIC_DOC, 'No such section') == ''


@pytest.mark.parametrize('title', _ADMISSION_LOOP_SECTIONS)
def test_admission_loop_names_the_bounded_acquire_and_instructs_no_sleep(title: str):
    """Each real admission loop is present, re-issues ``acquire --wait-seconds``, and
    never instructs a sleep."""
    section = _section(_BRANCH_CLEANUP.read_text(encoding='utf-8'), title)
    invocations = _acquire_invocations(section)

    assert section.strip(), f'section "{title}" not found in {_BRANCH_CLEANUP}'
    assert invocations, f'section "{title}" carries no merge_lock acquire invocation'
    assert all('--wait-seconds' in invocation for invocation in invocations), invocations
    assert not _SLEEP_INSTRUCTION.search(section)


@pytest.mark.parametrize('title', _ADMISSION_LOOP_SECTIONS)
def test_admission_loop_passes_no_removed_timeout_flag(title: str):
    """No acquire invocation, and no prose, in either loop still carries ``--timeout``."""
    section = _section(_BRANCH_CLEANUP.read_text(encoding='utf-8'), title)

    assert section.strip(), f'section "{title}" not found in {_BRANCH_CLEANUP}'
    assert '--timeout' not in section
