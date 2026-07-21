#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Roster-vs-registry closure regression for the finalize dispatched/inline split.

``standards/dispatch-inline-split.md`` is the single source of truth for which
finalize steps dispatch under ``Task: execution-context-{level}`` and which run
inline. It is hand-maintained prose with nothing structurally linking it to the
authoritative registry (``marshal.json`` → ``plan.phase-6-finalize.steps``), so
it drifted: the roster classified a subset of the registered steps while
claiming hardcoded counts that no longer matched.

These tests pin the closure invariant and the count-free rewrite:

(a) Every registered step is classified **exactly once** across the two rosters.
(b) The dispatched and inline rosters are **disjoint**.
(c) **No** step-count claim survives anywhere in ``dispatch-inline-split.md`` or
    in the ``SKILL.md`` § "Dispatched workflows vs inline steps" section. The
    sweep covers the whole document / section rather than two headline
    sentences, so every count claim is covered — a partial removal fails.

Steps are named in the roster by their exact registry key (``default:`` /
``project:`` / ``bundle:skill`` prefix included), so the comparison is a plain
set equality with no normalisation heuristics.
"""

from __future__ import annotations

import json
import re

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT

_SKILL_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize'
_ROSTER_DOC = _SKILL_DIR / 'standards' / 'dispatch-inline-split.md'
_SKILL_DOC = _SKILL_DIR / 'SKILL.md'
_MARSHAL_JSON = PROJECT_ROOT / '.plan' / 'marshal.json'

_DISPATCHED_HEADING = '## Dispatched steps'
_INLINE_HEADING = '## Inline steps'
_SKILL_SECTION_HEADING = '## Dispatched workflows vs inline steps'

#: A roster row names its step as the first backticked token of a list item.
_ROSTER_ROW = re.compile(r'^-\s+`([^`]+)`')

#: Count-bearing prose patterns. Each matched the pre-fix text:
#:   "Of the 17 default + project finalize steps"  -> _COUNT_BEFORE_STEPS
#:   "**6 dispatch**" / "**11 run inline**"        -> _COUNT_BOLD_CLASSIFIER
#:   "is not counted in the 6/17 roster above"     -> _COUNT_RATIO
_COUNT_BEFORE_STEPS = re.compile(r'\b\d+\s[\w\s+]{0,40}?\bsteps?\b', re.IGNORECASE)
_COUNT_BOLD_CLASSIFIER = re.compile(r'\d+\s+(?:dispatch|run\s+inline|inline)\b', re.IGNORECASE)
_COUNT_RATIO = re.compile(r'\b\d+\s*/\s*\d+\s+roster\b', re.IGNORECASE)

_COUNT_CLAIM_PATTERNS = (
    ('count-before-steps', _COUNT_BEFORE_STEPS),
    ('bold-count-classifier', _COUNT_BOLD_CLASSIFIER),
    ('count-ratio-roster', _COUNT_RATIO),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _registered_steps() -> set[str]:
    """Return the authoritative registered finalize-step key set."""
    data = json.loads(_MARSHAL_JSON.read_text(encoding='utf-8'))
    steps = data['plan']['phase-6-finalize']['steps']
    return set(steps.keys())


def _section_lines(text: str, heading: str) -> list[str]:
    """Return the lines between ``heading`` and the next ``## `` heading."""
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:  # pragma: no cover — guarded by its own test
        raise AssertionError(
            f'Heading not found: {heading!r} in the document'
        ) from None
    collected: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith('## '):
            break
        collected.append(line)
    return collected


def _roster(heading: str) -> list[str]:
    """Parse the step keys out of one roster section, preserving order."""
    text = _ROSTER_DOC.read_text(encoding='utf-8')
    keys: list[str] = []
    for line in _section_lines(text, heading):
        match = _ROSTER_ROW.match(line)
        if match:
            keys.append(match.group(1))
    return keys


def _count_claims(text: str) -> list[str]:
    """Return every count-bearing fragment found in ``text``."""
    hits: list[str] = []
    for label, pattern in _COUNT_CLAIM_PATTERNS:
        for match in pattern.finditer(text):
            hits.append(f'{label}: {match.group(0)!r}')
    return hits


# ---------------------------------------------------------------------------
# (a) + (b) closure and disjointness
# ---------------------------------------------------------------------------


def test_every_registered_step_is_classified_exactly_once():
    # Arrange
    registered = _registered_steps()
    dispatched = _roster(_DISPATCHED_HEADING)
    inline = _roster(_INLINE_HEADING)

    # Act
    classified = set(dispatched) | set(inline)

    # Assert — no registered step is unclassified, and no roster row is a ghost.
    unclassified = registered - classified
    assert not unclassified, (
        f'Registered finalize steps missing a dispatched/inline classification '
        f'in dispatch-inline-split.md: {sorted(unclassified)}'
    )
    ghosts = classified - registered
    assert not ghosts, (
        f'Roster rows that name no registered finalize step: {sorted(ghosts)}'
    )
    assert classified == registered


def test_roster_lists_are_disjoint():
    dispatched = _roster(_DISPATCHED_HEADING)
    inline = _roster(_INLINE_HEADING)

    overlap = set(dispatched) & set(inline)

    assert not overlap, (
        f'Steps classified BOTH dispatched and inline (exactly one required): '
        f'{sorted(overlap)}'
    )


def test_roster_rows_carry_no_duplicates():
    for heading in (_DISPATCHED_HEADING, _INLINE_HEADING):
        keys = _roster(heading)
        duplicates = {key for key in keys if keys.count(key) > 1}
        assert not duplicates, f'Duplicate rows under {heading!r}: {sorted(duplicates)}'


def test_both_rosters_are_non_empty():
    # Guards the parser itself: a heading rename that silently yields an empty
    # roster would otherwise make the closure assertions vacuous.
    assert _roster(_DISPATCHED_HEADING)
    assert _roster(_INLINE_HEADING)


def test_finalize_step_simplify_is_classified_dispatched():
    # Pinned explicitly: the pre-fix roster omitted it, while a real run
    # observably dispatched it.
    assert 'default:finalize-step-simplify' in _roster(_DISPATCHED_HEADING)


# ---------------------------------------------------------------------------
# (c) count-free sweep
# ---------------------------------------------------------------------------


def test_roster_document_carries_no_step_count_claim():
    text = _ROSTER_DOC.read_text(encoding='utf-8')

    hits = _count_claims(text)

    assert not hits, (
        f'Step-count claim(s) reintroduced into dispatch-inline-split.md — the '
        f'roster is deliberately count-free: {hits}'
    )


def test_skill_dispatch_section_carries_no_step_count_claim():
    text = _SKILL_DOC.read_text(encoding='utf-8')
    section = '\n'.join(_section_lines(text, _SKILL_SECTION_HEADING))

    hits = _count_claims(section)

    assert not hits, (
        f'Step-count claim(s) reintroduced into the SKILL.md '
        f'"{_SKILL_SECTION_HEADING}" section: {hits}'
    )


def test_count_claim_patterns_detect_the_pre_fix_prose():
    # Mutation guard: the sweep above is only meaningful if these patterns
    # actually fire on the exact prose this deliverable removed. Without this,
    # a typo in the regexes would make both sweeps vacuously green.
    pre_fix_samples = [
        'Of the 17 default + project finalize steps, **6 dispatch** and **11 run inline**.',
        'is not counted in the 6/17 roster above',
        'The 11 inline steps (`finalize-step-sync-baseline`, `push`) are pure scripts.',
    ]

    for sample in pre_fix_samples:
        assert _count_claims(sample), (
            f'Count-claim sweep failed to detect known pre-fix prose: {sample!r}'
        )


# ---------------------------------------------------------------------------
# Built-in dispatch table completeness (the third drifted roster surface)
# ---------------------------------------------------------------------------


def test_builtin_dispatch_table_lists_the_previously_missing_steps():
    text = _SKILL_DOC.read_text(encoding='utf-8')

    assert '| `default:pre-push-quality-gate` |' in text
    assert '| `default:finalize-step-preference-emitter` |' in text
