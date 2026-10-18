#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Decision parity between the OpenCode guard plugin and the Claude hook.

Deliverable 1 makes the two decision tables identical on the interpreter
surface: quoting-aware tokenisation, the same wrapper stripping, the same
case handling, the same shared allow-list (matched exactly on the script's
repository-relative path), and the same UNCONDITIONAL R5 — the plan-context
gate is gone, so R5 fires in every session on both harnesses. A source-level
comparison cannot show any of that, so every row below is driven through BOTH
implementations by REAL EXECUTION — the OpenCode plugin under ``node`` and the
Claude hook's ``evaluate`` — and the two verdicts must agree.

The corpus is the INTERPRETER (R5) surface only. The guard's R4 python branch
(``python3 build.py``, ``python3 -m {pytest mypy ruff}``) is a deliberately
broader rule with no hook counterpart; the bottom test pins that BOTH harnesses
still refuse those shapes out of context (the guard on R4, the hook on R5)
rather than folding them into the parity table, where they would be a false
equivalence.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _guard_node_harness import SUB_AGENT_AGENT, GuardHarness, build_harness, shell_event

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
#: a deny reason. R5 is enforced in EVERY session in both harnesses since
#: PLAN-LB-65 D1, so a refusal row is refused in context AND out of it — the two
#: columns agree on every row and are kept separate so a future re-gating shows
#: up here.
_PARITY_CORPUS: tuple[tuple[str, bool, bool], ...] = (
    ('timeout 5 python3 -c "x"', True, True),
    ('python3.12 -c "x"', True, True),
    ('PYTHON3 -c "x"', True, True),
    ('env python3 -c "x"', True, True),
    ('nice -n 5 python3 -c "x"', True, True),
    ('nohup python3 -c "x"', True, True),
    ('env -S "python3 -c x"', True, True),
    ('xargs -I{} python3 -c "x"', True, True),
    ('timeout 600s python3 -m py_compile f.py', True, True),
    ('python3 -m py_compile f.py', True, True),
    ('python3 -mjson.tool', True, True),
    ('python3 marketplace/targets/sync.py --target opencode', False, False),
    ('python3 .plan/execute-script.py a:b:c verb', False, False),
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


def _guard_refused(harness: GuardHarness, command: str, *, in_context: bool) -> bool:
    event = shell_event(command, agent=SUB_AGENT_AGENT) if in_context else shell_event(command)
    return bool(harness.run([event])[0].blocked)


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
def test_guards_agree_that_interpreter_bypasses_are_unconditional(
    tmp_path_factory: pytest.TempPathFactory, command: str
) -> None:
    """Both guards refuse an interpreter bypass out of context, by their own rule.

    Before PLAN-LB-65 D1 the guard refused via its unconditional R4 while the
    hook's context gate let it through — the documented divergence. R5 is now
    unconditional on both harnesses, so both refuse out of context: the guard on
    its R4 python branch, the hook on R5. The row is kept so the surface cannot
    silently re-diverge.
    """
    harness = build_harness(tmp_path_factory.mktemp('guard-r4-out'))
    guard_out = _guard_refused(harness, command, in_context=False)
    hook_out = _HOOK.evaluate(_hook_payload(command, in_context=False)) is not None
    assert guard_out is True, f'guard.js must refuse {command!r} out of context'
    assert hook_out is True, f'hook must refuse {command!r} out of context'


# =============================================================================
# D3 — the R5 side doors: one shared table, both harnesses refuse
# =============================================================================


#: The R5 side doors D3 closes: an interpreter reached through a wrapper prefix,
#: a shell spawn, a bare ``-``/``-<`` stdin form, and ``uv run``. Every row must
#: be refused on BOTH harnesses. Driven in a plan context (Signal 1) so the two
#: guards' refusal rule is the only variable.
_SIDE_DOOR_REFUSED: tuple[str, ...] = (
    'python3 - <<< "print(1)"',
    'python3 - < x.py',
    'python3 -',
    'exec python3 -c "print(1)"',
    'stdbuf -o0 python3 -c "print(1)"',
    'stdbuf -o L python3 -c "print(1)"',
    'setsid python3 -c "print(1)"',
    'nice python3 -c "print(1)"',
    'timeout 5 python3 -c "print(1)"',
    'env -i python3 script.py',
    'bash -c "python3 -c print(1)"',
    'sh -c "python3 -c print(1)"',
    'uv run python -c "print(1)"',
)

_SIDE_DOOR_REFUSED_IDS = list(_SIDE_DOOR_REFUSED)


@pytest.mark.parametrize('command', _SIDE_DOOR_REFUSED, ids=_SIDE_DOOR_REFUSED_IDS)
def test_guards_refuse_every_r5_side_door(tmp_path_factory: pytest.TempPathFactory, command: str) -> None:
    """Each side-door form is refused by BOTH the guard plugin and the hook."""
    harness = build_harness(tmp_path_factory.mktemp('guard-side-door'))
    guard_blocked = _guard_refused(harness, command, in_context=True)
    hook_reason = _HOOK.evaluate(_hook_payload(command, in_context=True))
    assert guard_blocked is True, f'guard.js must refuse {command!r}'
    assert hook_reason is not None, f'hook must refuse {command!r}'


#: The forms that MUST still pass: the documented relative executor form, the
#: D1 allow-listed repository-relative scripts, and the bare interpreter probe.
_SIDE_DOOR_ALLOWED: tuple[str, ...] = (
    'python3 .plan/execute-script.py a:b:c verb',
    'python3 marketplace/targets/sync.py --target opencode',
    'python3 marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/determine_mode.py mode',
    'python3 marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py ensure-executor',
    'python3 --version',
    'python3',
)

_SIDE_DOOR_ALLOWED_IDS = list(_SIDE_DOOR_ALLOWED)


@pytest.mark.parametrize('command', _SIDE_DOOR_ALLOWED, ids=_SIDE_DOOR_ALLOWED_IDS)
def test_guards_allow_the_documented_and_admitted_forms(tmp_path_factory: pytest.TempPathFactory, command: str) -> None:
    """The documented executor form and the D1 admitted forms still pass both guards."""
    harness = build_harness(tmp_path_factory.mktemp('guard-side-door-allow'))
    guard_blocked, guard_message = harness.blocks(shell_event(command, agent=SUB_AGENT_AGENT))
    hook_reason = _HOOK.evaluate(_hook_payload(command, in_context=True))
    assert not guard_blocked, f'guard.js must allow {command!r}; message={guard_message!r}'
    assert hook_reason is None, f'hook must allow {command!r}; reason={hook_reason!r}'


@pytest.mark.parametrize(
    'command',
    [
        'python3 /tmp/x/.plan/execute-script.py a:b:c verb',
        'python3 /tmp/x/skills/marshall-steward/scripts/determine_mode.py mode',
        'python3 /tmp/x/marketplace/targets/sync.py',
    ],
    ids=['executor-outside-repo', 'same-named-script-outside-deploy', 'allow-listed-basename-outside-repo'],
)
def test_guards_refuse_paths_outside_the_repository_and_the_deployment(
    tmp_path_factory: pytest.TempPathFactory, command: str
) -> None:
    """An out-of-repository copy never matches — neither the executor nor the allow-list."""
    harness = build_harness(tmp_path_factory.mktemp('guard-outside'))
    guard_blocked = _guard_refused(harness, command, in_context=True)
    hook_reason = _HOOK.evaluate(_hook_payload(command, in_context=True))
    assert guard_blocked is True, f'guard.js must refuse {command!r}'
    assert hook_reason is not None, f'hook must refuse {command!r}'
