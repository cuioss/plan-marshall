#!/usr/bin/env python3
"""Module discovery and path building utilities.

Shared infrastructure for discovering project modules across build systems.
Used by domain extensions (pm-dev-java, pm-dev-frontend) for module discovery.

Usage:
    from build_discover import discover_descriptors, build_module_base, find_readme

    # Find all pom.xml files
    descriptors = discover_descriptors("/path/to/project", "pom.xml")

    # Build module base from descriptor
    for desc in descriptors:
        base = build_module_base("/path/to/project", str(desc))
        print(base.to_dict())
"""

from dataclasses import dataclass
from pathlib import Path


# =============================================================================
# Constants
# =============================================================================

README_PATTERNS = ["README.md", "README.adoc", "README.txt", "README"]
"""Ordered list of README file patterns to search for."""

EXCLUDE_DIRS = {".git", "node_modules", "target", "build", "__pycache__", ".plan"}
"""Directory names to exclude from recursive searches."""


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ModulePaths:
    """Path structure for a module.

    All paths are relative to project root.
    """
    module: str
    """Relative path from project root to module directory."""

    descriptor: str
    """Relative path to build descriptor file (e.g., pom.xml)."""

    readme: str | None
    """Relative path to README file if exists, None otherwise."""


@dataclass
class ModuleBase:
    """Base module information before extension-specific enrichment.

    Contains only the information that can be determined from file system
    structure without parsing descriptor contents.
    """
    name: str
    """Module name (derived from directory name)."""

    paths: ModulePaths
    """Path structure for this module."""

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization.

        Returns:
            Dict with 'name' and 'paths' keys.
        """
        return {
            "name": self.name,
            "paths": {
                "module": self.paths.module,
                "descriptor": self.paths.descriptor,
                "readme": self.paths.readme,
            }
        }


# =============================================================================
# Discovery Functions
# =============================================================================

def discover_descriptors(
    project_root: str,
    descriptor_name: str,
    exclude_dirs: set | None = None
) -> list[Path]:
    """Recursively find all descriptor files in a project.

    Searches the project directory tree for files matching the descriptor name,
    excluding common non-source directories.

    Args:
        project_root: Absolute path to project root directory.
        descriptor_name: File name to find (e.g., "pom.xml", "package.json").
        exclude_dirs: Directory names to skip. Defaults to EXCLUDE_DIRS.

    Returns:
        List of absolute paths to descriptor files, sorted by depth
        (root-level first, then deeper levels).

    Example:
        >>> descriptors = discover_descriptors("/home/user/project", "pom.xml")
        >>> for d in descriptors:
        ...     print(d)
        /home/user/project/pom.xml
        /home/user/project/core/pom.xml
        /home/user/project/core/api/pom.xml
    """
    if exclude_dirs is None:
        exclude_dirs = EXCLUDE_DIRS

    root_path = Path(project_root).resolve()
    if not root_path.is_dir():
        return []

    descriptors = []

    def _search(directory: Path, depth: int) -> None:
        """Recursively search directory for descriptors."""
        try:
            for entry in directory.iterdir():
                if entry.is_file() and entry.name == descriptor_name:
                    descriptors.append((depth, entry))
                elif entry.is_dir() and entry.name not in exclude_dirs:
                    _search(entry, depth + 1)
        except PermissionError:
            pass

    _search(root_path, 0)

    # Sort by depth (root first), then by path for deterministic ordering
    descriptors.sort(key=lambda x: (x[0], str(x[1])))

    return [path for _, path in descriptors]


def build_module_base(project_root: str, descriptor_path: str) -> ModuleBase:
    """Build base module info from a descriptor path.

    Extracts module name from directory structure and locates README if present.

    Args:
        project_root: Absolute path to project root directory.
        descriptor_path: Absolute path to descriptor file.

    Returns:
        ModuleBase with name and paths populated.

    Example:
        >>> base = build_module_base("/home/user/project", "/home/user/project/core/pom.xml")
        >>> base.name
        'core'
        >>> base.paths.module
        'core'
        >>> base.paths.descriptor
        'core/pom.xml'
    """
    root_path = Path(project_root).resolve()
    desc_path = Path(descriptor_path).resolve()
    module_dir = desc_path.parent

    # Calculate relative paths
    try:
        rel_module = module_dir.relative_to(root_path)
        rel_descriptor = desc_path.relative_to(root_path)
    except ValueError:
        # descriptor_path is not under project_root
        rel_module = Path(".")
        rel_descriptor = Path(desc_path.name)

    # Module name: directory name, or "default" for root
    module_name = rel_module.name if rel_module != Path(".") else "default"
    if not module_name:
        module_name = "default"

    # Find README
    readme_rel = find_readme(str(module_dir))
    if readme_rel:
        # Make relative to project root
        readme_abs = module_dir / readme_rel
        try:
            readme_rel = str(readme_abs.relative_to(root_path))
        except ValueError:
            readme_rel = None

    paths = ModulePaths(
        module=str(rel_module) if str(rel_module) != "." else ".",
        descriptor=str(rel_descriptor),
        readme=readme_rel,
    )

    return ModuleBase(name=module_name, paths=paths)


def find_readme(module_path: str) -> str | None:
    """Find README file in a module directory.

    Searches for README files in order of preference defined by README_PATTERNS.

    Args:
        module_path: Absolute path to module directory.

    Returns:
        File name of README if found (not full path), None otherwise.

    Example:
        >>> find_readme("/home/user/project/core")
        'README.md'
    """
    module_dir = Path(module_path)
    if not module_dir.is_dir():
        return None

    for pattern in README_PATTERNS:
        readme_path = module_dir / pattern
        if readme_path.is_file():
            return pattern

    return None
