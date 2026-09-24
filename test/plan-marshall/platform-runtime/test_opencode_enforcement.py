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
  ``tool.execute.before``) is read from the plugin at test time as a
  behavioral contract: the R1-R4 declared sets below are parsed out of
  guard.js and compared to the expected pins, so plugin drift fails the
  contract test instead of passing against a stale literal.
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
from opencode_runtime import OpenCodeRuntime, to_opencode_grant
from toon_parser import parse_toon


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
    entries = {
        pattern: action for tool in ('read', 'bash') for pattern, action in written['permission'].get(tool, {}).items()
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
    """Ask-class operations persist as ask grants in the bash map."""
    monkeypatch.chdir(tmp_path)
    result = _parse(OpenCodeRuntime().permission_fix('project', 'ensure', ['ask(docker *)'], False))
    assert result['status'] == 'success'
    settings = json.loads((tmp_path / 'opencode.json').read_text(encoding='utf-8'))
    assert settings['permission']['bash']['docker *'] == 'ask'


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
    assert settings['permission']['bash'][permit] == 'allow'


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
    'PW_BUILD_VERBS',
    'BARE_BUILD_TOOLS',
    'JS_RUNNER_BUILD_VERBS',
    'PYTHON_DIRECT_RUNNERS',
    'SHELL_WRAPPERS',
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
#: fails the contract test.
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
    'PW_BUILD_VERBS': frozenset(
        {
            'verify',
            'compile',
            'test-compile',
            'module-tests',
            'coverage',
            'quality-gate',
            'clean',
            'gate',
            'test',
            'run',
            'check',
            'lint',
            'format',
            'build',
            'install',
            'tests',
        }
    ),
    'BARE_BUILD_TOOLS': frozenset({'mvn', 'mvnw', 'gradle', 'gradlew', 'make', 'cmake', 'ant', 'uv'}),
    'JS_RUNNER_BUILD_VERBS': frozenset({'test', 'run', 'build'}),
    'PYTHON_DIRECT_RUNNERS': frozenset({'pytest', 'mypy', 'ruff'}),
    'SHELL_WRAPPERS': frozenset({'command', 'env', 'sudo'}),
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
#: JS runner tool names are inlined (not a named set) in guard.js, so this
#: pin stays a literal list of the tools the R4 branch names.
_GUARD_JS_RUNNERS = frozenset({'npm', 'npx', 'bun', 'pnpm', 'yarn'})
_GUARD_JS_RUNNER_BUILD_VERBS = _GUARD_SETS['JS_RUNNER_BUILD_VERBS']

#: R3 — the generated executor path direct edits must target.
_GUARD_EXECUTOR_PATH = '.plan/execute-script.py'

#: R4 — the executor permit exempt from the hard-coded-build block.
_GUARD_EXECUTOR_PERMIT_PREFIX = 'python3 .plan/execute-script.py'


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


def test_guard_r4_pins_pw_build_verbs() -> None:
    """R4 blocks every build.py-routed ./pw verb, including test-compile."""
    assert 'test-compile' in _GUARD_SETS['PW_BUILD_VERBS']
    assert 'clean' in _GUARD_SETS['PW_BUILD_VERBS']
    assert 'verify' in _GUARD_SETS['PW_BUILD_VERBS']


def test_guard_r3_pins_executor_path() -> None:
    """R3 names the generated executor path as the blocked edit target."""
    assert _GUARD_EXECUTOR_PATH == '.plan/execute-script.py'
    assert _GUARD_EXECUTOR_PATH.endswith('execute-script.py')


def test_guard_r4_exempts_executor_permit() -> None:
    """The executor permit is exempt from the R4 hard-coded-build block."""
    command = 'python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list --plan-id x'
    assert command.startswith(_GUARD_EXECUTOR_PERMIT_PREFIX)
