#!/usr/bin/env python3
"""npm command execution — config-driven via execute handler factory.

Provides:
- execute_direct(): Foundation API for npm command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)

Usage:
    from _npm_execute import execute_direct, cmd_run, detect_command_type
"""

import re

from _build_execute import CaptureStrategy
from _build_execute_factory import ExecuteConfig, create_execute_handlers
from _build_shared import DEFAULT_BUILD_TIMEOUT
from _npm_cmd_parse import parse_log

# Commands that should use npx instead of npm (direct tool invocations)
NPX_COMMANDS = [
    'playwright', 'eslint', 'prettier', 'stylelint',  # linters/formatters
    'tsc', 'tsx', 'ts-node',  # TypeScript tools
    'jest', 'vitest', 'mocha',  # test runners
    'webpack', 'rollup', 'esbuild', 'vite',  # bundlers
    'babel',  # transpiler
]


def detect_command_type(args: str) -> str:
    """Detect whether to use npm or npx based on the command.

    Args:
        args: Command arguments.

    Returns:
        'npm' or 'npx'.
    """
    args_lower = args.lower().strip()
    for npx_cmd in NPX_COMMANDS:
        if args_lower.startswith(npx_cmd):
            return 'npx'
    return 'npm'


def _npm_scope_fn(args: str) -> str:
    """Extract scope from npm workspace or prefix arguments."""
    workspace_match = re.search(r'--workspace[=\s]+(\S+)', args)
    if workspace_match:
        return workspace_match.group(1)
    prefix_match = re.search(r'--prefix\s+(\S+)', args)
    if prefix_match:
        return prefix_match.group(1)
    return 'default'


def _npm_build_command_fn(wrapper: str, args: str, log_file: str) -> tuple[list[str], str]:
    """Build npm/npx command with dynamic command type detection."""
    command_type = detect_command_type(args)
    cmd_parts = [command_type] + args.split()
    command_str = ' '.join(cmd_parts)
    return cmd_parts, command_str


def _npm_command_key_fn(command_args: str) -> str:
    """Extract command key suffix from npm args."""
    return command_args.split()[0].replace(' ', '_').replace('-', '_') if command_args else 'default'


def _npm_wrapper_resolve_fn(project_dir: str) -> str:
    """npm doesn't need wrapper detection — return 'npm' as placeholder.

    The actual command (npm or npx) is determined per-invocation via
    build_command_fn's detect_command_type().
    """
    return 'npm'


def _npm_extra_result_fn(args: str, wrapper: str) -> dict:
    """Add command_type (npm or npx) to result based on args."""
    return {'command_type': detect_command_type(args)}


_CONFIG = ExecuteConfig(
    tool_name='npm',
    unix_wrapper='',
    windows_wrapper='',
    system_fallback='npm',
    capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
    build_command_fn=_npm_build_command_fn,
    scope_fn=_npm_scope_fn,
    command_key_fn=_npm_command_key_fn,
    default_timeout=DEFAULT_BUILD_TIMEOUT,
    wrapper_resolve_fn=_npm_wrapper_resolve_fn,
    parser_needs_command=True,
    supports_env_vars=True,
    supports_working_dir=True,
    extra_result_fn=_npm_extra_result_fn,
)

execute_direct, cmd_run = create_execute_handlers(_CONFIG, parse_log)
