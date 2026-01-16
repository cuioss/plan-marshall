#!/usr/bin/env python3
"""
Base file operations module for CUI workflow scripts.

Provides atomic file operations, metadata parsing, JSON output helpers,
and base directory configuration for workflow files.
Stdlib-only - no external dependencies.

Usage:
    from file_ops import (
        atomic_write_file,
        ensure_directory,
        output_success,
        output_error,
        parse_markdown_metadata,
        generate_markdown_metadata,
        get_base_dir,
        set_base_dir,
        base_path,
        get_temp_dir
    )
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# Default base directory for workflow files
# Can be overridden via PLAN_BASE_DIR environment variable for testing
_BASE_DIR = Path(os.environ.get('PLAN_BASE_DIR', '.plan'))


def get_base_dir() -> Path:
    """Get the base directory for workflow files.

    Returns:
        Path object for the workflow base directory (default: .plan)

    Note:
        Can be overridden via PLAN_BASE_DIR environment variable.
    """
    # Check env var each time to support runtime changes in tests
    env_dir = os.environ.get('PLAN_BASE_DIR')
    if env_dir:
        return Path(env_dir)
    return _BASE_DIR


def set_base_dir(path: Path | str) -> None:
    """Override the base directory for workflow files.

    Args:
        path: New base directory path

    Note:
        This is primarily for testing purposes. In production,
        the default .plan directory should be used.
    """
    global _BASE_DIR
    _BASE_DIR = Path(path)


def base_path(*parts: str) -> Path:
    """Construct a path within the workflow base directory.

    Args:
        *parts: Path components to join

    Returns:
        Full path including the workflow base directory

    Example:
        >>> base_path('plans', 'my-task', 'plan.md')
        PosixPath('.plan/plans/my-task/plan.md')
    """
    return _BASE_DIR.joinpath(*parts)


def get_temp_dir(subdir: str | None = None) -> Path:
    """Get temp directory under .plan/temp/{subdir}.

    Args:
        subdir: Optional subdirectory name within temp

    Returns:
        Path to temp directory (respects PLAN_BASE_DIR env var)

    Example:
        >>> get_temp_dir()
        PosixPath('.plan/temp')
        >>> get_temp_dir('tools-marketplace-inventory')
        PosixPath('.plan/temp/tools-marketplace-inventory')
    """
    temp_path = get_base_dir() / 'temp'
    if subdir:
        return temp_path / subdir
    return temp_path


def atomic_write_file(path: str | Path, content: str) -> None:
    """Write file atomically using temp file + rename pattern.

    Args:
        path: Target file path
        content: Content to write

    Raises:
        OSError: If write or rename fails
    """
    path = Path(path)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file first, then rename (atomic on most systems)
    fd, temp_path = tempfile.mkstemp(suffix=path.suffix, prefix='.tmp_', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
            # Ensure content ends with newline
            if content and not content.endswith('\n'):
                f.write('\n')
        os.replace(temp_path, path)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def ensure_directory(path: str | Path) -> Path:
    """Create directory and parents if needed.

    Args:
        path: File or directory path

    Returns:
        Path object for the directory

    Note:
        If path looks like a file (has extension), creates parent directory.
        Otherwise creates the directory itself.
    """
    path = Path(path)

    # If path has a file extension, assume it's a file path
    if path.suffix:
        target_dir = path.parent
    else:
        target_dir = path

    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def output_success(operation: str, **kwargs: Any) -> None:
    """Print JSON success output to stdout.

    Args:
        operation: Name of the operation
        **kwargs: Additional fields to include in output
    """
    result = {'success': True, 'operation': operation}
    result.update(kwargs)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def output_error(operation: str, error: str) -> None:
    """Print JSON error output to stderr.

    Args:
        operation: Name of the operation
        error: Error message
    """
    result = {'success': False, 'operation': operation, 'error': error}
    print(json.dumps(result, indent=2), file=sys.stderr)


def parse_markdown_metadata(content: str) -> dict[str, str]:
    """Parse key=value metadata from markdown content.

    Parses metadata at the start of markdown content that uses key=value format.
    Metadata ends at first blank line or markdown heading.

    Supports dot notation for nested keys: component.type=command

    Args:
        content: Full markdown file content

    Returns:
        Dictionary of metadata key-value pairs

    Example:
        >>> content = '''id=2025-11-28-001
        ... component.type=command
        ... applied=false
        ...
        ... # Title
        ... Content here...'''
        >>> parse_markdown_metadata(content)
        {'id': '2025-11-28-001', 'component.type': 'command', 'applied': 'false'}
    """
    metadata = {}
    lines = content.split('\n')

    for line in lines:
        line = line.strip()

        # Stop at blank line or heading
        if not line or line.startswith('#'):
            break

        # Parse key=value
        if '=' in line:
            key, value = line.split('=', 1)
            metadata[key.strip()] = value.strip()

    return metadata


def generate_markdown_metadata(data: dict[str, str]) -> str:
    """Generate key=value metadata block from dictionary.

    Args:
        data: Dictionary of metadata key-value pairs

    Returns:
        Formatted metadata block string

    Example:
        >>> data = {'id': '2025-11-28-001', 'component.type': 'command'}
        >>> print(generate_markdown_metadata(data))
        id=2025-11-28-001
        component.type=command
    """
    lines = []
    for key, value in data.items():
        lines.append(f'{key}={value}')
    return '\n'.join(lines)


def update_markdown_metadata(content: str, updates: dict[str, str]) -> str:
    """Update specific metadata fields in markdown content.

    Preserves existing metadata and content, only updating specified keys.

    Args:
        content: Full markdown file content
        updates: Dictionary of key-value pairs to update

    Returns:
        Updated content with modified metadata
    """
    lines = content.split('\n')
    metadata_end = 0
    metadata_lines = []
    found_keys = set()

    # Find metadata lines and their end position
    for i, line in enumerate(lines):
        stripped = line.strip()

        # Stop at blank line or heading
        if not stripped or stripped.startswith('#'):
            metadata_end = i
            break

        # Parse existing metadata line
        if '=' in stripped:
            key = stripped.split('=', 1)[0].strip()
            if key in updates:
                metadata_lines.append(f'{key}={updates[key]}')
                found_keys.add(key)
            else:
                metadata_lines.append(line)
        else:
            metadata_lines.append(line)
    else:
        # No blank line found, all content is metadata
        metadata_end = len(lines)

    # Add any new keys not found in existing metadata
    for key, value in updates.items():
        if key not in found_keys:
            metadata_lines.append(f'{key}={value}')

    # Reconstruct content
    remaining = lines[metadata_end:]
    return '\n'.join(metadata_lines + remaining)


def get_metadata_content_split(content: str) -> tuple[str, str]:
    """Split markdown content into metadata and body.

    Args:
        content: Full markdown file content

    Returns:
        Tuple of (metadata_block, body_content)
    """
    lines = content.split('\n')
    metadata_lines = []
    body_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Stop at blank line or heading
        if not stripped or stripped.startswith('#'):
            body_start = i
            break

        # This is a metadata line
        if '=' in stripped:
            metadata_lines.append(line)

    metadata_block = '\n'.join(metadata_lines)
    body = '\n'.join(lines[body_start:])

    return metadata_block, body


if __name__ == '__main__':
    # Quick self-test when run directly
    print('file_ops.py - File Operations Base Module')
    print('=' * 50)
    print(f'\nWorkflow Base Directory: {get_base_dir()}')
    print('\nAvailable functions:')
    print('- get_base_dir() -> Path')
    print('- set_base_dir(path)')
    print('- base_path(*parts) -> Path')
    print('- get_temp_dir(subdir?) -> Path')
    print('- atomic_write_file(path, content)')
    print('- ensure_directory(path)')
    print('- output_success(operation, **kwargs)')
    print('- output_error(operation, error)')
    print('- parse_markdown_metadata(content)')
    print('- generate_markdown_metadata(data)')
    print('- update_markdown_metadata(content, updates)')
    print('- get_metadata_content_split(content)')
    print('\nRun test-file-ops.py for full test suite.')
