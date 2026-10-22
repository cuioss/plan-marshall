#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D1 of PLAN-LB-88 — the spliced-command walk reads the grammar, or refuses it.

The R5 wrapper walk stops at the first level of shell grammar: ``splicedSegments``
splits on ``; & | newline`` only, so a grouping keyword, a shell option before
``-c``, a here-string or a script file hides the interpreter call from the check.

The decision recorded at outline is the FAIL-CLOSED FLOOR: a wrapper that runs a
command string (a shell's ``-c``, ``env -S``, ``script -c``), reads one from
stdin (a here-string / here-document), or is handed a script file is refused when
that text names an interpreter ANYWHERE — the segment walk decides only whether
the text is the admitted executor call. Extending the walk to C-like shell
grammar would restate the problem as a longer list, which is why it is not the
floor.

The population is DERIVED from the shared table: every table shell and every
table splice wrapper is crossed with every shell construct the table declares, so
a wrapper or a construct added later is covered by construction and one removed
from the data source fails the population floor below. Both harnesses are driven
by REAL EXECUTION (the plugin under ``node``, the hook's ``evaluate``).
"""

from __future__ import annotations

from pathlib import Path

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
    module_name='shell_constructs_pretooluse_hook',
    register=False,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

#: The one shared table both implementations read.
_TABLE = wrapper_table()
_SHELLS: tuple[str, ...] = tuple(_TABLE.get('shells', ()))
_CONSTRUCTS: tuple[str, ...] = tuple(_TABLE.get('shell_constructs', ()))
_WRAPPERS: dict = _TABLE.get('wrappers', {})

#: The interpreter call every construct wraps.
_CMD = 'python3 -c x'

#: The population floors. They are the reason a table wrapper or a construct
#: REMOVED from the data source fails this suite instead of silently shrinking it.
_MIN_SHELLS = 9
_MIN_CONSTRUCTS = 10
_MIN_WRAPPERS = 28
_MIN_SPLICE_WRAPPERS = 5


def _hook_refused(command: str, *, cwd: str | None = None) -> bool:
    payload: dict = {'agent_type': SUB_AGENT_AGENT, 'tool_name': 'Bash', 'tool_input': {'command': command}}
    if cwd is not None:
        payload['cwd'] = cwd
    return _HOOK.evaluate(payload) is not None


def _shell_command(shell: str, construct: str) -> str:
    return f"{shell} -c '{construct.replace('{CMD}', _CMD)}'"


def _splice_wrappers() -> tuple[str, ...]:
    """The non-shell wrappers that run a command string of their own.

    The table shells are excluded here because the shell cross-product above
    already covers them through their ``-c`` form; this set is what proves the
    floor is load-bearing beyond the shells (``env -S``, ``script -c``,
    ``flock -c``, ``watch`` and ``parallel``).
    """
    return tuple(
        sorted(
            name
            for name, spec in _WRAPPERS.items()
            if (spec.get('splice') or spec.get('splice_positional')) and name not in _SHELLS
        )
    )


def _splice_command(name: str, construct: str) -> str:
    """Build the wrapper's real command-string shape from its table entry."""
    spec = _WRAPPERS[name]
    body = construct.replace('{CMD}', _CMD)
    positionals = ['0'] * int(spec.get('leading_positionals') or 0)
    splice = spec.get('splice') or []
    if splice:
        return f'{name} {" ".join([*positionals, splice[0], repr(body)])}'
    return f'{name} {repr(body)}'


#: The D1 Done-when rows, verbatim.
_D1_ROWS: tuple[str, ...] = (
    "zsh -c 'if true; then python3 -c x; fi'",
    "zsh -c '(python3 -c x)'",
    "zsh -c '{ python3 -c x; }'",
    "zsh -c '! python3 -c x'",
    "zsh -c 'for i in 1; do python3 -c x; done'",
    "zsh -o pipefail -c 'python3 -c x'",
    "zsh <<< 'python3 -c x'",
    "fish -c 'python3 -c x'",
    "csh -c 'python3 -c x'",
    "tcsh -c 'python3 -c x'",
)


def test_the_table_declares_the_population_the_cross_product_needs() -> None:
    """The shells and the constructs are DATA, and the population floor is real.

    Removing one table wrapper or one construct from ``r5-wrappers.json`` drops the
    derived population below these floors, so the cross-product below fails rather
    than quietly covering less.
    """
    assert len(_SHELLS) >= _MIN_SHELLS, f'the shared table declares only {len(_SHELLS)} shells: {_SHELLS!r}'
    assert len(_CONSTRUCTS) >= _MIN_CONSTRUCTS, (
        f'the shared table declares only {len(_CONSTRUCTS)} shell constructs: {_CONSTRUCTS!r}'
    )
    assert len(_WRAPPERS) >= _MIN_WRAPPERS, (
        f'the shared table declares only {len(_WRAPPERS)} wrappers — a wrapper removed from the data '
        f'source must fail here: {sorted(_WRAPPERS)!r}'
    )
    assert len(_splice_wrappers()) >= _MIN_SPLICE_WRAPPERS, (
        f'the shared table declares only {len(_splice_wrappers())} non-shell splice wrappers: {_splice_wrappers()!r}'
    )
    for shell in ('bash', 'sh', 'dash', 'zsh', 'ksh', 'fish', 'csh', 'tcsh', '$SHELL'):
        assert shell in _SHELLS, f'the shared table lost the shell {shell!r}'
    for wrapper in ('fish', 'csh', 'tcsh'):
        assert wrapper in _WRAPPERS, f'the shared table lost the wrapper entry {wrapper!r}'
    assert {construct for construct in _CONSTRUCTS if '{CMD}' in construct} == set(_CONSTRUCTS), (
        'every construct template must carry the {CMD} placeholder'
    )


def test_every_shell_times_every_construct_is_refused(tmp_path_factory) -> None:
    """The generated cross-product is refused by BOTH harnesses.

    Not a hand-picked list: the rows come from the table's ``shells`` and
    ``shell_constructs``.
    """
    rows = [_shell_command(shell, construct) for shell in _SHELLS for construct in _CONSTRUCTS]
    assert rows, 'the cross-product is empty — the table declares nothing to cover'
    harness = build_harness(tmp_path_factory.mktemp('guard-shell-constructs'))
    outcomes = harness.run([shell_event(row, agent=SUB_AGENT_AGENT) for row in rows])
    admitted_by_guard = [row for row, outcome in zip(rows, outcomes, strict=True) if not outcome.blocked]
    assert not admitted_by_guard, f'guard.js admitted {len(admitted_by_guard)} construct row(s): {admitted_by_guard!r}'
    admitted_by_hook = [row for row in rows if not _hook_refused(row)]
    assert not admitted_by_hook, f'the hook admitted {len(admitted_by_hook)} construct row(s): {admitted_by_hook!r}'


def test_every_splice_wrapper_times_every_construct_is_refused(tmp_path_factory) -> None:
    """The floor also covers the non-shell splice wrappers, which R2 never sees.

    ``env -S``, ``script -c``, ``flock -c`` and the ``watch`` / ``parallel``
    positional command string run a string exactly as a shell does, so the same
    constructs must be refused through them.
    """
    wrappers = _splice_wrappers()
    assert wrappers, 'the table declares no splice wrapper'
    rows = [_splice_command(name, construct) for name in wrappers for construct in _CONSTRUCTS]
    assert rows, 'the splice cross-product is empty — the table declares nothing to cover'
    harness = build_harness(tmp_path_factory.mktemp('guard-splice-constructs'))
    outcomes = harness.run([shell_event(row, agent=SUB_AGENT_AGENT) for row in rows])
    admitted_by_guard = [row for row, outcome in zip(rows, outcomes, strict=True) if not outcome.blocked]
    assert not admitted_by_guard, f'guard.js admitted {len(admitted_by_guard)} splice row(s): {admitted_by_guard!r}'
    admitted_by_hook = [row for row in rows if not _hook_refused(row)]
    assert not admitted_by_hook, f'the hook admitted {len(admitted_by_hook)} splice row(s): {admitted_by_hook!r}'


def test_the_d1_done_when_rows_are_refused_on_both_harnesses(tmp_path_factory) -> None:
    """The Done-when's verbatim rows, on the guard under node and on the hook."""
    harness = build_harness(tmp_path_factory.mktemp('guard-d1-rows'))
    outcomes = harness.run([shell_event(row, agent=SUB_AGENT_AGENT) for row in _D1_ROWS])
    admitted_by_guard = [row for row, outcome in zip(_D1_ROWS, outcomes, strict=True) if not outcome.blocked]
    assert not admitted_by_guard, f'guard.js admitted {admitted_by_guard!r}'
    admitted_by_hook = [row for row in _D1_ROWS if not _hook_refused(row)]
    assert not admitted_by_hook, f'the hook admitted {admitted_by_hook!r}'


def test_a_table_shell_given_a_script_file_names_its_interpreter(tmp_path_factory) -> None:
    """``zsh script.zsh`` is refused when the script names an interpreter."""
    harness = build_harness(tmp_path_factory.mktemp('guard-script-file'))
    script = harness.root / 'fixture.zsh'
    script.write_text('#!/usr/bin/env zsh\npython3 -c x\n', encoding='utf-8')
    row = 'zsh fixture.zsh'
    blocked, message = harness.blocks(shell_event(row, agent=SUB_AGENT_AGENT))
    assert blocked, 'guard.js must refuse a table shell whose script names an interpreter'
    assert 'R5' in message, f'the refusal must be rule R5; message={message!r}'

    hook_dir = tmp_path_factory.mktemp('hook-script-file')
    (hook_dir / 'fixture.zsh').write_text('#!/usr/bin/env zsh\npython3 -c x\n', encoding='utf-8')
    assert _hook_refused(row, cwd=str(hook_dir)), 'the hook must refuse the same script file'


def test_r2_spawn_set_is_derived_from_the_shared_table(tmp_path_factory) -> None:
    """Neither implementation carries a second literal shell list."""
    table_shells = set(_SHELLS)
    assert set(_HOOK._r2_shell_spawns()) == table_shells | {'source'}, (
        'the hook R2 spawn set must be the table shells plus the `source` builtin'
    )

    # `source` is not a program in the table (it is a shell builtin), so it is the
    # ONE literal the spawn set adds; both harnesses must still refuse it.
    source_command = 'source ./env.sh'
    harness = build_harness(tmp_path_factory.mktemp('guard-source-builtin'))
    blocked, message = harness.blocks(shell_event(source_command, agent=SUB_AGENT_AGENT))
    assert blocked, 'guard.js must refuse the `source` builtin as an R2 spawn'
    assert 'R2' in message, f'the refusal must be rule R2; message={message!r}'
    assert _hook_refused(source_command), 'the hook must refuse the `source` builtin as an R2 spawn'

    # Every table shell is an R2 SPAWN on both harnesses, proven by a command that
    # names NO interpreter — so the refusal cannot come from R5.
    benign = [f"{shell} -c 'printf ok'" for shell in sorted(table_shells)]
    outcomes = harness.run([shell_event(row, agent=SUB_AGENT_AGENT) for row in benign])
    for row, outcome in zip(benign, outcomes, strict=True):
        assert outcome.blocked, f'guard.js admitted the shell spawn {row!r}'
        assert 'R2' in outcome.message, f'{row!r} must be refused as R2; message={outcome.message!r}'
        payload = {'agent_type': SUB_AGENT_AGENT, 'tool_name': 'Bash', 'tool_input': {'command': row}}
        assert _HOOK.evaluate(payload) == _HOOK._R2_REASON, f'the hook must refuse {row!r} as R2'

    # The directory-option mapping is data too: neither implementation hard-codes
    # `env`/`sudo` directory letters.
    assert wrapper_table()['wrappers']['env'].get('dir_options'), 'env must declare its directory options in the table'
    assert wrapper_table()['wrappers']['sudo'].get('dir_options'), (
        'sudo must declare its directory options in the table'
    )
    guard_source = guard_plugin_path().read_text(encoding='utf-8')
    hook_source = (
        REPO_ROOT / 'marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_pretooluse_hook.py'
    ).read_text(encoding='utf-8')
    assert 'dir_options' in guard_source, 'guard.js must read the directory-option data'
    assert 'dir_options' in hook_source, 'the hook must read the directory-option data'
    assert 'WRAPPER_TABLE.shells' in guard_source, 'guard.js must derive its shell spawn set from the shared table'
    parsed = guard_source.split('const MUTATION_FILE_OPS = new Set([', 1)[1].split('])', 1)[0]
    for shell in table_shells:
        assert f'"{shell}"' not in parsed, f'guard.js MUTATION_FILE_OPS still carries a literal shell {shell!r}'

    assert '_R2_SHELL_SPAWNS = (' not in hook_source, 'the hook still carries a literal shell-spawn tuple'
    assert "get('shells')" in hook_source, 'the hook must derive its shell spawn set from the shared table'


def test_a_nested_interpreter_behind_the_executor_is_still_refused(tmp_path_factory) -> None:
    """An admitted executor segment must not bless a LATER nested interpreter.

    ``script -c "python3 .plan/execute-script.py …; sh -c 'python3 -c x'"`` names
    the executor first and hides the real call inside a token of the second
    segment. The floor must recurse into a token, not stop at the admitted first
    segment — otherwise the admission becomes a bypass.
    """
    rows = [
        'script -c "python3 .plan/execute-script.py a:b:c verb; sh -c \'python3 -c x\'"',
        'env -S "python3 .plan/execute-script.py a:b:c verb; sh -c \'python3 -c x\'"',
        'watch "python3 .plan/execute-script.py a:b:c verb; sh -c \'python3 -c x\'"',
    ]
    harness = build_harness(tmp_path_factory.mktemp('guard-nested-splice'))
    outcomes = harness.run([shell_event(row, agent=SUB_AGENT_AGENT) for row in rows])
    for row, outcome in zip(rows, outcomes, strict=True):
        assert outcome.blocked, f'guard.js admitted {row!r}'
        assert 'R5' in outcome.message, f'the refusal for {row!r} must be R5; message={outcome.message!r}'
        assert _hook_refused(row), f'the hook admitted {row!r}'


def test_a_clustered_wrapper_directory_option_defeats_the_permit(tmp_path_factory) -> None:
    """``env -iC/tmp/x`` and ``sudo -D/tmp/x`` are directory changes too.

    The attached/clustered spellings are valid getopt forms of the same option;
    a rule that only recognises the detached spelling leaves the same vacuity one
    spelling over.
    """
    rows = [
        'env -iC/tmp/x -S "python3 .plan/execute-script.py a:b:c verb"',
        'sudo -D/tmp/x env -S "python3 .plan/execute-script.py a:b:c verb"',
        'env -C/tmp/x -S "python3 .plan/execute-script.py a:b:c verb"',
        'sudo -D /tmp/x env -S "python3 .plan/execute-script.py a:b:c verb"',
        'env --chdir=/tmp/x -S "python3 .plan/execute-script.py a:b:c verb"',
        'sudo --chdir=/tmp/x env -S "python3 .plan/execute-script.py a:b:c verb"',
        'sudo --chdir /tmp/x env -S "python3 .plan/execute-script.py a:b:c verb"',
        'sudo --directory=/tmp/x env -S "python3 .plan/execute-script.py a:b:c verb"',
    ]
    harness = build_harness(tmp_path_factory.mktemp('guard-clustered-dir'))
    outcomes = harness.run([shell_event(row, agent=SUB_AGENT_AGENT) for row in rows])
    for row, outcome in zip(rows, outcomes, strict=True):
        assert outcome.blocked, f'guard.js admitted {row!r}'
        assert 'R5' in outcome.message, f'the refusal for {row!r} must be R5; message={outcome.message!r}'
        assert _hook_refused(row), f'the hook admitted {row!r}'

    # Matched control: a flag-only cluster with no directory change keeps the
    # permit, so the rule is not simply refusing every clustered option.
    control = 'env -i -S "python3 .plan/execute-script.py a:b:c verb"'
    admitted, control_message = harness.blocks(shell_event(control, agent=SUB_AGENT_AGENT))
    assert not admitted, f'a cluster with no directory option must keep the permit; message={control_message!r}'
