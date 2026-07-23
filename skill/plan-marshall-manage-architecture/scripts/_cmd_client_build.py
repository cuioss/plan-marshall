#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Build-executable classification and execution-tier augmentation.

Extracted verbatim from ``_cmd_client``; the facade re-exports every public
name here so ``_cmd_client.<name>`` continues to resolve. Covers Bucket B
build-notation detection, build-skill ``_CONFIG`` loading, adaptive
bash-timeout lookup, and the four-field execution-tier augmentation consumed
by ``cmd_resolve`` / the deriver.
"""

import importlib.util
import shlex
from pathlib import Path
from typing import Any

from marketplace_bundles import (
    resolve_bundle_path,
    resolve_bundles_root,
)

# =============================================================================
# Build-executable classification (for resolve TOON augmentation)
# =============================================================================
#
# When ``cmd_resolve`` returns the executable for a build command (e.g., the
# ``verify`` command on a Python module resolves to
# ``python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build
# run --command-args "verify plan-marshall"``), the resolve TOON is augmented
# with four additional fields so the calling LLM can apply the correct Bash
# timeout and routing:
#
# * ``bash_timeout_seconds`` (int) — the recommended Bash-tool timeout in
#   seconds, computed as ``timeout_get(key, DEFAULT_BUILD_TIMEOUT) +
#   OUTER_TIMEOUT_BUFFER`` (the same arithmetic ``cmd_run`` performs).
# * ``exceeds_bash_ceiling`` (bool) — ``bash_timeout_seconds > 600``.
# * ``execution_tier`` — ``"per_task"`` when ``exceeds_bash_ceiling`` is
#   False, ``"orchestrator"`` when True.
# * ``hint`` — short pinned recognition phrase for the LLM:
#   ``"Bash timeout=<seconds*1000>ms"`` (per_task) or
#   ``"Exceeds Bash ceiling; orchestrator-tier only"`` (orchestrator).
#
# Non-build executables (Bucket A ``manage-*`` notations, raw shell invocations
# like ``./pw`` or ``grep``, etc.) cause classification to return ``None``;
# the four fields are omitted from the result and consumers fall back to
# today's behaviour. The threshold is computed from real measurements —
# nothing in this module hard-codes a list of "long-running" commands.

# Build-skill notations recognised as Bucket B build executables. The value
# is the ``tool_name`` configured on the corresponding skill's
# ``ExecuteConfig`` instance (``maven``, ``gradle``, ``npm``, ``python``);
# the same string forms the prefix of every key persisted by ``timeout_set``
# (e.g. ``python:verify_plan_marshall``).
_BUILD_NOTATIONS: dict[str, str] = {
    'plan-marshall:build-maven:maven': 'maven',
    'plan-marshall:build-gradle:gradle': 'gradle',
    'plan-marshall:build-npm:npm': 'npm',
    'plan-marshall:build-pyproject:pyproject_build': 'python',
}

# Bash tool's ``timeout`` parameter is capped by the host platform at 600s
# (10 minutes). Anything above this ceiling cannot be invoked synchronously
# from a sub-agent's Bash call without auto-backgrounding; the manifest
# composer routes such commands to phase_5.verification_steps (orchestrator
# tier) instead of emitting them as per-task verification.
_BASH_CEILING_SECONDS: int = 600

# Pinned recognition phrases — the numeric value the LLM needs is in
# ``bash_timeout_seconds``; the hint is a recognition token, not human prose.
_HINT_PER_TASK_TEMPLATE: str = 'Bash timeout={ms}ms'
_HINT_ORCHESTRATOR: str = 'Exceeds Bash ceiling; orchestrator-tier only'

# Marketplace bundle root, used to locate each build skill's ``_*_execute.py``
# module for ``_CONFIG`` import. Resolved via the validated bundles-root
# helper (identity walking, no index arithmetic) so the lookup honours
# version-pinned plugin-cache and worktree layouts.
_MARKETPLACE_BUNDLES_DIR: Path = resolve_bundles_root(Path(__file__))

# Build skills directory layout: each build skill stores its ``_CONFIG``
# (the ExecuteConfig instance) in a module named ``_{skill}_execute.py``
# under the skill's ``scripts/`` directory. Map tool_name to its module path
# components so ``_load_build_config`` can resolve the file deterministically.
_BUILD_CONFIG_LOCATIONS: dict[str, tuple[str, str]] = {
    # tool_name: (skill_dir_name, execute_module_filename)
    'maven': ('build-maven', '_maven_execute.py'),
    'gradle': ('build-gradle', '_gradle_execute.py'),
    'npm': ('build-npm', '_npm_execute.py'),
    'python': ('build-pyproject', '_pyproject_execute.py'),
}


def _classify_build_executable(executable: str) -> tuple[str, str] | None:
    """Detect Bucket B build notations in a resolved ``executable`` string.

    A build executable has the canonical shape::

        python3 .plan/execute-script.py {build_notation} run --command-args "{args}"

    where ``{build_notation}`` is one of the four keys in ``_BUILD_NOTATIONS``
    and ``{args}`` is the canonical command-args string the run-config keys
    are persisted against.

    The classifier returns ``(tool_name, command_args)`` when the executable
    matches this shape — ``tool_name`` is the value from ``_BUILD_NOTATIONS``,
    ``command_args`` is the literal string passed after ``--command-args``.
    Returns ``None`` for non-build executables (Bucket A ``manage-*``
    notations, raw shell invocations, executables that lack the ``run``
    subcommand, or executables missing ``--command-args``).

    Detection is structural: shlex tokenises the executable string so a
    quoted ``--command-args "verify plan-marshall"`` survives intact, and
    the four required tokens (script path, notation, ``run``, ``--command-args``)
    are checked positionally without regex backtracking surprises.
    """
    if not executable:
        return None

    try:
        tokens = shlex.split(executable)
    except ValueError:
        # Malformed quoting — treat as non-build.
        return None

    # Need at least: python3 <script> <notation> run --command-args <args>
    if len(tokens) < 6:
        return None

    # Locate the executor token (allow `python3` / `python` prefix variations).
    script_index: int | None = None
    for i, token in enumerate(tokens):
        if token.endswith('.plan/execute-script.py') or token.endswith('execute-script.py'):
            script_index = i
            break
    if script_index is None:
        return None

    # Notation immediately follows the script path.
    notation_index = script_index + 1
    if notation_index >= len(tokens):
        return None
    notation = tokens[notation_index]
    tool_name = _BUILD_NOTATIONS.get(notation)
    if tool_name is None:
        return None

    # Subcommand must be ``run``.
    sub_index = notation_index + 1
    if sub_index >= len(tokens) or tokens[sub_index] != 'run':
        return None

    # Find ``--command-args`` after the subcommand. Accept both
    # ``--command-args VALUE`` and ``--command-args=VALUE`` shapes.
    command_args: str | None = None
    i = sub_index + 1
    while i < len(tokens):
        tok = tokens[i]
        if tok == '--command-args':
            if i + 1 < len(tokens):
                command_args = tokens[i + 1]
            break
        if tok.startswith('--command-args='):
            command_args = tok[len('--command-args=') :]
            break
        i += 1

    if command_args is None:
        return None

    return tool_name, command_args


def _load_build_config(tool_name: str) -> Any | None:
    """Dynamically import the build skill's ``_CONFIG`` for ``tool_name``.

    Returns the ``ExecuteConfig`` instance from the corresponding
    ``_{skill}_execute.py`` module, or ``None`` when the module cannot be
    loaded (missing file, unexpected attribute layout). The loader uses
    ``importlib.util.spec_from_file_location`` so this works regardless of
    how the host process resolved its own ``sys.path``; the build-skill
    modules don't need to be already-imported.

    Caching is deliberately omitted: callers invoke ``cmd_resolve`` once per
    LLM request, and re-importing four small Python modules is cheaper than
    threading a cache through every code path.
    """
    location = _BUILD_CONFIG_LOCATIONS.get(tool_name)
    if location is None:
        return None
    skill_dir, module_filename = location
    module_path = resolve_bundle_path(
        _MARKETPLACE_BUNDLES_DIR, 'plan-marshall', f'skills/{skill_dir}/scripts/{module_filename}'
    )
    if not module_path.is_file():
        return None

    # Each build skill's scripts/ directory contains private helpers
    # (``_build_shared.py``, etc.) that the execute module imports. Augment
    # sys.path with the build skill's scripts dir AND the script-shared
    # bundle so the spec_from_file_location call below resolves siblings.
    import sys  # local import: only when classification reaches this point

    scripts_dir = str(module_path.parent)
    script_shared_dir = str(
        resolve_bundle_path(_MARKETPLACE_BUNDLES_DIR, 'plan-marshall', 'skills/script-shared/scripts/build')
    )
    added_paths: list[str] = []
    for candidate in (scripts_dir, script_shared_dir):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)
            added_paths.append(candidate)

    try:
        spec = importlib.util.spec_from_file_location(f'_arch_build_config_{tool_name}', module_path)
        if spec is None or spec.loader is None:
            return None
        # Use a private module name to avoid colliding with already-loaded
        # ``_pyproject_execute`` etc. — we only need the ``_CONFIG``
        # attribute, not registration in ``sys.modules``.
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, '_CONFIG', None)
    except Exception:
        return None
    finally:
        # Leave sys.path entries in place: each subsequent classifier call
        # re-uses them. Cleanup would be churny and serve no isolation
        # purpose at this layer.
        _ = added_paths


def _lookup_bash_timeout(tool_name: str, command_args: str, project_dir: str) -> int | None:
    """Resolve the Bash-tool timeout (in seconds) for a build invocation.

    Performs the round-trip ``compute_command_key`` -> ``timeout_get`` ->
    ``get_bash_timeout`` lookup using the same primitives ``cmd_run`` uses
    at execute time, guaranteeing the recommended timeout equals what the
    next real run will measure against (modulo adaptive updates).

    Returns the computed ``bash_timeout_seconds``, or ``None`` when any of
    the required modules cannot be imported (e.g., when the manage-architecture
    skill is loaded in isolation without the build skills present). The
    ``None`` return surfaces as omission of the four new fields in
    ``cmd_resolve``; non-build / non-resolvable executables behave as today.
    """
    config = _load_build_config(tool_name)
    if config is None:
        return None

    # Import ``compute_command_key`` and the timeout helpers lazily. Hot path
    # for non-build executables never touches these modules.
    import sys

    # Ensure the script-shared and manage-run-config directories are on
    # sys.path so the lazy imports resolve. ``_load_build_config`` already
    # added the shared build dir; this adds run-config.
    run_config_dir = str(
        resolve_bundle_path(_MARKETPLACE_BUNDLES_DIR, 'plan-marshall', 'skills/manage-run-config/scripts')
    )
    if run_config_dir not in sys.path:
        sys.path.insert(0, run_config_dir)

    try:
        from _build_execute_factory import compute_command_key
        from _build_shared import DEFAULT_BUILD_TIMEOUT, get_bash_timeout
        from run_config import timeout_get
    except ImportError:
        return None

    try:
        command_key = compute_command_key(config, command_args)
    except Exception:
        return None

    inner_timeout = timeout_get(command_key, DEFAULT_BUILD_TIMEOUT, project_dir)
    return get_bash_timeout(inner_timeout)


def _compute_execution_tier_fields(bash_timeout_seconds: int) -> dict[str, Any]:
    """Build the four-field augmentation dict for a known ``bash_timeout_seconds``.

    Returns the canonical shape consumed by ``cmd_resolve``. Hint strings are
    pinned recognition tokens — see module docstring.
    """
    exceeds = bash_timeout_seconds > _BASH_CEILING_SECONDS
    if exceeds:
        tier = 'orchestrator'
        hint = _HINT_ORCHESTRATOR
    else:
        tier = 'per_task'
        hint = _HINT_PER_TASK_TEMPLATE.format(ms=bash_timeout_seconds * 1000)
    return {
        'bash_timeout_seconds': bash_timeout_seconds,
        'exceeds_bash_ceiling': exceeds,
        'execution_tier': tier,
        'hint': hint,
    }
