#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``ci pr landing-state`` verb — the foreign done-ness discriminator.

Two layers:

* the pure correlation :func:`ci_base.derive_landing_state`, with ONE case per
  return value and the produced-state population asserted against the verb's OWN
  declared set (:data:`ci_base.LANDING_STATES`) rather than a hand-copied list;
* the github handler :func:`_github_pr.cmd_pr_landing_state`, driven end-to-end
  with the git / gh / auth primitives monkeypatched on ``github_ops`` so each of
  the four landing states — plus the stale-tip, truncation, malformed-entry,
  auth, and git-evidence fail-closed paths — is exercised through the real
  handler body.
"""

import argparse
import json

import pytest

import ci_base
import github_ops
import _github_pr
from ci_base import LANDING_STATES, derive_landing_state

# --------------------------------------------------------------------------- #
# Pure correlation: one case per return value, asserted vs the declared set
# --------------------------------------------------------------------------- #

#: One representative (pr_states, pushed) input per DECLARED landing state. The
#: mapping is keyed by the expected state so the test proves — structurally —
#: that every member of LANDING_STATES has a case and nothing outside it is
#: produced, rather than hand-listing the four strings a second time. Only the
#: KEYS mirror the authoritative set (and are asserted equal to it below); the
#: VALUES are representative input fixtures, which cannot be derived.
_CASE_PER_STATE: dict[str, tuple[list[str], bool]] = {
    'merged': (['MERGED'], True),
    'pr_open': (['OPEN'], True),
    'pushed_no_pr': ([], True),
    'unpushed': ([], False),
}


def test_declared_set_is_non_empty():
    # Non-vacuity guard: a derived-population sweep over an empty set would pass
    # every "for state in LANDING_STATES" assertion while testing nothing.
    assert len(LANDING_STATES) >= 1


def test_case_table_matches_the_declared_state_set():
    # The verb's declared population is the source of truth; the case table must
    # cover exactly it, so a future state added to LANDING_STATES fails here
    # until a case is supplied rather than going silently untested.
    assert set(_CASE_PER_STATE) == set(LANDING_STATES)


@pytest.mark.parametrize('expected_state', LANDING_STATES)
def test_each_declared_state_is_produced_by_its_case(expected_state):
    pr_states, pushed = _CASE_PER_STATE[expected_state]
    assert derive_landing_state(pr_states, pushed) == expected_state


def test_produced_states_cover_exactly_the_declared_set():
    produced = {derive_landing_state(prs, pushed) for prs, pushed in _CASE_PER_STATE.values()}
    assert produced  # non-vacuity
    assert produced == set(LANDING_STATES)


def test_merged_wins_over_open_when_both_reference_the_branch():
    assert derive_landing_state(['OPEN', 'MERGED'], True) == 'merged'


def test_merged_is_authoritative_even_when_branch_looks_unpushed():
    # A merged PR whose head branch was deleted by the merge reports merged even
    # though remote containment is now False — PR state precedes push state.
    assert derive_landing_state(['MERGED'], False) == 'merged'


def test_closed_unmerged_pr_collapses_to_pushed_no_pr():
    # A closed-but-unmerged PR leaves the change stranded on a remote branch with
    # nothing carrying it to merge — the blocking state, not pr_open/merged.
    assert derive_landing_state(['CLOSED'], True) == 'pushed_no_pr'


def test_state_spelling_is_case_insensitive():
    assert derive_landing_state(['merged'], True) == 'merged'
    assert derive_landing_state(['open'], True) == 'pr_open'


# --------------------------------------------------------------------------- #
# Handler: each landing state driven through the real cmd_pr_landing_state body
# --------------------------------------------------------------------------- #

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


@pytest.mark.parametrize('expected_state', LANDING_STATES)
def test_handler_produces_each_declared_state(monkeypatch, expected_state):
    pr_states, pushed = _CASE_PER_STATE[expected_state]
    _install_primitives(monkeypatch, pr_states=pr_states, pushed=pushed)

    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))

    assert result['status'] == 'success'
    assert result['landing_state'] == expected_state
    # The verb publishes its own declared population so a consumer/test reads it
    # from the code rather than re-listing it.
    assert result['landing_states'] == list(LANDING_STATES)
    assert result['tip_sha'] == _TIP_SHA


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
        return 0, json.dumps(
            [{'number': 7, 'state': 'OPEN', 'url': 'u', 'headRefName': 'feature/resolved', 'headRefOid': _TIP_SHA}]
        ), ''

    monkeypatch.setattr(github_ops, 'run_git', fake_run_git)
    monkeypatch.setattr(github_ops, 'run_gh', fake_run_gh)

    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch=None))
    assert result['status'] == 'success'
    assert result['branch'] == 'feature/resolved'
    assert result['landing_state'] == 'pr_open'


def test_stale_merged_pr_for_an_earlier_tip_is_not_merged(monkeypatch):
    # A merged PR whose head is an OLD tip on a reused branch name must not report
    # merged for the current tip's new, unlanded commits.
    _install_primitives(
        monkeypatch,
        pr_states=['MERGED'],
        pushed=True,
        head_oids=['0000000000000000000000000000000000000000'],  # != _TIP_SHA
    )
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'success'
    assert result['pr_count'] == 0  # the stale PR is filtered out
    assert result['landing_state'] == 'pushed_no_pr'


def test_truncated_pr_list_fails_closed(monkeypatch):
    _install_primitives(monkeypatch, pr_states=['OPEN'] * _github_pr._PR_LIST_LIMIT, pushed=True)
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'error'
    assert 'truncated' in result.get('error', '').lower()


def test_git_containment_failure_fails_closed_when_verdict_depends_on_it(monkeypatch):
    # No PR carries the branch, so the verdict rests on remote containment; a git
    # failure there is unreadable evidence and must not become a clearing state.
    _install_primitives(monkeypatch, pr_states=[], pushed=True, git_contain_rc=1)
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'error'


def test_git_containment_failure_tolerated_when_a_merged_pr_exists(monkeypatch):
    # A tip-matching merged PR settles the verdict without git, so a containment
    # failure is irrelevant and must not turn a merged change into an error.
    _install_primitives(monkeypatch, pr_states=['MERGED'], pushed=True, git_contain_rc=1)
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'success'
    assert result['landing_state'] == 'merged'


def test_unresolvable_tip_fails_closed(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'run_git', lambda args, timeout=60: (128, '', 'unknown revision'))
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'error'
    assert 'tip sha' in result.get('error', '').lower()


def test_malformed_pr_entry_fails_closed(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'run_git', lambda args, timeout=60: (0, f'{_TIP_SHA}\n', ''))
    monkeypatch.setattr(
        github_ops, 'run_gh', lambda args, capture_json=False, timeout=60: (0, json.dumps(['not-an-object']), '')
    )
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'error'


def test_pr_entry_without_state_fails_closed(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'run_git', lambda args, timeout=60: (0, f'{_TIP_SHA}\n', ''))
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        lambda args, capture_json=False, timeout=60: (0, json.dumps([{'number': 1, 'headRefOid': _TIP_SHA}]), ''),
    )
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'error'


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


def test_landing_states_is_the_authoritative_population_reference():
    # ci_base owns the declared population; the verb and its gate read it from
    # here. (Not a mirrored-literal assertion — it names the single source.)
    assert ci_base.LANDING_STATES is LANDING_STATES
    assert 'pushed_no_pr' in LANDING_STATES
