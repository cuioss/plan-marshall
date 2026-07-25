#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``orchestrator`` effort scope + scalar-knob surface in manage-config.

Covers the sibling ``orchestrator`` block (a peer of ``plan``), added by this plan:

- ``effort read``/``resolve-target --role orchestrator.{surface}`` per-surface
  precedence: surface override -> ``orchestrator.effort.default`` -> ``plan.effort``
  -> ``inherit``.
- The ``orchestrator.effort.max`` uplift ceiling: it clamps a higher resolved
  per-surface level on the ordinal ladder; an unset ``max`` is a no-op.
- The unset-everywhere == today invariant: with no ``orchestrator`` config, every
  surface resolves to ``plan.effort`` exactly as ``effort read --default`` does.
- ``effort set --scope orchestrator[.{surface}|.max]`` round-trips, including the
  scalar-``effort``-string -> object normalisation on a per-surface write.
- ``orchestrator get/set --field parallelization_scope``: round-trip, the
  fail-closed unknown-field rejection, and the int >= 1 validation.
"""

# ruff: noqa: I001, E402

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_effort_mod = _load_module('_cmd_effort_for_orchestrator_scope_test', '_cmd_effort.py')
_cmd_orchestrator_mod = _load_module('_cmd_orchestrator_for_orchestrator_scope_test', '_cmd_orchestrator.py')

cmd_effort = _cmd_effort_mod.cmd_effort
cmd_effort_resolve_target = _cmd_effort_mod.cmd_effort_resolve_target
cmd_effort_set = _cmd_effort_mod.cmd_effort_set
cmd_orchestrator_get = _cmd_orchestrator_mod.cmd_orchestrator_get
cmd_orchestrator_set = _cmd_orchestrator_mod.cmd_orchestrator_set


def _write_marshal(fixture_dir: Path, config: dict) -> Path:
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    return marshal_path


def _read_marshal(fixture_dir: Path) -> dict:
    data: dict = json.loads((fixture_dir / 'marshal.json').read_text(encoding='utf-8'))
    return data


def _read_role(role: str) -> dict:
    result: dict = cmd_effort(Namespace(role=role, phase=None, default=False))
    return result


# =============================================================================
# Per-surface precedence: surface -> default -> plan.effort -> inherit
# =============================================================================


def test_surface_override_wins_over_default(plan_context):
    """A per-surface override wins over the in-block ``default`` slot."""
    _write_marshal(
        plan_context.fixture_dir,
        {'orchestrator': {'effort': {'analyze': 'level-6', 'default': 'level-4'}},
         'plan': {'effort': 'level-2'}},
    )

    result = _read_role('orchestrator.analyze')

    assert result['status'] == 'success'
    assert result['level'] == 'level-6'
    assert result['source'] == 'orchestrator.effort.analyze'
    assert result['role'] == 'orchestrator.analyze'


def test_surface_absent_walks_to_default_slot(plan_context):
    """A surface with no override walks to the ``default`` slot."""
    _write_marshal(
        plan_context.fixture_dir,
        {'orchestrator': {'effort': {'analyze': 'level-6', 'default': 'level-4'}},
         'plan': {'effort': 'level-2'}},
    )

    for surface in ('decompose', 'reader'):
        result = _read_role(f'orchestrator.{surface}')
        assert result['status'] == 'success'
        assert result['level'] == 'level-4', f'{surface} should resolve to the default slot'
        assert result['source'] == 'orchestrator.effort.default'


def test_bare_orchestrator_resolves_default_slot(plan_context):
    """A bare ``--role orchestrator`` lookup resolves via the ``default`` slot."""
    _write_marshal(
        plan_context.fixture_dir,
        {'orchestrator': {'effort': {'default': 'level-4'}}, 'plan': {'effort': 'level-2'}},
    )

    result = _read_role('orchestrator')

    assert result['status'] == 'success'
    assert result['level'] == 'level-4'
    assert result['source'] == 'orchestrator.effort.default'
    assert result['role'] == 'orchestrator'


def test_surface_and_default_absent_falls_through_to_plan_effort(plan_context):
    """A surface absent AND no default slot falls through to ``plan.effort``."""
    _write_marshal(
        plan_context.fixture_dir,
        {'orchestrator': {'effort': {'decompose': 'level-5'}}, 'plan': {'effort': 'level-2'}},
    )

    result = _read_role('orchestrator.analyze')

    assert result['status'] == 'success'
    assert result['level'] == 'level-2'
    assert result['source'] == 'plan.effort'
    # the configured surface still resolves to its own value
    other = _read_role('orchestrator.decompose')
    assert other['level'] == 'level-5'
    assert other['source'] == 'orchestrator.effort.decompose'


def test_string_shorthand_applies_to_every_surface(plan_context):
    """A scalar ``orchestrator.effort`` string applies to every surface."""
    _write_marshal(
        plan_context.fixture_dir,
        {'orchestrator': {'effort': 'level-6'}, 'plan': {'effort': 'level-2'}},
    )

    for surface in ('analyze', 'decompose', 'reader'):
        result = _read_role(f'orchestrator.{surface}')
        assert result['status'] == 'success'
        assert result['level'] == 'level-6'
        assert result['source'] == 'orchestrator.effort'


def test_no_plan_effort_resolves_inherit(plan_context):
    """With no orchestrator config AND no plan.effort, a surface resolves to inherit."""
    _write_marshal(plan_context.fixture_dir, {})

    result = _read_role('orchestrator.analyze')

    assert result['status'] == 'success'
    assert result['level'] == 'inherit'
    assert result['source'] == 'implicit_default'


def test_unknown_surface_is_rejected(plan_context):
    """An unregistered orchestrator surface is rejected."""
    _write_marshal(plan_context.fixture_dir, {'orchestrator': {'effort': {'default': 'level-4'}}})

    result = _read_role('orchestrator.bogus')

    assert result['status'] == 'error'
    assert 'bogus' in result['error']


# =============================================================================
# max ceiling clamp
# =============================================================================


def test_max_clamps_a_higher_surface_level(plan_context):
    """``max`` clamps a resolved per-surface level that exceeds the ceiling."""
    _write_marshal(
        plan_context.fixture_dir,
        {'orchestrator': {'effort': {'analyze': 'level-7', 'max': 'level-4'}}},
    )

    result = _read_role('orchestrator.analyze')

    assert result['status'] == 'success'
    assert result['level'] == 'level-4', 'level-7 must clamp down to the level-4 ceiling'
    assert result['source'] == 'orchestrator.effort.max (clamp)'


def test_max_clamps_the_default_slot_resolution(plan_context):
    """The clamp applies to a value resolved through the default slot too."""
    _write_marshal(
        plan_context.fixture_dir,
        {'orchestrator': {'effort': {'default': 'level-7', 'max': 'level-3'}}},
    )

    result = _read_role('orchestrator.decompose')

    assert result['status'] == 'success'
    assert result['level'] == 'level-3'
    assert result['source'] == 'orchestrator.effort.max (clamp)'


def test_max_is_a_noop_when_resolved_below_ceiling(plan_context):
    """``max`` does not raise a level that already sits below the ceiling."""
    _write_marshal(
        plan_context.fixture_dir,
        {'orchestrator': {'effort': {'analyze': 'level-2', 'max': 'level-5'}}},
    )

    result = _read_role('orchestrator.analyze')

    assert result['status'] == 'success'
    assert result['level'] == 'level-2', 'a level below the ceiling is unchanged'
    assert result['source'] == 'orchestrator.effort.analyze'


def test_unset_max_is_a_noop(plan_context):
    """With ``max`` unset, a high per-surface level is returned unclamped."""
    _write_marshal(
        plan_context.fixture_dir,
        {'orchestrator': {'effort': {'analyze': 'level-7'}}},
    )

    result = _read_role('orchestrator.analyze')

    assert result['status'] == 'success'
    assert result['level'] == 'level-7'
    assert result['source'] == 'orchestrator.effort.analyze'


def test_invalid_max_level_is_rejected(plan_context):
    """An invalid ``max`` level keyword surfaces as an error."""
    _write_marshal(
        plan_context.fixture_dir,
        {'orchestrator': {'effort': {'analyze': 'level-5', 'max': 'level-99'}}},
    )

    result = _read_role('orchestrator.analyze')

    assert result['status'] == 'error'
    assert 'orchestrator.effort.max' in result['error']


# =============================================================================
# unset-everywhere == today invariant
# =============================================================================


def test_unset_orchestrator_resolves_identically_to_default(plan_context):
    """With ``orchestrator`` unset, every surface resolves to ``plan.effort`` == today.

    The `effort read --default` short-circuit is exactly what the three
    orchestrator dispatch surfaces used before this plan; the unset invariant is
    that each surface now resolves to the same level.
    """
    _write_marshal(plan_context.fixture_dir, {'plan': {'effort': 'level-3'}})

    default_result = cmd_effort(Namespace(role=None, phase=None, default=True))
    assert default_result['level'] == 'level-3'

    for surface in ('analyze', 'decompose', 'reader'):
        result = _read_role(f'orchestrator.{surface}')
        assert result['status'] == 'success'
        assert result['level'] == default_result['level']
        assert result['source'] == 'plan.effort'


def test_empty_orchestrator_block_falls_through_to_plan_effort(plan_context):
    """An explicit empty ``orchestrator: {}`` block is inert — falls through to plan.effort."""
    _write_marshal(
        plan_context.fixture_dir,
        {'orchestrator': {}, 'plan': {'effort': 'level-3'}},
    )

    result = _read_role('orchestrator.reader')

    assert result['status'] == 'success'
    assert result['level'] == 'level-3'
    assert result['source'] == 'plan.effort'


# =============================================================================
# resolve-target
# =============================================================================


def test_resolve_target_returns_variant_name(plan_context):
    """``resolve-target --role orchestrator.analyze`` returns the level variant."""
    _write_marshal(
        plan_context.fixture_dir,
        {'orchestrator': {'effort': {'analyze': 'level-5'}}},
    )

    result = cmd_effort_resolve_target(
        Namespace(role='orchestrator.analyze', phase=None, default=False)
    )

    assert result['status'] == 'success'
    assert result['level'] == 'level-5'
    assert result['target'] == 'execution-context-level-5'


def test_resolve_target_inherit_returns_canonical(plan_context):
    """A surface resolving to inherit maps to the canonical execution-context."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_effort_resolve_target(
        Namespace(role='orchestrator.decompose', phase=None, default=False)
    )

    assert result['status'] == 'success'
    assert result['level'] == 'inherit'
    assert result['target'] == 'execution-context'


# =============================================================================
# effort set --scope orchestrator[.{surface}|.max]
# =============================================================================


def test_set_scope_orchestrator_scalar_shorthand(plan_context):
    """``--scope orchestrator`` writes the scalar shorthand ``orchestrator.effort``."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_effort_set(Namespace(scope='orchestrator', level='level-4'))

    assert result['status'] == 'success'
    assert result['target'] == 'orchestrator.effort'
    config = _read_marshal(plan_context.fixture_dir)
    assert config['orchestrator']['effort'] == 'level-4'


def test_set_scope_orchestrator_surface_creates_object(plan_context):
    """``--scope orchestrator.analyze`` creates the effort object with the surface key."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_effort_set(Namespace(scope='orchestrator.analyze', level='level-5'))

    assert result['status'] == 'success'
    assert result['target'] == 'orchestrator.effort.analyze'
    config = _read_marshal(plan_context.fixture_dir)
    assert config['orchestrator']['effort'] == {'analyze': 'level-5'}


def test_set_scope_orchestrator_max(plan_context):
    """``--scope orchestrator.max`` writes the uplift ceiling."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_effort_set(Namespace(scope='orchestrator.max', level='level-4'))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    assert config['orchestrator']['effort'] == {'max': 'level-4'}


def test_set_scope_orchestrator_surface_normalises_scalar_into_object(plan_context):
    """A per-surface write normalises a pre-existing scalar effort into an object.

    The prior scalar value is seeded into the ``default`` slot so the write does
    not silently drop it, and sibling sub-keys survive.
    """
    _write_marshal(
        plan_context.fixture_dir,
        {'orchestrator': {'effort': 'level-3'}},
    )

    result = cmd_effort_set(Namespace(scope='orchestrator.analyze', level='level-6'))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    assert config['orchestrator']['effort'] == {'default': 'level-3', 'analyze': 'level-6'}


def test_set_scope_orchestrator_surface_preserves_siblings(plan_context):
    """A per-surface write preserves sibling sub-keys already in the object."""
    _write_marshal(
        plan_context.fixture_dir,
        {'orchestrator': {'effort': {'analyze': 'level-6', 'max': 'level-7'}}},
    )

    result = cmd_effort_set(Namespace(scope='orchestrator.decompose', level='level-5'))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    assert config['orchestrator']['effort'] == {
        'analyze': 'level-6',
        'max': 'level-7',
        'decompose': 'level-5',
    }


def test_set_scope_orchestrator_unknown_subkey_rejected(plan_context):
    """An unwritable ``orchestrator.<key>`` scope is rejected."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_effort_set(Namespace(scope='orchestrator.bogus', level='level-5'))

    assert result['status'] == 'error'
    assert 'bogus' in result['error']


def test_set_scope_orchestrator_invalid_level_rejected(plan_context):
    """An invalid level keyword is rejected on an orchestrator write."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_effort_set(Namespace(scope='orchestrator.analyze', level='level-99'))

    assert result['status'] == 'error'


def test_set_scope_orchestrator_round_trips_through_read(plan_context):
    """A written surface override reads back at the same level."""
    _write_marshal(plan_context.fixture_dir, {})

    set_result = cmd_effort_set(Namespace(scope='orchestrator.reader', level='level-5'))
    assert set_result['status'] == 'success'

    read_result = _read_role('orchestrator.reader')
    assert read_result['status'] == 'success'
    assert read_result['level'] == 'level-5'


# =============================================================================
# orchestrator get/set --field parallelization_scope
# =============================================================================


def test_orchestrator_set_parallelization_scope_round_trips(plan_context):
    """``orchestrator set --field parallelization_scope`` persists an int >= 1."""
    _write_marshal(plan_context.fixture_dir, {})

    set_result = cmd_orchestrator_set(
        Namespace(field='parallelization_scope', value='3')
    )

    assert set_result['status'] == 'success'
    assert set_result['value'] == 3
    config = _read_marshal(plan_context.fixture_dir)
    assert config['orchestrator']['parallelization_scope'] == 3

    get_result = cmd_orchestrator_get(Namespace(field='parallelization_scope'))
    assert get_result['status'] == 'success'
    assert get_result['value'] == 3
    assert get_result['set'] is True


def test_orchestrator_get_unset_reports_none(plan_context):
    """``orchestrator get`` on an unset field reports value None and set False."""
    _write_marshal(plan_context.fixture_dir, {})

    get_result = cmd_orchestrator_get(Namespace(field='parallelization_scope'))

    assert get_result['status'] == 'success'
    assert get_result['value'] is None
    assert get_result['set'] is False


def test_orchestrator_set_unknown_field_is_rejected(plan_context):
    """An unknown scalar field fails closed rather than persisting silently."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_orchestrator_set(Namespace(field='bogus_knob', value='1'))

    assert result['status'] == 'error'
    assert result.get('error_type') == 'unknown_field'
    # nothing was persisted
    config = _read_marshal(plan_context.fixture_dir)
    assert 'orchestrator' not in config or 'bogus_knob' not in config.get('orchestrator', {})


def test_orchestrator_get_unknown_field_is_rejected(plan_context):
    """``orchestrator get`` on an unknown field also fails closed."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_orchestrator_get(Namespace(field='bogus_knob'))

    assert result['status'] == 'error'
    assert result.get('error_type') == 'unknown_field'


def test_orchestrator_set_parallelization_scope_rejects_zero(plan_context):
    """``parallelization_scope`` must be >= 1 — zero is rejected."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_orchestrator_set(Namespace(field='parallelization_scope', value='0'))

    assert result['status'] == 'error'


def test_orchestrator_set_parallelization_scope_rejects_negative(plan_context):
    """A negative ``parallelization_scope`` is rejected."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_orchestrator_set(Namespace(field='parallelization_scope', value='-2'))

    assert result['status'] == 'error'


def test_orchestrator_set_parallelization_scope_rejects_non_int(plan_context):
    """A non-integer ``parallelization_scope`` is rejected."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_orchestrator_set(Namespace(field='parallelization_scope', value='abc'))

    assert result['status'] == 'error'


def test_orchestrator_set_parallelization_scope_accepts_one(plan_context):
    """The minimum valid ``parallelization_scope`` (1) is accepted."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_orchestrator_set(Namespace(field='parallelization_scope', value='1'))

    assert result['status'] == 'success'
    assert result['value'] == 1
