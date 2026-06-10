#!/usr/bin/env python3
"""Tests for the build-queue-limit subcommand group of manage-run-config.

Covers the build_queue.upper_limit_seconds knob added in D5:
- Default (floor) 600 s when the section is absent
- get/set round-trips that materialise the build_queue section
- Clamp to [600, 3600] on write (a value outside the bounds is clamped, not rejected)
- Non-positive values rejected via the invalid_value contract
- Help wiring for the new subcommands

Mirrors the test conventions used by ``test_architecture_refresh_section.py`` —
the PlanContext fixture isolates ``.plan`` state per test and run_script
invokes the script via the shared subprocess wrapper.
"""

import json

from conftest import get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-run-config', 'run_config.py')


# =============================================================================
# get — default behaviour and persisted reads
# =============================================================================


def test_get_default_when_section_absent(plan_context):
    """get returns the 600 s floor on a fresh project with no config file."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    result = run_script(SCRIPT_PATH, 'build-queue-limit', 'get')

    assert result.success, f'Should succeed: {result.stderr}'
    data = result.toon()
    assert data.get('status') == 'success'
    assert data.get('field') == 'build_queue_upper_limit'
    assert data.get('value') == 600


def test_get_default_when_section_missing_in_existing_config(plan_context):
    """get returns the floor when the build_queue section is missing."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'run-configuration.json').write_text(json.dumps({'version': 1, 'commands': {}}))

    result = run_script(SCRIPT_PATH, 'build-queue-limit', 'get')

    assert result.success, f'Should succeed: {result.stderr}'
    assert result.toon().get('value') == 600


def test_get_reads_persisted_value(plan_context):
    """get returns the persisted (in-bounds) value when explicitly stored."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'run-configuration.json').write_text(
        json.dumps({'version': 1, 'commands': {}, 'build_queue': {'upper_limit_seconds': 1800}})
    )

    result = run_script(SCRIPT_PATH, 'build-queue-limit', 'get')

    assert result.success, f'Should succeed: {result.stderr}'
    assert result.toon().get('value') == 1800


def test_get_clamps_persisted_value_above_ceiling(plan_context):
    """A persisted value above the 3600 s ceiling reads back clamped to 3600."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'run-configuration.json').write_text(
        json.dumps({'version': 1, 'commands': {}, 'build_queue': {'upper_limit_seconds': 99999}})
    )

    result = run_script(SCRIPT_PATH, 'build-queue-limit', 'get')

    assert result.success, f'Should succeed: {result.stderr}'
    assert result.toon().get('value') == 3600


# =============================================================================
# set — round-trip, clamp, and rejection
# =============================================================================


def test_set_round_trip(plan_context):
    """set persists an in-bounds value and get reads it back (main-anchored)."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    set_result = run_script(SCRIPT_PATH, 'build-queue-limit', 'set', '--value', '1800')
    assert set_result.success, f'set should succeed: {set_result.stderr}'
    set_data = set_result.toon()
    assert set_data.get('status') == 'success'
    assert set_data.get('field') == 'build_queue_upper_limit'
    assert set_data.get('value') == 1800

    # Verify file contents on disk under the build_queue block.
    config = json.loads((plan_dir / 'run-configuration.json').read_text())
    assert config['build_queue']['upper_limit_seconds'] == 1800

    # Round-trip via get.
    get_result = run_script(SCRIPT_PATH, 'build-queue-limit', 'get')
    assert get_result.success, f'get should succeed: {get_result.stderr}'
    assert get_result.toon().get('value') == 1800


def test_set_creates_section_when_absent(plan_context):
    """set materialises the build_queue section if missing."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'run-configuration.json').write_text(json.dumps({'version': 1, 'commands': {}}))

    result = run_script(SCRIPT_PATH, 'build-queue-limit', 'set', '--value', '900')

    assert result.success, f'Should succeed: {result.stderr}'
    config = json.loads((plan_dir / 'run-configuration.json').read_text())
    assert 'build_queue' in config
    assert config['build_queue']['upper_limit_seconds'] == 900


def test_set_clamps_above_ceiling(plan_context):
    """A --value above 3600 is clamped to 3600 on write (not rejected)."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    result = run_script(SCRIPT_PATH, 'build-queue-limit', 'set', '--value', '10000')

    assert result.success, f'Should succeed: {result.stderr}'
    assert result.toon().get('value') == 3600
    config = json.loads((plan_dir / 'run-configuration.json').read_text())
    assert config['build_queue']['upper_limit_seconds'] == 3600


def test_set_clamps_below_floor(plan_context):
    """A --value between 1 and 600 is clamped up to the 600 s floor on write."""
    plan_dir = plan_context.fixture_dir
    plan_dir.mkdir(parents=True, exist_ok=True)

    result = run_script(SCRIPT_PATH, 'build-queue-limit', 'set', '--value', '120')

    assert result.success, f'Should succeed: {result.stderr}'
    assert result.toon().get('value') == 600
    config = json.loads((plan_dir / 'run-configuration.json').read_text())
    assert config['build_queue']['upper_limit_seconds'] == 600


def test_set_rejects_non_positive_value(plan_context):
    """set rejects a non-positive --value via the invalid_value contract."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    result = run_script(SCRIPT_PATH, 'build-queue-limit', 'set', '--value', '0')

    assert result.success, f'Should run cleanly: {result.stderr}'
    data = result.toon()
    assert data.get('status') == 'error'
    assert data.get('error') == 'invalid_value'


def test_set_rejects_non_integer_value(plan_context):
    """set rejects a non-integer --value via argparse type coercion."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)

    result = run_script(SCRIPT_PATH, 'build-queue-limit', 'set', '--value', 'soon')

    assert result.returncode != 0, 'Non-integer value should be rejected by argparse'


# =============================================================================
# Help wiring
# =============================================================================


def test_build_queue_limit_help():
    """build-queue-limit shows both subcommands in help output."""
    result = run_script(SCRIPT_PATH, 'build-queue-limit', '--help')
    assert result.success, f'Should succeed: {result.stderr}'
    assert 'get' in result.stdout
    assert 'set' in result.stdout


def test_build_queue_limit_set_help_lists_value_flag():
    """set help advertises the --value flag."""
    result = run_script(SCRIPT_PATH, 'build-queue-limit', 'set', '--help')
    assert result.success, f'Should succeed: {result.stderr}'
    assert '--value' in result.stdout
