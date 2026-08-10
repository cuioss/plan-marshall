#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-cutting contract suite for the `cleanup` verb and the surfaces it touches.

The assertions here span deliverables and therefore cannot live in any single
seam's module. Every one of them is **population-derived**: the governed sets are
enumerated at test time from the router table, the workflow directory, the live
argparse declaration, and the marketplace markdown tree, and every count-bearing
assertion publishes the population it was computed over — a check that can return
`0` from an empty population must publish the population size.

Five groups:

- **(a) Router closure** — the workflow docs the `## Verb Routing` table
  REFERENCES against the `workflow/*.md` files on disk, in both directions. The
  comparison is over DOCUMENTS, never rows-vs-files: the row→doc mapping is
  legitimately many-to-one (`status` and `next` both route to
  `workflow/orchestrate.md`), so a literal row-set-vs-file-set equality would
  fail on pre-existing structure. Three populations are published so the
  many-to-one collapse is a visible property rather than a mistaken defect.
- **(b) Verb-enumeration agreement** — the verb set derived from the router
  table against every other enumerating surface: the `## Usage` block, the
  standard's Terminal-Title enumeration (its stated COUNT and its list), and
  `doc/concepts/orchestration.adoc`. This is the check that would have caught
  the pre-existing `archive` omission. ⚠ **The concepts document is held to
  AGREEMENT, not to existence.** A narrative document that defers to the router
  instead of restating its registry carries no verb set to go stale, which is
  the stronger form and the one the project's no-duplication standard prefers;
  mandating an enumeration there would mandate the duplication. So the check
  governs whatever enumeration the document carries and requires none: a
  re-introduced nine-of-ten list fails, and the deferring link passes. The
  enumeration is found by detecting a RUN of backticked verbs in any prose
  shape rather than by matching a fixed phrase, so the guard survives rewording,
  and its scan population is published by a companion assertion.
- **(c) Canonical-invocation coverage** — the sub-verb set derived from
  `orchestrator.py`'s own argparse declaration, each required to carry a
  `## Canonical invocations` subsection. Resolved from the tool's live
  declaration rather than from a hand-maintained list.
- **(d) Idempotence** — pinned at the seam that actually applies. ⚠ **Stated
  boundary**: the verb-level "second run's `applied[]` is empty" assertion is
  NOT mechanically reachable from a test, because `cleanup` is a prose workflow
  an LLM follows, not a script a test can invoke. What IS reachable, and what
  the `(spec id, finding class)` idempotence key actually rests on, is the
  single applying seam — `corpus set-verdict`. It is pinned as a byte-level
  no-op on an identical re-stamp, with the matched negative control the
  deliverable requires: a fixture mutated between runs MUST produce a change,
  so the no-op assertion cannot pass by the seam doing nothing at all.
- **(e) Verdict-field single definition** — exactly one marketplace file defines
  the grammar, the four consuming surfaces xref it and restate none of it, the
  emitter and the parser are one each, and a stamped verdict round-trips with
  every key intact including an `evidence` value containing the separator.

⛔ **Scope boundary for group (e)**: the population is the marketplace tree only.
`doc/plans/_template/plan.md` carries its own `## Claim Labels` section outside
that tree and is deliberately NOT in scope — it is a plan-lane template governed
by the `doc/plans/` lane, not a marketplace surface this grammar binds. The count
therefore reads "1 of the marketplace population", never "1 in the repository".
"""

import argparse
import json
import re
from argparse import Namespace
from pathlib import Path
from typing import Any

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT, load_script_module

_orch = load_script_module(
    'plan-marshall', 'marshall-orchestrator', 'orchestrator.py', 'orchestrator_script'
)

cmd_corpus_set_verdict = _orch.cmd_corpus_set_verdict
cmd_corpus_verdicts = _orch.cmd_corpus_verdicts
build_arg_parser = _orch._build_arg_parser
VERDICT_KEYS = _orch.VERDICT_KEYS
VERDICT_SEPARATOR = _orch.VERDICT_SEPARATOR

_MARKETPLACE: Path = Path(MARKETPLACE_ROOT)
_SKILL_DIR: Path = _MARKETPLACE / 'plan-marshall' / 'skills' / 'marshall-orchestrator'
SKILL_MD: Path = _SKILL_DIR / 'SKILL.md'
WORKFLOW_DIR: Path = _SKILL_DIR / 'workflow'
PLAN_SPEC_TEMPLATE: Path = _SKILL_DIR / 'templates' / 'plan-spec.md'
STANDARD_MD: Path = (
    _MARKETPLACE
    / 'plan-marshall'
    / 'skills'
    / 'persona-marshall-orchestrator'
    / 'standards'
    / 'orchestration-model.md'
)
CONCEPTS_ADOC: Path = Path(PROJECT_ROOT) / 'doc' / 'concepts' / 'orchestration.adoc'

#: The anchor every consuming surface xrefs instead of restating the grammar.
VERDICT_ANCHOR = 'Re-Grounding Verdict Field'

#: The code-level signature of the grammar: all five key names together. The
#: CONJUNCTION is what distinguishes a restatement from an xref that merely names
#: the anchor — any one token alone has plenty of innocent uses.
GRAMMAR_SIGNATURE = ('verdict', 'checked_at', 'by', 'rescoped', 'evidence')

#: The two tokens with no plausible non-grammar use. A consuming surface carrying
#: either has restated part of the grammar, which a five-token conjunction alone
#: would miss.
GRAMMAR_ONLY_TOKENS = ('checked_at', 'rescoped')

#: The four surfaces that CONSUME the field and must therefore xref it.
CONSUMING_SURFACES = (
    WORKFLOW_DIR / 'cleanup.md',
    WORKFLOW_DIR / 'analyze.md',
    WORKFLOW_DIR / 'orchestrate.md',
    PLAN_SPEC_TEMPLATE,
)

_ROUTING_ROW_RE = re.compile(r'^\|\s*`(?P<verb>[a-z][a-z-]*)`\s*\|\s*`(?P<doc>workflow/[a-z-]+\.md)`\s*\|')
_USAGE_VERB_RE = re.compile(r'^/marshall-orchestrator\s+(?P<verb>[a-z][a-z-]*)', re.MULTILINE)
_TITLE_ENUMERATION_RE = re.compile(
    r'All (?P<count_word>[a-z]+) verbs — (?P<list>.+?) — carry the obligation'
)
_BACKTICKED_RE = re.compile(r'`([a-z][a-z-]*)`')

#: A RUN of backticked lowercase tokens joined only by list separators (` / `,
#: `, `, ` and `). Matching the run rather than a surrounding phrase is what
#: makes the concepts-document check population-derived: an enumeration written
#: in ANY prose shape is found, so rewording the sentence around the list cannot
#: silently retire the guard the way a phrase-pinned pattern would.
_VERB_RUN_RE = re.compile(r'`[a-z][a-z-]*`(?:\s*(?:/|,?\s*and|,)\s*`[a-z][a-z-]*`)+')

#: How many routed verbs a run must carry before it counts as an ENUMERATION of
#: the verb set rather than prose that happens to name a verb or two (``the
#: `close` and `archive` verbs``, which must not be forced to list all ten).
#: ⚠ Stated boundary: an enumeration decayed to fewer than this many verbs falls
#: below the threshold and is not caught. The shape this guard exists for — all
#: but one, the pre-existing `archive` omission — is well above it.
_ENUMERATION_MIN_VERBS = 3
_CANONICAL_HEADING_RE = re.compile(r'^### (?P<name>.+)$', re.MULTILINE)

#: Number words the enumerating prose may use for its stated count. Kept small
#: and explicit: the count is a one-per-verb tally, not an arbitrary integer.
_NUMBER_WORDS = {
    'six': 6,
    'seven': 7,
    'eight': 8,
    'nine': 9,
    'ten': 10,
    'eleven': 11,
    'twelve': 12,
}


# =============================================================================
# Derivation helpers — every governed set is enumerated, never hand-listed
# =============================================================================


def _skill_text() -> str:
    return SKILL_MD.read_text(encoding='utf-8')


def _routing_rows() -> list[tuple[str, str]]:
    """Every `| \\`verb\\` | \\`workflow/doc.md\\` |` row of the Verb Routing table."""
    return [
        (match.group('verb'), match.group('doc'))
        for match in (_ROUTING_ROW_RE.match(line) for line in _skill_text().splitlines())
        if match is not None
    ]


def _on_disk_workflow_docs() -> set[str]:
    return {f'workflow/{path.name}' for path in WORKFLOW_DIR.glob('*.md')}


def _verb_enumerations(lines: list[str], routed: set[str]) -> list[tuple[int, set[str]]]:
    """Every line that ENUMERATES the verb set, paired with the verbs it lists.

    Derived from the routed population at call time rather than pinned to a
    phrase, and returning the run's FULL token set rather than its intersection
    with `routed`, so a bogus extra verb fails as loudly as a missing one.
    """
    found: list[tuple[int, set[str]]] = []
    for number, line in enumerate(lines, start=1):
        for run in _VERB_RUN_RE.findall(line):
            listed: set[str] = set(_BACKTICKED_RE.findall(run))
            if len(listed & routed) >= _ENUMERATION_MIN_VERBS:
                found.append((number, listed))
    return found


def _subparser_action(parser: argparse.ArgumentParser) -> Any:
    """Return the parser's subcommand action, or ``None`` when it has none."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def _declared_invocations() -> set[str]:
    """Every invocation name the live argparse declaration exposes.

    A leaf top-level verb yields its own name; a verb GROUP yields one
    ``{group} {action}`` entry per sub-action. Derived from the tool rather than
    restated, so a new sub-verb is governed the moment it is declared.
    """
    top = _subparser_action(build_arg_parser())
    assert top is not None, 'the parser declares no subcommands'
    names: set[str] = set()
    for name, sub in top.choices.items():
        nested = _subparser_action(sub)
        if nested is None:
            names.add(name)
        else:
            names.update(f'{name} {child}' for child in nested.choices)
    return names


def _canonical_headings() -> set[str]:
    """Every `### ` heading inside SKILL.md's `## Canonical invocations` section."""
    text = _skill_text()
    start = text.index('## Canonical invocations')
    end = text.find('\n## ', start + 1)
    section = text[start:] if end < 0 else text[start:end]
    return {match.group('name').strip() for match in _CANONICAL_HEADING_RE.finditer(section)}


def _marketplace_markdown() -> list[Path]:
    return sorted(_MARKETPLACE.rglob('*.md'))


def _matches_grammar_signature(path: Path) -> bool:
    text = path.read_text(encoding='utf-8', errors='ignore')
    return all(token in text for token in GRAMMAR_SIGNATURE)


# =============================================================================
# (a) Router closure — population-derived, over DOCUMENTS not rows
# =============================================================================


class TestRouterClosure:
    def test_should_publish_all_three_populations(self):
        """Non-empty-population guard for every set the closure compares."""
        rows = _routing_rows()
        referenced = {doc for _, doc in rows}
        on_disk = _on_disk_workflow_docs()

        assert len(rows) > 0, 'the Verb Routing table yielded no rows'
        assert len(referenced) > 0, 'no workflow doc is referenced by any row'
        assert len(on_disk) > 0, f'no workflow doc found on disk under {WORKFLOW_DIR}'
        assert len(rows) >= len(referenced), (
            'the row→doc mapping is many-to-one, so rows can never be FEWER than docs'
        )

    def test_every_referenced_doc_exists_on_disk(self):
        referenced = {doc for _, doc in _routing_rows()}

        dangling = sorted(referenced - _on_disk_workflow_docs())

        assert dangling == [], f'Verb Routing references workflow docs that do not exist: {dangling}'

    def test_every_workflow_doc_on_disk_is_referenced(self):
        # The other direction, with its own distinct failure message: an
        # unreferenced doc is unreachable through the router.
        on_disk = _on_disk_workflow_docs()

        unreferenced = sorted(on_disk - {doc for _, doc in _routing_rows()})

        assert unreferenced == [], f'workflow docs on disk that no Verb Routing row reaches: {unreferenced}'

    def test_the_many_to_one_collapse_is_a_stated_property(self):
        # `status` and `next` share one doc, so the row count exceeds the doc
        # count. Pinning it keeps a future reader from reading the gap as drift.
        rows = _routing_rows()
        by_doc: dict[str, list[str]] = {}
        for verb, doc in rows:
            by_doc.setdefault(doc, []).append(verb)

        shared = {doc: verbs for doc, verbs in by_doc.items() if len(verbs) > 1}

        assert shared, 'no doc is shared — the many-to-one property has disappeared'
        assert sorted(shared['workflow/orchestrate.md']) == ['next', 'status']


# =============================================================================
# (b) Verb-enumeration agreement across every enumerating surface
# =============================================================================


class TestVerbEnumerationAgreement:
    def test_the_router_table_is_the_non_empty_reference_set(self):
        verbs = [verb for verb, _ in _routing_rows()]

        assert verbs, 'the router table yielded no verbs'
        assert len(set(verbs)) == len(verbs), f'a verb is routed twice: {verbs}'
        assert 'cleanup' in verbs

    def test_the_usage_block_lists_exactly_the_routed_verbs(self):
        usage_verbs = {match.group('verb') for match in _USAGE_VERB_RE.finditer(_skill_text())}
        routed = {verb for verb, _ in _routing_rows()}

        assert usage_verbs == routed, (
            f'§ Usage and § Verb Routing disagree — only in Usage: {sorted(usage_verbs - routed)}, '
            f'only in Routing: {sorted(routed - usage_verbs)}'
        )

    def test_the_standards_terminal_title_enumeration_agrees_in_count_and_list(self):
        match = _TITLE_ENUMERATION_RE.search(STANDARD_MD.read_text(encoding='utf-8'))
        routed = {verb for verb, _ in _routing_rows()}

        assert match is not None, 'the Terminal-Title verb enumeration was not found in the standard'
        listed = set(_BACKTICKED_RE.findall(match.group('list')))
        stated_count = _NUMBER_WORDS.get(match.group('count_word'))
        assert stated_count is not None, f'unrecognised count word {match.group("count_word")!r}'
        assert listed == routed, (
            f'the standard enumerates a different verb set — only there: {sorted(listed - routed)}, '
            f'only routed: {sorted(routed - listed)}'
        )
        assert stated_count == len(routed), (
            f'the standard states {stated_count} verbs but enumerates {len(routed)}'
        )

    def test_the_concepts_document_agrees(self):
        # The surface that carried the pre-existing `archive` omission.
        #
        # ⚠ The contract is AGREEMENT, not existence. The document is not
        # required to enumerate: a link that defers to the router carries no
        # verb set to go stale, which is the stronger form and the one the
        # project's no-duplication standard prefers. What is required is that
        # any enumeration the document DOES carry agrees with the router — so
        # re-introducing a nine-of-ten list fails here, while deferring to the
        # router passes.
        routed = {verb for verb, _ in _routing_rows()}
        lines = CONCEPTS_ADOC.read_text(encoding='utf-8').splitlines()

        enumerations = _verb_enumerations(lines, routed)

        for number, listed in enumerations:
            assert listed == routed, (
                f'{CONCEPTS_ADOC.name}:{number} enumerates a different verb set — only there: '
                f'{sorted(listed - routed)}, only routed: {sorted(routed - listed)}'
            )

    def test_the_concepts_scan_publishes_its_population(self):
        # The companion to the agreement assertion above: that one iterates a
        # set that may legitimately be empty, so the scan's own population is
        # published here. A zero-enumeration result is then a READ RESULT
        # ("the document defers to the router") rather than an unnoticed empty
        # scan of an unreadable or relocated file.
        routed = {verb for verb, _ in _routing_rows()}
        lines = CONCEPTS_ADOC.read_text(encoding='utf-8').splitlines()

        enumerations = _verb_enumerations(lines, routed)

        assert lines, f'{CONCEPTS_ADOC} yielded no lines — the scan population is zero'
        assert len(enumerations) <= 1, (
            f'{CONCEPTS_ADOC.name} carries {len(enumerations)} verb enumerations, at lines '
            f'{[number for number, _ in enumerations]} — a second one is a duplicate registry '
            f'({len(lines)} lines scanned)'
        )

    def test_the_concepts_detector_catches_a_seeded_omission(self):
        # Matched control proving the agreement assertion is not vacuous: the
        # same detector the real check uses, run over a seeded nine-of-ten list
        # built from the LIVE routed set so the control cannot itself go stale.
        routed = {verb for verb, _ in _routing_rows()}
        dropped = sorted(routed)[0]
        seeded = ' / '.join(f'`{verb}`' for verb in sorted(routed - {dropped}))
        complete = ' / '.join(f'`{verb}`' for verb in sorted(routed))

        omitted = _verb_enumerations([f'* the verb router ({seeded})'], routed)
        intact = _verb_enumerations([f'* the verb router ({complete})'], routed)

        assert len(omitted) == 1, 'the detector did not see a verb enumeration in the live shape'
        assert omitted[0][1] == routed - {dropped}
        assert omitted[0][1] != routed, f'a list omitting {dropped!r} was read as agreeing'
        # The negative half: the detector must ACCEPT a complete list, so the
        # positive half above cannot pass by the detector rejecting everything.
        assert [listed for _, listed in intact] == [routed]

    def test_the_concepts_detector_does_not_flag_ordinary_prose(self):
        # Near-miss control: prose naming a verb or two is not an enumeration
        # and must not be forced to list all ten, or the guard would push the
        # duplicated registry back into the document it just left.
        routed = {verb for verb, _ in _routing_rows()}

        prose = _verb_enumerations(
            [
                'the `close` and `archive` verbs both retire an epic',
                'the verb router, which carries the authoritative verb set',
            ],
            routed,
        )

        assert prose == [], f'ordinary prose was mistaken for an enumeration: {prose}'


# =============================================================================
# (c) Canonical-invocation coverage, derived from the live argparse declaration
# =============================================================================


class TestCanonicalInvocationCoverage:
    def test_the_declared_invocation_population_is_non_empty(self):
        declared = _declared_invocations()

        assert declared, 'the argparse declaration yielded no invocations'
        assert 'cleanup restart-check' in declared
        assert 'corpus cross-check' in declared

    def test_every_declared_invocation_has_a_canonical_subsection(self):
        declared = _declared_invocations()

        undocumented = sorted(declared - _canonical_headings())

        assert undocumented == [], (
            f'{len(declared)} invocations are declared and these carry no '
            f'## Canonical invocations subsection: {undocumented}'
        )

    def test_no_canonical_subsection_documents_an_undeclared_invocation(self):
        headings = _canonical_headings()

        stale = sorted(headings - _declared_invocations())

        assert stale == [], f'canonical subsections for invocations the tool does not declare: {stale}'


# =============================================================================
# (d) Idempotence — pinned at the one seam that applies
# =============================================================================

SLUG = 'fixture-contract-epic'
_CLAIM = '- HYPOTHESIS: a clause — confirm/refute at `a.py` § `f` (verify-at-outline)'
SHA = '9f3a1c2'
PRODUCER = 'fixture-contract-epic/cleanup'


def _epic_dir(plan_context) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / SLUG


def _write_fixture_spec(plan_context) -> Path:
    doc = {
        'kind': 'orchestrator',
        'title': 'Fixture Contract Epic',
        'phase': 'orchestrating',
        'workstreams': ['WS-01'],
        'plans': [{'id': 'PLAN-01', 'slug': 'plan-01', 'workstream': 'WS-01', 'status': 'staged'}],
        'resume_anchor': 'fixture',
        'metadata': {},
        'created': '2020-01-01T00:00:00Z',
        'updated': '2020-01-01T00:00:00Z',
    }
    status_path = _epic_dir(plan_context) / 'status.json'
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    spec = _epic_dir(plan_context) / 'plans' / 'PLAN-01-alpha.md'
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text(
        '\n'.join(['# PLAN-01: Fixture', '', '## Claim Labels', '', _CLAIM]) + '\n',
        encoding='utf-8',
    )
    return spec


def _stamp(evidence: str = 'holds at this sha') -> Namespace:
    return Namespace(
        slug=SLUG,
        plan='PLAN-01',
        claim_index=0,
        verdict='corroborated',
        checked_at=SHA,
        by=PRODUCER,
        rescoped='n/a',
        evidence=evidence,
    )


class TestApplyIdempotence:
    def test_an_identical_restamp_is_a_byte_level_no_op(self, plan_context):
        spec = _write_fixture_spec(plan_context)

        cmd_corpus_set_verdict(_stamp())
        after_first = spec.read_bytes()
        second = cmd_corpus_set_verdict(_stamp())

        assert second['status'] == 'success'
        assert spec.read_bytes() == after_first, 'a re-apply of the same finding must change nothing'

    def test_a_changed_finding_does_produce_a_change(self, plan_context):
        # Matched negative control: without it the no-op assertion above could
        # pass by the seam applying nothing at all.
        spec = _write_fixture_spec(plan_context)

        cmd_corpus_set_verdict(_stamp(evidence='first pass'))
        after_first = spec.read_bytes()
        cmd_corpus_set_verdict(_stamp(evidence='second pass'))

        assert spec.read_bytes() != after_first
        assert b'second pass' in spec.read_bytes()

    def test_a_claim_never_accumulates_two_verdicts(self, plan_context):
        # The keying is per (spec, claim): a second apply REPLACES rather than
        # appends, which is what makes the re-run a no-op instead of a growth.
        spec = _write_fixture_spec(plan_context)

        cmd_corpus_set_verdict(_stamp(evidence='first pass'))
        cmd_corpus_set_verdict(_stamp(evidence='second pass'))

        assert spec.read_text(encoding='utf-8').count('- verdict:') == 1


# =============================================================================
# (e) Verdict-field single definition and producer/consumer agreement
# =============================================================================


class TestVerdictFieldSingleDefinition:
    def test_the_markdown_population_is_non_empty(self):
        population = _marketplace_markdown()

        assert population, f'no markdown enumerated under {_MARKETPLACE}'
        assert STANDARD_MD in population

    def test_exactly_one_marketplace_file_defines_the_grammar(self):
        population = _marketplace_markdown()

        carriers = [path for path in population if _matches_grammar_signature(path)]

        assert carriers == [STANDARD_MD], (
            f'of {len(population)} marketplace markdown files, these carry the full grammar '
            f'signature: {[str(path) for path in carriers]}'
        )

    def test_every_consuming_surface_xrefs_the_anchor(self):
        missing = [
            str(path)
            for path in CONSUMING_SURFACES
            if VERDICT_ANCHOR not in path.read_text(encoding='utf-8')
        ]

        assert len(CONSUMING_SURFACES) == 4, 'the consuming-surface population changed'
        assert missing == [], f'consuming surfaces that do not xref the anchor: {missing}'

    def test_no_consuming_surface_restates_the_grammar(self):
        # The sharper per-file assertion: the two tokens with no plausible
        # non-grammar use, so a PARTIAL restatement fails too — not only a
        # complete one, which the five-token conjunction alone would miss.
        offenders = [
            (str(path), token)
            for path in CONSUMING_SURFACES
            for token in GRAMMAR_ONLY_TOKENS
            if token in path.read_text(encoding='utf-8')
        ]

        assert offenders == [], f'consuming surfaces restating grammar tokens: {offenders}'

    def test_the_tool_declares_exactly_one_emitter_and_one_parser(self):
        declared = _declared_invocations()

        emitters = sorted(name for name in declared if name.endswith('set-verdict'))
        parsers = sorted(name for name in declared if name.endswith('verdicts'))

        assert len(declared) > 0, 'the argparse declaration yielded no invocations'
        assert emitters == ['corpus set-verdict'], f'expected exactly one emitter, found {emitters}'
        assert parsers == ['corpus verdicts'], f'expected exactly one parser, found {parsers}'

    def test_a_stamped_verdict_round_trips_with_every_key_intact(self, plan_context):
        # The separator inside the evidence is the case a naive full split loses.
        evidence = f'left{VERDICT_SEPARATOR}middle{VERDICT_SEPARATOR}right'
        _write_fixture_spec(plan_context)

        cmd_corpus_set_verdict(_stamp(evidence=evidence))
        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['claims_scanned'] == 1, 'the claim population did not materialize'
        row = result['claims'][0]
        assert row['evidence'] == evidence
        for key in VERDICT_KEYS:
            assert row[key], f'{key} did not survive the round trip'
