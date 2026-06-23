#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the unified ``manage-change-ledger`` CLI — the first-class
``worktree-sha`` + ``append`` + ``query`` API over the one append-only
change-ledger.

The script is the executor-callable surface; tests drive it through its real
entry point with :func:`conftest.run_script` so the argparse wiring, the TOON
output contract, and the deterministic ``_ledger_core`` read/write/construct
path are all exercised end-to-end. Every invocation runs inside a REAL
``git init`` repo staged under a unique ``tmp_path`` (so the shared
``compute_worktree_sha`` helper resolves a HEAD) and routes the ledger file under
an isolated ``PLAN_BASE_DIR`` (so ``get_tracked_config_dir`` resolves the
fixture, never the real ``.plan/`` tree).

Coverage:

* ``append --kind build`` — stamps ``kind``/``worktree_sha``/``timestamp_iso``
  plus the build fields and appends one JSONL line;
* ``append --kind change`` — stamps the change fields, storing
  ``commit_sha``/``changed_paths`` verbatim;
* ``query`` — round-trips both entries; ``--kind`` filters; an empty ledger
  yields ``count: 0``;
* worktree_sha currency — the stored hash matches the ``worktree-sha`` verb's
  output for the same tree; a pre-computed ``--worktree-sha`` is honoured;
* TOON output shape — ``status``/``kind``/``worktree_sha``/``ledger_path`` keys
  on append, ``status``/``count``/``ledger_path`` on query;
* error paths — missing ``--notation``/``--exit-code`` (build), missing
  ``--commit-sha`` / deliverable id (change), and ``worktree-sha`` in a
  non-git directory (``head_unresolvable``).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from conftest import get_script_path

_SCRIPT = get_script_path('plan-marshall', 'manage-change-ledger', 'manage-change-ledger.py')


def _git(repo: Path, *args: str) -> None:
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)


def _init_repo(repo: Path) -> None:
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    _git(repo, 'config', 'user.email', 't@t.test')
    _git(repo, 'config', 'user.name', 'Test')
    (repo / 'tracked.txt').write_text('original\n')
    _git(repo, 'add', '.')
    _git(repo, 'commit', '-q', '-m', 'init')


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


def _run(env, *args: str):
    """Invoke the ledger CLI in the repo cwd with the isolated PLAN_BASE_DIR."""
    from conftest import run_script

    return run_script(
        _SCRIPT,
        *args,
        cwd=str(env.repo),
        env_overrides=env.overrides,
    )


def _read_ledger(ledger_path: Path) -> list[dict]:
    """Parse the on-disk JSONL ledger into a list of dicts."""
    return [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# append --kind build
# ---------------------------------------------------------------------------


def test_append_build_writes_one_entry(env) -> None:
    result = env.run(
        'append',
        '--kind',
        'build',
        '--notation',
        'plan-marshall:build-pyproject:pyproject_build',
        '--exit-code',
        '0',
        '--plan-id',
        'my-plan',
        '--args',
        'module-tests plan-marshall',
        '--log-file',
        '/tmp/build.log',
    )

    # success TOON shape.
    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    assert data['kind'] == 'build'
    assert data['worktree_sha']
    assert data['ledger_path']

    # exactly one JSONL line with the build fields.
    entries = _read_ledger(env.ledger_path)
    assert len(entries) == 1
    entry = entries[0]
    assert entry['kind'] == 'build'
    assert entry['notation'] == 'plan-marshall:build-pyproject:pyproject_build'
    assert entry['plan_id'] == 'my-plan'
    assert entry['exit_code'] == 0
    assert entry['log_file'] == '/tmp/build.log'
    assert entry['worktree_sha'] == data['worktree_sha']
    assert entry['timestamp_iso']
    # A build is not a commit — no commit_sha / changed_paths keys.
    assert 'commit_sha' not in entry
    assert 'changed_paths' not in entry


def test_append_build_records_nonzero_exit(env) -> None:
    # a failed build is still recorded (the gate filters on it).
    result = env.run(
        'append',
        '--kind',
        'build',
        '--notation',
        'plan-marshall:build-pyproject:pyproject_build',
        '--exit-code',
        '1',
    )

    assert result.success, result.stderr
    entry = _read_ledger(env.ledger_path)[0]
    assert entry['exit_code'] == 1
    # plan_id is nullable — omitted here, stored as null.
    assert entry['plan_id'] is None


def test_append_build_requires_notation(env) -> None:
    # --notation is mandatory for kind=build.
    result = env.run('append', '--kind', 'build', '--exit-code', '0')

    # error TOON, no ledger line written.
    data = result.toon()
    assert data['status'] == 'error'
    assert not env.ledger_path.exists()


def test_append_build_requires_exit_code(env) -> None:
    # --exit-code is mandatory for kind=build.
    result = env.run(
        'append', '--kind', 'build', '--notation', 'plan-marshall:x:y'
    )

    data = result.toon()
    assert data['status'] == 'error'
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
        'append', '--kind', 'build', '--notation', 'n', '--exit-code', '0'
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
    env.run('append', '--kind', 'build', '--notation', 'n1', '--exit-code', '0')
    env.run('append', '--kind', 'build', '--notation', 'n2', '--exit-code', '1')
    env.run(
        'append', '--kind', 'change', '--deliverable-id', '1', '--commit-sha', 's'
    )

    # filter to builds only.
    result = env.run('query', '--kind', 'build')

    data = result.toon()
    assert data['count'] == 2


def test_query_exit_code_filter(env) -> None:
    # a passing and a failing build.
    env.run('append', '--kind', 'build', '--notation', 'n1', '--exit-code', '0')
    env.run('append', '--kind', 'build', '--notation', 'n2', '--exit-code', '1')

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
        'append', '--kind', 'build', '--notation', 'n', '--exit-code', '0'
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
        '--worktree-sha',
        'precomputed-sha-value',
    )

    # the stored hash is the supplied one (no recomputation).
    assert result.toon()['worktree_sha'] == 'precomputed-sha-value'
    assert _read_ledger(env.ledger_path)[0]['worktree_sha'] == 'precomputed-sha-value'


def test_worktree_sha_non_git_directory_errors(tmp_path: Path) -> None:
    # run the verb in a plain non-git directory with an isolated base.
    from conftest import run_script

    plain = tmp_path / 'plain'
    plain.mkdir()
    base = tmp_path / 'base'
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
