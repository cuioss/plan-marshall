#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""An OPTIONAL bot's decline or timeout is recorded — and never escalates.

Trigger B asks optional bots too (they join `trigger_bots[]` when
``re_review_on_loopback`` is true), and the ``not_triggered`` remediation asks every
configured bot because no ``pull_request``-event run exists for the PR at all. Both
then handed whatever answered to ``re_review_on_timeout`` with no optional-bot filter,
so an optional bot's decline returned ``escalate_ask{reason: re_review_timeout}`` — a
question the operator does not need answered, and, under the ``defer`` policy, a skipped
merge bought by a reviewer nobody required.

The quorum is over ``required_bots`` everywhere else in this contract, and an optional
bot's silence is explicitly not a failure. These tests hold both escalation sites to
that: the filter is stated, and the REQUIRED behaviour is unchanged — a required bot's
timeout still escalates under ``re_review_on_timeout: ask``.

The readers are exercised against synthetic documents first, so a reader that returns
nothing cannot make an assertion on the real document pass.
"""

from __future__ import annotations

import re

import pytest

from conftest import get_skill_dir

_AR_SKILL = get_skill_dir('plan-marshall', 'automatic-review') / 'SKILL.md'

_TIMEOUT_TITLE = 'On re-review timeout (trigger B)'
_NOT_TRIGGERED_ANCHOR = '**Generating the trigger for `not_triggered`.**'

_FILTER_PHRASES = (
    'an optional bot',
    'RECORDED',
    'does not escalate',
)

_HEADING = re.compile(r'^(#{1,6})\s+(.*)$')


def _section(text: str, title: str) -> str:
    """Return the body of the first heading starting with ``title``, to its next peer.

    Lines inside a fenced block are never read as headings, so a command block that
    happens to carry a ``#`` line cannot truncate the slice.
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


def _paragraph(text: str, anchor: str) -> str:
    """Return ``text`` from ``anchor`` to its own paragraph break, or to the end."""
    start = text.index(anchor)
    end = text.find('\n\n', start)
    return text[start:end] if end != -1 else text[start:]


def _assert_optional_filter(text: str, where: str) -> None:
    """THE rule — one definition, called by both sites' assertions and their controls.

    An optional bot must be (a) named, (b) RECORDED rather than dropped, and (c) said
    not to escalate. A document that merely mentions "optional" somewhere nearby is
    not a filter: all three conjuncts are required, and the required-bot behaviour is
    asserted separately so the filter cannot be implemented by silencing the
    escalation altogether.
    """
    missing = [phrase for phrase in _FILTER_PHRASES if phrase not in text]
    assert not missing, (
        f'{where} does not state the optional-bot filter ({", ".join(missing)} missing) — '
        'an optional bot answering it would escalate under re_review_on_timeout'
    )


def test_the_timeout_reader_returns_the_sub_block():
    """Scaffold control: the slice is bounded and non-empty."""
    section = _section(_AR_SKILL.read_text(encoding='utf-8'), _TIMEOUT_TITLE)

    assert section.strip(), 'the timeout sub-block was not found in the SKILL'
    assert 're_review_on_timeout' in section


def test_the_trigger_b_timeout_block_never_escalates_an_optional_bot():
    """Trigger B: an optional bot's decline or timeout is recorded, not escalated."""
    section = _section(_AR_SKILL.read_text(encoding='utf-8'), _TIMEOUT_TITLE)

    _assert_optional_filter(section, 'the trigger-B timeout sub-block')


def test_the_not_triggered_remediation_never_escalates_an_optional_bot():
    """The PR-wide remediation: same filter, because it triggers optional bots too."""
    paragraph = _paragraph(_AR_SKILL.read_text(encoding='utf-8'), _NOT_TRIGGERED_ANCHOR)

    _assert_optional_filter(paragraph, 'the not_triggered remediation')


def test_a_required_bot_still_escalates_on_timeout():
    """⛔ The other half: the filter must not have silenced the escalation itself.

    ``re_review_on_timeout: ask`` remains the default, and a REQUIRED bot that timed
    out or declined still returns ``escalate_ask{reason: re_review_timeout}``. Without
    this arm, deleting the whole timeout policy would pass the two tests above.
    """
    section = _section(_AR_SKILL.read_text(encoding='utf-8'), _TIMEOUT_TITLE)

    assert 'escalate_ask' in section
    assert 'reason: re_review_timeout' in section
    assert 're_review_on_timeout' in section


def test_the_rule_rejects_a_document_without_the_filter():
    """⛔ Negative control: the shipped defect, planted — the rule must FAIL on it.

    This is the pre-fix text's shape: optional bots join the trigger list and every
    answer is disposed under the timeout policy with no filter. The real documents are
    asserted ACCEPTED above, so the rejection is the planted omission rather than a
    rule that rejects everything.
    """
    without_filter = (
        'Read re_review_on_timeout and branch on its value; the policy is applied '
        'verbatim on both entry paths. Every bot that answered is disposed this way.'
    )

    with pytest.raises(AssertionError) as rejection:
        _assert_optional_filter(without_filter, 'synthetic')
    assert 'synthetic' in str(rejection.value)
