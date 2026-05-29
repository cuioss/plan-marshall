#!/usr/bin/env python3
"""
Core functions for manage-status: TypedDicts, path resolution, read/write, and shared constants.
"""

import json
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from constants import DIR_ARCHIVED, DIR_PLANS, FILE_STATUS  # type: ignore[import-not-found]
from file_ops import (  # type: ignore[import-not-found]
    atomic_write_file,
    base_path,
    get_plan_dir,
    now_utc_iso,
    output_toon,
    read_json,
    write_json,
)
from input_validation import require_valid_plan_id  # type: ignore[import-not-found]  # noqa: F401 - re-exported
from plan_logging import log_entry  # type: ignore[import-not-found]  # noqa: F401 - re-exported

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
    created: str
    updated: str


# =============================================================================
# Core Functions
# =============================================================================


def get_status_path(plan_id: str) -> Path:
    """Get the status.json file path."""
    return get_plan_dir(plan_id) / FILE_STATUS


def read_status(plan_id: str) -> dict[Any, Any]:
    """Read status.json for a plan."""
    return cast(dict[Any, Any], read_json(get_status_path(plan_id)))


def write_status(plan_id: str, status: dict) -> None:
    """Write status.json for a plan."""
    status['updated'] = now_utc_iso()
    write_json(get_status_path(plan_id), status)


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


# =============================================================================
# Title-Body Publication
# =============================================================================

# Terminal phases — when ``status['current_phase']`` is one of these, the
# title-body file is deleted rather than written. "file absent → no plan-title
# to render" is the only conditional carried by the per-target reader (see
# cluster-01 ``session render-title`` operation spec).
TITLE_BODY_TERMINAL_PHASES = frozenset({'complete', 'archived'})

# Filename of the writer-side title-body artifact published into the plan
# directory on every state mutation. Platform-agnostic plaintext (no JSON,
# no OSC); the per-target reader composes ``{icon} {body}`` from this file
# plus active-command state.
TITLE_BODY_FILENAME = 'title-body.txt'

# Prefix of the special Completed terminal body. Unlike the active-phase
# ``pm:{phase}[:{short}]`` bodies, a ``pm:Completed:{short}`` body is the one
# terminal body that must survive the archive move: ``cmd_archive`` publishes
# it BEFORE ``shutil.move`` so the per-target reader can resolve it from the
# archived path after the live plan directory is gone. See
# ``ref-workflow-architecture/standards/terminal-title-architecture.md``
# (title-body lifecycle, Completed terminal body).
COMPLETED_TITLE_BODY_PREFIX = 'pm:Completed:'


def _render_title_body(status_data: dict[Any, Any]) -> str | None:
    """Render the title-body string from an in-memory status dict.

    Returns ``"pm:{phase}"`` when no ``short_description`` is present, or
    ``"pm:{phase}:{short_description}"`` when it is. Returns ``None`` when
    ``current_phase`` is terminal (``complete`` / ``archived``) — callers
    treat ``None`` as the delete-the-file signal.
    """
    current_phase = status_data.get('current_phase')
    if not current_phase or current_phase in TITLE_BODY_TERMINAL_PHASES:
        return None
    short_description = status_data.get('short_description')
    if short_description:
        return f'pm:{current_phase}:{short_description}'
    return f'pm:{current_phase}'


def _render_completed_title_body(short_description: str | None) -> str:
    """Render the special Completed terminal body.

    Returns ``"pm:Completed:{short_description}"`` when a ``short_description``
    is present, or the bare ``"pm:Completed"`` when it is absent. Unlike
    ``_render_title_body``, this never returns ``None``: the Completed body is
    a non-deletable terminal body that ``cmd_archive`` publishes before the
    archive move so the reader can resolve it from the archived path.
    """
    if short_description:
        return f'{COMPLETED_TITLE_BODY_PREFIX}{short_description}'
    return COMPLETED_TITLE_BODY_PREFIX.rstrip(':')


def _publish_title_body(plan_dir: Path, status_data: dict[Any, Any]) -> None:
    """Publish the title-body artifact for a plan.

    Recomputes ``pm:{phase}[:{short_description}]`` from the supplied
    in-memory ``status_data`` (no re-read of ``status.json``) and writes
    it atomically to ``{plan_dir}/title-body.txt``. When the plan is in a
    terminal phase (``current_phase`` in ``TITLE_BODY_TERMINAL_PHASES``),
    the file is deleted instead of written — "file absent → no plan-title
    to render" is the reader's only conditional.

    Failures are swallowed silently to preserve the existing
    terminal-title hook semantics: the next successful mutation
    self-heals, and a missing file is harmless on the read path.
    """
    title_body_path = plan_dir / TITLE_BODY_FILENAME
    rendered = _render_title_body(status_data)
    try:
        if rendered is None:
            title_body_path.unlink(missing_ok=True)
            return
        # ``atomic_write_file`` appends exactly one terminating ``\n`` when
        # the supplied content does not already end in one — pass ``rendered``
        # unterminated so the artifact ends with exactly one ``\n``.
        atomic_write_file(title_body_path, rendered)
    except OSError:
        # Silent no-op — consistent with the legacy terminal-title hook.
        return


def _publish_completed_title_body(plan_dir: Path, status_data: dict[Any, Any]) -> None:
    """Publish the non-deletable Completed terminal body for a plan.

    Writes ``pm:Completed:{short_description}`` to ``{plan_dir}/title-body.txt``
    unconditionally — unlike ``_publish_title_body``, this never deletes the
    artifact even though the plan is in a terminal phase. ``cmd_archive`` calls
    this BEFORE ``shutil.move`` so the Completed body travels into the archive
    directory with the moved plan, where the per-target reader resolves it via
    the archived-path fallback. Failures are swallowed silently, matching the
    existing terminal-title hook semantics.
    """
    title_body_path = plan_dir / TITLE_BODY_FILENAME
    rendered = _render_completed_title_body(status_data.get('short_description'))
    try:
        # ``atomic_write_file`` appends exactly one terminating ``\n`` when the
        # supplied content does not already end in one — pass ``rendered``
        # unterminated so the artifact ends with exactly one ``\n``.
        atomic_write_file(title_body_path, rendered)
    except OSError:
        # Silent no-op — consistent with the legacy terminal-title hook.
        return


def require_status(args) -> dict[Any, Any] | None:
    """Validate plan_id and read status, returning None with TOON error if missing."""
    require_valid_plan_id(args)
    status = read_status(args.plan_id)
    if not status:
        output_toon(
            {'status': 'error', 'plan_id': args.plan_id, 'error': 'file_not_found', 'message': 'status.json not found'}
        )
        return None
    return status
