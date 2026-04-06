#!/usr/bin/env python3
"""
Core functions for manage-status: TypedDicts, path resolution, read/write, and shared constants.
"""

import json
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from constants import DIR_ARCHIVED, DIR_PLANS, FILE_STATUS  # type: ignore[import-not-found]
from file_ops import (  # type: ignore[import-not-found]
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
