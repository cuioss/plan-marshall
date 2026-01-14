#!/usr/bin/env python3
"""Tests for analyze.py - consolidated plugin analysis tools.

Consolidates tests from:
- test_analyze_skill_structure.py (structure subcommand)
- test_analyze_cross_file_content.py (cross-file subcommand)

Tests plugin component analysis capabilities.
"""

from pathlib import Path

# Import shared infrastructure
from conftest import get_script_path, run_script

# Script under test
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-doctor', '_analyze.py')
SKILL_STRUCTURE_FIXTURES = Path(__file__).parent / 'fixtures' / 'skill-structure'
CROSS_FILE_FIXTURES = Path(__file__).parent / 'fixtures' / 'cross-file-analysis'


# =============================================================================
# Main help tests
# =============================================================================


def test_script_exists():
    """Test that script exists."""
    assert Path(SCRIPT_PATH).exists(), f'Script not found: {SCRIPT_PATH}'


def test_main_help():
    """Test main --help displays all subcommands."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'markdown' in combined, 'markdown subcommand in help'
    assert 'structure' in combined, 'structure subcommand in help'
    assert 'coverage' in combined, 'coverage subcommand in help'
    assert 'cross-file' in combined, 'cross-file subcommand in help'


# =============================================================================
# Structure Subcommand Tests (from analyze-skill-structure.py)
# =============================================================================


def test_structure_table_refs_no_unreferenced():
    """Test that table-referenced files are detected (no unreferenced files)."""
    test_dir = SKILL_STRUCTURE_FIXTURES / 'table-references'
    if not test_dir.exists():
        return  # Skip if fixture not available

    result = run_script(SCRIPT_PATH, 'structure', '--directory', str(test_dir))
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = result.json()
    unreferenced = data.get('standards_files', {}).get('unreferenced_files', [])
    assert len(unreferenced) == 0, f'Should have no unreferenced files, found {len(unreferenced)}'


def test_structure_table_refs_no_missing():
    """Test that all referenced files exist (no missing files)."""
    test_dir = SKILL_STRUCTURE_FIXTURES / 'table-references'
    if not test_dir.exists():
        return  # Skip if fixture not available

    result = run_script(SCRIPT_PATH, 'structure', '--directory', str(test_dir))
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = result.json()
    missing = data.get('standards_files', {}).get('missing_files', [])
    assert len(missing) == 0, f'Should have no missing files, found {len(missing)}'


def test_structure_table_refs_perfect_score():
    """Test perfect score for table-referenced files."""
    test_dir = SKILL_STRUCTURE_FIXTURES / 'table-references'
    if not test_dir.exists():
        return  # Skip if fixture not available

    result = run_script(SCRIPT_PATH, 'structure', '--directory', str(test_dir))
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = result.json()
    score = data.get('structure_score', 0)
    assert score >= 100, f'Score should be 100, got {score}'


def test_structure_code_block_no_false_positive():
    """Test that example paths in code blocks are NOT detected as missing."""
    test_dir = SKILL_STRUCTURE_FIXTURES / 'code-block-examples'
    if not test_dir.exists():
        return  # Skip if fixture not available

    result = run_script(SCRIPT_PATH, 'structure', '--directory', str(test_dir))
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = result.json()
    missing = data.get('standards_files', {}).get('missing_files', [])
    assert len(missing) == 0, f'Should not flag code block examples as missing, found {len(missing)}'


def test_structure_cross_skill_no_false_positive():
    """Test that cross-skill references are NOT flagged as missing."""
    test_dir = SKILL_STRUCTURE_FIXTURES / 'cross-skill-references'
    if not test_dir.exists():
        return  # Skip if fixture not available

    result = run_script(SCRIPT_PATH, 'structure', '--directory', str(test_dir))
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = result.json()
    missing = data.get('standards_files', {}).get('missing_files', [])
    assert len(missing) == 0, f'Cross-skill refs should not be flagged as missing, found {len(missing)}'


def test_structure_real_plugin_doctor():
    """Test plugin-doctor skill (has table-format refs and cross-skill refs)."""
    skill_dir = PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'skills' / 'plugin-doctor'
    if not skill_dir.exists():
        return  # Skip if not found

    result = run_script(SCRIPT_PATH, 'structure', '--directory', str(skill_dir))
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = result.json()
    score = data.get('structure_score', 0)
    assert score >= 90, f'plugin-doctor should score >= 90, got {score}'


# =============================================================================
# Cross-File Subcommand Tests (from analyze-cross-file-content.py)
# =============================================================================


def test_crossfile_help():
    """Test cross-file --help is available."""
    result = run_script(SCRIPT_PATH, 'cross-file', '--help')
    assert 'skill-path' in result.stdout or 'skill-path' in result.stderr, (
        'Help output should contain skill-path option'
    )


def test_crossfile_missing_argument():
    """Test returns error for missing argument."""
    result = run_script(SCRIPT_PATH, 'cross-file')
    assert result.returncode != 0, 'Should return error for missing argument'
    output = result.stderr.lower() + result.stdout.lower()
    assert 'error' in output or 'required' in output, 'Should indicate error for missing argument'


def test_crossfile_invalid_path():
    """Test returns error for invalid path."""
    result = run_script(SCRIPT_PATH, 'cross-file', '--skill-path', '/nonexistent/path')
    assert result.returncode != 0, 'Should return error for invalid path'
    output = result.stderr.lower() + result.stdout.lower()
    assert 'not found' in output or 'error' in output, 'Should indicate path not found'


def test_crossfile_duplicates_valid_json():
    """Test returns valid JSON for skill with duplicates."""
    skill_path = CROSS_FILE_FIXTURES / 'skill-with-duplicates'
    if not skill_path.exists():
        return  # Skip if fixture not available

    result = run_script(SCRIPT_PATH, 'cross-file', '--skill-path', str(skill_path))
    data = result.json()
    assert data is not None, 'Should return valid JSON'


def test_crossfile_detect_exact_duplicates():
    """Test detection of exact duplicates."""
    skill_path = CROSS_FILE_FIXTURES / 'skill-with-duplicates'
    if not skill_path.exists():
        return  # Skip if fixture not available

    result = run_script(SCRIPT_PATH, 'cross-file', '--skill-path', str(skill_path))
    data = result.json()

    exact_duplicates = data.get('exact_duplicates', [])
    assert len(exact_duplicates) >= 1, f'Should detect exact duplicates, found {len(exact_duplicates)}'


def test_crossfile_extraction_candidates():
    """Test extraction_candidates field exists."""
    skill_path = CROSS_FILE_FIXTURES / 'skill-with-duplicates'
    if not skill_path.exists():
        return  # Skip if fixture not available

    result = run_script(SCRIPT_PATH, 'cross-file', '--skill-path', str(skill_path))
    data = result.json()

    assert 'extraction_candidates' in data, 'Should have extraction_candidates field'


def test_crossfile_llm_review_flag():
    """Test contains llm_review_required flag in summary."""
    skill_path = CROSS_FILE_FIXTURES / 'skill-with-duplicates'
    if not skill_path.exists():
        return  # Skip if fixture not available

    result = run_script(SCRIPT_PATH, 'cross-file', '--skill-path', str(skill_path))
    data = result.json()

    summary = data.get('summary', {})
    assert 'llm_review_required' in summary, 'Should contain llm_review_required flag in summary'


def test_crossfile_clean_skill():
    """Test returns valid JSON for clean skill."""
    skill_path = CROSS_FILE_FIXTURES / 'skill-clean'
    if not skill_path.exists():
        return  # Skip if fixture not available

    result = run_script(SCRIPT_PATH, 'cross-file', '--skill-path', str(skill_path))
    data = result.json()
    assert data is not None, 'Should return valid JSON for clean skill'


def test_crossfile_custom_threshold():
    """Test accepts custom similarity threshold."""
    skill_path = CROSS_FILE_FIXTURES / 'skill-clean'
    if not skill_path.exists():
        return  # Skip if fixture not available

    result = run_script(SCRIPT_PATH, 'cross-file', '--skill-path', str(skill_path), '--similarity-threshold', '0.3')
    data = result.json()
    assert data is not None, 'Should accept custom similarity threshold'


# =============================================================================
# Main
# =============================================================================
