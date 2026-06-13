#!/usr/bin/env python3
"""Deterministic classification-validation gate (flag-not-block).

Cross-checks a plan's ``change_type`` and ``scope_estimate`` against cheap
request signals at plan-init time and emits a phase-1-init Q-Gate finding on a
mismatch — it NEVER blocks routing. The gate is a pre-route validation pass:
``planning-lane route`` invokes it before resolving the lane, and the
``classification-validate`` subcommand exposes it standalone.

Two mismatch classes are detected, both chosen to raise zero false positives:

1. **feature-as-bug_fix** — ``change_type == 'bug_fix'`` while the deterministic
   change-type heuristic (the same scoring engine phase-3-outline uses) resolves
   a non-ambiguous ``feature`` winner from the request narrative. A request that
   reads as "add / create / implement a new X" mis-stamped as a bug fix is the
   recurring classification gap this guard catches. The heuristic must produce a
   *non-ambiguous* ``feature`` verdict for the flag to fire, so a borderline /
   tied narrative never trips it.

2. **non_empty_affected_files_with_null_scope** — ``references.affected_files`` is
   non-empty while ``references.scope_estimate`` is null / empty / ``none``. A
   plan that already enumerated touched files but left scope unestimated is a
   deterministic data gap (no heuristic involved), so this check is exact.

The Q-Gate finding is recorded against the ``2-init`` → ``2-refine`` boundary:
``1-init`` is not a Q-Gate phase (the Q-Gate store opens at ``2-refine``), and
``2-refine`` is exactly where classification is revisited, so the finding
surfaces to the phase that can act on it. The gate always returns
``status: success`` — the ``mismatches`` list and ``finding_*`` fields report
what fired; routing is never gated.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from _cmd_change_type_heuristic import (
    _apply_compound_intent_guard,
    _load_request_narrative,
    _pick_winner,
    _score_change_types,
    _tokenize,
)
from _status_core import read_status
from file_ops import get_plan_dir, read_json  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]

# The Q-Gate phase the classification finding attaches to. ``1-init`` is not a
# Q-Gate phase (the store opens at ``2-refine``); ``2-refine`` is where
# classification is refined, so the finding surfaces to the acting phase.
_GATE_QGATE_PHASE = '2-refine'

# scope_estimate values that count as "unestimated" for mismatch class 2.
_NULL_SCOPE_VALUES = frozenset({'', 'none'})


def _read_references(plan_id: str) -> dict[str, Any]:
    """Return the plan's references.json as a dict (empty on any failure)."""
    try:
        references = read_json(get_plan_dir(plan_id) / 'references.json', default={})
    except (OSError, json.JSONDecodeError):
        return {}
    return references if isinstance(references, dict) else {}


def _detect_feature_as_bug_fix(plan_id: str, change_type: str | None) -> dict[str, Any] | None:
    """Mismatch class 1 — bug_fix stamp over a non-ambiguous feature narrative.

    Returns a finding-descriptor dict when the heuristic resolves a
    non-ambiguous ``feature`` winner while ``change_type == 'bug_fix'``; returns
    ``None`` otherwise (including when the narrative is missing or the heuristic
    is ambiguous — no false positive).
    """
    if change_type != 'bug_fix':
        return None

    narrative, source = _load_request_narrative(plan_id)
    if source is None:
        return None

    tokens = _tokenize(narrative)
    scores = _score_change_types(tokens)
    scores = _apply_compound_intent_guard(scores, tokens)
    winner, confidence, ambiguous = _pick_winner(scores)

    if ambiguous or winner != 'feature':
        return None

    return {
        'mismatch': 'feature_as_bug_fix',
        'title': 'Classification mismatch: change_type=bug_fix over a feature-shaped request',
        'detail': (
            f'change_type is stamped bug_fix, but the deterministic change-type heuristic '
            f'resolves a non-ambiguous feature winner (confidence={confidence}) from the request '
            f'narrative. Re-confirm the change_type during refinement.'
        ),
    }


def _detect_affected_files_without_scope(references: dict[str, Any]) -> dict[str, Any] | None:
    """Mismatch class 2 — non-empty affected_files with a null scope_estimate.

    Returns a finding-descriptor dict when ``affected_files`` is a non-empty list
    while ``scope_estimate`` is missing / empty / ``none``; returns ``None``
    otherwise. Deterministic — no heuristic, no false positives.
    """
    affected = references.get('affected_files')
    if not isinstance(affected, list) or not affected:
        return None

    scope = references.get('scope_estimate')
    scope_norm = scope.strip().lower() if isinstance(scope, str) else None
    if scope_norm is not None and scope_norm not in _NULL_SCOPE_VALUES:
        return None

    return {
        'mismatch': 'non_empty_affected_files_with_null_scope',
        'title': 'Classification mismatch: affected_files non-empty but scope_estimate is unset',
        'detail': (
            f'references.affected_files lists {len(affected)} file(s) but scope_estimate is '
            f'{scope!r}. Estimate the scope during refinement so the lane router and manifest '
            f'composer see a concrete band.'
        ),
    }


def run_classification_validation(plan_id: str) -> dict[str, Any]:
    """Run both mismatch checks and emit one Q-Gate finding per fired mismatch.

    This is the reusable entry point: the ``classification-validate`` subcommand
    calls it directly, and ``planning-lane route`` calls it as a pre-route pass.
    Always returns ``status: success`` — the gate is flag-not-block.

    Returns a dict carrying the resolved ``change_type`` / ``scope_estimate``, the
    list of fired ``mismatches`` (each a ``{mismatch, title, finding_status,
    hash_id}`` row), and ``findings_emitted`` (the count of newly-recorded
    findings; deduplicated re-runs do not increment it).
    """
    try:
        status = read_status(plan_id)
    except FileNotFoundError:
        status = {}
    metadata = status.get('metadata') if isinstance(status, dict) else None
    change_type = metadata.get('change_type') if isinstance(metadata, dict) else None

    references = _read_references(plan_id)
    scope_estimate = references.get('scope_estimate')

    descriptors: list[dict[str, Any]] = []
    feature_mismatch = _detect_feature_as_bug_fix(plan_id, change_type)
    if feature_mismatch is not None:
        descriptors.append(feature_mismatch)
    scope_mismatch = _detect_affected_files_without_scope(references)
    if scope_mismatch is not None:
        descriptors.append(scope_mismatch)

    mismatches: list[dict[str, Any]] = []
    findings_emitted = 0
    for descriptor in descriptors:
        finding_status, hash_id = _emit_finding(plan_id, descriptor)
        if finding_status == 'success':
            findings_emitted += 1
        mismatches.append(
            {
                'mismatch': descriptor['mismatch'],
                'title': descriptor['title'],
                'finding_status': finding_status,
                'hash_id': hash_id,
            }
        )
        log_entry(
            'decision',
            plan_id,
            'WARNING',
            (
                f'(plan-marshall:manage-status:classification-validate) Mismatch '
                f'{descriptor["mismatch"]} flagged (finding_status={finding_status}) — '
                f'Q-Gate finding recorded against phase {_GATE_QGATE_PHASE}; routing NOT blocked'
            ),
        )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'change_type': change_type,
        'scope_estimate': scope_estimate,
        'mismatches': mismatches,
        'mismatch_count': len(mismatches),
        'findings_emitted': findings_emitted,
        'blocked': False,
    }


def _emit_finding(plan_id: str, descriptor: dict[str, Any]) -> tuple[str, str | None]:
    """Record one classification Q-Gate finding; return ``(status, hash_id)``.

    Best-effort: an import or write failure degrades to ``('unrecorded', None)``
    so the gate never raises — flag-not-block means a finding-store hiccup must
    not gate routing. Cross-skill import of ``_findings_core`` resolves via the
    executor's PYTHONPATH (and the test conftest's).
    """
    try:
        from _findings_core import add_qgate_finding  # type: ignore[import-not-found]
    except ImportError:
        return 'unrecorded', None

    try:
        result = add_qgate_finding(
            plan_id=plan_id,
            phase=_GATE_QGATE_PHASE,
            source='qgate',
            finding_type='anti-pattern',
            title=descriptor['title'],
            detail=descriptor['detail'],
            component='plan-marshall:manage-status',
            severity='warning',
        )
    except Exception:
        return 'unrecorded', None

    if not isinstance(result, dict):
        return 'unrecorded', None
    return str(result.get('status', 'unrecorded')), result.get('hash_id')


def cmd_classification_validate(args: argparse.Namespace) -> dict[str, Any]:
    """Handle ``classification-validate --plan-id PLAN_ID`` (standalone gate run)."""
    plan_id: str = args.plan_id

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'message': f'Plan directory not found: {plan_dir}',
        }

    return run_classification_validation(plan_id)
