#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Safety-bounded narrowing pass over a plan's ``references.domains`` set.

The domain-selection lifecycle is widen-only upstream of this verb: ``domain-detect``
unions its legs into ``references.domains`` at init, and phase-2-refine's re-merge may
only widen the set further. A domain admitted by early over-provisioning — the
``over_provisioned_resolve`` / ``over_provisioned_always_on_only`` /
``inclusion_only_resolve`` branches, which resolve without a plan-specific narrative
signal — can therefore never leave the set once the plan's real file footprint is known.

This verb is the missing narrowing leg. A domain currently in the set — other than the
synthetic ``system`` domain, which is exempt from the bound entirely (below) — is
DROPPABLE exactly when all three legs of the safety bound agree:

1. no already-resolved task depends on it,
2. the ``always_on`` inclusion leg does not claim it,
3. the ``file_globs`` inclusion leg does not claim it against the supplied declared
   footprint (the stronger signal that replaces the narrative path tokens available at
   init).

The synthetic ``system`` domain is EXEMPT from that bound rather than judged by it. It
is not an implementation domain, so it is filtered out of the mapping both inclusion legs
are evaluated over — meaning neither leg can contain it and neither ever looks at it.
Subjecting it to the bound would therefore drop it on the strength of two legs that were
structurally incapable of claiming it, which is the opposite of the bound agreeing. It is
retained unconditionally and its provenance records ``EXEMPT_SYSTEM`` rather than an empty
``claimed_by``, so the empty-``claimed_by``-means-dropped reading below stays exact.

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

#: The synthetic ``system`` domain key. It holds the workflow-skill wiring rather
#: than implementation skills, so it is filtered out of the mapping the inclusion
#: legs are evaluated over — the same filter the detector applies.
SYSTEM_DOMAIN = 'system'

#: Provenance marker for a domain retained WITHOUT any leg evaluation.
#:
#: Deliberately NOT named ``LEG_SYSTEM``. Each ``LEG_*`` token above names an
#: inclusion leg that ran and claimed the domain; this token names the opposite —
#: the domain was exempted from leg evaluation, so no leg ever looked at it. A
#: ``LEG_`` prefix would assert a symmetry that does not hold and would let
#: ``claimed_by`` report an evaluation that never happened.
EXEMPT_SYSTEM = 'system_exempt'


class _TaskLegUnreadable(Exception):
    """A ``TASK-*.json`` could not be read, so the task leg cannot be evaluated.

    Raised rather than skipped: a skipped task file silently removes the domain it
    claims from the leg, and the run then reports ``status: success`` with that domain
    dropped and an empty ``claimed_by`` — which the return contract reads as "no leg
    claimed it". That publishes a looked-and-found-nothing verdict for a leg that never
    looked, so the only honest outcome is the could-not-evaluate error.
    """

    def __init__(self, task_file, cause: Exception) -> None:
        self.task_file = task_file
        self.cause = cause
        super().__init__(f'{task_file}: {cause}')


def _read_affected_files(plan_dir) -> list[str] | None:
    """Return ``references.affected_files`` as a list, or ``None`` when unreadable.

    This is the PRIMARY footprint source and it keeps the paths a list end to end. The
    ``--affected-files`` flag remains as an out-of-band override, but routing the normal
    path through a comma-joined string was lossy twice over: a path legitimately
    containing a comma split into two entries, and the joined string had to be
    interpolated into a documented shell command line, putting repository-controlled
    text where ``$(...)``, backticks and backslashes are live.
    """
    refs_file = plan_dir / 'references.json'
    try:
        refs = json.loads(refs_file.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(refs, dict):
        return None
    files = refs.get('affected_files')
    if not isinstance(files, list):
        return None
    return [f for f in files if isinstance(f, str) and f]


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

    An unreadable or malformed task file raises :class:`_TaskLegUnreadable` rather than
    being skipped. Skipping it would drop the domain that file claims out of the leg
    silently, and the run would then report ``status: success`` with that domain in
    ``dropped`` and an empty ``claimed_by`` — publishing "no leg claimed it" for a leg
    that could not be evaluated at all. That is the fail-open the safety bound exists to
    prevent: a guard that could not look must not read as a guard that looked and found
    nothing.
    """
    claimed: set[str] = set()
    for task_file in sorted(plan_dir.glob('TASK-*.json')):
        try:
            task = json.loads(task_file.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise _TaskLegUnreadable(task_file, exc) from exc
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

    The synthetic ``system`` domain is the one entry ``claimed_by`` does not describe a
    leg evaluation for: it is retained by exemption and carries ``[EXEMPT_SYSTEM]``. That
    marker is what keeps the empty-``claimed_by`` reading above exact — a retained domain
    never carries an empty ``claimed_by``, so an empty one always means dropped.
    """
    plan_id: str = args.plan_id
    affected_files_raw: str | None = getattr(args, 'affected_files', None)

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
    # filter the detector applies before evaluating its legs. Because it is absent
    # here, neither inclusion leg below can ever contain it, which is exactly why
    # the retention loop exempts it instead of judging it.
    user_domains = {k: v for k, v in skill_domains.items() if k != SYSTEM_DOMAIN}

    # Primary source: the persisted list, which survives a path containing a comma.
    # The flag is the out-of-band override and is parsed the lossy way only because a
    # caller who passes it has already chosen a string surface.
    if affected_files_raw is None:
        declared = _read_affected_files(plan_dir)
        if declared is None:
            return {
                'status': 'error',
                'error': 'footprint_unreadable',
                'message': (
                    f'references.json for plan {plan_id} carries no readable affected_files '
                    'list and no --affected-files override was given, so the file_globs leg '
                    'had no footprint to evaluate against'
                ),
            }
        footprint = {f.strip() for f in declared if f.strip()}
    else:
        footprint = {p.strip() for p in affected_files_raw.split(',') if p.strip()}

    if not footprint:
        return {
            'status': 'error',
            'error': 'footprint_empty',
            'message': (
                'The declared footprint resolved to zero paths, so narrowing has no evidence '
                'to act on and refuses to drop any domain'
            ),
        }

    always_on_set = _always_on_domains(user_domains)
    glob_matched_set = _glob_matched_domains(user_domains, footprint)
    try:
        task_claimed = _task_claimed_domains(plan_dir)
    except _TaskLegUnreadable as exc:
        return {
            'status': 'error',
            'error': 'task_leg_unreadable',
            'message': (
                f'Task file {exc.task_file} could not be read, so the task leg of the '
                f'safety bound could not be evaluated and no domain may be dropped on it: {exc.cause}'
            ),
        }

    unique_current = sorted(set(current))
    retained: list[str] = []
    dropped: list[str] = []
    provenance: list[dict[str, Any]] = []
    for domain in unique_current:
        if domain == SYSTEM_DOMAIN:
            # Exempt from the safety bound, not judged by it: ``system`` is absent
            # from ``user_domains``, so the always_on and file_globs legs could
            # never claim it. Recording an empty ``claimed_by`` here would publish
            # "no leg claimed it" — whose documented reading is "dropped for want
            # of a claim" — for a domain two of the three legs never considered.
            provenance.append({'domain': domain, 'claimed_by': [EXEMPT_SYSTEM]})
            retained.append(domain)
            continue
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
        'report': _compose_report(unique_current, retained, dropped),
        'narrowed': bool(dropped),
    }
