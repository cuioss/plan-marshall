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


def test_the_deliverables_section_requires_the_sonar_open_finding_read() -> None:
    """A Sonar project's spec must list the head's open-finding read in its Done-when."""
    section = _section('## Deliverables')

    assert 'analyses its pull requests with Sonar' in section
    assert '`sonar: configured`' in section
    assert 'open-finding read at the head' in section
    assert 'security hotspots still to review' in section, (
        'the hotspot leg is the miss the read exists to close; the template must name it'
    )
    assert 'never `0`' in section, 'a failed read must not be written as a zero'


def test_the_standing_constraints_section_states_how_a_dismissal_is_obtained() -> None:
    section = _section('## Standing Constraints')

    assert 'OPERATOR' in section, 'a dismissal is the operator decision, never the lane decision'
    assert '`operator-selected: {issue-key}: {reason}`' in section, (
        'the record shape of an operator selection must be stated'
    )
    assert 'sonar_rest transition' in section, 'the plan-less transmission verb must be named'
    assert 'blocker' in section, 'a dismissal that cannot be transmitted must block'
    assert '`sonar-gate --dismissed-keys` is refused' in section, 'the retired lane-dismissal surface must be named'


def test_the_deliverables_section_requires_the_consumer_visible_set() -> None:
    """An unchanged-consumer deliverable must enumerate the field and edge set."""
    section = _section('## Deliverables')

    assert 'serves an existing consumer unchanged' in section
    assert 'consumer-visible field and edge set' in section
    assert 'one verification criterion per element' in section
    assert 'cannot enumerate the set says so' in section, 'an unenumerable set must be declared, not implied'


# =============================================================================
# The Done-when and Expected Surface authoring rules
# =============================================================================
#
# A Done-when labelled "fails at" a sha where the behaviour already holds cannot
# be met, and one labelled "holds at" over an unsettled HYPOTHESIS assumes what
# the spec has not established. Both defects reached shipped specs because no
# document stated the rule; the template and `decompose.md` Step 4 state it now,
# and `corpus lint-done-whens` checks it.

DECOMPOSE: Path = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-orchestrator' / 'workflow' / 'decompose.md'

#: The three Done-when rules, as the phrases every stating document must carry.
_DONE_WHEN_RULE_PHRASES = (
    'only for behaviour that is NEW at that sha',
    'preservation or coverage clause says "holds at `{sha}`"',
    'never labelled "holds at" while a claim it rests on is still a `HYPOTHESIS`',
)


def _decompose_step_four() -> str:
    """Step 4 of ``decompose.md`` with its whitespace collapsed."""
    text = DECOMPOSE.read_text(encoding='utf-8')
    match = re.search(r'^### Step 4:.*?(?=^### |\Z)', text, re.MULTILINE | re.DOTALL)
    assert match is not None, 'decompose.md carries no "### Step 4:" section'
    return ' '.join(match.group(0).split())


class TestDoneWhenAuthoringRules:
    def test_the_template_states_the_three_done_when_rules(self) -> None:
        section = _section('## Deliverables')

        for phrase in _DONE_WHEN_RULE_PHRASES:
            assert phrase in section, phrase

    def test_the_decompose_step_states_the_three_done_when_rules(self) -> None:
        step = _decompose_step_four()

        for phrase in _DONE_WHEN_RULE_PHRASES:
            assert phrase in step, phrase

    def test_the_template_requires_a_full_repo_relative_surface_entry(self) -> None:
        section = _section('## Expected Surface')

        assert 'FULL repo-relative path' in section
        assert 'reported as unresolved' in section, (
            'the template must say what happens to a bare filename, not only that it is wrong'
        )

    def test_both_documents_name_the_lint_verb(self) -> None:
        assert 'corpus lint-done-whens' in _section('## Deliverables')
        assert 'corpus lint-done-whens' in _decompose_step_four()


def test_the_template_asks_both_obligations_of_a_deliverable() -> None:
    """The two obligations are independent: neither stands in for the other."""
    deliverables = _section('## Deliverables')

    assert 'consumer-visible field and edge set' in deliverables
    assert 'open-finding read at the head' in deliverables
