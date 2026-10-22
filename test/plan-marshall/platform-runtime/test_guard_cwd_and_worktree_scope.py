#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D2 of PLAN-LB-88 — a spliced ``cd`` is applied and the exemption is exact.

Two admissions PLAN-LB-79 made exact are defeated by the same shells it added:

* ``effectiveCwd`` stops at the splice, so ``zsh -c "cd /tmp/x; python3
  .plan/execute-script.py …"`` is judged from the repository root and admitted
  although the executor really runs from ``/tmp/x``;
* the plan-worktree exemption is a ``worktrees/`` prefix with a slash boundary
  and admits ANY depth below it, including ``_orchestrator`` and sub-directories
  that are not the plan worktree root;
* with ``CLAUDE_PROJECT_DIR`` unset the hook used the payload ``cwd`` as its
  repository root, so a relative executor run from anywhere was admitted by a
  check that could not fail.

Every row runs against BOTH implementations by REAL EXECUTION.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _guard_node_harness import (
    SUB_AGENT_AGENT,
    GuardHarness,
    build_harness,
    shell_event,
    wrapper_table,
)

from conftest import load_script_module

_HOOK = load_script_module(
    'plan-marshall',
    'platform-runtime',
    'claude_pretooluse_hook.py',
    module_name='cwd_scope_pretooluse_hook',
    register=False,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

_SHELLS: tuple[str, ...] = tuple(wrapper_table().get('shells', ()))

_EXECUTOR = 'python3 .plan/execute-script.py a:b:c verb'


def _hook_payload(command: str, *, cwd: str) -> dict:
    return {'agent_type': SUB_AGENT_AGENT, 'tool_name': 'Bash', 'tool_input': {'command': command}, 'cwd': cwd}


def _hook_refused(command: str, *, cwd: str, project_dir: str) -> bool:
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('CLAUDE_PROJECT_DIR', project_dir)
        return _HOOK.evaluate(_hook_payload(command, cwd=cwd)) is not None


def test_a_cd_inside_a_spliced_string_is_applied_for_every_table_shell(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """The in-string ``cd`` moves the executor out of the repository — refused."""
    assert len(_SHELLS) >= 9, f'the shared table declares only {len(_SHELLS)} shells: {_SHELLS!r}'
    commands = [f'{shell} -c "cd /tmp/x; {_EXECUTOR}"' for shell in _SHELLS]
    harness: GuardHarness = build_harness(tmp_path_factory.mktemp('guard-spliced-cd'))
    outcomes = harness.run([shell_event(command, agent=SUB_AGENT_AGENT) for command in commands])
    for command, outcome in zip(commands, outcomes, strict=True):
        assert outcome.blocked, f'guard.js admitted {command!r}'
        assert 'R5' in outcome.message or 'R2' in outcome.message, (
            f'the refusal for {command!r} must be R5/R2; message={outcome.message!r}'
        )
    for command in commands:
        assert _HOOK.evaluate(_hook_payload(command, cwd=str(REPO_ROOT))) is not None, f'the hook admitted {command!r}'


def test_a_cd_inside_a_spliced_string_is_applied_for_splice_wrappers(tmp_path_factory: pytest.TempPathFactory) -> None:
    """The non-shell splice wrappers decide the admission only through the cd logic.

    Every table shell is ALSO an R2 shell spawn, so a shell row is refused even if
    the in-string ``cd`` is ignored. These rows are not R2 spawns: with the cd
    unapplied the relative executor would be admitted from the repository root,
    which is exactly the hole the deliverable closes.
    """
    rows = [
        f'env -S "cd /tmp/x; {_EXECUTOR}"',
        f'script -c "cd /tmp/x; {_EXECUTOR}"',
        f'watch "cd /tmp/x; {_EXECUTOR}"',
        f"parallel 'cd /tmp/x; {_EXECUTOR}'",
        f'flock 0 -c "cd /tmp/x; {_EXECUTOR}"',
    ]
    harness: GuardHarness = build_harness(tmp_path_factory.mktemp('guard-spliced-cd-wrappers'))
    outcomes = harness.run([shell_event(command, agent=SUB_AGENT_AGENT) for command in rows])
    for command, outcome in zip(rows, outcomes, strict=True):
        assert outcome.blocked, f'guard.js admitted {command!r}'
        assert 'R5' in outcome.message, f'the refusal for {command!r} must be R5; message={outcome.message!r}'
        assert _HOOK.evaluate(_hook_payload(command, cwd=str(REPO_ROOT))) is not None, f'the hook admitted {command!r}'

    # Matched positive control: the same shapes with the cd INTO the project root
    # leave the executor admitted.
    control = f'env -S "cd {harness.root}; {_EXECUTOR}"'
    admitted, control_message = harness.blocks(shell_event(control, agent=SUB_AGENT_AGENT))
    assert not admitted, f'the executor inside a spliced cd into the root must pass; message={control_message!r}'


def test_the_plan_worktree_exemption_is_exactly_one_level(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Only ``{root}/.plan/local/worktrees/{plan}`` is admitted — never deeper, never ``_orchestrator``."""
    harness = build_harness(tmp_path_factory.mktemp('guard-worktree-exact'))
    base = harness.root / '.plan' / 'local' / 'worktrees'
    plan = base / 'plan-a'
    plan.mkdir(parents=True, exist_ok=True)
    sub = plan / 'sub'
    sub.mkdir()
    orchestrator = base / '_orchestrator'
    orchestrator.mkdir()

    admitted, message = harness.blocks(shell_event(_EXECUTOR, agent=SUB_AGENT_AGENT, workdir=str(plan)))
    assert not admitted, f'the documented executor from the plan worktree must pass; message={message!r}'

    for refused_dir in (orchestrator, sub):
        blocked, refused_message = harness.blocks(
            shell_event(_EXECUTOR, agent=SUB_AGENT_AGENT, workdir=str(refused_dir))
        )
        assert blocked, f'guard.js admitted the relative executor from {refused_dir}'
        assert 'R5' in refused_message, f'the refusal must be rule R5; message={refused_message!r}'

    # The hook: the same three directories, with the scratch root as the project.
    assert not _hook_refused(_EXECUTOR, cwd=str(plan), project_dir=str(harness.root))
    for refused_dir in (orchestrator, sub):
        assert _hook_refused(_EXECUTOR, cwd=str(refused_dir), project_dir=str(harness.root)), (
            f'the hook admitted the relative executor from {refused_dir}'
        )


def test_the_hook_refuses_the_relative_executor_without_a_project_dir(tmp_path, monkeypatch) -> None:
    """With ``CLAUDE_PROJECT_DIR`` unset the root is the hook's own, never the payload cwd."""
    monkeypatch.delenv('CLAUDE_PROJECT_DIR', raising=False)
    payload = _hook_payload(_EXECUTOR, cwd=str(tmp_path))
    assert _HOOK.evaluate(payload) == _HOOK._R5_REASON, (
        'a cwd that is not the repository root must not become the repository root'
    )


def test_the_hook_still_admits_the_relative_executor_from_the_repository_root(monkeypatch) -> None:
    """The matched positive control: the documented invocation from the root passes."""
    monkeypatch.delenv('CLAUDE_PROJECT_DIR', raising=False)
    assert _HOOK.evaluate(_hook_payload(_EXECUTOR, cwd=str(REPO_ROOT))) is None
