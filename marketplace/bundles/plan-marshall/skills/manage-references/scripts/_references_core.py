#!/usr/bin/env python3
"""Shared utilities for manage-references scripts.

Provides path resolution, read/write operations, and TOON output formatting.
"""

from pathlib import Path
from typing import Any, TypedDict, cast

from constants import FILE_REFERENCES  # type: ignore[import-not-found]
from file_ops import get_plan_dir, output_toon, read_json, write_json  # type: ignore[import-not-found]

# =============================================================================
# Type Definitions
# =============================================================================


class ReferencesData(TypedDict, total=False):
    """Type definition for references data structure."""

    branch: str
    base_branch: str
    issue_url: str
    build_system: str
    modified_files: list[str]
    domains: list[str]
    affected_files: list[str]
    external_docs: dict[str, Any]


# =============================================================================
# File Operations
# =============================================================================


def get_references_path(plan_id: str) -> Path:
    """Get the references.json file path."""
    return get_plan_dir(plan_id) / FILE_REFERENCES


def read_references(plan_id: str) -> dict[Any, Any]:
    """Read references.json for a plan."""
    return cast(dict[Any, Any], read_json(get_references_path(plan_id)))


def write_references(plan_id: str, refs: dict) -> None:
    """Write references.json for a plan."""
    write_json(get_references_path(plan_id), refs)


def require_references(plan_id: str) -> dict[Any, Any]:
    """Read references, raising RuntimeError if not found.

    Args:
        plan_id: Plan identifier (must already be validated).

    Returns:
        References dict.

    Raises:
        RuntimeError: If references.json not found (error already printed).
    """
    refs = read_references(plan_id)
    if not refs:
        output_toon(
            {
                'status': 'error',
                'plan_id': plan_id,
                'error': 'file_not_found',
                'message': 'references.json not found',
            }
        )
        raise RuntimeError(f'references.json not found for plan {plan_id}')
    return refs
