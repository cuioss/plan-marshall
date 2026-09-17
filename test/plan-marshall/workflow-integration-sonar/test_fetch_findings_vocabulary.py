#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for sonar fetch_findings — classification vocabulary and readiness guards.
"""

from __future__ import annotations

from unittest.mock import patch
import pytest
from test_fetch_findings_core import sonar_mod


_is_suppressable = sonar_mod._is_suppressable


_map_severity = sonar_mod._map_severity


cmd_fetch_findings = sonar_mod.cmd_fetch_findings


cmd_post_responses = sonar_mod.cmd_post_responses


_wait_for_ce_ready = sonar_mod._wait_for_ce_ready


_resolve_ce_wait_timeout = sonar_mod._resolve_ce_wait_timeout


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
# Rejected producer-mismatch persist (P7) — FIELD_ONLY loudness
# =============================================================================
#
# The producer-mismatch finding exists to report that findings were lost. When
# its OWN persist is rejected, the loss must surface on the returned dict — but
# the enclosing ``status`` stays truthful about the fetch, which did succeed.
def _fetch_one_issue(plan_id):
    """Run ``fetch_findings`` over a single-issue fixture with CE settled."""
    with patch('sonar_mod._wait_for_ce_ready') as mock_wait, patch('sonar_mod._fetch_issues') as mock_fetch:
        mock_wait.return_value = {'count_status': 'confirmed'}
        mock_fetch.return_value = {'status': 'success', 'issues': [_issue()]}
        return cmd_fetch_findings(_make_args(plan_id))


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


class TestRejectedMismatchPersist:
    """A rejected producer-mismatch persist is surfaced, never absorbed."""

    def test_rejected_persist_surfaces_field_without_flipping_status(self, plan_context, monkeypatch):
        """Driven by the real validator — ``sonar-issue`` removed from FINDING_TYPES."""
        import _findings_core

        plan_id = 'sonar-persist-reject'
        plan_context.plan_dir_for(plan_id)
        monkeypatch.setattr(
            _findings_core,
            'FINDING_TYPES',
            tuple(t for t in _findings_core.FINDING_TYPES if t != 'sonar-issue'),
        )

        result = _fetch_one_issue(plan_id)

        # FIELD_ONLY loudness: the fetch itself succeeded, so its status is unchanged.
        assert result['status'] == 'success'
        assert result['count_status'] == 'confirmed'
        assert result['count_stored'] == 0
        assert result['qgate_persist_failed'] is True
        assert result['producer_mismatch_hash_id'] is None
        failure = result['qgate_persist_failure']
        assert '(producer-mismatch)' in failure['title']
        assert 'count_stored=0' in failure['detail']
        assert 'Invalid finding type' in failure['message']

    def test_deduplicated_persist_stays_benign(self, plan_context, monkeypatch):
        """A ``deduplicated`` mismatch persist is benign — never read as a rejection.

        Only the upstream issue store is forced to fail (so a mismatch arises);
        the mismatch persist itself runs against the REAL primitive, which dedups
        the identical finding on the second run.
        """
        import _findings_core

        plan_id = 'sonar-persist-dedup'
        plan_context.plan_dir_for(plan_id)
        monkeypatch.setattr(
            _findings_core,
            'add_finding',
            lambda **kwargs: {'status': 'error', 'message': 'forced issue-store failure'},
        )

        first = _fetch_one_issue(plan_id)
        assert first['status'] == 'success'
        assert first['count_stored'] == 0
        assert first['producer_mismatch_hash_id']
        assert 'qgate_persist_failed' not in first

        second = _fetch_one_issue(plan_id)

        assert second['status'] == 'success'
        assert 'qgate_persist_failed' not in second
        # Dedup returns the SAME record — still in the store, so still a hash id.
        assert second['producer_mismatch_hash_id'] == first['producer_mismatch_hash_id']

