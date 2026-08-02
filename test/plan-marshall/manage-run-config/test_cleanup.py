#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for cleanup subcommands in run_config.py (formerly standalone cleanup.py)."""

import json
import os
import re
import shutil
import time
from pathlib import Path

# Layout constants, imported from the side-effect-free modules that DECLARE
# them. Deliberately NOT from `_cmd_cleanup`: that module binds
# `PLAN_BASE_DIR = get_base_dir()` at import time, so importing it here (at
# collection time) would freeze the base directory before the autouse
# PLAN_BASE_DIR sandbox fixture redirects it.
from constants import CI_BODIES_DIRNAME, CLEANUP_TARGETS, DIR_PLANS, DIR_WORK
from marketplace_paths import NO_PLAN_SENTINEL

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import get_script_path, run_script

# Cleanup is now a subcommand of run_config.py (was standalone cleanup.py)
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-run-config', 'run_config.py')

# Default retention config for tests
DEFAULT_RETENTION = {
    'logs_days': 1,
    'archived_plans_days': 5,
    'no_plan_body_days': 7,
    'temp_on_maintenance': True,
}

# A marshal.json written BEFORE `no_plan_body_days` joined the retention
# defaults, and never re-synced with `manage-config sync-defaults`. Every real
# project's config predates some key, so the absent-key shape — not the fully
# populated one above — is what the retention reader must survive.
LEGACY_RETENTION_WITHOUT_NO_PLAN_BODY_DAYS = {
    'logs_days': 1,
    'archived_plans_days': 5,
    'temp_on_maintenance': True,
}


def clean_fixture_dirs(fixture_dir: Path):
    """Clean up directories that may leak between tests in shared fixture."""
    for subdir in ['temp', 'logs', 'archived-plans']:
        path = fixture_dir / subdir
        if path.exists():
            shutil.rmtree(path)
    # The sentinel body store lives under plans/NO_PLAN/, which the loop above
    # does not cover — its parent `plans/` holds real fixture plans and must
    # not be removed wholesale.
    sentinel = fixture_dir / 'plans' / 'NO_PLAN'
    if sentinel.exists():
        shutil.rmtree(sentinel)


def setup_marshal_json(fixture_dir: Path, retention: dict | None = None):
    """Create marshal.json with retention settings."""
    config = {'system': {'retention': retention or DEFAULT_RETENTION}}
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))


def test_clean_temp(plan_context):
    """Clean temp directory."""
    setup_marshal_json(plan_context.fixture_dir)

    temp_dir = plan_context.fixture_dir / 'temp'
    temp_dir.mkdir(parents=True, exist_ok=True)

    (temp_dir / 'file1.txt').write_text('content1')
    (temp_dir / 'file2.json').write_text('{"key": "value"}')
    subdir = temp_dir / 'subdir'
    subdir.mkdir(exist_ok=True)
    (subdir / 'nested.txt').write_text('nested content')

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'temp')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'status: success' in result.stdout
    assert 'temp_files: 3' in result.stdout

    remaining = list(temp_dir.iterdir())
    assert len(remaining) == 0, f'Files remain: {remaining}'


def test_clean_logs(plan_context):
    """Clean old log files."""
    setup_marshal_json(plan_context.fixture_dir)

    logs_dir = plan_context.fixture_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)

    old_log = logs_dir / 'old.log'
    old_log.write_text('old log content')
    old_time = time.time() - (2 * 86400)
    os.utime(old_log, (old_time, old_time))

    recent_log = logs_dir / 'recent.log'
    recent_log.write_text('recent log content')

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'logs')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'status: success' in result.stdout
    assert 'logs_deleted: 1' in result.stdout

    assert not old_log.exists(), 'Old log should be deleted'
    assert recent_log.exists(), 'Recent log should be kept'


def test_clean_archived_plans(plan_context, monkeypatch):
    """Clean old archived plans."""
    # Pin HOME and credentials dir for the subprocess so cleanup's
    # run-configuration side-effects cannot touch the real host paths.
    monkeypatch.setenv('HOME', str(plan_context.fixture_dir))
    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(plan_context.fixture_dir / 'creds'))
    setup_marshal_json(plan_context.fixture_dir)

    archived_dir = plan_context.fixture_dir / 'archived-plans'
    archived_dir.mkdir(parents=True, exist_ok=True)

    old_plan = archived_dir / 'old-plan'
    old_plan.mkdir()
    (old_plan / 'references.json').write_text('{"branch": "main"}')
    (old_plan / 'plan.md').write_text('plan')
    old_time = time.time() - (6 * 86400)
    os.utime(old_plan, (old_time, old_time))

    recent_plan = archived_dir / 'recent-plan'
    recent_plan.mkdir()
    (recent_plan / 'references.json').write_text('{"branch": "main"}')

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'archived-plans')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'status: success' in result.stdout
    assert 'archived_plans_deleted: 1' in result.stdout

    assert not old_plan.exists(), 'Old plan should be deleted'
    assert recent_plan.exists(), 'Recent plan should be kept'


def test_clean_all(plan_context):
    """Clean all directories."""
    setup_marshal_json(plan_context.fixture_dir)

    temp_dir = plan_context.fixture_dir / 'temp'
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / 'temp.txt').write_text('temp')

    logs_dir = plan_context.fixture_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    old_log = logs_dir / 'old.log'
    old_log.write_text('old')
    old_time = time.time() - (2 * 86400)
    os.utime(old_log, (old_time, old_time))

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'all')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'status: success' in result.stdout
    assert 'temp_files: 1' in result.stdout
    assert 'logs_deleted: 1' in result.stdout


def test_clean_dry_run(plan_context):
    """Dry run shows what would be deleted without deleting."""
    setup_marshal_json(plan_context.fixture_dir)

    temp_dir = plan_context.fixture_dir / 'temp'
    temp_dir.mkdir(parents=True, exist_ok=True)

    test_file = temp_dir / 'keep-me.txt'
    test_file.write_text('should not be deleted')

    result = run_script(SCRIPT_PATH, 'cleanup', '--dry-run', '--target', 'temp')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'status: dry_run' in result.stdout
    assert 'temp_files: 1' in result.stdout

    assert test_file.exists(), 'File should not be deleted in dry-run mode'


def test_status(plan_context):
    """Status command shows directory statistics."""
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)

    temp_dir = plan_context.fixture_dir / 'temp'
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / 'file1.txt').write_text('12345')

    logs_dir = plan_context.fixture_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / 'test.log').write_text('log')

    result = run_script(SCRIPT_PATH, 'cleanup-status')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'status: ok' in result.stdout
    assert 'temp_files: 1' in result.stdout
    assert 'logs_total: 1' in result.stdout


def test_clean_nonexistent(plan_context):
    """Clean on nonexistent directory succeeds with zero counts."""
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)

    # The fixture_dir exists but temp/logs/etc don't
    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'all')
    assert result.success, "Should succeed even if directories don't exist"
    assert 'status: success' in result.stdout
    assert 'temp_files: 0' in result.stdout


def test_missing_marshal_json(plan_context):
    """Script outputs TOON error and exits 0 when marshal.json is missing."""
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    if marshal_path.exists():
        marshal_path.unlink()

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'all')
    assert result.success, 'Should exit 0 with TOON error output'
    assert 'status: error' in result.stdout
    assert 'marshal.json not found' in result.stdout


def test_missing_retention_config(plan_context):
    """Script outputs TOON error and exits 0 when retention config is missing."""
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps({'other': 'config'}))

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'all')
    assert result.success, 'Should exit 0 with TOON error output'
    assert 'status: error' in result.stdout
    assert 'system.retention' in result.stdout.lower()


def test_missing_subcommand():
    """Missing required subcommand fails."""
    result = run_script(SCRIPT_PATH)
    assert not result.success, 'Should fail without subcommand'
    assert 'required' in result.stderr.lower() or 'error' in result.stderr.lower()


# =============================================================================
# no-plan-bodies target (NO_PLAN sentinel retention)
# =============================================================================

#: Derived from the SAME constants ``_cmd_cleanup.get_no_plan_bodies_dir``
#: joins, so a rename of any segment moves both sides together instead of
#: leaving this fixture helper pointing at a path production no longer uses.
SENTINEL_BODIES_SUBPATH = (DIR_PLANS, NO_PLAN_SENTINEL, DIR_WORK, CI_BODIES_DIRNAME)


def sentinel_bodies_dir(fixture_dir: Path) -> Path:
    """Path to the sentinel's prepared-body directory inside a fixture root."""
    return fixture_dir.joinpath(*SENTINEL_BODIES_SUBPATH)


def setup_sentinel(fixture_dir: Path) -> Path:
    """Materialize the sentinel plan dir + its status.json marker.

    Mirrors what ``file_ops._materialize_sentinel_plan`` writes, so the tests
    can assert the marker SURVIVES cleanup.
    """
    plan_dir = fixture_dir / 'plans' / 'NO_PLAN'
    plan_dir.mkdir(parents=True, exist_ok=True)
    status_path = plan_dir / 'status.json'
    status_path.write_text(json.dumps({'plan': {'metadata': {'sentinel': True}}}))
    sentinel_bodies_dir(fixture_dir).mkdir(parents=True, exist_ok=True)
    return plan_dir


def write_sentinel_body(fixture_dir: Path, name: str, age_days: float | None = None) -> Path:
    """Write a body file into the sentinel store, optionally back-dating it."""
    body = sentinel_bodies_dir(fixture_dir) / name
    body.write_text('## Summary\nbody content\n')
    if age_days is not None:
        stamp = time.time() - (age_days * 86400)
        os.utime(body, (stamp, stamp))
    return body


def test_clean_no_plan_bodies_removes_aged_keeps_fresh(plan_context):
    """Aged sentinel bodies are pruned; fresh ones and the marker survive."""
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)
    plan_dir = setup_sentinel(plan_context.fixture_dir)

    # Default no_plan_body_days is 7, so 10 days is aged and 1 day is fresh.
    aged = write_sentinel_body(plan_context.fixture_dir, 'pr-create-old.md', age_days=10)
    fresh = write_sentinel_body(plan_context.fixture_dir, 'pr-create-default.md', age_days=1)

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'no-plan-bodies')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'status: success' in result.stdout
    assert 'no_plan_bodies_deleted: 1' in result.stdout

    assert not aged.exists(), 'Aged sentinel body should be deleted'
    assert fresh.exists(), 'Fresh sentinel body should be kept'

    # The sentinel itself is shared, permanent state — never removed.
    assert plan_dir.exists(), 'Sentinel plan directory must survive cleanup'
    assert (plan_dir / 'status.json').exists(), 'Sentinel status.json must survive cleanup'
    assert sentinel_bodies_dir(plan_context.fixture_dir).exists(), 'work/ci-bodies must survive cleanup'


def test_clean_no_plan_bodies_dry_run_reports_without_deleting(plan_context):
    """--dry-run reports the aged count but removes nothing."""
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)
    setup_sentinel(plan_context.fixture_dir)

    aged = write_sentinel_body(plan_context.fixture_dir, 'pr-create-old.md', age_days=10)

    result = run_script(SCRIPT_PATH, 'cleanup', '--dry-run', '--target', 'no-plan-bodies')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'status: dry_run' in result.stdout
    assert 'no_plan_bodies_deleted: 1' in result.stdout

    assert aged.exists(), 'Dry run must not delete the aged sentinel body'


def test_clean_no_plan_bodies_absent_sentinel_is_clean_noop(plan_context):
    """A project that never prepared a plan-less body cleans to zero, not error."""
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)

    assert not sentinel_bodies_dir(plan_context.fixture_dir).exists()

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'no-plan-bodies')
    assert result.success, 'Absent sentinel must be a clean no-op'
    assert 'status: success' in result.stdout
    assert 'no_plan_bodies_deleted: 0' in result.stdout


def test_clean_no_plan_bodies_leaves_logs_and_archived_plans(plan_context, monkeypatch):
    """Target scoping: no-plan-bodies prunes bodies only."""
    monkeypatch.setenv('HOME', str(plan_context.fixture_dir))
    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(plan_context.fixture_dir / 'creds'))
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)
    setup_sentinel(plan_context.fixture_dir)

    aged_body = write_sentinel_body(plan_context.fixture_dir, 'pr-create-old.md', age_days=10)

    logs_dir = plan_context.fixture_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    old_log = logs_dir / 'old.log'
    old_log.write_text('old log content')
    old_time = time.time() - (2 * 86400)
    os.utime(old_log, (old_time, old_time))

    archived_dir = plan_context.fixture_dir / 'archived-plans'
    archived_dir.mkdir(parents=True, exist_ok=True)
    old_plan = archived_dir / 'old-plan'
    old_plan.mkdir()
    (old_plan / 'plan.md').write_text('plan')
    os.utime(old_plan, (time.time() - (6 * 86400),) * 2)

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'no-plan-bodies')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'no_plan_bodies_deleted: 1' in result.stdout
    assert 'logs_deleted: 0' in result.stdout
    assert 'archived_plans_deleted: 0' in result.stdout

    assert not aged_body.exists(), 'Aged sentinel body should be deleted'
    assert old_log.exists(), 'Aged log must be untouched by the no-plan-bodies target'
    assert old_plan.exists(), 'Aged archived plan must be untouched by the no-plan-bodies target'


def test_status_reports_no_plan_bodies(plan_context):
    """cleanup-status surfaces the sentinel-body counters and the knob."""
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)
    setup_sentinel(plan_context.fixture_dir)

    write_sentinel_body(plan_context.fixture_dir, 'pr-create-old.md', age_days=10)
    write_sentinel_body(plan_context.fixture_dir, 'pr-create-default.md', age_days=1)

    result = run_script(SCRIPT_PATH, 'cleanup-status')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'status: ok' in result.stdout
    assert 'retention_no_plan_body_days: 7' in result.stdout
    assert 'no_plan_bodies_total: 2' in result.stdout
    assert 'no_plan_bodies_old: 1' in result.stdout


def test_status_backfills_no_plan_body_days_when_config_predates_it(plan_context):
    """An un-synced marshal.json yields the default, not a KeyError traceback.

    ``cleanup-status`` indexes ``no_plan_body_days`` directly; a config written
    before that key existed would blow up with an unhandled KeyError instead of
    the structured TOON result the caller parses. Asserting the DEFAULT value
    (not merely a zero exit) is what proves the key was backfilled rather than
    the whole sentinel-body section silently skipped.
    """
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir, LEGACY_RETENTION_WITHOUT_NO_PLAN_BODY_DAYS)
    setup_sentinel(plan_context.fixture_dir)

    write_sentinel_body(plan_context.fixture_dir, 'pr-create-old.md', age_days=10)
    write_sentinel_body(plan_context.fixture_dir, 'pr-create-default.md', age_days=1)

    result = run_script(SCRIPT_PATH, 'cleanup-status')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'KeyError' not in result.stderr
    assert 'status: ok' in result.stdout
    assert 'retention_no_plan_body_days: 7' in result.stdout
    assert 'no_plan_bodies_old: 1' in result.stdout


def test_clean_backfills_no_plan_body_days_when_config_predates_it(plan_context):
    """The clean path honours the backfilled default and prunes accordingly."""
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir, LEGACY_RETENTION_WITHOUT_NO_PLAN_BODY_DAYS)
    setup_sentinel(plan_context.fixture_dir)

    aged = write_sentinel_body(plan_context.fixture_dir, 'pr-create-old.md', age_days=10)
    fresh = write_sentinel_body(plan_context.fixture_dir, 'pr-create-default.md', age_days=1)

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'no-plan-bodies')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'KeyError' not in result.stderr
    assert 'status: success' in result.stdout
    assert 'no_plan_bodies_deleted: 1' in result.stdout

    assert not aged.exists(), 'Aged sentinel body should be deleted under the backfilled default'
    assert fresh.exists(), 'Fresh sentinel body should be kept under the backfilled default'


def test_clean_all_includes_no_plan_bodies(plan_context):
    """--target all reaches the sentinel-body target too."""
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)
    setup_sentinel(plan_context.fixture_dir)

    aged = write_sentinel_body(plan_context.fixture_dir, 'pr-create-old.md', age_days=10)

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'all')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'no_plan_bodies_deleted: 1' in result.stdout
    assert not aged.exists(), 'Aged sentinel body should be deleted under --target all'


def test_sentinel_body_dir_matches_plan_resolver():
    """The cleanup target's path equals the one the body PRODUCER writes to.

    `_cmd_cleanup` derives the sentinel body directory from its own
    `PLAN_BASE_DIR` root rather than calling `get_plan_dir`, matching how its
    three sibling targets resolve. That local derivation is only safe while it
    stays byte-identical to the resolver the producer uses — otherwise cleanup
    would silently prune nothing.

    The right-hand side is the PRODUCER itself — the parent of a real
    `ci_base.get_body_path()` result — not a hand-reconstructed literal. A
    reconstructed expectation would keep passing through a production layout
    change in `get_body_path`, which is exactly the drift this test exists to
    catch. Both halves are resolved here in one process so a divergent sub-path
    fails loudly.
    """
    from _cmd_cleanup import get_no_plan_bodies_dir
    from ci_base import BODY_KIND_PR_CREATE, get_body_path

    producer_dir = get_body_path(NO_PLAN_SENTINEL, BODY_KIND_PR_CREATE).parent
    assert get_no_plan_bodies_dir() == producer_dir


# =============================================================================
# build-results target (per-plan build output, guarded by plan liveness)
# =============================================================================

#: A marshal.json whose retention block sets `archived_plans_days` to a value
#: FAR from the shipped default and carries no `build_results_days`. The gap is
#: what makes the backfill assertions falsifiable: a reader that fell back to
#: the shipped default instead of tracking the project's effective value would
#: report 5, not 30.
RETENTION_WITHOUT_BUILD_RESULTS_DAYS = {
    'logs_days': 1,
    'archived_plans_days': 30,
    'no_plan_body_days': 7,
    'temp_on_maintenance': True,
}

#: The same block with an EXPLICIT `build_results_days` that disagrees with
#: `archived_plans_days` in both directions of comparison, so a test can tell an
#: honoured explicit value apart from a backfilled one.
RETENTION_WITH_EXPLICIT_BUILD_RESULTS_DAYS = {
    'logs_days': 1,
    'archived_plans_days': 30,
    'no_plan_body_days': 7,
    'build_results_days': 2,
    'temp_on_maintenance': True,
}


def build_results_dir_for(plan_id: str) -> Path:
    """Resolve a plan's build-results tree through the PRODUCTION resolver.

    Deliberately not a hand-built ``{plan_dir}/build-results`` literal: the
    fixtures below are written exactly where ``file_ops.get_build_results_dir``
    — the single owner of the path, and the resolver every build wrapper writes
    through — says the output goes. A layout change in that resolver therefore
    moves the fixture and the cleanup target together, instead of leaving this
    suite green while cleanup silently prunes nothing.

    Imported inside the function for the same reason the module header gives for
    ``_cmd_cleanup``: resolution must happen after the ``PLAN_BASE_DIR`` sandbox
    fixture has redirected the base directory, never at collection time.
    """
    from file_ops import get_build_results_dir

    return get_build_results_dir(plan_id)


def setup_plan(fixture_dir: Path, plan_id: str, *, live: bool) -> Path:
    """Create a plan directory, with or without its liveness marker.

    ``live=True`` writes the ``status.json`` marker that makes the plan store
    treat the directory as a managed plan; ``live=False`` leaves the directory
    bare, which is the leftover shape ``manage-status list-orphans`` reports.
    """
    plan_dir = fixture_dir / DIR_PLANS / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    if live:
        (plan_dir / 'status.json').write_text(json.dumps({'plan': {'current_phase': '5-execute'}}))
    return plan_dir


def write_build_result(plan_id: str, name: str, age_days: float | None = None) -> Path:
    """Write a build-result log under a plan's tree, optionally back-dating it."""
    result_file = build_results_dir_for(plan_id) / 'plan-marshall' / name
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text('build log content\n')
    if age_days is not None:
        stamp = time.time() - (age_days * 86400)
        os.utime(result_file, (stamp, stamp))
    return result_file


def test_clean_build_results_never_deletes_a_live_plans_results(plan_context):
    """A LIVE plan's build results survive even when they are past the threshold.

    Age alone would condemn this file — it is 20 days old against a 5-day
    window. Only the liveness guard keeps it, so a guard that stopped firing
    fails here rather than passing on a technicality.
    """
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)
    setup_plan(plan_context.fixture_dir, 'live-plan', live=True)

    aged = write_build_result('live-plan', 'python-old.log', age_days=20)

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'build-results')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'status: success' in result.stdout
    assert 'build_results_deleted: 0' in result.stdout

    assert aged.exists(), "A live plan's build results must never be deleted"


def test_status_never_counts_a_live_plans_results_as_reclaimable(plan_context):
    """`cleanup-status` excludes a live plan from the population, not just from `old`.

    The guard has to hold on the REPORTING surface too: a status run that
    counted these bytes would advertise a running plan's build output as
    reclaimable, which is the same promise broken one step earlier.
    """
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)
    setup_plan(plan_context.fixture_dir, 'live-plan', live=True)

    write_build_result('live-plan', 'python-old.log', age_days=20)
    write_build_result('live-plan', 'python-fresh.log', age_days=1)

    result = run_script(SCRIPT_PATH, 'cleanup-status')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'status: ok' in result.stdout
    assert 'build_results_total: 0' in result.stdout
    assert 'build_results_old: 0' in result.stdout
    assert 'build_results_old_bytes: 0' in result.stdout


def test_clean_build_results_ages_out_a_non_live_plan(plan_context):
    """A plan directory with no liveness marker is subject to the age threshold."""
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)
    setup_plan(plan_context.fixture_dir, 'leftover-plan', live=False)

    aged = write_build_result('leftover-plan', 'python-old.log', age_days=20)
    fresh = write_build_result('leftover-plan', 'python-fresh.log', age_days=1)

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'build-results')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'build_results_deleted: 1' in result.stdout

    assert not aged.exists(), "A non-live plan's aged build result should be deleted"
    assert fresh.exists(), 'A result inside the retention window should be kept'


def test_clean_build_results_ages_out_the_sentinel(plan_context):
    """The never-archived `NO_PLAN` sentinel is aged by the same threshold.

    The sentinel carries a `status.json` marker of its own, so the liveness
    predicate alone would protect it forever — and nothing else ever ages it,
    since it is never archived. The explicit carve-out is what gives its build
    results a lifecycle at all; the marker itself must still survive.
    """
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)
    sentinel_dir = setup_sentinel(plan_context.fixture_dir)

    aged = write_build_result(NO_PLAN_SENTINEL, 'python-old.log', age_days=20)
    fresh = write_build_result(NO_PLAN_SENTINEL, 'python-fresh.log', age_days=1)

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'build-results')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'build_results_deleted: 1' in result.stdout

    assert not aged.exists(), "The sentinel's aged build result should be deleted"
    assert fresh.exists(), "The sentinel's fresh build result should be kept"
    assert (sentinel_dir / 'status.json').exists(), 'Sentinel marker must survive cleanup'


def test_clean_build_results_dry_run_reports_without_deleting(plan_context):
    """--dry-run reports the aged count but removes nothing."""
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)
    setup_plan(plan_context.fixture_dir, 'leftover-plan', live=False)

    aged = write_build_result('leftover-plan', 'python-old.log', age_days=20)

    result = run_script(SCRIPT_PATH, 'cleanup', '--dry-run', '--target', 'build-results')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'status: dry_run' in result.stdout
    assert 'build_results_deleted: 1' in result.stdout

    assert aged.exists(), 'Dry run must not delete the aged build result'


def test_clean_build_results_absent_tree_is_clean_noop(plan_context):
    """A project where no build ever ran cleans to zero, not an error."""
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'build-results')
    assert result.success, 'An absent build-results tree must be a clean no-op'
    assert 'status: success' in result.stdout
    assert 'build_results_deleted: 0' in result.stdout


def test_clean_build_results_leaves_logs_and_archived_plans(plan_context, monkeypatch):
    """Target scoping: build-results prunes build output only."""
    monkeypatch.setenv('HOME', str(plan_context.fixture_dir))
    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(plan_context.fixture_dir / 'creds'))
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)
    setup_plan(plan_context.fixture_dir, 'leftover-plan', live=False)

    aged_result = write_build_result('leftover-plan', 'python-old.log', age_days=20)

    logs_dir = plan_context.fixture_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    old_log = logs_dir / 'old.log'
    old_log.write_text('old log content')
    os.utime(old_log, (time.time() - (2 * 86400),) * 2)

    archived_dir = plan_context.fixture_dir / 'archived-plans'
    archived_dir.mkdir(parents=True, exist_ok=True)
    old_plan = archived_dir / 'old-plan'
    old_plan.mkdir()
    (old_plan / 'plan.md').write_text('plan')
    os.utime(old_plan, (time.time() - (6 * 86400),) * 2)

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'build-results')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'build_results_deleted: 1' in result.stdout
    assert 'logs_deleted: 0' in result.stdout
    assert 'archived_plans_deleted: 0' in result.stdout

    assert not aged_result.exists(), 'Aged build result should be deleted'
    assert old_log.exists(), 'Aged log must be untouched by the build-results target'
    assert old_plan.exists(), 'Aged archived plan must be untouched by the build-results target'


def test_clean_all_includes_build_results(plan_context):
    """--target all reaches the build-results target too."""
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir)
    setup_plan(plan_context.fixture_dir, 'leftover-plan', live=False)

    aged = write_build_result('leftover-plan', 'python-old.log', age_days=20)

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'all')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'build_results_deleted: 1' in result.stdout
    assert not aged.exists(), 'Aged build result should be deleted under --target all'


def test_build_results_days_backfills_from_effective_archived_plans_days(plan_context):
    """An absent knob tracks the project's EFFECTIVE `archived_plans_days`.

    The fixture sets `archived_plans_days` to 30 — far from the shipped default
    of 5 — so reporting 5 here would prove the reader fell back to the shipped
    default instead of following the value the project actually configured.
    """
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir, RETENTION_WITHOUT_BUILD_RESULTS_DAYS)

    result = run_script(SCRIPT_PATH, 'cleanup-status')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'KeyError' not in result.stderr
    assert 'status: ok' in result.stdout
    assert 'retention_build_results_days: 30' in result.stdout


def test_clean_honours_the_backfilled_build_results_window(plan_context):
    """The clean path prunes against the backfilled window, not the shipped default.

    At 10 days old the result is past the shipped 5-day default but well inside
    the project's configured 30-day window, so a reader that ignored the
    backfill would delete it.
    """
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir, RETENTION_WITHOUT_BUILD_RESULTS_DAYS)
    setup_plan(plan_context.fixture_dir, 'leftover-plan', live=False)

    inside_window = write_build_result('leftover-plan', 'python-10d.log', age_days=10)
    past_window = write_build_result('leftover-plan', 'python-40d.log', age_days=40)

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'build-results')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'build_results_deleted: 1' in result.stdout

    assert inside_window.exists(), 'A result inside the backfilled 30-day window must be kept'
    assert not past_window.exists(), 'A result past the backfilled window should be deleted'


def test_explicit_build_results_days_wins_over_the_backfill(plan_context):
    """An explicitly configured knob overrides the `archived_plans_days` backfill.

    The 3-day-old result is inside `archived_plans_days` (30) but outside the
    explicit `build_results_days` (2), so it can only be deleted if the explicit
    value — not the backfill — governed the sweep.
    """
    clean_fixture_dirs(plan_context.fixture_dir)
    setup_marshal_json(plan_context.fixture_dir, RETENTION_WITH_EXPLICIT_BUILD_RESULTS_DAYS)
    setup_plan(plan_context.fixture_dir, 'leftover-plan', live=False)

    aged = write_build_result('leftover-plan', 'python-3d.log', age_days=3)

    result = run_script(SCRIPT_PATH, 'cleanup', '--target', 'build-results')
    assert result.success, f'Script failed: {result.stderr}'
    assert 'build_results_deleted: 1' in result.stdout

    assert not aged.exists(), 'The explicit build_results_days must govern the sweep'


def test_cli_target_choices_equal_the_declared_cleanup_targets():
    """The advertised `--target` set is exactly the closed `CLEANUP_TARGETS` tuple.

    Reads the RENDERED argparse help — the surface an operator actually sees —
    rather than the choices list object, so a future edit that re-hardcodes the
    enum (the shape `CLEANUP_TARGETS` replaced) fails here instead of quietly
    letting the CLI advertise a set the dispatcher does not handle.
    """
    result = run_script(SCRIPT_PATH, 'cleanup', '--help')
    assert result.success, f'Script failed: {result.stderr}'

    match = re.search(r'--target \{([^}]+)\}', result.stdout)
    assert match is not None, f'No --target choices in help output:\n{result.stdout}'

    # argparse may wrap a long choices list; normalise the wrap before splitting.
    advertised = tuple(part.strip() for part in match.group(1).replace('\n', '').split(','))
    assert advertised == CLEANUP_TARGETS
