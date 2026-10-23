#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for what the plan-spec template must ASK of a staged spec.

Two authoring obligations were missing from the template, and both were learned
from a shipped plan whose review rounds paid for them one finding at a time:

* A project that analyses its pull requests with Sonar needs the open-issue read
  in the spec's Done-when and the dismissal rule in its Standing Constraints.
  Without them a staged spec lists the build gates and says nothing about the
  issues the merge leaves open — the run then reports a green gate over a pull
  request that is not clean.
* A deliverable that keeps an existing consumer unchanged must enumerate that
  consumer's consumer-visible field and edge set, with one verification
  criterion per element. Written as prose instead, the boundary is discovered
  across review rounds rather than at outline.

Each obligation is asserted inside the SECTION that must carry it, so a phrase
moved elsewhere in the template cannot satisfy the check.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT

TEMPLATE: Path = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-orchestrator' / 'templates' / 'plan-spec.md'


def _section(heading: str) -> str:
    """Return the template's text from *heading* up to the next level-2 heading.

    Whitespace is collapsed to single spaces: the assertions below quote phrases,
    and a phrase wrapped across two source lines states the same requirement.
    """
    text = TEMPLATE.read_text(encoding='utf-8')
    match = re.search(
        rf'^{re.escape(heading)}\s*$(?P<body>.*?)(?=^## |\Z)',
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f'the template carries no {heading!r} section'
    return ' '.join(match.group('body').split())


def test_the_deliverables_section_requires_the_sonar_open_issue_read() -> None:
    """A Sonar project's spec must list the head's open-issue read in its Done-when."""
    section = _section('## Deliverables')

    assert 'analyses its pull requests with Sonar' in section
    assert '`sonar: configured`' in section
    assert 'open-issue read at the head' in section
    assert 'never `0`' in section, 'a failed read must not be written as a zero'


def test_the_standing_constraints_section_states_how_a_dismissal_is_recorded() -> None:
    section = _section('## Standing Constraints')

    assert '`{issue-key}: {reason}`' in section, 'the record shape of a dismissal must be stated'
    assert 'sonar_rest transition' in section, 'the plan-less transmission verb must be named'
    assert 'blocker' in section, 'a dismissal that cannot be transmitted must block'


def test_the_deliverables_section_requires_the_consumer_visible_set() -> None:
    """An unchanged-consumer deliverable must enumerate the field and edge set."""
    section = _section('## Deliverables')

    assert 'serves an existing consumer unchanged' in section
    assert 'consumer-visible field and edge set' in section
    assert 'one verification criterion per element' in section
    assert 'cannot enumerate the set says so' in section, 'an unenumerable set must be declared, not implied'


def test_the_template_asks_both_obligations_of_a_deliverable() -> None:
    """The two obligations are independent: neither stands in for the other."""
    deliverables = _section('## Deliverables')

    assert 'consumer-visible field and edge set' in deliverables
    assert 'open-issue read at the head' in deliverables
