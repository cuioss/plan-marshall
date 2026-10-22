#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the plan-less Sonar read — ``sonar.py read_open_issues``.

The runbook lane consults a pull request's open Sonar issues before it reports
the pull request ready, and it has no plan directory: it passes ``NO_PLAN`` to
the CI verbs. ``fetch_findings`` cannot serve that call (it takes ``--plan-id``,
reads the plan-local manifest and files findings), so the provider carries a
read that takes a project key and a pull request and RETURNS the enumeration:
the open-issue count, each issue's rule and file, and the ``count_status``
discriminator with its reason on an undecidable read.

Three properties are asserted directly, because each is a way a "count" can lie:

* the read persists NOTHING — no plan directory, no findings entry, no
  scan-summary marker;
* a count is only ever reported from a settled analysis (a CE timeout or an
  auth/REST failure yields ``count: null`` with ``undecidable``, never ``0``);
* an unconfigured provider is the typed ``unconfigured`` status, distinct from a
  read that failed.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from conftest import load_script_module, parse_ns

sonar_mod = load_script_module('plan-marshall', 'workflow-integration-sonar', 'sonar.py', 'sonar_read_mod')

#: Resolved at import: a read verb the provider does not publish is a collection
#: error naming the missing attribute, which is the failure this module is written
#: to produce before the verb exists. The module registers under its OWN
#: ``sys.modules`` name: the sibling modules register this script as ``sonar_mod``
#: and patch it by that string target, so claiming the same name here would leave
#: their patches landing on a different module object than the one they call.
cmd_read_open_issues = sonar_mod.cmd_read_open_issues

_SUPPRESSABLE_RULE = 'java:S1135'


@pytest.fixture(autouse=True)
def _stub_sonar_configured():
    """Default the fail-loud credential guard to "configured".

    The credentials sandbox holds no real credential, so without this stub every
    read would take the ``unconfigured`` branch. The test that exercises that
    branch re-patches the same target inside a ``with`` block, which takes
    precedence.
    """
    with patch.object(sonar_mod, '_sonar_credential_missing', return_value=''):
        yield


def _args(*extra: str):
    """Build the namespace through the script's own parser.

    No ``--plan-id`` is ever passed: the read has none to pass, and a namespace
    the parser produced carries the real defaults rather than a hand-built shape.
    """
    return parse_ns(
        'plan-marshall',
        'workflow-integration-sonar',
        'sonar.py',
        'read_open_issues',
        '--project',
        'com.example:proj',
        *extra,
    )


def _issue(key='ISSUE-1', rule='java:S99999', file='src/Main.java', severities=('MAJOR', 'BUG')):
    severity, type_ = severities
    return {
        'key': key,
        'type': type_,
        'severity': severity,
        'file': file,
        'line': 42,
        'rule': rule,
        'message': 'Possible null dereference',
        'component': f'com.example:proj:{file}',
    }


def _snapshot(root: Path) -> set[str]:
    return {str(path.relative_to(root)) for path in root.rglob('*')}


class TestReadPersistsNothing:
    """The read returns to its caller and writes nothing on disk."""

    def test_read_without_a_plan_directory_leaves_no_file_behind(self, plan_context):
        before = _snapshot(plan_context.fixture_dir)
        args = _args('--pr', '42')
        assert not hasattr(args, 'plan_id'), 'the read must not require a plan id'

        with (
            patch.object(sonar_mod, '_wait_for_ce_ready', return_value={'count_status': 'confirmed'}),
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': [_issue()]}),
        ):
            result = cmd_read_open_issues(args)

        assert result['status'] == 'success'
        assert _snapshot(plan_context.fixture_dir) == before, 'the plan-less read wrote a file'

    def test_read_returns_the_issue_keys_for_a_later_dismissal(self, plan_context):
        with (
            patch.object(sonar_mod, '_wait_for_ce_ready', return_value={'count_status': 'confirmed'}),
            patch.object(
                sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': [_issue(key='ISSUE-77')]}
            ),
        ):
            result = cmd_read_open_issues(_args('--pr', '42'))

        assert [issue['key'] for issue in result['issues']] == ['ISSUE-77']


class TestConfirmedRead:
    """A settled analysis yields a confirmed count with the issues' rules and files."""

    def test_open_issues_return_their_count_and_rules(self):
        issues = [_issue(key='K1', rule='java:S1234'), _issue(key='K2', rule='python:S1481')]

        with (
            patch.object(sonar_mod, '_wait_for_ce_ready', return_value={'count_status': 'confirmed'}),
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': issues}),
        ):
            result = cmd_read_open_issues(_args('--pr', '42'))

        assert result['count_status'] == 'confirmed'
        assert result['open_issue_count'] == 2
        assert result['rules'] == ['java:S1234', 'python:S1481']
        assert result['files'] == ['src/Main.java']
        assert result['pull_request'] == '42'

    def test_an_issue_the_producer_pre_filter_would_drop_is_still_counted(self):
        """The read reports what Sonar reports; the pre-filter belongs to the producer."""
        issues = [_issue(key='K1', rule=_SUPPRESSABLE_RULE)]

        with (
            patch.object(sonar_mod, '_wait_for_ce_ready', return_value={'count_status': 'confirmed'}),
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': issues}),
        ):
            result = cmd_read_open_issues(_args('--pr', '42'))

        assert result['open_issue_count'] == 1
        assert result['rules'] == [_SUPPRESSABLE_RULE]

    def test_a_settled_analysis_with_no_issue_is_a_confirmed_zero(self):
        with (
            patch.object(sonar_mod, '_wait_for_ce_ready', return_value={'count_status': 'confirmed'}),
            patch.object(sonar_mod, '_fetch_issues', return_value={'status': 'success', 'issues': []}),
        ):
            result = cmd_read_open_issues(_args('--pr', '42'))

        assert result['count_status'] == 'confirmed'
        assert result['open_issue_count'] == 0


class TestUndecidableRead:
    """A read that cannot be taken reports null with a reason — never a false zero."""

    def test_an_analysis_that_never_settles_is_undecidable(self):
        poll = {'timed_out': True, 'last_data': {'ce_state': 'IN_PROGRESS', 'queue_length': 2}}

        with (
            patch.object(sonar_mod, 'poll_until', return_value=poll),
            patch.object(sonar_mod, '_fetch_issues') as fetch,
        ):
            result = cmd_read_open_issues(_args('--pr', '42', '--ce-wait-timeout', '30'))

        assert result['count_status'] == 'undecidable'
        assert result['open_issue_count'] is None
        assert result['open_issue_count'] != 0
        assert '30s' in result['count_status_reason']
        fetch.assert_not_called()

    def test_a_rejected_credential_on_the_ce_poll_is_undecidable(self):
        poll = {'timed_out': False, 'error': 'Sonar API error: HTTP 401', 'last_data': {}}

        with patch.object(sonar_mod, 'poll_until', return_value=poll):
            result = cmd_read_open_issues(_args('--pr', '42'))

        assert result['count_status'] == 'undecidable'
        assert result['open_issue_count'] is None
        assert 'HTTP 401' in result['count_status_reason']

    def test_a_rejected_credential_on_the_issue_fetch_is_undecidable(self):
        failure = {'status': 'error', 'message': 'Sonar API error: HTTP 403'}

        with (
            patch.object(sonar_mod, '_wait_for_ce_ready', return_value={'count_status': 'confirmed'}),
            patch.object(sonar_mod, '_fetch_issues', return_value=failure),
        ):
            result = cmd_read_open_issues(_args('--pr', '42'))

        assert result['count_status'] == 'undecidable'
        assert result['open_issue_count'] is None
        assert result['open_issue_count'] != 0
        assert 'HTTP 403' in result['count_status_reason']


class TestUnconfigured:
    """No Sonar configuration is the typed status, not a count."""

    def test_an_unconfigured_project_is_unconfigured_not_a_count(self):
        with patch.object(sonar_mod, '_sonar_credential_missing', return_value='No credentials configured'):
            result = cmd_read_open_issues(_args('--pr', '42'))

        assert result['status'] == 'unconfigured'
        assert result['operation'] == 'read_open_issues'
        assert result['provider'] == 'sonar'
        assert 'open_issue_count' not in result
        assert 'count_status' not in result
