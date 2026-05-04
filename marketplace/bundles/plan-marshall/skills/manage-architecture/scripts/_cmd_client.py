#!/usr/bin/env python3
"""Client command handlers for architecture script.

Handles: info, modules, graph, path, neighbors, impact, module, overview,
commands, resolve, profiles, siblings, files, which-module, find,
diff-modules.

Persistence model: per-module on-disk layout under
``.plan/project-architecture/``. Readers iterate ``_project.json``'s
``modules`` index and lazy-load per-module ``derived.json`` /
``enriched.json`` on demand via the core helpers.
"""

import fnmatch
import hashlib
import json
from collections import deque
from pathlib import Path
from typing import Any

from _architecture_core import (
    DATA_DIR,
    DataNotFoundError,
    ModuleNotFoundInProjectError,
    error_result_command_not_found,
    error_result_module_not_found,
    get_root_module,
    iter_modules,
    load_module_derived,
    load_module_enriched_or_empty,
    load_project_meta,
    merge_module_data,
    require_project_meta_result,
)
from constants import (  # type: ignore[import-not-found]
    DIR_PER_MODULE_DERIVED,
    FILE_PROJECT_META,
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


def get_module_graph(project_dir: str = '.', full: bool = False) -> dict[str, Any]:
    """Get complete internal module dependency graph with topological layers.

    Uses Kahn's algorithm to compute execution layers where layer 0 contains
    modules with no dependencies, and higher layers depend only on lower layers.
    """
    module_names_all = iter_modules(project_dir)

    # Lazily load each module's derived/enriched data once.
    derived_by_name: dict[str, dict[str, Any]] = {}
    enriched_by_name: dict[str, dict[str, Any]] = {}
    for name in module_names_all:
        try:
            derived_by_name[name] = load_module_derived(name, project_dir)
        except DataNotFoundError:
            derived_by_name[name] = {}
        enriched_by_name[name] = load_module_enriched_or_empty(name, project_dir)

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
            deps = mod_data.get('dependencies', [])
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


def resolve_command(command_name: str, module_name: str | None = None, project_dir: str = '.') -> dict[str, str]:
    """Resolve command to executable form with cascading fallback.

    Resolution order:
    1. Try command at specified module
    2. If not found AND module is not the root module -> try at root module
    3. If still not found -> raise ValueError
    """
    if not module_name:
        module_name = get_root_module(project_dir)
        if not module_name:
            raise ModuleNotFoundInProjectError('No modules found', [])

    derived = _load_module_or_raise(module_name, project_dir)
    commands = derived.get('commands', {})

    if command_name in commands:
        cmd_data = commands[command_name]
        executable = cmd_data if isinstance(cmd_data, str) else cmd_data.get('executable', '')
        return {'module': module_name, 'command': command_name, 'executable': executable, 'resolution_level': 'module'}

    # Cascade: try root module if current module is not already root.
    root_module_name = get_root_module(project_dir)
    if root_module_name and module_name != root_module_name:
        try:
            root_derived = load_module_derived(root_module_name, project_dir)
        except DataNotFoundError:
            root_derived = {}
        root_commands = root_derived.get('commands', {})
        if command_name in root_commands:
            cmd_data = root_commands[command_name]
            executable = cmd_data if isinstance(cmd_data, str) else cmd_data.get('executable', '')
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


def _build_internal_deps_map(project_dir: str = '.') -> tuple[dict[str, list[str]], list[str]]:
    """Build internal_dependencies mapping for all modules.

    Resolution order per module mirrors get_module_graph:
      1. enriched.{X}.internal_dependencies (LLM-curated)
      2. derived.{X}.internal_dependencies (from discover)
      3. computed from derived.{X}.dependencies via groupId:artifactId

    Args:
        project_dir: Project directory path

    Returns:
        Tuple of (deps_map, module_names) where deps_map maps each module name
        to its list of internal dependency module names. Lists are sorted to
        guarantee deterministic traversal order.
    """
    module_names = iter_modules(project_dir)
    derived_by_name: dict[str, dict[str, Any]] = {}
    enriched_by_name: dict[str, dict[str, Any]] = {}
    for name in module_names:
        try:
            derived_by_name[name] = load_module_derived(name, project_dir)
        except DataNotFoundError:
            derived_by_name[name] = {}
        enriched_by_name[name] = load_module_enriched_or_empty(name, project_dir)

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
            deps = mod_data.get('dependencies', [])
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


def _render_project_section(meta: dict) -> list[str]:
    name = meta.get('name', '(unnamed project)')
    description = (meta.get('description') or '').strip()
    lines = [f'# {name}', '']
    if description:
        lines.extend([description, ''])
    return lines


def _render_modules_section(enriched_by_name: dict[str, dict]) -> list[str]:
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


def _render_skills_by_profile_section(enriched_by_name: dict[str, dict]) -> list[str]:
    rows: list[tuple[str, dict]] = []
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
            data = skills_by_profile[profile]
            if isinstance(data, dict):
                defaults = data.get('defaults', [])
                optionals = data.get('optionals', [])
                count = len(defaults) + len(optionals)
            elif isinstance(data, list):
                count = len(data)
            else:
                count = 0
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
    enriched_by_name: dict[str, dict] = {
        name: load_module_enriched_or_empty(name, project_dir) for name in module_names
    }
    deps_map, _ = _build_internal_deps_map(project_dir)

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
) -> str:
    """Render budgeted markdown deep-dive for a single module.

    Sections in priority order: header (name, purpose, responsibility) >
    internal dependencies > key packages > skills_by_profile > tips/insights.

    Args:
        module_name: Module name (None resolves to root module)
        project_dir: Project directory path
        budget: Maximum line count for the rendered markdown

    Returns:
        Markdown string ending with a trailing newline.
    """
    if not module_name:
        module_name = get_root_module(project_dir)
        if not module_name:
            raise ModuleNotFoundInProjectError('No modules found', [])

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

    deps = sorted(merged.get('internal_dependencies', []) or [])
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
            data = skills_by_profile[profile]
            if isinstance(data, dict):
                defaults = data.get('defaults', [])
                optionals = data.get('optionals', [])
                count = len(defaults) + len(optionals)
            elif isinstance(data, list):
                count = len(data)
            else:
                count = 0
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


def _extract_profile_keys(skills_by_profile: dict) -> set[str]:
    """Extract profile keys from skills_by_profile structure."""
    return set(skills_by_profile.keys())


def cmd_info(args) -> dict:
    """CLI handler for info command."""
    try:
        info = get_project_info(args.project_dir)
        return {'status': 'success', **info}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_modules(args) -> dict:
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


def cmd_graph(args) -> dict:
    """CLI handler for graph command."""
    try:
        result = get_module_graph(args.project_dir, args.full)
        return {'status': 'success', **result}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_module(args) -> Any:
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


def cmd_overview(args) -> Any:
    """CLI handler for overview command. Returns markdown string."""
    try:
        budget = getattr(args, 'budget', DEFAULT_OVERVIEW_BUDGET)
        return render_overview(args.project_dir, budget)
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_commands(args) -> dict:
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


def cmd_resolve(args) -> dict:
    """CLI handler for resolve command."""
    try:
        result = resolve_command(args.resolve_command, args.module, args.project_dir)
        return {'status': 'success', **result}
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        try:
            modules = get_modules_list(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except ValueError:
        # Command not found at the resolved module.
        try:
            resolved_module = args.module or get_root_module(args.project_dir) or ''
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


def cmd_profiles(args) -> dict:
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


def cmd_siblings(args) -> dict:
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


def cmd_path(args) -> dict:
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
        try:
            modules = get_modules_list(args.project_dir)
        except Exception:
            modules = []
        missing = e.args[0].split(': ', 1)[-1] if e.args else args.source
        return error_result_module_not_found(missing, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_neighbors(args) -> dict:
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
    except ModuleNotFoundInProjectError:
        try:
            modules = get_modules_list(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except ValueError as e:
        return {'status': 'error', 'error': str(e)}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_impact(args) -> dict:
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
    except ModuleNotFoundInProjectError:
        try:
            modules = get_modules_list(args.project_dir)
        except Exception:
            modules = []
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


# =============================================================================
# Files Inventory Readers (files / which-module / find)
# =============================================================================


def _flatten_inventory(files_block: dict) -> list[tuple[str, str]]:
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


def cmd_files(args) -> dict:
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


def cmd_which_module(args) -> dict:
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


def cmd_find(args) -> dict:
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


def cmd_diff_modules(args) -> dict:
    """CLI handler for the ``diff-modules`` reader.

    Compares per-module ``derived.json`` shas between a snapshot directory
    (``--pre``) and the current project's ``project-architecture/`` tree, and
    classifies every module from the union of both module sets into one of
    four buckets: ``added``, ``removed``, ``changed``, ``unchanged``.

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

    try:
        current_modules = set(iter_modules(args.project_dir))
    except DataNotFoundError:
        return require_project_meta_result(args.project_dir)

    added = sorted(current_modules - snapshot_modules)
    removed = sorted(snapshot_modules - current_modules)

    current_data_dir = Path(args.project_dir) / DATA_DIR

    changed: list[str] = []
    unchanged: list[str] = []
    for name in sorted(snapshot_modules & current_modules):
        snap_sha = _sha256_file(snapshot_dir / name / DIR_PER_MODULE_DERIVED)
        cur_sha = _sha256_file(current_data_dir / name / DIR_PER_MODULE_DERIVED)
        # When a per-module derived.json is missing on either side, treat the
        # pair as changed — the index lists the module but the sha surface
        # cannot certify equality.
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
