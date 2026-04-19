#!/usr/bin/env python3
"""Tests for the `branch delete --remote-only` leaf command.

Covers three layers:

1. Argparse plumbing in ``ci_base.build_parser`` — the ``branch`` subparser
   and ``delete`` subcommand, required ``--remote-only`` and ``--branch``
   flags, and failure on omitted flags.
2. GitHub provider ``cmd_branch_delete`` — success (HTTP 204), already-gone
   (HTTP 404 / 422 mapped to success with ``already_gone: true``), and other
   errors surfaced as structured TOON error dicts.
3. GitLab provider ``cmd_branch_delete`` — symmetric scenarios with
   ``glab api``.

Mirrors the tiered pattern used by ``test_ci_base.py``, ``test_ci.py``, and
``test_ci_health.py``.
"""

import argparse

import github_ops  # type: ignore[import-not-found]
import gitlab_ops  # type: ignore[import-not-found]
import pytest
from ci_base import build_parser  # type: ignore[import-not-found]

# =============================================================================
# Shared test helpers
# =============================================================================


def _ok_auth():
    return True, ''


def _fail_auth():
    return False, 'Not authenticated'


def _make_github_run_stub(returncode: int = 0, stderr: str = ''):
    """Return a (run_gh_stub, captured_args) pair used to mock ``run_gh``.

    Only the DELETE-refs path is exercised by these tests, so the stub ignores
    the args beyond capturing them for assertions.
    """
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        return returncode, '', stderr

    return run_gh_stub, captured


def _make_gitlab_run_stub(returncode: int = 0, stderr: str = ''):
    """Return a (run_glab_stub, captured_args) pair used to mock ``run_glab``."""
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return returncode, '', stderr

    return run_glab_stub, captured


def _github_namespace(branch: str = 'feature/x') -> argparse.Namespace:
    return argparse.Namespace(branch=branch, remote_only=True)


def _gitlab_namespace(branch: str = 'feature/x') -> argparse.Namespace:
    return argparse.Namespace(branch=branch, remote_only=True)


# =============================================================================
# Tier 1: argparse plumbing in ci_base.build_parser
# =============================================================================


def test_build_parser_registers_branch_delete():
    """`branch delete` must be registered and capture --remote-only + --branch."""
    parser, _, _, _, branch_sub = build_parser('test')
    args = parser.parse_args(
        ['branch', 'delete', '--remote-only', '--branch', 'feature/x']
    )
    assert args.command == 'branch'
    assert args.branch_command == 'delete'
    assert args.branch == 'feature/x'
    assert args.remote_only is True
    # The branch subparser handle should also be returned for provider scripts.
    assert branch_sub is not None


def test_branch_delete_requires_branch_flag():
    """Omitting --branch must fail argparse validation."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['branch', 'delete', '--remote-only'])


def test_branch_delete_requires_remote_only_flag():
    """Omitting --remote-only must fail argparse validation.

    The flag is intentionally required (not defaulted) to make the caller
    explicitly acknowledge that local cleanup is out of scope.
    """
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['branch', 'delete', '--branch', 'feature/x'])


def test_branch_delete_requires_both_flags():
    """Omitting everything must fail with required-subcommand error."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['branch', 'delete'])


def test_branch_subparser_requires_subcommand():
    """`branch` alone (without `delete`) must fail argparse validation."""
    parser, _, _, _, _ = build_parser('test')
    with pytest.raises(SystemExit):
        parser.parse_args(['branch'])


# =============================================================================
# Tier 2: GitHub provider cmd_branch_delete
# =============================================================================


def test_github_branch_delete_success_http_204(monkeypatch):
    """HTTP 204 (returncode=0) → status: success, already_gone: false."""
    run_gh_stub, captured = _make_github_run_stub(returncode=0, stderr='')
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))

    result = github_ops.cmd_branch_delete(_github_namespace('feature/x'))

    assert result['status'] == 'success'
    assert result['operation'] == 'branch_delete'
    assert result['branch'] == 'feature/x'
    assert result['remote_only'] is True
    assert result['already_gone'] is False
    # The stub should have been asked to DELETE the heads ref for the branch.
    assert captured == [
        ['api', '-X', 'DELETE', 'repos/octo/repo/git/refs/heads/feature/x']
    ]


def test_github_branch_delete_already_gone_http_404(monkeypatch):
    """HTTP 404 (branch missing) maps to success with already_gone: true."""
    run_gh_stub, _ = _make_github_run_stub(
        returncode=1, stderr='gh: Not Found (HTTP 404)'
    )
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))

    result = github_ops.cmd_branch_delete(_github_namespace('feature/gone'))

    assert result['status'] == 'success'
    assert result['operation'] == 'branch_delete'
    assert result['branch'] == 'feature/gone'
    assert result['already_gone'] is True


def test_github_branch_delete_already_gone_http_422(monkeypatch):
    """HTTP 422 (ref already removed) also maps to success."""
    run_gh_stub, _ = _make_github_run_stub(
        returncode=1, stderr='gh: Reference does not exist (HTTP 422)'
    )
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))

    result = github_ops.cmd_branch_delete(_github_namespace('feature/x'))

    assert result['status'] == 'success'
    assert result['already_gone'] is True


def test_github_branch_delete_other_http_error(monkeypatch):
    """Non-2xx / non-404 / non-422 HTTP errors surface as TOON error dicts."""
    run_gh_stub, _ = _make_github_run_stub(
        returncode=1,
        stderr='gh: Must have admin rights to Repository (HTTP 403)',
    )
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))

    result = github_ops.cmd_branch_delete(_github_namespace('feature/x'))

    assert result['status'] == 'error'
    assert result['operation'] == 'branch_delete'
    assert 'feature/x' in result['error']
    assert 'HTTP 403' in result.get('context', '')


def test_github_branch_delete_auth_failure(monkeypatch):
    """Unauthenticated calls short-circuit before any HTTP request."""
    run_gh_stub, captured = _make_github_run_stub()
    monkeypatch.setattr(github_ops, 'check_auth', _fail_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))

    result = github_ops.cmd_branch_delete(_github_namespace('feature/x'))

    assert result['status'] == 'error'
    assert result['operation'] == 'branch_delete'
    assert captured == [], 'run_gh must not be invoked when auth fails'


def test_github_branch_delete_repo_info_missing(monkeypatch):
    """Missing owner/repo means no DELETE is attempted."""
    run_gh_stub, captured = _make_github_run_stub()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: (None, None))

    result = github_ops.cmd_branch_delete(_github_namespace('feature/x'))

    assert result['status'] == 'error'
    assert 'owner/name' in result['error']
    assert captured == [], 'run_gh must not be invoked when repo info missing'


# =============================================================================
# Tier 2: GitLab provider cmd_branch_delete
# =============================================================================


def test_gitlab_branch_delete_success_http_204(monkeypatch):
    """HTTP 204 → status: success, already_gone: false; project path URL-encoded."""
    run_glab_stub, captured = _make_gitlab_run_stub(returncode=0, stderr='')
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'get_project_path', lambda: 'group/repo')

    result = gitlab_ops.cmd_branch_delete(_gitlab_namespace('feature/x'))

    assert result['status'] == 'success'
    assert result['operation'] == 'branch_delete'
    assert result['branch'] == 'feature/x'
    assert result['remote_only'] is True
    assert result['already_gone'] is False
    # group/repo → group%2Frepo, feature/x → feature%2Fx (per quote(..., safe='')).
    assert captured == [
        [
            'api',
            '-X',
            'DELETE',
            'projects/group%2Frepo/repository/branches/feature%2Fx',
        ]
    ]


def test_gitlab_branch_delete_already_gone_http_404(monkeypatch):
    """HTTP 404 maps to success with already_gone: true."""
    run_glab_stub, _ = _make_gitlab_run_stub(
        returncode=1, stderr='HTTP 404 Not Found'
    )
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'get_project_path', lambda: 'group/repo')

    result = gitlab_ops.cmd_branch_delete(_gitlab_namespace('feature/gone'))

    assert result['status'] == 'success'
    assert result['branch'] == 'feature/gone'
    assert result['already_gone'] is True


def test_gitlab_branch_delete_already_gone_http_422(monkeypatch):
    """HTTP 422 symmetric with GitHub — mapped to success."""
    run_glab_stub, _ = _make_gitlab_run_stub(
        returncode=1, stderr='HTTP 422 Unprocessable Entity'
    )
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'get_project_path', lambda: 'group/repo')

    result = gitlab_ops.cmd_branch_delete(_gitlab_namespace('feature/x'))

    assert result['status'] == 'success'
    assert result['already_gone'] is True


def test_gitlab_branch_delete_other_http_error(monkeypatch):
    """Other HTTP errors surface as TOON error dicts."""
    run_glab_stub, _ = _make_gitlab_run_stub(
        returncode=1, stderr='HTTP 403 Forbidden'
    )
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'get_project_path', lambda: 'group/repo')

    result = gitlab_ops.cmd_branch_delete(_gitlab_namespace('feature/x'))

    assert result['status'] == 'error'
    assert result['operation'] == 'branch_delete'
    assert 'feature/x' in result['error']
    assert 'HTTP 403' in result.get('context', '')


def test_gitlab_branch_delete_auth_failure(monkeypatch):
    """Unauthenticated calls short-circuit before any HTTP request."""
    run_glab_stub, captured = _make_gitlab_run_stub()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _fail_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'get_project_path', lambda: 'group/repo')

    result = gitlab_ops.cmd_branch_delete(_gitlab_namespace('feature/x'))

    assert result['status'] == 'error'
    assert captured == [], 'run_glab must not be invoked when auth fails'


def test_gitlab_branch_delete_project_path_missing(monkeypatch):
    """Missing project path means no DELETE is attempted."""
    run_glab_stub, captured = _make_gitlab_run_stub()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    monkeypatch.setattr(gitlab_ops, 'get_project_path', lambda: None)

    result = gitlab_ops.cmd_branch_delete(_gitlab_namespace('feature/x'))

    assert result['status'] == 'error'
    assert 'project path' in result['error']
    assert captured == [], 'run_glab must not be invoked when project path missing'
