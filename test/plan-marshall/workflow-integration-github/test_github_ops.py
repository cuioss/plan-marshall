#!/usr/bin/env python3
"""Tests for github_ops.py --head flag routing.

Verifies that branch-aware operations forward the --head value to gh and that
the --pr-number/--head dual-flag validation works as expected.
"""

import argparse

import github_ops  # type: ignore[import-not-found]


def _ok_auth():
    return True, ''


def _capture_run_gh():
    """Return a (run_gh_stub, captured_args_list) pair."""
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        # Provide a minimal valid response per operation.
        if args[:2] == ['pr', 'create']:
            return 0, 'https://github.com/octo/repo/pull/42', ''
        if args[:2] == ['pr', 'view']:
            return 0, '{"number": 42, "url": "https://github.com/octo/repo/pull/42", "state": "OPEN"}', ''
        if args[:2] == ['pr', 'merge']:
            return 0, '', ''
        if args[:2] == ['pr', 'checks']:
            return 0, '[]', ''
        if args[:2] == ['pr', 'update-branch']:
            return 0, '', ''
        return 0, '', ''

    return run_gh_stub, captured


# =============================================================================
# pr_create --head
# =============================================================================


def _prepare_pr_create_body(tmp_path, monkeypatch, body_text='B', plan_id='p'):
    """Seed PLAN_BASE_DIR with a prepared pr-create body scratch file."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    from ci_base import BODY_KIND_PR_CREATE, get_body_path  # type: ignore[import-not-found]

    path = get_body_path(plan_id, BODY_KIND_PR_CREATE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body_text, encoding='utf-8')
    return plan_id


def test_pr_create_forwards_head_flag(monkeypatch, tmp_path):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    plan_id = _prepare_pr_create_body(tmp_path, monkeypatch)
    ns = argparse.Namespace(title='T', plan_id=plan_id, slot=None, base=None, draft=False, head='feature/x')
    result = github_ops.cmd_pr_create(ns)

    assert result['status'] == 'success', result
    assert any('--head' in c and 'feature/x' in c for c in captured), captured


def test_pr_create_omits_head_when_unset(monkeypatch, tmp_path):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    plan_id = _prepare_pr_create_body(tmp_path, monkeypatch)
    ns = argparse.Namespace(title='T', plan_id=plan_id, slot=None, base=None, draft=False, head=None)
    result = github_ops.cmd_pr_create(ns)

    assert result['status'] == 'success', result
    assert not any('--head' in c for c in captured), captured


# =============================================================================
# pr_view --head
# =============================================================================


def test_pr_view_forwards_head_as_positional(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(head='feature/x')
    result = github_ops.cmd_pr_view(ns)

    assert result['status'] == 'success', result
    pr_view_call = next(c for c in captured if c[:2] == ['pr', 'view'])
    assert 'feature/x' in pr_view_call, pr_view_call


# =============================================================================
# pr_merge --head / --pr-number
# =============================================================================


def test_pr_merge_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x', strategy='merge', delete_branch=False)
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'success', result
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert merge_call[2] == 'feature/x'


def test_pr_merge_with_pr_number(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head=None, strategy='merge', delete_branch=False)
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'success', result
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert merge_call[2] == '42'


def test_pr_merge_dual_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x', strategy='merge', delete_branch=False)
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']
    assert captured == [], 'Should not invoke gh when validation fails'


def test_pr_merge_neither_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head=None, strategy='merge', delete_branch=False)
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'error'
    assert 'either' in result['error']


# =============================================================================
# pr_auto_merge --head
# =============================================================================


def test_pr_auto_merge_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x', strategy='merge')
    result = github_ops.cmd_pr_auto_merge(ns)

    assert result['status'] == 'success', result
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert merge_call[2] == 'feature/x'
    assert '--auto' in merge_call


def test_pr_auto_merge_dual_flag_rejected(monkeypatch):
    run_gh_stub, _ = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x', strategy='merge')
    result = github_ops.cmd_pr_auto_merge(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']


# =============================================================================
# pr_update_branch --head / --pr-number
# =============================================================================


def test_pr_update_branch_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x')
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'success', result
    update_call = next(c for c in captured if c[:2] == ['pr', 'update-branch'])
    assert update_call[2] == 'feature/x'


def test_pr_update_branch_with_pr_number(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'success', result
    update_call = next(c for c in captured if c[:2] == ['pr', 'update-branch'])
    assert update_call[2] == '42'


def test_pr_update_branch_dual_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x')
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']
    assert captured == [], 'Should not invoke gh when validation fails'


def test_pr_update_branch_neither_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'either' in result['error']


def test_pr_update_branch_gh_failure(monkeypatch):
    """When gh returns non-zero, the handler should return an error result."""

    def failing_run_gh(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'update-branch']:
            return 1, '', 'merge conflict'
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', failing_run_gh)

    ns = argparse.Namespace(pr_number=42, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'Failed to update branch' in result['error']


def test_pr_update_branch_auth_failure(monkeypatch):
    """When auth fails, the handler should return an error result."""
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'not logged in'))
    monkeypatch.setattr(github_ops, 'run_gh', _capture_run_gh()[0])

    ns = argparse.Namespace(pr_number=42, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'not logged in' in result['error']


# =============================================================================
# ci_status --head
# =============================================================================


def test_ci_status_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x')
    result = github_ops.cmd_ci_status(ns)

    assert result['status'] == 'success', result
    checks_call = next(c for c in captured if c[:2] == ['pr', 'checks'])
    assert checks_call[2] == 'feature/x'


def test_ci_status_dual_flag_rejected(monkeypatch):
    run_gh_stub, _ = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x')
    result = github_ops.cmd_ci_status(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']


# =============================================================================
# pr wait-for-comments (poll-instead-of-sleep replacement)
# =============================================================================


def _wait_for_comments_args(timeout=2, interval=1):
    return argparse.Namespace(pr_number=42, timeout=timeout, interval=interval)


def test_pr_wait_for_comments_returns_when_new_comment_arrives(monkeypatch):
    """Happy path: baseline=1, second poll sees count=2 → returns timed_out: false, new_count: 1."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)

    call_counts = {'fetch': 0}

    def fake_fetch(pr_number, unresolved_only=False):
        assert pr_number == 42
        assert unresolved_only is True
        call_counts['fetch'] += 1
        # First call (baseline) returns 1; subsequent calls return 2 (new comment arrived)
        unresolved = 1 if call_counts['fetch'] == 1 else 2
        return {'status': 'success', 'unresolved': unresolved, 'comments': []}

    monkeypatch.setattr(github_ops, 'fetch_pr_comments_data', fake_fetch)

    result = github_ops.cmd_pr_wait_for_comments(_wait_for_comments_args())

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_wait_for_comments'
    assert result['pr_number'] == 42
    assert result['timed_out'] is False
    assert result['baseline_count'] == 1
    assert result['final_count'] == 2
    assert result['new_count'] == 1
    assert result['polls'] >= 1
    # baseline + at least one poll
    assert call_counts['fetch'] >= 2


def test_pr_wait_for_comments_times_out_when_no_new_comments(monkeypatch):
    """Timeout path: count never grows above baseline → returns timed_out: true, new_count: 0."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)

    def fake_fetch(pr_number, unresolved_only=False):
        return {'status': 'success', 'unresolved': 5, 'comments': []}

    monkeypatch.setattr(github_ops, 'fetch_pr_comments_data', fake_fetch)

    result = github_ops.cmd_pr_wait_for_comments(_wait_for_comments_args(timeout=1, interval=1))

    assert result['status'] == 'success', result
    assert result['operation'] == 'pr_wait_for_comments'
    assert result['timed_out'] is True
    assert result['baseline_count'] == 5
    assert result['final_count'] == 5
    assert result['new_count'] == 0


def test_pr_wait_for_comments_returns_error_when_initial_fetch_fails(monkeypatch):
    """Error path: baseline fetch fails → returns status: error before polling starts."""
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)

    def failing_fetch(pr_number, unresolved_only=False):
        return {'status': 'error', 'error': 'GraphQL query failed: boom'}

    monkeypatch.setattr(github_ops, 'fetch_pr_comments_data', failing_fetch)

    result = github_ops.cmd_pr_wait_for_comments(_wait_for_comments_args())

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_wait_for_comments'
    assert 'Initial unresolved-comment fetch failed' in result['error']


def test_pr_wait_for_comments_returns_error_when_auth_fails(monkeypatch):
    """Auth failure short-circuits before any fetch."""
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'not logged in'))

    fetch_calls = {'count': 0}

    def fake_fetch(pr_number, unresolved_only=False):
        fetch_calls['count'] += 1
        return {'status': 'success', 'unresolved': 0, 'comments': []}

    monkeypatch.setattr(github_ops, 'fetch_pr_comments_data', fake_fetch)

    result = github_ops.cmd_pr_wait_for_comments(_wait_for_comments_args())

    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_wait_for_comments'
    assert 'not logged in' in result['error']
    assert fetch_calls['count'] == 0, 'fetch should not be called when auth fails'


# =============================================================================
# --project-dir pre-parse plumbing (cwd forwarding)
# =============================================================================


def test_main_project_dir_sets_default_cwd(tmp_path, monkeypatch, capsys):
    """github_ops.main() strips --project-dir from argv and installs it as the
    process-global default cwd used by ci_base.run_cli."""
    import sys

    import ci_base  # type: ignore[import-not-found]

    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setattr(ci_base, '_DEFAULT_CWD', None, raising=False)

    worktree = str(tmp_path / 'worktree')
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'github_ops.py',
            '--project-dir',
            worktree,
            'pr',
            'prepare-body',
            '--plan-id',
            'test-plan',
        ],
    )

    rc = github_ops.main()
    assert rc == 0
    # Default cwd was installed before argparse ran.
    assert ci_base.get_default_cwd() == worktree
    # argv was stripped so argparse never saw --project-dir.
    assert '--project-dir' not in sys.argv
    # prepare-body emitted a success TOON payload.
    out = capsys.readouterr().out
    assert 'status' in out and 'success' in out


def test_main_project_dir_equals_form(tmp_path, monkeypatch, capsys):
    """The --project-dir=PATH form is also honoured by github_ops.main()."""
    import sys

    import ci_base  # type: ignore[import-not-found]

    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setattr(ci_base, '_DEFAULT_CWD', None, raising=False)

    worktree = str(tmp_path / 'wt2')
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'github_ops.py',
            f'--project-dir={worktree}',
            'pr',
            'prepare-body',
            '--plan-id',
            'eq-plan',
        ],
    )

    rc = github_ops.main()
    assert rc == 0
    assert ci_base.get_default_cwd() == worktree
    capsys.readouterr()  # drain


def test_main_without_project_dir_leaves_cwd_untouched(tmp_path, monkeypatch):
    """Omitting --project-dir must not mutate the process-global default cwd."""
    import sys

    import ci_base  # type: ignore[import-not-found]

    sentinel = str(tmp_path / 'sentinel')
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setattr(ci_base, '_DEFAULT_CWD', sentinel, raising=False)

    monkeypatch.setattr(
        sys,
        'argv',
        [
            'github_ops.py',
            'pr',
            'prepare-body',
            '--plan-id',
            'noflag',
        ],
    )

    rc = github_ops.main()
    assert rc == 0
    # Unchanged sentinel — pre-parse did not clobber an existing default.
    assert ci_base.get_default_cwd() == sentinel


# =============================================================================
# format_checks_toon — Go zero-value timestamp regression
# =============================================================================
#
# Regression for the lesson-2026-04-19-14-007 bug: a SKIPPED check with
# `0001-01-01T00:00:00Z` timestamps used to leak ~63.9-billion-second
# `elapsed_sec` values into the TOON aggregate. Contract after the fix:
#
#   (a) aggregate elapsed_sec is bounded by a 24h ceiling
#   (b) SKIPPED row (with Go zero-value timestamps) has NO `elapsed_sec` key
#   (c) other (real-timestamped) rows have non-negative integer `elapsed_sec`


_GO_ZERO_GH = '0001-01-01T00:00:00Z'


def test_format_checks_toon_skips_go_zero_timestamps():
    """Three checks: SUCCESS+real, SKIPPED+zero-time, SUCCESS+real.

    The SKIPPED check must contribute neither a row-level `elapsed_sec`
    nor any positive value to the aggregate. Aggregate must stay ≤ 24h.
    """
    # `gh pr checks --json` shape: name, state, bucket, startedAt, completedAt, link, workflow
    checks = [
        {
            'name': 'unit-tests',
            'state': 'SUCCESS',
            'bucket': 'pass',
            'startedAt': '2025-01-15T11:55:00+00:00',
            'completedAt': '2025-01-15T11:58:00+00:00',  # 180s
            'link': 'https://example.test/1',
            'workflow': 'CI',
        },
        {
            'name': 'integration-tests-skipped',
            'state': 'SKIPPED',
            'bucket': 'skipping',
            # Go zero-value emitted by gh for never-started checks.
            'startedAt': _GO_ZERO_GH,
            'completedAt': _GO_ZERO_GH,
            'link': '',
            'workflow': 'CI',
        },
        {
            'name': 'lint',
            'state': 'SUCCESS',
            'bucket': 'pass',
            'startedAt': '2025-01-15T11:50:00+00:00',
            'completedAt': '2025-01-15T11:55:00+00:00',  # 300s
            'link': 'https://example.test/2',
            'workflow': 'CI',
        },
    ]

    rows, total_elapsed = github_ops.format_checks_toon(checks)

    # (a) Aggregate is bounded by 24h ceiling (not ~63.9 billion seconds).
    assert isinstance(total_elapsed, int)
    assert 0 <= total_elapsed <= 24 * 3600, (
        f'Aggregate elapsed_sec={total_elapsed} out of [0, 86400] — '
        'Go zero-value timestamp likely poisoned the aggregate'
    )

    # Three rows preserved, in the input order.
    assert len(rows) == 3
    skipped_row = next(r for r in rows if r['status'] == 'SKIPPED')
    real_rows = [r for r in rows if r['status'] == 'SUCCESS']

    # (b) SKIPPED row has NO elapsed_sec key — TOON treats absent as null.
    assert 'elapsed_sec' not in skipped_row, f'SKIPPED row must omit elapsed_sec; got {skipped_row!r}'

    # (c) Real-timestamped rows expose non-negative integer elapsed_sec.
    assert len(real_rows) == 2
    for r in real_rows:
        assert 'elapsed_sec' in r, f'Real row missing elapsed_sec: {r!r}'
        assert isinstance(r['elapsed_sec'], int)
        assert r['elapsed_sec'] >= 0, f'Real row elapsed_sec must be non-negative; got {r!r}'


def test_format_checks_toon_clamps_runaway_aggregate(monkeypatch, capsys):
    """Defense-in-depth: if compute_total_elapsed somehow returns a runaway
    value, format_checks_toon clamps to the caller-supplied ceiling and warns.

    We patch compute_total_elapsed to simulate the exact pre-fix bug
    (63.9 billion seconds) and verify the clamp engages.
    """
    import ci_base  # type: ignore[import-not-found]

    # Simulate the pre-fix bug: compute_total_elapsed returns runaway value.
    monkeypatch.setattr(github_ops, 'compute_total_elapsed', lambda values, now: 63_870_000_000)

    checks = [
        {
            'name': 'unit-tests',
            'state': 'SUCCESS',
            'bucket': 'pass',
            'startedAt': '2025-01-15T11:55:00+00:00',
            'completedAt': '2025-01-15T11:58:00+00:00',
            'link': 'https://example.test/1',
            'workflow': 'CI',
        },
    ]

    # ci_status path: duration_ceiling=0 → clamp substitutes 0.
    rows, total_elapsed = github_ops.format_checks_toon(checks, duration_ceiling=0)
    assert total_elapsed == 0, f'Expected runaway aggregate to clamp to 0, got {total_elapsed}'
    captured = capsys.readouterr()
    assert 'out of range' in captured.err, 'Expected stderr warning when clamp engages'

    # ci_wait path: duration_ceiling=42 → clamp substitutes 42.
    _, total_elapsed_wait = github_ops.format_checks_toon(checks, duration_ceiling=42)
    assert total_elapsed_wait == 42

    # Ensure ci_base import survives the patching (sanity).
    assert ci_base is not None
