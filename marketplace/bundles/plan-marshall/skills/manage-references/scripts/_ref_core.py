#!/usr/bin/env python3
"""Shared utilities for manage-references scripts.

Provides path resolution, read/write operations, TOON output formatting,
and plan_id validation helpers.
"""

import json
import sys
from pathlib import Path
from typing import Any, TypedDict, cast

from file_ops import atomic_write_file, base_path, output_toon  # type: ignore[import-not-found]
from input_validation import is_valid_plan_id  # type: ignore[import-not-found]

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
    return cast(Path, base_path('plans', plan_id, 'references.json'))


def read_references(plan_id: str) -> dict[Any, Any]:
    """Read references.json for a plan."""
    path = get_references_path(plan_id)
    if not path.exists():
        return {}
    return cast(dict[Any, Any], json.loads(path.read_text(encoding='utf-8')))


def write_references(plan_id: str, refs: dict) -> None:
    """Write references.json for a plan."""
    path = get_references_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(refs, indent=2)
    atomic_write_file(path, content)


# =============================================================================
# Validation Helpers
# =============================================================================


def validate_plan_id(plan_id: str) -> bool:
    """Validate plan_id and output error if invalid.

    Returns:
        True if valid, False if invalid (error already printed).
    """
    if not is_valid_plan_id(plan_id):
        output_toon(
            {
                'status': 'error',
                'plan_id': plan_id,
                'error': 'invalid_plan_id',
                'message': f'Invalid plan_id format: {plan_id}',
            }
        )
        return False
    return True


def require_references(plan_id: str) -> dict[Any, Any]:
    """Read references, raising SystemExit with error if not found.

    Args:
        plan_id: Plan identifier (must already be validated).

    Returns:
        References dict.

    Raises:
        SystemExit: If references.json not found (error already printed).
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
        sys.exit(1)
    return refs
