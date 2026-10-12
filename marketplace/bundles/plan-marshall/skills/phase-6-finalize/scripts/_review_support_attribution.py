#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Attribution and domain set for ``review_support`` — internal module, not an entry point.

* :func:`compute_attribution` — per outline deliverable, its declared write set
  plus the files the change ledger attributes to it; the realized-footprint
  files no deliverable owns (the unrequested-change candidates); and, with a
  delta step, only the deliverables a delta round covers.
* :func:`compute_domains` — the plan's declared domains united with every
  configured skill domain whose ``file_globs`` match the realized footprint.

Both read the realized footprint through the one derivation
``manage-references compute-footprint`` uses, so no path is ever interpolated
into a command line. A footprint that could not be derived is reported as
``footprint_source: unresolved`` and the values computed from it are omitted —
never answered as an empty set.

Imported as ``from _review_support_attribution import ...`` by ``review_support.py``.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from _cmd_domain_detect import _glob_matched_domains
from _config_core import load_config
from _ledger_core import KIND_CHANGE, read_entries
from _plan_parsing import (
    deliverable_write_set,
    extract_deliverables,
    normalize_declared_path,
    parse_document_sections,
    split_deliverable_blocks,
)
from _references_core import compute_plan_branch_diff, read_references, resolve_base_ref, resolve_live_worktree
from _review_support_validate import deliverable_number
from file_ops import get_plan_dir
from verdict_currency import OUTCOME_COMPUTED, changed_paths_for_step

SOLUTION_FILE = 'solution_outline.md'

# Attribution sources and the fallback reasons a ``declared_only`` row names.
SOURCE_LEDGER = 'ledger'
SOURCE_DECLARED_ONLY = 'declared_only'
REASON_NONE = 'none'
REASON_NO_LEDGER_ROWS = 'no_ledger_rows'
REASON_COMMIT_NOT_ON_BRANCH = 'commit_not_on_branch'
REASON_DELIVERABLE_ID_ABSENT = 'deliverable_id_absent'
REASON_BRANCH_UNRESOLVED = 'branch_unresolved'

# Per-file origin inside a deliverable's code set.
ORIGIN_DECLARED = 'declared'
ORIGIN_LEDGER = 'ledger'
ORIGIN_BOTH = 'both'

ROUND_FULL = 'full'
ROUND_DELTA = 'delta'
ROUND_REASON_NO_DELTA_STEP = 'no_delta_step'

# Realized-footprint sources.
FOOTPRINT_LIVE = 'live'
FOOTPRINT_CAPTURED = 'captured'
FOOTPRINT_UNRESOLVED = 'unresolved'

PROVENANCE_DECLARED = 'declared'
PROVENANCE_FOOTPRINT = 'footprint'
PROVENANCE_BOTH = 'both'

_SUCCESS_CRITERIA_RE = re.compile(r'\*\*Success Criteria:\*\*\s*((?:- [^\n]+\n?)+)', re.IGNORECASE)


def error_payload(plan_id: str, error: str, message: str) -> dict[str, Any]:
    """Return the ``status: error`` payload every verb uses for an unreadable input."""
    return {'status': 'error', 'plan_id': plan_id, 'error': error, 'message': message}


def load_outline_deliverables(plan_id: str) -> list[dict[str, Any]] | None:
    """Return the outline deliverables, each with its ``write_set`` and ``success_criteria``.

    ``None`` when the outline does not exist — the caller reports that, it does
    not read it as an outline with no deliverables.
    """
    path = get_plan_dir(plan_id) / SOLUTION_FILE
    if not path.is_file():
        return None
    section = parse_document_sections(path.read_text(encoding='utf-8')).get('deliverables', '')
    bodies = {block['number']: block['content'] for block in split_deliverable_blocks(section)}
    deliverables = extract_deliverables(section)
    for deliverable in deliverables:
        deliverable['write_set'] = deliverable_write_set(deliverable)
        match = _SUCCESS_CRITERIA_RE.search(bodies.get(deliverable['number'], ''))
        bullets = match.group(1).splitlines() if match else []
        deliverable['success_criteria'] = [line[2:].strip() for line in bullets if line.startswith('- ')]
    return deliverables


def _references(plan_id: str) -> dict[str, Any]:
    refs = read_references(plan_id)
    return refs if isinstance(refs, dict) else {}


def realized_footprint(refs: dict[str, Any], worktree: Path) -> tuple[list[str] | None, str, str]:
    """Return ``(paths, source, base_ref)`` for the plan's realized footprint.

    The live worktree derivation is preferred (``live``); the captured
    ``references.realized_footprint`` is the fallback (``captured``). ``paths``
    is ``None`` with source ``unresolved`` when neither could be read.
    """
    base_ref = resolve_base_ref(None, refs, worktree)
    try:
        live = compute_plan_branch_diff(worktree, base_ref)
        return sorted({normalize_declared_path(p) for p in live if p}), FOOTPRINT_LIVE, base_ref
    except (subprocess.CalledProcessError, OSError):
        captured = refs.get('realized_footprint')
        if isinstance(captured, list):
            return sorted({normalize_declared_path(str(p)) for p in captured if p}), FOOTPRINT_CAPTURED, base_ref
    return None, FOOTPRINT_UNRESOLVED, base_ref


def branch_commits(worktree: Path, base_ref: str) -> set[str] | None:
    """Return the SHAs of ``git log {base_ref}..HEAD``, or ``None`` on a git failure."""
    try:
        proc = subprocess.run(
            ['git', '-C', str(worktree), 'log', '--format=%H', f'{base_ref}..HEAD'],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def _on_branch(sha: Any, commits: set[str]) -> bool:
    """A full SHA matches by equality; an abbreviated one (7+ chars) by prefix."""
    value = str(sha or '').strip()
    if not value:
        return False
    return value in commits or (len(value) >= 7 and any(commit.startswith(value) for commit in commits))


def attribute_deliverable(
    number: int, change_rows: list[dict[str, Any]], commits: set[str] | None
) -> tuple[str, str, list[str]]:
    """Return ``(attribution_source, reason, attributed_paths)`` for one deliverable.

    ``ledger`` needs at least one ``kind=change`` row for the deliverable whose
    commit is on the plan branch. Every other case is ``declared_only`` with the
    reason the ledger could not attribute: ``no_ledger_rows`` (the ledger holds
    no change row at all), ``deliverable_id_absent`` (it holds rows, none for
    this deliverable), ``commit_not_on_branch`` (its rows' commits are not on the
    branch — the normal case after a rebase rewrote the SHAs) or
    ``branch_unresolved`` (the branch's commits could not be listed).
    """
    own = [row for row in change_rows if deliverable_number(row.get('deliverable_id')) == number]
    if not own:
        reason = REASON_DELIVERABLE_ID_ABSENT if change_rows else REASON_NO_LEDGER_ROWS
        return SOURCE_DECLARED_ONLY, reason, []
    if commits is None:
        return SOURCE_DECLARED_ONLY, REASON_BRANCH_UNRESOLVED, []
    on_branch = [row for row in own if _on_branch(row.get('commit_sha'), commits)]
    if not on_branch:
        return SOURCE_DECLARED_ONLY, REASON_COMMIT_NOT_ON_BRANCH, []
    paths = {
        normalize_declared_path(str(path))
        for row in on_branch
        for path in (row.get('changed_paths') or [])
        if str(path).strip()
    }
    return SOURCE_LEDGER, REASON_NONE, sorted(paths)


def _round(plan_id: str, delta_step: str | None, worktree: Path) -> tuple[dict[str, Any], set[str] | None]:
    """Return the round fields and, for a delta round, the changed paths it covers.

    A delta round needs a computed tree difference since the step's recorded
    completion (``verdict_currency changed-paths``). ``first_firing``,
    ``last_firing_not_done`` and ``diff_unavailable`` all fall back to a full
    round — no anchored verdict means nothing to narrow. An unreadable status is
    returned as an error payload.
    """
    if not delta_step:
        return {'round_kind': ROUND_FULL, 'round_reason': ROUND_REASON_NO_DELTA_STEP}, None
    currency = changed_paths_for_step(plan_id, delta_step, str(worktree))
    if currency.get('status') != 'success':
        return error_payload(plan_id, str(currency.get('error')), str(currency.get('message', ''))), None
    outcome = str(currency.get('outcome'))
    if outcome != OUTCOME_COMPUTED:
        return {'round_kind': ROUND_FULL, 'round_reason': outcome}, None
    changed = {normalize_declared_path(str(path)) for path in currency.get('changed_paths', [])}
    return {'round_kind': ROUND_DELTA, 'round_reason': outcome, 'changed_paths': sorted(changed)}, changed


def compute_attribution(plan_id: str, delta_step: str | None) -> dict[str, Any]:
    """Assemble the ``attribution`` payload.

    A delta round keeps only the deliverables whose code set (declared write
    set ∪ attributed files) intersects the changed paths, and narrows the
    unrequested candidates to the changed paths too.
    """
    deliverables = load_outline_deliverables(plan_id)
    if deliverables is None:
        return error_payload(plan_id, 'outline_not_found', f'{SOLUTION_FILE} not found for plan {plan_id!r}')
    refs = _references(plan_id)
    worktree = resolve_live_worktree(plan_id) or Path.cwd()
    round_fields, changed = _round(plan_id, delta_step, worktree)
    if round_fields.get('status') == 'error':
        return round_fields
    footprint, footprint_source, base_ref = realized_footprint(refs, worktree)
    commits = branch_commits(worktree, base_ref)
    change_rows = [row for row in read_entries() if row.get('kind') == KIND_CHANGE]

    rows: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    owned: set[str] = set()
    for deliverable in deliverables:
        number = deliverable['number']
        source, reason, attributed = attribute_deliverable(number, change_rows, commits)
        declared = set(deliverable['write_set'])
        code_set = declared | set(attributed)
        owned |= code_set
        if changed is not None and not code_set & changed:
            continue
        rows.append(
            {
                'number': number,
                'title': deliverable['title'],
                'attribution_source': source,
                'reason': reason,
                'declared_count': len(declared),
                'attributed_count': len(attributed),
            }
        )
        for path in sorted(code_set):
            if path in declared:
                origin = ORIGIN_BOTH if path in attributed else ORIGIN_DECLARED
            else:
                origin = ORIGIN_LEDGER
            files.append({'deliverable': number, 'path': path, 'origin': origin})

    payload: dict[str, Any] = {'status': 'success', 'plan_id': plan_id, 'base_ref': base_ref, **round_fields}
    payload['deliverable_count'] = len(rows)
    payload['deliverables'] = rows
    payload['files'] = files
    payload['footprint_source'] = footprint_source
    if footprint is not None:
        payload['unrequested_candidates'] = [
            path for path in footprint if path not in owned and (changed is None or path in changed)
        ]
    return payload


def compute_domains(plan_id: str) -> dict[str, Any]:
    """Assemble the ``domains`` payload: declared ∪ footprint-matched, each with provenance.

    The footprint leg is the same ``file_globs`` match ``manage-config``'s domain
    detector applies (``_glob_matched_domains``); the synthetic ``system`` domain
    is excluded as it is there.
    """
    if not get_plan_dir(plan_id).is_dir():
        return error_payload(plan_id, 'plan_not_found', f'no plan directory for {plan_id!r}')
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as exc:
        return error_payload(plan_id, 'marshal_unreadable', f'marshal.json could not be read ({exc})')
    skill_domains = config.get('skill_domains') if isinstance(config, dict) else None
    configured = {k: v for k, v in skill_domains.items() if k != 'system'} if isinstance(skill_domains, dict) else {}

    refs = _references(plan_id)
    declared = {str(domain).strip() for domain in refs.get('domains') or [] if str(domain).strip()}
    worktree = resolve_live_worktree(plan_id) or Path.cwd()
    footprint, footprint_source, _ = realized_footprint(refs, worktree)
    matched = _glob_matched_domains(configured, set(footprint)) if footprint else set()

    rows = []
    for domain in sorted(declared | matched):
        if domain in declared:
            provenance = PROVENANCE_BOTH if domain in matched else PROVENANCE_DECLARED
        else:
            provenance = PROVENANCE_FOOTPRINT
        rows.append({'domain': domain, 'provenance': provenance})
    return {
        'status': 'success',
        'plan_id': plan_id,
        'footprint_source': footprint_source,
        'domain_count': len(rows),
        'domains': rows,
    }


__all__ = [
    'FOOTPRINT_CAPTURED',
    'FOOTPRINT_LIVE',
    'FOOTPRINT_UNRESOLVED',
    'ORIGIN_BOTH',
    'ORIGIN_DECLARED',
    'ORIGIN_LEDGER',
    'PROVENANCE_BOTH',
    'PROVENANCE_DECLARED',
    'PROVENANCE_FOOTPRINT',
    'REASON_BRANCH_UNRESOLVED',
    'REASON_COMMIT_NOT_ON_BRANCH',
    'REASON_DELIVERABLE_ID_ABSENT',
    'REASON_NONE',
    'REASON_NO_LEDGER_ROWS',
    'ROUND_DELTA',
    'ROUND_FULL',
    'ROUND_REASON_NO_DELTA_STEP',
    'SOLUTION_FILE',
    'SOURCE_DECLARED_ONLY',
    'SOURCE_LEDGER',
    'attribute_deliverable',
    'branch_commits',
    'compute_attribution',
    'compute_domains',
    'error_payload',
    'load_outline_deliverables',
    'realized_footprint',
]
