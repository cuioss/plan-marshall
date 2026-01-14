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
                    'defaults': ['pm-dev-java:java-core'],
                    'optionals': ['pm-dev-java:java-null-safety', 'pm-dev-java:java-lombok'],
                },
                'implementation': {
                    'defaults': [],
                    'optionals': ['pm-dev-java:java-cdi', 'pm-dev-java:java-maintenance'],
                },
                'module_testing': {
                    'defaults': ['pm-dev-java:junit-core'],
                    'optionals': ['pm-dev-java:junit-integration'],
                },
                'quality': {'defaults': ['pm-dev-java:javadoc'], 'optionals': []},
            },
        }

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-dev-java:ext-triage-java'

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
