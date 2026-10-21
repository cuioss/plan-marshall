#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Exact admissions — D2 of PLAN-LB-79.

Three admissions the merged guard and hook granted too cheaply:

* the RELATIVE executor form, which was admitted whatever directory the shell
  was in;
* the deployed bundle roots, which were a broad hard-coded list rather than the
  resolver's DEPLOY roots, compared lexically rather than after ``realpath``;
* the consumer scope, which a runbook-lane run in a consumer repository never
  reached because every lane call carries the main checkout as its workdir.

Every row is driven through BOTH implementations by REAL EXECUTION: the OpenCode
plugin under ``node`` and the Claude hook's ``evaluate``.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from _guard_node_harness import (
    SUB_AGENT_AGENT,
    GuardHarness,
    build_harness,
    layout_data,
    shell_event,
)

from conftest import load_script_module

_HOOK = load_script_module(
    'plan-marshall',
    'platform-runtime',
    'claude_pretooluse_hook.py',
    module_name='exact_admissions_pretooluse_hook',
    register=False,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

#: The flat deployed skill directory a steward script is admitted under.
_DEPLOYED_SKILL = 'plan-marshall-marshall-steward'
_DEPLOYED_SCRIPT = 'scripts/determine_mode.py'


def _hook_guard(harness: GuardHarness, command: str, *, workdir: str | None = None) -> tuple[bool, str]:
    """Run one command through the guard; returns ``(blocked, message)``."""
    return harness.blocks(shell_event(command, agent=SUB_AGENT_AGENT, workdir=workdir))


def _hook_refused(command: str, *, cwd: str = str(REPO_ROOT), in_context: bool = True) -> bool:
    payload: dict = {'tool_name': 'Bash', 'tool_input': {'command': command}, 'cwd': cwd}
    if in_context:
        payload['agent_type'] = SUB_AGENT_AGENT
    return _HOOK.evaluate(payload) is not None


def _hook_refused_in_project(command: str, *, cwd: str, project_dir: Path) -> bool:
    """Evaluate with an explicit ``CLAUDE_PROJECT_DIR``, as a real session has.

    Without it the hook derives its repository root FROM the shell cwd, so a
    ``cwd``-only probe could never distinguish "the root" from "somewhere else".
    """
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('CLAUDE_PROJECT_DIR', str(project_dir))
        return _hook_refused(command, cwd=cwd)


def _deploy_flat(root: Path) -> Path:
    script = root / 'skills' / _DEPLOYED_SKILL / _DEPLOYED_SCRIPT
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text('# deployed\n', encoding='utf-8')
    return script


# =============================================================================
# The relative executor: admitted only from the repository root
# =============================================================================

_EXECUTOR_CALL = 'python3 .plan/execute-script.py a:b:c verb'


def test_executor_from_the_repository_root_is_admitted(tmp_path_factory: pytest.TempPathFactory) -> None:
    """The documented relative executor form run from the repository root passes.

    This clause holds at the base sha — it is the positive control that keeps the
    tightening from refusing the documented invocation.
    """
    harness = build_harness(tmp_path_factory.mktemp('exact-root'))
    blocked, message = harness.blocks(shell_event(_EXECUTOR_CALL, agent=SUB_AGENT_AGENT))
    assert not blocked, f'the documented executor call from the root must pass; message={message!r}'
    assert not _hook_refused(_EXECUTOR_CALL)


def test_executor_from_another_workdir_is_refused(tmp_path_factory: pytest.TempPathFactory) -> None:
    """A shell call with ``workdir=/tmp/x`` may not use the relative executor."""
    harness = build_harness(tmp_path_factory.mktemp('exact-workdir'))
    blocked, message = _hook_guard(harness, _EXECUTOR_CALL, workdir='/tmp/x')
    assert blocked, 'the relative executor from another workdir must be refused'
    assert 'R5' in message, f'the refusal must be rule R5; message={message!r}'
    assert _hook_refused_in_project(_EXECUTOR_CALL, cwd='/tmp/x', project_dir=REPO_ROOT), (
        'the hook must refuse it from another cwd too'
    )


def test_executor_after_an_env_chdir_is_refused(tmp_path_factory: pytest.TempPathFactory) -> None:
    """``env -C /tmp/x python3 .plan/execute-script.py`` is refused."""
    command = 'env -C /tmp/x python3 .plan/execute-script.py a:b:c verb'
    harness = build_harness(tmp_path_factory.mktemp('exact-env-c'))
    blocked, message = harness.blocks(shell_event(command, agent=SUB_AGENT_AGENT))
    assert blocked, 'an env -C directory change must defeat the relative admission'
    assert 'R5' in message, f'the refusal must be rule R5; message={message!r}'
    assert _hook_refused(command), 'the hook must refuse the env -C form too'


def test_executor_after_a_leading_cd_is_refused(tmp_path_factory: pytest.TempPathFactory) -> None:
    """A preceding ``cd /tmp/x`` followed by the relative executor is refused."""
    command = 'cd /tmp/x; python3 .plan/execute-script.py a:b:c verb'
    harness = build_harness(tmp_path_factory.mktemp('exact-cd'))
    blocked, _message = harness.blocks(shell_event(command, agent=SUB_AGENT_AGENT))
    assert blocked, 'a leading cd must not leave the relative executor admitted'
    assert _hook_refused(command), 'the hook must refuse the leading-cd form too'


# =============================================================================
# The deployed roots: the resolver's DEPLOY roots, after realpath
# =============================================================================


def test_a_script_under_an_unnamed_root_is_refused(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A script planted under ``~/.agents/skills`` is refused when no root names it.

    ``~/.agents/skills`` is a skill-DISCOVERY root, not a bundle-DEPLOY root: the
    shared layout names only the directories this marketplace deploys to, so a
    planted tree there is not a deployed bundle.
    """
    home = tmp_path_factory.mktemp('exact-home')
    planted = home / '.agents' / 'skills' / _DEPLOYED_SKILL / _DEPLOYED_SCRIPT
    planted.parent.mkdir(parents=True, exist_ok=True)
    planted.write_text('# planted\n', encoding='utf-8')
    harness = build_harness(
        tmp_path_factory.mktemp('exact-agents'),
        extra_env={'HOME': str(home), 'XDG_CONFIG_HOME': str(home / '.config')},
    )
    blocked, message = harness.blocks(shell_event(f'python3 {planted} mode'))
    assert blocked, f'a script under a root the layout does not name must be refused; message={message!r}'
    assert 'R5' in message

    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('XDG_CONFIG_HOME', str(home / '.config'))
    assert _hook_refused(f'python3 {planted} mode'), 'the hook must refuse the planted script too'


def test_a_symlink_out_of_a_deployed_root_is_refused(tmp_path_factory: pytest.TempPathFactory) -> None:
    """A deployed path that is a symlink OUT of the root is refused (realpath)."""
    deployed = tmp_path_factory.mktemp('exact-deployed')
    script = _deploy_flat(deployed)
    outside = tmp_path_factory.mktemp('exact-outside') / 'determine_mode.py'
    outside.write_text('# outside\n', encoding='utf-8')
    script.unlink()
    script.symlink_to(outside)
    harness = build_harness(tmp_path_factory.mktemp('exact-symlink'), extra_env={'OPENCODE_CONFIG_DIR': str(deployed)})
    blocked, message = harness.blocks(shell_event(f'python3 {script} mode'))
    assert blocked, f'a symlink out of a deployed root must be refused; message={message!r}'
    assert 'R5' in message


def test_opencode_config_dir_admits_the_deployed_bundle_script(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With ``OPENCODE_CONFIG_DIR`` set the deployed bundle script is still admitted.

    Covers both the deployed-root resolution (the layout's ``env`` template) and
    ``loadAllowList`` honouring the same override.
    """
    deployed = tmp_path_factory.mktemp('exact-flat-root')
    script = _deploy_flat(deployed)
    harness = build_harness(tmp_path_factory.mktemp('exact-flat'), extra_env={'OPENCODE_CONFIG_DIR': str(deployed)})
    blocked, message = harness.blocks(shell_event(f'python3 {script} mode'))
    assert not blocked, f'the deployed flat script must be admitted; message={message!r}'

    monkeypatch.setenv('OPENCODE_CONFIG_DIR', str(deployed))
    assert not _hook_refused(f'python3 {script} mode'), 'the hook must admit the deployed flat script too'


# =============================================================================
# The consumer scope: a runbook-lane run is bound
# =============================================================================


def test_consumer_python_is_refused_inside_a_lane_run(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A consumer repository IS bound while a lane run carries its marker."""
    consumer = Path(tempfile.mkdtemp(prefix='pm-consumer-lane-'))
    harness = build_harness(tmp_path_factory.mktemp('exact-lane-guard'), include_allowlist=False)
    admitted, message = harness.blocks(shell_event('python3 x.py'))
    assert not admitted, f'a consumer outside any plan context must be admitted; message={message!r}'

    marker = harness.root / '.plan' / 'temp' / 'rb-fixture' / 'progress.md'
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text('setup: fixture\n', encoding='utf-8')
    blocked, refused_message = harness.blocks(shell_event('python3 x.py'))
    assert blocked, 'inside a lane run the consumer command must be refused'
    assert 'R5' in refused_message, f'the refusal must be rule R5; message={refused_message!r}'

    monkeypatch.setattr(_HOOK, '_repo_root_from_hook_location', lambda: None)
    monkeypatch.setenv('CLAUDE_PROJECT_DIR', str(consumer))
    lane_marker = consumer / '.plan' / 'temp' / 'rb-fixture' / 'progress.md'
    lane_marker.parent.mkdir(parents=True, exist_ok=True)
    lane_marker.write_text('setup: fixture\n', encoding='utf-8')
    assert _hook_refused('python3 x.py', cwd=str(consumer), in_context=False) is True
    lane_marker.unlink()
    assert _hook_refused('python3 x.py', cwd=str(consumer), in_context=False) is False


def test_the_layout_data_is_the_one_shared_file() -> None:
    """The deployed roots come from the shared layout data, not a literal list."""
    layout = layout_data()
    assert layout.get('targets'), 'the shared deployed-layout data names no targets'
    guard_source = (REPO_ROOT / '.opencode/plugin/guard.js').read_text(encoding='utf-8')
    hook_source = (
        REPO_ROOT / 'marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_pretooluse_hook.py'
    ).read_text(encoding='utf-8')
    assert 'deployed-layout.json' in guard_source, 'guard.js does not name the shared deployed-layout data'
    assert "_LAYOUT_DATA_NAME = 'deployed-layout.json'" in hook_source, 'the hook does not name it either'
    for stale in ('.gemini', 'plugins/cache/plan-marshall'):
        assert stale not in guard_source, f'guard.js still carries a hard-coded {stale} root'
