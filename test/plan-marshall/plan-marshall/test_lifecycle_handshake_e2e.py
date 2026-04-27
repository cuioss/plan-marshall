#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""End-to-end regression test for the phase_handshake lifecycle.

Locks in the chronic ``No phase_handshake data`` / ``No handshakes.toon
found`` warning out of the retrospective by simulating a full plan
lifecycle: at every phase boundary the test invokes the orchestrator
shape ``manage-status transition`` → ``phase_handshake capture`` and (for
boundaries beyond the first) ``phase_handshake verify --strict``. After
the run, ``summarize-invariants`` is asserted to return zero
``phase_handshake`` findings in both ``live`` and ``archived`` mode.

Implementation notes
--------------------
The handshake capture functions shell out to ``manage-tasks list``,
``manage-tasks read``, ``manage-findings qgate query`` and
``manage-config plan ... get`` via ``.plan/execute-script.py``. To keep
this test deterministic and independent of an installed executor, the
``_invariants._run_script`` hook is replaced with an in-process stub
that dispatches the same TOON contracts using the manage-tasks command
handlers loaded directly. This mirrors the pattern in
``test_invariants.py`` and exercises the real capture + storage path
end-to-end.

The summarize step uses a real subprocess (``run_script``) so the
``handshakes.toon`` file is read exactly as production would.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import types
from argparse import Namespace
from pathlib import Path

import pytest
from conftest import (  # type: ignore[import-not-found]
    MARKETPLACE_ROOT,
    PlanContext,
    get_script_path,
    run_script,
)

# =============================================================================
# Module wiring
# =============================================================================

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')
SCRIPTS_DIR = SCRIPT_PATH.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _handshake_commands as cmds  # noqa: E402
import _invariants as inv  # noqa: E402

from toon_parser import parse_toon  # noqa: E402

SUMMARIZE_SCRIPT = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'scripts'
    / 'summarize-invariants.py'
)

STATUS_SCRIPT = get_script_path('plan-marshall', 'manage-status', 'manage_status.py')

# Phase order used for the lifecycle simulation.
PHASES = ['1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-finalize']

# Core invariants (worktree-* are excluded — these tests do not run in worktree
# mode). ``phase_steps_complete`` is intentionally excluded from the non-null
# check because it captures only when the phase publishes a
# ``required-steps.md`` declaration; for the synthetic phases driven here, the
# capture function legitimately returns ``None`` for phases without that file.
_NON_NULL_CORE_INVARIANTS = (
    'main_sha',
    'task_state_hash',
    'qgate_open_count',
    'config_hash',
    'pending_tasks_count',
)


# =============================================================================
# In-process manage-tasks dispatcher (mirrors test_invariants.py).
# =============================================================================

_MT_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-tasks'
    / 'scripts'
)


def _load_mt_module(name: str, filename: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, _MT_SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_query = _load_mt_module('_e2e_handshake_tasks_query', '_tasks_query.py')

cmd_list = _query.cmd_list
cmd_read = _query.cmd_read


def _make_stub_run_script():
    """Return a stub for ``inv._run_script`` covering the four notations the
    capture functions invoke.

    - ``manage-tasks list`` and ``manage-tasks read`` resolve in-process via
      the manage-tasks command handlers (same pattern as test_invariants.py).
    - ``manage-findings qgate query`` returns a fixed zero-count payload —
      this test fixture has no Q-Gate findings.
    - ``manage-config plan ... get`` returns a stable empty config payload so
      ``_capture_config_hash`` produces a deterministic hash without needing
      a real marshal.json.
    """
    from file_ops import serialize_toon  # type: ignore[import-not-found]

    def _stub(args: list[str]) -> str | None:
        if len(args) < 2:
            return None
        notation = args[0]

        if notation == 'plan-marshall:manage-tasks:manage-tasks':
            try:
                pid_idx = args.index('--plan-id')
            except ValueError:
                return None
            if pid_idx + 1 >= len(args):
                return None
            plan_id = args[pid_idx + 1]
            subcommand = args[1]
            if subcommand == 'list':
                status_filter = 'all'
                if '--status' in args:
                    s_idx = args.index('--status')
                    if s_idx + 1 < len(args):
                        status_filter = args[s_idx + 1]
                ns = Namespace(
                    plan_id=plan_id,
                    status=status_filter,
                    deliverable=None,
                    ready=False,
                )
                return serialize_toon(cmd_list(ns))
            if subcommand == 'read':
                t_idx = args.index('--task')
                ns = Namespace(plan_id=plan_id, task=int(args[t_idx + 1]))
                return serialize_toon(cmd_read(ns))
            return None

        if notation == 'plan-marshall:manage-findings:manage-findings':
            # qgate query → zero open findings for any phase.
            return serialize_toon({'filtered_count': 0, 'findings': []})

        if notation == 'plan-marshall:manage-config:manage-config':
            # `plan phase-X get` → return an empty payload so the hash is
            # deterministic across phases (an empty config is the same hash).
            return serialize_toon({'plan': {}})

        return None

    return _stub


@pytest.fixture
def stub_handshake_run_script(monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect ``inv._run_script`` so handshake captures run in-process."""
    monkeypatch.setattr(inv, '_run_script', _make_stub_run_script())


@pytest.fixture
def stub_load_status_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub ``cmds._load_status_metadata`` to a non-worktree empty dict.

    The production helper shells out to ``manage-status read`` via the
    executor; with the executor symlink pointing at the main checkout the
    real call would resolve against the wrong PLAN_BASE_DIR. The metadata
    we need is "no worktree", and an empty dict satisfies that.
    """
    monkeypatch.setattr(cmds, '_load_status_metadata', lambda _pid: {})


# =============================================================================
# Helpers
# =============================================================================


def _capture_args(plan_id: str, phase: str) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        override=False,
        reason=None,
        strict=False,
    )


def _verify_args(plan_id: str, phase: str) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        override=False,
        reason=None,
        strict=True,
    )


def _create_plan(plan_id: str, title: str = 'E2E Handshake') -> None:
    """Create a plan with all six lifecycle phases via manage-status."""
    result = run_script(
        STATUS_SCRIPT,
        'create',
        '--plan-id',
        plan_id,
        '--title',
        title,
        '--phases',
        ','.join(PHASES),
    )
    assert result.success, f'manage-status create failed: {result.stderr}'


def _transition(plan_id: str, completed_phase: str) -> dict:
    result = run_script(
        STATUS_SCRIPT, 'transition', '--plan-id', plan_id, '--completed', completed_phase
    )
    assert result.success, f'manage-status transition failed: {result.stderr}'
    return parse_toon(result.stdout)


# =============================================================================
# Tests
# =============================================================================


def test_lifecycle_captures_handshakes_for_all_phases(
    stub_handshake_run_script, stub_load_status_metadata
) -> None:
    """Driving the orchestrator-shape sequence populates one row per phase.

    Iterates the five inter-phase boundaries (``1-init`` → ``2-refine`` …
    ``5-execute`` → ``6-finalize``). At each boundary:

    1. ``manage-status transition --completed {phase}`` (real subprocess).
    2. ``phase_handshake capture --phase {phase}`` (in-process via cmds).
    3. For boundaries beyond the first, ``phase_handshake verify --phase
       {prev_phase} --strict`` and assert ``status: ok``.

    After the loop, ``handshakes.toon`` must contain exactly five rows with
    every core invariant non-null.
    """
    plan_id = 'e2e-handshake-lifecycle'
    with PlanContext(plan_id=plan_id) as ctx:
        _create_plan(plan_id)

        prev_phase: str | None = None
        # Capture for the five phases that have a "next phase" (1-init through
        # 5-execute). The 6-finalize transition is the terminal one and the
        # plan's pretasks are exhausted there — this matches the workflow
        # wiring described in solution_outline.md.
        capture_phases = PHASES[:5]
        for phase in capture_phases:
            transition_result = _transition(plan_id, phase)
            assert transition_result['status'] == 'success', transition_result

            cap = cmds.cmd_capture(_capture_args(plan_id, phase))
            assert cap['status'] == 'success', f'capture failed at {phase}: {cap}'

            if prev_phase is not None:
                ver = cmds.cmd_verify(_verify_args(plan_id, prev_phase))
                assert ver['status'] == 'ok', (
                    f'verify {prev_phase} returned {ver["status"]}: {ver}'
                )
            prev_phase = phase

        # Inspect handshakes.toon directly via the context's plan_dir.
        assert ctx.plan_dir is not None
        handshakes_path = ctx.plan_dir / 'handshakes.toon'
        assert handshakes_path.exists(), 'handshakes.toon must be written'
        parsed = parse_toon(handshakes_path.read_text(encoding='utf-8'))
        rows = parsed.get('handshakes') or []
        assert len(rows) == 5, (
            f'expected 5 handshake rows, got {len(rows)}: {rows}'
        )

        captured_phases = [r['phase'] for r in rows]
        assert captured_phases == capture_phases, captured_phases

        for row in rows:
            for invariant in _NON_NULL_CORE_INVARIANTS:
                value = row.get(invariant)
                assert value not in (None, ''), (
                    f'phase {row["phase"]} missing non-null invariant '
                    f'{invariant}: row={row}'
                )


def test_lifecycle_summarize_invariants_zero_warnings_live_mode(
    stub_handshake_run_script, stub_load_status_metadata
) -> None:
    """After a populated lifecycle, ``summarize-invariants run --mode live``
    must report zero ``phase_handshake`` findings.

    This is the regression assertion that locks the chronic warning out:
    the warning is the canonical missing-data finding emitted when the
    retrospective cannot read ``handshakes.toon``. With the lifecycle
    properly populated the warning must not appear.
    """
    plan_id = 'e2e-handshake-live'
    with PlanContext(plan_id=plan_id):
        _create_plan(plan_id)
        for phase in PHASES[:5]:
            _transition(plan_id, phase)
            cap = cmds.cmd_capture(_capture_args(plan_id, phase))
            assert cap['status'] == 'success', cap

        result = run_script(SUMMARIZE_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        bulk = [
            f for f in data['findings'] if f.get('invariant') == 'phase_handshake'
        ]
        assert bulk == [], (
            f'live mode must not produce phase_handshake findings, got {bulk}'
        )


def test_lifecycle_summarize_invariants_zero_warnings_archived_mode(
    stub_handshake_run_script, stub_load_status_metadata, tmp_path: Path
) -> None:
    """Archive the populated plan and re-run ``summarize-invariants`` in
    ``archived`` mode against the archived path. Zero ``phase_handshake``
    findings must persist.

    Archiving here is performed by copying the plan directory out of the
    fixture base — ``manage-status archive`` requires a real archive root
    layout that this in-process test does not need to model. The
    summarize-invariants script reads ``<archived_path>/handshakes.toon``
    directly in archived mode, so a directory copy is sufficient.
    """
    plan_id = 'e2e-handshake-archived'
    with PlanContext(plan_id=plan_id) as ctx:
        _create_plan(plan_id)
        for phase in PHASES[:5]:
            _transition(plan_id, phase)
            cap = cmds.cmd_capture(_capture_args(plan_id, phase))
            assert cap['status'] == 'success', cap

        # Snapshot the live plan dir into a separate archived path BEFORE
        # PlanContext exits (which deletes the live plan dir).
        archived_dir = tmp_path / 'archived' / f'2026-04-27-{plan_id}'
        shutil.copytree(ctx.plan_dir, archived_dir)

    result = run_script(
        SUMMARIZE_SCRIPT,
        'run',
        '--archived-plan-path',
        str(archived_dir),
        '--mode',
        'archived',
    )
    assert result.success, result.stderr
    data = result.toon()
    bulk = [
        f for f in data['findings'] if f.get('invariant') == 'phase_handshake'
    ]
    assert bulk == [], (
        f'archived mode must not produce phase_handshake findings, got {bulk}'
    )


def test_regression_missing_handshakes_warns() -> None:
    """Negative regression: when capture is never invoked, the canonical
    ``No handshakes.toon found`` warning must fire.

    This proves the test catches the regression it is designed to lock
    out — without it, the positive assertions above could pass even if
    ``handshakes.toon`` were silently empty.
    """
    plan_id = 'e2e-handshake-missing'
    with PlanContext(plan_id=plan_id):
        _create_plan(plan_id)
        # Deliberately do NOT call cmds.cmd_capture — handshakes.toon stays
        # absent.

        result = run_script(
            SUMMARIZE_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live'
        )
        assert result.success, result.stderr
        data = result.toon()

        messages = [f.get('message', '') for f in data['findings']]
        assert 'No handshakes.toon found' in messages, (
            f'expected canonical warning, got messages: {messages}'
        )
