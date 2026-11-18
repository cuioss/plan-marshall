#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A daemon-routed job writes its log INSIDE the submitting project's tree.

The invariant these tests pin is a location, not a value: a build result's
``log_file`` names a path inside the tree the job was submitted for. It used to
name ``{daemon_dir}/job-logs/{job_id}.log``, outside that tree — so every consumer
that reads the named log was reading outside the project, and one confined to the
project had to break a rule on every routed build.

Four properties hold together:

* the result's ``log_file`` lies inside the submitting project's tree, the file
  exists, and it holds the job's own output;
* two jobs of ONE project do not overwrite each other's log;
* a log that cannot be written in the tree is a RECORDED logging failure, and it
  never falls back to the machine-global directory;
* the log's life follows the tree — removing the tree removes its logs, and the
  daemon's journal retention neither depends on nor deletes them.

The daemon is driven the way the rest of the suite drives it: a registered
project, a real submit through :meth:`Daemon.handle_request`, and the real
``asyncio`` child the supervisor spawns. The job log is therefore produced by
production code, not fabricated for the assertion.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import time
from pathlib import Path

# PLAIN import, deliberately: the build-server suites annotate against
# ``marshalld.Daemon``, which only a plain import gives mypy.
import marshalld
import pytest
from _build_server_protocol import STATUS_FAILURE, STATUS_SUCCESS, make_job_spec
from _build_server_registry import canonicalize_root, register_project
from _marshalld_journal import Journal
from _marshalld_scheduler import Scheduler

_NOTATION = 'plan-marshall:build-pyproject:pyproject_build'
_OTHER_NOTATION = 'plan-marshall:build-pyproject:pyproject_build_other'

#: The stub executor every job run in this module executes. It echoes its argv
#: tail, so the job log provably holds THIS job's output rather than an empty
#: file that merely exists at the right place.
_EXECUTOR_STUB = 'import sys\nprint("job-output " + " ".join(sys.argv[1:]))\n'

#: The in-tree directory the daemon is expected to write job logs into: the
#: project's own machine-local tier, mirroring the ``marshalld/job-logs`` naming
#: the machine-global directory used to carry.
_LOG_SUBDIR = Path('.plan') / 'local' / 'marshalld' / 'job-logs'


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Isolate the machine-global daemon home so no test touches the real one."""
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path / 'marshalld-home'))
    return tmp_path / 'marshalld-home'


def _register_project(root: Path, *notations: str, create: bool = True) -> str:
    """Enrol ``root``; when ``create`` is set, build the minimal executor tree too."""
    if create:
        (root / '.plan').mkdir(parents=True)
        (root / '.plan' / 'execute-script.py').write_text(_EXECUTOR_STUB)
    canonical = canonicalize_root(root)
    register_project(canonical, notation_allowlist=list(notations) or [_NOTATION])
    return canonical


def _spec(project: str, notation: str = _NOTATION, *, plan_id: str = 'p'):
    """Build a job spec whose command is the verified executor form."""
    return make_job_spec(
        command=['python3', str(Path(project) / '.plan' / 'execute-script.py'), notation, 'run'],
        exec_path=project,
        project_path=project,
        plan_id=plan_id,
    )


def _run_jobs(specs: list) -> list[dict]:
    """Submit ``specs`` to one in-process daemon and return their journal results."""
    results: list[dict] = []

    async def _drive() -> list[dict]:
        daemon = marshalld.Daemon(scheduler=Scheduler(max_slots=4), journal=Journal())
        job_ids = []
        for spec in specs:
            response = await daemon.handle_request({'op': 'submit', 'job': spec.to_dict()})
            assert response['status'] in ('queued', 'running'), response
            job_ids.append(response['job_id'])
        # Each finished job admits the next one for the same directory, so drain
        # the task set until it stops growing.
        for _ in range(10):
            daemon._admit_ready()
            if not daemon._tasks:
                break
            await asyncio.gather(*list(daemon._tasks.values()), return_exceptions=True)
        for job_id in job_ids:
            entry = daemon._journal.get(job_id)
            assert entry is not None, f'no journal entry for {job_id}'
            results.append(entry['result'] or {})
        return results

    return asyncio.run(_drive())


def _no_machine_global_job_logs(home: Path) -> None:
    """Assert the daemon wrote no job log in its machine-global state directory."""
    assert not (home / 'marshalld' / 'job-logs').exists(), (
        'a job log was written in the machine-global directory; the defect is back'
    )


# =============================================================================
# The log lives inside the submitting project's tree
# =============================================================================


def test_job_log_is_written_inside_the_submitting_project_tree(home, tmp_path):
    project = tmp_path / 'proj'
    canonical = _register_project(project)

    result = _run_jobs([_spec(canonical)])[0]

    assert result['status'] == STATUS_SUCCESS, result
    log_file = result['log_file']
    assert log_file, 'the result carries no log_file'
    log_path = Path(log_file)
    assert log_path.is_relative_to(project.resolve()), f'{log_path} is outside {project}'
    assert log_path.exists(), 'the reported log file does not exist'
    assert _NOTATION in log_path.read_text(encoding='utf-8'), 'the log does not hold the job output'
    assert log_path.parent == project.resolve() / _LOG_SUBDIR
    _no_machine_global_job_logs(home)


# =============================================================================
# Two jobs of one project never share a log file
# =============================================================================


def test_two_jobs_of_one_project_keep_separate_logs(home, tmp_path):
    project = tmp_path / 'proj'
    canonical = _register_project(project, _NOTATION, _OTHER_NOTATION)

    first, second = _run_jobs([_spec(canonical), _spec(canonical, _OTHER_NOTATION)])

    first_log = Path(first['log_file'])
    second_log = Path(second['log_file'])
    assert first_log != second_log, 'two jobs of one project wrote the same log file'
    assert first_log.is_relative_to(project.resolve())
    assert second_log.is_relative_to(project.resolve())
    assert first_log.exists() and second_log.exists()
    # Each log holds its OWN job's output — neither overwrote the other.
    assert _NOTATION in first_log.read_text(encoding='utf-8')
    assert _OTHER_NOTATION in second_log.read_text(encoding='utf-8')
    _no_machine_global_job_logs(home)


# =============================================================================
# An unwritable tree is a RECORDED failure, never a fall-back
# =============================================================================


@pytest.mark.skipif(os.name == 'nt', reason='POSIX directory permissions gate this case')
def test_unwritable_project_tree_records_a_logging_failure_without_fallback(home, tmp_path):
    project = tmp_path / 'proj'
    canonical = _register_project(project)
    # A read-only `.plan`: the daemon's own `.plan/local/marshalld/job-logs` cannot
    # be created, so the job's log has nowhere in the tree to go.
    plan_dir = project / '.plan'
    plan_dir.chmod(0o500)
    try:
        result = _run_jobs([_spec(canonical)])[0]
    finally:
        plan_dir.chmod(0o700)

    assert result['status'] == STATUS_FAILURE, result
    assert result.get('error') == 'log_file_failed', result
    assert result.get('reason'), 'the logging failure states no reason'
    _no_machine_global_job_logs(home)


def test_missing_project_tree_records_a_logging_failure_without_being_created(home, tmp_path):
    # The other unwritable-tree shape: the tree the job was submitted for is not
    # there at all. The daemon must report the logging failure, not fabricate a
    # project root by creating `.plan/local/...` inside it.
    project = tmp_path / 'proj'
    canonical = _register_project(project, create=False)

    result = _run_jobs([_spec(canonical)])[0]

    assert result['status'] == STATUS_FAILURE, result
    assert result.get('error') == 'log_file_failed', result
    assert not project.exists(), 'the daemon created a project tree that was not there'
    _no_machine_global_job_logs(home)


# =============================================================================
# The log's life follows the tree
# =============================================================================


def test_removing_the_tree_removes_its_logs(home, tmp_path):
    # A worktree is an ordinary directory as far as the log is concerned: once
    # `git worktree remove` deletes the tree, everything written inside it is
    # gone. A log written in the machine-global directory would survive.
    worktree = tmp_path / 'worktrees' / 'wt-1'
    canonical = _register_project(worktree)

    result = _run_jobs([_spec(canonical)])[0]

    log_path = Path(result['log_file'])
    assert log_path.is_relative_to(worktree.resolve())
    assert log_path.exists()

    shutil.rmtree(worktree)

    assert not log_path.exists(), 'the log outlived the tree it was written in'
    assert not worktree.exists()
    _no_machine_global_job_logs(home)


# =============================================================================
# Journal retention neither depends on nor deletes the log
# =============================================================================


def test_journal_gc_ignores_the_in_tree_log(home, tmp_path):
    project = tmp_path / 'proj'
    canonical = _register_project(project)

    async def _drive():
        daemon = marshalld.Daemon(scheduler=Scheduler(max_slots=2), journal=Journal())
        response = await daemon.handle_request({'op': 'submit', 'job': _spec(canonical).to_dict()})
        daemon._admit_ready()
        await asyncio.gather(*list(daemon._tasks.values()), return_exceptions=True)
        job_id = response['job_id']
        result = daemon._journal.get(job_id)['result']
        # Retention past every possible window: the journal entry goes, the log stays.
        removed = daemon._journal.gc(now=time.time() + 10**6)
        return job_id, result, removed

    job_id, result, removed = asyncio.run(_drive())

    assert job_id in removed
    log_path = Path(result['log_file'])
    assert log_path.is_relative_to(project.resolve())
    assert log_path.exists(), 'journal retention deleted the in-tree log'
    _no_machine_global_job_logs(home)
