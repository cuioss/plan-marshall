#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``capabilities`` reader (D2).

The capability report answers, for the EXECUTING envelope, which query
capabilities the substrate can answer right now — and it distinguishes *cannot
derive* (no producer ran) from *derived nothing* (a producer ran and found
none). It is the query-surface-wide counterpart to the per-verb
``resolver_count`` / ``attributor_count`` discriminators.

The properties pinned here:

* **cannot-derive vs derived-nothing vs derived-N** — the three states stay
  distinct on the ``module_edges`` capability.
* **One status vocabulary** — all three entries emit exactly ``derivable`` /
  ``not_derivable``, with no per-entry exception.
* **The verdict comes from the FULL producer population** — dispatched resolvers
  PLUS the reserved ``declared`` / ``sibling-cross-link`` producers stamped on
  the returned edges. ``producer_count`` stays resolver-scoped, so ``derivable``
  beside ``producer_count: 0`` is a reachable state rather than a contradiction.
* **actual grant, not the declaration** — the report reads the resolvers that
  actually RAN (monkeypatched here exactly as the graph seam is), never a
  registered-but-unrun class.
* **envelope-scoped** — the same call against two different project dirs answers
  for each independently, which is the property that makes the report correct in
  a dispatched leaf rather than only in the orchestrator.
* **content_search separates never-crawled from crawled-and-file-less** — the
  two states previously returned byte-identical payloads.
* **no memo survives into the answer** — the Axis-D attribution memo is dropped
  at entry, and it is keyed per project so two envelopes are never conflated.
"""

import argparse
import copy
import re
import tempfile
from pathlib import Path
from typing import Any

import extension_discovery
import pytest

from conftest import load_script_module, parse_ns

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')
_cmd_client_handlers = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client_handlers.py', '_cmd_client_handlers'
)

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
resolve_path_attribution = _architecture_core.resolve_path_attribution
invalidate_path_claim_cache = _architecture_core.invalidate_path_claim_cache
cmd_capabilities = _cmd_client.cmd_capabilities

#: The architecture script's address, as module-level string constants so the
#: ``parse_ns`` call below stays statically resolvable.
_ARCH_BUNDLE = 'plan-marshall'
_ARCH_SKILL = 'manage-architecture'
_ARCH_SCRIPT = 'architecture.py'

#: The client contract whose entry-shape table is the authority for the payload
#: key set. Resolved from the loaded module's own location so the test follows
#: the bundle rather than hard-coding a repo-relative path.
_CLIENT_API_MD = Path(_architecture_core.__file__).resolve().parent.parent / 'standards' / 'client-api.md'


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from the hoisted parser-derived base.

    The base supplies every parser default; ``overrides`` names only the fields
    this call differs in. A shallow copy is enough because a namespace's values
    are the parser's own scalars, and the base must stay unmutated for the other
    callers sharing it.
    """
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


#: The ``capabilities`` namespace, built by ``architecture.py``'s OWN parser so
#: it carries every default the production CLI applies — the ``command``
#: discriminator and the ``plan_id`` half of the ``--plan-id``/``--project-dir``
#: pair, neither of which the hand-built namespace carried. Hoisted to module
#: scope because ``parse_ns`` re-executes the script module on every call, and
#: ``register=False`` because only the namespace is wanted here.
_CAPABILITIES_ARGS = parse_ns(
    _ARCH_BUNDLE,
    _ARCH_SKILL,
    _ARCH_SCRIPT,
    '--project-dir',
    '.',
    'capabilities',
    register=False,
)


class _StubResolver:
    """A derivation resolver returning canned ``(edges, notes)``."""

    def __init__(self, resolver_id: str, edges=None):
        self.resolver_id = resolver_id
        self._edges = edges or []

    def derivation_resolver_id(self) -> str:
        return self.resolver_id

    def derive_edges(self, derived_by_name, enriched_by_name):
        return self._edges, []


class _StubAttributor:
    """A path attributor returning a canned ``(claims, notes)`` pair."""

    def __init__(self, attributor_id: str, claims=None):
        self.attributor_id = attributor_id
        self._claims = claims or []

    def path_attributor_id(self) -> str:
        return self.attributor_id

    def claim_paths(self):
        return self._claims, []


class _SequencedAttributor:
    """An attributor whose claim set CHANGES between successive merges.

    The mutation-sensitive input for the memo-key tests: a memo that replays an
    earlier merge returns the FIRST claim set, while a correctly-keyed lookup
    runs the merge again and returns the second. Without a changing input, a
    stale memo and a live re-merge are indistinguishable.
    """

    def __init__(self, attributor_id: str, claim_sequence: list[list[tuple[str, str]]]):
        self.attributor_id = attributor_id
        self._sequence = claim_sequence
        self.calls = 0

    def path_attributor_id(self) -> str:
        return self.attributor_id

    def claim_paths(self):
        index = min(self.calls, len(self._sequence) - 1)
        self.calls += 1
        return self._sequence[index], []


def _records(*producers: Any) -> list[dict[str, Any]]:
    """Wrap stub producers in the ``{origin, id, module}`` discovery record shape."""
    return [
        {
            'origin': f'stub-{getattr(p, "resolver_id", None) or p.attributor_id}',
            'id': getattr(p, 'resolver_id', None) or p.attributor_id,
            'module': p,
        }
        for p in producers
    ]


def _register_resolvers(monkeypatch, *resolvers: _StubResolver) -> None:
    records = _records(*resolvers)
    monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: records)


def _register_attributors(monkeypatch, *attributors: Any) -> None:
    records = _records(*attributors)
    monkeypatch.setattr(extension_discovery, 'discover_path_attributors', lambda: records)


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


@pytest.fixture(autouse=True)
def _clean_attribution_memo():
    """Drop the process-lifetime Axis-D memo around every test.

    The memo outlives a single test, so a claim set merged under one test's
    stub population would otherwise be replayed into the next test's assertion.
    """
    invalidate_path_claim_cache()
    yield
    invalidate_path_claim_cache()


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
    result: dict = cmd_capabilities(_variant(_CAPABILITIES_ARGS, project_dir=tmpdir))
    return result


def _cap(result: dict, name: str) -> dict:
    entry: dict = next(item for item in result['capabilities'] if item['capability'] == name)
    return entry


#: The entry-shape table's header row. Locating the table by its header is what
#: bounds the row walk below to THAT table: the per-field table immediately
#: following it also opens every row with a backtick-quoted lowercase name
#: (``producer_count``, ``edge_producers``), so a document-wide row regex would
#: pull field names into the entry population.
_ENTRY_TABLE_HEADER_RE = re.compile(r'^\|\s*Entry\s*\|\s*Fields\s*\|', re.MULTILINE)


def _documented_entry_fields() -> dict[str, set[str]]:
    """Parse client-api.md's capabilities entry-shape table into ``entry -> fields``.

    BOTH halves are DERIVED from the document — the field sets and the ENTRY
    POPULATION itself. Restating the entry names as a literal tuple made the
    guard silently partial in the direction it exists to catch: a fourth entry
    added to the payload and to the table would never be compared against
    anything, because the test only asked about the three names it already knew.
    The table is the authority for which entries exist, so it is read for that
    too.

    The table's first column is the entry name and its second column is the
    backtick-quoted field list; the walk runs from the header row until the first
    non-table line, so it cannot spill into the per-field table below it.
    """
    text = _CLIENT_API_MD.read_text(encoding='utf-8')
    header = _ENTRY_TABLE_HEADER_RE.search(text)
    assert header is not None, 'client-api.md carries no capabilities entry-shape table'

    documented: dict[str, set[str]] = {}
    # ``[1:]`` drops the remainder of the header line itself; the first row walked
    # is the ``|---|---|`` separator, which carries no backticked name and is
    # skipped by the name match below.
    for line in text[header.end() :].split('\n')[1:]:
        if not line.lstrip().startswith('|'):
            break
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) < 2:
            continue
        name = re.fullmatch(r'`([a-z_]+)`', cells[0])
        if name is None:
            continue
        documented[name.group(1)] = set(re.findall(r'`([a-z_]+)`', cells[1]))

    assert documented, (
        'the capabilities entry-shape table was found but no entry row parsed out of '
        'it, so the population is empty and every comparison against it would hold '
        'vacuously — a parse that read nothing must not present as a clean pass.'
    )
    return documented


def test_empty_envelope_reports_no_capabilities_not_false_ones():
    """An envelope with no architecture data reports every capability as absent.

    The crawl-based readers treat a greenfield/empty project as an empty module
    set (not an error), so the capability report answers truthfully: nothing is
    derivable here — never a false positive on an envelope that carries no
    substrate.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        result = _capabilities(tmpdir)

        assert result['status'] == 'success'
        assert _cap(result, 'module_edges')['status'] == 'not_derivable'
        assert _cap(result, 'path_attribution')['status'] == 'not_derivable'
        assert _cap(result, 'content_search')['status'] == 'not_derivable'


def test_every_entry_uses_the_same_two_status_values():
    """All three entries emit one vocabulary — no entry carries an exception.

    Pins the clean break: ``content_search`` shares ``derivable`` /
    ``not_derivable`` with the two derivation entries, so a consumer branches on
    one pair of literals for every entry it reads.
    """
    with tempfile.TemporaryDirectory() as bare, tempfile.TemporaryDirectory() as inventoried:
        _seed(bare, {'bare-a': _module('bare-a')})
        _seed(inventoried, {'inv-a': _module('inv-a', files={'source': ['inv-a/x.py']})})

        emitted = {
            entry['status']
            for result in (_capabilities(bare), _capabilities(inventoried))
            for entry in result['capabilities']
        }

        assert emitted <= {'derivable', 'not_derivable'}
        # Both members are actually reachable, so the assertion above is not
        # vacuously satisfied by a single-valued population.
        assert emitted == {'derivable', 'not_derivable'}


def test_entry_payload_keys_match_the_documented_entry_shape():
    """Each entry carries exactly the fields client-api.md's table names.

    The documented shape is PARSED, not restated, so the contract and the
    payload cannot drift apart without this test noticing.
    """
    documented = _documented_entry_fields()
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, {'keys-a': _module('keys-a', files={'source': ['keys-a/x.py']})})

        result = _capabilities(tmpdir)

        # The ENTRY SETS are compared before the field sets. With the population
        # derived from the table rather than restated, this is what the
        # derivation buys: an entry documented and never emitted, or emitted and
        # never documented, is now a failure instead of a row nobody looked at.
        assert {entry['capability'] for entry in result['capabilities']} == set(documented)
        for entry in result['capabilities']:
            assert set(entry) == documented[entry['capability']], entry['capability']


def test_module_edges_not_derivable_when_no_producer_reached_the_response():
    """No resolver ran AND no edge reached the graph → ``not_derivable``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, {'noedge-a': _module('noedge-a'), 'noedge-b': _module('noedge-b')})

        edges = _cap(_capabilities(tmpdir), 'module_edges')

        assert edges['status'] == 'not_derivable'
        assert edges['producer_count'] == 0
        assert edges['producers'] == []
        assert edges['edge_producers'] == []
        assert edges['derived_count'] == 0


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


def test_declared_edge_with_no_resolver_is_derivable_not_a_contradiction():
    """A declared edge reaches the graph with no resolver, and the report says so.

    The state the handler's own docstring once enumerated as impossible:
    ``derived_count`` above zero beside ``producer_count: 0``. The verdict is
    computed from the FULL producer population, so the reserved ``declared``
    producer carries it — ``not_derivable`` alongside a derived edge is the
    combination this asserts can no longer be emitted.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(
            tmpdir,
            {
                'app': _module('app', internal_dependencies=['core']),
                'core': _module('core'),
            },
        )

        edges = _cap(_capabilities(tmpdir), 'module_edges')

        assert edges['derived_count'] > 0
        assert edges['status'] == 'derivable'
        # producer_count stays RESOLVER-scoped — widening it would break the
        # feasibility guard that derives "underivable" from resolver_count > 0.
        assert edges['producer_count'] == 0
        assert edges['producers'] == []
        # The evidence the verdict was computed from is published on the payload.
        assert edges['edge_producers'] == ['declared']


def test_path_attribution_not_derivable_when_no_attributor_ran():
    """No attributor ran → ``path_attribution`` is ``not_derivable``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, {'pa-a': _module('pa-a')})

        pa = _cap(_capabilities(tmpdir), 'path_attribution')

        assert pa['status'] == 'not_derivable'
        assert pa['producer_count'] == 0
        assert pa['derived_count'] == 0


def test_path_attribution_derived_count_sums_claims_reported(monkeypatch):
    """``derived_count`` counts CLAIMS REPORTED, not paths attributed.

    Two attributors corroborating one prefix each report that claim, so the sum
    is 2 while only ONE path is attributed. The field is named for the
    population it actually counts rather than the one a reader might assume.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, {'shared': _module('shared')})
        _register_attributors(
            monkeypatch,
            _StubAttributor('attr-a', claims=[('shared/sub', 'shared')]),
            _StubAttributor('attr-b', claims=[('shared/sub', 'shared')]),
        )

        pa = _cap(_capabilities(tmpdir), 'path_attribution')

        assert pa['status'] == 'derivable'
        assert pa['producer_count'] == 2
        # One prefix is claimed; both attributors reported it.
        assert pa['derived_count'] == 2


def test_content_search_derivable_when_inventory_present():
    """A module carrying a non-empty inventory makes content search derivable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, {'inv-a': _module('inv-a', files={'source': ['inv-a/x.py']})})

        cs = _cap(_capabilities(tmpdir), 'content_search')

        assert cs['status'] == 'derivable'
        assert cs['modules_inventoried'] == 1
        assert cs['modules_total'] == 1


def test_content_search_separates_never_crawled_from_crawled_and_file_less():
    """The two zero-inventory states stop returning byte-identical payloads.

    (a) an envelope with no descriptors at all — nothing could be read, so the
    capability is absent; (b) N crawled modules that carry no files — the crawl
    answered, and the answer is empty. ``modules_inventoried: 0`` holds in both,
    so ``status`` is what tells them apart.
    """
    with tempfile.TemporaryDirectory() as no_descriptors, tempfile.TemporaryDirectory() as file_less:
        _seed(file_less, {'bare-a': _module('bare-a'), 'bare-b': _module('bare-b')})

        absent = _cap(_capabilities(no_descriptors), 'content_search')
        empty = _cap(_capabilities(file_less), 'content_search')

        assert absent != empty

        assert absent['status'] == 'not_derivable'
        assert absent['modules_inventoried'] == 0
        assert absent['modules_total'] == 0

        assert empty['status'] == 'derivable'
        assert empty['modules_inventoried'] == 0
        assert empty['modules_total'] == 2


def test_capabilities_reflects_an_attributor_population_changed_mid_process(monkeypatch):
    """A second call in one process re-runs attributor discovery.

    ``cmd_capabilities`` drops the process-lifetime Axis-D memo at entry, so it
    reports the population that exists NOW rather than replaying the one the
    first call happened to see.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, {'pop-a': _module('pop-a')})

        _register_attributors(monkeypatch, _StubAttributor('attr-a'))
        first = _cap(_capabilities(tmpdir), 'path_attribution')

        _register_attributors(monkeypatch, _StubAttributor('attr-a'), _StubAttributor('attr-b'))
        second = _cap(_capabilities(tmpdir), 'path_attribution')

        assert first['producer_count'] == 1
        assert second['producer_count'] == 2
        assert second['producers'] == ['attr-a', 'attr-b']


def test_explicit_memo_clear_is_the_positive_control(monkeypatch):
    """Clearing the memo by hand reaches the same answer the verb reaches itself.

    The matched positive control for the test above: it shows the second answer
    follows from the memo being dropped, not from some other difference between
    the two calls.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, {'ctl-a': _module('ctl-a')})
        module_names = ['ctl-a']

        _register_attributors(monkeypatch, _StubAttributor('attr-a'))
        _owner, first = resolve_path_attribution('ctl-a/x.py', module_names, tmpdir)

        _register_attributors(monkeypatch, _StubAttributor('attr-a'), _StubAttributor('attr-b'))
        invalidate_path_claim_cache()
        _owner, second = resolve_path_attribution('ctl-a/x.py', module_names, tmpdir)

        assert [report['id'] for report in first] == ['attr-a']
        assert [report['id'] for report in second] == ['attr-a', 'attr-b']


def test_attribution_memo_does_not_conflate_two_project_dirs(monkeypatch):
    """Identical module names in two projects get two independent answers.

    The memo is keyed on ``(project_dir, module_names)``. Keyed on the module
    tuple alone, the second project would be served the first project's merged
    claim set — a per-project answer silently becoming a per-module-name-set
    one. The attributor's claim set changes between merges, so a replayed memo
    and a live re-merge are distinguishable.
    """
    with tempfile.TemporaryDirectory() as project_a, tempfile.TemporaryDirectory() as project_b:
        # Identical module names in both projects — the discriminator must be
        # the project dir, since the module tuple cannot tell them apart.
        module_names = ['twin']
        _seed(project_a, {'twin': _module('twin')})
        _seed(project_b, {'twin': _module('twin')})

        _register_attributors(
            monkeypatch,
            _SequencedAttributor('attr-seq', [[('twin/first', 'twin')], [('twin/second', 'twin')]]),
        )

        owner_a, _reports_a = resolve_path_attribution('twin/first', module_names, project_a)
        owner_b_first, _reports = resolve_path_attribution('twin/first', module_names, project_b)
        owner_b_second, _reports = resolve_path_attribution('twin/second', module_names, project_b)

        # Project A saw the first claim set.
        assert owner_a == 'twin'
        # Project B re-merged and saw the SECOND claim set: the first prefix is
        # no longer claimed there, the second one is.
        assert owner_b_first is None
        assert owner_b_second == 'twin'


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

        assert cs_with['status'] == 'derivable'
        assert cs_with['modules_inventoried'] == 1
        assert cs_without['status'] == 'derivable'
        assert cs_without['modules_inventoried'] == 0


def test_module_docstring_points_at_cmd_handler_population_not_a_restated_roster():
    """The module docstring names the ``def cmd_*`` population as the source of
    truth for the handler roster, rather than restating a list or count of its
    own — a restated roster/count drifts silently the moment a handler is added
    without a matching docstring edit, which is exactly the defect this pointer
    replaced. The population itself must be non-empty (there is something for
    the pointer to point at), and the docstring must actually carry the
    pointer language rather than reintroducing a hand-maintained list.
    """
    verbs = sorted(
        name[len('cmd_') :].replace('_', '-') for name in dir(_cmd_client_handlers) if name.startswith('cmd_')
    )
    doc = _cmd_client_handlers.__doc__ or ''

    assert verbs, 'no cmd_* handlers were discovered — the population is empty'
    assert 'def cmd_*' in doc, 'docstring no longer points at the def cmd_* population as the roster source'
    assert 'deliberately not restated' in doc, 'docstring no longer states that the roster is deliberately not restated'
