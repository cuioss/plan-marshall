#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pyproject (Python/pyprojectx) command execution — config-driven via execute handler factory.

Provides:
- execute_direct(): Foundation API for pyprojectx command execution
- cmd_run(): Run subcommand handler (execute + auto-parse on failure)

pyproject routes through the SHARED factory ``cmd_run`` — the same
daemon-routing seam Maven, Gradle, and npm use — with the one-shot self-heal
applied to the in-process leg only (a routed build runs inside the daemon
child, which re-enters the factory and applies the self-heal there). A build
carrying ``--env`` or ``--working-dir`` is never routable: the daemon's clean
baseline environment cannot honour those overrides, so such a build falls back
in-process under ``auto`` and fails loud under ``execution_mode=daemon``.

The self-heal layer mitigates known worktree ``.pyprojectx``
cache-corruption symptoms: ``uv: command not found`` (exit 127) and
``Failed to create virtual environment ... Directory not empty``. On a
matching failure, the cache directory is renamed aside to
``.pyprojectx.broken`` and the command is re-run exactly once. The
self-heal is skipped when ``.pyprojectx.broken`` already exists so a prior
broken cache is never clobbered.

Usage:
    from _pyproject_execute import execute_direct, cmd_run
"""

import logging
from collections.abc import Callable
from pathlib import Path

from _build_execute import CaptureStrategy
from _build_execute_factory import (
    ExecuteConfig,
    create_execute_handlers,
    default_build_command_fn,
    default_command_key_fn,
)
from _build_result import DirectCommandResult
from _build_shared import DEFAULT_BUILD_TIMEOUT
from _pyproject_cmd_parse import parse_log

logger = logging.getLogger(__name__)


# Outer timeout floor (seconds) for pyprojectx builds. pytest runs its own
# per-test timeout backstop, configured under [tool.pytest.ini_options] in
# pyproject.toml. This outer floor MUST stay strictly greater than that inner
# backstop: if the outer wrapper timeout can expire first, it kills the run
# before pytest can report WHICH test hung, turning a diagnosable inner timeout
# into an opaque outer kill. See build-pyproject/standards/pyproject-impl.md
# § "Timeout bound ordering".
PYTEST_OUTER_FLOOR_SECONDS = 600


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
    min_timeout=PYTEST_OUTER_FLOOR_SECONDS,
    supports_env_vars=True,
    supports_working_dir=True,
    extra_result_fn=_python_extra_result_fn,
)

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


def _wrap_with_self_heal(
    inner_execute: Callable[..., DirectCommandResult],
) -> Callable[..., DirectCommandResult]:
    """Wrap the factory's inner executor with the one-shot self-heal retry.

    Applied via ``create_execute_handlers(..., wrap_execute_fn=...)`` so the
    self-heal rides the in-process leg of the shared routing ``cmd_run`` without
    pyproject forking a local ``cmd_run``. See the module docstring for the
    symptoms matched and the one-shot semantics.
    """

    def execute_direct(
        args: str,
        command_key: str,
        default_timeout: int = DEFAULT_BUILD_TIMEOUT,
        project_dir: str = '.',
        env_vars: dict[str, str] | None = None,
        working_dir: str | None = None,
    ) -> DirectCommandResult:
        result = inner_execute(
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
        return inner_execute(
            args=args,
            command_key=command_key,
            default_timeout=default_timeout,
            project_dir=project_dir,
            env_vars=env_vars,
            working_dir=working_dir,
        )

    return execute_direct


execute_direct, cmd_run = create_execute_handlers(
    _CONFIG, parse_log, wrap_execute_fn=_wrap_with_self_heal
)
