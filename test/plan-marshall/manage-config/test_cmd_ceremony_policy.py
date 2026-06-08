#!/usr/bin/env python3
"""Tests for the ``manage-config ceremony-policy get`` runtime read surface.

Tier-2 (direct import) tests covering the dotted-path read verb the runtime
orchestrator consumes for the three automation knobs and the run-at-all gates:

1. ``--field automation.<knob>`` returns the migrated automation bool.
2. ``--field planning.<gate>`` / ``--field finalize.<gate>`` return a gate value.
3. ``--field automation`` (a sub-block) returns the whole sub-dict.
4. No ``--field`` returns the whole merged ceremony_policy block.
5. A fresh marshal.json without a ceremony_policy block still reads the
   canonical defaults (defaults-merge fallback).
6. A live override of one sub-key wins while siblings fall back to default.
7. An unresolvable path returns ``error_type: field_not_found``.

The handler is read-only — round-trip stability of marshal.json is asserted by
hashing the file before and after each call.
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


_cmd_ceremony_mod = _load_module('_cmd_ceremony_policy', '_cmd_ceremony_policy.py')
cmd_ceremony_policy = _cmd_ceremony_mod.cmd_ceremony_policy

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
import conftest  # noqa: E402, F401


def _ns(field=None):
    """Build a Namespace shaped like argparse's output for `ceremony-policy get`."""
    return Namespace(verb='get', field=field)


def _ns_set(field, value):
    """Build a Namespace shaped like argparse's output for `ceremony-policy set`."""
    return Namespace(verb='set', field=field, value=value)


def _hash_marshal(fixture_dir):
    """Return SHA-256 of marshal.json for read-only round-trip stability checks."""
    return hashlib.sha256((fixture_dir / 'marshal.json').read_bytes()).hexdigest()


def _write_marshal_with_ceremony(fixture_dir, ceremony_block):
    """Write the base fixture, then set/clear the top-level ceremony_policy block."""
    create_marshal_json(fixture_dir)
    marshal_path = fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.pop('ceremony_policy', None)
    if ceremony_block is not None:
        config['ceremony_policy'] = ceremony_block
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')


# =============================================================================
# (1) automation knob reads
# =============================================================================


def test_get_automation_finalize_without_asking_default(plan_context):
    """`--field automation.finalize_without_asking` reads the migrated default (True)."""
    # Arrange — fresh fixture has no ceremony_policy block
    _write_marshal_with_ceremony(plan_context.fixture_dir, None)
    before = _hash_marshal(plan_context.fixture_dir)

    # Act
    result = cmd_ceremony_policy(_ns(field='automation.finalize_without_asking'))

    # Assert — value + read-only round-trip
    assert result['status'] == 'success'
    assert result['section'] == 'ceremony_policy'
    assert result['field'] == 'automation.finalize_without_asking'
    assert result['value'] is True
    assert _hash_marshal(plan_context.fixture_dir) == before


def test_get_automation_loop_back_without_asking_default(plan_context):
    """`--field automation.loop_back_without_asking` reads the migrated default (False)."""
    # Arrange
    _write_marshal_with_ceremony(plan_context.fixture_dir, None)

    # Act
    result = cmd_ceremony_policy(_ns(field='automation.loop_back_without_asking'))

    # Assert
    assert result['status'] == 'success'
    assert result['value'] is False


def test_get_automation_auto_merge_after_ci_default(plan_context):
    """`--field automation.auto_merge_after_ci` reads the migrated default (True)."""
    # Arrange
    _write_marshal_with_ceremony(plan_context.fixture_dir, None)

    # Act
    result = cmd_ceremony_policy(_ns(field='automation.auto_merge_after_ci'))

    # Assert
    assert result['status'] == 'success'
    assert result['value'] is True


# =============================================================================
# (2) run-at-all gate reads
# =============================================================================


def test_get_planning_deep_lane_default(plan_context):
    """`--field planning.deep_lane` reads the default run-at-all value ('auto')."""
    # Arrange
    _write_marshal_with_ceremony(plan_context.fixture_dir, None)

    # Act
    result = cmd_ceremony_policy(_ns(field='planning.deep_lane'))

    # Assert
    assert result['status'] == 'success'
    assert result['value'] == 'auto'


def test_get_finalize_qgate_default(plan_context):
    """`--field finalize.qgate` reads the default run-at-all value ('auto')."""
    # Arrange
    _write_marshal_with_ceremony(plan_context.fixture_dir, None)

    # Act
    result = cmd_ceremony_policy(_ns(field='finalize.qgate'))

    # Assert
    assert result['status'] == 'success'
    assert result['value'] == 'auto'


# =============================================================================
# (3) sub-block read
# =============================================================================


def test_get_automation_sub_block(plan_context):
    """`--field automation` returns the whole automation sub-dict."""
    # Arrange
    _write_marshal_with_ceremony(plan_context.fixture_dir, None)

    # Act
    result = cmd_ceremony_policy(_ns(field='automation'))

    # Assert — exactly the three migrated knobs
    assert result['status'] == 'success'
    assert result['value'] == {
        'finalize_without_asking': True,
        'loop_back_without_asking': False,
        'auto_merge_after_ci': True,
    }


# =============================================================================
# (4) whole-block read (no --field)
# =============================================================================


def test_get_whole_block_no_field(plan_context):
    """No `--field` returns the whole merged ceremony_policy block."""
    # Arrange
    _write_marshal_with_ceremony(plan_context.fixture_dir, None)

    # Act
    result = cmd_ceremony_policy(_ns(field=None))

    # Assert — all four top-level sections present
    assert result['status'] == 'success'
    assert result['section'] == 'ceremony_policy'
    assert {'planning', 'finalize', 'automation', 'overrides'}.issubset(result.keys())
    assert result['overrides'] == []


# =============================================================================
# (5) defaults-merge fallback (live override wins, siblings default)
# =============================================================================


def test_live_override_wins_sibling_falls_back(plan_context):
    """A live automation override wins; an unset sibling falls back to default."""
    # Arrange — override only loop_back_without_asking; the other two are absent
    _write_marshal_with_ceremony(
        plan_context.fixture_dir,
        {'automation': {'loop_back_without_asking': True}},
    )

    # Act
    overridden = cmd_ceremony_policy(_ns(field='automation.loop_back_without_asking'))
    sibling = cmd_ceremony_policy(_ns(field='automation.finalize_without_asking'))

    # Assert — live value wins, missing sibling falls back to canonical default
    assert overridden['value'] is True
    assert sibling['value'] is True  # default preserved


def test_live_gate_override_wins(plan_context):
    """A live planning gate override is reflected by the read."""
    # Arrange
    _write_marshal_with_ceremony(
        plan_context.fixture_dir,
        {'planning': {'deep_lane': 'always'}},
    )

    # Act
    result = cmd_ceremony_policy(_ns(field='planning.deep_lane'))

    # Assert
    assert result['value'] == 'always'


# =============================================================================
# (6) error path
# =============================================================================


def test_unknown_field_returns_field_not_found(plan_context):
    """An unresolvable dotted path returns error_type field_not_found."""
    # Arrange
    _write_marshal_with_ceremony(plan_context.fixture_dir, None)

    # Act
    result = cmd_ceremony_policy(_ns(field='automation.bogus_knob'))

    # Assert
    assert result['status'] == 'error'
    assert result['error_type'] == 'field_not_found'


def test_unknown_top_level_section_returns_field_not_found(plan_context):
    """A dotted path into a non-existent section returns field_not_found."""
    # Arrange
    _write_marshal_with_ceremony(plan_context.fixture_dir, None)

    # Act
    result = cmd_ceremony_policy(_ns(field='nonexistent.path'))

    # Assert
    assert result['status'] == 'error'
    assert result['error_type'] == 'field_not_found'


# =============================================================================
# (7) set verb — write surface for the wizard / operator
# =============================================================================


def test_set_automation_knob_roundtrips(plan_context):
    """`set --field automation.finalize_without_asking --value false` round-trips through get."""
    # Arrange
    _write_marshal_with_ceremony(plan_context.fixture_dir, None)

    # Act — set then get
    set_result = cmd_ceremony_policy(_ns_set('automation.finalize_without_asking', 'false'))
    get_result = cmd_ceremony_policy(_ns(field='automation.finalize_without_asking'))

    # Assert — bool coercion + persistence
    assert set_result['status'] == 'success'
    assert set_result['value'] is False
    assert get_result['value'] is False


def test_set_run_at_all_gate_roundtrips(plan_context):
    """`set --field planning.deep_lane --value always` round-trips through get."""
    # Arrange
    _write_marshal_with_ceremony(plan_context.fixture_dir, None)

    # Act
    set_result = cmd_ceremony_policy(_ns_set('planning.deep_lane', 'always'))
    get_result = cmd_ceremony_policy(_ns(field='planning.deep_lane'))

    # Assert
    assert set_result['status'] == 'success'
    assert set_result['value'] == 'always'
    assert get_result['value'] == 'always'


def test_set_footgun_gate_never_emits_warning(plan_context, capsys):
    """Setting a footgun gate to `never` emits a set-time [WARNING]."""
    # Arrange
    _write_marshal_with_ceremony(plan_context.fixture_dir, None)

    # Act — finalize.qgate is the hard footgun
    result = cmd_ceremony_policy(_ns_set('finalize.qgate', 'never'))

    # Assert — warning surfaced in the return + on stderr
    assert result['status'] == 'success'
    assert result['warnings']
    assert any('finalize.qgate' in w for w in result['warnings'])
    captured = capsys.readouterr()
    assert '[WARNING]' in captured.err


def test_set_rejects_invalid_run_at_all_value(plan_context):
    """An invalid run-at-all value is rejected before persisting."""
    # Arrange
    _write_marshal_with_ceremony(plan_context.fixture_dir, None)

    # Act
    result = cmd_ceremony_policy(_ns_set('finalize.qgate', 'sometimes'))

    # Assert
    assert result['status'] == 'error'
    assert result['error_type'] == 'invalid_value'


def test_set_rejects_non_section_field_path(plan_context):
    """A non `section.field` path is rejected with invalid_field."""
    # Arrange
    _write_marshal_with_ceremony(plan_context.fixture_dir, None)

    # Act — a single-segment path is not settable
    result = cmd_ceremony_policy(_ns_set('automation', 'true'))

    # Assert
    assert result['status'] == 'error'
    assert result['error_type'] == 'invalid_field'


def test_set_rejects_unknown_section(plan_context):
    """A dotted path into an unknown top-level section is rejected with invalid_field."""
    # Arrange
    _write_marshal_with_ceremony(plan_context.fixture_dir, None)

    # Act
    result = cmd_ceremony_policy(_ns_set('bogus.knob', 'true'))

    # Assert
    assert result['status'] == 'error'
    assert result['error_type'] == 'invalid_field'
