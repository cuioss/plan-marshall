#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the unified ``manage-change-ledger`` CLI — the first-class
``worktree-sha`` + ``append`` + ``query`` API over the one append-only
change-ledger.
"""


from __future__ import annotations

from pathlib import Path

import pytest
from _manage_change_ledger_fixtures import _init_repo, _read_ledger, _run
from _resolve_project_dir_fixtures import NO_PLAN_SENTINEL


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
