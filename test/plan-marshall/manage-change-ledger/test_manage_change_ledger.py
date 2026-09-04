#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Unit tests for the unified ``manage-change-ledger`` CLI — the first-class
``worktree-sha`` + ``append`` + ``query`` API over the one append-only
change-ledger.
"""


from __future__ import annotations

from pathlib import Path

from _manage_change_ledger_fixtures import (
    _SCRIPT,
    _init_repo,
    _read_ledger,
    _run,
    env,
)

# ---------------------------------------------------------------------------
# The three wrapper-reported build fields: command / duration_seconds / outcome
# ---------------------------------------------------------------------------
#
# ``args`` and ``command`` are TWO LAYERS of one invocation and neither
# substitutes for the other: ``args`` is the executor argv the caller supplied,
# ``command`` is what the build wrapper resolved that argv into and actually
# ran. They are asserted TOGETHER on purpose — a record that collapsed the two
# into a single field would satisfy either assertion alone while making the
# other layer unrecoverable, so only the paired check can see the collapse.


def test_build_record_emits_command_duration_and_outcome_beside_args() -> None:
    """``build_record`` carries the wrapper's three facts WITHOUT losing ``args``."""
    import _ledger_core

    payload = {
        'status': 'success',
        'command': './pw verify plan-marshall',
        'duration_seconds': 12.5,
        'log_file': '/tmp/build.log',
    }

    record = _ledger_core.build_record(
        notation='plan-marshall:build-pyproject:pyproject_build',
        plan_id='my-plan',
        args='run --command-args "verify plan-marshall"',
        command='./pw verify plan-marshall',
        duration_seconds=12.5,
        outcome=payload,
        exit_code=0,
        status='success',
        worktree_sha='deadbeef',
        log_file='/tmp/build.log',
    )

    assert record['command'] == './pw verify plan-marshall'
    assert record['duration_seconds'] == 12.5
    assert record['outcome'] == payload
    # args is UNCHANGED: it still carries the EXECUTOR argv, not the resolved
    # command, so a reader can recover both layers from one row.
    assert record['args'] == 'run --command-args "verify plan-marshall"'
    assert record['args'] != record['command']


def test_build_record_defaults_the_three_wrapper_fields_to_none() -> None:
    """A payload-less writer still produces a COMPLETE row.

    A killed or crashed build has no parseable wrapper payload, and the CLI
    ``append`` verb (the second writer) has none by construction. Both must
    still land a row: the three fields are keyword-only with a ``None`` default
    rather than required, so no caller is forced to invent a value.
    """
    import _ledger_core

    record = _ledger_core.build_record(
        notation='plan-marshall:build-pyproject:pyproject_build',
        plan_id='my-plan',
        args='run --command-args "verify plan-marshall"',
        exit_code=-1,
        status='killed',
        worktree_sha='deadbeef',
        log_file=None,
    )

    assert record['command'] is None
    assert record['duration_seconds'] is None
    assert record['outcome'] is None
    assert record['args'] == 'run --command-args "verify plan-marshall"'


# ---------------------------------------------------------------------------
# The never-null plan_id contract, asserted at the CLI VERB
# ---------------------------------------------------------------------------

def test_ledger_core_constructors_declare_plan_id_as_required_str() -> None:
    """``build_record`` / ``job_record`` no longer accept ``str | None``.

    The clean break is asserted on the SIGNATURE rather than on behaviour: the
    ``| None`` union is removed outright (not deprecated), which is what makes a
    caller that still passes ``None`` a type error rather than a silently-null
    row. Behaviour-only assertions cannot see this, because Python would happily
    store the ``None`` either way.
    """
    import inspect

    import _ledger_core

    for constructor in (_ledger_core.build_record, _ledger_core.job_record):
        annotation = inspect.signature(constructor).parameters['plan_id'].annotation
        assert annotation == 'str', (
            f'{constructor.__name__} declares plan_id as {annotation!r}; the '
            'str | None union must be removed, not deprecated.'
        )


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------


def test_query_empty_ledger_returns_zero(env) -> None:
    # query against a ledger that was never written.
    result = env.run('query')

    # count 0, no entries.
    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    assert data['count'] == 0


def test_query_round_trips_both_kinds(env) -> None:
    # one build entry and one change entry.
    env.run(
        'append', '--kind', 'build', '--notation', 'n', '--exit-code', '0',
        '--status', 'success',
    )
    env.run(
        'append',
        '--kind',
        'change',
        '--deliverable-id',
        '1',
        '--commit-sha',
        'sha1',
    )

    result = env.run('query')

    # both entries are read back.
    assert result.success, result.stderr
    data = result.toon()
    assert data['count'] == 2


def test_query_kind_filter(env) -> None:
    # two builds, one change.
    env.run('append', '--kind', 'build', '--notation', 'n1', '--exit-code', '0',
            '--status', 'success')
    env.run('append', '--kind', 'build', '--notation', 'n2', '--exit-code', '1',
            '--status', 'error')
    env.run(
        'append', '--kind', 'change', '--deliverable-id', '1', '--commit-sha', 's'
    )

    # filter to builds only.
    result = env.run('query', '--kind', 'build')

    data = result.toon()
    assert data['count'] == 2


def test_query_exit_code_filter(env) -> None:
    # a passing and a failing build.
    env.run('append', '--kind', 'build', '--notation', 'n1', '--exit-code', '0',
            '--status', 'success')
    env.run('append', '--kind', 'build', '--notation', 'n2', '--exit-code', '1',
            '--status', 'error')

    # filter to the failing build.
    result = env.run('query', '--exit-code', '1')

    # only the exit_code=1 entry matches.
    data = result.toon()
    assert data['count'] == 1


# ---------------------------------------------------------------------------
# worktree-sha verb — the first-class freshness API
# ---------------------------------------------------------------------------


def test_worktree_sha_matches_appended_entry(env) -> None:
    # capture the current tree's hash via the dedicated verb.
    sha_result = env.run('worktree-sha')
    assert sha_result.success, sha_result.stderr
    sha_data = sha_result.toon()
    assert sha_data['status'] == 'success'
    expected = sha_data['worktree_sha']
    assert expected

    # append a build entry against the same (unchanged) tree.
    append_result = env.run(
        'append', '--kind', 'build', '--notation', 'n', '--exit-code', '0',
        '--status', 'success',
    )

    # writer and verb hash the same tree to the same value.
    assert append_result.toon()['worktree_sha'] == expected


def test_worktree_sha_honours_precomputed_value(env) -> None:
    # a caller that already holds the hash passes it verbatim.
    result = env.run(
        'append',
        '--kind',
        'build',
        '--notation',
        'n',
        '--exit-code',
        '0',
        '--status',
        'success',
        '--worktree-sha',
        'precomputed-sha-value',
    )

    # the stored hash is the supplied one (no recomputation).
    assert result.toon()['worktree_sha'] == 'precomputed-sha-value'
    assert _read_ledger(env.ledger_path)[0]['worktree_sha'] == 'precomputed-sha-value'


def test_worktree_sha_non_git_directory_errors(outside_repo_dir: Path) -> None:
    # run the verb in a plain non-git directory with an isolated base.
    # The cwd must be OUTSIDE the repo: pytest's tmp_path now roots under the
    # repo-local --basetemp, where the dir IS inside a git worktree and HEAD
    # would resolve instead of failing.
    from conftest import run_script

    plain = outside_repo_dir / 'plain'
    plain.mkdir()
    base = outside_repo_dir / 'base'
    base.mkdir()

    result = run_script(
        _SCRIPT,
        'worktree-sha',
        cwd=str(plain),
        env_overrides={'PLAN_BASE_DIR': str(base)},
    )

    # HEAD is unresolvable → structured error, code head_unresolvable.
    data = result.toon()
    assert data['status'] == 'error'
    assert data['error_code'] == 'head_unresolvable'
