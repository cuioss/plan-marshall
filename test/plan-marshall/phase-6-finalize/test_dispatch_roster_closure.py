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
(e) Every dispatch branch in ``SKILL.md`` § "Step 3: Execute Step Pipeline"
    carries a **concrete** ``[DISPATCH]`` bash block: no ``Task:`` spawn is
    unpaired, and no citation of the emission contract satisfies the obligation
    with prose alone. The sweep is scoped to that one section — the section
    that holds every dispatch branch the document has — so a
    ``dispatch-logging.md`` reference in unrelated prose (a cross-reference
    table, say) is not misread as an unbacked emit site.
(f) Every step doc in this plan's own touched population that **self-classifies**
    (asserts "This step is \\*\\*inline\\*\\*" / "\\*\\*dispatched\\*\\*" in its own
    body) agrees with the roster: an inline-asserting doc's step appears under
    ``## Inline steps`` and NOT under ``## Dispatched steps``, and vice versa.
    This is the cross-document consistency check — the roster and the executor
    doc are two sources that can disagree, and ``default:architecture-refresh``
    is the case that did: its executor doc asserted inline while the roster
    classified it dispatched.

Steps are named in the roster by their exact registry key (``default:`` /
``project:`` / ``bundle:skill`` prefix included), so the comparison is a plain
set equality with no normalisation heuristics.

The (d), (e) and (f) populations are **derived, never hardcoded**: (d) iterates
the rows the roster parser finds under ``## Dispatched steps``, (e) iterates the
``Task:`` spawns and emission-contract citations found in that ``SKILL.md``
section, and (f) reads each step doc's OWN self-classification sentence rather
than asserting a ``default:architecture-refresh`` literal. A
hardcoded roster or emit-site list would pass vacuously the moment a row or a
dispatch branch is added, which is precisely the drift these tests exist to
catch — and an ``assert 'default:architecture-refresh' in inline`` literal would
pass vacuously the instant the pair is fixed, detecting nothing else ever again.
Each detector carries a mutation guard asserting it fires on the exact
pre-fix shape, so a regex typo cannot make it vacuously green.

(f)'s **file** population is deliberately bounded to the step docs this plan
itself mutates (deliverable 1's and deliverable 2's affected step docs, plus
``standards/architecture-refresh.md``) — it is NOT the general roster-vs-step-doc
mismatch population, which is owned by the sibling epic
``code-intelligence-substrate`` PLAN-121 (D5b/D5c) and spans every registered
step. Widening (f) to all registered steps would duplicate that sibling's
surface; the bounding is a scope decision, not an oversight.
"""

from __future__ import annotations

import json
import re

from _dispatch_roster import parse_roster, parse_roster_rows, section_lines
from conftest import MARKETPLACE_ROOT, PROJECT_ROOT

_SKILL_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize'
_ROSTER_DOC = _SKILL_DIR / 'standards' / 'dispatch-inline-split.md'
_SKILL_DOC = _SKILL_DIR / 'SKILL.md'
_MARSHAL_JSON = PROJECT_ROOT / '.plan' / 'marshal.json'

_DISPATCHED_HEADING = '## Dispatched steps'
_INLINE_HEADING = '## Inline steps'
_SKILL_SECTION_HEADING = '## Dispatched workflows vs inline steps'

#: The one ``SKILL.md`` section that carries every dispatch branch. The (e)
#: sweeps are scoped to it so a ``dispatch-logging.md`` link in unrelated prose
#: (e.g. the trailing ``## Related`` table) is not read as an emit site — the
#: exact false positive raised in review. The scoping drops no dispatch branch:
#: every ``Task: plan-marshall:`` spawn and every emission-contract citation in
#: the document today lies inside this section.
_SKILL_STEP3_HEADING = (
    '### Step 3: Execute Step Pipeline (Manifest-Driven, Resumable, Timeout-Wrapped)'
)

#: Terminate the Step-3 scope at the next ``### `` step heading as well as at
#: the next ``## `` heading. The bare ``('## ',)`` default does NOT stop at
#: ``### Step 4`` (``'### Step 4'.startswith('## ')`` is ``False``), which would
#: silently run the section to EOF and make the scoping a no-op. ``#### ``
#: sub-headings inside Step 3 correctly do not terminate it, for the same
#: prefix-comparison reason.
_SKILL_SECTION_STOP_PREFIXES = ('## ', '### ')

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

#: (f) The bounded step-doc population for the cross-document consistency check:
#: the step docs this plan's deliverable 1 and deliverable 2 touch, plus
#: ``standards/architecture-refresh.md``. Repo-relative so ``.claude/skills/``
#: project steps sit in the same list as the bundle-resident ones. Bounded on
#: purpose — the all-registered-steps population belongs to the sibling epic's
#: PLAN-121 (D5b/D5c); see the module docstring.
_D5E_STEP_DOC_PATHS = (
    'marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/architecture-refresh.md',
    'marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md',
    'marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md',
    'marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md',
    'marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/'
    'finalize-step-security-audit.md',
    'marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/'
    'pre-submission-self-review.md',
    'marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/sonar-roundtrip.md',
    'marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md',
    '.claude/skills/finalize-step-plugin-doctor/SKILL.md',
    '.claude/skills/finalize-step-era-stamp-fill/SKILL.md',
)

#: A step doc's own classification claim. The wording is the canonical
#: self-classification sentence (``architecture-refresh.md`` § "This step is
#: **inline** …"). The bold marker is load-bearing: it distinguishes a
#: *classification assertion* from narrative uses of the words — "This step runs
#: as inline orchestration …" (``sonar-roundtrip.md``, ``automatic-review``) and
#: "the dispatched prompt loads …" (``finalize-step-simplify.md``) are prose
#: about HOW the step behaves, not a roster classification, and reading them as
#: claims would drag this bounded check into the sibling epic's population.
_SELF_CLASSIFICATION = re.compile(r'\bThis step is \*\*(inline|dispatched)\*\*')

#: A step doc's frontmatter ``name:`` value. Searched inside the frontmatter
#: block only — the body carries ``name: <step-name>`` lines inside dispatch
#: prompt examples that must not be mistaken for the doc's own identity.
_FRONTMATTER_NAME = re.compile(r'^name:\s*(.+?)\s*$', re.MULTILINE)

#: Registry-key prefixes a bare frontmatter ``name:`` may resolve under.
_REGISTRY_KEY_PREFIXES = ('', 'default:', 'project:', 'plan-marshall:')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _registered_steps() -> set[str]:
    """Return the authoritative registered finalize-step key set."""
    data = json.loads(_MARSHAL_JSON.read_text(encoding='utf-8'))
    steps = data['plan']['phase-6-finalize']['steps']
    return set(steps.keys())


def _roster(heading: str) -> list[str]:
    """Parse the step keys out of one roster section, preserving order.

    Delegates to the shared ``_dispatch_roster`` parser (``test/_shared/``) so
    the row population is identical to the one
    ``test_step_termination_contract.py``'s reachability check reads — the
    two suites cannot silently drift apart one heading-walk at a time.
    """
    text = _ROSTER_DOC.read_text(encoding='utf-8')
    return parse_roster(text, heading)


def _count_claims(text: str) -> list[str]:
    """Return every count-bearing fragment found in ``text``."""
    hits: list[str] = []
    for label, pattern in _COUNT_CLAIM_PATTERNS:
        for match in pattern.finditer(text):
            hits.append(f'{label}: {match.group(0)!r}')
    return hits


def _roster_rows(heading: str) -> list[tuple[str, str]]:
    """Return ``(step_key, full_row_line)`` for one roster section.

    Delegates to the shared ``_dispatch_roster`` parser, so the row
    population is identical to the one ``_roster`` reads.
    """
    text = _ROSTER_DOC.read_text(encoding='utf-8')
    return parse_roster_rows(text, heading)


def _row_declares_resolver_lookup(row: str) -> bool:
    """Whether a roster row declares the resolve-target lookup it resolves under."""
    return bool(_RESOLVER_LOOKUP.search(row))


def _dispatch_branch_scoped_skill_text() -> str:
    """Return ``SKILL.md`` with every line outside the dispatch-branch section blanked.

    Blanking rather than slicing keeps the line count — and therefore every
    index the (e) detectors report — identical to the real document, so a
    reported ``line N`` still names the actual ``SKILL.md`` line. The detectors
    themselves keep taking raw text, so their mutation guards can go on feeding
    them synthetic snippets; the scoping lives here, at the call sites.

    Raises:
        AssertionError: via ``section_lines`` when the heading is renamed —
        a loud failure rather than a silently empty (vacuous) sweep.
    """
    text = _SKILL_DOC.read_text(encoding='utf-8')
    lines = text.splitlines()
    section = section_lines(
        text, _SKILL_STEP3_HEADING, stop_prefixes=_SKILL_SECTION_STOP_PREFIXES
    )
    heading_index = next(
        index
        for index, line in enumerate(lines)
        if line.strip() == _SKILL_STEP3_HEADING
    )
    start = heading_index + 1
    scoped = [''] * len(lines)
    scoped[start : start + len(section)] = section
    return '\n'.join(scoped)


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


def _frontmatter_name(text: str) -> str | None:
    """Return the ``name:`` value from a doc's YAML frontmatter block, if present."""
    if not text.startswith('---'):
        return None
    end = text.find('\n---', 3)
    if end == -1:
        return None
    match = _FRONTMATTER_NAME.search(text[3:end])
    return match.group(1).strip() if match else None


def _registry_key(frontmatter_name: str, registered: set[str]) -> str | None:
    """Resolve a doc's frontmatter ``name:`` to its registry key, or ``None``.

    A step doc spells its own name bare (``architecture-refresh``,
    ``finalize-step-plugin-doctor``) or already prefixed
    (``default:architecture-refresh``); the registry keys carry the prefix. Try
    each accepted prefix against the authoritative key set rather than guessing.
    """
    for prefix in _REGISTRY_KEY_PREFIXES:
        candidate = f'{prefix}{frontmatter_name}'
        if candidate in registered:
            return candidate
    return None


def _step_doc_claims() -> list[tuple[str, str, str]]:
    """Return ``(rel_path, registry_key, claim)`` for self-classifying step docs.

    Iterates the bounded (f) population and reads each doc's OWN classification
    sentence. Docs that make no classification claim contribute nothing — the
    check is about *disagreement* between two sources, so a doc that asserts
    nothing cannot disagree with the roster.
    """
    registered = _registered_steps()
    claims: list[tuple[str, str, str]] = []
    for rel in _D5E_STEP_DOC_PATHS:
        text = (PROJECT_ROOT / rel).read_text(encoding='utf-8')
        match = _SELF_CLASSIFICATION.search(text)
        if not match:
            continue
        name = _frontmatter_name(text)
        assert name, f'{rel} self-classifies but declares no frontmatter `name:`'
        key = _registry_key(name, registered)
        assert key, (
            f'{rel} declares frontmatter name {name!r}, which resolves to no '
            f'registered finalize-step key'
        )
        claims.append((rel, key, match.group(1)))
    return claims


def _classification_mismatches(
    claims: list[tuple[str, str, str]],
    dispatched: set[str],
    inline: set[str],
) -> list[str]:
    """Return one message per step doc whose self-claim contradicts the roster.

    Kept pure over its three inputs so the mutation guard can drive it with the
    exact pre-fix roster text and claim, without touching the real documents.
    """
    mismatches: list[str] = []
    for rel, key, claim in claims:
        expected, opposite = (
            (inline, dispatched) if claim == 'inline' else (dispatched, inline)
        )
        if key in expected and key not in opposite:
            continue
        mismatches.append(
            f'{rel}: the step doc asserts **{claim}** for {key!r}, but the roster '
            f'has dispatched={key in dispatched} inline={key in inline}'
        )
    return mismatches


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
    section = '\n'.join(section_lines(text, _SKILL_SECTION_HEADING))

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
    text = _dispatch_branch_scoped_skill_text()
    assert _TASK_SPAWN.search(text), (
        'No `Task:` spawn found in the SKILL.md '
        f'"{_SKILL_STEP3_HEADING}" section — the assertion would be vacuous'
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
    text = _dispatch_branch_scoped_skill_text()
    assert _EMISSION_CONTRACT_CITATION.search(text), (
        'No emission-contract citation found in the SKILL.md '
        f'"{_SKILL_STEP3_HEADING}" section — assertion vacuous'
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
# (f) cross-document consistency — roster vs the step doc's own classification
# ---------------------------------------------------------------------------


def test_d5e_population_step_docs_all_exist():
    # Guards the bounded population against silent shrinkage: a renamed or moved
    # step doc would otherwise drop out of the sweep unnoticed and take its
    # classification claim with it.
    missing = [rel for rel in _D5E_STEP_DOC_PATHS if not (PROJECT_ROOT / rel).exists()]

    assert not missing, (
        f'Step doc(s) in the cross-document consistency population no longer exist — '
        f'update _D5E_STEP_DOC_PATHS in the same change that moves them: {missing}'
    )


def test_touched_step_docs_agree_with_the_roster_classification():
    # Arrange — the claims are READ from the docs, not asserted about a named
    # step, so a second doc gaining a self-classification is covered for free.
    claims = _step_doc_claims()
    assert claims, (
        'No step doc in the cross-document consistency population declares its own '
        'dispatched/inline classification — the assertion would be vacuous'
    )

    # Act
    mismatches = _classification_mismatches(
        claims, set(_roster(_DISPATCHED_HEADING)), set(_roster(_INLINE_HEADING))
    )

    # Assert
    assert not mismatches, (
        f'Step doc(s) whose own classification contradicts dispatch-inline-split.md — '
        f'the roster is the single source of truth and the executor doc states the '
        f'reason, so the two must agree: {mismatches}'
    )


def test_self_classification_detector_matches_the_step_doc_sentence():
    # Mutation guard (detector half): the (f) sweep is only meaningful if the
    # claim regex actually fires on the canonical self-classification sentence.
    sentence = (
        'This step is **inline** (executed directly inside the finalize main context, '
        'not via a separate Task agent) because the Tier-1 `prompt` mode requires an '
        '`AskUserQuestion` interaction.'
    )

    match = _SELF_CLASSIFICATION.search(sentence)

    assert match is not None, (
        'Self-classification detector failed to match architecture-refresh.md\'s '
        'canonical inline sentence'
    )
    assert match.group(1) == 'inline'

    # Negative controls — narrative prose about HOW a step behaves is NOT a
    # classification claim. Reading these as claims would pull the two
    # dispatched wait-region producers into this bounded check and duplicate the
    # sibling epic's roster-vs-step-doc surface.
    narrative_not_a_claim = [
        'This step runs as inline orchestration (producer FIND + verified-scan marker '
        'read in main context) under a **FIND-only 15-minute (900 s) per-agent timeout '
        'budget** enforced by the SKILL.md Step 3 dispatcher.',
        'Domain-agnostic **by construction** — the dispatched prompt loads ONLY the '
        'three domain-invariant foundation standards.',
        'This step is inline because it is cheap.',
    ]
    for narrative in narrative_not_a_claim:
        assert _SELF_CLASSIFICATION.search(narrative) is None, (
            f'Self-classification detector read narrative prose as a classification '
            f'claim: {narrative!r}'
        )


def test_cross_document_consistency_detector_fires_on_the_pre_fix_shape():
    # Mutation guard (comparison half): reproduce the exact pre-fix pair — the
    # `default:architecture-refresh` row sitting under `## Dispatched steps` with
    # its "hybrid, classified dispatched" rationale, against
    # architecture-refresh.md's inline self-assertion.
    pre_fix_roster = '\n'.join(
        [
            '## Dispatched steps',
            '',
            '- `default:sonar-roundtrip` — → `phase-6-finalize` (no `--role`)',
            '- `default:architecture-refresh` — hybrid, classified dispatched: its '
            'Tier 0 discover + diff is deterministic inline script work, and its Tier 1 '
            're-enrichment fans out under `phase-6-finalize` per affected module — the '
            'only per-iteration parallel dispatch in the contract. The dispatching tier '
            'governs the classification, so the step carries exactly one roster row.',
            '',
            '## Inline steps',
            '',
            '- `default:push` — the single push barrier',
        ]
    )
    dispatched = set(parse_roster(pre_fix_roster, _DISPATCHED_HEADING))
    inline = set(parse_roster(pre_fix_roster, _INLINE_HEADING))
    assert 'default:architecture-refresh' in dispatched, (
        'Fixture sanity: the pre-fix roster must place architecture-refresh under '
        'the dispatched heading, or the guard proves nothing'
    )

    claims = [
        (
            'marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/'
            'architecture-refresh.md',
            'default:architecture-refresh',
            'inline',
        )
    ]

    assert _classification_mismatches(claims, dispatched, inline), (
        'Cross-document consistency detector failed to flag the known pre-fix pair '
        '(dispatched roster row vs inline executor-doc assertion)'
    )

    # Positive control — the post-fix rosters clear the detector, so it is not
    # unconditionally positive.
    post_fix_dispatched = dispatched - {'default:architecture-refresh'}
    post_fix_inline = inline | {'default:architecture-refresh'}
    assert not _classification_mismatches(claims, post_fix_dispatched, post_fix_inline)

    # And a doc classified on BOTH rosters is still a mismatch — the check is
    # "exactly one, and the right one", not merely "present somewhere".
    both = inline | {'default:architecture-refresh'}
    assert _classification_mismatches(claims, dispatched, both)


# ---------------------------------------------------------------------------
# Built-in dispatch table completeness (the third drifted roster surface)
# ---------------------------------------------------------------------------


def test_builtin_dispatch_table_lists_the_previously_missing_steps():
    text = _SKILL_DOC.read_text(encoding='utf-8')

    assert '| `default:pre-push-quality-gate` |' in text
    assert '| `default:finalize-step-preference-emitter` |' in text
