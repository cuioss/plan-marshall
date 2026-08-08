#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Generic file I/O operations for plan directories.

Provides basic CRUD operations for any file within a plan directory.
Uses file_ops for consistent path handling and atomic writes.

NOTE: For typed documents (request.md, solution_outline.md), prefer using
manage-plan-documents skill which provides validation and templating.

Usage:
    python3 manage-files.py read --plan-id EXAMPLE-PLAN --file notes.md
    python3 manage-files.py write --plan-id EXAMPLE-PLAN --file notes.md --content "..."
    python3 manage-files.py list --plan-id EXAMPLE-PLAN
    python3 manage-files.py exists --plan-id EXAMPLE-PLAN --file config.toon
    python3 manage-files.py remove --plan-id EXAMPLE-PLAN --file old-file.md
    python3 manage-files.py mkdir --plan-id EXAMPLE-PLAN --dir goals
    python3 manage-files.py discover --root /abs/path --glob "**/*.py" --include-files
    python3 manage-files.py open-in-ide --plan-id my-plan --document solution_outline
    python3 manage-files.py open-in-ide --path /abs/path/to/file.md
    python3 manage-files.py detect-ide

HARD INVARIANT: This module MUST NOT import `tempfile` and MUST NOT call
`mkstemp`, `NamedTemporaryFile`, or `mkdtemp`. The `open-in-ide` verb passes
absolute paths verbatim to the launcher without staging them through a
temporary file. A static AST guard in test_manage_files_open_in_ide.py
enforces this.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from file_ops import (
    atomic_write_file,
    get_executor_path,
    get_marshal_path,
    get_plan_dir,
    output_toon,
    safe_main,
)
from input_validation import (
    add_plan_id_arg,
    is_valid_relative_path,
    parse_args_with_toon_errors,
    require_valid_plan_id,
)
from plan_logging import log_entry

# get_plan_dir imported from file_ops

# =============================================================================
# open-in-ide: module-level constants
# =============================================================================

# Document-type enum for --document. Constrained via argparse `choices=`.
DOCUMENT_REQUEST = 'request'
DOCUMENT_SOLUTION_OUTLINE = 'solution_outline'

# Mapping document-type -> (executor notation, subcommand-arg tuple). The
# helper appends `--plan-id {plan_id}` at call time. Each resolver script
# returns TOON with a `path:` field that the handler parses.
DOCUMENT_RESOLVERS: dict[str, tuple[str, tuple[str, ...]]] = {
    DOCUMENT_REQUEST: (
        'plan-marshall:manage-plan-documents:manage-plan-documents',
        ('request', 'path'),
    ),
    DOCUMENT_SOLUTION_OUTLINE: (
        'plan-marshall:manage-solution-outline:manage-solution-outline',
        ('resolve-path',),
    ),
}

# JetBrains macOS bundle-id -> macOS app name (used as `open -a "<App>"`).
# Exhaustive — no wildcard fall-through. `__CFBundleIdentifier` is the
# platform-supplied env var that survives terminal-spawned subprocesses.
MACOS_JETBRAINS_BUNDLE_IDS: dict[str, str] = {
    'com.jetbrains.intellij': 'IntelliJ IDEA',
    'com.jetbrains.intellij.ce': 'IntelliJ IDEA',
    'com.jetbrains.intellij-EAP': 'IntelliJ IDEA',
    'com.jetbrains.pycharm': 'PyCharm',
    'com.jetbrains.WebStorm': 'WebStorm',
    'com.jetbrains.goland': 'GoLand',
    'com.jetbrains.rider': 'Rider',
    'com.google.android.studio': 'Android Studio',
}

# Linux JetBrains launcher names probed via `shutil.which` in priority order
# only after env-var detection failed.
LINUX_LAUNCHER_PRIORITY: tuple[str, ...] = (
    'idea',
    'pycharm',
    'webstorm',
    'goland',
    'rider',
    'studio',
)

# TERM_PROGRAM values used for VS Code / Cursor detection (cross-platform).
TERM_PROGRAM_VSCODE = 'vscode'
TERM_PROGRAM_CURSOR = 'cursor'


@dataclass(frozen=True)
class IdeRecord:
    """Resolved IDE identity + how to launch it.

    `name` is a stable identifier suitable for TOON return; `launcher_argv`
    is the argv prefix that gets `path` appended at launch time.
    """

    name: str
    launcher_argv: tuple[str, ...]


# =============================================================================
# open-in-ide: pure helpers (testable in isolation, no I/O)
# =============================================================================


def detect_ide(env: Mapping[str, str], platform: str) -> IdeRecord | None:
    """Detect the active IDE from the environment and host platform.

    Pure function: consumes the env mapping and platform string only. Returns
    `None` when no signal matches. `shutil.which` is consulted only for the
    Linux launcher-priority probe (last-resort path).
    """
    cf_bundle = env.get('__CFBundleIdentifier', '')
    term_program = env.get('TERM_PROGRAM', '').lower()

    if platform == 'darwin':
        # macOS: JetBrains family via __CFBundleIdentifier.
        app = MACOS_JETBRAINS_BUNDLE_IDS.get(cf_bundle)
        if app is not None:
            return IdeRecord(name=app, launcher_argv=('open', '-a', app))
        # macOS: VS Code / Cursor via TERM_PROGRAM. Cursor is NEVER silently
        # substituted with VS Code.
        if term_program == TERM_PROGRAM_VSCODE:
            return IdeRecord(name='Visual Studio Code', launcher_argv=('open', '-a', 'Visual Studio Code'))
        if term_program == TERM_PROGRAM_CURSOR:
            return IdeRecord(name='Cursor', launcher_argv=('open', '-a', 'Cursor'))
        return None

    if platform == 'linux':
        # Linux: TERM_PROGRAM short-circuits to a named launcher if present on PATH.
        if term_program == TERM_PROGRAM_VSCODE and shutil.which('code') is not None:
            return IdeRecord(name='Visual Studio Code', launcher_argv=('code',))
        if term_program == TERM_PROGRAM_CURSOR and shutil.which('cursor') is not None:
            return IdeRecord(name='Cursor', launcher_argv=('cursor',))
        # Linux JetBrains: priority probe on PATH.
        for launcher in LINUX_LAUNCHER_PRIORITY:
            if shutil.which(launcher) is not None:
                return IdeRecord(name=launcher, launcher_argv=(launcher,))
        return None

    # Unknown host platform — no detection.
    return None


def build_launch_command(ide: IdeRecord, path: Path) -> list[str]:
    """Build the argv for launching `ide` with `path` appended verbatim."""
    return [*ide.launcher_argv, str(path)]


def is_open_in_ide_enabled() -> bool:
    """Return whether `open-in-ide` is enabled in marshal.json.

    Lenient resolution: a missing file, a missing `plan` namespace, or a
    missing `plan.open_in_ide` field all resolve to the documented default
    `True`. A malformed JSON file or a `plan.open_in_ide` value that is
    not exactly a boolean raises `ValueError` — silent coercion of dicts
    / strings / numbers via `bool(...)` would misclassify obviously-broken
    configs (e.g. `bool({"enabled": False})` is `True`).
    """
    marshal_path = get_marshal_path()
    if not marshal_path.is_file():
        return True
    data = json.loads(marshal_path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(
            f"{marshal_path}: expected a JSON object at the top level, "
            f"got {type(data).__name__}"
        )
    plan_ns = data.get('plan')
    if not isinstance(plan_ns, dict):
        return True
    open_in_ide = plan_ns.get('open_in_ide')
    if open_in_ide is None:
        return True
    if not isinstance(open_in_ide, bool):
        raise ValueError(
            f"{marshal_path}: expected a boolean at plan.open_in_ide, "
            f"got {type(open_in_ide).__name__}"
        )
    return open_in_ide


def _resolve_document_path(plan_id: str, document: str) -> tuple[Path | None, str | None]:
    """Resolve the on-disk path for `document` via the manage-* resolver.

    Returns `(path, None)` on success, `(None, detail)` on resolver failure.
    Uses subprocess to invoke the resolver script via the executor (matches
    the manage-files convention of delegating to sibling manage-* scripts).
    """
    notation, sub_args = DOCUMENT_RESOLVERS[document]
    # The executor lives at `<plan-root>/.plan/execute-script.py`;
    # get_executor_path() resolves it cwd-relatively via the uniform cwd rule
    # (ADR-002) — worktree-resident during phase-5+, main during the regenerate path.
    # Fall back to the canonical PATH-based lookup if resolution fails or the
    # path is unavailable (defensive — should not trigger in normal operation
    # since the executor is always staged at the repo root by manage-architecture).
    try:
        executor: Path | None = get_executor_path()
    except RuntimeError:
        executor = None
    cmd = [
        sys.executable,
        str(executor) if executor is not None and executor.is_file() else '.plan/execute-script.py',
        notation,
        *sub_args,
        '--plan-id',
        plan_id,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or '').strip()
        return None, detail or f'resolver {notation} exited {proc.returncode}'

    # The TOON resolvers print `path: <abs>` somewhere in their output. Walk
    # the lines and pull the first `path: …` value.
    for line in proc.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith('path:'):
            value = stripped[len('path:'):].strip().strip('"')
            if value:
                return Path(value), None
    return None, 'resolver did not emit a path field'


def cmd_open_in_ide(args: argparse.Namespace) -> dict:
    """Open a file or plan-resolved document in the active IDE.

    Ordering (do not reorder — the config gate MUST run before detection so
    the disabled-by-config short-circuit performs neither detection nor
    launcher invocation):
      1. is_open_in_ide_enabled() — if false: skip everything, return success.
      2. Resolve the target path: Mode A (`--path`) verbatim, Mode B
         (`--plan-id + --document`) via the manage-* resolver.
      3. detect_ide(env, platform) — None → ide_not_detected error.
      4. subprocess.run(build_launch_command(ide, path)) — non-zero exit →
         launcher_missing error.
      5. Return success TOON.
    """
    # 1) Config gate.
    if not is_open_in_ide_enabled():
        return {
            'status': 'success',
            'action': 'skipped',
            'reason': 'disabled_by_config',
        }

    # 2) Resolve the target path.
    if args.path is not None:
        target_path = Path(args.path)
    else:
        # Mode B requires --plan-id + --document. argparse already enforces
        # the mutex group; here we just check --document is present.
        if args.plan_id is None or args.document is None:
            return {
                'status': 'error',
                'reason': 'invalid_arguments',
                'detail': 'Mode B requires both --plan-id and --document',
            }
        require_valid_plan_id(args)
        resolved, detail = _resolve_document_path(args.plan_id, args.document)
        if resolved is None:
            return {
                'status': 'error',
                'reason': 'document_resolution_failed',
                'detail': detail or 'unknown resolver error',
            }
        target_path = resolved

    # 3) Detect the IDE. Uses module-level os.environ + sys.platform so
    # tests can patch via `mock.patch.object(_mod, 'sys', ...)`.
    raw_platform = sys.platform
    platform = 'darwin' if raw_platform == 'darwin' else ('linux' if raw_platform.startswith('linux') else raw_platform)
    ide = detect_ide(os.environ, platform)
    if ide is None:
        return {
            'status': 'error',
            'reason': 'ide_not_detected',
            'detail': f'No supported IDE detected on platform={platform}',
        }

    # 4) Launch. Fire-and-forget contract: every supported launcher returns
    # immediately on its own.
    argv = build_launch_command(ide, target_path)
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        return {
            'status': 'error',
            'reason': 'launcher_missing',
            'detail': f'{argv[0]}: {exc}',
        }
    if proc.returncode != 0:
        return {
            'status': 'error',
            'reason': 'launcher_missing',
            'detail': (proc.stderr or proc.stdout or f'{argv[0]} exited {proc.returncode}').strip(),
        }

    return {
        'status': 'success',
        'ide': ide.name,
        'command': ' '.join(argv),
        'path': str(target_path),
    }


def _derive_detection_signal(env: Mapping[str, str], platform: str) -> str | None:
    """Re-run the detection priority and name the branch that fired.

    Returns one of: `cf_bundle_identifier`, `term_program`, `path_probe`, or
    `None` when no branch matches. Mirrors the priority order inside
    `detect_ide` exactly — keep in sync if `detect_ide` is ever reordered.
    """
    cf_bundle = env.get('__CFBundleIdentifier', '')
    term_program = env.get('TERM_PROGRAM', '').lower()

    if platform == 'darwin':
        if cf_bundle in MACOS_JETBRAINS_BUNDLE_IDS:
            return 'cf_bundle_identifier'
        if term_program in (TERM_PROGRAM_VSCODE, TERM_PROGRAM_CURSOR):
            return 'term_program'
        return None

    if platform == 'linux':
        if term_program == TERM_PROGRAM_VSCODE and shutil.which('code') is not None:
            return 'term_program'
        if term_program == TERM_PROGRAM_CURSOR and shutil.which('cursor') is not None:
            return 'term_program'
        for launcher in LINUX_LAUNCHER_PRIORITY:
            if shutil.which(launcher) is not None:
                return 'path_probe'
        return None

    return None


def cmd_detect_ide(args: argparse.Namespace) -> dict:
    """Detect the active IDE/terminal from the environment.

    Pure environment query — no `--plan-id`, no `marshal.json` gate, no
    launcher invocation. Wraps `detect_ide(os.environ, sys.platform)` and
    serializes the resulting `IdeRecord` (or absence thereof) to TOON.
    """
    raw_platform = sys.platform
    platform = 'darwin' if raw_platform == 'darwin' else ('linux' if raw_platform.startswith('linux') else raw_platform)
    ide = detect_ide(os.environ, platform)
    if ide is None:
        return {
            'status': 'success',
            'detected': False,
            'platform': platform,
        }
    signal = _derive_detection_signal(os.environ, platform)
    result: dict = {
        'status': 'success',
        'detected': True,
        'name': ide.name,
        'launcher_argv': list(ide.launcher_argv),
        'platform': platform,
    }
    if signal is not None:
        result['signal'] = signal
    return result


def cmd_read(args: argparse.Namespace) -> dict | None:
    """Read file content from plan directory."""
    require_valid_plan_id(args)

    if not is_valid_relative_path(args.file):
        return {'status': 'error', 'error': 'invalid_path', 'message': f'Invalid file path: {args.file}'}

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    if not file_path.exists():
        return {'status': 'error', 'error': 'file_not_found', 'message': f'File not found: {file_path}'}

    # Raw content output (not TOON) - print directly and return None
    print(file_path.read_text(encoding='utf-8'), end='')
    return None


def cmd_write(args: argparse.Namespace) -> dict:
    """Write content to file in plan directory."""
    require_valid_plan_id(args)

    if not is_valid_relative_path(args.file):
        return {'status': 'error', 'error': 'invalid_path', 'message': f'Invalid file path: {args.file}'}

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    # Mutual exclusion: --content and --content-file cannot be combined.
    content_file_raw = getattr(args, 'content_file', None)
    if args.content and content_file_raw:
        return {
            'status': 'error',
            'error': 'mutually_exclusive',
            'message': 'Cannot use both --content and --content-file',
        }

    # Get content from --content-file (highest precedence), --content, or --stdin.
    if content_file_raw:
        content_file_path = Path(content_file_raw).expanduser().resolve()
        if not content_file_path.exists() or not content_file_path.is_file():
            return {
                'status': 'error',
                'error': 'content_file_not_found',
                'content_file': str(content_file_path),
                'message': f'content_file does not exist or is not a regular file: {content_file_path}',
            }
        content = content_file_path.read_text(encoding='utf-8')
    elif args.content:
        content = args.content
    elif args.stdin:
        content = sys.stdin.read()
    else:
        return {
            'status': 'error',
            'error': 'missing_content',
            'message': 'Must provide --content, --content-file, or --stdin',
        }

    if not content:
        return {'status': 'error', 'error': 'empty_content', 'message': 'Content cannot be empty'}

    # Ensure plan directory exists
    plan_dir.mkdir(parents=True, exist_ok=True)

    # Write atomically
    atomic_write_file(file_path, content)
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-FILES] Created {args.file}')
    return {'status': 'success', 'action': 'created', 'file': args.file, 'path': str(file_path)}


def cmd_remove(args: argparse.Namespace) -> dict:
    """Remove file from plan directory."""
    require_valid_plan_id(args)

    if not is_valid_relative_path(args.file):
        return {'status': 'error', 'error': 'invalid_path', 'message': f'Invalid file path: {args.file}'}

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    if not file_path.exists():
        return {'status': 'error', 'error': 'file_not_found', 'message': f'File not found: {file_path}'}

    file_path.unlink()
    log_entry('work', args.plan_id, 'INFO', f'[MANAGE-FILES] Removed {args.file}')
    return {'status': 'success', 'action': 'removed', 'file': args.file, 'path': str(file_path)}


def cmd_list(args: argparse.Namespace) -> dict:
    """List files in plan directory."""
    require_valid_plan_id(args)

    plan_dir = get_plan_dir(args.plan_id)

    if args.dir:
        if not is_valid_relative_path(args.dir):
            return {'status': 'error', 'error': 'invalid_path', 'message': f'Invalid directory path: {args.dir}'}
        target_dir = plan_dir / args.dir
    else:
        target_dir = plan_dir

    if not target_dir.exists():
        return {'status': 'error', 'error': 'dir_not_found', 'message': f'Directory not found: {target_dir}'}

    files = []
    for item in sorted(target_dir.iterdir()):
        if item.is_dir():
            files.append(f'{item.name}/')
        else:
            files.append(item.name)

    return {'status': 'success', 'plan_id': args.plan_id, 'files': files}


def cmd_exists(args: argparse.Namespace) -> dict:
    """Check if file exists in plan directory.

    Returns dict with exists: true/false.
    """
    require_valid_plan_id(args)

    if not is_valid_relative_path(args.file):
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'file': args.file,
            'error': 'invalid_path',
            'message': f'Invalid file path: {args.file}',
        }

    plan_dir = get_plan_dir(args.plan_id)
    file_path = plan_dir / args.file

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'file': args.file,
        'exists': file_path.exists(),
        'path': str(file_path),
    }


def cmd_mkdir(args: argparse.Namespace) -> dict:
    """Create subdirectory in plan directory.

    Returns dict with the created directory path.
    """
    require_valid_plan_id(args)

    if not is_valid_relative_path(args.dir):
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'invalid_path',
            'message': f'Invalid directory path: {args.dir}',
        }

    plan_dir = get_plan_dir(args.plan_id)
    target_dir = plan_dir / args.dir

    already_exists = target_dir.exists()
    target_dir.mkdir(parents=True, exist_ok=True)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'action': 'exists' if already_exists else 'created',
        'dir': args.dir,
        'path': str(target_dir),
    }


def cmd_create_or_reference(args: argparse.Namespace) -> dict:
    """Create plan directory if it doesn't exist, or reference existing one.

    Returns dict indicating whether the plan was created or already exists.
    This replaces the two-step list+check pattern in plan-init.
    """
    require_valid_plan_id(args)

    plan_dir = get_plan_dir(args.plan_id)

    if plan_dir.exists():
        # Plan already exists - gather info about it
        result = {'status': 'success', 'plan_id': args.plan_id, 'action': 'exists', 'path': str(plan_dir)}

        # Check if status.json exists to get phase info
        status_path = plan_dir / 'status.json'
        if status_path.exists():
            try:
                status = json.loads(status_path.read_text(encoding='utf-8'))
                result['current_phase'] = status.get('current_phase', 'unknown')
            except (ValueError, KeyError, OSError):
                # Parse error or read error - just note file exists
                result['has_status'] = True

        return result
    else:
        # Create the plan directory
        plan_dir.mkdir(parents=True, exist_ok=True)

        return {'status': 'success', 'plan_id': args.plan_id, 'action': 'created', 'path': str(plan_dir)}


def cmd_discover(args: argparse.Namespace) -> dict:
    """Discover filesystem paths matching one or more glob patterns under a root.

    Pure pathlib implementation — never spawns subprocess or invokes shell. Consumer
    skills should call this rather than instructing the LLM to use the Glob tool, so
    discovery becomes deterministic and auditable.
    """
    root_path = Path(args.root)

    if not root_path.exists() or not root_path.is_dir():
        return {
            'status': 'error',
            'error': 'invalid_root',
            'message': f'Root does not exist or is not a directory: {args.root}',
        }

    if not args.glob:
        return {
            'status': 'error',
            'error': 'no_patterns',
            'message': 'At least one --glob pattern is required',
        }

    # Default behavior: include files only when neither flag is set.
    include_files = args.include_files or not args.include_dirs
    include_dirs = args.include_dirs

    seen: set[Path] = set()
    for pattern in args.glob:
        for match in root_path.glob(pattern):
            if match.is_file() and not include_files:
                continue
            if match.is_dir() and not include_dirs:
                continue
            seen.add(match.resolve())

    paths = sorted(str(p) for p in seen)

    return {
        'status': 'success',
        'root': str(root_path.resolve()),
        'paths': paths,
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(description='Generic file I/O operations for plan directories', allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True)

    # read
    read_parser = subparsers.add_parser('read', help='Read file content', allow_abbrev=False)
    add_plan_id_arg(read_parser)
    read_parser.add_argument('--file', required=True, help='Relative file path')
    read_parser.set_defaults(func=cmd_read)

    # write
    write_parser = subparsers.add_parser('write', help='Write file content', allow_abbrev=False)
    add_plan_id_arg(write_parser)
    write_parser.add_argument('--file', required=True, help='Relative file path')
    write_parser.add_argument('--content', help='Content to write')
    write_parser.add_argument(
        '--content-file',
        help='Path to a UTF-8 file whose contents fill the write payload. Mutually exclusive with --content.',
    )
    write_parser.add_argument('--stdin', action='store_true', help='Read content from stdin')
    write_parser.set_defaults(func=cmd_write)

    # remove
    remove_parser = subparsers.add_parser('remove', help='Remove file', allow_abbrev=False)
    add_plan_id_arg(remove_parser)
    remove_parser.add_argument('--file', required=True, help='Relative file path')
    remove_parser.set_defaults(func=cmd_remove)

    # list
    list_parser = subparsers.add_parser('list', help='List files', allow_abbrev=False)
    add_plan_id_arg(list_parser)
    list_parser.add_argument('--dir', help='Subdirectory to list')
    list_parser.set_defaults(func=cmd_list)

    # exists
    exists_parser = subparsers.add_parser('exists', help='Check if file exists', allow_abbrev=False)
    add_plan_id_arg(exists_parser)
    exists_parser.add_argument('--file', required=True, help='Relative file path')
    exists_parser.set_defaults(func=cmd_exists)

    # mkdir
    mkdir_parser = subparsers.add_parser('mkdir', help='Create subdirectory', allow_abbrev=False)
    add_plan_id_arg(mkdir_parser)
    mkdir_parser.add_argument('--dir', required=True, help='Directory to create')
    mkdir_parser.set_defaults(func=cmd_mkdir)

    # create-or-reference
    create_ref_parser = subparsers.add_parser(
        'create-or-reference',
        help='Create plan directory or reference existing one',
        allow_abbrev=False,
    )
    add_plan_id_arg(create_ref_parser)
    create_ref_parser.set_defaults(func=cmd_create_or_reference)

    # discover
    discover_parser = subparsers.add_parser(
        'discover',
        help='Discover filesystem paths matching glob patterns under a root (pathlib only)',
        allow_abbrev=False,
    )
    discover_parser.add_argument('--root', required=True, help='Absolute root directory')
    discover_parser.add_argument(
        '--glob',
        action='append',
        default=[],
        help='Glob pattern relative to root (repeatable)',
    )
    discover_parser.add_argument(
        '--include-files',
        action='store_true',
        help='Include files in results (default when neither flag set)',
    )
    discover_parser.add_argument(
        '--include-dirs',
        action='store_true',
        help='Include directories in results',
    )
    discover_parser.set_defaults(func=cmd_discover)

    # open-in-ide
    open_parser = subparsers.add_parser(
        'open-in-ide',
        help='Open a file in the active IDE (detected from env + host platform)',
        allow_abbrev=False,
    )
    # Mutually exclusive input mode: either a direct absolute path (Mode A)
    # or plan-id + document type (Mode B). Both modes must be in the SAME
    # mutex group so argparse rejects combinations like `--path X --plan-id Y`.
    open_mutex = open_parser.add_mutually_exclusive_group(required=True)
    open_mutex.add_argument(
        '--path',
        help='Absolute path to the file to open (Mode A)',
    )
    open_mutex.add_argument(
        '--plan-id',
        help='Plan identifier; requires --document (Mode B)',
    )
    open_parser.add_argument(
        '--document',
        choices=(DOCUMENT_REQUEST, DOCUMENT_SOLUTION_OUTLINE),
        help='Document type to resolve via manage-* (Mode B only)',
    )
    open_parser.set_defaults(func=cmd_open_in_ide)

    # detect-ide
    detect_ide_parser = subparsers.add_parser(
        'detect-ide',
        help='Detect active IDE/terminal from environment',
        allow_abbrev=False,
    )
    detect_ide_parser.set_defaults(func=cmd_detect_ide)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    if result is not None:
        output_toon(result)
    return 0


if __name__ == '__main__':
    main()
