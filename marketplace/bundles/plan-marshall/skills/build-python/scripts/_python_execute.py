#!/usr/bin/env python3
"""Python/pyprojectx command execution — config-driven via execute handler factory.

Provides:
- execute_direct(): Foundation API for pyprojectx command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)

Includes a one-shot self-heal layer that mitigates known worktree
``.pyprojectx`` cache-corruption symptoms: ``uv: command not found`` (exit
127) and ``Failed to create virtual environment ... Directory not empty``.
On a matching failure, the cache directory is renamed aside to
``.pyprojectx.broken`` and the command is re-run exactly once. The
self-heal is skipped when ``.pyprojectx.broken`` already exists so a prior
broken cache is never clobbered.

Usage:
    from _python_execute import execute_direct, cmd_run
"""

import logging
from pathlib import Path

from _build_execute import CaptureStrategy
from _build_execute import detect_wrapper as _detect_wrapper
from _build_execute_factory import (
    ExecuteConfig,
    create_execute_handlers,
    default_build_command_fn,
    default_command_key_fn,
)
from _build_result import DirectCommandResult
from _build_shared import DEFAULT_BUILD_TIMEOUT, cmd_run_common
from _python_cmd_parse import parse_log

logger = logging.getLogger(__name__)


def _python_wrapper_resolve_fn(project_dir: str) -> str:
    """Detect pyprojectx wrapper, raising FileNotFoundError if missing."""
    wrapper = _detect_wrapper(project_dir, 'pw', 'pw.bat', 'pwx')
    if wrapper is None:
        raise FileNotFoundError('No pyprojectx wrapper found (pw, pw.bat, or pwx)')
    return str(wrapper)


def _python_scope_fn(args: str) -> str:
    """Extract scope from pyprojectx args (second token is the module name)."""
    parts = args.split()
    return parts[1] if len(parts) > 1 else 'default'


def _python_extra_result_fn(args: str, wrapper: str) -> dict:
    """Add wrapper path to result for pyprojectx builds."""
    return {'wrapper': wrapper}


_CONFIG = ExecuteConfig(
    tool_name='python',
    unix_wrapper='pw',
    windows_wrapper='pw.bat',
    system_fallback='pwx',
    capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
    build_command_fn=default_build_command_fn,
    scope_fn=_python_scope_fn,
    command_key_fn=default_command_key_fn,
    default_timeout=DEFAULT_BUILD_TIMEOUT,
    wrapper_resolve_fn=_python_wrapper_resolve_fn,
    extra_result_fn=_python_extra_result_fn,
)

_inner_execute_direct, _ = create_execute_handlers(_CONFIG, parse_log)

_UV_MISSING_PATTERN = 'uv: command not found'
_VENV_PATTERN = 'Failed to create virtual environment'
_VENV_DETAIL_PATTERN = 'Directory not empty'


def _read_log(log_file: str) -> str:
    if not log_file:
        return ''
    try:
        return Path(log_file).read_text(errors='replace')
    except OSError:
        return ''


def _matches_self_heal_symptoms(haystack: str) -> bool:
    if _UV_MISSING_PATTERN in haystack:
        return True
    if _VENV_PATTERN in haystack and _VENV_DETAIL_PATTERN in haystack:
        return True
    return False


def _should_self_heal(result: DirectCommandResult, project_dir: str) -> bool:
    """True when the failure matches a documented cache-corruption symptom and the rename target is free."""
    if result.get('status') != 'error':
        return False
    haystack = _read_log(result.get('log_file', '') or '') + '\n' + str(result.get('error', ''))
    if not _matches_self_heal_symptoms(haystack):
        return False
    cache_dir = Path(project_dir) / '.pyprojectx'
    broken_dir = Path(project_dir) / '.pyprojectx.broken'
    if not cache_dir.exists():
        return False
    if broken_dir.exists():
        return False
    return True


def execute_direct(
    args: str,
    command_key: str,
    default_timeout: int = DEFAULT_BUILD_TIMEOUT,
    project_dir: str = '.',
    env_vars: dict[str, str] | None = None,
    working_dir: str | None = None,
):
    """pyprojectx execute_direct with a one-shot self-heal retry.

    On a matching cache-corruption failure, the worktree's ``.pyprojectx``
    cache is renamed aside to ``.pyprojectx.broken`` and the command is
    re-run once. The retry result replaces the original. Non-matching
    failures and successes pass through unchanged.
    """
    result = _inner_execute_direct(
        args=args,
        command_key=command_key,
        default_timeout=default_timeout,
        project_dir=project_dir,
        env_vars=env_vars,
        working_dir=working_dir,
    )
    if not _should_self_heal(result, project_dir):
        return result

    cache_dir = Path(project_dir) / '.pyprojectx'
    broken_dir = Path(project_dir) / '.pyprojectx.broken'
    try:
        cache_dir.rename(broken_dir)
    except OSError as exc:
        logger.warning('pyprojectx self-heal rename failed: %s', exc)
        return result
    logger.info('pyprojectx self-heal: renamed %s -> %s, retrying once', cache_dir, broken_dir)
    return _inner_execute_direct(
        args=args,
        command_key=command_key,
        default_timeout=default_timeout,
        project_dir=project_dir,
        env_vars=env_vars,
        working_dir=working_dir,
    )


def cmd_run(args) -> int:
    project_dir = getattr(args, 'project_dir', '.')
    command_args = args.command_args
    key_suffix = _CONFIG.command_key_fn(command_args)
    command_key = f'{_CONFIG.tool_name}:{key_suffix}'
    timeout_seconds = getattr(args, 'timeout', None) or _CONFIG.default_timeout
    result = execute_direct(
        args=command_args,
        command_key=command_key,
        default_timeout=timeout_seconds,
        project_dir=project_dir,
    )
    return cmd_run_common(
        result=result,
        parser_fn=parse_log,
        tool_name=_CONFIG.tool_name,
        output_format=getattr(args, 'format', 'toon'),
        mode=getattr(args, 'mode', 'actionable'),
        project_dir=project_dir,
        parser_needs_command=_CONFIG.parser_needs_command,
        plan_id=getattr(args, 'plan_id', None),
    )


execute_direct.__qualname__ = 'python_execute_direct'
cmd_run.__qualname__ = 'python_cmd_run'
