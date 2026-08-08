#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Build extension for plan-marshall:build-maven — file-to-build map and edge derivation.

Owns TWO axes of the extension contract for the Maven build system:

- **Axis-B** (:class:`BuildExtensionBase`) — the ``(pattern, role)`` build_map
  routes plus the ``classify_paths`` / ``classify_path_specificity`` lookups that
  the manage-execution-manifest aggregator and the build_map seed consume.
- **Axis-C** (:class:`DerivationResolverBase`) — the Maven coordinate join that
  derives which modules depend on which. It is the re-homed form of the join that
  previously lived inline in ``manage-architecture``: joining
  ``metadata.group_id`` / ``artifact_id`` against every module's
  ``groupId:artifactId:scope`` dependency strings is Maven domain knowledge, and
  the bundle that already understands that data is the one that owns it.

Skill-loading (Axis-A) is NOT here — it lives on the Java domain extension that
subclasses ``ExtensionBase``. The two Axis-C methods are opted into by multiple
inheritance, the only shape reachable from both otherwise-disjoint hierarchies.

The Maven build extension claims Java production / test sources under the
``src/main`` and ``src/test`` convention, the Maven-standard resource trees
(``src/main/resources`` → production, ``src/test/resources`` → test, whatever
the resource's extension), shell scripts by bare basename (``*.sh`` → config),
plus the ``pom.xml`` reactor descriptor. Gradle descriptors are owned by the
sibling build-gradle extension.
"""

import fnmatch
from posixpath import basename

from extension_base import (
    BUILD_CLASS_BUILD_CONFIG_FULL,
    BuildExtensionBase,
    DerivationResolverBase,
)


class BuildExtension(BuildExtensionBase, DerivationResolverBase):
    """Maven build-system file-to-build extension and module-edge derivation resolver."""

    def get_skill_domains(self) -> list[dict]:
        """Return the domain key this build system's routes are filed under.

        The Maven build system serves the ``java`` domain — the same key the
        ``pm-dev-java`` language extension declares. build-maven and build-gradle
        both serve ``java``; the route deriver MERGES their routes under that key.
        Applicability scoping gates on the language extension's
        ``applies_to_module``. Only the ``key`` is meaningful here.
        """
        return [{'domain': {'key': 'java', 'name': 'Java', 'description': 'Maven build system'}, 'profiles': {}}]

    # Glob patterns ordered by specificity (highest first). Each tuple is
    # (glob, role, specificity) where specificity is the count of non-wildcard
    # path-segment tokens in the glob. Matching is first-match-wins, so row
    # order carries the routing: the Maven-standard resource trees
    # (specificity 3) sit ABOVE the ``src/main`` / ``src/test`` java rows
    # (specificity 2), claiming every file under ``src/main/resources`` as
    # production and under ``src/test/resources`` as test regardless of
    # extension. The bare-basename ``*.sh`` config route is the FINAL row
    # (specificity 0) — below the ``pom.xml`` descriptor rows — so a shell
    # script inside a resource tree (``src/main/resources/bin/run.sh``) still
    # resolves to that tree's role, and only a script outside any claimed tree
    # (``build.sh``, ``scripts/release.sh``) falls through to config.
    _CLASSIFY_PATTERNS: tuple[tuple[str, str, int], ...] = (
        ('**/src/main/resources/**', 'production', 3),
        ('src/main/resources/**', 'production', 3),
        ('**/src/test/resources/**', 'test', 3),
        ('src/test/resources/**', 'test', 3),
        ('**/src/main/**/*.java', 'production', 2),
        ('src/main/**/*.java', 'production', 2),
        ('**/src/test/**/*.java', 'test', 2),
        ('src/test/**/*.java', 'test', 2),
        ('**/pom.xml', 'config', 1),
        ('pom.xml', 'config', 1),
        ('*.sh', 'config', 0),
    )

    def _match_classify(self, path: str) -> tuple[str, int] | None:
        for glob, role, score in self._CLASSIFY_PATTERNS:
            if fnmatch.fnmatchcase(path, glob):
                return role, score
        return None

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        """Classify paths for the Maven build system.

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
        """Return the Maven build system's explicit ``(pattern, role)`` build_map routes.

        Each route is a single-``*`` fnmatch glob paired with a resolved role.
        Patterns are matched with the shared two-regime matcher
        (``extension_base.route_matches``) by every downstream consumer: a
        bare-basename route (no ``/``) matches the path's basename anywhere in
        the tree, while a path-bearing route matches the full repo-relative
        path with a single ``*`` spanning ``/``,
        so the ``src/main`` / ``src/test`` Maven convention splits production from
        test by location: ``*/src/main/*.java`` covers every production source
        under any module's ``src/main`` tree (the leading ``*/`` admits the
        nested-module layout) and ``src/main/*.java`` covers the repo-root
        single-module layout; the parallel ``src/test`` routes claim test
        sources. Dedicated IT routes (``*IT.java`` / ``*ITCase.java`` /
        ``IT*.java`` under ``src/test``) sit above the generic test routes by
        glob-length specificity so ``classify_build_class`` stamps them with
        the Failsafe-bound ``verify`` build_class at seed time. The
        Maven-standard resource trees are routed the same way and
        listed first: ``*/src/main/resources/*`` and ``src/main/resources/*``
        claim resources under ``production``, the parallel ``src/test/resources``
        routes claim them under ``test`` — extension-independent, since a
        resource's role follows its tree, not its suffix. The bare ``pom.xml``
        reactor descriptor is a basename-only route under ``config``: it matches
        the descriptor at any tree depth (every module's ``pom.xml``), not only a
        repo-root instance. The bare-basename ``*.sh`` route claims shell scripts
        under ``config`` and is listed LAST so a script inside a resource tree
        keeps that tree's role. See the base classify_globs() contract for the
        route-collection wiring.
        """
        return [
            ('*/src/main/resources/*', 'production'),
            ('src/main/resources/*', 'production'),
            ('*/src/test/resources/*', 'test'),
            ('src/test/resources/*', 'test'),
            ('*/src/main/*.java', 'production'),
            ('src/main/*.java', 'production'),
            ('*/src/test/*IT.java', 'test'),
            ('src/test/*IT.java', 'test'),
            ('*/src/test/*ITCase.java', 'test'),
            ('src/test/*ITCase.java', 'test'),
            ('*/src/test/IT*.java', 'test'),
            ('src/test/IT*.java', 'test'),
            ('*/src/test/*.java', 'test'),
            ('src/test/*.java', 'test'),
            ('pom.xml', 'config'),
            ('*.sh', 'config'),
        ]

    # Failsafe's default inclusion patterns — the Maven integration-test naming
    # signature. A test file whose basename matches one of these is executed by
    # the Failsafe plugin (bound to the ``verify`` lifecycle phase), NOT by
    # Surefire's plain ``test`` goal, whose default includes EXCLUDE them.
    _IT_BASENAME_PATTERNS: tuple[str, ...] = ('*IT.java', 'IT*.java', '*ITCase.java')

    def classify_build_class(self, path: str, role: str) -> str:
        """Route Maven IT-signature test paths to the Failsafe-bound ``verify`` gate.

        The base role→build_class default maps ``test → module-tests`` — the
        module's plain Surefire ``test`` goal. Surefire's default includes
        exclude the Failsafe IT naming patterns (``*IT.java`` / ``IT*.java`` /
        ``*ITCase.java``), so that gate executes zero of a changed IT file's
        tests and reports success. IT-signature test paths therefore route to
        the existing ``verify`` build_class — the full-module reactor gate that
        runs the Failsafe plugin — keeping the build_class enum a closed
        4-value contract with no new member.

        Accepts both real paths and route-pattern strings: the build_map seed
        stamps each ``(pattern, role)`` route via this method at seed time, and
        an IT route's basename (e.g. ``*IT.java``) matches its own signature
        pattern under fnmatch, so the seeded IT routes carry
        ``build_class=verify`` while the generic ``*/src/test/*.java`` route
        keeps the ``module-tests`` default.

        Args:
            path: A repo-relative path or a route-pattern string claimed under
                ``role``.
            role: The role this extension claimed the path under.

        Returns:
            ``verify`` for ``test``-role paths whose basename matches the IT
            naming signature; the inherited base default otherwise.
        """
        if role == 'test' and any(
            fnmatch.fnmatchcase(basename(path), pattern)
            for pattern in self._IT_BASENAME_PATTERNS
        ):
            return BUILD_CLASS_BUILD_CONFIG_FULL
        return super().classify_build_class(path, role)

    # =========================================================================
    # Axis-C: module-edge derivation (the Maven coordinate join)
    # =========================================================================

    def derivation_resolver_id(self) -> str:
        """Return the stable provenance identity stamped onto every Maven edge.

        See extension-api/standards/ext-point-derivation-resolver.md for the
        complete four-face contract this identity participates in.
        """
        return 'maven'

    @staticmethod
    def _coordinate_owners(derived_by_name: dict) -> tuple[dict[str, str], list[str]]:
        """Map each UNAMBIGUOUS ``groupId:artifactId`` coordinate to its module.

        A coordinate claimed by exactly one module resolves to that module. A
        coordinate claimed by two or more distinct modules is **ambiguous** and is
        left out of the map entirely, so the join emits no edge for it, and the
        collision is reported in the returned notes.

        This is the ambiguous-identity-key obligation: the pre-move join built
        this map with a bare last-write-wins assignment, which silently dropped
        one module and every edge pointing at it, and which module survived
        depended on map iteration order — a non-deterministic answer presented as
        a confident one. Abstaining and reporting is strictly better than
        guessing, because a genuinely ambiguous coordinate cannot be attributed to
        a single module from the coordinate alone.

        Returns:
            An ``(artifact_to_module, notes)`` tuple. ``artifact_to_module`` maps
            each unambiguous coordinate to its owning module name. ``notes`` names
            one suppressed coordinate per collision, sorted for determinism.
        """
        claimants: dict[str, set[str]] = {}
        for mod_name, mod_data in derived_by_name.items():
            metadata = mod_data.get('metadata', {})
            group_id = metadata.get('group_id')
            artifact_id = metadata.get('artifact_id')
            if group_id and artifact_id:
                claimants.setdefault(f'{group_id}:{artifact_id}', set()).add(mod_name)

        artifact_to_module: dict[str, str] = {}
        notes: list[str] = []
        for coordinate in sorted(claimants):
            owners = claimants[coordinate]
            if len(owners) == 1:
                artifact_to_module[coordinate] = next(iter(owners))
                continue
            notes.append(
                f'ambiguous coordinate {coordinate}: claimed by '
                f'{", ".join(sorted(owners))} — no edge emitted'
            )
        return artifact_to_module, notes

    def derive_edges(
        self,
        derived_by_name: dict,
        enriched_by_name: dict,
    ) -> tuple[list[tuple[str, str]], list[str]]:
        """Derive module edges by joining Maven coordinates against dependency strings.

        The Maven reactor states its internal structure in coordinates: each module
        publishes a ``groupId:artifactId`` and names its dependencies as
        ``groupId:artifactId:scope`` strings. An edge exists wherever one module's
        dependency coordinate matches another module's published coordinate, which
        is what this join computes — matching on the first TWO colon-separated
        parts so the scope segment (and any further segment) is ignored.

        Behaviour is preserved from the pre-move inline join on every unambiguous
        input, with exactly ONE deliberate divergence: a coordinate claimed by two
        distinct modules yields no edge and a reported collision rather than a
        silent last-write-wins pick. See :meth:`_coordinate_owners`.

        Self-edges are excluded — a module's dependency on its own coordinate is
        not a reactor edge. (The core merge drops self-edges too; excluding them
        here keeps this resolver's own ``edge_count`` report honest.)

        The enriched overlay is unused: the precedence of a curated or discovered
        ``internal_dependencies`` declaration OVER a derived edge set is core's
        decision, applied ahead of the resolver call, so a resolver that
        second-guessed it would be overriding a ruling it does not own.

        Args:
            derived_by_name: Module name → derived data. Each module's
                ``dependencies`` list is already materialized by the caller (the
                cheap crawl leaves it empty, so the caller resolves it before
                dispatch) — this resolver runs no subprocess and touches no file.
            enriched_by_name: Module name → LLM-curated overlay. Unused here.

        Returns:
            An ``(edges, notes)`` tuple. ``edges`` is the sorted list of
            ``(dependent, dependency)`` module-name pairs. ``notes`` names every
            coordinate collision that suppressed an edge.
        """
        artifact_to_module, notes = self._coordinate_owners(derived_by_name)

        edges: set[tuple[str, str]] = set()
        for mod_name, mod_data in derived_by_name.items():
            for dependency in mod_data.get('dependencies') or []:
                parts = dependency.split(':')
                if len(parts) < 2:
                    continue
                dep_module = artifact_to_module.get(f'{parts[0]}:{parts[1]}')
                if dep_module is not None and dep_module != mod_name:
                    edges.add((mod_name, dep_module))

        return sorted(edges), notes
