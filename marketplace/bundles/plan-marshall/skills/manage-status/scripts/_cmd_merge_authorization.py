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

``grant`` writes ``merge_authorizations[kind] = {head, gap_class, granted_over,
reason, granted_at}``. A re-grant at a new HEAD OVERWRITES the record — that
overwrite IS the sanctioned re-seek, so there is no separate revoke verb.
``granted_over`` records WHAT the authorization was granted over as free prose
(the barrier renders it from its own verdict: the pending count and the
``unproven_bots`` list), so a later reader can re-evaluate the ruling against a
later delta. ``gap_class`` is the machine token for the SAME question — which
gate's gap the ruling covers — and it is what routing reads, because prose is not
comparable.

HEAD-binding alone is NOT sufficient, and this module deliberately reports two
different facts rather than one. Several authorization kinds are granted at sites
that run BEFORE the pre-merge review barrier, at the SAME HEAD, over a DIFFERENT
gap — ``pre-merge-consent`` most of all, which the Pre-Merge Confirmation Gate
grants on every interactive "Yes, merge" moments before the barrier fires. A
consumer routing on HEAD-validity alone would therefore find a valid record on
every ordinary merge and skip its own disposition universally, which is the same
fail-open shape the HEAD binding exists to remove. Hence:

- ``valid``/``lapsed`` — is this record still bound to the tree in hand;
- ``admissible`` — is it ``valid`` AND was it granted over the gap class the
  CALLER is reporting (``record.gap_class == --gap-class``).

``check`` takes NO ``--kind`` flag. The caller's question is "is there an
admissible authorization for the gap I am reporting", so the verb returns EVERY
record with both verdicts plus the aggregate lists — ``authorized_kinds``,
``lapsed_kinds``, ``admissible_kinds``, ``inadmissible_kinds``, ``any_authorized``
and ``any_admissible``. Admissibility narrows the ROUTING without narrowing the
REPORT: a valid-but-wrong-gap record still appears in ``authorized_kinds`` and in
``inadmissible_kinds``, and a lapsed sibling still appears in ``lapsed_kinds``, so
no filter can hide one. An empty store returns both aggregates false with empty
lists — fail-closed, and ``absent`` is never collapsed into ``valid``. A record
carrying no ``gap_class`` at all is never admissible for any class. A single-kind
filter is refused by construction: it would let one valid authorization mask a
lapsed sibling.

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
    gap_class = args.gap_class
    if not kind or not head or not gap_class:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_argument',
            'message': '--kind, --head and --gap-class are required and must be non-empty',
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
        'gap_class': gap_class,
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
        'gap_class': gap_class,
        'granted_over': record['granted_over'],
        'reason': record['reason'],
        'granted_at': record['granted_at'],
    }
    if previous_head is not None:
        result['previous_head'] = previous_head
    return result


def cmd_merge_authorization_check(args: argparse.Namespace) -> dict | None:
    """Return each record's HEAD verdict and its admissibility for the caller's gap."""
    status = require_status(args)
    if status is None:
        return None

    head = args.head
    gap_class = args.gap_class
    if not head or not gap_class:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_argument',
            'message': '--head and --gap-class are required and must be non-empty',
        }

    metadata = status.get('metadata') or {}
    stored = metadata.get('merge_authorizations')
    authorizations: dict[str, Any] = stored if isinstance(stored, dict) else {}

    authorized_kinds: list[str] = []
    lapsed_kinds: list[str] = []
    admissible_kinds: list[str] = []
    inadmissible_kinds: list[str] = []
    records: list[dict[str, Any]] = []
    for kind in sorted(authorizations):
        entry = authorizations[kind]
        # Fail-closed: only a well-formed record whose head equals the supplied
        # HEAD is `valid`. Every other shape — a malformed entry, a record from a
        # superseded HEAD — resolves to `lapsed`. There is no catch-all branch
        # admitting to the authorized set.
        granted_head = entry.get('head') if isinstance(entry, dict) else None
        granted_class = entry.get('gap_class') if isinstance(entry, dict) else None
        verdict = VERDICT_VALID if granted_head == head else VERDICT_LAPSED
        # Admissibility narrows the ROUTING, never the REPORT. A `valid` record
        # granted over a DIFFERENT gap stays in `authorized_kinds` (it really is
        # bound to this tree) and is additionally reported as inadmissible, so a
        # caller can name it when explaining the refusal. A record carrying no
        # `gap_class` matches no class — fail-closed, never a wildcard.
        admissible = verdict == VERDICT_VALID and bool(granted_class) and granted_class == gap_class
        if verdict == VERDICT_VALID:
            authorized_kinds.append(kind)
            (admissible_kinds if admissible else inadmissible_kinds).append(kind)
        else:
            lapsed_kinds.append(kind)
        records.append(
            {
                'kind': kind,
                'head': granted_head,
                'verdict': verdict,
                'gap_class': granted_class,
                'admissible': admissible,
                'granted_over': entry.get('granted_over') if isinstance(entry, dict) else None,
                'reason': entry.get('reason') if isinstance(entry, dict) else None,
                'granted_at': entry.get('granted_at') if isinstance(entry, dict) else None,
            }
        )

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'head': head,
        'gap_class': gap_class,
        'any_authorized': bool(authorized_kinds),
        'any_admissible': bool(admissible_kinds),
        'authorized_kinds': authorized_kinds,
        'lapsed_kinds': lapsed_kinds,
        'admissible_kinds': admissible_kinds,
        'inadmissible_kinds': inadmissible_kinds,
        'records': records,
    }
