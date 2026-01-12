#!/usr/bin/env python3
"""Tests for pm-dev-java:build-operations Maven scripts.

Tests all Maven build operations:
- run: Execute build and auto-parse on failure (see test_maven_run.py)
- parse: Parse Maven build output
- search-markers: Search OpenRewrite markers
- check-warnings: Categorize build warnings
"""

import sys
import json
import tempfile
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from conftest import run_script, TestRunner, get_script_path

# Script under test - pm-dev-java bundle
SCRIPT_PATH = get_script_path('pm-dev-java', 'plan-marshall-plugin', 'maven.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures'
MOCKS_DIR = Path(__file__).parent / 'mocks'


# =============================================================================
# Parse Subcommand Tests
# =============================================================================

def test_parse_successful_build():
    """Test parsing successful Maven build output."""
    result = run_script(
        SCRIPT_PATH,
        'parse',
        '--log', str(FIXTURES_DIR / 'sample-maven-success.log'),
        '--mode', 'structured'
    )
    assert result.success, f"Script failed: {result.stderr}"
    data = result.json()

    assert data['status'] == 'success', "Status should be success"
    assert data['data']['build_status'] == 'SUCCESS', "Build status should be SUCCESS"


def test_parse_compilation_errors():
    """Test parsing build with compilation errors."""
    result = run_script(
        SCRIPT_PATH,
        'parse',
        '--log', str(FIXTURES_DIR / 'sample-maven-failure.log'),
        '--mode', 'structured'
    )
    data = result.json()

    assert data['data']['build_status'] == 'FAILURE', "Build status should be FAILURE"
    assert data['data']['summary'].get('compilation_errors', 0) > 0, "Should detect compilation errors"


def test_parse_missing_file():
    """Test missing file handling."""
    result = run_script(
        SCRIPT_PATH,
        'parse',
        '--log', 'nonexistent.log',
        '--mode', 'structured'
    )
    data = result.json()

    assert data['status'] == 'error', "Should return error status for missing file"


# =============================================================================
# Search-Markers Subcommand Tests
# =============================================================================

def test_search_markers_no_markers():
    """Test searching when no markers exist."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        src_dir = temp_dir / 'src' / 'main' / 'java'
        src_dir.mkdir(parents=True)
        java_file = src_dir / 'Test.java'
        java_file.write_text('public class Test {}')

        result = run_script(
            SCRIPT_PATH,
            'search-markers',
            '--source-dir', str(temp_dir / 'src')
        )
        data = result.json()

        assert data['status'] == 'success', "Should succeed with no markers"
        assert data['data']['total_markers'] == 0, "Should find no markers"


# =============================================================================
# Check-Warnings Subcommand Tests
# =============================================================================

def test_check_warnings_empty():
    """Test with no warnings."""
    warnings = json.dumps([])
    acceptable = json.dumps({})

    result = run_script(
        SCRIPT_PATH,
        'check-warnings',
        '--warnings', warnings,
        '--acceptable-warnings', acceptable
    )
    data = result.json()

    assert data['success'] is True, "Should succeed with no warnings"
    assert data['total'] == 0, "Total should be 0"


# =============================================================================
# Help Tests
# =============================================================================

def test_help_main():
    """Test main --help output."""
    result = run_script(SCRIPT_PATH, '--help')
    assert 'run' in result.stdout, "Should show run subcommand"
    assert 'parse' in result.stdout, "Should show parse subcommand"
    assert 'search-markers' in result.stdout, "Should show search-markers subcommand"


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        test_parse_successful_build,
        test_parse_compilation_errors,
        test_parse_missing_file,
        test_search_markers_no_markers,
        test_check_warnings_empty,
        test_help_main,
    ])
    sys.exit(runner.run())
