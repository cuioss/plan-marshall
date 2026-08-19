#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the unified ``manage-change-ledger`` CLI — the first-class
``worktree-sha`` + ``append`` + ``query`` API over the one append-only
change-ledger.
"""


from __future__ import annotations

from pathlib import Path

import pytest
from _manage_change_ledger_fixtures import _SCRIPT, _init_repo, _read_ledger, _run


@pytest.fixture
def env(tmp_path: Path):
    """A real git repo + isolated ledger root.

    Returns a small namespace carrying the repo cwd, the ``PLAN_BASE_DIR``
    override, and the resolved ledger path so tests can assert on-disk state.
    """
    repo = tmp_path / 'repo'
    repo.mkdir()
    _init_repo(repo)

    base = tmp_path / 'base'
    base.mkdir()
    overrides = {'PLAN_BASE_DIR': str(base)}
    ledger_path = base / 'work' / 'change-ledger.jsonl'

    class Env:
        def __init__(self) -> None:
            self.repo = repo
            self.base = base
            self.overrides = overrides
            self.ledger_path = ledger_path

        def run(self, *args: str):
            return _run(self, *args)

    return Env()


@pytest.mark.parametrize(
    'kind,extra',
    [
        ('build', ('--notation', 'plan-marshall:build-pyproject:pyproject_build',
                   '--exit-code', '0', '--status', 'success')),
        ('job', ('--job-id', 'J-2',)),
    ],
)
def test_append_with_a_real_plan_id_stores_it_verbatim(env, kind, extra) -> None:
    """The fallback never overwrites a supplied plan id — the carve-out is narrow."""
    result = env.run('append', '--kind', kind, *extra, '--plan-id', 'my-plan')

    assert result.success, result.stderr
    entry = _read_ledger(env.ledger_path)[0]
    assert entry['plan_id'] == 'my-plan'


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


@pytest.mark.parametrize('build_status', ['success', 'error', 'timeout', 'killed'])
def test_append_build_stores_each_status_vocabulary_value(env, build_status: str) -> None:
    # every vocabulary value round-trips verbatim onto the stored entry.
    result = env.run(
        'append',
        '--kind',
        'build',
        '--notation',
        'plan-marshall:build-pyproject:pyproject_build',
        '--exit-code',
        '0',
        '--status',
        build_status,
    )

    assert result.success, result.stderr
    entry = _read_ledger(env.ledger_path)[0]
    assert entry['status'] == build_status


def test_append_build_requires_notation(env) -> None:
    # --notation is mandatory for kind=build.
    result = env.run(
        'append', '--kind', 'build', '--exit-code', '0', '--status', 'success'
    )

    # error TOON, no ledger line written.
    data = result.toon()
    assert data['status'] == 'error'
    assert not env.ledger_path.exists()


def test_append_build_requires_exit_code(env) -> None:
    # --exit-code is mandatory for kind=build.
    result = env.run(
        'append', '--kind', 'build', '--notation', 'plan-marshall:x:y',
        '--status', 'success',
    )

    data = result.toon()
    assert data['status'] == 'error'
    assert not env.ledger_path.exists()


def test_append_build_requires_status(env) -> None:
    # --status is mandatory for kind=build (the truthful outcome of record).
    result = env.run(
        'append', '--kind', 'build', '--notation', 'plan-marshall:x:y',
        '--exit-code', '0',
    )

    data = result.toon()
    assert data['status'] == 'error'
    assert not env.ledger_path.exists()


def test_append_build_rejects_unknown_status(env) -> None:
    # --status is choices-validated at the argparse boundary.
    result = env.run(
        'append', '--kind', 'build', '--notation', 'plan-marshall:x:y',
        '--exit-code', '0', '--status', 'flaky',
    )

    assert not result.success
    assert not env.ledger_path.exists()


# ---------------------------------------------------------------------------
# append --kind change
# ---------------------------------------------------------------------------


def test_append_change_stores_paths_verbatim(env) -> None:
    result = env.run(
        'append',
        '--kind',
        'change',
        '--deliverable-id',
        '2',
        '--commit-sha',
        'abc123',
        '--changed-paths',
        'src/a.py,src/b.py,test/c.py',
    )

    # success TOON.
    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    assert data['kind'] == 'change'

    # change fields stored verbatim.
    entry = _read_ledger(env.ledger_path)[0]
    assert entry['kind'] == 'change'
    assert entry['deliverable_id'] == '2'
    assert entry['commit_sha'] == 'abc123'
    assert entry['changed_paths'] == ['src/a.py', 'src/b.py', 'test/c.py']
    assert entry['worktree_sha']
    assert entry['timestamp_iso']


def test_append_change_accepts_task_id_alias(env) -> None:
    # --task-id is the accepted alternative to --deliverable-id.
    result = env.run(
        'append',
        '--kind',
        'change',
        '--task-id',
        'TASK-7',
        '--commit-sha',
        'def456',
    )

    # the alias populates deliverable_id; empty --changed-paths → [].
    assert result.success, result.stderr
    entry = _read_ledger(env.ledger_path)[0]
    assert entry['deliverable_id'] == 'TASK-7'
    assert entry['changed_paths'] == []


def test_append_change_requires_commit_sha(env) -> None:
    # --commit-sha is mandatory for kind=change.
    result = env.run('append', '--kind', 'change', '--deliverable-id', '2')

    data = result.toon()
    assert data['status'] == 'error'
    assert not env.ledger_path.exists()


def test_append_change_requires_deliverable_or_task(env) -> None:
    # one of --deliverable-id / --task-id is required.
    result = env.run('append', '--kind', 'change', '--commit-sha', 'abc123')

    data = result.toon()
    assert data['status'] == 'error'
    assert not env.ledger_path.exists()


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
