#!/usr/bin/env python3
"""Tests for sonar_rest.py module.

Tests REST client subcommands with mocked HTTP responses.
"""

from unittest.mock import MagicMock, patch

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-sonar', 'sonar_rest.py')


class TestSonarRestCLI:
    """Tests for sonar_rest.py CLI plumbing."""

    def test_search_requires_project(self):
        """Search subcommand requires --project."""
        result = run_script(SCRIPT_PATH, 'search')
        assert result.returncode != 0

    def test_transition_requires_issue_key(self):
        """Transition subcommand requires --issue-key."""
        result = run_script(SCRIPT_PATH, 'transition', '--transition', 'accept')
        assert result.returncode != 0

    def test_metrics_requires_project_and_component(self):
        """Metrics subcommand requires both --project and --component."""
        result = run_script(SCRIPT_PATH, 'metrics', '--project', 'foo')
        assert result.returncode != 0

    def test_help(self):
        """--help works."""
        result = run_script(SCRIPT_PATH, '--help')
        assert result.returncode == 0
        assert 'search' in result.stdout
        assert 'transition' in result.stdout
        assert 'metrics' in result.stdout

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


class TestSonarSearchLogic:
    """Tests for search subcommand logic."""

    def test_search_formats_issues(self):
        """Search extracts and formats issue data from API response."""
        import importlib.util

        spec = importlib.util.spec_from_file_location('sonar_rest', str(SCRIPT_PATH))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

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

        with patch.object(mod, 'get_authenticated_client', return_value=mock_client):
            from argparse import Namespace

            # Capture stdout
            from io import StringIO

            captured = StringIO()
            with patch('sys.stdout', captured):
                result = mod.cmd_search(Namespace(project='my-project', pr=None, severities=None, types=None))

            assert result == 0
            output = captured.getvalue()
            assert 'ISSUE-1' in output
            assert 'BUG' in output
