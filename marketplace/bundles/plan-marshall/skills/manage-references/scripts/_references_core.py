#!/usr/bin/env python3
"""Shared utilities for manage-references scripts.

Provides path resolution, read/write operations, and TOON output formatting.
"""

from pathlib import Path
from typing import Any, TypedDict, cast

from constants import FILE_REFERENCES  # type: ignore[import-not-found]
from file_ops import get_plan_dir, read_json, write_json  # type: ignore[import-not-found]

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
    """Read references, returning an error dict if not found.

    Args:
        plan_id: Plan identifier (must already be validated).

    Returns:
        References dict on success, or an error dict
        ``{'status': 'error', 'plan_id': ..., 'error': 'file_not_found',
        'message': 'references.json not found'}`` on failure. The caller MUST
        check ``result.get('status') == 'error'`` and propagate the dict so
        the main dispatcher can emit the TOON and surface exit_code=1.

    Raises:
        ValueError: If references.json exists but its top-level JSON value
            is not a JSON object (e.g., list, string, number, boolean, null).
            This indicates file corruption rather than the expected
            file-not-found state, so it surfaces as a clear error at the
            boundary instead of triggering ``AttributeError`` downstream when
            callers invoke ``.get()`` on the parsed value.
    """
    refs = read_references(plan_id)
    if not refs:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'file_not_found',
            'message': 'references.json not found',
        }
    if not isinstance(refs, dict):
        raise ValueError(
            f"references.json for plan {plan_id!r} has invalid format: "
            f"expected a JSON object, got {type(refs).__name__}"
        )
    return refs
