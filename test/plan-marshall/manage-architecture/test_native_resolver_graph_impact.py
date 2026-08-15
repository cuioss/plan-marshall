#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end: native Python / npm resolvers through the real graph and impact verbs.

The per-resolver unit tests pin each join in isolation. This module pins the
thing a consumer actually gets: a real multi-module Python project and a real
multi-package npm workspace, COPIED INTO A TEMP PROJECT ROOT and then queried
through the real ``graph`` and ``impact`` verbs with the real resolvers
registered — so the live worktree crawl performs the discovery, exactly as it
does for a consumer running ``architecture graph``.

**Impact is asserted SEPARATELY from edges, deliberately.** A resolver can emit
edges the traversal cannot consume — an edge whose endpoints do not match the
module keys the reverse-dependency closure walks, for instance — and that failure
mode presents as a non-empty edge list beside an empty impact set. Asserting only
the edge count would report success while every impact query stayed vacuous, so
each ecosystem asserts both, and the impact assertions name the expected
dependents rather than merely checking for non-emptiness.

The fixture is copied rather than seeded through ``save_module_derived`` on
purpose. That writer is a snapshot-fixture seam whose per-module directory is
named after the module, so a scoped npm package (``@sample/core``) nests into two
directories and the synthetic-project fallback that reads those directories back
never finds it — an npm workspace seeded that way silently loses every scoped
member before any resolver is consulted. Copying the tree exercises the
production path instead, where the crawl discovers modules directly and a ``/``
in a package name is not a filesystem question at all.

The Maven lazy-enrich seam is neutralised: a module with an empty
``dependencies`` list (the Python fixture's descriptor-less ``toolbox``) would
otherwise send the caller down ``enrich_maven_module``, which shells out to
Maven. Returning ``None`` is exactly what that seam does on a host without Maven,
so the rest of the real derivation path is exercised unchanged while the test
stays hermetic.
"""

import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import extension_discovery
import pytest

from conftest import load_script_module

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')
# _cmd_client.py's own `from _cmd_client_query import ...` registers the fresh
# instance in sys.modules — fetching it there guarantees the SAME module object
# whose globals the derivation helpers actually close over.
_cmd_client_query = sys.modules['_cmd_client_query']

_pyproject_extension = load_script_module(
    'plan-marshall', 'build-pyproject', 'extension.py', '_pyproject_extension_e2e'
)
_npm_extension = load_script_module('plan-marshall', 'build-npm', 'extension.py', '_npm_extension_e2e')

invalidate_crawl_cache = _architecture_core.invalidate_crawl_cache
get_module_graph = _cmd_client.get_module_graph
get_module_impact = _cmd_client.get_module_impact

TEST_ROOT = Path(__file__).parent.parent
PYTHON_FIXTURE = TEST_ROOT / 'build-pyproject' / 'fixtures' / 'multi-module-python'
NPM_FIXTURE = TEST_ROOT / 'build-npm' / 'fixtures' / 'workspace-monorepo'


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def _no_maven_enrich(monkeypatch):
    """Neutralise the Maven lazy-enrich seam (see the module docstring)."""
    monkeypatch.setattr(
        _cmd_client_query, '_enrich_maven_module_cached', lambda name, derived, project_dir: None
    )


@pytest.fixture(autouse=True)
def _native_resolvers(monkeypatch):
    """Register the REAL pyproject and npm resolvers on the discovery seam.

    The seam's deferred ``from extension_discovery import
    discover_derivation_resolvers`` does a fresh attribute lookup at every call,
    so patching the module attribute is sufficient. The resolver objects are the
    production classes, not stubs — this module's whole point is that the shipped
    joins reach the shipped traversal.

    Registering exactly these two also makes the provenance assertions below
    meaningful: any other resolver contributing an edge would show up as a
    producer the tests do not expect.
    """
    records = [
        {'origin': 'build-npm', 'id': 'npm', 'module': _npm_extension.BuildExtension()},
        {'origin': 'build-pyproject', 'id': 'pyproject', 'module': _pyproject_extension.BuildExtension()},
    ]
    monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: records)


@contextmanager
def _project_from(fixture: Path):
    """Yield a temp project root holding a copy of ``fixture``.

    The crawl memoises per resolved project root, so the memo is dropped on both
    entry and exit: a stale entry from an earlier temp directory whose path the
    OS happened to reuse would otherwise answer this test's queries.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / 'project'
        shutil.copytree(fixture, root)
        invalidate_crawl_cache(str(root))
        try:
            yield str(root)
        finally:
            invalidate_crawl_cache(str(root))


def python_project():
    """A temp project root holding the multi-module Python fixture."""
    return _project_from(PYTHON_FIXTURE)


def npm_project():
    """A temp project root holding the multi-package npm workspace fixture."""
    return _project_from(NPM_FIXTURE)


# =============================================================================
# Non-vacuity: the fixtures owe their edges to THESE resolvers
# =============================================================================
#
# Every assertion below this section would also pass if the fixtures carried
# declared ``internal_dependencies``, or if some other registered resolver
# happened to derive the same pairs. These two tests remove that reading: with
# the resolver set emptied and nothing else changed, the same fixtures produce
# nothing at all. They are what makes the rest of the module evidence that the
# native joins are load-bearing rather than merely consistent with the outcome.


@pytest.mark.parametrize('project_factory', [python_project, npm_project])
def test_same_fixture_yields_no_edges_when_no_resolver_is_registered(monkeypatch, project_factory):
    monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: [])

    with project_factory() as project:
        result = get_module_graph(project)

        assert result['edges'] == []
        assert result['resolver_count'] == 0


@pytest.mark.parametrize(
    ('project_factory', 'module_name'),
    [(python_project, 'sample_core'), (npm_project, '@sample/core')],
)
def test_same_fixture_yields_no_impact_when_no_resolver_is_registered(
    monkeypatch, project_factory, module_name
):
    monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: [])

    with project_factory() as project:
        impact, resolvers = get_module_impact(module_name, project)

        assert impact == []
        assert resolvers == [], 'zero resolvers must report an EMPTY list — the absence-of-capability state'


# =============================================================================
# Python: edges
# =============================================================================


def test_python_project_yields_non_empty_graph_edges():
    with python_project() as project:
        result = get_module_graph(project)

        assert result['edges'], 'a multi-module Python project produced an empty edge set'
        assert result['graph']['edge_count'] > 0


def test_python_edges_are_stamped_with_the_pyproject_producer():
    """Provenance, not merely presence: the edges must come from THIS resolver.

    An edge carrying ``npm`` would mean the npm join claimed a Python project's
    structure — the misattribution build-system scoping exists to prevent.
    """
    with python_project() as project:
        result = get_module_graph(project)

        assert all('pyproject' in edge['producers'] for edge in result['edges'])
        assert all('npm' not in edge['producers'] for edge in result['edges'])


def test_python_resolver_report_is_present_and_non_vacuous():
    """``resolver_count: N`` with edges is a positive answer, not an absence."""
    with python_project() as project:
        result = get_module_graph(project)

        assert result['resolver_count'] == 2
        reports = {report['id']: report for report in result['resolvers']}
        assert reports['pyproject']['edge_count'] > 0
        assert reports['pyproject']['status'] == 'ok'
        assert reports['npm']['edge_count'] == 0


def test_python_graph_edges_are_the_declared_internal_dependencies():
    """Note the direction: a graph edge runs from the DEPENDENCY to the DEPENDENT.

    ``get_module_graph`` emits edges that way so Kahn's algorithm can layer them,
    which is the reverse of the ``(dependent, dependency)`` pairs a resolver
    returns. Asserting the graph's own convention here is what makes this an
    end-to-end check rather than a restatement of the resolver unit tests.
    """
    with python_project() as project:
        result = get_module_graph(project)

        assert sorted((edge['from'], edge['to']) for edge in result['edges']) == [
            ('sample_api', 'default'),
            ('sample_api', 'sample_cli'),
            ('sample_core', 'default'),
            ('sample_core', 'sample_api'),
            ('sample_core', 'sample_cli'),
        ]


# =============================================================================
# Python: impact — asserted SEPARATELY from edges
# =============================================================================


def test_python_impact_is_non_empty_for_a_depended_upon_module():
    """The failure mode this catches: edges present, impact still empty."""
    with python_project() as project:
        impact, resolvers = get_module_impact('sample_core', project)

        assert impact, 'sample_core has three dependents but impact came back empty'
        assert resolvers, 'an empty resolver report would make the impact answer vacuous'


def test_python_impact_names_every_direct_and_transitive_dependent():
    """``sample_cli -> sample_api -> sample_core`` must close transitively."""
    with python_project() as project:
        impact, _ = get_module_impact('sample_core', project)

        assert impact == ['default', 'sample_api', 'sample_cli']


def test_python_impact_of_an_intermediate_module_excludes_its_own_dependency():
    with python_project() as project:
        impact, _ = get_module_impact('sample_api', project)

        assert impact == ['default', 'sample_cli']
        assert 'sample_core' not in impact


def test_python_impact_of_a_leaf_dependent_is_empty_but_not_vacuous():
    """A real, positive empty answer — nothing depends on the CLI."""
    with python_project() as project:
        impact, resolvers = get_module_impact('sample_cli', project)

        assert impact == []
        assert resolvers, 'the empty impact must still carry the resolver report'


# =============================================================================
# npm: edges
# =============================================================================


def test_npm_workspace_yields_non_empty_graph_edges():
    with npm_project() as project:
        result = get_module_graph(project)

        assert result['edges'], 'a multi-package npm workspace produced an empty edge set'
        assert result['graph']['edge_count'] > 0


def test_npm_edges_are_stamped_with_the_npm_producer():
    with npm_project() as project:
        result = get_module_graph(project)

        assert all('npm' in edge['producers'] for edge in result['edges'])
        assert all('pyproject' not in edge['producers'] for edge in result['edges'])


def test_npm_graph_reaches_scoped_workspace_members():
    """Scoped names are the dominant npm workspace convention.

    A graph that only ever linked unscoped packages would look non-empty while
    missing most of a real workspace, so a scoped endpoint is asserted directly.
    """
    with npm_project() as project:
        result = get_module_graph(project)

        # Graph edges run dependency -> dependent, so @sample/api depending on
        # @sample/core surfaces as ('@sample/core', '@sample/api').
        assert ('@sample/core', '@sample/api') in [
            (edge['from'], edge['to']) for edge in result['edges']
        ]


# =============================================================================
# npm: impact — asserted SEPARATELY from edges
# =============================================================================


def test_npm_impact_is_non_empty_for_a_depended_upon_package():
    """The failure mode this catches: edges present, impact still empty."""
    with npm_project() as project:
        impact, resolvers = get_module_impact('@sample/core', project)

        assert impact, '@sample/core has dependents but impact came back empty'
        assert resolvers, 'an empty resolver report would make the impact answer vacuous'


def test_npm_impact_names_every_workspace_dependent():
    with npm_project() as project:
        impact, _ = get_module_impact('@sample/core', project)

        assert impact == ['@sample/api', '@sample/cli', '@sample/monorepo', 'unnamed']


def test_npm_impact_closes_over_the_intermediate_package():
    """Pinning the intermediate hop keeps a scope-handling regression from
    hiding behind the leaf assertion above."""
    with npm_project() as project:
        impact, _ = get_module_impact('@sample/api', project)

        assert impact == ['@sample/cli']
