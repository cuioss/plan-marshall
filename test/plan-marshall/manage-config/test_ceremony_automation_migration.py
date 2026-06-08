#!/usr/bin/env python3
"""Migration-contract tests for the three finalize knobs → ceremony_policy.automation.

Pins the end-to-end contract of the deliverable "Migrate the three scattered
finalize knobs into ceremony_policy.automation and delete the loose fields
(config-doc-contract)". Three orthogonal assertions per knob:

1. **Resolves from the new path** — each of `finalize_without_asking`,
   `loop_back_without_asking`, `auto_merge_after_ci` reads back through the
   dedicated `ceremony-policy get --field automation.<knob>` verb with the
   migrated default value.
2. **Loose path is gone** — the knob is absent from both the loose
   `DEFAULT_PLAN_EXECUTE` / `DEFAULT_PLAN_FINALIZE` blocks AND from the
   `plan.phase-{5-execute,6-finalize}` sections of `get_default_config()`
   (config-doc-contract: no loose-path survivors).
3. **Effective behavior preserved** — the migrated defaults are byte-identical
   to the historical loose-field defaults (forward auto-continue `True`,
   reverse halt `False`, auto-merge `True`), so existing plans behave the same.

The handler is exercised via direct importlib loading (matching the
manage-config test convention), and read-only round-trip stability of
marshal.json is asserted by hashing the file before and after each `get`.
"""

# ruff: noqa: I001, E402

import hashlib
import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

from test_helpers import create_marshal_json

_MANAGE_CONFIG_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)

if str(_MANAGE_CONFIG_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_MANAGE_CONFIG_SCRIPTS_DIR))


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _MANAGE_CONFIG_SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_config_defaults = _load_module('_config_defaults_for_migration', '_config_defaults.py')
_cmd_ceremony = _load_module('_cmd_ceremony_policy_for_migration', '_cmd_ceremony_policy.py')
cmd_ceremony_policy = _cmd_ceremony.cmd_ceremony_policy

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
import conftest  # noqa: E402, F401


# The three migrated knobs with their historical (preserved) defaults.
_MIGRATED_KNOBS = (
    ('finalize_without_asking', True),
    ('loop_back_without_asking', False),
    ('auto_merge_after_ci', True),
)


def _ns_get(field):
    return Namespace(verb='get', field=field)


def _hash_marshal(fixture_dir):
    return hashlib.sha256((fixture_dir / 'marshal.json').read_bytes()).hexdigest()


def _fresh_marshal_without_ceremony(fixture_dir):
    """Write the base fixture and strip any ceremony_policy block (pre-migration shape)."""
    create_marshal_json(fixture_dir)
    marshal_path = fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.pop('ceremony_policy', None)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')


# =============================================================================
# (1) Resolves from the new ceremony_policy.automation path
# =============================================================================


def test_each_knob_resolves_from_ceremony_automation(plan_context):
    """Each migrated knob reads back through the ceremony-policy get verb with its default."""
    # Arrange — fresh marshal.json with no ceremony_policy block (defaults-merge path)
    _fresh_marshal_without_ceremony(plan_context.fixture_dir)
    before = _hash_marshal(plan_context.fixture_dir)

    # Act / Assert — each knob resolves to its historical default, read-only
    for knob, expected in _MIGRATED_KNOBS:
        result = cmd_ceremony_policy(_ns_get(f'automation.{knob}'))
        assert result['status'] == 'success', f'{knob} must resolve'
        assert result['field'] == f'automation.{knob}'
        assert result['value'] is expected, f'{knob} default must be {expected}'

    # The read path never mutates marshal.json
    assert _hash_marshal(plan_context.fixture_dir) == before


def test_automation_sub_block_carries_exactly_the_three_knobs(plan_context):
    """The automation sub-block read returns exactly the three migrated knobs."""
    # Arrange
    _fresh_marshal_without_ceremony(plan_context.fixture_dir)

    # Act
    result = cmd_ceremony_policy(_ns_get('automation'))

    # Assert — no extra / missing knobs
    assert result['status'] == 'success'
    assert set(result['value'].keys()) == {knob for knob, _ in _MIGRATED_KNOBS}


# =============================================================================
# (2) Loose field paths are gone (config-doc-contract: no loose-path survivors)
# =============================================================================


def test_loose_field_paths_absent_from_default_blocks():
    """No migrated knob survives in the loose DEFAULT_PLAN_EXECUTE / DEFAULT_PLAN_FINALIZE blocks."""
    # Arrange / Act / Assert
    for knob, _ in _MIGRATED_KNOBS:
        assert knob not in _config_defaults.DEFAULT_PLAN_EXECUTE, (
            f'{knob} must NOT survive in DEFAULT_PLAN_EXECUTE'
        )
        assert knob not in _config_defaults.DEFAULT_PLAN_FINALIZE, (
            f'{knob} must NOT survive in DEFAULT_PLAN_FINALIZE'
        )


def test_loose_field_paths_absent_from_get_default_config():
    """No migrated knob survives in the plan.phase-* sections of get_default_config()."""
    # Arrange
    cfg = _config_defaults.get_default_config()
    plan_block = cfg['plan']

    # Act / Assert — absent from both phase sections
    for knob, _ in _MIGRATED_KNOBS:
        assert knob not in plan_block['phase-5-execute'], (
            f'{knob} must NOT survive in plan.phase-5-execute'
        )
        assert knob not in plan_block['phase-6-finalize'], (
            f'{knob} must NOT survive in plan.phase-6-finalize'
        )


def test_ceremony_policy_is_top_level_not_nested_under_plan():
    """get_default_config() surfaces ceremony_policy as a top-level sibling of plan."""
    # Arrange
    cfg = _config_defaults.get_default_config()

    # Act / Assert
    assert 'ceremony_policy' in cfg
    assert 'ceremony_policy' not in cfg['plan']
    assert set(cfg['ceremony_policy']['automation'].keys()) == {
        knob for knob, _ in _MIGRATED_KNOBS
    }


# =============================================================================
# (3) Effective behavior preserved (defaults match the historical loose values)
# =============================================================================


def test_migrated_defaults_match_historical_values():
    """The migrated automation defaults are byte-identical to the historical loose defaults."""
    # Arrange
    automation = _config_defaults.DEFAULT_CEREMONY_POLICY['automation']

    # Act / Assert — forward auto-continue True, reverse halt False, auto-merge True
    for knob, expected in _MIGRATED_KNOBS:
        assert automation[knob] is expected, (
            f'{knob} must preserve its historical default {expected}'
        )


def test_get_default_config_and_module_constant_agree():
    """get_default_config() and DEFAULT_CEREMONY_POLICY expose the same automation values."""
    # Arrange
    cfg_automation = _config_defaults.get_default_config()['ceremony_policy']['automation']
    const_automation = _config_defaults.DEFAULT_CEREMONY_POLICY['automation']

    # Act / Assert — same physical default, no drift
    for knob, _ in _MIGRATED_KNOBS:
        assert cfg_automation[knob] == const_automation[knob]


def test_live_override_survives_and_resolves(plan_context):
    """A live ceremony_policy.automation override reads back through the get verb.

    Confirms the migration did not strand the write path — an operator who sets
    one knob to a non-default value reads it back unchanged while the untouched
    siblings fall back to their defaults.
    """
    # Arrange — override loop_back_without_asking to True, leave the others unset
    _fresh_marshal_without_ceremony(plan_context.fixture_dir)
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config['ceremony_policy'] = {'automation': {'loop_back_without_asking': True}}
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # Act
    overridden = cmd_ceremony_policy(_ns_get('automation.loop_back_without_asking'))
    sibling = cmd_ceremony_policy(_ns_get('automation.finalize_without_asking'))

    # Assert — override wins; untouched sibling falls back to default
    assert overridden['value'] is True
    assert sibling['value'] is True  # historical default preserved
