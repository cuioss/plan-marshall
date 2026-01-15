#!/usr/bin/env python3
"""Extension API for pm-documents bundle.

Provides skill-only domain detection for documentation projects.
"""

from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Documentation extension for pm-documents bundle."""

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-documents:ext-triage-docs'

    def provides_outline(self) -> str | None:
        """Return outline skill reference for documentation domain."""
        return 'pm-documents:ext-outline-docs'

    def get_skill_domains(self) -> dict:
        """Domain metadata for skill loading."""
        return {
            'domain': {
                'key': 'documentation',
                'name': 'Documentation',
                'description': 'AsciiDoc documentation, ADRs, and interface specifications',
            },
            'profiles': {
                'core': {'defaults': ['pm-documents:ref-documentation'], 'optionals': []},
                'implementation': {
                    'defaults': [],
                    'optionals': ['pm-documents:manage-adr', 'pm-documents:manage-interface'],
                },
                'module_testing': {'defaults': [], 'optionals': []},
                'quality': {'defaults': [], 'optionals': []},
                'documentation': {
                    'defaults': ['pm-documents:ref-documentation'],
                    'optionals': ['pm-documents:manage-adr', 'pm-documents:manage-interface'],
                },
            },
        }
