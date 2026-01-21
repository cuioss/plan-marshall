#!/usr/bin/env python3
"""
resolve-dependencies.py

Tracks and resolves all dependency relationships across marketplace and
project-level components.

Usage:
    python3 resolve-dependencies.py <subcommand> [options]

Subcommands:
    deps        Get direct + transitive dependencies of a component
    rdeps       Get reverse dependencies (what depends on component)
    tree        Visual dependency tree output
    validate    Check for broken/circular dependencies

Options:
    --component <notation>   Component to resolve (required for deps/rdeps/tree)
    --scope <value>          auto, marketplace, plugin-cache, project (default: auto)
    --format <value>         toon (default), json
    --direct-result          Output to stdout
    --depth <N>              Max transitive depth (default: 10)
    --dep-types <types>      Filter: script,skill,import,path,implements (comma-separated)

Component Notation:
    bundle:skill                    Skill (e.g., pm-workflow:phase-1-init)
    bundle:skill:script             Script (e.g., pm-workflow:manage-files:manage-files)
    bundle:agents:name              Agent (e.g., pm-workflow:agents:plan-init-agent)
    bundle:commands:name            Command (e.g., plan-marshall:commands:tools-fix-intellij-diagnostics)

Exit codes:
    0 - Success
    1 - Error (invalid parameters, component not found)
"""

import argparse
import json
import sys
from collections import defaultdict
from typing import Any

from _dep_detection import Dependency, DependencyType  # type: ignore[import-not-found]
from _dep_index import (  # type: ignore[import-not-found]
    DependencyIndex,
    build_dependency_index,
    get_base_path,
)

# Try to import toon_parser, fall back to simple serialization
try:
    from toon_parser import serialize_toon  # type: ignore[import-not-found]

    HAS_TOON_PARSER = True
except ImportError:
    HAS_TOON_PARSER = False


def serialize_toon_simple(data: dict[str, Any]) -> str:
    """Simple TOON serialization for when toon_parser is not available."""
    lines: list[str] = []

    def _serialize(obj: Any, indent: int = 0) -> None:
        prefix = '  ' * indent
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, dict):
                    lines.append(f'{prefix}{key}:')
                    _serialize(value, indent + 1)
                elif isinstance(value, list):
                    lines.append(f'{prefix}{key}[{len(value)}]:')
                    for item in value:
                        if isinstance(item, dict):
                            lines.append(f'{prefix}  - {_format_dict_inline(item)}')
                        else:
                            lines.append(f'{prefix}  - {item}')
                else:
                    lines.append(f'{prefix}{key}: {value}')
        else:
            lines.append(f'{prefix}{obj}')

    _serialize(data)
    return '\n'.join(lines)


def _format_dict_inline(d: dict) -> str:
    """Format a dict inline for list items."""
    parts = [f'{k}: {v}' for k, v in d.items()]
    return ', '.join(parts)


def serialize_output(data: dict[str, Any], fmt: str) -> str:
    """Serialize output in requested format."""
    if fmt == 'json':
        return json.dumps(data, indent=2)
    if HAS_TOON_PARSER:
        result: str = serialize_toon(data)
        return result
    return serialize_toon_simple(data)


def parse_dep_types(dep_types_str: str) -> set[DependencyType]:
    """Parse comma-separated dependency types string."""
    if not dep_types_str:
        return set(DependencyType)

    type_map = {
        'script': DependencyType.SCRIPT_NOTATION,
        'skill': DependencyType.SKILL_REFERENCE,
        'import': DependencyType.PYTHON_IMPORT,
        'path': DependencyType.RELATIVE_PATH,
        'implements': DependencyType.IMPLEMENTS,
    }

    result = set()
    for t in dep_types_str.split(','):
        t = t.strip().lower()
        if t in type_map:
            result.add(type_map[t])
        else:
            raise ValueError(f'Invalid dependency type: {t}')

    return result


def format_dependency(dep: Dependency) -> dict[str, Any]:
    """Format a dependency for output."""
    return {
        'target': dep.target.to_notation(),
        'type': dep.dep_type.value,
        'context': dep.context,
        'resolved': dep.resolved,
    }


def cmd_deps(
    index: DependencyIndex,
    component: str,
    depth: int,
    dep_types: set[DependencyType],
) -> dict[str, Any]:
    """Get direct and transitive dependencies of a component."""
    if component not in index.components:
        return {
            'status': 'error',
            'error': f'Component not found: {component}',
        }

    comp_info = index.components[component]
    direct_deps = index.get_forward_deps(component)

    # Filter by dep types
    filtered_direct = [d for d in direct_deps if d.dep_type in dep_types]

    # Get transitive deps
    transitive = index.resolve_transitive_deps(component, depth, dep_types)
    # Exclude direct deps from transitive
    direct_targets = {d.target.to_notation() for d in filtered_direct}
    filtered_transitive = [t for t in transitive if t['target'] not in direct_targets and t['depth'] > 1]

    # Count by type
    by_type: dict[str, int] = defaultdict(int)
    for dep in filtered_direct:
        by_type[dep.dep_type.value] += 1

    return {
        'status': 'success',
        'component': component,
        'component_type': comp_info.component_id.component_type,
        'file_path': str(comp_info.file_path),
        'direct_dependencies': [format_dependency(d) for d in filtered_direct],
        'transitive_dependencies': filtered_transitive,
        'statistics': {
            'direct_count': len(filtered_direct),
            'transitive_count': len(filtered_transitive),
            'by_type': dict(by_type),
        },
    }


def cmd_rdeps(
    index: DependencyIndex,
    component: str,
    dep_types: set[DependencyType],
) -> dict[str, Any]:
    """Get reverse dependencies (what depends on component)."""
    if component not in index.components:
        # Could be a partial match or interface - check implements index
        implementations = index.get_implementations(component)
        if implementations:
            return {
                'status': 'success',
                'interface': component,
                'implementations': implementations,
            }
        return {
            'status': 'error',
            'error': f'Component not found: {component}',
        }

    rdeps = index.get_reverse_deps(component)

    # Filter by dep types
    filtered = [d for d in rdeps if d.dep_type in dep_types]

    # Group by source component
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for dep in filtered:
        source_key = dep.source.to_notation()
        by_source[source_key].append({
            'type': dep.dep_type.value,
            'context': dep.context,
        })

    return {
        'status': 'success',
        'component': component,
        'dependent_count': len(by_source),
        'dependents': [
            {'component': src, 'references': refs}
            for src, refs in sorted(by_source.items())
        ],
    }


def cmd_tree(
    index: DependencyIndex,
    component: str,
    depth: int,
    dep_types: set[DependencyType],
) -> dict[str, Any]:
    """Generate a visual dependency tree."""
    if component not in index.components:
        return {
            'status': 'error',
            'error': f'Component not found: {component}',
        }

    lines: list[str] = [component]

    def build_tree(node: str, prefix: str, current_depth: int, visited: set[str]) -> None:
        if current_depth >= depth:
            return

        deps = index.get_forward_deps(node)
        filtered = [d for d in deps if d.dep_type in dep_types]

        for i, dep in enumerate(filtered):
            target = dep.target.to_notation()
            is_last = i == len(filtered) - 1
            connector = '\u2514\u2500\u2500 ' if is_last else '\u251c\u2500\u2500 '
            resolved_mark = '' if dep.resolved else ' [UNRESOLVED]'

            lines.append(f'{prefix}{connector}{target} ({dep.dep_type.value}){resolved_mark}')

            if target not in visited and dep.resolved:
                new_visited = visited | {target}
                new_prefix = prefix + ('    ' if is_last else '\u2502   ')
                build_tree(target, new_prefix, current_depth + 1, new_visited)

    build_tree(component, '', 0, {component})

    return {
        'status': 'success',
        'component': component,
        'tree': '\n'.join(lines),
    }


def cmd_validate(
    index: DependencyIndex,
    dep_types: set[DependencyType],
) -> dict[str, Any]:
    """Validate all dependencies and check for issues."""
    # Collect unresolved dependencies
    unresolved: list[dict[str, Any]] = []
    total_deps = 0
    resolved_count = 0

    for deps in index.forward_deps.values():
        for dep in deps:
            if dep.dep_type not in dep_types:
                continue
            total_deps += 1
            if dep.resolved:
                resolved_count += 1
            else:
                unresolved.append({
                    'source': dep.source.to_notation(),
                    'target': dep.target.to_notation(),
                    'type': dep.dep_type.value,
                    'context': dep.context,
                })

    # Detect circular dependencies
    circular = index.detect_circular_deps()

    # Determine status
    has_issues = len(unresolved) > 0 or len(circular) > 0
    status = 'error' if has_issues else 'success'
    validation_result = 'failed' if has_issues else 'passed'

    result: dict[str, Any] = {
        'status': status,
        'validation_result': validation_result,
        'total_components': len(index.components),
        'total_dependencies': total_deps,
        'resolved': resolved_count,
        'unresolved_count': len(unresolved),
    }

    if unresolved:
        result['unresolved'] = unresolved

    if circular:
        result['circular_dependencies'] = [
            {'chain': cycle} for cycle in circular
        ]

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Resolve dependencies between marketplace components'
    )
    parser.add_argument(
        'subcommand',
        choices=['deps', 'rdeps', 'tree', 'validate'],
        help='Subcommand to run',
    )
    parser.add_argument(
        '--component',
        help='Component notation to resolve',
    )
    parser.add_argument(
        '--scope',
        choices=['auto', 'marketplace', 'plugin-cache', 'project'],
        default='auto',
        help='Directory scope (default: auto)',
    )
    parser.add_argument(
        '--format',
        choices=['toon', 'json'],
        default='toon',
        help='Output format (default: toon)',
    )
    parser.add_argument(
        '--direct-result',
        action='store_true',
        help='Output directly to stdout',
    )
    parser.add_argument(
        '--depth',
        type=int,
        default=10,
        help='Max transitive depth (default: 10)',
    )
    parser.add_argument(
        '--dep-types',
        default='',
        help='Filter dependency types (comma-separated: script,skill,import,path,implements)',
    )

    args = parser.parse_args()

    # Validate required arguments
    if args.subcommand in ('deps', 'rdeps', 'tree') and not args.component:
        print(f'ERROR: --component is required for {args.subcommand}', file=sys.stderr)
        return 1

    # Parse dependency types
    try:
        dep_types = parse_dep_types(args.dep_types)
    except ValueError as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 1

    # Get base path
    try:
        base_path = get_base_path(args.scope)
    except (FileNotFoundError, ValueError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 1

    # Build dependency index
    index = build_dependency_index(base_path, dep_types)

    # Run subcommand
    if args.subcommand == 'deps':
        result = cmd_deps(index, args.component, args.depth, dep_types)
    elif args.subcommand == 'rdeps':
        result = cmd_rdeps(index, args.component, dep_types)
    elif args.subcommand == 'tree':
        result = cmd_tree(index, args.component, args.depth, dep_types)
    elif args.subcommand == 'validate':
        result = cmd_validate(index, dep_types)
    else:
        print(f'ERROR: Unknown subcommand: {args.subcommand}', file=sys.stderr)
        return 1

    # Output result
    output = serialize_output(result, args.format)
    print(output)

    # Return error code if status is error
    return 1 if result.get('status') == 'error' else 0


if __name__ == '__main__':
    sys.exit(main())
