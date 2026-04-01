#!/usr/bin/env python3
"""Factory for build-system-specific execute_direct and cmd_run functions.

Eliminates duplication between Maven and Gradle execute modules by extracting
the common pattern: detect_wrapper → scope_fn → build_command_fn → execute_direct_base.

Each build system provides a config dataclass; the factory returns ready-to-use
execute_direct() and cmd_run() functions.

Usage:
    from _build_execute_factory import ExecuteConfig, create_execute_handlers

    config = ExecuteConfig(
        tool_name='maven',
        unix_wrapper='mvnw',
        windows_wrapper='mvnw.cmd',
        system_fallback='mvn',
        capture_strategy=CaptureStrategy.MAVEN_LOG_FLAG,
        scope_fn=_maven_scope_fn,
        build_command_fn=_maven_build_command_fn,
        default_timeout=300,
    )

    execute_direct, cmd_run = create_execute_handlers(config, parse_log)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from _build_execute import BuildCommandFn, CaptureStrategy, ScopeFn, execute_direct_base
from _build_result import DirectCommandResult
from _build_shared import cmd_run_common
from _build_wrapper import detect_wrapper as _detect_wrapper


@dataclass(frozen=True)
class ExecuteConfig:
    """Configuration for a build system's execution layer."""

    tool_name: str
    """Build system name (e.g., 'maven', 'gradle'). Used for logging and command keys."""

    unix_wrapper: str
    """Unix wrapper filename (e.g., 'mvnw', 'gradlew')."""

    windows_wrapper: str
    """Windows wrapper filename (e.g., 'mvnw.cmd', 'gradlew.bat')."""

    system_fallback: str
    """System command when no wrapper exists (e.g., 'mvn', 'gradle')."""

    capture_strategy: CaptureStrategy
    """How output is captured to log file."""

    build_command_fn: BuildCommandFn
    """Constructs the tool-specific command line: (wrapper, args, log_file) -> (cmd_parts, command_str)."""

    scope_fn: ScopeFn
    """Extracts scope from command args for log file scoping: (args) -> scope string."""

    command_key_fn: Callable[[str], str]
    """Extracts command key suffix from command args: (args) -> key string.
    E.g., for Maven: 'clean verify -pl core' -> 'clean' -> key='maven:clean'."""

    default_timeout: int = 300
    """Default timeout in seconds if no learned value exists."""

    extra_result_fields: dict = field(default_factory=dict)
    """Additional fields to include in all result dicts."""


def create_execute_handlers(
    config: ExecuteConfig,
    parse_log_fn: Callable,
) -> tuple[Callable[..., DirectCommandResult], Callable]:
    """Create execute_direct() and cmd_run() functions from config.

    Args:
        config: Build system execution configuration.
        parse_log_fn: Parser function for build output logs.

    Returns:
        Tuple of (execute_direct, cmd_run) functions.
    """

    def detect_wrapper(project_dir: str = '.') -> str:
        wrapper = _detect_wrapper(project_dir, config.unix_wrapper, config.windows_wrapper, config.system_fallback)
        return wrapper or config.system_fallback

    def execute_direct(
        args: str, command_key: str, default_timeout: int = config.default_timeout, project_dir: str = '.'
    ) -> DirectCommandResult:
        wrapper = detect_wrapper(project_dir)
        return execute_direct_base(
            args=args,
            command_key=command_key,
            default_timeout=default_timeout,
            project_dir=project_dir,
            tool_name=config.tool_name,
            build_command_fn=config.build_command_fn,
            wrapper=wrapper,
            capture_strategy=config.capture_strategy,
            scope_fn=config.scope_fn,
            extra_result_fields=config.extra_result_fields or None,
        )

    def cmd_run(args) -> int:
        project_dir = getattr(args, 'project_dir', '.')
        command_args = args.command_args
        key_suffix = config.command_key_fn(command_args)
        command_key = f'{config.tool_name}:{key_suffix}'
        timeout_seconds = getattr(args, 'timeout', None) or config.default_timeout

        result = execute_direct(
            args=command_args, command_key=command_key, default_timeout=timeout_seconds, project_dir=project_dir
        )

        return cmd_run_common(
            result=result,
            parser_fn=parse_log_fn,
            tool_name=config.tool_name,
            output_format=getattr(args, 'format', 'toon'),
            mode=getattr(args, 'mode', 'actionable'),
            project_dir=project_dir,
        )

    # Preserve useful names for debugging
    execute_direct.__qualname__ = f'{config.tool_name}_execute_direct'
    cmd_run.__qualname__ = f'{config.tool_name}_cmd_run'

    return execute_direct, cmd_run
