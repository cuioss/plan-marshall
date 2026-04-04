#!/usr/bin/env python3
"""Extension API for pm-dev-frontend-cui bundle.

Provides CUI-specific JavaScript project patterns for Maven integration,
project structure, and SonarQube.

This is an ADDITIVE bundle - it extends pm-dev-frontend rather than standing alone.
It intentionally does NOT provide triage; it relies on pm-dev-frontend:ext-triage-js.
"""

from extension_base import ExtensionBase  # type: ignore[import-not-found]


class Extension(ExtensionBase):
    """CUI JavaScript extension for pm-dev-frontend-cui bundle."""

    def get_skill_domains(self) -> list[dict]:
        """Domain metadata for skill loading."""
        return [
            {
                'domain': {
                    'key': 'javascript-cui',
                    'name': 'CUI JavaScript Development',
                    'description': 'CUI-specific JavaScript project patterns for Maven integration and project structure',
                },
                'profiles': {
                    'core': {
                        'defaults': [
                            {
                                'skill': 'pm-dev-frontend-cui:cui-javascript-project',
                                'description': 'CUI JavaScript project structure, package.json configuration, and Maven integration standards',
                            },
                        ],
                        'optionals': [],
                    },
                    'implementation': {'defaults': [], 'optionals': []},
                    'module_testing': {'defaults': [], 'optionals': []},
                    'quality': {'defaults': [], 'optionals': []},
                },
            }
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        """Check if CUI JavaScript domain applies. Additive to 'javascript'.

        CUI JS modules have both npm and maven (dual build system).
        The frontend-maven-plugin drives npm from Maven, making dual presence
        the definitive signal for CUI-style frontend modules.
        """
        build_systems = module_data.get('build_systems', [])
        # CUI JS modules have both npm and maven (dual build system)
        if 'npm' not in build_systems or 'maven' not in build_systems:
            return {
                'applicable': False,
                'confidence': 'none',
                'signals': [],
                'additive_to': None,
                'skills_by_profile': {},
            }

        signals = [f'build_systems={",".join(build_systems)}']

        # Check for CUI dependencies as additional signal
        deps = module_data.get('dependencies', [])
        dep_strings = [d if isinstance(d, str) else '' for d in deps]
        cui_deps = [d for d in dep_strings if 'de.cuioss' in d]
        if cui_deps:
            signals.append(f'de.cuioss:* deps ({len(cui_deps)} found)')

        # frontend-maven-plugin is the canonical Maven-managed frontend signal
        frontend_maven_deps = [d for d in dep_strings if 'frontend-maven-plugin' in d]
        if frontend_maven_deps:
            signals.append('frontend-maven-plugin detected')

        return self._build_applicable_result(
            'high', signals, additive_to='javascript', module_data=module_data, active_profiles=active_profiles
        )

    def config_defaults(self, project_root: str) -> None:
        """Configure CUI-specific Maven defaults for frontend modules.

        CUI JavaScript modules are built via frontend-maven-plugin inside Maven,
        so Maven profile conventions apply identically to Java modules.

        Sets project-specific configuration for CUI Open Source projects:
        - Profile mappings for standard CUI profiles (pre-commit, coverage)
        - Skip list for internal/infrastructure profiles

        Uses write-once semantics - only sets values if not already configured.

        See: plan-marshall:build-maven:standards/maven-impl.md
        """
        from _config_core import ext_defaults_set_default  # type: ignore[import-not-found]
        from _maven_cmd_discover import EXT_KEY_PROFILES_MAP, EXT_KEY_PROFILES_SKIP  # type: ignore[import-not-found]
        from plan_logging import log_entry  # type: ignore[import-not-found]

        log_entry('script', 'global', 'INFO', '[CUI-FRONTEND-EXT] Configuring CUI Maven defaults for frontend module')

        # CUI standard profile mappings for frontend modules
        # pre-commit → quality-gate, coverage → coverage
        ext_defaults_set_default(EXT_KEY_PROFILES_MAP, 'pre-commit:quality-gate,coverage:coverage', project_root)

        # Skip internal profiles that shouldn't generate commands
        ext_defaults_set_default(
            EXT_KEY_PROFILES_SKIP,
            'build-plantuml,release,release-snapshot,license-cleanup,sonar,only-eclipse,release-pom',
            project_root,
        )
