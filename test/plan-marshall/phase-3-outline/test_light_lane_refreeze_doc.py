#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-133 D2 — a re-freeze decision in the light lane has a documented path.

The light lane's transition step treats every non-``success``
``snapshot-criteria`` result as an unreadable outline and halts. One of those
results is not that: ``refreeze_requires_decision`` says the criteria are
already frozen and a re-freeze needs an operator decision. The lane runs as a
dispatched envelope, so it cannot ask the operator itself — the documented path
is a prompt-required envelope the dispatching context turns into the operator
question, the ``criteria-refreeze-authorize`` verb and one retry.

Document-only: the behaviour lives in the snapshot verb and the finalize flow,
and this module asserts what the lane tells its dispatcher to do.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import get_skill_dir


def _normalized(path: Path) -> str:
    """The document's text with whitespace collapsed, so a wrapped sentence matches."""
    return re.sub(r'\s+', ' ', path.read_text(encoding='utf-8'))


def test_the_light_lane_routes_a_refreeze_decision_to_the_operator() -> None:
    """The lane names the decision, its verb, the envelope and the operator question."""
    text = _normalized(get_skill_dir('plan-marshall', 'phase-3-outline') / 'workflow' / 'light-lane.md')

    assert 'refreeze_requires_decision' in text, 'the light lane never names the re-freeze decision'
    assert 'criteria-refreeze-authorize' in text, 'the light lane names no re-freeze authorization verb'
    assert 'prompt-required envelope' in text, 'the lane documents no envelope the orchestrator can fire'
    assert 'AskUserQuestion' in text, 'the lane names no operator question'


def test_the_refreeze_result_is_not_read_as_an_unreadable_outline() -> None:
    """The blanket "any non-success is an error" reading is gone.

    The lane used to halt every non-``success`` freeze with ``status: error``,
    which is exactly the reading the decision does not deserve. The document
    keeps the error branch for the other failures and states the decision branch
    separately.
    """
    text = _normalized(get_skill_dir('plan-marshall', 'phase-3-outline') / 'workflow' / 'light-lane.md')

    assert 'Do NOT read this result as an unreadable outline' in text
    assert 'status: error' in text, 'the other non-success results still need the halt branch'
