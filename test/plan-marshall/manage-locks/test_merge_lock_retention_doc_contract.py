#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract pins for the merge-mutex proof and the queue-retention disclosure.

Three facts a reader of the planning corpus acts on, and the document SECTION that must
state each one:

* the merge dispatch refuses a caller that does not provably hold the cross-plan merge
  mutex (``manage-locks/SKILL.md`` § ``merge_lock — check`` and
  ``phase-6-finalize/standards/branch-cleanup.md`` § the pre-merge gate and its closed
  dispatch set);
* ``queue-list`` reports WHY admission keeps an entry, in a field beside ``liveness``
  (``manage-locks/SKILL.md`` § ``merge_lock — queue-list``);
* a retained entry has a named exit, and the abandoned-waiter sentence in
  ``branch-cleanup.md`` (§ Merge-Mutex Hold Window) states that field and that exit
  rather than only the hazard.

Each pin is a phrase the STATED section carries, not merely a phrase somewhere in the
file: a statement pinned document-wide would stay green after moving to a section that
does not state it. The negative control invents no check of its own — for every pinned
document it plants that document's OWN retired wording at the same site and asserts the
pin now reports the statement missing, so a pin that could never fail is caught here
rather than in a review.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import get_skill_dir

SKILL_MD = get_skill_dir('plan-marshall', 'manage-locks') / 'SKILL.md'
BRANCH_CLEANUP_MD = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'standards' / 'branch-cleanup.md'

#: Each pin: the document, the heading of the section that must state it, a phrase that
#: section carries, and the wording the document carried at that site BEFORE this change
#: (``None`` when the statement is wholly new at that site).
PINS: tuple[tuple[Path, str, str, str | None], ...] = (
    (
        SKILL_MD,
        '### merge_lock — check',
        '`pre_merge_gate merge` reads the merge-lock holder through `merge_lock.read_lock_holder`',
        None,
    ),
    (
        SKILL_MD,
        '### merge_lock — check',
        'A lock held by another plan, an absent lock and an unreadable lock file are three distinct refusals',
        None,
    ),
    (
        SKILL_MD,
        '### merge_lock — queue-list',
        'Each entry carries `position`, `plan_id`, `ts`, `liveness`, `retention` and `location`.',
        'Each entry carries `position`, `plan_id`, `ts`,\n`liveness` and `location`.',
    ),
    (
        SKILL_MD,
        '### merge_lock — queue-list',
        'names what KEEPS the entry in the queue',
        None,
    ),
    (
        BRANCH_CLEANUP_MD,
        '##### The dispatch set is CLOSED',
        'proves this plan holds the cross-plan merge mutex',
        'it evaluates the blocking-findings store and, only on a clean store, issues the verb its `--route` names.',
    ),
    (
        BRANCH_CLEANUP_MD,
        '#### Pre-merge blocking-findings store gate',
        'proves this plan holds the cross-plan merge mutex',
        None,
    ),
    (
        BRANCH_CLEANUP_MD,
        '#### Pre-merge blocking-findings store gate',
        'it is no longer the only net',
        None,
    ),
    (
        BRANCH_CLEANUP_MD,
        '## Merge-Mutex Hold Window (widened)',
        "`queue-list`'s `retention` field names the marker that keeps it",
        'because its plan directory still sits in its worktree the dead-waiter prune treats it as live and keeps the entry, so leaving it wedges every plan behind it.',
    ),
    (
        BRANCH_CLEANUP_MD,
        '## Merge-Mutex Hold Window (widened)',
        "the one named in the `not_fifo_front` reply's `queue_front.exit_command`",
        None,
    ),
)


def _section_text(text: str, heading: str) -> str:
    """Return ``text``'s section for ``heading``, up to the next same-or-higher heading.

    Fenced code blocks are skipped when looking for headings, so a ``#``-prefixed
    comment inside a fenced block cannot end the section early (which would redden a
    pin that is perfectly fine). An absent heading yields the empty string, which
    fails every pin anchored there — the fail-closed direction: a section that
    vanished states nothing.
    """
    target = heading.strip()
    level = len(target) - len(target.lstrip('#'))
    collected: list[str] = []
    inside = False
    in_fence = False
    for line in text.splitlines():
        stripped = line.lstrip()
        fenced = stripped.startswith('```')
        if not in_fence and not fenced and stripped == target:
            inside = True
            collected.append(line)
            continue
        if inside and not in_fence and not fenced and stripped.startswith('#'):
            marker_level = len(stripped) - len(stripped.lstrip('#'))
            if marker_level <= level and stripped[marker_level : marker_level + 1] == ' ':
                break
        if inside:
            collected.append(line)
        if fenced:
            in_fence = not in_fence
    return '\n'.join(collected)


def _pins_for(document: Path) -> tuple[tuple[Path, str, str, str | None], ...]:
    return tuple(pin for pin in PINS if pin[0] == document)


def _plant_in_section(text: str, heading: str, phrase: str, replacement: str) -> str:
    """Replace ``phrase`` INSIDE ``heading``'s section, leaving other sections alone.

    A phrase may be stated in more than one section; a document-wide replace would
    plant into whichever came first and leave the pinned section untouched, so the
    control would pass while proving nothing.
    """
    section = _section_text(text, heading)
    assert phrase in section, f'the pin {phrase!r} is not in {heading!r}, so nothing was planted'
    return text.replace(section, section.replace(phrase, replacement, 1), 1)


def _missing_pins(text: str, pins: tuple[tuple[Path, str, str, str | None], ...]) -> list[str]:
    """Return the pins ``text`` does not carry IN THE SECTION EACH NAMES."""
    missing: list[str] = []
    for _document, heading, phrase, _retired in pins:
        if phrase not in _section_text(text, heading):
            missing.append(f'{heading} :: {phrase}')
    return missing


def _assert_document_states(text: str, pins: tuple[tuple[Path, str, str, str | None], ...]) -> None:
    """Raise when ``text`` does not carry a pinned phrase in the section that states it."""
    missing = _missing_pins(text, pins)
    assert missing == [], 'the document no longer states: ' + '; '.join(repr(item) for item in missing)


@pytest.mark.parametrize('document', sorted({document for document, *_rest in PINS}, key=str))
def test_every_pin_holds_on_the_changed_document(document: Path) -> None:
    """The shipped document states each pinned fact in the section that owns it."""
    _assert_document_states(document.read_text(encoding='utf-8'), _pins_for(document))


@pytest.mark.parametrize('document', sorted({document for document, *_rest in PINS}, key=str))
def test_planting_the_retired_wording_reddens_that_document_s_pins(document: Path) -> None:
    """The control: plant the document's own old wording and the pins must fail.

    For every pinned statement the document carried before this change, the old
    sentence is substituted for the pinned one IN ITS OWN SECTION; where the statement
    is wholly new the planted copy is its absence. Either way the checker must report
    the pin missing — a pin that survived a plant would be asserting nothing.
    """
    pins = _pins_for(document)
    text = document.read_text(encoding='utf-8')
    plantable = [pin for pin in pins if pin[3] is not None]
    assert plantable, f'{document} carries no pinned statement with retired wording to plant'

    for _path, heading, phrase, retired in plantable:
        assert retired is not None
        assert retired not in text, (
            f'the retired wording is still present in {document}, so planting it would prove nothing: {retired!r}'
        )
        planted = _plant_in_section(text, heading, phrase, retired)
        assert phrase not in _section_text(planted, heading), (
            f'the plant did not remove {phrase!r} from {heading!r}, so the control proves nothing'
        )
        with pytest.raises(AssertionError):
            _assert_document_states(planted, pins)


@pytest.mark.parametrize('document', sorted({document for document, *_rest in PINS}, key=str))
def test_planting_an_absence_reddens_a_wholly_new_statement(document: Path) -> None:
    """A statement this change introduced is pinned too: deleting it must redden."""
    pins = _pins_for(document)
    text = document.read_text(encoding='utf-8')

    for _path, heading, phrase, _retired in pins:
        planted = _plant_in_section(text, heading, phrase, '')
        with pytest.raises(AssertionError):
            _assert_document_states(planted, pins)


def test_section_extraction_ignores_a_hash_comment_inside_a_fenced_block() -> None:
    """A ``#`` line inside a fence is text, not a heading — it cannot end a section.

    Without this the extractor would treat a shell comment as a heading and truncate
    the section, reddening a pin whose statement is intact.
    """
    text = '\n'.join(
        [
            '## Target',
            'before',
            '```bash',
            '# not a heading',
            'echo after',
            '```',
            'after the fence',
            '## Next',
            'elsewhere',
        ]
    )

    section = _section_text(text, '## Target')

    assert 'after the fence' in section
    assert 'elsewhere' not in section


def test_every_pinned_section_exists_in_its_document() -> None:
    """Anti-vacuity: each pinned heading is a real heading, and both documents are pinned.

    Without this, a renamed heading would silently empty a section and every pin
    anchored there would fail as ``missing`` — correct, but the cause would be opaque.
    """
    per_document: dict[Path, list[str]] = {}
    for document, heading, _phrase, _retired in PINS:
        per_document.setdefault(document, []).append(heading)
    assert set(per_document) == {SKILL_MD, BRANCH_CLEANUP_MD}

    for document, headings in per_document.items():
        text = document.read_text(encoding='utf-8')
        for heading in headings:
            assert _section_text(text, heading), f'{document} has no section {heading!r}'
        assert len(headings) >= 2, per_document
