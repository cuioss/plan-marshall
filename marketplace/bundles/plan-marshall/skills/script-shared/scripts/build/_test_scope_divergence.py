# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pure, tool-agnostic scope-resolution and divergence classification.

Two pure functions back the phase-6-finalize "whole-tree module-tests
divergence gate" (PLAN-14): they decide which module set a scoped test run
would cover and whether a whole-tree run is warranted, and they classify the
scoped-vs-whole-tree outcome pair into a caught/not-caught verdict.

Both functions are pure - no I/O, no subprocess, no git. The footprint, the
build_map globs and the registered-module names are all supplied by the caller
(the ``resolve-test-scope`` build subcommand reads them from the live worktree;
the tests inject them directly), so this module is deterministic and
unit-testable in isolation. In particular the registered-module set arrives as
an argument rather than being read from the architecture inventory here, which
is what keeps the "no I/O" property intact while still letting the derivation
reject a name that no module actually carries.

The scope-derivation rule mirrors, in code, the bundle-derivation prose in
``phase-6-finalize/standards/pre-push-quality-gate.md`` section "Derive unique
bundle set": each footprint entry's owning module is taken from path segment 2
for ``marketplace/bundles/{bundle}/...`` and segment 1 for ``{root}/{bundle}/...``
under any test root (``test/`` or its ``tests/`` sibling — see
:data:`_TEST_ROOTS`), and the derived name is kept only when it names a
registered module. A path that yields no such name is *unresolved*: it is
reported in ``unresolved_paths`` and it forces a whole-tree run.

Fail-closed classification discipline
-------------------------------------
This module applies rules (b) "fail closed on undetermined / None / empty state"
and (d) "require an affirmative success signal" from
``ref-code-quality/standards/error-handling.md``; see that document for the rule
statements rather than re-deriving them here. Concretely: an inability to
determine which module covers a footprint path is its own outcome and is never
laundered into the benign "no divergence possible" verdict. The one legitimate
benign verdict is an EMPTY footprint - see :func:`resolve_test_scope`.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

# Footprint prefixes whose presence means a scoped run cannot observe a
# cross-module regression - the PLAN-08 class. A change touching any of these
# forces ``divergence_possible`` regardless of how many modules the scoped set
# resolves to.
_SHARED_BUILD_INFRA_SEGMENT = 'script-shared/scripts/build/'

#: The pytest test roots this derivation recognises. ``test/`` is this
#: repository's root; ``tests/`` is the sibling convention. Every root-sensitive
#: predicate below derives from this ONE tuple, so no seam in this module can
#: recognise a root another seam does not — the asymmetry that let a ``tests/``
#: conftest resolve to a module while escaping the shared-infra check.
#:
#: The set MUST equal the ``_TEST_ROOTS`` the Python build extension declares for
#: its Axis-B tables. The two are deliberately NOT a shared import: this module's
#: purity contract is that it imports nothing from a build extension, and the
#: dependency would run the wrong way. A cross-check test pins them equal instead.
_TEST_ROOTS: tuple[str, ...] = ('test', 'tests')

#: ``{root}/`` prefixes, precomputed for ``str.startswith`` (which accepts a
#: tuple). Matching on the prefix — not on the bare root — keeps ``test/`` from
#: matching a ``tests/`` path and vice versa.
_TEST_ROOT_PREFIXES: tuple[str, ...] = tuple(f'{root}/' for root in _TEST_ROOTS)

#: The bundle-neutral homes for cross-bundle test helpers, one per test root.
#: Each is cross-module test infrastructure by construction (every bundle's suite
#: bare-imports from it), and its first path segment is not a module name, so
#: such a path is BOTH shared infra and unresolved.
_SHARED_TEST_INFRA_PREFIXES: tuple[str, ...] = tuple(f'{root}/_shared/' for root in _TEST_ROOTS)


@dataclass(frozen=True)
class TestScopeResolution:
    """Result of resolving which module set a scoped test run would cover.

    Attributes:
        scoped_modules: The sorted, de-duped module/bundle set a scoped run
            would target, derived from the footprint.
        divergence_possible: True when a scoped run could pass while a
            whole-tree run fails - the footprint spans more than one module, it
            touches shared / cross-module test infrastructure, or at least one
            footprint entry could not be mapped to a registered module.
        recommended_target: The single module a scoped run should target when
            divergence is impossible (scoped-equals-whole-tree by equivalence);
            None when a whole-tree run is warranted, and also None for the empty
            footprint (nothing to run). A consumer MUST check this value is
            non-null before interpolating it into a command.
        unresolved_paths: Every footprint entry that mapped to no registered
            module, in footprint order. Non-empty means coverage for those paths
            could not be determined, which is reported rather than silently
            dropped (ADR-014) and forces the whole-tree verdict.
    """

    scoped_modules: tuple[str, ...]
    divergence_possible: bool
    recommended_target: str | None
    unresolved_paths: tuple[str, ...]


@dataclass(frozen=True)
class DivergenceVerdict:
    """Verdict on a scoped-vs-whole-tree outcome pair.

    Attributes:
        divergent: True when the scoped run passed but the whole-tree run did
            not - the scoped-green / whole-tree-red regression.
        caught: True when the whole-tree run caught what the scoped run missed
            (identical to ``divergent`` - the whole-tree route is what surfaces
            the divergence).
    """

    divergent: bool
    caught: bool


def _touches_shared_infra(path: str) -> bool:
    """Return True when ``path`` is shared / cross-module test infrastructure.

    Concretely: any path under ``script-shared/scripts/build/``, any path under a
    ``{root}/_shared/`` cross-bundle test-helper root, and any ``conftest.py``
    under a test root (root ``{root}/conftest.py`` or a nested
    ``{root}/**/conftest.py``). These are exactly the footprints where a scoped
    run cannot see a cross-module regression.

    Both test-root predicates range over EVERY entry of :data:`_TEST_ROOTS`, not
    over ``test/`` alone. That symmetry is load-bearing rather than cosmetic:
    :func:`_module_for_path` derives a module name from either root, so a
    ``tests/{module}/conftest.py`` recognised as module-owned but NOT recognised
    as shared infra would yield a confident single-module verdict for a change
    that can break every module's suite — a fail-OPEN introduced by widening
    only one of the two seams.

    The ``{root}/`` + ``/conftest.py`` predicate already covers the root
    ``{root}/conftest.py`` case (``str.endswith`` overlaps at the leading ``/``),
    so no separate root-conftest branch is needed.
    """
    if _SHARED_BUILD_INFRA_SEGMENT in path:
        return True
    if path.startswith(_SHARED_TEST_INFRA_PREFIXES):
        return True
    return path.startswith(_TEST_ROOT_PREFIXES) and path.endswith('/conftest.py')


def _module_for_path(path: str, registered_modules: Collection[str]) -> str | None:
    """Return the owning module/bundle for ``path``, or None if it owns none.

    ``marketplace/bundles/{bundle}/...`` derives segment 2 (the ``{bundle}``
    token); ``{root}/{bundle}/...`` under ANY entry of :data:`_TEST_ROOTS`
    derives segment 1. Any other shape derives nothing.

    The test-root check reads ``segments[0]`` against the root set rather than
    prefix-matching a single literal, so ``test/`` and ``tests/`` are recognised
    independently and neither can match the other's paths.

    A name is derived only when ``path`` is nested *inside* a bundle/module
    directory: ``marketplace/bundles/{bundle}/...`` needs more than three
    segments and ``{root}/{bundle}/...`` needs more than two. A root-level file
    such as ``marketplace/bundles/README.md`` or ``test/conftest.py`` therefore
    derives no name and returns None.

    A derived name is returned only when it names a REGISTERED module. Returning
    the path segment verbatim would invent modules that do not exist - the
    ``test/_shared/...`` root derives the phantom name ``_shared``, and a scoped
    run against it targets nothing at all. An unregistered name is therefore
    reported as "no owning module" so the caller fails closed to the whole tree.

    Args:
        path: A repo-relative footprint entry.
        registered_modules: The caller-enumerated registered module names. The
            purity contract of this module means the set is supplied, never read
            from an inventory here.
    """
    segments = path.split('/')
    if path.startswith('marketplace/bundles/') and len(segments) > 3:
        derived = segments[2]
    elif segments[0] in _TEST_ROOTS and len(segments) > 2:
        derived = segments[1]
    else:
        return None
    # UNCHANGED fail-closed guard: widening WHICH roots yield a candidate name
    # must never widen WHICH names are accepted. A derived name that no
    # registered module carries is still rejected here, so the caller reports the
    # path in ``unresolved_paths`` and falls back to the whole tree.
    return derived if derived in registered_modules else None


def resolve_test_scope(
    footprint: list[str],
    build_map_globs: list[str],
    registered_modules: Collection[str],
) -> TestScopeResolution:
    """Resolve the scoped module set and whether a whole-tree run is warranted.

    Every footprint entry contributes its owning module (segment 2 for
    ``marketplace/bundles/...``, segment 1 for any test root in
    :data:`_TEST_ROOTS`) whenever that derived name is registered. Module
    ownership is derived independently of the
    ``build_map_globs`` filter: the globs answer "is this build-relevant", module
    ownership answers the different question "could a scoped run miss a
    regression", and conflating the two under-reports the span for a change whose
    cross-bundle files are not ``.py`` - a bundle's rule catalogue or roster
    document matches no glob yet is asserted on by that bundle's tests. The globs
    remain part of the caller-supplied input contract; they are deliberately not
    consulted for the span or for the empty-scope fallback, which is exactly the
    pre-filter whose removal this function's fail-closed behaviour depends on.

    ``divergence_possible`` is True when ANY of three conditions holds: the
    resolved set spans more than one module; any footprint entry touches shared /
    cross-module test infrastructure; or ``unresolved_paths`` is non-empty (at
    least one entry mapped to no registered module). The third condition is the
    fail-closed one: coverage for an unmapped path cannot be determined, so the
    run falls back to the whole tree rather than emitting a confident scoped
    target that does not cover it. A single-module footprint touching no shared
    infra and leaving nothing unresolved yields ``divergence_possible = False``
    with that module as the ``recommended_target`` (match by equivalence).

    ``recommended_target`` is non-null ONLY in that single-module case. The empty
    footprint is the one legitimate benign verdict: it genuinely has nothing to
    test, so it alone returns ``divergence_possible: False`` with
    ``recommended_target: None`` - collapsing it into the fail-closed branch
    would force a whole-tree pytest run on every no-op footprint, the opposite of
    the escalate-only-on-trigger discipline the gate exists to preserve. Because
    ``None`` therefore spans "whole-tree warranted" and "nothing to run", a
    consumer MUST check ``recommended_target`` is non-null before interpolating
    it into a command, and MUST branch on an empty ``scoped_modules`` before
    branching on ``divergence_possible`` (ADR-015: an absent identity is a stated
    sentinel and every presence guard is a meaning guard).

    Args:
        footprint: The live footprint - the paths a scoped run derives from.
        build_map_globs: The fnmatch globs from ``build.map`` describing which
            footprint entries are build-relevant. Part of the caller contract;
            see the paragraph above for why the span derivation does not consult
            them.
        registered_modules: The caller-enumerated registered module names. A
            derived name absent from this collection resolves to no module and
            lands in ``unresolved_paths``.

    Returns:
        A frozen :class:`TestScopeResolution`.
    """
    modules: set[str] = set()
    unresolved: list[str] = []
    for path in footprint:
        module = _module_for_path(path, registered_modules)
        if module is None:
            unresolved.append(path)
        else:
            modules.add(module)

    scoped_modules = tuple(sorted(modules))
    unresolved_paths = tuple(unresolved)
    shared_infra_touched = any(_touches_shared_infra(path) for path in footprint)
    divergence_possible = len(scoped_modules) > 1 or shared_infra_touched or bool(unresolved_paths)

    recommended_target: str | None
    if not divergence_possible and len(scoped_modules) == 1:
        recommended_target = scoped_modules[0]
    else:
        recommended_target = None

    return TestScopeResolution(
        scoped_modules=scoped_modules,
        divergence_possible=divergence_possible,
        recommended_target=recommended_target,
        unresolved_paths=unresolved_paths,
    )


def classify_divergence(scoped_outcome: str, whole_tree_outcome: str) -> DivergenceVerdict:
    """Classify a scoped-vs-whole-tree outcome pair into a caught/not-caught verdict.

    ``divergent`` is True only when the scoped run succeeded while the whole-tree
    run did not - the scoped-green / whole-tree-red regression the gate exists to
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
