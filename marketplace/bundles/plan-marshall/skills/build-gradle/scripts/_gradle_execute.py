#!/usr/bin/env python3
"""Gradle command execution — config-driven via execute handler factory.

Provides:
- execute_direct(): Foundation API for Gradle command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)

Usage:
    from _gradle_execute import execute_direct, cmd_run
"""

import re

from _build_execute import CaptureStrategy
from _build_execute_factory import ExecuteConfig, create_execute_handlers
from _build_shared import DEFAULT_BUILD_TIMEOUT
from _gradle_cmd_parse import parse_log


def _gradle_scope_fn(args: str) -> str:
    """Extract scope from Gradle task arguments.

    Handles both ':module:task' prefix and '-p path' syntax.
    """
    # Check :module:task format
    if args.startswith(':'):
        parts = args.split(':')
        if len(parts) >= 2 and parts[1]:
            return parts[1]
    # Check -p path format
    match = re.search(r'-p\s+(\S+)', args)
    if match:
        return match.group(1).rstrip('/').split('/')[-1]
    return 'default'


def _gradle_build_command_fn(wrapper: str, args: str, log_file: str) -> tuple[list[str], str]:
    """Build Gradle command with --console=plain for parseable output."""
    cmd_parts = [wrapper] + args.split() + ['--console=plain']
    command_str = ' '.join(cmd_parts)
    return cmd_parts, command_str


def _gradle_command_key_fn(command_args: str) -> str:
    """Extract command key suffix from Gradle args (first task, normalized to underscores)."""
    first_task = command_args.split()[0] if command_args else 'default'
    return first_task.lstrip(':').replace(':', '_').replace('-', '_')


_CONFIG = ExecuteConfig(
    tool_name='gradle',
    unix_wrapper='gradlew',
    windows_wrapper='gradlew.bat',
    system_fallback='gradle',
    capture_strategy=CaptureStrategy.STDOUT_REDIRECT,
    build_command_fn=_gradle_build_command_fn,
    scope_fn=_gradle_scope_fn,
    command_key_fn=_gradle_command_key_fn,
    default_timeout=DEFAULT_BUILD_TIMEOUT,
)

execute_direct, cmd_run = create_execute_handlers(_CONFIG, parse_log)
