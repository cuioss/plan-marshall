#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
        capture_strategy=CaptureStrategy.TOOL_LOG_FLAG,
        scope_fn=_maven_scope_fn,
        build_command_fn=_maven_build_command_fn,
        default_timeout=300,
    )

    execute_direct, cmd_run = create_execute_handlers(config, parse_log)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

import json  # noqa: E402
from pathlib import Path  # noqa: E402

from _build_execute import BuildCommandFn, CaptureStrategy, ScopeFn, execute_direct_base  # noqa: E402
from _build_execute import detect_wrapper as _detect_wrapper  # noqa: E402
from _build_queue_slot import BuildQueueTimeout, build_queue_slot  # noqa: E402
from _build_result import DirectCommandResult  # noqa: E402
from _build_shared import cmd_run_common  # noqa: E402
from file_ops import get_marshal_path, read_json  # type: ignore[import-not-found]  # noqa: E402
from toon_parser import serialize_toon  # type: ignore[import-not-found]  # noqa: E402

# Error type emitted when the build queue is saturated past max_retries.
ERROR_QUEUE_SATURATED = 'queue_saturated'


def _emit_queue_timeout(tool_name: str, command_args: str, output_format: str, exc: BuildQueueTimeout) -> int:
    """Render a structured 'try again later' error when no slot was admitted.

    The build never ran — the queue stayed saturated past ``max_retries`` — so
    this returns an exit code of 1 (the build did not complete) and prints an
    error envelope the orchestrator can branch on without a log file. The
    envelope is serialized with the generic TOON/JSON serializer (not the
    build-result formatter, which filters to known build fields and would drop
    the queue-specific ``message`` / ``plan_id`` / ``max_retries`` keys).
    """
    output = {
        'status': 'error',
        'error': ERROR_QUEUE_SATURATED,
        'message': str(exc),
        'tool': tool_name,
        'command': command_args,
        'max_retries': exc.max_retries,
        'plan_id': exc.plan_id,
    }
    if output_format == 'json':
        print(json.dumps(output, indent=2))
    else:
        print(serialize_toon(output))
    return 1


def default_command_key_fn(command_args: str) -> str:
    """Scope-aware command key: full args normalized to underscores.

    Prevents run-config key collisions between full-scope and
    module-scoped invocations (e.g., 'module-tests' vs
    'module-tests plan-marshall'), so adaptive timeouts learn
    per-scope values.

    Works for Maven goals, npm scripts, and pyprojectx commands.
    Gradle should override to strip leading colons.
    """
    if command_args is not None:
        tokens = command_args.strip().split()
        if tokens:
            return '_'.join(tokens).replace('-', '_')
    return 'default'


def default_build_command_fn(wrapper: str, args: str, log_file: str) -> tuple[list[str], str]:
    """Default build command: [wrapper] + args.split().

    Suitable for tools that use STDOUT_REDIRECT capture (e.g., pyprojectx).
    Tools with special flags (Maven -l, Gradle --console=plain) should override.
    """
    cmd_parts = [wrapper] + args.split()
    command_str = ' '.join(cmd_parts)
    return cmd_parts, command_str


def _resolve_marshal_path(project_dir: str) -> Path:
    """Resolve marshal.json honouring ``project_dir`` (the resolved tree).

    The override is read in-process BEFORE the build subprocess is spawned, so
    ``get_marshal_path()``'s cwd walk-up is not guaranteed to land on the build's
    tree. Walk up from ``project_dir`` to the nearest ancestor carrying a
    ``.plan/marshal.json`` so a worktree's marshal.json is honoured (NOT main's);
    fall back to ``get_marshal_path()`` (cwd walk-up) when no such ancestor exists.
    """
    try:
        root = Path(project_dir).resolve()
    except (OSError, ValueError):
        return get_marshal_path()
    for candidate in (root, *root.parents):
        marshal = candidate / '.plan' / 'marshal.json'
        if marshal.is_file():
            return marshal
    return get_marshal_path()


def _read_require_wrapper_override(tool_name: str, project_dir: str, default: bool) -> bool:
    """Read ``build.{tool_name}.require_wrapper`` from marshal.json.

    Mirrors ``_build_queue_slot._resolve_max_retries``'s graceful degradation: a
    missing file, missing ``build`` block, missing ``build.{tool_name}`` block,
    missing ``require_wrapper`` key, or a non-bool value all degrade to
    ``default`` (the per-build-system static ``ExecuteConfig.require_wrapper``).
    This is the operator escape valve a consumer repo lacking a checked-in
    wrapper sets to ``false`` WITHOUT editing marketplace code.
    """
    config = read_json(_resolve_marshal_path(project_dir), default={})
    if not isinstance(config, dict):
        return default
    build = config.get('build')
    if not isinstance(build, dict):
        return default
    block = build.get(tool_name)
    if not isinstance(block, dict):
        return default
    raw = block.get('require_wrapper')
    if not isinstance(raw, bool):
        return default
    return raw


@dataclass(frozen=True)
class ExecuteConfig:
    """Configuration for a build system's execution layer."""

    tool_name: str
    """Build system name (e.g., 'maven', 'gradle'). Used for logging and command keys."""

    unix_wrapper: str
    """Unix wrapper filename (e.g., 'mvnw', 'gradlew'). Empty string if no wrapper (e.g., npm)."""

    windows_wrapper: str
    """Windows wrapper filename (e.g., 'mvnw.cmd', 'gradlew.bat'). Empty string if no wrapper."""

    system_fallback: str
    """System command when no wrapper exists (e.g., 'mvn', 'gradle', 'npm')."""

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
    """Static extra fields added to all results. For per-invocation dynamic fields, use extra_result_fn."""

    wrapper_resolve_fn: Callable[[str], str] | None = None
    """Custom wrapper resolution: (project_dir) -> wrapper path.
    If set, overrides the default detect_wrapper logic. Useful for tools
    like npm that don't have wrappers, or Python where FileNotFoundError
    needs early detection."""

    require_wrapper: bool = False
    """When True, a build whose project provides a wrapper concept MUST find
    that wrapper; the factory's ``_resolve_wrapper`` raises ``FileNotFoundError``
    rather than falling back to ``system_fallback``. Default False preserves the
    historical system-fallback behaviour. Per-build-system static default;
    overridable per build system in marshal.json via
    ``build.{tool_name}.require_wrapper``."""

    parser_needs_command: bool = False
    """If True, passes the command string as second arg to parser_fn."""

    supports_env_vars: bool = False
    """If True, execute_direct() accepts env_vars kwarg and cmd_run() reads args.env."""

    supports_working_dir: bool = False
    """If True, execute_direct() accepts working_dir kwarg and cmd_run() reads args.working_dir."""

    extra_result_fn: Callable[[str, str], dict] | None = None
    """Dynamic extra result fields: (args, wrapper) -> dict of additional fields.
    Called per invocation, unlike extra_result_fields which is static.
    E.g., npm uses this to add command_type based on args."""


def compute_command_key(config: ExecuteConfig, command_args: str) -> str:
    """Compute the canonical run-config key for a build invocation.

    Returns ``f'{config.tool_name}:{config.command_key_fn(command_args)}'`` —
    the exact same key that ``cmd_run`` constructs at execute time (see
    ``create_execute_handlers.cmd_run`` below). Exposed as a pure helper so
    callers outside the execute path (e.g., the ``run-config-key`` CLI
    subcommand on each build skill, ``architecture resolve``'s adaptive
    timeout lookup) can derive the canonical key without re-implementing
    the construction and risking drift between learning and lookup.
    """
    key_suffix = config.command_key_fn(command_args)
    return f'{config.tool_name}:{key_suffix}'


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

    def _resolve_wrapper(project_dir: str = '.', require_wrapper: bool = False) -> str:
        # npm-style configs keep their custom resolve_fn (no wrapper concept,
        # returns 'npm' unconditionally) — the gate never applies to them.
        if config.wrapper_resolve_fn:
            return config.wrapper_resolve_fn(project_dir)
        # When require_wrapper is True, pass None as system_fallback so detection
        # never resolves to a PATH binary — a missing wrapper returns falsy and
        # the gate below raises instead of falling through to system mvn/gradle.
        wrapper = _detect_wrapper(
            project_dir,
            config.unix_wrapper,
            config.windows_wrapper,
            None if require_wrapper else config.system_fallback,
        )
        if require_wrapper and not wrapper:
            raise FileNotFoundError(
                f'No {config.tool_name} wrapper found ({config.unix_wrapper} or {config.windows_wrapper})'
            )
        return wrapper or config.system_fallback

    def execute_direct(
        args: str,
        command_key: str,
        default_timeout: int = config.default_timeout,
        project_dir: str = '.',
        env_vars: dict[str, str] | None = None,
        working_dir: str | None = None,
    ) -> DirectCommandResult:
        # config.tool_name is 'python' for pyproject builds, but the documented
        # marshal.json override key is build.pyproject.require_wrapper. Map
        # 'python' -> 'pyproject' so the override lookup matches the documented
        # config structure (CodeRabbit finding 75ab08).
        override_tool = 'pyproject' if config.tool_name == 'python' else config.tool_name
        effective_require = _read_require_wrapper_override(override_tool, project_dir, config.require_wrapper)
        try:
            wrapper = _resolve_wrapper(project_dir, effective_require)
        except FileNotFoundError as e:
            return {
                'status': 'error',
                'exit_code': -1,
                'duration_seconds': 0,
                'log_file': '',
                'command': f'{config.system_fallback} {args}',
                'error': str(e),
            }

        # Compute dynamic extra fields
        extras = dict(config.extra_result_fields) if config.extra_result_fields else {}
        if config.extra_result_fn:
            extras.update(config.extra_result_fn(args, wrapper))

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
            env_vars=env_vars,
            working_dir=working_dir,
            extra_result_fields=extras or None,
        )

    def cmd_run(args) -> int:
        project_dir = getattr(args, 'project_dir', '.')
        command_args = args.command_args
        command_key = compute_command_key(config, command_args)
        timeout_seconds = getattr(args, 'timeout', None) or config.default_timeout

        # Optional env_vars support
        env_vars = None
        if config.supports_env_vars:
            env_str = getattr(args, 'env', None)
            if env_str:
                env_vars = {}
                for env_pair in env_str.split():
                    if '=' in env_pair:
                        key, value = env_pair.split('=', 1)
                        env_vars[key] = value
                    else:
                        logger.warning('Skipping malformed env var (missing =): %s', env_pair)

        # Optional working_dir support
        working_dir = getattr(args, 'working_dir', None) if config.supports_working_dir else None

        # Acquire a build-queue slot when a plan_id is set; NO-OP passthrough
        # otherwise (plan-less builds run unchanged). The slot is released and
        # the title-token cleared in the context manager's finally.
        plan_id = getattr(args, 'plan_id', None)
        try:
            with build_queue_slot(plan_id):
                result = execute_direct(
                    args=command_args,
                    command_key=command_key,
                    default_timeout=timeout_seconds,
                    project_dir=project_dir,
                    env_vars=env_vars,
                    working_dir=working_dir,
                )
        except BuildQueueTimeout as exc:
            return _emit_queue_timeout(config.tool_name, command_args, getattr(args, 'format', 'toon'), exc)

        return cmd_run_common(
            result=result,
            parser_fn=parse_log_fn,
            tool_name=config.tool_name,
            output_format=getattr(args, 'format', 'toon'),
            mode=getattr(args, 'mode', 'actionable'),
            project_dir=project_dir,
            parser_needs_command=config.parser_needs_command,
            plan_id=getattr(args, 'plan_id', None),
        )

    # Preserve useful names for debugging
    execute_direct.__qualname__ = f'{config.tool_name}_execute_direct'
    cmd_run.__qualname__ = f'{config.tool_name}_cmd_run'

    return execute_direct, cmd_run
