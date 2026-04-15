#!/usr/bin/env python3
"""
Tests for ci_base.py shared utilities.

Tests functions:
- compute_elapsed: Elapsed time computation from ISO timestamps
- compute_total_elapsed: Total elapsed from earliest start
- truncate_log_content: Log truncation and escaping
- poll_until: Generic polling framework
"""

import argparse
import os
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta

import ci_base
import pytest
from ci_base import (
    BODY_KIND_ISSUE_CREATE,
    BODY_KIND_PR_CREATE,
    BODY_KIND_PR_EDIT,
    BODY_KIND_PR_REPLY,
    BODY_KIND_PR_THREAD_REPLY,
    CI_LOG_TRUNCATE_LINES,
    DEFAULT_CI_INTERVAL,
    DEFAULT_CI_TIMEOUT,
    add_head_arg,
    add_pr_create_args,
    build_parser,
    compute_elapsed,
    compute_total_elapsed,
    delete_consumed_body,
    get_body_path,
    get_default_cwd,
    poll_until,
    prepare_body,
    read_and_consume_body,
    run_cli,
    set_default_cwd,
    truncate_log_content,
)

# =============================================================================
# Shared constants tests
# =============================================================================


def test_default_constants():
    """Shared constants should have expected values."""
    assert DEFAULT_CI_TIMEOUT == 300
    assert DEFAULT_CI_INTERVAL == 30
    assert CI_LOG_TRUNCATE_LINES == 200


# =============================================================================
# compute_elapsed tests
# =============================================================================


def test_compute_elapsed_with_start_and_end():
    """Should compute seconds between start and end timestamps."""
    now = datetime.now(UTC)
    start = '2025-01-15T10:00:00+00:00'
    end = '2025-01-15T10:05:00+00:00'
    result = compute_elapsed(start, end, now)
    assert result == 300  # 5 minutes


def test_compute_elapsed_with_start_only():
    """Should compute seconds from start to now when no end."""
    now = datetime.now(UTC)
    start = (now - timedelta(seconds=60)).isoformat()
    result = compute_elapsed(start, None, now)
    assert 59 <= result <= 61  # approximately 60 seconds


def test_compute_elapsed_with_no_start():
    """Should return 0 when start is None."""
    now = datetime.now(UTC)
    result = compute_elapsed(None, None, now)
    assert result == 0


def test_compute_elapsed_with_invalid_timestamp():
    """Should return 0 on parse failure."""
    now = datetime.now(UTC)
    result = compute_elapsed('not-a-date', None, now)
    assert result == 0


# =============================================================================
# compute_total_elapsed tests
# =============================================================================


def test_compute_total_elapsed_picks_earliest():
    """Should compute elapsed from the earliest start time."""
    now = datetime.now(UTC)
    early = (now - timedelta(seconds=120)).isoformat()
    late = (now - timedelta(seconds=60)).isoformat()

    result = compute_total_elapsed([late, early, None], now)
    assert 119 <= result <= 121  # approximately 120 seconds from earliest


def test_compute_total_elapsed_all_none():
    """Should return 0 when all values are None."""
    now = datetime.now(UTC)
    result = compute_total_elapsed([None, None], now)
    assert result == 0


def test_compute_total_elapsed_empty_list():
    """Should return 0 for empty list."""
    now = datetime.now(UTC)
    result = compute_total_elapsed([], now)
    assert result == 0


# =============================================================================
# truncate_log_content tests
# =============================================================================


def test_truncate_log_content_short():
    """Short content should not be truncated."""
    content = 'line1\nline2\nline3'
    result, count = truncate_log_content(content)
    assert count == 3
    assert 'line1' in result


def test_truncate_log_content_long():
    """Content exceeding max_lines should be truncated."""
    lines = [f'line{i}' for i in range(500)]
    content = '\n'.join(lines)
    result, count = truncate_log_content(content)
    assert count == CI_LOG_TRUNCATE_LINES
    assert 'line0' in result
    assert 'line499' not in result


def test_truncate_log_content_custom_limit():
    """Should respect custom max_lines parameter."""
    lines = [f'line{i}' for i in range(100)]
    content = '\n'.join(lines)
    result, count = truncate_log_content(content, max_lines=10)
    assert count == 10


def test_truncate_log_content_escapes_newlines():
    """Output should have newlines escaped for TOON."""
    content = 'line1\nline2'
    result, _ = truncate_log_content(content)
    assert '\\n' in result


# =============================================================================
# poll_until tests
# =============================================================================


def test_poll_until_immediate_success():
    """Should return immediately when first check is complete."""
    call_count = 0

    def check_fn():
        nonlocal call_count
        call_count += 1
        return True, {'value': 'done'}

    def is_complete(data):
        return data.get('value') == 'done'

    result = poll_until(check_fn, is_complete, timeout=10, interval=1)
    assert not result['timed_out']
    assert result['polls'] == 1
    assert result['last_data']['value'] == 'done'
    assert call_count == 1


def test_poll_until_check_error():
    """Should propagate error from check_fn."""

    def check_fn():
        return False, {'error': 'Connection refused'}

    def is_complete(data):
        return False

    result = poll_until(check_fn, is_complete, timeout=10, interval=1)
    assert 'error' in result
    assert result['error'] == 'Connection refused'


def test_poll_until_timeout():
    """Should timeout when condition is never met."""

    def check_fn():
        return True, {'status': 'pending'}

    def is_complete(data):
        return False

    result = poll_until(check_fn, is_complete, timeout=1, interval=0.2)
    assert result['timed_out']
    assert result['polls'] >= 1
    assert result['last_data']['status'] == 'pending'


def test_poll_until_eventual_success():
    """Should succeed when condition is met after a few polls."""
    call_count = 0

    def check_fn():
        nonlocal call_count
        call_count += 1
        return True, {'ready': call_count >= 3}

    def is_complete(data):
        return data.get('ready')

    result = poll_until(check_fn, is_complete, timeout=10, interval=0.1)
    assert not result['timed_out']
    assert result['polls'] == 3
    assert result['last_data']['ready'] is True


# =============================================================================
# --head flag registration tests
# =============================================================================


def test_add_head_arg_registers_optional_flag():
    """add_head_arg should register --head as an optional argument on a subparser."""
    parser = argparse.ArgumentParser()
    add_head_arg(parser)

    # Optional — parses without --head
    args = parser.parse_args([])
    assert args.head is None

    # Accepts a branch name
    args = parser.parse_args(['--head', 'feature/x'])
    assert args.head == 'feature/x'


def test_pr_create_parser_accepts_head_flag():
    """add_pr_create_args should register --head on the pr create subparser."""
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add_pr_create_args(sub)

    args = parser.parse_args(
        ['create', '--title', 'T', '--plan-id', 'my-plan', '--head', 'feature/x']
    )
    assert args.head == 'feature/x'

    # Still optional — works without --head, but --plan-id is now required
    args = parser.parse_args(['create', '--title', 'T', '--plan-id', 'my-plan'])
    assert args.head is None
    assert args.plan_id == 'my-plan'


def test_pr_create_parser_rejects_body_and_body_file():
    """add_pr_create_args must NOT register the legacy body flags — they are deleted."""
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add_pr_create_args(sub)

    # Legacy body flags must raise SystemExit (unknown arg → argparse error)
    with pytest.raises(SystemExit):
        parser.parse_args(
            ['create', '--title', 'T', '--plan-id', 'p', '--body', 'X']
        )
    with pytest.raises(SystemExit):
        parser.parse_args(
            ['create', '--title', 'T', '--plan-id', 'p', '--body-file', '/tmp/x']
        )


def test_pr_create_parser_requires_plan_id():
    """add_pr_create_args must require --plan-id for body consumer args."""
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add_pr_create_args(sub)

    with pytest.raises(SystemExit):
        parser.parse_args(['create', '--title', 'T'])


def test_pr_create_parser_accepts_slot():
    """Optional --slot passes through to the namespace."""
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add_pr_create_args(sub)
    args = parser.parse_args(
        ['create', '--title', 'T', '--plan-id', 'p', '--slot', 'pr-body']
    )
    assert args.slot == 'pr-body'


def test_build_parser_pr_view_accepts_head_flag():
    """build_parser should register --head on pr view (was: no args)."""
    parser, _, _, _ = build_parser('test')
    args = parser.parse_args(['pr', 'view', '--head', 'feature/x'])
    assert args.head == 'feature/x'


def test_build_parser_pr_merge_pr_number_optional():
    """pr merge should accept --head as alternative to --pr-number (both optional)."""
    parser, _, _, _ = build_parser('test')
    # --head alone is allowed
    args = parser.parse_args(['pr', 'merge', '--head', 'feature/x'])
    assert args.head == 'feature/x'
    assert args.pr_number is None
    # --pr-number alone is allowed
    args = parser.parse_args(['pr', 'merge', '--pr-number', '42'])
    assert args.pr_number == 42
    assert args.head is None


def test_build_parser_pr_auto_merge_pr_number_optional():
    """pr auto-merge should accept --head as alternative to --pr-number."""
    parser, _, _, _ = build_parser('test')
    args = parser.parse_args(['pr', 'auto-merge', '--head', 'feature/x'])
    assert args.head == 'feature/x'
    assert args.pr_number is None


def test_build_parser_ci_status_pr_number_optional():
    """ci status should accept --head as alternative to --pr-number."""
    parser, _, _, _ = build_parser('test')
    args = parser.parse_args(['ci', 'status', '--head', 'feature/x'])
    assert args.head == 'feature/x'
    assert args.pr_number is None


# =============================================================================
# prepare-body subcommand registration (argparse wiring)
# =============================================================================


def test_build_parser_registers_pr_prepare_body():
    """`pr prepare-body` must be registered and require --plan-id."""
    parser, _, _, _ = build_parser('test')
    args = parser.parse_args(['pr', 'prepare-body', '--plan-id', 'my-plan'])
    assert args.command == 'pr'
    assert args.pr_command == 'prepare-body'
    assert args.plan_id == 'my-plan'
    assert args.prepare_for == 'create'  # default

    args = parser.parse_args(
        ['pr', 'prepare-body', '--plan-id', 'my-plan', '--for', 'edit', '--slot', 'update']
    )
    assert args.prepare_for == 'edit'
    assert args.slot == 'update'

    with pytest.raises(SystemExit):
        parser.parse_args(['pr', 'prepare-body'])  # missing --plan-id


def test_build_parser_registers_pr_prepare_comment():
    """`pr prepare-comment` must be registered with reply/thread-reply modes."""
    parser, _, _, _ = build_parser('test')
    args = parser.parse_args(['pr', 'prepare-comment', '--plan-id', 'my-plan'])
    assert args.pr_command == 'prepare-comment'
    assert args.prepare_for == 'reply'

    args = parser.parse_args(
        ['pr', 'prepare-comment', '--plan-id', 'my-plan', '--for', 'thread-reply']
    )
    assert args.prepare_for == 'thread-reply'


def test_build_parser_registers_issue_prepare_body():
    """`issue prepare-body` must be registered and require --plan-id."""
    parser, _, _, _ = build_parser('test')
    args = parser.parse_args(['issue', 'prepare-body', '--plan-id', 'my-plan'])
    assert args.command == 'issue'
    assert args.issue_command == 'prepare-body'
    assert args.plan_id == 'my-plan'


# =============================================================================
# Consumer subcommands reject removed legacy body flags
# =============================================================================


def test_pr_reply_rejects_body_flag():
    parser, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(
            ['pr', 'reply', '--pr-number', '1', '--plan-id', 'p', '--body', 'X']
        )


def test_pr_thread_reply_rejects_body_flag():
    parser, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                'pr',
                'thread-reply',
                '--pr-number',
                '1',
                '--thread-id',
                't',
                '--plan-id',
                'p',
                '--body',
                'X',
            ]
        )


def test_pr_edit_rejects_body_flag():
    parser, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(
            ['pr', 'edit', '--pr-number', '1', '--plan-id', 'p', '--body', 'X']
        )


def test_issue_create_rejects_body_flag():
    parser, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(
            ['issue', 'create', '--title', 'T', '--plan-id', 'p', '--body', 'X']
        )


def test_consumers_require_plan_id():
    parser, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['pr', 'reply', '--pr-number', '1'])
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'create', '--title', 'T'])


# =============================================================================
# Body store helpers
# =============================================================================


@pytest.fixture
def plan_base_env(tmp_path, monkeypatch):
    """Point PLAN_BASE_DIR at a temporary directory so get_plan_dir is sandboxed."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    return tmp_path


def test_get_body_path_rejects_unknown_kind(plan_base_env):
    with pytest.raises(ValueError):
        get_body_path('my-plan', 'unknown-kind')


def test_get_body_path_default_slot(plan_base_env):
    path = get_body_path('my-plan', BODY_KIND_PR_CREATE)
    assert path.name == 'pr-create-default.md'
    assert 'work/ci-bodies' in str(path)


def test_get_body_path_custom_slot(plan_base_env):
    path = get_body_path('my-plan', BODY_KIND_PR_CREATE, slot='alt')
    assert path.name == 'pr-create-alt.md'


def test_get_body_path_rejects_invalid_slot(plan_base_env):
    with pytest.raises(ValueError):
        get_body_path('my-plan', BODY_KIND_PR_CREATE, slot='Has Spaces!')


def test_prepare_body_creates_parent_directory(plan_base_env):
    result = prepare_body('my-plan', BODY_KIND_PR_CREATE)
    assert result['status'] == 'success'
    assert result['kind'] == BODY_KIND_PR_CREATE
    assert result['slot'] == 'default'
    assert result['exists'] is False
    # Parent directory was created so the caller can write immediately
    from pathlib import Path as _P
    assert _P(result['path']).parent.exists()


def test_prepare_body_reports_exists_flag(plan_base_env):
    result = prepare_body('my-plan', BODY_KIND_PR_REPLY)
    path = result['path']
    from pathlib import Path as _P
    _P(path).write_text('existing content', encoding='utf-8')
    result2 = prepare_body('my-plan', BODY_KIND_PR_REPLY)
    assert result2['exists'] is True


def test_prepare_body_rejects_invalid_slot(plan_base_env):
    result = prepare_body('my-plan', BODY_KIND_PR_CREATE, slot='BAD SLOT')
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_slot'


def test_read_and_consume_body_returns_content(plan_base_env):
    prep = prepare_body('my-plan', BODY_KIND_ISSUE_CREATE)
    from pathlib import Path as _P
    _P(prep['path']).write_text('Issue description body', encoding='utf-8')

    content, err = read_and_consume_body('my-plan', BODY_KIND_ISSUE_CREATE)
    assert err is None
    assert content == 'Issue description body'


def test_read_and_consume_body_missing_file(plan_base_env):
    content, err = read_and_consume_body('no-plan', BODY_KIND_PR_CREATE)
    assert content is None
    assert err is not None
    assert err['error'] == 'body_not_prepared'


def test_read_and_consume_body_empty_file(plan_base_env):
    prep = prepare_body('my-plan', BODY_KIND_PR_REPLY)
    from pathlib import Path as _P
    _P(prep['path']).write_text('   \n  ', encoding='utf-8')
    content, err = read_and_consume_body('my-plan', BODY_KIND_PR_REPLY)
    assert content is None
    assert err['error'] == 'body_empty'


def test_read_and_consume_body_optional_missing(plan_base_env):
    content, err = read_and_consume_body(
        'my-plan', BODY_KIND_PR_EDIT, required=False
    )
    assert err is None
    assert content == ''


def test_read_and_consume_body_requires_plan_id(plan_base_env):
    content, err = read_and_consume_body('', BODY_KIND_PR_CREATE)
    assert content is None
    assert err['error'] == 'missing_plan_id'


def test_delete_consumed_body_removes_file(plan_base_env):
    prep = prepare_body('my-plan', BODY_KIND_PR_THREAD_REPLY)
    from pathlib import Path as _P
    _P(prep['path']).write_text('body', encoding='utf-8')
    assert _P(prep['path']).exists()

    delete_consumed_body('my-plan', BODY_KIND_PR_THREAD_REPLY)
    assert not _P(prep['path']).exists()


def test_delete_consumed_body_silent_when_missing(plan_base_env):
    # Must not raise when the file does not exist
    delete_consumed_body('never-prepared', BODY_KIND_PR_CREATE)


# =============================================================================
# run_cli cwd propagation (worktree --project-dir plumbing)
# =============================================================================


class _FakeCompletedProcess:
    """Minimal stand-in for subprocess.CompletedProcess for run_cli tests."""

    def __init__(self, returncode: int = 0, stdout: str = '', stderr: str = ''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture
def _reset_default_cwd():
    """Save/restore the module-global _DEFAULT_CWD around each test."""
    previous = get_default_cwd()
    yield
    set_default_cwd(previous)


@pytest.fixture
def _capture_subprocess_run(monkeypatch):
    """Replace ci_base.subprocess.run with a capturing stub.

    Returns the list that will be populated with each call's kwargs. run_cli
    always calls subprocess.run via the ci_base module import, so patching the
    attribute on the module object is sufficient.
    """
    calls: list[dict] = []

    def fake_run(cmd, **kwargs):
        calls.append({'cmd': cmd, **kwargs})
        return _FakeCompletedProcess(returncode=0, stdout='ok', stderr='')

    monkeypatch.setattr(ci_base.subprocess, 'run', fake_run)
    return calls


def test_run_cli_forwards_explicit_cwd(_capture_subprocess_run, _reset_default_cwd):
    """An explicit cwd= kwarg must be passed through to subprocess.run."""
    set_default_cwd(None)
    rc, stdout, stderr = run_cli('gh', ['pr', 'list'], cwd='/tmp/worktree-xyz')
    assert rc == 0
    assert stdout == 'ok'
    assert stderr == ''
    assert len(_capture_subprocess_run) == 1
    call = _capture_subprocess_run[0]
    assert call['cwd'] == '/tmp/worktree-xyz'
    assert call['cmd'] == ['gh', 'pr', 'list']


def test_run_cli_uses_default_cwd_when_not_passed(
    _capture_subprocess_run, _reset_default_cwd
):
    """When no cwd= is passed, run_cli must fall back to _DEFAULT_CWD."""
    set_default_cwd('/tmp/from-default')
    run_cli('gh', ['pr', 'view'])
    assert _capture_subprocess_run[0]['cwd'] == '/tmp/from-default'


def test_run_cli_defaults_cwd_to_none(_capture_subprocess_run, _reset_default_cwd):
    """Legacy behaviour: no explicit cwd and no default → cwd=None."""
    set_default_cwd(None)
    run_cli('gh', ['pr', 'view'])
    assert _capture_subprocess_run[0]['cwd'] is None


def test_run_cli_explicit_cwd_overrides_default(
    _capture_subprocess_run, _reset_default_cwd
):
    """Explicit cwd= must win over the process-global default."""
    set_default_cwd('/tmp/from-default')
    run_cli('gh', ['pr', 'view'], cwd='/tmp/explicit')
    assert _capture_subprocess_run[0]['cwd'] == '/tmp/explicit'


def test_set_default_cwd_round_trip(_reset_default_cwd):
    """set_default_cwd / get_default_cwd should round-trip values including None."""
    set_default_cwd('/some/path')
    assert get_default_cwd() == '/some/path'
    set_default_cwd(None)
    assert get_default_cwd() is None


def test_run_cli_handles_file_not_found_without_touching_cwd(
    monkeypatch, _reset_default_cwd
):
    """When the CLI binary is missing, run_cli must still return gracefully."""

    def raising_run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(ci_base.subprocess, 'run', raising_run)
    set_default_cwd('/tmp/anywhere')
    rc, stdout, stderr = run_cli('nonexistent-cli', ['x'], not_found_msg='missing')
    assert rc == 127
    assert stdout == ''
    assert stderr == 'missing'


# Silence unused-import warnings caused by the fixtures above.
_ = (os, tempfile, subprocess)
