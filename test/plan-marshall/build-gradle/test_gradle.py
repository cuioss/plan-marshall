#!/usr/bin/env python3
"""Tests for plan-marshall:build-gradle scripts.

Tests all Gradle build operations:
- run: Execute Gradle builds (primary API)
- parse: Parse Gradle build output
- find-project: Find Gradle project paths
- search-markers: Search OpenRewrite markers
- check-warnings: Categorize build warnings
"""

import json
import sys
import tempfile
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from conftest import get_script_path, run_script

# Script under test - plan-marshall bundle
SCRIPT_PATH = get_script_path('plan-marshall', 'build-gradle', 'gradle.py')
FIXTURES_DIR = Path(__file__).parent / 'fixtures'
MOCKS_DIR = Path(__file__).parent / 'mocks'


# =============================================================================
# Parse Subcommand Tests
# =============================================================================


def test_parse_successful_build():
    """Test parsing successful Gradle build output."""
    result = run_script(
        SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'sample-gradle-success.log'),
        '--mode', 'structured', '--format', 'json',
    )
    assert result.success, f'Script failed: {result.stderr}'
    data = result.json()

    assert data['status'] == 'success', 'Status should be success'
    assert data['data']['build_status'] == 'SUCCESS', 'Build status should be SUCCESS'


def test_parse_compilation_errors():
    """Test parsing build with compilation errors."""
    result = run_script(
        SCRIPT_PATH, 'parse', '--log', str(FIXTURES_DIR / 'sample-gradle-failure.log'),
        '--mode', 'structured', '--format', 'json',
    )
    data = result.json()

    assert data['data']['build_status'] == 'FAILURE', 'Build status should be FAILURE'


def test_parse_missing_file():
    """Test missing file handling."""
    result = run_script(SCRIPT_PATH, 'parse', '--log', 'nonexistent.log', '--mode', 'structured')
    data = result.json()

    assert data['status'] == 'error', 'Should return error status for missing file'


# =============================================================================
# Find-Project Subcommand Tests
# =============================================================================


def test_find_project_by_name():
    """Test finding project by name (TOON output)."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        project_dir = temp_dir / 'modules' / 'auth-service'
        project_dir.mkdir(parents=True)
        build_file = project_dir / 'build.gradle'
        build_file.write_text('// Gradle build file')

        result = run_script(SCRIPT_PATH, 'find-project', '--project-name', 'auth-service', '--root', str(temp_dir))
        data = result.toon()

        assert data['status'] == 'success', f'Should find project: {data}'


def test_find_project_not_found():
    """Test finding non-existent project (TOON output)."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        result = run_script(SCRIPT_PATH, 'find-project', '--project-name', 'nonexistent', '--root', str(temp_dir))
        data = result.toon()

        assert data['status'] == 'error', 'Should return error for non-existent project'


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

        result = run_script(SCRIPT_PATH, 'search-markers', '--source-dir', str(temp_dir / 'src'))
        data = result.json()

        assert data['status'] == 'success', 'Should succeed with no markers'
        assert data['data']['total_markers'] == 0, 'Should find no markers'


# =============================================================================
# Check-Warnings Subcommand Tests
# =============================================================================


def test_check_warnings_empty():
    """Test with no warnings."""
    warnings = json.dumps([])
    acceptable = json.dumps({})

    result = run_script(SCRIPT_PATH, 'check-warnings', '--warnings', warnings, '--acceptable-warnings', acceptable)
    data = result.json()

    assert data['success'] is True, 'Should succeed with no warnings'
    assert data['total'] == 0, 'Total should be 0'


def test_check_warnings_with_real_patterns():
    """Test check-warnings with real warning data and acceptable patterns (H45).

    Gradle uses wildcard matching with no severity filter.
    Patterns must match as wildcard (* prefix/suffix for substring).
    """
    warnings = json.dumps([
        {'message': '[deprecation] DeprecatedApi has been deprecated'},
        {'message': '[unchecked] unchecked conversion'},
        {'message': 'some random warning'},
    ])
    acceptable = json.dumps({
        'patterns': ['*[deprecation]*', '*[unchecked]*'],
    })

    result = run_script(SCRIPT_PATH, 'check-warnings', '--warnings', warnings, '--acceptable-warnings', acceptable)
    data = result.json()

    assert data['success'] is True, 'Should succeed'
    assert data['total'] == 3, f'Should count all warnings, got: {data}'
    assert data['acceptable'] >= 2, f'Should accept deprecation and unchecked, got: {data}'


def test_search_markers_with_content():
    """Test searching when markers exist in source files (H49)."""
    markers_dir = FIXTURES_DIR / 'source-with-markers'
    result = run_script(SCRIPT_PATH, 'search-markers', '--source-dir', str(markers_dir / 'src'))
    data = result.json()

    assert data['status'] == 'success', 'Should succeed'
    assert data['data']['total_markers'] > 0, 'Should find markers in fixture files'


# =============================================================================
# Help Tests
# =============================================================================


def test_help_main():
    """Test main --help output."""
    result = run_script(SCRIPT_PATH, '--help')
    assert 'run' in result.stdout, 'Should show run subcommand'
    assert 'parse' in result.stdout, 'Should show parse subcommand'
    assert 'find-project' in result.stdout, 'Should show find-project subcommand'


# =============================================================================
# Main
# =============================================================================
