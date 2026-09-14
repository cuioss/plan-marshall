#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the steward per-level pin materialization step.

The pin step reads the machine-local effort-to-model map and emits one pin
per level for open-model-set harnesses. This suite pins the behavior the
steward menu depends on:

- Materializing twice over the same map yields identical pins
  (idempotent re-run).
- Both entry kinds materialize: a ``local`` entry yields its model, a
  ``provider`` entry yields its route.
- A level the map does not pin resolves to ``inherit``.
- An entry ranked above its level never promotes it — the guard holds the
  level at ``inherit`` and counts the hit.
- A malformed map fails closed with an error TOON and emits no pins.
- The Claude harness returns untouched and emits no pins.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

effort_pins = load_script_module(
    'plan-marshall', 'marshall-steward', 'effort_pins.py', module_name='effort_pins'
)


def _write_map(tmp_path: Path, payload: dict) -> str:
    map_file = tmp_path / 'effort-pins.json'
    map_file.write_text(json.dumps(payload), encoding='utf-8')
    return str(map_file)


def _good_map() -> dict:
    return {
        'pins': {
            'level-2': {'kind': 'local', 'model': 'local-model-a'},
            'level-4': {'kind': 'provider', 'route': 'zen/route-r'},
        }
    }


# =============================================================================
# Round-trip stability (idempotent re-run)
# =============================================================================


def test_materialize_twice_yields_identical_pins(tmp_path):
    """Materializing twice over the same map emits byte-identical pins."""
    # Arrange
    data = _good_map()

    # Act
    first, _ = effort_pins.materialize_levels(data)
    second, _ = effort_pins.materialize_levels(data)

    # Assert
    assert first == second
    assert first['level-2'] == 'local-model-a'
    assert first['level-4'] == 'zen/route-r'


# =============================================================================
# Both entry kinds materialize
# =============================================================================


def test_local_entry_yields_its_model():
    """A ``local`` entry provisions its model on its own level."""
    # Arrange
    data = {'pins': {'level-3': {'kind': 'local', 'model': 'local-model-b'}}}

    # Act
    pins, guard_hits = effort_pins.materialize_levels(data)

    # Assert
    assert pins['level-3'] == 'local-model-b'
    assert guard_hits == 0


def test_provider_entry_yields_its_route():
    """A ``provider`` entry provisions its route on its own level."""
    # Arrange
    data = {'pins': {'level-5': {'kind': 'provider', 'route': 'go/route-g'}}}

    # Act
    pins, guard_hits = effort_pins.materialize_levels(data)

    # Assert
    assert pins['level-5'] == 'go/route-g'
    assert guard_hits == 0


# =============================================================================
# Unpinned level resolves to inherit
# =============================================================================


def test_unpinned_level_resolves_to_inherit():
    """Levels the map does not pin dispatch on the session model."""
    # Arrange
    data = _good_map()

    # Act
    pins, _ = effort_pins.materialize_levels(data)

    # Assert
    assert pins['level-1'] == 'inherit'
    assert pins['level-3'] == 'inherit'
    assert pins['level-7'] == 'inherit'


def test_empty_map_resolves_everything_to_inherit():
    """A map with no pins leaves every level on the session model."""
    # Act
    pins, guard_hits = effort_pins.materialize_levels({'pins': {}})

    # Assert
    assert set(pins) == set(effort_pins.LEVELS)
    assert all(model == 'inherit' for model in pins.values())
    assert guard_hits == 0


# =============================================================================
# Never-escalate guard
# =============================================================================


def test_rank_above_rung_holds_level_at_inherit():
    """An entry ranked above its level never promotes the level."""
    # Arrange
    data = {
        'pins': {
            'level-1': {'kind': 'local', 'model': 'big-model', 'capability_rank': 6},
        }
    }

    # Act
    pins, guard_hits = effort_pins.materialize_levels(data)

    # Assert
    assert pins['level-1'] == 'inherit'
    assert guard_hits == 1


def test_rank_at_rung_provisions_normally():
    """An entry ranked at its own level provisions without a guard hit."""
    # Arrange
    data = {
        'pins': {
            'level-2': {'kind': 'local', 'model': 'local-model-a', 'capability_rank': 1},
        }
    }

    # Act
    pins, guard_hits = effort_pins.materialize_levels(data)

    # Assert
    assert pins['level-2'] == 'local-model-a'
    assert guard_hits == 0


# =============================================================================
# Schema fail-closed (malformed map → error TOON, no pins)
# =============================================================================


def test_validate_rejects_entry_missing_kind():
    """An entry without a usable kind is invalid, exactly as an absent one."""
    # Arrange
    data = {'pins': {'level-2': {'model': 'local-model-a'}}}

    # Act
    ok, errors = effort_pins.validate_map_data(data)

    # Assert
    assert not ok
    assert any('level-2' in error for error in errors)


def test_validate_rejects_local_entry_missing_model():
    """A ``local`` entry without a model is invalid."""
    # Arrange
    data = {'pins': {'level-2': {'kind': 'local'}}}

    # Act
    ok, errors = effort_pins.validate_map_data(data)

    # Assert
    assert not ok
    assert any('model' in error for error in errors)


def test_materialize_cli_fails_closed_on_malformed_map(tmp_path):
    """A malformed map yields an error TOON and emits no pins."""
    # Arrange
    map_path = _write_map(tmp_path, {'pins': {'level-2': {'kind': 'local'}}})
    script = get_script_path('plan-marshall', 'marshall-steward', 'effort_pins.py')

    # Act
    result = run_script(script, 'materialize', '--map-path', map_path)

    # Assert
    assert result.success
    payload = result.toon()
    assert payload['status'] == 'error'
    assert payload['error'] == 'map_schema_invalid'
    assert 'pins' not in payload


# =============================================================================
# Claude harness guard
# =============================================================================


def test_claude_harness_returns_untouched(tmp_path):
    """The Claude target flow is never modified by pin materialization."""
    # Arrange
    map_path = _write_map(tmp_path, _good_map())
    script = get_script_path('plan-marshall', 'marshall-steward', 'effort_pins.py')

    # Act
    result = run_script(script, 'materialize', '--map-path', map_path, '--harness', 'claude')

    # Assert
    assert result.success
    payload = result.toon()
    assert payload['status'] == 'success'
    assert payload['untouched'] is True
    assert 'pins' not in payload


# =============================================================================
# TOON output contract over the CLI boundary
# =============================================================================


def test_materialize_cli_emits_toon_contract(tmp_path):
    """The open-harness materialize run emits the documented TOON contract."""
    # Arrange
    map_path = _write_map(tmp_path, _good_map())
    script = get_script_path('plan-marshall', 'marshall-steward', 'effort_pins.py')

    # Act
    result = run_script(script, 'materialize', '--map-path', map_path, '--harness', 'open')

    # Assert
    assert result.success
    payload = result.toon()
    assert payload['status'] == 'success'
    assert payload['materialized_count'] == 2
    assert payload['inherit_count'] == 5
    assert payload['guard_hits'] == 0
    assert 'level-2=local-model-a' in payload['pins']
    assert 'level-4=zen/route-r' in payload['pins']
    assert 'level-1=inherit' in payload['pins']
