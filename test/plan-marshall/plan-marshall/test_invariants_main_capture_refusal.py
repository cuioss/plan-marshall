#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""The capture-time refusal of a row whose ``main_*`` columns read the worktree.

The two SHA columns exist because they describe two different trees. When they
hold the same commit **and** both resolved to the same directory, one tree is
being reported under two names — a capture bug, not a valid row — so
``capture_all`` raises and ``cmd_capture`` refuses to persist.

⛔ Equal commits alone are NOT the trigger, and these tests pin that in both
directions. Two DISTINCT trees can legitimately hold one commit — a
worktree-backed plan whose feature branch carries no commit of its own — and
that row is permitted, because the shipped phase-5 flow produces exactly that
state for an analysis-only plan (Step 2.5 materializes the worktree before the
``early_terminate`` short-circuit). The refusal is keyed on the same-tree
resolution, which is the defect; the equality is only its symptom.

A plan with no persisted ``worktree_path`` captures no ``worktree_sha``, so the
refusal is unreachable there. Note the gate is the PATH, not ``use_worktree``:
``_worktree_in_use`` never reads that flag.

The main-anchored resolution these columns depend on is pinned by the sibling
``test_invariants_main_resolution.py``.
"""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')
SCRIPTS_DIR = SCRIPT_PATH.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _handshake_commands as hc
import _invariants as inv


_SHA_COLUMNS = ('main_sha', 'worktree_sha')


def _narrow_to_sha_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restrict the registry to the two SHA columns the refusal compares.

    Keeps ``capture_all`` off the seven plan-state captures that shell out
    through ``_run_script``, so the test asserts the cross-field rule alone.

    Filters the LIVE registry by name rather than substituting a hand-written
    list, so a changed ``applies_fn`` on either column reaches these tests
    instead of being masked by a stale copy.
    """
    narrowed = [entry for entry in inv.INVARIANTS if entry[0] in _SHA_COLUMNS]
    assert len(narrowed) == len(_SHA_COLUMNS), (
        f'registry no longer carries {_SHA_COLUMNS}: found {[e[0] for e in narrowed]}'
    )
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)


def _equal_head(_tree: object) -> str:
    """Every tree reports the same HEAD — the symptom both directions share."""
    return 'cafebabe1234'


def test_refuses_when_both_columns_resolved_to_the_same_tree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The defect: the main-scoped resolution landed on the plan's worktree.

    Equal commits AND one directory. The payload names both resolved paths so
    the operator can see which two collapsed.
    """
    _narrow_to_sha_columns(monkeypatch)
    worktree = tmp_path / 'wt'
    worktree.mkdir()
    monkeypatch.setattr(inv, 'git_head', _equal_head)
    monkeypatch.setattr(inv, '_main_repo_root', lambda: worktree)

    with pytest.raises(inv.MainCaptureReadTheWorktree) as excinfo:
        inv.capture_all('p', {'worktree_path': str(worktree)}, '5-execute')

    assert excinfo.value.sha == 'cafebabe1234'
    assert excinfo.value.phase == '5-execute'
    assert excinfo.value.main_root == str(worktree)
    assert excinfo.value.worktree_path == str(worktree)


def test_permits_equal_shas_when_the_two_trees_are_distinct(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A commit-less feature branch is LEGITIMATE and must not be refused.

    ``phase-5-execute`` Step 2.5 materializes the worktree unconditionally,
    before the ``early_terminate`` short-circuit, so an analysis-only plan
    reaches its phase-5 boundary with no commit on its branch and both HEADs on
    the commit it branched from. Refusing that would hard-block a legitimate
    boundary with no override escape, and the row it writes is correct —
    ``main_sha`` genuinely is main's HEAD.
    """
    _narrow_to_sha_columns(monkeypatch)
    main_root = tmp_path / 'main'
    worktree = tmp_path / 'wt'
    main_root.mkdir()
    worktree.mkdir()
    monkeypatch.setattr(inv, 'git_head', _equal_head)
    monkeypatch.setattr(inv, '_main_repo_root', lambda: main_root)

    captured = inv.capture_all('p', {'worktree_path': str(worktree)}, '5-execute')

    assert captured == {'main_sha': 'cafebabe1234', 'worktree_sha': 'cafebabe1234'}


def test_permits_equal_shas_for_a_plan_with_no_worktree_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No persisted path → no ``worktree_sha`` → nothing to compare.

    Without this direction, a plan on main whose single tree is trivially
    "equal to itself" would be blocked at every boundary.
    """
    _narrow_to_sha_columns(monkeypatch)
    monkeypatch.setattr(inv, 'git_head', _equal_head)

    captured = inv.capture_all('p', {'use_worktree': False}, '5-execute')

    assert captured == {'main_sha': 'cafebabe1234'}


def test_the_gate_is_the_persisted_path_not_the_use_worktree_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``use_worktree: False`` does NOT exempt a plan that persisted a path.

    ``_worktree_in_use`` delegates to ``_worktree_materialized(metadata, None)``,
    which keys purely on ``worktree_path`` and never reads ``use_worktree`` — so
    the whole invariant family treats such a plan as worktree-backed, and this
    refusal must agree with it. Pins the predicate the docstrings name, which is
    easy to state as "not running on main" and get wrong.
    """
    _narrow_to_sha_columns(monkeypatch)
    worktree = tmp_path / 'wt'
    worktree.mkdir()
    monkeypatch.setattr(inv, 'git_head', _equal_head)
    monkeypatch.setattr(inv, '_main_repo_root', lambda: worktree)

    assert inv._worktree_in_use('p', {'use_worktree': False, 'worktree_path': str(worktree)})
    with pytest.raises(inv.MainCaptureReadTheWorktree):
        inv.capture_all(
            'p', {'use_worktree': False, 'worktree_path': str(worktree)}, '5-execute'
        )


@pytest.fixture()
def worktree_shadowing_main(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> str:
    """Arrange the defect for the CLI-level tests: one tree, two column names."""
    _narrow_to_sha_columns(monkeypatch)
    worktree = tmp_path / 'wt'
    worktree.mkdir()
    monkeypatch.setattr(inv, 'git_head', _equal_head)
    monkeypatch.setattr(inv, '_main_repo_root', lambda: worktree)
    monkeypatch.setattr(
        hc,
        '_load_status_metadata',
        lambda _plan_id: {'use_worktree': True, 'worktree_path': str(worktree)},
    )
    monkeypatch.setattr(hc, '_resolve_worktree_assertion', lambda _md, _phase: None)
    return str(worktree)


def test_cmd_capture_returns_structured_refusal_and_writes_no_row(
    worktree_shadowing_main: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``cmd_capture`` surfaces the refusal as a TOON error and persists nothing."""
    written: list[object] = []
    monkeypatch.setattr(hc, 'upsert_row', lambda *a, **k: written.append(a))

    result = hc.cmd_capture(
        Namespace(plan_id='p', phase='5-execute', override=False, reason='')
    )

    assert result['status'] == 'error'
    assert result['error'] == 'main_capture_read_the_worktree'
    assert result['sha'] == 'cafebabe1234'
    assert result['main_root'] == worktree_shadowing_main
    assert result['worktree_path'] == worktree_shadowing_main
    assert written == [], 'a row read from the wrong tree must not be persisted'


def test_cmd_verify_returns_the_same_refusal_rather_than_raising(
    worktree_shadowing_main: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A live re-capture reproducing the state refuses; it does not escape.

    ``capture_all`` runs the cross-field check itself, so the exception surfaces
    at ``cmd_verify``'s ``capture_all`` call. Without a handler on THAT call it
    escapes the verb entirely and the operator sees ``internal_error`` instead
    of the documented refusal — so this test drives the real ``cmd_verify``
    against a stored row rather than asserting the handler exists.
    """
    monkeypatch.setattr(
        hc, 'get_row', lambda _plan_id, _phase: {'phase': '5-execute', 'override': False}
    )

    result = hc.cmd_verify(Namespace(plan_id='p', phase='5-execute', strict=True))

    assert result['status'] == 'error'
    assert result['error'] == 'main_capture_read_the_worktree'
    assert result['main_root'] == worktree_shadowing_main
    assert result['message'] == hc.cmd_capture(
        Namespace(plan_id='p', phase='5-execute', override=False, reason='')
    )['message'], 'capture and verify must present one envelope'


def test_refusal_error_code_is_a_verify_refusal_that_blocks_transition() -> None:
    """The refusal is never bypassed by the loop-back auto-override marker.

    Quantified over the shipped ``VERIFY_REFUSAL_ERRORS`` set rather than a
    hard-coded copy of it.
    """
    lifecycle = load_script_module(
        'plan-marshall', 'manage-status', '_cmd_lifecycle.py', 'lifecycle_refusal_mod'
    )

    assert 'main_capture_read_the_worktree' in lifecycle.VERIFY_REFUSAL_ERRORS


def test_refusal_exits_non_zero_under_strict_verify(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``phase_handshake main()`` returns 1 on this error under ``--strict``.

    The ``VERIFY_REFUSAL_ERRORS`` membership above governs the transition guard;
    this governs the CLI exit code, a separate surface that a caller swallowing
    TOON output is the only thing it sees. Driven through the real ``main()``
    with a stubbed verb, so the assertion is the returned code and not the
    presence of a literal in the source.
    """
    handshake = load_script_module(
        'plan-marshall', 'plan-marshall', 'phase_handshake.py', 'handshake_strict_mod'
    )
    refusal = {
        'status': 'error',
        'error': 'main_capture_read_the_worktree',
        'plan_id': 'p',
        'phase': '5-execute',
    }
    monkeypatch.setattr(handshake, 'cmd_verify', lambda _args: refusal)
    monkeypatch.setattr(
        sys, 'argv', ['phase_handshake.py', 'verify', '--plan-id', 'p',
                      '--phase', '5-execute', '--strict']
    )

    with pytest.raises(SystemExit) as excinfo:
        handshake.main()

    assert excinfo.value.code == 1
    assert 'main_capture_read_the_worktree' in capsys.readouterr().out


def test_a_clean_strict_verify_still_exits_zero(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative control for the exit-code guard above.

    Without it, a ``main()`` that returned 1 unconditionally would satisfy the
    positive case and look correct.
    """
    handshake = load_script_module(
        'plan-marshall', 'plan-marshall', 'phase_handshake.py', 'handshake_clean_mod'
    )
    monkeypatch.setattr(
        handshake, 'cmd_verify', lambda _args: {'status': 'ok', 'plan_id': 'p'}
    )
    monkeypatch.setattr(
        sys, 'argv', ['phase_handshake.py', 'verify', '--plan-id', 'p',
                      '--phase', '5-execute', '--strict']
    )

    with pytest.raises(SystemExit) as excinfo:
        handshake.main()

    assert excinfo.value.code == 0
