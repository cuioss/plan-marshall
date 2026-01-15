#!/usr/bin/env python3
"""Extension API for pm-dev-python bundle.

Provides build system detection and module discovery for Python projects
using pyprojectx (pw wrapper).

Uses runtime discovery per extension-api specification:
- Parses pyproject.toml for [tool.pyprojectx.aliases]
- Maps aliases to canonical commands
- Validates ./pw wrapper existence

Note: This extension is mutually exclusive with pm-plugin-development.
It skips module discovery for the plan-marshall marketplace (handled by
pm-plugin-development instead).
"""

import json
import tomllib
from pathlib import Path

# Cross-skill imports (PYTHONPATH set by executor)
from _build_wrapper import has_wrapper  # type: ignore[import-not-found]
from extension_base import ExtensionBase  # type: ignore[import-not-found]

# Build file constant
PYPROJECT_TOML = 'pyproject.toml'

# Marketplace identification
MARKETPLACE_JSON = 'marketplace/.claude-plugin/marketplace.json'
PLAN_MARSHALL_NAME = 'plan-marshall'


def _is_plan_marshall_marketplace(project_root: str) -> bool:
    """Check if this is the plan-marshall marketplace by name.

    The plan-marshall marketplace is handled by pm-plugin-development,
    so pm-dev-python should skip module discovery for it.

    Args:
        project_root: Path to project root directory

    Returns:
        True if this is the plan-marshall marketplace, False otherwise
    """
    marketplace_json = Path(project_root) / MARKETPLACE_JSON
    if not marketplace_json.exists():
        return False
    try:
        data = json.loads(marketplace_json.read_text(encoding='utf-8'))
        name = data.get('name')
        return isinstance(name, str) and name == PLAN_MARSHALL_NAME
    except (OSError, json.JSONDecodeError):
        return False


class Extension(ExtensionBase):
    """Python/pyprojectx extension for pm-dev-python bundle."""

    def get_skill_domains(self) -> dict:
        """Domain metadata for skill loading."""
        return {
            'domain': {
                'key': 'python',
                'name': 'Python Development',
                'description': 'Modern Python with pyprojectx, ruff, mypy, pytest',
            },
            'profiles': {
                'core': {
                    'defaults': ['pm-dev-python:python-best-practices'],
                    'optionals': [],
                },
                'implementation': {
                    'defaults': ['pm-dev-python:python-best-practices'],
                    'optionals': [],
                },
                'module_testing': {
                    'defaults': ['pm-dev-python:python-best-practices'],
                    'optionals': [],
                },
                'quality': {
                    'defaults': ['pm-dev-python:python-best-practices'],
                    'optionals': [],
                },
            },
        }

    def provides_triage(self) -> str | None:
        """Return triage skill reference (future)."""
        return None  # ext-triage-python to be added later

    # =========================================================================
    # discover_modules() Implementation
    # =========================================================================

    def discover_modules(self, project_root: str) -> list:
        """Discover Python modules via runtime inspection.

        Uses runtime discovery per extension-api specification:
        1. Skip if this is the plan-marshall marketplace (handled by pm-plugin-development)
        2. Check pyproject.toml exists
        3. Parse [tool.pyprojectx.aliases] section (using tomllib)
        4. Map aliases to canonical commands
        5. Check ./pw wrapper exists
        6. Return module with discovered commands
        """
        # Skip plan-marshall marketplace (handled by pm-plugin-development)
        if _is_plan_marshall_marketplace(project_root):
            return []

        root = Path(project_root)
        pyproject = root / PYPROJECT_TOML

        if not pyproject.exists():
            return []

        # Parse pyproject.toml for pyprojectx aliases
        aliases = self._discover_aliases(pyproject)
        if not aliases:
            return []  # Not a pyprojectx project

        # Check for wrapper
        if not self._has_wrapper(root):
            return []  # No wrapper available

        # Map to canonical commands
        commands = self._map_to_canonical(aliases)

        # Build module info
        return [self._build_root_module(project_root, commands)]

    def _discover_aliases(self, pyproject: Path) -> dict:
        """Parse [tool.pyprojectx.aliases] from pyproject.toml.

        Args:
            pyproject: Path to pyproject.toml file

        Returns:
            Dict of alias name to command string, or empty dict
        """
        try:
            with open(pyproject, 'rb') as f:
                data = tomllib.load(f)
            aliases = data.get('tool', {}).get('pyprojectx', {}).get('aliases', {})
            # Ensure we return dict (tomllib may return Any from nested gets)
            return dict(aliases) if isinstance(aliases, dict) else {}
        except (OSError, tomllib.TOMLDecodeError):
            return {}

    def _has_wrapper(self, project_root: Path) -> bool:
        """Check if pyprojectx wrapper exists for current platform.

        On Windows: checks for pw.bat
        On Unix: checks for pw

        Args:
            project_root: Project root directory

        Returns:
            True if wrapper exists for current platform, False otherwise
        """
        return bool(has_wrapper(project_root, 'pw', 'pw.bat'))  # Cast: has_wrapper typed as Any

    def _map_to_canonical(self, aliases: dict) -> dict:
        """Map pyprojectx aliases to canonical command strings.

        Per canonical-commands.md, maps discovered aliases to:
        - compile, test-compile, module-tests, quality-gate, verify, clean, coverage

        Args:
            aliases: Dict of alias name to command string from pyprojectx

        Returns:
            Dict of canonical command name to full execute-script command
        """
        base = 'python3 .plan/execute-script.py pm-dev-python:plan-marshall-plugin:python_build run'

        # Canonical command names that we look for in aliases
        # Maps canonical name to alias name (same in this case)
        CANONICAL_MAPPING = {
            'compile': 'compile',
            'test-compile': 'test-compile',
            'module-tests': 'module-tests',
            'quality-gate': 'quality-gate',
            'verify': 'verify',
            'clean': 'clean',
            'coverage': 'coverage',
        }

        commands = {}
        for canonical, alias_name in CANONICAL_MAPPING.items():
            if alias_name in aliases:
                commands[canonical] = f'{base} --commandArgs "{canonical}"'

        return commands

    def _build_root_module(self, project_root: str, commands: dict) -> dict:
        """Build root module descriptor.

        Args:
            project_root: Project root directory
            commands: Dict of canonical commands

        Returns:
            Module dict per build-project-structure.md specification
        """
        root = Path(project_root)

        # Discover source directories
        source_dirs = self._discover_source_dirs(root)
        test_dirs = self._discover_test_dirs(root)

        # Find README
        readme = self._find_readme(root)

        # Build paths object
        paths = {
            'module': '.',
            'descriptor': PYPROJECT_TOML,
            'sources': source_dirs,
            'tests': test_dirs,
        }
        if readme:
            paths['readme'] = readme

        # Build metadata
        metadata = {
            'build_tool': 'pyprojectx',
            'package_manager': 'uv',
        }

        # Count files
        source_files = self._count_python_files(root, source_dirs)
        test_files = self._count_python_files(root, test_dirs)

        return {
            'name': '.',
            'build_systems': ['python'],
            'paths': paths,
            'metadata': metadata,
            'packages': {},
            'dependencies': [],  # Could be enhanced to parse pyproject.toml dependencies
            'stats': {'source_files': source_files, 'test_files': test_files},
            'commands': commands,
        }

    def _discover_source_dirs(self, project_root: Path) -> list:
        """Discover source directories.

        Args:
            project_root: Project root directory

        Returns:
            List of source directory paths relative to project root
        """
        source_dirs = []
        common_src_dirs = ['src', 'marketplace/bundles', 'lib']
        for src_dir in common_src_dirs:
            if (project_root / src_dir).exists():
                source_dirs.append(src_dir)
        return source_dirs

    def _discover_test_dirs(self, project_root: Path) -> list:
        """Discover test directories.

        Args:
            project_root: Project root directory

        Returns:
            List of test directory paths relative to project root
        """
        test_dirs = []
        common_test_dirs = ['test', 'tests']
        for test_dir in common_test_dirs:
            if (project_root / test_dir).exists():
                test_dirs.append(test_dir)
        return test_dirs

    def _find_readme(self, project_root: Path) -> str | None:
        """Find README file.

        Args:
            project_root: Project root directory

        Returns:
            README path relative to project root, or None
        """
        readme_names = ['README.md', 'README', 'readme.md', 'Readme.md', 'README.adoc']
        for name in readme_names:
            if (project_root / name).exists():
                return name
        return None

    def _count_python_files(self, project_root: Path, directories: list) -> int:
        """Count Python files in directories.

        Args:
            project_root: Project root directory
            directories: List of directory paths to count

        Returns:
            Total count of .py files
        """
        count = 0
        for dir_name in directories:
            dir_path = project_root / dir_name
            if dir_path.exists():
                for file in dir_path.rglob('*.py'):
                    if file.is_file():
                        count += 1
        return count
