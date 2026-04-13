"""
Shared marketplace bundle discovery and resolution.

Provides bundle discovery, name extraction, path resolution, and PYTHONPATH
building for marketplace scripts. Used by generate_executor.py,
scan-marketplace-inventory.py, and other scripts that work with bundles.
"""

import os
import re
from pathlib import Path


def find_bundles(base_path: Path) -> list[Path]:
    """Find all bundle directories by locating plugin.json files."""
    bundles = []
    for plugin_json in base_path.rglob('.claude-plugin/plugin.json'):
        bundle_dir = plugin_json.parent.parent
        if bundle_dir not in bundles:
            bundles.append(bundle_dir)
    return sorted(bundles)


def extract_bundle_name(bundle_dir: Path) -> str:
    """Extract bundle name, handling versioned plugin-cache structure.

    For versioned structure (plugin-cache): .../plan-marshall/0.1-BETA/ -> "plan-marshall"
    For non-versioned structure (marketplace): .../plan-marshall/ -> "plan-marshall"
    """
    name = bundle_dir.name
    if re.match(r'^\d+\.\d+', name):
        return bundle_dir.parent.name
    return name


def resolve_bundle_path(base_path: Path, bundle_name: str, subpath: str) -> Path:
    """Resolve path within a bundle, handling versioned cache structure.

    Tries versioned path first (plugin-cache with version dir), then non-versioned (marketplace).

    Args:
        base_path: Path to bundles directory (plugin-cache or marketplace)
        bundle_name: Name of the bundle (e.g., 'plan-marshall')
        subpath: Path within the bundle (e.g., 'skills/foo/scripts/bar.py')
    """
    bundle_dir = base_path / bundle_name

    if bundle_dir.is_dir():
        for version_dir in bundle_dir.iterdir():
            if version_dir.is_dir() and not version_dir.name.startswith('.'):
                versioned = version_dir / subpath
                if versioned.exists():
                    return versioned

    return bundle_dir / subpath


def collect_script_dirs(base_path: Path) -> list[str]:
    """Collect all skill script directories from bundles.

    Discovers script directories and their immediate subdirectories,
    enabling cross-skill imports for scripts organized in subdirectory trees.

    Args:
        base_path: Path to bundles directory (plugin-cache or marketplace)

    Returns:
        List of script directory paths (parent dirs first, then subdirs)
    """
    script_dirs: list[str] = []

    for bundle_dir in base_path.iterdir():
        if not bundle_dir.is_dir() or bundle_dir.name.startswith('.'):
            continue

        # Determine base directories to scan for skills:
        # versioned (plugin-cache) -> each version subdir; non-versioned -> bundle itself
        has_version_dirs = any(
            d.is_dir() and not d.name.startswith('.') and (d / 'skills').is_dir() for d in bundle_dir.iterdir()
        )
        scan_roots = []
        if has_version_dirs:
            scan_roots = [d for d in bundle_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        else:
            scan_roots = [bundle_dir]

        for root in scan_roots:
            skills_dir = root / 'skills'
            if not skills_dir.exists():
                continue
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir():
                    scripts_dir = skill_dir / 'scripts'
                    if scripts_dir.exists():
                        script_dirs.append(str(scripts_dir))

    subdirs: list[str] = []
    for scripts_path in script_dirs:
        scripts_dir = Path(scripts_path)
        for child in scripts_dir.iterdir():
            if child.is_dir() and not child.name.startswith('.') and not child.name == '__pycache__':
                subdirs.append(str(child))

    script_dirs.extend(subdirs)
    return script_dirs


def resolve_bundles_root(script_file: Path) -> Path:
    """Resolve the bundles root directory by walking up from a script file.

    Walks parents of ``script_file`` and returns the first ancestor that
    contains a ``plan-marshall`` bundle — detected by the presence of either:

    - ``plan-marshall/.claude-plugin/plugin.json`` (marketplace/source layout)
    - ``plan-marshall/<version>/.claude-plugin/plugin.json`` (plugin-cache layout)

    Uses identity walking (no index arithmetic). Raises ``RuntimeError`` with
    the full walked parent chain if no such ancestor exists, so import-time
    misconfiguration fails loudly instead of silently returning a wrong path.

    Args:
        script_file: Path to the calling script (typically ``Path(__file__)``).

    Returns:
        The bundles root directory (e.g. ``.../marketplace/bundles``).

    Raises:
        RuntimeError: If no ancestor contains a ``plan-marshall`` bundle.
    """
    start = Path(script_file).resolve()
    walked: list[Path] = []
    for ancestor in start.parents:
        walked.append(ancestor)
        candidate = ancestor / 'plan-marshall'
        if not candidate.is_dir():
            continue
        if (candidate / '.claude-plugin' / 'plugin.json').is_file():
            return ancestor
        for version_dir in candidate.iterdir():
            if (
                version_dir.is_dir()
                and not version_dir.name.startswith('.')
                and (version_dir / '.claude-plugin' / 'plugin.json').is_file()
            ):
                return ancestor
    chain = '\n  '.join(str(p) for p in walked)
    raise RuntimeError(
        f"resolve_bundles_root: could not locate a 'plan-marshall' bundle "
        f"above {start}. Walked parents:\n  {chain}"
    )


def resolve_skills_root(script_file: Path) -> Path:
    """Resolve the ``skills`` directory anchor by walking up from a script file.

    Walks parents of ``script_file`` and returns the first ancestor named
    ``skills`` whose parent contains a ``.claude-plugin/plugin.json`` (i.e. is
    a bundle directory). Uses identity walking (no index arithmetic). Raises
    ``RuntimeError`` with the full walked parent chain if no such ancestor
    exists, so import-time misconfiguration fails loudly.

    Args:
        script_file: Path to the calling script (typically ``Path(__file__)``).

    Returns:
        The ``skills`` directory inside the owning bundle.

    Raises:
        RuntimeError: If no ``skills`` ancestor with a sibling bundle manifest
            is found.
    """
    start = Path(script_file).resolve()
    walked: list[Path] = []
    for ancestor in start.parents:
        walked.append(ancestor)
        if ancestor.name != 'skills':
            continue
        if (ancestor.parent / '.claude-plugin' / 'plugin.json').is_file():
            return ancestor
    chain = '\n  '.join(str(p) for p in walked)
    raise RuntimeError(
        f"resolve_skills_root: could not locate a 'skills' directory inside "
        f"a bundle above {start}. Walked parents:\n  {chain}"
    )


def build_pythonpath(base_path: Path) -> str:
    """Build PYTHONPATH from all skill script directories.

    Enables cross-skill imports for scripts called via subprocess.

    Args:
        base_path: Path to bundles directory (plugin-cache or marketplace)

    Returns:
        PYTHONPATH string with all skill script directories
    """
    return os.pathsep.join(collect_script_dirs(base_path))
