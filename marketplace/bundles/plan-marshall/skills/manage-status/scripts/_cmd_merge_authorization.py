#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
merge-authorization command handlers for manage-status.

Binds every merge-gate authorization to the HEAD it was granted against, and
refuses it once that HEAD moves. The record lives in
``status.metadata.merge_authorizations``, keyed by authorization ``kind``, beside
the ``phase_steps`` map the same skill already owns. It is deliberately NOT a
``phase_steps`` entry: those keys are the finalize step roster and feed the
``phase_steps_complete`` handshake, so a synthetic authorization step would
pollute both — and the host step ``default:branch-cleanup`` correctly declares no
``head_dependent`` fact, because it records an action performed rather than a
HEAD-dependent verdict.

``grant`` writes ``merge_authorizations[kind] = {head, granted_over, reason,
granted_at}``. A re-grant at a new HEAD OVERWRITES the record — that overwrite IS
the sanctioned re-seek, so there is no separate revoke verb. ``granted_over``
records WHAT the authorization was granted over (the barrier renders it from its
own verdict: the pending count and the ``unproven_bots`` list), so a later reader
can re-evaluate the ruling against a later delta.

``check`` takes NO ``--kind`` flag. The barrier's question is "is there a valid
authorization for the gap I am reporting", so the verb returns EVERY record with
a per-record verdict plus the two aggregate lists. Per record the verdict is
``valid`` when ``record.head == --head`` and ``lapsed`` otherwise; the reply
carries ``authorized_kinds``, ``lapsed_kinds``, and ``any_authorized``. An empty
store returns ``any_authorized: false`` with empty lists — fail-closed, and
``absent`` is never collapsed into ``valid``. A single-kind filter is refused by
construction: it would let one valid authorization mask a lapsed sibling.

Both verbs exit 0 on either verdict — the verdict travels in the TOON per the
output contract. A non-zero exit is reserved for a genuine crash.
"""

import argparse
from typing import Any

from _status_core import require_status, write_status
from file_ops import now_utc_iso

VERDICT_VALID = 'valid'
VERDICT_LAPSED = 'lapsed'


def cmd_merge_authorization_grant(args: argparse.Namespace) -> dict | None:
    """Persist a HEAD-bound merge authorization into status.metadata."""
    status = require_status(args)
    if status is None:
        return None

    kind = args.kind
    head = args.head
    if not kind or not head:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_argument',
            'message': '--kind and --head are required and must be non-empty',
        }

    metadata: dict[str, Any] = status.setdefault('metadata', {})
    authorizations = metadata.get('merge_authorizations')
    if not isinstance(authorizations, dict):
        authorizations = {}
        metadata['merge_authorizations'] = authorizations

    previous = authorizations.get(kind)
    previous_head = previous.get('head') if isinstance(previous, dict) else None

    record: dict[str, Any] = {
        'head': head,
        'granted_over': args.granted_over,
        'reason': args.reason,
        'granted_at': now_utc_iso(),
    }
    authorizations[kind] = record
    write_status(args.plan_id, status)

    result: dict[str, Any] = {
        'status': 'success',
        'plan_id': args.plan_id,
        'kind': kind,
        'head': head,
        'granted_over': record['granted_over'],
        'reason': record['reason'],
        'granted_at': record['granted_at'],
    }
    if previous_head is not None:
        result['previous_head'] = previous_head
    return result


def cmd_merge_authorization_check(args: argparse.Namespace) -> dict | None:
    """Return the authorization verdict for every record at the supplied HEAD."""
    status = require_status(args)
    if status is None:
        return None

    head = args.head
    if not head:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_argument',
            'message': '--head is required and must be non-empty',
        }

    metadata = status.get('metadata') or {}
    stored = metadata.get('merge_authorizations')
    authorizations: dict[str, Any] = stored if isinstance(stored, dict) else {}

    authorized_kinds: list[str] = []
    lapsed_kinds: list[str] = []
    records: list[dict[str, Any]] = []
    for kind in sorted(authorizations):
        entry = authorizations[kind]
        # Fail-closed: only a well-formed record whose head equals the supplied
        # HEAD is `valid`. Every other shape — a malformed entry, a record from a
        # superseded HEAD — resolves to `lapsed`. There is no catch-all branch
        # admitting to the authorized set.
        granted_head = entry.get('head') if isinstance(entry, dict) else None
        verdict = VERDICT_VALID if granted_head == head else VERDICT_LAPSED
        if verdict == VERDICT_VALID:
            authorized_kinds.append(kind)
        else:
            lapsed_kinds.append(kind)
        records.append(
            {
                'kind': kind,
                'head': granted_head,
                'verdict': verdict,
                'granted_over': entry.get('granted_over') if isinstance(entry, dict) else None,
                'reason': entry.get('reason') if isinstance(entry, dict) else None,
                'granted_at': entry.get('granted_at') if isinstance(entry, dict) else None,
            }
        )

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'head': head,
        'any_authorized': bool(authorized_kinds),
        'authorized_kinds': authorized_kinds,
        'lapsed_kinds': lapsed_kinds,
        'records': records,
    }
