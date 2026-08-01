#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Extension API for pm-plugin-development bundle.

Owns two axes of the extension contract:

- **Axis-A** (:class:`ExtensionBase`) — skill domains, triage, outline skill, and
  module discovery. Marketplace bundles are discovered as modules for the
  per-module architecture layout (a top-level ``_project.json`` plus one
  ``{module}/derived.json`` per indexed module under
  ``.plan/project-architecture/``).
- **Axis-C** (:class:`DerivationResolverBase`) — the ``markdown`` derivation
  resolver, a pure join over the ``component_refs`` field ``discover_modules``
  materializes. Markdown cross-references (script notation, skill references,
  relative-path xrefs, ``implements:``) are marketplace domain knowledge, and
  the bundle that already understands that data is the one that owns it.

The Axis-C methods are opted into by multiple inheritance, the only shape
reachable from both otherwise-disjoint hierarchies.
"""

import sys
from pathlib import Path

# Allow direct invocation and testing — executor sets PYTHONPATH for production
SCRIPTS_DIR = Path(__file__).parent / 'scripts'
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from extension_base import DerivationResolverBase, ExtensionBase  # noqa: E402

MARKDOWN_DEP_TYPES = frozenset({'script', 'skill', 'path', 'implements'})
"""Reference kinds the markdown resolver owns.

``import`` is deliberately absent: Python-import edges belong to the python
resolver on the ``pm-dev-python`` extension. The split is the point — every
derived edge names which of the two resolvers produced it — so an ``import``
entry is outside this resolver's scope rather than a suppressed edge, and
carries no note.
"""

SUPPRESSION_CATEGORIES = ('unresolved-target', 'unknown-endpoint', 'self-edge')
"""Suppression buckets reported in ``notes[]``, in emission order."""

NOTE_SAMPLE_LIMIT = 3
"""Maximum suppressed references named inline in a single aggregated note."""


class Extension(ExtensionBase, DerivationResolverBase):
    """Plugin development extension and markdown module-edge derivation resolver."""

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
                    'security': {
                        'defaults': [
                            {
                                'skill': 'pm-plugin-development:plugin-security',
                                'description': 'Marketplace meta-project security — the Python script surface (subprocess, path traversal, env trust, config-key handling) and the markdown trust surface (untrusted-ingestion boundary, prompt-injection)',
                            },
                        ],
                        'optionals': [],
                    },
                },
            }
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        """Check if plugin development domain applies based on marketplace structure."""
        build_systems = module_data.get('build_systems') or []
        if 'marshall-plugin' in build_systems:
            return self._build_applicable_result(
                'high', ['build_systems=marshall-plugin'], module_data=module_data, active_profiles=active_profiles
            )

        paths = module_data.get('paths') or {}
        module_path = str(paths.get('module') or '')
        if 'marketplace' in module_path or 'bundles' in module_path:
            return self._build_applicable_result(
                'high', ['marketplace structure detected'], module_data=module_data, active_profiles=active_profiles
            )

        return {'applicable': False, 'confidence': 'none', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-plugin-development:ext-triage-plugin'

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

    # =========================================================================
    # Axis-C: module-edge derivation (the markdown cross-reference join)
    # =========================================================================

    def derivation_resolver_id(self) -> str:
        """Return the stable provenance identity stamped onto every markdown edge.

        See extension-api/standards/ext-point-derivation-resolver.md for the
        complete four-face contract this identity participates in.
        """
        return 'markdown'

    @staticmethod
    def _aggregate_notes(suppressed: dict[str, list[str]]) -> list[str]:
        """Render one aggregated note per non-empty suppression category.

        Aggregation is load-bearing rather than cosmetic. ``merge_resolver_edges``
        appends one note per dropped candidate, so a per-reference note would
        produce hundreds of entries and make the per-resolver report unreadable —
        which would defeat the reporting obligation instead of satisfying it. One
        note per category, carrying the full count plus a bounded sample, keeps
        every suppression visible without drowning the report.

        Args:
            suppressed: Category name → the ``source -> target [dep_type]``
                descriptions suppressed under it.

        Returns:
            One note per non-empty category, in :data:`SUPPRESSION_CATEGORIES`
            order. Samples are sorted so the note is byte-stable.
        """
        notes: list[str] = []
        for category in SUPPRESSION_CATEGORIES:
            candidates = sorted(suppressed[category])
            if not candidates:
                continue
            sample = ', '.join(candidates[:NOTE_SAMPLE_LIMIT])
            overflow = len(candidates) - NOTE_SAMPLE_LIMIT
            suffix = f' (+{overflow} more)' if overflow > 0 else ''
            notes.append(
                f'{category}: {len(candidates)} reference(s) suppressed - sample: {sample}{suffix}'
            )
        return notes

    def derive_edges(
        self,
        derived_by_name: dict,
        enriched_by_name: dict,
    ) -> tuple[list[tuple[str, str]], list[str]]:
        """Derive module edges from materialized markdown cross-references.

        A pure join over the ``component_refs`` field ``discover_modules``
        materializes: each entry is a ``{target_bundle, dep_type, resolved}``
        triple already projected from the engine's component vocabulary
        (``bundle:skill:script``) onto module granularity. The engine that
        detected those references reads files from disk, so it runs at discovery
        time; this method performs no file I/O and runs no subprocess, as the
        Axis-C purity contract requires.

        Only the four markdown reference kinds contribute
        (:data:`MARKDOWN_DEP_TYPES`); ``import`` entries belong to the sibling
        python resolver and are skipped without a note, since they are outside
        this resolver's scope rather than suppressed by it.

        Three conditions suppress a candidate edge, and each is reported in
        aggregated form: a reference whose target does not exist in the
        marketplace (``unresolved-target``), a target naming no known module
        (``unknown-endpoint``), and a reference from a bundle to itself
        (``self-edge``). Self-edges are dropped here as well as by the core
        merge, so this resolver's own ``edge_count`` report stays honest.

        The enriched overlay is unused: the precedence of a curated
        ``internal_dependencies`` declaration OVER a derived edge set is core's
        decision, applied ahead of the resolver call.

        Args:
            derived_by_name: Module name → derived data. Modules discovered by
                another extension carry no ``component_refs`` and contribute
                nothing.
            enriched_by_name: Module name → LLM-curated overlay. Unused here.

        Returns:
            An ``(edges, notes)`` tuple. ``edges`` is the sorted, deduplicated
            list of ``(dependent, dependency)`` module-name pairs. ``notes``
            carries one aggregated entry per non-empty suppression category.
        """
        edges: set[tuple[str, str]] = set()
        suppressed: dict[str, list[str]] = {category: [] for category in SUPPRESSION_CATEGORIES}

        for module_name, module_data in derived_by_name.items():
            for ref in module_data.get('component_refs') or []:
                dep_type = ref.get('dep_type')
                if dep_type not in MARKDOWN_DEP_TYPES:
                    continue

                target = ref.get('target_bundle')
                candidate = f'{module_name} -> {target} [{dep_type}]'

                if not ref.get('resolved'):
                    suppressed['unresolved-target'].append(candidate)
                elif target not in derived_by_name:
                    suppressed['unknown-endpoint'].append(candidate)
                elif target == module_name:
                    suppressed['self-edge'].append(candidate)
                else:
                    edges.add((module_name, target))

        return sorted(edges), self._aggregate_notes(suppressed)
