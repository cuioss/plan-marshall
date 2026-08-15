#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Build extension for plan-marshall:build-npm — file-to-build map and edge derivation.

Owns TWO axes of the extension contract for the npm build system:

- **Axis-B** (:class:`BuildExtensionBase`) — the ``(pattern, role)`` build_map
  routes plus the ``classify_paths`` / ``classify_path_specificity`` lookups that
  the manage-execution-manifest aggregator and the build_map seed consume.
- **Axis-C** (:class:`DerivationResolverBase`) — the ``npm`` package-name join
  that derives which modules depend on which. An npm package publishes no
  ``groupId:artifactId`` coordinate, so the Maven join can never match it; what a
  package DOES publish is its ``package.json`` ``name``, and that is what this
  resolver joins on.

Skill-loading (Axis-A) is NOT here — it lives on the JavaScript domain extension
that subclasses ``ExtensionBase``. The two Axis-C methods are opted into by
multiple inheritance, the only shape reachable from both otherwise-disjoint
hierarchies.

**Workspace members are covered by construction.** ``discover_npm_modules``
already resolves ``workspaces`` globs (npm/yarn array and object forms, and
pnpm's ``pnpm-workspace.yaml``) into one module per member, so every member is a
key of the map this resolver is handed. A workspace dependency is declared like
any other — ``"react-router": "workspace:*"`` records as ``react-router:runtime``
— so the name join resolves it with no workspace-specific branch.

The npm build extension claims JS/TS production / test sources (recognising
``.spec.`` / ``.test.`` colocated test files) plus the npm toolchain config
files (``package.json`` / ``tsconfig.json``).
"""

from _name_edge_join import derive_name_edges, normalize_npm
from extension_base import BuildExtensionBase, DerivationResolverBase

NPM_BUILD_SYSTEM = 'npm'
"""The ``build_systems`` entry the npm discoverer stamps on every module it finds.

The Axis-C join is scoped to modules carrying this entry. A bare package name is
a key shape every ecosystem uses, so an unscoped join would attribute another
ecosystem's edges to this resolver and could fabricate an edge between an npm
package and a same-named distribution from a different ecosystem.
"""


class BuildExtension(BuildExtensionBase, DerivationResolverBase):
    """npm/JS build-system file-to-build extension and module-edge derivation resolver."""

    def get_skill_domains(self) -> list[dict]:
        """Return the domain key this build system's routes are filed under.

        The npm build system serves the ``javascript`` domain — the same key the
        ``pm-dev-frontend`` language extension declares, so applicability scoping
        (``applies_to_module`` on the language extension) gates this build system's
        routes. Only the ``key`` is meaningful here; build extensions own no skill
        profiles (that is Axis-A on the language extension).
        """
        return [
            {'domain': {'key': 'javascript', 'name': 'JavaScript', 'description': 'npm build system'}, 'profiles': {}}
        ]

    # Test patterns are recognized via filename suffix `.spec.*` / `.test.*`.
    # Source patterns claim *.js, *.mjs, *.ts, *.tsx, *.jsx that are NOT test files.
    _SOURCE_SUFFIXES: tuple[str, ...] = ('.js', '.mjs', '.ts', '.tsx', '.jsx')
    _TEST_TOKENS: tuple[str, ...] = ('.spec.', '.test.')
    _CONFIG_FILES: tuple[str, ...] = (
        'package.json',
        'tsconfig.json',
    )
    _CONFIG_PREFIXES: tuple[str, ...] = ('eslint.config.',)

    def _match_classify(self, path: str) -> tuple[str, int] | None:
        # Config files (highest specificity — exact filename match).
        filename = path.rsplit('/', 1)[-1]
        if filename in self._CONFIG_FILES:
            return 'config', 1
        for prefix in self._CONFIG_PREFIXES:
            if filename.startswith(prefix):
                return 'config', 1
        # Test patterns — *.spec.* / *.test.* with a JS/TS extension.
        if any(token in filename for token in self._TEST_TOKENS):
            for ext in self._SOURCE_SUFFIXES:
                if filename.endswith(ext):
                    return 'test', 1
        # Production source — JS/TS suffix and NOT a test file.
        for ext in self._SOURCE_SUFFIXES:
            if filename.endswith(ext):
                return 'production', 1
        return None

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        """Classify paths for the npm / JavaScript build system.

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
        """Return the npm build system's explicit ``(pattern, role)`` build_map routes.

        Each route is a single-``*`` fnmatch glob paired with a resolved role.
        Patterns are matched with the shared two-regime matcher
        (``extension_base.route_matches``) by every downstream consumer: a
        bare-basename route (no ``/``) matches the path's basename anywhere in
        the tree, while a path-bearing route matches the full repo-relative
        path with a single ``*`` spanning ``/``.
        For each JS/TS suffix the extension declares a broad production route
        (e.g. ``*.js``) plus the more-specific colocated-test routes
        (``*.spec.js`` / ``*.test.js``); the seed aggregator's longest-glob-wins
        specificity comparison routes a ``.spec.`` / ``.test.`` file to ``test``
        even though the broad production glob also matches it. Config files are
        bare-basename routes that match the file at any tree depth (basename
        anywhere), so a ``package.json`` / ``tsconfig.json`` living only in a
        subdirectory is still kept in the seed and matched at build-decision time,
        not only a repo-root instance. See the base classify_globs() contract for
        the route-collection wiring.
        """
        routes: list[tuple[str, str]] = []
        # Production source — broad per-suffix route (a single ``*`` spans ``/``,
        # so ``*.js`` covers JS anywhere in the tree).
        for ext in self._SOURCE_SUFFIXES:
            routes.append((f'*{ext}', 'production'))
        # Test source — the colocated ``.spec.`` / ``.test.`` infix forms per
        # suffix (e.g. ``*.spec.js``). These are more specific than the broad
        # production glob, so the aggregator routes the overlap to ``test``.
        for ext in self._SOURCE_SUFFIXES:
            for token in self._TEST_TOKENS:
                routes.append((f'*{token}{ext.lstrip(".")}', 'test'))
        # Config — exact filenames the JS toolchain reads.
        for name in self._CONFIG_FILES:
            routes.append((name, 'config'))
        return routes

    # build_class: this extension claims the ``production`` / ``test`` /
    # ``config`` roles, for which the BuildExtensionBase defaults
    # (``production → compile``, ``test → module-tests``,
    # ``config → verify``) are correct. No classify_build_class
    # override is required — the inherited base default is the contract.

    # =========================================================================
    # Axis-C: module-edge derivation (the package-name join)
    # =========================================================================

    def derivation_resolver_id(self) -> str:
        """Return the stable provenance identity stamped onto every npm edge.

        See extension-api/standards/ext-point-derivation-resolver.md for the
        complete four-face contract this identity participates in.
        """
        return 'npm'

    def derivation_file_patterns(self) -> list[str]:
        """Return the build descriptor this resolver's package-name join reads.

        Descriptive metadata for the resolver-configuration menu, never a filter
        — see ``DerivationResolverBase.derivation_file_patterns``.
        """
        return ['**/package.json']

    @staticmethod
    def _package_name(module_data: dict) -> str | None:
        """Return the module's published ``package.json`` name, or ``None``.

        Read from ``metadata.name`` rather than from the module's own ``name``:
        that field falls back to the directory (or to ``default`` for an unnamed
        root) when package.json declares no name. A package with no declared name
        is unpublishable, so nothing can depend on it — and joining on the
        fallback would invent a key npm never published, which could match an
        unrelated registry package that happens to share the directory's name.
        A fabricated edge is worse than the missing one it would paper over.
        """
        name = (module_data.get('metadata') or {}).get('name')
        return name if isinstance(name, str) else None

    def derive_edges(
        self,
        derived_by_name: dict,
        enriched_by_name: dict,
    ) -> tuple[list[tuple[str, str]], list[str]]:
        """Derive module edges by joining ``package.json`` names.

        An npm workspace states its internal structure in package names: each
        package publishes a ``name`` and names its dependencies by that same
        string. An edge exists wherever one module's dependency name matches
        another module's published name. Scoped names (``@scope/pkg``) join
        unchanged — the scope is part of the name, not a separate coordinate
        segment — and comparison is case-folded, which admits the legacy
        mixed-case names predating npm's lower-case rule without merging names
        npm considers distinct.

        Both ``dependencies`` and ``devDependencies`` contribute. A dev
        dependency is a real edge for impact analysis — changing the
        depended-upon package can break the dependent's build or tests — which
        is the same reason the Maven join ignores its own scope segment.

        The enriched overlay is unused: the precedence of a curated or discovered
        ``internal_dependencies`` declaration OVER a derived edge set is core's
        decision, applied ahead of the resolver call.

        Args:
            derived_by_name: Module name → derived data. Each module's
                ``dependencies`` list is already materialized by the caller —
                this resolver runs no subprocess and touches no file.
            enriched_by_name: Module name → LLM-curated overlay. Unused here.

        Returns:
            An ``(edges, notes)`` tuple. ``edges`` is the sorted list of
            ``(dependent, dependency)`` module-name pairs. ``notes`` names every
            package-name collision that suppressed an edge.
        """
        return derive_name_edges(derived_by_name, NPM_BUILD_SYSTEM, self._package_name, normalize_npm)
