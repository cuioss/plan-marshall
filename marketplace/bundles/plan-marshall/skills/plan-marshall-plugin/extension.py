#!/usr/bin/env python3
"""Extension API for plan-marshall bundle - build system discovery.

Consolidates module discovery for Maven, Gradle, npm, and Python build systems.
Delegates to build-system-specific discovery scripts in sibling skill directories
(build-maven, build-gradle, build-npm, build-python).
"""

from pathlib import Path

from extension_base import ExtensionBase  # type: ignore[import-not-found]

# Build systems that indicate code content (vs documentation or plugin metadata)
_CODE_BUILD_SYSTEMS = {'maven', 'gradle', 'npm', 'python'}

# Build file constants
POM_XML = 'pom.xml'
BUILD_GRADLE = 'build.gradle'
BUILD_GRADLE_KTS = 'build.gradle.kts'
SETTINGS_GRADLE = 'settings.gradle'
SETTINGS_GRADLE_KTS = 'settings.gradle.kts'
PACKAGE_JSON = 'package.json'
PYPROJECT_TOML = 'pyproject.toml'


class Extension(ExtensionBase):
    """Build system discovery and cross-cutting development extension for plan-marshall bundle."""

    def get_skill_domains(self) -> list[dict]:
        """Return both build and general-dev domains."""
        return [
            {
                'domain': {
                    'key': 'build',
                    'name': 'Build Systems',
                    'description': 'Maven, Gradle, npm, and Python build detection and execution',
                },
                'profiles': {},
            },
            self._general_dev_domain(),
        ]

    def _general_dev_domain(self) -> dict:
        """Return general-dev domain metadata for skill loading."""
        return {
            'domain': {
                'key': 'general-dev',
                'name': 'General Development',
                'description': 'Cross-cutting code quality, documentation, and testing methodology',
            },
            'profiles': {
                'core': {
                    'defaults': [
                        {
                            'skill': 'plan-marshall:dev-general-practices',
                            'description': 'Foundational development practices (user interaction, tool usage, research, dependency management)',
                        },
                    ],
                    'optionals': [],
                },
                'implementation': {
                    'defaults': [
                        {
                            'skill': 'plan-marshall:dev-general-code-quality',
                            'description': 'Language-agnostic code quality, refactoring, and documentation principles',
                        },
                    ],
                    'optionals': [],
                },
                'module_testing': {
                    'defaults': [
                        {
                            'skill': 'plan-marshall:dev-general-code-quality',
                            'description': 'Language-agnostic code quality principles (SRP, CQS, complexity, error handling)',
                        },
                        {
                            'skill': 'plan-marshall:dev-general-module-testing',
                            'description': 'Language-agnostic testing methodology (AAA, coverage, reliability, determinism)',
                        },
                    ],
                    'optionals': [],
                },
                'quality': {
                    'defaults': [
                        {
                            'skill': 'plan-marshall:dev-general-code-quality',
                            'description': 'Language-agnostic code quality, refactoring, and documentation principles',
                        },
                    ],
                    'optionals': [],
                },
            },
        }

    def provides_recipes(self) -> list[dict]:
        """Return built-in recipes provided by plan-marshall."""
        return [
            {
                'key': 'refactor-to-profile-standards',
                'name': 'Refactor to Profile Standards',
                'description': 'Refactor code to comply with configured profile standards, package by package',
                'skill': 'plan-marshall:recipe-refactor-to-profile-standards',
                'default_change_type': 'tech_debt',
                'scope': 'codebase_wide',
            },
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        """Applicable only to modules with code build systems.

        Uses general-dev domain skills (not build domain, which has empty profiles).
        """
        build_systems = set(module_data.get('build_systems', []))
        if not build_systems & _CODE_BUILD_SYSTEMS:
            return {
                'applicable': False,
                'confidence': 'none',
                'signals': [],
                'additive_to': None,
                'skills_by_profile': {},
            }

        return self._build_applicable_result(
            'high',
            ['cross-cutting'],
            module_data=module_data,
            active_profiles=active_profiles,
            domain_key='general-dev',
        )

    # =========================================================================
    # discover_modules() - Consolidated build system discovery
    # =========================================================================

    def discover_modules(self, project_root: str) -> list:
        """Discover all modules across Maven, Gradle, npm, and Python.

        Delegates to build-system-specific discovery scripts:
        - Maven: build-maven/scripts/_maven_cmd_discover.py
        - Gradle: build-gradle/scripts/_gradle_cmd_discover.py
        - npm: build-npm/scripts/_npm_cmd_discover.py
        - Python: build-python/scripts/_python_cmd_discover.py
        """
        modules = []

        # Maven modules
        modules.extend(self._discover_maven(project_root))

        # Gradle modules (avoid duplicates with Maven)
        modules.extend(self._discover_gradle(project_root, modules))

        # npm modules
        modules.extend(self._discover_npm(project_root))

        # Python modules
        modules.extend(self._discover_python(project_root))

        # Cross-extension: find nested build descriptors missed by primary discovery
        modules.extend(self._discover_nested_descriptors(project_root, modules))

        return modules

    # =========================================================================
    # Maven Discovery
    # =========================================================================

    def _discover_maven(self, project_root: str) -> list:
        """Discover Maven modules via pom.xml analysis."""
        root = Path(project_root)
        if not (root / POM_XML).exists():
            return []

        from _maven_cmd_discover import discover_maven_modules

        return discover_maven_modules(project_root)

    # =========================================================================
    # Gradle Discovery
    # =========================================================================

    def _discover_gradle(self, project_root: str, existing_modules: list) -> list:
        """Discover Gradle modules, excluding those already found by Maven."""
        root = Path(project_root)
        gradle_files = [BUILD_GRADLE_KTS, BUILD_GRADLE, SETTINGS_GRADLE_KTS, SETTINGS_GRADLE]
        has_gradle = any((root / bf).exists() for bf in gradle_files)
        if not has_gradle:
            return []

        from _gradle_cmd_discover import discover_gradle_modules

        maven_paths = {m['paths']['module'] for m in existing_modules if 'paths' in m}
        gradle_modules = discover_gradle_modules(project_root)

        result = []
        for gm in gradle_modules:
            # Error-only modules (no paths) are always included
            if 'error' in gm or gm['paths']['module'] not in maven_paths:
                result.append(gm)
        return result

    # =========================================================================
    # npm Discovery (delegated to build-npm)
    # =========================================================================

    def _discover_npm(self, project_root: str) -> list:
        """Discover npm modules via package.json analysis.

        Delegates to build-npm/scripts/_npm_cmd_discover.py which handles
        workspaces, metadata enrichment, and canonical command generation.
        """
        root = Path(project_root)
        if not (root / PACKAGE_JSON).exists():
            return []

        from _npm_cmd_discover import discover_npm_modules

        return discover_npm_modules(project_root)

    # =========================================================================
    # Cross-Extension Nested Discovery
    # =========================================================================

    def _discover_nested_descriptors(self, project_root: str, existing_modules: list) -> list:
        """Discover nested build descriptors missed by primary discovery.

        Scans module paths discovered by one build system for co-located
        descriptors from other build systems. For example, a Maven module
        at path/e2e-playwright/ may also contain a package.json for npm.

        Args:
            project_root: Absolute path to project root.
            existing_modules: Modules already discovered by primary discovery.

        Returns:
            List of additional module dicts for nested descriptors.
        """
        root = Path(project_root)

        # Collect paths already covered by each build system
        npm_paths = set()
        non_npm_paths = set()
        gradle_paths = set()
        non_gradle_paths = set()

        for mod in existing_modules:
            if 'paths' not in mod:
                continue
            mod_path = mod['paths']['module']
            build_systems = set(mod.get('build_systems', []))
            if 'npm' in build_systems:
                npm_paths.add(mod_path)
            else:
                non_npm_paths.add(mod_path)
            if 'gradle' in build_systems:
                gradle_paths.add(mod_path)
            else:
                non_gradle_paths.add(mod_path)

        nested = []

        # Find package.json in non-npm module paths
        for mod_path in non_npm_paths:
            abs_path = root / mod_path if mod_path != '.' else root
            if (abs_path / PACKAGE_JSON).exists() and mod_path not in npm_paths:
                from _npm_cmd_discover import discover_standalone_npm_module

                module = discover_standalone_npm_module(project_root, str(abs_path))
                if module:
                    nested.append(module)

        # Find build.gradle[.kts] in non-gradle module paths
        for mod_path in non_gradle_paths:
            abs_path = root / mod_path if mod_path != '.' else root
            gradle_files = [BUILD_GRADLE_KTS, BUILD_GRADLE]
            has_gradle = any((abs_path / gf).exists() for gf in gradle_files)
            if has_gradle and mod_path not in gradle_paths:
                from _gradle_cmd_discover import discover_gradle_modules

                gradle_modules = discover_gradle_modules(project_root)
                for gm in gradle_modules:
                    if 'paths' in gm and gm['paths']['module'] == mod_path:
                        nested.append(gm)
                        break

        return nested

    # =========================================================================
    # Python Discovery (delegated to build-python)
    # =========================================================================

    def _discover_python(self, project_root: str) -> list:
        """Discover Python modules via pyprojectx project analysis.

        Delegates to build-python/scripts/_python_cmd_discover.py which handles
        module detection, metadata extraction, and canonical command generation.
        """
        root = Path(project_root)
        if not (root / PYPROJECT_TOML).exists():
            return []

        from _python_cmd_discover import discover_python_modules

        return discover_python_modules(project_root)
