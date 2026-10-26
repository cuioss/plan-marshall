#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the analysis-revision truth gate on the Sonar count verbs.

A count is taken from the issue set the latest analysis produced. When that
analysis is of another commit — a push landed after the scan — the issue set
describes an older tree, and a ``0`` read from it is a clean analysis of the
wrong code. ``count_status`` therefore has to cover the revision as well as the
Compute-Engine state:

* an analysis revision equal to the head confirms the count;
* a different revision is ``undecidable`` with reason ``stale_analysis`` and both
  SHAs, never ``confirmed``;
* a revision the API does not report is ``undecidable``, never ``confirmed``.

The Sonar API is stubbed at the REST client, and the comparison head is stubbed at
the git resolver, so the revision lookup and the comparison themselves run for
real.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from conftest import add_skill_scripts_to_path, load_script_module, parse_ns

sonar_mod = load_script_module('plan-marshall', 'workflow-integration-sonar', 'sonar.py', 'sonar_revision_mod')

#: ``_providers_core`` is imported INSIDE the verbs, so the stub has to land on
#: that module object rather than on ``sonar_mod``.
add_skill_scripts_to_path('plan-marshall', 'manage-providers')
import _providers_core  # noqa: E402

_HEAD = 'a' * 40
_STALE = 'b' * 40
_PROJECT = 'cuioss_plan-marshall'
_PR_LIST = '/api/project_pull_requests/list'


class _FakeClient:
    """One Sonar REST client whose GETs answer from a per-path payload map."""

    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, dict(params or {})))
        value = self._responses[path]
        if isinstance(value, Exception):
            raise value
        return value

    def close(self):
        pass


def _install_api(monkeypatch, responses):
    """Point every verb's client at one fake Sonar, returning it for call assertions."""
    client = _FakeClient(responses)
    monkeypatch.setattr(_providers_core, 'get_authenticated_client', lambda *a, **k: client)
    return client


def _pr_listing(sha=None, branch='fix/lb-58-verification-truth', key='42', with_commit=True):
    entry = {'key': key, 'branch': branch}
    if with_commit:
        commit = {} if sha is None else {'sha': sha}
        entry['commit'] = commit
    return {'pullRequests': [entry]}


def _fetch_args(plan_id, pr='42'):
    argv = ['--plan-id', plan_id, '--project', _PROJECT]
    if pr is not None:
        argv += ['--pr', pr]
    return parse_ns(
        'plan-marshall',
        'workflow-integration-sonar',
        'sonar.py',
        'fetch_findings',
        *argv,
    )


def _read_args(pr='42'):
    argv = ['--project', _PROJECT]
    if pr is not None:
        argv += ['--pr', pr]
    return parse_ns(
        'plan-marshall',
        'workflow-integration-sonar',
        'sonar.py',
        'read_open_issues',
        *argv,
    )


def _rows(plan_id):
    """Read back the plan's attestation rows, via the producer's own resolver."""
    from _findings_core import get_findings_dir

    marker = get_findings_dir(plan_id) / 'sonar-scan-summary.jsonl'
    if not marker.exists():
        return []
    return [json.loads(line) for line in marker.read_text(encoding='utf-8').splitlines() if line.strip()]


@pytest.fixture(autouse=True)
def _stub_sonar_configured():
    with patch.object(sonar_mod, '_sonar_credential_missing', return_value=''):
        yield


def _settled(head=_HEAD):
    """The CE wait settled and the working tree is at ``head``."""
    return (
        patch.object(sonar_mod, '_wait_for_ce_ready', return_value={'count_status': 'confirmed'}),
        patch.object(sonar_mod, '_resolve_head_revision', return_value=head),
    )


class TestRevisionOfTheCountedHead:
    """An analysis of the head being counted is the only confirmed state."""

    def test_analysis_of_the_counted_head_confirms_the_zero(self, monkeypatch, plan_context):
        plan_context.plan_dir_for('rev-match')
        _install_api(monkeypatch, {_PR_LIST: _pr_listing(_HEAD)})
        ce, head = _settled()

        with (
            ce,
            head,
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': [], 'total': 0}),
        ):
            result = sonar_mod.cmd_fetch_findings(_fetch_args('rev-match'))

        assert result['count_status'] == 'confirmed'
        assert result['new_code_issue_count'] == 0
        assert result['analysis_revision'] == _HEAD

    def test_the_attestation_row_records_the_analysis_revision(self, monkeypatch, plan_context):
        plan_context.plan_dir_for('rev-row')
        _install_api(monkeypatch, {_PR_LIST: _pr_listing(_HEAD)})
        ce, head = _settled()

        with (
            ce,
            head,
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': [], 'total': 0}),
        ):
            sonar_mod.cmd_fetch_findings(_fetch_args('rev-row'))

        row = _rows('rev-row')[-1]
        assert row['count_status'] == 'confirmed'
        assert row['analysis_revision'] == _HEAD
        assert 'scanned_sha' in row, 'the analysis revision joins the scanned_sha the row already records'

    def test_the_revision_is_read_from_this_pulls_request_entry(self, monkeypatch, plan_context):
        plan_context.plan_dir_for('rev-pr')
        client = _install_api(
            monkeypatch,
            {
                _PR_LIST: {
                    'pullRequests': [
                        {'key': '7', 'branch': 'other', 'commit': {'sha': _STALE}},
                        {'key': '42', 'branch': 'fix/lb-58-verification-truth', 'commit': {'sha': _HEAD}},
                    ]
                }
            },
        )
        ce, head = _settled()

        with (
            ce,
            head,
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': [], 'total': 0}),
        ):
            result = sonar_mod.cmd_fetch_findings(_fetch_args('rev-pr'))

        assert client.calls[0][0] == _PR_LIST
        assert client.calls[0][1]['project'] == _PROJECT
        assert result['analysis_revision'] == _HEAD


class TestStaleAnalysis:
    """An analysis of another revision never stands in for this one."""

    def test_another_revision_is_undecidable_never_confirmed(self, monkeypatch, plan_context):
        plan_context.plan_dir_for('rev-stale')
        _install_api(monkeypatch, {_PR_LIST: _pr_listing(_STALE)})
        ce, head = _settled()

        with (
            ce,
            head,
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': [], 'total': 0}),
        ):
            result = sonar_mod.cmd_fetch_findings(_fetch_args('rev-stale'))

        assert result['count_status'] == 'undecidable'
        assert result['new_code_issue_count'] is None
        assert result['count_status_reason'].startswith('stale_analysis')
        assert result['analysis_revision'] == _STALE
        assert result['head_revision'] == _HEAD
        assert _STALE in result['count_status_reason']
        assert _HEAD in result['count_status_reason']

    def test_a_stale_analysis_is_never_enumerated(self, monkeypatch, plan_context):
        plan_context.plan_dir_for('rev-stale-enum')
        _install_api(monkeypatch, {_PR_LIST: _pr_listing(_STALE)})
        ce, head = _settled()

        with ce, head, patch.object(sonar_mod, '_fetch_issues') as fetch:
            sonar_mod.cmd_fetch_findings(_fetch_args('rev-stale-enum'))

        fetch.assert_not_called()

    def test_the_stale_row_carries_both_revisions(self, monkeypatch, plan_context):
        plan_context.plan_dir_for('rev-stale-row')
        _install_api(monkeypatch, {_PR_LIST: _pr_listing(_STALE)})
        ce, head = _settled()

        with (
            ce,
            head,
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': [], 'total': 0}),
        ):
            sonar_mod.cmd_fetch_findings(_fetch_args('rev-stale-row'))

        row = _rows('rev-stale-row')[-1]
        assert row['count_status'] == 'undecidable'
        assert row['analysis_revision'] == _STALE
        assert row['head_revision'] == _HEAD


class TestUnreportedRevision:
    """A revision nothing reports leaves the count unconfirmed."""

    def test_a_pull_request_entry_without_a_commit_is_undecidable(self, monkeypatch, plan_context):
        plan_context.plan_dir_for('rev-nocommit')
        _install_api(monkeypatch, {_PR_LIST: _pr_listing(with_commit=False)})
        ce, head = _settled()

        with (
            ce,
            head,
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': [], 'total': 0}),
        ):
            result = sonar_mod.cmd_fetch_findings(_fetch_args('rev-nocommit'))

        assert result['count_status'] == 'undecidable'
        assert result['count_status_reason'] == 'analysis_revision_unavailable'

    def test_a_commit_without_a_sha_is_undecidable(self, monkeypatch, plan_context):
        plan_context.plan_dir_for('rev-nosha')
        _install_api(monkeypatch, {_PR_LIST: _pr_listing(with_commit=True)})
        ce, head = _settled()

        with (
            ce,
            head,
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': [], 'total': 0}),
        ):
            result = sonar_mod.cmd_fetch_findings(_fetch_args('rev-nosha'))

        assert result['count_status'] == 'undecidable'
        assert result['count_status_reason'] == 'analysis_revision_unavailable'

    def test_a_rejected_revision_read_is_undecidable(self, monkeypatch, plan_context):
        plan_context.plan_dir_for('rev-auth')
        _install_api(monkeypatch, {_PR_LIST: _providers_core.RestClientError(401, 'unauthorized')})
        ce, head = _settled()

        with (
            ce,
            head,
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': [], 'total': 0}),
        ):
            result = sonar_mod.cmd_fetch_findings(_fetch_args('rev-auth'))

        assert result['count_status'] == 'undecidable'
        assert 'HTTP 401' in result['count_status_reason']

    def test_an_unresolvable_head_is_undecidable(self, monkeypatch, plan_context):
        plan_context.plan_dir_for('rev-nohead')
        _install_api(monkeypatch, {_PR_LIST: _pr_listing(_HEAD)})
        ce, head = _settled(head='')

        with (
            ce,
            head,
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': [], 'total': 0}),
        ):
            result = sonar_mod.cmd_fetch_findings(_fetch_args('rev-nohead'))

        assert result['count_status'] == 'undecidable'
        assert result['count_status_reason'] == 'head_revision_unavailable'


class TestPlanlessReadRevision:
    """The plan-less read carries the same truth, or it reports no count."""

    def test_a_stale_analysis_blocks_a_confirmed_read(self, monkeypatch, plan_context):
        plan_context.plan_dir_for('rev-read-stale')
        _install_api(monkeypatch, {_PR_LIST: _pr_listing(_STALE)})
        ce, head = _settled()

        with (
            ce,
            head,
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': [], 'total': 0}),
        ):
            result = sonar_mod.cmd_read_open_issues(_read_args())

        assert result['count_status'] == 'undecidable'
        assert result['open_issue_count'] is None
        assert result['count_status_reason'].startswith('stale_analysis')
        assert result['analysis_revision'] == _STALE
        assert result['head_revision'] == _HEAD

    def test_a_matching_analysis_keeps_the_read_confirmed(self, monkeypatch, plan_context):
        plan_context.plan_dir_for('rev-read-match')
        _install_api(monkeypatch, {_PR_LIST: _pr_listing(_HEAD)})
        ce, head = _settled()

        with (
            ce,
            head,
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': [], 'total': 0}),
        ):
            result = sonar_mod.cmd_read_open_issues(_read_args())

        assert result['count_status'] == 'confirmed'
        assert result['open_issue_count'] == 0


class TestBranchReadOutOfScope:
    """A fetch with no pull request keeps the CE contract, and says so.

    The provider reports no analysed revision for a branch read
    (``/api/project_analyses/search`` describes the DEFAULT branch, never the
    branch being counted), so comparing it with the working tree's HEAD would
    compare two unrelated trees and report every branch fetch undecidable. Such a
    read answers ``confirmed`` on a settled CE and leaves both revisions blank.
    """

    def test_a_branch_fetch_consults_no_revision_endpoint(self, monkeypatch, plan_context):
        plan_context.plan_dir_for('rev-branch')
        client = _install_api(monkeypatch, {})

        with (
            patch.object(sonar_mod, '_wait_for_ce_ready', return_value={'count_status': 'confirmed'}),
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': [], 'total': 0}),
            patch.object(sonar_mod, '_resolve_head_revision') as head,
        ):
            result = sonar_mod.cmd_fetch_findings(_fetch_args('rev-branch', pr=None))

        assert result['count_status'] == 'confirmed'
        assert result['analysis_revision'] == ''
        assert result['head_revision'] == ''
        assert client.calls == [], 'a branch read has no reported revision to read'
        head.assert_not_called()

    def test_a_planless_branch_read_consults_no_revision_endpoint(self, monkeypatch, plan_context):
        plan_context.plan_dir_for('rev-branch-read')
        client = _install_api(monkeypatch, {})

        with (
            patch.object(sonar_mod, '_wait_for_ce_ready', return_value={'count_status': 'confirmed'}),
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': [], 'total': 0}),
        ):
            result = sonar_mod.cmd_read_open_issues(_read_args(pr=None))

        assert result['count_status'] == 'confirmed'
        assert result['open_issue_count'] == 0
        assert client.calls == []


class TestHeadResolution:
    """The comparison head is the branch under review, not the caller's checkout."""

    def test_the_pulls_request_branch_is_tried_before_the_working_tree_head(self, monkeypatch):
        seen = []

        def fake_rev_parse(ref):
            seen.append(ref)
            return _HEAD if ref == 'refs/heads/fix/x' else ''

        monkeypatch.setattr(sonar_mod, '_git_rev_parse', fake_rev_parse)

        assert sonar_mod._resolve_head_revision('fix/x') == _HEAD
        assert seen == ['refs/heads/fix/x']

    def test_the_remote_tracking_ref_answers_when_the_local_branch_is_absent(self, monkeypatch):
        seen = []

        def fake_rev_parse(ref):
            seen.append(ref)
            return _STALE if ref == 'refs/remotes/origin/fix/x' else ''

        monkeypatch.setattr(sonar_mod, '_git_rev_parse', fake_rev_parse)

        assert sonar_mod._resolve_head_revision('fix/x') == _STALE
        assert seen == ['refs/heads/fix/x', 'refs/remotes/origin/fix/x']

    def test_no_branch_falls_back_to_the_working_tree_head(self, monkeypatch):
        seen = []

        def fake_rev_parse(ref):
            seen.append(ref)
            return _HEAD

        monkeypatch.setattr(sonar_mod, '_git_rev_parse', fake_rev_parse)

        assert sonar_mod._resolve_head_revision(None) == _HEAD
        assert seen == ['HEAD']
