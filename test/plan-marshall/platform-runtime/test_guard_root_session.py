#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A root session gets the guard's verdict, and R6 names the plan from every form — D3.

Two divergences the merged code left open:

* the hook gated R1, R2 and R4 on the plan context, so a ROOT session of this
  repository was admitted for forms the OpenCode guard refuses. The decision is
  to LIFT the gating for this repository rather than to give R5 its own full
  scan: the guard applies R1-R4 unconditionally and the hook must give the same
  verdict, while a consumer repository outside a plan context stays untouched
  (the two-tier permission map governs it). The side-door table below is the row
  set that fails the moment the gating is restored: every row runs with NO plan
  context.
* R6 named the plan only from ``-C``, so ``--git-dir`` / ``--work-tree``,
  ``GIT_DIR``, an unexpanded ``-C`` variable and a ``-c alias`` all escaped it.
  Every form is refused now, the last two fail-closed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _guard_node_harness import SUB_AGENT_AGENT, GuardHarness, build_harness, shell_event
from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, run_script

_HOOK = load_script_module(
    'plan-marshall',
    'platform-runtime',
    'claude_pretooluse_hook.py',
    module_name='root_session_pretooluse_hook',
    register=False,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
_MANAGE_STATUS = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')
_PHASES = '1-init,2-refine,3-outline,4-plan,5-execute,6-finalize'


def _managed_plan(base: Path, plan_id: str, phase: str) -> None:
    """Create a REAL managed plan under *base* and move it to *phase*."""
    env = {'PLAN_BASE_DIR': str(base), 'PLAN_DIR_NAME': '.plan'}
    created = run_script(
        _MANAGE_STATUS, 'create', '--plan-id', plan_id, '--title', 't', '--phases', _PHASES, env_overrides=env
    )
    assert created.returncode == 0, f'manage-status create failed: {created.stdout}{created.stderr}'
    assert parse_toon(created.stdout).get('status') == 'success', created.stdout
    shifted = run_script(_MANAGE_STATUS, 'set-phase', '--plan-id', plan_id, '--phase', phase, env_overrides=env)
    assert shifted.returncode == 0, f'manage-status set-phase failed: {shifted.stdout}{shifted.stderr}'


def _hook_reason(command: str, *, cwd: str, in_context: bool = False) -> str | None:
    payload: dict = {'tool_name': 'Bash', 'tool_input': {'command': command}, 'cwd': cwd}
    if in_context:
        payload['agent_type'] = SUB_AGENT_AGENT
    reason = _HOOK.evaluate(payload)
    return reason if isinstance(reason, str) else None


#: The D3 side-door rows, run in a ROOT session (no plan context) and again inside
#: a plan context. Each is refused by the OpenCode guard in BOTH; the hook must
#: give the same verdict in both. The rule that fires is intentionally NOT pinned:
#: `bash -c` and `env bash -c` are reachable as R2 (shell spawn) and as R5 (the
#: spliced interpreter), and the contract is the refusal.
_ROOT_SESSION_SIDE_DOORS: tuple[str, ...] = (
    'true && python3 -c x',
    'echo hi | python3 -',
    'bash -c "python3 -c x"',
    'env bash -c "python3 -c x"',
    'uv run python -c "x"',
    'env ./pw verify',
)


@pytest.mark.parametrize('in_context', [False, True], ids=['root-session', 'plan-context'])
@pytest.mark.parametrize('command', _ROOT_SESSION_SIDE_DOORS, ids=list(_ROOT_SESSION_SIDE_DOORS))
def test_root_session_refuses_every_side_door(
    command: str, in_context: bool, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """A root session of this repository gets the guard's verdict, in both contexts.

    The root-session arm is the row set that fails when the hook's gating is
    restored: with no ``agent_type`` and a cwd outside any worktree, a gated
    R1-R4 chain admits all six.
    """
    reason = _hook_reason(command, cwd=str(REPO_ROOT), in_context=in_context)
    assert reason is not None, f'the hook must refuse {command!r} (in_context={in_context})'

    harness: GuardHarness = build_harness(tmp_path_factory.mktemp('d3-root'))
    event = shell_event(command, agent=SUB_AGENT_AGENT) if in_context else shell_event(command)
    blocked, message = harness.blocks(event)
    assert blocked, f'guard.js must refuse {command!r} (in_context={in_context}); message={message!r}'


# =============================================================================
# R6 — the plan is named from every commit form
# =============================================================================

#: Forms that name the ``6-finalize`` plan through a git directory/work tree.
_R6_NAMED_FORMS: tuple[str, ...] = (
    'git --git-dir=.git/worktrees/plan-a --work-tree=.plan/local/worktrees/plan-a commit -m "fix: x"',
    'env GIT_DIR=.git/worktrees/plan-a GIT_WORK_TREE=.plan/local/worktrees/plan-a git commit -m "fix: x"',
    'git -C .plan/local/worktrees/plan-a -c alias.ci=commit ci -m "fix: x"',
    'zsh -c "cd /tmp; git -C .plan/local/worktrees/plan-a commit -m x"',
    'watch "cd /tmp; git -C .plan/local/worktrees/plan-a commit -m x"',
    'zsh -c "cd .plan/local/worktrees/plan-a; git commit -m x"',
)


def test_the_side_door_rows_depend_on_the_scope(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The negative control: with the scope switched off, the same rows are ADMITTED.

    The table proves the hook's gating is what refuses them — restoring the gate
    (i.e. removing this-repository/lane binding) turns all six red, exactly as the
    merged code did.
    """
    monkeypatch.setattr(_HOOK, '_is_this_repository', lambda payload: False)
    monkeypatch.setattr(_HOOK, '_is_lane_run', lambda payload: False)
    monkeypatch.setattr(_HOOK.gate, 'context_gate', lambda payload: False)
    for command in _ROOT_SESSION_SIDE_DOORS:
        assert _hook_reason(command, cwd=str(REPO_ROOT)) is None, (
            f'{command!r} must be ADMITTED once the scope is off, proving the rows are scope-driven'
        )


@pytest.mark.parametrize(
    'command',
    _R6_NAMED_FORMS,
    ids=[
        'git-dir-work-tree',
        'env-git-dir',
        'alias-resolved',
        'zsh-later-segment',
        'watch-later-segment',
        'zsh-leading-cd',
    ],
)
def test_r6_names_the_plan_from_every_commit_form(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """``--git-dir``/``--work-tree``, ``GIT_DIR`` and a resolved alias all name the plan."""
    base = tmp_path / '.plan' / 'local'
    base.mkdir(parents=True)
    _managed_plan(base, 'plan-a', '6-finalize')
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    (base / 'worktrees' / 'plan-a').mkdir(parents=True)
    assert _hook_reason(command, cwd=str(tmp_path)) == _HOOK._R6_REASON

    harness = build_harness(tmp_path_factory.mktemp('d3-r6-forms'))
    _managed_plan(harness.plan_base, 'plan-a', '6-finalize')
    blocked, message = harness.blocks(shell_event(command))
    assert blocked, f'guard.js must refuse {command!r}; message={message!r}'
    assert 'R6' in message, f'the refusal must be rule R6; message={message!r}'


@pytest.mark.parametrize(
    'command',
    [
        'git -C "$WT" commit -m "fix: x"',
        'git -c "alias.x=!sh -c commit" x -m "fix: x"',
    ],
    ids=['unexpanded-dash-C', 'shell-alias'],
)
def test_r6_refuses_an_unresolvable_commit_target(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """An unexpanded ``-C`` variable and a shell aliased subcommand are refused fail-closed.

    The guard cannot know where such a commit lands, so it refuses rather than
    guessing a plan — even with no plan state present. The refusal is scoped to
    the enforced scope, so the payload names this repository as its project (as a
    real main-checkout session does) while the shell cwd is the fixture.
    """
    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
    monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(REPO_ROOT))
    assert _hook_reason(command, cwd=str(tmp_path)) == _HOOK._R6_REASON

    harness = build_harness(tmp_path_factory.mktemp('d3-r6-unresolvable'))
    blocked, message = harness.blocks(shell_event(command))
    assert blocked, f'guard.js must refuse {command!r}; message={message!r}'
    assert 'R6' in message, f'the refusal must be rule R6; message={message!r}'


def test_r6_refuses_a_wrapper_spliced_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """A commit hidden inside ``watch 'git commit …'`` is still a raw commit."""
    base = tmp_path / '.plan' / 'local'
    base.mkdir(parents=True)
    _managed_plan(base, 'plan-a', '6-finalize')
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    (base / 'worktrees' / 'plan-a').mkdir(parents=True)
    command = "watch 'git -C .plan/local/worktrees/plan-a commit -m x'"
    assert _hook_reason(command, cwd=str(tmp_path)) == _HOOK._R6_REASON
    harness = build_harness(tmp_path_factory.mktemp('d3-r6-spliced'))
    _managed_plan(harness.plan_base, 'plan-a', '6-finalize')
    blocked, message = harness.blocks(shell_event(command))
    assert blocked, f'guard.js must refuse {command!r}; message={message!r}'
    assert 'R6' in message, f'the refusal must be rule R6; message={message!r}'


def test_r6_still_ignores_non_commit_subcommands(tmp_path: Path) -> None:
    """The widened naming does not turn unrelated git subcommands into commits."""
    for command in ('git status', 'git --git-dir=.git/worktrees/x --work-tree=.plan/local/worktrees/x status'):
        assert _hook_reason(command, cwd=str(tmp_path)) is None, command
