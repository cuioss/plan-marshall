#!/usr/bin/env python3
"""
Tests for ci_base.py shared utilities.

Tests functions:
- compute_elapsed: Elapsed time computation from ISO timestamps
- compute_total_elapsed: Total elapsed from earliest start
- truncate_log_content: Log truncation and escaping
- poll_until: Generic polling framework
"""

from datetime import UTC, datetime, timedelta

import argparse

from ci_base import (
    CI_LOG_TRUNCATE_LINES,
    DEFAULT_CI_INTERVAL,
    DEFAULT_CI_TIMEOUT,
    add_head_arg,
    add_pr_create_args,
    build_parser,
    compute_elapsed,
    compute_total_elapsed,
    poll_until,
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

    args = parser.parse_args(['create', '--title', 'T', '--head', 'feature/x'])
    assert args.head == 'feature/x'

    # Still optional — works without --head
    args = parser.parse_args(['create', '--title', 'T'])
    assert args.head is None


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
