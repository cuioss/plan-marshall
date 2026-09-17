#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for gitlab_ops.py — CLI surface and formatting."""

from __future__ import annotations

import argparse
import gitlab_ops
from _ci_wait_contract import _ok_auth
from _resolve_project_dir_fixtures import worktree_query_result


# =============================================================================
# format_checks_toon (jobs) — Go zero-value timestamp regression
# =============================================================================
#
# A SKIPPED job carrying Go zero-value `0001-01-01T00:00:00Z` timestamps
# must not leak ~63.9-billion-second `elapsed_sec` values into the TOON
# aggregate. The contract:
#
#   (a) aggregate elapsed_sec is bounded by a 24h ceiling
#   (b) skipped row (with Go zero-value timestamps) has NO `elapsed_sec` key
#   (c) other (real-timestamped) rows have non-negative integer `elapsed_sec`
_GO_ZERO_GL = '0001-01-01T00:00:00Z'


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
    # The manage-status shell-out seam lives in file_ops; resolve_project_dir
    # delegates the worktree face to file_ops.resolve_plan_context.
    import file_ops as _resolver_core
    from ci_base import get_default_cwd, set_default_cwd

    monkeypatch.setattr(
        _resolver_core, '_query_worktree_path', lambda _pid: worktree_query_result(True, '/tmp/wt-gitlab-resolved')
    )

    monkeypatch.setattr('sys.argv', ['gitlab_ops.py', '--plan-id', 'task-routing-canonical', '--help'])

    import pytest as _pytest

    with _pytest.raises(SystemExit):
        gitlab_ops.main()

    assert get_default_cwd() == '/tmp/wt-gitlab-resolved'
    set_default_cwd(None)
