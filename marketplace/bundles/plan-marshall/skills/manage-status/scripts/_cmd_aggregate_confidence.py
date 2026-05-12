#!/usr/bin/env python3
"""Weighted-math confidence aggregator for phase-2-refine Step 10.

Replaces the prior multi-step LLM aggregation with a pure weighted-math
computation. Inputs are the six per-dimension scores produced by the
phase-2-refine analyzer (Correctness, Completeness, Consistency,
Non-Duplication, Ambiguity, Module Mapping); the script returns the
single overall confidence plus a per-dimension breakdown the caller
can include verbatim in the phase-2 return TOON.

The dimension weights mirror phase-2-refine SKILL.md § Step 10:

  - Correctness:        20 %
  - Completeness:       20 %
  - Consistency:        20 %
  - Non-Duplication:    10 %
  - Ambiguity:          20 %
  - Module Mapping:     10 %

Scores are 0..100 (inclusive). Missing dimensions default to 0; the
script never silently fabricates a value but does record absence in
``missing_dimensions`` so the caller can decide whether to abort.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _status_core import read_status, write_status
from file_ops import get_plan_dir  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]

# Canonical dimension weights from phase-2-refine § Step 10. Order is
# fixed so the breakdown is deterministic.
_DIMENSION_WEIGHTS: tuple[tuple[str, float], ...] = (
    ('correctness', 0.20),
    ('completeness', 0.20),
    ('consistency', 0.20),
    ('non_duplication', 0.10),
    ('ambiguity', 0.20),
    ('module_mapping', 0.10),
)

# CLI-friendly aliases for the dimension keys above. The script accepts
# either kebab-case (``--non-duplication``) or snake_case (``--non_duplication``)
# values from the caller; the canonical key remains snake_case.
_DIMENSION_FLAGS: dict[str, str] = {
    'correctness': 'correctness',
    'completeness': 'completeness',
    'consistency': 'consistency',
    'non_duplication': 'non_duplication',
    'non-duplication': 'non_duplication',
    'ambiguity': 'ambiguity',
    'module_mapping': 'module_mapping',
    'module-mapping': 'module_mapping',
}


def _validate_score(name: str, value: Any) -> float:
    """Coerce a raw score into a 0..100 float, clamping out-of-range inputs.

    Raises ``ValueError`` only when the input is non-numeric — invalid
    types must fail loudly so the caller can correct the input.
    """
    try:
        score = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Dimension {name!r} score is not numeric: {value!r}") from e
    if score < 0:
        return 0.0
    if score > 100:
        return 100.0
    return score


def _load_scores(args) -> tuple[dict[str, float], list[str]]:
    """Return ``(scores_by_dimension, missing_dimensions)``.

    The caller may supply scores either via ``--scores-file PATH`` (JSON
    object keyed by dimension) or as individual ``--<dimension> N`` flags.
    The two forms are mutually exclusive; the flag form takes precedence
    over the file when both are supplied (defensive — the argparser also
    enforces exclusivity).
    """
    scores: dict[str, float] = {}
    missing: list[str] = []

    if getattr(args, 'scores_file', None):
        payload_path = Path(args.scores_file)
        if not payload_path.exists():
            raise FileNotFoundError(f'Scores file not found: {payload_path}')
        try:
            raw = json.loads(payload_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            raise ValueError(f'Invalid JSON in scores file {payload_path}: {e}') from e
        if not isinstance(raw, dict):
            raise ValueError(f'Scores file {payload_path} must contain a JSON object')
        for key, value in raw.items():
            canonical = _DIMENSION_FLAGS.get(str(key).replace('-', '_'))
            if canonical is None:
                continue
            scores[canonical] = _validate_score(canonical, value)

    # CLI flags override / fill in the file payload.
    for flag_attr in ('correctness', 'completeness', 'consistency', 'non_duplication', 'ambiguity', 'module_mapping'):
        value = getattr(args, flag_attr, None)
        if value is not None:
            scores[flag_attr] = _validate_score(flag_attr, value)

    for dim, _weight in _DIMENSION_WEIGHTS:
        if dim not in scores:
            missing.append(dim)
            scores[dim] = 0.0

    return scores, missing


def cmd_aggregate_confidence(args) -> dict[str, Any]:
    """Compute the weighted confidence aggregate for phase-2-refine Step 10."""
    plan_id: str = args.plan_id
    persist: bool = bool(getattr(args, 'persist', False))

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'message': f'Plan directory not found: {plan_dir}',
        }

    try:
        scores, missing = _load_scores(args)
    except (FileNotFoundError, ValueError) as e:
        return {
            'status': 'error',
            'error': 'invalid_input',
            'message': str(e),
        }

    breakdown: list[dict[str, Any]] = []
    overall = 0.0
    for dim, weight in _DIMENSION_WEIGHTS:
        score = scores.get(dim, 0.0)
        weighted = round(score * weight, 3)
        overall += weighted
        breakdown.append(
            {
                'dimension': dim,
                'score': round(score, 3),
                'weight': weight,
                'weighted': weighted,
            }
        )
    overall = round(overall, 3)

    persisted = False
    if persist:
        try:
            status = read_status(plan_id)
        except FileNotFoundError:
            status = {}
        if 'metadata' not in status or not isinstance(status['metadata'], dict):
            status['metadata'] = {}
        status['metadata']['confidence'] = overall
        write_status(plan_id, status)
        log_entry(
            'work',
            plan_id,
            'INFO',
            f'[MANAGE-STATUS] (aggregate-confidence) confidence={overall} (dimensions: {len(breakdown)}, missing: {len(missing)}).',
        )
        persisted = True

    return {
        'status': 'success',
        'plan_id': plan_id,
        'confidence': overall,
        'breakdown': breakdown,
        'missing_dimensions': missing,
        'persisted': persisted,
    }
