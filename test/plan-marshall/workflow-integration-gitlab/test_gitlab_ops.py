#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for gitlab_ops.py --head flag routing.

Verifies that branch-aware operations forward the --head value to glab and that
the --pr-number/--head dual-flag validation works as expected. Branch->IID lookup
is exercised via a stubbed ``glab mr list``.
"""

import argparse

import gitlab_ops
from _ci_wait_contract import _ok_auth


def _capture_run_glab(*, mr_list_iid: int = 7):
    """Return a (run_glab_stub, captured_args_list) pair.

    ``mr_list_iid`` controls what the ``glab mr list --source-branch ...`` lookup returns.
    Set to ``None`` to simulate a zero-match result.
    """
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        if args[:3] == ['mr', 'list', '--source-branch']:
            if mr_list_iid is None:
                return 0, '[]', ''
            return 0, f'[{{"iid": {mr_list_iid}, "title": "T"}}]', ''
        if args[:2] == ['mr', 'create']:
            return 0, 'https://gitlab.com/octo/repo/-/merge_requests/42', ''
        if args[:2] == ['mr', 'view']:
            return 0, '{"iid": 7, "state": "opened", "title": "T", "pipeline": {"id": 99, "status": "success"}}', ''
        if args[:2] == ['mr', 'merge']:
            return 0, '', ''
        if args[:2] == ['ci', 'view']:
            return 0, '{"jobs": []}', ''
        return 0, '', ''

    return run_glab_stub, captured


# =============================================================================
# pr_create --head -> --source-branch
# =============================================================================


def _prepare_pr_create_body(tmp_path, monkeypatch, body_text='B', plan_id='p'):
    """Seed PLAN_BASE_DIR with a prepared pr-create body scratch file."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    from ci_base import BODY_KIND_PR_CREATE, get_body_path

    path = get_body_path(plan_id, BODY_KIND_PR_CREATE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body_text, encoding='utf-8')
    return plan_id


def test_pr_create_forwards_head_as_source_branch(monkeypatch, tmp_path):
    run_glab_stub, captured = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    plan_id = _prepare_pr_create_body(tmp_path, monkeypatch)
    ns = argparse.Namespace(title='T', plan_id=plan_id, slot=None, base=None, draft=False, head='feature/x')
    result = gitlab_ops.cmd_pr_create(ns)

    assert result['status'] == 'success', result
    create_call = next(c for c in captured if c[:2] == ['mr', 'create'])
    assert '--source-branch' in create_call
    assert 'feature/x' in create_call


def test_pr_create_omits_source_branch_when_head_unset(monkeypatch, tmp_path):
    run_glab_stub, captured = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    plan_id = _prepare_pr_create_body(tmp_path, monkeypatch)
    ns = argparse.Namespace(title='T', plan_id=plan_id, slot=None, base=None, draft=False, head=None)
    result = gitlab_ops.cmd_pr_create(ns)

    assert result['status'] == 'success', result
    create_call = next(c for c in captured if c[:2] == ['mr', 'create'])
    assert '--source-branch' not in create_call


# =============================================================================
# pr_view --head
# =============================================================================


def test_pr_view_forwards_head(monkeypatch):
    run_glab_stub, captured = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(head='feature/x')
    result = gitlab_ops.cmd_pr_view(ns)

    assert result['status'] == 'success', result
    view_call = next(c for c in captured if c[:2] == ['mr', 'view'])
    assert 'feature/x' in view_call


# =============================================================================
# pr_merge --head -> branch->IID lookup
# =============================================================================


def test_pr_merge_with_head_resolves_iid(monkeypatch):
    run_glab_stub, captured = _capture_run_glab(mr_list_iid=7)
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x', strategy='merge', delete_branch=False)
    result = gitlab_ops.cmd_pr_merge(ns)

    assert result['status'] == 'success', result
    list_call = next(c for c in captured if c[:3] == ['mr', 'list', '--source-branch'])
    assert 'feature/x' in list_call
    merge_call = next(c for c in captured if c[:2] == ['mr', 'merge'])
    assert merge_call[2] == '7'


def test_pr_merge_with_pr_number_skips_lookup(monkeypatch):
    run_glab_stub, captured = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=42, head=None, strategy='merge', delete_branch=False)
    result = gitlab_ops.cmd_pr_merge(ns)

    assert result['status'] == 'success', result
    assert not any(c[:3] == ['mr', 'list', '--source-branch'] for c in captured)
    merge_call = next(c for c in captured if c[:2] == ['mr', 'merge'])
    assert merge_call[2] == '42'


def test_pr_merge_dual_flag_rejected(monkeypatch):
    run_glab_stub, captured = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x', strategy='merge', delete_branch=False)
    result = gitlab_ops.cmd_pr_merge(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']
    assert captured == [], 'Should not invoke glab when validation fails'


def test_pr_merge_zero_match_rejected(monkeypatch):
    run_glab_stub, captured = _capture_run_glab(mr_list_iid=None)
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x', strategy='merge', delete_branch=False)
    result = gitlab_ops.cmd_pr_merge(ns)

    assert result['status'] == 'error'
    assert 'no MR found' in result['error']


# =============================================================================
# pr_auto_merge --head
# =============================================================================


def test_pr_auto_merge_with_head_resolves_iid(monkeypatch):
    run_glab_stub, captured = _capture_run_glab(mr_list_iid=7)
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x', strategy='merge')
    result = gitlab_ops.cmd_pr_auto_merge(ns)

    assert result['status'] == 'success', result
    merge_call = next(c for c in captured if c[:2] == ['mr', 'merge'])
    assert merge_call[2] == '7'
    assert '--when-pipeline-succeeds' in merge_call


def test_pr_auto_merge_dual_flag_rejected(monkeypatch):
    run_glab_stub, _ = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x', strategy='merge')
    result = gitlab_ops.cmd_pr_auto_merge(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']


# =============================================================================
# ci_status --head
# =============================================================================


def test_ci_status_with_head_resolves_iid(monkeypatch):
    run_glab_stub, captured = _capture_run_glab(mr_list_iid=7)
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x')
    result = gitlab_ops.cmd_ci_status(ns)

    assert result['status'] == 'success', result
    list_call = next(c for c in captured if c[:3] == ['mr', 'list', '--source-branch'])
    assert 'feature/x' in list_call
    view_call = next(c for c in captured if c[:2] == ['mr', 'view'])
    assert view_call[2] == '7'


def test_ci_status_dual_flag_rejected(monkeypatch):
    run_glab_stub, _ = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x')
    result = gitlab_ops.cmd_ci_status(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']


# =============================================================================
# --project-dir pre-parse plumbing (cwd forwarding)
# =============================================================================


def test_main_project_dir_sets_default_cwd(tmp_path, monkeypatch, capsys):
    """gitlab_ops.main() strips --project-dir from argv and installs it as the
    process-global default cwd used by ci_base.run_cli.

    Uses ``pr view`` (no subcommand-level --plan-id) with a mocked glab response
    so the test does not require a live GitLab token.

    Fix A (secondary guard): ``--plan-id`` must appear before the subcommand
    token, not after. ``--project-dir`` may still appear before the subcommand
    as the explicit-path escape hatch.
    """
    import sys

    import ci_base

    monkeypatch.setattr(ci_base, '_DEFAULT_CWD', None, raising=False)

    # Mock run_glab so pr view returns minimal success JSON without needing
    # a live glab token or repository.
    monkeypatch.setattr(
        gitlab_ops,
        'run_glab',
        lambda args: (0, '{"iid": 1, "state": "opened", "title": "T", "pipeline": null}', ''),
    )
    monkeypatch.setattr(gitlab_ops, 'check_auth', lambda: (True, ''))

    worktree = str(tmp_path / 'worktree')
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'gitlab_ops.py',
            '--project-dir',
            worktree,
            'pr',
            'view',
        ],
    )

    rc = gitlab_ops.main()
    assert rc == 0
    assert ci_base.get_default_cwd() == worktree
    assert '--project-dir' not in sys.argv
    capsys.readouterr()  # drain


def test_main_project_dir_equals_form(tmp_path, monkeypatch, capsys):
    """The --project-dir=PATH form is also honoured by gitlab_ops.main().

    Uses ``pr view`` (no subcommand-level --plan-id) with a mocked glab response
    so the test does not require a live GitLab token.

    Fix A (secondary guard): ``--plan-id`` must appear before the subcommand
    token. ``--project-dir=PATH`` (equals form) before the subcommand is the
    explicit-path escape hatch and must still work.
    """
    import sys

    import ci_base

    monkeypatch.setattr(ci_base, '_DEFAULT_CWD', None, raising=False)

    # Mock run_glab so pr view returns minimal success JSON without needing
    # a live glab token or repository.
    monkeypatch.setattr(
        gitlab_ops,
        'run_glab',
        lambda args: (0, '{"iid": 1, "state": "opened", "title": "T", "pipeline": null}', ''),
    )
    monkeypatch.setattr(gitlab_ops, 'check_auth', lambda: (True, ''))

    worktree = str(tmp_path / 'wt2')
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'gitlab_ops.py',
            f'--project-dir={worktree}',
            'pr',
            'view',
        ],
    )

    rc = gitlab_ops.main()
    assert rc == 0
    assert ci_base.get_default_cwd() == worktree
    capsys.readouterr()


def test_ci_logs_honours_default_cwd(monkeypatch):
    """gitlab_ops.cmd_ci_logs uses subprocess.run directly (120s timeout) and
    must forward the process-global default cwd installed via --project-dir."""
    import ci_base

    captured: dict = {}

    class _FakeResult:
        returncode = 0
        stdout = 'log line\n'
        stderr = ''

    def fake_run(cmd, **kwargs):
        captured['cmd'] = list(cmd)
        captured['cwd'] = kwargs.get('cwd')
        captured['timeout'] = kwargs.get('timeout')
        return _FakeResult()

    saved_cwd = ci_base.get_default_cwd()
    try:
        ci_base.set_default_cwd('/tmp/ci-logs-worktree')
        monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
        monkeypatch.setattr(gitlab_ops.subprocess, 'run', fake_run)

        ns = argparse.Namespace(run_id='job-123')
        result = gitlab_ops.cmd_ci_logs(ns)
    finally:
        ci_base.set_default_cwd(saved_cwd)

    assert result['status'] == 'success', result
    assert captured['cmd'] == ['glab', 'ci', 'trace', 'job-123']
    assert captured['cwd'] == '/tmp/ci-logs-worktree'
    # Preserves the 120s override, not the default 60s from run_cli.
    assert captured['timeout'] == 120


def test_ci_logs_without_default_cwd_passes_none(monkeypatch):
    """When --project-dir was not supplied, ci_logs falls through with cwd=None
    so subprocess.run inherits the Python process cwd."""
    import ci_base

    captured: dict = {}

    class _FakeResult:
        returncode = 0
        stdout = ''
        stderr = ''

    def fake_run(cmd, **kwargs):
        captured['cwd'] = kwargs.get('cwd')
        return _FakeResult()

    saved_cwd = ci_base.get_default_cwd()
    try:
        ci_base.set_default_cwd(None)
        monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
        monkeypatch.setattr(gitlab_ops.subprocess, 'run', fake_run)

        ns = argparse.Namespace(run_id='job-xyz')
        gitlab_ops.cmd_ci_logs(ns)
    finally:
        ci_base.set_default_cwd(saved_cwd)

    assert captured['cwd'] is None


# =============================================================================
# format_checks_toon (jobs) — Go zero-value timestamp regression
# =============================================================================
#
# Regression for the lesson-2026-04-19-14-007 bug: a SKIPPED job with
# `0001-01-01T00:00:00Z` timestamps used to leak ~63.9-billion-second
# `elapsed_sec` values into the TOON aggregate. Contract after the fix:
#
#   (a) aggregate elapsed_sec is bounded by a 24h ceiling
#   (b) skipped row (with Go zero-value timestamps) has NO `elapsed_sec` key
#   (c) other (real-timestamped) rows have non-negative integer `elapsed_sec`


_GO_ZERO_GL = '0001-01-01T00:00:00Z'


def test_format_jobs_toon_skips_go_zero_timestamps():
    """Three jobs: success+real, skipped+zero-time, success+real.

    The skipped job must contribute neither a row-level `elapsed_sec`
    nor any positive value to the aggregate. Aggregate must stay ≤ 24h.
    """
    # `glab` job shape: name, status, started_at, created_at, finished_at, web_url, stage
    jobs = [
        {
            'name': 'unit-tests',
            'status': 'success',
            'started_at': '2025-01-15T11:55:00+00:00',
            'finished_at': '2025-01-15T11:58:00+00:00',  # 180s
            'web_url': 'https://gitlab.test/1',
            'stage': 'test',
        },
        {
            'name': 'integration-tests-skipped',
            'status': 'skipped',
            # Go zero-value emitted by glab for never-started jobs.
            'started_at': _GO_ZERO_GL,
            'created_at': _GO_ZERO_GL,
            'finished_at': _GO_ZERO_GL,
            'web_url': '',
            'stage': 'test',
        },
        {
            'name': 'lint',
            'status': 'success',
            'started_at': '2025-01-15T11:50:00+00:00',
            'finished_at': '2025-01-15T11:55:00+00:00',  # 300s
            'web_url': 'https://gitlab.test/2',
            'stage': 'lint',
        },
    ]

    rows, total_elapsed = gitlab_ops.format_checks_toon(jobs)

    # (a) Aggregate is bounded by 24h ceiling (not ~63.9 billion seconds).
    assert isinstance(total_elapsed, int)
    assert 0 <= total_elapsed <= 24 * 3600, (
        f'Aggregate elapsed_sec={total_elapsed} out of [0, 86400] — '
        'Go zero-value timestamp likely poisoned the aggregate'
    )

    # Three rows preserved, in input order.
    assert len(rows) == 3
    skipped_row = next(r for r in rows if r['result'] == 'skipped')
    real_rows = [r for r in rows if r['result'] == 'success']

    # (b) Skipped row has NO elapsed_sec key — TOON treats absent as null.
    assert 'elapsed_sec' not in skipped_row, f'Skipped row must omit elapsed_sec; got {skipped_row!r}'

    # (c) Real-timestamped rows expose non-negative integer elapsed_sec.
    assert len(real_rows) == 2
    for r in real_rows:
        assert 'elapsed_sec' in r, f'Real row missing elapsed_sec: {r!r}'
        assert isinstance(r['elapsed_sec'], int)
        assert r['elapsed_sec'] >= 0, f'Real row elapsed_sec must be non-negative; got {r!r}'


def test_format_jobs_toon_clamps_runaway_aggregate(monkeypatch, capsys):
    """Defense-in-depth: if compute_total_elapsed somehow returns a runaway
    value, format_checks_toon clamps to the caller-supplied ceiling and warns.

    We patch compute_total_elapsed to simulate the exact pre-fix bug
    (63.9 billion seconds) and verify the clamp engages.
    """
    monkeypatch.setattr(gitlab_ops, 'compute_total_elapsed', lambda values, now: 63_870_000_000)

    jobs = [
        {
            'name': 'unit-tests',
            'status': 'success',
            'started_at': '2025-01-15T11:55:00+00:00',
            'finished_at': '2025-01-15T11:58:00+00:00',
            'web_url': 'https://gitlab.test/1',
            'stage': 'test',
        },
    ]

    # ci_status path: duration_ceiling=0 → clamp substitutes 0.
    rows, total_elapsed = gitlab_ops.format_checks_toon(jobs, duration_ceiling=0)
    assert total_elapsed == 0, f'Expected runaway aggregate to clamp to 0, got {total_elapsed}'
    captured = capsys.readouterr()
    assert 'out of range' in captured.err, 'Expected stderr warning when clamp engages'

    # ci_wait path: duration_ceiling=42 → clamp substitutes 42.
    _, total_elapsed_wait = gitlab_ops.format_checks_toon(jobs, duration_ceiling=42)
    assert total_elapsed_wait == 42


# =============================================================================
# Two-state ``--plan-id`` / ``--project-dir`` routing in gitlab_ops.main()
# =============================================================================
#
# gitlab_ops.main() mirrors github_ops.main(): router-level --plan-id is
# consumed by ci_base.extract_routing_args BEFORE argparse runs, with
# the resolved cwd installed via set_default_cwd. Both flags together
# → mutually_exclusive_args TOON error + exit 2.


def test_gitlab_main_routes_plan_id_via_extract_routing_args(monkeypatch):
    """gitlab_ops.main() MUST consume router-level --plan-id and set the default cwd."""
    import resolve_project_dir as _routing
    from ci_base import get_default_cwd, set_default_cwd

    monkeypatch.setattr(_routing, '_query_worktree_path', lambda _pid: (True, '/tmp/wt-gitlab-resolved'))

    monkeypatch.setattr('sys.argv', ['gitlab_ops.py', '--plan-id', 'task-routing-canonical', '--help'])

    import pytest as _pytest

    with _pytest.raises(SystemExit):
        gitlab_ops.main()

    assert get_default_cwd() == '/tmp/wt-gitlab-resolved'
    set_default_cwd(None)


def test_gitlab_main_emits_mutually_exclusive_error_on_both_flags(monkeypatch, capsys):
    """gitlab_ops.main() with both --plan-id and --project-dir → mutually_exclusive_args."""
    monkeypatch.setattr(
        'sys.argv',
        [
            'gitlab_ops.py',
            '--plan-id',
            'task-routing-canonical',
            '--project-dir',
            '/tmp/explicit',
            'pr',
            'view',
        ],
    )
    import pytest as _pytest

    with _pytest.raises(SystemExit) as exc_info:
        gitlab_ops.main()
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert 'mutually_exclusive_args' in captured.out


def test_gitlab_main_project_dir_only_keeps_legacy_path(monkeypatch):
    """Pre-existing --project-dir-only callers must continue working."""
    from ci_base import get_default_cwd

    monkeypatch.setattr(
        'sys.argv',
        [
            'gitlab_ops.py',
            '--project-dir',
            '/tmp/wt-gitlab-explicit',
            '--help',
        ],
    )
    import pytest as _pytest

    with _pytest.raises(SystemExit):
        gitlab_ops.main()
    assert get_default_cwd() == '/tmp/wt-gitlab-explicit'


# =============================================================================
# issue comment
# =============================================================================


def _prepare_issue_comment_body(tmp_path, monkeypatch, body_text='Milestone reached', plan_id='p'):
    """Seed PLAN_BASE_DIR with a prepared issue-comment body scratch file."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    from ci_base import BODY_KIND_ISSUE_COMMENT, get_body_path

    path = get_body_path(plan_id, BODY_KIND_ISSUE_COMMENT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body_text, encoding='utf-8')
    return plan_id


def test_cmd_issue_comment_posts_prepared_body(monkeypatch, tmp_path):
    """cmd_issue_comment posts the prepared body via `glab issue note {iid} --message`."""
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    plan_id = _prepare_issue_comment_body(tmp_path, monkeypatch, body_text='Outline ready')
    ns = argparse.Namespace(issue='42', plan_id=plan_id, slot=None)
    result = gitlab_ops.cmd_issue_comment(ns)

    assert result['status'] == 'success', result
    assert result['operation'] == 'issue_comment'
    assert result['issue_number'] == '42'
    assert captured[-1] == ['issue', 'note', '42', '--message', 'Outline ready']


def test_cmd_issue_comment_deletes_body_on_success(monkeypatch, tmp_path):
    """The prepared scratch body is removed only after a successful post."""
    from ci_base import BODY_KIND_ISSUE_COMMENT, get_body_path

    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', lambda args: (0, '', ''))

    plan_id = _prepare_issue_comment_body(tmp_path, monkeypatch)
    body_path = get_body_path(plan_id, BODY_KIND_ISSUE_COMMENT)
    assert body_path.exists()

    ns = argparse.Namespace(issue='42', plan_id=plan_id, slot=None)
    result = gitlab_ops.cmd_issue_comment(ns)

    assert result['status'] == 'success', result
    assert not body_path.exists()


def test_cmd_issue_comment_body_not_prepared(monkeypatch, tmp_path):
    """A missing prepared body yields a body_not_prepared error, no glab call."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(issue='42', plan_id='p', slot=None)
    result = gitlab_ops.cmd_issue_comment(ns)

    assert result['status'] == 'error', result
    assert result['operation'] == 'issue_comment'
    assert captured == []


def test_cmd_issue_comment_api_failure_keeps_body(monkeypatch, tmp_path):
    """A non-zero glab exit returns an error and leaves the scratch body in place."""
    from ci_base import BODY_KIND_ISSUE_COMMENT, get_body_path

    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', lambda args: (1, '', 'glab: not found'))

    plan_id = _prepare_issue_comment_body(tmp_path, monkeypatch)
    body_path = get_body_path(plan_id, BODY_KIND_ISSUE_COMMENT)

    ns = argparse.Namespace(issue='42', plan_id=plan_id, slot=None)
    result = gitlab_ops.cmd_issue_comment(ns)

    assert result['status'] == 'error', result
    assert body_path.exists()


def test_cmd_issue_comment_auth_failure(monkeypatch, tmp_path):
    """An auth failure short-circuits before any glab call."""
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'check_auth', lambda: (False, 'not logged in'))
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(issue='42', plan_id='p', slot=None)
    result = gitlab_ops.cmd_issue_comment(ns)

    assert result['status'] == 'error', result
    assert captured == []


def test_cmd_issue_prepare_comment_allocates_path(monkeypatch, tmp_path):
    """_cmd_issue_prepare_comment allocates an issue-comment scratch path."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plan_dir = tmp_path / 'plans' / 'p'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')

    ns = argparse.Namespace(plan_id='p', slot=None)
    result = gitlab_ops._cmd_issue_prepare_comment(ns)

    assert result['status'] == 'success', result
    assert result['kind'] == 'issue-comment'
    assert result['path'].endswith('issue-comment-default.md')


def test_cmd_issue_comment_normalizes_full_url(monkeypatch, tmp_path):
    """A full GitLab issue URL in --issue is normalized to the IID for `glab issue note` and the return."""
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    plan_id = _prepare_issue_comment_body(tmp_path, monkeypatch, body_text='Outline ready')
    ns = argparse.Namespace(issue='https://gitlab.com/o/r/-/issues/42', plan_id=plan_id, slot=None)
    result = gitlab_ops.cmd_issue_comment(ns)

    assert result['status'] == 'success', result
    assert result['issue_number'] == '42'
    assert captured[-1] == ['issue', 'note', '42', '--message', 'Outline ready']
