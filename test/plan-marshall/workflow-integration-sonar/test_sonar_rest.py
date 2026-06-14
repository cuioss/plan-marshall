#!/usr/bin/env python3
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
