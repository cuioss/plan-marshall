#!/usr/bin/env python3
"""Tests for ci_health.py script.

Tests provider detection, tool verification, and configuration persistence.

Tier 2 (direct import) tests for cmd_* functions.
Tier 3 (subprocess) tests retained for CLI plumbing and persist (marshal.json I/O).
"""

import json
from argparse import Namespace

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from unittest.mock import patch

from conftest import PlanContext, get_script_path, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'tools-integration-ci', 'ci_health.py')

# Tier 2 direct imports
from ci_health import (  # type: ignore[import-not-found]  # noqa: E402
    _match_directory,
    _match_url,
    cmd_detect,
    cmd_status,
    cmd_verify,
    detect_provider,
)

# =============================================================================
# Tier 2: Direct import tests for cmd_detect
# =============================================================================


def test_detect_returns_success():
    """Test detect command returns valid output via direct import."""
    result = cmd_detect(Namespace())
    assert result['status'] == 'success'
    assert 'provider' in result
    assert result['provider'] in ('github', 'gitlab', 'unknown')
    assert 'confidence' in result


def test_detect_includes_repo_url():
    """Test detect output includes repo_url field."""
    result = cmd_detect(Namespace())
    assert 'repo_url' in result


# =============================================================================
# Tier 2: Direct import tests for cmd_verify
# =============================================================================


def test_verify_all_tools():
    """Test verify command checks all tools via direct import."""
    result = cmd_verify(Namespace(tool=None))
    assert result['status'] == 'success'
    assert 'tools' in result
    # Should have git at minimum
    assert 'git' in result['tools']
    assert 'installed' in result['tools']['git']


def test_verify_specific_tool_git():
    """Test verify command for specific tool via direct import."""
    result = cmd_verify(Namespace(tool='git'))
    assert result['status'] == 'success'
    assert 'tools' in result
    assert 'git' in result['tools']


def test_verify_unknown_tool():
    """Test verify command with unknown tool returns error via direct import."""
    result = cmd_verify(Namespace(tool='unknown_tool_xyz'))
    assert result['status'] == 'error'
    assert 'error' in result


# =============================================================================
# Tier 2: Direct import tests for cmd_status
# =============================================================================


def test_status_returns_comprehensive_output():
    """Test status command returns comprehensive output via direct import."""
    result = cmd_status(Namespace())
    assert result['status'] == 'success'
    assert 'provider' in result
    assert 'tools' in result
    assert 'overall' in result
    assert result['overall'] in ('healthy', 'degraded', 'unknown')


# =============================================================================
# Tier 2: Declarative detection pattern tests
# =============================================================================

GITHUB_PATTERN = {
    'provider_key': 'github',
    'url_patterns': [r'github\.com'],
    'directory_markers': ['.github'],
    'enterprise_patterns': [],
}

GITLAB_PATTERN = {
    'provider_key': 'gitlab',
    'url_patterns': [r'gitlab\.com'],
    'directory_markers': ['.gitlab-ci.yml'],
    'enterprise_patterns': [r'gitlab\.', r'\.gitlab\.'],
}

TEST_PATTERNS = [GITHUB_PATTERN, GITLAB_PATTERN]


def test_match_url_github():
    """Test URL matching for github.com."""
    match = _match_url('https://github.com/org/repo.git', TEST_PATTERNS)
    assert match is not None
    assert match['provider_key'] == 'github'


def test_match_url_gitlab():
    """Test URL matching for gitlab.com."""
    match = _match_url('https://gitlab.com/org/repo.git', TEST_PATTERNS)
    assert match is not None
    assert match['provider_key'] == 'gitlab'


def test_match_url_gitlab_enterprise():
    """Test URL matching for GitLab enterprise (self-hosted)."""
    match = _match_url('https://gitlab.example.com/org/repo.git', TEST_PATTERNS)
    assert match is not None
    assert match['provider_key'] == 'gitlab'


def test_match_url_unknown():
    """Test URL matching returns None for unknown providers."""
    match = _match_url('https://bitbucket.org/org/repo.git', TEST_PATTERNS)
    assert match is None


def test_match_directory_github(tmp_path):
    """Test directory marker matching for .github."""
    (tmp_path / '.github').mkdir()
    match = _match_directory(tmp_path, TEST_PATTERNS)
    assert match is not None
    assert match['provider_key'] == 'github'


def test_match_directory_gitlab(tmp_path):
    """Test directory marker matching for .gitlab-ci.yml."""
    (tmp_path / '.gitlab-ci.yml').touch()
    match = _match_directory(tmp_path, TEST_PATTERNS)
    assert match is not None
    assert match['provider_key'] == 'gitlab'


def test_match_directory_unknown(tmp_path):
    """Test directory marker returns None when no markers found."""
    match = _match_directory(tmp_path, TEST_PATTERNS)
    assert match is None


@patch('ci_health.DETECTION_PATTERNS', TEST_PATTERNS)
@patch('ci_health.run_command')
def test_detect_provider_github_url(mock_run):
    """Test detect_provider matches GitHub via URL patterns."""
    mock_run.return_value = (0, 'https://github.com/org/repo.git\n', '')
    result = detect_provider()
    assert result['provider'] == 'github'
    assert result['confidence'] == 'high'


@patch('ci_health.DETECTION_PATTERNS', TEST_PATTERNS)
@patch('ci_health.run_command')
def test_detect_provider_gitlab_enterprise_url(mock_run):
    """Test detect_provider matches GitLab enterprise via enterprise patterns."""
    mock_run.return_value = (0, 'https://gitlab.mycompany.com/org/repo.git\n', '')
    result = detect_provider()
    assert result['provider'] == 'gitlab'
    assert result['confidence'] == 'high'


@patch('ci_health.DETECTION_PATTERNS', TEST_PATTERNS)
@patch('ci_health.run_command')
def test_detect_provider_directory_fallback(mock_run, tmp_path):
    """Test detect_provider falls back to directory markers when URL unknown."""
    mock_run.return_value = (0, 'https://unknown.example.com/repo.git\n', '')
    (tmp_path / '.github').mkdir()
    result = detect_provider(cwd=str(tmp_path))
    assert result['provider'] == 'github'
    assert result['confidence'] == 'medium'


@patch('ci_health.DETECTION_PATTERNS', TEST_PATTERNS)
@patch('ci_health.run_command')
def test_detect_provider_no_remote_with_markers(mock_run, tmp_path):
    """Test detect_provider uses directory markers when no git remote."""
    mock_run.return_value = (1, '', 'fatal: not a git repository')
    (tmp_path / '.gitlab-ci.yml').touch()
    result = detect_provider(cwd=str(tmp_path))
    assert result['provider'] == 'gitlab'
    assert result['confidence'] == 'medium'


@patch('ci_health.DETECTION_PATTERNS', TEST_PATTERNS)
@patch('ci_health.run_command')
def test_detect_provider_unknown(mock_run, tmp_path):
    """Test detect_provider returns unknown when nothing matches."""
    mock_run.return_value = (0, 'https://bitbucket.org/org/repo.git\n', '')
    result = detect_provider(cwd=str(tmp_path))
    assert result['provider'] == 'unknown'
    assert result['confidence'] == 'none'


@patch('ci_health.DETECTION_PATTERNS', [])
@patch('ci_health.run_command')
def test_detect_provider_no_patterns(mock_run):
    """Test detect_provider returns unknown when no patterns configured."""
    mock_run.return_value = (0, 'https://github.com/org/repo.git\n', '')
    result = detect_provider()
    assert result['provider'] == 'unknown'
    assert result['confidence'] == 'none'


# =============================================================================
# Tier 2: ci_base re-export compatibility tests
# =============================================================================


def test_ci_health_imports_safe_main_via_ci_base():
    """Verify ci_health.safe_main is the ci_base re-export (not a direct file_ops import)."""
    import ci_base
    import ci_health

    # ci_health imports safe_main from ci_base; ci_base re-exports from file_ops.
    # Both must resolve to the exact same function object.
    assert ci_health.safe_main is ci_base.safe_main


def test_ci_health_imports_serialize_toon_via_ci_base():
    """Verify ci_health.serialize_toon is the ci_base re-export."""
    import ci_base
    import ci_health

    assert ci_health.serialize_toon is ci_base.serialize_toon


def test_ci_health_imports_run_cli_from_ci_base():
    """Verify ci_health.run_cli comes from ci_base (shared CLI runner)."""
    import ci_base
    import ci_health

    assert ci_health.run_cli is ci_base.run_cli


# =============================================================================
# Tier 3: Subprocess tests for CLI plumbing
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


def test_verify_all_no_marshal_json():
    """Test verify-all fails when marshal.json is missing."""
    with PlanContext(plan_id='test-verify-all-missing'):
        result = run_script(SCRIPT_PATH, 'verify-all')
        assert result.success, 'Expected exit 0 (error in TOON output)'
        data = result.toon_or_error()
        assert data.get('status') != 'success', 'Expected error status in TOON output'
        assert 'error' in data


def test_verify_all_with_marshal_json():
    """Test verify-all succeeds and does NOT write config['ci']."""
    with PlanContext(plan_id='test-verify-all-success') as ctx:
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps({
            'version': 1,
            'providers': [{
                'skill_name': 'plan-marshall:workflow-integration-github',
                'category': 'ci',
                'verify_command': 'gh auth status',
            }],
        }))

        result = run_script(SCRIPT_PATH, 'verify-all')
        assert result.success, f'Script failed: {result.stderr}'

        updated = json.loads(marshal_path.read_text())
        # providers[] is the canonical source — verify-all must not write config['ci']
        assert 'ci' not in updated, f"verify-all should not write config['ci'], got: {updated.get('ci')}"
        assert updated['providers'][0]['category'] == 'ci'


def test_verify_all_leaves_providers_intact():
    """Test verify-all leaves providers[] untouched (single source of truth)."""
    with PlanContext(plan_id='test-verify-all-intact') as ctx:
        marshal_path = ctx.fixture_dir / 'marshal.json'
        original_providers = [{
            'skill_name': 'plan-marshall:workflow-integration-github',
            'category': 'ci',
            'verify_command': 'gh auth status',
        }]
        marshal_path.write_text(json.dumps({
            'version': 1,
            'providers': original_providers,
        }))

        result = run_script(SCRIPT_PATH, 'verify-all')
        assert result.success, f'Script failed: {result.stderr}'

        updated = json.loads(marshal_path.read_text())
        assert 'ci' not in updated
        assert updated['providers'] == original_providers
