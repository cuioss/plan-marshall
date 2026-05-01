#!/usr/bin/env python3
"""Client command handlers for architecture script.

Handles: info, modules, graph, module, commands, resolve, profiles, siblings,
files, which-module, find.

Persistence model: per-module on-disk layout under
``.plan/project-architecture/``. Readers iterate ``_project.json``'s
``modules`` index and lazy-load per-module ``derived.json`` /
``enriched.json`` on demand via the core helpers.
"""

import fnmatch
from typing import Any

from _architecture_core import (
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
        module_overview.append(
            {'name': name, 'path': paths.get('module', ''), 'purpose': enriched.get('purpose', '')}
        )

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


def cmd_module(args) -> dict:
    """CLI handler for module command."""
    try:
        # Resolve module name (root if not provided), then merge.
        module_name = args.module or get_root_module(args.project_dir)
        if not module_name:
            raise ModuleNotFoundInProjectError('No modules found', [])
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
