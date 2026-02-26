#!/usr/bin/env python3
"""Extension API for pm-dev-java bundle.

Minimal wrapper providing build system detection, module discovery,
and command mappings for Maven and Gradle projects.

Implementation logic resides in scripts/ directory.
"""

import sys
from pathlib import Path

from extension_base import ExtensionBase

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent / 'scripts'
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# Build file constants
POM_XML = 'pom.xml'
BUILD_GRADLE = 'build.gradle'
BUILD_GRADLE_KTS = 'build.gradle.kts'
SETTINGS_GRADLE = 'settings.gradle'
SETTINGS_GRADLE_KTS = 'settings.gradle.kts'


class Extension(ExtensionBase):
    """Java/Maven/Gradle extension for pm-dev-java bundle."""

    def get_skill_domains(self) -> dict:
        """Domain metadata for skill loading."""
        return {
            'domain': {
                'key': 'java',
                'name': 'Java Development',
                'description': 'Java code patterns, CDI, JUnit testing, Maven/Gradle builds',
            },
            'profiles': {
                'core': {
                    'defaults': [
                        {
                            'skill': 'pm-dev-java:java-core',
                            'description': 'Core Java patterns including modern features and performance optimization',
                        }
                    ],
                    'optionals': [
                        {
                            'skill': 'pm-dev-java:java-null-safety',
                            'description': 'JSpecify null safety annotations with @NullMarked, @Nullable, and package-level configuration',
                        },
                        {
                            'skill': 'pm-dev-java:java-lombok',
                            'description': 'Lombok patterns including @Delegate, @Builder, @Value, @UtilityClass for reducing boilerplate',
                        },
                    ],
                },
                'implementation': {
                    'defaults': [],
                    'optionals': [
                        {
                            'skill': 'pm-dev-java:java-cdi',
                            'description': 'CDI patterns including constructor injection, scopes, producers, and Quarkus configuration',
                        },
                        {
                            'skill': 'pm-dev-java:java-maintenance',
                            'description': 'Java code maintenance standards including prioritization, refactoring triggers, and compliance',
                        },
                    ],
                },
                'module_testing': {
                    'defaults': [
                        {
                            'skill': 'pm-dev-java:junit-core',
                            'description': 'JUnit 5 testing patterns with AAA structure, coverage analysis, and assertion standards',
                        }
                    ],
                    'optionals': [
                        {
                            'skill': 'pm-dev-java:junit-integration',
                            'description': 'Maven integration testing with Failsafe plugin, IT naming conventions, and profiles',
                        }
                    ],
                },
                'quality': {
                    'defaults': [
                        {
                            'skill': 'pm-dev-java:javadoc',
                            'description': 'JavaDoc documentation standards including class, method, and code example patterns',
                        }
                    ],
                    'optionals': [],
                },
            },
        }

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-dev-java:ext-triage-java'

    def provides_verify_steps(self) -> list[dict]:
        """Return Java-specific verification steps."""
        return [
            {
                'name': 'technical_impl',
                'agent': 'pm-dev-java:java-verify-agent',
                'description': 'Verify implementation standards compliance',
            },
            {
                'name': 'technical_test',
                'agent': 'pm-dev-java:java-coverage-agent',
                'description': 'Verify test coverage meets thresholds',
            },
        ]

    def provides_recipes(self) -> list[dict]:
        """Return Java-specific recipe definitions."""
        return [
            {
                'key': 'refactor-to-standards',
                'name': 'Refactor to Implementation Standards',
                'description': 'Refactor production code to comply with java-core and java-maintenance standards, package by package',
                'skill': 'pm-dev-java:recipe-refactor-to-standards',
                'default_change_type': 'tech_debt',
                'scope': 'codebase_wide',
            },
            {
                'key': 'refactor-to-test-standards',
                'name': 'Refactor to Test Standards',
                'description': 'Refactor test code to comply with junit-core standards, test-package by test-package',
                'skill': 'pm-dev-java:recipe-refactor-to-test-standards',
                'default_change_type': 'tech_debt',
                'scope': 'codebase_wide',
            },
        ]

    def discover_modules(self, project_root: str) -> list:
        """Discover all modules with complete metadata.

        Delegates to maven_cmd_discover.py and gradle_cmd_discover.py.
        """
        modules = []
        root = Path(project_root)

        # Maven modules
        if (root / POM_XML).exists():
            from _maven_cmd_discover import discover_maven_modules

            modules.extend(discover_maven_modules(project_root))

        # Gradle modules (only if no Maven at same path)
        # Note: modules with 'error' key have no paths - include them directly
        maven_paths = {m['paths']['module'] for m in modules if 'paths' in m}
        gradle_files = [BUILD_GRADLE_KTS, BUILD_GRADLE, SETTINGS_GRADLE_KTS, SETTINGS_GRADLE]
        has_gradle = any((root / bf).exists() for bf in gradle_files)
        if has_gradle:
            from _gradle_cmd_discover import discover_gradle_modules

            gradle_modules = discover_gradle_modules(project_root)
            for gm in gradle_modules:
                # Error-only modules (no paths) are always included
                if 'error' in gm or gm['paths']['module'] not in maven_paths:
                    modules.append(gm)

        return modules
