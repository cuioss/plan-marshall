#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""CLI cluster of manage-ci-artifacts tests.

Behaviour scope: the ``cmd_*`` CLI surface — ``cmd_persist`` with a
populated / empty / absent ``--jobs-file``, ``cmd_read --latest``
dispatch, unloadable-jobs-file handling, empty run_id handling, the
cmd-level operation-failure-exits-zero regression gate, and the
script-source canonical-path guard.

Moved byte-for-byte from ``test_manage_ci_artifacts.py`` — no
behavioural edit, no class split.
"""

from __future__ import annotations

import argparse
import json

from conftest import get_scripts_dir, load_script_module

_SCRIPTS_DIR = get_scripts_dir('plan-marshall', 'manage-ci-artifacts')


def _load_module(name: str, filename: str):
    return load_script_module('plan-marshall', 'manage-ci-artifacts', filename, name)


_mod = _load_module('manage_ci_artifacts', 'manage-ci-artifacts.py')
persist = _mod.persist
read_manifest = _mod.read_manifest
read_latest_manifest = _mod.read_latest_manifest
list_runs = _mod.list_runs
cmd_persist = _mod.cmd_persist
cmd_read = _mod.cmd_read
_run_dir = _mod._run_dir
_manifest_path = _mod._manifest_path
_safe_job_filename = _mod._safe_job_filename
parse_toon = _mod.parse_toon
serialize_toon = _mod.serialize_toon


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_fetcher(provider: str, run_id: str, job: dict) -> str:
    return f'STUB-LOG provider={provider} run_id={run_id} name={job.get("name", "")}\n'


def _job(name: str, conclusion: str = 'success') -> dict:
    return {
        'name': name,
        'conclusion': conclusion,
        'workflow_name': 'ci',
        'job_name': name,
        'started_at': '2026-05-19T00:00:00Z',
        'completed_at': '2026-05-19T00:01:00Z',
        'run_url': 'https://example/runs/x',
    }


# ---------------------------------------------------------------------------
# cmd_persist with a populated --jobs-file. The CLI surface
# accepts a JSON file path so the green-CI path can persist per-job
# evidence. The manifest MUST carry one jobs[] row per input job, each with
# a non-empty log_path, and the manifest+return MUST be labelled
# jobs_source: enumerated.
# ---------------------------------------------------------------------------


def _persist_args(**overrides) -> argparse.Namespace:
    """Build an argparse.Namespace matching the ``persist`` subparser."""
    base = {
        'plan_id': 'ci-artifacts-cmd-jobs',
        'run_id': '777',
        'head_sha': 'deadbeef',
        'pr_number': 55,
        'provider': 'github',
        'jobs_file': None,
        'wait_outcome': 'completed',
        'final_status': 'success',
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def test_cmd_persist_with_populated_jobs_file_writes_job_rows(tmp_path, capsys, plan_context):
    """cmd_persist handed a non-empty --jobs-file MUST write one jobs[]
    manifest row per input job, each with a non-empty log_path, and label
    the manifest jobs_source: enumerated.
    """
    plan_id = 'ci-artifacts-cmd-jobs-populated'
    jobs = [_job('build', 'success'), _job('lint', 'success')]
    jobs_file = tmp_path / 'jobs.json'
    jobs_file.write_text(json.dumps(jobs), encoding='utf-8')

    exit_code = cmd_persist(
        _persist_args(
            plan_id=plan_id,
            run_id='777',
            jobs_file=str(jobs_file),
        )
    )
    assert exit_code == 0
    # The captured TOON output carries jobs_source + job_count.
    out = capsys.readouterr().out
    assert 'jobs_source: enumerated' in out
    assert 'job_count: 2' in out

    # The persisted manifest enumerates both jobs with log paths.
    result = read_manifest(plan_id=plan_id, run_id='777')
    assert result['status'] == 'success'
    manifest = result['manifest']
    assert manifest['jobs_source'] == 'enumerated'
    manifest_jobs = manifest['jobs']
    assert len(manifest_jobs) == 2
    assert {j['name'] for j in manifest_jobs} == {'build', 'lint'}
    for row in manifest_jobs:
        assert row['log_path'], (
            f'job row {row["name"]!r} has an empty log_path — the green-CI persist path must record per-job evidence'
        )


def test_cmd_persist_with_empty_jobs_file_labels_zero_jobs_manifest(tmp_path, capsys, plan_context):
    """An empty --jobs-file MUST produce a clearly-labelled zero-jobs
    manifest (jobs_source: empty) rather than silently looking like a
    run where no CI executed.
    """
    plan_id = 'ci-artifacts-cmd-jobs-empty'
    jobs_file = tmp_path / 'jobs-empty.json'
    jobs_file.write_text('[]', encoding='utf-8')

    exit_code = cmd_persist(
        _persist_args(
            plan_id=plan_id,
            run_id='778',
            jobs_file=str(jobs_file),
        )
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'jobs_source: empty' in out
    assert 'job_count: 0' in out

    result = read_manifest(plan_id=plan_id, run_id='778')
    assert result['status'] == 'success'
    assert result['manifest']['jobs_source'] == 'empty'
    assert (result['manifest'].get('jobs') or []) == []


def test_cmd_persist_without_jobs_file_labels_empty_source(capsys, plan_context):
    """A missing --jobs-file (None) is treated the same as an empty file —
    the manifest is labelled jobs_source: empty.
    """
    plan_id = 'ci-artifacts-cmd-jobs-missing'
    exit_code = cmd_persist(
        _persist_args(
            plan_id=plan_id,
            run_id='779',
            jobs_file=None,
        )
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'jobs_source: empty' in out

    result = read_manifest(plan_id=plan_id, run_id='779')
    assert result['status'] == 'success'
    assert result['manifest']['jobs_source'] == 'empty'


def test_cmd_read_latest_dispatches_to_latest_accessor(capsys, plan_context):
    """The ``read --latest`` CLI surface MUST route through
    read_latest_manifest. We assert via the captured TOON output rather
    than monkeypatching so the test pins the full CLI plumbing.
    """
    plan_id = 'ci-artifacts-cmd-latest'
    persist(
        plan_id=plan_id,
        run_id='888',
        head_sha='c0ffee',
        pr_number=1,
        provider='github',
        jobs=[_job('build')],
        log_fetcher=_stub_fetcher,
    )

    args = argparse.Namespace(
        plan_id=plan_id,
        run_id=None,
        latest=True,
    )
    exit_code = cmd_read(args)
    assert exit_code == 0
    out = capsys.readouterr().out
    # The latest manifest's run_id appears in the TOON output.
    assert "'888'" in out or '"888"' in out or 'run_id: 888' in out


def test_cmd_read_latest_error_envelope_when_no_runs(capsys, plan_context):
    """When no runs are persisted, ``read --latest`` MUST emit the
    structured error envelope and exit 0.

    Operation failure (no persisted runs) is NOT a script crash — the
    script ran successfully, only the operation failed. Per the output
    contract (pm-plugin-development:plugin-script-architecture →
    output-contract.md), cmd_read exits 0 and carries the verdict in the
    TOON ``status: error`` / ``no_persisted_runs`` payload on stdout.
    Callers branch on ``status``, never on the process exit code. Exit 1
    is reserved for genuine script crashes; exit 2 for argparse.
    """
    plan_id = 'ci-artifacts-cmd-latest-empty'
    args = argparse.Namespace(
        plan_id=plan_id,
        run_id=None,
        latest=True,
    )
    exit_code = cmd_read(args)
    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'status: error' in out
    assert 'no_persisted_runs' in out


# ---------------------------------------------------------------------------
# Regression: every cmd-level operation failure exits 0 with status: error
#
# Operation failures (manifest not found, no persisted runs, empty run_id,
# unloadable --jobs-file) are NOT script crashes — the script ran
# successfully, only the operation failed. Per the output contract
# (pm-plugin-development:plugin-script-architecture → output-contract.md),
# these exit 0 and carry the verdict in the TOON ``status: error`` payload on
# stdout. Callers branch on ``status``, never on the process exit code. A
# future regression of any cmd handler back to a non-zero exit on operation
# failure fails this gate.
# ---------------------------------------------------------------------------


def test_cmd_read_missing_run_exits_zero_with_toon_error(capsys, plan_context):
    """cmd_read for a missing run_id exits 0 with a TOON status:error payload."""
    plan_id = 'ci-artifacts-cmd-read-missing'
    args = argparse.Namespace(plan_id=plan_id, run_id='no-such-run', latest=False)
    exit_code = cmd_read(args)
    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'status: error' in out


def test_cmd_persist_empty_run_id_exits_zero_with_toon_error(capsys, plan_context):
    """cmd_persist with an empty run_id exits 0 with a TOON status:error payload.

    persist() rejects the empty run_id with a status:error dict; cmd_persist
    must emit that TOON and exit 0 (operation failure, not a script crash).
    """
    plan_id = 'ci-artifacts-cmd-persist-empty-run-id'
    exit_code = cmd_persist(_persist_args(plan_id=plan_id, run_id=''))
    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'status: error' in out
    assert 'run_id' in out


def test_cmd_persist_unloadable_jobs_file_exits_zero_with_toon_error(tmp_path, capsys, plan_context):
    """cmd_persist handed an unparseable --jobs-file exits 0 with status:error.

    Malformed JSON in the jobs file is an operation failure, not a script
    crash — the handler reports it via the TOON ``status: error`` payload and
    exits 0. Callers branch on ``status``, never on the exit code.
    """
    plan_id = 'ci-artifacts-cmd-persist-bad-jobs-file'
    bad_jobs = tmp_path / 'bad-jobs.json'
    bad_jobs.write_text('{not valid json', encoding='utf-8')

    exit_code = cmd_persist(_persist_args(plan_id=plan_id, run_id='780', jobs_file=str(bad_jobs)))
    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'status: error' in out
    assert 'jobs-file' in out


def test_script_source_uses_canonical_local_plans_path():
    """The script source references .plan/local/plans, not the legacy form.

    Regression guard for the path-consolidation sweep: ``_run_dir``'s docstring
    must spell the artifact location as ``.plan/local/plans/`` — the legacy
    bare ``.plan/plans/`` form is incorrect since runtime state moved under
    ``.plan/local``.
    """
    import re

    source = (_SCRIPTS_DIR / 'manage-ci-artifacts.py').read_text(encoding='utf-8')
    assert '.plan/local/plans/' in source
    legacy = re.findall(r'(?<!local/)\.plan/plans/', source)
    assert legacy == [], f'Legacy .plan/plans/ strings remain: {legacy}'
