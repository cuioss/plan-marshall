#!/usr/bin/env python3
"""
Dependency detection functions for resolve-dependencies.py.

Provides functions to extract different types of dependencies from
marketplace component files (skills, agents, commands, scripts).

Dependency types:
- script: bundle:skill:script notation references
- skill: skills: frontmatter and Skill: patterns
- import: Python from X import Y statements
- path: Relative markdown links (../../skill/file.md)
- implements: implements: frontmatter interface references
"""

import ast
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class DependencyType(Enum):
    """Types of dependencies that can be detected."""

    SCRIPT_NOTATION = 'script'  # bundle:skill:script references
    SKILL_REFERENCE = 'skill'  # skills: frontmatter, Skill: patterns
    PYTHON_IMPORT = 'import'  # from module import statements
    RELATIVE_PATH = 'path'  # ../../skill/file.md references
    IMPLEMENTS = 'implements'  # implements: frontmatter interface refs


@dataclass
class ComponentId:
    """Identifier for a marketplace component."""

    bundle: str
    component_type: str  # skill, agent, command, script
    name: str
    parent_skill: str | None = None  # For scripts only

    def to_notation(self) -> str:
        """Convert to notation string."""
        if self.component_type == 'script' and self.parent_skill:
            return f'{self.bundle}:{self.parent_skill}:{self.name}'
        if self.component_type in ('agent', 'command'):
            return f'{self.bundle}:{self.component_type}s:{self.name}'
        return f'{self.bundle}:{self.name}'

    @classmethod
    def from_notation(cls, notation: str) -> 'ComponentId | None':
        """Parse a notation string into a ComponentId.

        Supports:
        - bundle:skill (skill)
        - bundle:skill:script (script)
        - bundle:agents:name (agent)
        - bundle:commands:name (command)
        """
        parts = notation.split(':')
        if len(parts) == 2:
            bundle, name = parts
            if name == 'agents' or name == 'commands':
                return None  # Invalid: just bundle:agents with no name
            return cls(bundle=bundle, component_type='skill', name=name)
        if len(parts) == 3:
            bundle, middle, name = parts
            if middle == 'agents':
                return cls(bundle=bundle, component_type='agent', name=name)
            if middle == 'commands':
                return cls(bundle=bundle, component_type='command', name=name)
            # Otherwise it's a script: bundle:skill:script
            return cls(bundle=bundle, component_type='script', name=name, parent_skill=middle)
        return None


@dataclass
class Dependency:
    """A detected dependency between components."""

    source: ComponentId
    target: ComponentId
    dep_type: DependencyType
    context: str  # Location (line number, field name)
    resolved: bool = True  # False if target doesn't exist


# Known Python module to skill mappings
PYTHON_MODULE_MAPPINGS: dict[str, str] = {
    'toon_parser': 'plan-marshall:ref-toon-format:toon_parser',
    'extension_base': 'plan-marshall:extension-api:extension_base',
    'plan_logging': 'plan-marshall:manage-logging:plan_logging',
    'run_config': 'plan-marshall:manage-run-config:run_config',
    'file_ops': 'plan-marshall:tools-file-ops:file_ops',
    'extension_discovery': 'plan-marshall:extension-api:extension_discovery',
}


def extract_frontmatter(content: str) -> tuple[dict[str, Any], int]:
    """Extract YAML frontmatter from markdown content.

    Returns:
        Tuple of (frontmatter dict, end line number)
    """
    if not content.startswith('---'):
        return {}, 0

    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}, 0

    frontmatter_text = match.group(1)
    end_line = content[: match.end()].count('\n')

    # Simple YAML parsing (handles flat key: value and lists)
    result: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] = []

    for line in frontmatter_text.split('\n'):
        line = line.rstrip()
        if not line or line.startswith('#'):
            continue

        # Check for list item
        if line.startswith('  - ') and current_key:
            current_list.append(line[4:].strip())
            continue

        # Save previous list if any
        if current_key and current_list:
            result[current_key] = current_list
            current_list = []

        # Parse key: value
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip()
            current_key = key
            if value:
                result[key] = value

    # Save final list if any
    if current_key and current_list:
        result[current_key] = current_list

    return result, end_line


def detect_script_notations(content: str, source: ComponentId) -> list[Dependency]:
    """Detect bundle:skill:script notation references in content.

    Looks for patterns like:
    - python3 .plan/execute-script.py bundle:skill:script
    - `bundle:skill:script`
    - Skill: bundle:skill (2-part notation for skills)
    """
    deps: list[Dependency] = []

    # Pattern for 3-part notation: bundle:skill:script
    # Must be word characters separated by colons
    pattern_3part = r'\b([\w-]+):([\w-]+):([\w-]+)\b'

    for line_num, line in enumerate(content.split('\n'), 1):
        # Skip comments in code
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('//'):
            continue

        # Skip lines that look like URLs
        if re.search(r'https?://', line):
            continue

        for match in re.finditer(pattern_3part, line):
            bundle, skill, script = match.groups()
            # Filter out common false positives
            if bundle in ('http', 'https', 'file', 'mailto'):
                continue
            # Avoid version numbers like 1.0:2.0:3.0
            if bundle[0].isdigit():
                continue
            # Skip if skill looks like a port number (all digits)
            if skill.isdigit():
                continue

            target = ComponentId(
                bundle=bundle,
                component_type='script',
                name=script,
                parent_skill=skill,
            )
            deps.append(
                Dependency(
                    source=source,
                    target=target,
                    dep_type=DependencyType.SCRIPT_NOTATION,
                    context=f'line:{line_num}',
                )
            )

    return deps


def detect_skill_references(content: str, frontmatter: dict[str, Any], source: ComponentId) -> list[Dependency]:
    """Detect skill references from frontmatter and content.

    Looks for:
    - skills: list in frontmatter
    - Skill: bundle:skill patterns in content
    """
    deps: list[Dependency] = []

    # Check frontmatter skills: list
    skills = frontmatter.get('skills', [])
    if isinstance(skills, list):
        for skill_ref in skills:
            if ':' in skill_ref:
                parts = skill_ref.split(':')
                if len(parts) == 2:
                    bundle, name = parts
                    target = ComponentId(bundle=bundle, component_type='skill', name=name)
                    deps.append(
                        Dependency(
                            source=source,
                            target=target,
                            dep_type=DependencyType.SKILL_REFERENCE,
                            context='frontmatter:skills',
                        )
                    )

    # Pattern for Skill: bundle:skill in content
    pattern = r'Skill:\s*([\w-]+):([\w-]+)'
    for line_num, line in enumerate(content.split('\n'), 1):
        for match in re.finditer(pattern, line):
            bundle, name = match.groups()
            target = ComponentId(bundle=bundle, component_type='skill', name=name)
            deps.append(
                Dependency(
                    source=source,
                    target=target,
                    dep_type=DependencyType.SKILL_REFERENCE,
                    context=f'line:{line_num}',
                )
            )

    return deps


def detect_python_imports(content: str, source: ComponentId) -> list[Dependency]:
    """Detect Python import statements and map to known skills.

    Uses AST parsing to find ImportFrom nodes, then maps module names
    to known skill locations.
    """
    deps: list[Dependency] = []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return deps

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module
            if module and module in PYTHON_MODULE_MAPPINGS:
                notation = PYTHON_MODULE_MAPPINGS[module]
                target = ComponentId.from_notation(notation)
                if target:
                    deps.append(
                        Dependency(
                            source=source,
                            target=target,
                            dep_type=DependencyType.PYTHON_IMPORT,
                            context=f'line:{node.lineno}',
                        )
                    )

    return deps


def detect_relative_paths(content: str, source: ComponentId, source_path: Path) -> list[Dependency]:
    """Detect relative path references in markdown links.

    Looks for patterns like [text](../../skill/file.md)
    """
    deps: list[Dependency] = []

    # Pattern for markdown links with relative paths
    pattern = r'\[.*?\]\((\.\.\/[^)]+)\)'

    for line_num, line in enumerate(content.split('\n'), 1):
        for match in re.finditer(pattern, line):
            rel_path = match.group(1)
            # Try to resolve the path
            try:
                resolved = (source_path.parent / rel_path).resolve()
                # Extract bundle and skill from resolved path
                # Path structure: .../marketplace/bundles/{bundle}/skills/{skill}/...
                parts = resolved.parts
                if 'bundles' in parts and 'skills' in parts:
                    bundles_idx = parts.index('bundles')
                    if bundles_idx + 1 < len(parts):
                        bundle = parts[bundles_idx + 1]
                        skills_idx = parts.index('skills') if 'skills' in parts else -1
                        if skills_idx > 0 and skills_idx + 1 < len(parts):
                            skill = parts[skills_idx + 1]
                            target = ComponentId(bundle=bundle, component_type='skill', name=skill)
                            deps.append(
                                Dependency(
                                    source=source,
                                    target=target,
                                    dep_type=DependencyType.RELATIVE_PATH,
                                    context=f'line:{line_num}',
                                )
                            )
            except (ValueError, IndexError):
                continue

    return deps


def detect_implements(frontmatter: dict[str, Any], source: ComponentId) -> list[Dependency]:
    """Detect interface implementations from frontmatter.

    Looks for implements: bundle:skill/path pattern.
    """
    deps: list[Dependency] = []

    implements = frontmatter.get('implements')
    if not implements:
        return deps

    # Parse bundle:skill/path format
    if ':' in implements:
        bundle_skill, *path_parts = implements.split('/')
        if ':' in bundle_skill:
            bundle, skill = bundle_skill.split(':', 1)
            target = ComponentId(bundle=bundle, component_type='skill', name=skill)
            deps.append(
                Dependency(
                    source=source,
                    target=target,
                    dep_type=DependencyType.IMPLEMENTS,
                    context='frontmatter:implements',
                )
            )

    return deps


def detect_all_dependencies(
    file_path: Path,
    source: ComponentId,
    dep_types: set[DependencyType] | None = None,
) -> list[Dependency]:
    """Detect all dependencies in a file.

    Args:
        file_path: Path to the file to analyze
        source: ComponentId of the source component
        dep_types: Set of dependency types to detect (None = all)

    Returns:
        List of detected dependencies
    """
    if dep_types is None:
        dep_types = set(DependencyType)

    try:
        content = file_path.read_text()
    except (OSError, UnicodeDecodeError):
        return []

    deps: list[Dependency] = []

    # Extract frontmatter for markdown files
    frontmatter: dict[str, Any] = {}
    if file_path.suffix == '.md':
        frontmatter, _ = extract_frontmatter(content)

    # Detect each type
    if DependencyType.SCRIPT_NOTATION in dep_types:
        deps.extend(detect_script_notations(content, source))

    if DependencyType.SKILL_REFERENCE in dep_types:
        deps.extend(detect_skill_references(content, frontmatter, source))

    if DependencyType.PYTHON_IMPORT in dep_types and file_path.suffix == '.py':
        deps.extend(detect_python_imports(content, source))

    if DependencyType.RELATIVE_PATH in dep_types and file_path.suffix == '.md':
        deps.extend(detect_relative_paths(content, source, file_path))

    if DependencyType.IMPLEMENTS in dep_types:
        deps.extend(detect_implements(frontmatter, source))

    return deps
