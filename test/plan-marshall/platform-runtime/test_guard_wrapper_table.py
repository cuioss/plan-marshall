#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ONE shared wrapper table — D1 of PLAN-LB-79.

The wrapper prefixes the R5 interpreter check strips used to be two literal
copies (``guard.js`` ``SHELL_WRAPPERS``/``WRAPPER_VALUE_OPTS`` and the hook's
``_R5_SHELL_WRAPPERS``/``_R5_WRAPPER_VALUE_OPTS``). They now live in ONE data
file — ``standards/r5-wrappers.json``, the sibling of ``r5-allowlist.json`` —
read by the OpenCode guard plugin, the Claude hook and these pins.

Every row below is driven through BOTH implementations by REAL EXECUTION (the
plugin under ``node``, the hook's ``evaluate``), so a wrapper that only one side
knows about fails here. The wrapper population is DERIVED from the data file, so
an entry added to the table without a working stripper on either side fails, and
an entry removed from the table fails the probe that still names it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from _guard_node_harness import (
    SUB_AGENT_AGENT,
    GuardHarness,
    build_harness,
    guard_plugin_path,
    shell_event,
    wrapper_table,
    wrapper_table_path,
)

from conftest import load_script_module

_HOOK = load_script_module(
    'plan-marshall',
    'platform-runtime',
    'claude_pretooluse_hook.py',
    module_name='wrapper_table_pretooluse_hook',
    register=False,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _hook_refused(command: str) -> bool:
    payload = {'agent_type': SUB_AGENT_AGENT, 'tool_name': 'Bash', 'tool_input': {'command': command}}
    return _HOOK.evaluate(payload) is not None


def _wrapper_probe(name: str, spec: dict[str, Any]) -> str:
    """Build ``{wrapper} {positionals} python3 -c x`` from the table entry.

    The leading positionals the table declares (timeout's DURATION, flock's lock
    file, chrt's priority, taskset's mask) are supplied first, so the probe
    reaches the interpreter instead of being consumed as the wrapper's own
    argument — exactly the shape a real invocation has.
    """
    positionals = ['0'] * int(spec.get('leading_positionals') or 0)
    return ' '.join([name, *positionals, 'python3', '-c', 'x'])


_TABLE = wrapper_table()
_WRAPPERS = _TABLE.get('wrappers', {})

#: Wrappers that are ALSO R2 shell spawns, so the guard's R2 refuses them before
#: the interpreter check runs (the hook's R2 does the same).
_R2_SHELLS = frozenset({'bash', 'sh'})


def test_the_shared_wrapper_table_exists_and_carries_the_wrappers() -> None:
    """The one shared data file must exist and declare a substantive population."""
    assert wrapper_table_path().is_file(), f'the shared wrapper table is missing: {wrapper_table_path()}'
    assert _WRAPPERS, 'the shared wrapper table declares no wrappers'
    for required in ('env', 'sudo', 'timeout', 'ionice', 'chrt', 'taskset', 'flock', 'script', 'watch', 'parallel'):
        assert required in _WRAPPERS, f'the wrapper table lost {required!r}'


def test_neither_implementation_carries_a_literal_wrapper_table() -> None:
    """Both readers load the SAME data file; neither keeps a second literal list."""
    guard_source = guard_plugin_path().read_text(encoding='utf-8')
    hook_source = (
        REPO_ROOT / 'marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_pretooluse_hook.py'
    ).read_text(encoding='utf-8')
    assert 'SHELL_WRAPPERS' not in guard_source, 'guard.js still carries a literal wrapper set'
    assert 'WRAPPER_VALUE_OPTS' not in guard_source, 'guard.js still carries a literal value-option map'
    assert '_R5_SHELL_WRAPPERS' not in hook_source, 'the hook still carries a literal wrapper set'
    assert '_R5_WRAPPER_VALUE_OPTS' not in hook_source, 'the hook still carries a literal value-option map'
    assert 'r5-wrappers.json' in guard_source, 'guard.js does not name the shared wrapper table'
    assert "_R5_WRAPPER_TABLE_NAME = 'r5-wrappers.json'" in hook_source, (
        'the hook does not name the shared wrapper table'
    )
    assert _HOOK._wrapper_table_path() == wrapper_table_path(), 'the hook resolves a different wrapper table file'
    assert not _HOOK._wrapper_table()['missing'], 'the hook cannot read the shared wrapper table'


@pytest.mark.parametrize('name', sorted(_WRAPPERS))
def test_both_harnesses_strip_every_table_wrapper(name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
    """A wrapper declared in the table hides nothing on EITHER harness."""
    command = _wrapper_probe(name, _WRAPPERS[name])
    assert _hook_refused(command), f'the hook must refuse {command!r}'
    harness: GuardHarness = build_harness(tmp_path_factory.mktemp(f'guard-wrapper-{name}'))
    blocked, message = harness.blocks(shell_event(command, agent=SUB_AGENT_AGENT))
    assert blocked, f'guard.js must refuse {command!r}'
    if name not in _R2_SHELLS:
        # `bash`/`sh` are ALSO R2 shell spawns, so the guard's own R2 refuses them
        # first; every other wrapper must reach the interpreter rule.
        assert 'R5' in message, f'the guard refusal for {command!r} must be rule R5; message={message!r}'


#: The D1 Done-when rows, verbatim: path-qualified wrappers, an option cluster, a
#: value-taking sudo option, and the wrappers the merged code did not know.
_D1_REFUSED: tuple[str, ...] = (
    '/usr/bin/env python3 -c x',
    '/usr/bin/timeout 5 python3 -c x',
    'env -iu FOO python3 -c x',
    'sudo -D /tmp python3 -c x',
    'sudo -p P python3 -c x',
    'ionice python3 -c x',
    'chrt -f 1 python3 -c x',
    'taskset -c 0-3 python3 -c x',
    'flock /tmp/lock python3 -c x',
    'watch python3 -c x',
    'parallel python3 -c x',
    'busybox sh -c "python3 -c x"',
    'zsh -c "python3 -c x"',
    'dash -c "python3 -c x"',
    'ksh -c "python3 -c x"',
    '$SHELL -c "python3 -c x"',
    'pypy3 -c x',
    'find . -exec python3 -c x {} +',
    'find . -execdir python3 -c x {} +',
)


@pytest.mark.parametrize('command', _D1_REFUSED, ids=list(_D1_REFUSED))
def test_d1_side_doors_are_refused_on_both_harnesses(command: str, tmp_path_factory: pytest.TempPathFactory) -> None:
    """Every D1 row is refused by the guard under node AND by the hook."""
    harness: GuardHarness = build_harness(tmp_path_factory.mktemp('guard-d1-wrapper'))
    blocked, message = harness.blocks(shell_event(command, agent=SUB_AGENT_AGENT))
    assert blocked, f'guard.js must refuse {command!r}'
    assert 'R5' in message, f'the guard refusal must be rule R5; message={message!r}'
    assert _hook_refused(command), f'the hook must refuse {command!r}'


def test_every_table_wrapper_has_a_probe_or_a_named_row() -> None:
    """The probes are DERIVED, so a table entry cannot be silently unexercised.

    Each table wrapper produces one generic probe (``<wrapper> … python3 -c x``),
    and the D1 rows cover the wrappers whose real shape needs an option (a shell's
    ``-c`` string, ``find -exec``, a path-qualified spelling). A wrapper added to
    the table is therefore exercised without editing this list.
    """
    asserted = set(_WRAPPERS)
    assert asserted, 'no wrappers to exercise'
    for name in ('zsh', 'dash', 'ksh', '$SHELL'):
        assert name in asserted, f'the shells the D1 rows name must stay in the table: {name!r}'
