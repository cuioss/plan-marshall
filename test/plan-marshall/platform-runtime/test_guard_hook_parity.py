#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Decision parity between the OpenCode guard plugin and the Claude hook.

Deliverable 1 makes the two decision tables identical on the interpreter
surface: quoting-aware tokenisation, the same wrapper stripping, the same
case handling, the same shared allow-list, and the same plan-context gate on
R5. A source-level comparison cannot show any of that, so every row below is
driven through BOTH implementations by REAL EXECUTION — the OpenCode plugin
under ``node`` and the Claude hook's ``evaluate`` — and the two verdicts must
agree.

The corpus is the INTERPRETER (R5) surface only. The guard's R4 python branch
(``python3 build.py``, ``python3 -m {pytest mypy ruff}``) is a deliberately
broader, UNCONDITIONAL rule with no hook counterpart; its documented
out-of-context divergence is pinned separately at the bottom rather than
folded into the parity table, where it would be a false equivalence.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _guard_node_harness import SUB_AGENT_AGENT, build_harness, shell_event

from conftest import load_script_module

_HOOK = load_script_module(
    'plan-marshall',
    'platform-runtime',
    'claude_pretooluse_hook.py',
    module_name='parity_pretooluse_hook',
    register=False,
)
REPO_ROOT = Path(__file__).resolve().parents[3]

#: ``(command, refused_in_context, refused_out_of_context)``. Both guards must
#: produce these values. ``refused`` means the guard threw and the hook returned
#: a deny reason.
_PARITY_CORPUS: tuple[tuple[str, bool, bool], ...] = (
    ('timeout 5 python3 -c "x"', True, False),
    ('python3.12 -c "x"', True, False),
    ('PYTHON3 -c "x"', True, False),
    ('env python3 -c "x"', True, False),
    ('nice -n 5 python3 -c "x"', True, False),
    ('nohup python3 -c "x"', True, False),
    ('env -S "python3 -c x"', True, False),
    ('xargs -I{} python3 -c "x"', True, False),
    ('timeout 600s python3 -m py_compile f.py', True, False),
    ('python3 -m py_compile f.py', True, False),
    ('python3 -mjson.tool', True, False),
    ('python3 marketplace/targets/sync.py --target opencode', False, False),
    ('python3 /abs/repo/.plan/execute-script.py a:b:c verb', False, False),
    ('python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list --plan-id x', False, False),
    ('python3 --version', False, False),
    ('python3', False, False),
)

_PARITY_IDS = [command for command, _in, _out in _PARITY_CORPUS]


def _hook_payload(command: str, *, in_context: bool) -> dict:
    payload: dict = {'tool_name': 'Bash', 'tool_input': {'command': command}}
    if in_context:
        payload['agent_type'] = SUB_AGENT_AGENT
    return payload


def _guard_refused(harness, command: str, *, in_context: bool) -> bool:
    event = shell_event(command, agent=SUB_AGENT_AGENT) if in_context else shell_event(command)
    return harness.run([event])[0].blocked


def test_parity_corpus_is_substantive() -> None:
    """The corpus must exercise both verdicts and both contexts, or it proves little."""
    assert len(_PARITY_CORPUS) >= 10, f'parity corpus too small: {len(_PARITY_CORPUS)} rows'
    assert any(in_context for _c, in_context, _o in _PARITY_CORPUS), 'no in-context refusal rows'
    assert any(not in_context for _c, in_context, _o in _PARITY_CORPUS), 'no allowed rows'


@pytest.mark.parametrize(('command', 'in_context', 'out_context'), _PARITY_CORPUS, ids=_PARITY_IDS)
def test_guards_agree_on_the_interpreter_surface(
    tmp_path_factory: pytest.TempPathFactory, command: str, in_context: bool, out_context: bool
) -> None:
    """Both guards refuse (or allow) each corpus row identically, in both contexts."""
    harness = build_harness(tmp_path_factory.mktemp('guard-parity'))

    guard_in = _guard_refused(harness, command, in_context=True)
    hook_in = _HOOK.evaluate(_hook_payload(command, in_context=True)) is not None
    assert guard_in == in_context, f'guard.js in-context verdict for {command!r}: got {guard_in}, expected {in_context}'
    assert hook_in == in_context, f'hook in-context verdict for {command!r}: got {hook_in}, expected {in_context}'

    guard_out = _guard_refused(harness, command, in_context=False)
    hook_out = _HOOK.evaluate(_hook_payload(command, in_context=False)) is not None
    assert guard_out == out_context, (
        f'guard.js out-context verdict for {command!r}: got {guard_out}, expected {out_context}'
    )
    assert hook_out == out_context, f'hook out-context verdict for {command!r}: got {hook_out}, expected {out_context}'


@pytest.mark.parametrize('command', ['python3 build.py', 'python3 -m pytest x'])
def test_guard_r4_python_branch_is_unconditional_where_the_hook_is_gated(
    tmp_path_factory: pytest.TempPathFactory, command: str
) -> None:
    """The guard's R4 python branch refuses out of context; the hook's gate still applies.

    This divergence is DELIBERATE and documented: R1–R4 stay unconditional in
    guard.js, while the Claude hook enforces every rule only inside a plan
    context. It is pinned here so the two surfaces cannot drift silently and so
    the parity table above is not read as claiming a symmetry the guard does not
    have.
    """
    harness = build_harness(tmp_path_factory.mktemp('guard-r4-out'))
    guard_out = _guard_refused(harness, command, in_context=False)
    hook_out = _HOOK.evaluate(_hook_payload(command, in_context=False)) is not None
    assert guard_out is True, f'guard.js must refuse {command!r} out of context (unconditional R4)'
    assert hook_out is False, f'hook must allow {command!r} out of context (gated)'
