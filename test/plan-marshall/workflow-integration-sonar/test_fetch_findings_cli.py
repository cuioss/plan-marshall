#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for sonar fetch_findings — transmission verbs and dispatch surface.
"""

from __future__ import annotations

from unittest.mock import patch
import pytest
from conftest import get_script_path, run_script
from ci_base import extract_routing_args
from test_fetch_findings_core import sonar_mod


SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-sonar', 'sonar.py')


cmd_fetch_findings = sonar_mod.cmd_fetch_findings


cmd_post_responses = sonar_mod.cmd_post_responses


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


class _FakeSonarClient:
    """Records ``/api/issues/do_transition`` POSTs for the post_responses tests."""

    def __init__(self):
        self.posts = []

    def post(self, path, body=None):
        self.posts.append((path, body))
        return {}

    def close(self):
        pass


class _FailingSonarClient:
    """A Sonar client whose ``do_transition`` POST always raises.

    Records the attempted POST before raising so a test can assert the call was
    attempted, then failed — exercising the "no marker on failure" retry path.
    """

    def __init__(self, exc):
        self.exc = exc
        self.posts = []

    def post(self, path, body=None):
        self.posts.append((path, body))
        raise self.exc

    def close(self):
        pass


# =============================================================================
# post_responses — hash_id-keyed dismissal transitions (Sonar do_transition shape)
# =============================================================================
class TestPostResponses:
    """post_responses maps terminal dispositions to Sonar dismissals, keyed by hash_id."""

    def _stage_one_issue(self, plan_id, issue):
        """File one sonar-issue finding via fetch_findings and return its hash_id."""
        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'success', 'issues': [issue]}
            result = cmd_fetch_findings(_make_args(plan_id))
        return result['stored_hash_ids'][0]

    def test_suppressed_maps_to_wontfix_keyed_by_issue_key(self, plan_context):
        plan_context.plan_dir_for('sonar-respond-wontfix')
        hash_id = self._stage_one_issue('sonar-respond-wontfix', _issue(key='ISSUE-77'))

        from _findings_core import resolve_finding

        resolve_finding('sonar-respond-wontfix', hash_id, 'suppressed', detail='Documented false positive.')

        import _providers_core

        fake = _FakeSonarClient()
        with patch.object(_providers_core, 'get_authenticated_client', return_value=fake):
            result = cmd_post_responses(_make_args('sonar-respond-wontfix'))

        assert result['status'] == 'success'
        assert result['count_responded'] == 1
        assert result['count_failed'] == 0
        assert result['responded'][0]['hash_id'] == hash_id
        assert result['responded'][0]['issue_key'] == 'ISSUE-77'
        assert result['responded'][0]['transition'] == 'wontfix'
        # The dismissal is transmitted keyed by the issue key parsed from detail.
        assert len(fake.posts) == 1
        path, body = fake.posts[0]
        assert path == '/api/issues/do_transition'
        assert body == {'issue': 'ISSUE-77', 'transition': 'wontfix'}

    def test_rejected_maps_to_falsepositive(self, plan_context):
        plan_context.plan_dir_for('sonar-respond-fp')
        hash_id = self._stage_one_issue('sonar-respond-fp', _issue(key='ISSUE-88'))

        from _findings_core import resolve_finding

        resolve_finding('sonar-respond-fp', hash_id, 'rejected', detail='Not a real issue.')

        import _providers_core

        fake = _FakeSonarClient()
        with patch.object(_providers_core, 'get_authenticated_client', return_value=fake):
            result = cmd_post_responses(_make_args('sonar-respond-fp'))

        assert result['count_responded'] == 1
        assert fake.posts[0][1] == {'issue': 'ISSUE-88', 'transition': 'falsepositive'}

    def test_fixed_finding_gets_no_sonar_action(self, plan_context):
        """A finding resolved ``fixed`` is cleared in code, not dismissed — no do_transition."""
        plan_context.plan_dir_for('sonar-respond-fixed')
        hash_id = self._stage_one_issue('sonar-respond-fixed', _issue(key='ISSUE-99'))

        from _findings_core import resolve_finding

        resolve_finding('sonar-respond-fixed', hash_id, 'fixed', detail='Fixed in code.')

        import _providers_core

        fake = _FakeSonarClient()
        with patch.object(_providers_core, 'get_authenticated_client', return_value=fake):
            result = cmd_post_responses(_make_args('sonar-respond-fixed'))

        assert result['status'] == 'success'
        assert result['count_responded'] == 0
        assert fake.posts == []

    def test_pending_finding_is_not_dismissed(self, plan_context):
        """A still-pending (un-triaged) finding gets no Sonar action."""
        plan_context.plan_dir_for('sonar-respond-pending')
        self._stage_one_issue('sonar-respond-pending', _issue(key='ISSUE-55'))  # left pending

        import _providers_core

        fake = _FakeSonarClient()
        with patch.object(_providers_core, 'get_authenticated_client', return_value=fake):
            result = cmd_post_responses(_make_args('sonar-respond-pending'))

        assert result['status'] == 'success'
        assert result['count_responded'] == 0
        assert fake.posts == []

    def test_responded_marker_persisted_after_successful_post(self, plan_context):
        """A successful dismissal stamps the finding with responded + responded_at."""
        plan_context.plan_dir_for('sonar-respond-marker')
        hash_id = self._stage_one_issue('sonar-respond-marker', _issue(key='ISSUE-11'))

        from _findings_core import get_finding, resolve_finding

        resolve_finding('sonar-respond-marker', hash_id, 'suppressed', detail='Documented false positive.')

        import _providers_core

        fake = _FakeSonarClient()
        with patch.object(_providers_core, 'get_authenticated_client', return_value=fake):
            cmd_post_responses(_make_args('sonar-respond-marker'))

        stored = get_finding('sonar-respond-marker', hash_id)
        assert stored['status'] == 'success'
        assert stored['responded'] is True
        assert stored['responded_at']

    def test_rerun_skips_already_responded_finding(self, plan_context):
        """A second post_responses pass skips the marked finding — no duplicate POST."""
        plan_context.plan_dir_for('sonar-respond-idempotent')
        hash_id = self._stage_one_issue('sonar-respond-idempotent', _issue(key='ISSUE-22'))

        from _findings_core import resolve_finding

        resolve_finding('sonar-respond-idempotent', hash_id, 'rejected', detail='Not a real issue.')

        import _providers_core

        first = _FakeSonarClient()
        with patch.object(_providers_core, 'get_authenticated_client', return_value=first):
            first_result = cmd_post_responses(_make_args('sonar-respond-idempotent'))

        assert first_result['count_responded'] == 1
        assert len(first.posts) == 1

        second = _FakeSonarClient()
        with patch.object(_providers_core, 'get_authenticated_client', return_value=second):
            second_result = cmd_post_responses(_make_args('sonar-respond-idempotent'))

        assert second_result['count_responded'] == 0
        assert second_result['count_skipped'] == 1
        assert second_result['skipped'][0]['hash_id'] == hash_id
        assert second_result['skipped'][0]['reason'] == 'already responded'
        # No duplicate transmission on the second pass.
        assert second.posts == []

    def test_failed_post_does_not_mark_responded(self, plan_context):
        """A do_transition failure leaves the finding un-marked so it retries next pass."""
        plan_context.plan_dir_for('sonar-respond-retry')
        hash_id = self._stage_one_issue('sonar-respond-retry', _issue(key='ISSUE-33'))

        from _findings_core import get_finding, resolve_finding

        resolve_finding('sonar-respond-retry', hash_id, 'suppressed', detail='Documented false positive.')

        import _providers_core
        from _providers_core import RestClientError

        fake = _FailingSonarClient(RestClientError(500, 'boom'))
        with patch.object(_providers_core, 'get_authenticated_client', return_value=fake):
            result = cmd_post_responses(_make_args('sonar-respond-retry'))

        assert result['count_failed'] == 1
        assert result['count_responded'] == 0
        # The transmission was attempted but failed — the marker must NOT be set.
        assert len(fake.posts) == 1
        stored = get_finding('sonar-respond-retry', hash_id)
        assert stored['status'] == 'success'
        assert stored.get('responded') is not True


# =============================================================================
# CLI plumbing
# =============================================================================
class TestSonarMain:
    def test_help_lists_only_supported_subcommands(self):
        result = run_script(SCRIPT_PATH, '--help')

        assert result.returncode == 0
        assert 'fetch_findings' in result.stdout
        assert 'post_responses' in result.stdout
        # Retired surfaces MUST be absent from the CLI.
        assert 'fetch-and-store' not in result.stdout
        assert 'triage-batch' not in result.stdout

    @pytest.mark.parametrize(
        'argv',
        [
            pytest.param(['triage', '--issue', '{}'], id='triage-rejected'),
            pytest.param(['triage-batch', '--issues', '[]'], id='triage-batch-rejected'),
            pytest.param(
                ['fetch-and-store', '--plan-id', 'x', '--project', 'com.example:proj'],
                id='fetch-and-store-rejected',
            ),
        ],
    )
    def test_retired_subcommand_rejected(self, argv):
        result = run_script(SCRIPT_PATH, *argv)

        assert result.returncode != 0


# =============================================================================
# Regression: subcommand routing must not strip --plan-id
# =============================================================================
class TestFetchFindingsRouting:
    """Regression for the subcommand-routing defect (ported from fetch-and-store).

    sonar.py registers ``fetch_findings`` as a top-level subcommand token (via
    the module-level ``register_subcommands({'fetch_findings', 'post_responses'})``
    call) so that ``extract_routing_args`` locates the subcommand boundary
    correctly. Without that registration, ``fetch_findings`` is not in the
    known-subcommand registry, ``_split_at_subcommand`` treats the whole argv as
    router-level prefix, and the subcommand-level ``--plan-id`` is consumed
    (stripped) at the router layer before reaching the subcommand parser — the
    original bug. These tests assert the post-fix behaviour: the
    subcommand-level ``--plan-id`` and every other subcommand argument survive in
    ``remaining_argv`` so the ``fetch_findings`` subparser can consume them.
    """

    def test_plan_id_immediately_after_subcommand_preserves_pairing(self):
        # The --plan-id flag and its value must remain adjacent so the subparser
        # binds the value to the flag (a stray strip of only the value would
        # leave a dangling --plan-id with no argument).
        _resolved, remaining = extract_routing_args(
            ['fetch_findings', '--plan-id', 'P-123', '--project', 'com.example:proj']
        )

        idx = remaining.index('--plan-id')
        assert remaining[idx + 1] == 'P-123'

    def test_all_subcommand_args_survive_routing(self):
        # Every fetch_findings argument (including optional --pr / --severities)
        # must reach the subparser intact, not just --plan-id.
        argv = [
            'fetch_findings',
            '--plan-id',
            'P-456',
            '--project',
            'com.example:proj',
            '--pr',
            '99',
            '--severities',
            'BLOCKER,CRITICAL',
        ]
        _resolved, remaining = extract_routing_args(argv)

        for token in argv:
            assert token in remaining
        assert _resolved is None

