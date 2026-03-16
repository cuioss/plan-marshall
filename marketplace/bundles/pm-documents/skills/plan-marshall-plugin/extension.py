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

    # Note: Documentation domain uses generic workflow-outline-change-type standards from plan-marshall.
    # Domain-specific skills can be added later if needed by implementing
    # provides_outline_skill() with documentation-specific outline instructions.

    def get_skill_domains(self) -> list[dict]:
        """Domain metadata for skill loading."""
        return [{
            'domain': {
                'key': 'documentation',
                'name': 'Documentation',
                'description': 'AsciiDoc documentation, ADRs, and interface specifications',
            },
            'profiles': {
                'core': {
                    'defaults': [
                        {
                            'skill': 'pm-documents:ref-documentation',
                            'description': 'General documentation standards for README, AsciiDoc, and technical documentation',
                        }
                    ],
                    'optionals': [],
                },
                'documentation': {
                    'defaults': [
                        {
                            'skill': 'pm-documents:ref-documentation',
                            'description': 'General documentation standards for README, AsciiDoc, and technical documentation',
                        }
                    ],
                    'optionals': [
                        {
                            'skill': 'pm-documents:manage-adr',
                            'description': 'Manage Architectural Decision Records with CRUD operations and AsciiDoc formatting',
                        },
                        {
                            'skill': 'pm-documents:manage-interface',
                            'description': 'Manage Interface specifications with CRUD operations and AsciiDoc formatting',
                        },
                    ],
                },
            },
        }]

    def applies_to_module(self, module_data: dict,
                          active_profiles: set[str] | None = None) -> dict:
        """Check if documentation domain applies based on doc directories."""
        paths = module_data.get('paths', {})
        module_path = paths.get('module', '')
        sources = paths.get('sources', [])

        signals = []
        all_paths = [module_path] + sources
        for p in all_paths:
            p_str = str(p)
            if 'doc' in p_str.lower():
                signals.append(f'doc directory in {p}')

        # Check build_systems for documentation marker
        build_systems = module_data.get('build_systems', [])
        if 'documentation' in build_systems:
            signals.append('build_systems=documentation')

        if not signals:
            return {'applicable': False, 'confidence': 'none', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}

        return self._build_applicable_result('high', signals,
                                              module_data=module_data,
                                              active_profiles=active_profiles)

    def provides_verify_steps(self) -> list[dict]:
        """Return documentation-specific verification steps."""
        return [
            {
                'name': 'doc_sync',
                'agent': 'pm-documents:doc-verify',
                'description': 'Verify documentation is synchronized',
            },
        ]

    def discover_modules(self, project_root: str) -> list:
        """Discover documentation modules in the project.

        Detects projects with documentation by checking for:
        - doc/ or docs/ directory with .adoc or .md files
        - README.adoc at project root

        Returns a single 'documentation' module if documentation is found.
        """
        root = Path(project_root)
        has_documentation = False
        found_doc_dir = 'doc'

        # Check for doc/ or docs/ directory with documentation files
        for doc_dir_name in ['doc', 'docs']:
            doc_dir = root / doc_dir_name
            if doc_dir.is_dir():
                # Check for .adoc or .md files
                adoc_files = list(doc_dir.glob('*.adoc'))
                md_files = list(doc_dir.glob('*.md'))
                if adoc_files or md_files:
                    has_documentation = True
                    found_doc_dir = doc_dir_name
                    break

        # Check for README.adoc at root
        if not has_documentation and (root / 'README.adoc').exists():
            has_documentation = True

        if not has_documentation:
            return []

        return [
            {
                'name': 'documentation',
                'paths': {'module': found_doc_dir},
                'build_systems': ['documentation'],
                'metadata': {
                    'description': 'Project documentation',
                },
            }
        ]
