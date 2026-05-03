#!/usr/bin/env python3
"""Tests for the architecture-refresh subcommand group of manage-run-config.

Covers the architecture_refresh schema added in Phase D, Task 3:
- Default tier-0 (enabled) and tier-1 (prompt) when the section is absent
- get/set round-trips that materialise the architecture_refresh section
- Enum-value enforcement rejecting unknown tier values
- Validate subcommand acceptance of run-configuration files that include
  an architecture_refresh section (forward-compatible schema)
- Help wiring for the new subcommands

Mirrors the test conventions used by ``test_run_config.py`` — the
PlanContext fixture isolates ``.plan`` state per test and run_script
invokes the script via the shared subprocess wrapper.
"""

import json

from conftest import PlanContext, get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-run-config', 'run_config.py')


# =============================================================================
# get-tier-0 — default behaviour and persisted reads
# =============================================================================


def test_get_tier_0_default_when_section_absent():
    """get-tier-0 returns 'enabled' on a fresh project with no config file."""
    with PlanContext() as ctx:
        ctx.fixture_dir.mkdir(parents=True, exist_ok=True)

        result = run_script(SCRIPT_PATH, 'architecture-refresh', 'get-tier-0')

        assert result.success, f'Should succeed: {result.stderr}'
        data = result.toon()
        assert data.get('status') == 'success'
        assert data.get('field') == 'tier_0'
        assert data.get('value') == 'enabled'


def test_get_tier_0_default_when_section_missing_in_existing_config():
    """get-tier-0 returns the default when the architecture_refresh section is missing."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / 'run-configuration.json').write_text(
            json.dumps({'version': 1, 'commands': {}})
        )

        result = run_script(SCRIPT_PATH, 'architecture-refresh', 'get-tier-0')

        assert result.success, f'Should succeed: {result.stderr}'
        data = result.toon()
        assert data.get('value') == 'enabled'


def test_get_tier_0_reads_persisted_value():
    """get-tier-0 returns persisted value when explicitly stored."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / 'run-configuration.json').write_text(
            json.dumps(
                {
                    'version': 1,
                    'commands': {},
                    'architecture_refresh': {'tier_0': 'disabled'},
                }
            )
        )

        result = run_script(SCRIPT_PATH, 'architecture-refresh', 'get-tier-0')

        assert result.success, f'Should succeed: {result.stderr}'
        data = result.toon()
        assert data.get('value') == 'disabled'


# =============================================================================
# set-tier-0 — round-trip and enum enforcement
# =============================================================================


def test_set_tier_0_round_trip():
    """set-tier-0 persists value and get-tier-0 reads it back."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)

        set_result = run_script(
            SCRIPT_PATH, 'architecture-refresh', 'set-tier-0', '--value', 'disabled'
        )
        assert set_result.success, f'set should succeed: {set_result.stderr}'
        set_data = set_result.toon()
        assert set_data.get('status') == 'success'
        assert set_data.get('field') == 'tier_0'
        assert set_data.get('value') == 'disabled'

        # Verify file contents on disk
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert config['architecture_refresh']['tier_0'] == 'disabled'

        # Round-trip via get
        get_result = run_script(SCRIPT_PATH, 'architecture-refresh', 'get-tier-0')
        assert get_result.success, f'get should succeed: {get_result.stderr}'
        assert get_result.toon().get('value') == 'disabled'


def test_set_tier_0_creates_section_when_absent():
    """set-tier-0 materialises architecture_refresh section if missing."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / 'run-configuration.json').write_text(
            json.dumps({'version': 1, 'commands': {}})
        )

        result = run_script(
            SCRIPT_PATH, 'architecture-refresh', 'set-tier-0', '--value', 'enabled'
        )

        assert result.success, f'Should succeed: {result.stderr}'
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert 'architecture_refresh' in config
        assert config['architecture_refresh']['tier_0'] == 'enabled'


def test_set_tier_0_rejects_unknown_value():
    """set-tier-0 rejects values outside the (enabled|disabled) enum."""
    with PlanContext() as ctx:
        ctx.fixture_dir.mkdir(parents=True, exist_ok=True)

        result = run_script(
            SCRIPT_PATH, 'architecture-refresh', 'set-tier-0', '--value', 'maybe'
        )

        # argparse choices=… rejects with non-zero exit
        assert result.returncode != 0, 'Unknown value should be rejected by argparse'


# =============================================================================
# get-tier-1 — default and persisted reads
# =============================================================================


def test_get_tier_1_default_when_section_absent():
    """get-tier-1 returns 'prompt' default on a fresh project."""
    with PlanContext() as ctx:
        ctx.fixture_dir.mkdir(parents=True, exist_ok=True)

        result = run_script(SCRIPT_PATH, 'architecture-refresh', 'get-tier-1')

        assert result.success, f'Should succeed: {result.stderr}'
        data = result.toon()
        assert data.get('status') == 'success'
        assert data.get('field') == 'tier_1'
        assert data.get('value') == 'prompt'


def test_get_tier_1_reads_persisted_value():
    """get-tier-1 returns persisted value when explicitly stored."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / 'run-configuration.json').write_text(
            json.dumps(
                {
                    'version': 1,
                    'commands': {},
                    'architecture_refresh': {'tier_1': 'auto'},
                }
            )
        )

        result = run_script(SCRIPT_PATH, 'architecture-refresh', 'get-tier-1')

        assert result.success, f'Should succeed: {result.stderr}'
        assert result.toon().get('value') == 'auto'


# =============================================================================
# set-tier-1 — round-trip and enum enforcement
# =============================================================================


def test_set_tier_1_round_trip():
    """set-tier-1 persists value and get-tier-1 reads it back."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)

        set_result = run_script(
            SCRIPT_PATH, 'architecture-refresh', 'set-tier-1', '--value', 'auto'
        )
        assert set_result.success, f'set should succeed: {set_result.stderr}'
        set_data = set_result.toon()
        assert set_data.get('status') == 'success'
        assert set_data.get('field') == 'tier_1'
        assert set_data.get('value') == 'auto'

        # Verify file contents on disk
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert config['architecture_refresh']['tier_1'] == 'auto'

        # Round-trip via get
        get_result = run_script(SCRIPT_PATH, 'architecture-refresh', 'get-tier-1')
        assert get_result.success, f'get should succeed: {get_result.stderr}'
        assert get_result.toon().get('value') == 'auto'


def test_set_tier_1_accepts_disabled():
    """set-tier-1 accepts 'disabled' (shared enum value with tier-0)."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)

        result = run_script(
            SCRIPT_PATH, 'architecture-refresh', 'set-tier-1', '--value', 'disabled'
        )

        assert result.success, f'Should succeed: {result.stderr}'
        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert config['architecture_refresh']['tier_1'] == 'disabled'


def test_set_tier_1_rejects_unknown_value():
    """set-tier-1 rejects values outside the (prompt|auto|disabled) enum."""
    with PlanContext() as ctx:
        ctx.fixture_dir.mkdir(parents=True, exist_ok=True)

        result = run_script(
            SCRIPT_PATH, 'architecture-refresh', 'set-tier-1', '--value', 'enabled'
        )

        # tier_1 does not allow 'enabled' (only tier_0 does)
        assert result.returncode != 0, 'Unknown value should be rejected by argparse'


def test_set_tier_1_rejects_garbage_value():
    """set-tier-1 rejects arbitrary strings outside the enum."""
    with PlanContext() as ctx:
        ctx.fixture_dir.mkdir(parents=True, exist_ok=True)

        result = run_script(
            SCRIPT_PATH, 'architecture-refresh', 'set-tier-1', '--value', 'sometimes'
        )

        assert result.returncode != 0


# =============================================================================
# Independence — tier_0 and tier_1 do not collide
# =============================================================================


def test_tier_0_and_tier_1_persist_independently():
    """Setting tier_0 does not perturb tier_1, and vice versa."""
    with PlanContext() as ctx:
        plan_dir = ctx.fixture_dir
        plan_dir.mkdir(parents=True, exist_ok=True)

        run_script(
            SCRIPT_PATH, 'architecture-refresh', 'set-tier-0', '--value', 'disabled'
        )
        run_script(
            SCRIPT_PATH, 'architecture-refresh', 'set-tier-1', '--value', 'auto'
        )

        config = json.loads((plan_dir / 'run-configuration.json').read_text())
        assert config['architecture_refresh']['tier_0'] == 'disabled'
        assert config['architecture_refresh']['tier_1'] == 'auto'

        # Re-read via the CLI to confirm
        t0 = run_script(SCRIPT_PATH, 'architecture-refresh', 'get-tier-0').toon()
        t1 = run_script(SCRIPT_PATH, 'architecture-refresh', 'get-tier-1').toon()
        assert t0.get('value') == 'disabled'
        assert t1.get('value') == 'auto'


# =============================================================================
# Validate subcommand — schema accepts architecture_refresh section
# =============================================================================


def test_validate_accepts_config_with_architecture_refresh_section():
    """validate succeeds for a config that includes architecture_refresh."""
    with PlanContext() as ctx:
        config_path = ctx.fixture_dir / 'run-configuration.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(
                {
                    'version': 1,
                    'commands': {},
                    'architecture_refresh': {
                        'tier_0': 'enabled',
                        'tier_1': 'prompt',
                    },
                }
            )
        )

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(config_path))

        assert result.success, f'Should succeed: {result.stderr}'
        data = result.toon()
        assert data.get('status') == 'success'
        assert data.get('valid') is True


def test_validate_accepts_config_without_architecture_refresh_section():
    """validate succeeds for a baseline config without architecture_refresh."""
    with PlanContext() as ctx:
        config_path = ctx.fixture_dir / 'run-configuration.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({'version': 1, 'commands': {}}))

        result = run_script(SCRIPT_PATH, 'validate', '--file', str(config_path))

        assert result.success, f'Should succeed: {result.stderr}'
        assert result.toon().get('valid') is True


# =============================================================================
# Help wiring
# =============================================================================


def test_architecture_refresh_help():
    """architecture-refresh shows all four subcommands in help output."""
    result = run_script(SCRIPT_PATH, 'architecture-refresh', '--help')
    assert result.success, f'Should succeed: {result.stderr}'
    assert 'get-tier-0' in result.stdout
    assert 'set-tier-0' in result.stdout
    assert 'get-tier-1' in result.stdout
    assert 'set-tier-1' in result.stdout


def test_architecture_refresh_set_tier_0_help_lists_choices():
    """set-tier-0 help advertises the (enabled|disabled) value choices."""
    result = run_script(
        SCRIPT_PATH, 'architecture-refresh', 'set-tier-0', '--help'
    )
    assert result.success, f'Should succeed: {result.stderr}'
    assert '--value' in result.stdout
    assert 'enabled' in result.stdout
    assert 'disabled' in result.stdout


def test_architecture_refresh_set_tier_1_help_lists_choices():
    """set-tier-1 help advertises the (prompt|auto|disabled) value choices."""
    result = run_script(
        SCRIPT_PATH, 'architecture-refresh', 'set-tier-1', '--help'
    )
    assert result.success, f'Should succeed: {result.stderr}'
    assert '--value' in result.stdout
    assert 'prompt' in result.stdout
    assert 'auto' in result.stdout
    assert 'disabled' in result.stdout
