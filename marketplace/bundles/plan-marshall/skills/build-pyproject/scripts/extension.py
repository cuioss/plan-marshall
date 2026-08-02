#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Build extension for plan-marshall:build-pyproject — the Python file-to-build map.

Owns Axis-B of the extension contract for the Python build system: the
``(pattern, role)`` build_map routes plus the ``classify_paths`` /
``classify_path_specificity`` lookups that the manage-execution-manifest
aggregator and the build_map seed consume. Subclasses
:class:`BuildExtensionBase` (file-to-build only); skill-loading (Axis-A) lives
on the language domain extensions that subclass ``ExtensionBase``.

The Python build extension claims ``pyproject.toml`` as config but NOT
``uv.lock`` or ``marshal.json`` — neither lockfile nor marshal config triggers a
Python build, so neither is a build-map config route.
"""

import fnmatch
from pathlib import Path

import marketplace_paths
from extension_base import BuildExtensionBase


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
# the sibling convention the ``.py`` rows below already carry.
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


class BuildExtension(BuildExtensionBase):
    """Python build-system file-to-build extension."""

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
        # Test python under any test/ or tests/ directory (deep child + direct child).
        ('test/**/*.py', 'test', 1),
        ('tests/**/*.py', 'test', 1),
        ('test/*.py', 'test', 1),
        ('tests/*.py', 'test', 1),
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

        The test routes cover ``test/*.py`` plus the non-python fixture content
        pytest reads under the same roots (see :data:`_TEST_FIXTURE_SUFFIXES`);
        both this list and ``_CLASSIFY_PATTERNS`` derive those globs from
        :func:`_test_fixture_routes`, so the two tables cannot drift apart.

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
            ('test/*.py', 'test'),
            *((glob, 'test') for glob in _test_fixture_routes()),
            ('pyproject.toml', 'config'),
        ]

    # build_class: this extension claims the ``production`` / ``test`` /
    # ``config`` roles, for which the BuildExtensionBase defaults
    # (``production → compile``, ``test → module-tests``,
    # ``config → verify``) are correct. No classify_build_class
    # override is required — the inherited base default is the contract.
