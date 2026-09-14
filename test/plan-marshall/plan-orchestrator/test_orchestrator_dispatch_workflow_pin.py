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

The module carries a **second** pin over the same derived surface:
``TestDraftingDispatchWritePathContainment`` asserts the write-path containment of
the dispatchable DRAFTING sub-steps — that every doc declaring one also names the
orchestrator as the writer, that no doc grants a leaf a ledger-write path, and that
every declared spec-body draft states the monotonic-resource constraint. Both pins
derive their document set the same way, so a doc added later is covered by both
without being listed in either.
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
_INVOCATION_RE = re.compile(r'effort resolve-target --role orchestrator\.(?:[a-z-]+|\{[a-z_]+\})[^`\n]*')

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
        assert _PLAN_MARSHALL.is_dir(), f'the plan-marshall skills tree root does not exist: {_PLAN_MARSHALL}'
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
            "the newcomer's flagless invocation was not reported as missing the flag"
        )

    def test_a_document_set_with_no_dispatch_invocation_yields_an_empty_population(self, tmp_path):
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


# =============================================================================
# Write-path containment for dispatchable DRAFTING sub-steps
# =============================================================================
#
# The write-freedom test admits a sub-step that only DRAFTS the content of a
# ledger write. That widening changes the test's truth conditions, so a drafting
# sub-step that previously FAILED write-freedom now passes it — and the control
# below asserts BOTH directions of that inversion, because the untested direction
# is exactly where the inverse defect lands:
#
#   1. a drafting declaration is ADMITTED, but only when its doc also states that
#      the orchestrator performs the resulting write; and
#   2. a leaf that PERFORMS a ledger write is STILL REJECTED, so widening the test
#      did not also admit the class it was always meant to exclude.
#
# The population is the SAME derived surface the `--workflow` pin runs over — the
# orchestrator dispatch docs derived from the plan-marshall skills tree — never a
# hard-coded document list.

#: A doc DECLARES a dispatchable drafting sub-step only when it ADMITS drafting —
#: either by qualifying a drafting sub-step as ``dispatchable`` (in that order,
#: within one sentence) or by stating that the drafting passes the write-freedom
#: test. Mere adjacency of "drafting" and "dispatch" is deliberately NOT enough:
#: the phrase occurs in headings and in prose that DENIES the declaration, and the
#: matched negative control below is what established that the looser form matched
#: a decoy. The one-sentence window (``[^.]``) is load-bearing too — it is what
#: keeps a "dispatchable" in one sentence from pairing with a "draft" in the next.
_DRAFTING_DECLARATION_RE = re.compile(
    r'(?i)dispatchable[^.]{0,160}draft(?:ing|ed)?'
    r'|draft(?:ing|ed)?[^.]{0,160}passes write-freedom'
    r'|draft(?:ing|ed)?[^.]{0,160}admitted by the write-freedom'
)

#: The orchestrator-applies clause: the doc must say the ORCHESTRATOR performs the
#: write whose content the leaf drafted. Without it a doc declares a dispatch that
#: drafts a write and names nobody who performs it, which is the gap that reads as
#: a licence for the leaf to perform it itself.
_ORCHESTRATOR_APPLIES_RE = re.compile(r'(?i)the orchestrator\b[^.]{0,80}\bperforms\b[^.]{0,180}\bwrite')

#: The concrete calls a drafting leaf may never make — the write path the refined
#: write-freedom test still excludes. Lower-cased, because the grant scan folds
#: case before matching.
_FORBIDDEN_WRITE_TARGETS: tuple[str, ...] = (
    '`write`',
    '`edit`',
    'manage-status',
    'manage-logging --store orchestrator',
    'orchestrator queue',
    'corpus set-verdict',
    '.plan/local/orchestrator',
)

#: The affirmative half of a grant: a permission or an assertion that the leaf DOES
#: the named call. The vocabulary is deliberately WIDE, because the narrow original
#: set — ``may|can|writes|write|calls|invokes|performs`` — made the condition a test
#: of PHRASING rather than of meaning: "the leaf records the disposition via
#: `manage-status`" and "the leaf appends the drafted row via `orchestrator queue`"
#: name exactly the write path the containment rule excludes, satisfy the leaf and
#: the forbidden-target conditions, and matched NOTHING here, so
#: ``test_no_dispatch_doc_grants_a_leaf_a_write_path`` reported green over the
#: sentence it exists to catch. ``test_a_grant_phrased_outside_the_narrow_verb_set_is_detected``
#: is the control that pins the widening.
#:
#: Widening this condition moves the discrimination onto the other three — a
#: sentence must still name a ``leaf``, name a forbidden target, and carry no
#: negation — which is close to the inversion (leaf + target + no negation = grant)
#: the alternative reading would have made explicit. What still separates the two is
#: that a sentence naming a leaf beside a forbidden call with no permission or
#: assertion at all (a bare cross-reference, a heading, a return-shape listing) does
#: not read as a grant here.
#:
#: ``sets`` is spelled plural-only on purpose: a bare ``set`` carries a word boundary
#: at the hyphen of the forbidden target ``corpus set-verdict``, so every sentence
#: naming that call would satisfy this condition by naming it, making the affirmative
#: half vacuous exactly where it is most load-bearing.
_AFFIRMATIVE_RE = re.compile(
    r'\b(?:may|can|shall|must|will|is responsible for'
    r'|write|writes|writing|written'
    r'|call|calls|calling'
    r'|invoke|invokes|invoking'
    r'|perform|performs|performing'
    r'|record|records|recording'
    r'|author|authors|authoring|authored'
    r'|sets|setting'
    r'|mutate|mutates|mutating'
    r'|append|appends|appending'
    r'|stamp|stamps|stamping'
    r'|persist|persists|persisting'
    r'|emit|emits|emitting)\b'
)

#: Negation vocabulary. Every real statement about a leaf and a forbidden call is a
#: PROHIBITION ("it MAY NOT call", "No leaf ... writes"), so a grant scan that
#: ignored negation would report the containment rule itself as the violation.
_NEGATION_RE = re.compile(
    r'\b(?:not|never|nothing|no|none|cannot|bars|barred|prohibited|prohibits|forbidden|forbids|without|outside)\b'
)

_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')

#: A doc declares a dispatchable SPEC-BODY draft when it declares the return field
#: that carries one. Keying on the declared field rather than on any mention of a
#: spec draft is deliberate: the monotonic-resource constraint binds where the
#: draft's SHAPE is specified — the doc a leaf author works from — which is the two
#: verb docs, not the shared rule that merely indexes the dispatch.
_SPEC_BODY_DRAFT_RE = re.compile(r'(?i)\bspec_drafts\b|\bspec_body\b|drafted spec body')

_MONOTONIC_CONSTRAINT_RE = re.compile(r'(?i)monotonic resource')
_SELECTION_RULE_RE = re.compile(r'(?i)selection rule')


def _normalized(path: Path) -> str:
    """One document's text with continuation backslashes folded away."""
    return _CONTINUATION_RE.sub(' ', path.read_text(encoding='utf-8'))


def _declares_drafting_dispatch(text: str) -> bool:
    return bool(_DRAFTING_DECLARATION_RE.search(text))


def _states_orchestrator_applies(text: str) -> bool:
    return bool(_ORCHESTRATOR_APPLIES_RE.search(text))


def _leaf_write_grants(text: str) -> list[str]:
    """Sentences that grant a dispatched leaf a ledger-write path.

    A grant is a sentence that names a ``leaf``, names one of the forbidden write
    targets, carries an affirmative permission or assertion, and carries NO
    negation. All four conditions are load-bearing — dropping the negation
    condition turns every prohibition in the containment rule into a reported
    grant. The affirmative condition is deliberately wide rather than a list of
    the verbs the current docs happen to use: a grant phrased with any other verb
    names the same write path, and a narrow set silently excuses it (see
    ``_AFFIRMATIVE_RE``).
    """
    grants: list[str] = []
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        lowered = sentence.lower()
        if not re.search(r'\bleaf\b', lowered):
            continue
        if not any(target in lowered for target in _FORBIDDEN_WRITE_TARGETS):
            continue
        if not _AFFIRMATIVE_RE.search(lowered):
            continue
        if _NEGATION_RE.search(lowered):
            continue
        grants.append(' '.join(sentence.split()))
    return grants


def _containment_population(root: Path) -> dict[str, object]:
    """The labelled populations every containment assertion is computed over.

    Each count is returned under a key that NAMES the population it enumerated.
    The three document counts are NESTED SUBSETS (scanned ⊇ derived ⊇ drafting
    ⊇ spec-body), so they are reported side by side and never differenced as
    though they counted one set.
    """
    scanned = _scanned_docs_under(root)
    derived = _dispatch_docs_under(root)
    texts = {doc: _normalized(doc) for doc in derived}
    drafting = [doc for doc in derived if _declares_drafting_dispatch(texts[doc])]
    spec_body = [doc for doc in drafting if _SPEC_BODY_DRAFT_RE.search(texts[doc])]
    return {
        'markdown_docs_scanned': len(scanned),
        'docs_derived_as_orchestrator_dispatch_docs': len(derived),
        'dispatch_docs_declaring_a_drafting_substep': len(drafting),
        'drafting_docs_declaring_a_spec_body_draft': len(spec_body),
        'drafting_doc_names': sorted(doc.name for doc in drafting),
        'spec_body_doc_names': sorted(doc.name for doc in spec_body),
        'drafting_docs': drafting,
        'spec_body_docs': spec_body,
        'texts': texts,
    }


def _evidence(population: dict[str, object]) -> str:
    """The population statement every assertion message below carries."""
    return (
        f'Populations, each named by what it enumerated (nested subsets, not comparable counts): '
        f'markdown documents scanned under the plan-marshall skills tree='
        f'{population["markdown_docs_scanned"]}; '
        f'of those, documents derived as orchestrator dispatch docs='
        f'{population["docs_derived_as_orchestrator_dispatch_docs"]}; '
        f'of those, documents declaring a dispatchable drafting sub-step='
        f'{population["dispatch_docs_declaring_a_drafting_substep"]} '
        f'{population["drafting_doc_names"]}; '
        f'of those, documents declaring a spec-body draft return field='
        f'{population["drafting_docs_declaring_a_spec_body_draft"]} '
        f'{population["spec_body_doc_names"]}.'
    )


class TestDraftingDispatchWritePathContainment:
    def test_the_drafting_declaration_population_is_not_vacuous(self):
        """A zero drafting-declaration count is a BROKEN PIN, not a clean pass.

        Every assertion below quantifies over the drafting docs, so an enumerator
        that matched none would make all of them pass while asserting nothing.
        """
        population = _containment_population(_PLAN_MARSHALL)

        assert population['dispatch_docs_declaring_a_drafting_substep'], (
            'NO document in the derived orchestrator dispatch surface declares a dispatchable '
            'drafting sub-step, so every containment assertion in this class would pass '
            f'vacuously. Reported as a broken pin rather than green. {_evidence(population)}'
        )

    def test_every_drafting_declaration_names_the_orchestrator_as_the_writer(self):
        """Direction 1 of the inversion: drafting is admitted, but only with the applies-clause."""
        population = _containment_population(_PLAN_MARSHALL)
        texts: dict[Path, str] = population['texts']
        drafting: list[Path] = population['drafting_docs']
        silent = [doc.name for doc in drafting if not _states_orchestrator_applies(texts[doc])]

        assert not silent, (
            f'{len(silent)} document(s) declare a dispatchable drafting sub-step without stating '
            f'that the orchestrator performs the resulting write: {silent}. A drafting dispatch '
            'that names nobody as the writer reads as a licence for the leaf to perform the write '
            f'itself. {_evidence(population)}'
        )

    def test_no_dispatch_doc_grants_a_leaf_a_write_path(self):
        """Direction 2 of the inversion: performing a ledger write is STILL rejected.

        Widening write-freedom to admit drafting must not also admit the class the
        test was always meant to exclude. This runs over every derived dispatch
        doc, not only the drafting ones — a grant is out of bounds wherever it is
        written.
        """
        population = _containment_population(_PLAN_MARSHALL)
        texts: dict[Path, str] = population['texts']
        offenders = {doc.name: _leaf_write_grants(text) for doc, text in texts.items() if _leaf_write_grants(text)}

        assert not offenders, (
            f'{len(offenders)} orchestrator dispatch document(s) grant a dispatched leaf a '
            f'ledger-write path: {offenders}. The refined write-freedom test admits DRAFTING the '
            'content of a write; performing one stays with the orchestrator. '
            f'{_evidence(population)}'
        )

    def test_every_spec_body_draft_carries_the_monotonic_resource_constraint(self):
        """A drafted spec body must state the selection rule, never assume an ordinal."""
        population = _containment_population(_PLAN_MARSHALL)
        texts: dict[Path, str] = population['texts']
        spec_body_docs: list[Path] = population['spec_body_docs']

        assert spec_body_docs, (
            'NO document declares a spec-body draft return field, so this assertion would '
            f'quantify over an empty set. {_evidence(population)}'
        )

        uncovered = [
            doc.name
            for doc in spec_body_docs
            if not (_MONOTONIC_CONSTRAINT_RE.search(texts[doc]) and _SELECTION_RULE_RE.search(texts[doc]))
        ]

        assert not uncovered, (
            f'{len(uncovered)} document(s) declare a dispatchable spec-body draft without stating '
            f'the monotonic-resource constraint and the selection rule it substitutes: {uncovered}. '
            'A draft that embeds an assumed PLAN-NN ordinal instead of the selection rule would be '
            f'silently accepted, and it collides with a sibling staged against the same HEAD. '
            f'{_evidence(population)}'
        )

    def test_a_drafting_declaration_without_the_applies_clause_is_detected(self, tmp_path):
        # Matched POSITIVE control: the assertion above is green over the real
        # tree, so this proves that green is a measured pass rather than a
        # detector that cannot fail.
        offender = tmp_path / 'silent-drafting.md'
        offender.write_text(
            '- **Dispatchable** — the landing-report body is drafting work and rides one envelope.\n',
            encoding='utf-8',
        )
        text = _normalized(offender)

        assert _declares_drafting_dispatch(text), 'the drafting-declaration detector missed a declaration'
        assert not _states_orchestrator_applies(text), (
            'the fixture was supposed to omit the orchestrator-applies clause, so the detector '
            'pair cannot demonstrate a failure'
        )

    def test_a_doc_with_no_drafting_dispatch_is_not_matched(self, tmp_path):
        # Matched NEGATIVE control: pointed at a doc that talks about dispatch and
        # about drafts in unrelated sentences, the detector must NOT claim a
        # declaration. Without this, a too-greedy pattern would make every
        # document look like a drafting dispatch and the population above healthy.
        # This is not hypothetical: the first form of the detector matched the
        # heading below — the adversarial phrase is deliberately the one that
        # DENIES the declaration, and the sentence pairing "dispatchable" with a
        # later "draft" across a sentence boundary is the second decoy.
        decoy = tmp_path / 'no-drafting.md'
        decoy.write_text(
            '# Not a drafting dispatch\n\n'
            'This verb has one dispatchable sub-step: corroborating a landing against ground '
            'truth.\n\n'
            'Separately, the operator sometimes keeps a draft of the report in their own notes.\n',
            encoding='utf-8',
        )

        assert not _declares_drafting_dispatch(_normalized(decoy))

    def test_a_leaf_granted_a_write_path_is_detected(self, tmp_path):
        # Matched control for direction 2: each forbidden call must be caught on
        # its own, so a detector covering only the `Write`/`Edit` half cannot pass
        # this. Asserted per-target rather than over one omnibus fixture, because
        # an omnibus doc is matched by whichever target the scan happens to
        # support.
        grants = {
            'write-in-epic-tree': 'The leaf may call `Write` inside `.plan/local/orchestrator/{slug}/plans/`.',
            'status-store': 'The leaf writes the queue row itself via `manage-status` with the orchestrator store.',
            'queue': 'The leaf calls `orchestrator queue` to append the row once it has drafted the spec.',
            'verdict': 'The leaf invokes `corpus set-verdict` for each claim it settled.',
        }
        for label, sentence in grants.items():
            fixture = tmp_path / f'grant-{label}.md'
            fixture.write_text(sentence + '\n', encoding='utf-8')
            found = _leaf_write_grants(_normalized(fixture))
            assert found, f'the grant scan missed the {label} write path: {sentence}'

    def test_a_grant_phrased_outside_the_narrow_verb_set_is_detected(self, tmp_path):
        # The gap this control closes, and the reason it is separate from the
        # per-target control above: that one varies the TARGET while holding the
        # phrasing inside the original affirmative set, so it never exercised the
        # affirmative condition itself. A grant that chose any other verb satisfied
        # the leaf and target conditions, failed the affirmative one, and was
        # reported as no grant at all — the assertion passed green over exactly the
        # sentence it exists to catch.
        #
        # Each phrasing is asserted TWICE, and the second half is what makes this a
        # measured widening rather than a wider regex nobody needed: the superseded
        # narrow pattern must MISS the sentence the current scan catches. A fixture
        # the old pattern already matched would witness nothing.
        superseded = re.compile(r'\b(?:may|can|writes|write|calls|invokes|performs)\b')
        grants = {
            'records': 'The leaf records each disposition through `manage-status` in the orchestrator store.',
            'appends': 'The leaf appends the drafted row via `orchestrator queue` once the mapping is settled.',
            'authors': 'The leaf authors the landing record inside `.plan/local/orchestrator/{slug}/landings/`.',
            'is-responsible-for-writing': (
                'The leaf is responsible for writing each settled verdict with `corpus set-verdict`.'
            ),
        }
        for label, sentence in grants.items():
            fixture = tmp_path / f'wide-grant-{label}.md'
            fixture.write_text(sentence + '\n', encoding='utf-8')

            found = _leaf_write_grants(_normalized(fixture))

            assert found, f'the grant scan missed the {label} phrasing: {sentence}'
            assert not superseded.search(sentence.lower()), (
                f'the {label} fixture is phrased with a verb the narrow set already matched, so it '
                f'cannot witness the widening — repick the verb: {sentence}'
            )

    def test_a_prohibition_is_not_read_as_a_grant(self, tmp_path):
        # The matched negative half of direction 2's control, and the one that
        # actually bites: every real statement pairing a leaf with a forbidden
        # call is a PROHIBITION, so a grant scan that ignored negation would
        # report the containment rule itself as the violation.
        rule = tmp_path / 'prohibition.md'
        rule.write_text(
            'A drafting leaf MAY compose a spec draft; it MAY NOT call `Write`/`Edit` inside '
            '`.plan/local/orchestrator/{slug}/**`, `manage-status` or `manage-logging --store '
            'orchestrator`, `orchestrator queue`, or `corpus set-verdict`.\n\n'
            'No leaf dispatched by an orchestrator verb writes inside '
            '`.plan/local/orchestrator/{slug}/**`.\n',
            encoding='utf-8',
        )

        assert _leaf_write_grants(_normalized(rule)) == []
