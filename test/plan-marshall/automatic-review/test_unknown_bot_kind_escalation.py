#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pin the ``unregistered_kind`` escalation contract in ``automatic-review/SKILL.md``.

The classifier can only report the state; what makes it ACTIONABLE is the prose the
step surfaces when a required bot lands on it. That prose is the deliverable, so it
is what this suite pins.

The escalation must name THREE things, and each is here for a reason the other two
do not cover:

1. **The configured token, verbatim** — otherwise the operator is told a reviewer
   name is wrong and not which one, and cannot search ``marshal.json`` for it.
2. **The live kind set it was checked against** — the remedy. Naming a name as
   wrong without naming the right ones is half an escalation, and this set is where
   the corrected token comes from (ADR-019's coverage discriminator, carried on the
   predicate's return for exactly this use).
3. **The login→kind mapping for any reviewer OBSERVED on the PR that the
   configuration does not classify** — the other half of the same confusion. To an
   operator "a configured name the registry cannot place" and "an observed reviewer
   the configuration does not classify" look identical, and their remedies differ.

**Pre-fix form fails.** Before this deliverable the escalation block does not exist
in ``SKILL.md`` at all, so every assertion below fails against the pre-change text —
including the block-presence test, which fails with a message naming what is absent
rather than with a bare ``ValueError`` out of a string search.

**Every expectation is DERIVED, never a literal reviewer name.** The state token is
read off ``review_completeness``'s own constant and the kind set off
``bot_registry.bot_kinds()``, so the assertions survive a registry rename unchanged —
which is the point: a hard-coded "valid" bot name would turn this suite red on a
rename that changed nothing about the contract it pins.
"""

from __future__ import annotations

import re
from pathlib import Path

# ``bot_registry`` / ``review_completeness`` are automatic-review skill scripts.
# Under the executor they arrive on one injected PYTHONPATH; under pytest the root
# conftest puts every marketplace ``scripts/`` directory on ``sys.path`` before any
# test module is imported, so no bootstrap is needed here.
import bot_registry
import review_completeness as rc

from conftest import get_skill_dir

_SKILL_MD: Path = get_skill_dir('plan-marshall', 'automatic-review') / 'SKILL.md'

#: The escalation block's opening marker and the heading that closes it. Both are
#: bold-run markers in the surrounding numbered list rather than ``#`` headings, so
#: the block is delimited by them rather than by a heading-level scan.
_BLOCK_START = '**Escalating `unregistered_kind`'
_BLOCK_END = '**Generating the trigger for `not_triggered`.**'

#: Cardinals a member count could be written as: digit runs, the number words, and the
#: vague quantifiers English substitutes for them. The set is deliberately INDEPENDENT
#: of the taxonomy's current size — a detector that enumerated only the cardinals
#: bracketing today's count would stop matching the moment the count it exists to catch
#: drifted past that bracket, which is the one case it is for.
_CARDINAL = (
    r'\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
    r'thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|'
    r'thirty|forty|fifty|dozen|several'
)

#: A cardinal is a restated member count only when it sits beside the noun phrase the
#: contract names. Anchoring on ``non-participation`` is what keeps unrelated prose out
#: of the match — "PR 508 closed the loop" and "the 2 member logins" both carry a
#: cardinal next to one of the nouns, and neither restates a count.
_STALE_COUNT_RE = re.compile(
    rf'\b(?:{_CARDINAL})[ -](?:closed[ -])?non-participation',
    re.IGNORECASE,
)


def _skill_text() -> str:
    return _SKILL_MD.read_text(encoding='utf-8')


def _live_kinds() -> list[str]:
    """The registry kind set — derived, and asserted non-empty.

    The emptiness guard is the anti-vacuity check for the negative assertion below:
    "no live kind literal appears in the escalation block" is trivially true over an
    empty set, so a registry that resolved nothing would make that test pass while
    proving nothing.
    """
    kinds = bot_registry.bot_kinds()
    assert kinds, 'bot_registry resolved no kinds — the derived assertions would be vacuous'
    return kinds


def _escalation_block() -> str:
    """The ``unregistered_kind`` escalation block, or a failure naming its absence."""
    text = _skill_text()
    assert _BLOCK_START in text, (
        f'{_SKILL_MD.name} carries no {_BLOCK_START!r} block — the unregistered_kind '
        'escalation is the deliverable this suite pins, and without it a required bot '
        'on that state renders exactly like `absent` and sends the operator to chase a '
        'reviewer that does not exist.'
    )
    start = text.index(_BLOCK_START)
    assert _BLOCK_END in text[start:], (
        f'the escalation block is not closed by {_BLOCK_END!r}; the delimiters this '
        'suite reads have moved and the extraction can no longer be trusted'
    )
    return text[start : text.index(_BLOCK_END, start)]


def test_the_escalation_block_is_present():
    """The block-presence gate: this is the assertion the pre-fix form fails on."""
    assert _escalation_block()


def test_escalation_names_the_configured_token_verbatim():
    """(1) The offending token itself, sourced from the classifier's own row.

    The block must point at `bot_states` (where the token lives) and render the token
    into the operator-facing message. A message that only says "an unknown reviewer is
    configured" names no token at all.
    """
    block = _escalation_block()

    assert 'bot_states' in block, 'the escalation does not say where the token comes from'
    assert '{bot_kind}' in block, (
        'the escalation renders no token placeholder — the operator is told a name is '
        'wrong without being told which name'
    )


def test_escalation_names_the_live_kind_set_it_was_checked_against():
    """(2) The remedy set, by the field the predicate actually carries.

    ``known_bot_kinds`` is the population the membership test ran over. Naming the
    field (rather than a snapshot of its contents) is what keeps the escalation
    correct as the registry changes.
    """
    block = _escalation_block()

    assert 'known_bot_kinds' in block, (
        'the escalation never names the live kind set — an operator told a name is '
        'wrong is not told which names are right'
    )


def test_escalation_names_the_unclassified_login_mapping():
    """(3) The observed-reviewer half of the same confusion.

    Without it the escalation covers only one of the two indistinguishable failures,
    and the operator cannot tell which one they are looking at.
    """
    block = _escalation_block()

    assert 'unclassified_bots' in block, (
        'the escalation never names the observed reviewers the configuration does not '
        'classify — the other half of the confusion it exists to resolve'
    )


def test_the_kind_literal_scan_is_answerable_over_this_document():
    """Positive control for the negative assertion below.

    "No live reviewer name appears in the escalation block" is only meaningful if the
    scan could have found one. This proves it can: at least one registry kind IS named
    somewhere in this document, so a zero inside the block is a real absence rather
    than a scan that never matches anything.
    """
    text = _skill_text()
    present = [kind for kind in _live_kinds() if kind in text]

    assert present, (
        'no registry kind name appears anywhere in SKILL.md, so the negative assertion '
        'below cannot discriminate — it would pass against any text at all'
    )


def test_escalation_does_not_hardcode_todays_reviewer_names():
    """The MATCHED NEGATIVE CONTROL: the remedy set is a field, not a snapshot.

    Spelling today's bot names into the prose would read identically to a reader and
    go stale silently on the next registry change — including this plan's own rename.
    Naming ``known_bot_kinds`` instead is what makes the escalation survive it.
    """
    block = _escalation_block()
    hardcoded = [kind for kind in _live_kinds() if kind in block]

    assert hardcoded == [], (
        f'the escalation hard-codes reviewer name(s) {hardcoded!r}; render '
        'known_bot_kinds instead so the remedy set follows the registry'
    )


def test_escalation_cross_references_the_unclassified_bots_owner():
    """The `unclassified_bots` contract is cross-referenced, never restated.

    Two descriptions of one producer field are two things to keep in step, and the
    copy is the one that goes stale — so the outline requires a cross-reference here.
    """
    block = _escalation_block()

    assert '../workflow-integration-github/SKILL.md' in block, (
        'the escalation does not link the producer that owns unclassified_bots'
    )


def test_escalation_defers_the_member_definition_to_the_contract_doc():
    """The taxonomy member is owned by the central standard, not restated here.

    Enforcement-critical taxonomy content lives in exactly one place; a second copy in
    an operator-facing escalation is how the doc and the classifier come to disagree.
    """
    block = _escalation_block()

    assert 'standards/bot-participation-contract.md' in block, (
        'the escalation does not defer the member definition to the owning standard'
    )


def test_escalation_points_at_the_two_knobs_that_hold_the_token():
    """The remedy is an edit, and the escalation says which keys to edit."""
    block = _escalation_block()

    assert 'required_bots' in block and 'optional_bots' in block, (
        'the escalation prescribes correcting the token without naming the knobs it '
        'lives in'
    )


def test_the_state_token_in_the_doc_is_the_modules_own_constant():
    """The doc names the state by the value the classifier actually returns.

    Derived from ``review_completeness`` rather than typed as a literal, so a rename of
    the constant cannot leave the escalation keyed on a state nothing resolves to.
    """
    block = _escalation_block()

    assert rc.STATE_UNREGISTERED_KIND in block


def test_the_state_blocks_and_the_document_lists_it_among_the_unproven_members():
    """Escalating a member that did not block would be prose over nothing.

    Both halves are asserted from their own source: membership from the module's
    ``_UNPROVEN_STATES``, and the document's own enumeration of the blocking set.
    """
    assert rc.STATE_UNREGISTERED_KIND in rc._UNPROVEN_STATES

    text = _skill_text()
    unproven_sentence = text[text.index('at least one REQUIRED bot is in `unproven_bots`') :][:400]
    assert rc.STATE_UNREGISTERED_KIND in unproven_sentence, (
        'the document enumerates the blocking members without naming '
        f'{rc.STATE_UNREGISTERED_KIND}, so a reader concludes it does not block'
    )


def test_the_document_enumerates_the_taxonomy_without_restating_its_size():
    """A hand-written member count is the defect one member later.

    The count is stated in exactly one place — the contract doc, where a test reads it
    back against the module's own constants. Any cardinal restated beside the
    "non-participation" noun phrase here is an unguarded duplicate, and this document's
    own enumeration line already went stale that way once.
    """
    text = _skill_text()
    stale_count = _STALE_COUNT_RE.search(text)

    assert stale_count is None, (
        f'SKILL.md restates a taxonomy member count ({stale_count.group(0)!r}); enumerate '
        'the members instead and leave the count to bot-participation-contract.md, whose '
        'figure is asserted against review_completeness'
    )


def test_the_full_state_enumeration_names_the_new_member():
    """The `bot_states` enumeration is what a reader maps a returned row against."""
    text = _skill_text()
    enumeration = text[text.index('`bot_states` carries one `{bot_kind, state}` row') :][:900]

    assert rc.STATE_UNREGISTERED_KIND in enumeration
