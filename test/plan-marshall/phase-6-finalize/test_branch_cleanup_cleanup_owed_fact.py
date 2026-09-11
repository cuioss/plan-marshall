#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Guard: every terminal ``branch-cleanup`` call site records the ``cleanup_owed`` fact.

``branch-cleanup``'s Branch F2 (the merge queue dequeued the PR) records
``merge_state=closed`` — a fully-readable value — so before ``cleanup_owed``
existed its owed cleanup lived only in a ``display_detail`` string no consumer
routes on, and the landing read complete and clean. The fact is the structured
carrier; this module pins that it is wired where the ruling says it is.

The population is DERIVED from ``branch-cleanup.md`` § "Mark Step Complete": every
labelled branch block carrying a ``mark-step-done`` call is a terminal call site.
The count is published and asserted against the expected branch set in BOTH
directions, so a parser that matched nothing, or a branch added without a ruled
value, can never read as a clean pass.

Each detector is a pure function over document text, and each is pinned by a
mutation control: a fabricated pre-fix input fed to the SAME detector must be
reported as an offender, so a refactor that leaves the guard green over a defect
it no longer detects turns the build red.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT

_BRANCH_CLEANUP_DOC: Path = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards' / 'branch-cleanup.md'
)

#: The ruled ``cleanup_owed`` value at every terminal call site: ``false`` where the
#: cleanup was completed or there was nothing to clean up, ``true`` where it is left
#: owed. Stated as literals rather than derived from the document, so the document
#: cannot drift together with its own guard.
_EXPECTED_CLEANUP_OWED: dict[str, str] = {
    'Branch A': 'false',
    'Branch B': 'false',
    'Branch C': 'true',
    'Branch D': 'false',
    'Branch E': 'false',
    'F1': 'true',
    'F2': 'true',
    'F3': 'true',
}

#: The undifferentiated claim the closing note made before the fact existed: it
#: credited the landing with carrying F2's owed cleanup when nothing carried it.
_PRE_FIX_CLOSING_CLAIM = 'carry the owed cleanup in the landing'

_MARK_STEP_SECTION = re.compile(r'^## Mark Step Complete$(.*?)(?=^## |\Z)', re.MULTILINE | re.DOTALL)
_BRANCH_LABEL = re.compile(r'^\*\*(Branch [A-Z]|F\d) — ', re.MULTILINE)
_BASH_BLOCK = re.compile(r'```bash\n(.*?)```', re.DOTALL)
_FACT = re.compile(r'--fact\s+([a-z_]+)=([^\s\\}]+)')
_CLOSING_NOTE = re.compile(
    r'^\*\*Why F1 loops back and F2/F3 do not\.\*\*(.*?)(?=^⚠ |\Z)',
    re.MULTILINE | re.DOTALL,
)


# --------------------------------------------------------------------------- #
# Pure detectors
# --------------------------------------------------------------------------- #


def _mark_step_section(text: str) -> str:
    match = _MARK_STEP_SECTION.search(text)
    assert match, 'branch-cleanup.md carries no "## Mark Step Complete" section'
    return match.group(1)


def terminal_call_sites(section: str) -> dict[str, dict[str, str]]:
    """Map each labelled branch that issues ``mark-step-done`` to the facts it records.

    A label's segment runs to the next label. A segment with no ``mark-step-done``
    block (Branch F's overview, which only introduces F1/F2/F3) is not a terminal
    call site and is left out.
    """
    labels = list(_BRANCH_LABEL.finditer(section))
    sites: dict[str, dict[str, str]] = {}
    for index, label in enumerate(labels):
        end = labels[index + 1].start() if index + 1 < len(labels) else len(section)
        segment = section[label.end() : end]
        blocks = [block for block in _BASH_BLOCK.findall(segment) if 'mark-step-done' in block]
        if not blocks:
            continue
        sites[label.group(1)] = {key: value for block in blocks for key, value in _FACT.findall(block)}
    return sites


def sites_missing_cleanup_owed(sites: dict[str, dict[str, str]]) -> list[str]:
    """The terminal call sites that record no ``cleanup_owed`` fact."""
    return sorted(label for label, facts in sites.items() if 'cleanup_owed' not in facts)


def sites_with_wrong_cleanup_owed(sites: dict[str, dict[str, str]]) -> list[str]:
    """The terminal call sites whose ``cleanup_owed`` value departs from the ruling."""
    return sorted(
        label
        for label, facts in sites.items()
        if label in _EXPECTED_CLEANUP_OWED and facts.get('cleanup_owed') != _EXPECTED_CLEANUP_OWED[label]
    )


def closing_note_offends(note: str) -> bool:
    """Whether the closing note fails to name the carrier or keeps the old claim."""
    return 'cleanup_owed' not in note or _PRE_FIX_CLOSING_CLAIM in note


def _closing_note(text: str) -> str:
    match = _CLOSING_NOTE.search(text)
    assert match, 'branch-cleanup.md carries no "Why F1 loops back and F2/F3 do not." note'
    return match.group(1)


def _document_sites() -> dict[str, dict[str, str]]:
    return terminal_call_sites(_mark_step_section(_BRANCH_CLEANUP_DOC.read_text(encoding='utf-8')))


# --------------------------------------------------------------------------- #
# The population
# --------------------------------------------------------------------------- #


def test_the_terminal_call_site_population_is_the_ruled_branch_set():
    """Published and non-empty, and equal to the ruled set in both directions.

    A missing label means the parser stopped seeing a branch; an extra one means
    a branch was added without a ruled ``cleanup_owed`` value.
    """
    sites = _document_sites()

    assert len(sites) > 0, 'the parser found no terminal call site, so every assertion would pass vacuously'
    assert len(sites) == len(_EXPECTED_CLEANUP_OWED), f'parsed {len(sites)} terminal call sites: {sorted(sites)}'
    assert set(sites) == set(_EXPECTED_CLEANUP_OWED)


# --------------------------------------------------------------------------- #
# (a) every terminal call site records the fact
# --------------------------------------------------------------------------- #


def test_every_terminal_call_site_records_cleanup_owed():
    assert sites_missing_cleanup_owed(_document_sites()) == []


def test_mutation_pin_a_pre_fix_f2_block_is_reported_missing():
    """The pre-fix F2 block — no ``cleanup_owed`` line — must be reported."""
    pre_fix = (
        '**F2 — dequeued without merging** (`state == closed`).\n\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \\\n'
        '  --plan-id {plan_id} --phase 6-finalize --step branch-cleanup --outcome done \\\n'
        '  --fact merge_state=closed \\\n'
        '  --fact work_performed=true \\\n'
        '  --display-detail "dequeued without merging, cleanup owed"\n'
        '```\n'
    )

    sites = terminal_call_sites(pre_fix)

    assert set(sites) == {'F2'}, 'the fabricated block was not parsed, so the pin proves nothing'
    assert sites_missing_cleanup_owed(sites) == ['F2']


# --------------------------------------------------------------------------- #
# (b) the owed branches record true, (c) the completed ones record false
# --------------------------------------------------------------------------- #


def test_the_owed_branches_record_true():
    """F2 — the branch that had no structured carrier — and F1, F3 and C record ``true``."""
    sites = _document_sites()

    for label in ('F2', 'F1', 'F3', 'Branch C'):
        assert sites[label].get('cleanup_owed') == 'true', f'{label}: {sites[label]}'


def test_the_completed_branches_record_false():
    """A, B, D and E record ``false``, so both carriers are exercised.

    Without this half a single constant ``true`` wired everywhere would satisfy
    every presence assertion above.
    """
    sites = _document_sites()

    for label in ('Branch A', 'Branch B', 'Branch D', 'Branch E'):
        assert sites[label].get('cleanup_owed') == 'false', f'{label}: {sites[label]}'
    assert {facts['cleanup_owed'] for facts in sites.values()} == {'true', 'false'}


def test_every_terminal_call_site_matches_the_ruling():
    assert sites_with_wrong_cleanup_owed(_document_sites()) == []


def test_mutation_pin_an_all_true_fact_set_is_reported():
    """A single constant ``true`` wired at every site must be reported at the completed branches."""
    all_true = {label: {'cleanup_owed': 'true'} for label in _EXPECTED_CLEANUP_OWED}

    assert sites_with_wrong_cleanup_owed(all_true) == ['Branch A', 'Branch B', 'Branch D', 'Branch E']


# --------------------------------------------------------------------------- #
# (d) the closing note names the carrier, and the F2 block agrees with it
# --------------------------------------------------------------------------- #


def test_the_closing_note_names_cleanup_owed_and_drops_the_old_claim():
    assert not closing_note_offends(_closing_note(_BRANCH_CLEANUP_DOC.read_text(encoding='utf-8')))


def test_the_f2_block_names_the_same_carrier_as_the_closing_note():
    """The F2 block and the closing note make the same claim, so the two sites cannot disagree."""
    section = _mark_step_section(_BRANCH_CLEANUP_DOC.read_text(encoding='utf-8'))
    f2 = re.search(r'^\*\*F2 — (.*?)(?=^\*\*F3 — )', section, re.MULTILINE | re.DOTALL)

    assert f2, 'the F2 block was not found'
    prose = _BASH_BLOCK.sub('', f2.group(1))
    assert 'cleanup_owed=true' in prose, 'the F2 prose does not name the structured carrier of its owed cleanup'


def test_mutation_pin_the_pre_fix_closing_note_is_reported():
    """The pre-fix closing sentence — the undifferentiated claim — must be reported."""
    pre_fix_note = (
        ' F2 and F3 also leave cleanup owed, but re-running cannot discharge it. They terminate '
        'with an honest `merge_state` and carry the owed cleanup in the landing.'
    )

    assert closing_note_offends(pre_fix_note)
