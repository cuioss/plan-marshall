#!/usr/bin/env python3
"""Extension API for pm-dev-frontend-cui bundle.

Provides CUI-specific JavaScript project patterns for Maven integration,
Quarkus DevUI, NiFi, and SonarQube.

This is an ADDITIVE bundle - it extends pm-dev-frontend rather than standing alone.
It intentionally does NOT provide triage; it relies on pm-dev-frontend:ext-triage-js.
"""

from extension_base import ExtensionBase  # type: ignore[import-not-found]


class Extension(ExtensionBase):
    """CUI JavaScript extension for pm-dev-frontend-cui bundle."""

    def get_skill_domains(self) -> list[dict]:
        """Domain metadata for skill loading."""
        return [{
            'domain': {
                'key': 'javascript-cui',
                'name': 'CUI JavaScript Development',
                'description': 'CUI-specific JavaScript project patterns for Maven integration and project structure',
            },
            'profiles': {
                'core': {
                    'defaults': [],
                    'optionals': ['pm-dev-frontend-cui:cui-javascript-project'],
                },
                'implementation': {'defaults': [], 'optionals': []},
                'module_testing': {'defaults': [], 'optionals': []},
                'quality': {'defaults': [], 'optionals': []},
            },
        }]

    def applies_to_module(self, module_data: dict,
                          active_profiles: set[str] | None = None) -> dict:
        """Check if CUI JavaScript domain applies. Additive to 'javascript'."""
        build_systems = module_data.get('build_systems', [])
        # CUI JS modules have both npm and maven (dual build system)
        if 'npm' not in build_systems or 'maven' not in build_systems:
            return {'applicable': False, 'confidence': 'none', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}

        signals = [f'build_systems={",".join(build_systems)}']

        # Check for CUI dependencies as additional signal
        deps = module_data.get('dependencies', [])
        dep_strings = [d if isinstance(d, str) else '' for d in deps]
        cui_deps = [d for d in dep_strings if 'de.cuioss' in d]
        if cui_deps:
            signals.append(f'de.cuioss:* deps ({len(cui_deps)} found)')

        return self._build_applicable_result('high', signals, additive_to='javascript',
                                              module_data=module_data,
                                              active_profiles=active_profiles)
