#!/usr/bin/env python3
"""Tests for npm-output.py - npm build output analysis tool.

Tests the parse subcommand for analyzing npm/npx build logs.
"""

from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('pm-dev-frontend-cui', 'cui-javascript-project', 'npm-output.py')
FIXTURES_DIR = Path(__file__).parent / 'build'


# =============================================================================
# Main help tests
# =============================================================================


def test_script_exists():
    """Test that the script exists."""
    assert SCRIPT_PATH.exists(), f'Script not found: {SCRIPT_PATH}'


def test_main_help():
    """Test main --help displays all subcommands."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'parse' in combined, 'parse subcommand in help'


def test_parse_help():
    """Test parse --help displays usage."""
    result = run_script(SCRIPT_PATH, 'parse', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), 'Parse help not shown'


# =============================================================================
# Parse subcommand tests
# =============================================================================


def test_parse_successful_build():
    """Test parsing successful build log."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'successful-build.log'))
    data = result.json()
    assert data['status'] == 'success', 'Successfully parsed build log'


def test_parse_failed_build():
    """Test parsing failed build log."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'failed-build.log'))
    data = result.json()
    assert data['status'] == 'failure', 'Detected build failure'


def test_parse_test_failure_log():
    """Test parsing test failure log."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'test-failure.log'))
    data = result.json()
    assert 'metrics' in data, 'Metrics present in output'


def test_parse_structured_mode():
    """Test structured output mode."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'failed-build.log'), '--mode', 'structured')
    data = result.json()
    assert 'issues' in data.get('data', {}), 'Structured mode has issues array'


def test_parse_errors_mode():
    """Test errors-only output mode."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'failed-build.log'), '--mode', 'errors')
    data = result.json()
    assert 'errors' in data.get('data', {}), 'Errors mode has errors array'


def test_parse_missing_log_error():
    """Test error handling for missing log file."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', 'nonexistent.log')
    data = result.json()
    assert data['status'] == 'error', 'Returns error for missing file'


def test_parse_output_file_field():
    """Test output_file field is present."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'successful-build.log'))
    data = result.json()
    assert 'output_file' in data.get('data', {}), 'output_file field present'


def test_parse_workspace_build():
    """Test parsing workspace/monorepo build log."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'workspace-build.log'))
    data = result.json()
    assert data['status'] in ['success', 'failure'], 'Parsed workspace build'


# =============================================================================
# Vitest pattern tests
# =============================================================================


def test_parse_vitest_failure_detected():
    """Test that Vitest failure log is classified as failure."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'vitest-failure.log'))
    data = result.json()
    assert data['status'] == 'failure', 'Vitest failure log classified as failure'


def test_parse_vitest_test_failure_issues():
    """Test that Vitest × marker, RERUN, and AssertionError lines produce test_failure issues."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'vitest-failure.log'), '--mode', 'structured')
    data = result.json()
    issues = data['data']['issues']
    test_failure_types = [i for i in issues if i['type'] == 'test_failure']
    assert len(test_failure_types) > 0, 'Vitest failure lines categorized as test_failure'


def test_parse_vitest_failure_metrics():
    """Test that Vitest failure metrics count test failures and summary line."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'vitest-failure.log'), '--mode', 'structured')
    data = result.json()
    metrics = data['metrics']
    assert metrics['test_failures'] > 0, 'Vitest test_failures counter > 0'
    assert metrics['total_errors'] > 0, 'Vitest total_errors counter > 0'


def test_parse_vitest_assertion_error_pattern():
    """Test that AssertionError lines are recognized as test failures."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'vitest-failure.log'), '--mode', 'structured')
    data = result.json()
    issues = data['data']['issues']
    messages = [i['message'] for i in issues]
    assertion_issues = [m for m in messages if 'AssertionError' in m]
    assert len(assertion_issues) > 0, 'AssertionError lines captured as issues'


# =============================================================================
# TypeScript tsc pattern tests
# =============================================================================


def test_parse_typescript_error_detected():
    """Test that TypeScript tsc error log is classified as failure."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'typescript-error.log'))
    data = result.json()
    assert data['status'] == 'failure', 'TypeScript tsc error log classified as failure'


def test_parse_typescript_compilation_issues():
    """Test that tsc file-location format lines produce compilation_error issues."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'typescript-error.log'), '--mode', 'structured')
    data = result.json()
    issues = data['data']['issues']
    compilation_types = [i for i in issues if i['type'] == 'compilation_error']
    assert len(compilation_types) > 0, 'TypeScript errors categorized as compilation_error'


def test_parse_typescript_file_location_extracted():
    """Test that tsc file(line,col) format extracts file path correctly."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'typescript-error.log'), '--mode', 'structured')
    data = result.json()
    issues = data['data']['issues']
    issues_with_file = [i for i in issues if i['file'] is not None and '.ts' in i['file']]
    assert len(issues_with_file) > 0, 'File path extracted from tsc file(line,col) format'


def test_parse_typescript_metrics():
    """Test that typescript_errors metric counts TS errors."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'typescript-error.log'), '--mode', 'structured')
    data = result.json()
    metrics = data['metrics']
    assert metrics['typescript_errors'] > 0, 'typescript_errors metric > 0 for tsc output'
    assert metrics['compilation_errors'] > 0, 'compilation_errors metric > 0'


# =============================================================================
# Biome linter pattern tests
# =============================================================================


def test_parse_biome_error_detected():
    """Test that Biome linter error log is classified as failure."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'biome-error.log'))
    data = result.json()
    assert data['status'] == 'failure', 'Biome error log classified as failure'


def test_parse_biome_lint_issues():
    """Test that Biome lint/suspicious/noExplicitAny and error[lint/...] lines produce lint_error issues."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'biome-error.log'), '--mode', 'structured')
    data = result.json()
    issues = data['data']['issues']
    lint_types = [i for i in issues if i['type'] == 'lint_error']
    assert len(lint_types) > 0, 'Biome lint lines categorized as lint_error'


def test_parse_biome_found_errors_summary():
    """Test that Biome 'Found N errors.' summary line triggers failure classification."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'biome-error.log'), '--mode', 'structured')
    data = result.json()
    issues = data['data']['issues']
    messages = [i['message'] for i in issues]
    found_errors_lines = [m for m in messages if 'Found' in m and 'error' in m.lower()]
    assert len(found_errors_lines) > 0, 'Biome Found N errors summary line captured'


def test_parse_biome_metrics():
    """Test that biome_errors metric counts Biome lint errors."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'biome-error.log'), '--mode', 'structured')
    data = result.json()
    metrics = data['metrics']
    assert metrics['biome_errors'] > 0, 'biome_errors metric > 0 for Biome output'
    assert metrics['lint_errors'] > 0, 'lint_errors metric > 0'


def test_parse_biome_warning_severity():
    """Test that Biome warn[lint/...] lines are categorized as WARNING severity."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'biome-error.log'), '--mode', 'structured')
    data = result.json()
    issues = data['data']['issues']
    warning_issues = [i for i in issues if i['severity'] == 'WARNING' and i['type'] == 'lint_error']
    assert len(warning_issues) > 0, 'Biome warn[lint/...] lines classified as WARNING'


# =============================================================================
# Playwright modern pattern tests
# =============================================================================


def test_parse_playwright_modern_detected():
    """Test that modern Playwright error log is classified as failure."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'playwright-modern.log'))
    data = result.json()
    assert data['status'] == 'failure', 'Playwright modern error log classified as failure'


def test_parse_playwright_expect_locator_pattern():
    """Test that expect(locator).toBeVisible() Timeout lines are captured as playwright_error."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'playwright-modern.log'), '--mode', 'structured')
    data = result.json()
    issues = data['data']['issues']
    pw_types = [i for i in issues if i['type'] == 'playwright_error']
    assert len(pw_types) > 0, 'Playwright errors categorized as playwright_error'


def test_parse_playwright_wait_for_selector_pattern():
    """Test that page.waitForSelector Timeout lines are captured."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'playwright-modern.log'), '--mode', 'structured')
    data = result.json()
    issues = data['data']['issues']
    messages = [i['message'] for i in issues if i['type'] == 'playwright_error']
    wait_issues = [m for m in messages if 'waitForSelector' in m]
    assert len(wait_issues) > 0, 'page.waitForSelector Timeout line captured'


def test_parse_playwright_browser_launch_pattern():
    """Test that browserType.launch error lines are captured."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'playwright-modern.log'), '--mode', 'structured')
    data = result.json()
    issues = data['data']['issues']
    messages = [i['message'] for i in issues if i['type'] == 'playwright_error']
    launch_issues = [m for m in messages if 'browserType.launch' in m]
    assert len(launch_issues) > 0, 'browserType.launch error line captured'


def test_parse_playwright_net_err_pattern():
    """Test that net::ERR_ network error lines are captured."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'playwright-modern.log'), '--mode', 'structured')
    data = result.json()
    issues = data['data']['issues']
    messages = [i['message'] for i in issues if i['type'] == 'playwright_error']
    net_err_issues = [m for m in messages if 'net::ERR' in m]
    assert len(net_err_issues) > 0, 'net::ERR_ network error line captured'


def test_parse_playwright_metrics():
    """Test that playwright_errors metric is populated."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'playwright-modern.log'), '--mode', 'structured')
    data = result.json()
    metrics = data['metrics']
    assert metrics['playwright_errors'] > 0, 'playwright_errors metric > 0'


# =============================================================================
# Main
# =============================================================================
