#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the named `.plan/marshal.json` recovery case in the planning workflow docs.

Plan ``truthful-signals/210-named-recovery-discards-operator-config``.

Three workflow-doc blocks instructed the orchestrator, when a post-dispatch
clean-main assertion reports ``.plan/marshal.json`` dirty, to emit
``Recovery: git checkout -- .plan/marshal.json`` — justified by the claim that
restoring the file from HEAD "is always safe". The justification is a non
sequitur: the clean-main guard establishes only that *the dispatched phase* did
not write the file, not that nobody did. The likeliest author of a dirty
``marshal.json`` in the main checkout is the **operator**, and ``git checkout --``
destroys uncommitted, unstaged edits irrecoverably (no reflog covers a worktree
file). The recovery must instead inspect the diff and require an explicit
operator disposition before any discard.

These tests assert the *derivation* of the assertion class, not a hard-coded
enumeration of the three known sites — pinning only the known sites would
re-create the sample-as-population error this plan exists to prevent. The
population is derived by **assertion shape** (the named-recovery heading for
``.plan/marshal.json``) swept across every workflow doc, so a new phase boundary
that adds such a block is covered automatically.

Test-to-deliverable map:

* ``test_named_recovery_never_instructs_unconditional_discard`` — D3(a): no
  derived region instructs an unconditional discard, EVERY derived region is
  inspection-first, and no "always safe" justification survives.
* ``test_named_recovery_inspection_first_population_nonempty_and_covers_known_members``
  — D3(b): the derived population of inspection-first sites is asserted
  non-empty and covers the known members (planning.md + both
  planning-outline.md boundaries). A non-vacuous control proves the sweep
  examined a populated surface, so the non-empty assertion cannot pass on an
  empty sweep.
* ``test_named_recovery_contract_is_a_single_authority`` — D2: the contract
  exists as ONE authority the other sites reference, not as three drifting
  copies.
"""

from __future__ import annotations

import re

from conftest import MARKETPLACE_ROOT

WORKFLOW_DIR = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow'
)

#: The stable assertion-shape identifier for a named-recovery site. Derivation
#: keys on this heading, not on a command string — the command is exactly the
#: thing the fix removes, so a command-string sweep would report the class
#: "closed" the moment the fix lands.
HEADING_MARKER = 'Named recovery case — `.plan/marshal.json`'

#: The region owned by one named-recovery contract ends at the next unrelated
#: bold directive or markdown heading. The region deliberately extends past the
#: recovery block through its ``**Cross-references**`` sub-section, so an
#: "always"-flavoured justification in a cross-reference bullet is in scope too.
_REGION_BOUNDARY = re.compile(r'^(#{2,6}\s|\*\*Metrics\*\*|\*\*Phase handshake|\*\*Step\s)')

#: The destructive form: any ``git checkout``/``git restore`` aimed at the
#: operator's file, under ANY lead-in. The former pattern required a literal
#: ``Recovery:`` prefix, so a block that issued the same command under different
#: wording carried the identical hazard and matched nothing.
_UNCONDITIONAL_DISCARD = re.compile(r'git (?:checkout|restore)\b[^\n`]*\.plan/marshal\.json')

#: Any concrete ``git diff`` inspection command aimed at ``.plan/marshal.json``.
#: Widened from the single literal ``git diff -- .plan/marshal.json`` so a
#: restatement cannot evade the single-authority test merely by dropping the
#: ``--`` separator or adding an option. ``[^\n`]*`` keeps the match inside one
#: contiguous command span, so prose that merely names ``git diff`` in one code
#: span and the path in another does not read as an inspection command.
_INSPECTION_COMMAND = re.compile(r'git diff\b[^\n`]*\.plan/marshal\.json')

#: The cross-reference that points at the single authority — accepted as a
#: ``- `` bullet or as an inline ``§`` citation, since both are pointers.
_AUTHORITY_POINTER = re.compile(
    r'`plan-marshall:plan-marshall/workflow/planning\.md`\s*§\s*"Named recovery case'
)

#: The operator-disposition enumeration that only the authority may carry.
#: Keyed on BOTH dispositions appearing as list items: naming the operator's two
#: choices IS the contract, so a site carrying both has restated it.
_DISPOSITION_KEEP = re.compile(r'^\s*[-*]\s+\**Keep\**\s*[—:-]', re.MULTILINE)
_DISPOSITION_DISCARD = re.compile(r'^\s*[-*]\s+\**Discard\**\s*[—:-]', re.MULTILINE)


def _derive_named_recovery_regions() -> list[tuple]:
    """Sweep every workflow doc for named ``.plan/marshal.json`` recovery blocks.

    Returns a list of ``(path, region_text, heading_lineno)`` — the derived
    population. Empty return is a real signal (the class moved or vanished),
    never silently treated as "clean".
    """
    regions: list[tuple] = []
    for md in sorted(WORKFLOW_DIR.glob('*.md')):
        lines = md.read_text(encoding='utf-8').splitlines()
        for i, line in enumerate(lines):
            if HEADING_MARKER in line and line.lstrip().startswith('**Named recovery case'):
                block = [line]
                for j in range(i + 1, min(i + 40, len(lines))):
                    if _REGION_BOUNDARY.match(lines[j]):
                        break
                    block.append(lines[j])
                regions.append((md, '\n'.join(block), i + 1))
    return regions


def _has_unconditional_discard_directive(text: str) -> bool:
    return bool(_UNCONDITIONAL_DISCARD.search(text))


def _has_always_safety_claim(text: str) -> bool:
    low = text.lower()
    return 'always safe' in low or 'always a spurious' in low


def _is_inspection_first(text: str) -> bool:
    """A region that mandates inspection and an explicit operator disposition
    before any discard, and carries no "always safe" justification.

    The destructive-command signature is deliberately NOT part of this test.
    Once ``_UNCONDITIONAL_DISCARD`` was broadened to match the command under any
    lead-in it also matches the authority's own *cautionary* mention ("...would
    destroy those edits irrecoverably"), so folding it in here would make the
    property unsatisfiable for the one region that states the contract. The two
    are combined at the offender rule instead: carrying the command is an
    offence only where the region does not also mandate inspection-then-
    disposition.
    """
    low = text.lower()
    return (
        ('inspect' in low or 'git diff' in low)
        and 'operator' in low
        and ('disposition' in low or 'confirm' in low or 'decide' in low)
        and not _has_always_safety_claim(text)
    )


def _is_authority(text: str) -> bool:
    """Only the single authority carries a concrete ``git diff`` inspection
    command against ``marshal.json``. The reference sites point to it instead."""
    return bool(_INSPECTION_COMMAND.search(text))


def _restates_contract(text: str) -> bool:
    """Whether ``text`` carries the operator-disposition enumeration.

    Structural by design rather than a line or character budget: a budget needs
    a threshold nobody can settle, and drifts as the prose is edited. Carrying
    both ``Keep`` and ``Discard`` as list items IS the contract.
    """
    return bool(_DISPOSITION_KEEP.search(text)) and bool(_DISPOSITION_DISCARD.search(text))


def _references_authority(text: str) -> bool:
    """Whether a non-authority region DEFERS to the authority rather than restating it.

    Replaces the former ``'planning.md' in low and 'named recovery' in low``
    heuristic, which a full restatement satisfies just as easily as a pointer:
    the region heading makes the second term true by construction, and any
    restatement that names its source makes the first true. Deference is now
    two-sided — an explicit pointer to the authority section MUST be present,
    and the operator-disposition enumeration MUST NOT.
    """
    return bool(_AUTHORITY_POINTER.search(text)) and not _restates_contract(text)


def test_named_recovery_never_instructs_unconditional_discard():
    """No derived named-recovery region instructs an unconditional discard, EVERY
    region is inspection-first, and no "always safe" justification survives.

    The universal inspection-first assertion is what makes the population-derived
    sweep worth deriving: the two literal signatures alone pass any reworded site
    that avoids their exact wording, so a fourth destructive block was invisible
    to a test that swept every region."""
    regions = _derive_named_recovery_regions()
    assert regions, (
        'assertion-shape sweep for the named `.plan/marshal.json` recovery case '
        'matched nothing — the contract moved or the derivation is vacuous'
    )
    offenders: list[str] = []
    for path, block, lineno in regions:
        # Literal-signature floor, retained as an additional check.
        if _has_always_safety_claim(block):
            offenders.append(f'{path.name}:{lineno} — "always safe"/"always a spurious" justification')
        # UNIVERSAL assertion: every derived region — not merely the three
        # already-known members — must mandate inspection then an explicit
        # operator disposition. A reworded site that carries the cross-reference
        # bullet and avoids the "always safe" phrasing clears every literal
        # signature and is caught only here.
        if not _is_inspection_first(block):
            if _has_unconditional_discard_directive(block):
                offenders.append(
                    f'{path.name}:{lineno} — `git checkout`/`git restore` against '
                    'marshal.json with no inspection-then-disposition mandate'
                )
            else:
                offenders.append(
                    f'{path.name}:{lineno} — not inspection-first (needs inspection '
                    'plus an explicit operator disposition)'
                )
    assert not offenders, (
        'destructive named-recovery text survives (a dirty `marshal.json` is most '
        'likely uncommitted operator config, and `git checkout --` destroys it '
        'irrecoverably):\n  ' + '\n  '.join(offenders)
    )


def test_named_recovery_inspection_first_population_nonempty_and_covers_known_members():
    """D3(b): the derived population of inspection-first named-recovery sites is
    non-empty and covers the known members.

    The plain sweep is the non-vacuous control — it proves the derivation
    examined a populated surface, so the non-empty assertion below cannot be
    satisfied by an empty sweep (a matched-nothing sweep looks identical to a
    clean tree, which is exactly the confusion this epic is named for)."""
    regions = _derive_named_recovery_regions()
    # Non-vacuous control: the surface is populated.
    assert regions, (
        'assertion-shape sweep matched nothing — cannot distinguish a fixed class '
        'from a vanished one'
    )
    known_files = {path.name for path, _, _ in regions}
    assert 'planning.md' in known_files
    assert 'planning-outline.md' in known_files
    assert sum(1 for path, _, _ in regions if path.name == 'planning-outline.md') >= 2, (
        'planning-outline.md must carry the named-recovery case at both the '
        'outline and plan phase boundaries'
    )

    # The derived population of correctly-handled sites — asserted non-empty.
    inspection_first = [(path, block) for path, block, _ in regions if _is_inspection_first(block)]
    assert inspection_first, (
        'no named-recovery site mandates inspection-before-discard with an '
        'explicit operator disposition — the class is unfixed'
    )
    covered = {path.name for path, _ in inspection_first}
    assert 'planning.md' in covered
    assert 'planning-outline.md' in covered
    assert sum(1 for path, _ in inspection_first if path.name == 'planning-outline.md') >= 2, (
        'both planning-outline.md boundaries must handle the recovery inspection-first'
    )


def test_named_recovery_contract_is_a_single_authority():
    """D2: the named-recovery contract is ONE authority the other sites reference,
    not three near-identical copies (which drift, as this triplet already did)."""
    regions = _derive_named_recovery_regions()
    assert regions, 'assertion-shape sweep matched nothing'
    authorities = [(path, block) for path, block, _ in regions if _is_authority(block)]
    assert len(authorities) == 1, (
        'expected exactly ONE named-recovery authority (the block carrying the '
        f'concrete inspection command); found {len(authorities)}: '
        f'{[path.name for path, _ in authorities]} — collapse the copies to a '
        'single authority the sites reference, do not synchronise them'
    )
    _, authority_block = authorities[0]
    for path, block, lineno in regions:
        if block == authority_block:
            continue
        assert _references_authority(block), (
            f'{path.name}:{lineno} restates the named-recovery contract instead of '
            'referencing the single authority — where a copy exists, delete the '
            'copy (do not synchronise it)'
        )
