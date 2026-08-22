#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Extension API for pm-documents bundle.

Owns three axes of the extension contract for the documentation domain:

- **Axis-A** (:class:`ExtensionBase`) — skill domains, triage, module discovery
  over the doc tree.
- **Axis-D** (:class:`PathAttributionBase`) — the documentation domain owns its
  corpus. It claims ``doc/**`` and the repo-root prose docs (``README.md`` /
  ``CONTRIBUTING.md``) for the ``documentation`` module, so ``which-module``
  attributes them to the documentation domain with provenance rather than to the
  generic project-root module. See
  ``extension-api/standards/ext-point-path-attribution.md``.
- **Axis-C** (:class:`DerivationResolverBase`) — the ``documentation`` derivation
  resolver, a pure join over the ``component_refs`` field ``discover_modules``
  materializes from cross-document references (``xref:`` / ``link:`` / markdown
  links). It reports every unresolvable reference — the dangling-anchor /
  deleted-heading class that is documentation domain knowledge only this bundle
  holds.

The Axis-C and Axis-D faces are opted into by multiple inheritance, the only shape
reachable from the otherwise-disjoint hierarchies.
"""

import sys
from pathlib import Path

# Allow direct invocation and testing — the executor sets PYTHONPATH for
# production, but a direct import of this file needs its own scripts dir on the
# path so the sibling ``doc_references`` module resolves by bare name.
SCRIPTS_DIR = Path(__file__).parent / 'scripts'
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from extension_base import (  # noqa: E402
    DerivationResolverBase,
    ExtensionBase,
    PathAttributionBase,
)

#: Reference kinds this resolver reports on. A doc cross-reference is a
#: relative-path reference, so the single dep_type it joins over is ``path``.
_DOC_DEP_TYPES = frozenset({'path'})

#: Suppression buckets reported in ``notes[]``, in emission order. The shared
#: ``DerivationResolverBase._aggregate_notes`` renders whatever categories it is
#: handed, in the order they are seeded here.
_SUPPRESSION_CATEGORIES = ('unresolved-target', 'unknown-endpoint', 'self-edge')

#: The build-system marker the documentation module carries; used to scope the
#: Axis-C resolver to documentation modules so it does not also process the
#: marketplace-bundle ``path`` refs the ``markdown`` resolver owns.
_DOCUMENTATION_BUILD_SYSTEM = 'documentation'


class Extension(ExtensionBase, PathAttributionBase, DerivationResolverBase):
    """Documentation extension for pm-documents bundle.

    Opts into Axis-D (path attribution) and Axis-C (edge derivation) by multiple
    inheritance — the only shape that lets an Axis-A domain extension also declare
    path claims and derive module edges. See
    ``extension-api/standards/ext-point-path-attribution.md`` and
    ``ext-point-derivation-resolver.md``.
    """

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
                                'description': 'Narrative styles for technical documentation — tone, voice, and arc for the engineering-narrative style',
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
                                'skill': 'plan-marshall:manage-adr',
                                'description': 'Manage Architectural Decision Records with CRUD operations and AsciiDoc formatting',
                            },
                            {
                                'skill': 'pm-documents:manage-interface',
                                'description': 'Manage Interface specifications with CRUD operations and AsciiDoc formatting',
                            },
                        ],
                    },
                    # Documentation-module skill alias: phase-4-plan's closed task-profile
                    # enum looks up skills_by_profile.implementation for every deliverable,
                    # so documentation modules must declare the profile or doc tasks ship
                    # with an empty skill set. The core doc skills fold in via
                    # _build_applicable_result's core-merge.
                    'implementation': {
                        'defaults': [],
                        'optionals': [],
                    },
                },
            }
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        """Check if documentation domain applies based on doc directories."""
        paths = module_data.get('paths') or {}
        module_path = paths.get('module') or ''
        sources = paths.get('sources') or []

        signals = []
        all_paths = [module_path] + sources
        for p in all_paths:
            p_str = str(p)
            if 'doc' in p_str.lower():
                signals.append(f'doc directory in {p}')

        # Check build_systems for documentation marker
        build_systems = module_data.get('build_systems') or []
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
            {
                'key': 'verify-ascii-diagrams',
                'name': 'Verify ASCII Diagrams',
                'description': 'Verify and fix alignment of ASCII box diagrams across .md and .adoc files',
                'skill': 'pm-documents:recipe-verify-ascii-diagrams',
                'default_change_type': 'tech_debt',
                'scope': 'codebase_wide',
            },
        ]

    def discover_modules(self, project_root: str) -> list:
        """Discover documentation modules in the project.

        Detects projects with documentation by checking for:
        - doc/ or docs/ directory containing .adoc or .md files at ANY depth
        - README.adoc at project root

        The doc-file check is RECURSIVE (``rglob``) rather than top-level only: a
        project that keeps its documentation in sub-directories — ``doc/concepts/``,
        ``doc/adr/``, ``doc/developer/`` — is exactly as much a documentation
        project as one with files directly under ``doc/``, and a non-recursive glob
        left the documentation domain's discovery seat inert for it. Detection stops
        at the first matching file (``next(...)``) so a large tree is not fully
        walked just to answer "is there any documentation here".

        Returns a single 'documentation' module when documentation is found. The
        module carries its outbound ``component_refs`` — the cross-document
        references its Axis-C resolver joins over — materialized here at discovery
        time (the resolver may not read the filesystem).
        """
        root = Path(project_root)
        found_doc_dir = ''

        # Check for a doc/ or docs/ directory containing documentation at any depth.
        for doc_dir_name in ['doc', 'docs']:
            doc_dir = root / doc_dir_name
            if not doc_dir.is_dir():
                continue
            has_doc_file = any(
                next(doc_dir.rglob(f'*{suffix}'), None) is not None for suffix in ('.adoc', '.md')
            )
            if has_doc_file:
                found_doc_dir = doc_dir_name
                break

        # Fall back to a root-level README.adoc (a doc-only project shape). The
        # module still roots at ``doc`` — never ``.`` — so the reference engine and
        # the crawl walk the (possibly-absent, hence empty) ``doc`` tree rather than
        # rglob-ing the whole project root.
        if not found_doc_dir and (root / 'README.adoc').exists():
            found_doc_dir = 'doc'

        if not found_doc_dir:
            return []

        from doc_references import build_doc_component_refs

        return [
            {
                'name': 'documentation',
                'paths': {'module': found_doc_dir},
                'build_systems': [_DOCUMENTATION_BUILD_SYSTEM],
                'metadata': {
                    'description': 'Project documentation',
                },
                'component_refs': build_doc_component_refs(project_root, found_doc_dir),
            }
        ]

    # =========================================================================
    # Axis-D: path attribution (the documentation domain owns its corpus)
    # =========================================================================

    def path_attributor_id(self) -> str:
        """Return this attributor's stable provenance identity (Axis-D)."""
        return 'documentation'

    def claim_paths(self) -> tuple[list[tuple[str, str]], list[str]]:
        """Declare the repo-relative trees the ``documentation`` module owns.

        The documentation domain owns its corpus. The doc tree itself is claimed
        explicitly so the ownership is provenance-carrying at the seam — even
        though ``which-module`` also resolves a ``doc/**`` path to ``documentation``
        via its more-specific inventory prefix, the seam claim is what makes the
        ownership a stated fact rather than an accident of module-path length, and
        it is the key the de-duplication precedence reads (see
        ``manage-architecture`` § claimed-path collapse).

        The repo-root prose docs — ``README.md`` and ``CONTRIBUTING.md`` — are
        claimed too, because they are documentation that lives outside ``doc/`` and
        would otherwise resolve to the generic project-root module. The claim is
        **per file, not by a root glob**: ``CLAUDE.md`` and ``AGENTS.md`` are
        deliberately NOT claimed. They are agent-instruction files, not prose
        documentation, and sweeping the whole repo root into the documentation
        module would mis-own them — whether they belong to the root module or the
        core bundle is a separate question this claim does not decide.

        A claim naming ``documentation`` is dropped by the core merge in a project
        where no documentation module exists (the module-existence guard), so this
        attributor is inert exactly where it should be and active exactly where the
        doc tree is discovered.
        """
        return (
            [
                ('doc', 'documentation'),
                ('README.md', 'documentation'),
                ('CONTRIBUTING.md', 'documentation'),
            ],
            [],
        )

    # =========================================================================
    # Axis-C: module-edge derivation (the cross-document reference join)
    # =========================================================================

    def derivation_resolver_id(self) -> str:
        """Return the stable provenance identity stamped onto every doc edge.

        See extension-api/standards/ext-point-derivation-resolver.md for the
        complete four-face contract this identity participates in.
        """
        return 'documentation'

    def derivation_file_patterns(self) -> list[str]:
        """Return the file patterns this resolver's cross-reference join reads.

        The markdown patterns overlap the ``markdown`` resolver's, and that is
        the intended shape: this resolver is scoped to documentation modules, so
        the two see different corpora through the same extension. Where both do
        see one reference the merge unions them into a single edge carrying both
        producer ids.

        Descriptive metadata for the resolver-configuration menu, never a filter
        — see ``DerivationResolverBase.derivation_file_patterns``.
        """
        return ['**/*.adoc', '**/*.md']

    def derive_edges(
        self,
        derived_by_name: dict,
        enriched_by_name: dict,
    ) -> tuple[list[tuple[str, str]], list[str]]:
        """Derive module edges from materialized cross-document references.

        A pure join over the ``component_refs`` field ``discover_modules``
        materializes for the documentation module: each entry is a
        ``{target_bundle, dep_type, resolved}`` triple already projected from a
        doc reference onto module granularity. The engine that resolved those
        references reads files from disk, so it runs at discovery time; this method
        performs no file I/O and runs no subprocess, as the Axis-C purity contract
        requires.

        The scan is scoped to documentation modules (those carrying the
        ``documentation`` build system) so this resolver does not also process the
        marketplace-bundle ``path`` refs the ``markdown`` resolver on
        ``pm-plugin-development`` owns. Where both resolvers legitimately see the
        SAME doc reference — the doc module's own refs are visible to any
        all-modules resolver — the core merge unions the two into one edge carrying
        both producer ids, which is corroboration, not a conflict.

        Three conditions suppress a candidate edge, and each is reported in
        aggregated form so a dangling reference is never silently lost: a reference
        whose target does not exist (``unresolved-target`` — the deleted-heading /
        dangling-anchor class), a target naming no known module
        (``unknown-endpoint``), and a reference from the doc module to itself
        (``self-edge`` — the common case, since most cross-document references are
        between files of the one documentation module). A resolvable reference to
        another module becomes an edge.

        The enriched overlay is unused: the precedence of a curated
        ``internal_dependencies`` declaration over a derived edge set is core's
        decision, applied ahead of the resolver call.

        Returns:
            An ``(edges, notes)`` tuple. ``edges`` is the sorted, deduplicated list
            of ``(dependent, dependency)`` module-name pairs. ``notes`` carries one
            aggregated entry per non-empty suppression category.
        """
        edges: set[tuple[str, str]] = set()
        suppressed: dict[str, list[str]] = {category: [] for category in _SUPPRESSION_CATEGORIES}

        for module_name, module_data in derived_by_name.items():
            build_systems = module_data.get('build_systems') or []
            if _DOCUMENTATION_BUILD_SYSTEM not in build_systems:
                continue
            for ref in module_data.get('component_refs') or []:
                dep_type = ref.get('dep_type')
                if dep_type not in _DOC_DEP_TYPES:
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
