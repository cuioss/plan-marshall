#!/usr/bin/env python3
"""
Dependency index building and querying for resolve-dependencies.py.

Provides functions to:
- Discover all components in marketplace
- Build a dependency index from all components
- Query forward and reverse dependencies
- Detect circular dependencies
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _dep_detection import (  # type: ignore[import-not-found]
    ComponentId,
    Dependency,
    DependencyType,
    detect_all_dependencies,
    extract_frontmatter,
)

# Constants for path discovery
MARKETPLACE_BUNDLES_PATH = 'marketplace/bundles'
CLAUDE_DIR = '.claude'
PLUGIN_CACHE_SUBPATH = 'plugins/cache/plan-marshall'


@dataclass
class ComponentInfo:
    """Information about a discovered component."""

    component_id: ComponentId
    file_path: Path
    frontmatter: dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyIndex:
    """Index of all dependencies between components."""

    components: dict[str, ComponentInfo] = field(default_factory=dict)
    forward_deps: dict[str, list[Dependency]] = field(default_factory=lambda: defaultdict(list))
    reverse_deps: dict[str, list[Dependency]] = field(default_factory=lambda: defaultdict(list))
    implements_index: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def add_component(self, component: ComponentInfo) -> None:
        """Add a component to the index."""
        key = component.component_id.to_notation()
        self.components[key] = component

    def add_dependency(self, dep: Dependency) -> None:
        """Add a dependency to the index."""
        source_key = dep.source.to_notation()
        target_key = dep.target.to_notation()

        self.forward_deps[source_key].append(dep)
        self.reverse_deps[target_key].append(dep)

        # Track implements relationships specially
        if dep.dep_type == DependencyType.IMPLEMENTS:
            self.implements_index[target_key].append(source_key)

    def get_forward_deps(self, notation: str) -> list[Dependency]:
        """Get direct dependencies of a component."""
        return self.forward_deps.get(notation, [])

    def get_reverse_deps(self, notation: str) -> list[Dependency]:
        """Get components that depend on this component."""
        return self.reverse_deps.get(notation, [])

    def get_implementations(self, interface_notation: str) -> list[str]:
        """Get all components implementing an interface."""
        return self.implements_index.get(interface_notation, [])

    def resolve_transitive_deps(
        self,
        notation: str,
        max_depth: int = 10,
        dep_types: set[DependencyType] | None = None,
    ) -> list[dict[str, Any]]:
        """Resolve transitive dependencies.

        Args:
            notation: Component notation to resolve
            max_depth: Maximum depth to traverse
            dep_types: Filter to specific dependency types

        Returns:
            List of dicts with target, depth, via fields
        """
        result: list[dict[str, Any]] = []
        visited: set[str] = {notation}
        queue: list[tuple[str, int, str]] = [(notation, 0, '')]

        while queue:
            current, depth, via = queue.pop(0)
            if depth >= max_depth:
                continue

            for dep in self.forward_deps.get(current, []):
                if dep_types and dep.dep_type not in dep_types:
                    continue

                target_key = dep.target.to_notation()
                if target_key not in visited:
                    visited.add(target_key)
                    new_via = current if depth > 0 else ''
                    result.append(
                        {
                            'target': target_key,
                            'depth': depth + 1,
                            'via': new_via,
                        }
                    )
                    queue.append((target_key, depth + 1, current))

        return result

    def detect_circular_deps(self) -> list[list[str]]:
        """Detect circular dependencies.

        Returns:
            List of cycles, where each cycle is a list of component notations
        """
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for dep in self.forward_deps.get(node, []):
                target = dep.target.to_notation()
                if target not in visited:
                    dfs(target, path.copy())
                elif target in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(target)
                    cycle = path[cycle_start:] + [target]
                    # Normalize cycle to avoid duplicates
                    min_idx = cycle.index(min(cycle))
                    normalized = cycle[min_idx:-1] + cycle[:min_idx] + [cycle[min_idx]]
                    if normalized not in cycles:
                        cycles.append(normalized)

            rec_stack.remove(node)

        for component in self.components:
            if component not in visited:
                dfs(component, [])

        return cycles


def discover_components(base_path: Path) -> list[ComponentInfo]:
    """Discover all components in a marketplace directory.

    Args:
        base_path: Path to marketplace/bundles or similar

    Returns:
        List of discovered components
    """
    components: list[ComponentInfo] = []

    # Find all bundles (directories with .claude-plugin/plugin.json)
    for plugin_json in base_path.rglob('.claude-plugin/plugin.json'):
        bundle_dir = plugin_json.parent.parent
        bundle_name = _extract_bundle_name(bundle_dir)

        # Discover agents
        agents_dir = bundle_dir / 'agents'
        if agents_dir.is_dir():
            for agent_file in agents_dir.glob('*.md'):
                component_id = ComponentId(
                    bundle=bundle_name,
                    component_type='agent',
                    name=agent_file.stem,
                )
                content = agent_file.read_text()
                frontmatter, _ = extract_frontmatter(content)
                components.append(
                    ComponentInfo(
                        component_id=component_id,
                        file_path=agent_file,
                        frontmatter=frontmatter,
                    )
                )

        # Discover commands
        commands_dir = bundle_dir / 'commands'
        if commands_dir.is_dir():
            for command_file in commands_dir.glob('*.md'):
                component_id = ComponentId(
                    bundle=bundle_name,
                    component_type='command',
                    name=command_file.stem,
                )
                content = command_file.read_text()
                frontmatter, _ = extract_frontmatter(content)
                components.append(
                    ComponentInfo(
                        component_id=component_id,
                        file_path=command_file,
                        frontmatter=frontmatter,
                    )
                )

        # Discover skills and scripts
        skills_dir = bundle_dir / 'skills'
        if skills_dir.is_dir():
            for skill_md in skills_dir.glob('*/SKILL.md'):
                skill_dir = skill_md.parent
                skill_name = skill_dir.name

                # Add skill
                content = skill_md.read_text()
                frontmatter, _ = extract_frontmatter(content)
                component_id = ComponentId(
                    bundle=bundle_name,
                    component_type='skill',
                    name=skill_name,
                )
                components.append(
                    ComponentInfo(
                        component_id=component_id,
                        file_path=skill_md,
                        frontmatter=frontmatter,
                    )
                )

                # Add scripts (excluding private modules)
                scripts_dir = skill_dir / 'scripts'
                if scripts_dir.is_dir():
                    for script_file in scripts_dir.glob('*.py'):
                        # Skip private modules (underscore prefix)
                        if script_file.name.startswith('_'):
                            continue
                        script_id = ComponentId(
                            bundle=bundle_name,
                            component_type='script',
                            name=script_file.stem,
                            parent_skill=skill_name,
                        )
                        components.append(
                            ComponentInfo(
                                component_id=script_id,
                                file_path=script_file,
                                frontmatter={},
                            )
                        )

                    for script_file in scripts_dir.glob('*.sh'):
                        if script_file.name.startswith('_'):
                            continue
                        script_id = ComponentId(
                            bundle=bundle_name,
                            component_type='script',
                            name=script_file.stem,
                            parent_skill=skill_name,
                        )
                        components.append(
                            ComponentInfo(
                                component_id=script_id,
                                file_path=script_file,
                                frontmatter={},
                            )
                        )

    return components


def _extract_bundle_name(bundle_dir: Path) -> str:
    """Extract bundle name, handling versioned plugin-cache structure.

    For versioned structure (plugin-cache): .../plan-marshall/0.1-BETA/ -> "plan-marshall"
    For non-versioned structure (marketplace): .../plan-marshall/ -> "plan-marshall"
    """
    name = bundle_dir.name
    # If name looks like a version, use parent name
    if re.match(r'^\d+\.\d+', name):
        return bundle_dir.parent.name
    return name


def build_dependency_index(
    base_path: Path,
    dep_types: set[DependencyType] | None = None,
) -> DependencyIndex:
    """Build a complete dependency index from a marketplace directory.

    Args:
        base_path: Path to marketplace/bundles or similar
        dep_types: Filter to specific dependency types

    Returns:
        Populated DependencyIndex
    """
    index = DependencyIndex()

    # Discover all components
    components = discover_components(base_path)

    # Add components to index
    for component in components:
        index.add_component(component)

    # Detect dependencies for each component
    for component in components:
        deps = detect_all_dependencies(
            component.file_path,
            component.component_id,
            dep_types,
        )
        for dep in deps:
            # Mark as unresolved if target not in index
            target_key = dep.target.to_notation()
            if target_key not in index.components:
                dep.resolved = False
            index.add_dependency(dep)

    return index


def get_base_path(scope: str) -> Path:
    """Determine base path based on scope.

    Args:
        scope: One of 'auto', 'marketplace', 'plugin-cache', 'project'

    Returns:
        Path to the base directory

    Raises:
        FileNotFoundError: If the specified scope cannot be found
    """
    # Script-relative path to marketplace
    script_dir = Path(__file__).resolve().parent
    marketplace_from_script = script_dir.parent.parent.parent.parent.parent

    if scope == 'auto':
        # Try marketplace first
        if (Path.cwd() / MARKETPLACE_BUNDLES_PATH).is_dir():
            return Path.cwd() / MARKETPLACE_BUNDLES_PATH
        if marketplace_from_script.is_dir():
            return marketplace_from_script
        # Fall back to plugin cache
        cache = Path.home() / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH
        if cache.is_dir():
            return cache
        raise FileNotFoundError(f'Neither {MARKETPLACE_BUNDLES_PATH} nor plugin cache found.')

    if scope == 'marketplace':
        if (Path.cwd() / MARKETPLACE_BUNDLES_PATH).is_dir():
            return Path.cwd() / MARKETPLACE_BUNDLES_PATH
        if marketplace_from_script.is_dir():
            return marketplace_from_script
        raise FileNotFoundError(f'{MARKETPLACE_BUNDLES_PATH} directory not found')

    if scope == 'plugin-cache':
        cache = Path.home() / CLAUDE_DIR / PLUGIN_CACHE_SUBPATH
        if cache.is_dir():
            return cache
        raise FileNotFoundError(f'Plugin cache not found: {cache}')

    if scope == 'project':
        project_claude = Path.cwd() / CLAUDE_DIR
        if project_claude.is_dir():
            return project_claude
        raise FileNotFoundError(f'Project .claude directory not found: {project_claude}')

    raise ValueError(f'Invalid scope: {scope}')
