#!/usr/bin/env python3
"""
Base file operations module for workflow scripts.

Provides atomic file operations, metadata parsing, TOON output helpers,
and base directory configuration for workflow files.

Usage:
    from file_ops import (
        atomic_write_file,
        ensure_directory,
        output_toon,
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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from toon_parser import serialize_toon  # type: ignore[import-not-found]

# Default base directory for workflow files
# Can be overridden via PLAN_BASE_DIR environment variable for testing
_BASE_DIR = Path(os.environ.get('PLAN_BASE_DIR', '.plan'))


def now_utc_iso() -> str:
    """Get current UTC time as ISO 8601 string with Z suffix.

    Returns:
        ISO 8601 formatted timestamp, e.g., '2025-12-02T10:30:00Z'
    """
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


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
    return get_base_dir().joinpath(*parts)


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


def get_plan_dir(plan_id: str) -> Path:
    """Get the plan directory path for a given plan ID.

    Args:
        plan_id: Plan identifier

    Returns:
        Path to .plan/plans/{plan_id}/
    """
    return base_path('plans', plan_id)


def read_json(path: str | Path, default: Any = None) -> Any:
    """Read and parse a JSON file, returning default if not found.

    Args:
        path: Path to JSON file
        default: Value to return if file doesn't exist (default: empty dict)

    Returns:
        Parsed JSON content, or default if file not found
    """
    if default is None:
        default = {}
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding='utf-8'))


def write_json(path: str | Path, data: Any) -> None:
    """Write data as formatted JSON, creating parent dirs as needed.

    Args:
        path: Target file path
        data: Data to serialize as JSON
    """
    atomic_write_file(path, json.dumps(data, indent=2))


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
        if Path(temp_path).exists():
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


def output_toon(data: dict[str, Any]) -> None:
    """Print TOON formatted data to stdout.

    Generic TOON output helper for scripts that need to emit structured responses.

    Args:
        data: Dictionary to serialize as TOON
    """
    print(serialize_toon(data))


def format_toon_value(value: Any) -> str:
    """Format a value for TOON output.

    Args:
        value: Value to format

    Returns:
        Formatted string
    """
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, list):
        return '+'.join(str(v) for v in value)
    return str(value)


def print_toon_table(name: str, items: list, fields: list) -> None:
    """Print a TOON table with tab-separated columns.

    Args:
        name: Table name
        items: List of dicts
        fields: List of field names to include
    """
    field_spec = ','.join(fields)
    print(f'{name}[{len(items)}]{{{field_spec}}}:')
    for item in items:
        values = [format_toon_value(item.get(f, '')) for f in fields]
        print('\t'.join(values))


def print_toon_list(name: str, items: list) -> None:
    """Print a TOON list.

    Args:
        name: List name
        items: List of values
    """
    print(f'{name}[{len(items)}]:')
    for item in items:
        print(f'  - {item}')


def print_toon_kv(key: str, value: Any, indent: int = 0) -> None:
    """Print a key-value pair in TOON format.

    Args:
        key: Key name
        value: Value (can be str, int, bool, list, dict)
        indent: Indentation level
    """
    prefix = '  ' * indent
    if isinstance(value, dict):
        print(f'{prefix}{key}:')
        for k, v in value.items():
            print_toon_kv(k, v, indent + 1)
    elif isinstance(value, list):
        print(f'{prefix}{key}[{len(value)}]:')
        for item in value:
            print(f'{prefix}  - {item}')
    else:
        formatted = format_toon_value(value)
        print(f'{prefix}{key}: {formatted}')


def output_success(operation: str, **kwargs: Any) -> None:
    """Print TOON success output to stdout.

    Args:
        operation: Name of the operation
        **kwargs: Additional fields to include in output
    """
    result = {'status': 'success', 'success': True, 'operation': operation}
    result.update(kwargs)
    print(serialize_toon(result))


def output_error(operation: str, error: str) -> None:
    """Print TOON error output to stderr.

    Args:
        operation: Name of the operation
        error: Error message
    """
    result = {'status': 'error', 'success': False, 'operation': operation, 'error': error}
    print(serialize_toon(result), file=sys.stderr)


def output_toon_error(error_code: str, message: str, **kwargs: Any) -> None:
    """Print TOON error output to stdout following the manage-* contract.

    Standard error format: status=error, error=<code>, message=<msg>.

    Args:
        error_code: Machine-readable error code (e.g., 'invalid_plan_id')
        message: Human-readable error description
        **kwargs: Additional fields to include in output
    """
    result: dict[str, Any] = {'status': 'error', 'error': error_code, 'message': message}
    result.update(kwargs)
    print(serialize_toon(result))


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


def safe_main(main_fn: Any) -> Any:
    """Decorator for script entry points that catches unhandled exceptions.

    Wraps the main function so that unhandled exceptions produce a TOON error
    on stderr and exit with code 1, instead of printing a raw traceback.

    Usage:
        @safe_main
        def main() -> int:
            ...
            return 0

        if __name__ == '__main__':
            main()  # calls sys.exit internally
    """
    import functools

    @functools.wraps(main_fn)
    def wrapper() -> None:
        try:
            sys.exit(main_fn())
        except KeyboardInterrupt:
            sys.exit(130)
        except SystemExit:
            raise
        except Exception as e:
            output_error('main', str(e))
            sys.exit(1)

    return wrapper


