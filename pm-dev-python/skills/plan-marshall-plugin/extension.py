#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Extension API for pm-dev-python bundle.

Owns two axes of the extension contract:

- **Axis-A** (:class:`ExtensionBase`) — slim domain registration providing skill
  domains, module applicability, triage, and the arch-gate tool binding for
  Python projects.
- **Axis-C** (:class:`DerivationResolverBase`) — the ``python`` derivation
  resolver, a pure join over the ``component_refs`` field module discovery
  materializes. Python-import edges are Python-language knowledge, so they
  belong to the Python domain bundle rather than to a build-system bundle.

Build operations (pyproject_build) have moved to plan-marshall:build-pyproject.
Module discovery is in plan-marshall:plan-marshall-plugin.
"""

from extension_base import DerivationResolverBase, ExtensionBase

PYTHON_DEP_TYPE = 'import'
"""The single reference kind this resolver owns.

The markdown reference kinds (``script`` / ``skill`` / ``path`` /
``implements``) belong to the sibling markdown resolver on
``pm-plugin-development``. The split is the point — every derived edge names
which of the two resolvers produced it — so a non-``import`` entry is outside
this resolver's scope rather than an edge it suppressed, and carries no note.
"""

SUPPRESSION_CATEGORIES = ('unresolved-target', 'unknown-endpoint', 'self-edge')
"""Suppression buckets reported in ``notes[]``, in emission order.

The rendering of those buckets is not this resolver's business — the shared
``DerivationResolverBase._aggregate_notes`` renders whatever categories it is
handed, in the order they are seeded here.
"""


class Extension(ExtensionBase, DerivationResolverBase):
    """Python domain extension and python-import module-edge derivation resolver."""

    def get_skill_domains(self) -> list[dict]:
        """Domain metadata for skill loading."""
        return [
            {
                'domain': {
                    'key': 'python',
                    'name': 'Python Development',
                    'description': 'Modern Python with pyprojectx, ruff, mypy, pytest',
                },
                'profiles': {
                    'core': {
                        'defaults': [
                            {
                                'skill': 'pm-dev-python:python-core',
                                'description': 'Core Python patterns — types, data structures, error handling, naming',
                            },
                            {
                                'skill': 'plan-marshall:ref-code-quality',
                                'description': 'Language-agnostic code quality principles (SRP, CQS, complexity, error handling)',
                            },
                        ],
                        'optionals': [],
                    },
                    'implementation': {
                        'defaults': [
                            {
                                'skill': 'pm-dev-python:python-core',
                                'description': 'Core Python patterns — types, data structures, error handling, naming',
                            },
                            {
                                'skill': 'plan-marshall:ref-code-quality',
                                'description': 'Language-agnostic code quality, refactoring, and documentation principles',
                            },
                        ],
                        'optionals': [],
                    },
                    'module_testing': {
                        'defaults': [
                            {
                                'skill': 'pm-dev-python:pytest-testing',
                                'description': 'Pytest standards — fixtures, isolation, mocking, assertions, coverage',
                            },
                            {
                                'skill': 'plan-marshall:persona-module-tester',
                                'description': 'Language-agnostic testing methodology (AAA, coverage, reliability, determinism)',
                            },
                        ],
                        'optionals': [],
                    },
                    'quality': {
                        'defaults': [
                            {
                                'skill': 'pm-dev-python:python-core',
                                'description': 'Core Python patterns — types, data structures, error handling, naming',
                            },
                            {
                                'skill': 'plan-marshall:ref-code-quality',
                                'description': 'Language-agnostic code quality principles (SRP, CQS, complexity, error handling)',
                            },
                        ],
                        'optionals': [],
                    },
                    'security': {
                        'defaults': [
                            {
                                'skill': 'pm-dev-python:python-security',
                                'description': 'Python security — injection sinks (subprocess, eval, deserialization, SQL) and path-traversal prevention',
                            },
                        ],
                        'optionals': [],
                    },
                },
            }
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        """Check if Python domain applies based on .py files in paths."""
        paths = module_data.get('paths') or {}
        sources = paths.get('sources') or []
        tests = paths.get('tests') or []
        build_systems = module_data.get('build_systems') or []

        signals = []
        if 'python' in build_systems:
            signals.append('build_systems=python')
        all_paths = sources + tests
        py_paths = [p for p in all_paths if str(p).endswith('.py') or '/py/' in str(p) or str(p).endswith('/py')]
        if py_paths:
            signals.append(f'*.py in {",".join(py_paths[:3])}')

        if not signals:
            return {
                'applicable': False,
                'confidence': 'none',
                'signals': [],
                'additive_to': None,
                'skills_by_profile': {},
            }

        confidence = 'high' if 'python' in build_systems else 'medium'
        return self._build_applicable_result(
            confidence, signals, module_data=module_data, active_profiles=active_profiles
        )

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-dev-python:ext-triage-python'

    def provides_arch_gate(self) -> dict | None:
        """import-linter: Python arch-gate tool. Binding: pm-dev-python:arch-gate-python."""
        return {'tool': 'import-linter'}

    # =========================================================================
    # Axis-C: module-edge derivation (the python-import join)
    # =========================================================================

    def derivation_resolver_id(self) -> str:
        """Return the stable provenance identity stamped onto every python edge.

        See extension-api/standards/ext-point-derivation-resolver.md for the
        complete four-face contract this identity participates in.
        """
        return 'python'

    def derive_edges(
        self,
        derived_by_name: dict,
        enriched_by_name: dict,
    ) -> tuple[list[tuple[str, str]], list[str]]:
        """Derive module edges from materialized Python-import references.

        A pure join over the ``component_refs`` field module discovery
        materializes: each entry is a ``{target_bundle, dep_type, resolved}``
        triple already projected onto module granularity. The engine that
        detected those imports parses files from disk, so it runs at discovery
        time; this method performs no file I/O and runs no subprocess, as the
        Axis-C purity contract requires.

        Only ``import`` entries contribute (:data:`PYTHON_DEP_TYPE`); the four
        markdown reference kinds belong to the sibling markdown resolver and are
        skipped without a note, being outside this resolver's scope rather than
        suppressed by it.

        Three conditions suppress a candidate edge, and each is reported in
        aggregated form: an import whose target does not exist in the
        marketplace (``unresolved-target``), a target naming no known module
        (``unknown-endpoint``), and an import from a bundle to itself
        (``self-edge``). Self-edges are dropped here as well as by the core
        merge, so this resolver's own ``edge_count`` report stays honest.

        This resolver reads the pre-materialized field only. It imports nothing
        from the bundle that materializes it, so registering a second resolver
        creates no code coupling between the two bundles.

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
                if ref.get('dep_type') != PYTHON_DEP_TYPE:
                    continue

                target = ref.get('target_bundle')
                candidate = f'{module_name} -> {target} [{PYTHON_DEP_TYPE}]'

                if not ref.get('resolved'):
                    suppressed['unresolved-target'].append(candidate)
                elif target not in derived_by_name:
                    suppressed['unknown-endpoint'].append(candidate)
                elif target == module_name:
                    suppressed['self-edge'].append(candidate)
                else:
                    edges.add((module_name, target))

        return sorted(edges), self._aggregate_notes(suppressed)
