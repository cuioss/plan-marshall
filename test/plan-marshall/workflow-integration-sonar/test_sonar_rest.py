#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for sonar_rest.py module.

Tests REST client subcommands with mocked HTTP responses.
"""

import importlib.util
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-sonar', 'sonar_rest.py')

# Module-level importlib load — the cmd_* logic tests call into the script's
# functions in-process, so the module is imported once here rather than inside
# each test.
_spec = importlib.util.spec_from_file_location('sonar_rest', str(SCRIPT_PATH))
assert _spec is not None and _spec.loader is not None
sonar_rest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sonar_rest)


class TestSonarRestCLI:
    """Tests for sonar_rest.py CLI plumbing."""

    @pytest.mark.parametrize(
        'argv',
        [
            pytest.param(['search'], id='search-requires-project'),
            pytest.param(['transition', '--transition', 'accept'], id='transition-requires-issue-key'),
            pytest.param(['metrics', '--project', 'foo'], id='metrics-requires-project-and-component'),
            pytest.param(['gate-status'], id='gate-status-requires-project'),
            pytest.param(['ce-status'], id='ce-status-requires-project'),
            pytest.param(['hotspots'], id='hotspots-requires-project'),
        ],
    )
    def test_subcommand_rejects_missing_required_arg(self, argv):
        """Each subcommand exits non-zero when a required argument is absent."""
        result = run_script(SCRIPT_PATH, *argv)

        assert result.returncode != 0

    def test_help(self):
        """--help works."""
        result = run_script(SCRIPT_PATH, '--help')

        assert result.returncode == 0
        assert 'search' in result.stdout
        assert 'transition' in result.stdout
        assert 'metrics' in result.stdout
        assert 'gate-status' in result.stdout
        assert 'ce-status' in result.stdout
        assert 'hotspots' in result.stdout

    def test_project_dir_accepted_as_noop_with_help(self):
        """sonar_rest.py accepts --project-dir as a top-level no-op; the
        pre-parse strips it before argparse runs, so combining it with --help
        must succeed."""
        result = run_script(SCRIPT_PATH, '--project-dir', '/tmp/wt-rest', '--help')

        assert result.returncode == 0, result.stderr
        assert 'search' in result.stdout
        assert 'unrecognized arguments' not in result.stderr

    def test_project_dir_equals_form_accepted(self):
        """The --project-dir=PATH form is also accepted."""
        result = run_script(SCRIPT_PATH, '--project-dir=/tmp/wt-rest2', '--help')

        assert result.returncode == 0, result.stderr
        assert 'unrecognized arguments' not in result.stderr

    def test_plan_id_accepted_as_noop_with_help(self):
        """sonar_rest.py accepts --plan-id as a top-level routing flag.

        The pre-parse strips it before argparse runs (auto-resolves the
        worktree path via manage-status), so combining it with --help
        must succeed regardless of whether the plan exists.
        """
        result = run_script(SCRIPT_PATH, '--plan-id', 'task-routing-canonical', '--help')

        # --help triggers SystemExit(0). The resolver may fail with worktree
        # resolution errors before --help runs (no real plan persisted), so
        # we accept either 0 (help reached) or 2 (resolver error) — the
        # regression we're guarding is "argparse rejects --plan-id".
        assert 'unrecognized arguments' not in result.stderr, (
            f'--plan-id must be consumed by the router, not rejected by argparse: {result.stderr!r}'
        )

    def test_both_plan_id_and_project_dir_yields_mutually_exclusive_error(self, tmp_path):
        """Router-level --plan-id + --project-dir → mutually_exclusive_args TOON error."""
        result = run_script(
            SCRIPT_PATH,
            '--plan-id',
            'task-routing-canonical',
            '--project-dir',
            str(tmp_path),
            '--help',
        )

        # The resolver branch emits a TOON error and exits 2 BEFORE --help
        # is processed.
        assert result.returncode == 2, f'Expected exit 2, got {result.returncode}; stdout={result.stdout!r}'
        assert 'mutually_exclusive_args' in result.stdout, (
            f'Expected mutually_exclusive_args TOON error, got: {result.stdout!r}'
        )

    def test_neither_routing_flag_keeps_legacy_behaviour(self):
        """Neither flag → no auto-routing, no error; legacy "inherit cwd" preserved."""
        result = run_script(SCRIPT_PATH, '--help')

        assert result.returncode == 0
        # No TOON error payload on stdout.
        assert 'mutually_exclusive_args' not in result.stdout
        assert 'worktree_resolution_failed' not in result.stdout


class TestSonarSearchLogic:
    """Tests for search subcommand logic."""

    def test_search_formats_issues(self, capsys):
        """Search extracts and formats issue data from API response."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            'issues': [
                {
                    'key': 'ISSUE-1',
                    'type': 'BUG',
                    'severity': 'MAJOR',
                    'component': 'org:src/Main.java',
                    'line': 42,
                    'rule': 'java:S1234',
                    'message': 'Fix this bug',
                }
            ]
        }

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            result = sonar_rest.cmd_search(
                Namespace(project='my-project', pr=None, severities=None, types=None)
            )

        assert result == 0
        output = capsys.readouterr().out
        assert 'ISSUE-1' in output
        assert 'BUG' in output


class TestSonarGateStatusLogic:
    """Tests for gate-status subcommand logic."""

    def test_gate_status_formats_conditions(self, capsys):
        """gate-status surfaces the overall status plus each condition."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            'projectStatus': {
                'status': 'ERROR',
                'conditions': [
                    {
                        'metricKey': 'new_coverage',
                        'comparator': 'LT',
                        'errorThreshold': '80',
                        'actualValue': '72.5',
                        'status': 'ERROR',
                    }
                ],
            }
        }

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            result = sonar_rest.cmd_gate_status(
                Namespace(project='my-project', branch=None, pr=None)
            )

        assert result == 0
        output = capsys.readouterr().out
        assert 'ERROR' in output
        assert 'new_coverage' in output
        assert '72.5' in output

    def test_gate_status_branch_param_forwarded(self):
        """When --branch is given, it is forwarded to the API and --pr is not."""
        mock_client = MagicMock()
        mock_client.get.return_value = {'projectStatus': {'status': 'OK', 'conditions': []}}

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            sonar_rest.cmd_gate_status(Namespace(project='my-project', branch='develop', pr=None))

        _, kwargs = mock_client.get.call_args
        assert kwargs['params']['branch'] == 'develop'
        assert 'pullRequest' not in kwargs['params']

    def test_gate_status_api_error_yields_error_toon(self, capsys):
        """A RestClientError yields the status: error TOON."""
        mock_client = MagicMock()
        mock_client.get.side_effect = sonar_rest.RestClientError(500, 'boom')

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            result = sonar_rest.cmd_gate_status(
                Namespace(project='my-project', branch=None, pr=None)
            )

        assert result == 0
        output = capsys.readouterr().out
        assert 'error' in output
        assert 'HTTP 500' in output

    def test_gate_status_pr_param_forwarded_when_no_branch(self):
        """When only --pr is given, it is forwarded as pullRequest and branch is not."""
        mock_client = MagicMock()
        mock_client.get.return_value = {'projectStatus': {'status': 'OK', 'conditions': []}}

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            sonar_rest.cmd_gate_status(Namespace(project='my-project', branch=None, pr='123'))

        _, kwargs = mock_client.get.call_args
        assert kwargs['params']['pullRequest'] == '123'
        assert 'branch' not in kwargs['params']

    def test_gate_status_branch_takes_precedence_over_pr(self):
        """When both --branch and --pr are given, branch wins (elif ordering)."""
        mock_client = MagicMock()
        mock_client.get.return_value = {'projectStatus': {'status': 'OK', 'conditions': []}}

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            sonar_rest.cmd_gate_status(Namespace(project='my-project', branch='develop', pr='123'))

        _, kwargs = mock_client.get.call_args
        assert kwargs['params']['branch'] == 'develop'
        assert 'pullRequest' not in kwargs['params']

    def test_gate_status_ok_path_emits_empty_conditions(self, capsys):
        """A passing gate yields gate_status OK and no condition rows."""
        mock_client = MagicMock()
        mock_client.get.return_value = {'projectStatus': {'status': 'OK', 'conditions': []}}

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            result = sonar_rest.cmd_gate_status(
                Namespace(project='my-project', branch=None, pr=None)
            )

        assert result == 0
        output = capsys.readouterr().out
        assert 'success' in output
        assert 'OK' in output


class TestSonarCeStatusLogic:
    """Tests for ce-status subcommand logic."""

    def test_ce_status_distinguishes_infra_failure(self, capsys):
        """ce-status surfaces task status, errorType and errorMessage."""
        mock_client = MagicMock()
        mock_client.get.side_effect = [
            {
                'tasks': [
                    {
                        'id': 'TASK-1',
                        'status': 'FAILED',
                        'branch': 'main',
                        'submittedAt': '2026-06-14T10:00:00+0000',
                        'executedAt': '2026-06-14T10:01:00+0000',
                        'errorType': 'PROVISIONING',
                        'errorMessage': 'Could not provision analysis',
                    }
                ]
            },
            {'current': {'status': 'FAILED'}, 'queue': []},
        ]

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            result = sonar_rest.cmd_ce_status(Namespace(project='my-project', branch=None))

        assert result == 0
        output = capsys.readouterr().out
        assert 'FAILED' in output
        assert 'PROVISIONING' in output
        assert 'Could not provision analysis' in output

    def test_ce_status_api_error_yields_error_toon(self, capsys):
        """A RestClientError yields the status: error TOON."""
        mock_client = MagicMock()
        mock_client.get.side_effect = sonar_rest.RestClientError(503, 'unavailable')

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            result = sonar_rest.cmd_ce_status(Namespace(project='my-project', branch=None))

        assert result == 0
        output = capsys.readouterr().out
        assert 'error' in output
        assert 'HTTP 503' in output

    def test_ce_status_branch_forwarded_to_activity(self):
        """--branch is forwarded to the /api/ce/activity call only."""
        mock_client = MagicMock()
        mock_client.get.side_effect = [
            {'tasks': []},
            {'current': {'status': 'SUCCESS'}, 'queue': []},
        ]

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            sonar_rest.cmd_ce_status(Namespace(project='my-project', branch='release'))

        # First call is /api/ce/activity and must carry the branch param.
        activity_call = mock_client.get.call_args_list[0]
        assert activity_call.args[0] == '/api/ce/activity'
        assert activity_call.kwargs['params']['branch'] == 'release'
        # Second call is /api/ce/component and must NOT carry the branch param.
        component_call = mock_client.get.call_args_list[1]
        assert component_call.args[0] == '/api/ce/component'
        assert 'branch' not in component_call.kwargs['params']

    def test_ce_status_surfaces_queue_length_and_current_status(self, capsys):
        """A pending analysis surfaces queue_length and current_status."""
        mock_client = MagicMock()
        mock_client.get.side_effect = [
            {'tasks': []},
            {'current': {'status': 'SUCCESS'}, 'queue': [{'id': 'Q-1'}, {'id': 'Q-2'}]},
        ]

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            result = sonar_rest.cmd_ce_status(Namespace(project='my-project', branch=None))

        assert result == 0
        output = capsys.readouterr().out
        assert 'success' in output
        assert 'SUCCESS' in output
        assert 'queue_length' in output
        assert '2' in output

    def test_ce_status_defaults_current_status_when_absent(self, capsys):
        """A missing current task defaults current_status to none."""
        mock_client = MagicMock()
        mock_client.get.side_effect = [
            {'tasks': []},
            {'queue': []},
        ]

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            result = sonar_rest.cmd_ce_status(Namespace(project='my-project', branch=None))

        assert result == 0
        output = capsys.readouterr().out
        assert 'current_status' in output
        assert 'none' in output


class TestSonarHotspotsLogic:
    """Tests for hotspots subcommand logic."""

    def test_hotspots_formats_entries(self, capsys):
        """hotspots returns security hotspots with key and probability."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            'hotspots': [
                {
                    'key': 'HOTSPOT-1',
                    'status': 'TO_REVIEW',
                    'vulnerabilityProbability': 'HIGH',
                    'securityCategory': 'sql-injection',
                    'component': 'org:src/Db.java',
                    'line': 17,
                    'message': 'Review this SQL usage',
                }
            ]
        }

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            result = sonar_rest.cmd_hotspots(
                Namespace(project='my-project', branch=None, pr=None)
            )

        assert result == 0
        output = capsys.readouterr().out
        assert 'HOTSPOT-1' in output
        assert 'HIGH' in output
        assert 'src/Db.java' in output

    def test_hotspots_api_error_yields_error_toon(self, capsys):
        """A RestClientError yields the status: error TOON."""
        mock_client = MagicMock()
        mock_client.get.side_effect = sonar_rest.RestClientError(404, 'not found')

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            result = sonar_rest.cmd_hotspots(
                Namespace(project='my-project', branch=None, pr=None)
            )

        assert result == 0
        output = capsys.readouterr().out
        assert 'error' in output
        assert 'HTTP 404' in output

    def test_hotspots_pr_param_forwarded_when_no_branch(self):
        """When only --pr is given, it is forwarded as pullRequest and branch is not."""
        mock_client = MagicMock()
        mock_client.get.return_value = {'hotspots': []}

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            sonar_rest.cmd_hotspots(Namespace(project='my-project', branch=None, pr='99'))

        _, kwargs = mock_client.get.call_args
        assert kwargs['params']['pullRequest'] == '99'
        assert 'branch' not in kwargs['params']

    def test_hotspots_branch_takes_precedence_over_pr(self):
        """When both --branch and --pr are given, branch wins (elif ordering)."""
        mock_client = MagicMock()
        mock_client.get.return_value = {'hotspots': []}

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            sonar_rest.cmd_hotspots(Namespace(project='my-project', branch='main', pr='99'))

        _, kwargs = mock_client.get.call_args
        assert kwargs['params']['branch'] == 'main'
        assert 'pullRequest' not in kwargs['params']

    def test_hotspots_aggregates_by_vulnerability_probability(self, capsys):
        """Statistics tally hotspots per vulnerability probability bucket."""
        mock_client = MagicMock()
        mock_client.get.return_value = {
            'hotspots': [
                {
                    'key': 'H-1',
                    'status': 'TO_REVIEW',
                    'vulnerabilityProbability': 'HIGH',
                    'securityCategory': 'sql-injection',
                    'component': 'org:src/A.java',
                    'line': 1,
                    'message': 'a',
                },
                {
                    'key': 'H-2',
                    'status': 'TO_REVIEW',
                    'vulnerabilityProbability': 'HIGH',
                    'securityCategory': 'weak-crypto',
                    'component': 'org:src/B.java',
                    'line': 2,
                    'message': 'b',
                },
                {
                    'key': 'H-3',
                    'status': 'TO_REVIEW',
                    'vulnerabilityProbability': 'LOW',
                    'securityCategory': 'dos',
                    'component': 'org:src/C.java',
                    'line': 3,
                    'message': 'c',
                },
            ]
        }

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            result = sonar_rest.cmd_hotspots(
                Namespace(project='my-project', branch=None, pr=None)
            )

        assert result == 0
        output = capsys.readouterr().out
        assert 'total_hotspots_fetched' in output
        assert 'by_vulnerability_probability' in output
        assert 'HIGH' in output
        assert 'LOW' in output

    def test_hotspots_empty_result_yields_zero_statistics(self, capsys):
        """An empty hotspots list yields a zero total and success status."""
        mock_client = MagicMock()
        mock_client.get.return_value = {'hotspots': []}

        with patch.object(sonar_rest, 'get_authenticated_client', return_value=mock_client):
            result = sonar_rest.cmd_hotspots(
                Namespace(project='my-project', branch=None, pr=None)
            )

        assert result == 0
        output = capsys.readouterr().out
        assert 'success' in output
        assert 'total_hotspots_fetched' in output
