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

README_PATTERNS = ['README.md', 'README.adoc', 'README.txt', 'README']
"""Ordered list of README file patterns to search for."""

EXCLUDE_DIRS = {'.git', 'node_modules', 'target', 'build', '__pycache__', '.plan'}
"""Directory names to exclude from recursive searches."""

# JVM languages and their source file extensions (used by discover_sources / count_source_files)
JVM_LANGUAGES = ['java', 'kotlin', 'groovy', 'scala']
"""JVM languages checked during source directory discovery."""

JVM_EXTENSIONS: dict[str, str] = {
    'java': '*.java',
    'kotlin': '*.kt',
    'groovy': '*.groovy',
    'scala': '*.scala',
}
"""Glob patterns for JVM source files, keyed by language name."""

# JavaScript/TypeScript extensions for npm/frontend projects
JS_EXTENSIONS: dict[str, str] = {
    'js': '*.js',
    'jsx': '*.jsx',
    'ts': '*.ts',
    'tsx': '*.tsx',
    'mjs': '*.mjs',
    'cjs': '*.cjs',
}
"""Glob patterns for JavaScript/TypeScript source files."""

# Python extensions for Python projects
PY_EXTENSIONS: dict[str, str] = {'py': '*.py'}
"""Glob patterns for Python source files."""

# Common JS source directory names (not following src/main/{lang} convention)
JS_SOURCE_DIRS = ['src', 'lib', 'app', 'pages', 'components']
"""Standard source directory names for JavaScript/TypeScript projects."""

JS_TEST_DIRS = ['test', 'tests', '__tests__', 'spec', 'specs', 'e2e']
"""Standard test directory names for JavaScript/TypeScript projects."""


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
            'name': self.name,
            'paths': {
                'module': self.paths.module,
                'descriptor': self.paths.descriptor,
                'readme': self.paths.readme,
            },
        }


# =============================================================================
# Discovery Functions
# =============================================================================


def discover_descriptors(project_root: str, descriptor_name: str, exclude_dirs: set | None = None) -> list[Path]:
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
        rel_module = Path('.')
        rel_descriptor = Path(desc_path.name)

    # Module name: directory name, or "default" for root
    module_name = rel_module.name if rel_module != Path('.') else 'default'
    if not module_name:
        module_name = 'default'

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
        module=str(rel_module) if str(rel_module) != '.' else '.',
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


# =============================================================================
# Source Directory Discovery
# =============================================================================


def discover_sources(module_path: str | Path) -> dict[str, list[str]]:
    """Discover source directories for all JVM languages plus resources.

    Checks for Java, Kotlin, Groovy, Scala source directories and
    resource directories under the standard src/main and src/test layout.

    Args:
        module_path: Absolute path to module directory.

    Returns:
        Dict with 'main' and 'test' keys, each containing a list of
        relative source directory paths that exist. Example::

            {
                'main': ['src/main/java', 'src/main/kotlin', 'src/main/resources'],
                'test': ['src/test/java', 'src/test/resources']
            }
    """
    mod = Path(module_path)
    sources: dict[str, list[str]] = {'main': [], 'test': []}

    for lang in JVM_LANGUAGES:
        main_dir = mod / 'src' / 'main' / lang
        test_dir = mod / 'src' / 'test' / lang
        if main_dir.exists():
            sources['main'].append(f'src/main/{lang}')
        if test_dir.exists():
            sources['test'].append(f'src/test/{lang}')

    # Resources directories
    if (mod / 'src' / 'main' / 'resources').exists():
        sources['main'].append('src/main/resources')
    if (mod / 'src' / 'test' / 'resources').exists():
        sources['test'].append('src/test/resources')

    return sources


def discover_js_sources(module_path: str | Path) -> dict[str, list[str]]:
    """Discover source directories for JavaScript/TypeScript projects.

    JS projects typically use flat directories like src/, lib/, app/.
    Test directories include test/, tests/, __tests__/, spec/.

    Also detects JVM-style source layout for hybrid projects (e.g., Maven + npm
    in the same directory) so that source stats remain accurate even though
    virtual module splitting handles build-system separation at a higher level.

    Args:
        module_path: Absolute path to module directory.

    Returns:
        Dict with 'main' and 'test' keys, each containing a list of
        relative source directory paths that exist.
    """
    mod = Path(module_path)
    sources: dict[str, list[str]] = {'main': [], 'test': []}

    # Check for JVM-style layout first (for hybrid projects like Maven + npm
    # in the same directory — virtual module splitting handles this at a higher
    # level, but JVM sources should still be detected for accurate stats)
    for lang in JVM_LANGUAGES:
        main_dir = mod / 'src' / 'main' / lang
        test_dir = mod / 'src' / 'test' / lang
        if main_dir.exists():
            sources['main'].append(f'src/main/{lang}')
        if test_dir.exists():
            sources['test'].append(f'src/test/{lang}')

    # JS-style source directories (only if no JVM sources found in that dir)
    for dir_name in JS_SOURCE_DIRS:
        dir_path = mod / dir_name
        if dir_path.is_dir() and dir_name not in [d.split('/')[-1] for d in sources['main']]:
            # Verify it actually has JS/TS files
            has_js = any(list(dir_path.rglob(ext))[:1] for ext in JS_EXTENSIONS.values())
            if has_js:
                sources['main'].append(dir_name)

    # JS-style test directories
    for dir_name in JS_TEST_DIRS:
        dir_path = mod / dir_name
        if dir_path.is_dir():
            sources['test'].append(dir_name)

    # Resources directories (shared with JVM)
    if (mod / 'src' / 'main' / 'resources').exists():
        sources['main'].append('src/main/resources')
    if (mod / 'src' / 'test' / 'resources').exists():
        sources['test'].append('src/test/resources')

    return sources


def count_source_files(
    module_path: str | Path, source_dirs: list[str], extra_extensions: dict[str, str] | None = None
) -> int:
    """Count source files in the given source directories.

    Determines the language from the directory path (e.g. ``src/main/kotlin``
    → ``*.kt``) and counts matching files recursively. Resource directories
    and directories not mapping to a known language are skipped.

    For JS/TS projects, pass ``extra_extensions=JS_EXTENSIONS`` to count
    JavaScript and TypeScript files in flat source directories.

    Args:
        module_path: Absolute path to module directory.
        source_dirs: List of relative source directory paths
            (as returned by :func:`discover_sources` or :func:`discover_js_sources`).
        extra_extensions: Additional file extension mappings beyond JVM.
            Keys are arbitrary identifiers, values are glob patterns.

    Returns:
        Total count of source files across all directories.
    """
    mod = Path(module_path)
    all_extensions = dict(JVM_EXTENSIONS)
    if extra_extensions:
        all_extensions.update(extra_extensions)

    count = 0
    for src in source_dirs:
        src_path = mod / src
        if not src_path.exists():
            continue
        # Determine language from trailing directory name
        lang = Path(src).name
        if lang in all_extensions:
            count += len(list(src_path.rglob(all_extensions[lang])))
        elif extra_extensions:
            # For flat dirs (src/, lib/), count all extra extension files
            for ext_glob in extra_extensions.values():
                count += len(list(src_path.rglob(ext_glob)))
        # Skip resources and other non-code directories
    return count


def discover_packages(
    module_path: str | Path,
    source_dirs: list[str],
    relative_path: str,
    extra_extensions: dict[str, str] | None = None,
) -> dict:
    """Discover packages from source directories.

    Scans source directories for source files and groups them by
    package (directory structure converted to dotted notation).

    For JVM projects, uses JVM_EXTENSIONS by default. For JS/TS projects,
    pass ``extra_extensions=JS_EXTENSIONS`` to also find JavaScript packages.

    Args:
        module_path: Absolute path to module directory.
        source_dirs: List of relative source directory paths to scan.
        relative_path: Module path relative to project root (used to
            prefix paths in the output). Use ``""`` for root modules.
        extra_extensions: Additional file extension mappings beyond JVM.

    Returns:
        Dict keyed by package name. Each value contains::

            {
                'path': str,                    # Relative path to package dir
                'package_info': str | absent,   # Path to package-info.java if exists
                'files': list[str] | absent     # Sorted source file names
            }
    """
    mod = Path(module_path)
    packages: dict[str, dict] = {}

    # Collect all file extensions to search for
    all_ext = dict(JVM_EXTENSIONS)
    if extra_extensions:
        all_ext.update(extra_extensions)
    all_extensions = list(all_ext.values())
    all_suffixes = {'.java', '.kt', '.groovy', '.scala'}
    if extra_extensions:
        all_suffixes.update(f'.{k}' for k in extra_extensions)

    for source_dir in source_dirs:
        source_path = mod / source_dir
        if not source_path.exists():
            continue

        # Skip resource directories — no packages there
        if Path(source_dir).name == 'resources':
            continue

        seen: set[str] = set()
        # Find all JVM source files across all languages
        source_files_by_dir: dict[Path, list[Path]] = {}
        for ext_glob in all_extensions:
            for src_file in source_path.rglob(ext_glob):
                pkg_dir = src_file.parent
                source_files_by_dir.setdefault(pkg_dir, []).append(src_file)

        for pkg_dir, _files in source_files_by_dir.items():
            pkg_name = str(pkg_dir.relative_to(source_path)).replace('/', '.').replace('\\', '.')

            # Skip root "." package
            if not pkg_name or pkg_name == '.' or pkg_name in seen:
                continue
            seen.add(pkg_name)

            rel_path = str(pkg_dir.relative_to(mod))
            if relative_path:
                rel_path = f'{relative_path}/{rel_path}'

            pkg_info: dict[str, str | list[str]] = {'path': rel_path}

            # Check for package-info.java
            info_file = pkg_dir / 'package-info.java'
            if info_file.exists():
                info_path = str(info_file.relative_to(mod))
                if relative_path:
                    info_path = f'{relative_path}/{info_path}'
                pkg_info['package_info'] = info_path

            # List direct source files (not recursive — sub-packages have their own entry)
            direct_files = sorted(
                f.name
                for f in pkg_dir.iterdir()
                if f.is_file() and f.suffix in all_suffixes and f.name != 'package-info.java'
            )
            if direct_files:
                pkg_info['files'] = direct_files

            packages[pkg_name] = pkg_info

    return packages
