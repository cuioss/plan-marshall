#!/usr/bin/env python3
"""6-axis canonical-identifier rejection tests for ``phase_handshake.py``.

Covers the canonical identifier flags declared by the script:

* ``--plan-id`` (capture, verify, list, clear) — validated via
  ``add_plan_id_arg`` → ``validate_plan_id`` (PLAN_ID_RE).
* ``--phase`` (capture, verify, clear) — validated via ``add_phase_arg``
  using ``choices=PHASES``. argparse's invalid-choice error message
  starts with ``argument --phase:`` so ``parse_args_with_toon_errors``
  translates it into the canonical ``invalid_phase`` TOON contract.

Re-uses ``test/plan-marshall/_input_validation_fixtures.py`` for the
canonical 6-axis matrix (TASK-2 foundation).
"""

from __future__ import annotations

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from _input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
    assert_not_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')

# Subcommands that declare ``--plan-id`` (all four).
_PLAN_ID_SUBCOMMANDS = ('capture', 'verify', 'list', 'clear')

# Subcommands that declare ``--phase`` (capture, verify, clear — list does NOT).
_PHASE_SUBCOMMANDS = ('capture', 'verify', 'clear')


# =============================================================================
# --plan-id rejection-path tests (parametrized across all four subcommands)
# =============================================================================


@pytest.mark.parametrize('subcommand', _PLAN_ID_SUBCOMMANDS)
@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_plan_id_rejected_per_subcommand(subcommand, axis, bad_value):
    """Each malformed --plan-id axis must surface invalid_plan_id on stdout TOON.

    The validator runs at parse time, before any handshake-store I/O,
    so we don't need to set up plan directories.
    """
    args = [subcommand, '--plan-id', bad_value]
    if subcommand in _PHASE_SUBCOMMANDS:
        # ``capture``, ``verify``, ``clear`` all require --phase too.
        # Use a canonical phase value so the failure is unambiguously
        # attributed to --plan-id (and not to a missing required arg).
        args += ['--phase', HAPPY_VALUES['phase']]

    result = run_script(SCRIPT_PATH, *args)
    assert_invalid_field(result, 'invalid_plan_id')


# =============================================================================
# --phase rejection-path tests (parametrized across capture/verify/clear)
# =============================================================================


@pytest.mark.parametrize('subcommand', _PHASE_SUBCOMMANDS)
@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['phase'])
def test_phase_rejected_per_subcommand(subcommand, axis, bad_value):
    """Each malformed --phase axis must surface invalid_phase on stdout TOON.

    ``add_phase_arg`` uses ``choices=PHASES`` rather than a regex
    ``type=`` validator. The argparse invalid-choice message starts
    with ``argument --phase:`` so ``parse_args_with_toon_errors``
    correctly maps it to ``invalid_phase`` (per
    ``_FLAG_TO_ERROR_CODE`` in input_validation.py).
    """
    result = run_script(
        SCRIPT_PATH,
        subcommand,
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--phase',
        bad_value,
    )
    assert_invalid_field(result, 'invalid_phase')


def test_phase_invalid_kebab_string_also_rejected():
    """A plausible-looking-but-not-canonical phase id (e.g. ``invalid-phase``)
    is rejected by argparse's choices constraint.

    This documents the contract independently of the malformed-axis
    matrix above: ``invalid-phase`` is the example called out in the
    task description and must surface ``invalid_phase`` on stdout
    TOON, not argparse's exit-2 stderr error.
    """
    result = run_script(
        SCRIPT_PATH,
        'capture',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--phase',
        'invalid-phase',
    )
    assert_invalid_field(result, 'invalid_phase')


# =============================================================================
# Happy-path: canonical inputs MUST NOT trigger the validators
# =============================================================================


@pytest.mark.parametrize('subcommand', _PHASE_SUBCOMMANDS)
def test_canonical_inputs_dont_trigger_invalid_field(subcommand, tmp_path):
    """Canonical --plan-id + --phase MUST NOT report invalid_plan_id/invalid_phase.

    The script will likely fail with another error (no plan dir, no
    handshake row, etc.), but it MUST NOT mis-attribute the failure to
    the canonical identifier validators.
    """
    result = run_script(
        SCRIPT_PATH,
        subcommand,
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--phase',
        HAPPY_VALUES['phase'],
        env_overrides={'PLAN_BASE_DIR': str(tmp_path)},
    )
    assert_not_invalid_field(result, 'invalid_plan_id')
    assert_not_invalid_field(result, 'invalid_phase')


def test_list_subcommand_canonical_plan_id(tmp_path):
    """``list`` accepts only --plan-id; happy-path must pass the validator."""
    result = run_script(
        SCRIPT_PATH,
        'list',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        env_overrides={'PLAN_BASE_DIR': str(tmp_path)},
    )
    assert_not_invalid_field(result, 'invalid_plan_id')
