#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""One deterministic ingestion pass over quarantined ``raw_input`` free-text.

Producers file untrusted free-text under a quarantined ``raw_input.{field}``
sub-object (see ``_findings_core._quarantine_raw_input``); the top-level record
fields stay clean-by-construction until this pass runs. ``ingest_findings``
iterates every PENDING finding in the plan ledger — the per-plan findings across
all types plus the per-phase Q-Gate findings — and for each finding carrying a
``raw_input`` sub-object:

  * runs the ``validate_struct`` ``finding`` schema over the ``raw_input`` mapping
    in-process (``validate_candidate``), which enforces additionalProperties:false,
    per-field ``maxLength`` clamping, and the domain allowlist — the single
    containment boundary; and
  * on ``status: success`` promotes each clamped value to the top-level field of
    the same name, leaving ``raw_input.*`` in place for audit; or
  * on a validator rejection resolves the finding as ``rejected`` (recording the
    violation as the ``resolution_detail``) rather than promoting.

The invariant this guarantees for the downstream triage pass: NO top-level field
is ever populated from an un-validated ``raw_input`` value — the top-level read
surface triage consumes is clean-by-construction.

Stdlib-only — no external dependencies (except shared modules via PYTHONPATH).
"""

from typing import Any

from _findings_core import (
    get_findings_path,
    get_qgate_path,
    query_findings,
    query_qgate_findings,
    resolve_finding,
    resolve_qgate_finding,
)
from constants import QGATE_PHASES
from jsonl_store import update_jsonl
from validate_struct import validate_candidate

# The validate_struct schema selector for ledger free-text ingestion.
FINDING_SCHEMA = 'finding'

# The resolution a validator rejection assigns to a finding whose quarantined
# free-text failed schema/allowlist validation (a non-pending, non-blocking
# terminal resolution — the finding is excluded from the triage read surface).
REJECTED_RESOLUTION = 'rejected'


def _rejection_detail(result: dict[str, Any]) -> str:
    """Build a ``resolution_detail`` string naming why a raw_input struct rejected."""
    parts = result.get('violations') or result.get('rejected_urls')
    if parts:
        return 'raw_input ingestion rejected: ' + '; '.join(str(p) for p in parts)
    return 'raw_input ingestion rejected: ' + str(result.get('message', 'validation failed'))


def _classify(record: dict[str, Any], schema: str) -> tuple[str, Any, list[str]]:
    """Classify one finding's ``raw_input`` — a pure query, no side effects.

    Returns ``(outcome, payload, clamped)`` where:
      * ``skipped``  → ``payload`` is ``None`` (the finding carries no ``raw_input``);
      * ``promoted`` → ``payload`` is the validated+clamped fields dict to write to
        the record's top level;
      * ``rejected`` → ``payload`` is the ``resolution_detail`` string.
    The side-effecting writeback / resolution is performed by the caller so this
    function stays a pure classifier (command-query separation).
    """
    raw = record.get('raw_input')
    if not raw:
        return 'skipped', None, []

    result = validate_candidate(schema, raw)
    if result.get('status') == 'success':
        return 'promoted', result['struct'], list(result.get('clamped', []))
    return 'rejected', _rejection_detail(result), []


def ingest_findings(plan_id: str, schema: str = FINDING_SCHEMA) -> dict[str, Any]:
    """Run one batched ingestion pass over every pending finding in the ledger.

    Promotes validated ``raw_input.{field}`` values to top-level fields and routes
    validator rejections to the ``rejected`` resolution. Returns a summary carrying
    the ``promoted`` / ``rejected`` / ``skipped`` counts, the accumulated ``clamped``
    reports, and a per-finding ``outcomes`` list.
    """
    promoted = 0
    rejected = 0
    skipped = 0
    clamped: list[str] = []
    outcomes: list[dict[str, Any]] = []

    # 1. Per-plan findings — locate each record's file by its `type`.
    for record in query_findings(plan_id, resolution='pending')['findings']:
        outcome, payload, record_clamped = _classify(record, schema)
        if outcome == 'promoted':
            if payload:
                update_jsonl(get_findings_path(plan_id, record['type']), record['hash_id'], payload)
            promoted += 1
        elif outcome == 'rejected':
            resolve_finding(plan_id, record['hash_id'], REJECTED_RESOLUTION, payload)
            rejected += 1
        else:
            skipped += 1
        clamped.extend(record_clamped)
        outcomes.append({'hash_id': record['hash_id'], 'outcome': outcome})

    # 2. Per-phase Q-Gate findings — locate each record's file by its phase.
    for phase in QGATE_PHASES:
        for record in query_qgate_findings(plan_id, phase, resolution='pending')['findings']:
            outcome, payload, record_clamped = _classify(record, schema)
            if outcome == 'promoted':
                if payload:
                    update_jsonl(get_qgate_path(plan_id, phase), record['hash_id'], payload)
                promoted += 1
            elif outcome == 'rejected':
                resolve_qgate_finding(plan_id, phase, record['hash_id'], REJECTED_RESOLUTION, payload)
                rejected += 1
            else:
                skipped += 1
            clamped.extend(record_clamped)
            outcomes.append({'hash_id': record['hash_id'], 'outcome': outcome})

    return {
        'status': 'success',
        'plan_id': plan_id,
        'schema': schema,
        'promoted': promoted,
        'rejected': rejected,
        'skipped': skipped,
        'clamped': clamped,
        'outcomes': outcomes,
    }
