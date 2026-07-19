# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pure, tool-agnostic scope-resolution and divergence classification.

Two pure functions back the phase-6-finalize "whole-tree module-tests
divergence gate" (PLAN-14): they decide which module set a scoped test run
would cover and whether a whole-tree run is warranted, and they classify the
scoped-vs-whole-tree outcome pair into a caught/not-caught verdict.

Both functions are pure — no I/O, no subprocess, no git. The footprint and the
build_map globs are supplied by the caller (the ``resolve-test-scope`` build
subcommand reads them from the live worktree; the tests inject them directly),
so this module is deterministic and unit-testable in isolation.

The scope-derivation rule mirrors, in code, the bundle-derivation prose in
``phase-6-finalize/standards/pre-push-quality-gate.md`` § "Derive unique bundle
set": each footprint entry is fnmatched against the build_map globs, then the
owning module is taken from path segment 2 for ``marketplace/bundles/{bundle}/…``
and segment 1 for ``test/{bundle}/…``. It is a faithful extraction of the
existing derivation, not a new policy.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass

# Footprint prefixes whose presence means a scoped run cannot observe a
# cross-module regression — the PLAN-08 class. A change touching any of these
# forces ``divergence_possible`` regardless of how many modules the scoped set
# resolves to.
_SHARED_BUILD_INFRA_SEGMENT = 'script-shared/scripts/build/'


@dataclass(frozen=True)
class TestScopeResolution:
    """Result of resolving which module set a scoped test run would cover.

    Attributes:
        scoped_modules: The sorted, de-duped module/bundle set a scoped run
            would target, derived from the footprint.
        divergence_possible: True when a scoped run could pass while a
            whole-tree run fails — the footprint spans more than one module, or
            it touches shared / cross-module test infrastructure.
        recommended_target: The single module a scoped run should target when
            divergence is impossible (scoped-equals-whole-tree by equivalence);
            None when a whole-tree run is warranted (no module arg).
    """

    scoped_modules: tuple[str, ...]
    divergence_possible: bool
    recommended_target: str | None


@dataclass(frozen=True)
class DivergenceVerdict:
    """Verdict on a scoped-vs-whole-tree outcome pair.

    Attributes:
        divergent: True when the scoped run passed but the whole-tree run did
            not — the scoped-green / whole-tree-red regression.
        caught: True when the whole-tree run caught what the scoped run missed
            (identical to ``divergent`` — the whole-tree route is what surfaces
            the divergence).
    """

    divergent: bool
    caught: bool


def _touches_shared_infra(path: str) -> bool:
    """Return True when ``path`` is shared / cross-module test infrastructure.

    Concretely: any path under ``script-shared/scripts/build/``, any
    ``conftest.py`` under ``test/`` (root ``test/conftest.py`` or a nested
    ``test/**/conftest.py``). These are exactly the footprints where a scoped
    run cannot see a cross-module regression.
    """
    if _SHARED_BUILD_INFRA_SEGMENT in path:
        return True
    if path == 'test/conftest.py':
        return True
    return path.startswith('test/') and path.endswith('/conftest.py')


def _module_for_path(path: str) -> str | None:
    """Return the owning module/bundle for ``path``, or None if it owns none.

    ``marketplace/bundles/{bundle}/…`` → segment 2 (the ``{bundle}`` token);
    ``test/{bundle}/…`` → segment 1. Any other shape contributes no module.
    """
    segments = path.split('/')
    if path.startswith('marketplace/bundles/') and len(segments) > 2:
        return segments[2]
    if path.startswith('test/') and len(segments) > 1:
        return segments[1]
    return None


def resolve_test_scope(footprint: list[str], build_map_globs: list[str]) -> TestScopeResolution:
    """Resolve the scoped module set and whether a whole-tree run is warranted.

    Each footprint entry is fnmatched against ``build_map_globs``; only matching
    entries contribute a module (segment 2 for ``marketplace/bundles/…``,
    segment 1 for ``test/…``). ``divergence_possible`` is True when the resolved
    set spans more than one module OR any footprint entry touches shared /
    cross-module test infrastructure. A single-module footprint touching no
    shared infra yields ``divergence_possible = False`` with that module as the
    ``recommended_target`` (match by equivalence); a divergent footprint yields
    ``recommended_target = None`` (whole-tree, no module arg).

    Args:
        footprint: The live footprint — the paths a scoped run derives from.
        build_map_globs: The fnmatch globs from ``build.map`` used to filter the
            footprint down to build-relevant entries.

    Returns:
        A frozen :class:`TestScopeResolution`.
    """
    modules: set[str] = set()
    for path in footprint:
        if not any(fnmatch.fnmatch(path, glob) for glob in build_map_globs):
            continue
        module = _module_for_path(path)
        if module is not None:
            modules.add(module)

    scoped_modules = tuple(sorted(modules))
    shared_infra_touched = any(_touches_shared_infra(path) for path in footprint)
    divergence_possible = len(scoped_modules) > 1 or shared_infra_touched

    recommended_target: str | None
    if not divergence_possible and len(scoped_modules) == 1:
        recommended_target = scoped_modules[0]
    else:
        recommended_target = None

    return TestScopeResolution(
        scoped_modules=scoped_modules,
        divergence_possible=divergence_possible,
        recommended_target=recommended_target,
    )


def classify_divergence(scoped_outcome: str, whole_tree_outcome: str) -> DivergenceVerdict:
    """Classify a scoped-vs-whole-tree outcome pair into a caught/not-caught verdict.

    ``divergent`` is True only when the scoped run succeeded while the whole-tree
    run did not — the scoped-green / whole-tree-red regression the gate exists to
    catch. ``caught`` equals ``divergent``: the whole-tree route is what surfaces
    the divergence. A scoped-red pair is not divergent by this definition (the
    scoped run already failed, so nothing slipped through).

    Args:
        scoped_outcome: The scoped run's outcome string (``'success'`` or other).
        whole_tree_outcome: The whole-tree run's outcome string.

    Returns:
        A frozen :class:`DivergenceVerdict`.
    """
    divergent = scoped_outcome == 'success' and whole_tree_outcome != 'success'
    return DivergenceVerdict(divergent=divergent, caught=divergent)
