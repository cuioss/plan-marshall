#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the display-timezone subcommand group of manage-run-config (D2).

Covers the display_timezone knob:
- Default 'UTC' when the field is absent
- get/set round-trips that persist the top-level display_timezone field
- IANA-name validation rejecting an unknown zone (runtime invalid_value error)
- The feature-defining input shape (a slash-bearing IANA name) driven through
  the CLI entry point — the mandatory first boundary test for a new input shape
- Validate subcommand acceptance of a config that carries display_timezone
- Help wiring for the new subcommands

Mirrors the conventions of test_architecture_refresh_section.py.
"""

import json

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-run-config', 'run_config.py')


# =============================================================================
# get — default and persisted reads
# =============================================================================


def test_get_defaults_to_utc_when_absent(plan_context):
    """get returns 'UTC' on a fresh project with no config file."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    result = run_script(SCRIPT_PATH, 'display-timezone', 'get')

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    assert data.get('status') == 'success'
    assert data.get('field') == 'display_timezone'
    assert data.get('value') == 'UTC'


def test_get_reads_persisted_value(plan_context):
    """get returns the persisted IANA zone when explicitly stored."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'run-configuration.json').write_text(
        json.dumps({'version': 1, 'commands': {}, 'display_timezone': 'Europe/Berlin'})
    )

    result = run_script(SCRIPT_PATH, 'display-timezone', 'get')

    assert result.success, f'Should succeed: {result.stderr}'
    assert result.toon().get('value') == 'Europe/Berlin'


# =============================================================================
# set — round-trip, IANA validation, and the feature-defining input shape
# =============================================================================


def test_set_round_trip_with_slash_bearing_iana_name(plan_context):
    """set persists a slash-bearing IANA name and get reads it back.

    This is the mandatory first boundary test for the new input shape: the value
    proposition of ``set`` is an IANA zone name (a slash-bearing token), driven
    through the CLI entry point rather than by calling the validator in isolation.
    """
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    set_result = run_script(SCRIPT_PATH, 'display-timezone', 'set', '--value', 'America/New_York')
    assert set_result.success, f'set should succeed: {set_result.stderr}'
    set_data = set_result.toon()
    assert set_data.get('status') == 'success'
    assert set_data.get('field') == 'display_timezone'
    assert set_data.get('value') == 'America/New_York'

    config = json.loads((plan_dir / 'run-configuration.json').read_text())
    assert config['display_timezone'] == 'America/New_York'

    get_result = run_script(SCRIPT_PATH, 'display-timezone', 'get')
    assert get_result.success, f'get should succeed: {get_result.stderr}'
    assert get_result.toon().get('value') == 'America/New_York'


def test_set_accepts_utc(plan_context):
    """set accepts the default zone 'UTC' without touching the IANA database."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    result = run_script(SCRIPT_PATH, 'display-timezone', 'set', '--value', 'UTC')

    assert result.success, f'Should succeed: {result.stderr}'
    assert result.toon().get('value') == 'UTC'
    config = json.loads((plan_dir / 'run-configuration.json').read_text())
    assert config['display_timezone'] == 'UTC'


def test_set_rejects_unknown_iana_name(plan_context):
    """set rejects a name that is not a loadable IANA zone (invalid_value)."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    result = run_script(SCRIPT_PATH, 'display-timezone', 'set', '--value', 'Nonsense/Zone')

    # Runtime validation (not argparse choices): the script exits 0 but the TOON
    # carries an invalid_value error and nothing is persisted.
    assert result.success, f'Script should run: {result.stderr}'
    data = result.toon()
    assert data.get('status') == 'error'
    assert data.get('error') == 'invalid_value'
    assert not (plan_context.fixture_dir / 'run-configuration.json').exists()


def test_set_creates_field_in_existing_config(plan_context):
    """set materialises display_timezone in an existing config without clobbering it."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'run-configuration.json').write_text(
        json.dumps({'version': 1, 'commands': {'x': {'timeout_seconds': 42}}})
    )

    result = run_script(SCRIPT_PATH, 'display-timezone', 'set', '--value', 'Asia/Kolkata')

    assert result.success, f'Should succeed: {result.stderr}'
    config = json.loads((plan_dir / 'run-configuration.json').read_text())
    assert config['display_timezone'] == 'Asia/Kolkata'
    # Pre-existing content is preserved.
    assert config['commands']['x']['timeout_seconds'] == 42


# =============================================================================
# validate — schema accepts display_timezone
# =============================================================================


def test_validate_accepts_config_with_display_timezone(plan_context):
    """validate succeeds for a config that includes display_timezone."""
    config_path = plan_context.fixture_dir / 'run-configuration.json'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps({'version': 1, 'commands': {}, 'display_timezone': 'America/New_York'})
    )

    result = run_script(SCRIPT_PATH, 'validate', '--file', str(config_path))

    assert result.success, f'Should succeed: {result.stderr}'
    assert result.toon().get('valid') is True


# =============================================================================
# Help wiring
# =============================================================================


def test_display_timezone_help_lists_subcommands():
    """display-timezone help shows get and set."""
    result = run_script(SCRIPT_PATH, 'display-timezone', '--help')
    assert result.success, f'Should succeed: {result.stderr}'
    assert 'get' in result.stdout
    assert 'set' in result.stdout


def test_display_timezone_set_help_advertises_value_flag():
    """set help advertises the --value argument."""
    result = run_script(SCRIPT_PATH, 'display-timezone', 'set', '--help')
    assert result.success, f'Should succeed: {result.stderr}'
    assert '--value' in result.stdout
