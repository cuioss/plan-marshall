#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for gitlab_ops.py — CLI surface and formatting."""

from __future__ import annotations

import argparse
from types import SimpleNamespace

import ci_base
import gitlab_ops
import pytest
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


# =============================================================================
# checks logs — --scope / --match / --job (parity with the GitHub handler)
# =============================================================================
#
# ``glab ci trace`` returns the full trace of the addressed job regardless of
# its conclusion, so both scopes are served from the same read: ``failed`` keeps
# the head-window truncation, ``full`` returns the trace whole. ``--match``
# selects from the whole trace, and ``--job`` is rejected because ``--run-id``
# already addresses exactly one job.


def _patch_trace(monkeypatch, stdout='', *, returncode=0, stderr=''):
    """Stub ``glab ci trace`` and return the list of argv it was called with."""
    calls: list[list[str]] = []

    fake = SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)

    def fake_run(cmd, **_kwargs):
        calls.append(list(cmd))
        return fake

    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops.subprocess, 'run', fake_run)
    return calls


def _logs_args(**overrides):
    values: dict = {'run_id': 'job-1', 'scope': 'failed', 'match': None, 'job': None}
    values.update(overrides)
    return argparse.Namespace(**values)


def _long_trace(line_count=260):
    return [f'trace line {i}' for i in range(line_count)]


@pytest.mark.parametrize('scope', ['failed', 'full'])
def test_ci_logs_both_scopes_read_the_same_trace(monkeypatch, scope):
    """Neither scope is refused: both run ``glab ci trace`` on the addressed job."""
    calls = _patch_trace(monkeypatch, 'a line\n')

    result = gitlab_ops.cmd_ci_logs(_logs_args(scope=scope))

    assert result['status'] == 'success', result
    assert calls == [['glab', 'ci', 'trace', 'job-1']]
    assert result['scope'] == scope


def test_ci_logs_failed_scope_truncates_and_full_scope_does_not(monkeypatch):
    """failed keeps the head-window truncation; full returns the trace whole."""
    lines = _long_trace()
    _patch_trace(monkeypatch, '\n'.join(lines))

    failed = gitlab_ops.cmd_ci_logs(_logs_args(scope='failed'))
    full = gitlab_ops.cmd_ci_logs(_logs_args(scope='full'))

    assert failed['log_lines'] == ci_base.CI_LOG_TRUNCATE_LINES
    assert failed['log_lines'] < len(lines)
    assert full['log_lines'] == len(lines)
    assert full['content'] == '\\n'.join(lines)


def test_ci_logs_match_returns_only_matching_lines(monkeypatch):
    """--match keeps only the lines containing the literal, case-sensitively."""
    _patch_trace(monkeypatch, 'starting\nAssembled review charter\nassembled review charter\ndone\n')

    result = gitlab_ops.cmd_ci_logs(_logs_args(scope='full', match='Assembled review charter'))

    assert result['status'] == 'success', result
    assert result['match_count'] == 1
    assert result['log_lines'] == 1
    assert result['content'] == 'Assembled review charter'


def test_ci_logs_match_selects_from_the_whole_trace_under_failed_scope(monkeypatch):
    """A match past the head window is still found: --match reads the whole trace."""
    lines = _long_trace()
    _patch_trace(monkeypatch, '\n'.join(lines))

    result = gitlab_ops.cmd_ci_logs(_logs_args(scope='failed', match='trace line 259'))

    assert result['match_count'] == 1
    assert result['content'] == 'trace line 259'


def test_ci_logs_zero_match_is_success_with_measured_zero(monkeypatch):
    """A fetched trace with no matching line is a success carrying match_count 0."""
    _patch_trace(monkeypatch, 'one\ntwo\n')

    result = gitlab_ops.cmd_ci_logs(_logs_args(scope='full', match='absent literal'))

    assert result['status'] == 'success', result
    assert result['match_count'] == 0
    assert result['log_lines'] == 0
    assert result['content'] == ''


@pytest.mark.parametrize('scope', ['failed', 'full'])
@pytest.mark.parametrize('match', [None, 'anything'])
def test_ci_logs_fetch_failure_is_error_never_empty_success(monkeypatch, scope, match):
    """A non-zero glab exit is status: error with the stderr — with or without --match."""
    _patch_trace(monkeypatch, '', returncode=1, stderr='job is still running\n')

    result = gitlab_ops.cmd_ci_logs(_logs_args(scope=scope, match=match))

    assert result['status'] == 'error'
    assert result['context'] == 'job is still running'
    assert 'match_count' not in result
    assert 'content' not in result


def test_ci_logs_job_is_rejected_without_reading_a_trace(monkeypatch):
    """--job is rejected explicitly: --run-id already addresses exactly one job."""
    calls = _patch_trace(monkeypatch, 'never read\n')

    result = gitlab_ops.cmd_ci_logs(_logs_args(scope='full', job='review / review'))

    assert result['status'] == 'error'
    assert '--job is not supported on GitLab' in result['error']
    assert '--run-id already addresses one job' in result['error']
    assert calls == []


def test_ci_logs_empty_match_is_refused_before_any_fetch(monkeypatch):
    """An empty --match would match every line, so it is refused outright."""
    calls = _patch_trace(monkeypatch, 'one\n')

    result = gitlab_ops.cmd_ci_logs(_logs_args(scope='full', match=''))

    assert result['status'] == 'error'
    assert '--match' in result['error']
    assert calls == []


def test_ci_logs_default_scope_is_failed_for_a_flagless_caller(monkeypatch):
    """A Namespace carrying only run_id reads exactly what an explicit failed scope reads."""
    _patch_trace(monkeypatch, '\n'.join(_long_trace()))

    flagless = gitlab_ops.cmd_ci_logs(argparse.Namespace(run_id='job-1'))
    explicit = gitlab_ops.cmd_ci_logs(_logs_args(scope='failed'))

    assert flagless == explicit
    assert flagless['scope'] == 'failed'
    assert 'match_count' not in flagless


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
