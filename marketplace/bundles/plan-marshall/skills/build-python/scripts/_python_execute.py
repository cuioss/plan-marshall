#!/usr/bin/env python3
"""Python/pyprojectx command execution — config-driven via execute handler factory.

Provides:
- execute_direct(): Foundation API for pyprojectx command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)

Usage:
    from _python_execute import execute_direct, cmd_run
"""

from _build_execute import CaptureStrategy
from _build_execute_factory import ExecuteConfig, create_execute_handlers
from _build_shared import DEFAULT_BUILD_TIMEOUT
from _build_wrapper import detect_wrapper as _detect_wrapper
from _python_cmd_parse import parse_log


def _python_build_command_fn(wrapper: str, args: str, log_file: str) -> tuple[list[str], str]:
    """Build pyprojectx command."""
    cmd_parts = [wrapper] + args.split()
    command_str = ' '.join(cmd_parts)
    return cmd_parts, command_str


def _python_command_key_fn(command_args: str) -> str:
    """Extract command key suffix from pyprojectx args."""
    return command_args.split()[0].replace(' ', '_').replace('-', '_') if command_args else 'default'


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
    build_command_fn=_python_build_command_fn,
    scope_fn=_python_scope_fn,
    command_key_fn=_python_command_key_fn,
    default_timeout=DEFAULT_BUILD_TIMEOUT,
    wrapper_resolve_fn=_python_wrapper_resolve_fn,
    extra_result_fn=_python_extra_result_fn,
)

execute_direct, cmd_run = create_execute_handlers(_CONFIG, parse_log)
