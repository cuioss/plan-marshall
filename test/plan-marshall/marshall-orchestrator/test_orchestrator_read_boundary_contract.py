#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Doc-contract tests pinning the orchestrator read/write boundary (deliverable 3).

The pinned contract: **no governed document states an orchestrator read
prohibition covering a path that another governed document states is readable.**

The orchestrator's carve-out was originally authored as a single
"direct-file-access" rule governing Read, Write and Edit together. That
conflation was self-contradicting: the strict half declared any Read outside the
epic's own tree out of bounds, while the small-ops half explicitly sanctioned
reading code, artifacts, PRs and logs to verify claims. The boundary is now split
by dimension — writes are bounded to the epic's own tree, reads are unrestricted
in location and bounded only by the "anything larger becomes a plan" category
threshold. This module guards that split against re-divergence.

The detector is **population-derived**: it enumerates the governed document set at
test time and scans it, never a hard-coded file list. A hard-coded list would pass
vacuously the moment another document reintroduces the prohibition, which is the
exact failure this module exists to prevent.

The governed population is the union of three surfaces, matching the document set
the deliverable-2 sweep covers — a guard whose population is narrower than the fix
set's population is vacuous on exactly the gap the sweep found:

1. every ``*.md`` under ``MARKETPLACE_ROOT``, **union**
2. every ``*.adoc`` under ``PROJECT_ROOT / 'doc'``, recursively, **union**
3. ``PROJECT_ROOT / 'CLAUDE.md'``.

Because the population spans two markup languages, sentence extraction dispatches
on file extension and handles AsciiDoc surface forms (``* `` bullets, ``*bold*``,
``link:``/``xref:`` macros) as well as Markdown ones.

Non-vacuity is pinned by two negative fixtures carrying the pre-fix text verbatim
in each markup language. They are the accepted substitute for a red-first pre-fix
run: a red-first ordering would fail this deliverable's own phase-5 verification
and stall the pipeline, while the fixtures supply the same anti-vacuity evidence
without a red pipeline. Do not regress this design.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT

# ---------------------------------------------------------------------------
# Governed population
# ---------------------------------------------------------------------------

_DOC_ROOT = PROJECT_ROOT / 'doc'
_CLAUDE_MD = PROJECT_ROOT / 'CLAUDE.md'

#: The three orchestrator documents whose presence proves ``MARKETPLACE_ROOT``
#: resolved to a real tree rather than an empty one.
_ORCHESTRATION_MODEL = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'persona-marshall-orchestrator'
    / 'standards'
    / 'orchestration-model.md'
)
_MARSHALL_ORCHESTRATOR_SKILL = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'marshall-orchestrator' / 'SKILL.md'
)
_PERSONA_ORCHESTRATOR_SKILL = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'persona-marshall-orchestrator' / 'SKILL.md'
)
#: The marketplace-external restatement. Its presence proves ``PROJECT_ROOT /
#: 'doc'`` resolved, rather than silently shrinking the population to
#: marketplace-only — the precise vacuity the widening exists to prevent.
_CONCEPTS_ORCHESTRATION = _DOC_ROOT / 'concepts' / 'orchestration.adoc'


@lru_cache(maxsize=1)
def _governed_population() -> tuple[Path, ...]:
    """Enumerate the governed document population at call time.

    Returns marketplace ``*.md`` ∪ ``doc/**/*.adoc`` ∪ ``CLAUDE.md``, sorted for
    determinism. Never a hard-coded list — the enumeration IS the guard.
    """
    docs: list[Path] = []
    docs.extend(sorted(MARKETPLACE_ROOT.rglob('*.md')))
    docs.extend(sorted(_DOC_ROOT.rglob('*.adoc')))
    if _CLAUDE_MD.is_file():
        docs.append(_CLAUDE_MD)
    return tuple(docs)


# ---------------------------------------------------------------------------
# Markup-aware sentence extraction
# ---------------------------------------------------------------------------

_MD_LINK_RE = re.compile(r'\[([^\]]*)\]\([^)]*\)')
_ADOC_MACRO_RE = re.compile(r'(?:link|xref):[^\[\s]*\[([^\]]*)\]')
_MD_BULLET_RE = re.compile(r'^\s*(?:[-*+]\s+|\d+\.\s+)')
_ADOC_BULLET_RE = re.compile(r'^\s*(?:\*+\s+|\.+\s+|-\s+)')
_MD_HEADING_RE = re.compile(r'^\s*#{1,6}\s+(.*)$')
_ADOC_HEADING_RE = re.compile(r'^\s*={1,6}\s+(.*)$')
_BOLD_RE = re.compile(r'\*{1,2}([^*]+)\*{1,2}')
_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')


def _normalize_line(line: str, suffix: str) -> str:
    """Strip markup surface forms so the detector sees plain prose.

    ``suffix`` selects the dialect: ``.adoc`` uses AsciiDoc bullet and macro
    forms, everything else uses Markdown ones. Extension-driven dispatch is
    sufficient here — no full parser is warranted.
    """
    text = line
    if suffix == '.adoc':
        text = _ADOC_MACRO_RE.sub(r'\1', text)
        text = _ADOC_BULLET_RE.sub('', text)
    else:
        text = _MD_LINK_RE.sub(r'\1', text)
        text = _MD_BULLET_RE.sub('', text)
    text = _BOLD_RE.sub(r'\1', text)
    return text.strip()


def _heading_of(line: str, suffix: str) -> str | None:
    """Return the heading text when ``line`` is a heading, else ``None``."""
    pattern = _ADOC_HEADING_RE if suffix == '.adoc' else _MD_HEADING_RE
    match = pattern.match(line)
    return match.group(1).strip() if match else None


def _sentences(text: str) -> list[str]:
    """Split a normalized line into sentences, dropping empties."""
    return [part.strip() for part in _SENTENCE_SPLIT_RE.split(text) if part.strip()]


def _iter_scoped_sentences(document: Path) -> list[tuple[int, str, str]]:
    """Yield ``(line_number, sentence, enclosing_heading)`` for one document."""
    suffix = document.suffix
    heading = ''
    out: list[tuple[int, str, str]] = []
    for lineno, raw in enumerate(document.read_text(encoding='utf-8').splitlines(), start=1):
        found = _heading_of(raw, suffix)
        if found is not None:
            heading = found
            continue
        normalized = _normalize_line(raw, suffix)
        if not normalized:
            continue
        for sentence in _sentences(normalized):
            out.append((lineno, sentence, heading))
    return out


# ---------------------------------------------------------------------------
# Canonical path vocabulary
# ---------------------------------------------------------------------------

#: The path classes the read boundary reasons about. Each maps a set of surface
#: spellings to one canonical id, so a prohibition and a permission that name the
#: same surface with different words still intersect.
_PATH_TOKENS: dict[str, tuple[str, ...]] = {
    'repository-source': ('repository source',),
    'plan-artifacts': ('.plan/local/plans/', 'plan artifacts'),
    'other-epic-tree': ("another epic's tree", "other epics' trees", "other epic's tree"),
}

#: The full canonical set — what an exclusive construction ("only within its own
#: tree") covers when it names no explicit out-of-bounds list, since everything
#: outside the epic tree is then prohibited.
_ALL_PATHS = frozenset(_PATH_TOKENS)


def _paths_named(sentence: str) -> frozenset[str]:
    lowered = sentence.lower()
    return frozenset(
        canonical
        for canonical, spellings in _PATH_TOKENS.items()
        if any(spelling.lower() in lowered for spelling in spellings)
    )


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------

#: A sentence mentions reading when any of these appear as whole words.
_READ_TOKEN_RE = re.compile(r'\bread(?:s|ing|able)?\b', re.IGNORECASE)

#: Prohibitive / exclusive constructions that make a read-mentioning sentence a
#: read PROHIBITION rather than a description.
_PROHIBITION_MARKERS: tuple[str, ...] = (
    'out of bounds',
    'permitted only within',
    'only within',
    'never read',
    'must not read',
    'may not read',
    'cannot read',
    'not permitted to read',
)

#: Exclusive constructions that bound reads to the epic tree without naming an
#: explicit out-of-bounds list — they cover every canonical path by implication.
_EXCLUSIVE_MARKERS: tuple[str, ...] = ('permitted only within', 'only within')

#: Sentences whose grammatical subject is a PLAN, not the orchestrator. The
#: ledger write-boundary legitimately says "a plan never reads the ledger"; that
#: is a different contract and must not be mistaken for an orchestrator read
#: prohibition.
_PLAN_SUBJECT_RE = re.compile(r'^(?:a|an|the)\s+(?:executing\s+)?plan\b', re.IGNORECASE)

#: Grants of read access. The small-ops read-only-analysis clause is the canonical
#: one; the others catch equivalent phrasings.
_PERMISSION_MARKERS: tuple[str, ...] = (
    'read-only analysis',
    'reads are unrestricted',
    'are all readable',
)


def _is_orchestrator_document(document: Path) -> bool:
    """True for the documents that GOVERN the orchestrator.

    Used to scope read PERMISSIONS only. A grant lives under a section heading
    ("Small-ops carve-out") that does not repeat the word "orchestrator", so
    sentence-level scoping alone would drop it and leave the intersection
    assertion vacuous. Prohibitions keep the strict sentence-level scoping below,
    so a prohibition reintroduced in ANY governed document is still caught.
    """
    return 'orchestrator' in str(document).lower()


def _is_orchestrator_scoped(sentence: str, heading: str) -> bool:
    if _PLAN_SUBJECT_RE.match(sentence):
        return False
    haystack = f'{sentence}\n{heading}'.lower()
    return 'orchestrator' in haystack


def _prohibited_paths(sentence: str) -> frozenset[str]:
    """The path classes a prohibitive sentence puts out of bounds for reading.

    An exclusive construction that names no explicit out-of-bounds list ("only
    within its own tree") covers every canonical class by implication.
    """
    named = _paths_named(sentence)
    if named:
        return named
    lowered = sentence.lower()
    if any(marker in lowered for marker in _EXCLUSIVE_MARKERS):
        return _ALL_PATHS
    return frozenset()


def _is_read_prohibition(sentence: str) -> bool:
    """True when the sentence prohibits reading a NAMED path class.

    The path requirement is load-bearing: unrelated prose such as "``compose``
    never reads or writes it" or "silence is never read as success" carries a
    prohibition marker and a read token but bounds no path, and is not a read
    boundary statement.
    """
    if not _READ_TOKEN_RE.search(sentence):
        return False
    lowered = sentence.lower()
    if not any(marker in lowered for marker in _PROHIBITION_MARKERS):
        return False
    return bool(_prohibited_paths(sentence))


def _is_read_permission(sentence: str) -> bool:
    lowered = sentence.lower()
    return any(marker in lowered for marker in _PERMISSION_MARKERS)


def _scan() -> tuple[list[tuple[Path, int, str]], set[str], set[str]]:
    """Scan the population once.

    Returns the flagged prohibition sites, the union of prohibited-read paths, and
    the union of permitted-read paths.
    """
    prohibitions: list[tuple[Path, int, str]] = []
    prohibited: set[str] = set()
    permitted: set[str] = set()
    for document in _governed_population():
        governs_orchestrator = _is_orchestrator_document(document)
        for lineno, sentence, heading in _iter_scoped_sentences(document):
            if _is_orchestrator_scoped(sentence, heading) and _is_read_prohibition(sentence):
                prohibitions.append((document, lineno, sentence))
                prohibited |= _prohibited_paths(sentence)
            elif governs_orchestrator and _is_read_permission(sentence):
                permitted |= _paths_named(sentence)
    return prohibitions, prohibited, permitted


# ---------------------------------------------------------------------------
# Positive-population guard
# ---------------------------------------------------------------------------


def test_population_is_non_empty():
    """A broken MARKETPLACE_ROOT must fail loudly, not shrink the scan to nothing."""
    population = _governed_population()

    assert population, 'governed document population is empty — root resolution is broken'


def test_population_contains_the_three_orchestrator_documents():
    population = set(_governed_population())

    for expected in (
        _ORCHESTRATION_MODEL,
        _MARSHALL_ORCHESTRATOR_SKILL,
        _PERSONA_ORCHESTRATOR_SKILL,
    ):
        assert expected in population, f'{expected} missing from the governed population'


def test_population_adoc_slice_is_non_empty():
    """Guards the widening: a broken ``doc`` resolution must not silently pass."""
    adocs = [doc for doc in _governed_population() if doc.suffix == '.adoc']

    assert adocs, f'no .adoc documents enumerated under {_DOC_ROOT} — doc root did not resolve'


def test_population_contains_the_marketplace_external_restatement():
    population = set(_governed_population())

    assert _CONCEPTS_ORCHESTRATION in population, (
        f'{_CONCEPTS_ORCHESTRATION} missing from the governed population — the guard would be '
        'vacuous on the exact marketplace-external surface the sweep found'
    )


def test_population_contains_claude_md():
    population = set(_governed_population())

    assert _CLAUDE_MD in population, f'{_CLAUDE_MD} missing from the governed population'


# ---------------------------------------------------------------------------
# Non-vacuity guard (negative fixtures, verbatim pre-fix text)
# ---------------------------------------------------------------------------

#: The pre-fix ``orchestration-model.md:91`` sentence, verbatim.
_PRE_FIX_MARKDOWN = (
    "Any Read/Write/Edit outside the epic's own `{slug}/` tree — repository source, "
    "another epic's tree, `.plan/local/plans/` — is out of bounds for the orchestrator."
)

#: The pre-fix ``doc/concepts/orchestration.adoc:31`` bullet, verbatim.
_PRE_FIX_ASCIIDOC = (
    '* **Direct file access** — Read/Write/Edit only within its own '
    '`.plan/local/orchestrator/{slug}/` tree (the ledger documents are free-form authored '
    'artifacts); logging and status transitions stay script-mediated even inside the tree.'
)


def test_detector_flags_the_pre_fix_markdown_sentence():
    """Without this the detector could stop matching after a rewording and pass forever."""
    normalized = _normalize_line(_PRE_FIX_MARKDOWN, '.md')
    sentence = _sentences(normalized)[0]

    assert _is_orchestrator_scoped(sentence, '')
    assert _is_read_prohibition(sentence)
    assert _prohibited_paths(sentence) == {
        'repository-source',
        'plan-artifacts',
        'other-epic-tree',
    }


def test_detector_flags_the_pre_fix_asciidoc_bullet():
    """Proves the AsciiDoc surface form is genuinely parsed, not silently skipped."""
    normalized = _normalize_line(_PRE_FIX_ASCIIDOC, '.adoc')
    sentence = _sentences(normalized)[0]

    assert _is_orchestrator_scoped(sentence, '')
    assert _is_read_prohibition(sentence)
    # The bullet names no explicit out-of-bounds list, so its exclusive
    # construction covers every canonical path by implication.
    assert _prohibited_paths(sentence) == _ALL_PATHS


def test_detector_does_not_flag_the_plan_side_ledger_clause():
    """The ledger write-boundary's "a plan never reads the ledger" is a different contract."""
    sentence = 'A plan never reads the ledger to make a decision.'

    assert not _is_orchestrator_scoped(sentence, 'Ledger Write-Boundary')


# ---------------------------------------------------------------------------
# The contradiction assertion
# ---------------------------------------------------------------------------


def test_read_permission_extractor_is_non_vacuous():
    """The permitted set must be populated, or the intersection assertion is vacuous."""
    _, _, permitted = _scan()

    assert permitted == _ALL_PATHS, (
        'the governed documents no longer grant orchestrator reads over all three canonical '
        f'path classes — extracted {sorted(permitted)}, expected {sorted(_ALL_PATHS)}'
    )


def test_no_document_prohibits_a_read_another_document_permits():
    prohibitions, prohibited, permitted = _scan()

    contradiction = prohibited & permitted
    offenders = '\n'.join(
        f'  {path.relative_to(PROJECT_ROOT)}:{lineno}: {sentence}'
        for path, lineno, sentence in prohibitions
    )

    assert not contradiction, (
        'orchestrator read/write boundary has re-diverged — these path classes are both '
        f'prohibited and permitted for reading: {sorted(contradiction)}\n'
        f'offending read-prohibition sites:\n{offenders}'
    )
