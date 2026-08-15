#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the npm derivation resolver (Axis-C).

An npm package publishes no ``groupId:artifactId`` coordinate, so the Maven join
could never match one: before this resolver existed, every npm workspace's
internal-dependency set was structurally empty while every graph verb reported
success. This resolver joins on what npm actually publishes — the
``package.json`` ``name`` — and these tests pin that join.

The whole ``workspace-monorepo`` fixture is driven through the REAL npm discovery
path, so the workspace resolution (the ``workspaces: ["packages/*"]`` glob) is
exercised rather than assumed, and the modules under test are the ones production
code actually produces. No subprocess runs: npm discovery is pure
``package.json`` parsing.

The fixture is shaped to make three failure modes falsifiable rather than merely
absent:

1. ``@sample/cli`` spells its dependency ``@SAMPLE/API`` — the same package under
   npm's case rules but textually different, so an unfolded join loses the edge.
2. ``packages/unnamed`` declares no ``name`` while another module depends on the
   string ``@sample/core``; a resolver that fell back to the directory name would
   invent a package identity npm never published.
3. ``@sample/cli`` reaches ``@sample/core`` only through ``devDependencies``, so a
   join that dropped the dev scope would lose that edge.
"""

from pathlib import Path

from conftest import load_script_module

FIXTURE = Path(__file__).parent / 'fixtures' / 'workspace-monorepo'

_npm_cmd_discover = load_script_module(
    'plan-marshall', 'build-npm', '_npm_cmd_discover.py', '_npm_cmd_discover'
)
_extension = load_script_module('plan-marshall', 'build-npm', 'extension.py', '_npm_extension')

discover_npm_modules = _npm_cmd_discover.discover_npm_modules


def _discovered() -> dict[str, dict]:
    """The fixture, discovered through the real path and keyed by module name."""
    return {module['name']: module for module in discover_npm_modules(str(FIXTURE))}


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
# Identity and workspace discovery
# =============================================================================


def test_resolver_id_is_npm():
    assert _resolver().derivation_resolver_id() == 'npm'


def test_workspace_members_are_discovered_as_modules():
    """The join can only reach members discovery actually resolved.

    Asserting this separately keeps a workspace-resolution regression from
    presenting as a resolver defect.
    """
    discovered = _discovered()
    for member in ('@sample/core', '@sample/api', '@sample/cli'):
        assert member in discovered, f'workspace member {member} was not discovered'


def test_package_json_name_is_carried_on_metadata():
    """``metadata.name`` is the join key, distinct from the module's own ``name``.

    The module ``name`` falls back to the directory when package.json declares
    none, so only this field can tell a published package from an unnamed one.
    """
    discovered = _discovered()
    assert discovered['@sample/core']['metadata']['name'] == '@sample/core'
    assert discovered['unnamed']['metadata']['name'] is None


# =============================================================================
# The join produces a non-empty edge set
# =============================================================================


def test_workspace_fixture_yields_non_empty_edges():
    """The deliverable's own success condition, asserted on real discovery output."""
    assert _edges(), 'the npm resolver derived no edges from a multi-package workspace'


def test_workspace_dependency_between_members_becomes_an_edge():
    """``"@sample/core": "workspace:*"`` — the workspace protocol needs no branch.

    Discovery records the dependency as ``@sample/core:runtime``, name only, so
    the version specifier never reaches the join.
    """
    assert ('@sample/api', '@sample/core') in _edges()


def test_scoped_names_join_unchanged():
    """``@scope/pkg`` is one name, not a two-segment coordinate."""
    assert ('@sample/monorepo', '@sample/core') in _edges()


def test_full_edge_set_is_exactly_the_declared_internal_dependencies():
    assert _edges() == [
        ('@sample/api', '@sample/core'),
        ('@sample/cli', '@sample/api'),
        ('@sample/cli', '@sample/core'),
        ('@sample/monorepo', '@sample/core'),
        ('unnamed', '@sample/core'),
    ]


# =============================================================================
# Case folding, scope handling, and the no-fallback rule
# =============================================================================


def test_case_differing_spelling_still_joins():
    """``@SAMPLE/API`` reaches ``@sample/api`` under npm's case rules."""
    assert ('@sample/cli', '@sample/api') in _edges()


def test_dev_dependency_is_an_edge():
    """``@sample/cli`` reaches ``@sample/core`` only via ``devDependencies``."""
    assert ('@sample/cli', '@sample/core') in _edges()


def test_package_without_a_name_is_never_an_edge_target():
    """An unnamed package is unpublishable, so nothing can depend on it."""
    assert all(target != 'unnamed' for _, target in _edges())


def test_package_without_a_name_is_still_an_edge_source():
    """It publishes nothing, but it still DECLARES dependencies.

    Dropping it from the source side too would lose a real edge — the asymmetry
    is deliberate and is pinned so a future simplification cannot quietly remove
    it.
    """
    assert ('unnamed', '@sample/core') in _edges()


def test_external_dependencies_produce_neither_edges_nor_notes():
    """``zod`` / ``tslib`` / ``typescript`` name no module — not a suppression."""
    edges, notes = _resolver().derive_edges(_discovered(), {})
    assert all(target in _discovered() for _, target in edges)
    assert notes == []


# =============================================================================
# The ambiguous-identity-key obligation
# =============================================================================


def test_two_modules_publishing_one_package_name_yield_no_edge_and_a_note():
    modules = {
        'first': {
            'name': 'first',
            'build_systems': ['npm'],
            'metadata': {'name': '@sample/shared'},
            'dependencies': [],
        },
        'second': {
            'name': 'second',
            'build_systems': ['npm'],
            'metadata': {'name': '@sample/shared'},
            'dependencies': [],
        },
        'consumer': {
            'name': 'consumer',
            'build_systems': ['npm'],
            'metadata': {'name': '@sample/consumer'},
            'dependencies': ['@sample/shared:runtime'],
        },
    }

    edges, notes = _resolver().derive_edges(modules, {})

    assert edges == []
    assert len(notes) == 1
    assert '@sample/shared' in notes[0]
    assert 'first' in notes[0] and 'second' in notes[0]


# =============================================================================
# Build-system scoping
# =============================================================================


def test_join_ignores_modules_another_build_system_discovered():
    """A bare package name is a key shape every ecosystem uses."""
    modules = {
        'npm-consumer': {
            'name': 'npm-consumer',
            'build_systems': ['npm'],
            'metadata': {'name': 'npm-consumer'},
            'dependencies': ['shared-name:runtime'],
        },
        'py-distribution': {
            'name': 'py-distribution',
            'build_systems': ['python'],
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
            'build_systems': ['npm'],
            'metadata': {'name': '@sample/solo'},
            'dependencies': ['@sample/solo:runtime'],
        },
    }

    edges, _ = _resolver().derive_edges(modules, {})

    assert edges == []


def test_zero_modules_is_a_non_error_empty_result():
    assert _resolver().derive_edges({}, {}) == ([], [])
