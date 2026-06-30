#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Client command handlers for architecture script.

Handles: info, modules, graph, path, neighbors, impact, module, overview,
commands, resolve, profiles, siblings, files, which-module, find,
diff-modules, descriptor-regression-check.

Persistence model: ``_project.json`` and per-module ``enriched.json`` live on
disk under ``.plan/project-architecture/``; per-module ``derived.json`` is
ephemeral — every reader call resolves derived data via
``_architecture_core.load_module_derived`` which crawls the live worktree
filesystem rooted at ``args.project_dir`` / ``project_dir``. Every public
reader in this module threads ``project_dir`` through to the core helpers;
nothing falls back to ``Path.cwd()`` or ``git rev-parse``.
"""

import argparse
import fnmatch
import hashlib
import importlib.util
import json
import shlex
from collections import deque
from pathlib import Path
from typing import Any

from _architecture_core import (
    DATA_DIR,
    DataNotFoundError,
    ModuleNotFoundInProjectError,
    classify_changed_path,
    crawl_all_modules,
    error_result_command_not_found,
    error_result_module_not_found,
    get_root_module,
    iter_modules,
    load_merged_build_map,
    load_module_derived,
    load_module_enriched_or_empty,
    load_project_meta,
    merge_module_data,
    require_project_meta_result,
    resolve_module_for_path,
)
from constants import (  # type: ignore[import-not-found]
    DIR_PER_MODULE_DERIVED,
    FILE_PROJECT_META,
)
from marketplace_bundles import (  # type: ignore[import-not-found]
    resolve_bundle_path,
    resolve_bundles_root,
)


def _load_module_or_raise(module_name: str, project_dir: str) -> dict[str, Any]:
    """Validate module presence in ``_project.json`` and return its derived dict.

    Distinct from a missing ``_project.json`` case (which raises
    ``DataNotFoundError`` upstream): if the module is not in the index, raise
    ``ModuleNotFoundInProjectError`` regardless of disk state.
    """
    available = iter_modules(project_dir)
    if module_name not in available:
        raise ModuleNotFoundInProjectError(f'Module not found: {module_name}', available)
    return load_module_derived(module_name, project_dir)


NEIGHBORS_DEPTH_CAP = 8
DEFAULT_OVERVIEW_BUDGET = 200

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

# =============================================================================
# Build-class → command derivation (derive-verification)
# =============================================================================
#
# The build_class IS the canonical ``architecture resolve --command`` verb: a
# ``compile``/``module-tests``/``verify`` build_class resolves directly to the
# command of the same name (no indirection map). ``none`` is NOT
# architecture-resolved (it derives nothing), so the deriver handles it
# explicitly. The single source of truth for this contract is
# ``manage-architecture/standards/resolve-command.md`` §
# "Build-class → verification command".

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
        from _build_execute_factory import compute_command_key  # type: ignore[import-not-found]
        from _build_shared import DEFAULT_BUILD_TIMEOUT, get_bash_timeout  # type: ignore[import-not-found]
        from run_config import timeout_get  # type: ignore[import-not-found]
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


# =============================================================================
# Lazy Maven enrichment (subprocess-backed, per-module, cached)
# =============================================================================
#
# The cheap architecture crawl is subprocess-free: it parses each pom.xml with
# stdlib XML and does not run Maven, so the resolved dependency tree and the
# Maven-resolved/inherited profiles are NOT populated. Two consumers need those
# fields:
#
#   * ``resolve_command`` — when a profile-derived canonical (coverage /
#     integration-tests / e2e / benchmark / profile-overridable quality-gate)
#     is requested and absent from the cheap command map.
#   * the dependency-graph path (``_build_internal_deps_map`` /
#     ``get_module_graph``) — which reads each module's ``dependencies`` to
#     compute internal edges.
#
# Both route through ``enrich_maven_module`` (build-maven), which runs
# ``help:all-profiles dependency:tree`` for ONE module. The result is memoized
# per (project_dir, module_name) for the lifetime of one CLI invocation so a
# graph build enriches each module at most once.

# Per-process enrich memo. Key: (resolved project_dir, module_name). Value: the
# enrich dict (or None when the module could not be enriched). Mirrors the
# crawl memo in _architecture_core — one CLI call resolves each module once.
_ENRICH_CACHE: dict[tuple[str, str], dict[str, Any] | None] = {}


def _enrich_maven_module_cached(module_name: str, derived: dict[str, Any], project_dir: str) -> dict[str, Any] | None:
    """Run (and memoize) the one-module Maven enrich for ``module_name``.

    Resolves the module's directory from its ``paths.module`` and calls
    ``enrich_maven_module`` (build-maven). The import is deferred and guarded so
    manage-architecture still loads in isolation (without the build skills). A
    failed import or a failed Maven run memoizes ``None`` so the caller falls
    back to the cheap data without retrying.
    """
    cache_key = (str(Path(project_dir).resolve()), module_name)
    if cache_key in _ENRICH_CACHE:
        return _ENRICH_CACHE[cache_key]

    try:
        from _maven_cmd_discover import enrich_maven_module  # type: ignore[import-not-found]
    except ImportError:
        _ENRICH_CACHE[cache_key] = None
        return None

    module_rel = (derived.get('paths') or {}).get('module') or ''
    module_dir = Path(project_dir) if module_rel in ('', '.') else Path(project_dir) / module_rel

    try:
        enriched = enrich_maven_module(module_dir, project_dir)
    except Exception:
        enriched = None

    _ENRICH_CACHE[cache_key] = enriched
    return enriched


def _enrich_module_commands(module_name: str, derived: dict[str, Any], project_dir: str) -> dict[str, Any] | None:
    """Return ``derived``'s command map merged with profile-derived canonicals.

    Lazily enriches ``module_name`` (one Maven run, memoized) and rebuilds the
    profile-derived canonical commands (coverage / integration-tests / e2e /
    benchmark / profile-mapped quality-gate) from the Maven-resolved profiles,
    merging them onto the cheap command map. Returns ``None`` when enrichment is
    unavailable (caller keeps the cheap map).
    """
    enriched = _enrich_maven_module_cached(module_name, derived, project_dir)
    if enriched is None:
        return None
    profiles = enriched.get('profiles') or []
    if not profiles:
        return dict(derived.get('commands', {}))

    try:
        from _maven_cmd_discover import _build_commands  # type: ignore[import-not-found]
    except ImportError:
        return None

    relative_path = (derived.get('paths') or {}).get('module') or '.'
    packaging = (derived.get('metadata') or {}).get('packaging') or 'jar'
    stats = derived.get('stats') or {}
    rebuilt = _build_commands(
        module_name=module_name,
        packaging=packaging,
        has_sources=bool(stats.get('source_files', 0)),
        has_tests=bool(stats.get('test_files', 0)),
        profiles=profiles,
        relative_path=relative_path,
    )
    # Overlay profile-derived canonicals onto the cheap map; keep the cheap map's
    # entries for everything the rebuilt map does not carry.
    merged = dict(derived.get('commands', {}))
    merged.update({k: v for k, v in rebuilt.items() if k != 'conflicts'})
    return merged


def _enriched_dependencies(module_name: str, derived: dict[str, Any], project_dir: str) -> list[str]:
    """Return a module's resolved dependency list, enriching lazily when empty.

    The cheap crawl leaves ``dependencies`` empty. The graph path needs the
    resolved tree to compute internal edges, so this enriches the module (once,
    memoized) and returns the enriched ``dependencies``. Falls back to whatever
    ``derived`` already carries when enrichment is unavailable.
    """
    existing = derived.get('dependencies') or []
    if existing:
        return existing
    enriched = _enrich_maven_module_cached(module_name, derived, project_dir)
    if enriched is None:
        return existing
    return enriched.get('dependencies') or []


# =============================================================================
# API Functions
# =============================================================================


def get_project_info(project_dir: str = '.') -> dict[str, Any]:
    """Get project summary with metadata and module overview."""
    meta = load_project_meta(project_dir)

    module_names = iter_modules(project_dir)

    # Collect unique build systems and per-module rows.
    technologies: set[str] = set()
    module_overview: list[dict[str, Any]] = []

    for name in module_names:
        try:
            derived = load_module_derived(name, project_dir)
        except DataNotFoundError:
            derived = {}
        for bs in derived.get('build_systems', []):
            technologies.add(bs)

        enriched = load_module_enriched_or_empty(name, project_dir)
        paths = derived.get('paths', {})
        module_overview.append({'name': name, 'path': paths.get('module', ''), 'purpose': enriched.get('purpose', '')})

    return {
        'project': {'name': meta.get('name', ''), 'description': meta.get('description', '')},
        'technologies': sorted(technologies),
        'modules': module_overview,
    }


def get_modules_list(project_dir: str = '.') -> list[str]:
    """Get list of module names from ``_project.json``."""
    return iter_modules(project_dir)


def get_modules_with_command(command_name: str, project_dir: str = '.') -> list[str]:
    """Get list of module names that provide a specific command."""
    modules_with_command: list[str] = []

    for module_name in iter_modules(project_dir):
        try:
            derived = load_module_derived(module_name, project_dir)
        except DataNotFoundError:
            continue
        commands = derived.get('commands', {})
        if command_name in commands:
            modules_with_command.append(module_name)

    return modules_with_command


def get_modules_by_physical_path(physical_path: str, project_dir: str = '.') -> list[str]:
    """Get list of module names at a specific physical path.

    For virtual modules, multiple modules may share the same physical path.
    """
    modules_at_path: list[str] = []

    for module_name in iter_modules(project_dir):
        try:
            derived = load_module_derived(module_name, project_dir)
        except DataNotFoundError:
            continue

        # Check virtual_module.physical_path first.
        virtual = derived.get('virtual_module', {})
        mod_physical_path = virtual.get('physical_path') if virtual else None

        # Fall back to paths.module.
        if not mod_physical_path:
            paths = derived.get('paths', {})
            mod_physical_path = paths.get('module', '.')

        if mod_physical_path == physical_path:
            modules_at_path.append(module_name)

    return modules_at_path


def get_sibling_modules(module_name: str, project_dir: str = '.') -> list[str]:
    """Get sibling virtual modules for a given module."""
    derived = _load_module_or_raise(module_name, project_dir)
    virtual = derived.get('virtual_module', {})
    siblings: list[str] = virtual.get('sibling_modules', [])
    return siblings


def get_module_graph(
    project_dir: str = '.',
    full: bool = False,
    *,
    derived_by_name: dict[str, dict[str, Any]] | None = None,
    enriched_by_name: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Get complete internal module dependency graph with topological layers.

    Uses Kahn's algorithm to compute execution layers where layer 0 contains
    modules with no dependencies, and higher layers depend only on lower layers.

    Args:
        project_dir: Project directory path
        full: When False, aggregator (pom-packaging) modules are filtered out.
        derived_by_name: Optional pre-loaded ``module_name → derived.json`` map
            shared with other helpers in the same caller; avoids redundant I/O.
        enriched_by_name: Optional pre-loaded ``module_name → enriched.json`` map.
    """
    if derived_by_name is None:
        module_names_all = iter_modules(project_dir)
        # Lazily load each module's derived/enriched data once.
        derived_by_name = {}
        for name in module_names_all:
            try:
                derived_by_name[name] = load_module_derived(name, project_dir)
            except DataNotFoundError:
                derived_by_name[name] = {}
    else:
        module_names_all = list(derived_by_name.keys())

    if enriched_by_name is None:
        enriched_by_name = {
            name: load_module_enriched_or_empty(name, project_dir) for name in module_names_all
        }

    # Build mapping of groupId:artifactId -> module_name for internal dep
    # detection. Lets us identify which dependencies are internal to the project.
    artifact_to_module: dict[str, str] = {}
    for mod_name, mod_data in derived_by_name.items():
        metadata = mod_data.get('metadata', {})
        group_id = metadata.get('group_id')
        artifact_id = metadata.get('artifact_id')
        if group_id and artifact_id:
            artifact_to_module[f'{group_id}:{artifact_id}'] = mod_name

    # Compute internal_dependencies for each module from its dependencies list.
    internal_deps_map: dict[str, list[str]] = {}
    for mod_name, mod_data in derived_by_name.items():
        enriched_mod = enriched_by_name.get(mod_name, {})
        if 'internal_dependencies' in enriched_mod:
            internal_deps_map[mod_name] = enriched_mod['internal_dependencies']
        elif 'internal_dependencies' in mod_data:
            internal_deps_map[mod_name] = mod_data['internal_dependencies']
        else:
            # The cheap crawl leaves ``dependencies`` empty — enrich this one
            # module lazily (memoized) so internal edges can be computed.
            deps = _enriched_dependencies(mod_name, mod_data, project_dir)
            internal: set[str] = set()
            for dep in deps:
                parts = dep.split(':')
                if len(parts) >= 2:
                    ga = f'{parts[0]}:{parts[1]}'
                    if ga in artifact_to_module:
                        dep_module = artifact_to_module[ga]
                        if dep_module != mod_name:
                            internal.add(dep_module)
            internal_deps_map[mod_name] = list(internal)

    # Post-resolution augmentation: symmetric virtual-sibling cross-linking.
    # See _apply_sibling_cross_links for the full rationale.
    _apply_sibling_cross_links(internal_deps_map, derived_by_name)

    # Filter out aggregator modules unless --full is specified.
    # Aggregators are pom-packaging modules (not jar, nar, war, etc.). However
    # enriched data can mark pom modules as is_leaf to override filtering.
    if full:
        module_names: list[str] = list(module_names_all)
        filtered_out: list[str] = []
    else:
        module_names = []
        filtered_out = []
        for name in module_names_all:
            data = derived_by_name.get(name, {})
            metadata = data.get('metadata', {})
            packaging = metadata.get('packaging', 'jar')
            enriched_mod = enriched_by_name.get(name, {})

            is_leaf = enriched_mod.get('is_leaf', False)
            purpose = enriched_mod.get('purpose', '')
            is_purpose_leaf = purpose in ['integration-tests', 'e2e', 'deployment', 'benchmark']

            if packaging != 'pom' or is_leaf or is_purpose_leaf:
                module_names.append(name)
            else:
                filtered_out.append(name)

    # Build adjacency list and in-degree count.
    # Edge direction: from dependency TO dependent (for topological sort).
    in_degree: dict[str, int] = dict.fromkeys(module_names, 0)
    dependents: dict[str, list[str]] = {name: [] for name in module_names}

    edges: list[dict[str, str]] = []
    for module_name in module_names:
        internal_deps = internal_deps_map.get(module_name, [])
        for dep in internal_deps:
            if dep in module_names:
                edges.append({'from': dep, 'to': module_name})
                in_degree[module_name] += 1
                dependents[dep].append(module_name)

    # Kahn's algorithm for topological sort with layer assignment.
    layers: list[dict[str, Any]] = []
    remaining = set(module_names)
    node_layers: dict[str, int] = {}

    current_layer = [name for name in module_names if in_degree[name] == 0]

    layer_num = 0
    while current_layer:
        layers.append({'layer': layer_num, 'modules': sorted(current_layer)})
        for name in current_layer:
            node_layers[name] = layer_num
            remaining.discard(name)

        next_layer = []
        for name in current_layer:
            for dependent in dependents[name]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0 and dependent in remaining:
                    next_layer.append(dependent)
                    remaining.discard(dependent)

        current_layer = next_layer
        layer_num += 1

    circular_deps: list[str] | None = list(remaining) if remaining else None

    nodes: list[dict[str, Any]] = []
    for name in module_names:
        enriched_module = enriched_by_name.get(name, {})
        nodes.append(
            {
                'name': name,
                'purpose': enriched_module.get('purpose', ''),
                'layer': node_layers.get(name, -1),
            }
        )

    roots = [name for name in module_names if not internal_deps_map.get(name, [])]
    leaves = [name for name in module_names if not dependents[name]]

    return {
        'graph': {'node_count': len(nodes), 'edge_count': len(edges)},
        'nodes': nodes,
        'edges': edges,
        'layers': layers,
        'roots': sorted(roots),
        'leaves': sorted(leaves),
        'circular_dependencies': circular_deps,
        'filtered_out': sorted(filtered_out) if filtered_out else None,
    }


def get_module_info(module_name: str | None = None, full: bool = False, project_dir: str = '.') -> dict[str, Any]:
    """Get module information merged from derived + enriched data."""
    if not module_name:
        module_name = get_root_module(project_dir)
        if not module_name:
            raise ModuleNotFoundInProjectError('No modules found', [])

    # Validate the resolved name appears in the index.
    available = iter_modules(project_dir)
    if module_name not in available:
        raise ModuleNotFoundInProjectError(f'Module not found: {module_name}', available)

    merged = merge_module_data(module_name, project_dir)

    if not full:
        reasoning_fields = [
            'responsibility_reasoning',
            'purpose_reasoning',
            'key_dependencies_reasoning',
            'skills_by_profile_reasoning',
        ]
        for field in reasoning_fields:
            merged.pop(field, None)

        merged.pop('packages', None)
        merged.pop('dependencies', None)

    return merged


def get_module_commands(module_name: str | None = None, project_dir: str = '.') -> dict[str, Any]:
    """Get available commands for a module."""
    if not module_name:
        module_name = get_root_module(project_dir)
        if not module_name:
            raise ModuleNotFoundInProjectError('No modules found', [])

    derived = _load_module_or_raise(module_name, project_dir)
    commands = derived.get('commands', {})

    command_list: list[dict[str, str]] = []
    for cmd_name, cmd_data in commands.items():
        description = ''
        if isinstance(cmd_data, dict):
            description = cmd_data.get('description', '')
        command_list.append({'name': cmd_name, 'description': description})

    return {'module': module_name, 'commands': command_list}


# Profile-derived canonical commands that the cheap (subprocess-free) Maven
# crawl cannot fully populate: their presence/value depends on Maven profile
# resolution. When one of these is requested and the module's cheap command map
# lacks it (or carries only the plain ``verify`` base for ``quality-gate``,
# which a profile MIGHT override), ``resolve_command`` lazily enriches that one
# module via ``enrich_maven_module`` and re-resolves. The plain build verbs
# (compile/verify/test/package/clean/install) NEVER trigger enrichment.
_PROFILE_CANONICALS: frozenset[str] = frozenset(
    {'coverage', 'integration-tests', 'e2e', 'benchmark'}
)


def _command_executable(commands: dict[str, Any], command_name: str) -> str:
    """Return the executable string for ``command_name`` in a command map."""
    cmd_data = commands[command_name]
    return cmd_data if isinstance(cmd_data, str) else cmd_data.get('executable', '')


def _needs_profile_enrichment(command_name: str, commands: dict[str, Any]) -> bool:
    """Whether requesting ``command_name`` warrants a lazy profile enrich.

    True when the requested command is a profile-derived canonical that is
    absent from the cheap command map, OR is ``quality-gate`` whose cheap value
    is still the plain ``verify`` base (a profile might override it). The plain
    build verbs never warrant enrichment.
    """
    if command_name in _PROFILE_CANONICALS:
        return command_name not in commands
    if command_name == 'quality-gate':
        if 'quality-gate' not in commands:
            return False
        executable = _command_executable(commands, 'quality-gate')
        verify_exec = _command_executable(commands, 'verify') if 'verify' in commands else None
        # Cheap quality-gate == verify base means no in-pom profile has been
        # mapped onto it yet; an enrich might surface a profile-bearing one.
        return verify_exec is not None and executable == verify_exec
    return False


def resolve_command(command_name: str, module_name: str | None = None, project_dir: str = '.') -> dict[str, str]:
    """Resolve command to executable form with cascading fallback.

    Resolution order:
    1. Try command at specified module (lazily enriching that one module first
       when the command is a profile-derived canonical absent from the cheap map)
    2. If not found AND module is not the root module -> try at root module
    3. If still not found -> raise ValueError

    The ``default`` module alias resolves to the real root module. ``get_root_module``
    is consulted exactly once and reused for both the default resolution and the
    root cascade.
    """
    root_module_name = get_root_module(project_dir)

    # ``default`` is an alias for the real root module.
    if module_name == 'default':
        module_name = root_module_name

    if not module_name:
        module_name = root_module_name
        if not module_name:
            raise ModuleNotFoundInProjectError('No modules found', [])

    derived = _load_module_or_raise(module_name, project_dir)
    commands = derived.get('commands', {})

    # Lazy profile enrichment: a profile-derived canonical (coverage,
    # integration-tests, e2e, benchmark, or a profile-overridable quality-gate)
    # may be missing from the cheap crawl. Enrich this ONE module and merge the
    # profile-derived commands before lookup. Plain build verbs skip this.
    if _needs_profile_enrichment(command_name, commands):
        enriched_commands = _enrich_module_commands(module_name, derived, project_dir)
        if enriched_commands is not None:
            commands = enriched_commands

    if command_name in commands:
        executable = _command_executable(commands, command_name)
        return {'module': module_name, 'command': command_name, 'executable': executable, 'resolution_level': 'module'}

    # Cascade: try root module if current module is not already root.
    if root_module_name and module_name != root_module_name:
        try:
            root_derived = load_module_derived(root_module_name, project_dir)
        except DataNotFoundError:
            root_derived = {}
        root_commands = root_derived.get('commands', {})
        if _needs_profile_enrichment(command_name, root_commands):
            enriched_root = _enrich_module_commands(root_module_name, root_derived, project_dir)
            if enriched_root is not None:
                root_commands = enriched_root
        if command_name in root_commands:
            executable = _command_executable(root_commands, command_name)
            return {
                'module': root_module_name,
                'command': command_name,
                'executable': executable,
                'resolution_level': 'root',
            }

    raise ValueError(f'Command not found: {command_name}')


# =============================================================================
# Graph Traversal Helpers
# =============================================================================


def _apply_sibling_cross_links(
    deps_map: dict[str, list[str]],
    derived_by_name: dict[str, Any],
) -> None:
    """Add symmetric virtual-sibling edges to ``deps_map`` in-place.

    Every maven↔npm virtual-sibling pair must be cross-linked in both
    directions.  ``_split_to_virtual_modules`` records ``sibling_modules``
    symmetrically on both pair members, so iterating every module and adding
    its declared siblings yields symmetric edges for all pairs — including
    modules whose ``internal_dependencies`` came from the LLM-curated
    ``enriched.json`` branch.

    Args:
        deps_map: Mutable mapping of module name → sorted dependency list.
            Modified in-place; absent module entries are treated as empty.
        derived_by_name: Mapping of module name → derived module data dict.
            Used to validate that a sibling name actually exists as a module.
    """
    for mod_name, mod_data in derived_by_name.items():
        siblings = mod_data.get('virtual_module', {}).get('sibling_modules', [])
        if not siblings:
            continue
        augmented = set(deps_map.get(mod_name, []))
        for sibling in siblings:
            if sibling in derived_by_name and sibling != mod_name:
                augmented.add(sibling)
        deps_map[mod_name] = sorted(augmented)


def _build_internal_deps_map(
    project_dir: str = '.',
    *,
    derived_by_name: dict[str, dict[str, Any]] | None = None,
    enriched_by_name: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, list[str]], list[str]]:
    """Build internal_dependencies mapping for all modules.

    Resolution order per module mirrors get_module_graph:
      1. enriched.{X}.internal_dependencies (LLM-curated)
      2. derived.{X}.internal_dependencies (from discover)
      3. computed from derived.{X}.dependencies via groupId:artifactId

    Args:
        project_dir: Project directory path
        derived_by_name: Optional pre-loaded ``module_name → derived.json`` map.
            When supplied, the helper skips its per-module ``load_module_derived``
            calls and reuses the caller's already-loaded data. Module-name set
            is taken from this dict's keys (preserves caller's ordering).
        enriched_by_name: Optional pre-loaded ``module_name → enriched.json``
            map. When supplied, the helper skips its per-module
            ``load_module_enriched_or_empty`` calls.

    Returns:
        Tuple of (deps_map, module_names) where deps_map maps each module name
        to its list of internal dependency module names. Lists are sorted to
        guarantee deterministic traversal order.
    """
    if derived_by_name is None:
        module_names = iter_modules(project_dir)
        derived_by_name = {}
        for name in module_names:
            try:
                derived_by_name[name] = load_module_derived(name, project_dir)
            except DataNotFoundError:
                derived_by_name[name] = {}
    else:
        module_names = list(derived_by_name.keys())

    if enriched_by_name is None:
        enriched_by_name = {
            name: load_module_enriched_or_empty(name, project_dir) for name in module_names
        }

    artifact_to_module: dict[str, str] = {}
    for mod_name, mod_data in derived_by_name.items():
        metadata = mod_data.get('metadata', {})
        group_id = metadata.get('group_id')
        artifact_id = metadata.get('artifact_id')
        if group_id and artifact_id:
            artifact_to_module[f'{group_id}:{artifact_id}'] = mod_name

    deps_map: dict[str, list[str]] = {}
    for mod_name, mod_data in derived_by_name.items():
        enriched_mod = enriched_by_name.get(mod_name, {})
        if 'internal_dependencies' in enriched_mod:
            deps_map[mod_name] = sorted(set(enriched_mod['internal_dependencies']))
        elif 'internal_dependencies' in mod_data:
            deps_map[mod_name] = sorted(set(mod_data['internal_dependencies']))
        else:
            # The cheap crawl leaves ``dependencies`` empty — enrich this one
            # module lazily (memoized) so internal edges can be computed.
            deps = _enriched_dependencies(mod_name, mod_data, project_dir)
            internal: set[str] = set()
            for dep in deps:
                parts = dep.split(':')
                if len(parts) >= 2:
                    ga = f'{parts[0]}:{parts[1]}'
                    if ga in artifact_to_module:
                        dep_module = artifact_to_module[ga]
                        if dep_module != mod_name:
                            internal.add(dep_module)
            deps_map[mod_name] = sorted(internal)

    # Post-resolution augmentation: symmetric virtual-sibling cross-linking.
    # See _apply_sibling_cross_links for the full rationale.
    _apply_sibling_cross_links(deps_map, derived_by_name)

    return deps_map, module_names


def get_module_path(source: str, target: str, project_dir: str = '.') -> list[str] | None:
    """BFS shortest path from source to target over internal_dependencies edges.

    Edge semantics: a directed edge exists from M to N iff N appears in M's
    internal_dependencies. The path therefore walks the "depends on" relation:
    each successor in the returned list is a direct dependency of its predecessor.

    Args:
        source: Starting module name
        target: Destination module name
        project_dir: Project directory path

    Returns:
        Shortest path [source, ..., target] as a list of module names, or None
        when target is unreachable from source. When source == target returns
        [source].

    Raises:
        ModuleNotFoundInProjectError: If source or target is not a known module
    """
    deps_map, module_names = _build_internal_deps_map(project_dir)

    if source not in deps_map:
        raise ModuleNotFoundInProjectError(f'Module not found: {source}', module_names)
    if target not in deps_map:
        raise ModuleNotFoundInProjectError(f'Module not found: {target}', module_names)

    if source == target:
        return [source]

    visited: set[str] = {source}
    queue: deque[tuple[str, list[str]]] = deque([(source, [source])])
    while queue:
        current, path = queue.popleft()
        for neighbor in deps_map.get(current, []):
            if neighbor == target:
                return [*path, neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, [*path, neighbor]))
    return None


def get_module_neighbors(module_name: str, depth: int, project_dir: str = '.') -> list[str]:
    """N-hop neighborhood of a module over internal_dependencies edges.

    Args:
        module_name: Starting module
        depth: Hop count. 0 returns just the module itself; values above
            NEIGHBORS_DEPTH_CAP are clamped to the cap.
        project_dir: Project directory path

    Returns:
        Sorted list of module names reachable within `depth` hops, including
        the starting module. Excludes modules that are not part of the project.

    Raises:
        ValueError: If depth is negative
        ModuleNotFoundInProjectError: If module_name is not a known module
    """
    if depth < 0:
        raise ValueError(f'depth must be >= 0, got {depth}')
    if depth > NEIGHBORS_DEPTH_CAP:
        depth = NEIGHBORS_DEPTH_CAP

    deps_map, module_names = _build_internal_deps_map(project_dir)

    if module_name not in deps_map:
        raise ModuleNotFoundInProjectError(f'Module not found: {module_name}', module_names)

    visited: set[str] = {module_name}
    frontier: set[str] = {module_name}
    for _ in range(depth):
        next_frontier: set[str] = set()
        for node in frontier:
            for neighbor in deps_map.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.add(neighbor)
        if not next_frontier:
            break
        frontier = next_frontier
    return sorted(visited)


def get_module_impact(module_name: str, project_dir: str = '.') -> list[str]:
    """Transitive reverse-dependency closure of a module.

    Returns every module Y such that `module_name` is in the transitive closure
    of Y's internal_dependencies. The starting module itself is excluded from
    the result.

    Args:
        module_name: Module name whose impact set should be computed
        project_dir: Project directory path

    Returns:
        Sorted list of module names that transitively depend on module_name.

    Raises:
        ModuleNotFoundInProjectError: If module_name is not a known module
    """
    deps_map, module_names = _build_internal_deps_map(project_dir)

    if module_name not in deps_map:
        raise ModuleNotFoundInProjectError(f'Module not found: {module_name}', module_names)

    rev: dict[str, list[str]] = {name: [] for name in module_names}
    for mod, deps in deps_map.items():
        for dep in deps:
            if dep in rev:
                rev[dep].append(mod)

    impact: set[str] = set()
    queue: deque[str] = deque(rev.get(module_name, []))
    while queue:
        current = queue.popleft()
        if current == module_name or current in impact:
            continue
        impact.add(current)
        queue.extend(rev.get(current, []))
    return sorted(impact)


# =============================================================================
# Overview Renderer
# =============================================================================


_TRUNCATION_MARKER_PREFIX = '... (truncated to fit budget='


def _truncation_marker(budget: int, required: int) -> str:
    return f'{_TRUNCATION_MARKER_PREFIX}{budget}; full output requires --budget {required})'


def _render_project_section(meta: dict[str, Any]) -> list[str]:
    name = meta.get('name', '(unnamed project)')
    description = (meta.get('description') or '').strip()
    lines = [f'# {name}', '']
    if description:
        lines.extend([description, ''])
    return lines


def _render_modules_section(enriched_by_name: dict[str, dict[str, Any]]) -> list[str]:
    if not enriched_by_name:
        return []

    lines = ['## Modules', '', '| Module | Purpose | Responsibility |', '|---|---|---|']
    for name in sorted(enriched_by_name.keys()):
        enriched_mod = enriched_by_name[name]
        purpose = (enriched_mod.get('purpose') or '').strip() or '—'
        responsibility = (enriched_mod.get('responsibility') or '').strip()
        responsibility = responsibility.replace('\n', ' ') if responsibility else '—'
        lines.append(f'| {name} | {purpose} | {responsibility} |')
    lines.append('')
    return lines


def _render_adjacency_section(deps_map: dict[str, list[str]]) -> list[str]:
    if not deps_map:
        return []
    lines = ['## Adjacency', '', '| Module | Internal Dependencies |', '|---|---|']
    for name in sorted(deps_map.keys()):
        deps = deps_map[name]
        rendered = ', '.join(sorted(deps)) if deps else '—'
        lines.append(f'| {name} | {rendered} |')
    lines.append('')
    return lines


def _count_profile_skills(profile_data: Any) -> int:
    """Count skill entries in a single profile's value.

    The value may be either a dict (with ``defaults``/``optionals`` lists) or
    a flat list. Any other shape contributes zero. Centralised so render
    helpers and module deep-dives stay in lock-step on the count semantics.
    """
    if isinstance(profile_data, dict):
        defaults = profile_data.get('defaults', [])
        optionals = profile_data.get('optionals', [])
        return len(defaults) + len(optionals)
    if isinstance(profile_data, list):
        return len(profile_data)
    return 0


def _render_skills_by_profile_section(enriched_by_name: dict[str, dict[str, Any]]) -> list[str]:
    rows: list[tuple[str, dict[str, Any]]] = []
    for name in sorted(enriched_by_name.keys()):
        skills_by_profile = enriched_by_name[name].get('skills_by_profile', {})
        if skills_by_profile:
            rows.append((name, skills_by_profile))
    if not rows:
        return []

    lines = ['## Skills by Profile', '']
    for name, skills_by_profile in rows:
        lines.append(f'### {name}')
        lines.append('')
        for profile in sorted(skills_by_profile.keys()):
            count = _count_profile_skills(skills_by_profile[profile])
            lines.append(f'- {profile}: {count} skill{"s" if count != 1 else ""}')
        lines.append('')
    return lines


def _apply_budget(sections: list[list[str]], budget: int) -> tuple[list[str], int]:
    """Apply line budget to ordered sections, dropping trailing sections first.

    Sections are listed in priority order (most important first). When the
    concatenated output exceeds `budget` lines, drop trailing sections one at
    a time until it fits, leaving room for a single truncation marker line.

    Returns:
        (rendered_lines, required_budget) where required_budget is the line
        count that would be needed to render every section in full.
    """
    full = [line for section in sections for line in section]
    required = len(full)
    if required <= budget:
        return full, required

    # Try keeping prefixes of section list, leaving 1 line for marker.
    for keep in range(len(sections) - 1, 0, -1):
        prefix = [line for section in sections[:keep] for line in section]
        if len(prefix) + 1 <= budget:
            return [*prefix, _truncation_marker(budget, required)], required

    # Even one section won't fit. Hard-truncate the first section.
    head = sections[0][: max(budget - 1, 0)]
    return [*head, _truncation_marker(budget, required)], required


def render_overview(project_dir: str = '.', budget: int = DEFAULT_OVERVIEW_BUDGET) -> str:
    """Render deterministic markdown summary of the project architecture.

    Sections in priority order: project header > modules table > adjacency
    table > skills_by_profile summary. When the rendered output exceeds
    `budget` lines, trailing sections are dropped and a marker is appended.

    Args:
        project_dir: Project directory path
        budget: Maximum line count for the rendered markdown

    Returns:
        Markdown string. Always ends with a trailing newline so byte-identical
        repeat invocations produce identical files.
    """
    meta = load_project_meta(project_dir)
    module_names = iter_modules(project_dir)
    derived_by_name: dict[str, dict[str, Any]] = {}
    for name in module_names:
        try:
            derived_by_name[name] = load_module_derived(name, project_dir)
        except DataNotFoundError:
            derived_by_name[name] = {}
    enriched_by_name: dict[str, dict[str, Any]] = {
        name: load_module_enriched_or_empty(name, project_dir) for name in module_names
    }
    deps_map, _ = _build_internal_deps_map(
        project_dir,
        derived_by_name=derived_by_name,
        enriched_by_name=enriched_by_name,
    )

    sections = [
        _render_project_section(meta),
        _render_modules_section(enriched_by_name),
        _render_adjacency_section(deps_map),
        _render_skills_by_profile_section(enriched_by_name),
    ]
    sections = [s for s in sections if s]

    rendered, _ = _apply_budget(sections, budget)
    return '\n'.join(rendered).rstrip('\n') + '\n'


def render_module_markdown(
    module_name: str | None = None,
    project_dir: str = '.',
    budget: int = DEFAULT_OVERVIEW_BUDGET,
    *,
    merged: dict[str, Any] | None = None,
) -> str:
    """Render budgeted markdown deep-dive for a single module.

    Sections in priority order: header (name, purpose, responsibility) >
    internal dependencies > key packages > skills_by_profile > tips/insights.

    Args:
        module_name: Module name (None resolves to root module)
        project_dir: Project directory path
        budget: Maximum line count for the rendered markdown
        merged: Optional pre-loaded merged module data (derived + enriched).
            When supplied, the helper skips ``_load_module_or_raise`` /
            ``merge_module_data`` calls and trusts the caller's already-loaded
            dict. The caller is responsible for having validated the module
            name when the kwarg is non-None.

    Returns:
        Markdown string ending with a trailing newline.
    """
    if not module_name:
        module_name = get_root_module(project_dir)
        if not module_name:
            raise ModuleNotFoundInProjectError('No modules found', [])

    if merged is None:
        # Validate the module exists; raises ModuleNotFoundInProjectError otherwise
        _load_module_or_raise(module_name, project_dir)
        merged = merge_module_data(module_name, project_dir)

    purpose = merged.get('purpose', '').strip() or '—'
    responsibility = merged.get('responsibility', '').strip() or '—'
    header = [
        f'# {module_name}',
        '',
        f'**Purpose**: {purpose}',
        f'**Responsibility**: {responsibility}',
        '',
    ]

    deps_map, _ = _build_internal_deps_map(project_dir)
    deps = deps_map.get(module_name, [])
    deps_section: list[str] = []
    if deps:
        deps_section = ['## Internal Dependencies', '']
        deps_section.extend(f'- {d}' for d in deps)
        deps_section.append('')

    packages = merged.get('key_packages') or merged.get('packages') or []
    packages_section: list[str] = []
    if packages:
        packages_section = ['## Key Packages', '']
        for pkg in packages:
            if isinstance(pkg, dict):
                pkg_name = pkg.get('name') or pkg.get('package') or ''
                desc = pkg.get('description', '').strip()
                if desc:
                    packages_section.append(f'- `{pkg_name}` — {desc}')
                else:
                    packages_section.append(f'- `{pkg_name}`')
            else:
                packages_section.append(f'- `{pkg}`')
        packages_section.append('')

    skills_section: list[str] = []
    skills_by_profile = merged.get('skills_by_profile', {})
    if skills_by_profile:
        skills_section = ['## Skills by Profile', '']
        for profile in sorted(skills_by_profile.keys()):
            count = _count_profile_skills(skills_by_profile[profile])
            skills_section.append(f'- {profile}: {count} skill{"s" if count != 1 else ""}')
        skills_section.append('')

    notes_section: list[str] = []
    tips = merged.get('tips') or []
    insights = merged.get('insights') or []
    practices = merged.get('best_practices') or []
    if tips or insights or practices:
        notes_section = ['## Notes', '']
        for label, items in (('Tips', tips), ('Insights', insights), ('Best Practices', practices)):
            if items:
                notes_section.append(f'**{label}**:')
                for item in items:
                    if isinstance(item, dict):
                        text = item.get('text') or item.get('message') or item.get('description') or str(item)
                    else:
                        text = str(item)
                    notes_section.append(f'- {text}')
                notes_section.append('')

    sections = [s for s in (header, deps_section, packages_section, skills_section, notes_section) if s]
    rendered, _ = _apply_budget(sections, budget)
    return '\n'.join(rendered).rstrip('\n') + '\n'


# =============================================================================
# CLI Handlers
# =============================================================================


def _extract_profile_keys(skills_by_profile: dict[str, Any]) -> set[str]:
    """Extract profile keys from skills_by_profile structure."""
    return set(skills_by_profile.keys())


def cmd_info(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for info command."""
    try:
        info = get_project_info(args.project_dir)
        return {'status': 'success', **info}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_modules(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for modules command."""
    try:
        command_filter = getattr(args, 'filter_command', None)
        physical_path_filter = getattr(args, 'physical_path', None)

        if command_filter:
            modules = get_modules_with_command(command_filter, args.project_dir)
            return {'status': 'success', 'command': command_filter, 'modules': modules}
        elif physical_path_filter:
            modules = get_modules_by_physical_path(physical_path_filter, args.project_dir)
            return {'status': 'success', 'physical_path': physical_path_filter, 'modules': modules}
        else:
            modules = get_modules_list(args.project_dir)
            return {'status': 'success', 'modules': modules}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_graph(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for graph command."""
    try:
        result = get_module_graph(args.project_dir, args.full)
        return {'status': 'success', **result}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_module(args: argparse.Namespace) -> Any:
    """CLI handler for module command.

    Returns a TOON dict by default. When `--full --budget N` is supplied, returns
    a markdown string for a token-bounded module deep-dive instead. `--budget`
    without `--full` is silently a no-op (TOON output, identical to plain `--full`).
    """
    try:
        # Resolve module name (root if not provided), then merge.
        module_name = args.module or get_root_module(args.project_dir)
        if not module_name:
            raise ModuleNotFoundInProjectError('No modules found', [])
        budget = getattr(args, 'budget', None)
        if args.full and budget is not None:
            return render_module_markdown(module_name, args.project_dir, budget)
        module = get_module_info(module_name, args.full, args.project_dir)
        return {'status': 'success', 'module': module}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        try:
            modules = get_modules_list(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_overview(args: argparse.Namespace) -> Any:
    """CLI handler for overview command. Returns markdown string."""
    try:
        budget = getattr(args, 'budget', DEFAULT_OVERVIEW_BUDGET)
        return render_overview(args.project_dir, budget)
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_commands(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for commands command."""
    try:
        result = get_module_commands(args.module, args.project_dir)
        return {'status': 'success', **result}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        try:
            modules = get_modules_list(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_resolve(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for resolve command.

    When the resolved ``executable`` is a Bucket B build notation, the result
    is augmented with four additional fields (``bash_timeout_seconds``,
    ``exceeds_bash_ceiling``, ``execution_tier``, ``hint``) derived from the
    persisted run-config timeout. Non-build executables return today's TOON
    shape unchanged. See the module-level "Build-executable classification"
    section for the full contract.
    """
    try:
        result = resolve_command(args.resolve_command, args.module, args.project_dir)
        # Augment with adaptive-timeout / execution-tier fields when the
        # executable is a Bucket B build notation.
        augmented = {'status': 'success', **_augment_resolved(result, args.project_dir)}
        return augmented
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        try:
            modules = get_modules_list(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except ValueError:
        # Command not found at the resolved module. Resolve the ``default``
        # alias here too so the error names the real root module, matching the
        # alias handling in ``resolve_command``.
        try:
            requested = None if args.module == 'default' else args.module
            resolved_module = requested or get_root_module(args.project_dir) or ''
            if resolved_module:
                derived = load_module_derived(resolved_module, args.project_dir)
                commands = list(derived.get('commands', {}).keys())
            else:
                commands = []
        except Exception:
            resolved_module = args.module or ''
            commands = []
        return error_result_command_not_found(resolved_module, args.resolve_command, commands)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def _augment_resolved(executable_result: dict[str, Any], project_dir: str) -> dict[str, Any]:
    """Apply the Bucket B execution-tier augmentation to a resolved command dict.

    Shared by ``cmd_resolve`` and the deriver: when the resolved ``executable``
    is a Bucket B build notation, attach the ``bash_timeout_seconds`` /
    ``exceeds_bash_ceiling`` / ``execution_tier`` / ``hint`` quartet so the
    per-task timeout routing keeps working for derived commands exactly as it
    does for a direct ``resolve`` call.
    """
    augmented = dict(executable_result)
    classification = _classify_build_executable(executable_result.get('executable', ''))
    if classification is not None:
        tool_name, command_args = classification
        bash_timeout = _lookup_bash_timeout(tool_name, command_args, project_dir)
        if bash_timeout is not None:
            augmented.update(_compute_execution_tier_fields(bash_timeout))
    return augmented


def _resolve_verbs_for_build_class(build_class: str) -> list[str]:
    """Return the ``architecture resolve --command`` verbs for a build_class.

    The ``build_class`` names the canonical command directly, so it resolves as
    itself — except ``module-tests``, whose test gate is the two-rung ladder
    ``test-compile`` **+** ``module-tests`` (compile the tests, then run them).
    ``none`` is handled by the deriver before this is reached and yields an empty
    verb list here. The single source of truth for this mapping is
    ``manage-architecture/standards/resolve-command.md`` §
    "Build-class → verification command".
    """
    if build_class == 'compile':
        return ['compile']
    if build_class == 'module-tests':
        return ['test-compile', 'module-tests']
    if build_class == 'verify':
        return ['verify']
    return []


def cmd_derive_verification(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for ``derive-verification`` — the single deterministic deriver.

    Reads the merged ``build_map`` from marshal.json, classifies each changed
    artifact's role+build_class (longest-glob-wins), groups by build_class, and
    emits the architecture-resolved verification command set per the
    build_class → command table. The deriver is pure and deterministic: the
    same (changed artifacts, build_map, architecture) always yields the same
    command list. A docs-only changed set derives ZERO Python builds — this is
    what structurally ends the docs-only build recurrence.

    See ``manage-architecture/standards/resolve-command.md`` §
    "Build-class → verification command" for the canonical mapping.
    """
    raw = args.changed_artifacts or ''
    paths = [p.strip() for p in raw.split(',') if p.strip()]
    project_dir = args.project_dir

    merged = load_merged_build_map(project_dir)

    classified: list[dict[str, str]] = []
    unclaimed: list[str] = []
    for path in paths:
        build_class = classify_changed_path(path, merged)
        if build_class is None:
            unclaimed.append(path)
            continue
        classified.append({'path': path, 'build_class': build_class})

    # De-duplicate derived commands by their executable string so a changed set
    # touching N production files in one module derives ONE compile, not N.
    commands: list[dict[str, str]] = []
    seen_executables: set[str] = set()

    for item in classified:
        path = item['path']
        build_class = item['build_class']

        if build_class == 'none':
            continue

        resolve_verbs = _resolve_verbs_for_build_class(build_class)
        if not resolve_verbs:
            # Unknown build_class (should never happen — closed enum). Skip
            # rather than crash; the unclaimed/unknown surface below records it.
            unclaimed.append(path)
            continue

        module_name = resolve_module_for_path(path, project_dir)
        for verb in resolve_verbs:
            try:
                resolved = resolve_command(verb, module_name, project_dir)
            except (ValueError, ModuleNotFoundInProjectError, DataNotFoundError):
                continue
            augmented = _augment_resolved(resolved, project_dir)
            if augmented.get('executable') and augmented['executable'] not in seen_executables:
                seen_executables.add(augmented['executable'])
                commands.append({'build_class': build_class, 'path': path, **augmented})

    return {
        'status': 'success',
        'changed_count': len(paths),
        'classified_count': len(classified),
        'command_count': len(commands),
        'unclaimed': sorted(set(unclaimed)),
        'commands': commands,
    }


def cmd_profiles(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for profiles command.

    Extract unique profile keys from skills_by_profile for given modules.
    Used by marshall-steward to auto-discover profiles for task_executors config.
    """
    try:
        all_modules = iter_modules(args.project_dir)

        if args.modules:
            module_names = [m.strip() for m in args.modules.split(',')]
            for name in module_names:
                if name not in all_modules:
                    raise ModuleNotFoundInProjectError(f'Module not found: {name}', all_modules)
        else:
            module_names = list(all_modules)

        profiles: set[str] = set()
        modules_analyzed: list[str] = []

        for module_name in module_names:
            module_enriched = load_module_enriched_or_empty(module_name, args.project_dir)
            skills_by_profile = module_enriched.get('skills_by_profile', {})
            if skills_by_profile:
                modules_analyzed.append(module_name)
                profiles.update(_extract_profile_keys(skills_by_profile))

        return {
            'status': 'success',
            'count': len(profiles),
            'profiles': sorted(profiles),
            'modules_analyzed': sorted(modules_analyzed),
        }
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError as e:
        try:
            modules = iter_modules(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(str(e), modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_siblings(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for siblings command.

    Find sibling virtual modules for a given module.
    """
    try:
        siblings = get_sibling_modules(args.module, args.project_dir)

        result: dict[str, Any] = {
            'status': 'success',
            'module': args.module,
            'siblings': siblings,
        }

        if not siblings:
            result['note'] = 'Module is not a virtual module or has no siblings'

        return result
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        try:
            modules = get_modules_list(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def _modules_from_exception_or_fallback(exc: ModuleNotFoundInProjectError, project_dir: str) -> list[str]:
    """Prefer the module list embedded in the exception; fall back to a re-read.

    ``ModuleNotFoundInProjectError`` carries the available module names in
    ``args[1]`` when raised from the architecture core helpers. CLI handlers
    that already provoked the exception can reuse that list rather than
    re-loading ``_project.json``. Defensive fallback to ``get_modules_list``
    handles one-arg constructions and unforeseen call sites.
    """
    if len(exc.args) >= 2 and isinstance(exc.args[1], list):
        return list(exc.args[1])
    try:
        return get_modules_list(project_dir)
    except Exception:
        return []


def cmd_path(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for path command."""
    try:
        path = get_module_path(args.source, args.target, args.project_dir)
        return {
            'status': 'success',
            'source': args.source,
            'target': args.target,
            'path': path,
        }
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError as e:
        modules = _modules_from_exception_or_fallback(e, args.project_dir)
        missing = e.args[0].split(': ', 1)[-1] if e.args else args.source
        return error_result_module_not_found(missing, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_neighbors(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for neighbors command."""
    try:
        neighbors = get_module_neighbors(args.module, args.depth, args.project_dir)
        return {
            'status': 'success',
            'module': args.module,
            'depth': min(args.depth, NEIGHBORS_DEPTH_CAP),
            'neighbors': neighbors,
        }
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError as e:
        modules = _modules_from_exception_or_fallback(e, args.project_dir)
        return error_result_module_not_found(args.module, modules)
    except ValueError as e:
        return {'status': 'error', 'error': str(e)}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_impact(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for impact command."""
    try:
        impact = get_module_impact(args.module, args.project_dir)
        return {
            'status': 'success',
            'module': args.module,
            'impact': impact,
        }
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError as e:
        modules = _modules_from_exception_or_fallback(e, args.project_dir)
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


# =============================================================================
# Files Inventory Readers (files / which-module / find)
# =============================================================================


def _flatten_inventory(files_block: dict[str, Any]) -> list[tuple[str, str]]:
    """Flatten a ``files`` block into ``(category, path)`` pairs.

    Elided categories contribute their ``sample`` paths only — callers that
    need the full list must fall back to Glob, which is the documented
    contract of the elision shape.
    """
    pairs: list[tuple[str, str]] = []
    for category, value in files_block.items():
        if isinstance(value, list):
            for path in value:
                pairs.append((category, path))
        elif isinstance(value, dict) and 'sample' in value:
            for path in value['sample']:
                pairs.append((category, path))
    return pairs


def cmd_files(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for the ``files`` reader.

    Loads the target module's ``derived.json`` and returns its ``files``
    block. When ``--category`` is supplied, the response is narrowed to
    that single bucket (and the ``elided``/``sample`` shape is preserved
    verbatim if the bucket was capped).
    """
    try:
        derived = _load_module_or_raise(args.module, args.project_dir)
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        try:
            modules = get_modules_list(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

    files_block = derived.get('files') or {}
    category = getattr(args, 'category', None)

    if category:
        bucket = files_block.get(category)
        if bucket is None:
            return {
                'status': 'success',
                'module': args.module,
                'category': category,
                'files': [],
            }
        return {
            'status': 'success',
            'module': args.module,
            'category': category,
            'files': bucket,
        }

    return {
        'status': 'success',
        'module': args.module,
        'files': files_block,
    }


def cmd_which_module(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for the ``which-module`` reader.

    Resolves a path to its owning module by scanning every module's
    ``files`` inventory. When the path appears in more than one module
    (e.g. paths shared across virtual modules), the tie-breaker is the
    longest ``paths.module`` prefix — so a file under
    ``marketplace/bundles/pm-dev-java/...`` resolves to ``pm-dev-java``,
    not the project-root ``default`` module.
    """
    target = args.path
    try:
        module_names = iter_modules(args.project_dir)
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

    matches: list[tuple[int, str]] = []  # (paths.module length, name)
    for name in module_names:
        try:
            derived = load_module_derived(name, args.project_dir)
        except DataNotFoundError:
            continue
        files_block = derived.get('files') or {}
        for _category, path in _flatten_inventory(files_block):
            if path == target:
                module_path = (derived.get('paths') or {}).get('module') or ''
                matches.append((len(module_path), name))
                break

    if not matches:
        return {
            'status': 'success',
            'path': target,
            'module': None,
        }

    # Longest paths.module prefix wins. ``sorted`` is stable so module names
    # tie-break alphabetically when the prefix length is identical.
    matches.sort(key=lambda item: (-item[0], item[1]))
    return {
        'status': 'success',
        'path': target,
        'module': matches[0][1],
    }


def cmd_find(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for the ``find`` reader.

    Cross-module pattern search across the inventory. ``--pattern`` is
    glob-style (``fnmatch``), case-sensitive, anchored to the full path.
    ``--category`` narrows the search to one bucket. Elided buckets
    contribute their ``sample`` only — the same fallback contract as
    ``files``.
    """
    pattern = args.pattern
    category_filter = getattr(args, 'category', None)

    try:
        module_names = iter_modules(args.project_dir)
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

    results: list[dict[str, str]] = []
    for name in module_names:
        try:
            derived = load_module_derived(name, args.project_dir)
        except DataNotFoundError:
            continue
        files_block = derived.get('files') or {}
        for category, path in _flatten_inventory(files_block):
            if category_filter and category != category_filter:
                continue
            if fnmatch.fnmatchcase(path, pattern):
                results.append({'module': name, 'category': category, 'path': path})

    results.sort(key=lambda item: (item['module'], item['category'], item['path']))

    return {
        'status': 'success',
        'pattern': pattern,
        'category': category_filter,
        'count': len(results),
        'results': results,
    }


# =============================================================================
# Snapshot Diff (diff-modules)
# =============================================================================


def _sha256_file(path: Path) -> str | None:
    """Return the sha256 hexdigest of ``path`` or None when the file is absent."""
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def _sha256_payload(payload: dict[str, Any] | None) -> str | None:
    """Return the sha256 hexdigest of a module's derived payload.

    Computed over the canonical JSON serialisation (``json.dumps(payload,
    sort_keys=True)``) so the digest is byte-identical to what
    ``_write_json`` would have written under the legacy on-disk model. Returns
    ``None`` when the payload is missing.
    """
    if payload is None:
        return None
    canonical = json.dumps(payload, indent=2, sort_keys=True).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()


def _resolve_snapshot_dir(pre: str) -> Path:
    """Resolve a ``--pre`` argument to a snapshot directory.

    The argument may be either the snapshot root containing ``_project.json``
    directly, or a project root whose ``.plan/project-architecture/`` subtree
    holds the snapshot. The first shape that points at an existing
    ``_project.json`` wins; callers handle the no-match case via
    ``snapshot_not_found``.
    """
    base = Path(pre)
    direct = base / FILE_PROJECT_META
    if direct.is_file():
        return base
    nested = base / DATA_DIR / FILE_PROJECT_META
    if nested.is_file():
        return base / DATA_DIR
    # Default to the direct shape so error reporting points at the simpler path.
    return base


def cmd_diff_modules(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for the ``diff-modules`` reader.

    Compares pre-snapshot per-module ``derived.json`` shas (read from the
    on-disk snapshot under ``--pre``) against the sha of the live on-demand
    crawl of the current project's modules, and classifies every module from
    the union of both module sets into one of four buckets: ``added``,
    ``removed``, ``changed``, ``unchanged``.

    The snapshot side keeps its file-based read because the snapshot is an
    on-disk artifact captured at some earlier point. The current side
    computes a fresh crawl-based sha; nothing reads
    ``{module}/derived.json`` from the current project's
    ``project-architecture/`` directory.

    Comparison surface is intentionally narrow — only ``derived.json`` shas
    matter. Differences confined to ``enriched.json`` (LLM-curated fields)
    never produce a ``changed`` classification.

    Error contract: when the snapshot directory or its ``_project.json`` is
    missing, returns ``status: error, error: snapshot_not_found, path: <pre>``.
    """
    pre_arg = args.pre
    snapshot_dir = _resolve_snapshot_dir(pre_arg)
    snapshot_meta_path = snapshot_dir / FILE_PROJECT_META

    if not snapshot_meta_path.is_file():
        return {
            'status': 'error',
            'error': 'snapshot_not_found',
            'path': pre_arg,
        }

    try:
        snapshot_meta = json.loads(snapshot_meta_path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        return {
            'status': 'error',
            'error': 'snapshot_not_found',
            'path': pre_arg,
            'detail': str(e),
        }

    snapshot_modules = set((snapshot_meta.get('modules') or {}).keys())

    current_modules_data = crawl_all_modules(args.project_dir)
    current_modules = set(current_modules_data.keys())
    if not current_modules:
        return require_project_meta_result(args.project_dir)

    added = sorted(current_modules - snapshot_modules)
    removed = sorted(snapshot_modules - current_modules)

    changed: list[str] = []
    unchanged: list[str] = []
    for name in sorted(snapshot_modules & current_modules):
        snap_sha = _sha256_file(snapshot_dir / name / DIR_PER_MODULE_DERIVED)
        # Use the pre-crawled data to avoid O(N^2) project walks: the
        # full crawl happened once above; each iteration just serialises
        # the already-computed payload dict.
        cur_sha = _sha256_payload(current_modules_data.get(name))
        # When the snapshot derived.json is missing on disk, or the live
        # crawl no longer surfaces the module, treat the pair as changed —
        # the index lists the module on both sides but the sha surface cannot
        # certify equality.
        if snap_sha is None or cur_sha is None or snap_sha != cur_sha:
            changed.append(name)
        else:
            unchanged.append(name)

    return {
        'status': 'success',
        'added': added,
        'removed': removed,
        'changed': changed,
        'unchanged': unchanged,
    }


# =============================================================================
# Descriptor Regression Check (descriptor-regression-check)
# =============================================================================


def _is_blanked(baseline_value: Any, current_value: Any) -> bool:
    """Whether a descriptor field transitioned from non-empty to empty.

    Treats ``None`` and whitespace-only strings as empty on both sides, so a
    curated value being wiped to ``''`` (the legacy ``api_discover`` blanking
    behaviour) is the only transition that returns ``True``. A field that was
    already empty in the baseline never counts as regressive.
    """
    had_value = bool((baseline_value or '').strip())
    has_value = bool((current_value or '').strip())
    return had_value and not has_value


def cmd_descriptor_regression_check(args: argparse.Namespace) -> dict[str, Any]:
    """CLI handler for the ``descriptor-regression-check`` commit gate.

    Compares the baseline ``_project.json`` (read from the on-disk snapshot
    under ``--pre``) against the regenerated descriptor at the current
    project's ``.plan/project-architecture/_project.json`` and classifies the
    project-identity delta as regressive or benign. This is the defense-in-depth
    backstop for the ``api_discover`` identity-preservation fix: even if a future
    source path reintroduces the worktree-basename corruption, the
    ``architecture-refresh`` commit gate refuses to commit a regressive delta.

    Regressive predicates (each contributes one ``violations[]`` entry):

    * ``name`` — the baseline carried a curated name AND the regenerated name
      differs from it. A regenerated name equal to the project-dir basename (the
      canonical worktree/plan-id corruption) is reported with that signature; any
      other divergence from the curated baseline name is also regressive.
    * ``description`` — transitioned from non-empty to empty (curated text wiped).
    * ``description_reasoning`` — transitioned from non-empty to empty.

    A benign refresh (identity preserved, only the ``modules`` index changing as
    modules are added/removed) returns ``regressive: false`` with no violations.

    Error contract: when the snapshot directory or its ``_project.json`` is
    missing, returns ``status: error, error: snapshot_not_found, path: <pre>``;
    when the current project's ``_project.json`` is absent, returns the standard
    ``require_project_meta_result`` error.
    """
    pre_arg = args.pre
    snapshot_dir = _resolve_snapshot_dir(pre_arg)
    baseline_meta_path = snapshot_dir / FILE_PROJECT_META

    if not baseline_meta_path.is_file():
        return {
            'status': 'error',
            'error': 'snapshot_not_found',
            'path': pre_arg,
        }

    try:
        baseline_meta = json.loads(baseline_meta_path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        return {
            'status': 'error',
            'error': 'snapshot_not_found',
            'path': pre_arg,
            'detail': str(e),
        }

    try:
        current_meta = load_project_meta(args.project_dir)
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)

    project_basename = Path(args.project_dir).resolve().name

    violations: list[dict[str, str]] = []

    baseline_name = (baseline_meta.get('name') or '').strip()
    current_name = (current_meta.get('name') or '').strip()
    if baseline_name and current_name != baseline_name:
        if current_name == project_basename:
            reason = (
                f'name overwritten with the project-dir basename "{project_basename}" '
                f'(curated name was "{baseline_name}")'
            )
        else:
            reason = f'name changed from curated "{baseline_name}" to "{current_name}"'
        violations.append({'field': 'name', 'reason': reason})

    if _is_blanked(baseline_meta.get('description'), current_meta.get('description')):
        violations.append({'field': 'description', 'reason': 'curated description blanked'})

    if _is_blanked(baseline_meta.get('description_reasoning'), current_meta.get('description_reasoning')):
        violations.append(
            {'field': 'description_reasoning', 'reason': 'curated description_reasoning blanked'}
        )

    return {
        'status': 'success',
        'regressive': bool(violations),
        'violations': violations,
    }
