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
        validate_orchestrator_block({'auto_emit': True})


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
# get_default_config self-validation
# =============================================================================


def test_get_default_config_self_validation_is_clean():
    """get_default_config() runs the orchestrator self-validation without raising."""
    config = _config_defaults_mod.get_default_config()
    # the seeded block is present, empty, and passes its own validator
    assert config['orchestrator'] == {}
    validate_orchestrator_block(config['orchestrator'])


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
