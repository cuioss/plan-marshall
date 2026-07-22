#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for logging module."""

import os
import tempfile
import time
from datetime import date
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
# Import the module under test (PYTHONPATH set by conftest)
import plan_logging as module
import pytest

#: Fixed date the global-log filename seam is pinned to. The production code
#: builds ``work-{date.today()}.log`` and the assertions used to recompute
#: ``date.today()`` independently, so a run crossing midnight compared two
#: different days and failed. Freezing the seam removes the rollover race.
_FROZEN_DATE = date(2026, 1, 15)


class _FrozenDate:
    """Stand-in for ``datetime.date`` whose ``today()`` is pinned."""

    @staticmethod
    def today():
        return _FROZEN_DATE


@pytest.fixture
def frozen_log_date(monkeypatch):
    """Pin the global-log filename date seam in the module under test."""
    monkeypatch.setattr(module, 'date', _FrozenDate)
    return _FROZEN_DATE


# =============================================================================
# TESTS: format_timestamp
# =============================================================================


def test_format_timestamp_iso8601():
    """Timestamp is ISO 8601 format with Z suffix."""
    ts = module.format_timestamp()
    assert ts.endswith('Z'), f'Expected Z suffix, got {ts}'
    assert 'T' in ts, f'Expected T separator, got {ts}'
    assert len(ts) == 20, f'Expected 20 chars, got {len(ts)}: {ts}'


# =============================================================================
# TESTS: format_log_entry
# =============================================================================


def test_format_log_entry_basic():
    """Log entry has correct structure with hash."""
    entry = module.format_log_entry('INFO', 'test message')
    assert '[INFO]' in entry, 'Missing level'
    assert 'test message' in entry, 'Missing message'
    assert entry.endswith('\n'), 'Should end with newline'
    # Hash should be present (6 hex chars in brackets)
    import re

    hash_match = re.search(r'\[[a-f0-9]{6}\]', entry)
    assert hash_match, f'Missing hash in entry: {entry}'


def test_format_log_entry_with_fields():
    """Log entry includes additional fields."""
    entry = module.format_log_entry('ERROR', 'failed', exit_code=1, args='--plan-id test')
    assert '  exit_code: 1' in entry, 'Missing exit_code field'
    assert '  args: --plan-id test' in entry, 'Missing args field'


def test_format_log_entry_message_cannot_forge_a_second_header():
    """A \\n/\\r-bearing message cannot inject an extra parsed log entry (CWE-117)."""
    forged_header = '[2026-01-15T12:00:00Z] [ERROR] [abcdef] forged entry'
    entry = module.format_log_entry('INFO', f'benign\n{forged_header}\r\nmore')

    # Exactly one header line survives: the one this call legitimately produced.
    assert len(module.HEADER_PATTERN.findall(entry)) == 1, (
        f'control characters in the message forged an extra entry: {entry!r}'
    )
    assert '\n' not in entry[:-1], f'message newlines must be stripped: {entry!r}'
    assert '\r' not in entry, f'message carriage returns must be stripped: {entry!r}'


def test_format_log_entry_field_value_cannot_forge_a_second_header():
    """A \\n-bearing field value cannot inject an extra parsed log entry (CWE-117)."""
    forged_header = '[2026-01-15T12:00:00Z] [ERROR] [abcdef] forged entry'
    entry = module.format_log_entry('INFO', 'benign', detail=f'value\n{forged_header}')

    assert len(module.HEADER_PATTERN.findall(entry)) == 1, (
        f'control characters in a field value forged an extra entry: {entry!r}'
    )
    # The field survives as exactly one indented line, with the injection inlined.
    assert len(module.FIELD_PATTERN.findall(entry)) == 1, (
        f'field value newlines forged an extra field line: {entry!r}'
    )


def test_format_log_entry_skips_empty_fields():
    """Log entry skips None/empty fields."""
    entry = module.format_log_entry('INFO', 'message', phase='init', detail=None, empty='')
    assert '  phase: init' in entry, 'Missing phase field'
    assert 'detail' not in entry, 'Should skip None field'
    assert 'empty' not in entry, 'Should skip empty field'


# =============================================================================
# TESTS: compute_entry_hash
# =============================================================================


def test_compute_entry_hash_deterministic():
    """Same message always produces same hash."""
    message = 'test message content'
    hash1 = module.compute_entry_hash(message)
    hash2 = module.compute_entry_hash(message)
    assert hash1 == hash2, f'Hash not deterministic: {hash1} != {hash2}'


def test_compute_entry_hash_length():
    """Hash is exactly 6 hex characters."""
    message = 'any message'
    hash_id = module.compute_entry_hash(message)
    assert len(hash_id) == 6, f'Expected 6 chars, got {len(hash_id)}'
    assert all(c in '0123456789abcdef' for c in hash_id), f'Not hex: {hash_id}'


def test_compute_entry_hash_different_messages():
    """Different messages produce different hashes."""
    hash1 = module.compute_entry_hash('message one')
    hash2 = module.compute_entry_hash('message two')
    assert hash1 != hash2, 'Different messages should have different hashes'


def test_format_log_entry_hash_deterministic():
    """Same message in format_log_entry produces same hash."""
    import re

    message = 'consistent test message'
    entry1 = module.format_log_entry('INFO', message)
    entry2 = module.format_log_entry('INFO', message)

    # Extract hashes
    hash_pattern = re.compile(r'\[([a-f0-9]{6})\]')
    match1 = hash_pattern.search(entry1)
    match2 = hash_pattern.search(entry2)

    assert match1 and match2, 'Hash not found in entries'
    assert match1.group(1) == match2.group(1), 'Hashes should match for same message'


# =============================================================================
# TESTS: get_log_path
# =============================================================================


def _init_plan_dir(plan_base: Path, plan_id: str) -> Path:
    """Create an INITIALIZED plan dir (carries the status.json sentinel)."""
    plan_dir = plan_base / 'plans' / plan_id
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')
    return plan_dir


def test_get_log_path_plan_scoped_script():
    """Script log path for an initialized plan (status.json present)."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = _init_plan_dir(plan_base, 'my-plan')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            path = module.get_log_path('my-plan', 'script')
            assert path == plan_dir / 'logs' / 'script-execution.log'
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_get_log_path_plan_scoped_work():
    """Work log path for an initialized plan (status.json present)."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = _init_plan_dir(plan_base, 'my-plan')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            path = module.get_log_path('my-plan', 'work')
            assert path == plan_dir / 'logs' / 'work.log'
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_get_log_path_plan_scoped_decision():
    """Decision log path for an initialized plan (status.json present)."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = _init_plan_dir(plan_base, 'my-plan')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            path = module.get_log_path('my-plan', 'decision')
            assert path == plan_dir / 'logs' / 'decision.log'
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_get_log_path_global_fallback(frozen_log_date):
    """Script log falls back to global when no plan."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            path = module.get_log_path(None, 'script')
            assert path.parent == plan_base / 'logs'
            assert path.name.startswith('script-execution-')
            assert str(frozen_log_date) in path.name
        finally:
            del os.environ['PLAN_BASE_DIR']


# =============================================================================
# TESTS: get_log_path status.json sentinel (orphan-slot hardening)
# =============================================================================


def test_get_log_path_orphan_dir_without_sentinel_falls_back_to_global():
    """A plan dir that exists but lacks status.json resolves to the global log.

    Regression guard for the orphan-slot fix: a status.json-less plan dir (the
    orphan shape — only logs/ or work/ materialized while the authoritative dir
    is worktree-resident) MUST NOT be treated as plan-scoped. get_log_path falls
    through to the date-suffixed global fallback instead of extending the orphan.
    """
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        orphan_dir = plan_base / 'plans' / 'orphan-plan'
        orphan_dir.mkdir(parents=True)  # exists, but NO status.json sentinel

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            for log_type, prefix in (
                ('script', 'script-execution-'),
                ('work', 'work-'),
                ('decision', 'decision-'),
            ):
                path = module.get_log_path('orphan-plan', log_type)
                assert path.parent == plan_base / 'logs', (
                    f'{log_type}: expected global fallback, got {path}'
                )
                assert path.name.startswith(prefix), f'{log_type}: unexpected name {path.name}'
                # The orphan dir must NOT acquire a plan-scoped logs/ subdirectory.
                assert not (orphan_dir / 'logs').exists(), (
                    f'{log_type}: orphan plan-scoped logs/ should not be resolved'
                )
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_get_log_path_sentinel_present_resolves_plan_scoped():
    """A plan dir carrying status.json resolves plan-scoped for every log type."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = _init_plan_dir(plan_base, 'init-plan')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            assert module.get_log_path('init-plan', 'script') == plan_dir / 'logs' / 'script-execution.log'
            assert module.get_log_path('init-plan', 'work') == plan_dir / 'logs' / 'work.log'
            assert module.get_log_path('init-plan', 'decision') == plan_dir / 'logs' / 'decision.log'
        finally:
            del os.environ['PLAN_BASE_DIR']


# =============================================================================
# TESTS: extract_plan_id
# =============================================================================


def test_extract_plan_id_with_space_separator():
    """Extract plan-id with --plan-id value format."""
    args = ['add', '--plan-id', 'my-plan', '--file', 'test.md']
    result = module.extract_plan_id(args)
    assert result == 'my-plan', f"Expected 'my-plan', got {result}"


def test_extract_plan_id_with_equals_separator():
    """Extract plan-id with --plan-id=value format."""
    args = ['add', '--plan-id=my-plan', '--file', 'test.md']
    result = module.extract_plan_id(args)
    assert result == 'my-plan', f"Expected 'my-plan', got {result}"


def test_extract_plan_id_missing():
    """Return None when --plan-id is not present."""
    args = ['add', '--file', 'test.md']
    result = module.extract_plan_id(args)
    assert result is None, f'Expected None, got {result}'


# =============================================================================
# TESTS: log_script_execution
# =============================================================================


def test_log_script_execution_success():
    """Success entry is written to log file."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = _init_plan_dir(plan_base, 'test-plan')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            module.log_script_execution(
                notation='test:skill:script',
                subcommand='add',
                args=['--plan-id', 'test-plan'],
                exit_code=0,
                duration=0.15,
            )

            log_file = plan_dir / 'logs' / 'script-execution.log'
            assert log_file.exists(), 'Log file not created'

            content = log_file.read_text()
            assert '[INFO]' in content
            assert 'test:skill:script add' in content
            assert '0.15s' in content
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_log_script_execution_error_with_details():
    """Error entry includes exit_code, args, stderr."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = _init_plan_dir(plan_base, 'test-plan')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            module.log_script_execution(
                notation='test:skill:script',
                subcommand='add',
                args=['--plan-id', 'test-plan', '--file', 'missing.md'],
                exit_code=1,
                duration=0.23,
                stderr='FileNotFoundError: missing.md',
            )

            log_file = plan_dir / 'logs' / 'script-execution.log'
            content = log_file.read_text()
            assert '[ERROR]' in content
            assert 'exit_code: 1' in content
            assert 'args:' in content
            assert 'stderr:' in content
            assert 'FileNotFoundError' in content
        finally:
            del os.environ['PLAN_BASE_DIR']


# =============================================================================
# TESTS: log_script_execution producer-tier routing (--plan-id presence)
# =============================================================================
#
# Regression guard for the orchestrator-context build-call bug (deliverable 1):
# the pre-push-quality-gate build MUST forward --plan-id so its log line lands in
# the plan-scoped script-execution.log tier — the exact log that
# pre-commit-verify-freshness reads. The old --project-dir-only shape carried no
# --plan-id, so log_script_execution's extract_plan_id() returned None and the
# build line was misrouted to the global date-suffixed tier, false-negativing the
# plan-scoped freshness gate. These tests pin both halves: the FIXED shape routes
# plan-scoped, the legacy shape routes global.

_PYPROJECT_NOTATION = 'plan-marshall:build-pyproject:pyproject_build'


def test_log_script_execution_plan_id_routes_plan_scoped(frozen_log_date):
    """FIXED orchestrator-context build shape (--plan-id present) -> plan-scoped tier.

    Mirrors the post-fix call: pyproject_build run with the quality-gate command-args
    AND --plan-id. extract_plan_id resolves the plan, get_log_path hits the
    status.json sentinel branch, and the [INFO] build line lands in the plan-scoped
    logs/script-execution.log — ABSENT from the global day-log.
    """
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = _init_plan_dir(plan_base, 'fixed-plan')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            module.log_script_execution(
                notation=_PYPROJECT_NOTATION,
                subcommand='run',
                args=['run', '--command-args', 'quality-gate plan-marshall', '--plan-id', 'fixed-plan'],
                exit_code=0,
                duration=12.5,
            )

            plan_log = plan_dir / 'logs' / 'script-execution.log'
            assert plan_log.exists(), 'Build line should land in the plan-scoped script log'
            plan_content = plan_log.read_text(encoding='utf-8')
            assert '[INFO]' in plan_content
            assert f'{_PYPROJECT_NOTATION} run' in plan_content, (
                'Plan-scoped log must carry the pyproject_build run line'
            )

            global_log = plan_base / 'logs' / f'script-execution-{frozen_log_date}.log'
            if global_log.exists():
                assert _PYPROJECT_NOTATION not in global_log.read_text(encoding='utf-8'), (
                    'Build line must NOT leak into the global tier when --plan-id is present'
                )
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_log_script_execution_no_plan_id_routes_global(frozen_log_date):
    """Legacy --project-dir-only build shape (NO --plan-id) -> global tier (the bug).

    Companion proving the bug the fix closes: the same pyproject_build run call WITHOUT
    --plan-id (the old --project-dir-only shape) carries no plan id, so extract_plan_id
    returns None and the build line is misrouted to the global date-suffixed tier — the
    plan-scoped script log the freshness gate reads is left without the build line.
    """
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = _init_plan_dir(plan_base, 'legacy-plan')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            module.log_script_execution(
                notation=_PYPROJECT_NOTATION,
                subcommand='run',
                args=['run', '--command-args', 'quality-gate plan-marshall', '--project-dir', str(plan_base)],
                exit_code=0,
                duration=12.5,
            )

            global_log = plan_base / 'logs' / f'script-execution-{frozen_log_date}.log'
            assert global_log.exists(), 'No-plan-id build line should land in the global tier'
            assert f'{_PYPROJECT_NOTATION} run' in global_log.read_text(encoding='utf-8'), (
                'Global tier must carry the build line for the --project-dir/no---plan-id shape'
            )

            plan_log = plan_dir / 'logs' / 'script-execution.log'
            assert not plan_log.exists(), (
                'Plan-scoped freshness-gate log must be left WITHOUT the build line — this is the bug'
            )
        finally:
            del os.environ['PLAN_BASE_DIR']


# =============================================================================
# TESTS: cleanup_old_script_logs
# =============================================================================


def test_cleanup_deletes_old_logs():
    """Cleanup deletes logs older than max_age_days."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        log_dir = plan_base / 'logs'
        log_dir.mkdir()

        old_log = log_dir / 'script-execution-2020-01-01.log'
        old_log.write_text('old log')
        old_time = time.time() - (30 * 86400)
        os.utime(old_log, (old_time, old_time))

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            deleted = module.cleanup_old_script_logs(max_age_days=7)
            assert deleted == 1, f'Expected 1 deleted, got {deleted}'
            assert not old_log.exists(), 'Old log should be deleted'
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_cleanup_preserves_recent_logs(frozen_log_date):
    """Cleanup preserves logs newer than max_age_days."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        log_dir = plan_base / 'logs'
        log_dir.mkdir()

        recent_log = log_dir / f'script-execution-{frozen_log_date}.log'
        recent_log.write_text('recent log')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            deleted = module.cleanup_old_script_logs(max_age_days=7)
            assert deleted == 0, f'Expected 0 deleted, got {deleted}'
            assert recent_log.exists(), 'Recent log should be preserved'
        finally:
            del os.environ['PLAN_BASE_DIR']


# =============================================================================
# TESTS: log_work
# =============================================================================


def test_log_work_default_category():
    """Log work with default PROGRESS category."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = _init_plan_dir(plan_base, 'test-plan')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            result = module.log_work(
                plan_id='test-plan', category='PROGRESS', message='Starting init phase', phase='init'
            )

            assert result['status'] == 'success'
            assert result['category'] == 'PROGRESS'
            assert result['total_entries'] == 1

            log_file = plan_dir / 'logs' / 'work.log'
            content = log_file.read_text()
            assert '[INFO]' in content
            assert '[PROGRESS]' in content
            assert 'Starting init phase' in content
            assert 'phase: init' in content
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_log_work_all_categories():
    """Log work with each valid category."""
    # DECISION now goes to decision.log, not work.log
    categories = ['ARTIFACT', 'PROGRESS', 'ERROR', 'OUTCOME', 'FINDING']

    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = _init_plan_dir(plan_base, 'test-plan')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            for cat in categories:
                result = module.log_work(plan_id='test-plan', category=cat, message=f'Test {cat}', phase='init')
                assert result['status'] == 'success', f'Failed for {cat}'
                assert result['category'] == cat

            log_file = plan_dir / 'logs' / 'work.log'
            content = log_file.read_text()
            for cat in categories:
                assert f'[{cat}]' in content, f'Missing {cat}'
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_log_work_invalid_plan_id():
    """Log work fails for invalid plan_id."""
    result = module.log_work(plan_id='INVALID_ID', category='PROGRESS', message='Test', phase='init')
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_plan_id'


def test_log_work_invalid_category():
    """Log work fails for invalid category."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = plan_base / 'plans' / 'test-plan'
        plan_dir.mkdir(parents=True)

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            result = module.log_work(plan_id='test-plan', category='INVALID', message='Test', phase='init')
            assert result['status'] == 'error'
            assert result['error'] == 'invalid_category'
        finally:
            del os.environ['PLAN_BASE_DIR']


# =============================================================================
# TESTS: read_work_log
# =============================================================================


def test_read_work_log_all_entries():
    """Read all work log entries."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        _init_plan_dir(plan_base, 'test-plan')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            # Add some entries (DECISION is now separate log)
            module.log_work('test-plan', 'PROGRESS', 'Entry 1', 'init')
            module.log_work('test-plan', 'OUTCOME', 'Entry 2', 'refine')
            module.log_work('test-plan', 'ARTIFACT', 'Entry 3', 'execute')

            result = module.read_work_log('test-plan')
            assert result['status'] == 'success'
            assert result['total_entries'] == 3
            assert len(result['entries']) == 3
            # Each entry should have hash_id
            for entry in result['entries']:
                assert 'hash_id' in entry, f'Missing hash_id in entry: {entry}'
                assert len(entry['hash_id']) == 6, f'Invalid hash_id: {entry["hash_id"]}'
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_read_work_log_filtered_by_phase():
    """Read work log entries filtered by phase."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        _init_plan_dir(plan_base, 'test-plan')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            module.log_work('test-plan', 'PROGRESS', 'Init entry', 'init')
            module.log_work('test-plan', 'OUTCOME', 'Refine entry', 'refine')
            module.log_work('test-plan', 'PROGRESS', 'Another init', 'init')

            result = module.read_work_log('test-plan', phase='init')
            assert result['status'] == 'success'
            assert result['total_entries'] == 2
            for entry in result['entries']:
                assert entry['phase'] == 'init'
        finally:
            del os.environ['PLAN_BASE_DIR']


# =============================================================================
# TESTS: list_recent_work
# =============================================================================


def test_list_recent_work_with_limit():
    """List recent entries respects limit."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        _init_plan_dir(plan_base, 'test-plan')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            for i in range(5):
                module.log_work('test-plan', 'PROGRESS', f'Entry {i}', 'init')

            result = module.list_recent_work('test-plan', limit=3)
            assert result['status'] == 'success'
            assert result['total_entries'] == 5
            assert result['showing'] == 3
            assert len(result['entries']) == 3
            # Should be most recent
            assert 'Entry 4' in result['entries'][-1]['message']
        finally:
            del os.environ['PLAN_BASE_DIR']


# =============================================================================
# TESTS: orphan-slot logging fallback (writers honor the status.json sentinel)
# =============================================================================


def test_log_work_orphan_dir_writes_global_not_plan_scoped(frozen_log_date):
    """log_work against a status.json-less orphan dir writes to the global log.

    The orphan plan dir (logs/work materialized while the authoritative dir is
    worktree-resident, no status.json) MUST NOT acquire a plan-scoped logs/. The
    entry lands in the date-suffixed global work log instead.
    """
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        orphan_dir = plan_base / 'plans' / 'orphan-plan'
        orphan_dir.mkdir(parents=True)  # exists, no status.json sentinel

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            result = module.log_work('orphan-plan', 'PROGRESS', 'orphan entry', 'execute')
            assert result['status'] == 'success'

            global_work_log = plan_base / 'logs' / f'work-{frozen_log_date}.log'
            assert global_work_log.exists(), 'Entry should land in the global work log'
            assert 'orphan entry' in global_work_log.read_text(encoding='utf-8')

            assert not (orphan_dir / 'logs').exists(), 'No plan-scoped logs/ under the orphan dir'
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_log_decision_orphan_dir_writes_global_not_plan_scoped(frozen_log_date):
    """log_decision against a status.json-less orphan dir writes to the global log."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        orphan_dir = plan_base / 'plans' / 'orphan-plan'
        orphan_dir.mkdir(parents=True)  # exists, no status.json sentinel

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            result = module.log_decision('orphan-plan', 'orphan decision', 'execute')
            assert result['status'] == 'success'

            global_decision_log = plan_base / 'logs' / f'decision-{frozen_log_date}.log'
            assert global_decision_log.exists(), 'Entry should land in the global decision log'
            assert 'orphan decision' in global_decision_log.read_text(encoding='utf-8')

            assert not (orphan_dir / 'logs').exists(), 'No plan-scoped logs/ under the orphan dir'
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_log_entry_orphan_dir_writes_global_not_plan_scoped(frozen_log_date):
    """log_entry against a status.json-less orphan dir writes to the global log."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        orphan_dir = plan_base / 'plans' / 'orphan-plan'
        orphan_dir.mkdir(parents=True)  # exists, no status.json sentinel

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            module.log_entry('work', 'orphan-plan', 'INFO', 'orphan log_entry message')

            global_work_log = plan_base / 'logs' / f'work-{frozen_log_date}.log'
            assert global_work_log.exists(), 'Entry should land in the global work log'
            assert 'orphan log_entry message' in global_work_log.read_text(encoding='utf-8')

            assert not (orphan_dir / 'logs').exists(), 'No plan-scoped logs/ under the orphan dir'
        finally:
            del os.environ['PLAN_BASE_DIR']


def test_log_work_sentinel_present_writes_plan_scoped(frozen_log_date):
    """log_work against an initialized (status.json) plan dir writes plan-scoped."""
    with tempfile.TemporaryDirectory() as tmp:
        plan_base = Path(tmp)
        plan_dir = _init_plan_dir(plan_base, 'init-plan')

        os.environ['PLAN_BASE_DIR'] = str(plan_base)
        try:
            result = module.log_work('init-plan', 'PROGRESS', 'init entry', 'execute')
            assert result['status'] == 'success'

            plan_work_log = plan_dir / 'logs' / 'work.log'
            assert plan_work_log.exists(), 'Entry should land in the plan-scoped work log'
            assert 'init entry' in plan_work_log.read_text(encoding='utf-8')

            global_work_log = plan_base / 'logs' / f'work-{frozen_log_date}.log'
            assert not global_work_log.exists(), 'Initialized plan must not fall back to global'
        finally:
            del os.environ['PLAN_BASE_DIR']


# =============================================================================
# TESTS: canonical .plan/local/plans path strings (regression guard)
# =============================================================================


def test_module_source_uses_canonical_local_plans_path():
    """The module source references .plan/local/plans, not the legacy form.

    Regression guard for the path-consolidation sweep: the docstring header and
    the __main__ diagnostic prints must spell the plan-scoped log location as
    ``.plan/local/plans/{plan_id}/...`` — the legacy bare ``.plan/plans/`` form
    is incorrect since runtime state moved under ``.plan/local``.
    """
    source = Path(module.__file__).read_text(encoding='utf-8')
    assert '.plan/local/plans/{plan_id}/logs/' in source
    # No bare ``.plan/plans/`` occurrence (i.e. not preceded by ``local/``).
    import re

    legacy = re.findall(r'(?<!local/)\.plan/plans/', source)
    assert legacy == [], f'Legacy .plan/plans/ strings remain: {legacy}'
