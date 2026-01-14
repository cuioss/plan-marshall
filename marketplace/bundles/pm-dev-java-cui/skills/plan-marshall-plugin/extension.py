#!/usr/bin/env python3
"""Extension API for pm-dev-java-cui bundle.

Provides CUI-specific Java patterns for logging, testing, and HTTP.

This is an ADDITIVE bundle - it extends pm-dev-java rather than standing alone.
It intentionally does NOT provide triage; it relies on pm-dev-java:ext-triage-java.
"""

from extension_base import ExtensionBase  # type: ignore[import-not-found]


class Extension(ExtensionBase):
    """CUI Java extension for pm-dev-java-cui bundle."""

    def get_skill_domains(self) -> dict:
        """Domain metadata for skill loading."""
        return {
            'domain': {
                'key': 'java-cui',
                'name': 'CUI Java Development',
                'description': 'CUI-specific Java patterns for logging, testing, and HTTP',
            },
            'profiles': {
                'core': {'defaults': ['pm-dev-java-cui:cui-logging'], 'optionals': []},
                'implementation': {'defaults': [], 'optionals': ['pm-dev-java-cui:cui-http']},
                'module_testing': {
                    'defaults': [],
                    'optionals': ['pm-dev-java-cui:cui-testing', 'pm-dev-java-cui:cui-testing-http'],
                },
                'quality': {'defaults': [], 'optionals': []},
            },
        }

    def config_defaults(self, project_root: str) -> None:
        """Configure CUI-specific Maven defaults.

        Sets project-specific configuration for CUI Open Source projects:
        - Profile mappings for standard CUI profiles (pre-commit, coverage, javadoc)
        - Skip list for internal/infrastructure profiles

        Uses write-once semantics - only sets values if not already configured.

        See: pm-dev-java:plan-marshall-plugin:standards/maven-impl.md
        """
        from _maven_cmd_discover import EXT_KEY_PROFILES_MAP, EXT_KEY_PROFILES_SKIP  # type: ignore[import-not-found]
        from plan_logging import log_entry  # type: ignore[import-not-found]
        from run_config import ext_defaults_set_default  # type: ignore[import-not-found]

        log_entry('script', 'global', 'INFO', '[CUI-JAVA-EXT] Configuring CUI Maven defaults')

        # CUI standard profile mappings
        # pre-commit → quality-gate, coverage → coverage, javadoc → javadoc
        ext_defaults_set_default(
            EXT_KEY_PROFILES_MAP, 'pre-commit:quality-gate,coverage:coverage,javadoc:javadoc', project_root
        )

        # Skip internal profiles that shouldn't generate commands
        ext_defaults_set_default(
            EXT_KEY_PROFILES_SKIP,
            'build-plantuml,rewrite-maven-clean, release, release-snapshot, license-cleanup, sonar, only-eclipse,release-pom',
            project_root,
        )
