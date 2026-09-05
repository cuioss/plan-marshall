#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Safety-bounded narrowing pass over a plan's ``references.domains`` set.

The domain-selection lifecycle is widen-only upstream of this verb: ``domain-detect``
unions its legs into ``references.domains`` at init, and phase-2-refine's re-merge may
only widen the set further. A domain admitted by early over-provisioning — the
``over_provisioned_resolve`` / ``over_provisioned_always_on_only`` /
``inclusion_only_resolve`` branches, which resolve without a plan-specific narrative
signal — can therefore never leave the set once the plan's real file footprint is known.

This verb is the missing narrowing leg. A domain currently in the set is DROPPABLE
exactly when all three legs of the safety bound agree:

1. no already-resolved task depends on it,
2. the ``always_on`` inclusion leg does not claim it,
3. the ``file_globs`` inclusion leg does not claim it against the supplied declared
   footprint (the stronger signal that replaces the narrative path tokens available at
   init).

Everything not droppable is retained, so narrowing is a strict subset operation that
never adds a domain. The inclusion semantics themselves are NOT restated here — the two
leg helpers are imported from :mod:`_cmd_domain_detect` so they keep exactly one home.

Read-only: it reads ``marshal.json``, ``references.json``, and the plan's task state, and
writes nothing. There is no LLM dispatch on this path.

The three outcomes stay mutually distinguishable in the return: narrowing ran and dropped
domains (``narrowed: true``, non-empty ``dropped``); narrowing ran and found nothing
droppable (``narrowed: false``, empty ``dropped``, ``status: success``); and narrowing
could not evaluate (``status: error`` carrying the reason). A verb that could not look
never renders as a verb that looked and found nothing.
"""

from __future__ import annotations

import json
from typing import Any

from _cmd_domain_detect import _always_on_domains, _glob_matched_domains
from _config_core import load_config
from file_ops import get_plan_dir

LEG_TASK = 'task'
LEG_ALWAYS_ON = 'always_on'
LEG_FILE_GLOBS = 'file_globs'


def _read_domains(plan_dir) -> list[str] | None:
    """Return ``references.domains`` for the plan, or ``None`` when unreadable.

    ``None`` is the could-not-look signal — an absent or malformed
    ``references.json`` carries no domain set to narrow, which is distinct from a
    readable file recording an empty one.
    """
    path = plan_dir / 'references.json'
    try:
        refs = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(refs, dict):
        return None
    domains = refs.get('domains')
    if not isinstance(domains, list):
        return None
    return [d for d in domains if isinstance(d, str) and d]


def _task_claimed_domains(plan_dir) -> set[str]:
    """Return the domains the plan's already-resolved tasks depend on.

    A task file records the domain its skill set was resolved against, so a domain
    named by any ``TASK-*.json`` is load-bearing for work already planned and is never
    droppable. At the end-of-outline narrowing site no task file exists yet, so this leg
    is vacuously empty there — which is what makes that site the safest one to narrow at.
    """
    claimed: set[str] = set()
    for task_file in sorted(plan_dir.glob('TASK-*.json')):
        try:
            task = json.loads(task_file.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        domain = task.get('domain') if isinstance(task, dict) else None
        if isinstance(domain, str) and domain:
            claimed.add(domain)
    return claimed


def _compose_report(current: list[str], retained: list[str], dropped: list[str]) -> str:
    """Compose the single-line user-facing summary.

    Emitted for BOTH outcomes: a run that found nothing droppable still reports, so
    "nothing to narrow" stays distinguishable from "narrowing never ran".
    """
    head = f'domain-narrow: {len(current)} domain(s) -> {len(retained)} retained'
    if dropped:
        return f'{head}; dropped {", ".join(dropped)}'
    return f'{head}; nothing droppable'


def cmd_domain_narrow(args) -> dict[str, Any]:
    """Narrow a plan's domain set to the domains its declared footprint justifies.

    Returns the contract ``{retained, dropped, provenance, report, narrowed}`` on
    success. ``provenance`` carries exactly one entry per domain in the PRE-narrowing
    set — ``{domain, claimed_by}`` — where an empty ``claimed_by`` records that no leg
    claimed the domain, which is why it was dropped.
    """
    plan_id: str = args.plan_id
    affected_files_raw: str = args.affected_files

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'message': f'Plan directory not found: {plan_dir}',
        }

    current = _read_domains(plan_dir)
    if current is None:
        return {
            'status': 'error',
            'error': 'domains_unreadable',
            'message': (
                f'references.json for plan {plan_id} carries no readable domains list, '
                'so there was no set to narrow'
            ),
        }

    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as exc:
        return {
            'status': 'error',
            'error': 'marshal_not_readable',
            'message': f'Could not load marshal.json, so no inclusion leg could be evaluated: {exc}',
        }

    skill_domains = config.get('skill_domains', {}) if isinstance(config, dict) else {}
    if not isinstance(skill_domains, dict) or not skill_domains:
        return {
            'status': 'error',
            'error': 'no_skill_domains_configured',
            'message': 'marshal.json configures no skill_domains, so no inclusion leg could be evaluated',
        }

    # The synthetic ``system`` domain is not an implementation domain — the same
    # filter the detector applies before evaluating its legs.
    user_domains = {k: v for k, v in skill_domains.items() if k != 'system'}
    footprint = {p.strip() for p in affected_files_raw.split(',') if p.strip()}

    always_on_set = _always_on_domains(user_domains)
    glob_matched_set = _glob_matched_domains(user_domains, footprint)
    task_claimed = _task_claimed_domains(plan_dir)

    retained: list[str] = []
    dropped: list[str] = []
    provenance: list[dict[str, Any]] = []
    for domain in sorted(set(current)):
        claimed_by = [
            leg
            for leg, claimants in (
                (LEG_TASK, task_claimed),
                (LEG_ALWAYS_ON, always_on_set),
                (LEG_FILE_GLOBS, glob_matched_set),
            )
            if domain in claimants
        ]
        provenance.append({'domain': domain, 'claimed_by': claimed_by})
        (retained if claimed_by else dropped).append(domain)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'retained': retained,
        'dropped': dropped,
        'provenance': provenance,
        'report': _compose_report(sorted(set(current)), retained, dropped),
        'narrowed': bool(dropped),
    }
