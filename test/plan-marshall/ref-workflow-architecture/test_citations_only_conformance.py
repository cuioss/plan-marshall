#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Conformance detector for the citations-only return shape.

``ref-workflow-architecture/standards/citations-only-return.md`` is the single
source of truth for the return shape every read-only dispatch uses: one TOON
summary, detail persisted to a structured sink, no free prose. The rule used to
live inlined inside ``phase-3-outline/standards/component-analysis-contract.md``
(§ Output Format and Critical Rule 1), where a second applying dispatch site had
no way to reference it except by copying it.

These tests pin the delegation invariant:

(a) Every entry on the standard's ``## Applies to`` roster resolves to a real
    document.
(b) Every rostered document **delegates** to the standard — it names
    ``citations-only-return.md`` — rather than restating the rule inline.
(c) The standard names the ``execution-context-reader`` untrusted-ingestion
    boundary as explicitly out of scope, so the containment boundary is never
    folded into this economy rule.
(d) Adding a conforming read-only dispatch to the roster is picked up **with no
    detector edit** — the population is parsed out of the roster, never
    hand-maintained in this module.

The population is derived, never hardcoded. A hardcoded site list would pass
vacuously the moment a new dispatch site is rostered, which is precisely the
drift this detector exists to catch. The restatement detector carries a mutation
guard asserting it fires on the exact pre-fix text, so a regex typo cannot make
this module vacuously green.
"""

from __future__ import annotations

import re
from pathlib import Path

from _dispatch_roster import parse_roster, parse_roster_rows
from conftest import MARKETPLACE_ROOT, PROJECT_ROOT

_STANDARD = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'ref-workflow-architecture'
    / 'standards'
    / 'citations-only-return.md'
)

_APPLIES_TO_HEADING = '## Applies to'

#: The delegation marker: a conforming doc names the standard by filename.
_STANDARD_FILENAME = 'citations-only-return.md'

#: Inline-restatement patterns. Each matched the pre-fix
#: ``component-analysis-contract.md`` text that this standard replaced:
#:   "Single TOON summary — no other text output."      -> no-text-output
#:   "**No text output** except the final TOON summary" -> no-text-output
#:                                                      -> except-final-toon
_RESTATEMENT_PATTERNS = (
    ('no-text-output', re.compile(r'no\s+(?:other\s+)?text\s+output', re.IGNORECASE)),
    (
        'except-final-toon',
        re.compile(r'except\s+the\s+final\s+TOON\s+summary', re.IGNORECASE),
    ),
)

#: The exact pre-fix sentences the delegation replaced. The mutation guard feeds
#: these to the detector to prove it is not vacuous.
_PRE_FIX_SAMPLES = (
    'Single TOON summary — no other text output. All analysis detail is '
    'persisted to assessments.jsonl.',
    '1. **No text output** except the final TOON summary — all reasoning goes '
    'to assessments.jsonl',
)


def _rostered_paths(standard_text: str) -> list[str]:
    """Parse the ``## Applies to`` roster into repo-relative document paths."""
    return parse_roster(standard_text, _APPLIES_TO_HEADING)


def _restatements(doc_text: str) -> list[str]:
    """Return the names of every inline-restatement pattern that fires."""
    return [name for name, pattern in _RESTATEMENT_PATTERNS if pattern.search(doc_text)]


def _delegates(doc_text: str) -> bool:
    """True when the document names the standard instead of copying its rule."""
    return _STANDARD_FILENAME in doc_text


class TestAppliesToRoster:
    """The roster is the detector's population — it must parse, be non-empty,
    and name documents that actually exist."""

    def test_roster_parses_and_is_non_empty(self):
        # A population of zero would make every downstream assertion vacuous.
        rows = parse_roster_rows(_STANDARD.read_text(encoding='utf-8'), _APPLIES_TO_HEADING)

        assert rows, f'{_APPLIES_TO_HEADING} roster in {_STANDARD.name} parsed no rows'

    def test_every_rostered_entry_resolves_to_a_real_document(self):
        # A roster row names a repo-relative path; a typo must fail loudly here
        # rather than silently shrinking the conformance population.
        missing = [
            rel
            for rel in _rostered_paths(_STANDARD.read_text(encoding='utf-8'))
            if not (PROJECT_ROOT / rel).is_file()
        ]

        assert missing == [], f'Rostered entries that do not resolve: {missing}'

    def test_roster_row_carries_a_reason(self):
        # Each row explains why the site applies; a bare path is an unreviewable
        # roster entry.
        rows = parse_roster_rows(_STANDARD.read_text(encoding='utf-8'), _APPLIES_TO_HEADING)

        bare = [key for key, line in rows if line.strip() == f'- `{key}`']

        assert bare == [], f'Roster rows with no accompanying reason: {bare}'


class TestRosteredDocsDelegate:
    """Every rostered document delegates the return-shape rule to the standard
    rather than carrying its own copy."""

    def test_every_rostered_doc_names_the_standard(self):
        offenders = [
            rel
            for rel in _rostered_paths(_STANDARD.read_text(encoding='utf-8'))
            if not _delegates((PROJECT_ROOT / rel).read_text(encoding='utf-8'))
        ]

        assert offenders == [], (
            f'Rostered docs that never reference {_STANDARD_FILENAME}: {offenders}'
        )

    def test_no_rostered_doc_restates_the_rule_inline(self):
        offenders: dict[str, list[str]] = {}
        for rel in _rostered_paths(_STANDARD.read_text(encoding='utf-8')):
            fired = _restatements((PROJECT_ROOT / rel).read_text(encoding='utf-8'))
            if fired:
                offenders[rel] = fired

        assert offenders == {}, f'Rostered docs still restating the rule inline: {offenders}'

    def test_restatement_detector_fires_on_the_pre_fix_text(self):
        # Mutation guard: the two sentences the delegation replaced MUST trip the
        # detector, otherwise the green above proves nothing.
        fired = [_restatements(sample) for sample in _PRE_FIX_SAMPLES]

        assert all(fired), f'Detector went vacuous on the pre-fix text: {fired}'


class TestStandardScopeExclusion:
    """The untrusted-ingestion boundary is a containment rule, not a return-shape
    economy rule, and the standard must say so in its own text."""

    def test_untrusted_ingestion_boundary_is_named_out_of_scope(self):
        text = _STANDARD.read_text(encoding='utf-8')

        assert '## Out of scope' in text
        assert 'execution-context-reader' in text

    def test_reader_boundary_is_not_on_the_applies_to_roster(self):
        rostered = _rostered_paths(_STANDARD.read_text(encoding='utf-8'))

        assert not any('execution-context-reader' in rel for rel in rostered)


class TestPopulationIsDerived:
    """Adding a conforming site to the roster is picked up with no detector edit
    — the prohibited shape is a hand-maintained site list inside this module."""

    def test_added_roster_entry_is_picked_up_without_editing_the_detector(
        self, tmp_path: Path
    ):
        # Arrange: a synthetic standard whose roster carries one MORE entry than
        # the shipped one — a real, conforming doc that is not rostered today.
        shipped = _STANDARD.read_text(encoding='utf-8')
        extra = (
            'marketplace/bundles/pm-plugin-development/skills/ext-outline-workflow'
            '/workflow/component-analysis.md'
        )
        assert extra not in _rostered_paths(shipped), (
            'fixture stale: the extra entry is already rostered'
        )
        augmented = shipped.replace(
            '\n\n## Out of scope',
            f'\n- `{extra}` — synthetic fixture entry.\n\n## Out of scope',
        )
        (tmp_path / 'augmented.md').write_text(augmented, encoding='utf-8')

        # Act: the SAME parse + conformance helpers, unmodified.
        rostered = _rostered_paths(augmented)

        # Assert: the new entry joined the population and conforms on the same
        # predicates — no branch in this module names it.
        assert extra in rostered
        assert len(rostered) == len(_rostered_paths(shipped)) + 1
        added_text = (PROJECT_ROOT / extra).read_text(encoding='utf-8')
        assert _delegates(added_text)
        assert _restatements(added_text) == []

    def test_detector_names_no_site_outside_the_roster(self):
        # The module's only literal document path is the standard itself; any
        # other hardcoded marketplace doc path would be a site list.
        source = Path(__file__).read_text(encoding='utf-8')
        roster_section_start = source.index('class TestAppliesToRoster')

        # Paths named before the first test class are the module's constants.
        literal_docs = re.findall(
            r"'(marketplace/bundles/[^']+\.md)'", source[:roster_section_start]
        )

        assert literal_docs == [], f'Hardcoded site list in the detector: {literal_docs}'
