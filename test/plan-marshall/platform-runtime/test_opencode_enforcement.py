#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pins for the OpenCode enforcement matrix and the guard decision table.

Covers deliverable 5's enforcement surface:

* Deny-class operations are refused (``protect-path`` emits a real deny
  with ``status: success``, never an honest no-op).
* Ask-class operations surface as asks (the ``ask(...)`` wrapper threads
  through ``to_opencode_grant`` into the persisted bash map).
* Carve-out operations pass (the executor permit resolves to ``allow``).
* The D2 guard decision table (``.opencode/plugin/guard.js``,
  ``tool.execute.before``) is exercised by REAL EXECUTION under ``node``
  (see ``_guard_node_harness``), so a decision change fails the suite
  instead of passing against a stale literal. The declared sets are still
  parsed out of guard.js and compared to their pins so set drift fails
  loudly, and a few source-shape pins guard structural ordering.
  Read-side probes (``ls``, ``cat``, ``head``, ``tail``, ``grep``,
  ``find``) are NOT in the R2 guard class — the two-tier permission map
  governs them.

conftest.py sets up PYTHONPATH so the cross-skill imports resolve without
manual sys.path manipulation.
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any

import pytest
from _guard_node_harness import SUB_AGENT_AGENT, WORKTREE_WORKDIR, build_harness, shell_event
from opencode_runtime import OpenCodeRuntime, to_opencode_grant
from toon_parser import parse_toon

from conftest import get_script_path, run_script

MANAGE_STATUS = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')
_PHASES = '1-init,2-refine,3-outline,4-plan,5-execute,6-finalize'


def _write_managed_plan(base: pathlib.Path, plan_id: str, phase: str) -> pathlib.Path:
    """Create a REAL plan under *base* whose status is written by ``manage-status``.

    The R6 tests must not hand-write ``status.json``: the field is
    ``current_phase`` (never ``phase``), and only the sanctioned writer can
    produce it. Returns the plan directory.
    """
    env = {'PLAN_BASE_DIR': str(base), 'PLAN_DIR_NAME': '.plan'}
    created = run_script(
        MANAGE_STATUS, 'create', '--plan-id', plan_id, '--title', 't', '--phases', _PHASES, env_overrides=env
    )
    assert created.returncode == 0, f'manage-status create failed: {created.stdout}{created.stderr}'
    assert parse_toon(created.stdout).get('status') == 'success', f'manage-status create refused: {created.stdout}'
    _set_managed_phase(base, plan_id, phase)
    return base / 'plans' / plan_id


def _set_managed_phase(base: pathlib.Path, plan_id: str, phase: str) -> None:
    """Move an EXISTING managed plan to *phase* through ``manage-status set-phase``."""
    env = {'PLAN_BASE_DIR': str(base), 'PLAN_DIR_NAME': '.plan'}
    shifted = run_script(MANAGE_STATUS, 'set-phase', '--plan-id', plan_id, '--phase', phase, env_overrides=env)
    assert shifted.returncode == 0, f'manage-status set-phase failed: {shifted.stdout}{shifted.stderr}'


def _parse(output: str) -> dict[str, Any]:
    result = parse_toon(output)
    assert isinstance(result, dict), f'parse_toon returned non-dict: {output!r}'
    return result


# =============================================================================
# Deny class — protect-path emits a real deny
# =============================================================================


def test_deny_class_protect_path_emits_real_deny(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Deny-class operations are refused via a real writing deny, not a no-op."""
    monkeypatch.chdir(tmp_path)
    protected = str(tmp_path / 'creds')
    result = _parse(OpenCodeRuntime().permission_fix('project', 'protect-path', [protected], False))
    assert result['status'] == 'success'
    assert result['fix_operation'] == 'protect-path'
    assert result['changes_applied'] >= 1

    written = json.loads((tmp_path / 'opencode.json').read_text(encoding='utf-8'))
    assert 'permission' not in written, 'a `permission` map must never be added beside a `permissions` list'
    entries = {
        rule['resource']: rule['effect']
        for rule in written['permissions']
        if rule['action'] in ('read', 'shell') and isinstance(rule.get('resource'), str)
    }
    guarded = {pattern: action for pattern, action in entries.items() if 'creds' in pattern}
    assert guarded, 'protect-path wrote no guard entries for the protected directory'
    assert all(action == 'deny' for action in guarded.values())


def test_deny_wrapper_action_survives_grant_translation() -> None:
    """A deny(...) intent reaches the bash map as deny, never degrading to allow."""
    category, pattern, action = to_opencode_grant('deny(gh *)')
    assert category == 'bash'
    assert pattern == 'gh *'
    assert action == 'deny'


# =============================================================================
# Ask class — ask operations surface as asks
# =============================================================================


def test_ask_class_surfaces_as_ask(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ask-class operations persist as ask rules in the permissions list."""
    monkeypatch.chdir(tmp_path)
    result = _parse(OpenCodeRuntime().permission_fix('project', 'ensure', ['ask(docker *)'], False))
    assert result['status'] == 'success'
    settings = json.loads((tmp_path / 'opencode.json').read_text(encoding='utf-8'))
    rules = [rule for rule in settings['permissions'] if rule['action'] == 'shell' and rule['resource'] == 'docker *']
    assert rules and rules[-1]['effect'] == 'ask'


def test_ask_wrapper_action_survives_grant_translation() -> None:
    """An ask(...) intent reaches the bash map as ask."""
    category, pattern, action = to_opencode_grant('ask(git push *)')
    assert category == 'bash'
    assert pattern == 'git push *'
    assert action == 'ask'


# =============================================================================
# Carve-out — the executor permit passes
# =============================================================================


def test_carve_out_executor_permit_passes(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The executor permit is allowed — the confined surface stays usable."""
    monkeypatch.chdir(tmp_path)
    permit = 'python3 .plan/execute-script.py *'
    category, pattern, action = to_opencode_grant(permit)
    assert (category, pattern, action) == ('bash', permit, 'allow')
    result = _parse(OpenCodeRuntime().permission_fix('project', 'ensure', [permit], False))
    assert result['status'] == 'success'
    settings = json.loads((tmp_path / 'opencode.json').read_text(encoding='utf-8'))
    assert any(
        rule['action'] == 'shell' and rule['resource'] == permit and rule['effect'] == 'allow'
        for rule in settings['permissions']
    )


# =============================================================================
# Guard decision-table mirror (D2 behavioral contract)
# =============================================================================

#: Guard decision-table sets parsed from the plugin at test time (D2
#: behavioral contract). Every `const <NAME> = new Set([...])` below is read
#: out of `.opencode/plugin/guard.js` — never a hand-maintained literal — so
#: removing an entry from the plugin fails the contract test instead of
#: passing against a stale copy.
_GUARD_SET_NAMES = (
    'MUTATION_FILE_OPS',
    'BARE_BUILD_TOOLS',
    'JS_RUNNERS',
    'JS_RUNNER_BUILD_VERBS',
    'PYTHON_DIRECT_RUNNERS',
    'PYTHON_INTERPRETERS',
    'R5_ALWAYS_REFUSE_FLAGS',
)


def _guard_plugin_path() -> pathlib.Path:
    """Locate `.opencode/plugin/guard.js` by walking up from this file."""
    for parent in pathlib.Path(__file__).resolve().parents:
        candidate = parent / '.opencode' / 'plugin' / 'guard.js'
        if candidate.is_file():
            return candidate
    raise AssertionError('.opencode/plugin/guard.js not found above the test file')


def _parse_guard_sets(path: pathlib.Path) -> dict[str, frozenset[str]]:
    """Parse every declared set out of the guard plugin source."""
    source = path.read_text(encoding='utf-8')
    parsed: dict[str, frozenset[str]] = {}
    for name in _GUARD_SET_NAMES:
        match = re.search(r'\bconst\s+' + name + r'\s*=\s*new\s+Set\(\[(.*?)\]\)', source, re.DOTALL)
        assert match is not None, f'guard.js carries no {name} set'
        members = frozenset(re.findall(r'"([^"]+)"', match.group(1)))
        assert members, f'guard.js {name} parsed empty'
        parsed[name] = members
    return parsed


#: Expected guard decision-table pins. The parsed sets above must equal
#: these exactly — drift in either direction (a removed or an added entry)
#: fails the contract test. ``SHELL_WRAPPERS`` is NOT here: the wrapper table
#: lives in the shared data file ``standards/r5-wrappers.json``, so there is no
#: literal wrapper set in the plugin to parse (see
#: ``test_guard_carries_no_literal_wrapper_table``).
_GUARD_EXPECTED: dict[str, frozenset[str]] = {
    'MUTATION_FILE_OPS': frozenset(
        {
            'rm',
            'mv',
            'cp',
            'touch',
            'mkdir',
            'rmdir',
            'truncate',
            'tee',
            'chmod',
            'chown',
            'ln',
            'dd',
            'sh',
            'bash',
            'source',
        }
    ),
    'BARE_BUILD_TOOLS': frozenset({'mvn', 'mvnw', 'gradle', 'gradlew', 'make', 'cmake', 'ant', 'uv'}),
    'JS_RUNNERS': frozenset({'npm', 'npx', 'bun', 'pnpm', 'yarn'}),
    'JS_RUNNER_BUILD_VERBS': frozenset({'test', 'run', 'build'}),
    'PYTHON_DIRECT_RUNNERS': frozenset({'pytest', 'mypy', 'ruff'}),
    'PYTHON_INTERPRETERS': frozenset({'python', 'python3', 'pypy', 'pypy3'}),
    'R5_ALWAYS_REFUSE_FLAGS': frozenset({'-c', '-m'}),
}

_GUARD_SETS = _parse_guard_sets(_guard_plugin_path())

#: R2 — shell file operations, mutation class (parsed from guard.js
#: MUTATION_FILE_OPS). Read-side probes are NOT members.
_GUARD_MUTATION_FILE_OPS = _GUARD_SETS['MUTATION_FILE_OPS']

#: Read-side probes governed by the two-tier permission map, never by R2.
_GUARD_READ_PROBES = ('ls', 'cat', 'head', 'tail', 'grep', 'find')

#: R4 — bare build tools bypassing the executor (parsed from guard.js
#: BARE_BUILD_TOOLS plus the Python direct runners).
_GUARD_BARE_BUILD_TOOLS = _GUARD_SETS['BARE_BUILD_TOOLS']
_GUARD_PYTHON_DIRECT_RUNNERS = _GUARD_SETS['PYTHON_DIRECT_RUNNERS']
#: R4 — JS runner tool names (parsed from the named guard.js JS_RUNNERS set,
#: consumed by the R4 branch — removing a runner from the plugin fails the
#: contract test instead of passing against a stale literal).
_GUARD_JS_RUNNERS = _GUARD_SETS['JS_RUNNERS']
_GUARD_JS_RUNNER_BUILD_VERBS = _GUARD_SETS['JS_RUNNER_BUILD_VERBS']


def _guard_plugin_source() -> str:
    """Return the raw guard.js plugin source for literal and shape pins."""
    return _guard_plugin_path().read_text(encoding='utf-8')


def _parse_guard_executor_path(source: str) -> str:
    """Parse the generated-executor path literal out of guard.js.

    The literal is the string ``normalizedIsExecutorPath`` compares against —
    parsing it here (instead of repeating it) keeps the R3 pin a statement
    about the plugin rather than about a local copy: changing the path in
    the plugin fails this pin instead of passing against a stale literal.
    """
    match = re.search(r'"(\.plan/execute-script\.py)"', source)
    assert match is not None, 'guard.js carries no quoted .plan/execute-script.py path literal'
    return match.group(1)


#: R3 — the generated executor path direct edits must target, parsed from
#: guard.js rather than repeated as a local literal.
_GUARD_EXECUTOR_PATH = _parse_guard_executor_path(_guard_plugin_source())

#: R4 — the executor permit exempt from the hard-coded-build block, derived
#: from the parsed executor path (the two must stay in lock-step in the
#: plugin: the permit is ``python3 `` plus the executor path).
_GUARD_EXECUTOR_PERMIT_PREFIX = f'python3 {_GUARD_EXECUTOR_PATH}'


def test_guard_r2_blocks_mutation_class_not_read_probes() -> None:
    """R2 blocks the mutation class; read probes stay map-governed."""
    assert 'rm' in _GUARD_MUTATION_FILE_OPS
    assert 'sh' in _GUARD_MUTATION_FILE_OPS
    for probe in _GUARD_READ_PROBES:
        assert probe not in _GUARD_MUTATION_FILE_OPS, f'read probe {probe!r} must not be an R2 guard member'


def test_guard_r4_pins_bare_build_tools() -> None:
    """R4 pins the hard-coded build bypass set."""
    assert 'mvn' in _GUARD_BARE_BUILD_TOOLS
    assert 'pytest' in _GUARD_PYTHON_DIRECT_RUNNERS
    assert 'npm' in _GUARD_JS_RUNNERS


def test_guard_sets_match_plugin_contract() -> None:
    """Every set parsed from guard.js equals its expected pin exactly."""
    assert set(_GUARD_SETS) == set(_GUARD_EXPECTED), 'parsed set names drifted from the contract'
    for name, expected in _GUARD_EXPECTED.items():
        assert _GUARD_SETS[name] == expected, f'guard.js {name} drifted from its pin'


def test_guard_r4_pw_allowlists_generate_prefix_only() -> None:
    """R4 blocks `./pw` unless its verb is explicitly allowed.

    The decision table allowlists by prefix, not by verb set: only
    `./pw generate*` and `./pw --*` pass, and a missing verb blocks — so a
    new build.py-routed alias cannot bypass R4 by omission from a set.
    """
    source = _guard_plugin_source()
    assert 'PW_BUILD_VERBS' not in source, 'guard.js must not gate ./pw on a verb set'
    assert 'verb.startsWith("generate")' in source, 'guard.js must allowlist the generate prefix'
    assert 'verb.startsWith("--")' in source, 'guard.js must allowlist the -- prefix'


def test_guard_r3_pins_executor_path() -> None:
    """R3 names the generated executor path as the blocked edit target.

    The path is parsed out of guard.js (not repeated as a local literal),
    and the R3 hook branch references the ``targetsExecutor`` /
    ``normalizedIsExecutorPath`` helpers that compare against it — so
    changing the path in the plugin fails this pin instead of passing
    against a stale copy.
    """
    assert _GUARD_EXECUTOR_PATH == '.plan/execute-script.py'
    assert _GUARD_EXECUTOR_PATH.endswith('execute-script.py')
    source = _guard_plugin_source()
    assert 'targetsExecutor' in source
    assert 'normalizedIsExecutorPath' in source
    assert 'patchTextTargetsExecutor' in source


def test_guard_r4_exempts_executor_permit() -> None:
    """The executor permit is exempt from the R4 hard-coded-build block.

    The permit prefix derives from the executor path parsed out of guard.js
    (the two stay in lock-step), and the plugin checks the R1 chaining gate
    before the permit and the permit before every R4 build-tool branch — so
    the exemption cannot silently widen past the executor invocation.
    """
    assert _GUARD_EXECUTOR_PERMIT_PREFIX == 'python3 .plan/execute-script.py'
    command = 'python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list --plan-id x'
    assert command.startswith(_GUARD_EXECUTOR_PERMIT_PREFIX)
    source = _guard_plugin_source()
    assert 'isExecutorPermit' in source
    r1_at = source.index('hasChainingConstructor(command)')
    permit_at = source.index('isExecutorPermit(command, root, workdir)) return')
    bare_at = source.index('BARE_BUILD_TOOLS.has')
    assert r1_at < permit_at < bare_at, 'hook order must be R1 gate, then executor permit, then R4 branches'


def test_guard_r5_refusal_names_remedy() -> None:
    """The R5 refusal names the remedy: executor for builds, manage tools for state."""
    source = _guard_plugin_source()
    assert 'python3 .plan/execute-script.py' in source
    assert 'manage-*' in source


# =============================================================================
# Guard decision table, exercised by real execution under node (D1)
# =============================================================================


def test_guard_node_refuses_wrapper_and_versioned_interpreter(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Done-when (a): a wrapper or a versioned interpreter does not hide an R5 bypass."""
    harness = build_harness(tmp_path_factory.mktemp('guard-a'))
    commands = ['timeout 5 python3 -c "x"', 'python3.12 -c "x"']
    outcomes = harness.run([shell_event(command, agent=SUB_AGENT_AGENT) for command in commands])
    for command, outcome in zip(commands, outcomes, strict=True):
        assert outcome.blocked, f'guard.js must refuse {command!r}; message={outcome.message!r}'
        assert 'R5' in outcome.message, f'the refusal for {command!r} must be rule R5; message={outcome.message!r}'


def test_guard_node_allows_documented_non_executor_invocations(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Done-when (b): the documented sync engine and the relative executor call pass."""
    harness = build_harness(tmp_path_factory.mktemp('guard-b'))
    commands = [
        'python3 marketplace/targets/sync.py --target opencode',
        'python3 .plan/execute-script.py a:b:c verb',
    ]
    outcomes = harness.run([shell_event(command, agent=SUB_AGENT_AGENT) for command in commands])
    for command, outcome in zip(commands, outcomes, strict=True):
        assert not outcome.blocked, f'guard.js must allow {command!r}; message={outcome.message!r}'


def test_guard_node_outside_context_still_refuses_py_compile(tmp_path_factory: pytest.TempPathFactory) -> None:
    """R5 binds in this repository in every session, so py_compile is refused outside a plan context too."""
    harness = build_harness(tmp_path_factory.mktemp('guard-c'))
    blocked, message = harness.blocks(shell_event('python3 -m py_compile f.py'))
    assert blocked, f'guard.js must refuse py_compile outside a plan context; message={message!r}'
    assert 'R5' in message, f'the refusal must be rule R5; message={message!r}'


def test_guard_node_signal2_worktree_workdir_enables_r5(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Signal 2 (a worktree cwd) alone turns R5 on — the gate is an OR."""
    harness = build_harness(tmp_path_factory.mktemp('guard-signal2'))
    blocked, message = harness.blocks(shell_event('python3 -c "x"', workdir=WORKTREE_WORKDIR))
    assert blocked, f'a worktree cwd must enable R5; message={message!r}'
    assert 'R5' in message


def test_guard_node_allows_python_build_py_out_of_context_but_refuses_in(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """The R4 python branch stays unconditional while R5 is gated."""
    harness = build_harness(tmp_path_factory.mktemp('guard-r4'))
    out_blocked, _ = harness.blocks(shell_event('python3 build.py'))
    in_blocked, in_message = harness.blocks(shell_event('python3 build.py', agent=SUB_AGENT_AGENT))
    assert out_blocked, 'R4 (python3 build.py) must refuse out of context'
    assert in_blocked, 'R4 (python3 build.py) must refuse in context'
    assert 'R4' in in_message


def test_guard_node_r6_refuses_raw_commit_in_finalize(tmp_path_factory: pytest.TempPathFactory) -> None:
    """R6: a raw ``git commit`` is refused while the plan is in phase 6-finalize.

    The plan is named by the worktree path and its phase is read from the plan's
    own ``status.json`` field ``current_phase``, written by ``manage-status`` and
    resolved MAIN-ANCHORED — never an alphabetically-first plan found by a
    directory scan.
    """
    harness = build_harness(tmp_path_factory.mktemp('guard-r6'))
    _write_managed_plan(harness.plan_base, 'plan-a', '6-finalize')
    worktree = harness.root / '.plan' / 'local' / 'worktrees' / 'plan-a'
    worktree.mkdir(parents=True, exist_ok=True)

    blocked, message = harness.blocks(shell_event('git commit -m "fix: x"', workdir=str(worktree)))
    assert blocked, 'a raw git commit must be refused in 6-finalize'
    assert 'R6' in message, f'the refusal must be rule R6; message={message!r}'

    blocked_opt, _ = harness.blocks(shell_event('git -C . commit -m "fix: y"', workdir=str(worktree)))
    assert blocked_opt, 'git -C . commit must still resolve to the commit subcommand'

    blocked_wrapped, _ = harness.blocks(shell_event('env git commit -m "fix: w"', workdir=str(worktree)))
    assert blocked_wrapped, 'a wrapper-prefixed raw commit must still be refused'

    _set_managed_phase(harness.plan_base, 'plan-a', '5-execute')
    allowed, _ = harness.blocks(shell_event('git commit -m "fix: z"', workdir=str(worktree)))
    assert not allowed, 'a raw commit outside 6-finalize must pass through'


def test_guard_node_r6_names_the_plan_from_the_dash_C_target(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Done-when (D2): the ``-C`` target names the plan, from the main checkout.

    ``git -C .plan/local/worktrees/{plan} commit`` is the persona-mandated form
    run from the main checkout. With NO shell ``workdir``, the plan must be named
    from the ``-C`` value (resolved against the project root); the runbook-lane
    worktree carries no plan record and passes.
    """
    harness = build_harness(tmp_path_factory.mktemp('guard-r6-dashc'))
    _write_managed_plan(harness.plan_base, 'plan-a', '6-finalize')

    blocked, message = harness.blocks(shell_event('git -C .plan/local/worktrees/plan-a commit -m "fix: x"'))
    assert blocked, f'a raw commit into the named worktree must be refused; message={message!r}'
    assert 'R6' in message, f'the refusal must be rule R6; message={message!r}'

    # Successive -C values COMPOSE (git resolves each against the running target).
    blocked_chained, chained_message = harness.blocks(
        shell_event('git -C . -C .plan/local/worktrees/plan-a commit -m "fix: c"')
    )
    assert blocked_chained, f'a chained -C commit must be refused; message={chained_message!r}'
    assert 'R6' in chained_message, f'the refusal must be rule R6; message={chained_message!r}'

    lane_ok, lane_message = harness.blocks(
        shell_event('git -C .plan/local/worktrees/lb-99-runbook-lane commit -m "fix: y"')
    )
    assert not lane_ok, f'a runbook-lane worktree with no plan record must pass; message={lane_message!r}'


def test_guard_node_r6_does_not_judge_another_plans_status(tmp_path_factory: pytest.TempPathFactory) -> None:
    """R6 reads the phase of the worktree NAMED plan, never the first plan found.

    A finalize plan sits under the same main anchor; the committing worktree's own
    plan is in 5-execute. Resolving by directory scan would refuse this commit.
    """
    harness = build_harness(tmp_path_factory.mktemp('guard-r6-named'))
    _write_managed_plan(harness.plan_base, 'aaa-other', '6-finalize')
    _write_managed_plan(harness.plan_base, 'plan-z', '5-execute')

    mine = harness.root / '.plan' / 'local' / 'worktrees' / 'plan-z'
    mine.mkdir(parents=True, exist_ok=True)

    blocked, message = harness.blocks(shell_event('git commit -m "fix: x"', workdir=str(mine)))
    assert not blocked, f'the commit must be judged by plan-z (5-execute), not aaa-other; message={message!r}'


def test_guard_node_r6_reads_the_worktree_resident_record(tmp_path_factory: pytest.TempPathFactory) -> None:
    """R6 reads the WORKTREE-RESIDENT plan record — the live one during phase 5+."""
    harness = build_harness(tmp_path_factory.mktemp('guard-r6-resident'))
    worktree = harness.root / '.plan' / 'local' / 'worktrees' / 'plan-a'
    worktree.mkdir(parents=True, exist_ok=True)
    _write_managed_plan(worktree / '.plan' / 'local', 'plan-a', '6-finalize')

    blocked, message = harness.blocks(shell_event('git commit -m "fix: x"', workdir=str(worktree)))
    assert blocked, f'the worktree-resident record must drive R6; message={message!r}'
    assert 'R6' in message


def test_guard_node_refuses_a_relative_script_from_outside_the_project(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """A relative allow-listed token run from another cwd resolves outside the repo."""
    harness = build_harness(tmp_path_factory.mktemp('guard-r5-cwd'))
    blocked, message = harness.blocks(shell_event('python3 marketplace/targets/sync.py', workdir='/tmp/elsewhere'))
    assert blocked, f'a copy under another cwd must be refused; message={message!r}'
    assert 'R5' in message


def test_guard_node_r6_no_plan_state_does_not_fire(tmp_path_factory: pytest.TempPathFactory) -> None:
    """R6 needs plan state: with no status.json a raw commit is untouched."""
    harness = build_harness(tmp_path_factory.mktemp('guard-r6-none'))
    blocked, _ = harness.blocks(shell_event('git commit -m "fix: x"', agent=SUB_AGENT_AGENT))
    assert not blocked


def test_guard_node_r4_reads_an_attached_m_module(tmp_path_factory: pytest.TempPathFactory) -> None:
    """The R4 python branch reads an attached ``-mpytest`` module (guard parity)."""
    harness = build_harness(tmp_path_factory.mktemp('guard-r4-m'))
    blocked, message = harness.blocks(shell_event('python3 -mpytest x', agent=SUB_AGENT_AGENT))
    assert blocked, 'python3 -mpytest must be refused'
    assert 'R4' in message, f'the refusal must be rule R4; message={message!r}'


# =============================================================================
# D1 — R5 binds in this repository in every session; the allow-list is exact
# =============================================================================

#: The documented repository-relative form of the steward's permission-fix
#: script. The allow-list entry is this exact repository-relative path, so the
#: invocation below is permitted; a basename or a copy outside the repository is
#: not.
_DOCUMENTED_PERMISSION_FIX = 'marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py'


def test_guard_node_root_session_refuses_python_c(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Done-when (D1): a ROOT session (no plan context) in this repo still enforces R5.

    The command carries no sub-agent identity and no worktree workdir, so the
    plan-context gate is OFF — yet this repository binds R5 in every session, so
    ``python3 -c`` is refused.
    """
    harness = build_harness(tmp_path_factory.mktemp('guard-d1-root'))
    blocked, message = harness.blocks(shell_event('python3 -c "x"'))
    assert blocked, f'a root session must refuse python3 -c; message={message!r}'
    assert 'R5' in message, f'the refusal must be rule R5; message={message!r}'


def test_guard_node_root_session_refuses_outside_repo_script(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Done-when (D1): a copy of an allow-listed script OUTSIDE the repo is refused.

    ``/tmp/x/permission_fix.py`` shares the basename of an allow-list entry but
    is not the repository-relative path, so it must be refused (the basename
    bypass PLAN-LB-62 shipped).
    """
    harness = build_harness(tmp_path_factory.mktemp('guard-d1-outside'))
    blocked, message = harness.blocks(shell_event('python3 /tmp/x/permission_fix.py'))
    assert blocked, f'a script outside the repository must be refused; message={message!r}'
    assert 'R5' in message, f'the refusal must be rule R5; message={message!r}'


def test_guard_node_root_session_allows_documented_repo_relative_script(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Done-when (D1): the documented repository-relative form is allowed."""
    harness = build_harness(tmp_path_factory.mktemp('guard-d1-allow'))
    command = f'python3 {_DOCUMENTED_PERMISSION_FIX} ensure-executor --target project --dry-run'
    blocked, message = harness.blocks(shell_event(command))
    assert not blocked, f'the documented repo-relative invocation must be allowed; message={message!r}'


@pytest.mark.parametrize('command', ['python3 -u x.py', 'python3 foo.py', 'python3 -Ic "x"'])
def test_guard_node_refuses_extra_interpreter_shapes(command: str, tmp_path_factory: pytest.TempPathFactory) -> None:
    """Done-when (D1): the executed guard refuses the extra interpreter shapes."""
    harness = build_harness(tmp_path_factory.mktemp('guard-d1-shapes'))
    blocked, message = harness.blocks(shell_event(command))
    assert blocked, f'{command!r} must be refused; message={message!r}'
    assert 'R5' in message, f'the refusal for {command!r} must be rule R5; message={message!r}'


# =============================================================================
# D1 — the deployed bundle-relative allow-list, and the consumer scope
# =============================================================================

#: The bundle-relative entry form a deployed steward script is admitted by.
_FLAT_DEPLOYED_SKILL = 'plan-marshall-marshall-steward'
_NESTED_DEPLOYED_VERSION = '1.0.0'


def _deploy_flat(root: pathlib.Path, skill_dir_name: str, relative: str) -> pathlib.Path:
    """Write a deployed FLAT skill tree under ``{root}/skills/``; return the script."""
    script = root / 'skills' / skill_dir_name / relative
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text('# deployed\n', encoding='utf-8')
    return script


def test_guard_node_admits_a_flat_deployed_bundle_script(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Done-when (D1): the guard admits a steward script at its FLAT deployed path."""
    deployed = tmp_path_factory.mktemp('opencode-flat-root')
    script = _deploy_flat(deployed, _FLAT_DEPLOYED_SKILL, 'scripts/determine_mode.py')
    harness = build_harness(tmp_path_factory.mktemp('guard-d1-flat'), extra_env={'OPENCODE_CONFIG_DIR': str(deployed)})

    blocked, message = harness.blocks(shell_event(f'python3 {script} mode'))
    assert not blocked, f'the deployed flat script must be admitted; message={message!r}'


def test_guard_node_admits_a_nested_cache_bundle_script(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Done-when (D1): the guard admits the nested-cache steward and generator scripts."""
    home = tmp_path_factory.mktemp('home')
    base = home / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / 'plan-marshall' / _NESTED_DEPLOYED_VERSION
    marker = base / '.claude-plugin' / 'plugin.json'
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text('{"name": "plan-marshall"}\n', encoding='utf-8')
    scripts = {
        'determine_mode.py': ('marshall-steward', 'mode'),
        'generate_executor.py': ('tools-script-executor', 'generate'),
    }
    commands = []
    for name, (skill, verb) in scripts.items():
        script = base / 'skills' / skill / 'scripts' / name
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text('# deployed\n', encoding='utf-8')
        commands.append(f'python3 {script} {verb}')
    harness = build_harness(
        tmp_path_factory.mktemp('guard-d1-nested'),
        extra_env={'HOME': str(home), 'XDG_CONFIG_HOME': str(home / '.config')},
    )

    outcomes = harness.run([shell_event(command) for command in commands])
    for command, outcome in zip(commands, outcomes, strict=True):
        assert not outcome.blocked, f'the cache-path script must be admitted: {command!r} — {outcome.message!r}'


def test_guard_node_refuses_a_non_deployed_same_named_script(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Done-when (D1): a same-named script under a NON-deployed directory is refused."""
    deployed = tmp_path_factory.mktemp('opencode-flat-root-2')
    _deploy_flat(deployed, _FLAT_DEPLOYED_SKILL, 'scripts/determine_mode.py')
    harness = build_harness(
        tmp_path_factory.mktemp('guard-d1-nondeployed'), extra_env={'OPENCODE_CONFIG_DIR': str(deployed)}
    )
    elsewhere = tmp_path_factory.mktemp('not-deployed')
    impostor = elsewhere / 'skills' / 'marshall-steward' / 'scripts' / 'determine_mode.py'
    impostor.parent.mkdir(parents=True, exist_ok=True)
    impostor.write_text('# impostor\n', encoding='utf-8')

    blocked, message = harness.blocks(shell_event(f'python3 {impostor} mode'))
    assert blocked, f'a non-deployed same-named script must be refused; message={message!r}'
    assert 'R5' in message, f'the refusal must be rule R5; message={message!r}'


def test_guard_node_consumer_out_of_context_allows_ordinary_python(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Done-when (D1): a consumer repository outside a plan context is not refused.

    The scratch root carries no repository marker (no allow-list file), so R5 does
    not bind and the consumer's ordinary Python work passes.
    """
    harness = build_harness(tmp_path_factory.mktemp('guard-consumer'), include_allowlist=False)
    for command in ('python3 -m pip install x', 'python3 x.py', 'python3 -m venv .venv'):
        blocked, message = harness.blocks(shell_event(command))
        assert not blocked, f'a consumer must be able to run {command!r}; message={message!r}'


def test_guard_node_consumer_inside_a_plan_worktree_still_refuses(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Done-when (D1): the same consumer command IS refused inside a plan worktree."""
    harness = build_harness(tmp_path_factory.mktemp('guard-consumer-in'), include_allowlist=False)
    blocked, message = harness.blocks(shell_event('python3 -m pip install x', workdir=WORKTREE_WORKDIR))
    assert blocked, f'inside a plan worktree the consumer command must be refused; message={message!r}'
    assert 'R5' in message, f'the refusal must be rule R5; message={message!r}'


def test_guard_node_this_repository_binds_every_session(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Done-when (D1): in THIS repository R5 binds even outside a plan context."""
    harness = build_harness(tmp_path_factory.mktemp('guard-this-repo'))
    blocked, message = harness.blocks(shell_event('python3 x.py'))
    assert blocked, f'this repository must refuse python3 x.py in a root session; message={message!r}'
    assert 'R5' in message
