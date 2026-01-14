#!/usr/bin/env python3
"""Extension API for pm-plugin-development bundle.

Provides module discovery and skill domains for plugin development projects.
Discovers marketplace bundles as modules for derived-data.json generation.
"""

import sys
from pathlib import Path

# Add scripts directory to path for plugin_discover import
SCRIPTS_DIR = Path(__file__).parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Plugin development extension for pm-plugin-development bundle."""

    def get_skill_domains(self) -> dict:
        """Domain metadata for skill loading."""
        return {
            "domain": {
                "key": "plan-marshall-plugin-dev",
                "name": "Plugin Development",
                "description": "Claude Code marketplace component development"
            },
            "profiles": {
                "core": {
                    "defaults": ["pm-plugin-development:plugin-architecture"],
                    "optionals": ["pm-plugin-development:plugin-script-architecture"]
                },
                "implementation": {
                    "defaults": [],
                    "optionals": []
                },
                "module_testing": {
                    "defaults": [],
                    "optionals": []
                },
                "quality": {
                    "defaults": [],
                    "optionals": []
                }
            }
        }

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return "pm-plugin-development:ext-triage-plugin"

    def provides_outline(self) -> str | None:
        """Return outline skill reference."""
        return "pm-plugin-development:ext-outline-plugin"

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
        bundles_path = Path(project_root) / "marketplace" / "bundles"
        if not bundles_path.exists():
            return []

        from plugin_discover import discover_plugin_modules

        return discover_plugin_modules(project_root)
