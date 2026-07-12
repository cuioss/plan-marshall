#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Project / module query API and dependency-graph traversal.

Extracted verbatim from ``_cmd_client``; the facade re-exports every public
name here. Covers project/module info readers, the lazy per-module Maven
enrichment cache, command resolution, the internal-dependency graph, and the
BFS path / neighbor / impact traversals.

The per-process ``_ENRICH_CACHE`` lives here and is re-exported (by identity)
from ``_cmd_client`` so ``_cmd_client._ENRICH_CACHE.clear()`` mutates the same
object the enrichment helpers read.
"""

from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

from _architecture_core import (
    DataNotFoundError,
    ModuleNotFoundInProjectError,
    get_root_module,
    iter_modules,
    load_module_derived,
    load_module_enriched_or_empty,
    load_project_meta,
    merge_module_data,
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
        from _maven_cmd_discover import enrich_maven_module
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
        from _maven_cmd_discover import _build_commands
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


# =============================================================================
# skills_by_profile staleness guard (read-path, non-blocking WARNING)
# =============================================================================
#
# The enriched ``skills_by_profile`` map can drift out of sync with the live
# skill registry: a skill can be renamed or retired while a module's
# enriched.json still references the old ``bundle:skill`` notation, or a module
# can carry no ``skills_by_profile`` at all. Neither case is fatal — task
# planning still runs — so the guard surfaces a non-blocking WARNING on the
# module read path rather than raising. Registry resolution is deferred and
# fail-safe: when the bundle root cannot be located (e.g. a unit test running
# outside a bundle tree) the stale-notation check is skipped, but the
# missing/empty check still fires because it needs no registry.


def _iter_skill_notations(skills_by_profile: dict[str, Any]) -> list[str]:
    """Collect every ``bundle:skill`` notation referenced by a skills_by_profile map."""
    notations: list[str] = []
    for profile_data in skills_by_profile.values():
        if not isinstance(profile_data, dict):
            continue
        for section in ('defaults', 'optionals'):
            for entry in profile_data.get(section, []):
                if isinstance(entry, dict):
                    skill = entry.get('skill', '')
                elif isinstance(entry, str):
                    skill = entry
                else:
                    skill = ''
                if skill:
                    notations.append(skill)
    return notations


def detect_stale_skills_by_profile(
    module_name: str, skills_by_profile: dict[str, Any], is_live: Callable[[str], bool]
) -> list[str]:
    """Return non-blocking WARNING messages for a stale or missing skills_by_profile map.

    Two independent signals are surfaced:

    * The map is missing entirely or empty.
    * The map references one or more skill notations that ``is_live`` reports as
      absent from the live registry (retired / renamed IDs).

    ``is_live`` is injected so the check is deterministic and unit-testable
    without a real bundle tree. Returns an empty list when the map is present
    and every notation resolves.
    """
    if not isinstance(skills_by_profile, dict):
        return [f"module '{module_name}': skills_by_profile is malformed (expected a dictionary)"]
    if not skills_by_profile:
        return [f"module '{module_name}': skills_by_profile is missing or empty"]
    stale = sorted({n for n in _iter_skill_notations(skills_by_profile) if not is_live(n)})
    if stale:
        return [
            f"module '{module_name}': skills_by_profile references skill notations "
            f'absent from the live registry: {", ".join(stale)}'
        ]
    return []


def _skill_notation_is_live(notation: str, bundles_root: Path) -> bool:
    """Whether a ``bundle:skill`` notation resolves to a real SKILL.md under ``bundles_root``."""
    bundle, sep, skill = notation.partition(':')
    if not sep or not bundle or not skill:
        return False
    try:
        from marketplace_bundles import resolve_bundle_path

        return resolve_bundle_path(bundles_root, bundle, f'skills/{skill}/SKILL.md').exists()
    except Exception:
        return False


def _emit_skills_by_profile_staleness_warning(module_name: str, merged: dict[str, Any]) -> None:
    """Emit a non-blocking WARNING when ``merged``'s skills_by_profile is stale or missing."""
    skills_by_profile = merged.get('skills_by_profile', {})

    if skills_by_profile:
        try:
            from marketplace_bundles import resolve_bundles_root

            bundles_root = resolve_bundles_root(Path(__file__))
        except Exception:
            return  # registry root unresolvable — skip the stale-notation check (fail-safe)

        def is_live(notation: str) -> bool:
            return _skill_notation_is_live(notation, bundles_root)
    else:

        def is_live(notation: str) -> bool:
            return True  # unused: an empty map warns without a registry lookup

    for message in detect_stale_skills_by_profile(module_name, skills_by_profile, is_live):
        try:
            from plan_logging import log_entry

            log_entry('script', None, 'WARNING', f'[STALENESS] {message}')
        except Exception:
            pass


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

    # Read-path staleness guard: non-blocking WARNING when skills_by_profile is
    # stale (retired notations) or missing entirely. Never raises.
    _emit_skills_by_profile_staleness_warning(module_name, merged)

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
