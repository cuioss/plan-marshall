#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Extension API for the pm-code-intelligence bundle.

Hosts Axis-C only in substance: the ``lsp`` derivation resolver, a pure join over
the language-server references the discovery-time harvest materializes into
``component_refs``.

The bundle also subclasses :class:`ExtensionBase` (Axis-A) because that is the
only way to be *discovered*: ``discover_derivation_resolvers()`` spans the Axis-A
and Axis-B discovery paths, and a class inheriting ``DerivationResolverBase``
alone would be reachable from neither. It registers no skill domain, which is the
honest answer for a bundle that contributes an edge set rather than skills.

Why this resolver is not on ``pm-dev-python``: a bundle registers at most one
resolver, so its edges would be stamped ``python`` and become indistinguishable
from that bundle's AST-import join. Keeping the ids distinct is the entire point
— where both derive the same pair they have corroborated rather than disagreed,
and the core merge unions them into one edge carrying both producer ids.
"""

from extension_base import DerivationResolverBase, ExtensionBase

LSP_DEP_TYPE = 'lsp'
"""The single reference kind this resolver owns.

Declared as a literal rather than imported from the engine that writes it: a
resolver imports nothing from the bundle materializing its field, so each
registration stands alone. The sibling kinds (``script`` / ``skill`` / ``import``
/ ``path`` / ``implements``) belong to the markdown, python, and documentation
resolvers, so a non-``lsp`` entry is outside this resolver's scope rather than an
edge it suppressed, and carries no note.
"""

HARVEST_STATUS_FIELD = 'lsp_harvest'
"""Module-dict field carrying the harvest's ``{ran, reason, notes}`` record.

The field is what makes a zero-edge answer non-vacuous. Without it, a server that
never started and a workspace with genuinely no references both reach the caller
as ``status: ok, edge_count: 0`` — the confident empty answer this substrate
exists to eliminate.
"""

SUPPRESSION_CATEGORIES = ('unresolved-target', 'unknown-endpoint', 'self-edge')
"""Suppression buckets reported in ``notes[]``, in emission order."""


class Extension(ExtensionBase, DerivationResolverBase):
    """Code-intelligence extension and ``lsp`` module-edge derivation resolver."""

    def get_skill_domains(self) -> list[dict]:
        """Return no skill domain.

        This bundle contributes an edge set, not skills. Declaring a domain with
        no skills would put an empty entry in front of every domain-selection
        surface (``skill-domains get-available``, the steward wizard) and assert a
        capability the bundle does not have. Resolver discovery is unaffected:
        ``discover_derivation_resolvers()`` applies no domain filter.
        """
        return []

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        """Report non-applicability — the bundle registers no domain to apply.

        Detection gates skill loading, not resolver registration, so this verdict
        has no bearing on whether the ``lsp`` resolver runs.
        """
        return {
            'applicable': False,
            'confidence': 'none',
            'signals': [],
            'additive_to': None,
            'skills_by_profile': {},
        }

    # This bundle deliberately implements NO ``config_defaults``. The harvest is
    # configured entirely by the shared machine-local ``language_servers`` binding
    # that ``plan-marshall:lsp-client`` already reads, and a second key naming the
    # same server for the same language would be exactly the parallel
    # configuration surface that store exists to prevent. Off-by-default falls out
    # of the same fact: the store is git-ignored, so a fresh clone has no binding.

    # =========================================================================
    # Axis-C: module-edge derivation (the language-server symbol join)
    # =========================================================================

    def derivation_resolver_id(self) -> str:
        """Return the stable provenance identity stamped onto every lsp edge."""
        return 'lsp'

    def derivation_file_patterns(self) -> list[str]:
        """Return the file patterns this resolver's harvest reads.

        The harvest drives one language end-to-end (``lsp_harvest``'s
        ``HARVEST_LANGUAGE``), so the declared set is Python's. It is descriptive
        only — whether the resolver runs at all is decided by the enabled
        ``language_servers`` binding and by this resolver's own
        ``derivation_resolvers`` entry, never by matching a file against these
        patterns.

        Descriptive metadata for the resolver-configuration menu, never a filter
        — see ``DerivationResolverBase.derivation_file_patterns``.
        """
        return ['**/*.py']

    def derive_edges(
        self,
        derived_by_name: dict,
        enriched_by_name: dict,
    ) -> tuple[list[tuple[str, str]], list[str]]:
        """Derive module edges from harvested language-server references.

        A pure join over the ``component_refs`` field discovery materializes: the
        language server ran at discovery time, its file-granular references were
        lifted to module granularity, and this method performs no file I/O and
        runs no subprocess, as the Axis-C purity contract requires.

        **That lift happens upstream, in the harvest, and it does not go through
        the Axis-D path-attribution seam** — so do not look for an attribution
        callable in this method; there is none, and this paragraph is a statement
        about ``lsp_harvest.lift_to_modules`` rather than about the code below.
        The harvest uses a caller-supplied path-to-module lookup — a
        longest-prefix table it builds from the discovered module set. That is
        necessary rather
        than incidental: the live seam claims only ``.claude`` and ``.plan``, so
        it attributes no ``marketplace/bundles/**`` path at all and routing
        through it would guarantee zero edges. The substitute does **not** carry
        the seam's ambiguous-ownership obligation (its equal-length tie-break is
        iteration order, which the seam's contract forbids; unreachable today
        because bundle directory names are unique), and vendored-tree exclusion
        is handled by the harvest rather than by the lookup.

        The harvest's own status record is read first and reported. A harvest that
        did not run yields a note naming the reason, so ``edge_count: 0`` from a
        server that never started stays distinguishable from ``edge_count: 0`` on
        a workspace with genuinely no references.

        Args:
            derived_by_name: Module name → derived data. A module carrying no
                harvest record contributes nothing.
            enriched_by_name: Module name → curated overlay. Unused: the
                precedence of a declared ``internal_dependencies`` over a derived
                edge set is core's decision, applied ahead of this call.

        Returns:
            An ``(edges, notes)`` tuple. ``notes`` carries the harvest status
            first, then one aggregated entry per non-empty suppression category.
        """
        edges: set[tuple[str, str]] = set()
        suppressed: dict[str, list[str]] = {category: [] for category in SUPPRESSION_CATEGORIES}
        harvest_notes: list[str] = []
        seen_notes: set[str] = set()
        saw_status = False

        for module_name, module_data in derived_by_name.items():
            saw_status |= self._collect_harvest_notes(module_data, harvest_notes, seen_notes)

            for ref in module_data.get('component_refs') or []:
                if ref.get('dep_type') != LSP_DEP_TYPE:
                    continue

                target = ref.get('target_bundle')
                candidate = f'{module_name} -> {target} [{LSP_DEP_TYPE}]'

                if not ref.get('resolved'):
                    suppressed['unresolved-target'].append(candidate)
                elif target not in derived_by_name:
                    suppressed['unknown-endpoint'].append(candidate)
                elif target == module_name:
                    suppressed['self-edge'].append(candidate)
                else:
                    edges.add((module_name, target))

        if derived_by_name and not saw_status:
            # No module carries a harvest record at all, which means no
            # discovery-time harvest ran over this project. Reporting that is the
            # difference between "the harvest found nothing" and "no harvest
            # happened here" — without it, every project whose modules are
            # discovered by an extension that does not materialize the field would
            # get a confident `status: ok, edge_count: 0`.
            harvest_notes.append(
                'harvest-did-not-run: no module carries a harvest record, so no '
                'discovery-time language-server harvest ran for this project'
            )

        return sorted(edges), harvest_notes + self._aggregate_notes(suppressed)

    @staticmethod
    def _collect_harvest_notes(module_data: dict, notes: list[str], seen: set[str]) -> bool:
        """Fold one module's harvest record into the deduplicated note list.

        Every module carries the same workspace-wide record, so the notes are
        deduplicated on content rather than emitted once per module.

        Returns:
            Whether this module carried a harvest record at all — the caller uses
            it to tell "the harvest ran and reported" from "nothing harvested
            here", which are different answers.
        """
        status = module_data.get(HARVEST_STATUS_FIELD)
        if not isinstance(status, dict):
            return False

        if not status.get('ran'):
            reason = status.get('reason') or 'unstated reason'
            note = f'harvest-did-not-run: {reason}'
            if note not in seen:
                seen.add(note)
                notes.append(note)
            return True

        for note in status.get('notes') or []:
            if note not in seen:
                seen.add(note)
                notes.append(note)
        return True
