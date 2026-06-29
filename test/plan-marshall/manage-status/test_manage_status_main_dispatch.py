#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process tests for the manage-status.py CLI dispatcher (``main``).

The existing manage-status suites drive the per-command handlers directly
(``cmd_create``, ``cmd_metadata``, …) or invoke the script through a
subprocess. Neither path attributes coverage to the dispatcher body in
``manage-status.py`` — the argparse construction, the ``func``-dispatch, the
``transition`` exit-code contract, and the ``_loop_back_target_type`` argparse
``type=`` validator. These tests call ``main()`` in-process (after setting
``sys.argv``) so coverage lands on the dispatcher source, while still asserting
real behaviour: exit codes, the emitted TOON status, and routing payloads.

``main()`` is wrapped by ``@safe_main``, which calls ``sys.exit(main())``;
every dispatch therefore raises ``SystemExit`` whose ``.code`` is the script's
integer return.
"""

import sys

import pytest

from conftest import load_script_module

# Load the dispatcher module in-process (unique module name) so coverage is
# attributed to manage-status.py rather than to a subprocess.
_ms = load_script_module('plan-marshall', 'manage-status', 'manage-status.py', 'inproc_manage_status_main')

_PHASES = '1-init,2-refine,3-outline,4-plan,5-execute,6-finalize'


def _run(monkeypatch, capsys, argv):
    """Invoke ``main()`` with ``argv`` and return (exit_code, stdout, stderr)."""
    monkeypatch.setattr(sys, 'argv', ['manage-status.py', *argv])
    with pytest.raises(SystemExit) as exc:
        _ms.main()
    captured = capsys.readouterr()
    code = exc.value.code if exc.value.code is not None else 0
    return code, captured.out, captured.err


def _parse(out):
    from toon_parser import parse_toon  # type: ignore[import-not-found]

    return parse_toon(out)


# =============================================================================
# create -> read roundtrip through the dispatcher
# =============================================================================


def test_main_create_then_read_roundtrip(plan_context, monkeypatch, capsys):
    """create then read dispatch successfully and round-trip the plan title."""
    # Arrange / Act: create
    code, out, _ = _run(
        monkeypatch, capsys, ['create', '--plan-id', 'ms-disp-rt', '--title', 'Dispatch RT', '--phases', _PHASES]
    )
    # Assert: create succeeded with exit 0
    assert code == 0
    assert _parse(out)['status'] == 'success'

    # Act: read the just-created plan
    code, out, _ = _run(monkeypatch, capsys, ['read', '--plan-id', 'ms-disp-rt'])

    # Assert: read returns the persisted title
    assert code == 0
    data = _parse(out)
    assert data['status'] == 'success'
    # cmd_read nests the persisted status under the 'plan' key.
    assert data['plan']['title'] == 'Dispatch RT'


def test_main_list_returns_success(plan_context, monkeypatch, capsys):
    """The ``list`` subcommand dispatches and reports success on an empty store."""
    code, out, _ = _run(monkeypatch, capsys, ['list'])

    assert code == 0
    assert 'status: success' in out


# =============================================================================
# route / self-test (no plan required)
# =============================================================================


def test_main_route_returns_skill_for_known_phase(plan_context, monkeypatch, capsys):
    """``route --phase 1-init`` returns the routed skill for that phase."""
    code, out, _ = _run(monkeypatch, capsys, ['route', '--phase', '1-init'])

    assert code == 0
    data = _parse(out)
    assert data['status'] == 'success'
    assert data['phase'] == '1-init'
    assert data['skill']  # a non-empty skill notation is routed


def test_main_route_unknown_phase_reports_error(plan_context, monkeypatch, capsys):
    """An unroutable phase yields a status: error TOON but still exits 0."""
    code, out, _ = _run(monkeypatch, capsys, ['route', '--phase', '99-bogus'])

    assert code == 0
    data = _parse(out)
    assert data['status'] == 'error'
    assert data['error'] == 'invalid_phase'


def test_main_self_test_passes(plan_context, monkeypatch, capsys):
    """``self-test`` dispatches and reports all internal health checks passing."""
    code, out, _ = _run(monkeypatch, capsys, ['self-test'])

    assert code == 0
    data = _parse(out)
    assert data['status'] == 'success'
    assert int(data['failed']) == 0
    assert int(data['passed']) >= 1


# =============================================================================
# metadata / title-token / update-phase / progress
# =============================================================================


def test_main_metadata_set_then_get(plan_context, monkeypatch, capsys):
    """metadata --set persists a field that metadata --get reads back."""
    _run(monkeypatch, capsys, ['create', '--plan-id', 'ms-disp-md', '--title', 'MD', '--phases', _PHASES])

    code, out, _ = _run(
        monkeypatch, capsys, ['metadata', '--plan-id', 'ms-disp-md', '--set', '--field', 'change_type', '--value', 'feature']
    )
    assert code == 0
    assert _parse(out)['status'] == 'success'

    code, out, _ = _run(
        monkeypatch, capsys, ['metadata', '--plan-id', 'ms-disp-md', '--get', '--field', 'change_type']
    )
    assert code == 0
    data = _parse(out)
    assert data['status'] == 'success'
    assert data['value'] == 'feature'


def test_main_title_token_set_then_clear(plan_context, monkeypatch, capsys):
    """title-token set persists a state; title-token clear removes it idempotently."""
    _run(monkeypatch, capsys, ['create', '--plan-id', 'ms-disp-tt', '--title', 'TT', '--phases', _PHASES])

    code, out, _ = _run(
        monkeypatch, capsys, ['title-token', 'set', '--plan-id', 'ms-disp-tt', '--state', 'build-busy']
    )
    assert code == 0
    assert _parse(out)['status'] == 'success'

    code, out, _ = _run(monkeypatch, capsys, ['title-token', 'clear', '--plan-id', 'ms-disp-tt'])
    assert code == 0
    assert _parse(out)['status'] == 'success'


def test_main_title_token_rejects_unknown_state(plan_context, monkeypatch, capsys):
    """An out-of-enum --state is an argparse rejection (exit 2)."""
    code, _, _ = _run(
        monkeypatch, capsys, ['title-token', 'set', '--plan-id', 'ms-disp-tt2', '--state', 'not-a-state']
    )

    assert code == 2


def test_main_update_phase_marks_done(plan_context, monkeypatch, capsys):
    """update-phase dispatches and transitions a phase to done."""
    _run(monkeypatch, capsys, ['create', '--plan-id', 'ms-disp-up', '--title', 'UP', '--phases', _PHASES])

    code, out, _ = _run(
        monkeypatch, capsys, ['update-phase', '--plan-id', 'ms-disp-up', '--phase', '1-init', '--status', 'done']
    )

    assert code == 0
    assert _parse(out)['status'] == 'success'


def test_main_progress_after_create(plan_context, monkeypatch, capsys):
    """progress dispatches and reports a success payload for an existing plan."""
    _run(monkeypatch, capsys, ['create', '--plan-id', 'ms-disp-pr', '--title', 'PR', '--phases', _PHASES])

    code, out, _ = _run(monkeypatch, capsys, ['progress', '--plan-id', 'ms-disp-pr'])

    assert code == 0
    assert _parse(out)['status'] == 'success'


# =============================================================================
# Result-is-None dispatch branch (handler returns None, output skipped)
# =============================================================================


def test_main_get_context_missing_plan_exits_zero_with_error(plan_context, monkeypatch, capsys):
    """get-context on a missing plan returns None from the handler.

    ``require_status`` emits the file_not_found TOON itself and returns None, so
    the dispatcher skips its own ``output_toon`` (the ``result is None`` branch)
    and still exits 0.
    """
    code, out, _ = _run(monkeypatch, capsys, ['get-context', '--plan-id', 'ms-disp-absent'])

    assert code == 0
    data = _parse(out)
    assert data['status'] == 'error'
    assert data['error'] == 'file_not_found'


# =============================================================================
# transition exit-code contract
# =============================================================================


def test_main_transition_normal_boundary_exits_zero(plan_context, monkeypatch, capsys):
    """A transition across a non-blocking boundary succeeds and exits 0."""
    _run(monkeypatch, capsys, ['create', '--plan-id', 'ms-disp-tr', '--title', 'TR', '--phases', _PHASES])

    code, out, _ = _run(monkeypatch, capsys, ['transition', '--plan-id', 'ms-disp-tr', '--completed', '1-init'])

    assert code == 0
    assert _parse(out)['status'] == 'success'


def test_main_transition_invalid_phase_exits_zero_with_error(plan_context, monkeypatch, capsys):
    """Transitioning a non-existent completed phase returns an error and exits 0.

    The result is an error dict (``invalid_phase``) that ``verify_blocks_transition``
    does NOT treat as a transition-block, so the dispatcher's exit-code guard
    leaves the code at 0.
    """
    _run(monkeypatch, capsys, ['create', '--plan-id', 'ms-disp-tri', '--title', 'TRI', '--phases', _PHASES])

    code, out, _ = _run(monkeypatch, capsys, ['transition', '--plan-id', 'ms-disp-tri', '--completed', 'no-such-phase'])

    assert code == 0
    data = _parse(out)
    assert data['status'] == 'error'
    assert data['error'] == 'invalid_phase'


# =============================================================================
# mark-step-done (loop-back classification through the dispatcher)
# =============================================================================


def test_main_mark_step_done_loop_back_records_target(plan_context, monkeypatch, capsys):
    """A loop_back outcome with a valid --loop-back-target dispatches and persists."""
    _run(monkeypatch, capsys, ['create', '--plan-id', 'ms-disp-ms', '--title', 'MS', '--phases', _PHASES])

    code, out, _ = _run(
        monkeypatch,
        capsys,
        [
            'mark-step-done',
            '--plan-id', 'ms-disp-ms',
            '--phase', '5-execute',
            '--step', 'discovery',
            '--outcome', 'loop_back',
            '--loop-back-target', '5-execute',
        ],
    )

    assert code == 0
    data = _parse(out)
    assert data['status'] == 'success'
    assert data['outcome'] == 'loop_back'
    assert data['loop_back_target'] == '5-execute'


def test_main_mark_step_done_loop_back_missing_target_errors(plan_context, monkeypatch, capsys):
    """loop_back without --loop-back-target is rejected by the handler (exit 0, error)."""
    _run(monkeypatch, capsys, ['create', '--plan-id', 'ms-disp-msx', '--title', 'MSX', '--phases', _PHASES])

    code, out, _ = _run(
        monkeypatch,
        capsys,
        [
            'mark-step-done',
            '--plan-id', 'ms-disp-msx',
            '--phase', '5-execute',
            '--step', 'discovery',
            '--outcome', 'loop_back',
        ],
    )

    assert code == 0
    data = _parse(out)
    assert data['status'] == 'error'
    assert data['error'] == 'missing_loop_back_target'


# =============================================================================
# argparse-level rejections at the dispatcher boundary
# =============================================================================


def test_main_missing_subcommand_exits_2(plan_context, monkeypatch, capsys):
    """No subcommand is an argparse error: SystemExit code 2."""
    code, _, err = _run(monkeypatch, capsys, [])

    assert code == 2
    assert 'usage' in err.lower() or 'error' in err.lower()


def test_main_unknown_flag_exits_2(plan_context, monkeypatch, capsys):
    """An unknown flag on a real subcommand is an argparse error: exit 2."""
    code, _, _ = _run(monkeypatch, capsys, ['list', '--definitely-not-a-flag'])

    assert code == 2


# =============================================================================
# _loop_back_target_type argparse validator (module-level function)
# =============================================================================


def test_loop_back_target_type_normalizes_case():
    """The validator lowercases a valid target and returns the canonical form."""
    assert _ms._loop_back_target_type('5-EXECUTE') == '5-execute'
    assert _ms._loop_back_target_type('6-finalize') == '6-finalize'


def test_loop_back_target_type_rejects_unknown():
    """An unknown target raises argparse.ArgumentTypeError naming the valid set."""
    import argparse

    with pytest.raises(argparse.ArgumentTypeError) as exc:
        _ms._loop_back_target_type('banana')
    assert 'banana' in str(exc.value)
