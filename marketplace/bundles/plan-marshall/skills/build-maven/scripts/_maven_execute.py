#!/usr/bin/env python3
"""Maven command execution — config-driven via execute handler factory.

Provides:
- execute_direct(): Foundation API for Maven command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)

Usage:
    from _maven_execute import execute_direct, cmd_run
"""

import re

from _build_execute import CaptureStrategy
from _build_execute_factory import ExecuteConfig, create_execute_handlers, default_command_key_fn
from _build_shared import DEFAULT_BUILD_TIMEOUT
from _maven_cmd_parse import parse_log


def _maven_scope_fn(args: str) -> str:
    """Extract scope from Maven -pl argument.

    Handles both '-pl module' and '-pl=module' forms.
    """
    match = re.search(r'-pl[=\s]+(\S+)', args)
    if match:
        return match.group(1)
    return 'default'


def _maven_build_command_fn(wrapper: str, args: str, log_file: str) -> tuple[list[str], str]:
    """Build Maven command with -l flag for log file output."""
    cmd_parts = [wrapper, '-l', log_file] + args.split()
    command_str = ' '.join(cmd_parts)
    return cmd_parts, command_str


_CONFIG = ExecuteConfig(
    tool_name='maven',
    unix_wrapper='mvnw',
    windows_wrapper='mvnw.cmd',
    system_fallback='mvn',
    capture_strategy=CaptureStrategy.TOOL_LOG_FLAG,
    build_command_fn=_maven_build_command_fn,
    scope_fn=_maven_scope_fn,
    command_key_fn=default_command_key_fn,
    default_timeout=DEFAULT_BUILD_TIMEOUT,
)

execute_direct, cmd_run = create_execute_handlers(_CONFIG, parse_log)
