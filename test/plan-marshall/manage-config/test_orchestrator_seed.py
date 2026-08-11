#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``orchestrator`` block validator + canonical key-order placement.

Covers the seed-side surface added by this plan:

- ``validate_orchestrator_block``: an empty block is legal; a populated block's
  ``effort`` (string OR surface object over the known keys, each a valid level)
  and ``parallelization_scope`` (int >= 1) shapes are checked; unknown keys, bad
  effort levels, and non-int / ``< 1`` scopes are rejected.
- ``CANONICAL_TOP_LEVEL_KEY_ORDER`` places ``orchestrator`` immediately after
  ``plan``, and ``order_config_keys`` emits it there.
"""

# ruff: noqa: I001, E402

import importlib.util
import sys
from pathlib import Path

import pytest

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


_config_defaults_mod = _load_module('_config_defaults_for_orchestrator_seed_test', '_config_defaults.py')
_config_core_mod = _load_module('_config_core_for_orchestrator_seed_test', '_config_core.py')

validate_orchestrator_block = _config_defaults_mod.validate_orchestrator_block


# =============================================================================
# validate_orchestrator_block — legal shapes
# =============================================================================


def test_empty_block_is_legal():
    """An empty ``{}`` orchestrator block passes validation."""
    validate_orchestrator_block({})  # must not raise


def test_string_shorthand_effort_is_legal():
    """A scalar effort string is a legal effort shorthand."""
    validate_orchestrator_block({'effort': 'level-5'})


def test_object_effort_over_known_keys_is_legal():
    """An effort object over the known surfaces + default + max is legal."""
    validate_orchestrator_block(
        {'effort': {'analyze': 'level-6', 'decompose': 'level-4', 'reader': 'level-5',
                    'default': 'level-3', 'max': 'level-7'}}
    )


def test_parallelization_scope_positive_int_is_legal():
    """A ``parallelization_scope`` int >= 1 is legal."""
    validate_orchestrator_block({'parallelization_scope': 1})
    validate_orchestrator_block({'parallelization_scope': 8})


def test_fully_populated_block_is_legal():
    """A block carrying both effort and parallelization_scope is legal."""
    validate_orchestrator_block(
        {'effort': {'analyze': 'level-6', 'max': 'level-5'}, 'parallelization_scope': 3}
    )


def test_inherit_is_a_legal_effort_level():
    """``inherit`` is an accepted effort level keyword."""
    validate_orchestrator_block({'effort': 'inherit'})
    validate_orchestrator_block({'effort': {'default': 'inherit'}})


def test_auto_emit_bool_is_legal():
    """``auto_emit`` as a bool is a legal scalar knob (merged PLAN-48 field)."""
    validate_orchestrator_block({'auto_emit': True})
    validate_orchestrator_block({'auto_emit': False})


# =============================================================================
# validate_orchestrator_block — rejected shapes
# =============================================================================


def test_non_dict_block_is_rejected():
    """A non-dict orchestrator block is rejected."""
    with pytest.raises(ValueError, match='expected a dict'):
        validate_orchestrator_block('level-5')


def test_unknown_top_level_key_is_rejected():
    """An unknown key in the orchestrator block is rejected (fail-closed)."""
    with pytest.raises(ValueError, match='orchestrator block keys'):
        validate_orchestrator_block({'bogus_knob': True})


def test_auto_emit_non_bool_is_rejected():
    """A non-bool ``auto_emit`` is rejected (fail-closed)."""
    with pytest.raises(ValueError, match='orchestrator.auto_emit'):
        validate_orchestrator_block({'auto_emit': 'yes'})


def test_bad_effort_string_level_is_rejected():
    """A malformed scalar effort level keyword is rejected."""
    with pytest.raises(ValueError, match='orchestrator.effort'):
        validate_orchestrator_block({'effort': 'level-99'})


def test_bad_effort_object_level_is_rejected():
    """A malformed per-surface effort level is rejected."""
    with pytest.raises(ValueError, match='orchestrator.effort.analyze'):
        validate_orchestrator_block({'effort': {'analyze': 'turbo'}})


def test_unknown_effort_object_key_is_rejected():
    """An unknown key inside the effort object is rejected."""
    with pytest.raises(ValueError, match='orchestrator.effort keys'):
        validate_orchestrator_block({'effort': {'bogus': 'level-5'}})


def test_effort_non_string_non_dict_is_rejected():
    """An effort value that is neither a string nor a dict is rejected."""
    with pytest.raises(ValueError, match='orchestrator.effort'):
        validate_orchestrator_block({'effort': 5})


def test_parallelization_scope_zero_is_rejected():
    """``parallelization_scope`` of 0 is rejected (must be >= 1)."""
    with pytest.raises(ValueError, match='parallelization_scope'):
        validate_orchestrator_block({'parallelization_scope': 0})


def test_parallelization_scope_negative_is_rejected():
    """A negative ``parallelization_scope`` is rejected."""
    with pytest.raises(ValueError, match='parallelization_scope'):
        validate_orchestrator_block({'parallelization_scope': -1})


def test_parallelization_scope_non_int_is_rejected():
    """A non-int ``parallelization_scope`` is rejected."""
    with pytest.raises(ValueError, match='parallelization_scope'):
        validate_orchestrator_block({'parallelization_scope': '3'})


def test_parallelization_scope_bool_is_rejected():
    """A bool ``parallelization_scope`` is rejected even though bool is an int subclass."""
    with pytest.raises(ValueError, match='parallelization_scope'):
        validate_orchestrator_block({'parallelization_scope': True})


# =============================================================================
# get_default_config self-validation + default-surfacing (D5a)
# =============================================================================


def test_get_default_config_self_validation_is_clean():
    """get_default_config() runs the orchestrator self-validation without raising."""
    config = _config_defaults_mod.get_default_config()
    validate_orchestrator_block(config['orchestrator'])


def test_seed_surfaces_every_orchestrator_knob():
    """The seeded orchestrator block materialises every settable knob (D5a).

    This assertion FAILS against the old ``{'auto_emit': False}`` seed — it pins
    the surfacing fix, not the defect. Each knob a reader can set must appear in
    the seeded file with its effective default so it is discoverable; a knob
    present in code but absent from the seed is a default-surfacing gap
    (recipe-marshal-json-config-audit Aspect 1).
    """
    orch = _config_defaults_mod.get_default_config()['orchestrator']
    # Field-set completeness, DERIVED from the authoritative key set rather than a
    # hard-coded mirror: every key the block supports must be seeded, so a future
    # key added to ORCHESTRATOR_KNOWN_KEYS but not to DEFAULT_ORCHESTRATOR fails
    # here. This is the live default-surfacing guard — a hard-coded list would pass
    # trivially until a developer remembered to update it.
    assert set(orch) == set(_config_defaults_mod.ORCHESTRATOR_KNOWN_KEYS)
    # Effective-default assertions, kept separate from the field-set check:
    # auto_emit safe-posture False, effort an empty (behaviourally-inert) object,
    # scope its default of 1.
    assert orch == {'auto_emit': False, 'effort': {}, 'parallelization_scope': 1}
    validate_orchestrator_block(orch)


def test_orchestrator_known_keys_is_the_authoritative_nonempty_source():
    """ORCHESTRATOR_KNOWN_KEYS is the single, non-empty source of valid block keys.

    ``validate_orchestrator_block`` and the seed-completeness tests both derive
    from it, so it must be non-empty — a vacuous set would make those derived
    checks pass trivially (the non-vacuity guard). Its exact CONTENT is pinned
    WITHOUT a hard-coded mirror here: ``test_seed_surfaces_every_orchestrator_knob``
    asserts ``set(orch) == set(ORCHESTRATOR_KNOWN_KEYS)`` and separately pins the
    seed's keys via its value assertion, so the known-key set is fixed
    transitively. This test guards only what that transitive pin does not: the set
    is non-empty, and the validator actually derives its whitelist from it.
    """
    known = _config_defaults_mod.ORCHESTRATOR_KNOWN_KEYS
    assert known, 'ORCHESTRATOR_KNOWN_KEYS must be non-empty (non-vacuity guard)'
    # No `set(known) == {literal}` assertion here — that would be a second
    # hard-coded mirror of the key set. The content is pinned transitively by the
    # seed-completeness + seed-value assertions in the tests above.
    # A key outside the authoritative set is rejected by the validator that derives
    # its whitelist from it.
    with pytest.raises(ValueError, match='orchestrator block keys'):
        validate_orchestrator_block({'not_a_known_key': 1})


def test_validation_accepts_both_seeded_and_legacy_shapes():
    """Both the newly-seeded shape and a genuine legacy block validate (D5c).

    ``{'auto_emit': False}`` is the exact shape a pre-materialisation ``init``
    wrote, so it is a real legacy fixture, not a synthesised omission. An existing
    consumer's file must not become invalid: the validator accepts a block missing
    ``effort`` / ``parallelization_scope`` exactly as it accepts the fully-seeded
    block.
    """
    validate_orchestrator_block(
        _config_defaults_mod.get_default_config()['orchestrator']
    )  # newly-seeded shape
    validate_orchestrator_block({'auto_emit': False})  # genuine legacy shape


# =============================================================================
# Canonical key-order placement
# =============================================================================


def test_orchestrator_ordered_immediately_after_plan_in_canonical_order():
    """``orchestrator`` sits immediately after ``plan`` in the canonical key order."""
    order = _config_core_mod.CANONICAL_TOP_LEVEL_KEY_ORDER
    assert 'orchestrator' in order
    assert 'plan' in order
    assert order.index('orchestrator') == order.index('plan') + 1


def test_order_config_keys_emits_orchestrator_after_plan():
    """``order_config_keys`` places ``orchestrator`` right after ``plan``.

    A scrambled input with ``orchestrator`` ahead of ``plan`` is re-keyed so
    ``plan`` precedes ``orchestrator`` and both precede the trailing keys.
    """
    scrambled = {'system': {}, 'orchestrator': {}, 'plan': {}, 'build': {}}

    ordered = list(_config_core_mod.order_config_keys(scrambled).keys())

    assert ordered.index('plan') < ordered.index('orchestrator')
    assert ordered.index('orchestrator') < ordered.index('build')
    assert ordered.index('orchestrator') == ordered.index('plan') + 1
