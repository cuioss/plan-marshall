#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Primitives cluster — constants, elapsed computation, truncation, poll_until."""


import argparse
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import ci_base
import pytest
from _merge_shaped_roster import PROVIDERS, registry_keys
from _resolve_project_dir_fixtures import worktree_query_result
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
    normalize_issue_ref,
    poll_until,
    prepare_body,
    read_and_consume_body,
    register_subcommands,
    run_cli,
    set_default_cwd,
    truncate_log_content,
)

from conftest import PROJECT_ROOT

# =============================================================================
# Shared constants tests
# =============================================================================


def _option_strings(parser: argparse.ArgumentParser) -> set[str]:
    """Return every option string declared directly on *parser*."""
    return {opt for action in parser._actions for opt in action.option_strings}


def _parser_paths(parser: argparse.ArgumentParser, prefix: tuple[str, ...] = ()) -> dict[int, str]:
    """Map ``id(sub_parser)`` -> its space-joined command path, for every node under *parser*."""
    paths: dict[int, str] = {}
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, sub in action.choices.items():
                path = (*prefix, name)
                paths[id(sub)] = ' '.join(path)
                paths.update(_parser_paths(sub, path))
    return paths


@pytest.fixture
def plan_base_env(tmp_path, monkeypatch):
    """Point PLAN_BASE_DIR at a temporary directory so get_plan_dir is sandboxed.

    Also seeds an initialized plan directory for the conventional ``my-plan``
    plan_id used by the body-store happy-path tests. The
    ``ci_base.prepare_body`` script-side guard requires the plan dir to contain a ``status.json`` sentinel before any
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


def _documented_checks_verbs() -> set[str]:
    """Return the ``checks`` sub-verbs the leaf-command reference documents.

    Raises:
        AssertionError: if the reference yielded no row at all. An empty derivation
            is the vacuity this guard exists to catch — the equality assertion that
            consumes it would otherwise compare the live parser against an empty
            set and fail for the wrong reason, or (had it been a subset check) pass
            over nothing.
    """
    text = _LEAF_COMMAND_REFERENCE.read_text(encoding='utf-8')
    verbs = {match.group('verb') for match in _CHECKS_ROW.finditer(text)}
    assert verbs, (
        f'no `checks {{verb}}` table row was derived from {_LEAF_COMMAND_REFERENCE} — '
        f'the documented population is vacuous, so it cannot pin the live parser'
    )
    return verbs


def _registered_pr_verbs() -> set[str]:
    """Return every ``pr`` sub-verb some CI provider registers.

    Derived from the providers' ``handlers: HandlerMap`` registry literals — the
    closed population — never from a ``def cmd_pr_`` scan, which is a sample.

    Raises:
        AssertionError: if no ``('pr', verb)`` key was derived at all. An empty
            derivation is the vacuity every guard below would otherwise pass over.
    """
    verbs = {
        key[1]
        for text in _PROVIDER_OPS_TEXT.values()
        for key in registry_keys(text)
        if len(key) == 2 and key[0] == 'pr'
    }
    assert verbs, (
        f'no ("pr", verb) registry key was derived from {sorted(_PROVIDER_OPS_TEXT)} — '
        f'the registered population is vacuous, so it cannot pin any documentation'
    )
    return verbs


def _documented_pr_verbs(document: Path) -> set[str]:
    """Return the ``pr`` sub-verbs ``document`` carries a table row for.

    Raises:
        AssertionError: if the document yielded no row at all — the same vacuity
            guard ``_documented_checks_verbs`` applies, for the same reason.
    """
    verbs = {match.group('verb') for match in _PR_ROW.finditer(document.read_text(encoding='utf-8'))}
    assert verbs, (
        f'no `pr {{verb}}` table row was derived from {document} — the documented '
        f'population is vacuous, so it cannot pin the registered verb set'
    )
    return verbs


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


def _mq_wait_ns(*, adaptive: bool, timeout):
    """Build the minimal namespace ``_run_checks_wait`` reads (adaptive, timeout)."""
    return argparse.Namespace(adaptive=adaptive, timeout=timeout)


#: The independent authority the registered ``checks`` verb set is pinned against.
#: Its own preamble declares each group table a COMPLETE index of that group's
#: registered sub-verbs, which is what makes an equality comparison against it
#: meaningful rather than merely conventional.
_LEAF_COMMAND_REFERENCE = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'tools-integration-ci'
    / 'standards'
    / 'leaf-command-reference.md'
)


#: A ``checks {verb}`` row of that reference's group table: the backticked command
#: opening a table row's leading cell. Anchored at the line start and requiring the
#: leading pipe, so a ``ci checks status`` shown inside a fenced example is prose
#: and never joins the documented population.
_CHECKS_ROW = re.compile(r'^\|\s*`checks (?P<verb>[a-z][a-z0-9-]*)`\s*\|', re.MULTILINE)


#: The response-shape authority. Its ``pr`` rows are spread over TWO tables — the
#: read-verb table under "PR Operations" and the "State-Transition Operations
#: (summary)" table — so the derivation reads the whole document and a row in
#: EITHER satisfies the guard. Resolved as a sibling of the leaf-command reference
#: rather than by re-typing the path chain above it.
_API_CONTRACT = _LEAF_COMMAND_REFERENCE.parent / 'api-contract.md'


#: ``marketplace/bundles/plan-marshall/skills`` — the leaf-command reference sits at
#: ``{skills}/tools-integration-ci/standards/leaf-command-reference.md``, so three
#: levels up is the skills root the provider modules also hang off.
_BUNDLE_SKILLS = _LEAF_COMMAND_REFERENCE.parents[2]


#: Each provider's ``*_ops.py`` source text, keyed by the provider set the shared
#: roster declares — iterated rather than re-typed, so a third provider joins this
#: guard by being added there.
_PROVIDER_OPS_TEXT: dict[str, str] = {
    provider: (_BUNDLE_SKILLS / f'workflow-integration-{provider}' / 'scripts' / f'{provider}_ops.py').read_text(
        encoding='utf-8'
    )
    for provider in PROVIDERS
}


#: A ``pr {verb}`` documentation row in either reference. The verb is the backticked
#: command's second word; the remainder of the leading cell is skipped (``[^|]*``)
#: because a row legitimately carries more there — an inline argument
#: (``pr close --pr-number N``) or a provider annotation (``**(GitHub only)**``).
#: Anchored at the line start and requiring the leading pipe AND the backtick, so a
#: ``ci pr merge`` shown in an anti-pattern table or a fenced example is prose and
#: never joins the documented population.
_PR_ROW = re.compile(r'^\|\s*`pr (?P<verb>[a-z][a-z0-9-]*)[^|]*\|', re.MULTILINE)


#: Registered ``pr`` verbs deliberately absent from ``api-contract.md``, each mapped
#: to the reason it is exempt. An exemption is a recorded decision rather than a
#: silence, and it is kept honest from both directions by
#: ``test_api_contract_pr_exemptions_are_live`` below: an entry naming a verb that is
#: no longer registered, or one that HAS since gained its row, fails rather than
#: quietly widening the allowance.
_API_CONTRACT_PR_EXEMPT: dict[str, str] = {
    'submit-review': (
        'api-contract.md documents response SHAPES, and this verb adds none — it '
        'publishes a pending draft review and returns the standard envelope with no '
        'extra response field. Its argument surface is documented in '
        'leaf-command-reference.md (which this guard pins by equality) and its '
        'GitLab-side refusal in that provider impl doc.'
    ),
}


def test_default_constants():
    """Shared constants should have expected values.

    ``DEFAULT_CI_TIMEOUT`` is resolved from marshal.json at module load via
    ``_resolve_ci_timeout``. The 600s value is the
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
# compute_total_elapsed — naive/aware timezone mismatch
# =============================================================================
#
# The per-entry `datetime.fromisoformat` parse was guarded by a try that caught
# (ValueError, TypeError), but the FINAL `now - earliest` subtraction sat
# OUTSIDE it. Python raises TypeError ("can't subtract offset-naive and
# offset-aware datetimes") when the two operands disagree on tz-awareness, so a
# successfully-parsed-but-naive timestamp against an aware `now` (or the mirror)
# escaped the guard and crashed the caller outright — a hard failure, not a
# wrong number. `compute_elapsed` has always kept the same arithmetic inside its
# try; these cases pin the parity.
#
# Both directions are asserted because they are NOT the same code path in
# CPython: the operand that carries the tzinfo differs, and a guard placed on
# only one side would leave the other reachable.


@pytest.mark.parametrize(
    'started_at,now',
    [
        # Aware timestamp, naive now.
        ('2025-01-15T11:55:00+00:00', datetime(2025, 1, 15, 12, 0, 0)),
        # Naive timestamp, aware now (the mirrored pairing).
        ('2025-01-15T11:55:00', datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)),
    ],
    ids=['aware_start_naive_now', 'naive_start_aware_now'],
)

def test_compute_total_elapsed_timezone_mismatch_returns_zero(started_at, now):
    """A naive/aware mismatch returns the documented 0 instead of raising."""
    result = compute_total_elapsed([started_at], now)

    assert result == 0


@pytest.mark.parametrize(
    'started_at,now',
    [
        # Both aware.
        ('2025-01-15T11:55:00+00:00', datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)),
        # Both naive.
        ('2025-01-15T11:55:00', datetime(2025, 1, 15, 12, 0, 0)),
    ],
    ids=['both_aware', 'both_naive'],
)

def test_compute_total_elapsed_matching_awareness_still_computes(started_at, now):
    """Negative control: a consistent pairing still returns the real delta.

    Without this, an implementation that simply returned 0 unconditionally —
    or that swallowed every exception around the subtraction — would satisfy
    the mismatch cases above while silently zeroing every legitimate aggregate.
    """
    result = compute_total_elapsed([started_at], now)

    assert result == 300


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


