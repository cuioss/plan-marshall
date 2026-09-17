#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for sonar_rest — quality-gate and compute-engine state handling.
"""

from __future__ import annotations

from argparse import Namespace
from unittest.mock import MagicMock, patch
from conftest import load_script_module


# Module-level importlib load — the cmd_* logic tests call into the script's
# functions in-process, so the module is imported once here rather than inside
# each test.
sonar_rest = load_script_module('plan-marshall', 'workflow-integration-sonar', 'sonar_rest.py', 'sonar_rest')


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
            result = sonar_rest.cmd_gate_status(Namespace(project='my-project', branch=None, pr=None))

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
            result = sonar_rest.cmd_gate_status(Namespace(project='my-project', branch=None, pr=None))

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
            result = sonar_rest.cmd_gate_status(Namespace(project='my-project', branch=None, pr=None))

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

