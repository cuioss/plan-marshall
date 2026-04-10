#!/usr/bin/env python3
"""Tests for ci.py provider-agnostic router script.

Tests that the router correctly parses arguments and delegates.
Note: Without marshal.json, the router exits with an error (expected).
"""

import json

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import get_script_path, run_script

# Get script path
SCRIPT_PATH = get_script_path('plan-marshall', 'tools-integration-ci', 'ci.py')


def test_help_flag():
    """Test --help flag works."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.success, f'--help failed: {result.stderr}'
    assert (
        'provider-agnostic' in result.stdout.lower()
        or 'router' in result.stdout.lower()
        or 'ci' in result.stdout.lower()
    )


def test_no_args_exits_gracefully():
    """Test that running without args exits without crashing."""
    result = run_script(SCRIPT_PATH)
    # Two valid outcomes depending on marshal.json state:
    # - No CI provider: exit 0 with TOON error
    # - CI provider configured: exit 2 from argparse (no subcommand)
    assert result.returncode in (0, 2)


def test_pr_subcommand_returns_success():
    """Test that pr subcommand returns exit 0."""
    result = run_script(SCRIPT_PATH, 'pr', '--help')
    # Either delegates to provider (shows help) or returns TOON error
    assert result.success


def test_get_provider_reads_from_providers_array(tmp_path):
    """Test that get_provider() resolves CI provider from providers array."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    marshal = {
        'providers': [
            {
                'skill_name': 'plan-marshall:workflow-integration-github',
                'category': 'ci',
            },
        ],
    }
    (plan_dir / 'marshal.json').write_text(json.dumps(marshal))

    result = run_script(SCRIPT_PATH, cwd=tmp_path)
    # Should detect github provider and fail on missing subcommand (exit 2),
    # not on "CI provider not configured" (exit 0 with error TOON)
    assert result.returncode == 2 or 'not configured' not in result.stdout


def test_get_provider_returns_none_without_ci_entry(tmp_path):
    """Test that get_provider() returns None when no CI provider in providers array."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    marshal = {
        'providers': [
            {
                'skill_name': 'plan-marshall:workflow-integration-sonar',
                'category': 'other',
            },
        ],
    }
    (plan_dir / 'marshal.json').write_text(json.dumps(marshal))

    result = run_script(SCRIPT_PATH, cwd=tmp_path)
    assert result.success
    assert 'not configured' in result.stdout


def test_get_provider_derives_from_skill_name(tmp_path):
    """Test that get_provider() derives provider key from skill_name when provider field missing."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    marshal = {
        'providers': [
            {
                'skill_name': 'plan-marshall:workflow-integration-gitlab',
                'category': 'ci',
            },
        ],
    }
    (plan_dir / 'marshal.json').write_text(json.dumps(marshal))

    result = run_script(SCRIPT_PATH, cwd=tmp_path)
    # Should detect gitlab provider (derived from skill_name), not "not configured"
    assert result.returncode == 2 or 'not configured' not in result.stdout
