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

    # Note: Documentation domain uses generic phase-3-outline standards from plan-marshall.
    # Domain-specific skills can be added later if needed by implementing
    # provides_outline_skill() with documentation-specific outline instructions.

    def get_skill_domains(self) -> list[dict]:
        """Domain metadata for skill loading."""
        return [
            {
                'domain': {
                    'key': 'documentation',
                    'name': 'Documentation',
                    'description': 'AsciiDoc documentation, ADRs, and interface specifications',
                },
                'profiles': {
                    'core': {
                        'defaults': [
                            {
                                'skill': 'pm-documents:ref-asciidoc',
                                'description': 'AsciiDoc formatting, validation, link verification, and template creation',
                            },
                            {
                                'skill': 'pm-documents:ref-documentation',
                                'description': 'Content quality, tone analysis, organization standards, and review orchestration',
                            },
                            {
                                'skill': 'pm-documents:ref-narrative-styles',
                                'description': 'Narrative styles for technical documentation — tone, voice, and arc per surface (concept pages, user guides, spec references)',
                            },
                            {
                                'skill': 'pm-documents:ref-svg-diagrams',
                                'description': 'SVG diagram authoring standards — visual language, theme handling, AsciiDoc embedding, per-diagram-type patterns',
                            },
                        ],
                        'optionals': [],
                    },
                    'documentation': {
                        'defaults': [],
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
            }
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
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
            return {
                'applicable': False,
                'confidence': 'none',
                'signals': [],
                'additive_to': None,
                'skills_by_profile': {},
            }

        return self._build_applicable_result('high', signals, module_data=module_data, active_profiles=active_profiles)

    def provides_verify_steps(self) -> list[dict]:
        """No verify steps — documentation verification is handled via recipe."""
        return []

    # =========================================================================
    # File-type classifier
    # =========================================================================

    # Documentation files — *.md, *.adoc, *.asciidoc — but EXCLUDING any
    # markdown that lives under marketplace/bundles/*/skills/, which is
    # claimed by pm-plugin-development with a more specific glob. Both
    # extensions emit claims; the aggregator's longest-glob-wins overlap
    # resolution routes the overlap to pm-plugin-development.
    _DOC_SUFFIXES: tuple[str, ...] = ('.md', '.adoc', '.asciidoc')

    def _match_classify(self, path: str) -> tuple[str, int] | None:
        for suffix in self._DOC_SUFFIXES:
            if path.endswith(suffix):
                return 'documentation', 0
        return None

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        """Classify paths for the documentation domain.

        Claims every *.md / *.adoc / *.asciidoc path under the documentation
        role. The aggregator routes overlap with pm-plugin-development's
        marketplace-skill glob to pm-plugin-development via longest-glob-wins.

        See extension-api/standards/extension-contract.md § classify_paths()
        for the full contract.
        """
        claims: dict[str, list[str]] = {
            'production': [], 'test': [], 'documentation': [], 'config': []
        }
        for path in paths:
            match = self._match_classify(path)
            if match is not None:
                claims[match[0]].append(path)
        return claims

    def classify_path_specificity(self, path: str, role: str) -> int:
        match = self._match_classify(path)
        if match is not None and match[0] == role:
            return match[1]
        return 0

    def classify_globs(self) -> list[tuple[str, str]]:
        """Return an explicit (glob, role) inventory synthesized from the rules.

        Hand-rolled extension (no _CLASSIFY_PATTERNS tuple): _match_classify uses
        suffix checks, so there is no tuple to derive from. Each documentation
        suffix becomes a ``*{suffix}`` glob claiming the documentation role. See
        the base classify_globs() contract.
        """
        return [(f'*{suffix}', 'documentation') for suffix in self._DOC_SUFFIXES]

    # build_class: this extension claims only the ``documentation`` role
    # (*.md / *.adoc / *.asciidoc), for which the ExtensionBase default
    # ``documentation → docs-validate`` is correct. No classify_build_class
    # override is required — the inherited base default is the contract.

    def provides_recipes(self) -> list[dict]:
        """Return documentation recipes."""
        return [
            {
                'key': 'doc-verify',
                'name': 'Verify Documentation Quality',
                'description': 'Validate AsciiDoc format, links, and documentation drift',
                'skill': 'pm-documents:recipe-doc-verify',
                'default_change_type': 'verification',
                'scope': 'codebase_wide',
            },
            {
                'key': 'verify-architecture-diagrams',
                'name': 'Verify Architecture Diagrams',
                'description': 'Verify and update PlantUML diagrams to reflect current codebase state',
                'skill': 'pm-documents:recipe-verify-architecture-diagrams',
                'default_change_type': 'tech_debt',
                'scope': 'codebase_wide',
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
