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

import importlib.util  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402
from argparse import Namespace  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

from _build_execute import BuildCommandFn, CaptureStrategy, ScopeFn, execute_direct_base  # noqa: E402
from _build_execute import detect_wrapper as _detect_wrapper  # noqa: E402
from _build_queue_slot import BuildQueueTimeout, build_queue_slot  # noqa: E402
from _build_result import (  # noqa: E402
    ERROR_BUILD_FAILED,
    DirectCommandResult,
    error_result,
    success_result,
    timeout_result,
)
from _build_server_protocol import MARSHALLD_JOB_ENV  # noqa: E402
from _build_shared import cmd_run_common  # noqa: E402
from toon_parser import serialize_toon  # noqa: E402

# Error type emitted when the build queue is saturated past max_retries.
ERROR_QUEUE_SATURATED = 'queue_saturated'

# Error type emitted when execution_mode=daemon is requested but the build
# cannot be routed to the marshalld daemon (a genuine unavailability, an
# unroutable tool, or an env/working-dir override the daemon cannot honour).
# In daemon mode this is a hard failure, NOT a silent in-process fallback.
ERROR_DAEMON_REQUIRED = 'daemon_required'

# ---------------------------------------------------------------------------
# marshalld build-execute routing seam (D5)
# ---------------------------------------------------------------------------
# A build is routed to the marshalld daemon when the project is registered AND
# the daemon answers a verified handshake ("ready"); otherwise it runs in-process
# under a single machine-global build-queue slot (the fallback). A build takes
# EXACTLY ONE limiter path — never both, never stacked: a routed build's slot is
# held by the daemon child (which re-runs the executor in-process, acquiring the
# shared machine-global slot itself), so the routing seam takes no fallback slot.

# tool_name -> the executor notation the daemon re-runs (command[2], verified
# against the project's notation_allowlist by the daemon's S1 check). An unknown
# tool has no notation and never routes (safe in-process fallback).
_TOOL_NOTATIONS = {
    'maven': 'plan-marshall:build-maven:maven',
    'gradle': 'plan-marshall:build-gradle:gradle',
    'npm': 'plan-marshall:build-npm:npm',
    'python': 'plan-marshall:build-pyproject:pyproject_build',
}


def routable_notations() -> tuple[str, ...]:
    """Return the sorted executor notations the daemon may re-run.

    The single source of truth for the "which builds route" set: the sorted
    values of :data:`_TOOL_NOTATIONS`. Registration derives its default
    ``notation_allowlist`` from this accessor, so a newly-added build tool
    becomes routable AND default-allowlisted from one edit, with no drift —
    without importing the private ``_TOOL_NOTATIONS`` name across modules.

    Returns:
        The sorted notation tuple.
    """
    return tuple(sorted(_TOOL_NOTATIONS.values()))

# build_server.py (the build-server-client verbs) is NOT an executor-registered
# notation reachable from this build subprocess's PYTHONPATH, so it is reused as
# the single owner of the submit/wait/preflight contract via an in-process
# file-path import, mirroring _build_queue_slot._load_build_queue. The sibling
# scripts dirs it imports transitively are ensured on sys.path before the exec.
_FACTORY_DIR = Path(__file__).resolve().parent
_BUILD_SERVER_CLIENT_PATH = (
    _FACTORY_DIR.parent.parent.parent / 'build-server-client' / 'scripts' / 'build_server.py'
)
_BUILD_SERVER_DEP_DIRS: tuple[Path, ...] = (
    _BUILD_SERVER_CLIENT_PATH.parent,                                   # build_server itself
    _FACTORY_DIR,                                                       # _build_server_protocol/_registry
    _FACTORY_DIR.parent,                                               # marketplace_paths, worktree_sha
    _FACTORY_DIR.parent / 'workflow',                                  # triage_helpers
    _FACTORY_DIR.parent.parent.parent / 'manage-change-ledger' / 'scripts',  # _ledger_core
)

# Lazily-imported build_server client module (file-path import; see below).
_build_server_mod: Any = None


def _load_build_server() -> Any:
    """Import the sibling ``build_server.py`` client by file path (cached).

    Mirrors ``_build_queue_slot._load_build_queue``: the client is reused as the
    single owner of the submit/wait/preflight contract via an in-process
    file-path import rather than a subprocess, with its transitive sibling
    ``scripts`` dirs ensured on ``sys.path`` first (a file-path import does not
    carry them).
    """
    global _build_server_mod
    if _build_server_mod is not None:
        return _build_server_mod
    for dep_dir in _BUILD_SERVER_DEP_DIRS:
        dep_str = str(dep_dir)
        if dep_dir.is_dir() and dep_str not in sys.path:
            sys.path.insert(0, dep_str)
    spec = importlib.util.spec_from_file_location('build_server', _BUILD_SERVER_CLIENT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load build_server from {_BUILD_SERVER_CLIENT_PATH}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _build_server_mod = module
    return module


def _resolve_notation(config: ExecuteConfig) -> str:
    """Resolve the executor notation the daemon re-runs for ``config``.

    An explicit ``config.notation`` wins; otherwise it is looked up by
    ``tool_name``. An empty result means "do not route" — the build runs
    in-process (the safe default for an unknown build tool).
    """
    return config.notation or _TOOL_NOTATIONS.get(config.tool_name, '')


def _daemon_result_to_direct(waited: dict[str, Any], command_str: str) -> DirectCommandResult:
    """Map a client ``wait`` status-TOON to a ``DirectCommandResult``.

    The daemon's terminal job statuses (``success|failure|timeout|killed``) are
    rendered into the shared build-result shape so the routed build flows through
    the SAME ``cmd_run_common`` rendering/parse path as an in-process build. A
    ``killed`` job carries the no-blind-retry message so a harness reap on the
    daemon side is never mistaken for a flaky build.
    """
    job_status = str(waited.get('job_status', ''))
    log_file = str(waited.get('log_file', '') or '')
    duration = int(waited.get('duration_seconds', 0) or 0)
    exit_code = int(waited.get('exit_code', 0) or 0)
    if job_status == 'success':
        return success_result(duration, log_file, command_str)  # type: ignore[return-value]
    if job_status == 'timeout':
        return timeout_result(duration, duration, log_file, command_str)  # type: ignore[return-value]
    result = error_result(
        'killed' if job_status == 'killed' else ERROR_BUILD_FAILED,
        exit_code or 1,
        duration,
        log_file,
        command_str,
    )
    if job_status == 'killed':
        result['error'] = 'killed'
        result['message'] = str(
            waited.get('message', 'externally killed — not flaky, do not blind-retry')
        )
    return result  # type: ignore[return-value]


def _route_to_daemon(
    config: ExecuteConfig, project_dir: str, plan_id: str | None
) -> tuple[DirectCommandResult | None, str]:
    """Route a build to marshalld when registered AND ready; else signal fallback.

    Returns ``(result, '')`` when the daemon ran the build to a terminal status
    (the caller renders that result and takes NO fallback slot). Returns
    ``(None, reason)`` when routing did not happen and the caller must build
    in-process, where ``reason`` names why: ``in_daemon_job`` (re-entrancy guard),
    ``no_notation`` (unroutable tool), or a preflight / submit / wait degradation
    reason (``disabled``, ``socket_absent``, ``not_registered``, …) that the
    caller records so the fallback is never silent.
    """
    # Re-entrancy guard: a build already running INSIDE a marshalld job child
    # never routes back to the daemon (that would recurse without bound).
    if os.environ.get(MARSHALLD_JOB_ENV):
        return None, 'in_daemon_job'

    notation = _resolve_notation(config)
    if not notation:
        return None, 'no_notation'

    client = _load_build_server()
    exec_root = str(Path(project_dir).resolve())
    preflight = client.run_preflight(Namespace(project_path=exec_root))
    if preflight.get('preflight') != 'ready':
        # disabled (unregistered — no daemon probe) or down + reason → fallback.
        return None, str(preflight.get('reason') or preflight.get('preflight') or 'unavailable')

    # Reconstruct the executor-form command the daemon re-runs from THIS build
    # process's own argv tail — argv[0] is the build script path, argv[1:] is the
    # `run --command-args "<args>" [flags…]` the executor invoked us with.
    command = ['python3', str(Path(exec_root) / '.plan' / 'execute-script.py'), notation, *sys.argv[1:]]
    command_str = ' '.join(command)

    submit = client.run_submit(
        Namespace(
            command=json.dumps(command),
            exec_path=exec_root,
            project_path=exec_root,
            plan_id=plan_id or '',
        )
    )
    if submit.get('status') != 'success':
        # refused (verifier) or degraded (unreachable) → in-process fallback.
        return None, str(submit.get('reason') or submit.get('status') or 'submit_failed')

    job_id = str(submit.get('job_id', ''))
    # Bounded long-poll: re-issue wait on a live `running` return — NEVER sleep
    # or background the wait (a reaped wait costs one re-poll, not the build).
    while True:
        waited = client.run_wait(Namespace(job_id=job_id, plan_id=plan_id or '', bound=None))
        if waited.get('status') == 'degraded':
            return None, str(waited.get('reason') or 'wait_degraded')
        if str(waited.get('job_status', '')) == 'running':
            continue
        return _daemon_result_to_direct(waited, command_str), ''


def _emit_error_envelope(output_format: str, output: dict) -> int:
    """Serialize and print a pre-built error envelope; always returns exit 1.

    Shared print/serialize tail for the build-execute error emitters below —
    the generic TOON/JSON serializer, not the build-result formatter (which
    filters to known build fields and would drop emitter-specific keys like
    ``max_retries`` or ``reason``).
    """
    if output_format == 'json':
        print(json.dumps(output, indent=2))
    else:
        print(serialize_toon(output))
    return 1


def _emit_queue_timeout(tool_name: str, command_args: str, output_format: str, exc: BuildQueueTimeout) -> int:
    """Render a structured 'try again later' error when no slot was admitted.

    The build never ran — the queue stayed saturated past ``max_retries`` — so
    this returns an exit code of 1 (the build did not complete) and prints an
    error envelope the orchestrator can branch on without a log file.
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
    return _emit_error_envelope(output_format, output)


def _emit_daemon_required(
    tool_name: str,
    command_args: str,
    output_format: str,
    reason: str,
    notation: str,
    plan_id: str | None,
) -> int:
    """Render a loud error envelope when ``execution_mode=daemon`` cannot route.

    In ``daemon`` mode the caller demands that the marshalld daemon run the
    build; a genuine unavailability (daemon down, unregistered, an unroutable
    tool, or a build carrying an env / working-dir override the daemon's clean
    baseline cannot honour) is a HARD failure, never a silent in-process
    fallback. The build was not run, so this returns exit 1 and prints an error
    envelope the orchestrator can branch on. Records the requested-vs-resolved
    audit line (resolved=fail-loud) before emitting.
    """
    logger.info(
        '[BUILD-SERVER] resolved build (requested=daemon, resolved=fail-loud, reason=%s, notation=%s, plan=%s)',
        reason, notation, plan_id,
    )
    output = {
        'status': 'error',
        'error': ERROR_DAEMON_REQUIRED,
        'message': (
            f'execution_mode=daemon requires the marshalld daemon to run this build, '
            f'but routing was unavailable (reason={reason}). The build was not run in-process.'
        ),
        'tool': tool_name,
        'command': command_args,
        'reason': reason,
        'plan_id': plan_id or '',
    }
    return _emit_error_envelope(output_format, output)


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

    notation: str = ''
    """Executor notation the marshalld daemon re-runs for this build (D5 routing).

    When empty it is resolved by ``tool_name`` (:data:`_TOOL_NOTATIONS`); an
    unresolvable tool never routes and always builds in-process. Set explicitly
    to override the tool-name lookup (e.g. in tests, or for a custom build tool
    the daemon should serve)."""

    extra_result_fields: dict = field(default_factory=dict)
    """Static extra fields added to all results. For per-invocation dynamic fields, use extra_result_fn."""

    wrapper_resolve_fn: Callable[[str], str] | None = None
    """Custom wrapper resolution: (project_dir) -> wrapper path.
    If set, overrides the default detect_wrapper logic. Useful for tools
    like npm that don't have wrappers, or Python where FileNotFoundError
    needs early detection."""

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

    def _resolve_wrapper(project_dir: str = '.') -> str:
        # npm-style configs keep their custom resolve_fn (no wrapper concept,
        # returns 'npm' unconditionally).
        if config.wrapper_resolve_fn:
            return config.wrapper_resolve_fn(project_dir)
        # Prefer the project wrapper; fall back to the system binary when absent.
        wrapper = _detect_wrapper(
            project_dir,
            config.unix_wrapper,
            config.windows_wrapper,
            config.system_fallback,
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
        wrapper = _resolve_wrapper(project_dir)

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

        plan_id = getattr(args, 'plan_id', None)
        execution_mode = getattr(args, 'execution_mode', 'auto')
        notation = _resolve_notation(config)

        # A build carrying a client-forwarded env or a working-dir override can
        # NEVER be routed: the daemon's S2 clean-baseline env cannot honour it.
        daemon_incompatible = env_vars is not None or working_dir is not None

        # D5 routing seam, gated by the explicit ``execution_mode``:
        #   auto        — route to marshalld when registered AND the daemon
        #                 answers a verified handshake; otherwise fall back
        #                 in-process (recording the degradation reason). This is
        #                 the exact historical behaviour.
        #   in_process  — never attempt to route; always build in-process (no
        #                 preflight / submit attempt).
        #   daemon      — require the daemon; a genuine unavailability is a hard
        #                 fail-loud (ERROR_DAEMON_REQUIRED, exit 1), never a
        #                 silent in-process fallback. The sole exception is
        #                 ``in_daemon_job`` — this process IS the daemon child
        #                 re-running the build and MUST proceed in-process.
        #
        # A routed build takes NO fallback slot (the daemon child holds the
        # single machine-global slot), so a build takes exactly one limiter
        # path, never stacked. ``fallback_reason`` carries the degradation
        # reason (or None) into the single resolved=in_process audit line.
        fallback_reason: str | None = None
        if execution_mode == 'daemon' and daemon_incompatible:
            # Requested daemon, but the build carries env / working-dir the
            # daemon cannot honour — fail loud instead of falling back.
            return _emit_daemon_required(
                config.tool_name, command_args, getattr(args, 'format', 'toon'),
                'env_or_working_dir_set', notation, plan_id,
            )
        if execution_mode == 'auto' and daemon_incompatible:
            # auto mode carrying env / working-dir the daemon cannot honour:
            # never attempt to route (the routing guard below is False), and
            # record the degradation reason so the in-process fallback is not
            # silent. The literal matches the daemon-required fail-loud path's
            # own reason for the identical condition.
            fallback_reason = 'env_or_working_dir_set'
        if execution_mode != 'in_process' and not daemon_incompatible:
            routed, reason = _route_to_daemon(config, project_dir, plan_id)
            if routed is not None:
                logger.info(
                    '[BUILD-SERVER] resolved build (requested=%s, resolved=routed, notation=%s, plan=%s)',
                    execution_mode, notation, plan_id,
                )
                return cmd_run_common(
                    result=routed,
                    parser_fn=parse_log_fn,
                    tool_name=config.tool_name,
                    output_format=getattr(args, 'format', 'toon'),
                    mode=getattr(args, 'mode', 'actionable'),
                    project_dir=project_dir,
                    parser_needs_command=config.parser_needs_command,
                    plan_id=plan_id,
                )
            # Routing did not happen; ``reason`` names why. In daemon mode a
            # genuine unavailability is fatal — the sole in-process exception is
            # ``in_daemon_job`` (this process IS the daemon child).
            if execution_mode == 'daemon' and reason != 'in_daemon_job':
                return _emit_daemon_required(
                    config.tool_name, command_args, getattr(args, 'format', 'toon'),
                    reason, notation, plan_id,
                )
            # auto (or the daemon child): record the degradation reason so the
            # in-process fallback is never silent (a bare re-entrancy /
            # unroutable-tool skip is not a degradation and is not recorded).
            if reason not in ('in_daemon_job', 'no_notation'):
                fallback_reason = reason

        # Resolved to an in-process build (explicit in_process, auto fallback,
        # or the daemon child). Record the requested-vs-resolved audit line.
        logger.info(
            '[BUILD-SERVER] resolved build (requested=%s, resolved=in_process, reason=%s, notation=%s, plan=%s)',
            execution_mode, fallback_reason, notation, plan_id,
        )

        # In-process fallback: acquire a build-queue slot on the single
        # machine-global queue file when a plan_id is set; NO-OP passthrough
        # otherwise (plan-less builds run unchanged). The slot is released in the
        # context manager's finally.
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
            plan_id=plan_id,
        )

    # Preserve useful names for debugging
    execute_direct.__qualname__ = f'{config.tool_name}_execute_direct'
    cmd_run.__qualname__ = f'{config.tool_name}_cmd_run'

    return execute_direct, cmd_run
