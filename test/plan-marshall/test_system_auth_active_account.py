#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""One ``gh auth status`` report, one authentication verdict — across two skills.

A developer holding a stale account alongside a healthy active one is the
user-visible defect this module pins: ``gh auth status`` sets a non-zero exit
code whenever ANY configured account fails, so an aggregate-exit-code decision
reports that developer unauthenticated while ``gh`` works perfectly.

Two entry points answer "is the CI tool authenticated?" from opposite sides of
the marketplace, and a fix applied to only one of them leaves the other
reporting the opposite verdict for the same machine:

    manage-providers      _providers_core.verify_system_auth()
    tools-integration-ci  ci_health.verify_tool(), and the cmd_status /
                          cmd_verify_all results that read it

Both report shapes below exit with the SAME non-zero code, so the exit code
cannot discriminate them: only reading the per-account report can. That is what
makes the pair a matched positive/negative control — an implementation that
consults the exit code fails the positive case, and one that ignores the report
whenever an account block is present fails the negative case.

The pair runs over a second axis, the stream the CLI wrote the report to. A
capture that selects one stream rather than combining them discards the report
whenever the other stream is non-empty, leaving text with no account marker and
sending the decision back to the exit code — reopening the hole from the far
side. Holding the verdict constant across both placements is what closes it.

The module lives at the top level of ``test/plan-marshall/`` because it spans
two skills, alongside the other cross-cutting modules there.
"""

import argparse
import subprocess

import ci_health
import file_ops
import pytest
from _providers_core import verify_system_auth

# The provider declaration the manage-providers path verifies, matching the
# shipped github provider's system-auth shape.
_GITHUB_PROVIDER = {
    'skill_name': 'plan-marshall:workflow-integration-github',
    'verify_command': 'gh auth status',
}

# ``gh auth status`` exits non-zero when ANY configured account fails — which is
# true of BOTH reports below. The exit code is therefore held constant across
# the positive and the negative case, so it cannot be the discriminator.
_GH_EXIT_CODE_WITH_A_FAILED_ACCOUNT = 1

# A stale account alongside a healthy ACTIVE account: the tool is usable.
_ACTIVE_ACCOUNT_HEALTHY = """github.com
  X Failed to log in to github.com account stale-bot (keyring)
  - Active account: false
  - The token in keyring is no longer valid.
  ✓ Logged in to github.com account octocat (keyring)
  - Active account: true
  - Git operations protocol: https
"""

# The same two accounts with the roles swapped — the ACTIVE account is the
# failed one, so the tool is genuinely unusable.
_ACTIVE_ACCOUNT_FAILED = """github.com
  ✓ Logged in to github.com account octocat (keyring)
  - Active account: false
  - Git operations protocol: https
  X Failed to log in to github.com account stale-bot (keyring)
  - Active account: true
  - The token in keyring is no longer valid.
"""

_ACCOUNT_REPORTS = [
    pytest.param(_ACTIVE_ACCOUNT_HEALTHY, True, id='active-account-healthy'),
    pytest.param(_ACTIVE_ACCOUNT_FAILED, False, id='active-account-failed'),
]

# An unrelated line a CLI may print to stdout while writing its actual status
# report to stderr. It carries no account marker, so a capture that keeps only
# stdout hands the decision text-with-no-report and the verdict silently falls
# back to the exit code held constant above.
_UNRELATED_STDOUT_NOTICE = 'A new release of gh is available: 2.45.0 -> 2.46.0\n'

# Where the CLI wrote its account report. Both placements must produce the same
# verdict, so the pair is a second matched control crossing the report axis: an
# implementation that selects one stream passes on-stdout and fails on-stderr.
_REPORT_STREAMS = [
    pytest.param('stdout', id='report-on-stdout'),
    pytest.param('stderr', id='report-on-stderr-behind-a-stdout-notice'),
]

_REPO_URL = 'https://github.com/cuioss/plan-marshall.git'


def _split_streams(report: str, stream: str) -> tuple[str, str]:
    """Return ``(stdout, stderr)`` placing ``report`` on the named stream.

    On the ``stderr`` placement stdout is deliberately NON-empty, because an
    empty stdout would let a stream-selecting capture fall through to stderr and
    pass for the wrong reason.
    """
    if stream == 'stdout':
        return report, ''
    return _UNRELATED_STDOUT_NOTICE, report


def _stub_providers_path(monkeypatch, report: str, stream: str = 'stdout') -> None:
    """Feed ``report`` to the manage-providers path's subprocess seam."""
    stdout, stderr = _split_streams(report, stream)

    def _fake_run(argv, **kwargs):
        assert argv == ['gh', 'auth', 'status']
        return subprocess.CompletedProcess(
            argv, _GH_EXIT_CODE_WITH_A_FAILED_ACCOUNT, stdout=stdout, stderr=stderr
        )

    monkeypatch.setattr('_providers_core.subprocess.run', _fake_run)


def _stub_ci_path(monkeypatch, report: str, stream: str = 'stdout') -> None:
    """Feed ``report`` to the tools-integration-ci path's command seam.

    Also answers the remote-URL probe (so the provider resolves to github and
    ``gh`` is the required tool) and the ``--version`` probes. Any other command
    is a defect in the test rather than a silent pass.
    """
    auth_stdout, auth_stderr = _split_streams(report, stream)

    def _fake_run_command(cmd, cwd=None):
        arguments = list(cmd[1:])
        if arguments == ['remote', 'get-url', 'origin']:
            return 0, f'{_REPO_URL}\n', ''
        if arguments == ['--version']:
            return 0, f'{cmd[0]} version 2.45.0\n', ''
        if arguments == ['auth', 'status']:
            return _GH_EXIT_CODE_WITH_A_FAILED_ACCOUNT, auth_stdout, auth_stderr
        raise AssertionError(f'unexpected command: {cmd}')

    monkeypatch.setattr(ci_health, 'run_command', _fake_run_command)


@pytest.mark.parametrize('stream', _REPORT_STREAMS)
@pytest.mark.parametrize(('report', 'expected'), _ACCOUNT_REPORTS)
def test_both_entry_points_agree_on_the_active_account(report, expected, stream, monkeypatch):
    """The manage-providers and tools-integration-ci paths return one verdict.

    Asserting each side against ``expected`` pins the verdict itself; asserting
    them against each other pins the agreement, which is what a fix applied to
    only one of the two surfaces breaks.

    Running the pair over both report streams pins the capture shape at both
    sites: a capture that keeps stdout alone sees only the unrelated notice on
    the ``stderr`` placement, finds no account marker, and falls back to the
    non-zero exit code — failing the positive case while still passing the
    negative one, which is why the pair must be matched.
    """
    _stub_providers_path(monkeypatch, report, stream)
    _stub_ci_path(monkeypatch, report, stream)

    providers_verdict = verify_system_auth(_GITHUB_PROVIDER)['success']
    ci_verdict = ci_health.verify_tool('gh')['authenticated']

    assert providers_verdict is expected
    assert ci_verdict is expected
    assert providers_verdict is ci_verdict


@pytest.mark.parametrize(('report', 'expected'), _ACCOUNT_REPORTS)
def test_ci_status_reports_the_active_account_verdict(report, expected, monkeypatch):
    """``ci_health status`` carries the verdict through to overall health.

    This is the surface an operator reads, so a correct ``verify_tool`` that
    the aggregate never consumed would still present a stale developer as
    degraded.
    """
    _stub_ci_path(monkeypatch, report)

    result = ci_health.cmd_status(argparse.Namespace())

    assert result['tools']['gh']['authenticated'] is expected
    assert result['required_tool'] == 'gh'
    assert result['required_tool_ready'] is expected
    assert result['overall'] == ('healthy' if expected else 'degraded')


@pytest.mark.parametrize(('report', 'expected'), _ACCOUNT_REPORTS)
def test_ci_verify_all_reports_the_active_account_verdict(report, expected, monkeypatch, tmp_path):
    """``ci_health verify-all`` admits ``gh`` to authenticated_tools on the verdict.

    The list is what downstream callers read to decide whether the CI provider
    is usable, so it is the second aggregate that must not disagree.
    """
    marshal_path = tmp_path / 'marshal.json'
    marshal_path.write_text('{}')
    monkeypatch.setattr(file_ops, 'get_marshal_path', lambda: marshal_path)
    _stub_ci_path(monkeypatch, report)

    result = ci_health.cmd_verify_all(argparse.Namespace())

    assert result['status'] == 'success'
    assert result['provider'] == 'github'
    assert ('gh' in result['authenticated_tools']) is expected
    assert result['git_present'] is True
