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

import importlib
import sys
import tempfile

import pytest
import run_config

from conftest import load_script_module


def _live(module_name: str):
    """Return the module object currently registered under *module_name*.

    Resolved at patch time rather than captured by a module-level ``import``: a
    sibling test elsewhere in the tree loads these scripts through
    ``load_script_module``, which re-registers a FRESH object in ``sys.modules``,
    leaving a collection-time reference stale so that patching it silently does
    nothing.

    ``import_module`` rather than a bare ``sys.modules`` lookup, because this
    file may be the FIRST to need the module: a raw lookup raises ``KeyError``
    when nothing has imported it yet, which is how this test behaves when run
    alone rather than in a full-suite sweep.
    """
    return importlib.import_module(module_name)

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
    monkeypatch.setattr(_live('extension_discovery'), 'discover_derivation_resolvers', lambda: records)


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
    assert reports['alpha']['status'] == 'ok'
    assert reports['beta']['status'] == 'ok'


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


def test_disabling_every_resolver_yields_no_edges_and_a_zero_run_count(plan_context, two_resolvers):
    """Nothing ran, so ``resolver_count`` is 0 — and the report still explains why.

    The count is the anti-vacuity discriminator: ``0`` means no resolver ran.
    Disabling every resolver genuinely means none ran, so counting the disabled
    ones would report an edge-derivation capability this envelope does not have.
    The suppression stays visible in ``resolvers[]`` instead, which is what keeps
    this distinguishable from "no resolver was ever registered".
    """
    for resolver_id in ('alpha', 'beta'):
        run_config.cmd_derivation_resolver_set(_ns(resolver=resolver_id, enabled=False, disabled=True))

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        result = get_module_graph(tmpdir)

    assert result['edges'] == []
    assert result['resolver_count'] == 0
    # Both are still REPORTED — discovered, explained, but not run.
    assert len(result['resolvers']) == 2
    for report in result['resolvers']:
        assert report['status'] == 'not_dispatched', report['id']
        assert report['notes'], report['id']


def test_resolver_count_excludes_only_the_disabled_ones(plan_context, two_resolvers):
    """One disabled, one dispatched: the count is 1 while the roster stays 2."""
    run_config.cmd_derivation_resolver_set(_ns(resolver='beta', enabled=False, disabled=True))

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        result = get_module_graph(tmpdir)

    assert result['resolver_count'] == 1
    assert len(result['resolvers']) == 2
    reports = _report_by_id(result)
    assert reports['alpha']['status'] == 'ok'
    assert reports['beta']['status'] == 'not_dispatched'


def test_capabilities_reports_not_derivable_when_every_resolver_is_disabled(
    plan_context, two_resolvers
):
    """⛔ A registered-but-unrun producer is never reported as a capability.

    Disabling every resolver leaves the envelope genuinely unable to derive
    edges. Reporting ``derivable`` would promise a capability the envelope does
    not have — the precise invariant ``doc/concepts/code-intelligence.adoc``
    states for this report.
    """
    for resolver_id in ('alpha', 'beta'):
        run_config.cmd_derivation_resolver_set(_ns(resolver=resolver_id, enabled=False, disabled=True))

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        report = _cmd_client.cmd_capabilities(_ns(project_dir=tmpdir))

    edges = next(c for c in report['capabilities'] if c['capability'] == 'module_edges')
    assert edges['status'] == 'not_derivable'
    assert edges['producer_count'] == 0
    assert edges['producers'] == []


def test_capabilities_reports_only_dispatched_producers(plan_context, two_resolvers):
    """A disabled resolver is not named as a producer of a capability it never ran for."""
    run_config.cmd_derivation_resolver_set(_ns(resolver='beta', enabled=False, disabled=True))

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        report = _cmd_client.cmd_capabilities(_ns(project_dir=tmpdir))

    edges = next(c for c in report['capabilities'] if c['capability'] == 'module_edges')
    assert edges['status'] == 'derivable'
    assert edges['producers'] == ['alpha']
    assert edges['producer_count'] == 1


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
    assert reports['beta']['status'] == 'not_dispatched'


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


def test_every_report_carries_the_same_key_set(plan_context, two_resolvers):
    """⛔ The report list stays a UNIFORM array, disabled resolvers included.

    The not-dispatched state rides on ``status`` rather than on a separate
    boolean precisely so this holds. The reports are serialized as a uniform
    TOON array, whose header is the UNION of the records' keys: a key present on
    only some records renders as an empty cell on the others, so a boolean would
    print a resolver that DID run as ``dispatched: ""`` next to a sibling row
    reading ``false`` — which reads as "not dispatched", inverting the very fact
    the mechanism exists to carry. It would also float the column's position,
    since the header takes first-occurrence key order over an id-sorted list.
    """
    run_config.cmd_derivation_resolver_set(_ns(resolver='beta', enabled=False, disabled=True))

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        result = get_module_graph(tmpdir)

    key_sets = {frozenset(report) for report in result['resolvers']}
    assert len(key_sets) == 1, f'report records are not uniform: {key_sets}'
    assert key_sets.pop() == {'id', 'edge_count', 'status', 'notes'}


def test_an_errored_resolver_still_counts_as_having_run(plan_context, monkeypatch):
    """``error`` is a resolver that ran and failed — a different fact from never called.

    Only ``not_dispatched`` is excluded from ``resolver_count``; folding ``error``
    in would report "no resolver ran" for an envelope where one ran and broke.
    """

    class _Raising(_StubResolver):
        def derive_edges(self, derived_by_name, enriched_by_name):
            raise RuntimeError('resolver exploded')

    _register(monkeypatch, _Raising('alpha'))

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        result = get_module_graph(tmpdir)

    assert result['resolvers'][0]['status'] == 'error'
    assert result['resolver_count'] == 1


# =============================================================================
# 3b. The rendered surface never credits a resolver that did not run
# =============================================================================


def test_overview_footer_does_not_credit_a_disabled_resolver(plan_context, two_resolvers):
    """The rendered footer names derivers, and a withheld resolver derived nothing.

    Crediting it would be the rendered form of the same false claim
    ``resolver_count`` excludes it to avoid.
    """
    run_config.cmd_derivation_resolver_set(_ns(resolver='beta', enabled=False, disabled=True))

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        rendered = _cmd_client.render_overview(tmpdir)

    assert 'derived by 1 resolver(s) — alpha' in rendered
    assert 'switched off by the machine-local configuration — beta' in rendered


def test_overview_footer_states_the_cause_when_every_resolver_is_disabled(
    plan_context, two_resolvers
):
    """A sparse graph explains itself rather than reading as "nothing depends on anything"."""
    for resolver_id in ('alpha', 'beta'):
        run_config.cmd_derivation_resolver_set(_ns(resolver=resolver_id, enabled=False, disabled=True))

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        rendered = _cmd_client.render_overview(tmpdir)

    assert 'switched off by the machine-local configuration' in rendered
    assert 'No edges were derived' in rendered
    # NOT the "no resolver is registered" wording — two ARE registered.
    assert 'no derivation resolver is registered' not in rendered


# =============================================================================
# 3c. The TOON wire — the shape an agent actually reads
# =============================================================================


def test_mixed_roster_serializes_as_a_uniform_toon_table(plan_context, two_resolvers):
    """⛔ The wire must not encode "did not run" as an empty cell.

    This is the property the ``status``-value design exists for, pinned against
    the REAL serializer rather than against the Python dicts. TOON renders a
    uniform array's header as the UNION of the records' keys, so a marker present
    on only the withheld records would render the resolvers that DID run with an
    empty cell in that column — and an empty cell beside a sibling reading
    ``not_dispatched`` reads as "not dispatched", inverting the fact the marker
    carries. The header order would drift too, since it follows first-occurrence
    over an id-sorted list.

    Encoding the state as a third ``status`` value keeps every record's key set
    identical, so the table is four columns wide whatever the configuration is.
    """
    from toon_parser import serialize_toon

    run_config.cmd_derivation_resolver_set(_ns(resolver='beta', enabled=False, disabled=True))

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        result = get_module_graph(tmpdir)

    rendered = serialize_toon({'resolvers': result['resolvers']})
    header = next(line for line in rendered.splitlines() if line.startswith('resolvers['))

    assert header.startswith('resolvers[2]{id,edge_count,status,notes}'), header
    # No empty cell stands in for "dispatched".
    assert ',,' not in rendered
    assert 'not_dispatched' in rendered


def test_toon_header_is_identical_configured_or_not(plan_context, two_resolvers):
    """The column set does not move when the operator changes the binding.

    An agent parsing by the documented header must not have to re-derive it per
    call — which is what a presence-varying key would have forced.
    """
    from toon_parser import serialize_toon

    def _header() -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            _seed_triple(tmpdir)
            result = get_module_graph(tmpdir)
        rendered = serialize_toon({'resolvers': result['resolvers']})
        return next(line for line in rendered.splitlines() if line.startswith('resolvers['))

    unconfigured = _header()
    run_config.cmd_derivation_resolver_set(_ns(resolver='alpha', enabled=False, disabled=True))
    configured = _header()

    assert unconfigured == configured


# =============================================================================
# 4. Fail-open
# =============================================================================


def test_unreadable_store_leaves_every_resolver_dispatched(plan_context, two_resolvers, monkeypatch):
    """A raising store read must not blank the graph."""

    def _boom() -> dict:
        raise OSError('store unreadable')

    monkeypatch.setattr(_live('run_config'), 'read_derivation_resolvers_section', _boom)

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_triple(tmpdir)
        result = get_module_graph(tmpdir)

    assert result['graph']['edge_count'] == 2


def test_raising_enabled_check_treats_the_resolver_as_active(plan_context, two_resolvers, monkeypatch):
    """A per-resolver read failure fails open for that resolver, not against it."""

    def _boom(resolver_id: str, section=None) -> bool:
        raise ValueError('bad entry')

    monkeypatch.setattr(_live('run_config'), 'is_derivation_resolver_enabled', _boom)

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
