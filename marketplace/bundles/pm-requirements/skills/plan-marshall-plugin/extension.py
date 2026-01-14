#!/usr/bin/env python3
"""Extension API for pm-requirements bundle.

Provides skill-only domain detection for requirements engineering projects.
"""

from extension_base import ExtensionBase  # type: ignore[import-not-found]


class Extension(ExtensionBase):
    """Requirements extension for pm-requirements bundle."""

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-requirements:ext-triage-reqs'

    def get_skill_domains(self) -> dict:
        """Domain metadata for skill loading."""
        return {
            'domain': {
                'key': 'requirements',
                'name': 'Requirements Engineering',
                'description': 'User stories, acceptance criteria, specifications',
            },
            'profiles': {
                'core': {'defaults': ['pm-requirements:requirements-authoring'], 'optionals': []},
                'implementation': {'defaults': [], 'optionals': []},
                'module_testing': {'defaults': [], 'optionals': []},
                'quality': {'defaults': [], 'optionals': []},
            },
        }
