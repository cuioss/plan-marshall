#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Execution-context dispatch audit — deterministic facts for a plan.

The former incarnation of this aspect (aspect 11 in ``plan-retrospective``) was
LLM-only prose: its detection logic lived entirely in
``standards/execution-context-dispatch-audit.md`` and the orchestrator
synthesised the fragment by hand. An LLM-synthesised detector cannot be tested,
cannot be shown to FAIL against a divergent site, and — most consequentially —
renders a *never-evaluated* state and an *evaluated-clean* state as the identical
``0``. This script makes the deterministic half of the audit a real, testable
detector that emits facts; the reference doc still guides the LLM's *judgement*
of those facts, per the SKILL's "scripts never judge, references never run code"
split.

The three deterministic facts, each computed population-derived (from the
evidence actually present) rather than from a literal, and each publishing the
size of the population it evaluated so a zero is legible:

D1 — ``shape_violation`` (does dispatch that RESOLVED get LOGGED?).
    Surface B is the ``effort resolve-target`` decision-log record (the *intent*
    side); Surface A is the ``[DISPATCH]`` work-log line (the *observable* side).
    A resolve with no matching dispatch line is a shape violation. The check's
    left-hand side is Surface B, so when Surface B is EMPTY the check reports
    ``not_evaluated`` with its empty-population reason — never a bare ``0`` that a
    reader could mistake for "evaluated clean". Every count is published beside
    its ``evaluated_population``.

D2 — ``dispatch_coverage`` (did dispatch that SHOULD have happened, happen — and
    is a missing line an instrumentation gap or a discipline violation?).
    The discriminator is the **token record**, not the completion line: the
    ``[STEP] … Completed step:`` line fires for inline steps too, whereas a
    non-zero ``execution_log[]`` ``total_tokens`` is written only when the step
    ran as a dispatched Task agent (an inline step records a measured ``0``). So
    each terminal finalize step is classified from its token record into one of
    three evidence states — ``dispatched`` (non-zero tokens), ``ran_inline`` (a
    RECORDED zero), ``no_evidence`` (no token row at all, OR a row whose
    ``total_tokens`` could not be read) — and NEVER reported as "ran inline where
    dispatch was required" on the strength of a missing dispatch line alone.

    ⛔ ``ran_inline`` is an **UPPER BOUND on inline execution, never proof of it**.
    It means *a recorded zero token attribution*, which an inline step produces —
    and which a DISPATCHED step also produces when its ``<usage>`` tag was never
    captured. Reading the bucket as "these steps ran inline" over-claims by
    exactly the size of the uncaptured-usage population. What the bucket rules out
    is the third state: an absent or unreadable record, which now lands in
    ``no_evidence`` rather than being coerced to a measured zero.

    A step proven to have dispatched (non-zero tokens) whose dispatch line is
    nonetheless absent is a ``missing_dispatch_emission`` — an instrumentation
    finding against the DISPATCHER, not a discipline finding against the step. The
    count is a FLOOR for two independent reasons: a re-fire adds lines without
    adding steps, and a step whose token record is unreadable is not counted as
    dispatched at all. A conditionally-dispatching step that legitimately ran
    inline carries a recorded-zero token record and so lands in ``ran_inline``,
    never a coverage violation — the token evidence *is* the population-derived
    qualifier, so no hand-maintained roster annotation (the recurring
    "hand-maintained mirror" archetype the programme forbids) is introduced.

D3 — ``channel_completeness`` (how trustworthy is the dispatch channel itself?).
    Publishes the FINALIZE-SCOPED ``[DISPATCH]``-line count against the
    ``[STEP] Completed`` count and the token-proven dispatched-step count — all
    three over the same finalize population — and downgrades the audit's own
    ``confidence`` when the channel is sparse. The all-caller line total rides
    alongside as ``all_caller_dispatch_line_count``, labelled with its own
    population, so the whole-plan volume stays readable without becoming the
    comparand for a finalize verdict. A detector that consumes voluntarily-emitted
    evidence can only ever report a lower bound; this makes that shortfall visible
    rather than letting a sparse channel silently weaken every verdict. When every
    input is zero the grade is ``not_evaluated`` with a reason — a fourth grade
    added because its absence let a log-less plan grade ``nominal``.

Inputs (all read defensively; a missing input degrades the affected block to
``not_evaluated`` / ``no_evidence`` with a reason, never a false clean):

- ``logs/work.log``      — Surface A ``[DISPATCH]`` lines + ``[STEP] Completed`` lines.
- ``logs/decision.log``  — Surface B ``effort resolve-target`` resolve records.
- ``execution.toon``     — ``execution_log[]`` per-step token records (D2/D3).
- ``status.json``        — ``metadata.phase_steps["6-finalize"]`` terminal outcomes (D2).

Usage:
    python3 check-dispatch-audit.py run --plan-id EXAMPLE-PLAN --mode live
    python3 check-dispatch-audit.py run --archived-plan-path /abs --mode archived
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from _step_completion_marker import COMPLETION_MARKER_RE
from file_ops import base_path, output_toon, safe_main
from input_validation import (
    add_plan_id_arg,
    parse_args_with_toon_errors,
)
from toon_parser import parse_toon

MANIFEST_FILENAME = 'execution.toon'
STATUS_FILENAME = 'status.json'
FINALIZE_PHASE = '6-finalize'

#: The finalize dispatcher's caller prefix. Every finalize ``[DISPATCH]`` line
#: carries this caller because each finalize dispatch resolves its target with
#: ``--caller plan-marshall:phase-6-finalize``, and the ``effort resolve-target``
#: resolve seam emits the line under that caller as a per-firing side effect (see
#: ``phase-6-finalize/SKILL.md`` Step 3). Counting lines by this caller scopes the
#: ``missing_dispatch_emission`` comparison to finalize without pulling in phase-5
#: dispatches that share the work log.
FINALIZE_DISPATCH_CALLER = 'plan-marshall:phase-6-finalize'

#: A ``[DISPATCH] (caller) …`` spawn line. The caller paren is required — a bare
#: ``[DISPATCH] role=phase-N`` phase-entry marker carries no ``(caller)`` and no
#: ``target=`` and is NOT a spawn record (see ``dispatch-logging.md``); such a
#: line is excluded both by this pattern and by the ``target=`` guard below.
_DISPATCH_LINE_RE = re.compile(r'\[DISPATCH\]\s*\((?P<caller>[^)]*)\)')

#: The decision-log resolve record (Surface B). The seam writes
#: ``… effort resolve-target role=X -> target=Y level=Z``; the older illustrative
#: form spelled ``--role X``. Both are recognised so a mixed corpus pairs.
_RESOLVE_LINE_RE = re.compile(r'\beffort resolve-target\b')
_RESOLVE_ROLE_RE = re.compile(r'\brole=(?P<eq>\S+)|--role\s+(?P<flag>\S+)')

#: The ``(bundle:skill)`` caller prefix a decision-log line carries. Captured on
#: the RESOLVE side so a role's resolve callers can be compared against the
#: callers that emitted its ``[DISPATCH]`` lines — see ``_foreign_caller_lines``.
_RESOLVE_CALLER_RE = re.compile(r'\((?P<caller>[^)]*)\)')

#: The per-step completion line, emitted by ``manage-status mark-step-done`` as a
#: side effect of every finalize terminal write (``_emit_completion_marker``).
#: Fires for BOTH dispatched and inline steps, so it is a *completion* witness,
#: never a *dispatch* witness — it is the D3 denominator, never a D2 discriminator.
#:
#: Bound to the SHARED marker-shape module rather than re-typed here, so the
#: producer's template and this read pattern sit in one file and a widening edit
#: sees both. Sharing a file is not coupling, though — the two are separate
#: literals. What actually keeps this consumer reading what the producer writes
#: is the round-trip test in
#: ``test/plan-marshall/manage-status/test_step_completion_marker.py``: it
#: formats a line with the template and requires this pattern to recover the same
#: ``step`` and ``outcome``, so a widening that retires the shape matched here
#: fails there rather than silently under-counting ``completion_count``. The pattern
#: treats the ``(outcome=…)`` suffix as optional because a retrospective reads
#: work logs from earlier runs, whose completion lines carry none — requiring it
#: would silently drop every historical completion from ``completion_count`` and
#: grade the D3 ratio against a zero denominator.
_STEP_COMPLETED_RE = COMPLETION_MARKER_RE

#: A direct ``Task: general-purpose`` spawn in the work log — a generic subagent
#: that bypassed the dispatcher entirely. (Documentation mentions live in ``.md``
#: files, not in ``logs/``, so a plain substring scan of the work log is safe.)
_GENERIC_SUBAGENT_RE = re.compile(r'Task:\s*general-purpose')

#: The envelope a ``[DISPATCH]`` line's ``target=`` must name. Anything else is a
#: dispatch routed through the wrong (or a generic) target.
_ALLOWED_TARGETS = frozenset(
    {'execution-context'} | {f'execution-context-level-{level}' for level in range(1, 8)}
)

#: Confidence downgrades below this dispatch/completion ratio when the channel is
#: not provably sparse by the token comparison. Kept as a labelled constant so the
#: threshold is visible rather than buried in a branch.
_SPARSE_RATIO = 0.5


def _canon_step(step: str) -> str:
    """Normalize a step key to the canonical form ``execution_log`` records use.

    ``phase_steps`` keys carry the registry prefix (``default:`` / ``project:`` /
    ``bundle:skill``), while ``record-step`` canonicalises its ``--step-id`` by
    dropping a leading ``default:`` (``canonicalize_step_key``). Stripping the
    same prefix on both sides lets a ``default:``-prefixed terminal step match its
    prefix-free token row; a ``project:`` / ``bundle:skill`` key is already
    canonical and passes through unchanged.
    """
    return step[len('default:'):] if step.startswith('default:') else step


def _search_kv(line: str, key: str) -> str | None:
    """Return the value of a ``key=value`` field in ``line``, or ``None``."""
    match = re.search(rf'\b{re.escape(key)}=(\S+)', line)
    return match.group(1) if match else None


def resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    if mode == 'live':
        if not plan_id:
            raise ValueError('--plan-id is required for live mode')
        return base_path('plans', plan_id)
    if mode == 'archived':
        if not archived_plan_path:
            raise ValueError('--archived-plan-path is required for archived mode')
        return Path(archived_plan_path)
    raise ValueError(f'Unknown mode: {mode!r}')


def read_log_lines(path: Path) -> list[str]:
    """Return the non-empty lines of a log file; ``[]`` when absent or unreadable.

    An absent log is a real state (a plan that dispatched nothing writes no
    ``[DISPATCH]`` line), so it degrades the affected block to its
    ``not_evaluated`` / ``no_evidence`` branch rather than raising.
    """
    if not path.exists():
        return []
    try:
        content = path.read_text(encoding='utf-8')
    except OSError:
        return []
    return [line for line in content.splitlines() if line.strip()]


def load_manifest(plan_dir: Path) -> dict[str, Any] | None:
    """Return the parsed ``execution.toon`` dict, or ``None`` when absent/unreadable."""
    manifest_path = plan_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    try:
        raw = manifest_path.read_text(encoding='utf-8')
    except OSError:
        return None
    parsed = parse_toon(raw)
    return parsed if isinstance(parsed, dict) else None


def load_status_metadata(plan_dir: Path) -> dict[str, Any]:
    """Return the status-metadata READ RESULT — never a bare ``{}`` for every failure.

    Four materially different states used to collapse into the same empty dict:
    the file was absent, the file could not be read, the file was not valid JSON,
    and the file was read fine and simply carries no ``metadata`` block. The
    coverage block computed from that dict then published
    ``evaluated_population: 0`` in all four, so a plan whose ``status.json`` was
    never written and a plan whose finalize phase legitimately recorded no
    terminal step were byte-identical in the output.

    Returns ``{'status': 'evaluated', 'metadata': {...}}`` when a metadata block
    was actually read, and ``{'status': 'not_evaluated', 'reason': ..., 'metadata': {}}``
    otherwise. The ``metadata`` key is always present so callers that only need
    the mapping stay simple; the ``status`` key is what makes a downstream zero
    legible.
    """
    status_path = plan_dir / STATUS_FILENAME
    if not status_path.exists():
        return {
            'status': 'not_evaluated',
            'reason': (
                f'{STATUS_FILENAME} is absent from the plan directory, so no finalize '
                'terminal-step population could be read. This is `not_evaluated`, NOT an '
                'evaluated-clean population of zero.'
            ),
            'metadata': {},
        }
    try:
        status = json.loads(status_path.read_text(encoding='utf-8'))
    except OSError as exc:
        return {
            'status': 'not_evaluated',
            'reason': (
                f'{STATUS_FILENAME} exists but could not be read ({exc.__class__.__name__}), '
                'so no finalize terminal-step population could be read.'
            ),
            'metadata': {},
        }
    except json.JSONDecodeError as exc:
        return {
            'status': 'not_evaluated',
            'reason': (
                f'{STATUS_FILENAME} exists but is not valid JSON ({exc.msg}), so no '
                'finalize terminal-step population could be read.'
            ),
            'metadata': {},
        }
    metadata = status.get('metadata') if isinstance(status, dict) else None
    if not isinstance(metadata, dict):
        return {
            'status': 'not_evaluated',
            'reason': (
                f'{STATUS_FILENAME} was read but carries no `metadata` mapping, so no '
                'finalize terminal-step population could be read.'
            ),
            'metadata': {},
        }
    return {'status': 'evaluated', 'metadata': metadata}


def parse_dispatch_lines(work_lines: list[str]) -> list[dict[str, str | None]]:
    """Return one record per ``[DISPATCH]`` spawn line (Surface A).

    A ``[DISPATCH] (caller) …`` line with a ``target=`` field is a spawn record;
    a bare phase-entry marker without ``target=`` is skipped, matching the
    dispatch-audit's own scoping rule.
    """
    out: list[dict[str, str | None]] = []
    for line in work_lines:
        match = _DISPATCH_LINE_RE.search(line)
        if not match:
            continue
        target = _search_kv(line, 'target')
        if target is None:
            continue
        out.append(
            {
                'caller': match.group('caller'),
                'role': _search_kv(line, 'role'),
                'target': target,
                'workflow': _search_kv(line, 'workflow'),
            }
        )
    return out


def _distinct_finalize_dispatches(dispatches: list[dict[str, str | None]]) -> int:
    """Count DISTINCT finalize dispatch emissions, keyed by ``(role, workflow)``.

    The ``missing_dispatch_emission`` comparison is *steps token-proven to have
    dispatched* against *dispatch lines emitted for them*, so a re-fire of the
    same step must not inflate the line side and mask a genuine gap. Deduplicating
    on ``role`` ALONE would over-correct in the other direction: two distinct
    finalize steps can resolve the same role (several steps route through
    ``verification-feedback``-shaped roles), so collapsing by role would fold two
    real emissions into one and manufacture a gap that is not there. The pair is
    what identifies one step's dispatch: the role selects the target and the
    workflow names the body it runs.

    A line carrying no ``workflow=`` field keys on ``(role, None)``, so a caller
    that emits the role alone still contributes exactly one distinct emission
    rather than being dropped.
    """
    distinct: set[tuple[str | None, str | None]] = set()
    for record in dispatches:
        if record['caller'] != FINALIZE_DISPATCH_CALLER:
            continue
        distinct.add((record['role'], record.get('workflow')))
    return len(distinct)


def _category_count(block: dict[str, Any]) -> dict[str, Any]:
    """Render one ``counts.by_category`` entry from an evaluator's own block.

    Derived FROM the block rather than restated beside it, so the summary count
    and the detailed block cannot disagree about either the number or the status
    it was measured under.
    """
    return {
        'count': block['violations'],
        'status': block['status'],
        'evaluated_population': block['evaluated_population'],
    }


def parse_resolve_records(decision_lines: list[str]) -> list[dict[str, str | None]]:
    """Return one record per ``effort resolve-target`` decision-log line (Surface B).

    The ``(bundle:skill)`` caller prefix is captured alongside the role. The
    pairing below compares COUNTS per role, which is caller-blind by
    construction: a hand-written ``[DISPATCH]`` line for a role the seam also
    resolved cancels the resolve out and the pair reads as matched. Carrying the
    caller is what lets the per-role breakdown report that cancellation as a fact
    instead of letting it pass as corroboration.
    """
    out: list[dict[str, str | None]] = []
    for line in decision_lines:
        if not _RESOLVE_LINE_RE.search(line):
            continue
        role_match = _RESOLVE_ROLE_RE.search(line)
        role = None
        if role_match:
            role = role_match.group('eq') or role_match.group('flag')
        caller_match = _RESOLVE_CALLER_RE.search(line)
        out.append(
            {
                'role': role,
                'caller': caller_match.group('caller') if caller_match else None,
            }
        )
    return out


def finalize_token_records(manifest: dict[str, Any] | None) -> dict[str, int | None]:
    """Return ``{canonical_step_id: total_tokens | None}`` for finalize rows.

    ``record-step`` writes one row per finalize step — dispatched OR inline —
    carrying ``step_id``, ``phase`` and ``total_tokens``; a dispatched step's row
    carries the agent's measured tokens, an inline step's a measured ``0``. Rows
    for other phases are ignored.

    ⛔ **An unreadable ``total_tokens`` maps to ``None``, never to ``0``.** A row
    with no ``total_tokens`` column at all, a non-integer value, and a
    non-digit string are three ways of saying *nothing was recorded* — and the
    predecessor coerced all three to ``0``, which the classifier then read as a
    MEASURED zero and filed under ``ran_inline``, the bucket the module docstring
    and the shipped standard both present as evidence the step ran inline. ``None``
    routes to ``no_evidence`` instead, where the absence belongs. An EXPLICIT
    integer ``0`` still maps to ``0`` and still classifies ``ran_inline``, which
    bounds the change: no plan whose rows carry real token columns changes verdict.

    When two rows name the same step (a re-fire that re-recorded) the larger
    RECORDED value wins, so a later zero cannot mask an earlier dispatched
    measurement — and a recorded value of any size wins over ``None``, because a
    measurement outranks its absence.
    """
    tokens: dict[str, int | None] = {}
    if not isinstance(manifest, dict):
        return tokens
    rows = manifest.get('execution_log')
    if not isinstance(rows, list):
        return tokens
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get('phase')) != FINALIZE_PHASE:
            continue
        step_id = row.get('step_id')
        if not isinstance(step_id, str) or not step_id:
            continue
        raw = row.get('total_tokens')
        value: int | None
        if isinstance(raw, bool):
            # A bool is not a token count. It is a recorded-but-unreadable value,
            # so it is an absence of evidence rather than a measured zero.
            value = None
        elif isinstance(raw, int):
            value = raw
        elif isinstance(raw, str) and raw.strip().lstrip('-').isdigit():
            value = int(raw)
        else:
            value = None
        key = _canon_step(step_id)
        if key not in tokens:
            tokens[key] = value
            continue
        existing = tokens[key]
        if existing is None:
            tokens[key] = value
        elif value is not None:
            tokens[key] = max(existing, value)
    return tokens


def finalize_terminal_steps(metadata: dict[str, Any]) -> list[str]:
    """Return the canonical keys of finalize steps that reached a terminal outcome.

    Read from ``status.metadata.phase_steps["6-finalize"]`` (Surface C). Every key
    present there was marked terminal by ``mark-step-done``; the entry is a
    ``{"outcome": …}`` dict (or, under the legacy shim, a bare outcome string) —
    either shape counts as "reached a terminal outcome" for the coverage
    population, so the value shape is not inspected further.
    """
    phase_steps = metadata.get('phase_steps')
    if not isinstance(phase_steps, dict):
        return []
    finalize = phase_steps.get(FINALIZE_PHASE)
    if not isinstance(finalize, dict):
        return []
    return sorted({_canon_step(step) for step in finalize if isinstance(step, str)})


def evaluate_shape_violation(
    resolves: list[dict[str, str | None]],
    dispatches: list[dict[str, str | None]],
) -> dict[str, Any]:
    """D1 — pair each resolve record (Surface B) with a dispatch line (Surface A).

    Population-derived: the population is the number of ``effort resolve-target``
    records, computed from the log, never a literal. When that population is empty
    the check reports ``not_evaluated`` with its reason — the left-hand side of
    the pairing is absent, so the check evaluated nothing, and saying ``0`` would
    be indistinguishable from an evaluated-clean verdict. When non-empty, a role
    whose resolve count exceeds its dispatch-line count contributes one finding
    naming the shortfall.
    """
    population = len(resolves)
    if population == 0:
        return {
            'status': 'not_evaluated',
            'evaluated_population': 0,
            'violations': 0,
            'reason': (
                'no `effort resolve-target` records in decision.log — Surface B (the '
                'resolve/intent side of the pairing) is empty, so the shape-violation '
                'check has no left-hand side to evaluate. This is `not_evaluated`, NOT '
                'evaluated-clean: a bare 0 here would be a never-evaluated verdict '
                'wearing an evaluated-clean face.'
            ),
            'findings': [],
            'by_role': [],
        }

    resolve_roles: Counter[str | None] = Counter(record['role'] for record in resolves)
    dispatch_roles: Counter[str | None] = Counter(record['role'] for record in dispatches)
    findings: list[dict[str, str]] = []
    by_role: list[dict[str, Any]] = []
    # Union of both sides, so a role that appears ONLY on the dispatch side is
    # published too. Restricting the walk to the resolve side is what made the
    # surplus direction invisible: a hand-written `[DISPATCH]` line for a role the
    # dispatcher never resolved contributed nothing to the output at all.
    # Per role, the callers seen on each surface. The pairing itself is
    # caller-blind (it compares counts), so these are what make a cancellation
    # legible: a resolve emitted by the seam and a [DISPATCH] line written by
    # something else are not the same event, however neatly their counts match.
    resolve_callers_by_role: dict[str | None, set[str | None]] = {}
    for record in resolves:
        resolve_callers_by_role.setdefault(record['role'], set()).add(record.get('caller'))
    dispatch_callers_by_role: dict[str | None, list[str | None]] = {}
    for record in dispatches:
        dispatch_callers_by_role.setdefault(record['role'], []).append(record['caller'])

    all_roles = set(resolve_roles) | set(dispatch_roles)
    for role in sorted(all_roles, key=lambda item: item or ''):
        resolve_count = resolve_roles.get(role, 0)
        dispatch_count = dispatch_roles.get(role, 0)
        # A [DISPATCH] line for this role whose caller resolved NOTHING for it.
        # Non-zero means the role's dispatch lines are not all corroborated by the
        # resolve seam — the hand-written-emission shape — and it is reported as a
        # FACT rather than a finding, for the same reason a negative delta is: a
        # hand-written line is not by itself a discipline failure.
        resolve_callers = resolve_callers_by_role.get(role, set())
        foreign_caller_lines = sum(
            1
            for caller in dispatch_callers_by_role.get(role, [])
            if caller not in resolve_callers
        )
        # SIGNED. A positive delta is the finding (a resolve with no emission); a
        # NEGATIVE delta is a fact, not a finding — more `[DISPATCH]` lines than
        # resolves means lines came from somewhere other than the resolve seam
        # (a hand-written emission, or a caller this check cannot see). Reporting
        # that as a violation would fail plans for a legitimate emission, and
        # discarding it — which the predecessor did — hid the one signal that
        # distinguishes a caller-blind clean verdict from a corroborated one.
        delta = resolve_count - dispatch_count
        by_role.append(
            {
                'role': role if role is not None else '',
                'resolves': resolve_count,
                'dispatch_lines': dispatch_count,
                'delta': delta,
                'foreign_caller_lines': foreign_caller_lines,
            }
        )
        if delta > 0:
            findings.append(
                {
                    'severity': 'error',
                    'category': 'shape_violation',
                    'message': (
                        f'{delta} resolve record(s) for role={role} in decision.log '
                        f'have no matching [DISPATCH] emission in work.log '
                        f'(resolved={resolve_count}, dispatched={dispatch_count})'
                    ),
                }
            )
    return {
        'status': 'evaluated',
        'evaluated_population': population,
        'violations': len(findings),
        'findings': findings,
        'by_role': by_role,
    }


def evaluate_dispatch_coverage(
    terminal_steps: list[str],
    tokens_by_step: dict[str, int | None],
    finalize_dispatch_line_count: int,
    population_status: str = 'evaluated',
    population_reason: str = '',
) -> dict[str, Any]:
    """D2 — classify each terminal finalize step by its TOKEN record, three states.

    The token record is the second, independent evidence source the coverage
    check consults before ever concluding "ran inline": a non-zero
    ``total_tokens`` proves a dispatched envelope ran, a measured ``0`` proves the
    step ran inline, and an absent row is honest ``no_evidence``. The old
    "ran inline where dispatch was required" discipline finding — a fabricated
    violation against the step — is not emitted at all. Its replacement is
    ``missing_dispatch_emission``: when more steps are token-proven to have
    dispatched than there are finalize ``[DISPATCH]`` lines, the shortfall is an
    instrumentation gap in the DISPATCHER (a floor, since a re-fire adds lines but
    not steps). Population is published beside every count.
    """
    dispatched: list[str] = []
    ran_inline: list[str] = []
    no_evidence: list[str] = []
    for step in terminal_steps:
        recorded = tokens_by_step.get(step, None)
        if step not in tokens_by_step or recorded is None:
            # Two routes into the same honest state: no row at all, and a row
            # whose `total_tokens` could not be read. Neither is a measurement,
            # so neither may buy the step a `ran_inline` classification.
            no_evidence.append(step)
        elif recorded > 0:
            dispatched.append(step)
        else:
            ran_inline.append(step)

    missing = max(0, len(dispatched) - finalize_dispatch_line_count)
    findings: list[dict[str, str]] = []
    if missing > 0:
        findings.append(
            {
                'severity': 'error',
                'category': 'missing_dispatch_emission',
                'message': (
                    f'{len(dispatched)} finalize step(s) recorded non-zero token '
                    f'attribution (proof of a dispatched envelope) but only '
                    f'{finalize_dispatch_line_count} distinct (role, workflow) [DISPATCH] '
                    f'line(s) carry the finalize dispatcher caller — {missing} dispatch '
                    f'emission(s) missing. This is a FLOOR on the gap, for two independent '
                    f'reasons: a step whose token row is unreadable lands in `no_evidence` '
                    f'and is not counted as dispatched here at all, and a re-fire adds '
                    f'lines without adding steps. It is an instrumentation gap in the '
                    f'DISPATCHER, not an inline-execution (discipline) violation against '
                    f'any step.'
                ),
            }
        )
    result: dict[str, Any] = {
        'status': population_status,
        'evaluated_population': len(terminal_steps),
        'dispatched': len(dispatched),
        # The dispatched step ids, published beside the no-evidence ones. A reader
        # reconciling a `missing_dispatch_emission` count against the work log needs
        # to know WHICH steps the count was taken over; a bare number sends them
        # back to the manifest to re-derive it.
        'dispatched_steps': dispatched,
        'ran_inline': len(ran_inline),
        'no_evidence': len(no_evidence),
        'no_evidence_steps': no_evidence,
        'missing_dispatch_emission': missing,
        'findings': findings,
    }
    if population_status != 'evaluated':
        result['reason'] = population_reason
    return result


def evaluate_channel_completeness(
    dispatch_line_count: int,
    completion_count: int,
    dispatched_step_count: int,
    all_caller_dispatch_line_count: int,
) -> dict[str, Any]:
    """D3 — publish dispatch-line volume against completion volume; grade confidence.

    ⛔ **``dispatch_line_count`` is FINALIZE-SCOPED**, matching the other two
    figures in this block: ``completion_count`` counts finalize terminal writes
    and ``dispatched_step_count`` counts token-proven FINALIZE steps. The
    predecessor was handed the ALL-CALLER line total instead, so a plan with many
    phase-5 dispatch lines and none at all from the finalize dispatcher divided a
    whole-plan numerator by a finalize denominator and graded the channel
    ``nominal``. ``all_caller_dispatch_line_count`` is published beside it —
    labelled with the population it was taken over — because the whole-plan volume
    is still worth reading; it simply is not the comparand for a finalize verdict.

    ``ratio`` is the finalize-scoped ``[DISPATCH]``-line count over the
    ``[STEP] Completed`` count (``None`` when there are no completions to divide
    by). ``confidence`` is the audit's own trust in its dispatch-discipline
    verdicts:

    - ``not_evaluated`` — every input is zero. Nothing was measured, so no verdict
      about the channel can be substantiated. This grade exists because its
      absence let a log-less plan — no work log, no manifest, no status.json —
      grade ``nominal``, which is an evaluated-clean verdict over an empty
      evaluation. It carries a ``reason``.
    - ``none``   — no finalize ``[DISPATCH]`` lines at all despite completions or
      token-proven dispatches: the audit saw zero dispatch evidence where it
      expected some, so any dispatch-discipline verdict it renders is
      unsubstantiated.
    - ``low``    — fewer ``[DISPATCH]`` lines than steps token-proven to have
      dispatched (a provable shortfall), or a dispatch/completion ratio under the
      sparse threshold.
    - ``nominal``— the channel was evaluated and is not provably sparse by either
      measure.
    """
    ratio = round(dispatch_line_count / completion_count, 3) if completion_count > 0 else None
    reason = ''
    # Ordered FIRST, and the order is load-bearing: every later branch reads a
    # zero as a measured one. An all-zero input set is the state in which no
    # branch below has anything to say, and the predecessor's `else` handed it
    # the healthiest grade in the vocabulary.
    if (
        dispatch_line_count == 0
        and completion_count == 0
        and dispatched_step_count == 0
        and all_caller_dispatch_line_count == 0
    ):
        confidence = 'not_evaluated'
        reason = (
            'no [DISPATCH] lines, no [STEP] Completed lines and no token-proven '
            'dispatched finalize steps — every input to the channel grade is empty, '
            'so nothing was evaluated. This is `not_evaluated`, NOT `nominal`: a '
            'nominal grade over an empty evaluation is an unsubstantiated clean '
            'verdict.'
        )
    elif dispatch_line_count == 0 and (completion_count > 0 or dispatched_step_count > 0):
        confidence = 'none'
    elif dispatched_step_count > 0 and dispatch_line_count < dispatched_step_count:
        confidence = 'low'
    elif ratio is not None and ratio < _SPARSE_RATIO and completion_count > 0:
        confidence = 'low'
    else:
        confidence = 'nominal'
    result: dict[str, Any] = {
        # Finalize-scoped — the population every other figure in this block is
        # taken over. Labelled in the key's own documentation rather than left to
        # a reader to infer from the surrounding fields.
        'dispatch_line_count': dispatch_line_count,
        'dispatch_line_population': 'finalize_dispatcher_caller',
        'all_caller_dispatch_line_count': all_caller_dispatch_line_count,
        'all_caller_dispatch_line_population': 'every_caller_in_work_log',
        'completion_count': completion_count,
        'dispatched_step_count': dispatched_step_count,
        'ratio': ratio,
        'confidence': confidence,
    }
    if reason:
        result['reason'] = reason
    return result


def evaluate_envelope_violations(
    dispatches: list[dict[str, str | None]],
) -> dict[str, Any]:
    """Every ``[DISPATCH]`` line whose ``target=`` is not an execution-context envelope.

    Returns ``{status, evaluated_population, violations, findings}`` rather than a
    bare list. The population is the number of ``[DISPATCH]`` spawn lines the check
    walked; ``violations`` is the length of ``findings``; ``status`` is
    ``evaluated`` only when that population was non-empty. Published together
    because the length ALONE was the whole output before, and a plan with no work
    log and a plan with a populated clean work log both rendered as ``0`` — the
    two states this block most needs to distinguish, and ``status`` is the field
    that separates them.
    """
    findings: list[dict[str, str]] = []
    for record in dispatches:
        target = record['target']
        if target is not None and target not in _ALLOWED_TARGETS:
            findings.append(
                {
                    'severity': 'error',
                    'category': 'envelope_violation',
                    'message': (
                        f'[DISPATCH] line carries target={target} — not an '
                        f'execution-context envelope'
                    ),
                }
            )
    return {
        'status': 'evaluated' if dispatches else 'not_evaluated',
        'evaluated_population': len(dispatches),
        'violations': len(findings),
        'findings': findings,
    }


def evaluate_generic_subagent(work_lines: list[str]) -> dict[str, Any]:
    """Every ``Task: general-purpose`` spawn observed directly in the work log.

    Returns ``{status, evaluated_population, violations, findings}`` for the same
    reason :func:`evaluate_envelope_violations` does: the population here is the
    number of work-log lines scanned, and a zero over an EMPTY log is a different
    statement from a zero over a populated one — ``status`` is what carries that
    difference, which is why it is named here rather than left to the caller.
    """
    findings: list[dict[str, str]] = []
    for line in work_lines:
        if _GENERIC_SUBAGENT_RE.search(line):
            findings.append(
                {
                    'severity': 'error',
                    'category': 'generic_subagent_violation',
                    'message': (
                        f'Direct Task: general-purpose invocation in work.log: '
                        f'{line.strip()[:200]}'
                    ),
                }
            )
    return {
        'status': 'evaluated' if work_lines else 'not_evaluated',
        'evaluated_population': len(work_lines),
        'violations': len(findings),
        'findings': findings,
    }


def _summary(
    shape: dict[str, Any],
    coverage: dict[str, Any],
    channel: dict[str, Any],
    findings: list[dict[str, str]],
) -> str:
    """One-line human summary for the report's section body."""
    if shape['status'] == 'not_evaluated':
        shape_text = 'shape-violation not_evaluated (Surface B empty)'
    else:
        shape_text = f'shape-violation {shape["violations"]}/{shape["evaluated_population"]}'
    if coverage['status'] == 'not_evaluated':
        coverage_text = 'coverage not_evaluated (status.json population unreadable)'
    else:
        coverage_text = (
            f'coverage {coverage["dispatched"]} dispatched / {coverage["ran_inline"]} inline / '
            f'{coverage["no_evidence"]} no-evidence of {coverage["evaluated_population"]}'
        )
    channel_text = f'channel confidence={channel["confidence"]}'
    return f'{len(findings)} finding(s); {shape_text}; {coverage_text}; {channel_text}.'


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    logs_dir = plan_dir / 'logs'

    work_lines = read_log_lines(logs_dir / 'work.log')
    decision_lines = read_log_lines(logs_dir / 'decision.log')

    dispatch_lines = parse_dispatch_lines(work_lines)
    resolves = parse_resolve_records(decision_lines)
    completion_count = sum(1 for line in work_lines if _STEP_COMPLETED_RE.search(line))
    finalize_dispatch_line_count = _distinct_finalize_dispatches(dispatch_lines)
    all_caller_dispatch_line_count = len(dispatch_lines)

    manifest = load_manifest(plan_dir)
    tokens_by_step = finalize_token_records(manifest)
    status_read = load_status_metadata(plan_dir)
    metadata = status_read['metadata']
    terminal_steps = finalize_terminal_steps(metadata)

    shape = evaluate_shape_violation(resolves, dispatch_lines)
    coverage = evaluate_dispatch_coverage(
        terminal_steps,
        tokens_by_step,
        finalize_dispatch_line_count,
        population_status=str(status_read['status']),
        population_reason=str(status_read.get('reason', '')),
    )
    channel = evaluate_channel_completeness(
        finalize_dispatch_line_count,
        completion_count,
        coverage['dispatched'],
        all_caller_dispatch_line_count,
    )
    envelope = evaluate_envelope_violations(dispatch_lines)
    generic = evaluate_generic_subagent(work_lines)

    findings = (
        shape['findings'] + coverage['findings'] + envelope['findings'] + generic['findings']
    )
    # ⛔ Every entry is a STRUCTURED value carrying its own population and status,
    # never a bare integer. A reader consulting `counts.by_category` alone used to
    # see `shape_violation: 0` whether the check had evaluated a population and
    # found it clean or had never evaluated anything — the two states the block
    # above already distinguishes, flattened back into one number by the summary
    # that most readers stop at.
    counts = {
        'total': len(findings),
        'by_category': {
            'shape_violation': _category_count(shape),
            'missing_dispatch_emission': {
                'count': coverage['missing_dispatch_emission'],
                'status': coverage['status'],
                'evaluated_population': coverage['evaluated_population'],
            },
            'envelope_violation': _category_count(envelope),
            'generic_subagent_violation': _category_count(generic),
        },
    }

    return {
        'status': 'success',
        'aspect': 'execution-context-dispatch-audit',
        'plan_id': args.plan_id or plan_dir.name,
        'plan_dir': str(plan_dir),
        'summary': _summary(shape, coverage, channel, findings),
        'shape_violation': shape,
        'dispatch_coverage': coverage,
        'channel_completeness': channel,
        'envelope_violation': envelope,
        'generic_subagent_violation': generic,
        'findings': findings,
        'counts': counts,
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Execution-context dispatch audit — deterministic facts for a plan',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser(
        'run', help='Compute the dispatch-audit facts', allow_abbrev=False
    )
    add_plan_id_arg(run_parser, required=False)
    run_parser.add_argument(
        '--archived-plan-path',
        help='Absolute path to archived plan directory (archived mode)',
    )
    run_parser.add_argument(
        '--mode',
        choices=['live', 'archived'],
        required=True,
        help='Resolution mode',
    )
    run_parser.set_defaults(func=cmd_run)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
