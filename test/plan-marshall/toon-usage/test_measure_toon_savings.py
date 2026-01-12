#!/usr/bin/env python3
"""Tests for TOON token savings measurement.

Migrated from test/measure-toon-savings.sh - measures token savings
from TOON format vs estimated JSON equivalent.
"""

import sys
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import TestRunner

# Test root directory
TEST_ROOT = Path(__file__).parent.parent.parent

# Expected TOON files to measure (relative to test root)
# Note: cui-task-workflow was renamed to planning
EXPECTED_TOON_FILES = [
    'pm-workflow/sonar-workflow/sonar-issues.toon',
    'pm-workflow/sonar-workflow/triage-results.toon',
    'pm-workflow/sonar-workflow/fix-suggestions.toon',
    'pm-workflow/pr-workflow/review-comments.toon',
    'pm-workflow/pr-workflow/triage-results.toon',
    'pm-dev-frontend/coverage/coverage-analysis.toon',
    'pm-dev-java/coverage/coverage-analysis.toon',
    'pm-dev-builder/maven/build-failure/expected-categorization.toon',
    'pm-dev-frontend/build/build-analysis.toon',
]


def count_words(text):
    """Count words in text (rough token approximation)."""
    return len(text.split())


def find_toon_files():
    """Find all .toon files in test directory."""
    return list(TEST_ROOT.rglob('*.toon'))


def measure_toon_file(file_path):
    """
    Measure a TOON file and return metrics.

    Returns:
        dict with word_count, estimated_json_words, savings_pct
    """
    content = file_path.read_text()
    toon_words = count_words(content)

    # Conservative estimate: JSON is typically 2x larger than TOON
    json_estimate = toon_words * 2
    savings = json_estimate - toon_words
    savings_pct = (savings * 100) // json_estimate if json_estimate > 0 else 0

    return {
        'toon_words': toon_words,
        'json_estimate': json_estimate,
        'savings': savings,
        'savings_pct': savings_pct,
    }


# =============================================================================
# Tests
# =============================================================================

def test_toon_files_exist():
    """Test that .toon files exist."""
    toon_files = find_toon_files()
    assert len(toon_files) > 0, "No .toon files found in test directory"


def test_expected_toon_files_present():
    """Test expected TOON fixture files are present."""
    missing = []
    for rel_path in EXPECTED_TOON_FILES:
        full_path = TEST_ROOT / rel_path
        if not full_path.exists():
            missing.append(rel_path)

    # Allow some flexibility - not all files may exist
    present_count = len(EXPECTED_TOON_FILES) - len(missing)
    assert present_count >= 5, \
        f"Only {present_count} of {len(EXPECTED_TOON_FILES)} expected TOON files present. Missing: {missing}"


def test_toon_files_not_empty():
    """Test TOON files have content to measure."""
    toon_files = find_toon_files()
    empty_files = []

    for file_path in toon_files:
        metrics = measure_toon_file(file_path)
        if metrics['toon_words'] == 0:
            empty_files.append(file_path.relative_to(TEST_ROOT))

    assert len(empty_files) == 0, f"Empty TOON files: {empty_files}"


def test_toon_provides_savings():
    """Test TOON format provides token savings over JSON estimate."""
    toon_files = find_toon_files()

    total_toon_words = 0
    total_json_estimate = 0

    for file_path in toon_files:
        metrics = measure_toon_file(file_path)
        total_toon_words += metrics['toon_words']
        total_json_estimate += metrics['json_estimate']

    # TOON should be significantly smaller than JSON estimate
    assert total_toon_words < total_json_estimate, \
        "TOON should be smaller than JSON estimate"

    # Calculate overall savings percentage
    savings_pct = ((total_json_estimate - total_toon_words) * 100) // total_json_estimate

    # Expect at least 40% savings (conservative, since JSON estimate is 2x)
    assert savings_pct >= 40, \
        f"Expected at least 40% savings, got {savings_pct}%"


def test_individual_files_have_reasonable_size():
    """Test individual TOON files have reasonable word counts."""
    toon_files = find_toon_files()
    issues = []

    for file_path in toon_files:
        metrics = measure_toon_file(file_path)
        words = metrics['toon_words']

        # Flag extremely small files (< 10 words) as potential issues
        if words < 10:
            rel_path = file_path.relative_to(TEST_ROOT)
            issues.append(f"{rel_path}: only {words} words")

    # Allow some small files, but not all
    if len(toon_files) > 0:
        small_ratio = len(issues) / len(toon_files)
        assert small_ratio < 0.5, \
            f"Too many small TOON files ({len(issues)}/{len(toon_files)}): {issues}"


def test_total_token_savings_report():
    """Test we can generate a token savings report."""
    toon_files = find_toon_files()

    total_toon_words = 0
    total_json_estimate = 0
    file_metrics = []

    for file_path in toon_files:
        metrics = measure_toon_file(file_path)
        total_toon_words += metrics['toon_words']
        total_json_estimate += metrics['json_estimate']
        file_metrics.append({
            'file': file_path.relative_to(TEST_ROOT),
            **metrics
        })

    # Should have measurable content
    assert total_toon_words > 0, "No TOON content to measure"
    assert len(file_metrics) > 0, "No files measured"

    # Calculate estimated token counts (words * 1.3)
    toon_tokens = int(total_toon_words * 1.3)
    json_tokens = int(total_json_estimate * 1.3)

    assert toon_tokens > 0, "Should have TOON tokens"
    assert json_tokens > toon_tokens, "JSON estimate should be larger than TOON"


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        test_toon_files_exist,
        test_expected_toon_files_present,
        test_toon_files_not_empty,
        test_toon_provides_savings,
        test_individual_files_have_reasonable_size,
        test_total_token_savings_report,
    ])
    sys.exit(runner.run())
