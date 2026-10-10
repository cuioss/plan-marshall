#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract test: the light lane persists ``pr_title`` before the 2-refine capture.

The ``2-refine`` handshake capture refuses with ``pr_title_missing`` when
``status.metadata.pr_title`` is absent. On the deep lane phase-2-refine Step 13
authors the title; the light lane runs no phase-2-refine, so planning.md's
"Light-lane branch" makes the orchestrator persist it before the capture. This
test pins the ORDER inside that section: a producer documented after the
capture would leave every light-lane plan refusing at the boundary (or
needing ``--override``), which is the defect this contract closes. The
behavioural counterpart lives in ``test_lifecycle_handshake_e2e.py``.
"""

from __future__ import annotations

import re

from conftest import MARKETPLACE_ROOT

PLANNING_MD = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow' / 'planning.md'

_SECTION_START = '**Light-lane branch**'
_SECTION_END = '**Deep-lane branch**'

# The producer: a manage-status metadata --set call naming the pr_title field.
_PRODUCER_RE = re.compile(
    r'manage-status:manage-status metadata\s*\\?\s*--plan-id \{plan_id\} --set --field pr_title\b'
)

# The consumer: the 2-refine handshake capture (the command may wrap onto a
# continuation line between the verb and its flags).
_CAPTURE_RE = re.compile(r'phase_handshake capture\s*\\?\s*--plan-id \{plan_id\} --phase 2-refine\b')

# The 2-refine transition the capture is paired with.
_TRANSITION_RE = re.compile(
    r'manage-status:manage-status transition\s*\\?\s*--plan-id \{plan_id\} --completed 2-refine\b'
)


def _light_lane_section() -> str:
    text: str = PLANNING_MD.read_text(encoding='utf-8')
    start = text.find(_SECTION_START)
    assert start != -1, f'{_SECTION_START!r} not found in {PLANNING_MD}'
    end = text.find(_SECTION_END, start)
    assert end != -1, f'{_SECTION_END!r} not found after the light-lane section in {PLANNING_MD}'
    return text[start:end]


def _single_match(pattern: re.Pattern[str], section: str, label: str) -> re.Match[str]:
    matches = list(pattern.finditer(section))
    assert len(matches) == 1, f'expected exactly one {label} in the light-lane section, found {len(matches)}'
    return matches[0]


def test_pr_title_persist_precedes_refine_capture() -> None:
    section = _light_lane_section()

    producer = _single_match(_PRODUCER_RE, section, 'pr_title persist')
    capture = _single_match(_CAPTURE_RE, section, '2-refine capture')

    assert producer.start() < capture.start(), (
        'planning.md light-lane section must persist pr_title BEFORE the phase_handshake capture --phase 2-refine call'
    )


def test_pr_title_persist_precedes_refine_transition() -> None:
    """The producer sits ahead of the whole close sequence, not just the capture.

    The transition and its paired capture must not be separated, so a producer
    wedged between them would split the pair; it belongs before both.
    """
    section = _light_lane_section()

    producer = _single_match(_PRODUCER_RE, section, 'pr_title persist')
    transition = _single_match(_TRANSITION_RE, section, '2-refine transition')

    assert producer.start() < transition.start(), (
        'planning.md light-lane section must persist pr_title BEFORE the 2-refine transition'
    )
