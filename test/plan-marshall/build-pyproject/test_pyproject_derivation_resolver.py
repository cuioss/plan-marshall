#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pyproject derivation resolver (Axis-C).

A Python project publishes no ``groupId:artifactId`` coordinate, so the Maven
join could never match one: before this resolver existed, every Python project's
internal-dependency set was structurally empty while every graph verb reported
success. This resolver joins on what Python actually publishes — the PEP 621
``[project] name`` — and these tests pin that join.

The whole ``multi-module-python`` fixture is driven through the REAL Python
discovery path, not a hand-built sample of it, so the module dicts under test are
the ones production code actually produces. No subprocess runs: the Python
discoverer's dependency extraction is pure ``pyproject.toml`` parsing.

The fixture is shaped to make three failure modes falsifiable rather than merely
absent:

1. ``sample_cli`` spells its dependencies as ``Sample_API`` and ``sample.core``
   — PEP 503-equivalent to the published ``sample-api`` / ``sample-core`` but
   textually different, so a raw string join loses both edges.
2. ``toolbox`` is a discovered module that declares no ``[project] name``, and
   the fixture root depends on the same string. A resolver that fell back to the
   directory name would fabricate that edge.
3. ``sample_cli``'s ``sample.core`` entry is a ``dev`` optional-dependency, so a
   join that dropped the dev scope would lose it.
"""

from pathlib import Path

from conftest import load_script_module

FIXTURE = Path(__file__).parent / 'fixtures' / 'multi-module-python'

_pyproject_cmd_discover = load_script_module(
    'plan-marshall', 'build-pyproject', '_pyproject_cmd_discover.py', '_pyproject_cmd_discover'
)
_extension = load_script_module('plan-marshall', 'build-pyproject', 'extension.py', '_pyproject_extension')

discover_python_modules = _pyproject_cmd_discover.discover_python_modules


def _discovered() -> dict[str, dict]:
    """The fixture, discovered through the real path and keyed by module name."""
    return {module['name']: module for module in discover_python_modules(str(FIXTURE))}


def _resolver():
    return _extension.BuildExtension()


def _edges() -> list[tuple[str, str]]:
    # The extension is loaded by file location, so it carries no type
    # information; declaring the unpack target keeps the helper's contract
    # explicit rather than propagating ``Any`` into every caller.
    edges: list[tuple[str, str]]
    edges, _ = _resolver().derive_edges(_discovered(), {})
    return edges


# =============================================================================
# Identity
# =============================================================================


def test_resolver_id_is_pyproject_not_python():
    """``python`` belongs to pm-dev-python's import join; ids must stay unique.

    Two resolvers answering to one id collapse into a single producer identity,
    so the discovery collector drops the second claimant — which would silently
    remove one of the two derivations entirely.
    """
    assert _resolver().derivation_resolver_id() == 'pyproject'


# =============================================================================
# The join produces a non-empty edge set
# =============================================================================


def test_multi_module_fixture_yields_non_empty_edges():
    """The deliverable's own success condition, asserted on real discovery output."""
    assert _edges(), 'the pyproject resolver derived no edges from a multi-module Python project'


def test_declared_internal_dependency_becomes_an_edge():
    assert ('sample_api', 'sample_core') in _edges()


def test_root_module_edges_use_the_distribution_name_not_the_directory_name():
    """The root discovers as ``default`` but publishes ``sample-platform``.

    Both ends of the join are distribution names while both ends of the EDGE are
    module names, so this pins that the resolver translates between them.
    """
    edges = _edges()
    assert ('default', 'sample_core') in edges
    assert ('default', 'sample_api') in edges


def test_full_edge_set_is_exactly_the_declared_internal_dependencies():
    assert _edges() == [
        ('default', 'sample_api'),
        ('default', 'sample_core'),
        ('sample_api', 'sample_core'),
        ('sample_cli', 'sample_api'),
        ('sample_cli', 'sample_core'),
    ]


# =============================================================================
# PEP 503 normalisation, scope handling, and the no-fallback rule
# =============================================================================


def test_pep503_equivalent_spelling_still_joins():
    """``Sample_API`` and ``sample-api`` are one distribution under PEP 503."""
    assert ('sample_cli', 'sample_api') in _edges()


def test_dev_scope_dependency_is_an_edge():
    """``sample.core`` is declared under ``optional-dependencies.dev``.

    A dev dependency is a real edge for impact analysis: changing the
    depended-upon module can break the dependent's tests.
    """
    assert ('sample_cli', 'sample_core') in _edges()


def test_module_without_a_project_name_is_never_an_edge_target():
    """``toolbox`` declares no ``[project] name``, so it publishes no distribution.

    The fixture root depends on the string ``toolbox``, which can therefore only
    be the unrelated PyPI package of that name. Falling back to the directory
    name would turn that into a fabricated internal edge.
    """
    assert all(target != 'toolbox' for _, target in _edges())


def test_external_dependencies_produce_neither_edges_nor_notes():
    """``requests`` / ``typing-extensions`` name no module — not a suppression.

    Reporting every external dependency as a suppressed edge would bury the
    genuine suppressions the report exists to surface.
    """
    edges, notes = _resolver().derive_edges(_discovered(), {})
    assert all(target in _discovered() for _, target in edges)
    assert notes == []


# =============================================================================
# The ambiguous-identity-key obligation
# =============================================================================


def test_two_modules_publishing_one_distribution_name_yield_no_edge_and_a_note():
    """Abstain-and-report, never a last-write-wins pick.

    Resolving the collision by insertion order would silently drop one module and
    every edge pointing at it, and which module survived would depend on map
    iteration order — a non-deterministic answer presented as a confident one.
    """
    modules = {
        'first': {
            'name': 'first',
            'build_systems': ['python'],
            'metadata': {'name': 'shared-dist'},
            'dependencies': [],
        },
        'second': {
            'name': 'second',
            'build_systems': ['python'],
            'metadata': {'name': 'shared-dist'},
            'dependencies': [],
        },
        'consumer': {
            'name': 'consumer',
            'build_systems': ['python'],
            'metadata': {'name': 'consumer'},
            'dependencies': ['shared-dist:runtime'],
        },
    }

    edges, notes = _resolver().derive_edges(modules, {})

    assert edges == []
    assert len(notes) == 1
    assert 'shared-dist' in notes[0]
    assert 'first' in notes[0] and 'second' in notes[0]


# =============================================================================
# Build-system scoping
# =============================================================================


def test_join_ignores_modules_another_build_system_discovered():
    """A bare distribution name is a key shape every ecosystem uses.

    Without scoping this resolver would claim provenance for an npm package's
    edges and could fabricate an edge between a Python distribution and a
    same-named npm package.
    """
    modules = {
        'py-consumer': {
            'name': 'py-consumer',
            'build_systems': ['python'],
            'metadata': {'name': 'py-consumer'},
            'dependencies': ['shared-name:runtime'],
        },
        'npm-package': {
            'name': 'npm-package',
            'build_systems': ['npm'],
            'metadata': {'name': 'shared-name'},
            'dependencies': [],
        },
    }

    edges, notes = _resolver().derive_edges(modules, {})

    assert edges == []
    assert notes == []


def test_self_dependency_is_not_an_edge():
    modules = {
        'solo': {
            'name': 'solo',
            'build_systems': ['python'],
            'metadata': {'name': 'solo-dist'},
            'dependencies': ['solo-dist:runtime'],
        },
    }

    edges, _ = _resolver().derive_edges(modules, {})

    assert edges == []


def test_zero_modules_is_a_non_error_empty_result():
    assert _resolver().derive_edges({}, {}) == ([], [])
