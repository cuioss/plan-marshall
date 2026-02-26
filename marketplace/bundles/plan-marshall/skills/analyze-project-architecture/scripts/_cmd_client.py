#!/usr/bin/env python3
"""Client command handlers for architecture script.

Handles: info, modules, graph, module, commands, resolve
These commands merge derived + enriched data for consumer output.
"""

import sys
from typing import Any

from _architecture_core import (
    DataNotFoundError,
    ModuleNotFoundError,
    error_command_not_found,
    error_data_not_found,
    error_module_not_found,
    get_derived_path,
    get_module,
    get_module_names,
    get_root_module,
    load_derived_data,
    load_llm_enriched_or_empty,
    merge_module_data,
    print_toon_list,
    print_toon_table,
)

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
            is_purpose_leaf = purpose in ['integration-tests', 'deployment', 'benchmark']

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
            raise ModuleNotFoundError('No modules found', [])

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
            raise ModuleNotFoundError('No modules found', [])

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
    2. If not found AND module is not the root module → try at root module
    3. If still not found → raise ValueError

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
            raise ModuleNotFoundError('No modules found', [])

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
# CLI Handlers
# =============================================================================


def cmd_info(args) -> int:
    """CLI handler for info command."""
    try:
        info = get_project_info(args.project_dir)

        # Output project info
        print('project:')
        print(f'  name: {info["project"]["name"]}')
        print(f'  description: {info["project"]["description"]}')
        print()

        # Output technologies
        print_toon_list('technologies', info['technologies'])
        print()

        # Output modules table
        print_toon_table('modules', info['modules'], ['name', 'path', 'purpose'])

        return 0
    except DataNotFoundError:
        error_data_not_found(str(get_derived_path(args.project_dir)), "Run 'architecture.py discover' first")
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1


def cmd_modules(args) -> int:
    """CLI handler for modules command."""
    try:
        command_filter = getattr(args, 'filter_command', None)
        physical_path_filter = getattr(args, 'physical_path', None)

        if command_filter:
            # Filter modules by command availability
            modules = get_modules_with_command(command_filter, args.project_dir)
            print(f'command: {command_filter}')
            print()
        elif physical_path_filter:
            # Filter modules by physical path (for virtual modules)
            modules = get_modules_by_physical_path(physical_path_filter, args.project_dir)
            print(f'physical_path: {physical_path_filter}')
            print()
        else:
            # List all modules
            modules = get_modules_list(args.project_dir)

        print_toon_list('modules', modules)
        return 0
    except DataNotFoundError:
        error_data_not_found(str(get_derived_path(args.project_dir)), "Run 'architecture.py discover' first")
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1


def cmd_graph(args) -> int:
    """CLI handler for graph command."""
    try:
        result = get_module_graph(args.project_dir, args.full)
        nodes = result['nodes']
        edges = result['edges']

        print('status: success')
        print()

        # Single module: just print the name
        if len(nodes) == 1:
            print(f'module: {nodes[0]["name"]}')
            return 0

        # Build dependency lookup: what does each module depend on
        dependencies: dict[str, list[str]] = {n['name']: [] for n in nodes}
        for edge in edges:
            # edge['from'] depends on edge['to']
            dependencies[edge['to']].append(edge['from'])

        # Print each leaf module with its dependency tree
        leaves = result['leaves']
        printed = set()

        def print_deps(module_name: str, indent: int = 0):
            """Print module and its dependencies with indentation."""
            prefix = '  ' * indent
            if indent > 0:
                print(f'{prefix}- {module_name}')
            else:
                print(module_name)

            if module_name in printed:
                return
            printed.add(module_name)

            # Get what this module depends on
            deps = sorted(dependencies.get(module_name, []))
            for dep in deps:
                print_deps(dep, indent + 1)

        for i, leaf in enumerate(sorted(leaves)):
            if i > 0:
                print()
            print_deps(leaf)

        # Circular dependencies warning
        if result.get('circular_dependencies'):
            print()
            print('warning: circular_dependencies_detected')
            print_toon_list('circular_dependencies', result['circular_dependencies'])

        return 0
    except DataNotFoundError:
        error_data_not_found(str(get_derived_path(args.project_dir)), "Run 'architecture.py discover' first")
        return 1
    except Exception as e:
        print('status: error', file=sys.stderr)
        print(f'error: {e}', file=sys.stderr)
        return 1


def cmd_module(args) -> int:
    """CLI handler for module command."""
    try:
        derived = load_derived_data(args.project_dir)
        module_name = args.name or get_root_module(derived)

        module = get_module_info(module_name, args.full, args.project_dir)

        # Output module info
        print('module:')
        print(f'  name: {module.get("name", module_name)}')
        if module.get('responsibility'):
            print(f'  responsibility: {module["responsibility"]}')
        if args.full and module.get('responsibility_reasoning'):
            print(f'  responsibility_reasoning: {module["responsibility_reasoning"]}')
        if module.get('purpose'):
            print(f'  purpose: {module["purpose"]}')
        if args.full and module.get('purpose_reasoning'):
            print(f'  purpose_reasoning: {module["purpose_reasoning"]}')
        paths = module.get('paths', {})
        print(f'  path: {paths.get("module", "")}')
        print()

        # Output paths
        print('paths:')
        sources = paths.get('sources', [])
        if sources:
            print(f'  sources[{len(sources)}]:')
            for s in sources:
                print(f'    - {s}')
        tests = paths.get('tests', [])
        if tests:
            print(f'  tests[{len(tests)}]:')
            for t in tests:
                print(f'    - {t}')
        if paths.get('descriptor'):
            print(f'  descriptor: {paths["descriptor"]}')
        print()

        # Output key_packages
        key_packages = module.get('key_packages', {})
        if key_packages:
            pkg_items = []
            for pkg_name, pkg_data in key_packages.items():
                desc = pkg_data.get('description', '') if isinstance(pkg_data, dict) else ''
                pkg_items.append({'name': pkg_name, 'description': desc})
            print_toon_table('key_packages', pkg_items, ['name', 'description'])
            print()

        # Full mode: all packages
        if args.full:
            packages = module.get('packages', {})
            if packages:
                pkg_items = []
                for pkg_name, pkg_data in packages.items():
                    has_info = 'true' if pkg_data.get('package_info') else 'false'
                    file_count = str(len(pkg_data.get('files', [])))
                    pkg_items.append({
                        'name': pkg_name,
                        'path': pkg_data.get('path', ''),
                        'has_package_info': has_info,
                        'file_count': file_count,
                    })
                print_toon_table('packages', pkg_items, ['name', 'path', 'has_package_info', 'file_count'])
                print()

        # Output key_dependencies
        key_deps = module.get('key_dependencies', [])
        if key_deps:
            print_toon_list('key_dependencies', key_deps)
        if args.full and module.get('key_dependencies_reasoning'):
            print(f'key_dependencies_reasoning: {module["key_dependencies_reasoning"]}')
        print()

        # Full mode: all dependencies
        if args.full:
            deps = module.get('dependencies', [])
            if deps:
                dep_items = []
                for dep in deps[:30]:  # Limit display
                    parts = dep.split(':')
                    if len(parts) >= 3:
                        dep_items.append(
                            {'artifact': f'{parts[0]}:{parts[1]}', 'scope': parts[2] if len(parts) > 2 else ''}
                        )
                print_toon_table('dependencies', dep_items, ['artifact', 'scope'])
                if len(deps) > 30:
                    print(f'  ... and {len(deps) - 30} more')
                print()

        # Output internal_dependencies
        internal_deps = module.get('internal_dependencies', [])
        print_toon_list('internal_dependencies', internal_deps)
        print()

        # Output skills_by_profile (supports both flat and structured formats)
        skills_by_profile = module.get('skills_by_profile', {})
        if skills_by_profile:
            print('skills_by_profile:')
            for profile, profile_data in skills_by_profile.items():
                print(f'  {profile}:')
                if isinstance(profile_data, list):
                    # Legacy flat format
                    for skill in profile_data:
                        print(f'    - {skill}')
                elif isinstance(profile_data, dict):
                    # New structured format with defaults/optionals
                    defaults = profile_data.get('defaults', [])
                    optionals = profile_data.get('optionals', [])
                    if defaults:
                        print(f'    defaults[{len(defaults)}]{{skill,description}}:')
                        for entry in defaults:
                            if isinstance(entry, dict):
                                skill = entry.get('skill', '')
                                desc = entry.get('description', '')
                                print(f'      - {skill},"{desc}"')
                            else:
                                print(f'      - {entry}')
                    if optionals:
                        print(f'    optionals[{len(optionals)}]{{skill,description}}:')
                        for entry in optionals:
                            if isinstance(entry, dict):
                                skill = entry.get('skill', '')
                                desc = entry.get('description', '')
                                print(f'      - {skill},"{desc}"')
                            else:
                                print(f'      - {entry}')
        if args.full and module.get('skills_by_profile_reasoning'):
            print(f'skills_by_profile_reasoning: {module["skills_by_profile_reasoning"]}')
        print()

        # Output commands
        commands = module.get('commands', {})
        if commands:
            print_toon_list('commands', list(commands.keys()))

        return 0
    except DataNotFoundError:
        error_data_not_found(str(get_derived_path(args.project_dir)), "Run 'architecture.py discover' first")
        return 1
    except ModuleNotFoundError:
        modules = get_modules_list(args.project_dir)
        error_module_not_found(args.name, modules)
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1


def cmd_commands(args) -> int:
    """CLI handler for commands command."""
    try:
        result = get_module_commands(args.name, args.project_dir)

        print(f'module: {result["module"]}')
        print()
        print_toon_table('commands', result['commands'], ['name', 'description'])

        return 0
    except DataNotFoundError:
        error_data_not_found(str(get_derived_path(args.project_dir)), "Run 'architecture.py discover' first")
        return 1
    except ModuleNotFoundError:
        modules = get_modules_list(args.project_dir)
        error_module_not_found(args.name, modules)
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1


def cmd_resolve(args) -> int:
    """CLI handler for resolve command."""
    try:
        result = resolve_command(args.resolve_command, args.name, args.project_dir)

        print(f'module: {result["module"]}')
        print(f'command: {result["command"]}')
        print(f'executable: {result["executable"]}')
        print(f'resolution_level: {result["resolution_level"]}')

        return 0
    except DataNotFoundError:
        error_data_not_found(str(get_derived_path(args.project_dir)), "Run 'architecture.py discover' first")
        return 1
    except ModuleNotFoundError:
        modules = get_modules_list(args.project_dir)
        error_module_not_found(args.name, modules)
        return 1
    except ValueError:
        # Command not found
        derived = load_derived_data(args.project_dir)
        resolved_module: str = args.name or get_root_module(derived) or ''
        module = get_module(derived, resolved_module)
        commands = list(module.get('commands', {}).keys())
        error_command_not_found(resolved_module, args.resolve_command, commands)
        return 1
    except Exception as e:
        print('status\terror', file=sys.stderr)
        print(f'error\t{e}', file=sys.stderr)
        return 1


def _extract_profile_keys(skills_by_profile: dict) -> set[str]:
    """Extract profile keys from skills_by_profile structure.

    Handles both flat format {"profile": [...]} and
    structured format {"profile": {"defaults": [...], "optionals": [...]}}.

    Args:
        skills_by_profile: Dict mapping profile names to skill lists or structured dicts

    Returns:
        Set of profile key names
    """
    return set(skills_by_profile.keys())


def _flatten_skills_by_profile(skills_by_profile: dict, include_optionals: bool = False) -> dict[str, list[str]]:
    """Flatten skills_by_profile to simple profile->skill_list mapping.

    Useful for consumers that need flat lists (defaults only by default).

    Args:
        skills_by_profile: Dict mapping profile names to skill lists or structured dicts
        include_optionals: Whether to include optional skills (default: False, only defaults)

    Returns:
        Dict mapping profile names to flat skill name lists
    """
    result: dict[str, list[str]] = {}
    for profile_name, profile_data in skills_by_profile.items():
        skills: list[str] = []
        if isinstance(profile_data, list):
            # Legacy flat format - all skills are "defaults"
            skills = profile_data
        elif isinstance(profile_data, dict):
            # New structured format
            defaults = profile_data.get('defaults', [])
            for entry in defaults:
                if isinstance(entry, dict):
                    skill = entry.get('skill', '')
                    if skill:
                        skills.append(skill)
                elif isinstance(entry, str):
                    skills.append(entry)

            if include_optionals:
                optionals = profile_data.get('optionals', [])
                for entry in optionals:
                    if isinstance(entry, dict):
                        skill = entry.get('skill', '')
                        if skill:
                            skills.append(skill)
                    elif isinstance(entry, str):
                        skills.append(entry)
        result[profile_name] = skills
    return result


def cmd_profiles(args) -> int:
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
                    raise ModuleNotFoundError(f'Module not found: {name}', all_modules)
        else:
            # Default: all modules with enrichment data
            module_names = list(enriched_modules.keys())

        # Collect unique profiles (handles both flat and structured formats)
        profiles: set[str] = set()
        modules_analyzed = []

        for module_name in module_names:
            module_enriched = enriched_modules.get(module_name, {})
            skills_by_profile = module_enriched.get('skills_by_profile', {})
            if skills_by_profile:
                modules_analyzed.append(module_name)
                profiles.update(_extract_profile_keys(skills_by_profile))

        # Output in TOON format
        print('status: success')
        print(f'count: {len(profiles)}')
        print()
        print(f'profiles[{len(profiles)}]:')
        for profile in sorted(profiles):
            print(f'  - {profile}')
        print()
        print(f'modules_analyzed[{len(modules_analyzed)}]:')
        for module in sorted(modules_analyzed):
            print(f'  - {module}')

        return 0
    except DataNotFoundError:
        error_data_not_found(str(get_derived_path(args.project_dir)), "Run 'architecture.py discover' first")
        return 1
    except ModuleNotFoundError as e:
        modules = get_module_names(load_derived_data(args.project_dir))
        error_module_not_found(str(e), modules)
        return 1
    except Exception as e:
        print('status: error', file=sys.stderr)
        print(f'error: {e}', file=sys.stderr)
        return 1


def cmd_siblings(args) -> int:
    """CLI handler for siblings command.

    Find sibling virtual modules for a given module.
    """
    try:
        siblings = get_sibling_modules(args.name, args.project_dir)

        print(f'module: {args.name}')
        print()

        if siblings:
            print_toon_list('siblings', siblings)
        else:
            print('siblings: []')
            print('note: Module is not a virtual module or has no siblings')

        return 0
    except DataNotFoundError:
        error_data_not_found(str(get_derived_path(args.project_dir)), "Run 'architecture.py discover' first")
        return 1
    except ModuleNotFoundError:
        modules = get_modules_list(args.project_dir)
        error_module_not_found(args.name, modules)
        return 1
    except Exception as e:
        print('status: error', file=sys.stderr)
        print(f'error: {e}', file=sys.stderr)
        return 1
