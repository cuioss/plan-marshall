#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the run_config ``derivation-resolver`` verbs (the resolver-binding surface).

The ``derivation_resolvers`` section decides which discovered derivation
resolvers are dispatched in a checkout. It lives in the machine-local
run-configuration store beside ``language_servers``, keyed on the resolver
**id** — a resolver returns ``(module, module)`` pairs carrying no file
provenance, so there is no dispatch point at which a per-file binding could
apply.

The property that matters most here is the **default**: an unconfigured project
runs every discovered resolver. A default of "off" would leave a fresh checkout
with an empty edge set — the zero-edge defect arriving as a configuration
failure instead of a derivation one — so it is asserted from several directions
rather than once.
"""

import argparse

import run_config

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-run-config', 'run_config.py')


def _set(resolver: str = 'markdown', *, enabled: bool = False, disabled: bool = True) -> argparse.Namespace:
    return argparse.Namespace(resolver=resolver, enabled=enabled, disabled=disabled)


# ---------------------------------------------------------------------------
# The default: absent configuration means ACTIVE
# ---------------------------------------------------------------------------


def test_unconfigured_resolver_is_enabled(plan_context):
    """An id with no entry resolves to enabled — the working default."""
    assert run_config.is_derivation_resolver_enabled('markdown') is True


def test_unconfigured_store_enables_every_resolver(plan_context):
    """With no section at all, every id is active — a fresh clone still derives.

    This is the D3 regression: a design where resolvers only ran once
    configured would blank the graph on every unconfigured project.
    """
    for resolver_id in ('maven', 'npm', 'pyproject', 'markdown', 'python', 'lsp', 'documentation'):
        assert run_config.is_derivation_resolver_enabled(resolver_id) is True, resolver_id


def test_default_constant_is_enabled(plan_context):
    """The default is a named constant, not an inline literal that could drift."""
    assert run_config.DERIVATION_RESOLVER_ENABLED_DEFAULT is True


def test_configuring_one_resolver_leaves_the_others_active(plan_context):
    """Disabling one resolver is not an opt-in switch for the rest.

    Writing the section could plausibly have been read as "now only what is
    listed runs". It is not: every id still absent stays active.
    """
    run_config.cmd_derivation_resolver_set(_set('lsp'))
    assert run_config.is_derivation_resolver_enabled('lsp') is False
    assert run_config.is_derivation_resolver_enabled('markdown') is True
    assert run_config.is_derivation_resolver_enabled('maven') is True


def test_malformed_entry_falls_back_to_enabled(plan_context):
    """A non-dict entry cannot switch a resolver off — reads fail OPEN.

    An unreadable or corrupt store blanking the graph is the same zero-edge
    outcome the default exists to prevent.
    """
    config_path = run_config.get_run_config_path()
    config = run_config.read_run_config(config_path)
    config['derivation_resolvers'] = {'markdown': 'not-a-dict'}
    run_config._write_json_file(config_path, config)
    assert run_config.is_derivation_resolver_enabled('markdown') is True


def test_non_dict_section_falls_back_to_enabled(plan_context):
    """A section of the wrong TYPE is ignored rather than obeyed."""
    config_path = run_config.get_run_config_path()
    config = run_config.read_run_config(config_path)
    config['derivation_resolvers'] = ['markdown']
    run_config._write_json_file(config_path, config)
    assert run_config.read_derivation_resolvers_section() == {}
    assert run_config.is_derivation_resolver_enabled('markdown') is True


def test_entry_without_enabled_key_defaults_to_enabled(plan_context):
    """An entry that exists but says nothing about ``enabled`` stays active."""
    config_path = run_config.get_run_config_path()
    config = run_config.read_run_config(config_path)
    config['derivation_resolvers'] = {'markdown': {}}
    run_config._write_json_file(config_path, config)
    assert run_config.is_derivation_resolver_enabled('markdown') is True


# ---------------------------------------------------------------------------
# Persistence round-trip (D2)
# ---------------------------------------------------------------------------


def test_set_disabled_round_trips(plan_context):
    run_config.cmd_derivation_resolver_set(_set('lsp'))
    got = run_config.cmd_derivation_resolver_get(argparse.Namespace(resolver='lsp'))
    assert got['status'] == 'success'
    assert got['configured'] is True
    assert got['enabled'] is False


def test_set_enabled_round_trips(plan_context):
    run_config.cmd_derivation_resolver_set(_set('lsp'))
    run_config.cmd_derivation_resolver_set(_set('lsp', enabled=True, disabled=False))
    got = run_config.cmd_derivation_resolver_get(argparse.Namespace(resolver='lsp'))
    assert got['configured'] is True
    assert got['enabled'] is True


def test_persists_into_the_keyed_section_beside_language_servers(plan_context):
    """The binding lands in the shared store under its own key, not a new file.

    The plan's D2 requires the existing keyed-section pattern rather than a
    parallel store, so the assertion is on the shape in the SAME file that
    ``language_servers`` occupies.
    """
    run_config.cmd_language_server_set(
        argparse.Namespace(language='python', command='["srv"]', language_id=None, disabled=False)
    )
    run_config.cmd_derivation_resolver_set(_set('lsp'))

    config = run_config.read_run_config(run_config.get_run_config_path())
    assert config['derivation_resolvers'] == {'lsp': {'enabled': False}}
    assert 'python' in config['language_servers']


def test_get_reports_unconfigured_but_enabled(plan_context):
    """``configured`` and ``enabled`` are different questions and stay separate.

    Collapsing them would make "left at the default" indistinguishable from
    "deliberately switched on".
    """
    got = run_config.cmd_derivation_resolver_get(argparse.Namespace(resolver='markdown'))
    assert got['configured'] is False
    assert got['enabled'] is True


def test_list_reports_configured_entries_only(plan_context):
    listed = run_config.cmd_derivation_resolver_list(argparse.Namespace())
    assert listed['resolvers'] == []
    assert listed['count'] == 0
    assert listed['unconfigured_default_enabled'] is True

    run_config.cmd_derivation_resolver_set(_set('lsp'))
    run_config.cmd_derivation_resolver_set(_set('python', enabled=True, disabled=False))
    listed = run_config.cmd_derivation_resolver_list(argparse.Namespace())
    assert listed['resolvers'] == [
        {'id': 'lsp', 'enabled': False},
        {'id': 'python', 'enabled': True},
    ]
    assert listed['count'] == 2


def test_remove_returns_resolver_to_default_active(plan_context):
    run_config.cmd_derivation_resolver_set(_set('lsp'))
    assert run_config.is_derivation_resolver_enabled('lsp') is False

    removed = run_config.cmd_derivation_resolver_remove(argparse.Namespace(resolver='lsp'))
    assert removed['action'] == 'removed'
    assert run_config.is_derivation_resolver_enabled('lsp') is True

    skipped = run_config.cmd_derivation_resolver_remove(argparse.Namespace(resolver='lsp'))
    assert skipped['action'] == 'skipped'


def test_section_snapshot_is_reusable_across_resolvers(plan_context):
    """A pre-read section answers for every id, so callers read the store once."""
    run_config.cmd_derivation_resolver_set(_set('lsp'))
    section = run_config.read_derivation_resolvers_section()
    assert run_config.is_derivation_resolver_enabled('lsp', section) is False
    assert run_config.is_derivation_resolver_enabled('markdown', section) is True


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_set_rejects_both_flags(plan_context):
    result = run_config.cmd_derivation_resolver_set(
        argparse.Namespace(resolver='lsp', enabled=True, disabled=True)
    )
    assert result['status'] == 'error'


def test_set_rejects_neither_flag(plan_context):
    """The verb's value proposition is the flag pair, so the empty case is pinned."""
    result = run_config.cmd_derivation_resolver_set(
        argparse.Namespace(resolver='lsp', enabled=False, disabled=False)
    )
    assert result['status'] == 'error'


def test_rejecting_a_bad_flag_pair_persists_nothing(plan_context):
    result = run_config.cmd_derivation_resolver_set(
        argparse.Namespace(resolver='lsp', enabled=True, disabled=True)
    )
    assert result['status'] == 'error'
    assert run_config.read_derivation_resolvers_section() == {}


# ---------------------------------------------------------------------------
# CLI boundary — the shape the verb exists to support, driven through argparse
# ---------------------------------------------------------------------------


def test_cli_set_disabled(plan_context):
    result = run_script(SCRIPT_PATH, 'derivation-resolver', 'set', '--resolver', 'lsp', '--disabled')
    assert result.success, result.stderr
    data = result.toon()
    assert data.get('status') == 'success'
    assert data.get('action') == 'set'
    assert data.get('enabled') is False


def test_cli_get_reports_effective_state(plan_context):
    run_script(SCRIPT_PATH, 'derivation-resolver', 'set', '--resolver', 'lsp', '--disabled')
    result = run_script(SCRIPT_PATH, 'derivation-resolver', 'get', '--resolver', 'lsp')
    assert result.success, result.stderr
    data = result.toon()
    assert data.get('configured') is True
    assert data.get('enabled') is False


def test_cli_get_unconfigured_is_enabled(plan_context):
    result = run_script(SCRIPT_PATH, 'derivation-resolver', 'get', '--resolver', 'markdown')
    assert result.success, result.stderr
    data = result.toon()
    assert data.get('configured') is False
    assert data.get('enabled') is True


def test_cli_list_and_remove(plan_context):
    run_script(SCRIPT_PATH, 'derivation-resolver', 'set', '--resolver', 'lsp', '--disabled')
    listed = run_script(SCRIPT_PATH, 'derivation-resolver', 'list')
    assert listed.success, listed.stderr
    assert listed.toon().get('count') == 1

    removed = run_script(SCRIPT_PATH, 'derivation-resolver', 'remove', '--resolver', 'lsp')
    assert removed.success, removed.stderr
    assert removed.toon().get('action') == 'removed'
