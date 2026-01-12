#!/usr/bin/env python3
"""Extension API for pm-plugin-development bundle.

Provides skill-only domain detection for plugin development projects.
"""

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
                "testing": {
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
        return "pm-plugin-development:plugin-triage"

    def provides_outline(self) -> str | None:
        """Return outline skill reference."""
        return "pm-plugin-development:plugin-solution-outline"
