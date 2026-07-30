#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic classification-validation gate (flag-not-block).

Cross-checks a plan's ``change_type`` and ``scope_estimate`` against cheap
request signals at plan-init time and emits a phase-1-init Q-Gate finding on a
mismatch — it NEVER blocks routing. The gate is a pre-route validation pass:
``planning-lane route`` invokes it before resolving the lane, and the
``classification-validate`` subcommand exposes it standalone.

Three mismatch classes are detected, each chosen to raise zero false positives:

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

3. **scale_mismatch_light_routing** — a persisted ``scope_estimate`` of
   ``surgical`` alongside a request body that reads as ``multi_module`` to the
   sensor: either its distinct-path count has reached the ``multi_module`` floor,
   or the body could not be safely scanned in full (``scan_incomplete``), which the
   sensor itself bands ``multi_module`` BEFORE consulting the count because a
   truncated total is a lower bound, not a count. This is the safety net for the one
   residual the pre-route sensor cannot close on its own: the sensor is not the only
   writer of ``references.scope_estimate`` (phase-2-refine's module-mapping
   derivation and phase-3-outline's refinement both write it through the generic
   setter), so a narrow band can outlive a body that plainly is not narrow. The
   check is exact rather than heuristic — it compares two readings of the SAME
   document and fires only when they genuinely disagree — and the threshold and the
   bounded path scanner are both imported from ``_cmd_planning_lane`` rather than
   restated, so the gate can never drift away from the sensor it is checking.

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
from file_ops import get_plan_dir, read_json
from plan_logging import log_entry

# The Q-Gate phase the classification finding attaches to. ``1-init`` is not a
# Q-Gate phase (the store opens at ``2-refine``); ``2-refine`` is where
# classification is refined, so the finding surfaces to the acting phase.
_GATE_QGATE_PHASE = '2-refine'

# scope_estimate values that count as "unestimated" for mismatch class 2.
_NULL_SCOPE_VALUES = frozenset({'', 'none'})

# The one persisted band mismatch class 3 treats as a narrow claim. Only the
# genuinely-narrow band qualifies: `single_module` is the catch-all middle band, so
# pairing it with a high path count is not a contradiction worth flagging.
_NARROW_CLAIM_SCOPE = 'surgical'


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


def _detect_scale_mismatch_light_routing(
    plan_id: str, references: dict[str, Any]
) -> dict[str, Any] | None:
    """Mismatch class 3 — a narrow persisted band over a demonstrably large body.

    Returns a finding-descriptor dict when ``scope_estimate`` is persisted as
    ``surgical`` while the request body reads as multi-module to the sensor — i.e.
    the persisted band claims the work is tightly bounded while the body the sensor
    scores says it is not. Returns ``None`` otherwise, including for an unscoreable
    body (nothing to contradict).

    Exact, not heuristic: it re-derives the reading from the SAME whole-body read the
    sensor uses, so the two readings are comparable by construction and the check
    fires only on a genuine disagreement.

    **Scan-truthfulness — the reason this routes through ``_safe_path_scan`` and not
    ``_distinct_paths``.** ``_distinct_paths`` DISCARDS the ``scan_incomplete`` flag,
    returning only whatever paths the ReDoS-bounded scan managed to reach. On a body
    too large or adversarially-repetitive to scan in full that total is an UNDERCOUNT,
    and comparing an undercount against ``_MULTI_MODULE_MIN_PATHS`` would let this
    detector silently return ``None`` on exactly the body ``classify_scope_pure``
    bands ``multi_module`` — its ``scan_incomplete`` row wins BEFORE the path-count
    rows are consulted, precisely because a partial count must never read as an
    accurate narrow one. Reading the flag here keeps the gate on the sensor's own
    verdict: an incomplete scan is NOT evidence of narrowness, so it falls through to
    the mismatch rather than short-circuiting past it. Treating a truncated scan as a
    low count would reproduce, inside this safety net, the scale-blind false negative
    the net exists to catch.

    Reachability — load-bearing, and the reason this class needs call sites beyond
    ``route``. Inside ``planning-lane route`` this check runs immediately after
    phase-1-init Step 8a.5 wrote ``scope_estimate`` with the SAME
    ``_safe_path_scan`` / ``_MULTI_MODULE_MIN_PATHS`` logic re-derived below, so the
    two readings cannot disagree there and the class can never fire from that site
    alone. It becomes reachable only where a LATER writer overwrites the band: the
    phase-2-refine Step 13 ``scope_estimate`` persist (Persist and Return Results —
    Step 9 is where the value is DERIVED, not where it is re-validated) and the
    phase-3-outline light-lane persist both re-invoke ``classification-validate``
    immediately after their overwrite for exactly this reason. The light-lane site is the one that matters
    for this class specifically — a light-routed plan never enters refine's
    clarification loop, so the refine-side re-validation never runs for it. Removing
    either re-invocation turns this detector back into a guard that cannot fire.
    """
    scope = references.get('scope_estimate')
    if not isinstance(scope, str) or scope.strip().lower() != _NARROW_CLAIM_SCOPE:
        return None

    # DEFERRED IMPORT, and it must stay deferred: `_cmd_planning_lane` imports
    # `run_classification_validation` from THIS module at module scope, so a
    # top-level import back would close an import cycle and fail — at the time
    # `_cmd_planning_lane` is mid-initialisation, `_safe_path_scan` does not exist
    # yet. Importing here (rather than restating the threshold or the scanner) is
    # what keeps the gate and the sensor on one definition. The `try/except
    # ImportError` mirrors `_emit_finding`'s deferred `_findings_core` import below:
    # `run_classification_validation` is documented flag-not-block and is called with
    # no surrounding guard from `cmd_planning_lane_route`, so an import failure must
    # degrade THIS one advisory check, never crash `planning-lane route`.
    try:
        from _cmd_planning_lane import (  # noqa: PLC0415
            _MULTI_MODULE_MIN_PATHS,
            _read_request_body,
            _safe_path_scan,
        )
    except ImportError:
        return None

    body = _read_request_body(plan_id)
    if not body:
        return None

    distinct_paths, scan_incomplete = _safe_path_scan(body)
    distinct_path_count = len(distinct_paths)
    # An incomplete scan is NOT evidence of narrowness: the count is a lower bound,
    # and the sensor bands such a body multi_module before it ever consults the
    # count. Only a COMPLETE scan below the floor clears the check.
    if not scan_incomplete and distinct_path_count < _MULTI_MODULE_MIN_PATHS:
        return None

    if scan_incomplete:
        evidence = (
            f'the request body could not be scanned in full — the ReDoS-bounded path scan hit its '
            f'line-length or budget limit after finding {distinct_path_count} distinct file '
            f'path(s), so that total is a lower bound, not a count. The scope sensor bands such a '
            f'body multi_module for exactly this reason'
        )
    else:
        evidence = (
            f'the request body names {distinct_path_count} distinct file paths — at or above the '
            f'multi_module floor of {_MULTI_MODULE_MIN_PATHS}'
        )

    return {
        'mismatch': 'scale_mismatch_light_routing',
        'title': 'Classification mismatch: scope_estimate=surgical over a multi-module-sized request',
        'detail': (
            f'references.scope_estimate is persisted as {_NARROW_CLAIM_SCOPE!r}, but {evidence}. '
            f'A narrow band suppresses the S3/S4 escalation signals and projects the minimal '
            f'execution posture, so re-confirm the scope during refinement before the narrow '
            f'claim is relied on.'
        ),
    }


def run_classification_validation(plan_id: str) -> dict[str, Any]:
    """Run all three mismatch checks and emit one Q-Gate finding per fired mismatch.

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
    scale_mismatch = _detect_scale_mismatch_light_routing(plan_id, references)
    if scale_mismatch is not None:
        descriptors.append(scale_mismatch)

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
        from _findings_core import add_qgate_finding
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
