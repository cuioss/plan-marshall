#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Core functions for manage-status: TypedDicts, path resolution, read/write, and shared constants.
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from constants import DIR_ARCHIVED, DIR_PLANS, FILE_STATUS
from file_ops import (
    base_path,
    get_executor_path,
    get_plan_dir,
    now_utc_iso,
    output_toon,
    read_json,
    write_json,
)
from input_validation import require_valid_plan_id  # noqa: F401 - re-exported
from plan_logging import log_entry  # noqa: F401 - re-exported

logger = logging.getLogger(__name__)

# =============================================================================
# TypedDict Definitions
# =============================================================================


class PhaseData(TypedDict):
    """Type definition for phase data."""

    name: str
    status: str  # pending | in_progress | done


class StatusData(TypedDict):
    """Type definition for status data structure."""

    title: str
    current_phase: str
    phases: list[PhaseData]
    metadata: NotRequired[dict[str, Any]]
    title_token: NotRequired[str]
    created: str
    updated: str


# Valid title-token states — the two lock-coordination states (lock-waiting /
# lock-owned) plus the orchestration-busy state (build-busy). The token is a
# field-only marker written into status.json by the ``title-token set`` verb;
# manage-status performs NO rendering. The composition (glyph vocabulary +
# ``{icon} {body}`` assembly) lives in ``manage-terminal-title`` — manage-status
# only persists the bare state string so the per-target renderer can read it.
# build-busy is written/cleared by the orchestration layer (not the lock
# machinery) to surface a 🔨 build symbol for the duration of a long-running
# orchestration Bash call; manage-terminal-title renders it as a token-keyed
# icon-slot override, not a glyph.
TITLE_TOKEN_STATES = frozenset({'lock-waiting', 'lock-owned', 'build-busy'})


# =============================================================================
# Core Functions
# =============================================================================


def get_status_path(plan_id: str) -> Path:
    """Get the status.json file path."""
    return get_plan_dir(plan_id) / FILE_STATUS


def read_status(plan_id: str) -> dict[Any, Any]:
    """Read status.json for a plan."""
    return cast(dict[Any, Any], read_json(get_status_path(plan_id)))


def write_status(plan_id: str, status: dict[Any, Any]) -> None:
    """Write status.json for a plan."""
    status['updated'] = now_utc_iso()
    write_json(get_status_path(plan_id), status)


# =============================================================================
# Persisted-title-state-write drive seam (best-effort, executor channel)
# =============================================================================
#
# manage-status is the STATE layer: it writes status.json and composes/emits
# NOTHING itself. On every persisted ``current_phase`` write the state layer
# fires two best-effort, fire-and-forget delegations to ``platform-runtime`` —
# a bind (session→plan, last-driven-wins; Defect 2) and a repaint (icon-optional
# title push; Defect 1) — exactly mirroring how ``manage-locks/merge_lock.py``
# delegates its title-token surface. Both are invoked through the executor as a
# subprocess (the established merge_lock channel, not a fragile file-path import
# across the multi-module platform-runtime layout) and fully swallow every
# failure, so a delegation error NEVER alters the status-write outcome or exit
# code. The single shared ``_surface_drive`` helper is the ONE home both phase
# writers (``cmd_create`` / ``cmd_transition`` / ``cmd_set_phase``) share.

_PLATFORM_RUNTIME_NOTATION = 'plan-marshall:platform-runtime:platform_runtime'


def _run_executor(notation: str, *cli_args: str) -> None:
    """Best-effort: invoke ``{notation}`` through the executor as a subprocess.

    Fire-and-forget — any failure (executor missing, non-zero exit, OSError) is
    swallowed at DEBUG. The drive seam is a display affordance and MUST NOT
    change the status-write outcome. Mirrors ``merge_lock._run_executor``'s
    best-effort contract (the established D6 executor channel).

    The executor is resolved and existence-checked BEFORE the spawn: when the
    plan root is unresolvable or no ``execute-script.py`` is on disk (an
    isolated test fixture, a pre-bootstrap window), there is nothing to delegate
    to, so the call returns without launching a subprocess. Skipping the spawn
    keeps the seam a true no-op wherever the executor is absent instead of
    launching a Python process that would only fail to find the script.
    """
    try:
        executor = get_executor_path()
    except RuntimeError as exc:
        logger.debug('drive-seam %s skipped (no plan root): %s', notation, exc)
        return
    if not executor.is_file():
        logger.debug('drive-seam %s skipped (executor absent at %s)', notation, executor)
        return
    cmd = [sys.executable, str(executor), notation, *cli_args]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        logger.debug('drive-seam %s failed: %s', notation, exc)


def _drive_bind(plan_id: str) -> None:
    """Best-effort ``session bind --plan-id {id}`` (last-driven-wins; Defect 2)."""
    _run_executor(_PLATFORM_RUNTIME_NOTATION, 'session', 'bind', '--plan-id', plan_id)


def _drive_repaint(plan_id: str) -> None:
    """Best-effort ``session push-title-token --plan-id {id}`` (no icon; Defect 1).

    The push runs with no ``--icon`` — a plain repaint of the freshly composed
    title with the default active icon, so the title bar reflects the new phase
    immediately instead of freezing at the last-rendered phase.
    """
    _run_executor(_PLATFORM_RUNTIME_NOTATION, 'session', 'push-title-token', '--plan-id', plan_id)


def _surface_drive(plan_id: str) -> None:
    """Best-effort: fire one bind + one repaint after a persisted phase-state write.

    Called immediately AFTER ``write_status`` by the three ``current_phase``
    writers (``cmd_create`` seed / ``cmd_transition`` advance / ``cmd_set_phase``).
    The single shared home so both call sites share it rather than a per-caller
    convention. Fully exception-swallowing: a subprocess/delegation failure never
    changes the command's status or exit code.
    """
    try:
        _drive_bind(plan_id)
        _drive_repaint(plan_id)
    except Exception as exc:  # noqa: BLE001 — drive seam is best-effort
        logger.debug('drive-seam surface for %s failed: %s', plan_id, exc)


# Phase routing maps phase names to skills (for route command).
# Note: This is a fallback mapping. The authoritative source is
# manage-config's skill_domains.system.workflow_skills in marshal.json.
# When marshal.json is initialized, resolve-workflow-skill should be
# preferred over this static mapping.
PHASE_ROUTING = {
    '1-init': ('plan-init', 'Initialize plan structure'),
    '2-refine': ('request-refine', 'Clarify request until confident'),
    '3-outline': ('solution-outline', 'Create solution outline with deliverables'),
    '4-plan': ('task-plan', 'Create tasks from deliverables'),
    '5-execute': ('plan-execute', 'Execute implementation tasks'),
    '6-finalize': ('plan-finalize', 'Finalize with commit/PR'),
}


def get_plans_dir() -> Path:
    """Get the plans directory."""
    return cast(Path, base_path(DIR_PLANS))


def get_archive_dir() -> Path:
    """Get the archived plans directory."""
    return cast(Path, base_path(DIR_ARCHIVED))


def _try_read_status_json(plan_dir: Path) -> dict[Any, Any] | None:
    """Try to read status.json from a plan directory."""
    status_file = plan_dir / FILE_STATUS
    if status_file.exists():
        try:
            return cast(dict[Any, Any], json.loads(status_file.read_text(encoding='utf-8')))
        except (ValueError, OSError):
            return None
    return None


def require_status(args: argparse.Namespace) -> dict[Any, Any] | None:
    """Validate plan_id and read status, returning None with TOON error if missing."""
    require_valid_plan_id(args)
    status = read_status(args.plan_id)
    if not status:
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'file_not_found', 'message': 'status.json not found'}
        )
        return None
    return status
