#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for sonar fetch_findings — fetch semantics, counts, and scoping.
"""

from __future__ import annotations

import json
from unittest.mock import patch
import pytest
from conftest import load_script_module


# Resolved by (bundle, skill, file) and REGISTERED under ``sonar_mod``: the
# ``patch('sonar_mod....')` targets throughout this module are string targets, so
# they resolve the name through ``sys.modules`` and the registration is what makes
# them reachable. Nothing imports the name plainly, so the registration displaces
# nothing.
sonar_mod = load_script_module('plan-marshall', 'workflow-integration-sonar', 'sonar.py', 'sonar_mod')


cmd_fetch_findings = sonar_mod.cmd_fetch_findings


_wait_for_ce_ready = sonar_mod._wait_for_ce_ready


@pytest.fixture(autouse=True)
def _stub_sonar_configured():
    """Default the fail-loud credential guard to "configured".

    ``cmd_fetch_findings`` / ``cmd_post_responses`` call ``_sonar_credential_missing``
    first and short-circuit to a typed ``unconfigured`` status when no credential is
    resolvable. The autouse credentials sandbox means no real credential is present,
    so without this stub every happy-path test would take the unconfigured branch.
    Tests that exercise the unconfigured path re-patch the same target inside a
    ``with`` block, which takes precedence.
    """
    with patch('sonar_mod._sonar_credential_missing', return_value=''):
        yield


# =============================================================================
# Helpers
# =============================================================================
def _make_args(plan_id, project='com.example:proj', pr=None, severities=None, types=None):
    class _Args:
        pass

    a = _Args()
    a.plan_id = plan_id
    a.project = project
    a.pr = pr
    a.severities = severities
    a.types = types
    return a


def _issue(
    key='ISSUE-1',
    type_='BUG',
    severity='MAJOR',
    file='src/Main.java',
    line=42,
    rule='java:S99999',
    message='Possible null dereference',
    component='com.example:proj:src/Main.java',
):
    """Build one Sonar issue payload dict, overriding only the fields a test cares about."""
    return {
        'key': key,
        'type': type_,
        'severity': severity,
        'file': file,
        'line': line,
        'rule': rule,
        'message': message,
        'component': component,
    }


# =============================================================================
# Scan-summary marker helper
# =============================================================================
def _read_scan_summary_rows(plan_id):
    """Read every attestation row from the plan's sonar-scan-summary.jsonl.

    Resolves the marker via the SAME shared findings-dir resolver the producer
    uses (``_findings_core.get_findings_dir``), so the test reads back exactly
    where ``_write_scan_summary`` wrote. Returns ``[]`` when the file is absent.
    """
    from _findings_core import get_findings_dir

    marker_path = get_findings_dir(plan_id) / 'sonar-scan-summary.jsonl'
    if not marker_path.exists():
        return []
    rows = []
    for line in marker_path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


# =============================================================================
# fetch_findings flow
# =============================================================================
class TestFetchFindings:
    """fetch_findings writes one sonar-issue finding per surviving issue."""

    def test_fetch_findings_persists_findings(self, plan_context):
        issues_payload = [_issue()]
        plan_context.plan_dir_for('sonar-stage-1')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'success', 'issues': issues_payload}
            result = cmd_fetch_findings(_make_args('sonar-stage-1'))

        assert result['status'] == 'success'
        assert result['count_fetched'] == 1
        assert result['count_skipped_suppressable'] == 0
        assert result['count_stored'] == 1

        from _findings_core import query_findings

        q = query_findings('sonar-stage-1', finding_type='sonar-issue')
        assert q['filtered_count'] == 1
        stored = q['findings'][0]
        assert stored['type'] == 'sonar-issue'
        assert stored['rule'] == 'java:S99999'
        assert stored['severity'] == 'error'  # MAJOR → error
        assert stored['module'] == 'com.example:proj'
        # The trusted structured metadata lives in detail (rule, key, ...).
        assert 'rule: java:S99999' in stored['detail']
        # The untrusted Sonar message is quarantined under raw_input.{message}, NOT in detail.
        assert 'Possible null dereference' not in stored['detail']
        assert stored['raw_input']['message'] == 'Possible null dereference'

    def test_fetch_findings_skips_suppressable(self, plan_context):
        # Take a rule from the live SUPPRESSABLE_RULES dict so the test exercises
        # real configuration. An empty dict would make the counter assertion
        # vacuous, so the precondition is asserted rather than skipped.
        # Read off the loaded module object rather than importing the registered
        # name plainly: a name that is both file-loaded and plainly imported is a
        # live displacement hazard, and the loader-contract guard reports it.
        SUPPRESSABLE_RULES = sonar_mod.SUPPRESSABLE_RULES

        assert SUPPRESSABLE_RULES, 'No suppressable rules configured in sonar-rules.json'
        rule = next(iter(SUPPRESSABLE_RULES.keys()))

        issues_payload = [_issue(type_='CODE_SMELL', severity='MINOR', line=1, rule=rule, message='m')]
        plan_context.plan_dir_for('sonar-stage-skip')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'success', 'issues': issues_payload}
            result = cmd_fetch_findings(_make_args('sonar-stage-skip'))

        assert result['count_fetched'] == 1
        assert result['count_skipped_suppressable'] == 1
        assert result['count_stored'] == 0

    def test_fetch_findings_propagates_provider_error(self, plan_context):
        plan_context.plan_dir_for('sonar-stage-err')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'error', 'message': 'HTTP 401'}
            result = cmd_fetch_findings(_make_args('sonar-stage-err'))

        assert result['status'] == 'error'

    def test_fetch_findings_count_mismatch_produces_qgate_finding(self, plan_context):
        """When count_stored != expected_stored, a (producer-mismatch) Q-Gate
        finding must be recorded with type=sonar-issue and source=qgate."""
        issues_payload = [
            _issue(),
            _issue(
                key='ISSUE-2',
                severity='CRITICAL',
                file='src/Other.java',
                line=7,
                rule='java:S88888',
                message='Race condition',
                component='com.example:proj:src/Other.java',
            ),
        ]
        plan_context.plan_dir_for('sonar-stage-mismatch')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'success', 'issues': issues_payload}
            with patch('_findings_core.add_finding') as mock_add:

                def _side_effect(**kwargs):
                    if mock_add.call_count == 1:
                        return {'status': 'error', 'message': 'simulated store failure'}
                    return {'status': 'success', 'hash_id': 'h-' + str(mock_add.call_count)}

                mock_add.side_effect = _side_effect
                result = cmd_fetch_findings(_make_args('sonar-stage-mismatch'))

        assert result['status'] == 'success'
        assert result['count_fetched'] == 2
        assert result['count_skipped_suppressable'] == 0
        assert result['count_stored'] == 1

        from _findings_core import query_qgate_findings

        q = query_qgate_findings('sonar-stage-mismatch', phase='5-execute')
        assert q['filtered_count'] == 1
        qf = q['findings'][0]
        assert qf['title'].startswith('(producer-mismatch)')
        assert qf['source'] == 'qgate'
        assert qf['type'] == 'sonar-issue'


# =============================================================================
# Verified count + undecidable state + unconditional marker write
# =============================================================================
class TestVerifiedCount:
    """fetch_findings reports a verified new_code_issue_count with a
    confirmed/undecidable discriminator, and ALWAYS writes one scan-summary
    attestation row (including at count==0 and on undecidable)."""

    def test_confirmed_count_matches_fetched_issues(self, plan_context):
        plan_context.plan_dir_for('sonar-count-confirmed')
        issues_payload = [_issue(), _issue(key='ISSUE-2', file='src/Other.java')]

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'success', 'issues': issues_payload}
            result = cmd_fetch_findings(_make_args('sonar-count-confirmed'))

        assert result['count_status'] == 'confirmed'
        assert result['new_code_issue_count'] == 2

    def test_confirmed_zero_is_a_real_zero_not_undecidable(self, plan_context):
        # An empty PR-scoped new-code result against a settled CE is a CONFIRMED
        # zero, never undecidable — the core defect this contract guards against.
        plan_context.plan_dir_for('sonar-count-zero')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'success', 'issues': []}
            result = cmd_fetch_findings(_make_args('sonar-count-zero'))

        assert result['count_status'] == 'confirmed'
        assert result['new_code_issue_count'] == 0

    def test_confirmed_zero_writes_marker_row(self, plan_context):
        # The attestation marker is written even at count==0 so a verified zero
        # is a positive on-disk fact (an absent file means "not checked").
        plan_context.plan_dir_for('sonar-marker-zero')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'success', 'issues': []}
            result = cmd_fetch_findings(_make_args('sonar-marker-zero'))

        rows = _read_scan_summary_rows('sonar-marker-zero')
        assert len(rows) == 1
        assert rows[0]['count_status'] == 'confirmed'
        assert rows[0]['new_code_issue_count'] == 0
        assert result['scan_summary_path'].endswith('sonar-scan-summary.jsonl')

    def test_ce_timeout_reports_undecidable_null_count_and_writes_marker(self, plan_context):
        # CE never settled within budget → new_code_issue_count is null,
        # count_status undecidable, _fetch_issues is NEVER called, and the
        # undecidable marker row is still written.
        plan_context.plan_dir_for('sonar-undecidable-timeout')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {
                'count_status': 'undecidable',
                'count_status_reason': 'CE analysis not DONE within 600s',
            }
            result = cmd_fetch_findings(_make_args('sonar-undecidable-timeout'))

        assert result['count_status'] == 'undecidable'
        assert result['new_code_issue_count'] is None
        assert 'not DONE' in result['count_status_reason']
        mock_fetch.assert_not_called()

        rows = _read_scan_summary_rows('sonar-undecidable-timeout')
        assert len(rows) == 1
        assert rows[0]['count_status'] == 'undecidable'
        assert rows[0]['new_code_issue_count'] is None
        assert rows[0]['count_status_reason'] == 'CE analysis not DONE within 600s'

    def test_fetch_rest_failure_reports_undecidable_and_writes_marker(self, plan_context):
        # A REST/auth failure during the issue fetch (after CE settled) is
        # undecidable with a null count, never a false 0, and writes a marker.
        plan_context.plan_dir_for('sonar-undecidable-fetch')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'error', 'message': 'Sonar API error: HTTP 401'}
            result = cmd_fetch_findings(_make_args('sonar-undecidable-fetch'))

        assert result['count_status'] == 'undecidable'
        assert result['new_code_issue_count'] is None
        assert result['count_status_reason'] == 'Sonar API error: HTTP 401'

        rows = _read_scan_summary_rows('sonar-undecidable-fetch')
        assert len(rows) == 1
        assert rows[0]['count_status'] == 'undecidable'
        assert rows[0]['new_code_issue_count'] is None

    def test_confirmed_run_writes_count_in_marker(self, plan_context):
        # A confirmed non-zero run records the real count in the marker row.
        plan_context.plan_dir_for('sonar-marker-count')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'success', 'issues': [_issue()]}
            cmd_fetch_findings(_make_args('sonar-marker-count'))

        rows = _read_scan_summary_rows('sonar-marker-count')
        assert len(rows) == 1
        assert rows[0]['count_status'] == 'confirmed'
        assert rows[0]['new_code_issue_count'] == 1


# =============================================================================
# PR scoping — --pr forwarded to BOTH the CE lookup and the issue query
# =============================================================================
class TestPrScoping:
    """A supplied --pr must scope BOTH the CE-readiness lookup and the new-code
    issue enumeration, and surface on the marker row, so the count is a
    confirmed PR-scoped count rather than a whole-project one."""

    def test_pr_forwarded_to_ce_wait_and_issue_query(self, plan_context):
        plan_context.plan_dir_for('sonar-pr-scope')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'success', 'issues': []}
            result = cmd_fetch_findings(_make_args('sonar-pr-scope', pr='123'))

        # CE-readiness wait received the pr (2nd positional arg).
        assert mock_wait.call_args.args[1] == '123'
        # Issue fetch received the pr (2nd positional arg).
        assert mock_fetch.call_args.args[1] == '123'
        assert result['pull_request'] == '123'

    def test_pr_recorded_on_marker_row(self, plan_context):
        plan_context.plan_dir_for('sonar-pr-marker')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'success', 'issues': []}
            cmd_fetch_findings(_make_args('sonar-pr-marker', pr='456'))

        rows = _read_scan_summary_rows('sonar-pr-marker')
        assert rows[0]['pr'] == '456'

    def test_pr_forwarded_to_ce_wait_on_undecidable_path(self, plan_context):
        # Even when CE is undecidable, the pr must have reached the CE lookup
        # and be recorded on the undecidable marker row.
        plan_context.plan_dir_for('sonar-pr-undecidable')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait:
            mock_wait.return_value = {
                'count_status': 'undecidable',
                'count_status_reason': 'CE analysis not DONE within 600s',
            }
            cmd_fetch_findings(_make_args('sonar-pr-undecidable', pr='789'))

        assert mock_wait.call_args.args[1] == '789'
        rows = _read_scan_summary_rows('sonar-pr-undecidable')
        assert rows[0]['pr'] == '789'

    def test_no_pr_reports_none(self, plan_context):
        plan_context.plan_dir_for('sonar-no-pr')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'success', 'issues': []}
            result = cmd_fetch_findings(_make_args('sonar-no-pr'))

        assert result['pull_request'] == 'none'
        rows = _read_scan_summary_rows('sonar-no-pr')
        assert rows[0]['pr'] is None

