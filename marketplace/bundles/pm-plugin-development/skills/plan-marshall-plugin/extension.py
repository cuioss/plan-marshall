#!/usr/bin/env python3
"""Extension API for pm-plugin-development bundle.

Provides module discovery and skill domains for plugin development projects.
Discovers marketplace bundles as modules for derived-data.json generation.
"""

import sys
from pathlib import Path

# Allow direct invocation and testing — executor sets PYTHONPATH for production
SCRIPTS_DIR = Path(__file__).parent / 'scripts'
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from extension_base import ExtensionBase  # noqa: E402


class Extension(ExtensionBase):
    """Plugin development extension for pm-plugin-development bundle."""

    def get_skill_domains(self) -> list[dict]:
        """Domain metadata for skill loading."""
        return [
            {
                'domain': {
                    'key': 'plan-marshall-plugin-dev',
                    'name': 'Plugin Development',
                    'description': 'marketplace component development',
                },
                'profiles': {
                    'core': {
                        'defaults': [
                            {
                                'skill': 'pm-plugin-development:plugin-architecture',
                                'description': 'Architecture principles, skill patterns, and design guidance for building marketplace components',
                            }
                        ],
                        'optionals': [
                            {
                                'skill': 'pm-plugin-development:plugin-script-architecture',
                                'description': 'Script development standards covering implementation patterns, testing, and output contracts',
                            },
                            {
                                'skill': 'plan-marshall:ref-toon-format',
                                'description': 'TOON format knowledge for output specifications - use when migrating to/from TOON',
                            },
                        ],
                    },
                    'implementation': {'defaults': [], 'optionals': []},
                    'module_testing': {'defaults': [], 'optionals': []},
                    'quality': {'defaults': [], 'optionals': []},
                },
            }
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        """Check if plugin development domain applies based on marketplace structure."""
        build_systems = module_data.get('build_systems', [])
        if 'marshall-plugin' in build_systems:
            return self._build_applicable_result(
                'high', ['build_systems=marshall-plugin'], module_data=module_data, active_profiles=active_profiles
            )

        paths = module_data.get('paths', {})
        module_path = str(paths.get('module', ''))
        if 'marketplace' in module_path or 'bundles' in module_path:
            return self._build_applicable_result(
                'high', ['marketplace structure detected'], module_data=module_data, active_profiles=active_profiles
            )

        return {'applicable': False, 'confidence': 'none', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-plugin-development:ext-triage-plugin'

    def provides_outline_skill(self) -> str | None:
        """Return domain-specific outline skill for plugin development.

        The skill's standards/ directory contains change-{type}.md
        sub-skill instructions for feature, enhancement, bug_fix, and
        tech_debt. Other types (analysis, verification) fall back to
        generic plan-marshall:phase-3-outline standards.
        """
        return 'pm-plugin-development:ext-outline-workflow'

    def discover_modules(self, project_root: str) -> list:
        """Discover plugin bundles as modules.

        Each marketplace bundle becomes a module with:
        - build_systems: ["marshall-plugin"]
        - packages: skills, agents, commands
        - commands: module-tests, quality-gate

        Args:
            project_root: Absolute path to project root.

        Returns:
            List of module dicts if marketplace/bundles exists, else empty list.
        """
        bundles_path = Path(project_root) / 'marketplace' / 'bundles'
        if not bundles_path.exists():
            return []

        from plugin_discover import discover_plugin_modules

        return discover_plugin_modules(project_root)
