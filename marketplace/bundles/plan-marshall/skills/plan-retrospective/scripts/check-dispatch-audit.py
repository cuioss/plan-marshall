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
    three evidence states — ``dispatched`` (non-zero tokens), ``ran_inline``
    (measured zero), ``no_evidence`` (no token row at all) — and NEVER reported
    as "ran inline where dispatch was required" on the strength of a missing
    dispatch line alone. A step proven to have dispatched (non-zero tokens) whose
    dispatch line is nonetheless absent is a ``missing_dispatch_emission`` — an
    instrumentation finding against the DISPATCHER, not a discipline finding
    against the step. A conditionally-dispatching step that legitimately ran
    inline carries a measured-zero token record and so lands in ``ran_inline``,
    never a coverage violation — the token evidence *is* the population-derived
    qualifier, so no hand-maintained roster annotation (the recurring
    "hand-maintained mirror" archetype the programme forbids) is introduced.

D3 — ``channel_completeness`` (how trustworthy is the dispatch channel itself?).
    Publishes the ``[DISPATCH]``-line count against the ``[STEP] Completed``
    count and the token-proven dispatched-step count, and downgrades the audit's
    own ``confidence`` when the channel is sparse. A detector that consumes
    voluntarily-emitted evidence can only ever report a lower bound; this makes
    that shortfall visible rather than letting a sparse channel silently weaken
    every verdict. It needs no new instrumentation — both the ``[DISPATCH]`` line
    and the ``[STEP] Completed`` line are already emitted — and it works whether
    or not any emission fix has landed.

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

#: The per-step completion line, emitted by ``manage-status mark-step-done`` as a
#: side effect of every finalize terminal write (``_emit_completion_marker``).
#: Fires for BOTH dispatched and inline steps, so it is a *completion* witness,
#: never a *dispatch* witness — it is the D3 denominator, never a D2 discriminator.
#:
#: Bound to the SHARED marker-shape module rather than re-typed here: the producer
#: formats from the same module's template, so widening the emitted line cannot
#: leave this consumer matching a shape that is no longer written. The pattern
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
    """Return ``status.metadata`` (``{}`` when status.json is absent/malformed)."""
    status_path = plan_dir / STATUS_FILENAME
    if not status_path.exists():
        return {}
    try:
        status = json.loads(status_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    metadata = status.get('metadata') if isinstance(status, dict) else None
    return metadata if isinstance(metadata, dict) else {}


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
            }
        )
    return out


def parse_resolve_records(decision_lines: list[str]) -> list[dict[str, str | None]]:
    """Return one record per ``effort resolve-target`` decision-log line (Surface B)."""
    out: list[dict[str, str | None]] = []
    for line in decision_lines:
        if not _RESOLVE_LINE_RE.search(line):
            continue
        role_match = _RESOLVE_ROLE_RE.search(line)
        role = None
        if role_match:
            role = role_match.group('eq') or role_match.group('flag')
        out.append({'role': role})
    return out


def finalize_token_records(manifest: dict[str, Any] | None) -> dict[str, int]:
    """Return ``{canonical_step_id: total_tokens}`` for finalize ``execution_log`` rows.

    ``record-step`` writes one row per finalize step — dispatched OR inline —
    carrying ``step_id``, ``phase`` and ``total_tokens``; a dispatched step's row
    carries the agent's measured tokens, an inline step's a measured ``0``. Rows
    for other phases are ignored. When two rows name the same step (a re-fire that
    re-recorded) the larger token value wins, so a later zero cannot mask an
    earlier dispatched measurement.
    """
    tokens: dict[str, int] = {}
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
        if isinstance(raw, bool):
            value = 0
        elif isinstance(raw, int):
            value = raw
        elif isinstance(raw, str) and raw.strip().lstrip('-').isdigit():
            value = int(raw)
        else:
            value = 0
        key = _canon_step(step_id)
        tokens[key] = max(tokens.get(key, 0), value)
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
        }

    resolve_roles: Counter[str | None] = Counter(record['role'] for record in resolves)
    dispatch_roles: Counter[str | None] = Counter(record['role'] for record in dispatches)
    findings: list[dict[str, str]] = []
    for role, resolve_count in sorted(resolve_roles.items(), key=lambda item: item[0] or ''):
        dispatch_count = dispatch_roles.get(role, 0)
        unmatched = resolve_count - dispatch_count
        if unmatched > 0:
            findings.append(
                {
                    'severity': 'error',
                    'category': 'shape_violation',
                    'message': (
                        f'{unmatched} resolve record(s) for role={role} in decision.log '
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
    }


def evaluate_dispatch_coverage(
    terminal_steps: list[str],
    tokens_by_step: dict[str, int],
    finalize_dispatch_line_count: int,
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
        if step not in tokens_by_step:
            no_evidence.append(step)
        elif tokens_by_step[step] > 0:
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
                    f'{finalize_dispatch_line_count} [DISPATCH] line(s) carry the finalize '
                    f'dispatcher caller — {missing} dispatch emission(s) missing. This is an '
                    f'instrumentation gap in the DISPATCHER, not an inline-execution '
                    f'(discipline) violation against any step.'
                ),
            }
        )
    return {
        'evaluated_population': len(terminal_steps),
        'dispatched': len(dispatched),
        'ran_inline': len(ran_inline),
        'no_evidence': len(no_evidence),
        'no_evidence_steps': no_evidence,
        'missing_dispatch_emission': missing,
        'findings': findings,
    }


def evaluate_channel_completeness(
    dispatch_line_count: int,
    completion_count: int,
    dispatched_step_count: int,
) -> dict[str, Any]:
    """D3 — publish dispatch-line volume against completion volume; grade confidence.

    ``ratio`` is the ``[DISPATCH]``-line count over the ``[STEP] Completed`` count
    (``None`` when there are no completions to divide by). ``confidence`` is the
    audit's own trust in its dispatch-discipline verdicts, downgraded when the
    channel is sparse:

    - ``none``   — no ``[DISPATCH]`` lines at all despite completions or
      token-proven dispatches: the audit saw zero dispatch evidence, so any
      dispatch-discipline verdict it renders is unsubstantiated.
    - ``low``    — fewer ``[DISPATCH]`` lines than steps token-proven to have
      dispatched (a provable shortfall), or a dispatch/completion ratio under the
      sparse threshold.
    - ``nominal``— the channel is not provably sparse by either measure.
    """
    ratio = round(dispatch_line_count / completion_count, 3) if completion_count > 0 else None
    if dispatch_line_count == 0 and (completion_count > 0 or dispatched_step_count > 0):
        confidence = 'none'
    elif dispatched_step_count > 0 and dispatch_line_count < dispatched_step_count:
        confidence = 'low'
    elif ratio is not None and ratio < _SPARSE_RATIO and completion_count > 0:
        confidence = 'low'
    else:
        confidence = 'nominal'
    return {
        'dispatch_line_count': dispatch_line_count,
        'completion_count': completion_count,
        'dispatched_step_count': dispatched_step_count,
        'ratio': ratio,
        'confidence': confidence,
    }


def evaluate_envelope_violations(
    dispatches: list[dict[str, str | None]],
) -> list[dict[str, str]]:
    """Every ``[DISPATCH]`` line whose ``target=`` is not an execution-context envelope."""
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
    return findings


def evaluate_generic_subagent(work_lines: list[str]) -> list[dict[str, str]]:
    """Every ``Task: general-purpose`` spawn observed directly in the work log."""
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
    return findings


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
    finalize_dispatch_line_count = sum(
        1 for record in dispatch_lines if record['caller'] == FINALIZE_DISPATCH_CALLER
    )

    manifest = load_manifest(plan_dir)
    tokens_by_step = finalize_token_records(manifest)
    metadata = load_status_metadata(plan_dir)
    terminal_steps = finalize_terminal_steps(metadata)

    shape = evaluate_shape_violation(resolves, dispatch_lines)
    coverage = evaluate_dispatch_coverage(
        terminal_steps, tokens_by_step, finalize_dispatch_line_count
    )
    channel = evaluate_channel_completeness(
        len(dispatch_lines), completion_count, coverage['dispatched']
    )
    envelope_findings = evaluate_envelope_violations(dispatch_lines)
    generic_findings = evaluate_generic_subagent(work_lines)

    findings = shape['findings'] + coverage['findings'] + envelope_findings + generic_findings
    counts = {
        'total': len(findings),
        'by_category': {
            'shape_violation': shape['violations'],
            'missing_dispatch_emission': coverage['missing_dispatch_emission'],
            'envelope_violation': len(envelope_findings),
            'generic_subagent_violation': len(generic_findings),
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
