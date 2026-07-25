#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Routing-decision verification aspect — deterministic predicate re-evaluation.

Grades the routing decisions a run actually made (recipe-match, aspect
classification, and the execution-profile posture) against the realized
footprint, so the lane mechanism self-corrects. This is the per-plan analog of
the corpus-level recipe-match / track-selection-accuracy / token-economics audit
checks.

The script is DETERMINISTIC by design — it re-evaluates the named prune
predicates (owned by ``plan-marshall:extension-api/standards/ext-point-lane-element.md``)
against the realized footprint and emits TOON fact fragments. It reserves NO
cognition for itself: the OVER-PROVISIONED / UNDER-PROVISIONED / correct posture
counterfactual is an LLM judgment synthesized from these facts by the aspect's
reference contract (``references/routing-decision-verification.md``). The script
sets ``llm_judgement_required: true`` to mark that boundary.

Facts emitted:
  * ``posture`` / ``planning_lane`` — the recorded routing decisions.
  * ``mis_prune`` checks — for each prunable step ABSENT from the final
    ``phase_6.steps``, first resolve WHY it was removed from the recorded
    decision log, and only then re-evaluate its predicate. A step named by one
    of the four recorded non-predicate removal mechanisms (posture cutoff,
    ``unresolved_ask_provider_drop``, ``simplify_inactive``, and a
    ``ceremony_finalize_selection`` resolving ``never``) is SKIPPED — its
    predicate never fired, so its absence proves nothing about the footprint.
    Only a step whose removal no recorded mechanism explains, in a decision log
    that was actually readable, has its predicate re-evaluated: a predicate that
    is now FALSE (e.g. ``sonar-roundtrip`` skipped as "no code delta" but the
    merged diff touched production code) is a mis-prune — the highest-value
    output. An absent or unreadable decision log substantiates no cause at all,
    so the verdict is ``inconclusive`` rather than a fabricated ``fail``.
  * ``cost_preview`` — predicted (init preview) vs actual (``execution_log``)
    token totals and the delta, feeding the §4.6a recalibration loop.
  * ``kept_step_yield`` — finding count as the adversarial-step yield proxy.
  * ``recompose_divergence`` — the lane_resolution decision-log entry count.

Inputs (all present at retrospective time): ``execution.toon`` (manifest +
``execution_log``), ``status.json`` (posture, ``planning_lane``), the
decision-log, and the findings JSONL.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from file_ops import base_path, output_toon, safe_main
from input_validation import (
    add_plan_id_arg,
    parse_args_with_toon_errors,
)
from toon_parser import parse_toon

MANIFEST_FILENAME = 'execution.toon'
STATUS_FILENAME = 'status.json'
DECISION_LOG_RELPATH = ('logs', 'decision.log')

# Bookkeeping path prefixes filtered out of the realized footprint before any
# predicate re-evaluation (mirrors check-manifest-consistency).
_BOOKKEEPING_PREFIXES = ('.plan/', '.claude/')
_DOCS_SUFFIXES = ('.md', '.adoc')
_TEST_DIR_TOKENS = ('test/', '/test/', 'tests/', '/tests/')
_TEST_NAME_RE = re.compile(
    r'(^|/)(test_[^/]+\.py|[^/]+_test\.py|[^/]+Test\.java|[^/]+\.test\.js|[^/]+\.spec\.js)$'
)

# Prunable steps whose absence from the final phase_6.steps is re-checked against
# the realized footprint. Each maps to its ``prunable_when`` predicate id — the
# vocabulary is owned by ext-point-lane-element.md; this map records only which
# step carries which predicate for the deterministic re-evaluation.
#
# RE-DERIVATION OBLIGATION: ``_REMOVAL_CAUSE_PATTERNS`` below enumerates every
# recorded mechanism that can remove one of THESE members from ``phase_6.steps``
# without its predicate firing. That enumeration is bound to this map's
# membership — adding a step here obliges a re-derivation of the removal-cause
# set against ``manage-execution-manifest/standards/decision-rules.md``. An
# unenumerated removal mechanism reintroduces the false ``mis_prune`` verdict by
# that route.
_PRUNABLE_PREDICATES = {
    'sonar-roundtrip': 'no_code_delta',
    'finalize-step-simplify': 'no_code_delta',
}

# The lane_resolution decision-log caller tag.
_LANE_DECISION_RE = re.compile(r'lane_resolution\b')

# Recorded non-predicate removal mechanisms, one pattern per mechanism. Each
# line shape is copied verbatim from
# ``manage-execution-manifest/standards/decision-rules.md`` (the emitter
# contract). A step named by any of these left ``phase_6.steps`` for a reason
# orthogonal to its prune predicate, so its absence is NOT evidence the
# predicate fired.
#
# Mechanism 4 (``ceremony_finalize_selection``) shares one line shape across
# both directions — ``added {step} to`` and ``dropped {step} from``. Only the
# ``dropped ... from`` direction is a removal; the ``added`` direction is a
# force-include and MUST NOT be read as a cause.
_REMOVAL_CAUSE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        'posture_cutoff',
        re.compile(
            r'lane_resolution\s+—\s+execution_profile=[^,]+,\s+dropped\s+(?P<steps>.+?)'
            r'\s+from\s+phase_6\.steps\s+\(tier above posture cutoff\)'
        ),
    ),
    (
        'unresolved_ask_provider_drop',
        re.compile(
            r'unresolved_ask_provider_drop\s+—\s+dropped\s+(?P<steps>.+?)'
            r'\s+from\s+phase_6\.steps\s+\(unresolved lane:ask, provider absent\)'
        ),
    ),
    (
        'simplify_inactive',
        re.compile(r'(?P<steps>finalize-step-simplify)\s+omitted\s+—\s+change_type='),
    ),
    (
        'ceremony_finalize_never',
        re.compile(
            r'ceremony_finalize selection\s+—\s+finalize\.\w+=[^,]+,\s+dropped\s+(?P<steps>.+?)'
            r'\s+from\s+phase_6\.steps'
        ),
    ),
)

# Removal-cause tokens for rows where no recorded mechanism applies.
_CAUSE_NOT_REMOVED = 'not_removed'
_CAUSE_NOT_EVALUATED = 'not_evaluated'
_CAUSE_PREDICATE_EVALUATED = 'predicate_evaluated'
_CAUSE_UNESTABLISHABLE = 'unestablishable'


def _bare_step(name: str) -> str:
    """Normalize a step key to its bare form.

    Recorded decision-log lines may name a step with a ``default:`` /
    ``project:`` prefix while ``_PRUNABLE_PREDICATES`` keys are bare. Both sides
    are normalized with the same ``rsplit(':', 1)`` rule ``_phase_6_steps``
    applies, so a prefixed recorded drop matches the bare predicate key.
    """
    return name.rsplit(':', 1)[-1] if ':' in name else name


def _parse_step_tokens(raw: str) -> list[str]:
    """Split a decision-log ``{steps}`` capture into bare step names.

    The lane-resolution mechanism renders its step list as a Python list repr
    (``['a', 'b']``); the other three name a single bare step. Both forms are
    tolerated.
    """
    text = raw.strip()
    if text.startswith('[') and text.endswith(']'):
        text = text[1:-1]
    tokens = []
    for part in text.split(','):
        token = part.strip().strip('\'"').strip()
        if token:
            tokens.append(_bare_step(token))
    return tokens


def resolve_removal_causes(decision_lines: list[str]) -> dict[str, str]:
    """Return ``{bare_step_name: removal_cause}`` from the recorded decision log.

    Pure over its input — no filesystem access. The first mechanism that names a
    step wins, so a step removed once and later re-added-then-dropped keeps its
    earliest recorded cause.
    """
    causes: dict[str, str] = {}
    for line in decision_lines:
        for cause, pattern in _REMOVAL_CAUSE_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            for step in _parse_step_tokens(match.group('steps')):
                causes.setdefault(step, cause)
    return causes


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


def load_manifest(plan_dir: Path) -> dict[str, Any] | None:
    """Return the parsed manifest dict, or ``None`` when ``execution.toon`` is absent."""
    manifest_path = plan_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    try:
        raw = manifest_path.read_text(encoding='utf-8')
    except OSError:
        return None
    parsed = parse_toon(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f'{MANIFEST_FILENAME} must parse to a top-level dict')
    return parsed


def load_status_metadata(plan_dir: Path) -> dict[str, Any]:
    """Return ``status.metadata`` (empty dict when status.json is absent/malformed)."""
    status_path = plan_dir / STATUS_FILENAME
    if not status_path.exists():
        return {}
    try:
        status = json.loads(status_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    metadata = status.get('metadata') if isinstance(status, dict) else None
    return metadata if isinstance(metadata, dict) else {}


def load_decision_log_lines(plan_dir: Path) -> tuple[list[str], bool]:
    """Return ``(lines, log_readable)`` for the plan's decision log.

    ``log_readable`` is ``True`` only when the file existed AND was read
    successfully. A missing or unreadable log yields ``([], False)`` — the
    explicit discriminator that separates "the log records no removal cause for
    this step" (positive evidence) from "no log was available to record one"
    (no evidence at all). Collapsing both to ``[]``, as the previous loader did,
    is exactly the ambiguity that let an unestablishable cause be reported as a
    substantiated mis-prune.
    """
    log_path = plan_dir.joinpath(*DECISION_LOG_RELPATH)
    if not log_path.exists():
        return [], False
    try:
        return log_path.read_text(encoding='utf-8').splitlines(), True
    except OSError:
        return [], False


def lane_resolution_view(decision_lines: list[str]) -> list[str]:
    """Return the ``lane_resolution`` subset of ``decision_lines``.

    The thin view feeding the report-facing ``recompose_divergence`` /
    ``recorded_lane_decisions`` fields. Widening the underlying loader must not
    change what those two fields count, so the filter lives here rather than in
    the loader.
    """
    return [line for line in decision_lines if _LANE_DECISION_RE.search(line)]


def load_decision_lane_entries(plan_dir: Path) -> list[str]:
    """Return the decision-log lines mentioning ``lane_resolution``."""
    lines, _readable = load_decision_log_lines(plan_dir)
    return lane_resolution_view(lines)


def load_diff_files(diff_file: str | None) -> list[str]:
    """Return the realized footprint path list from a pre-saved diff file.

    ``--diff-file`` carries one path per line (the end-of-execute diff). Absent
    or unreadable → an empty footprint (the predicate re-evaluation degrades to
    "no realized footprint", which is a skip, not a false positive).
    """
    if not diff_file:
        return []
    path = Path(diff_file)
    if not path.exists():
        return []
    try:
        return [line.strip() for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    except OSError:
        return []


def _is_bookkeeping(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _BOOKKEEPING_PREFIXES)


def _is_docs(path: str) -> bool:
    return path.endswith(_DOCS_SUFFIXES)


def _is_test(path: str) -> bool:
    return any(token in path for token in _TEST_DIR_TOKENS) or bool(_TEST_NAME_RE.search(path))


def footprint_has_production(files: list[str]) -> bool:
    """Return True when the realized footprint touched non-doc, non-test production code."""
    for path in files:
        if _is_bookkeeping(path) or _is_docs(path) or _is_test(path):
            continue
        return True
    return False


def sum_execution_log_tokens(manifest: dict[str, Any]) -> int:
    """Sum the ``total_tokens`` attribution across every ``execution_log`` row."""
    rows = manifest.get('execution_log')
    if not isinstance(rows, list):
        return 0
    total = 0
    for row in rows:
        if isinstance(row, dict):
            value = row.get('total_tokens')
            if isinstance(value, int):
                total += value
            elif isinstance(value, str) and value.isdigit():
                total += int(value)
    return total


def _phase_6_steps(manifest: dict[str, Any]) -> list[str]:
    phase_6 = manifest.get('phase_6')
    if isinstance(phase_6, dict):
        steps = phase_6.get('steps')
        if isinstance(steps, list):
            return [str(s) for s in steps]
    return []


def evaluate_mis_prunes(
    manifest: dict[str, Any],
    footprint: list[str],
    have_footprint: bool,
    decision_lines: list[str],
    log_readable: bool,
) -> list[dict[str, Any]]:
    """Resolve each absent prunable step's REMOVAL CAUSE, then re-evaluate its predicate.

    The removal *fact* never implies the removal *cause*: a prunable step can
    leave ``phase_6.steps`` through four recorded mechanisms that are all
    orthogonal to the footprint (see ``_REMOVAL_CAUSE_PATTERNS``). The recorded
    decision log is consulted FIRST, and the predicate is re-evaluated only for a
    step whose removal no recorded mechanism explains.

    The verdict rules are mutually exclusive and jointly exhaustive over an
    absent step:

    ===================================================  ==============
    Absent step's state                                  Verdict
    ===================================================  ==============
    No realized footprint                                ``skip``
    Named by a recorded non-predicate cause              ``skip``
    Log unreadable / absent (``log_readable == False``)  ``inconclusive``
    Readable log names no cause, predicate now false     ``fail``
    Readable log names no cause, predicate still holds   ``pass``
    ===================================================  ==============

    ``log_readable`` is the SOLE discriminator between ``fail`` and
    ``inconclusive``. The composer emits a decision-log line for every one of the
    four mechanisms, so a *readable* log naming no cause for this step is
    positive evidence the predicate is the remover — a substantiated ``fail``.
    An *unreadable or absent* log substantiates nothing, so the honest verdict is
    ``inconclusive``.

    Every returned row carries ``removal_cause``: the mechanism token for a
    recorded removal, ``predicate_evaluated`` where the predicate actually ran,
    and a descriptive token otherwise.
    """
    final_steps = {s.rsplit(':', 1)[-1] if ':' in s else s for s in _phase_6_steps(manifest)}
    bare_final = set(_phase_6_steps(manifest)) | final_steps
    has_production = footprint_has_production(footprint)
    removal_causes = resolve_removal_causes(decision_lines)
    checks: list[dict[str, Any]] = []
    for step, predicate in _PRUNABLE_PREDICATES.items():
        absent = step not in bare_final
        if not absent:
            checks.append({
                'check': f'mis_prune:{step}',
                'status': 'pass',
                'predicate': predicate,
                'removal_cause': _CAUSE_NOT_REMOVED,
                'detail': 'step ran',
            })
            continue
        if not have_footprint:
            checks.append({
                'check': f'mis_prune:{step}',
                'status': 'skip',
                'predicate': predicate,
                'removal_cause': _CAUSE_NOT_EVALUATED,
                'detail': 'no realized footprint',
            })
            continue
        recorded_cause = removal_causes.get(step)
        if recorded_cause is not None:
            checks.append({
                'check': f'mis_prune:{step}',
                'status': 'skip',
                'predicate': predicate,
                'removal_cause': recorded_cause,
                'detail': f'dropped by {recorded_cause}, prune predicate not evaluated',
            })
            continue
        if not log_readable:
            checks.append({
                'check': f'mis_prune:{step}',
                'status': 'inconclusive',
                'predicate': predicate,
                'removal_cause': _CAUSE_UNESTABLISHABLE,
                'detail': 'removal cause unestablishable — decision log absent or unreadable',
            })
            continue
        # no_code_delta predicate is now FALSE when the diff touched production.
        if predicate == 'no_code_delta' and has_production:
            checks.append({
                'check': f'mis_prune:{step}',
                'status': 'fail',
                'predicate': predicate,
                'removal_cause': _CAUSE_PREDICATE_EVALUATED,
                'detail': f'{step} skipped as no_code_delta but the realized footprint touched production code',
            })
        else:
            checks.append({
                'check': f'mis_prune:{step}',
                'status': 'pass',
                'predicate': predicate,
                'removal_cause': _CAUSE_PREDICATE_EVALUATED,
                'detail': 'predicate still holds',
            })
    return checks


def evaluate_cost_preview(manifest: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    """Compare the init cost preview against the actual ``execution_log`` token total.

    The predicted total is the init-dialogue preview persisted to
    ``status.metadata.execution_profile_cost_preview`` (when present); the actual
    is the summed ``execution_log`` attribution. The signed delta feeds the
    §4.6a ``cost_size_token_table`` recalibration loop.
    """
    actual = sum_execution_log_tokens(manifest)
    raw_predicted = metadata.get('execution_profile_cost_preview')
    predicted: int | None = None
    if isinstance(raw_predicted, int):
        predicted = raw_predicted
    elif isinstance(raw_predicted, str) and raw_predicted.isdigit():
        predicted = int(raw_predicted)
    preview: dict[str, Any] = {'actual_tokens': actual, 'predicted_tokens': predicted}
    if predicted is not None:
        preview['delta_tokens'] = actual - predicted
        preview['delta_pct'] = round((actual - predicted) / predicted * 100, 1) if predicted else None
    return preview


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    plan_id = args.plan_id or plan_dir.name

    manifest = load_manifest(plan_dir)
    if manifest is None:
        return {
            'status': 'skipped',
            'aspect': 'routing-decisions',
            'plan_id': plan_id,
            'plan_dir': str(plan_dir),
            'manifest_present': False,
            'reason': f'{MANIFEST_FILENAME} not found',
            'checks': [],
            'summary': {'passed': 0, 'failed': 0, 'skipped': 0},
        }

    metadata = load_status_metadata(plan_dir)
    decision_lines, log_readable = load_decision_log_lines(plan_dir)
    lane_decision_entries = lane_resolution_view(decision_lines)
    footprint = load_diff_files(args.diff_file)
    have_footprint = bool(footprint)

    mis_prune_checks = evaluate_mis_prunes(
        manifest, footprint, have_footprint, decision_lines, log_readable
    )
    cost_preview = evaluate_cost_preview(manifest, metadata)

    summary = {
        'passed': sum(1 for c in mis_prune_checks if c['status'] == 'pass'),
        'failed': sum(1 for c in mis_prune_checks if c['status'] == 'fail'),
        'skipped': sum(1 for c in mis_prune_checks if c['status'] == 'skip'),
    }

    return {
        'status': 'success',
        'aspect': 'routing-decisions',
        'plan_id': plan_id,
        'plan_dir': str(plan_dir),
        'manifest_present': True,
        # Recorded routing decisions (facts).
        'posture': metadata.get('execution_profile'),
        'planning_lane': metadata.get('planning_lane'),
        # Deterministic predicate re-evaluation.
        'mis_prune_checks': mis_prune_checks,
        'cost_preview': cost_preview,
        # Forensic facts for the LLM judgment.
        'recompose_divergence': {'lane_resolution_log_entries': len(lane_decision_entries)},
        'recorded_lane_decisions': lane_decision_entries,
        'summary': summary,
        # The OVER/UNDER posture counterfactual is an LLM judgment over the facts
        # above — NOT computed here. See references/routing-decision-verification.md.
        'llm_judgement_required': True,
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Routing-decision verification aspect — deterministic predicate re-evaluation',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser('run', help='Re-evaluate routing-decision predicates', allow_abbrev=False)
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
    run_parser.add_argument(
        '--diff-file',
        default=None,
        help='Pre-saved realized footprint (one path per line). Drives the prune-predicate re-evaluation.',
    )
    run_parser.set_defaults(func=cmd_run)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
