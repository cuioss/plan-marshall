#!/usr/bin/env python3
"""Extension API for pm-plugin-development bundle.

Provides module discovery and skill domains for plugin development projects.
Discovers marketplace bundles as modules for the per-module architecture
layout (a top-level ``_project.json`` plus one
``{module}/derived.json`` per indexed module under
``.plan/project-architecture/``).
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
                    'implementation': {
                        'defaults': [],
                        'optionals': [
                            {
                                'skill': 'pm-plugin-development:plugin-script-architecture',
                                'description': 'Script development standards, implementation patterns, and output contracts — use for script-heavy plugin tasks',
                            },
                        ],
                    },
                    'module_testing': {
                        'defaults': [],
                        'optionals': [
                            {
                                'skill': 'pm-plugin-development:plugin-script-architecture',
                                'description': 'Script testing patterns and output contract verification',
                            },
                        ],
                    },
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

    # =========================================================================
    # File-type classifier
    # =========================================================================

    # Marketplace skill markdown lives under
    # marketplace/bundles/<bundle>/skills/<skill>/{SKILL.md, workflow/*.md,
    # standards/*.md, references/*.md}. The specificity score reflects the
    # count of non-wildcard path-segment tokens. The aggregator routes the
    # overlap with pm-documents (*.md glob, specificity 0) to this extension
    # via longest-glob-wins.
    _CLASSIFY_PATTERNS: tuple[tuple[str, str, int], ...] = (
        ('marketplace/bundles/*/skills/*/SKILL.md', 'documentation', 4),
        ('marketplace/bundles/*/skills/*/workflow/*.md', 'documentation', 5),
        ('marketplace/bundles/*/skills/*/standards/*.md', 'documentation', 5),
        ('marketplace/bundles/*/skills/*/references/*.md', 'documentation', 5),
    )

    def _match_classify(self, path: str) -> tuple[str, int] | None:
        import fnmatch
        for glob, role, score in self._CLASSIFY_PATTERNS:
            if fnmatch.fnmatchcase(path, glob):
                return role, score
        return None

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        """Classify marketplace skill markdown paths under the documentation role.

        See extension-api/standards/extension-contract.md § classify_paths()
        for the full contract. This extension's globs are deliberately more
        specific than pm-documents's broad *.md glob so that marketplace
        skill markdown routes here under longest-glob-wins.
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
        """Return the (glob, role) inventory derived from _CLASSIFY_PATTERNS.

        Tuple-shape extension: the (glob, role) pairs are the first two elements
        of each _CLASSIFY_PATTERNS entry (the third element is specificity, which
        the build_map seed does not need). All entries claim the documentation
        role (marketplace skill markdown). See the base classify_globs() contract.
        """
        return [(glob, role) for glob, role, _ in self._CLASSIFY_PATTERNS]

    # build_class: this extension claims only the ``documentation`` role
    # (marketplace skill markdown), for which the ExtensionBase default
    # ``documentation → docs-validate`` is correct. No classify_build_class
    # override is required — the inherited base default is the contract.

    def provides_retrospective_aspects(self) -> list[dict]:
        """Return the plan-marshall-plugin-dev retrospective aspects.

        Contributes the ``wrapper-tangle`` aspect — the former Surface C of the
        generic ``plan-marshall:plan-retrospective:direct-gh-glab-usage`` aspect.
        It scans plan-marshall's own CI-abstraction sources
        (``tools-integration-ci``, ``workflow-integration-{github,gitlab}``) for
        subprocess / ``run_gh`` / ``run_glab`` args that tangle a ``gh``/``glab``
        CLI invocation with a local-git mutation. The scan is only meaningful for
        plans authored against the plan-marshall-plugin-dev domain, so it is
        gated by that domain and merged into plan-retrospective only when the
        audited plan matches.

        See extension-api/standards/ext-point-retrospective.md for the contract.
        """
        return [
            {
                'aspect': 'wrapper-tangle',
                'domain': 'plan-marshall-plugin-dev',
                'script': 'pm-plugin-development:plan-marshall-plugin:wrapper-tangle-scan',
                'reference': 'pm-plugin-development:plan-marshall-plugin/references/wrapper-tangle.md',
                'description': 'Scan plan-marshall CI-wrapper sources for tangled gh/glab + local-git mutations',
                'order': 500,
            }
        ]

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
