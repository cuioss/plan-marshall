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
(d) Every row under ``## Dispatched steps`` declares the ``effort
    resolve-target`` lookup it resolves under — the roster's resolver-lookup
    completeness invariant.
(e) Every dispatch branch in ``SKILL.md`` carries a **concrete**
    ``[DISPATCH]`` bash block: no ``Task:`` spawn is unpaired, and no citation
    of the emission contract satisfies the obligation with prose alone.

Steps are named in the roster by their exact registry key (``default:`` /
``project:`` / ``bundle:skill`` prefix included), so the comparison is a plain
set equality with no normalisation heuristics.

The (d) and (e) populations are **derived, never hardcoded**: (d) iterates the
rows the roster parser finds under ``## Dispatched steps``, and (e) iterates the
``Task:`` spawns and emission-contract citations found in ``SKILL.md``. A
hardcoded roster or emit-site list would pass vacuously the moment a row or a
dispatch branch is added, which is precisely the drift these tests exist to
catch. Each detector carries a mutation guard asserting it fires on the exact
pre-fix shape, so a regex typo cannot make it vacuously green.
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

#: A roster row declares its resolver lookup as a backticked ``phase-6-finalize``
#: token, optionally carrying the ``--role`` sub-key it resolves under. Rows that
#: track ``phase-6-finalize.default`` spell the bare phase token plus an explicit
#: "no ``--role``" note, so the bare form is a legitimate declaration.
_RESOLVER_LOOKUP = re.compile(r'`phase-6-finalize(?:\s+--role\s+[\w-]+)?`')

#: The concrete emission: the actual ``--message "[DISPATCH] …"`` bash argument.
#: A prose reference to the emission contract does NOT match.
_CONCRETE_DISPATCH_EMIT = re.compile(r'--message\s+"\[DISPATCH\]')

#: A dispatch branch's ``Task:`` spawn line. ``MULTILINE`` so the same pattern
#: anchors per-line both when matched line-by-line and when swept over the whole
#: document by the vacuity guard.
_TASK_SPAWN = re.compile(r'^\s*Task:\s+plan-marshall:', re.MULTILINE)

#: A citation of the emission contract marks an emit site.
_EMISSION_CONTRACT_CITATION = re.compile(r'dispatch-logging\.md')

#: How far back from a ``Task:`` spawn the paired concrete emit may sit. The
#: widest real gap is the project/skill branch (~16 lines: the emit block, the
#: indivisible-pair paragraph, and the item-(3) preamble); 25 leaves headroom
#: while staying far below the ~300-line distance between distinct branches, so
#: one branch's emit can never satisfy another branch's spawn.
_EMIT_LOOKBACK_LINES = 25

#: How far after an emission-contract citation the concrete block may sit.
_EMIT_LOOKAHEAD_LINES = 15


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


def _roster_rows(heading: str) -> list[tuple[str, str]]:
    """Return ``(step_key, full_row_line)`` for one roster section.

    Shares the ``_section_lines`` + ``_ROSTER_ROW`` machinery ``_roster`` uses,
    so the row population is identical to the one the closure assertions read.
    """
    text = _ROSTER_DOC.read_text(encoding='utf-8')
    rows: list[tuple[str, str]] = []
    for line in _section_lines(text, heading):
        match = _ROSTER_ROW.match(line)
        if match:
            rows.append((match.group(1), line))
    return rows


def _row_declares_resolver_lookup(row: str) -> bool:
    """Whether a roster row declares the resolve-target lookup it resolves under."""
    return bool(_RESOLVER_LOOKUP.search(row))


def _spawns_missing_concrete_emit(text: str) -> list[str]:
    """Return every ``Task:`` spawn not preceded by a concrete ``[DISPATCH]`` emit.

    The population is derived from the spawn sites present in ``text``; nothing
    about how many dispatch branches exist is assumed.
    """
    lines = text.splitlines()
    unpaired: list[str] = []
    for index, line in enumerate(lines):
        if not _TASK_SPAWN.match(line):
            continue
        window = lines[max(0, index - _EMIT_LOOKBACK_LINES) : index]
        if not any(_CONCRETE_DISPATCH_EMIT.search(prior) for prior in window):
            unpaired.append(f'line {index + 1}: {line.strip()!r}')
    return unpaired


def _prose_only_emit_sites(text: str) -> list[str]:
    """Return every emission-contract citation unbacked by a concrete bash block.

    An emit site that cites ``dispatch-logging.md`` but carries no
    ``--message "[DISPATCH] …"`` block within the following window satisfies the
    emission obligation with prose alone — the exact pre-fix shape of the
    wait-region unified-triage hook.
    """
    lines = text.splitlines()
    prose_only: list[str] = []
    for index, line in enumerate(lines):
        if not _EMISSION_CONTRACT_CITATION.search(line):
            continue
        window = lines[index : index + _EMIT_LOOKAHEAD_LINES + 1]
        if not any(_CONCRETE_DISPATCH_EMIT.search(nxt) for nxt in window):
            prose_only.append(f'line {index + 1}: {line.strip()!r}')
    return prose_only


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
# (d) resolver-lookup completeness — population derived from the roster
# ---------------------------------------------------------------------------


def test_every_dispatched_roster_row_declares_a_resolver_lookup():
    # Arrange — the population IS the parsed roster, so a newly-added row is
    # covered automatically rather than needing a hardcoded list extended.
    rows = _roster_rows(_DISPATCHED_HEADING)
    assert rows, 'Dispatched roster parsed empty — the assertion would be vacuous'

    # Act
    lookup_less = [key for key, line in rows if not _row_declares_resolver_lookup(line)]

    # Assert
    assert not lookup_less, (
        f'Dispatched roster rows that declare no `effort resolve-target` lookup — '
        f'every row must name the `--phase` value and its `--role` sub-key (or an '
        f'explicit "no --role"): {sorted(lookup_less)}'
    )


def test_roster_row_population_matches_the_closure_parser():
    # Guards the new parser against silently reading a different population than
    # the closure assertions do — a divergence would make (d) cover a subset.
    assert [key for key, _ in _roster_rows(_DISPATCHED_HEADING)] == _roster(
        _DISPATCHED_HEADING
    )


# ---------------------------------------------------------------------------
# (e) concrete-emit completeness — population derived from SKILL.md
# ---------------------------------------------------------------------------


def test_every_task_spawn_is_paired_with_a_concrete_dispatch_emit():
    # The `[DISPATCH]` write and the `Task:` spawn are one indivisible pair: a
    # spawn with no preceding concrete emit is a contract violation.
    text = _SKILL_DOC.read_text(encoding='utf-8')
    assert _TASK_SPAWN.search(text), (
        'No `Task:` spawn found in SKILL.md — the assertion would be vacuous'
    )

    unpaired = _spawns_missing_concrete_emit(text)

    assert not unpaired, (
        f'`Task:` spawn(s) in phase-6-finalize/SKILL.md with no preceding concrete '
        f'`--message "[DISPATCH] …"` block — the emit and the spawn are one '
        f'indivisible pair: {unpaired}'
    )


def test_no_dispatch_emit_site_is_prose_only():
    # Every citation of the emission contract must be backed by a concrete bash
    # block; prose alone does not discharge the emission obligation.
    text = _SKILL_DOC.read_text(encoding='utf-8')
    assert _EMISSION_CONTRACT_CITATION.search(text), (
        'No emission-contract citation found in SKILL.md — assertion vacuous'
    )

    prose_only = _prose_only_emit_sites(text)

    assert not prose_only, (
        f'Emission-contract citation(s) in phase-6-finalize/SKILL.md unbacked by a '
        f'concrete `--message "[DISPATCH] …"` block — no dispatch branch may satisfy '
        f'the emission obligation with prose alone: {prose_only}'
    )


# ---------------------------------------------------------------------------
# Mutation guards for (d) and (e)
# ---------------------------------------------------------------------------


def test_resolver_lookup_detector_fires_on_the_pre_fix_row():
    # Mutation guard: the (d) sweep is only meaningful if the detector actually
    # rejects the exact lookup-less rows this deliverable completed.
    pre_fix_rows = [
        '- `project:finalize-step-lessons-housekeeping` — `mode: workflow`; reasons '
        'from the just-finished plan\'s outcome about the lessons corpus (remove / '
        'promote-then-retire / trim), so it earns an envelope',
        '- `project:finalize-step-review-retrospective` — `mode: workflow`; hybrid by '
        'construction — a deterministic per-reviewer metrics pass augmented by an LLM '
        'qualitative judgment and comparative verdict',
    ]
    for row in pre_fix_rows:
        assert not _row_declares_resolver_lookup(row), (
            f'Resolver-lookup detector failed to reject a known lookup-less row: {row!r}'
        )

    # Positive control — the post-fix shapes ARE accepted, so the detector is not
    # unconditionally negative.
    post_fix_rows = [
        '- `project:finalize-step-review-retrospective` — → `phase-6-finalize` (no '
        '`--role`; tracks `phase-6-finalize.default`); `mode: workflow`',
        '- `project:finalize-step-plugin-doctor` — → `phase-6-finalize --role '
        'verification-feedback` (`producer=plugin-doctor` runtime input)',
    ]
    for row in post_fix_rows:
        assert _row_declares_resolver_lookup(row), (
            f'Resolver-lookup detector rejected a valid post-fix row: {row!r}'
        )


def test_concrete_emit_detectors_fire_on_the_pre_fix_prose_only_site():
    # Mutation guard: reproduce the pre-fix wait-region unified-triage hook — an
    # emission-contract citation followed straight by the `Task:` spawn, with no
    # concrete bash block anywhere between them.
    pre_fix = '\n'.join(
        [
            '      (1) Resolve the level-bound target under the role:',
            '      (2) Emit the standardized `[DISPATCH]` work-log line (see',
            '          [`dispatch-logging.md`](../x/dispatch-logging.md) § Emission contract).',
            '      (3) Dispatch ONE `verification-feedback` envelope:',
            '          ```text',
            '          Task: plan-marshall:{target}',
            '            prompt: |',
            '              name: wait-region-unified-triage',
            '          ```',
        ]
    )

    assert _prose_only_emit_sites(pre_fix), (
        'Prose-only detector failed to flag the known pre-fix emit site'
    )
    assert _spawns_missing_concrete_emit(pre_fix), (
        'Unpaired-spawn detector failed to flag the known pre-fix `Task:` spawn'
    )

    # Positive control — the post-fix shape clears BOTH detectors, so neither is
    # unconditionally positive.
    post_fix = '\n'.join(
        [
            '      (2) Emit the standardized `[DISPATCH]` work-log line (see',
            '          [`dispatch-logging.md`](../x/dispatch-logging.md) § Emission contract).',
            '          ```bash',
            '          python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \\',
            '            work --plan-id {plan_id} --level INFO \\',
            '            --message "[DISPATCH] (plan-marshall:phase-6-finalize) '
            'target={target} role=verification-feedback plan_id={plan_id}"',
            '          ```',
            '      (3) Dispatch ONE `verification-feedback` envelope:',
            '          ```text',
            '          Task: plan-marshall:{target}',
            '          ```',
        ]
    )

    assert not _prose_only_emit_sites(post_fix)
    assert not _spawns_missing_concrete_emit(post_fix)


# ---------------------------------------------------------------------------
# Built-in dispatch table completeness (the third drifted roster surface)
# ---------------------------------------------------------------------------


def test_builtin_dispatch_table_lists_the_previously_missing_steps():
    text = _SKILL_DOC.read_text(encoding='utf-8')

    assert '| `default:pre-push-quality-gate` |' in text
    assert '| `default:finalize-step-preference-emitter` |' in text
