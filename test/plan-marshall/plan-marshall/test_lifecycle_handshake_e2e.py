#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
``manage-tasks read`` and ``manage-findings qgate query`` via
``.plan/execute-script.py``. To keep this test deterministic and
independent of an installed executor, the ``_invariants._run_script``
hook is replaced with an in-process stub that dispatches the same TOON
contracts using the manage-tasks command handlers loaded directly. The
``config_hash`` capture reads ``marshal.json`` directly (not the
executor); ``stub_marshal_config`` writes one into the sandbox so the
fingerprint is stable and non-null. This mirrors the pattern in
``test_invariants.py`` and exercises the real capture + storage path
end-to-end.

The summarize step uses a real subprocess (``run_script``) so the
``handshakes.toon`` file is read exactly as production would.
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
from pathlib import Path
from typing import Any

# Imported PLAINLY so this suite holds the same instances the production path
# resolves; their marketplace ``scripts/`` directory is already on ``sys.path``
# via the root conftest.
import _handshake_commands as cmds
import _invariants as inv
import pytest
from toon_parser import parse_toon

from conftest import (
    MARKETPLACE_ROOT,
    get_script_path,
    load_script_module,
    parse_ns,
    run_script,
)

# =============================================================================
# Module wiring
# =============================================================================

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')

SUMMARIZE_SCRIPT = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'summarize-invariants.py'
)

STATUS_SCRIPT = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')

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
    'unfinished_tasks_count',
)


# =============================================================================
# In-process manage-tasks dispatcher (mirrors test_invariants.py).
# =============================================================================

# Loaded under a name used nowhere else in the tree, so the registration the
# shared loader performs cannot displace another module's copy.
_query = load_script_module(
    'plan-marshall', 'manage-tasks', '_tasks_query.py', '_e2e_handshake_tasks_query'
)

cmd_list = _query.cmd_list
cmd_read = _query.cmd_read


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from a hoisted parser-derived base.

    The base supplies every parser default; ``overrides`` names only the fields
    this call differs in. A shallow copy is enough because the values are the
    parser's own scalars, and the base must stay unmutated for the other callers
    sharing it.
    """
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


#: Parser-derived bases for the two surfaces this e2e drives, hoisted to module
#: scope because ``parse_ns`` re-executes the script module on every call. The
#: ``phase_handshake`` pair is where the parser is most corrective: ``capture``
#: declares no ``--strict`` and ``verify`` declares neither ``--override`` nor
#: ``--reason``, yet the hand-built namespaces these replace gave every field to
#: both — so each test asserted against a shape the CLI cannot produce.
#: ``register=False`` throughout, so none displaces a module registration this
#: file already performs under its own explicit names.
_TASKS_LIST_ARGS = parse_ns(
    'plan-marshall', 'manage-tasks', 'manage-tasks.py',
    'list', '--plan-id', 'placeholder',
    register=False,
)
_TASKS_READ_ARGS = parse_ns(
    'plan-marshall', 'manage-tasks', 'manage-tasks.py',
    'read', '--plan-id', 'placeholder', '--task-number', '1',
    register=False,
)
_HANDSHAKE_CAPTURE_ARGS = parse_ns(
    'plan-marshall', 'plan-marshall', 'phase_handshake.py',
    'capture', '--plan-id', 'placeholder', '--phase', '1-init',
    register=False,
)
_HANDSHAKE_VERIFY_ARGS = parse_ns(
    'plan-marshall', 'plan-marshall', 'phase_handshake.py',
    'verify', '--plan-id', 'placeholder', '--phase', '1-init', '--strict',
    register=False,
)


def _make_stub_run_script():
    """Return a stub for ``inv._run_script`` covering the notations the capture
    functions invoke.

    - ``manage-tasks list`` and ``manage-tasks read`` resolve in-process via
      the manage-tasks command handlers (same pattern as test_invariants.py).
    - ``manage-findings qgate query`` returns a fixed zero-count payload —
      this test fixture has no Q-Gate findings.

    ``_capture_config_hash`` no longer goes through ``_run_script`` — it reads
    ``marshal.json`` directly (see ``stub_marshal_config``), so there is no
    ``manage-config`` branch here.
    """
    from file_ops import serialize_toon

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
                ns = _variant(_TASKS_LIST_ARGS, plan_id=plan_id, status=status_filter)
                return serialize_toon(cmd_list(ns))
            if subcommand == 'read':
                # ``--task-number`` is the flag the real CLI declares, and
                # ``task_number`` the field its parser produces. The hand-built
                # namespace this replaces named both ``--task`` and ``task``, so
                # the branch could never have matched a real capture's argv.
                t_idx = args.index('--task-number')
                ns = _variant(_TASKS_READ_ARGS, plan_id=plan_id, task_number=int(args[t_idx + 1]))
                return serialize_toon(cmd_read(ns))
            return None

        if notation == 'plan-marshall:manage-findings:manage-findings':
            # qgate query → zero open findings for any phase.
            return serialize_toon({'filtered_count': 0, 'findings': []})

        return None

    return _stub


@pytest.fixture
def stub_handshake_run_script(monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect ``inv._run_script`` so handshake captures run in-process."""
    monkeypatch.setattr(inv, '_run_script', _make_stub_run_script())


@pytest.fixture
def stub_marshal_config(monkeypatch: pytest.MonkeyPatch, plan_context) -> None:
    """Provide a ``marshal.json`` so ``_capture_config_hash`` reads a real,
    phase-independent plan-config fingerprint.

    The capture reads ``marshal.json`` directly (not via the executor), so
    ``inv.get_marshal_path`` is redirected at a fixture file written into the
    per-test sandbox. Its content is fixed for the whole lifecycle, so the
    fingerprint is stable across every phase and non-null in every row.
    """
    marshal = plan_context.fixture_dir / 'marshal.json'
    marshal.write_text(
        json.dumps({'plan': {'phase-5-execute': {'max_iterations': 5}}}),
        encoding='utf-8',
    )
    monkeypatch.setattr(inv, 'get_marshal_path', lambda: marshal)


@pytest.fixture
def stub_load_status_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub ``cmds._load_status_metadata`` to a non-worktree metadata dict.

    The production helper shells out to ``manage-status read`` via the
    executor; with the executor symlink pointing at the main checkout the
    real call would resolve against the wrong PLAN_BASE_DIR. The metadata
    we need is "no worktree", which an absent ``worktree_path`` satisfies.

    A realistic post-refine plan carries ``pr_title`` (authored at
    phase-2-refine Step 13), so the stub includes it — the
    ``pr_title_present`` invariant raises ``PrTitleMissing`` at the
    ``2-refine``+ boundaries this lifecycle exercises when the field is
    absent, exactly as a real plan that skipped refine title-authoring would.
    """
    monkeypatch.setattr(
        cmds,
        '_load_status_metadata',
        lambda _pid: {'pr_title': 'fix(handshake): lifecycle e2e PR title'},
    )


# =============================================================================
# Helpers
# =============================================================================


def _capture_args(plan_id: str, phase: str) -> argparse.Namespace:
    return _variant(_HANDSHAKE_CAPTURE_ARGS, plan_id=plan_id, phase=phase)


def _verify_args(plan_id: str, phase: str) -> argparse.Namespace:
    return _variant(_HANDSHAKE_VERIFY_ARGS, plan_id=plan_id, phase=phase)


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
    result = run_script(STATUS_SCRIPT, 'transition', '--plan-id', plan_id, '--completed', completed_phase)
    assert result.success, f'manage-status transition failed: {result.stderr}'
    return parse_toon(result.stdout)


# =============================================================================
# Tests
# =============================================================================


def test_lifecycle_captures_handshakes_for_all_phases(
    stub_handshake_run_script, stub_load_status_metadata, stub_marshal_config, plan_context
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
    plan_dir = plan_context.plan_dir_for(plan_id)
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
            assert ver['status'] == 'ok', f'verify {prev_phase} returned {ver["status"]}: {ver}'
        prev_phase = phase

    # Inspect handshakes.toon directly via the resolved plan_dir.
    handshakes_path = plan_dir / 'handshakes.toon'
    assert handshakes_path.exists(), 'handshakes.toon must be written'
    parsed = parse_toon(handshakes_path.read_text(encoding='utf-8'))
    rows = parsed.get('handshakes') or []
    assert len(rows) == 5, f'expected 5 handshake rows, got {len(rows)}: {rows}'

    captured_phases = [r['phase'] for r in rows]
    assert captured_phases == capture_phases, captured_phases

    for row in rows:
        for invariant in _NON_NULL_CORE_INVARIANTS:
            value = row.get(invariant)
            assert value not in (None, ''), (
                f'phase {row["phase"]} missing non-null invariant {invariant}: row={row}'
            )


def test_lifecycle_summarize_invariants_zero_warnings_live_mode(
    stub_handshake_run_script, stub_load_status_metadata, stub_marshal_config, plan_context
) -> None:
    """After a populated lifecycle, ``summarize-invariants run --mode live``
    must report zero ``phase_handshake`` findings.

    This is the regression assertion that locks the chronic warning out:
    the warning is the canonical missing-data finding emitted when the
    retrospective cannot read ``handshakes.toon``. With the lifecycle
    properly populated the warning must not appear.
    """
    plan_id = 'e2e-handshake-live'
    plan_context.plan_dir_for(plan_id)
    _create_plan(plan_id)
    for phase in PHASES[:5]:
        _transition(plan_id, phase)
        cap = cmds.cmd_capture(_capture_args(plan_id, phase))
        assert cap['status'] == 'success', cap

    result = run_script(SUMMARIZE_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live')
    assert result.success, result.stderr
    data = result.toon()

    bulk = [f for f in data['findings'] if f.get('invariant') == 'phase_handshake']
    assert bulk == [], f'live mode must not produce phase_handshake findings, got {bulk}'


def test_lifecycle_summarize_invariants_zero_warnings_archived_mode(
    stub_handshake_run_script, stub_load_status_metadata, stub_marshal_config, plan_context, tmp_path: Path
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
    plan_dir = plan_context.plan_dir_for(plan_id)
    _create_plan(plan_id)
    for phase in PHASES[:5]:
        _transition(plan_id, phase)
        cap = cmds.cmd_capture(_capture_args(plan_id, phase))
        assert cap['status'] == 'success', cap

    # Snapshot the live plan dir into a separate archived path.
    archived_dir = tmp_path / 'archived' / f'2026-04-27-{plan_id}'
    shutil.copytree(plan_dir, archived_dir)

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
    bulk = [f for f in data['findings'] if f.get('invariant') == 'phase_handshake']
    assert bulk == [], f'archived mode must not produce phase_handshake findings, got {bulk}'


def test_regression_missing_handshakes_warns(plan_context) -> None:
    """Negative regression: when capture is never invoked, the canonical
    ``No handshakes.toon found`` warning must fire.

    This proves the test catches the regression it is designed to lock
    out — without it, the positive assertions above could pass even if
    ``handshakes.toon`` were silently empty.
    """
    plan_id = 'e2e-handshake-missing'
    plan_context.plan_dir_for(plan_id)
    _create_plan(plan_id)
    # Deliberately do NOT call cmds.cmd_capture — handshakes.toon stays
    # absent.

    result = run_script(SUMMARIZE_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live')
    assert result.success, result.stderr
    data = result.toon()

    messages = [f.get('message', '') for f in data['findings']]
    assert 'No handshakes.toon found' in messages, f'expected canonical warning, got messages: {messages}'
