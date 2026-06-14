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
from datetime import UTC, datetime, timedelta

import ci_base
import pytest
from ci_base import (
    BODY_KIND_ISSUE_COMMENT,
    BODY_KIND_ISSUE_CREATE,
    BODY_KIND_PR_CREATE,
    BODY_KIND_PR_EDIT,
    BODY_KIND_PR_REPLY,
    BODY_KIND_PR_THREAD_REPLY,
    CI_LOG_TRUNCATE_LINES,
    DEFAULT_CI_INTERVAL,
    DEFAULT_CI_TIMEOUT,
    VALID_BODY_KINDS,
    add_head_arg,
    add_pr_create_args,
    build_parser,
    compute_elapsed,
    compute_total_elapsed,
    delete_consumed_body,
    enrich_failing_checks_with_logs,
    get_body_path,
    get_default_cwd,
    get_known_subcommands,
    poll_until,
    prepare_body,
    read_and_consume_body,
    register_subcommands,
    run_cli,
    set_default_cwd,
    truncate_log_content,
)

# =============================================================================
# Shared constants tests
# =============================================================================


def test_default_constants():
    """Shared constants should have expected values.

    ``DEFAULT_CI_TIMEOUT`` is now resolved from marshal.json at module load via
    ``_resolve_ci_timeout`` — see deliverable 7 (B8). The 600s value is the
    conservative fallback when marshal.json is absent (the test runs outside
    a configured project) OR the value baked into the project's marshal.json.
    A real marshal.json override would surface as a different integer here;
    this assertion exists to document the fallback contract.
    """
    assert DEFAULT_CI_TIMEOUT == 600
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
    """Should return None when start is None (new contract — was 0)."""
    now = datetime.now(UTC)
    result = compute_elapsed(None, None, now)
    assert result is None


def test_compute_elapsed_with_invalid_timestamp():
    """Should return None on parse failure (new contract — was 0)."""
    now = datetime.now(UTC)
    result = compute_elapsed('not-a-date', None, now)
    assert result is None


# =============================================================================
# compute_elapsed — Go zero-value timestamp handling (PARAMETERIZED)
# =============================================================================
#
# The provider CLIs (gh, glab) emit Go's zero-value time
# `0001-01-01T00:00:00Z` for never-started checks. Treating that as a real
# timestamp produces ~63.9 billion-second elapsed values. The contract:
#
# - Real start + real completed → non-negative int (delta in seconds)
# - Zero-time started_at → None (filtered)
# - Zero-time completed_at + real start → falls back to (now - start)
# - completedAt before startedAt → None (negative delta clamped)
# - Parse-failure on either side → None
#
# All cases below use a fixed `now` so deltas are deterministic.


_NOW = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
_GO_ZERO = '0001-01-01T00:00:00Z'


@pytest.mark.parametrize(
    'started_at,completed_at,expected',
    [
        # Case 1: Valid pair → delta in seconds
        (
            '2025-01-15T11:55:00+00:00',
            '2025-01-15T12:00:00+00:00',
            300,
        ),
        # Case 2: Zero-time started_at → None (Go sentinel poisons computation)
        (_GO_ZERO, '2025-01-15T12:00:00+00:00', None),
        # Case 3: Zero-time completed_at, real start → fallback to (now - start)
        ('2025-01-15T11:59:00+00:00', _GO_ZERO, 60),
        # Case 4: completedAt before startedAt (negative delta) → None
        (
            '2025-01-15T12:00:05+00:00',
            '2025-01-15T12:00:00+00:00',
            None,
        ),
        # Case 5: Parse-failure on started_at → None
        ('garbage-not-a-date', '2025-01-15T12:00:00+00:00', None),
        # Case 6: Parse-failure on completed_at with real start. Because
        # `_is_zero_time(completed_at)` returns True for unparseable strings
        # (defensive default), the function falls back to `now - start` and
        # returns the elapsed-since-start value. This is the documented
        # behaviour of the `else` branch in `compute_elapsed`.
        ('2025-01-15T11:59:00+00:00', 'still-garbage', 60),
        # Case 7: Empty string started_at → None
        ('', '2025-01-15T12:00:00+00:00', None),
        # Case 8: Pre-1971 sentinel year → None (handled by _is_zero_time)
        ('1970-01-01T00:00:00+00:00', '2025-01-15T12:00:00+00:00', None),
    ],
    ids=[
        'valid_pair',
        'zero_time_started_at',
        'zero_time_completed_at',
        'completed_before_started',
        'parse_failure_started',
        'parse_failure_completed',
        'empty_started',
        'pre_1971_sentinel',
    ],
)
def test_compute_elapsed_parameterized(started_at, completed_at, expected):
    """Parameterized matrix of compute_elapsed contract cases."""
    result = compute_elapsed(started_at, completed_at, _NOW)
    assert result == expected, (
        f'compute_elapsed({started_at!r}, {completed_at!r}, _NOW) → {result!r}, expected {expected!r}'
    )


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
# compute_total_elapsed — Go zero-value timestamp handling
# =============================================================================


def test_compute_total_elapsed_skips_go_zero_value_sentinels():
    """Go zero-value timestamps must not poison the aggregate.

    Without filtering, 0001-01-01 produces ~63.9 billion-second elapsed
    values. The earliest of [zero, real-60s-ago, zero] should be the real
    timestamp, yielding ~60s.
    """
    now = datetime.now(UTC)
    real = (now - timedelta(seconds=60)).isoformat()
    result = compute_total_elapsed([_GO_ZERO, real, _GO_ZERO], now)
    assert 59 <= result <= 61, (
        f'Expected ~60s aggregate (real start) but got {result}s — '
        'Go zero-value sentinel may have poisoned the earliest pick'
    )


def test_compute_total_elapsed_all_go_zero_returns_zero():
    """When every entry is a Go zero-value sentinel, no usable start exists → 0."""
    now = datetime.now(UTC)
    result = compute_total_elapsed([_GO_ZERO, _GO_ZERO, None], now)
    assert result == 0


def test_compute_total_elapsed_mixed_real_and_zero_picks_real_earliest():
    """Mixed list: earliest real timestamp wins; zeros are skipped."""
    now = datetime.now(UTC)
    early = (now - timedelta(seconds=300)).isoformat()
    late = (now - timedelta(seconds=60)).isoformat()
    # Order intentionally shuffled with zero-time and None interspersed.
    result = compute_total_elapsed([late, _GO_ZERO, None, early, _GO_ZERO], now)
    assert 299 <= result <= 301, f'Expected ~300s (earliest real) but got {result}s'


def test_compute_total_elapsed_parse_failures_skipped():
    """Unparseable timestamps must be silently skipped."""
    now = datetime.now(UTC)
    real = (now - timedelta(seconds=60)).isoformat()
    result = compute_total_elapsed(['garbage', real, 'still-bad'], now)
    assert 59 <= result <= 61


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

    args = parser.parse_args(['create', '--title', 'T', '--plan-id', 'my-plan', '--head', 'feature/x'])
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
        parser.parse_args(['create', '--title', 'T', '--plan-id', 'p', '--body', 'X'])
    with pytest.raises(SystemExit):
        parser.parse_args(['create', '--title', 'T', '--plan-id', 'p', '--body-file', '/tmp/x'])


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
    args = parser.parse_args(['create', '--title', 'T', '--plan-id', 'p', '--slot', 'pr-body'])
    assert args.slot == 'pr-body'


def test_build_parser_pr_view_accepts_head_flag():
    """build_parser should register --head on pr view (was: no args)."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['pr', 'view', '--head', 'feature/x'])
    assert args.head == 'feature/x'


def test_build_parser_pr_merge_pr_number_optional():
    """pr merge should accept --head as alternative to --pr-number (both optional)."""
    parser, _, _, _, _ = build_parser('test')
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
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['pr', 'auto-merge', '--head', 'feature/x'])
    assert args.head == 'feature/x'
    assert args.pr_number is None


def test_build_parser_ci_status_pr_number_optional():
    """checks status should accept --head as alternative to --pr-number."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'status', '--head', 'feature/x'])
    assert args.head == 'feature/x'
    assert args.pr_number is None


# =============================================================================
# prepare-body subcommand registration (argparse wiring)
# =============================================================================


def test_build_parser_registers_pr_prepare_body():
    """`pr prepare-body` must be registered and require --plan-id."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['pr', 'prepare-body', '--plan-id', 'my-plan'])
    assert args.command == 'pr'
    assert args.pr_command == 'prepare-body'
    assert args.plan_id == 'my-plan'
    assert args.prepare_for == 'create'  # default

    args = parser.parse_args(['pr', 'prepare-body', '--plan-id', 'my-plan', '--for', 'edit', '--slot', 'update'])
    assert args.prepare_for == 'edit'
    assert args.slot == 'update'

    with pytest.raises(SystemExit):
        parser.parse_args(['pr', 'prepare-body'])  # missing --plan-id


def test_build_parser_registers_pr_prepare_comment():
    """`pr prepare-comment` must be registered with reply/thread-reply modes."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['pr', 'prepare-comment', '--plan-id', 'my-plan'])
    assert args.pr_command == 'prepare-comment'
    assert args.prepare_for == 'reply'

    args = parser.parse_args(['pr', 'prepare-comment', '--plan-id', 'my-plan', '--for', 'thread-reply'])
    assert args.prepare_for == 'thread-reply'


def test_build_parser_registers_issue_prepare_body():
    """`issue prepare-body` must be registered and require --plan-id."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['issue', 'prepare-body', '--plan-id', 'my-plan'])
    assert args.command == 'issue'
    assert args.issue_command == 'prepare-body'
    assert args.plan_id == 'my-plan'


def test_issue_comment_body_kind_in_valid_set():
    """The issue-comment body kind must be a recognised consumer surface."""
    assert BODY_KIND_ISSUE_COMMENT == 'issue-comment'
    assert BODY_KIND_ISSUE_COMMENT in VALID_BODY_KINDS


def test_get_body_path_accepts_issue_comment_kind(plan_base_env):
    """get_body_path must resolve a scratch path for the issue-comment kind."""
    path = get_body_path('my-plan', BODY_KIND_ISSUE_COMMENT)
    assert path.name == 'issue-comment-default.md'
    assert 'work/ci-bodies' in str(path)


def test_build_parser_registers_issue_comment():
    """`issue comment` must be registered, require --issue and --plan-id, accept --slot."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['issue', 'comment', '--issue', '42', '--plan-id', 'my-plan'])
    assert args.command == 'issue'
    assert args.issue_command == 'comment'
    assert args.issue == '42'
    assert args.plan_id == 'my-plan'

    args = parser.parse_args(['issue', 'comment', '--issue', '42', '--plan-id', 'my-plan', '--slot', 'milestone'])
    assert args.slot == 'milestone'


def test_issue_comment_requires_issue():
    """`issue comment` must reject a missing --issue."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'comment', '--plan-id', 'my-plan'])


def test_issue_comment_requires_plan_id():
    """`issue comment` must reject a missing --plan-id (body consumer)."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'comment', '--issue', '42'])


def test_issue_comment_rejects_body_flag():
    """`issue comment` consumes a prepared body — a raw --body flag is rejected."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'comment', '--issue', '42', '--plan-id', 'p', '--body', 'X'])


def test_build_parser_registers_issue_prepare_comment():
    """`issue prepare-comment` must be registered and require --plan-id."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['issue', 'prepare-comment', '--plan-id', 'my-plan'])
    assert args.command == 'issue'
    assert args.issue_command == 'prepare-comment'
    assert args.plan_id == 'my-plan'

    args = parser.parse_args(['issue', 'prepare-comment', '--plan-id', 'my-plan', '--slot', 'alt'])
    assert args.slot == 'alt'


def test_issue_prepare_comment_requires_plan_id():
    """`issue prepare-comment` must reject a missing --plan-id."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'prepare-comment'])


# =============================================================================
# Consumer subcommands reject removed legacy body flags
# =============================================================================


def test_pr_reply_rejects_body_flag():
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['pr', 'reply', '--pr-number', '1', '--plan-id', 'p', '--body', 'X'])


def test_pr_thread_reply_rejects_body_flag():
    parser, _, _, _, _ = build_parser('test')
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
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['pr', 'edit', '--pr-number', '1', '--plan-id', 'p', '--body', 'X'])


def test_issue_create_rejects_body_flag():
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'create', '--title', 'T', '--plan-id', 'p', '--body', 'X'])


def test_consumers_require_plan_id():
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['pr', 'reply', '--pr-number', '1'])
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'create', '--title', 'T'])


# =============================================================================
# Body store helpers
# =============================================================================


@pytest.fixture
def plan_base_env(tmp_path, monkeypatch):
    """Point PLAN_BASE_DIR at a temporary directory so get_plan_dir is sandboxed.

    Also seeds an initialized plan directory for the conventional ``my-plan``
    plan_id used by the body-store happy-path tests. The
    ``ci_base.prepare_body`` script-side guard (lesson 2026-05-15-X) now
    requires the plan dir to contain a ``status.json`` sentinel before any
    scratch path is materialised; without this seed every existing
    prepare-body test would fail.

    Tests that exercise the guard's rejection path (unknown plan_id, plan
    dir missing status.json) deliberately use a DIFFERENT plan_id so the
    seed below does not satisfy the guard for them.
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plan_dir = tmp_path / 'plans' / 'my-plan'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')
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


# ---------------------------------------------------------------------------
# Script-side require_plan_exists guard
#
# prepare_body MUST refuse to materialise a body scratch path under a plan
# directory that does not exist (or exists but lacks status.json). The guard
# returns the canonical TOON envelope and MUST NOT mkdir the plan tree as a
# side-effect.
# ---------------------------------------------------------------------------


def test_prepare_body_rejects_unknown_plan_id_no_mkdir(plan_base_env):
    """Unknown plan_id: prepare_body returns plan_not_found, no plan dir created."""
    unknown_plan_dir = plan_base_env / 'plans' / 'never-initialized'
    assert not unknown_plan_dir.exists(), 'pre-condition: plan dir must not exist'

    result = prepare_body('never-initialized', BODY_KIND_PR_CREATE)

    assert result['status'] == 'error'
    assert result['error'] == 'plan_not_found'
    assert result['plan_id'] == 'never-initialized'
    assert 'never-initialized' in result['plan_dir']
    # Side-effect invariant: the guard MUST NOT have created the plan dir
    # (the orphan-mkdir failure mode this guard exists to prevent).
    assert not unknown_plan_dir.exists()
    # And no scratch ci-bodies dir is left behind either.
    assert not (unknown_plan_dir / 'work' / 'ci-bodies').exists()


def test_prepare_body_rejects_plan_dir_missing_status_json_no_mkdir(plan_base_env):
    """Plan dir exists but no status.json: prepare_body returns plan_not_found."""
    half_dir = plan_base_env / 'plans' / 'half-initialized'
    half_dir.mkdir(parents=True)
    assert not (half_dir / 'status.json').exists()

    result = prepare_body('half-initialized', BODY_KIND_PR_REPLY)

    assert result['status'] == 'error'
    assert result['error'] == 'plan_not_found'
    assert result['plan_id'] == 'half-initialized'
    # The pre-existing directory was left untouched — the guard does not
    # remove it, and it certainly does not auto-create status.json.
    assert half_dir.is_dir()
    assert not (half_dir / 'status.json').exists()
    # The scratch tree was NOT materialised.
    assert not (half_dir / 'work' / 'ci-bodies').exists()


def test_prepare_body_with_initialized_plan_id_continues_to_work(plan_base_env):
    """Happy path: initialized plan_id (status.json present) → success.

    The `plan_base_env` fixture seeds `my-plan/status.json`. This test pins
    that the guard does not regress the existing prepare-body contract for
    in-progress plans.
    """
    result = prepare_body('my-plan', BODY_KIND_PR_CREATE)

    assert result['status'] == 'success'
    assert result['kind'] == BODY_KIND_PR_CREATE
    assert result['slot'] == 'default'
    from pathlib import Path as _P

    assert _P(result['path']).parent.exists()


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
    content, err = read_and_consume_body('my-plan', BODY_KIND_PR_EDIT, required=False)
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


def test_run_cli_uses_default_cwd_when_not_passed(_capture_subprocess_run, _reset_default_cwd):
    """When no cwd= is passed, run_cli must fall back to _DEFAULT_CWD."""
    set_default_cwd('/tmp/from-default')
    run_cli('gh', ['pr', 'view'])
    assert _capture_subprocess_run[0]['cwd'] == '/tmp/from-default'


def test_run_cli_defaults_cwd_to_none(_capture_subprocess_run, _reset_default_cwd):
    """Legacy behaviour: no explicit cwd and no default → cwd=None."""
    set_default_cwd(None)
    run_cli('gh', ['pr', 'view'])
    assert _capture_subprocess_run[0]['cwd'] is None


def test_run_cli_explicit_cwd_overrides_default(_capture_subprocess_run, _reset_default_cwd):
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


def test_run_cli_handles_file_not_found_without_touching_cwd(monkeypatch, _reset_default_cwd):
    """When the CLI binary is missing, run_cli must still return gracefully."""

    def raising_run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(ci_base.subprocess, 'run', raising_run)
    set_default_cwd('/tmp/anywhere')
    rc, stdout, stderr = run_cli('nonexistent-cli', ['x'], not_found_msg='missing')
    assert rc == 127
    assert stdout == ''
    assert stderr == 'missing'


# =============================================================================
# checks wait-for-status-flip argparse tests
# =============================================================================


def test_ci_wait_for_status_flip_registered():
    """`checks wait-for-status-flip` subcommand must be registered under the checks subparser."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'wait-for-status-flip', '--pr-number', '42'])
    assert args.command == 'checks'
    assert args.checks_command == 'wait-for-status-flip'
    assert args.pr_number == 42


def test_ci_wait_for_status_flip_requires_pr_number():
    """`checks wait-for-status-flip` must exit when --pr-number is omitted."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['checks', 'wait-for-status-flip'])


def test_ci_wait_for_status_flip_defaults():
    """--timeout and --interval default to module constants; --expected defaults to 'any'."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'wait-for-status-flip', '--pr-number', '7'])
    assert args.timeout == DEFAULT_CI_TIMEOUT
    assert args.interval == DEFAULT_CI_INTERVAL
    assert args.expected == 'any'


def test_ci_wait_for_status_flip_accepts_custom_timeout_and_interval():
    """--timeout and --interval should accept integer overrides."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(
        [
            'checks',
            'wait-for-status-flip',
            '--pr-number',
            '7',
            '--timeout',
            '600',
            '--interval',
            '15',
        ]
    )
    assert args.timeout == 600
    assert args.interval == 15


@pytest.mark.parametrize('expected', ['success', 'failure', 'any'])
def test_ci_wait_for_status_flip_accepts_valid_expected_values(expected):
    """--expected accepts success, failure, and any."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', 'wait-for-status-flip', '--pr-number', '7', '--expected', expected])
    assert args.expected == expected


def test_ci_wait_for_status_flip_rejects_invalid_expected_value():
    """--expected must reject values outside the success|failure|any choice set."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                'checks',
                'wait-for-status-flip',
                '--pr-number',
                '7',
                '--expected',
                'pending',
            ]
        )


# =============================================================================
# issue wait-for-close argparse tests
# =============================================================================


def test_issue_wait_for_close_registered():
    """`issue wait-for-close` subcommand must be registered under the issue subparser."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['issue', 'wait-for-close', '--issue-number', '99'])
    assert args.command == 'issue'
    assert args.issue_command == 'wait-for-close'
    assert args.issue_number == 99


def test_issue_wait_for_close_requires_issue_number():
    """`issue wait-for-close` must exit when --issue-number is omitted."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'wait-for-close'])


def test_issue_wait_for_close_defaults():
    """--timeout and --interval default to module constants."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['issue', 'wait-for-close', '--issue-number', '99'])
    assert args.timeout == DEFAULT_CI_TIMEOUT
    assert args.interval == DEFAULT_CI_INTERVAL


def test_issue_wait_for_close_accepts_custom_timeout_and_interval():
    """--timeout and --interval should accept integer overrides."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(
        [
            'issue',
            'wait-for-close',
            '--issue-number',
            '99',
            '--timeout',
            '120',
            '--interval',
            '5',
        ]
    )
    assert args.timeout == 120
    assert args.interval == 5


# =============================================================================
# issue wait-for-label argparse tests
# =============================================================================


def test_issue_wait_for_label_registered():
    """`issue wait-for-label` subcommand must be registered under the issue subparser."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(
        [
            'issue',
            'wait-for-label',
            '--issue-number',
            '99',
            '--label',
            'ready',
        ]
    )
    assert args.command == 'issue'
    assert args.issue_command == 'wait-for-label'
    assert args.issue_number == 99
    assert args.label == 'ready'


def test_issue_wait_for_label_requires_issue_number():
    """`issue wait-for-label` must exit when --issue-number is omitted."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'wait-for-label', '--label', 'ready'])


def test_issue_wait_for_label_requires_label():
    """`issue wait-for-label` must exit when --label is omitted."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['issue', 'wait-for-label', '--issue-number', '99'])


def test_issue_wait_for_label_defaults():
    """--timeout and --interval default to module constants; --mode defaults to 'present'."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(
        [
            'issue',
            'wait-for-label',
            '--issue-number',
            '99',
            '--label',
            'ready',
        ]
    )
    assert args.timeout == DEFAULT_CI_TIMEOUT
    assert args.interval == DEFAULT_CI_INTERVAL
    assert args.mode == 'present'


def test_issue_wait_for_label_accepts_custom_timeout_and_interval():
    """--timeout and --interval should accept integer overrides."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(
        [
            'issue',
            'wait-for-label',
            '--issue-number',
            '99',
            '--label',
            'ready',
            '--timeout',
            '45',
            '--interval',
            '3',
        ]
    )
    assert args.timeout == 45
    assert args.interval == 3


@pytest.mark.parametrize('mode', ['present', 'absent'])
def test_issue_wait_for_label_accepts_valid_mode_values(mode):
    """--mode accepts present and absent."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(
        [
            'issue',
            'wait-for-label',
            '--issue-number',
            '99',
            '--label',
            'ready',
            '--mode',
            mode,
        ]
    )
    assert args.mode == mode


def test_issue_wait_for_label_rejects_invalid_mode_value():
    """--mode must reject values outside the present|absent choice set."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                'issue',
                'wait-for-label',
                '--issue-number',
                '99',
                '--label',
                'ready',
                '--mode',
                'toggled',
            ]
        )


# =============================================================================
# extract_routing_args — two-state ``--plan-id`` / ``--project-dir`` contract
# =============================================================================
#
# ``extract_routing_args`` is the router-side wrapper that combines
# ``extract_project_dir`` and ``extract_plan_id``. It enforces:
#
# * router-level ``--plan-id`` is consumed for worktree resolution
# * subcommand-level ``--plan-id`` (after pr/ci/issue/branch) is left in place
# * supplying both flags at the router → exit 2 + mutually_exclusive_args
# * supplying only ``--plan-id`` → manage-status get-worktree-path resolves
# * supplying only ``--project-dir`` → returned verbatim (legacy escape hatch)
# * supplying neither → returns (None, argv)


@pytest.fixture(autouse=False)
def _reset_subcommand_cache():
    """Reset ci_base._KNOWN_SUBCOMMANDS_CACHE around each test.

    The subcommand registry is module-level state — tests that call
    ``register_subcommands`` or that trigger ``get_known_subcommands``
    would otherwise pollute later tests in the session.  This fixture
    saves and restores the cache value so each test starts clean.
    """
    previous = ci_base._KNOWN_SUBCOMMANDS_CACHE
    ci_base._KNOWN_SUBCOMMANDS_CACHE = None
    yield
    ci_base._KNOWN_SUBCOMMANDS_CACHE = previous


def test_extract_routing_args_neither_flag_returns_none():
    """No routing flags → (None, argv) so the legacy "inherit cwd" path runs."""
    from ci_base import extract_routing_args

    resolved, remaining = extract_routing_args(['pr', 'view'])
    assert resolved is None
    assert remaining == ['pr', 'view']


def test_extract_routing_args_project_dir_only_returns_path():
    """--project-dir alone is returned verbatim as the resolved cwd."""
    from ci_base import extract_routing_args

    resolved, remaining = extract_routing_args(['--project-dir', '/tmp/explicit', 'pr', 'view'])
    # The resolver normalizes to absolute paths; we assert the input survived.
    assert resolved is not None
    assert resolved.endswith('explicit'), f'Expected absolute path ending in explicit, got: {resolved!r}'
    assert remaining == ['pr', 'view']


def test_extract_routing_args_plan_id_only_resolves_via_manage_status(monkeypatch):
    """--plan-id alone is resolved via the patched manage-status helper."""
    import resolve_project_dir as _routing
    from ci_base import extract_routing_args

    monkeypatch.setattr(_routing, '_query_worktree_path', lambda _pid: (True, '/tmp/worktree-resolved'))
    resolved, remaining = extract_routing_args(['--plan-id', 'task-routing-canonical', 'pr', 'view'])
    assert resolved is not None
    assert resolved.endswith('worktree-resolved'), f'Expected worktree path, got: {resolved!r}'
    assert remaining == ['pr', 'view']


def test_extract_routing_args_plan_id_use_worktree_false_falls_back(monkeypatch):
    """--plan-id with use_worktree=false falls back to main checkout root."""
    import resolve_project_dir as _routing
    from ci_base import extract_routing_args

    monkeypatch.setattr(_routing, '_query_worktree_path', lambda _pid: (False, ''))
    monkeypatch.setattr(_routing, '_main_checkout_root', lambda: '/tmp/main-checkout')
    resolved, remaining = extract_routing_args(['--plan-id', 'task-routing-canonical', 'pr', 'view'])
    assert resolved == '/tmp/main-checkout'
    assert remaining == ['pr', 'view']


def test_extract_routing_args_both_flags_exits_with_mutually_exclusive_error(capsys):
    """Both --plan-id and --project-dir at the router → exit 2 + TOON error."""
    from ci_base import extract_routing_args

    with pytest.raises(SystemExit) as exc_info:
        extract_routing_args(
            [
                '--plan-id',
                'task-routing-canonical',
                '--project-dir',
                '/tmp/explicit',
                'pr',
                'view',
            ]
        )
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert 'mutually_exclusive_args' in captured.out


def test_extract_routing_args_router_level_plan_id_before_prepare_body_accepted(monkeypatch):
    """``--plan-id`` BEFORE a body-consumer subcommand is accepted at router level.

    Fix A (secondary guard): the guard rejects routing flags that appear AFTER
    the subcommand boundary. When ``--plan-id`` is placed BEFORE the subcommand
    token (router-level placement), the guard must NOT fire — the flag is
    consumed by the router, worktree resolution succeeds, and the remaining argv
    contains only the subcommand and its own arguments.

    This test specifically uses ``pr prepare-body`` — a subcommand that declares
    its own ``--plan-id`` argument via ``add_plan_id_arg``. The test demonstrates
    that router-level ``--plan-id`` placement is the correct calling convention
    even when the downstream subcommand also needs a ``--plan-id`` at its own
    argparse level.
    """
    import resolve_project_dir as _routing
    from ci_base import extract_routing_args

    monkeypatch.setattr(_routing, '_query_worktree_path', lambda _pid: (True, '/tmp/worktree-resolved'))
    resolved, remaining = extract_routing_args(['--plan-id', 'my-plan', 'pr', 'prepare-body'])
    assert resolved is not None
    assert resolved.endswith('worktree-resolved'), f'Expected worktree path, got: {resolved!r}'
    assert remaining == ['pr', 'prepare-body']


def test_extract_routing_args_plan_id_after_prepare_body_passes_through():
    """``--plan-id`` AFTER ``pr prepare-body`` passes through to the subcommand parser.

    Body-consumer subcommands (``pr prepare-body``, ``pr create``, ``issue create`` …)
    declare their own ``--plan-id`` argparse argument and consume the post-subcommand
    occurrence themselves. The positional guard MUST NOT reject this placement —
    rejecting it would break the documented invocation pattern for every body-
    consumer call site.

    The router returns ``resolved=None`` (no router-level routing flag supplied)
    and the unchanged argv so the subcommand argparse can consume ``--plan-id``.
    """
    from ci_base import extract_routing_args

    resolved, remaining = extract_routing_args(['pr', 'prepare-body', '--plan-id', 'my-plan'])
    assert resolved is None
    assert remaining == ['pr', 'prepare-body', '--plan-id', 'my-plan']


def test_argparse_layer_plan_id_unaffected_by_routing_guard():
    """The positional routing guard does not interfere with ``build_parser`` argparse.

    Fix A (secondary guard) lives exclusively in ``extract_routing_args``. The
    argparse layer — used by provider scripts AFTER routing has been done — must
    still accept ``pr prepare-body --plan-id xxx`` when the tokens are passed
    directly to ``build_parser().parse_args()``.

    This test documents the separation of concerns: ``extract_routing_args``
    enforces the router-level placement rule; ``build_parser`` enforces the
    subcommand-level argument contract. A provider that has already stripped
    router-level flags via ``extract_routing_args`` can subsequently feed the
    remaining subcommand argv (which may include a subcommand-level ``--plan-id``)
    directly to its argparse parser without triggering the routing guard.
    """
    parser, _, _, _, _ = build_parser('test')
    # Direct argparse parse — no extract_routing_args in the call path.
    # The routing guard is absent here, so --plan-id at the subcommand level
    # is accepted by argparse normally.
    args = parser.parse_args(['pr', 'prepare-body', '--plan-id', 'my-plan'])
    assert args.command == 'pr'
    assert args.pr_command == 'prepare-body'
    assert args.plan_id == 'my-plan'


def test_extract_routing_args_comments_stage_plan_id_passes_through(_reset_subcommand_cache):
    """``--plan-id`` AFTER the ``comments-stage`` token passes through to the subcommand.

    ``comments-stage`` declares its own ``--plan-id`` argument (for finding-store
    routing). The positional guard MUST NOT reject this placement — the subcommand
    parser consumes ``--plan-id`` directly from its own argv.

    Provider scripts register ``comments-stage`` via ``register_subcommands`` at
    import time; this test mirrors that pattern.
    """
    from ci_base import extract_routing_args

    register_subcommands({'comments-stage', 'fetch-comments'})

    resolved, remaining = extract_routing_args(
        ['comments-stage', '--pr-number', '123', '--plan-id', 'my-plan'],
    )
    assert resolved is None
    assert remaining == ['comments-stage', '--pr-number', '123', '--plan-id', 'my-plan']


def test_extract_routing_args_fetch_comments_plan_id_passes_through(_reset_subcommand_cache):
    """``--plan-id`` AFTER the ``fetch-comments`` token passes through to the subcommand.

    Same contract as ``comments-stage`` — the subcommand parser declares and
    consumes its own ``--plan-id`` argument; the router MUST NOT reject the
    post-subcommand placement.
    """
    from ci_base import extract_routing_args

    register_subcommands({'comments-stage', 'fetch-comments'})

    resolved, remaining = extract_routing_args(
        ['fetch-comments', '--pr', '5', '--plan-id', 'my-plan'],
    )
    assert resolved is None
    assert remaining == ['fetch-comments', '--pr', '5', '--plan-id', 'my-plan']


# =============================================================================
# Registration-driven subcommand boundary set — unit tests
# =============================================================================
#
# These tests cover the ``get_known_subcommands`` / ``register_subcommands``
# contract introduced to replace the literal ``_SUBCOMMAND_TOKENS`` frozenset.
# Each test uses the ``_reset_subcommand_cache`` fixture so the module-level
# cache is restored to its pre-test value after each case.


def test_get_known_subcommands_bootstraps_from_build_parser(_reset_subcommand_cache):
    """get_known_subcommands() must include every top-level key from build_parser()."""
    tokens = get_known_subcommands()
    # build_parser() registers four top-level subcommands.
    assert 'pr' in tokens
    assert 'checks' in tokens
    assert 'issue' in tokens
    assert 'branch' in tokens


def test_get_known_subcommands_returns_frozenset(_reset_subcommand_cache):
    """get_known_subcommands() must return a frozenset (immutable)."""
    tokens = get_known_subcommands()
    assert isinstance(tokens, frozenset)


def test_get_known_subcommands_cached_on_second_call(_reset_subcommand_cache):
    """get_known_subcommands() must return the same object on repeated calls (lazy cache)."""
    first = get_known_subcommands()
    second = get_known_subcommands()
    assert first is second


def test_register_subcommands_extends_known_set(_reset_subcommand_cache):
    """register_subcommands() must merge extra tokens into the registry."""
    before = get_known_subcommands()
    assert 'fetch-comments' not in before
    assert 'comments-stage' not in before

    register_subcommands({'fetch-comments', 'comments-stage'})

    after = get_known_subcommands()
    assert 'fetch-comments' in after
    assert 'comments-stage' in after
    # Existing parser-derived tokens must still be present.
    assert 'pr' in after
    assert 'checks' in after


def test_register_subcommands_idempotent(_reset_subcommand_cache):
    """Calling register_subcommands() twice with overlapping tokens is safe."""
    register_subcommands({'fetch-comments'})
    register_subcommands({'fetch-comments', 'comments-stage'})
    tokens = get_known_subcommands()
    assert 'fetch-comments' in tokens
    assert 'comments-stage' in tokens


def test_register_subcommands_does_not_remove_existing(_reset_subcommand_cache):
    """register_subcommands() must never shrink the existing token set."""
    base = get_known_subcommands()
    register_subcommands({'extra-token'})
    after = get_known_subcommands()
    # All original tokens still present.
    assert base.issubset(after)
    assert 'extra-token' in after


def test_split_at_subcommand_uses_registry(_reset_subcommand_cache):
    """_split_at_subcommand must use the live registry, not a stale literal."""
    from ci_base import _split_at_subcommand

    # Before registration, 'fetch-comments' is unknown; entire argv is prefix.
    pre, post = _split_at_subcommand(['--plan-id', 'p', 'fetch-comments', '--pr', '5'])
    assert post == []  # 'fetch-comments' not yet known

    # After registration, 'fetch-comments' splits the argv.
    register_subcommands({'fetch-comments'})
    pre2, post2 = _split_at_subcommand(['--plan-id', 'p', 'fetch-comments', '--pr', '5'])
    assert pre2 == ['--plan-id', 'p']
    assert post2 == ['fetch-comments', '--pr', '5']


# =============================================================================
# --error-style registration on checks wait / checks status
# =============================================================================
#
# The shared failure-path log-download hook (``enrich_failing_checks_with_logs``)
# is governed by an ``--error-style`` selector. That flag MUST be registered on
# both the ``checks wait`` and ``checks status`` subparsers so a caller can pick
# the per-build-system filter heuristic at invocation time. The default is
# ``generic`` and the choice set is restricted to maven|gradle|npm|generic.


@pytest.mark.parametrize('checks_command', ['wait', 'status'])
def test_error_style_registered_on_checks_subparsers(checks_command):
    """``--error-style`` must be accepted on both checks wait and checks status."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(
        ['checks', checks_command, '--pr-number', '42', '--error-style', 'maven']
    )
    assert args.error_style == 'maven'


@pytest.mark.parametrize('checks_command', ['wait', 'status'])
def test_error_style_defaults_to_generic(checks_command):
    """When ``--error-style`` is omitted it defaults to ``generic`` on both subparsers."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(['checks', checks_command, '--pr-number', '42'])
    assert args.error_style == 'generic'


@pytest.mark.parametrize('checks_command', ['wait', 'status'])
@pytest.mark.parametrize('style', ['maven', 'gradle', 'npm', 'generic'])
def test_error_style_accepts_every_valid_choice(checks_command, style):
    """Every member of the maven|gradle|npm|generic choice set is accepted."""
    parser, _, _, _, _ = build_parser('test')
    args = parser.parse_args(
        ['checks', checks_command, '--pr-number', '42', '--error-style', style]
    )
    assert args.error_style == style


@pytest.mark.parametrize('checks_command', ['wait', 'status'])
def test_error_style_rejects_unknown_value(checks_command):
    """An out-of-choice ``--error-style`` value must exit (argparse error)."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(
            ['checks', checks_command, '--pr-number', '42', '--error-style', 'sbt']
        )


def test_add_error_style_arg_registers_default_generic():
    """add_error_style_arg directly registers ``--error-style`` defaulting to generic."""
    parser = argparse.ArgumentParser()
    ci_base.add_error_style_arg(parser)
    args = parser.parse_args([])
    assert args.error_style == 'generic'
    args = parser.parse_args(['--error-style', 'gradle'])
    assert args.error_style == 'gradle'


# =============================================================================
# enrich_failing_checks_with_logs — shared failure-path download+filter+store
# =============================================================================
#
# The hook iterates a list of failing-check entries and, for each, downloads the
# raw log via an injected fetcher, filters it, persists raw + filtered variants
# under the manage-ci-artifacts storage layout, and appends the plan-dir-relative
# ``log_file`` / ``filtered_log_file`` back onto the entry. The contract pinned
# below:
#
# - For >=2 entries it appends a DISTINCT log_file / filtered_log_file per entry,
#   slug-disambiguated, with NO collision even when two entries share a run_id.
# - It degrades gracefully PER ENTRY (empty path fields on the affected entry
#   only, never raising) when plan_id / run_id is absent or a fetch fails.
#
# Tests inject a stub raw-log fetcher and use the ``plan_context`` fixture's
# isolated plan dir so no live CI access is required.


def _failing_check(name: str, run_id: str, *, job_name: str | None = None) -> dict:
    """Build a minimal failing-check entry for the enrich hook."""
    return {
        'name': name,
        'job_name': job_name if job_name is not None else name,
        'workflow_name': 'ci',
        'conclusion': 'failure',
        'run_id': run_id,
        'started_at': '2026-05-19T00:00:00Z',
        'completed_at': '2026-05-19T00:01:00Z',
        'run_url': 'https://example/runs/x',
        'head_sha': 'cafef00d',
        'pr_number': 7,
    }


def test_enrich_appends_distinct_paths_per_entry(plan_context):
    """Two failing checks (distinct run_ids) each gain their own raw + filtered paths."""
    plan_id = 'enrich-distinct-runs'
    entries = [
        _failing_check('verify / verify', '101'),
        _failing_check('build (3.12)', '102'),
    ]

    def fetcher(run_id: str, job_id: str = '') -> str:
        return f'ERROR boom for run {run_id}\ntrailing line\n'

    result = enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
    )

    # The hook mutates in place and returns the same list.
    assert result is entries
    log_files = [e['log_file'] for e in entries]
    filtered_files = [e['filtered_log_file'] for e in entries]
    # Every entry got a non-empty, distinct pair.
    assert all(log_files), log_files
    assert all(filtered_files), filtered_files
    assert len(set(log_files)) == 2, f'log_file paths collided: {log_files}'
    assert len(set(filtered_files)) == 2, f'filtered_log_file paths collided: {filtered_files}'
    # Paths reflect each check's slug.
    assert any('verify-verify' in p for p in log_files)
    assert any('build-3-12' in p for p in log_files)


def test_enrich_no_collision_when_two_checks_share_run_id(plan_context):
    """Two failing checks sharing ONE run_id must get distinctly-slugged, non-colliding files."""
    plan_id = 'enrich-shared-run-id'
    entries = [
        _failing_check('verify / verify', '500'),
        _failing_check('build (3.12)', '500'),
    ]

    def fetcher(run_id: str, job_id: str = '') -> str:
        return f'ERROR failure log for {run_id}\n'

    enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
    )

    log_files = [e['log_file'] for e in entries]
    filtered_files = [e['filtered_log_file'] for e in entries]
    assert all(log_files), log_files
    assert all(filtered_files), filtered_files
    # The defining assertion: same run_id, but the slug disambiguates so the two
    # entries never write to the same on-disk path.
    assert log_files[0] != log_files[1], f'shared run_id collided: {log_files}'
    assert filtered_files[0] != filtered_files[1], (
        f'shared run_id filtered paths collided: {filtered_files}'
    )
    # Both raw files actually exist on disk (no overwrite of one by the other).
    # persist() expresses paths relative to the anchor (get_base_dir().parent);
    # in fixture mode get_base_dir() == fixture_dir, so the anchor is its parent.
    plan_context.plan_dir_for(plan_id)  # ensure the plan dir exists
    base = plan_context.fixture_dir.parent
    for rel in log_files:
        assert (base / rel).is_file(), f'expected raw log on disk: {rel}'
    for rel in filtered_files:
        assert (base / rel).is_file(), f'expected filtered log on disk: {rel}'


def test_enrich_degrades_when_plan_id_absent():
    """plan_id=None makes the hook a no-op enrichment — empty path fields, no raise."""
    entries = [_failing_check('verify / verify', '101')]

    def fetcher(run_id: str, job_id: str = '') -> str:  # pragma: no cover - must not be called
        raise AssertionError('fetcher must not run when plan_id is None')

    result = enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=None,
    )
    assert result is entries
    assert entries[0]['log_file'] == ''
    assert entries[0]['filtered_log_file'] == ''


def test_enrich_degrades_per_entry_when_run_id_missing(plan_context):
    """An entry with no run_id keeps empty path fields; siblings still enriched."""
    plan_id = 'enrich-missing-run-id'
    good = _failing_check('verify / verify', '900')
    bad = _failing_check('build (3.12)', '')  # empty run_id
    entries = [good, bad]

    def fetcher(run_id: str, job_id: str = '') -> str:
        return f'ERROR boom {run_id}\n'

    enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
    )
    # The healthy entry was enriched.
    assert good['log_file']
    assert good['filtered_log_file']
    # The run_id-less entry degraded to empty path fields — never raised.
    assert bad['log_file'] == ''
    assert bad['filtered_log_file'] == ''


def test_enrich_degrades_per_entry_when_fetch_fails(plan_context):
    """A fetch failure on one entry must not abort enrichment of the others, nor raise."""
    plan_id = 'enrich-fetch-fails'
    first = _failing_check('verify / verify', '601')
    second = _failing_check('build (3.12)', '602')
    entries = [first, second]

    def fetcher(run_id: str, job_id: str = '') -> str:
        if run_id == '601':
            raise RuntimeError('network down')
        return f'ERROR ok {run_id}\n'

    # Must not raise despite the per-entry fetch failure.
    enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
    )
    # The failing-fetch entry degraded to empty path fields.
    assert first['log_file'] == ''
    assert first['filtered_log_file'] == ''
    # The healthy entry was still enriched.
    assert second['log_file']
    assert second['filtered_log_file']


def test_enrich_degrades_per_entry_when_fetch_returns_none(plan_context):
    """A fetcher returning None for an entry leaves that entry's path fields empty."""
    plan_id = 'enrich-fetch-none'
    first = _failing_check('verify / verify', '701')
    second = _failing_check('build (3.12)', '702')
    entries = [first, second]

    def fetcher(run_id: str, job_id: str = '') -> str | None:
        if run_id == '701':
            return None
        return f'ERROR ok {run_id}\n'

    enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
    )
    assert first['log_file'] == ''
    assert first['filtered_log_file'] == ''
    assert second['log_file']
    assert second['filtered_log_file']


def test_enrich_records_error_style_on_each_entry(plan_context):
    """The chosen error_style is stamped onto every entry (default generic)."""
    plan_id = 'enrich-error-style'
    entries = [_failing_check('verify / verify', '111')]

    def fetcher(run_id: str, job_id: str = '') -> str:
        return f'ERROR boom {run_id}\n'

    enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
        error_style='maven',
    )
    assert entries[0]['error_style'] == 'maven'


def test_enrich_passes_job_id_to_fetcher(plan_context):
    """The entry's job_id is forwarded as the fetcher's second positional arg.

    Reusable-workflow callers populate ``job_id`` on the failing-check entry;
    the shared hook must thread it through to ``raw_log_fetcher`` so the
    GitHub fetcher can target the nested called job.
    """
    plan_id = 'enrich-job-id-forward'
    entry = _failing_check('verify / verify', '321')
    entry['job_id'] = '654'
    entries = [entry]

    captured: list[tuple[str, str]] = []

    def fetcher(run_id: str, job_id: str = '') -> str:
        captured.append((run_id, job_id))
        return f'ERROR boom {run_id}\n'

    enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
    )

    assert captured == [('321', '654')]


def test_enrich_passes_empty_job_id_when_absent(plan_context):
    """When the entry carries no job_id, the fetcher receives an empty string."""
    plan_id = 'enrich-job-id-absent'
    entries = [_failing_check('build (3.12)', '322')]  # no job_id key

    captured: list[tuple[str, str]] = []

    def fetcher(run_id: str, job_id: str = '') -> str:
        captured.append((run_id, job_id))
        return f'ERROR boom {run_id}\n'

    enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='github',
        raw_log_fetcher=fetcher,
        plan_id=plan_id,
    )

    assert captured == [('322', '')]
