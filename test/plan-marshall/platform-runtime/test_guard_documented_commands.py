#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D3 of PLAN-LB-88 — the two harnesses agree on the repository's own commands.

Three divergences remain after PLAN-LB-79:

* ``./pw generate`` is admitted by the guard's R4 and refused by the hook's R4,
  although ``CLAUDE.md`` § Multi-Assistant Support prescribes it. The verdict is
  DECIDED here: ``generate`` is admitted on both, and the decision is DATA in the
  ONE shared table (``build_wrapper_admission``), not a branch in each file;
* the absent-table branch refuses only when a RAW token is an interpreter, so
  ``zsh -c "python3 -c x"`` passes with the table missing on both harnesses;
* the file-search git verbs (``git grep`` / ``git -C … grep``) were left without a
  recorded decision — recorded in ``pretooluse-enforcement.md`` and pinned there
  by ``test_guard_enforcement_scope_docs.py``.

The shared row set below is driven through BOTH implementations by REAL
EXECUTION, and the two verdicts must agree with each other and with the row.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _guard_node_harness import (
    SUB_AGENT_AGENT,
    build_harness,
    guard_plugin_path,
    shell_event,
    wrapper_table,
)

from conftest import load_script_module

_HOOK = load_script_module(
    'plan-marshall',
    'platform-runtime',
    'claude_pretooluse_hook.py',
    module_name='documented_commands_pretooluse_hook',
    register=False,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

#: ``(command, refused)`` — the repository's own documented commands, shared by
#: both harnesses. A row is a promise the documentation makes.
_DOCUMENTED_COMMANDS: tuple[tuple[str, bool], ...] = (
    ('./pw generate', False),
    ('./pw generate --target opencode --output .plan/temp/generated', False),
    ('./pw verify', True),
    ('python3 .plan/execute-script.py a:b:c verb', False),
    (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args module-tests',
        False,
    ),
    ('python3 marketplace/targets/sync.py --target opencode', False),
)

_DOCUMENTED_IDS = [command for command, _refused in _DOCUMENTED_COMMANDS]


def _hook_refused(command: str) -> bool:
    payload = {'agent_type': SUB_AGENT_AGENT, 'tool_name': 'Bash', 'tool_input': {'command': command}}
    return _HOOK.evaluate(payload) is not None


def test_the_documented_command_rows_agree_on_both_harnesses(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Each shared row gets the same verdict from the guard under node and the hook."""
    assert len(_DOCUMENTED_COMMANDS) >= 6, 'the shared row set must cover the documented surfaces'
    assert any(refused for _c, refused in _DOCUMENTED_COMMANDS), 'no refused row'
    assert any(not refused for _c, refused in _DOCUMENTED_COMMANDS), 'no admitted row'
    harness = build_harness(tmp_path_factory.mktemp('guard-documented'))
    commands = [command for command, _refused in _DOCUMENTED_COMMANDS]
    outcomes = harness.run([shell_event(command, agent=SUB_AGENT_AGENT) for command in commands])
    for (command, refused), outcome in zip(_DOCUMENTED_COMMANDS, outcomes, strict=True):
        assert outcome.blocked == refused, (
            f'guard.js verdict for {command!r}: got blocked={outcome.blocked}, expected {refused}; '
            f'message={outcome.message!r}'
        )
        assert _hook_refused(command) == refused, (
            f'hook verdict for {command!r}: got refused={_hook_refused(command)}, expected {refused}'
        )


def test_the_pw_verdict_is_data_in_the_one_shared_table() -> None:
    """``./pw generate`` is admitted from the shared data, not a branch per file."""
    admission = wrapper_table().get('build_wrapper_admission') or {}
    assert 'generate' in (admission.get('pw_admitted_verbs') or []), 'the shared table must admit the generate verb'
    assert '--' in (admission.get('pw_admitted_prefixes') or []), (
        'the shared table must admit the -- prefixed invocations'
    )
    guard_source = guard_plugin_path().read_text(encoding='utf-8')
    hook_source = (
        REPO_ROOT / 'marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_pretooluse_hook.py'
    ).read_text(encoding='utf-8')
    assert 'build_wrapper_admission' in guard_source, 'guard.js does not read the shared admission data'
    assert 'build_wrapper_admission' in hook_source, 'the hook does not read the shared admission data'


def test_the_absent_table_refuses_a_spliced_interpreter(
    tmp_path_factory: pytest.TempPathFactory, tmp_path: Path
) -> None:
    """With ``r5-wrappers.json`` absent, an interpreter inside a command string is refused."""
    command = 'zsh -c "python3 -c x"'
    # An empty HOME / config root, so the guard cannot fall back to a DEPLOYED
    # copy of the table: this test is about the missing-table branch itself.
    empty = tmp_path / 'empty-home'
    empty.mkdir()
    harness = build_harness(
        tmp_path_factory.mktemp('guard-no-table'),
        include_wrapper_table=False,
        extra_env={
            'HOME': str(empty),
            'XDG_CONFIG_HOME': str(empty / '.config'),
            'OPENCODE_CONFIG_DIR': str(empty / 'skills'),
        },
    )
    blocked, message = harness.blocks(shell_event(command, agent=SUB_AGENT_AGENT))
    assert blocked, 'guard.js admitted a spliced interpreter with the shared table absent'
    assert 'R5' in message, f'the refusal must be rule R5; message={message!r}'

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(_HOOK, '_wrapper_table_path', lambda: Path('/nonexistent/r5-wrappers.json'))
        assert _HOOK._wrapper_table()['missing'] is True
        assert (
            _HOOK.evaluate({'agent_type': SUB_AGENT_AGENT, 'tool_name': 'Bash', 'tool_input': {'command': command}})
            == _HOOK._R5_REASON
        )

    allowed = 'zsh -c "echo hi"'
    blocked_control, control_message = harness.blocks(shell_event(allowed, agent=SUB_AGENT_AGENT))
    assert not blocked_control, (
        f'the absent-table branch must not refuse a command string that names no interpreter; '
        f'message={control_message!r}'
    )
