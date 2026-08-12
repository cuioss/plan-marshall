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
  derived region instructs an unconditional discard, and no "always safe"
  justification survives.
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

#: The pre-fix destructive form: a ``Recovery:`` directive line whose command is
#: an unconditional discard of the operator's file.
_UNCONDITIONAL_DISCARD = re.compile(r'Recovery:\s*git checkout -- \.plan/marshal\.json')


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
    before any discard, and carries neither destructive signature."""
    low = text.lower()
    return (
        ('inspect' in low or 'git diff' in low)
        and 'operator' in low
        and ('disposition' in low or 'confirm' in low or 'decide' in low)
        and not _has_unconditional_discard_directive(text)
        and not _has_always_safety_claim(text)
    )


def _is_authority(text: str) -> bool:
    """Only the single authority carries the concrete inspection command that
    surfaces the diff. The reference sites point to it rather than restate it."""
    return 'git diff -- .plan/marshal.json' in text


def _references_authority(text: str) -> bool:
    low = text.lower()
    return 'planning.md' in low and 'named recovery' in low


def test_named_recovery_never_instructs_unconditional_discard():
    """D3(a): no derived named-recovery region instructs an unconditional discard,
    and no "always safe" justification survives."""
    regions = _derive_named_recovery_regions()
    assert regions, (
        'assertion-shape sweep for the named `.plan/marshal.json` recovery case '
        'matched nothing — the contract moved or the derivation is vacuous'
    )
    offenders: list[str] = []
    for path, block, lineno in regions:
        if _has_unconditional_discard_directive(block):
            offenders.append(f'{path.name}:{lineno} — unconditional `git checkout --` recovery directive')
        if _has_always_safety_claim(block):
            offenders.append(f'{path.name}:{lineno} — "always safe"/"always a spurious" justification')
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
