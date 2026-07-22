# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for workflow-integration-sonar sonar.py — two-verb provider contract.

The provider surface is exactly two pure, zero-LLM verbs:

- ``fetch_findings`` — CE-readiness wait + fetch gate-blocking new-code issues +
  suppressable-rules pre-filter + file one ``sonar-issue`` finding per surviving
  issue; the untrusted Sonar ``message`` is quarantined under
  ``raw_input.{message}`` (never embedded raw in the top-level ``detail``)
- ``post_responses`` — apply already-decided triage dispositions back to Sonar via
  ``/api/issues/do_transition`` (``suppressed`` → ``wontfix``, ``rejected`` →
  ``falsepositive``; ``fixed`` / ``accepted`` / ``taken_into_account`` get no
  action), keyed by each finding's own ``hash_id``

Both verbs FAIL LOUD when no Sonar credential is configured — a typed
``unconfigured`` status, never a silent success.
"""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-sonar', 'sonar.py')

_path = Path(SCRIPT_PATH)
_spec = importlib.util.spec_from_file_location('sonar_mod', _path)
assert _spec is not None and _spec.loader is not None
sonar_mod = importlib.util.module_from_spec(_spec)
sys.modules['sonar_mod'] = sonar_mod
_spec.loader.exec_module(sonar_mod)

_is_suppressable = sonar_mod._is_suppressable
_map_severity = sonar_mod._map_severity
cmd_fetch_findings = sonar_mod.cmd_fetch_findings
cmd_post_responses = sonar_mod.cmd_post_responses
_wait_for_ce_ready = sonar_mod._wait_for_ce_ready
_resolve_ce_wait_timeout = sonar_mod._resolve_ce_wait_timeout

# Importing sonar.py (above) runs its module-level ``register_subcommands({'fetch_findings', 'post_responses'})``
# call, which extends the shared ci_base subcommand registry. ``extract_routing_args`` is the
# router-level pre-parser that the bug stripped ``--plan-id`` through; the regression test below
# exercises it directly.
from ci_base import extract_routing_args  # noqa: E402,I001


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


def _issue(key='ISSUE-1', type_='BUG', severity='MAJOR', file='src/Main.java', line=42,
           rule='java:S99999', message='Possible null dereference',
           component='com.example:proj:src/Main.java'):
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
# Pre-filter helpers
# =============================================================================


class TestIsSuppressable:
    """The pre-filter drops issues already documented as suppressable."""

    def test_always_fix_type_never_suppressed(self):
        # VULNERABILITY is in always_fix_types — it must NEVER be suppressed
        # even if the rule appears in suppressable_rules.
        assert not _is_suppressable('java:S2076', 'src/X.java', 'VULNERABILITY')

    def test_unknown_rule_passes_through(self):
        assert not _is_suppressable('java:S99999', 'src/X.java', 'CODE_SMELL')


class TestMapSeverity:
    @pytest.mark.parametrize(
        'sonar_severity,expected',
        [
            ('BLOCKER', 'error'),
            ('CRITICAL', 'error'),
            ('MAJOR', 'error'),
            ('MINOR', 'warning'),
            ('INFO', 'info'),
            ('OTHER', None),
        ],
    )
    def test_maps_sonar_severity_to_finding_severity(self, sonar_severity, expected):
        assert _map_severity(sonar_severity) == expected


# =============================================================================
# fetch_findings flow
# =============================================================================


class TestFetchFindings:
    """fetch_findings writes one sonar-issue finding per surviving issue."""

    def test_fetch_findings_persists_findings(self, plan_context):
        issues_payload = [_issue()]
        plan_context.plan_dir_for('sonar-stage-1')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, \
                patch('sonar_mod._fetch_issues') as mock_fetch:
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
        from sonar_mod import SUPPRESSABLE_RULES  # type: ignore[import-not-found]

        assert SUPPRESSABLE_RULES, 'No suppressable rules configured in sonar-rules.json'
        rule = next(iter(SUPPRESSABLE_RULES.keys()))

        issues_payload = [_issue(type_='CODE_SMELL', severity='MINOR', line=1, rule=rule, message='m')]
        plan_context.plan_dir_for('sonar-stage-skip')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, \
                patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'success', 'issues': issues_payload}
            result = cmd_fetch_findings(_make_args('sonar-stage-skip'))

        assert result['count_fetched'] == 1
        assert result['count_skipped_suppressable'] == 1
        assert result['count_stored'] == 0

    def test_fetch_findings_propagates_provider_error(self, plan_context):
        plan_context.plan_dir_for('sonar-stage-err')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, \
                patch('sonar_mod._fetch_issues') as mock_fetch:
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

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, \
                patch('sonar_mod._fetch_issues') as mock_fetch:
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
# Fail-loud unconfigured provider (both verbs)
# =============================================================================


class TestFailLoudUnconfigured:
    """Both verbs return a typed ``unconfigured`` status when no Sonar credential is configured."""

    def test_fetch_findings_unconfigured_is_not_silent_success(self, plan_context):
        plan_context.plan_dir_for('sonar-unconfigured-fetch')
        with patch('sonar_mod._sonar_credential_missing', return_value='No credentials configured'):
            result = cmd_fetch_findings(_make_args('sonar-unconfigured-fetch'))

        assert result['status'] == 'unconfigured'
        assert result['operation'] == 'fetch_findings'
        assert result['provider'] == 'sonar'
        # No findings were filed on the unconfigured path.
        from _findings_core import query_findings

        assert query_findings('sonar-unconfigured-fetch', finding_type='sonar-issue')['filtered_count'] == 0

    def test_post_responses_unconfigured_is_not_silent_success(self, plan_context):
        plan_context.plan_dir_for('sonar-unconfigured-respond')
        with patch('sonar_mod._sonar_credential_missing', return_value='No credentials configured'):
            result = cmd_post_responses(_make_args('sonar-unconfigured-respond'))

        assert result['status'] == 'unconfigured'
        assert result['operation'] == 'post_responses'
        assert result['provider'] == 'sonar'


# =============================================================================
# post_responses — hash_id-keyed dismissal transitions (Sonar do_transition shape)
# =============================================================================


class TestPostResponses:
    """post_responses maps terminal dispositions to Sonar dismissals, keyed by hash_id."""

    def _stage_one_issue(self, plan_id, issue):
        """File one sonar-issue finding via fetch_findings and return its hash_id."""
        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, \
                patch('sonar_mod._fetch_issues') as mock_fetch:
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
# CE-readiness wait contract (bounded wait is mocked — no wall-clock sleep)
# =============================================================================


class TestWaitForCeReady:
    """The synchronous bounded CE-readiness wait gates the count on a settled
    analysis. ``poll_until`` is mocked so the unit test never sleeps on the
    wall clock; the assertions are on the count_status discriminator the wait
    derives from the poll outcome (settled / timed-out / REST-error).
    """

    def test_ce_settled_reports_confirmed(self):
        # poll_until returns a non-timed-out, non-error result → confirmed.
        with patch('sonar_mod.poll_until') as mock_poll:
            mock_poll.return_value = {
                'timed_out': False,
                'last_data': {'ce_state': 'SUCCESS', 'queue_length': 0},
            }
            result = _wait_for_ce_ready('com.example:proj', None, timeout=600)

        assert result['count_status'] == 'confirmed'
        assert 'count_status_reason' not in result

    def test_ce_timeout_reports_undecidable_with_reason(self):
        # poll_until reports timed_out → undecidable, reason names the budget
        # and the last observed CE state, never a false confirmed.
        with patch('sonar_mod.poll_until') as mock_poll:
            mock_poll.return_value = {
                'timed_out': True,
                'last_data': {'ce_state': 'IN_PROGRESS', 'queue_length': 2},
            }
            result = _wait_for_ce_ready('com.example:proj', None, timeout=300)

        assert result['count_status'] == 'undecidable'
        assert '300s' in result['count_status_reason']
        assert 'IN_PROGRESS' in result['count_status_reason']

    def test_ce_rest_error_reports_undecidable(self):
        # poll_until propagates a REST/auth failure → undecidable.
        with patch('sonar_mod.poll_until') as mock_poll:
            mock_poll.return_value = {
                'timed_out': False,
                'error': 'Sonar API error: HTTP 401',
                'last_data': {},
            }
            result = _wait_for_ce_ready('com.example:proj', None, timeout=600)

        assert result['count_status'] == 'undecidable'
        assert 'HTTP 401' in result['count_status_reason']

    def test_timeout_budget_forwarded_to_poll_until(self):
        # The resolved budget must reach poll_until's ``timeout`` kwarg — the
        # wait is bounded by the configured budget, not the framework default.
        with patch('sonar_mod.poll_until') as mock_poll:
            mock_poll.return_value = {'timed_out': False, 'last_data': {}}
            _wait_for_ce_ready('com.example:proj', None, timeout=123)

        assert mock_poll.call_args.kwargs['timeout'] == 123


class TestResolveCeWaitTimeout:
    """The CE-wait budget resolution order: explicit flag wins, then the
    manifest step-params snapshot, then the conservative 600s fallback (never
    raises)."""

    def test_explicit_flag_wins(self):
        args = _make_args('p')
        args.ce_wait_timeout = 42
        # explicit flag wins even when the snapshot carries a different value
        assert _resolve_ce_wait_timeout(args, {'ce_wait_timeout_seconds': 900}) == 42

    def test_missing_attribute_falls_back_to_default(self):
        # _make_args produces no ce_wait_timeout attribute; with no snapshot
        # params the resolver returns the conservative 600s fallback.
        assert _resolve_ce_wait_timeout(_make_args('p')) == 600

    def test_snapshot_param_resolves_when_no_explicit_flag(self):
        # No explicit flag → the prefix-stripped ce_wait_timeout_seconds from the
        # manifest step-params snapshot is used.
        assert _resolve_ce_wait_timeout(_make_args('p'), {'ce_wait_timeout_seconds': 300}) == 300

    def test_empty_snapshot_falls_back_to_default(self):
        # An empty snapshot (no ce_wait_timeout_seconds) falls back to 600s.
        assert _resolve_ce_wait_timeout(_make_args('p'), {}) == 600

    def test_non_positive_snapshot_value_falls_back_to_default(self):
        # A zero / negative snapshot value is ignored in favour of the fallback.
        assert _resolve_ce_wait_timeout(_make_args('p'), {'ce_wait_timeout_seconds': 0}) == 600


class TestReadManifestSonarParams:
    """``_read_manifest_sonar_params`` reads the default:sonar-roundtrip step's
    snapshotted params from the plan-local execution manifest (one-stop read),
    falling back to an empty dict when the manifest is absent or malformed."""

    def test_reads_snapshotted_params_from_manifest(self, plan_context):
        from file_ops import get_plan_dir
        from toon_parser import serialize_toon

        plan_dir = get_plan_dir('sonar-snap')
        plan_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            'manifest_version': 1,
            'plan_id': 'sonar-snap',
            'phase_6': {
                'steps': ['sonar-roundtrip'],
                'step_params': {
                    'sonar-roundtrip': {
                        'touched_file_cleanup': 'touched_files_zero',
                        'do_transition': True,
                        'ce_wait_timeout_seconds': 720,
                    }
                },
            },
        }
        (plan_dir / 'execution.toon').write_text(serialize_toon(manifest), encoding='utf-8')

        params = sonar_mod._read_manifest_sonar_params('sonar-snap')
        assert params['ce_wait_timeout_seconds'] == 720
        assert params['touched_file_cleanup'] == 'touched_files_zero'
        assert params['do_transition'] is True

    def test_missing_manifest_returns_empty_dict(self, plan_context):
        # no manifest composed for this plan → empty dict, no raise
        assert sonar_mod._read_manifest_sonar_params('sonar-no-manifest') == {}


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

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, \
                patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'success', 'issues': issues_payload}
            result = cmd_fetch_findings(_make_args('sonar-count-confirmed'))

        assert result['count_status'] == 'confirmed'
        assert result['new_code_issue_count'] == 2

    def test_confirmed_zero_is_a_real_zero_not_undecidable(self, plan_context):
        # An empty PR-scoped new-code result against a settled CE is a CONFIRMED
        # zero, never undecidable — the core defect this contract guards against.
        plan_context.plan_dir_for('sonar-count-zero')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, \
                patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'success', 'issues': []}
            result = cmd_fetch_findings(_make_args('sonar-count-zero'))

        assert result['count_status'] == 'confirmed'
        assert result['new_code_issue_count'] == 0

    def test_confirmed_zero_writes_marker_row(self, plan_context):
        # The attestation marker is written even at count==0 so a verified zero
        # is a positive on-disk fact (an absent file means "not checked").
        plan_context.plan_dir_for('sonar-marker-zero')

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, \
                patch('sonar_mod._fetch_issues') as mock_fetch:
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

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, \
                patch('sonar_mod._fetch_issues') as mock_fetch:
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

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, \
                patch('sonar_mod._fetch_issues') as mock_fetch:
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

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, \
                patch('sonar_mod._fetch_issues') as mock_fetch:
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

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, \
                patch('sonar_mod._fetch_issues') as mock_fetch:
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

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, \
                patch('sonar_mod._fetch_issues') as mock_fetch:
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

        with patch('sonar_mod._wait_for_ce_ready') as mock_wait, \
                patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_wait.return_value = {'count_status': 'confirmed'}
            mock_fetch.return_value = {'status': 'success', 'issues': []}
            result = cmd_fetch_findings(_make_args('sonar-no-pr'))

        assert result['pull_request'] == 'none'
        rows = _read_scan_summary_rows('sonar-no-pr')
        assert rows[0]['pr'] is None


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
            '--plan-id', 'P-456',
            '--project', 'com.example:proj',
            '--pr', '99',
            '--severities', 'BLOCKER,CRITICAL',
        ]
        _resolved, remaining = extract_routing_args(argv)

        for token in argv:
            assert token in remaining
        assert _resolved is None
