#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Characterization tests for the Maven derivation resolver (Axis-C).

The Maven coordinate join used to live inline in ``manage-architecture``; it now
lives on ``build-maven``'s ``BuildExtension`` as a ``DerivationResolverBase``
implementor. These tests pin the edge set that join produces so the re-homing is
demonstrably behaviour-preserving on every unambiguous input, and pin the ONE
deliberate divergence: a coordinate claimed by two distinct module names yields
no edge and a reported collision instead of a silent last-write-wins pick.

The characterization set is the WHOLE ``multi-module-project`` fixture — all five
poms (the reactor root, core, services/auth-service, services/user-service, and
legacy/auth-service) — discovered through the real Maven discovery path, not a
hand-built sample of it.

**No Maven subprocess runs here.** Discovery's cheap path is subprocess-free but
deliberately leaves ``dependencies`` empty; the resolved dependency tree is an
enrich-path concern (``enrich_maven_module`` runs ``dependency:tree``). Since a
resolver is a pure function of its arguments and the CALLER materializes
``dependencies`` before dispatch, these tests play the caller: they inject exactly
the ``groupId:artifactId:scope`` strings the enrich path would return for each
fixture pom's declared ``<dependencies>``. That keeps the test hermetic while
exercising the real join over real discovery output.

## What characterization surfaced

Two findings the fixture exposes, both recorded here rather than smoothed over:

1. **The fixture's ambiguity is at the module-NAME level, not merely the
   coordinate level.** A discovered module's ``name`` IS its ``artifactId``, so
   ``services/auth-service`` and ``legacy/auth-service`` both discover as
   ``auth-service``. The graph layer keys modules by name, so building that
   name-keyed map COLLAPSES the two into one entry before any resolver is
   consulted — see
   :func:`test_fixture_name_collision_collapses_before_the_resolver_sees_it`. This
   is upstream of Axis-C and is NOT something a derivation resolver can fix.
2. **Consequently the resolver's coordinate-collision branch is unreachable via
   this fixture's name-keyed map** (one surviving claimant is not a collision), so
   that branch is pinned separately against the input shape it exists for: two
   DISTINCT module names publishing one coordinate.
"""

import importlib.util
from pathlib import Path

from conftest import load_script_module

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
FIXTURES_DIR = Path(__file__).parent / 'fixtures'
MULTI_MODULE_FIXTURE = FIXTURES_DIR / 'multi-module-project'

EXTENSION_FILE = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'build-maven'
    / 'scripts'
    / 'extension.py'
)

_maven_cmd_discover = load_script_module(
    'plan-marshall', 'build-maven', '_maven_cmd_discover.py', '_maven_cmd_discover'
)
discover_maven_modules = _maven_cmd_discover.discover_maven_modules


def _load_maven_build_extension():
    """Load the build-maven BuildExtension by explicit file path.

    Every build skill ships an ``extension.py`` sharing the module basename
    ``extension``; loading via ``spec_from_file_location`` against the explicit
    path avoids the cross-skill ``import extension`` collision.
    """
    spec = importlib.util.spec_from_file_location('maven_build_extension', EXTENSION_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BuildExtension = _load_maven_build_extension().BuildExtension


# =============================================================================
# Fixture wiring — real discovery + caller-materialized dependencies
# =============================================================================

# The resolved dependency tree each fixture pom's declared <dependencies> block
# produces, keyed by the module's repo-relative path (NOT its name — two fixture
# modules share the name ``auth-service``, which is finding #1 above). Scope is
# ``compile`` because none of the fixture declarations names a scope.
_ENRICHED_DEPENDENCIES_BY_PATH: dict[str, list[str]] = {
    '.': [],
    'core': [],
    'legacy/auth-service': [],
    'services/auth-service': ['com.example:core-module:compile'],
    'services/user-service': [
        'com.example:core-module:compile',
        'com.example:auth-service:compile',
    ],
}


def _discovered_fixture_modules() -> list[dict]:
    """Discover the whole fixture through the real Maven discovery path.

    Returns the discovery LIST (not a name-keyed map), so both same-named
    ``auth-service`` modules survive and the name collapse stays observable.
    """
    modules: list[dict] = list(discover_maven_modules(str(MULTI_MODULE_FIXTURE)))
    for module in modules:
        module_path = module['paths']['module']
        module['dependencies'] = list(_ENRICHED_DEPENDENCIES_BY_PATH[module_path])
    return modules


def _fixture_derived_by_name() -> dict[str, dict]:
    """Build the name-keyed derived map the graph layer hands a resolver.

    This is the real shape — ``manage-architecture`` keys modules by name — and
    it is where the two ``auth-service`` modules collapse into one entry.
    """
    return {module['name']: module for module in _discovered_fixture_modules()}


def _module(name: str, group_id=None, artifact_id=None, dependencies=None) -> dict:
    """A minimal derived-module dict carrying only what the join reads."""
    return {
        'name': name,
        'metadata': {'group_id': group_id, 'artifact_id': artifact_id},
        'dependencies': list(dependencies or []),
    }


def _derive(modules: dict[str, dict]) -> tuple[list[tuple[str, str]], list[str]]:
    """Run the Maven resolver's derive_edges over a name-keyed module map."""
    edges: list[tuple[str, str]]
    notes: list[str]
    edges, notes = BuildExtension().derive_edges(modules, {})
    return edges, notes


# =============================================================================
# 1. Identity
# =============================================================================


def test_derivation_resolver_id_is_the_stable_maven_identity():
    assert BuildExtension().derivation_resolver_id() == 'maven'


# =============================================================================
# 2. Characterization over the whole fixture
# =============================================================================


def test_fixture_discovers_all_five_poms():
    """The characterization set is the whole fixture — all five poms."""
    modules = _discovered_fixture_modules()

    assert len(modules) == 5
    assert sorted(module['paths']['module'] for module in modules) == [
        '.',
        'core',
        'legacy/auth-service',
        'services/auth-service',
        'services/user-service',
    ]


def test_fixture_name_collision_collapses_before_the_resolver_sees_it():
    """FINDING: two fixture modules discover under one name, so the map loses one.

    ``name`` IS ``artifactId``, so ``services/auth-service`` and
    ``legacy/auth-service`` both discover as ``auth-service``. Keying by name
    therefore drops one module — and WHICH one survives is decided by discovery
    order, not by anything meaningful. Discovery sorts descriptors by (depth,
    path), so ``legacy/...`` is inserted first and ``services/...`` overwrites it.

    This assertion documents current behaviour; it is NOT an endorsement of it.
    The loss happens in the graph layer's name-keyed map, upstream of Axis-C, so
    no derivation resolver can repair it.
    """
    modules = _discovered_fixture_modules()
    derived_by_name = _fixture_derived_by_name()

    assert len(modules) == 5
    assert len(derived_by_name) == 4, 'the two auth-service modules collapse to one key'
    assert derived_by_name['auth-service']['paths']['module'] == 'services/auth-service'


def test_fixture_edge_set_is_the_pinned_coordinate_join():
    """Pin the edge set the join produces over the real fixture.

    ``services/auth-service`` depends on ``com.example:core-module``, and
    ``services/user-service`` depends on both ``com.example:core-module`` and
    ``com.example:auth-service``. Every one of those coordinates resolves to a
    known module, so all three edges are internal. Edges run
    (dependent, dependency).
    """
    edges, notes = _derive(_fixture_derived_by_name())

    assert edges == [
        ('auth-service', 'core-module'),
        ('user-service', 'auth-service'),
        ('user-service', 'core-module'),
    ]
    # No coordinate has two distinct claimants in the name-keyed map (the collapse
    # already removed the second auth-service), so the join reports nothing.
    assert notes == []


def test_fixture_aggregator_root_contributes_no_edge():
    """The reactor root declares no dependencies, so it is edge-free."""
    edges, _notes = _derive(_fixture_derived_by_name())

    assert all('parent-project' not in edge for edge in edges)


def test_fixture_user_service_edge_to_auth_service_is_ambiguous_by_construction():
    """The one fixture edge that cannot be attributed to a single module.

    ``services/user-service`` declares a dependency on ``com.example:auth-service``
    — a coordinate TWO fixture modules publish. The emitted edge names the module
    that happened to survive the name collapse, so this edge is confident-looking
    and yet unattributable. It is the concrete reason the collision rule exists.
    """
    edges, _notes = _derive(_fixture_derived_by_name())

    assert ('user-service', 'auth-service') in edges


# =============================================================================
# 3. The deliberate divergence — duplicate coordinate, two distinct names
# =============================================================================


def test_duplicate_coordinate_emits_no_edge_and_reports_the_collision():
    """The single intentional divergence from the pre-move join.

    Two DISTINCT module names publish ``com.example:auth-service``. The pre-move
    join built its map with a bare last-write-wins assignment, silently dropping
    one module and every edge pointing at it. The resolver instead abstains and
    reports, because the dependency cannot be attributed from the coordinate alone.
    """
    modules = {
        'services-auth': _module('services-auth', 'com.example', 'auth-service'),
        'legacy-auth': _module('legacy-auth', 'com.example', 'auth-service'),
        'user-service': _module(
            'user-service',
            'com.example',
            'user-service',
            ['com.example:auth-service:compile'],
        ),
    }

    edges, notes = _derive(modules)

    assert edges == [], 'an ambiguous coordinate must yield NO edge'
    assert notes == [
        'ambiguous coordinate com.example:auth-service: claimed by '
        'legacy-auth, services-auth — no edge emitted'
    ]


def test_duplicate_coordinate_does_not_suppress_unambiguous_siblings():
    """A collision suppresses ONLY its own coordinate, not the whole edge set."""
    modules = {
        'services-auth': _module('services-auth', 'com.example', 'auth-service'),
        'legacy-auth': _module('legacy-auth', 'com.example', 'auth-service'),
        'core': _module('core', 'com.example', 'core-module'),
        'user-service': _module(
            'user-service',
            'com.example',
            'user-service',
            ['com.example:auth-service:compile', 'com.example:core-module:compile'],
        ),
    }

    edges, notes = _derive(modules)

    assert edges == [('user-service', 'core')]
    assert len(notes) == 1


def test_three_way_coordinate_collision_names_every_claimant():
    """Every colliding module is named, so the report is not itself lossy."""
    modules = {
        'alpha': _module('alpha', 'com.example', 'shared'),
        'beta': _module('beta', 'com.example', 'shared'),
        'gamma': _module('gamma', 'com.example', 'shared'),
    }

    _edges, notes = _derive(modules)

    assert notes == [
        'ambiguous coordinate com.example:shared: claimed by '
        'alpha, beta, gamma — no edge emitted'
    ]


def test_one_module_claiming_a_coordinate_twice_is_not_a_collision():
    """A collision needs two DISTINCT module names, not two mentions of one."""
    modules = {
        'core': _module('core', 'com.example', 'core-module'),
        'app': _module(
            'app',
            'com.example',
            'app',
            ['com.example:core-module:compile', 'com.example:core-module:test'],
        ),
    }

    edges, notes = _derive(modules)

    assert edges == [('app', 'core')]
    assert notes == []


# =============================================================================
# 4. Behaviour preserved on the remaining unambiguous inputs
# =============================================================================


def test_module_without_group_id_contributes_no_coordinate():
    """A module missing ``group_id`` publishes nothing, so nothing resolves to it."""
    modules = {
        'nameless': _module('nameless', None, 'core-module'),
        'app': _module('app', 'com.example', 'app', ['com.example:core-module:compile']),
    }

    edges, notes = _derive(modules)

    assert edges == []
    assert notes == []


def test_module_without_artifact_id_contributes_no_coordinate():
    modules = {
        'nameless': _module('nameless', 'com.example', None),
        'app': _module('app', 'com.example', 'app', ['com.example:core-module:compile']),
    }

    edges, _notes = _derive(modules)

    assert edges == []


def test_dependency_string_with_fewer_than_two_parts_is_ignored():
    """The join matches on the first TWO colon-separated parts; fewer cannot match."""
    modules = {
        'core': _module('core', 'com.example', 'core-module'),
        'app': _module('app', 'com.example', 'app', ['com.example', 'bare-token', '']),
    }

    edges, notes = _derive(modules)

    assert edges == []
    assert notes == []


def test_dependency_with_more_than_three_parts_still_matches_on_the_first_two():
    """Extra segments beyond groupId:artifactId are ignored, not a match failure."""
    modules = {
        'core': _module('core', 'com.example', 'core-module'),
        'app': _module('app', 'com.example', 'app', ['com.example:core-module:jar:1.0:test']),
    }

    edges, _notes = _derive(modules)

    assert edges == [('app', 'core')]


def test_external_dependency_matching_no_module_produces_no_edge():
    modules = {
        'core': _module('core', 'com.example', 'core-module'),
        'app': _module(
            'app',
            'com.example',
            'app',
            ['org.slf4j:slf4j-api:compile', 'com.example:core-module:compile'],
        ),
    }

    edges, _notes = _derive(modules)

    assert edges == [('app', 'core')], 'only the internal coordinate yields an edge'


def test_self_dependency_is_excluded():
    """A module depending on its own coordinate is not a reactor edge."""
    modules = {'core': _module('core', 'com.example', 'core-module', ['com.example:core-module:compile'])}

    edges, _notes = _derive(modules)

    assert edges == []


def test_empty_module_map_derives_nothing():
    """Zero modules is a non-error outcome, not an exception."""
    edges, notes = _derive({})

    assert edges == []
    assert notes == []


def test_edges_are_sorted_for_byte_stable_output():
    modules = {
        'zeta': _module('zeta', 'com.example', 'zeta'),
        'alpha': _module('alpha', 'com.example', 'alpha'),
        'app': _module(
            'app',
            'com.example',
            'app',
            ['com.example:zeta:compile', 'com.example:alpha:compile'],
        ),
    }

    edges, _notes = _derive(modules)

    assert edges == [('app', 'alpha'), ('app', 'zeta')]
    assert edges == sorted(edges)


def test_enriched_overlay_is_not_consulted():
    """Declaration-over-derivation precedence is core's ruling, applied upstream.

    A resolver that honoured ``internal_dependencies`` itself would be
    second-guessing a decision it does not own, so the overlay must not change
    what the join returns.
    """
    modules = {
        'core': _module('core', 'com.example', 'core-module'),
        'app': _module('app', 'com.example', 'app', ['com.example:core-module:compile']),
    }
    overlay = {'app': {'internal_dependencies': []}}

    with_overlay, _notes = BuildExtension().derive_edges(modules, overlay)
    without_overlay, _ = BuildExtension().derive_edges(modules, {})

    assert with_overlay == without_overlay == [('app', 'core')]
