#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Build extension for plan-marshall:build-pyproject — file-to-build map and edge derivation.

Owns TWO axes of the extension contract for the Python build system:

- **Axis-B** (:class:`BuildExtensionBase`) — the ``(pattern, role)`` build_map
  routes plus the ``classify_paths`` / ``classify_path_specificity`` lookups that
  the manage-execution-manifest aggregator and the build_map seed consume.
- **Axis-C** (:class:`DerivationResolverBase`) — the ``pyproject`` distribution-name
  join that derives which modules depend on which. A Python project publishes no
  ``groupId:artifactId`` coordinate, so the Maven join can never match it; what a
  Python distribution DOES publish is its **distribution name**, and that is what
  this resolver joins on. The name reaches ``metadata.name`` from whichever
  descriptor form the project uses — PEP 621 ``[project] name``, Poetry's
  ``[tool.poetry] name``, or ``setup.cfg``'s ``[metadata] name`` — and this
  resolver reads the field, never the descriptor, so it is indifferent to which
  supplied it.

Skill-loading (Axis-A) is NOT here — it lives on the Python domain extension that
subclasses ``ExtensionBase``. The three Axis-C methods are opted into by multiple
inheritance, the only shape reachable from both otherwise-disjoint hierarchies.

**This resolver is distinct from ``pm-dev-python``'s ``python`` resolver, and both
are wanted.** That one joins AST-parsed import statements (Python-language
knowledge, owned by the language bundle); this one joins declared distribution
dependencies (build-system knowledge, owned by the build skill). They answer
different questions — "what does this code import" versus "what does this project
declare" — and a consumer project that declares its dependencies but is not
crawled for imports gets its graph from this one alone. Each registration site
stamps a single resolver id, so keeping the two joins at separate sites is also
what keeps per-edge provenance able to say WHICH of the two derived a given edge.

The Python build extension claims ``pyproject.toml`` as config but NOT
``uv.lock`` or ``marshal.json`` — neither lockfile nor marshal config triggers a
Python build, so neither is a build-map config route.
"""

import fnmatch
from pathlib import Path

import marketplace_paths
from _name_edge_join import derive_name_edges, normalize_pep503
from extension_base import BuildExtensionBase, DerivationResolverBase

PYTHON_BUILD_SYSTEM = 'python'
"""The ``build_systems`` entry the Python discoverer stamps on every module it finds.

The Axis-C join is scoped to modules carrying this entry. A bare distribution
name is a key shape every ecosystem uses, so an unscoped join would attribute
another ecosystem's edges to this resolver and could fabricate an edge between a
Python distribution and a same-named package from a different ecosystem.
"""


def _project_local_skill_globs() -> list[tuple[str, str]]:
    """Build ``(glob, 'production')`` routes for the target's project-local-skill roots.

    Routes through the platform-runtime layout op (memoised per process) so the
    production-source classification covers the correct project-local-skill
    layout per target (Claude → ``.claude/skills``; OpenCode → its repo-relative
    roots). ``~``-anchored / absolute user-global roots are dropped: ``classify_globs``
    routes are repo-relative fnmatch globs over git-tracked files, and a tracked
    ``.py`` never lives under a user-global root.

    Resolved via the ``marketplace_paths`` module attribute (not a bound name)
    so the layout-op source can be substituted in tests.
    """
    globs: list[tuple[str, str]] = []
    for root in marketplace_paths.get_project_skill_roots():
        if root.startswith('~') or Path(root).is_absolute():
            continue
        globs.append((f'{root}/*.py', 'production'))
    return globs


# Non-python fixture content under the pyprojectx test roots. pytest reads these
# files as fixture data, so a change to one can break a module test, yet no build
# extension claimed them and no owner-less aggregator rule recognised them - they
# resolved to the ``unknown`` bucket, which blocks any deliverable listing one.
#
# The set is an explicit per-class enumeration rather than a catch-all under the
# roots, for two reasons. First, a fixture class nobody has routed keeps
# surfacing as ``unknown`` instead of being silently absorbed by a catch-all.
# Second, documentation suffixes (``.md`` / ``.adoc`` / ``.asciidoc``) are
# deliberately absent: documentation has no build-system owner and the aggregator
# recognises it generically BEFORE any extension is consulted, so a documentation
# claim here would be unreachable.
_TEST_FIXTURE_SUFFIXES: tuple[str, ...] = (
    '.info',
    '.java',
    '.json',
    '.lcov',
    '.log',
    '.toon',
    '.xml',
)

# The pyprojectx test roots. ``test/`` is this repository's root; ``tests/`` is
# the sibling convention. This tuple is the SINGLE source both Axis-B tables
# derive their test routes from — the ``.py`` rows of ``_CLASSIFY_PATTERNS``, the
# ``.py`` routes of ``classify_globs()``, and (through ``_test_fixture_routes``)
# the non-python fixture routes in both — so neither table can claim a root the
# other does not.
#
# ``_test_scope_divergence._TEST_ROOTS`` in script-shared declares the same roots
# for the orthogonal module-ownership derivation. The two are deliberately NOT a
# shared import (that module's purity contract forbids importing a build
# extension, and the dependency would run the wrong way); a cross-check test pins
# them equal instead.
_TEST_ROOTS: tuple[str, ...] = ('test', 'tests')


def _test_fixture_routes() -> tuple[str, ...]:
    """Return the fnmatch globs covering non-python fixture content under the test roots.

    Single source of truth for both Axis-B tables: ``_CLASSIFY_PATTERNS`` pairs
    each glob with the ``test`` role and a specificity of 1 (one non-wildcard
    path-segment token - the root), while ``classify_globs`` pairs the same glob
    with the ``test`` role as a build_map route. Deriving both from one list is
    what keeps the two tables from drifting apart.

    A single ``*`` spans ``/`` under fnmatch, so one glob per (root, suffix) pair
    covers both direct children and nested fixture trees.
    """
    return tuple(
        f'{root}/*{suffix}' for suffix in _TEST_FIXTURE_SUFFIXES for root in _TEST_ROOTS
    )


class BuildExtension(BuildExtensionBase, DerivationResolverBase):
    """Python build-system file-to-build extension and module-edge derivation resolver."""

    def get_skill_domains(self) -> list[dict]:
        """Return the domain key this build system's routes are filed under.

        The build_map aggregator keys each build extension's routes by its served
        domain key and resolves the owning extension's ``classify_build_class`` via
        the same key. The Python build system serves the ``python`` domain — the
        same key the ``pm-dev-python`` language extension declares, so applicability
        scoping (``applies_to_module`` on the language extension) gates this build
        system's routes. Only the ``key`` is meaningful here; build extensions own
        no skill profiles (that is Axis-A on the language extension).
        """
        return [{'domain': {'key': 'python', 'name': 'Python', 'description': 'Python build system'}, 'profiles': {}}]

    # Glob patterns ordered by specificity (highest first). Each tuple is
    # (glob, role, specificity) where specificity is the count of non-wildcard
    # path-segment tokens in the glob. The aggregator resolves multi-extension
    # overlap by comparing specificity values across claiming extensions.
    _CLASSIFY_PATTERNS: tuple[tuple[str, str, int], ...] = (
        # Production python under any NESTED scripts/ directory. Both
        # `*/scripts/sub/foo.py` (deep) and `*/scripts/foo.py` (direct child)
        # variants must match — fnmatch's `**/scripts/**/*.py` requires a
        # subdirectory after `scripts/`, so the direct-child pattern is needed
        # alongside. Both rows need a path component BEFORE `scripts/`, so a
        # repo-root `scripts/foo.py` matches neither — deliberately: this table
        # claims no root that `classify_globs()` declares no route for, or
        # `validate_tree_completeness` could never see the claimed population.
        ('**/scripts/**/*.py', 'production', 2),
        ('**/scripts/*.py', 'production', 2),
        # Production python at the roots classify_globs() already declares but this
        # table did not: the bundle tree, the multi-target generator tree, and the
        # repo-root build script. A single `*` spans `/` under fnmatch, so one row
        # per root covers direct children and nested files alike.
        ('marketplace/bundles/*.py', 'production', 2),
        ('marketplace/targets/*.py', 'production', 2),
        ('build.py', 'production', 1),
        # Test python under any test root (deep child + direct child), derived
        # from _TEST_ROOTS so this table cannot declare a root classify_globs()
        # does not — the same anti-drift discipline the fixture globs use.
        *((f'{root}/**/*.py', 'test', 1) for root in _TEST_ROOTS),
        *((f'{root}/*.py', 'test', 1) for root in _TEST_ROOTS),
        # Non-python fixture content under the same test roots, one row per
        # routed class (see _TEST_FIXTURE_SUFFIXES).
        *((glob, 'test', 1) for glob in _test_fixture_routes()),
        # Config files. The Python build extension claims pyproject.toml only -
        # uv.lock and marshal.json do NOT trigger a Python build, so neither is a
        # build-map config route.
        ('pyproject.toml', 'config', 1),
        # Python-source templates - render sources for generated python, of which
        # the executor template is the live instance. Claimed `production`, since
        # what they render into is production python. Last row: a bare-basename
        # glob carries no non-wildcard path-segment token, so its specificity is 0
        # and every located row above outranks it.
        ('*.py.template', 'production', 0),
    )

    def _match_classify(self, path: str) -> tuple[str, int] | None:
        """Return (role, specificity) for the first matching glob, or None.

        Patterns are evaluated in declaration order; the first match wins
        within this extension. The aggregator handles cross-extension overlap
        via classify_path_specificity().
        """
        for glob, role, score in self._CLASSIFY_PATTERNS:
            if fnmatch.fnmatchcase(path, glob):
                return role, score
        return None

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        """Classify paths for the Python build system.

        See extension-api/standards/extension-contract.md § classify_paths()
        for the full contract.
        """
        claims: dict[str, list[str]] = {
            'production': [], 'test': [], 'documentation': [], 'config': []
        }
        for path in paths:
            match = self._match_classify(path)
            if match is not None:
                role, _ = match
                claims[role].append(path)
        return claims

    def classify_path_specificity(self, path: str, role: str) -> int:
        match = self._match_classify(path)
        if match is not None and match[0] == role:
            return match[1]
        return 0

    def classify_globs(self) -> list[tuple[str, str]]:
        """Return the Python build system's explicit ``(pattern, role)`` build_map routes.

        Each route is a single-``*`` fnmatch glob (or a bare basename) paired with
        a resolved role (``production`` / ``test`` / ``config``). Patterns are
        matched by the shared two-regime matcher ``extension_base.route_matches``:
        a path-bearing route matches the full repo-relative path with a single
        ``*`` spanning ``/`` -- so ``marketplace/bundles/*.py`` covers every
        production ``.py`` anywhere beneath ``marketplace/bundles/`` and
        ``test/*.py`` covers every test module beneath ``test/`` -- while a
        bare-basename route matches the file's basename anywhere in the tree.

        The production routes enumerate every root a plan-marshall ``.py`` can
        live under, plus the one basename-anchored python render source:

        - ``build.py`` at the repo root
        - the target's project-local-skill root(s), resolved via the
          platform-runtime layout op (Claude: ``.claude/skills/``; OpenCode: its
          repo-relative roots)
        - ``marketplace/bundles/``
        - ``marketplace/targets/``
        - ``*.py.template`` -- python-source templates anywhere in the tree, the
          render sources for generated python (the executor template is the live
          instance). Basename-anchored rather than root-anchored, because a
          render source is recognised by what it renders into, not by where it
          sits.

        The git-tracked completeness validator (``validate_tree_completeness``)
        reports any tracked ``.py`` these routes forgot.

        The test routes cover ``{root}/*.py`` for every root in
        :data:`_TEST_ROOTS` plus the non-python fixture content pytest reads
        under the same roots (see :data:`_TEST_FIXTURE_SUFFIXES`). Both this list
        and ``_CLASSIFY_PATTERNS`` derive their ``.py`` test routes from
        :data:`_TEST_ROOTS` and their fixture routes from
        :func:`_test_fixture_routes`, so the two tables cannot drift apart about
        WHICH roots are claimed — the asymmetry where ``_CLASSIFY_PATTERNS``
        carried ``tests/`` rows this list did not declare.

        The sole config route is ``pyproject.toml`` -- ``uv.lock`` and
        ``marshal.json`` are deliberately NOT claimed, since neither triggers a
        Python build. See the base classify_globs() contract for the
        route-collection wiring.
        """
        return [
            ('build.py', 'production'),
            *_project_local_skill_globs(),
            ('marketplace/bundles/*.py', 'production'),
            ('marketplace/targets/*.py', 'production'),
            ('*.py.template', 'production'),
            *((f'{root}/*.py', 'test') for root in _TEST_ROOTS),
            *((glob, 'test') for glob in _test_fixture_routes()),
            ('pyproject.toml', 'config'),
        ]

    # build_class: this extension claims the ``production`` / ``test`` /
    # ``config`` roles, for which the BuildExtensionBase defaults
    # (``production → compile``, ``test → module-tests``,
    # ``config → verify``) are correct. No classify_build_class
    # override is required — the inherited base default is the contract.

    # =========================================================================
    # Axis-C: module-edge derivation (the distribution-name join)
    # =========================================================================

    def derivation_resolver_id(self) -> str:
        """Return the stable provenance identity stamped onto every pyproject edge.

        Deliberately ``pyproject`` and not ``python``: ``pm-dev-python``'s
        import join already owns ``python``, ids must be unique across resolvers
        (the discovery collector drops the second claimant of a duplicate id),
        and the two derivations must stay distinguishable in an edge's
        ``producers[]`` — an edge that only the declared-dependency join found is
        a different fact from one the import join also found.

        See extension-api/standards/ext-point-derivation-resolver.md for the
        complete four-face contract this identity participates in.
        """
        return 'pyproject'

    def derivation_file_patterns(self) -> list[str]:
        """Return the build descriptor this resolver's distribution-name join reads.

        Declared dependencies, not imports: the ``python`` resolver declares
        ``**/*.py`` because it joins import statements, and the two answer
        different questions over the same language.

        Descriptive metadata for the resolver-configuration menu, never a filter
        — see ``DerivationResolverBase.derivation_file_patterns``.
        """
        return ['**/pyproject.toml']

    @staticmethod
    def _distribution_name(module_data: dict) -> str | None:
        """Return the module's published distribution name, or ``None``.

        The name lives in ``metadata.name``, which the Python discoverer fills
        from whichever descriptor form named the project — ``pyproject.toml``'s
        PEP 621 ``[project] name``, its Poetry ``[tool.poetry] name``, or
        ``setup.cfg``'s ``[metadata] name``. This method reads the field alone
        and never re-opens a descriptor, so all three forms join identically.

        There is deliberately NO fallback to the module's own ``name``: that
        field is directory-derived when **no** descriptor names the project, and
        a directory that names itself in none of the three publishes no
        distribution, so nothing can depend on it by name. Falling back would
        invent a join key the ecosystem never publishes and could match an
        unrelated third-party package that happens to share the directory's
        name — a fabricated edge, which is worse than the missing one it would
        paper over.
        """
        name = (module_data.get('metadata') or {}).get('name')
        return name if isinstance(name, str) else None

    def derive_edges(
        self,
        derived_by_name: dict,
        enriched_by_name: dict,
    ) -> tuple[list[tuple[str, str]], list[str]]:
        """Derive module edges by joining published distribution names.

        A Python project states its internal structure in distribution names:
        each module publishes a name — from PEP 621, Poetry or ``setup.cfg``,
        indifferently — and names its dependencies as ``name:scope`` strings. An edge exists wherever one module's dependency
        name matches another module's published name, compared in PEP 503
        normalised form so the ``-``/``_``/``.``/case variants of one distribution
        resolve to the same module.

        Both scopes contribute. A ``dev`` dependency is a real edge for impact
        analysis — changing the depended-upon module can break the dependent's
        tests — which is the same reason the Maven join ignores its own scope
        segment.

        The enriched overlay is unused: the precedence of a curated or discovered
        ``internal_dependencies`` declaration OVER a derived edge set is core's
        decision, applied ahead of the resolver call, so a resolver that
        second-guessed it would be overriding a ruling it does not own.

        Args:
            derived_by_name: Module name → derived data. Each module's
                ``dependencies`` list is already materialized by the caller —
                this resolver runs no subprocess and touches no file.
            enriched_by_name: Module name → LLM-curated overlay. Unused here.

        Returns:
            An ``(edges, notes)`` tuple. ``edges`` is the sorted list of
            ``(dependent, dependency)`` module-name pairs. ``notes`` names every
            distribution-name collision that suppressed an edge.
        """
        return derive_name_edges(
            derived_by_name, PYTHON_BUILD_SYSTEM, self._distribution_name, normalize_pep503
        )
