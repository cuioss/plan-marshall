#!/usr/bin/env python3
"""Measure achieved thoroughness for a plan (HYBRID: deterministic + LLM).

The achieved-thoroughness measurement is the *achieved* side of the coverage
contract gated by the ``coverage_contract`` phase-handshake invariant (D4). It
is hybrid by construction:

- **Deterministic item-coverage** — reuses the artifact-consistency footprint
  primitive (``extract_affected_files_per_deliverable`` + the recall threshold
  from ``check-artifact-consistency.py``): declared in-scope files from
  ``solution_outline.md`` ``Affected files:`` bullets vs the actual touched
  footprint in ``references.json`` ``modified_files``. The recall ratio maps to
  an item-coverage rung (full footprint ≥ threshold → meets T2 item coverage;
  partial → below, T1).
- **LLM relation-depth verdict** — whether the declared T3+/T4+ relations were
  actually traced (callers/tests/cross-refs for T3, call-graph/cross-ref-graph
  for T4). The deterministic script does NOT compute this; the consuming
  workflow (``plan-retrospective``) runs the auditor pass and folds the verdict
  in. This script accepts the auditor's rung via ``--relation-depth-rung`` (or
  records the ``unaudited`` placeholder when absent) and the achieved rung is
  the FLOOR of the item-coverage rung and the relation-depth rung
  (grade-to-the-floor rule, ``dev-agent-behavior-rules/standards/thoroughness.md``).

The script emits ``work/coverage-measurement-{phase}.toon`` — the exact artifact
the D4 capture function ``_capture_coverage_contract`` reads to compute the
achieved-vs-declared shortfall.

Usage:
    python3 measure-thoroughness.py run --plan-id EXAMPLE --mode live --phase 5-execute
    python3 measure-thoroughness.py run --plan-id EXAMPLE --mode live --phase 5-execute \
        --relation-depth-rung T4 --declared-scope component
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

from file_ops import base_path, output_toon, safe_main, serialize_toon  # type: ignore[import-not-found]
from input_validation import (  # type: ignore[import-not-found]
    add_plan_id_arg,
    parse_args_with_toon_errors,
)


def _load_artifact_consistency() -> Any:
    """Load the hyphenated ``check-artifact-consistency.py`` sibling module.

    The footprint primitive (``extract_affected_files_per_deliverable`` and the
    shared ``_RECALL_THRESHOLD``) lives in ``check-artifact-consistency.py``;
    its hyphenated filename cannot be imported with a plain ``import``
    statement, so it is loaded by file path from this script's own directory
    (the executor places that directory on ``sys.path`` / ``__file__`` is
    resolvable). Reusing the existing helper keeps a single source of truth for
    the declared-vs-actual footprint comparison (lean posture — do NOT
    re-implement the comparison logic here).
    """
    sibling = Path(__file__).resolve().parent / 'check-artifact-consistency.py'
    spec = importlib.util.spec_from_file_location('_check_artifact_consistency', sibling)
    if spec is None or spec.loader is None:
        raise ImportError(f'cannot load sibling module at {sibling}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_artifact_consistency = _load_artifact_consistency()
extract_affected_files_per_deliverable = _artifact_consistency.extract_affected_files_per_deliverable
_RECALL_THRESHOLD = _artifact_consistency._RECALL_THRESHOLD

# Ordinal rank over the thoroughness ladder, kept in lock-step with
# ``dev-agent-behavior-rules/standards/thoroughness.md`` § Thoroughness Ladder.
_THOROUGHNESS_RANK: dict[str, int] = {'T1': 1, 'T2': 2, 'T3': 3, 'T4': 4, 'T5': 5}

# Placeholder the deterministic pass records when the LLM relation-depth
# auditor has not run yet. Treated as the lowest rung for the floor so an
# unaudited measurement never over-claims relation depth.
_RELATION_DEPTH_UNAUDITED = 'unaudited'

# Item-coverage rungs: a full footprint (recall >= threshold) meets the
# full-read T2 item-coverage rung; a partial footprint is the sampled T1 rung.
_ITEM_COVERAGE_FULL_RUNG = 'T2'
_ITEM_COVERAGE_PARTIAL_RUNG = 'T1'


def resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    """Resolve the plan directory for ``live`` / ``archived`` mode.

    Mirrors ``check-artifact-consistency.resolve_plan_dir`` so both aspects
    share one resolution contract.
    """
    if mode == 'live':
        if not plan_id:
            raise ValueError('--plan-id is required for live mode')
        return base_path('plans', plan_id)
    if mode == 'archived':
        if not archived_plan_path:
            raise ValueError('--archived-plan-path is required for archived mode')
        return Path(archived_plan_path)
    raise ValueError(f'Unknown mode: {mode!r}')


def _read_modified_files(references_path: Path) -> set[str]:
    """Return the ``modified_files`` set from ``references.json`` (empty on error)."""
    if not references_path.exists():
        return set()
    try:
        refs = json.loads(references_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(refs, dict):
        return set()
    raw = refs.get('modified_files', [])
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return set()
    return {str(p).strip() for p in raw if p}


def compute_item_coverage(solution_content: str, references_path: Path) -> tuple[float, str]:
    """Return ``(recall_ratio, item_coverage_rung)`` from the footprint primitive.

    Reuses ``extract_affected_files_per_deliverable`` (declared) vs
    ``references.json`` ``modified_files`` (actual) and the shared
    ``_RECALL_THRESHOLD``. When no files are declared, recall is ``1.0`` (an
    empty contract is trivially met) and the rung is the full-read rung.
    """
    declared = set(extract_affected_files_per_deliverable(solution_content))
    if not declared:
        return 1.0, _ITEM_COVERAGE_FULL_RUNG
    actual = _read_modified_files(references_path)
    found = declared & actual
    recall = len(found) / len(declared)
    rung = _ITEM_COVERAGE_FULL_RUNG if recall >= _RECALL_THRESHOLD else _ITEM_COVERAGE_PARTIAL_RUNG
    return recall, rung


def floor_rung(item_coverage_rung: str, relation_depth_rung: str) -> str:
    """Return the lower of two thoroughness rungs (grade-to-the-floor rule).

    The achieved thoroughness is the FLOOR across the deterministic
    item-coverage rung and the LLM relation-depth rung. An unranked
    relation-depth value (e.g. the ``unaudited`` placeholder or a malformed
    token) floors the result to the item-coverage rung's value only when it is
    the lower of the two — an unaudited measurement therefore cannot raise the
    achieved rung above what item coverage alone supports.
    """
    item_rank = _THOROUGHNESS_RANK.get(item_coverage_rung, 1)
    relation_rank = _THOROUGHNESS_RANK.get(relation_depth_rung)
    if relation_rank is None:
        # Relation depth unaudited / unknown — it cannot raise the floor, so
        # the achieved rung is the item-coverage rung.
        return item_coverage_rung
    if relation_rank <= item_rank:
        return relation_depth_rung
    return item_coverage_rung


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    phase = args.phase

    solution_path = plan_dir / 'solution_outline.md'
    solution_content = solution_path.read_text(encoding='utf-8') if solution_path.exists() else ''
    references_path = plan_dir / 'references.json'

    recall, item_coverage_rung = compute_item_coverage(solution_content, references_path)
    relation_depth_rung = args.relation_depth_rung or _RELATION_DEPTH_UNAUDITED
    achieved_thoroughness = floor_rung(item_coverage_rung, relation_depth_rung)
    achieved_scope = args.declared_scope or 'inherit'

    measurement = {
        'deterministic_item_coverage': round(recall, 4),
        'item_coverage_rung': item_coverage_rung,
        'relation_depth_verdict': relation_depth_rung,
        'achieved_thoroughness': achieved_thoroughness,
        'achieved_scope': achieved_scope,
    }

    work_dir = plan_dir / 'work'
    work_dir.mkdir(parents=True, exist_ok=True)
    artifact = work_dir / f'coverage-measurement-{phase}.toon'
    artifact.write_text(serialize_toon(measurement) + '\n', encoding='utf-8')

    return {
        'status': 'success',
        'aspect': 'achieved_thoroughness',
        'plan_id': args.plan_id or plan_dir.name,
        'plan_dir': str(plan_dir),
        'phase': phase,
        'artifact': str(artifact),
        **measurement,
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Measure achieved thoroughness (hybrid deterministic + LLM auditor)',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser('run', help='Compute and emit the achieved cell', allow_abbrev=False)
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
        '--phase',
        required=True,
        help='Phase key for the measurement artifact (e.g. 5-execute)',
    )
    run_parser.add_argument(
        '--relation-depth-rung',
        choices=['T1', 'T2', 'T3', 'T4', 'T5'],
        help='LLM relation-depth auditor verdict (rung). Omit for the unaudited placeholder.',
    )
    run_parser.add_argument(
        '--declared-scope',
        help='Achieved scope rung to record on the artifact (e.g. component)',
    )
    run_parser.set_defaults(func=cmd_run)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()  # type: ignore[no-untyped-call]
