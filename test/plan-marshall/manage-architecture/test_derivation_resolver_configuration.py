#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the machine-local resolver-activation binding at the graph seam.

The ``derivation_resolvers`` section decides which DISCOVERED resolvers are
actually dispatched. These tests drive the real ``get_module_graph`` path — not
the store API in isolation — because the property that matters is what the graph
query *produces*, and a binding that reads correctly while failing to gate (or
gating too hard) is exactly the defect a store-only test cannot see.

Three properties are pinned:

* **An unconfigured project derives its edges.** Absent configuration means
  ACTIVE. A design where resolvers ran only once configured would leave every
  fresh checkout with an empty edge set — the zero-edge defect arriving as a
  configuration failure instead of a derivation one, which is the same broken
  outcome one layer up. This is the plan's D3 requirement, asserted here on an
  unconfigured project rather than on the configured path (a test that only
  exercised the configured path would pass against the exact regression the
  deliverable exists to prevent).
* **A disabled resolver is REPORTED, never silently pruned.** It stays on the
  per-resolver report with ``edge_count: 0`` and a ``configuration:`` note, so
  "switched off by the operator" stays distinguishable from "never registered" —
  the anti-vacuity property the whole seam is built on.
* **Every read failure fails OPEN.** An unreadable store leaves every resolver
  dispatched, because a store problem blanking the graph is the same zero-edge
  outcome the default exists to prevent.

Resolvers are injected by monkeypatching ``extension_discovery``, matching
``test_graph_resolver_provenance.py`` — the seam's deferred import does a fresh
attribute lookup at every call.
"""

import sys
import tempfile

import extension_discovery
import pytest
import run_config

from conftest import load_script_module

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')
_cmd_client_query = sys.modules['_cmd_client_query']

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
get_module_graph = _cmd_client.get_module_graph


# =============================================================================
# Fixtures
# =============================================================================


def _module(name: str) -> dict:
    """A module with no declared internal_dependencies and non-empty dependencies."""
    return {
        'name': name,
        'paths': {'module': name},
        # Non-empty so ``_enriched_dependencies`` short-circuits (no Maven run).
        'dependencies': ['org.example:external:compile'],
        'commands': {},
    }


def _seed_triple(tmpdir: str) -> None:
    """Three modules with NO declared edges — every edge must come from a resolver."""
    modules = {name: _module(name) for name in ('api', 'core', 'app')}
    save_project_meta(
        {
            'name': 'resolver-config-fixture',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {name: {} for name in modules},
        },
        tmpdir,
    )
    for name, data in modules.items():
        save_module_derived(name, data, tmpdir)


class _StubResolver:
    """A resolver returning canned ``(edges, notes)``."""

    def __init__(self, resolver_id: str, edges=None):
        self.resolver_id = resolver_id
        self._edges = edges or []

    def derivation_resolver_id(self) -> str:
        return self.resolver_id

    def derive_edges(self, derived_by_name, enriched_by_name):
        return self._edges, []


def _register(monkeypatch, *resolvers: _StubResolver) -> None:
    records = [
        {'origin': f'stub-{r.resolver_id}', 'id': r.resolver_id, 'module': r} for r in resolvers
    ]
    monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: records)


@pytest.fixture
def two_resolvers(monkeypatch):
    """Two resolvers, each deriving one distinct edge."""
    _register(
        monkeypatch,
        _StubResolver('alpha', [('app', 'core')]),
        _StubResolver('beta', [('core', 'api')]),
    )


def _report_by_id(result: dict) -> dict:
    return {report['id']: report for report in result['resolvers']}


# =============================================================================
# 1. The default — an unconfigured project derives its edges (D3)
# =============================================================================


def test_unconfigured_project_still_derives_edges(plan_context, two_resolvers):
    """⛔ The D3 regression guard: no configuration, full edge set.

    ``plan_context`` gives a run-configuration store with no
    ``derivation_resolvers`` section at all — the state of every fresh clone.
    """
    assert run_config.read_derivation_resolvers_section() == {}

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        result = get_module_graph(tmpdir)

    assert result['resolver_count'] == 2
    assert result['graph']['edge_count'] == 2
    # Emitted edges run dependency -> dependent, so a resolver's ('app', 'core')
    # surfaces as ('core', 'app').
    assert {(e['from'], e['to']) for e in result['edges']} == {('core', 'app'), ('api', 'core')}


def test_unconfigured_resolvers_are_all_reported_as_having_run(plan_context, two_resolvers):
    """Both resolvers report real work, not a suppressed zero."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        result = get_module_graph(tmpdir)

    reports = _report_by_id(result)
    assert reports['alpha']['edge_count'] == 1
    assert reports['beta']['edge_count'] == 1
    assert reports['alpha']['notes'] == []
    assert reports['beta']['notes'] == []


def test_configuring_one_resolver_does_not_deactivate_the_others(plan_context, two_resolvers):
    """Writing the section is not an allow-list — unlisted resolvers stay active.

    The plausible misreading of a config section is "now only what is listed
    runs". Disabling ``alpha`` must leave ``beta`` deriving.
    """
    run_config.cmd_derivation_resolver_set(
        _ns(resolver='alpha', enabled=False, disabled=True)
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        result = get_module_graph(tmpdir)

    assert {(e['from'], e['to']) for e in result['edges']} == {('api', 'core')}


# =============================================================================
# 2. Disabling actually gates the dispatch
# =============================================================================


def test_disabled_resolver_contributes_no_edges(plan_context, two_resolvers):
    run_config.cmd_derivation_resolver_set(_ns(resolver='beta', enabled=False, disabled=True))

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        result = get_module_graph(tmpdir)

    assert {(e['from'], e['to']) for e in result['edges']} == {('core', 'app')}
    assert all('beta' not in edge['producers'] for edge in result['edges'])


def test_disabling_every_resolver_yields_no_edges_but_a_full_report(plan_context, two_resolvers):
    """The empty graph still explains itself — this is not the zero-resolver state.

    ``resolver_count: 0`` means no resolver ran. Here two ran-or-were-considered,
    so the count stays 2 and the notes say why the edges are absent.
    """
    for resolver_id in ('alpha', 'beta'):
        run_config.cmd_derivation_resolver_set(_ns(resolver=resolver_id, enabled=False, disabled=True))

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        result = get_module_graph(tmpdir)

    assert result['edges'] == []
    assert result['resolver_count'] == 2
    for report in result['resolvers']:
        assert report['notes'], report['id']


# =============================================================================
# 3. A disabled resolver is reported, never pruned
# =============================================================================


def test_disabled_resolver_stays_on_the_report(plan_context, two_resolvers):
    run_config.cmd_derivation_resolver_set(_ns(resolver='beta', enabled=False, disabled=True))

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        result = get_module_graph(tmpdir)

    reports = _report_by_id(result)
    assert set(reports) == {'alpha', 'beta'}
    assert reports['beta']['edge_count'] == 0
    assert reports['beta']['status'] == 'ok'


def test_disabled_report_carries_a_configuration_note(plan_context, two_resolvers):
    """The note names CONFIGURATION as the cause, distinct from a merge-side drop.

    Without it, a reader cannot tell an operator's decision from a resolver that
    ran and legitimately found nothing.
    """
    run_config.cmd_derivation_resolver_set(_ns(resolver='beta', enabled=False, disabled=True))

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        result = get_module_graph(tmpdir)

    notes = _report_by_id(result)['beta']['notes']
    assert len(notes) == 1
    assert notes[0].startswith('configuration: ')
    assert 'derivation_resolvers' in notes[0]


def test_report_order_is_stable_when_a_resolver_is_disabled(plan_context, two_resolvers):
    """A disabled resolver lands where it would have run, keeping output byte-stable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        baseline = [report['id'] for report in get_module_graph(tmpdir)['resolvers']]

    run_config.cmd_derivation_resolver_set(_ns(resolver='alpha', enabled=False, disabled=True))

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        gated = [report['id'] for report in get_module_graph(tmpdir)['resolvers']]

    assert gated == baseline == ['alpha', 'beta']


# =============================================================================
# 4. Fail-open
# =============================================================================


def test_unreadable_store_leaves_every_resolver_dispatched(plan_context, two_resolvers, monkeypatch):
    """A raising store read must not blank the graph."""

    def _boom() -> dict:
        raise OSError('store unreadable')

    monkeypatch.setattr(run_config, 'read_derivation_resolvers_section', _boom)

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        result = get_module_graph(tmpdir)

    assert result['graph']['edge_count'] == 2


def test_raising_enabled_check_treats_the_resolver_as_active(plan_context, two_resolvers, monkeypatch):
    """A per-resolver read failure fails open for that resolver, not against it."""

    def _boom(resolver_id: str, section=None) -> bool:
        raise ValueError('bad entry')

    monkeypatch.setattr(run_config, 'is_derivation_resolver_enabled', _boom)

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        result = get_module_graph(tmpdir)

    assert result['graph']['edge_count'] == 2


# =============================================================================
# Helper
# =============================================================================


def _ns(**kwargs):
    from argparse import Namespace

    return Namespace(**kwargs)
