#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""CLI cluster — health CLI surface."""

import json
from argparse import Namespace
from unittest.mock import patch

# conftest.py sets up PYTHONPATH so tools-integration-ci scripts are importable.
from conftest import get_script_path, run_script

# Script path for the Tier 3 subprocess (CLI plumbing) tests.
SCRIPT_PATH = get_script_path('plan-marshall', 'tools-integration-ci', 'ci_health.py')

# Tier 2 direct imports — resolved after conftest bootstraps PYTHONPATH above.
import ci_health  # noqa: E402
from ci_health import (  # noqa: E402
    _match_directory,
    _match_url,
    cmd_detect,
    cmd_status,
    cmd_verify,
    detect_provider,
    verify_tool,
)

# =============================================================================
# Tier 2: Direct import tests for cmd_detect
# =============================================================================


def test_help_flag():
    """Test --help flag works."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.success, f'--help failed: {result.stderr}'
    assert 'detect' in result.stdout
    assert 'verify' in result.stdout
    assert 'status' in result.stdout
    assert 'verify-all' in result.stdout


def test_detect_cli_output():
    """Test detect subcommand produces valid TOON via subprocess."""
    result = run_script(SCRIPT_PATH, 'detect')
    assert result.success, f'Script failed: {result.stderr}'
    data = result.toon()
    assert data['status'] == 'success'


def test_verify_cli_output():
    """Test verify subcommand produces valid TOON via subprocess."""
    result = run_script(SCRIPT_PATH, 'verify')
    assert result.success, f'Script failed: {result.stderr}'
    data = result.toon()
    assert data['status'] == 'success'


# =============================================================================
# Tier 3: Subprocess tests for verify-all (live verification, no persistence)
# =============================================================================


def test_verify_all_no_marshal_json(plan_context):
    """Test verify-all fails when marshal.json is missing."""
    result = run_script(SCRIPT_PATH, 'verify-all')
    assert result.success, 'Expected exit 0 (error in TOON output)'
    data = result.toon_or_error()
    assert data.get('status') != 'success', 'Expected error status in TOON output'
    assert 'error' in data


def test_verify_all_with_marshal_json(plan_context):
    """Test verify-all succeeds and does NOT write config['ci']."""
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(
        json.dumps(
            {
                'version': 1,
                'providers': [
                    {
                        'skill_name': 'plan-marshall:workflow-integration-github',
                        'category': 'ci',
                        'verify_command': 'gh auth status',
                    }
                ],
            }
        )
    )

    result = run_script(SCRIPT_PATH, 'verify-all')
    assert result.success, f'Script failed: {result.stderr}'

    updated = json.loads(marshal_path.read_text())
    # providers[] is the canonical source — verify-all must not write config['ci']
    assert 'ci' not in updated, f"verify-all should not write config['ci'], got: {updated.get('ci')}"
    assert updated['providers'][0]['category'] == 'ci'


def test_verify_all_leaves_providers_intact(plan_context):
    """Test verify-all leaves providers[] untouched (single source of truth)."""
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    original_providers = [
        {
            'skill_name': 'plan-marshall:workflow-integration-github',
            'category': 'ci',
            'verify_command': 'gh auth status',
        }
    ]
    marshal_path.write_text(
        json.dumps(
            {
                'version': 1,
                'providers': original_providers,
            }
        )
    )

    result = run_script(SCRIPT_PATH, 'verify-all')
    assert result.success, f'Script failed: {result.stderr}'

    updated = json.loads(marshal_path.read_text())
    assert 'ci' not in updated
    assert updated['providers'] == original_providers
