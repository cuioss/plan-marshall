#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Init-time semantic sibling-dedup collision gate for phase-1-init.

Scans all active (non-archived) sibling plans and flags two collision classes
against the plan currently under init, in priority order:

1. **source-origin match** (primary) — the same audit / lesson / issue
   ``source_id`` backs more than one active plan (a same-source fan-out). The
   plan's ``(source, source_id)`` is read from its ``request.md`` header and
   compared against every active sibling's ``request.md`` header; a sibling whose
   non-empty ``source_id`` equals this plan's ``source_id`` is flagged.

2. **file-path overlap** (secondary) — concrete file paths named in this plan's
   ``request.md`` body intersect a sibling's ``references.json`` ``affected_files``.
   Path extraction is deterministic (a repo-relative path regex), and the match
   is exact normalized-string equality, so the check raises zero false positives.

The verb is read-only and deterministic — no LLM dispatch and no writes. It
returns the two match lists plus a ``collision_detected`` boolean; the
phase-1-init step consumes the result and raises the user gate (proceed / rename
/ abort) BEFORE phase-2, rather than deferring the discovery to finalize.

Active-plan enumeration mirrors ``_status_query.cmd_list``: it merges the
main-checkout plans (``get_plans_dir()``) with the worktree-resident plans a
phase-5+ plan was moved into (``get_worktree_root()/{wt}/.plan/local/plans/{id}``),
deduped by id. Archived plans live under a separate directory and are excluded by
construction.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from _plan_parsing import parse_document_sections
from _status_core import get_plans_dir
from constants import DIR_PLANS, FILE_STATUS
from file_ops import (
    get_plan_dir,
    get_worktree_root,
    read_json,
)
from marketplace_paths import PLAN_DIR_NAME

# source_id values that count as "no traceable origin" — a description-sourced
# plan has no external id, so it can never trip the source-origin check.
_NULL_SOURCE_ID_VALUES = frozenset({'', 'none'})

# Repo-relative path matcher. Requires at least one ``/`` segment boundary and a
# trailing ``.ext`` so bare words and section anchors are never mistaken for
# files. The leading negative lookbehind keeps the match anchored at a path
# start (whitespace, backtick, parenthesis, line start), never mid-token.
_PATH_RE = re.compile(
    r'(?<![\w./-])([A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)+\.[A-Za-z0-9]+)'
)

# Within-row join separator for the ``overlapping_files`` column. The TOON
# uniform-array table separator is ``,``; joining the per-row file list with
# ``;`` keeps each row a single well-formed column (paths never contain ``;``).
_OVERLAP_JOIN = ';'


def _normalize_path(raw: str) -> str:
    """Normalize a path for exact-equality comparison.

    Strips surrounding whitespace and a single leading ``./`` so a request-body
    ``./a/b.py`` and a references ``a/b.py`` compare equal.
    """
    cleaned = raw.strip()
    if cleaned.startswith('./'):
        cleaned = cleaned[2:]
    return cleaned


def _read_request_source(plan_dir: Path) -> tuple[str | None, str | None]:
    """Return ``(source, source_id)`` from a plan's ``request.md`` header.

    ``parse_document_sections`` promotes the allowlisted ``source`` /
    ``source_id`` header fields to virtual sections. A missing / unreadable
    request, or an absent field, yields ``None`` for that element. A
    ``source_id`` in ``_NULL_SOURCE_ID_VALUES`` is normalized to ``None`` so the
    caller never matches on an empty origin.
    """
    request_path = plan_dir / 'request.md'
    if not request_path.exists():
        return None, None
    try:
        content = request_path.read_text(encoding='utf-8')
    except OSError:
        return None, None

    sections = parse_document_sections(content)
    source = sections.get('source') or None
    source_id_raw = sections.get('source_id')
    source_id: str | None = None
    if isinstance(source_id_raw, str) and source_id_raw.strip().lower() not in _NULL_SOURCE_ID_VALUES:
        source_id = source_id_raw.strip()
    return source, source_id


def _read_request_body(plan_dir: Path) -> str:
    """Return the raw ``request.md`` text (empty on any read failure)."""
    request_path = plan_dir / 'request.md'
    if not request_path.exists():
        return ''
    try:
        return request_path.read_text(encoding='utf-8')
    except OSError:
        return ''


def _extract_paths(text: str) -> set[str]:
    """Extract the set of normalized repo-relative file paths named in ``text``."""
    return {_normalize_path(m.group(1)) for m in _PATH_RE.finditer(text)}


def _read_affected_files(plan_dir: Path) -> set[str]:
    """Return the normalized ``affected_files`` set from a plan's references.json."""
    references = read_json(plan_dir / 'references.json', default={})
    if not isinstance(references, dict):
        return set()
    affected = references.get('affected_files')
    if not isinstance(affected, list):
        return set()
    return {_normalize_path(p) for p in affected if isinstance(p, str) and p.strip()}


def _iter_active_plan_dirs() -> dict[str, Path]:
    """Return ``{plan_id: plan_dir}`` for every active (non-archived) plan.

    Mirrors ``_status_query.cmd_list``: main-checkout plans first, then
    worktree-resident plans (deduped — a moved-in plan appears once). Only
    directories carrying a ``status.json`` sentinel are included.
    """
    result: dict[str, Path] = {}

    plans_dir = get_plans_dir()
    if plans_dir.is_dir():
        try:
            plan_dirs = sorted(plans_dir.iterdir())
        except OSError:
            plan_dirs = []
        for plan_dir in plan_dirs:
            status_file = plan_dir / FILE_STATUS
            if plan_dir.is_dir() and status_file.is_file() and not status_file.is_symlink():
                result.setdefault(plan_dir.name, plan_dir)

    try:
        worktree_root = get_worktree_root()
    except RuntimeError:
        worktree_root = None

    if worktree_root is not None and worktree_root.is_dir():
        try:
            wt_dirs = sorted(worktree_root.iterdir())
        except OSError:
            wt_dirs = []
        for worktree_dir in wt_dirs:
            if not worktree_dir.is_dir():
                continue
            wt_plans_dir = worktree_dir / PLAN_DIR_NAME / 'local' / DIR_PLANS
            if not wt_plans_dir.is_dir():
                continue
            try:
                plan_dirs = sorted(wt_plans_dir.iterdir())
            except OSError:
                continue
            for plan_dir in plan_dirs:
                status_file = plan_dir / FILE_STATUS
                if (
                    plan_dir.is_dir()
                    and plan_dir.name not in result
                    and status_file.is_file()
                    and not status_file.is_symlink()
                ):
                    result[plan_dir.name] = plan_dir

    return result


def run_sibling_collision_check(plan_id: str) -> dict[str, Any]:
    """Run both collision checks for ``plan_id`` against every active sibling.

    Returns a dict carrying this plan's ``(source, source_id)``, the count of
    active siblings scanned, the two match lists, and ``collision_detected``.
    Read-only and deterministic — no writes, no LLM dispatch.
    """
    self_dir = get_plan_dir(plan_id)
    self_source, self_source_id = _read_request_source(self_dir)
    self_paths = _extract_paths(_read_request_body(self_dir))

    active = _iter_active_plan_dirs()
    siblings = {pid: pdir for pid, pdir in active.items() if pid != plan_id}

    source_origin_matches: list[dict[str, str]] = []
    file_overlap_matches: list[dict[str, Any]] = []

    for sibling_id in sorted(siblings):
        sibling_dir = siblings[sibling_id]

        # Check 1 (primary): source-origin fan-out.
        if self_source is not None and self_source_id is not None:
            sib_source, sib_source_id = _read_request_source(sibling_dir)
            if (
                sib_source is not None
                and sib_source == self_source
                and sib_source_id is not None
                and sib_source_id == self_source_id
            ):
                source_origin_matches.append(
                    {
                        'plan_id': sibling_id,
                        'source': sib_source or '',
                        'source_id': sib_source_id,
                    }
                )

        # Check 2 (secondary): concrete file-path overlap.
        if self_paths:
            overlap = sorted(self_paths & _read_affected_files(sibling_dir))
            if overlap:
                file_overlap_matches.append(
                    {
                        'plan_id': sibling_id,
                        'overlap_count': len(overlap),
                        'overlapping_files': _OVERLAP_JOIN.join(overlap),
                    }
                )

    collision_detected = bool(source_origin_matches or file_overlap_matches)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'source': self_source or '',
        'source_id': self_source_id or '',
        'active_sibling_count': len(siblings),
        'source_origin_matches': source_origin_matches,
        'source_origin_match_count': len(source_origin_matches),
        'file_overlap_matches': file_overlap_matches,
        'file_overlap_match_count': len(file_overlap_matches),
        'collision_detected': collision_detected,
    }


def cmd_sibling_collision(args: argparse.Namespace) -> dict[str, Any]:
    """Handle ``sibling-collision-check --plan-id PLAN_ID``.

    Returns a structured ``plan_dir_not_found`` error when the plan directory is
    absent; otherwise delegates to :func:`run_sibling_collision_check`.
    """
    plan_id: str = args.plan_id

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'plan_id': plan_id,
            'message': f'Plan directory not found: {plan_dir}',
        }

    return run_sibling_collision_check(plan_id)
