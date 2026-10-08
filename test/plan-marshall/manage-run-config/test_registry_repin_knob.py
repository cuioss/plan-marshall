#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the registry-repin subcommand group of manage-run-config.

Covers the machine-local registry_repin opt-in:
- The default reads ``disabled`` — on a project with no config file and on a
  config file carrying no ``registry_repin`` key
- get/set round-trips for both enum values, with the source reported rather
  than left to be inferred from the value
- An out-of-enum value is rejected with ``invalid_value`` and persists nothing
- A malformed stored value reads ``disabled`` — the read fails closed, so no
  damaged store is taken as consent to write the registry
- Help wiring for the new subcommands

Mirrors the conventions of test_commit_trailer_knob.py.
"""

import json

import pytest

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-run-config', 'run_config.py')

CONFIG_FILE = 'run-configuration.json'

# Stored values that are not exactly one of the two enum strings. Each must read
# as the default: a near-miss spelling and a truthy non-string are the two
# shapes most likely to be mistaken for consent.
MALFORMED_STORED_VALUES = [
    pytest.param('yes', id='unknown-string'),
    pytest.param('ENABLED', id='wrong-case'),
    pytest.param(' enabled', id='padded'),
    pytest.param('', id='empty-string'),
    pytest.param(True, id='boolean-true'),
    pytest.param(1, id='integer'),
    pytest.param(None, id='null'),
    pytest.param(['enabled'], id='list'),
    pytest.param({'value': 'enabled'}, id='object'),
]


def _write_config(plan_context, **sections) -> None:
    """Persist a run-configuration carrying ``sections`` for one test."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / CONFIG_FILE).write_text(json.dumps({'version': 1, 'commands': {}, **sections}))


def _stored_config(plan_context) -> dict:
    """Read back what the store holds on disk, bypassing the script under test."""
    loaded: dict = json.loads((plan_context.fixture_dir / CONFIG_FILE).read_text())
    return loaded


# =============================================================================
# get — the default
# =============================================================================


def test_get_defaults_to_disabled_without_a_config_file(plan_context):
    """get reads disabled on a project that has no run-configuration at all."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    result = run_script(SCRIPT_PATH, 'registry-repin', 'get')

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    assert data.get('status') == 'success'
    assert data.get('value') == 'disabled'
    assert data.get('source') == 'default'


def test_get_defaults_to_disabled_when_the_key_is_absent(plan_context):
    """get reads disabled on a config file carrying no registry_repin key."""
    _write_config(plan_context)

    data = run_script(SCRIPT_PATH, 'registry-repin', 'get').toon()

    assert data.get('value') == 'disabled'
    assert data.get('source') == 'default'


def test_get_does_not_materialise_the_key(plan_context):
    """Reading the default is a read: the store is left without the key."""
    _write_config(plan_context)

    run_script(SCRIPT_PATH, 'registry-repin', 'get')

    assert 'registry_repin' not in _stored_config(plan_context)


# =============================================================================
# set — round-trip and source reporting
# =============================================================================


@pytest.mark.parametrize('value', ['enabled', 'disabled'])
def test_set_round_trips_each_value(plan_context, value):
    """set persists the value and a subsequent get reads it back as configured."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    written = run_script(SCRIPT_PATH, 'registry-repin', 'set', '--value', value)

    assert written.success, f'Should succeed: {written.stderr}'
    assert written.toon().get('value') == value
    data = run_script(SCRIPT_PATH, 'registry-repin', 'get').toon()
    assert data.get('value') == value
    assert data.get('source') == 'configured'
    assert _stored_config(plan_context).get('registry_repin') == value


def test_set_disabled_is_reported_as_configured_not_default(plan_context):
    """Matched positive control: an explicit value equal to the default is `configured`.

    Without it the ``source`` field would carry no signal on the default value,
    and the absent-key tests above could pass on a constant.
    """
    _write_config(plan_context, registry_repin='disabled')

    data = run_script(SCRIPT_PATH, 'registry-repin', 'get').toon()

    assert data.get('value') == 'disabled'
    assert data.get('source') == 'configured'


def test_set_overwrites_a_previous_value(plan_context):
    """The opt-in can be withdrawn: enabled then disabled reads disabled."""
    _write_config(plan_context, registry_repin='enabled')

    run_script(SCRIPT_PATH, 'registry-repin', 'set', '--value', 'disabled')

    assert run_script(SCRIPT_PATH, 'registry-repin', 'get').toon().get('value') == 'disabled'


def test_set_leaves_the_other_sections_untouched(plan_context):
    """Writing the opt-in does not disturb a sibling section of the same store."""
    trailer = {'name': 'my-system', 'email': 'bot@example.org'}
    _write_config(plan_context, commit_trailer=trailer)

    run_script(SCRIPT_PATH, 'registry-repin', 'set', '--value', 'enabled')

    stored = _stored_config(plan_context)
    assert stored.get('commit_trailer') == trailer
    assert stored.get('registry_repin') == 'enabled'


# =============================================================================
# set — an invalid value persists nothing
# =============================================================================


@pytest.mark.parametrize('value', ['yes', 'true', 'ENABLED', 'on', ''])
def test_set_rejects_an_out_of_enum_value_with_invalid_value(plan_context, value):
    """Any value outside the enum is answered with the structured invalid_value result."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    data = run_script(SCRIPT_PATH, 'registry-repin', 'set', '--value', value).toon()

    assert data.get('status') == 'error'
    assert data.get('error') == 'invalid_value'
    assert data.get('allowed') == ['enabled', 'disabled']


def test_set_invalid_value_leaves_a_stored_value_untouched(plan_context):
    """A rejected set does not overwrite — or clear — what the store already held."""
    _write_config(plan_context, registry_repin='enabled')
    before = (plan_context.fixture_dir / CONFIG_FILE).read_text()

    run_script(SCRIPT_PATH, 'registry-repin', 'set', '--value', 'yes')

    assert (plan_context.fixture_dir / CONFIG_FILE).read_text() == before
    assert run_script(SCRIPT_PATH, 'registry-repin', 'get').toon().get('value') == 'enabled'


def test_set_invalid_value_creates_no_config_file(plan_context):
    """A rejected set on a project with no config file writes no file at all."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    run_script(SCRIPT_PATH, 'registry-repin', 'set', '--value', 'yes')

    assert not (plan_context.fixture_dir / CONFIG_FILE).exists()


# =============================================================================
# get — a malformed stored value reads disabled
# =============================================================================


@pytest.mark.parametrize('stored', MALFORMED_STORED_VALUES)
def test_get_reads_a_malformed_stored_value_as_disabled(plan_context, stored):
    """A stored value that is not exactly an enum string is never read as enabled."""
    _write_config(plan_context, registry_repin=stored)

    result = run_script(SCRIPT_PATH, 'registry-repin', 'get')

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    assert data.get('status') == 'success'
    assert data.get('value') == 'disabled'
    assert data.get('source') == 'default'


def test_a_malformed_stored_value_can_be_repaired_by_set(plan_context):
    """set replaces a malformed stored value rather than tripping over it."""
    _write_config(plan_context, registry_repin={'value': 'enabled'})

    run_script(SCRIPT_PATH, 'registry-repin', 'set', '--value', 'enabled')

    data = run_script(SCRIPT_PATH, 'registry-repin', 'get').toon()
    assert data.get('value') == 'enabled'
    assert data.get('source') == 'configured'


# =============================================================================
# CLI wiring
# =============================================================================


def test_registry_repin_help_lists_subcommands():
    """--help exposes both sub-verbs of the group."""
    result = run_script(SCRIPT_PATH, 'registry-repin', '--help')

    assert result.success
    assert 'get' in result.stdout
    assert 'set' in result.stdout


def test_registry_repin_set_help_lists_the_value_flag():
    """set --help advertises the --value flag and both enum values."""
    result = run_script(SCRIPT_PATH, 'registry-repin', 'set', '--help')

    assert result.success
    assert '--value' in result.stdout
    assert 'enabled' in result.stdout
    assert 'disabled' in result.stdout
