#!/usr/bin/env python3
"""6-axis canonical-identifier rejection tests for ``phase_handshake.py``.

Covers the canonical identifier flags declared by the script:

* ``--plan-id`` (capture, verify, list, clear) — validated via
  ``add_plan_id_arg`` → ``validate_plan_id`` (PLAN_ID_RE).
* ``--phase`` (capture, verify, clear) — validated via ``add_phase_arg``
  using ``choices=PHASES``. argparse's invalid-choice error message
  starts with ``argument --phase:`` so ``parse_args_with_toon_errors``
  translates it into the canonical ``invalid_phase`` TOON contract.

Re-uses ``test/plan-marshall/_pm_input_validation_fixtures.py`` for the
canonical 6-axis matrix (TASK-2 foundation).
"""

from __future__ import annotations

import sys

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from _pm_input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
    assert_not_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')

# Bootstrap the script dir so the underscore-prefixed sibling modules
# (_invariants) are importable for the retained-vs-relaxed behaviour tests.
_SCRIPTS_DIR = SCRIPT_PATH.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _invariants as inv  # type: ignore[import-not-found]  # noqa: E402

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

    Isolation note: ``capture`` fans out to ~10 invariant-capture
    subprocesses (``_invariants.capture_all`` → ``manage-*`` via the
    executor, plus ``git`` on the main checkout). ``_repo_root()`` and
    ``git_main_checkout_root()`` both fall back to the *process cwd* when
    ``PLAN_BASE_DIR`` does not resolve to the canonical ``.../​.plan/local``
    shape — which is exactly the case here (the env points at ``tmp_path``).
    Without pinning cwd, those subprocesses run ``git status --porcelain``
    and resolve ``<repo>/.plan/execute-script.py`` against the REAL repo
    working tree, so under ``-n auto`` they observe transient state mutated
    by concurrent workers (a known recurring real-tree-leak signature) and
    the aggregate capture becomes non-deterministic. Running with
    ``cwd=tmp_path`` (a non-git, isolated dir) makes ``git_main_checkout_root``
    return ``None`` so the executor/git fan-out short-circuits cleanly to
    "not applicable" — the identifier validators still run at PARSE time
    (the only behaviour this test asserts), so coverage is unchanged while
    the contention source is removed.
    """
    result = run_script(
        SCRIPT_PATH,
        subcommand,
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--phase',
        HAPPY_VALUES['phase'],
        cwd=str(tmp_path),
        env_overrides={'PLAN_BASE_DIR': str(tmp_path)},
    )
    assert_not_invalid_field(result, 'invalid_plan_id')
    assert_not_invalid_field(result, 'invalid_phase')


def test_list_subcommand_canonical_plan_id(tmp_path):
    """``list`` accepts only --plan-id; happy-path must pass the validator.

    Pins ``cwd=tmp_path`` for the same isolation reason documented on
    ``test_canonical_inputs_dont_trigger_invalid_field``: although ``list``
    itself does not fan out to invariant captures, running every canonical
    happy-path invocation against an isolated, non-git cwd keeps the parse-
    time validator assertion free of any dependency on the real repo tree.
    """
    result = run_script(
        SCRIPT_PATH,
        'list',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        cwd=str(tmp_path),
        env_overrides={'PLAN_BASE_DIR': str(tmp_path)},
    )
    assert_not_invalid_field(result, 'invalid_plan_id')


# =============================================================================
# Retained-vs-relaxed worktree-state drift validators (Option 5' / ADR-002)
# =============================================================================
#
# Under the cwd-pinned move model the worktree-state drift checks
# (``main_dirty_files`` layer-D leak guard + the sideways ``worktree_sha`` /
# ``worktree_dirty`` invariants) are RETAINED for the planning-phase
# boundaries (1-init / 2-refine / 3-outline / 4-plan) that still run on main,
# and RELAXED for the ``5-execute → 6-finalize`` boundary the move model makes
# safe. The single cwd-unchanged invariant — asserted by
# ``file_ops.guard_worktree_cwd`` — is what makes the relaxation sound: cwd
# stays pinned to the worktree so plan work cannot leak into main. These
# validators pin both halves of the contract at the function level.
# =============================================================================

_RELAXED_WORKTREE_INVARIANTS = (
    'main_dirty_files',
    'worktree_sha',
    'worktree_dirty',
)
_PLANNING_PHASES = ('1-init', '2-refine', '3-outline', '4-plan')


@pytest.mark.parametrize('invariant', _RELAXED_WORKTREE_INVARIANTS)
@pytest.mark.parametrize('phase', _PLANNING_PHASES)
def test_worktree_state_drift_retained_at_planning_boundaries(invariant, phase):
    """RETAINED: drift in the worktree-state invariants is blocking at 1-4."""
    assert inv.is_invariant_blocking_at_phase(invariant, phase) is True


@pytest.mark.parametrize('invariant', _RELAXED_WORKTREE_INVARIANTS)
def test_worktree_state_drift_relaxed_at_phase_5_boundary(invariant):
    """RELAXED: drift in the worktree-state invariants is NOT blocking at 5-execute."""
    assert inv.is_invariant_blocking_at_phase(invariant, '5-execute') is False


def test_check_main_dirty_drift_gated_to_planning_phases():
    """``_check_main_dirty_drift`` mirrors the relaxation: it fires only for the
    pre-materialization (planning) phases.

    Drives the function directly with a proper-superset drift input and a
    worktree-routed plan. At ``4-plan`` it raises ``MainCheckoutDirtiedDuringPlan``;
    at ``5-execute`` it returns ``None`` (relaxed) for the SAME input.
    """
    import _handshake_commands as cmds  # type: ignore[import-not-found]

    captured_row = {'main_dirty_files': ['existing.txt']}
    observed = {'main_dirty_files': ['existing.txt', 'leaked.py']}
    metadata = {'use_worktree': True}

    # Planning boundary → retained → raises.
    with pytest.raises(inv.MainCheckoutDirtiedDuringPlan):
        cmds._check_main_dirty_drift('p', '4-plan', captured_row, observed, metadata)

    # Phase-5 boundary → relaxed → no raise.
    assert (
        cmds._check_main_dirty_drift('p', '5-execute', captured_row, observed, metadata)
        is None
    )


def test_cwd_unchanged_invariant_guard_holds_when_cwd_is_worktree(tmp_path, monkeypatch):
    """The single cwd-unchanged invariant guard passes when cwd is the worktree.

    ``guard_worktree_cwd`` is the caller-side assertion that underpins the
    phase-5+ relaxation: with cwd pinned to the worktree the guard returns
    ``None`` (invariant holds). Pins ``PLAN_BASE_DIR`` + cwd per the
    test-isolation lessons.
    """
    import file_ops  # type: ignore[import-not-found]

    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    worktree = tmp_path / 'worktrees' / 'plan-guard-ok'
    worktree.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(worktree)

    assert file_ops.guard_worktree_cwd('plan-guard-ok') is None


def test_cwd_unchanged_invariant_guard_flags_when_cwd_left_worktree(tmp_path, monkeypatch):
    """The guard flags a violation when cwd has left the worktree."""
    import file_ops  # type: ignore[import-not-found]

    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    worktree = tmp_path / 'worktrees' / 'plan-guard-left'
    worktree.mkdir(parents=True, exist_ok=True)
    elsewhere = tmp_path / 'main'
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    result = file_ops.guard_worktree_cwd('plan-guard-left')
    assert result is not None
    assert result['error'] == 'cwd_left_worktree'
