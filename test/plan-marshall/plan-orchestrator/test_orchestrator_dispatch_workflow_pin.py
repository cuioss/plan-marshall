#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pin the ``--workflow`` argument across every orchestrator dispatch doc site.

``--workflow`` is not decoration on the ``effort resolve-target`` call: it is what
makes the resolve seam emit the ``[DISPATCH]`` work-log line and its paired
decision-log record. A site that resolves a dispatch level with a bare ``--role``
still dispatches, still resolves the right tier, and leaves NO trail — the
failure is invisible at the point it happens and only shows up later as a
dispatch nobody can account for.

The guard is deliberately **population-derived**: it enumerates the orchestrator
dispatch resolve invocations out of the documents themselves and asserts the flag
over whatever it found, rather than checking a hard-coded list of three known
sites. A hard-coded list cannot notice a FOURTH site added later without the
flag — which is precisely the drift this pin exists to catch.

Because a population-derived guard can pass by finding nothing, every assertion
here publishes the evidence it was computed over (the population size and the
matched sites), and ``test_the_enumerator_is_not_vacuous`` pins the population as
non-empty — mirroring ``test_landing_completeness.py``'s
``test_the_extractors_are_not_vacuous``. A guard that can return 0 from an empty
population MUST publish that population size, or a green proves only that the
enumerator ran.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT

_PLAN_MARSHALL = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'

#: Every document that carries an orchestrator dispatch resolve invocation. This
#: is the SEARCH SURFACE, not the expected answer: how many invocations each file
#: holds is derived below, never asserted from a constant here.
_DISPATCH_DOCS: tuple[Path, ...] = (
    _PLAN_MARSHALL / 'plan-orchestrator' / 'workflow' / 'analyze.md',
    _PLAN_MARSHALL / 'plan-orchestrator' / 'workflow' / 'decompose.md',
    _PLAN_MARSHALL / 'persona-plan-orchestrator' / 'standards' / 'orchestration-model.md',
)

#: One orchestrator dispatch resolve invocation. The two workflow docs carry the
#: call inline in prose and the standards doc carries it in a fenced block with
#: backslash continuations, so the scan runs over whitespace-normalized text and
#: stops at the end of the invocation rather than assuming a single line.
#:
#: The surface segment admits BOTH spellings the docs use: a concrete surface
#: (``orchestrator.analyze``) at the two call sites, and the ``{surface}``
#: placeholder in the standards doc's canonical form. Matching only the concrete
#: spelling silently drops the canonical form — the one site a reader copies
#: from — and the pin then passes while speaking for two of the three documents.
_INVOCATION_RE = re.compile(
    r'effort resolve-target --role orchestrator\.(?:[a-z-]+|\{[a-z_]+\})[^`\n]*'
)

#: A resolve invocation ends at the first backtick (prose form) or at the end of
#: the fenced command (standards form). Both are covered by normalizing the
#: continuation backslashes away before the scan.
_CONTINUATION_RE = re.compile(r'\\\s*\n\s*')


def _invocations(path: Path) -> list[str]:
    """Every orchestrator dispatch resolve invocation in one document."""
    text = _CONTINUATION_RE.sub(' ', path.read_text(encoding='utf-8'))
    return [match.group(0) for match in _INVOCATION_RE.finditer(text)]


def _population() -> list[tuple[Path, str]]:
    """The (document, invocation) population the assertions below run over."""
    found: list[tuple[Path, str]] = []
    for doc in _DISPATCH_DOCS:
        found.extend((doc, invocation) for invocation in _invocations(doc))
    return found


class TestDispatchResolveSitesCarryWorkflow:
    def test_every_dispatch_doc_exists(self):
        # The enumerator reads these files; a renamed doc would otherwise shrink
        # the population silently and the pin would pass over the remainder.
        missing = [doc for doc in _DISPATCH_DOCS if not doc.is_file()]

        assert not missing, (
            f'{len(missing)} of {len(_DISPATCH_DOCS)} dispatch document(s) are missing, so '
            'the enumeration below runs over a shrunken surface: '
            f'{[str(doc) for doc in missing]}'
        )

    def test_the_enumerator_is_not_vacuous(self):
        """The enumerator must find something, or the pin below proves nothing."""
        population = _population()

        assert population, (
            'The orchestrator dispatch resolve enumerator matched NO invocation across '
            f'{len(_DISPATCH_DOCS)} document(s): '
            f'{[doc.name for doc in _DISPATCH_DOCS]}. Every assertion in this module would '
            'pass vacuously, so the pin is reported as broken rather than green.'
        )

    def test_the_enumerator_finds_an_invocation_in_every_dispatch_doc(self):
        # Per-document floor: the whole-population count above can stay non-zero
        # while one document contributes nothing, which would let that document
        # drop its flag unnoticed.
        empty = [doc.name for doc in _DISPATCH_DOCS if not _invocations(doc)]

        assert not empty, (
            f'{len(empty)} dispatch document(s) contributed no invocation to the '
            f'population: {empty}. The pin cannot speak for a document it matched '
            'nothing in.'
        )

    def test_every_enumerated_invocation_carries_the_workflow_argument(self):
        population = _population()
        missing = [(doc.name, text) for doc, text in population if '--workflow' not in text]

        assert not missing, (
            f'{len(missing)} of {len(population)} enumerated orchestrator dispatch resolve '
            'invocation(s) omit `--workflow`. The flag is what makes the resolve seam emit '
            'the [DISPATCH] line and its paired decision-log record, so each of these '
            f'dispatches would leave no trail at all: {missing}'
        )

    def test_the_population_is_reported_with_its_matched_sites(self):
        # The evidence assertion: the count is only meaningful beside the sites it
        # was computed from, so both are asserted together.
        population = _population()
        sites = sorted({doc.name for doc, _ in population})

        assert len(population) >= len(_DISPATCH_DOCS), (
            f'{len(population)} invocation(s) enumerated across {len(sites)} document(s) '
            f'{sites}, which is fewer than the {len(_DISPATCH_DOCS)} documents searched — '
            'at least one document contributed nothing.'
        )

    def test_a_document_set_with_no_dispatch_invocation_yields_an_empty_population(
        self, tmp_path
    ):
        # Matched negative control for the anti-vacuity guard: pointed at a
        # document carrying no dispatch invocation, the enumerator must return
        # empty rather than matching something incidental. Without this, a
        # too-greedy pattern could make every population look healthy.
        decoy = tmp_path / 'no-dispatch.md'
        decoy.write_text(
            '# Not a dispatch doc\n\n'
            'This document mentions effort and roles and even orchestrator.analyze, '
            'but issues no `effort resolve-target` invocation at all.\n',
            encoding='utf-8',
        )

        assert _invocations(decoy) == []

    def test_an_invocation_without_the_flag_is_detected(self, tmp_path):
        # Matched positive control for the DETECTOR itself: the assertion above
        # reports green over the real tree, so this proves that green is a
        # measured pass rather than a detector that cannot fail.
        offender = tmp_path / 'offender.md'
        offender.write_text(
            'The level is resolved via `effort resolve-target --role orchestrator.analyze '
            '--plan-id none --caller plan-marshall:persona-plan-orchestrator` here.\n',
            encoding='utf-8',
        )

        found = _invocations(offender)

        assert len(found) == 1, f'the enumerator matched {len(found)} invocation(s), expected 1'
        assert '--workflow' not in found[0]
