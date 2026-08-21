#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: F811 — tests take the imported fixture as a parameter
"""Unit tests for the ``append`` verb of the unified ``manage-change-ledger`` CLI."""


from __future__ import annotations

import pytest
from _manage_change_ledger_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _init_repo,
    _read_ledger,
    _run,
    env,
)
from _resolve_project_dir_fixtures import NO_PLAN_SENTINEL

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
        '--status',
        'success',
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
    assert entry['status'] == 'success'
    assert entry['log_file'] == '/tmp/build.log'
    assert entry['worktree_sha'] == data['worktree_sha']
    assert entry['timestamp_iso']
    # A build is not a commit — no commit_sha / changed_paths keys.
    assert 'commit_sha' not in entry
    assert 'changed_paths' not in entry


def test_append_build_records_nonzero_exit(env) -> None:
    # a failed build is still recorded (exit_code is diagnostic detail).
    result = env.run(
        'append',
        '--kind',
        'build',
        '--notation',
        'plan-marshall:build-pyproject:pyproject_build',
        '--exit-code',
        '1',
        '--status',
        'error',
    )

    assert result.success, result.stderr
    entry = _read_ledger(env.ledger_path)[0]
    assert entry['exit_code'] == 1
    assert entry['status'] == 'error'
    # plan_id is NEVER null — an omitted flag resolves to the NO_PLAN sentinel.
    assert entry['plan_id'] == NO_PLAN_SENTINEL


# ---------------------------------------------------------------------------
# The three wrapper-reported build fields: command / duration_seconds / outcome
# ---------------------------------------------------------------------------

def test_append_verb_row_carries_the_three_fields_as_null(env) -> None:
    """The CLI second writer emits the KEYS, with null values.

    Asserted at the VERB, not only at the constructor: the CLI is a real
    production construction site, and a row that omitted the keys entirely
    would read as a different shape to every consumer than a row that carries
    them as null.
    """
    result = env.run(
        'append',
        '--kind',
        'build',
        '--notation',
        'plan-marshall:build-pyproject:pyproject_build',
        '--exit-code',
        '0',
        '--status',
        'success',
        '--args',
        'module-tests plan-marshall',
    )

    assert result.success, result.stderr
    entry = _read_ledger(env.ledger_path)[0]
    assert entry['command'] is None
    assert entry['duration_seconds'] is None
    assert entry['outcome'] is None
    assert entry['args'] == 'module-tests plan-marshall'


# ---------------------------------------------------------------------------
# The never-null plan_id contract, asserted at the CLI VERB
# ---------------------------------------------------------------------------
#
# This verb is the SECOND production construction site for build_record /
# job_record — the executor dispatch boundary is the first, and this one was
# absent from the original enumeration precisely because the coverage stopped at
# the constructor. Asserting through the verb (not the constructor) is what makes
# the "no build-class operation can emit plan_id: null" claim cover both sites.


@pytest.mark.parametrize(
    'kind,extra',
    [
        ('build', ('--notation', 'plan-marshall:build-pyproject:pyproject_build',
                   '--exit-code', '0', '--status', 'success')),
        ('job', ('--job-id', 'J-1', '--fingerprint', 'fp-1',
                 '--notation', 'plan-marshall:build-pyproject:pyproject_build')),
    ],
)
def test_append_without_plan_id_records_the_sentinel_never_null(env, kind, extra) -> None:
    """``append --kind {build,job}`` with NO ``--plan-id`` writes ``NO_PLAN``.

    Fail-first shape: before the resolution, ``run_append`` passed
    ``args.plan_id`` straight through and both rows landed as ``plan_id: null``.
    """
    result = env.run('append', '--kind', kind, *extra)

    assert result.success, result.stderr
    entry = _read_ledger(env.ledger_path)[0]
    assert entry['kind'] == kind
    assert entry['plan_id'] == NO_PLAN_SENTINEL, (
        f'append --kind {kind} without --plan-id stored {entry["plan_id"]!r}; '
        'the row must carry the NO_PLAN sentinel, never null.'
    )


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
