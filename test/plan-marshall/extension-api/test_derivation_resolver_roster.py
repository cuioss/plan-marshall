#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the resolver roster behind the configuration menu.

``extension_api.list_derivation_resolvers()`` joins three surfaces the menu
needs and cannot obtain from any one of them alone: the DISCOVERED resolvers
(``discover_derivation_resolvers``), the machine-local activation binding
(``run_config``), and each resolver's own declared file patterns
(``derivation_file_patterns``).

The properties pinned here:

* **The roster is not pruned by the binding.** A disabled resolver must still be
  listed, or the menu has no way to offer re-enabling it.
* **``enabled`` and ``configured`` stay distinct.** "Active because nobody
  changed it" and "active on purpose" are different facts, and collapsing them
  would hide which resolvers the operator has actually decided about.
* **The round-trip persists** — the plan's D1 is verified by changing a binding
  and re-reading it through the roster, not by the menu rendering.
* **File patterns come from the resolver**, so a menu can never carry a
  transcribed list that outlives the resolver it describes.
* **Every failure degrades to a truthful answer**, never to an error or an
  invented one.

Resolvers are injected by monkeypatching ``extension_discovery``, matching the
seam's own tests — the deferred import does a fresh attribute lookup per call.

⚠ The patch target is resolved from ``sys.modules`` at patch time, NOT captured
by a module-level ``import``. A sibling test in this directory loads
``extension_discovery.py`` through ``load_script_module``, which re-registers a
FRESH module object in ``sys.modules``; a reference captured at collection time
is then stale, and patching it silently does nothing. These tests passed in
isolation and failed in the full suite until the lookup was deferred.
"""

import importlib
import json

import extension_api
import pytest
import run_config
from conftest import parse_ns


def _live(module_name: str):
    """Return the module object currently registered under *module_name*.

    ``import_module`` rather than a bare ``sys.modules`` lookup: it returns the
    live object when one is registered, and imports it when this file is the
    first to need it, so the helper works both in a full-suite sweep and when
    the file is run alone.
    """
    return importlib.import_module(module_name)


class _StubResolver:
    """A resolver declaring an id and a file domain."""

    def __init__(self, resolver_id: str, patterns=None):
        self.resolver_id = resolver_id
        self._patterns = patterns if patterns is not None else []

    def derivation_resolver_id(self) -> str:
        return self.resolver_id

    def derive_edges(self, derived_by_name, enriched_by_name):
        return [], []

    def derivation_file_patterns(self) -> list[str]:
        return self._patterns


def _register(monkeypatch, *resolvers: _StubResolver) -> None:
    records = [
        {'origin': f'bundle-{r.resolver_id}', 'id': r.resolver_id, 'module': r} for r in resolvers
    ]
    monkeypatch.setattr(_live('extension_discovery'), 'discover_derivation_resolvers', lambda: records)


@pytest.fixture
def roster(monkeypatch):
    _register(
        monkeypatch,
        _StubResolver('python', ['**/*.py']),
        _StubResolver('markdown', ['**/*.md']),
    )


def _by_id(result: dict) -> dict:
    return {entry['id']: entry for entry in result['resolvers']}


# ---------------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------------


def test_lists_every_discovered_resolver_sorted_by_id(plan_context, roster):
    result = extension_api.list_derivation_resolvers()
    assert result['status'] == 'success'
    assert [entry['id'] for entry in result['resolvers']] == ['markdown', 'python']
    assert result['count'] == 2


def test_reports_origin_and_declared_patterns_from_the_resolver(plan_context, roster):
    """The file domain is read from the resolver, never transcribed into the menu."""
    entries = _by_id(extension_api.list_derivation_resolvers())
    assert entries['python']['file_patterns'] == ['**/*.py']
    assert entries['python']['origin'] == 'bundle-python'
    assert entries['markdown']['file_patterns'] == ['**/*.md']


def test_resolver_declaring_no_patterns_reports_an_empty_list(plan_context, monkeypatch):
    """Not-declared is an empty list, asserting nothing — never a fabricated domain."""
    _register(monkeypatch, _StubResolver('bare'))
    entries = _by_id(extension_api.list_derivation_resolvers())
    assert entries['bare']['file_patterns'] == []


# ---------------------------------------------------------------------------
# The join against the binding
# ---------------------------------------------------------------------------


def test_unconfigured_resolvers_are_enabled_but_not_configured(plan_context, roster):
    """The default state: active, and visibly untouched by the operator."""
    result = extension_api.list_derivation_resolvers()
    for entry in result['resolvers']:
        assert entry['enabled'] is True, entry['id']
        assert entry['configured'] is False, entry['id']
    assert result['enabled_count'] == 2


def test_disabled_resolver_stays_in_the_roster(plan_context, roster):
    """⛔ Pruning it would leave the menu unable to offer re-enabling it."""
    run_config.cmd_derivation_resolver_set(parse_ns('plan-marshall', 'manage-run-config', 'run_config.py', 'derivation-resolver', 'set', '--resolver', 'python', '--disabled'))

    result = extension_api.list_derivation_resolvers()
    assert [entry['id'] for entry in result['resolvers']] == ['markdown', 'python']
    assert _by_id(result)['python']['enabled'] is False
    assert result['enabled_count'] == 1


def test_explicitly_enabled_resolver_is_marked_configured(plan_context, roster):
    """Enabled-by-default and enabled-on-purpose stay distinguishable."""
    run_config.cmd_derivation_resolver_set(parse_ns('plan-marshall', 'manage-run-config', 'run_config.py', 'derivation-resolver', 'set', '--resolver', 'python', '--enabled'))

    entries = _by_id(extension_api.list_derivation_resolvers())
    assert entries['python']['enabled'] is True
    assert entries['python']['configured'] is True
    assert entries['markdown']['enabled'] is True
    assert entries['markdown']['configured'] is False


# ---------------------------------------------------------------------------
# The D1 round-trip: change a binding, re-read, confirm it persisted
# ---------------------------------------------------------------------------


def test_binding_change_round_trips_through_the_roster(plan_context, roster):
    assert _by_id(extension_api.list_derivation_resolvers())['python']['enabled'] is True

    run_config.cmd_derivation_resolver_set(parse_ns('plan-marshall', 'manage-run-config', 'run_config.py', 'derivation-resolver', 'set', '--resolver', 'python', '--disabled'))
    assert _by_id(extension_api.list_derivation_resolvers())['python']['enabled'] is False

    run_config.cmd_derivation_resolver_set(parse_ns('plan-marshall', 'manage-run-config', 'run_config.py', 'derivation-resolver', 'set', '--resolver', 'python', '--enabled'))
    assert _by_id(extension_api.list_derivation_resolvers())['python']['enabled'] is True

    run_config.cmd_derivation_resolver_remove(parse_ns('plan-marshall', 'manage-run-config', 'run_config.py', 'derivation-resolver', 'remove', '--resolver', 'python'))
    entry = _by_id(extension_api.list_derivation_resolvers())['python']
    assert entry['enabled'] is True
    assert entry['configured'] is False


def test_round_trip_persists_to_the_machine_local_store(plan_context, roster):
    """The round-trip goes through the file, not through in-process state."""
    run_config.cmd_derivation_resolver_set(parse_ns('plan-marshall', 'manage-run-config', 'run_config.py', 'derivation-resolver', 'set', '--resolver', 'markdown', '--disabled'))

    config = run_config.read_run_config(run_config.get_run_config_path())
    assert config['derivation_resolvers'] == {'markdown': {'enabled': False}}
    assert _by_id(extension_api.list_derivation_resolvers())['markdown']['enabled'] is False


# ---------------------------------------------------------------------------
# Degradation — a truthful answer, never an error or an invented one
# ---------------------------------------------------------------------------


def test_zero_discovered_resolvers_is_a_success_with_an_empty_roster(plan_context, monkeypatch):
    monkeypatch.setattr(_live('extension_discovery'), 'discover_derivation_resolvers', lambda: [])
    result = extension_api.list_derivation_resolvers()
    assert result['status'] == 'success'
    assert result['resolvers'] == []
    assert result['count'] == 0
    assert result['enabled_count'] == 0


def test_raising_discovery_degrades_to_an_empty_roster(plan_context, monkeypatch):
    def _boom():
        raise RuntimeError('discovery exploded')

    monkeypatch.setattr(_live('extension_discovery'), 'discover_derivation_resolvers', _boom)
    result = extension_api.list_derivation_resolvers()
    assert result['status'] == 'success'
    assert result['count'] == 0


def test_raising_pattern_accessor_degrades_to_no_patterns(plan_context, monkeypatch):
    """A broken resolver costs its patterns, not the whole roster."""

    class _RaisingPatterns(_StubResolver):
        def derivation_file_patterns(self) -> list[str]:
            raise ValueError('bad declaration')

    _register(monkeypatch, _RaisingPatterns('broken'), _StubResolver('fine', ['**/*.py']))
    entries = _by_id(extension_api.list_derivation_resolvers())
    assert entries['broken']['file_patterns'] == []
    assert entries['fine']['file_patterns'] == ['**/*.py']


def test_raising_enabled_check_treats_the_resolver_as_active(plan_context, roster, monkeypatch):
    """A per-resolver read failure costs that resolver's state, not the roster.

    The seam's gate guards each resolver individually; the roster must too, or a
    single malformed entry would raise out of the read the menu depends on.
    """

    def _boom(resolver_id: str, section=None) -> bool:
        raise ValueError('bad entry')

    monkeypatch.setattr(_live('run_config'), 'is_derivation_resolver_enabled', _boom)

    result = extension_api.list_derivation_resolvers()
    assert result['count'] == 2
    assert result['enabled_count'] == 2


def test_unreadable_store_reports_every_resolver_enabled(plan_context, roster, monkeypatch):
    """Fail-open, matching the seam's gate: a store problem never reads as disabled."""

    def _boom() -> dict:
        raise OSError('store unreadable')

    monkeypatch.setattr(_live('run_config'), 'read_derivation_resolvers_section', _boom)

    result = extension_api.list_derivation_resolvers()
    assert result['enabled_count'] == 2
    for entry in result['resolvers']:
        assert entry['enabled'] is True
        assert entry['configured'] is False


# ---------------------------------------------------------------------------
# CLI boundary
# ---------------------------------------------------------------------------


def test_cli_verb_dispatches_to_the_roster(plan_context, roster):
    result = extension_api.cmd_derivation_resolvers_list(parse_ns('plan-marshall', 'manage-run-config', 'run_config.py', 'derivation-resolver', 'list'))
    assert result['status'] == 'success'
    assert [entry['id'] for entry in result['resolvers']] == ['markdown', 'python']


# ---------------------------------------------------------------------------
# One store, one meaning of `configured`
# ---------------------------------------------------------------------------


MALFORMED_ENTRY = 'yes'
"""A non-dict entry — the shape the two readers used to disagree about."""


def _write_malformed_entry(resolver_id: str = 'markdown') -> None:
    """Put a non-dict entry into the store, bypassing the `set` verb's validation."""
    live = _live('run_config')
    path = live.get_run_config_path()
    config = live.read_run_config(path)
    config['derivation_resolvers'] = {resolver_id: MALFORMED_ENTRY}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config), encoding='utf-8')


def test_a_non_dict_entry_is_not_configured_in_the_roster(plan_context, roster):
    """Key presence is not configuration: the menu renders this as "deliberately set"."""
    _write_malformed_entry()

    assert _by_id(extension_api.list_derivation_resolvers())['markdown']['configured'] is False


def test_both_readers_agree_on_a_non_dict_entry(plan_context, roster):
    """The defect was the DISAGREEMENT, so the guard compares the two answers.

    Asserting a value on one side alone would pass against the shipped code,
    which was self-consistent on each side and contradictory across them: the
    roster reported `configured: true` for `{"markdown": "yes"}` while
    `derivation-resolver get --resolver markdown` reported `configured: false`,
    and the menu document instructs the agent to render that field as the
    distinction between "left at the default" and "deliberately set".
    """
    _write_malformed_entry()

    roster_says = _by_id(extension_api.list_derivation_resolvers())['markdown']['configured']
    store_says = _live('run_config').cmd_derivation_resolver_get(
        parse_ns('plan-marshall', 'manage-run-config', 'run_config.py',
                 'derivation-resolver', 'get', '--resolver', 'markdown')
    )['configured']

    assert roster_says == store_says
    assert roster_says is False  # positively, not merely "they match"


def test_both_readers_agree_on_a_well_formed_entry(plan_context, roster):
    """The control: agreement must not have been bought by reporting False always."""
    run_config.cmd_derivation_resolver_set(parse_ns('plan-marshall', 'manage-run-config', 'run_config.py', 'derivation-resolver', 'set', '--resolver', 'markdown', '--enabled'))

    roster_says = _by_id(extension_api.list_derivation_resolvers())['markdown']['configured']
    store_says = _live('run_config').cmd_derivation_resolver_get(
        parse_ns('plan-marshall', 'manage-run-config', 'run_config.py',
                 'derivation-resolver', 'get', '--resolver', 'markdown')
    )['configured']

    assert roster_says == store_says
    assert roster_says is True


def test_a_malformed_entry_still_fails_open_on_enabled(plan_context, roster):
    """Tightening `configured` must not have tightened `enabled` — that fails OPEN."""
    _write_malformed_entry()

    assert _by_id(extension_api.list_derivation_resolvers())['markdown']['enabled'] is True
