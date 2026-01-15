#!/usr/bin/env python3
"""Extension API for pm-documents bundle.

Provides documentation domain detection for projects with doc directories or AsciiDoc files.
"""

from pathlib import Path

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

    def discover_modules(self, project_root: str) -> list:
        """Discover documentation modules in the project.

        Detects projects with documentation by checking for:
        - doc/ or docs/ directory with .adoc or .md files
        - README.adoc at project root

        Returns a single 'documentation' module if documentation is found.
        """
        root = Path(project_root)
        has_documentation = False

        # Check for doc/ or docs/ directory with documentation files
        for doc_dir_name in ['doc', 'docs']:
            doc_dir = root / doc_dir_name
            if doc_dir.is_dir():
                # Check for .adoc or .md files
                adoc_files = list(doc_dir.glob('*.adoc'))
                md_files = list(doc_dir.glob('*.md'))
                if adoc_files or md_files:
                    has_documentation = True
                    break

        # Check for README.adoc at root
        if not has_documentation and (root / 'README.adoc').exists():
            has_documentation = True

        if not has_documentation:
            return []

        return [
            {
                'name': 'documentation',
                'paths': {'module': 'doc'},
                'build_systems': ['documentation'],
                'metadata': {
                    'description': 'Project documentation',
                },
            }
        ]
