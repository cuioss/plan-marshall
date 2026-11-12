#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract pins for the merge-mutex proof and the queue-retention disclosure.

Three facts a reader of the planning corpus acts on, and the documents that must state
each one where the behaviour lives:

* the merge dispatch refuses a caller that does not provably hold the cross-plan merge
  mutex (``manage-locks/SKILL.md`` § ``merge_lock — check`` and
  ``phase-6-finalize/standards/branch-cleanup.md`` § the pre-merge gate);
* ``queue-list`` reports WHY admission keeps an entry, in a field beside ``liveness``
  (``manage-locks/SKILL.md`` § ``merge_lock — queue-list``);
* a retained entry has a named exit, and the abandoned-waiter sentence in
  ``branch-cleanup.md`` states that field and that exit rather than only the hazard.

Each pin is a phrase the stating section carries. The negative control does not invent
a check of its own: for every pinned document it plants the document's OWN retired
wording at the same site and asserts the pin list now reports the statement missing, so
a pin that could never fail is caught here rather than in a review.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import get_skill_dir

SKILL_MD = get_skill_dir('plan-marshall', 'manage-locks') / 'SKILL.md'
BRANCH_CLEANUP_MD = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'standards' / 'branch-cleanup.md'

#: Each pin: the document, a phrase the stating section carries, and the wording the
#: document carried at that site BEFORE this change (``None`` when the statement is
#: wholly new, in which case the planted "old sentence" is the sentence's absence).
PINS: tuple[tuple[Path, str, str | None], ...] = (
    (
        SKILL_MD,
        '`pre_merge_gate merge` reads the merge-lock holder through `merge_lock.read_lock_holder`',
        None,
    ),
    (
        SKILL_MD,
        'A lock held by another plan, an absent lock and an unreadable lock file are three distinct refusals',
        None,
    ),
    (
        SKILL_MD,
        'Each entry carries `position`, `plan_id`, `ts`, `liveness`, `retention` and `location`.',
        'Each entry carries `position`, `plan_id`, `ts`,\n`liveness` and `location`.',
    ),
    (
        SKILL_MD,
        'names what KEEPS the entry in the queue',
        None,
    ),
    (
        BRANCH_CLEANUP_MD,
        'proves this plan holds the cross-plan merge mutex',
        'it evaluates the blocking-findings store and, only on a clean store, issues the verb its `--route` names.',
    ),
    (
        BRANCH_CLEANUP_MD,
        'it is no longer the only net',
        None,
    ),
    (
        BRANCH_CLEANUP_MD,
        "`queue-list`'s `retention` field names the marker that keeps it",
        'because its plan directory still sits in its worktree the dead-waiter prune treats it as live and keeps the entry, so leaving it wedges every plan behind it.',
    ),
    (
        BRANCH_CLEANUP_MD,
        "the one named in the `not_fifo_front` reply's `queue_front.exit_command`",
        None,
    ),
)


def _missing_pins(text: str, pins: tuple[tuple[Path, str, str | None], ...]) -> list[str]:
    """Return the pins ``text`` does not carry, in declaration order."""
    return [phrase for _document, phrase, _retired in pins if phrase not in text]


def _assert_document_states(text: str, pins: tuple[tuple[Path, str, str | None], ...]) -> None:
    """Raise when ``text`` does not carry every pinned phrase."""
    missing = _missing_pins(text, pins)
    assert missing == [], 'the document no longer states: ' + '; '.join(repr(m) for m in missing)


@pytest.mark.parametrize('document', sorted({document for document, _phrase, _retired in PINS}, key=str))
def test_every_pin_holds_on_the_changed_document(document: Path) -> None:
    """The shipped document states each pinned fact."""
    pins = tuple((path, phrase, retired) for path, phrase, retired in PINS if path == document)

    _assert_document_states(document.read_text(encoding='utf-8'), pins)


@pytest.mark.parametrize('document', sorted({document for document, _phrase, _retired in PINS}, key=str))
def test_planting_the_retired_wording_reddens_that_document_s_pins(document: Path) -> None:
    """The control: plant the document's own old wording and the pins must fail.

    For every pinned statement the document carried before this change, the old
    sentence is substituted for the pinned one; where the statement is wholly new the
    planted copy is its absence. Either way the checker must report the pin missing —
    a pin that survived a plant would be asserting nothing.
    """
    pins = tuple((path, phrase, retired) for path, phrase, retired in PINS if path == document)
    text = document.read_text(encoding='utf-8')
    plantable = [pin for pin in pins if pin[2] is not None]
    assert plantable, f'{document} carries no pinned statement with retired wording to plant'

    for _path, phrase, retired in plantable:
        assert retired is not None
        assert retired not in text, (
            f'the retired wording is still present in {document}, so planting it would prove nothing: {retired!r}'
        )
        planted = text.replace(phrase, retired)
        assert planted != text, f'the pin {phrase!r} was not found in {document}, so nothing was planted'
        with pytest.raises(AssertionError):
            _assert_document_states(planted, pins)


@pytest.mark.parametrize('document', sorted({document for document, _phrase, _retired in PINS}, key=str))
def test_planting_an_absence_reddens_a_wholly_new_statement(document: Path) -> None:
    """A statement this change introduced is pinned too: deleting it must redden."""
    pins = tuple(pin for pin in PINS if pin[0] == document)
    text = document.read_text(encoding='utf-8')

    for _path, phrase, _retired in pins:
        planted = text.replace(phrase, '')
        assert planted != text
        with pytest.raises(AssertionError):
            _assert_document_states(planted, pins)


def test_the_pin_census_covers_both_documents() -> None:
    """Anti-vacuity: both documents are pinned, and each by more than one statement."""
    per_document: dict[Path, int] = {}
    for document, _phrase, _retired in PINS:
        per_document[document] = per_document.get(document, 0) + 1

    assert set(per_document) == {SKILL_MD, BRANCH_CLEANUP_MD}
    assert all(count >= 2 for count in per_document.values()), per_document
