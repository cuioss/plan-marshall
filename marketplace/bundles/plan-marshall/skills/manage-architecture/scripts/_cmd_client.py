#!/usr/bin/env python3
"""Client command handlers for architecture script.

Handles: info, modules, graph, module, commands, resolve, path, neighbors,
impact, overview.
These commands merge derived + enriched data for consumer output.
"""

from collections import deque
from typing import Any

from _architecture_core import (
    DataNotFoundError,
    ModuleNotFoundInProjectError,
    error_result_command_not_found,
    error_result_module_not_found,
    get_module,
    get_module_names,
    get_root_module,
    load_derived_data,
    load_llm_enriched_or_empty,
    merge_module_data,
    require_derived_data_result,
)

NEIGHBORS_DEPTH_CAP = 8
DEFAULT_OVERVIEW_BUDGET = 200

# =============================================================================
# API Functions
# =============================================================================


def get_project_info(project_dir: str = '.') -> dict[str, Any]:
    """Get project summary with metadata and module overview.

    Args:
        project_dir: Project directory path

    Returns:
        Dict with project info, technologies, and module overview
    """
    derived = load_derived_data(project_dir)
    enriched = load_llm_enriched_or_empty(project_dir)

    project = derived.get('project', {})
    enriched_project = enriched.get('project', {})

    # Collect unique build systems
    technologies = set()
    modules_data = derived.get('modules', {})
    for module in modules_data.values():
        for bs in module.get('build_systems', []):
            technologies.add(bs)

    # Build module overview with enriched purpose
    module_overview: list[dict[str, Any]] = []
    enriched_modules = enriched.get('modules', {})
    for name, data in modules_data.items():
        paths = data.get('paths', {})
        enriched_module = enriched_modules.get(name, {})
        module_overview.append(
            {'name': name, 'path': paths.get('module', ''), 'purpose': enriched_module.get('purpose', '')}
        )

    return {
        'project': {'name': project.get('name', ''), 'description': enriched_project.get('description', '')},
        'technologies': sorted(technologies),
        'modules': module_overview,
    }


def get_modules_list(project_dir: str = '.') -> list[str]:
    """Get list of module names.

    Args:
        project_dir: Project directory path

    Returns:
        List of module names
    """
    derived = load_derived_data(project_dir)
    return get_module_names(derived)


def get_modules_with_command(command_name: str, project_dir: str = '.') -> list[str]:
    """Get list of module names that provide a specific command.

    Args:
        command_name: Command name to filter by
        project_dir: Project directory path

    Returns:
        List of module names that have the specified command
    """
    derived = load_derived_data(project_dir)
    modules_with_command: list[str] = []

    for module_name, module_data in derived.get('modules', {}).items():
        commands = module_data.get('commands', {})
        if command_name in commands:
            modules_with_command.append(module_name)

    return modules_with_command


def get_modules_by_physical_path(physical_path: str, project_dir: str = '.') -> list[str]:
    """Get list of module names at a specific physical path.

    For virtual modules, multiple modules may share the same physical path.

    Args:
        physical_path: Physical directory path to filter by
        project_dir: Project directory path

    Returns:
        List of module names at the specified physical path
    """
    derived = load_derived_data(project_dir)
    modules_at_path: list[str] = []

    for module_name, module_data in derived.get('modules', {}).items():
        # Check virtual_module.physical_path first
        virtual = module_data.get('virtual_module', {})
        mod_physical_path = virtual.get('physical_path') if virtual else None

        # Fall back to paths.module
        if not mod_physical_path:
            paths = module_data.get('paths', {})
            mod_physical_path = paths.get('module', '.')

        if mod_physical_path == physical_path:
            modules_at_path.append(module_name)

    return modules_at_path


def get_sibling_modules(module_name: str, project_dir: str = '.') -> list[str]:
    """Get sibling virtual modules for a given module.

    Args:
        module_name: Module name to find siblings for
        project_dir: Project directory path

    Returns:
        List of sibling module names (empty if not a virtual module)
    """
    derived = load_derived_data(project_dir)
    module = get_module(derived, module_name)

    virtual = module.get('virtual_module', {})
    siblings: list[str] = virtual.get('sibling_modules', [])
    return siblings


def get_module_graph(project_dir: str = '.', full: bool = False) -> dict[str, Any]:
    """Get complete internal module dependency graph with topological layers.

    Uses Kahn's algorithm to compute execution layers where layer 0 contains
    modules with no dependencies, and higher layers depend only on lower layers.

    Args:
        project_dir: Project directory path
        full: Include aggregator modules (pom-only parents). Default filters them out.

    Returns:
        Dict with graph structure: nodes, edges, layers, roots, leaves
    """
    derived = load_derived_data(project_dir)
    enriched = load_llm_enriched_or_empty(project_dir)
    enriched_modules = enriched.get('modules', {})

    modules_data = derived.get('modules', {})

    # Build mapping of groupId:artifactId -> module_name for internal dep detection
    # This allows us to identify which dependencies are internal to the project
    artifact_to_module: dict[str, str] = {}
    for mod_name, mod_data in modules_data.items():
        metadata = mod_data.get('metadata', {})
        group_id = metadata.get('group_id')
        artifact_id = metadata.get('artifact_id')
        if group_id and artifact_id:
            artifact_to_module[f'{group_id}:{artifact_id}'] = mod_name

    # Compute internal_dependencies for each module from its dependencies list
    internal_deps_map: dict[str, list[str]] = {}
    for mod_name, mod_data in modules_data.items():
        # Check enriched data first (LLM-curated internal deps)
        enriched_mod = enriched_modules.get(mod_name, {})
        if 'internal_dependencies' in enriched_mod:
            internal_deps_map[mod_name] = enriched_mod['internal_dependencies']
        # Check derived data next (from discover command)
        elif 'internal_dependencies' in mod_data:
            internal_deps_map[mod_name] = mod_data['internal_dependencies']
        else:
            # Compute from dependencies list (deduplicated)
            deps = mod_data.get('dependencies', [])
            internal = set()  # Use set to deduplicate
            for dep in deps:
                # Format: groupId:artifactId:scope or groupId:artifactId:version:scope
                parts = dep.split(':')
                if len(parts) >= 2:
                    ga = f'{parts[0]}:{parts[1]}'
                    if ga in artifact_to_module:
                        dep_module = artifact_to_module[ga]
                        if dep_module != mod_name:  # Don't include self
                            internal.add(dep_module)
            internal_deps_map[mod_name] = list(internal)

    # Filter out aggregator modules unless --full is specified
    # Aggregators are pom-packaging modules (not jar, nar, war, etc.)
    # BUT enriched data can mark pom modules as is_leaf to override filtering
    if full:
        module_names: list[str] = list(modules_data.keys())
        filtered_out: list[str] = []
    else:
        module_names = []
        filtered_out = []
        for name, data in modules_data.items():
            metadata = data.get('metadata', {})
            packaging = metadata.get('packaging', 'jar')
            enriched_mod = enriched_modules.get(name, {})

            # Check if enriched data marks this as a leaf (overrides packaging filter)
            is_leaf = enriched_mod.get('is_leaf', False)
            # Also check purpose - integration-tests/deployment/benchmark are leaves
            purpose = enriched_mod.get('purpose', '')
            is_purpose_leaf = purpose in ['integration-tests', 'e2e', 'deployment', 'benchmark']

            # Include if: non-pom packaging OR marked as leaf OR purpose indicates leaf
            if packaging != 'pom' or is_leaf or is_purpose_leaf:
                module_names.append(name)
            else:
                filtered_out.append(name)

    # Build adjacency list and in-degree count
    # Edge direction: from dependency TO dependent (for topological sort)
    in_degree: dict[str, int] = dict.fromkeys(module_names, 0)
    dependents: dict[str, list[str]] = {name: [] for name in module_names}  # who depends on this module

    edges: list[dict[str, str]] = []
    for module_name in module_names:
        internal_deps = internal_deps_map.get(module_name, [])
        for dep in internal_deps:
            if dep in module_names:
                # module_name depends on dep
                # Edge: dep -> module_name (dep must be built before module_name)
                edges.append({'from': dep, 'to': module_name})
                in_degree[module_name] += 1
                dependents[dep].append(module_name)

    # Kahn's algorithm for topological sort with layer assignment
    layers: list[dict[str, Any]] = []
    remaining = set(module_names)
    node_layers: dict[str, int] = {}

    # Find all nodes with no dependencies (layer 0)
    current_layer = [name for name in module_names if in_degree[name] == 0]

    layer_num = 0
    while current_layer:
        layers.append({'layer': layer_num, 'modules': sorted(current_layer)})
        for name in current_layer:
            node_layers[name] = layer_num
            remaining.discard(name)

        # Find next layer: nodes whose dependencies are all processed
        next_layer = []
        for name in current_layer:
            for dependent in dependents[name]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0 and dependent in remaining:
                    next_layer.append(dependent)
                    remaining.discard(dependent)

        current_layer = next_layer
        layer_num += 1

    # Check for circular dependencies
    circular_deps: list[str] | None = list(remaining) if remaining else None

    # Build nodes with layer and purpose
    nodes: list[dict[str, Any]] = []
    for name in module_names:
        enriched_module = enriched_modules.get(name, {})
        nodes.append(
            {
                'name': name,
                'purpose': enriched_module.get('purpose', ''),
                'layer': node_layers.get(name, -1),  # -1 indicates circular dependency
            }
        )

    # Identify roots (no dependencies) and leaves (nothing depends on them)
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
    """Get module information merged from derived + enriched data.

    Args:
        module_name: Module name (None for root module)
        full: Include all fields (packages, dependencies, reasoning)
        project_dir: Project directory path

    Returns:
        Merged module data dict
    """
    derived = load_derived_data(project_dir)
    enriched = load_llm_enriched_or_empty(project_dir)

    # Default to root module
    if not module_name:
        module_name = get_root_module(derived)
        if not module_name:
            raise ModuleNotFoundInProjectError('No modules found', [])

    # Merge data
    merged = merge_module_data(derived, enriched, module_name)

    # Filter fields based on full flag
    if not full:
        # Remove reasoning fields and full package/dependency lists
        reasoning_fields = [
            'responsibility_reasoning',
            'purpose_reasoning',
            'key_dependencies_reasoning',
            'skills_by_profile_reasoning',
        ]
        for field in reasoning_fields:
            merged.pop(field, None)

        # Keep only key_packages, not all packages
        merged.pop('packages', None)

        # Keep only key_dependencies (already in enriched)
        merged.pop('dependencies', None)

    return merged


def get_module_commands(module_name: str | None = None, project_dir: str = '.') -> dict[str, Any]:
    """Get available commands for a module.

    Args:
        module_name: Module name (None for root module)
        project_dir: Project directory path

    Returns:
        Dict with module name and commands list
    """
    derived = load_derived_data(project_dir)

    # Default to root module
    if not module_name:
        module_name = get_root_module(derived)
        if not module_name:
            raise ModuleNotFoundInProjectError('No modules found', [])

    module = get_module(derived, module_name)
    commands = module.get('commands', {})

    # Build command list with descriptions
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

    Args:
        command_name: Command name to resolve
        module_name: Module name (None for root module)
        project_dir: Project directory path

    Returns:
        Dict with module, command, executable, and resolution_level
    """
    derived = load_derived_data(project_dir)

    # Default to root module
    if not module_name:
        module_name = get_root_module(derived)
        if not module_name:
            raise ModuleNotFoundInProjectError('No modules found', [])

    module = get_module(derived, module_name)
    commands = module.get('commands', {})

    if command_name in commands:
        cmd_data = commands[command_name]
        executable = cmd_data if isinstance(cmd_data, str) else cmd_data.get('executable', '')
        return {'module': module_name, 'command': command_name, 'executable': executable, 'resolution_level': 'module'}

    # Cascade: try root module if current module is not already root
    root_module_name = get_root_module(derived)
    if root_module_name and module_name != root_module_name:
        root_module = get_module(derived, root_module_name)
        root_commands = root_module.get('commands', {})
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
      1. enriched.modules.{X}.internal_dependencies (LLM-curated)
      2. derived.modules.{X}.internal_dependencies (from discover)
      3. computed from derived.modules.{X}.dependencies via groupId:artifactId

    Args:
        project_dir: Project directory path

    Returns:
        Tuple of (deps_map, module_names) where deps_map maps each module name
        to its list of internal dependency module names. Lists are sorted to
        guarantee deterministic traversal order.
    """
    derived = load_derived_data(project_dir)
    enriched = load_llm_enriched_or_empty(project_dir)
    enriched_modules = enriched.get('modules', {})
    modules_data = derived.get('modules', {})

    artifact_to_module: dict[str, str] = {}
    for mod_name, mod_data in modules_data.items():
        metadata = mod_data.get('metadata', {})
        group_id = metadata.get('group_id')
        artifact_id = metadata.get('artifact_id')
        if group_id and artifact_id:
            artifact_to_module[f'{group_id}:{artifact_id}'] = mod_name

    deps_map: dict[str, list[str]] = {}
    for mod_name, mod_data in modules_data.items():
        enriched_mod = enriched_modules.get(mod_name, {})
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

    return deps_map, list(modules_data.keys())


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


def _render_project_section(derived: dict, enriched: dict) -> list[str]:
    project = derived.get('project', {})
    enriched_project = enriched.get('project', {})
    name = project.get('name', '(unnamed project)')
    description = enriched_project.get('description', '').strip()
    lines = [f'# {name}', '']
    if description:
        lines.extend([description, ''])
    return lines


def _render_modules_section(derived: dict, enriched: dict) -> list[str]:
    modules_data = derived.get('modules', {})
    enriched_modules = enriched.get('modules', {})
    if not modules_data:
        return []

    lines = ['## Modules', '', '| Module | Purpose | Responsibility |', '|---|---|---|']
    for name in sorted(modules_data.keys()):
        enriched_mod = enriched_modules.get(name, {})
        purpose = enriched_mod.get('purpose', '').strip() or '—'
        responsibility = enriched_mod.get('responsibility', '').strip()
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


def _render_skills_by_profile_section(enriched: dict) -> list[str]:
    enriched_modules = enriched.get('modules', {})
    rows: list[tuple[str, dict]] = []
    for name in sorted(enriched_modules.keys()):
        skills_by_profile = enriched_modules[name].get('skills_by_profile', {})
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
    derived = load_derived_data(project_dir)
    enriched = load_llm_enriched_or_empty(project_dir)
    deps_map, _ = _build_internal_deps_map(project_dir)

    sections = [
        _render_project_section(derived, enriched),
        _render_modules_section(derived, enriched),
        _render_adjacency_section(deps_map),
        _render_skills_by_profile_section(enriched),
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
    derived = load_derived_data(project_dir)
    enriched = load_llm_enriched_or_empty(project_dir)

    if not module_name:
        module_name = get_root_module(derived)
        if not module_name:
            raise ModuleNotFoundInProjectError('No modules found', [])

    # Validate the module exists; raises ModuleNotFoundInProjectError otherwise
    get_module(derived, module_name)
    merged = merge_module_data(derived, enriched, module_name)

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
        return require_derived_data_result(args.project_dir)
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
        return require_derived_data_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_graph(args) -> dict:
    """CLI handler for graph command."""
    try:
        result = get_module_graph(args.project_dir, args.full)
        return {'status': 'success', **result}
    except DataNotFoundError:
        return require_derived_data_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_module(args) -> Any:
    """CLI handler for module command.

    Returns a TOON dict by default. When `--full --budget N` is supplied, returns
    a markdown string for a token-bounded module deep-dive instead. `--budget`
    without `--full` is silently a no-op (TOON output, identical to plain `--full`).
    """
    try:
        derived = load_derived_data(args.project_dir)
        module_name = args.module or get_root_module(derived)
        budget = getattr(args, 'budget', None)
        if args.full and budget is not None:
            return render_module_markdown(module_name, args.project_dir, budget)
        module = get_module_info(module_name, args.full, args.project_dir)
        return {'status': 'success', 'module': module}
    except DataNotFoundError:
        return require_derived_data_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        modules = get_modules_list(args.project_dir)
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_overview(args) -> Any:
    """CLI handler for overview command. Returns markdown string."""
    try:
        budget = getattr(args, 'budget', DEFAULT_OVERVIEW_BUDGET)
        return render_overview(args.project_dir, budget)
    except DataNotFoundError:
        return require_derived_data_result(args.project_dir)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_commands(args) -> dict:
    """CLI handler for commands command."""
    try:
        result = get_module_commands(args.module, args.project_dir)
        return {'status': 'success', **result}
    except DataNotFoundError:
        return require_derived_data_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        modules = get_modules_list(args.project_dir)
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_resolve(args) -> dict:
    """CLI handler for resolve command."""
    try:
        result = resolve_command(args.resolve_command, args.module, args.project_dir)
        return {'status': 'success', **result}
    except DataNotFoundError:
        return require_derived_data_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        modules = get_modules_list(args.project_dir)
        return error_result_module_not_found(args.module, modules)
    except ValueError:
        # Command not found
        derived = load_derived_data(args.project_dir)
        resolved_module: str = args.module or get_root_module(derived) or ''
        module = get_module(derived, resolved_module)
        commands = list(module.get('commands', {}).keys())
        return error_result_command_not_found(resolved_module, args.resolve_command, commands)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def cmd_profiles(args) -> dict:
    """CLI handler for profiles command.

    Extract unique profile keys from skills_by_profile for given modules.
    Used by marshall-steward to auto-discover profiles for task_executors config.
    """
    try:
        derived = load_derived_data(args.project_dir)
        enriched = load_llm_enriched_or_empty(args.project_dir)
        enriched_modules = enriched.get('modules', {})

        # Determine which modules to analyze
        if args.modules:
            module_names = [m.strip() for m in args.modules.split(',')]
            # Validate module names
            all_modules = get_module_names(derived)
            for name in module_names:
                if name not in all_modules:
                    raise ModuleNotFoundInProjectError(f'Module not found: {name}', all_modules)
        else:
            # Default: all modules with enrichment data
            module_names = list(enriched_modules.keys())

        # Collect unique profiles from skills_by_profile
        profiles: set[str] = set()
        modules_analyzed = []

        for module_name in module_names:
            module_enriched = enriched_modules.get(module_name, {})
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
        return require_derived_data_result(args.project_dir)
    except ModuleNotFoundInProjectError as e:
        modules = get_module_names(load_derived_data(args.project_dir))
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
        return require_derived_data_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        modules = get_modules_list(args.project_dir)
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
        return require_derived_data_result(args.project_dir)
    except ModuleNotFoundInProjectError as e:
        modules = get_modules_list(args.project_dir)
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
        return require_derived_data_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        modules = get_modules_list(args.project_dir)
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
        return require_derived_data_result(args.project_dir)
    except ModuleNotFoundInProjectError:
        modules = get_modules_list(args.project_dir)
        return error_result_module_not_found(args.module, modules)
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
