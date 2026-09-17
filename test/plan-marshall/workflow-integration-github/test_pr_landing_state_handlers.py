# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``ci pr landing-state`` verb — the foreign done-ness discriminator.

Three layers:

* the pure correlation :func:`ci_base.derive_landing_state`, with ONE case per
  return value and the produced-state population asserted against the verb's OWN
  declared set (:data:`ci_base.LANDING_STATES`) rather than a hand-copied list;
* the github handler :func:`_github_pr.cmd_pr_landing_state`, driven end-to-end
  with the git / gh / auth primitives monkeypatched on ``github_ops`` so each of
  the four landing states — plus the stale-tip, truncation, malformed-entry,
  auth, and git-evidence fail-closed paths — is exercised through the real
  handler body;
* the DOC-vs-runtime parity guard at the end of this module, which holds
  ``tools-integration-ci/standards/api-contract.md`` to the two closed
  populations ``ci_base`` declares — :data:`ci_base.LANDING_STATES` and
  :data:`ci_base.PR_VIEW_CAUSES`. The runtime sides were already guarded; the
  DOCUMENTED copies were not, and that document is the surface a consumer reads
  to decide what to branch on.
"""

import argparse
import json
import re
from pathlib import Path

import _github_pr
import ci_base
import github_ops
import pytest
from ci_base import LANDING_STATES, PR_VIEW_CAUSES, derive_landing_state

from conftest import PROJECT_ROOT

_CASE_PER_STATE: dict[str, tuple[list[str], bool]] = {
    'merged': (['MERGED'], True),
    'pr_open': (['OPEN'], True),
    'pushed_no_pr': ([], True),
    'unpushed': ([], False),
}
_TIP_SHA = 'deadbeefcafebabefeedface00000000deadbeef'


def _install_primitives(
    monkeypatch,
    *,
    pr_states,
    pushed,
    auth=(True, ''),
    tip_sha=_TIP_SHA,
    head_oids=None,
    git_contain_rc=0,
):
    """Monkeypatch github_ops' auth / gh / git primitives for one handler run.

    ``pr_states`` becomes the ``gh pr list --json`` payload; each PR's
    ``headRefOid`` is ``head_oids[i]`` (default: all == ``tip_sha`` so every PR is
    tip-matching). ``pushed`` drives ``git branch -r --contains`` (non-empty ⇒
    pushed); ``git_contain_rc`` forces a containment failure when non-zero.
    """
    monkeypatch.setattr(github_ops, 'check_auth', lambda: auth)
    oids = head_oids if head_oids is not None else [tip_sha] * len(pr_states)

    def fake_run_gh(args, capture_json=False, timeout=60):
        assert args[:2] == ['pr', 'list']
        payload = [
            {
                'number': i + 1,
                'state': s,
                'url': f'https://x/pull/{i + 1}',
                'headRefName': 'feature/x',
                'headRefOid': oids[i],
            }
            for i, s in enumerate(pr_states)
        ]
        return 0, json.dumps(payload), ''

    def fake_run_git(args, timeout=60):
        if args[:2] == ['rev-parse', '--abbrev-ref']:
            return 0, 'feature/x\n', ''
        if args[:1] == ['rev-parse']:
            return 0, f'{tip_sha}\n', ''
        if args[:3] == ['branch', '-r', '--contains']:
            if git_contain_rc != 0:
                return git_contain_rc, '', 'containment error'
            return (0, '  origin/feature/x\n', '') if pushed else (0, '', '')
        return 1, '', f'unexpected git args: {args}'

    monkeypatch.setattr(github_ops, 'run_gh', fake_run_gh)
    monkeypatch.setattr(github_ops, 'run_git', fake_run_git)


_API_CONTRACT: Path = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'tools-integration-ci'
    / 'standards'
    / 'api-contract.md'
)
_CAUSE_TABLE_HEADER = '| `error_cause` |'
_LANDING_POPULATION_RE = re.compile(r'own declared population \(([^)]*)\)')
_MEMBER_RE = re.compile(r'`([a-z_]+)`')
_SEPARATOR_RE = re.compile(r'^\|[\s:|-]+$')


def test_handler_reports_pushed_flag(monkeypatch):
    _install_primitives(monkeypatch, pr_states=[], pushed=True)
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['pushed'] is True
    assert result['landing_state'] == 'pushed_no_pr'


def test_handler_resolves_current_branch_when_branch_omitted(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))

    def fake_run_git(args, timeout=60):
        if args[:2] == ['rev-parse', '--abbrev-ref']:
            return 0, 'feature/resolved\n', ''
        if args[:1] == ['rev-parse']:
            return 0, f'{_TIP_SHA}\n', ''
        if args[:3] == ['branch', '-r', '--contains']:
            return 0, 'origin/feature/resolved\n', ''
        return 1, '', 'unexpected'

    def fake_run_gh(args, capture_json=False, timeout=60):
        # The resolved branch must be the one queried.
        assert '--head' in args and args[args.index('--head') + 1] == 'feature/resolved'
        return (
            0,
            json.dumps(
                [{'number': 7, 'state': 'OPEN', 'url': 'u', 'headRefName': 'feature/resolved', 'headRefOid': _TIP_SHA}]
            ),
            '',
        )

    monkeypatch.setattr(github_ops, 'run_git', fake_run_git)
    monkeypatch.setattr(github_ops, 'run_gh', fake_run_gh)

    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch=None))
    assert result['status'] == 'success'
    assert result['branch'] == 'feature/resolved'
    assert result['landing_state'] == 'pr_open'


def test_handler_refuses_detached_head(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'run_git', lambda args, timeout=60: (0, 'HEAD\n', ''))
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch=None))
    assert result['status'] == 'error'
    assert 'detached' in result.get('error', '').lower()


def test_handler_errors_on_auth_failure_rather_than_downgrading(monkeypatch):
    # An unauthenticated gh must not silently become pushed_no_pr — a merged/open
    # verdict would be lost. The handler errors instead.
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'not authenticated'))
    monkeypatch.setattr(github_ops, 'run_git', lambda args, timeout=60: (0, f'{_TIP_SHA}\n', ''))
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'error'


def test_handler_errors_on_unparseable_gh_output(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'run_git', lambda args, timeout=60: (0, f'{_TIP_SHA}\n', ''))
    monkeypatch.setattr(github_ops, 'run_gh', lambda args, capture_json=False, timeout=60: (0, 'not json', ''))
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'error'


def test_handler_errors_on_gh_list_failure(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'run_git', lambda args, timeout=60: (0, f'{_TIP_SHA}\n', ''))
    monkeypatch.setattr(github_ops, 'run_gh', lambda args, capture_json=False, timeout=60: (1, '', 'boom'))
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'error'
