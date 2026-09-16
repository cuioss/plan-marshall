#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the top-level ``interaction_mode`` preference (PLAN-09).

Covers the foundation deliverable's contract through the ``manage-config``
surface:

- Each mode (``basic`` / ``advanced`` / ``expert``) resolves via a
  ``interaction-mode set`` → ``get`` round-trip.
- An invalid value is refused fail-closed (``status: error``,
  ``error_type: invalid_value``) and never persists.
- An absent field resolves to the ``advanced`` default (``set: false``).
- An unknown field is rejected by the provisioning-write guard
  (``error_type: unknown_field``).

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.
"""

import json
from argparse import Namespace

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from _manage_config_fixtures import SCRIPT_PATH, create_marshal_json

from conftest import load_script_module, run_script

_cmd_interaction_mode = load_script_module(
    'plan-marshall', 'manage-config', '_cmd_interaction_mode.py', module_name='_cmd_interaction_mode'
)
_config_defaults_mod = load_script_module(
    'plan-marshall', 'manage-config', '_config_defaults.py', module_name='_config_defaults_for_interaction_mode_test'
)
_config_core_mod = load_script_module(
    'plan-marshall', 'manage-config', '_config_core.py', module_name='_config_core_for_interaction_mode_test'
)

cmd_interaction_mode_get = _cmd_interaction_mode.cmd_interaction_mode_get
cmd_interaction_mode_set = _cmd_interaction_mode.cmd_interaction_mode_set


# =============================================================================
# Validator unit tests
# =============================================================================


@pytest.mark.parametrize('mode', _config_defaults_mod.VALID_INTERACTION_MODES)
def test_validate_interaction_mode_accepts_each_mode(mode):
    """Every allowed mode validates cleanly."""
    _config_defaults_mod.validate_interaction_mode(mode)  # must not raise


@pytest.mark.parametrize('value', ['turbo', '', 'ADVANCED', 'basic ', None, 42, True])
def test_validate_interaction_mode_rejects_other_values(value):
    """Anything outside the allowed set fails closed."""
    with pytest.raises(ValueError, match='interaction_mode'):
        _config_defaults_mod.validate_interaction_mode(value)


def test_interaction_mode_default_is_advanced():
    """The seeded default is ``advanced`` and validates."""
    assert _config_defaults_mod.DEFAULT_INTERACTION_MODE == 'advanced'
    assert set(_config_defaults_mod.VALID_INTERACTION_MODES) == {'basic', 'advanced', 'expert'}


# =============================================================================
# Seed + canonical order
# =============================================================================


def test_get_default_config_seeds_interaction_mode():
    """``get_default_config()`` carries the top-level scalar at its default."""
    config = _config_defaults_mod.get_default_config()
    assert config['interaction_mode'] == 'advanced'


def test_interaction_mode_in_canonical_top_level_order():
    """The key has a canonical slot (between ``credentials_config`` and ``project``)."""
    order = _config_core_mod.CANONICAL_TOP_LEVEL_KEY_ORDER
    assert 'interaction_mode' in order
    assert order.index('credentials_config') < order.index('interaction_mode') < order.index('project')


# =============================================================================
# resolve_interaction_mode helper
# =============================================================================


def test_resolve_interaction_mode_absent_key_falls_back_to_default():
    """A pre-feature config without the key resolves to ``advanced``."""
    assert _config_core_mod.resolve_interaction_mode({}) == 'advanced'


@pytest.mark.parametrize('mode', _config_defaults_mod.VALID_INTERACTION_MODES)
def test_resolve_interaction_mode_returns_persisted_value(mode):
    """A persisted valid mode resolves verbatim."""
    assert _config_core_mod.resolve_interaction_mode({'interaction_mode': mode}) == mode


def test_resolve_interaction_mode_invalid_value_fails_closed():
    """A hand-corrupted persisted value raises instead of resolving silently."""
    with pytest.raises(ValueError, match='interaction_mode'):
        _config_core_mod.resolve_interaction_mode({'interaction_mode': 'turbo'})


# =============================================================================
# Get/set round-trip (Tier 2 - direct import)
# =============================================================================


@pytest.mark.parametrize('mode', _config_defaults_mod.VALID_INTERACTION_MODES)
def test_interaction_mode_set_get_round_trip(plan_context, mode):
    """Each mode persists and reads back with ``set: true``."""
    create_marshal_json(plan_context.fixture_dir)

    set_result = cmd_interaction_mode_set(Namespace(field='interaction_mode', value=mode))
    assert set_result['status'] == 'success'
    assert set_result['value'] == mode

    get_result = cmd_interaction_mode_get(Namespace(field='interaction_mode'))
    assert get_result['status'] == 'success'
    assert get_result['value'] == mode
    assert get_result['set'] is True


def test_interaction_mode_get_absent_key_returns_default(plan_context):
    """The fixture config predates the key — ``get`` falls back to ``advanced``."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_interaction_mode_get(Namespace(field='interaction_mode'))

    assert result['status'] == 'success'
    assert result['value'] == 'advanced'
    assert result['set'] is False


def test_interaction_mode_set_invalid_value_refused(plan_context):
    """An out-of-schema value is refused and never persists."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_interaction_mode_set(Namespace(field='interaction_mode', value='turbo'))

    assert result['status'] == 'error'
    assert result.get('error_type') == 'invalid_value'

    # The refused write left no trace — the key is still absent.
    verify = cmd_interaction_mode_get(Namespace(field='interaction_mode'))
    assert verify['value'] == 'advanced'
    assert verify['set'] is False


def test_interaction_mode_get_invalid_persisted_value_fails_closed(plan_context, monkeypatch):
    """A hand-corrupted marshal.json fails loud on read instead of propagating."""
    path = create_marshal_json(plan_context.fixture_dir)
    config = json.loads(path.read_text(encoding='utf-8'))
    config['interaction_mode'] = 'turbo'
    path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    result = cmd_interaction_mode_get(Namespace(field='interaction_mode'))

    assert result['status'] == 'error'
    assert result.get('error_type') == 'invalid_value'


def test_interaction_mode_unknown_field_rejected(plan_context):
    """The provisioning-write guard refuses an unknown field on both verbs."""
    create_marshal_json(plan_context.fixture_dir)

    for verb in (cmd_interaction_mode_get, cmd_interaction_mode_set):
        result = verb(Namespace(field='not_a_real_mode_key', value='advanced'))
        assert result['status'] == 'error', f'{verb.__name__} must fail closed on an unknown field'
        assert result.get('error_type') == 'unknown_field'


@pytest.mark.parametrize('root', [[], [1, 2], 42, 'advanced', True, None])
def test_interaction_mode_non_object_root_returns_structured_error(plan_context, root):
    """A non-object marshal.json root yields a structured config error, not a TypeError."""
    path = create_marshal_json(plan_context.fixture_dir)
    path.write_text(json.dumps(root), encoding='utf-8')

    for verb in (cmd_interaction_mode_get, cmd_interaction_mode_set):
        result = verb(Namespace(field='interaction_mode', value='advanced'))
        assert result['status'] == 'error', f'{verb.__name__} must fail closed on a non-object root'
        assert result.get('error_type') == 'invalid_config'


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_interaction_mode_get(plan_context):
    """Test CLI plumbing: interaction-mode get outputs TOON with the default."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'interaction-mode', 'get', '--field', 'interaction_mode')

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'advanced' in result.stdout


def test_cli_interaction_mode_set(plan_context):
    """Test CLI plumbing: interaction-mode set outputs TOON."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'interaction-mode', 'set', '--field', 'interaction_mode', '--value', 'expert')

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'expert' in result.stdout
