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

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# Bootstrap sys.path so script-shared/scripts is importable. file_ops needs
# git_main_checkout_root from script-shared.marketplace_paths (the canonical
# implementation lives there to avoid byte-for-byte duplication between the
# two bundles — see PR #160 review). The walk locates the bundle's
# skills/ root from this script's own __file__ and inserts script-shared/scripts
# at the front of sys.path. Doing this in module init means callers (tests,
# bootstrap scripts) don't have to remember to set up PYTHONPATH first.
_THIS_FILE = Path(__file__).resolve()
for _ancestor in _THIS_FILE.parents:
    if _ancestor.name == 'skills' and (_ancestor.parent / '.claude-plugin' / 'plugin.json').is_file():
        _shared_scripts = str(_ancestor / 'script-shared' / 'scripts')
        if _shared_scripts not in sys.path:
            sys.path.insert(0, _shared_scripts)
        break

from constants import (  # noqa: E402
    DIR_PER_MODULE_DERIVED,
    DIR_PER_MODULE_ENRICHED,
)
from marketplace_paths import (  # type: ignore[import-not-found]  # noqa: E402
    PLAN_DIR_NAME,
    git_main_checkout_root,
)
from toon_parser import serialize_toon  # type: ignore[import-not-found]  # noqa: E402

# Plan-marshall runtime state (plans, archived-plans, run-configuration.json,
# lessons-learned, memory, logs) lives at ``<git_main_checkout_root>/.plan/local``
# — project-local, covered by the existing ``Write(.plan/**)`` permission.
# Worktrees are anchored separately at ``<root>/.claude/worktrees/``.

# Runtime-overridable base directory (set by set_base_dir for tests).
# None means "resolve from environment / git on each call".
_BASE_DIR_OVERRIDE: Path | None = None


def now_utc_iso() -> str:
    """Get current UTC time as ISO 8601 string with Z suffix.

    Returns:
        ISO 8601 formatted timestamp, e.g., '2025-12-02T10:30:00Z'
    """
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def parse_duration(duration_str: str) -> 'timedelta':
    """Parse a duration string like '7d', '24h', '30m' into a timedelta.

    Args:
        duration_str: Duration string with suffix d (days), h (hours), or m (minutes)

    Returns:
        timedelta object

    Raises:
        ValueError: If format is invalid
    """
    import re
    from datetime import timedelta

    match = re.match(r'^(\d+)([dhm])$', duration_str.strip())
    if not match:
        raise ValueError(f"Invalid duration format: '{duration_str}'. Use Nd, Nh, or Nm.")
    value = int(match.group(1))
    unit = match.group(2)
    if unit == 'd':
        return timedelta(days=value)
    if unit == 'h':
        return timedelta(hours=value)
    return timedelta(minutes=value)


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like '5.2s', '3m12s', '1h5m'
    """
    if seconds < 60:
        return f'{seconds:.1f}s'
    if seconds < 3600:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f'{m}m{s}s'
    h = int(seconds // 3600)
    m = int(seconds % 3600 // 60)
    return f'{h}h{m}m'


def get_worktree_root() -> Path:
    """Return the project-local worktree root for plan-marshall.

    Resolves to ``<git_main_checkout_root>/.claude/worktrees`` — the canonical
    location documented by Claude Code for per-feature worktrees. Worktrees
    live under the main checkout so they inherit the project's existing
    permission allow-list and IDE indexing.

    Raises:
        RuntimeError: when not inside a git repository (worktrees require a
            main checkout to anchor against).
    """
    root = git_main_checkout_root()
    if root is None:
        raise RuntimeError(
            'get_worktree_root() requires a git repository; '
            'no main checkout root could be resolved from cwd.'
        )
    return root / '.claude' / 'worktrees'


def normalize_to_repo_relative(path: str) -> str:
    """Normalize absolute file paths to repository-relative paths.

    If the path is already relative, returns it unchanged.
    If absolute, attempts to strip the git repo root prefix.

    Args:
        path: File path (absolute or relative)

    Returns:
        Repository-relative path string
    """
    if not path.startswith('/'):
        return path
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        repo_root = result.stdout.strip()
        if path.startswith(repo_root + '/'):
            return path[len(repo_root) + 1 :]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return path


def get_base_dir() -> Path:
    """Get the base directory for plan-marshall runtime state.

    Resolution order:
        1. Explicit set_base_dir() override (tests).
        2. PLAN_BASE_DIR environment variable (tests, user override).
        3. ``<git_main_checkout_root>/.plan/local`` when inside a git repo.

    Raises:
        RuntimeError: when none of the above resolve (no override, no
            env var, and not inside a git repository).
    """
    if _BASE_DIR_OVERRIDE is not None:
        return _BASE_DIR_OVERRIDE
    env_dir = os.environ.get('PLAN_BASE_DIR')
    if env_dir:
        return Path(env_dir)
    root = git_main_checkout_root()
    if root is None:
        raise RuntimeError(
            'plan-marshall runtime state requires a git checkout; '
            'no main checkout root could be resolved from cwd. '
            'Set PLAN_BASE_DIR to override (tests).'
        )
    return root / PLAN_DIR_NAME / 'local'


def set_base_dir(path: Path | str) -> None:
    """Override the base directory for workflow files.

    Args:
        path: New base directory path

    Note:
        This is primarily for testing purposes. In production,
        the default per-project global directory should be used.
    """
    global _BASE_DIR_OVERRIDE
    _BASE_DIR_OVERRIDE = Path(path)


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
    """Get temp directory under the repo-local tracked config dir.

    Args:
        subdir: Optional subdirectory name within temp

    Returns:
        Path to ``.plan/temp[/subdir]`` inside the repo checkout.

    Note:
        temp/ intentionally stays project-local (unlike the runtime state
        under get_base_dir()) so each worktree gets its own isolated temp,
        build logs sit next to the source they came from, and the existing
        ``Write(.plan/**)`` permission keeps covering it. Resolution
        honours PLAN_TRACKED_CONFIG_DIR / PLAN_BASE_DIR overrides via
        get_tracked_config_dir().
    """
    temp_path = get_tracked_config_dir() / 'temp'
    if subdir:
        return temp_path / subdir
    return temp_path


def get_plan_dir(plan_id: str) -> Path:
    """Get the plan directory path for a given plan ID.

    Args:
        plan_id: Plan identifier

    Returns:
        Path to {base_dir}/plans/{plan_id}/
    """
    return base_path('plans', plan_id)


def get_tracked_config_dir() -> Path:
    """Get the repo-local tracked configuration directory.

    Returns the repo-local ``.plan/`` directory where tracked files live
    (``marshal.json`` and ``project-architecture/``). Unlike get_base_dir(),
    this normally points at the repo — not the per-project global directory.

    The ``project-architecture/`` subdirectory uses a per-module layout: a
    top-level ``_project.json`` (the source of truth for "which modules
    exist") plus one directory per module containing ``derived.json``
    (deterministic discovery output) and ``enriched.json`` (LLM-augmented
    fields). Path constants live in ``constants.py`` as ``FILE_PROJECT_META``,
    ``DIR_PER_MODULE_DERIVED``, and ``DIR_PER_MODULE_ENRICHED``; per-module
    paths are constructed via ``get_module_derived_path()`` and
    ``get_module_enriched_path()``.

    Resolution order:
        1. Explicit set_base_dir() override (tests).
        2. PLAN_TRACKED_CONFIG_DIR environment variable (tests, fine-grained
           override).
        3. PLAN_BASE_DIR environment variable (backward compatibility for
           tests that already stage both runtime state AND marshal.json in
           the same fixture directory).
        4. {git-main-checkout-root}/.plan when inside a git repo.
        5. ./.plan relative to cwd (fallback).
    """
    if _BASE_DIR_OVERRIDE is not None:
        return _BASE_DIR_OVERRIDE
    env_tracked = os.environ.get('PLAN_TRACKED_CONFIG_DIR')
    if env_tracked:
        return Path(env_tracked)
    env_base = os.environ.get('PLAN_BASE_DIR')
    if env_base:
        return Path(env_base)
    root = git_main_checkout_root()
    if root is not None:
        return root / PLAN_DIR_NAME
    return Path(PLAN_DIR_NAME)


def get_marshal_path() -> Path:
    """Path to the tracked marshal.json file."""
    return get_tracked_config_dir() / 'marshal.json'


def get_project_architecture_dir() -> Path:
    """Path to the tracked project-architecture/ directory."""
    return get_tracked_config_dir() / 'project-architecture'


def get_module_derived_path(plan_id: str, module_name: str) -> Path:
    """Path to a module's ``derived.json`` under project-architecture.

    Resolves to ``{tracked_config_dir}/project-architecture/{module_name}/derived.json``.
    The file holds the deterministic discovery output for the named module
    (paths, packages, dependencies). Use ``constants.DIR_PER_MODULE_DERIVED``
    as the filename literal.

    Args:
        plan_id: Plan identifier. Reserved for future per-plan
            project-architecture overrides; currently unused because the
            tracked project-architecture tree is project-wide. Pass the
            active plan id for forward compatibility.
        module_name: Module name as listed in ``_project.json``'s ``modules``
            index.

    Returns:
        Path to ``{module_name}/derived.json`` under the project-architecture
        directory. Existence is not checked.
    """
    # plan_id is currently unused; project-architecture is project-wide,
    # but keeping the parameter preserves the public signature so callers
    # can pass plan-scoped context when (and if) per-plan overlays land.
    del plan_id
    return get_project_architecture_dir() / module_name / DIR_PER_MODULE_DERIVED


def get_module_enriched_path(plan_id: str, module_name: str) -> Path:
    """Path to a module's ``enriched.json`` under project-architecture.

    Resolves to ``{tracked_config_dir}/project-architecture/{module_name}/enriched.json``.
    The file holds the LLM-augmented fields for the named module
    (responsibility, purpose, key_packages, skills_by_profile, …). Use
    ``constants.DIR_PER_MODULE_ENRICHED`` as the filename literal.

    Args:
        plan_id: Plan identifier. Reserved for future per-plan
            project-architecture overrides; currently unused because the
            tracked project-architecture tree is project-wide. Pass the
            active plan id for forward compatibility.
        module_name: Module name as listed in ``_project.json``'s ``modules``
            index.

    Returns:
        Path to ``{module_name}/enriched.json`` under the project-architecture
        directory. Existence is not checked.
    """
    del plan_id
    return get_project_architecture_dir() / module_name / DIR_PER_MODULE_ENRICHED


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
    """Print TOON error output to stderr (canonical low-level variant).

    This is the shared base implementation. Domain-specific variants exist in
    ci_base.py, manage-memory.py, _tasks_core.py, and _documents_core.py.
    Per manage-contract.md: prefer output_toon_error() for manage-* scripts.
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


def copy_tree(src: Path, dst: Path) -> None:
    """Recursively copy ``src`` directory tree into ``dst``.

    Used by ``phase-1-init`` to snapshot ``.plan/project-architecture/`` into
    ``.plan/local/plans/{plan_id}/architecture-pre/`` so ``phase-6-finalize``
    can compute the architectural delta produced by the plan via
    ``manage-architecture diff-modules --pre``.

    Behaviour:
        - Recursive copy of every regular file in ``src`` into ``dst``.
        - Symlinks are skipped (not followed) — the snapshot is a static
          copy of the on-disk descriptor, never indirected through symlinks.
        - Parent directories of ``dst`` are created on demand (``mkdir -p``).
        - Raises ``FileExistsError`` when ``dst`` already exists. Callers MUST
          either choose a fresh destination path or remove ``dst`` before
          calling — this skill never silently merges over a previous snapshot.
        - Implementation delegates to ``shutil.copytree`` with
          ``symlinks=False`` (skip symlinks) and ``dirs_exist_ok=False``
          (raise on existing destination).

    Args:
        src: Source directory to copy from. Must exist and be a directory.
        dst: Destination directory. Must NOT exist; parent directories are
            created automatically.

    Raises:
        FileNotFoundError: when ``src`` does not exist.
        NotADirectoryError: when ``src`` exists but is not a directory.
        FileExistsError: when ``dst`` already exists.
    """
    src_path = Path(src)
    dst_path = Path(dst)

    if not src_path.exists():
        raise FileNotFoundError(f'copy_tree source does not exist: {src_path}')
    if not src_path.is_dir():
        raise NotADirectoryError(f'copy_tree source is not a directory: {src_path}')
    if dst_path.exists():
        raise FileExistsError(f'copy_tree destination already exists: {dst_path}')

    # Ensure parent of dst exists (mkdir -p semantics for the parent only;
    # dst itself is created by copytree).
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    # shutil.copytree walks the source tree; symlinks=False would convert any
    # symlink it visits into a copy of its target (following file symlinks AND
    # recursing into directory symlinks). A copy_function-only filter cannot
    # block directory symlinks because copytree decides whether to recurse
    # before invoking copy_function on the directory's children. To skip
    # symlinks entirely (file AND directory), filter them out at the directory
    # listing level via the `ignore` callable so copytree never sees them.
    def _ignore_symlinks(directory: str, names: list[str]) -> list[str]:
        return [name for name in names if (Path(directory) / name).is_symlink()]

    shutil.copytree(
        src_path,
        dst_path,
        symlinks=False,
        ignore=_ignore_symlinks,
        ignore_dangling_symlinks=True,
        dirs_exist_ok=False,
    )


def _cli_copy_tree(args: argparse.Namespace) -> int:
    """CLI handler: ``file_ops copy-tree --src SRC --dst DST``.

    Wraps :func:`copy_tree` for invocation via the marketplace executor
    (e.g. from ``phase-1-init/SKILL.md``). Resolves ``src`` and ``dst`` to
    absolute paths against the current working directory, then delegates to
    the library function. Errors surface as the standard manage-* TOON
    contract (``status: error``, ``error: <code>``, ``message: ...``).
    """
    src = Path(args.src).resolve()
    dst = Path(args.dst).resolve()

    try:
        copy_tree(src, dst)
    except FileNotFoundError as exc:
        output_toon_error('src_not_found', str(exc), src=str(src), dst=str(dst))
        return 1
    except NotADirectoryError as exc:
        output_toon_error('src_not_directory', str(exc), src=str(src), dst=str(dst))
        return 1
    except FileExistsError as exc:
        output_toon_error('dst_already_exists', str(exc), src=str(src), dst=str(dst))
        return 1

    output_toon({
        'status': 'success',
        'operation': 'copy-tree',
        'src': str(src),
        'dst': str(dst),
    })
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for file_ops CLI subcommands."""
    parser = argparse.ArgumentParser(
        prog='file_ops',
        description='File operations utility (CLI wrappers around library helpers).',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    cp = subparsers.add_parser(
        'copy-tree',
        help='Recursively copy a directory tree (symlinks skipped, '
        'fails if destination exists).',
        allow_abbrev=False,
    )
    cp.add_argument('--src', required=True, help='Source directory path.')
    cp.add_argument('--dst', required=True, help='Destination directory path (must not exist).')
    cp.set_defaults(handler=_cli_copy_tree)

    return parser


def _main() -> int:
    """CLI entry-point. Dispatches to the selected subcommand handler."""
    parser = _build_arg_parser()
    args = parser.parse_args()
    return int(args.handler(args))


if __name__ == '__main__':
    sys.exit(_main())
