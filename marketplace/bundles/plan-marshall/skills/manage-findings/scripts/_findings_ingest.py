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

``ingest`` is a WRITE surface — it calls ``update_jsonl`` to promote fields and
``resolve_finding`` / ``resolve_qgate_finding`` to reject — so it carries the
same explicit store guard as the ``add_`` surfaces and refuses an unreached store
through the shared ``unresolved_store_error`` rather than reporting a pass over
records it never read.

Stdlib-only — no external dependencies (except shared modules via PYTHONPATH).
"""

from typing import Any

from _findings_core import (
    _store_findings_path,
    _store_qgate_path,
    query_findings,
    query_qgate_findings,
    resolve_finding,
    resolve_qgate_finding,
)
from _findings_store_state import (
    resolve_findings_store,
    store_state_fields,
    store_unreached,
    unresolved_store_error,
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


def _classify(record: dict[str, Any], schema: str) -> tuple[str, Any, list[str], list[dict[str, Any]]]:
    """Classify one finding's ``raw_input`` — a pure query, no side effects.

    Returns ``(outcome, payload, clamped, clamps)`` where:
      * ``skipped``  → ``payload`` is ``None`` (the finding carries no ``raw_input``);
      * ``promoted`` → ``payload`` is the validated+clamped fields dict to write to
        the record's top level;
      * ``rejected`` → ``payload`` is the ``resolution_detail`` string.
    ``clamped`` is the validator's human-readable report and ``clamps`` its structured
    twin, which is what lets the record state its own cut rather than only the pass
    summary doing so. The side-effecting writeback / resolution is performed by the
    caller so this function stays a pure classifier (command-query separation).
    """
    raw = record.get('raw_input')
    if not raw:
        return 'skipped', None, [], []

    result = validate_candidate(schema, raw)
    if result.get('status') == 'success':
        return (
            'promoted',
            result['struct'],
            list(result.get('clamped', [])),
            list(result.get('clamps', [])),
        )
    return 'rejected', _rejection_detail(result), [], []


def _truncation_fields(clamps: list[dict[str, Any]]) -> dict[str, Any]:
    """The TRUSTED truncation facts a finding carries when one of its fields was cut.

    Computed by the producer from the validator's structured report, never parsed out
    of a human-readable message: ``truncated`` says the record was cut,
    ``original_length`` states the pre-clamp length, and ``truncated_fields`` maps each
    cut field to its own original length. A finding whose fields all fit carries none
    of these keys, so "no flag" stays distinguishable from "flag computed as false".
    """
    if not clamps:
        return {}
    per_field = {str(clamp.get('field') or ''): int(clamp.get('original_length') or 0) for clamp in clamps}
    return {
        'truncated': True,
        'original_length': max(per_field.values(), default=0),
        'truncated_fields': per_field,
    }


#: The keys :func:`_truncation_fields` writes. Named once, because a later promotion
#: has to know whether an EXISTING record carries them.
_TRUNCATION_KEYS: tuple[str, ...] = ('truncated', 'original_length', 'truncated_fields')


def _promotion_payload(
    payload: dict[str, Any], clamps: list[dict[str, Any]], existing: dict[str, Any]
) -> dict[str, Any]:
    """The top-level fields this pass writes, including the truncation facts.

    ``update_jsonl`` MERGES, it never deletes, so a record cut by an earlier pass keeps
    its flags even when the current ``raw_input`` fits. The record's per-field map is
    therefore REBUILT on every promotion from three sources:

    - a field this pass CUT gets this pass's original length;
    - a field this pass REPLACED without cutting loses its entry (it now fits);
    - a field this pass did not mention at all keeps its earlier entry — it still holds
      the cut text.

    That holds whether or not this pass cut anything, so a pass that cuts ``summary``
    while leaving an earlier cut ``body`` in place reports both. A record that has never
    been cut and cuts nothing receives none of the keys.
    """
    existing_fields = existing.get('truncated_fields')
    carried = (
        {str(field): int(length or 0) for field, length in existing_fields.items() if field not in payload}
        if isinstance(existing_fields, dict)
        else {}
    )
    merged = {**carried, **{str(clamp['field']): int(clamp['original_length']) for clamp in clamps}}
    promoted = {**payload, **_truncation_fields(clamps)}
    if merged:
        promoted.update(
            {
                'truncated': True,
                'original_length': max(merged.values()),
                'truncated_fields': merged,
            }
        )
    elif any(key in existing for key in _TRUNCATION_KEYS):
        # The record carried cut facts and none survive: state the cleared result
        # rather than leaving the previous claim behind.
        promoted.update({'truncated': False, 'original_length': 0, 'truncated_fields': {}})
    return promoted


def ingest_findings(plan_id: str, schema: str = FINDING_SCHEMA) -> dict[str, Any]:
    """Run one batched ingestion pass over every pending finding in the ledger.

    Promotes validated ``raw_input.{field}`` values to top-level fields and routes
    validator rejections to the ``rejected`` resolution. Returns a summary carrying
    the ``promoted`` / ``rejected`` / ``skipped`` counts, the accumulated ``clamped``
    reports, and a per-finding ``outcomes`` list — plus the four store-state fields
    every other surface publishes, so the counts are never reported without the
    substrate they were computed from.

    REFUSES an unreached store, exactly as the ``add_`` surfaces do and for a
    stronger reason: this pass both READS and WRITES. Against a ``plan_absent`` /
    ``unknown`` store the counts would be a three-way zero for records that were
    never looked at, and the writes would address a store the read never reached.
    """
    store = resolve_findings_store(plan_id)
    if store_unreached(store):
        return unresolved_store_error(plan_id, store)

    promoted = 0
    rejected = 0
    skipped = 0
    clamped: list[str] = []
    outcomes: list[dict[str, Any]] = []

    # 1. Per-plan findings — locate each record's file by its `type`.
    for record in query_findings(plan_id, resolution='pending')['findings']:
        outcome, payload, record_clamped, record_clamps = _classify(record, schema)
        if outcome == 'promoted':
            promoted_payload = _promotion_payload(payload, record_clamps, record)
            if promoted_payload:
                update_jsonl(_store_findings_path(store, record['type']), record['hash_id'], promoted_payload)
            promoted += 1
        elif outcome == 'rejected':
            resolve_finding(plan_id, record['hash_id'], REJECTED_RESOLUTION, payload)
            rejected += 1
        else:
            skipped += 1
        clamped.extend(f'{record["hash_id"]}: {entry}' for entry in record_clamped)
        outcomes.append({'hash_id': record['hash_id'], 'outcome': outcome})

    # 2. Per-phase Q-Gate findings — locate each record's file by its phase.
    for phase in QGATE_PHASES:
        for record in query_qgate_findings(plan_id, phase, resolution='pending')['findings']:
            outcome, payload, record_clamped, record_clamps = _classify(record, schema)
            if outcome == 'promoted':
                promoted_payload = _promotion_payload(payload, record_clamps, record)
                if promoted_payload:
                    update_jsonl(_store_qgate_path(store, phase), record['hash_id'], promoted_payload)
                promoted += 1
            elif outcome == 'rejected':
                resolve_qgate_finding(plan_id, phase, record['hash_id'], REJECTED_RESOLUTION, payload)
                rejected += 1
            else:
                skipped += 1
            clamped.extend(f'{record["hash_id"]}: {entry}' for entry in record_clamped)
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
        **store_state_fields(store),
    }
