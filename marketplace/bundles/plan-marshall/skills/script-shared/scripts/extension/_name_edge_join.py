#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The name-keyed module-edge join shared by the native build-system resolvers.

Maven and Gradle publish a ``groupId:artifactId`` coordinate pair, so their edge
derivation joins on that pair. Python and npm publish no such pair: a Python
distribution is identified by its PEP 621 ``[project] name`` and an npm package
by its ``package.json`` ``name``, and both ecosystems name their dependencies by
that single string. The join those ecosystems need is therefore keyed on ONE
name, not on a coordinate pair — which is what this module owns.

The mechanics are identical across the two ecosystems and only the KEY differs
(PEP 503 normalisation for Python, case folding for npm), so the shape lives
here once, parameterised by a normaliser, rather than being copied into each
build skill's extension. What stays with each resolver is the domain knowledge:
which field carries the published name, and how two names are compared.

This module holds no state, runs no subprocess and touches no file — the Axis-C
purity contract binds every caller, so it binds this helper too. See
``extension-api/standards/ext-point-derivation-resolver.md`` for the four-face
contract these joins implement.
"""

import re
from collections.abc import Callable
from typing import Any

#: Runs of ``-``, ``_`` and ``.`` collapse to a single ``-`` under PEP 503.
_PEP503_SEPARATORS = re.compile(r'[-_.]+')


def normalize_pep503(name: str) -> str:
    """Return ``name`` in PEP 503 normalised form.

    Python packaging compares distribution names case-insensitively and treats
    any run of ``-``, ``_`` or ``.`` as equivalent, so ``Typing_Extensions``,
    ``typing.extensions`` and ``typing-extensions`` are ONE distribution. A join
    that compared the raw strings would miss a real edge whenever a dependency
    spelled a sibling's name in a different but equivalent form — a silent
    under-report, which is the failure class this seam exists to remove.
    """
    return _PEP503_SEPARATORS.sub('-', name).strip().lower()


def normalize_npm(name: str) -> str:
    """Return ``name`` in the form used to compare npm package names.

    npm requires new package names to be lower-case and compares them as exact
    strings otherwise; scope prefixes (``@scope/pkg``) are part of the name. Case
    folding is therefore the whole normalisation: it admits the legacy
    mixed-case names that predate the lower-case rule without merging two names
    that npm itself considers distinct.
    """
    return name.strip().lower()


def scoped_modules(
    derived_by_name: dict[str, dict[str, Any]],
    build_system: str,
) -> dict[str, dict[str, Any]]:
    """Return only the modules ``build_system`` discovered.

    A name-keyed join MUST be scoped to one ecosystem, and the reason is not
    tidiness. Unlike a ``groupId:artifactId`` coordinate — which only Maven and
    Gradle publish, so the Maven join is scoped by the shape of its own key — a
    bare distribution/package name is a shape every ecosystem uses. An unscoped
    name join would therefore do two wrong things at once in a mixed repository:
    it would claim provenance for edges another ecosystem's resolver derived
    (``producers: [npm, pyproject]`` on a pure-Python edge asserts that the npm
    resolver found it, which it did not), and it would FABRICATE an edge between
    a Python distribution and an npm package that merely share a name. Both were
    observed before this scoping existed.

    Scoping applies to both ends of the join: a module outside the ecosystem is
    neither a possible edge source nor a possible edge target.

    Args:
        derived_by_name: Module name → derived data, as handed to ``derive_edges``.
        build_system: The ``build_systems`` entry this resolver owns (e.g.
            ``'python'``, ``'npm'``).

    Returns:
        The subset of ``derived_by_name`` whose ``build_systems`` names
        ``build_system``.
    """
    return {
        name: data
        for name, data in derived_by_name.items()
        if build_system in (data.get('build_systems') or [])
    }


def build_name_owners(
    derived_by_name: dict[str, dict[str, Any]],
    published_name: Callable[[dict[str, Any]], str | None],
    normalize: Callable[[str], str],
) -> tuple[dict[str, str], list[str]]:
    """Map each UNAMBIGUOUS published name to the module that publishes it.

    A name claimed by exactly one module resolves to that module. A name claimed
    by two or more distinct modules is **ambiguous** and is left out of the map
    entirely, so the join emits no edge for it and the collision is reported.

    This discharges the ambiguous-identity-key obligation the resolver contract
    places on every resolver: resolving a collision by insertion order would
    silently drop one module and every edge pointing at it, and which module
    survived would depend on map iteration order — a non-deterministic answer
    presented as a confident one. Abstaining and reporting is strictly better
    than guessing, because a genuinely ambiguous name cannot be attributed to a
    single module from the name alone.

    A module for which ``published_name`` yields nothing publishes no name at
    all, so nothing can depend on it by name and it is simply absent from the
    map. That is not a suppressed edge and carries no note: a directory that is
    a module but not a distribution (a scripts folder, an unnamed workspace
    root) is outside the join rather than lost by it.

    Args:
        derived_by_name: Module name → derived data, as handed to ``derive_edges``.
        published_name: Reads a module's published distribution/package name out
            of its derived data, or ``None`` when it publishes none.
        normalize: Folds a name into the form both sides of the join compare on.

    Returns:
        An ``(owners, notes)`` tuple. ``owners`` maps each unambiguous normalised
        name to its owning module name. ``notes`` names one suppressed key per
        collision, sorted for determinism.
    """
    claimants: dict[str, set[str]] = {}
    for mod_name, mod_data in derived_by_name.items():
        raw = published_name(mod_data)
        if not raw:
            continue
        key = normalize(raw)
        if key:
            claimants.setdefault(key, set()).add(mod_name)

    owners: dict[str, str] = {}
    notes: list[str] = []
    for key in sorted(claimants):
        claiming = claimants[key]
        if len(claiming) == 1:
            owners[key] = next(iter(claiming))
            continue
        notes.append(
            f'ambiguous name {key}: claimed by {", ".join(sorted(claiming))} — no edge emitted'
        )
    return owners, notes


def derive_name_edges(
    derived_by_name: dict[str, dict[str, Any]],
    build_system: str,
    published_name: Callable[[dict[str, Any]], str | None],
    normalize: Callable[[str], str],
) -> tuple[list[tuple[str, str]], list[str]]:
    """Derive module edges by joining dependency names against published names.

    The join is scoped to the modules ``build_system`` discovered — see
    :func:`scoped_modules` for why an unscoped name join both misattributes
    provenance and fabricates cross-ecosystem edges.

    Within that scope, both ecosystems state a dependency as a ``name:scope``
    string (the technology-native format ``module-discovery.md`` documents), so
    the join takes the FIRST colon-separated part as the dependency's name and
    looks it up among the published names. The scope segment is deliberately
    ignored, exactly as the Maven join ignores its own: a development-time
    dependency is still a real edge for impact analysis, since changing the
    depended-upon module can break the dependent's tests.

    A dependency naming no known module is an EXTERNAL dependency, not a
    suppressed edge — the overwhelming majority of any real project's dependency
    list — so it is skipped without a note. Only a condition that suppressed an
    edge the join could otherwise have made is reported, which keeps the
    per-resolver report readable enough to be worth reading.

    Self-edges are excluded: a module's dependency on its own published name is
    not an internal edge. (The core merge drops self-edges too; excluding them
    here keeps each resolver's own ``edge_count`` report honest.)

    Args:
        derived_by_name: Module name → derived data, as handed to ``derive_edges``.
        build_system: The ``build_systems`` entry this resolver owns.
        published_name: Reads a module's published distribution/package name.
        normalize: Folds a name into the form both sides of the join compare on.

    Returns:
        An ``(edges, notes)`` tuple. ``edges`` is the sorted list of
        ``(dependent, dependency)`` module-name pairs. ``notes`` names every name
        collision that suppressed an edge.
    """
    in_scope = scoped_modules(derived_by_name, build_system)
    owners, notes = build_name_owners(in_scope, published_name, normalize)

    edges: set[tuple[str, str]] = set()
    for mod_name, mod_data in in_scope.items():
        for dependency in mod_data.get('dependencies') or []:
            if not isinstance(dependency, str):
                continue
            dep_name = dependency.split(':', 1)[0]
            if not dep_name:
                continue
            target = owners.get(normalize(dep_name))
            if target is not None and target != mod_name:
                edges.add((mod_name, target))

    return sorted(edges), notes
