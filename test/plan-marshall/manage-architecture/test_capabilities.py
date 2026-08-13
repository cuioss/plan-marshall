#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the ``capabilities`` reader (D2).

The capability report answers, for the EXECUTING envelope, which query
capabilities the substrate can answer right now — and it distinguishes *cannot
derive* (no producer ran) from *derived nothing* (a producer ran and found
none). It is the query-surface-wide counterpart to the per-verb
``resolver_count`` / ``attributor_count`` discriminators.

The properties pinned here:

* **cannot-derive vs derived-nothing vs derived-N** — the three states stay
  distinct on the ``module_edges`` capability: ``not_derivable``
  (producer_count 0), ``derivable`` with ``derived_count 0``, and ``derivable``
  with ``derived_count N``.
* **actual grant, not the declaration** — the report reads the resolvers that
  actually RAN (monkeypatched here exactly as the graph seam is), never a
  registered-but-unrun class.
* **envelope-scoped** — the same call against two different project dirs answers
  for each independently, which is the property that makes the report correct in
  a dispatched leaf rather than only in the orchestrator.
* **content-search availability** tracks whether the crawl produced an inventory.
"""

import tempfile
from argparse import Namespace

import extension_discovery
import pytest

from conftest import load_script_module

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
cmd_capabilities = _cmd_client.cmd_capabilities


class _StubResolver:
    """A derivation resolver returning canned ``(edges, notes)``."""

    def __init__(self, resolver_id: str, edges=None):
        self.resolver_id = resolver_id
        self._edges = edges or []

    def derivation_resolver_id(self) -> str:
        return self.resolver_id

    def derive_edges(self, derived_by_name, enriched_by_name):
        return self._edges, []


def _register_resolvers(monkeypatch, *resolvers: _StubResolver) -> None:
    records = [
        {'origin': f'stub-{r.resolver_id}', 'id': r.resolver_id, 'module': r} for r in resolvers
    ]
    monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: records)


@pytest.fixture(autouse=True)
def _controlled_producers(monkeypatch):
    """Default every test to an EMPTY producer environment.

    No resolver and no attributor unless a test registers one, so the
    marketplace tree on the test path cannot leak a real producer into an
    assertion. Individual tests override the resolver seam via
    :func:`_register_resolvers`.
    """
    monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: [])
    monkeypatch.setattr(extension_discovery, 'discover_path_attributors', lambda: [])


def _seed(tmpdir: str, modules: dict[str, dict]) -> None:
    save_project_meta(
        {
            'name': 'cap-fixture',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {name: {} for name in modules},
        },
        tmpdir,
    )
    for name, data in modules.items():
        save_module_derived(name, data, tmpdir)


def _module(name: str, **extra) -> dict:
    """A module with no declared edges and a non-empty dependency list.

    The non-empty ``dependencies`` short-circuits the lazy Maven enrichment so
    no subprocess runs; the absent ``internal_dependencies`` keeps the declared
    precedence from shadowing an injected resolver.
    """
    data = {
        'name': name,
        'paths': {'module': name},
        'dependencies': ['org.example:external:compile'],
        'commands': {},
    }
    data.update(extra)
    return data


def _capabilities(tmpdir: str) -> dict:
    result: dict = cmd_capabilities(Namespace(project_dir=tmpdir))
    return result


def _cap(result: dict, name: str) -> dict:
    entry: dict = next(item for item in result['capabilities'] if item['capability'] == name)
    return entry


def test_empty_envelope_reports_no_capabilities_not_false_ones():
    """An envelope with no architecture data reports every capability as absent.

    The crawl-based readers treat a greenfield/empty project as an empty module
    set (not an error), so the capability report answers truthfully: nothing is
    derivable or available here — never a false positive on an envelope that
    carries no substrate.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        result = _capabilities(tmpdir)

        assert result['status'] == 'success'
        assert _cap(result, 'module_edges')['status'] == 'not_derivable'
        assert _cap(result, 'path_attribution')['status'] == 'not_derivable'
        assert _cap(result, 'content_search')['status'] == 'unavailable'


def test_report_lists_the_three_capabilities_with_producer_evidence():
    """The report names exactly the three capabilities, each with producer evidence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, {'struct-a': _module('struct-a')})

        result = _capabilities(tmpdir)

        assert result['status'] == 'success'
        assert result['project_dir'] == tmpdir
        assert [entry['capability'] for entry in result['capabilities']] == [
            'module_edges',
            'path_attribution',
            'content_search',
        ]
        for entry in result['capabilities']:
            assert 'status' in entry
            if 'producer_count' in entry:
                # The producer list and its count can never disagree.
                assert entry['producer_count'] == len(entry['producers'])


def test_module_edges_not_derivable_when_no_resolver_ran():
    """No resolver ran → ``not_derivable`` with ``producer_count: 0`` (an absence)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, {'noedge-a': _module('noedge-a'), 'noedge-b': _module('noedge-b')})

        edges = _cap(_capabilities(tmpdir), 'module_edges')

        assert edges['status'] == 'not_derivable'
        assert edges['producer_count'] == 0
        assert edges['producers'] == []


def test_module_edges_derivable_but_empty_is_distinct_from_not_derivable(monkeypatch):
    """A resolver that ran and found nothing is ``derivable`` — NOT ``not_derivable``.

    This is the whole point of the deliverable: the empty edge set from "no
    resolver ran" and the empty edge set from "a resolver ran and found none" are
    different facts, and the report says which.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, {'empty-a': _module('empty-a'), 'empty-b': _module('empty-b')})
        _register_resolvers(monkeypatch, _StubResolver('maven', edges=[]))

        edges = _cap(_capabilities(tmpdir), 'module_edges')

        assert edges['status'] == 'derivable'
        assert edges['producer_count'] == 1
        assert edges['producers'] == ['maven']
        assert edges['derived_count'] == 0


def test_module_edges_derivable_with_edges_reports_the_count(monkeypatch):
    """A resolver that produced edges is ``derivable`` with a non-zero ``derived_count``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, {'app': _module('app'), 'core': _module('core')})
        _register_resolvers(monkeypatch, _StubResolver('maven', edges=[('app', 'core')]))

        edges = _cap(_capabilities(tmpdir), 'module_edges')

        assert edges['status'] == 'derivable'
        assert edges['producer_count'] == 1
        assert edges['derived_count'] == 1


def test_path_attribution_not_derivable_when_no_attributor_ran():
    """No attributor ran → ``path_attribution`` is ``not_derivable``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, {'pa-a': _module('pa-a')})

        pa = _cap(_capabilities(tmpdir), 'path_attribution')

        assert pa['status'] == 'not_derivable'
        assert pa['producer_count'] == 0


def test_content_search_available_when_inventory_present():
    """A module carrying a non-empty inventory makes content search ``available``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, {'inv-a': _module('inv-a', files={'source': ['inv-a/x.py']})})

        cs = _cap(_capabilities(tmpdir), 'content_search')

        assert cs['status'] == 'available'
        assert cs['modules_inventoried'] == 1


def test_content_search_unavailable_when_no_inventory():
    """No module carries an inventory → content search is ``unavailable``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, {'bare-a': _module('bare-a'), 'bare-b': _module('bare-b')})

        cs = _cap(_capabilities(tmpdir), 'content_search')

        assert cs['status'] == 'unavailable'
        assert cs['modules_inventoried'] == 0


def test_downstream_exception_returns_structured_error_not_a_crash(monkeypatch):
    """An unexpected exception from a downstream reader yields a structured error.

    ``cmd_capabilities`` runs its whole evaluation under one error boundary, so a
    failure in ``get_module_graph`` / ``resolve_path_attribution`` returns
    ``{'status': 'error', ...}`` rather than propagating an uncaught exception —
    the same fail-closed contract the other handlers in the file honour. Here the
    attributor discovery raises a non-ImportError, which reaches the handler
    directly through ``resolve_path_attribution``.
    """

    def _boom():
        raise RuntimeError('attributor discovery blew up')

    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, {'err-a': _module('err-a')})
        monkeypatch.setattr(extension_discovery, 'discover_path_attributors', _boom)

        result = _capabilities(tmpdir)

        assert result['status'] == 'error'
        assert 'capabilities' not in result


def test_report_is_envelope_scoped_to_project_dir():
    """The same call against two envelopes answers for each independently.

    This is the property the deliverable is verified on: a report correct in the
    orchestrator and wrong in a leaf has failed. Two project dirs with different
    inventories must produce different answers from the identical invocation.
    """
    with tempfile.TemporaryDirectory() as with_inv, tempfile.TemporaryDirectory() as without_inv:
        _seed(with_inv, {'es-a': _module('es-a', files={'source': ['es-a/x.py']})})
        _seed(without_inv, {'es-b': _module('es-b')})

        cs_with = _cap(_capabilities(with_inv), 'content_search')
        cs_without = _cap(_capabilities(without_inv), 'content_search')

        assert cs_with['status'] == 'available'
        assert cs_without['status'] == 'unavailable'
