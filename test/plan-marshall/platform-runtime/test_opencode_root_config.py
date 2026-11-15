#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pins for the repository's root ``opencode.json`` under OpenCode 2 semantics.

OpenCode 2 merges the project ``permissions`` list with the agent's
``permissions`` list and applies the LAST matching rule. The base policy an
agent's ruleset begins with was OBSERVED at ``opencode v2.2.7``
(``GET /api/agent/execution-context-reader``) as
``{action: "*", resource: "*", effect: allow}`` — so an action no rule names is
allowed, not asked, and a catch-all rule has to come first in each list or it
overrides every specific rule before it. These tests evaluate the file the same
way and pin the effects that matter, so a reordering that silently disables the
deny rules fails here.

The guard plugin pin covers the other OpenCode 2 change: the shell tool is
named ``shell`` (OpenCode 1 named it ``bash``).
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest


def _repo_file(*parts: str) -> pathlib.Path:
    """Locate a repository-root file by walking up from this test file."""
    for parent in pathlib.Path(__file__).resolve().parents:
        candidate = parent.joinpath(*parts)
        if candidate.is_file():
            return candidate
    raise AssertionError(f'{"/".join(parts)} not found above the test file')


_CONFIG = json.loads(_repo_file('opencode.json').read_text(encoding='utf-8'))
_AGENTS = sorted(_CONFIG['agents'])
assert _AGENTS, 'opencode.json declares no agents, so the per-agent pins would run over nothing'

#: The agents whose source declares no ``Bash``/``Write``/``Edit``
#: (``agents/execution-context-reader.md``: ``tools: WebSearch, WebFetch, Read,
#: Grep``). Their blocks must give them no shell or edit allow.
_READER_AGENTS = [name for name in _AGENTS if name.startswith('execution-context-reader')]
assert _READER_AGENTS, 'opencode.json declares no reader agents, so the reader pins would run over nothing'

#: The base policy observed at ``opencode v2.2.7``: allow-all, denied only by a
#: later explicit row.
_BASE_POLICY = {'action': '*', 'resource': '*', 'effect': 'allow'}


def _matches(pattern: str, command: str) -> bool:
    regex = '^' + re.escape(pattern).replace(r'\*', '.*') + '$'
    return re.match(regex, command, re.S) is not None


def _effect(agent: str, command: str) -> str:
    """Evaluate a shell command the way OpenCode 2 does: base policy, last match wins."""
    rules = [_BASE_POLICY] + list(_CONFIG['permissions']) + list(_CONFIG['agents'][agent].get('permissions', []))
    hits = [r for r in rules if r['action'] in ('shell', '*') and _matches(r['resource'], command)]
    return hits[-1]['effect'] if hits else 'allow'


@pytest.mark.parametrize('agent', _AGENTS)
@pytest.mark.parametrize(
    'command',
    [
        'gh pr view 1',
        'glab mr list',
        'rm x',
        'git stash pop',
        'git restore x',
        'git clean -fd',
        'mvn verify',
        'python3 -m pytest test',
    ],
)
def test_deny_rules_hold_for_every_agent(agent: str, command: str) -> None:
    assert _effect(agent, command) == 'deny'


@pytest.mark.parametrize('agent', _AGENTS)
def test_executor_is_allowed_for_every_write_capable_agent(agent: str) -> None:
    """The executor permit stands for agents whose source declares ``Bash``.

    A reader agent declares no ``Bash``, so its block must not hand it the
    executor permit: the root configuration is reconciled with the source.
    """
    effect = _effect(agent, 'python3 .plan/execute-script.py a:b:c')
    if agent in _READER_AGENTS:
        assert effect != 'allow', f'{agent} declares no Bash but its block allows the executor'
    else:
        assert effect == 'allow'


@pytest.mark.parametrize('agent', _READER_AGENTS)
def test_reader_blocks_carry_no_allow_row(agent: str) -> None:
    """A source declaring ``WebSearch, WebFetch, Read, Grep`` gains no allow.

    The block may deny (a restriction) and may restate the catch-all ``ask``,
    but an ``allow`` row would grant a shell or edit capability the source
    does not declare.
    """
    allows = [rule for rule in _CONFIG['agents'][agent].get('permissions', []) if rule['effect'] == 'allow']
    assert allows == [], f'{agent}: {allows}'


def test_catch_all_is_first_in_every_rule_list() -> None:
    lists = {'permissions': _CONFIG['permissions']}
    lists.update({f'agents.{name}': agent.get('permissions', []) for name, agent in _CONFIG['agents'].items()})
    for name, rules in lists.items():
        catch_all = [i for i, r in enumerate(rules) if r['action'] == 'shell' and r['resource'] == '*']
        assert catch_all in ([], [0]), f'{name}: shell catch-all must be the first rule, found at {catch_all}'


def test_guard_plugin_guards_the_opencode_2_shell_tool() -> None:
    source = _repo_file('.opencode', 'plugin', 'guard.js').read_text(encoding='utf-8')
    gate = re.search(r'if \((tool !== "[a-z_]+"(?: && tool !== "[a-z_]+")*)\) return', source)
    assert gate is not None, 'guard.js carries no shell-tool gate'
    guarded = set(re.findall(r'tool !== "([a-z_]+)"', gate.group(1)))
    assert 'shell' in guarded
