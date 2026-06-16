#!/usr/bin/env python3
"""Regression tests for the dissolved ``ceremony_policy`` block (D9).

The ``ceremony_policy`` block — its top-level JSON key, the ``DEFAULT_CEREMONY_POLICY``
seed, the ``validate_ceremony_policy`` validator, the ``CEREMONY_*`` constants, the
footgun catalogues, and the ``overrides[]`` list — was dissolved. Every run-at-all
gate and automation knob was distributed back into the phase block whose decision it
governs:

- ``deep_lane`` / ``escalation``     → ``plan.phase-1-init``
- ``revalidation``                   → ``plan.phase-2-refine``
- ``qgate`` (planning)               → ``plan.phase-3-outline``
- ``self_review`` / ``qgate`` /
  ``simplify``                       → ``plan.phase-6-finalize``
- the three auto-continuation knobs  → ``plan.phase-6-finalize``

This module pins the post-dissolution contract:

1. The ``ceremony_policy`` symbols are gone from ``_config_defaults``.
2. ``get_default_config()`` carries no ``ceremony_policy`` top-level key.
3. Each distributed gate surfaces under its owning phase block with the ``auto``
   default, readable via the standard ``plan phase-<N> get --field <gate>`` path.
4. ``VALID_RUN_AT_ALL`` enumerates exactly ``auto|always|never``.

The handlers are exercised via per-file ``importlib`` loading (the manage-config
test convention).
"""

# ruff: noqa: I001, E402

import importlib.util
import sys
from argparse import Namespace
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
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_config_defaults_mod = _load_module('_config_defaults_for_dissolution_test', '_config_defaults.py')
_cmd_quality_phases_mod = _load_module(
    '_cmd_quality_phases_for_dissolution_test', '_cmd_quality_phases.py'
)
_cmd_init_mod = _load_module('_cmd_init_for_dissolution_test', '_cmd_init.py')

# Import shared infrastructure (conftest.py sets up PYTHONPATH).
import conftest  # noqa: E402, F401

# The distributed run-at-all gates and the phase block each now lives under.
_DISTRIBUTED_GATES = (
    ('phase-1-init', 'deep_lane'),
    ('phase-1-init', 'escalation'),
    ('phase-2-refine', 'revalidation'),
    ('phase-3-outline', 'qgate'),
    ('phase-6-finalize', 'self_review'),
    ('phase-6-finalize', 'qgate'),
    ('phase-6-finalize', 'simplify'),
)


# =============================================================================
# (1) The dissolved ceremony_policy symbols are gone
# =============================================================================


@pytest.mark.parametrize(
    'symbol',
    [
        'DEFAULT_CEREMONY_POLICY',
        'CEREMONY_PLANNING_GATES',
        'CEREMONY_FINALIZE_GATES',
        'CEREMONY_FOOTGUNS',
        'CEREMONY_HARD_FOOTGUNS',
        'VALID_CEREMONY_RUN_AT_ALL',
        'validate_ceremony_policy',
    ],
)
def test_dissolved_ceremony_symbol_is_gone(symbol):
    """No ``CEREMONY_*`` / ``ceremony_policy`` symbol survives in _config_defaults."""
    assert not hasattr(_config_defaults_mod, symbol), (
        f'{symbol} must be gone after the ceremony_policy dissolution'
    )


def test_get_default_config_has_no_ceremony_policy_key():
    """get_default_config() must NOT carry a top-level ceremony_policy block."""
    config = _config_defaults_mod.get_default_config()
    assert 'ceremony_policy' not in config, (
        'ceremony_policy must be absent from get_default_config() after dissolution'
    )


# =============================================================================
# (2) Distributed gates surface under their owning phase block
# =============================================================================


@pytest.mark.parametrize('phase,gate', _DISTRIBUTED_GATES)
def test_distributed_gate_in_default_config(phase, gate):
    """Each run-at-all gate defaults to 'auto' under its owning phase block."""
    config = _config_defaults_mod.get_default_config()
    phase_block = config['plan'][phase]
    assert phase_block.get(gate) == 'auto', (
        f'plan.{phase}.{gate} must default to auto in get_default_config()'
    )


@pytest.mark.parametrize('phase,gate', _DISTRIBUTED_GATES)
def test_distributed_gate_reads_via_phase_get(phase, gate, plan_context):
    """Each gate resolves through the standard ``plan phase-<N> get --field <gate>`` path."""
    # initialize a fresh marshal.json (no gate overrides → default merge)
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # exercise the actual cmd_phase get path the runtime uses
    result = _cmd_quality_phases_mod.cmd_phase(Namespace(verb='get', field=gate), phase)

    # the default merge surfaces 'auto'
    assert result['status'] == 'success'
    assert result['value'] == 'auto'


def test_distributed_gates_not_in_other_phases():
    """A finalize gate must NOT leak into the planning phases and vice versa."""
    config = _config_defaults_mod.get_default_config()
    # self_review is a finalize-only gate; it must not appear in phase-1-init.
    assert 'self_review' not in config['plan']['phase-1-init']
    # deep_lane is a phase-1-init gate; it must not appear in phase-6-finalize.
    assert 'deep_lane' not in config['plan']['phase-6-finalize']


# =============================================================================
# (3) The run-at-all enum survives under its distributed name
# =============================================================================


def test_valid_run_at_all_enumerates_expected_values():
    """VALID_RUN_AT_ALL must enumerate exactly auto|always|never."""
    assert _config_defaults_mod.VALID_RUN_AT_ALL == ('auto', 'always', 'never')


def test_validate_run_at_all_accepts_every_allowed_value():
    """validate_run_at_all accepts each allowed value without raising."""
    for value in _config_defaults_mod.VALID_RUN_AT_ALL:
        _config_defaults_mod.validate_run_at_all(value, 'plan.phase-6-finalize.qgate')


def test_validate_run_at_all_rejects_unknown_value():
    """validate_run_at_all raises ValueError naming the offending knob path."""
    with pytest.raises(ValueError, match=r'plan\.phase-6-finalize\.qgate'):
        _config_defaults_mod.validate_run_at_all('sometimes', 'plan.phase-6-finalize.qgate')
