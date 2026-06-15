"""Tests for workflow-integration-sonar sonar.py — producer-side surface.

The triage / triage-batch subcommands have been retired. The remaining
callable surface is ``fetch-and-store`` which fetches gate-blocking issues,
applies the suppressable-rules pre-filter, and persists one ``sonar-issue``
finding per surviving issue via ``manage-findings add``.
"""

import importlib.util
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
cmd_fetch_and_store = sonar_mod.cmd_fetch_and_store

# Importing sonar.py (above) runs its module-level ``register_subcommands({'fetch-and-store'})``
# call, which extends the shared ci_base subcommand registry. ``extract_routing_args`` is the
# router-level pre-parser that the bug stripped ``--plan-id`` through; the regression test below
# exercises it directly.
from ci_base import extract_routing_args  # type: ignore[import-not-found]  # noqa: E402,I001


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
# fetch-and-store flow
# =============================================================================


class TestFetchAndStore:
    """fetch-and-store writes one sonar-issue finding per surviving issue."""

    def test_fetch_and_store_persists_findings(self, plan_context):
        issues_payload = [_issue()]
        plan_context.plan_dir_for('sonar-stage-1')

        with patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_fetch.return_value = {'status': 'success', 'issues': issues_payload}
            result = cmd_fetch_and_store(_make_args('sonar-stage-1'))

        assert result['status'] == 'success'
        assert result['count_fetched'] == 1
        assert result['count_skipped_suppressable'] == 0
        assert result['count_stored'] == 1

        from _findings_core import query_findings  # type: ignore[import-not-found]

        q = query_findings('sonar-stage-1', finding_type='sonar-issue')
        assert q['filtered_count'] == 1
        stored = q['findings'][0]
        assert stored['type'] == 'sonar-issue'
        assert stored['rule'] == 'java:S99999'
        assert stored['severity'] == 'error'  # MAJOR → error
        assert stored['module'] == 'com.example:proj'
        assert 'Possible null dereference' in stored['detail']

    def test_fetch_and_store_skips_suppressable(self, plan_context):
        # First find a rule from the live SUPPRESSABLE_RULES dict to ensure
        # the test exercises real configuration. If the dict is empty the
        # test trivially passes; that is acceptable because the assertion
        # is on observable counter behaviour, not config presence.
        from sonar_mod import SUPPRESSABLE_RULES  # type: ignore[import-not-found]

        if not SUPPRESSABLE_RULES:
            pytest.skip('No suppressable rules configured in sonar-rules.json')
        rule = next(iter(SUPPRESSABLE_RULES.keys()))

        issues_payload = [_issue(type_='CODE_SMELL', severity='MINOR', line=1, rule=rule, message='m')]
        plan_context.plan_dir_for('sonar-stage-skip')

        with patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_fetch.return_value = {'status': 'success', 'issues': issues_payload}
            result = cmd_fetch_and_store(_make_args('sonar-stage-skip'))

        assert result['count_fetched'] == 1
        assert result['count_skipped_suppressable'] == 1
        assert result['count_stored'] == 0

    def test_fetch_and_store_propagates_provider_error(self, plan_context):
        plan_context.plan_dir_for('sonar-stage-err')

        with patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_fetch.return_value = {'status': 'error', 'message': 'HTTP 401'}
            result = cmd_fetch_and_store(_make_args('sonar-stage-err'))

        assert result['status'] == 'error'

    def test_fetch_and_store_count_mismatch_produces_qgate_finding(self, plan_context):
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

        with patch('sonar_mod._fetch_issues') as mock_fetch:
            mock_fetch.return_value = {'status': 'success', 'issues': issues_payload}
            with patch('_findings_core.add_finding') as mock_add:
                def _side_effect(**kwargs):
                    if mock_add.call_count == 1:
                        return {'status': 'error', 'message': 'simulated store failure'}
                    return {'status': 'success', 'hash_id': 'h-' + str(mock_add.call_count)}

                mock_add.side_effect = _side_effect
                result = cmd_fetch_and_store(_make_args('sonar-stage-mismatch'))

        assert result['status'] == 'success'
        assert result['count_fetched'] == 2
        assert result['count_skipped_suppressable'] == 0
        assert result['count_stored'] == 1

        from _findings_core import query_qgate_findings  # type: ignore[import-not-found]

        q = query_qgate_findings('sonar-stage-mismatch', phase='5-execute')
        assert q['filtered_count'] == 1
        qf = q['findings'][0]
        assert qf['title'].startswith('(producer-mismatch)')
        assert qf['source'] == 'qgate'
        assert qf['type'] == 'sonar-issue'


# =============================================================================
# CLI plumbing
# =============================================================================


class TestSonarMain:
    def test_help_lists_only_supported_subcommand(self):
        result = run_script(SCRIPT_PATH, '--help')

        assert result.returncode == 0
        assert 'fetch-and-store' in result.stdout
        assert 'triage-batch' not in result.stdout

    @pytest.mark.parametrize(
        'argv',
        [
            pytest.param(['triage', '--issue', '{}'], id='triage-rejected'),
            pytest.param(['triage-batch', '--issues', '[]'], id='triage-batch-rejected'),
        ],
    )
    def test_retired_subcommand_rejected(self, argv):
        result = run_script(SCRIPT_PATH, *argv)

        assert result.returncode != 0


# =============================================================================
# Regression: subcommand routing must not strip --plan-id
# =============================================================================


class TestFetchAndStoreRouting:
    """Regression for the fetch-and-store routing defect.

    sonar.py registers ``fetch-and-store`` as a top-level subcommand token (via
    the module-level ``register_subcommands({'fetch-and-store'})`` call) so that
    ``extract_routing_args`` locates the subcommand boundary correctly. Without
    that registration, ``fetch-and-store`` is not in the known-subcommand
    registry, ``_split_at_subcommand`` treats the whole argv as router-level
    prefix, and the subcommand-level ``--plan-id`` is consumed (stripped) at the
    router layer before reaching the subcommand parser — the original bug. These
    tests assert the post-fix behaviour: the subcommand-level ``--plan-id`` and
    every other subcommand argument survive in ``remaining_argv`` so the
    ``fetch-and-store`` subparser can consume them.

    Red/green contract: green against the fixed sonar.py (token registered at
    import); red against the unfixed version (token absent, ``--plan-id``
    stripped, so the assertions below fail).
    """

    def test_plan_id_immediately_after_subcommand_preserves_pairing(self):
        # The --plan-id flag and its value must remain adjacent so the subparser
        # binds the value to the flag (a stray strip of only the value would
        # leave a dangling --plan-id with no argument).
        _resolved, remaining = extract_routing_args(
            ['fetch-and-store', '--plan-id', 'P-123', '--project', 'com.example:proj']
        )

        idx = remaining.index('--plan-id')
        assert remaining[idx + 1] == 'P-123'

    def test_all_subcommand_args_survive_routing(self):
        # Every fetch-and-store argument (including optional --pr / --severities)
        # must reach the subparser intact, not just --plan-id.
        argv = [
            'fetch-and-store',
            '--plan-id', 'P-456',
            '--project', 'com.example:proj',
            '--pr', '99',
            '--severities', 'BLOCKER,CRITICAL',
        ]
        _resolved, remaining = extract_routing_args(argv)

        for token in argv:
            assert token in remaining
        assert _resolved is None
