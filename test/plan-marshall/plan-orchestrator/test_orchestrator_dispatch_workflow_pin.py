#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pin the ``--workflow`` argument across every orchestrator dispatch doc site.

``--workflow`` is not decoration on the ``effort resolve-target`` call: it is what
makes the resolve seam emit the ``[DISPATCH]`` work-log line and its paired
decision-log record. A site that resolves a dispatch level with a bare ``--role``
still dispatches, still resolves the right tier, and leaves NO trail — the
failure is invisible at the point it happens and only shows up later as a
dispatch nobody can account for.

The guard is **population-derived on both axes**, and the distinction matters
because getting only one of them is what this module previously shipped:

- the **invocation count** per document is enumerated out of the document text,
  never asserted from a constant; and
- the **document set** is enumerated out of the plan-marshall skills tree — every
  markdown file under it is opened, and the ones carrying an orchestrator
  dispatch resolve invocation ARE the search surface.

A hard-coded document list gets the first axis and misses the second: it cannot
notice a FOURTH DOCUMENT added later without the flag, because it never opens it.
That is the drift this pin exists to catch, and deriving the surface is what
actually catches it. ``_KNOWN_DISPATCH_DOCS`` survives only as a **floor** — the
sites the pin is known to have covered, asserted to still be covered — never as
the surface.

Because a population-derived guard can pass by finding nothing, every assertion
here publishes the evidence it was computed over (the tree size, the derived
document set, the invocation population, and the matched sites), and
``test_the_enumerator_is_not_vacuous`` pins the population as non-empty —
mirroring ``test_landing_completeness.py``'s ``test_the_extractors_are_not_vacuous``.
A guard that can return 0 from an empty population MUST publish that population
size, or a green proves only that the enumerator ran.
"""

from __future__ import annotations

import functools
import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT

_PLAN_MARSHALL = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'

#: The documents this pin was originally written against. This is a FLOOR, NOT
#: the search surface: the surface is derived from the tree below, and this tuple
#: only asserts that the derivation still REACHES every site the pin is known to
#: have covered. A rename, a move, or a doc that silently stops carrying its
#: invocation would otherwise shrink the derived set with no assertion firing.
_KNOWN_DISPATCH_DOCS: tuple[Path, ...] = (
    _PLAN_MARSHALL / 'plan-orchestrator' / 'workflow' / 'analyze.md',
    _PLAN_MARSHALL / 'plan-orchestrator' / 'workflow' / 'decompose.md',
    _PLAN_MARSHALL / 'persona-plan-orchestrator' / 'standards' / 'orchestration-model.md',
)

#: One orchestrator dispatch resolve invocation. The workflow docs carry the
#: call inline in prose, the standards doc carries it in a fenced block with
#: backslash continuations, and the marshal.json reference carries it in a table
#: cell, so the scan runs over whitespace-normalized text and stops at the end of
#: the invocation rather than assuming a single line.
#:
#: The surface segment admits BOTH spellings the docs use: a concrete surface
#: (``orchestrator.analyze``) at the call sites, and the ``{surface}``
#: placeholder in the canonical forms. Matching only the concrete spelling
#: silently drops the canonical form — the one site a reader copies from — and
#: the pin then speaks for a fraction of the documents it claims to cover.
#:
#: The invariant this pattern enforces is therefore about WRITTEN FORM, not about
#: intent: any document that spells a WHOLE ``effort resolve-target --role
#: orchestrator.…`` invocation must carry the flag, because a full-looking command
#: line is a copy source whatever the surrounding prose says it is. A doc that
#: wants to illustrate the bare role lookup writes the FRAGMENT
#: (``--role orchestrator.analyze``) instead of a whole invocation — which is what
#: ``effort-roles.md`` does, and why it is correctly outside the derived surface.
_INVOCATION_RE = re.compile(
    r'effort resolve-target --role orchestrator\.(?:[a-z-]+|\{[a-z_]+\})[^`\n]*'
)

#: A resolve invocation ends at the first backtick (prose and table-cell forms)
#: or at the end of the fenced command (standards form). Both are covered by
#: normalizing the continuation backslashes away before the scan.
_CONTINUATION_RE = re.compile(r'\\\s*\n\s*')


def _invocations(path: Path) -> list[str]:
    """Every orchestrator dispatch resolve invocation in one document."""
    text = _CONTINUATION_RE.sub(' ', path.read_text(encoding='utf-8'))
    return [match.group(0) for match in _INVOCATION_RE.finditer(text)]


@functools.cache
def _scanned_docs_under(root: Path) -> tuple[Path, ...]:
    """Every markdown document under ``root`` — the derivation's INPUT."""
    return tuple(sorted(root.rglob('*.md')))


@functools.cache
def _dispatch_docs_under(root: Path) -> tuple[Path, ...]:
    """The DERIVED search surface: the scanned docs carrying an invocation.

    Parameterized on ``root`` so the derivation itself can be exercised against
    a fixture tree — a hard-wired root would leave the "a document nobody listed
    is still scanned" claim untestable, which is how the previous hard-coded
    surface went unchallenged.
    """
    return tuple(doc for doc in _scanned_docs_under(root) if _invocations(doc))


def _population_under(root: Path) -> list[tuple[Path, str]]:
    """The (document, invocation) population derived from ``root``."""
    found: list[tuple[Path, str]] = []
    for doc in _dispatch_docs_under(root):
        found.extend((doc, invocation) for invocation in _invocations(doc))
    return found


def _population() -> list[tuple[Path, str]]:
    """The (document, invocation) population the assertions below run over."""
    return _population_under(_PLAN_MARSHALL)


class TestDispatchResolveSitesCarryWorkflow:
    def test_the_scanned_tree_is_a_real_population(self):
        """The derivation's INPUT is published, not assumed.

        Everything below is derived from this scan, so a glob that resolved
        against the wrong root would make every later population a shrunken one
        while every assertion stayed green.
        """
        assert _PLAN_MARSHALL.is_dir(), (
            f'the plan-marshall skills tree root does not exist: {_PLAN_MARSHALL}'
        )
        scanned = _scanned_docs_under(_PLAN_MARSHALL)

        assert len(scanned) > 50, (
            f'the markdown scan over {_PLAN_MARSHALL} opened {len(scanned)} document(s). '
            'The plan-marshall skills tree carries far more, so the scan is reading the '
            'wrong root and the derived dispatch-doc surface below is not the real one.'
        )

    def test_the_enumerator_is_not_vacuous(self):
        """The enumerator must find something, or the pin below proves nothing."""
        scanned = _scanned_docs_under(_PLAN_MARSHALL)
        derived = _dispatch_docs_under(_PLAN_MARSHALL)
        population = _population()

        assert population, (
            'The orchestrator dispatch resolve enumerator matched NO invocation. It opened '
            f'{len(scanned)} markdown document(s) under {_PLAN_MARSHALL} and derived '
            f'{len(derived)} dispatch document(s) from them. Every assertion in this module '
            'would pass vacuously, so the pin is reported as broken rather than green.'
        )

    def test_the_derived_surface_covers_every_known_dispatch_doc(self):
        """The floor: the derivation must still reach the known sites.

        This replaces the old ``test_every_dispatch_doc_exists``. Asserting that
        a hard-coded path EXISTS is tautological once the surface is derived from
        the tree — the derivation would simply not include a deleted file. What
        is NOT tautological is that the derivation still reaches those sites: a
        rename, a move, or a doc that quietly stopped carrying its invocation
        shrinks the derived set, and nothing else here would notice.
        """
        derived = set(_dispatch_docs_under(_PLAN_MARSHALL))
        uncovered = [str(doc) for doc in _KNOWN_DISPATCH_DOCS if doc not in derived]

        assert not uncovered, (
            f'{len(uncovered)} of {len(_KNOWN_DISPATCH_DOCS)} known dispatch document(s) are '
            f'absent from the {len(derived)}-document derived surface: {uncovered}. Either '
            'the document was renamed or moved (update the floor), or it stopped carrying '
            'an orchestrator dispatch resolve invocation the pin used to cover.'
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
        """The evidence assertion: counts are only meaningful beside their sites."""
        scanned = _scanned_docs_under(_PLAN_MARSHALL)
        derived = _dispatch_docs_under(_PLAN_MARSHALL)
        population = _population()
        sites = sorted({doc.name for doc, _ in population})

        assert len(population) >= len(_KNOWN_DISPATCH_DOCS), (
            f'{len(population)} invocation(s) enumerated across {len(sites)} document(s) '
            f'{sites}, derived from {len(derived)} dispatch document(s) out of '
            f'{len(scanned)} markdown document(s) scanned. That is fewer invocations than '
            f'the {len(_KNOWN_DISPATCH_DOCS)} sites this pin is known to cover, so the '
            'derivation lost ground rather than gaining it.'
        )

    def test_a_document_nobody_listed_is_still_scanned(self, tmp_path):
        """The crux of the derivation, proved by execution.

        The previous surface was a hard-coded three-path tuple, so a FOURTH
        document carrying a bare-``--role`` invocation was never opened and this
        pin stayed green over it. (The real tree held exactly such a document.)
        Here the derivation is pointed at a fixture tree whose only dispatch doc
        is named in no constant anywhere: it must be found, and its flagless
        invocation must be the thing the flag assertion would report.
        """
        nested = tmp_path / 'some-skill' / 'standards'
        nested.mkdir(parents=True)
        newcomer = nested / 'brand-new-surface.md'
        newcomer.write_text(
            'The level is resolved via `effort resolve-target --role orchestrator.newsurface '
            '--plan-id none --caller plan-marshall:persona-plan-orchestrator` at this site.\n',
            encoding='utf-8',
        )
        (tmp_path / 'unrelated.md').write_text('# Nothing to see\n', encoding='utf-8')

        derived = _dispatch_docs_under(tmp_path)
        population = _population_under(tmp_path)

        assert derived == (newcomer,), (
            f'the derivation returned {[str(doc) for doc in derived]} from a tree of '
            f'{len(_scanned_docs_under(tmp_path))} document(s), expected only the newcomer'
        )
        assert [text for _, text in population if '--workflow' not in text], (
            'the newcomer\'s flagless invocation was not reported as missing the flag'
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
        assert _dispatch_docs_under(tmp_path) == ()

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
