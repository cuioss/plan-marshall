#!/usr/bin/env python3
"""Tests for profiles.py module."""

import sys
import tempfile
from pathlib import Path

# Import shared infrastructure (sets up PYTHONPATH for cross-skill imports)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Direct imports - conftest sets up PYTHONPATH
from _architecture_core import save_derived_data
from profiles import (
    classify_profile,
    get_unmatched_profiles,
    list_profiles,
    suggest_classifications,
)

# =============================================================================
# Helper Functions
# =============================================================================


def create_test_derived_data(tmpdir: str, profiles: list | None = None) -> dict:
    """Create test derived-data.json with Maven module and profiles."""
    if profiles is None:
        profiles = [
            {'id': 'jacoco', 'canonical': 'coverage'},
            {'id': 'it-tests', 'canonical': 'integration-tests'},
            {'id': 'apache-release', 'canonical': 'NO-MATCH-FOUND'},
            {'id': 'custom-profile', 'canonical': 'NO-MATCH-FOUND'},
        ]

    test_data = {
        'project': {'name': 'test-project'},
        'modules': {
            'module-a': {
                'name': 'module-a',
                'build_systems': ['maven'],
                'paths': {'module': 'module-a'},
                'metadata': {'profiles': profiles},
                'packages': {},
                'dependencies': [],
                'commands': {},
            }
        },
    }
    save_derived_data(test_data, tmpdir)
    return test_data


# =============================================================================
# Tests for classify_profile
# =============================================================================


def test_classify_jacoco():
    """classify_profile identifies jacoco as coverage."""
    result = classify_profile('jacoco')
    assert result['classification'] == 'coverage'
    assert result['confidence'] == 'high'


def test_classify_integration_tests():
    """classify_profile identifies integration-tests pattern."""
    result = classify_profile('integration-tests')
    assert result['classification'] == 'integration-tests'


def test_classify_it():
    """classify_profile identifies it as integration-tests."""
    result = classify_profile('it-tests')
    assert result['classification'] == 'integration-tests'


def test_classify_jmh():
    """classify_profile identifies jmh as benchmark."""
    result = classify_profile('jmh')
    assert result['classification'] == 'benchmark'


def test_classify_benchmark():
    """classify_profile identifies benchmark as benchmark."""
    result = classify_profile('benchmark')
    assert result['classification'] == 'benchmark'


def test_classify_pre_commit():
    """classify_profile identifies pre-commit as quality-gate."""
    result = classify_profile('pre-commit')
    assert result['classification'] == 'quality-gate'


def test_classify_apache_release():
    """classify_profile identifies apache-release as skip."""
    result = classify_profile('apache-release')
    assert result['classification'] == 'skip'


def test_classify_skip_tests():
    """classify_profile identifies skip-tests as skip."""
    result = classify_profile('skip-tests')
    assert result['classification'] == 'skip'


def test_classify_unknown():
    """classify_profile returns unknown for unrecognized profile."""
    result = classify_profile('my-custom-thing')
    assert result['classification'] == 'unknown'
    assert result['confidence'] == 'low'


# =============================================================================
# Tests for list_profiles
# =============================================================================


def test_list_profiles_returns_all():
    """list_profiles returns all profiles from Maven modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        result = list_profiles(tmpdir)

        assert result['total_profiles'] == 4
        assert len(result['modules']) == 1
        assert result['modules'][0]['name'] == 'module-a'


def test_list_profiles_counts_unmatched():
    """list_profiles counts unmatched profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        result = list_profiles(tmpdir)

        assert result['unmatched_count'] == 2  # apache-release, custom-profile


def test_list_profiles_filters_by_module():
    """list_profiles can filter by module name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        result = list_profiles(tmpdir, module_name='module-a')
        assert len(result['modules']) == 1

        result = list_profiles(tmpdir, module_name='nonexistent')
        assert len(result['modules']) == 0


# =============================================================================
# Tests for get_unmatched_profiles
# =============================================================================


def test_get_unmatched_profiles():
    """get_unmatched_profiles returns deduplicated list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        unmatched = get_unmatched_profiles(tmpdir)

        assert len(unmatched) == 2
        assert 'apache-release' in unmatched
        assert 'custom-profile' in unmatched


def test_get_unmatched_profiles_empty():
    """get_unmatched_profiles returns empty list when all matched."""
    with tempfile.TemporaryDirectory() as tmpdir:
        profiles = [
            {'id': 'jacoco', 'canonical': 'coverage'},
            {'id': 'it-tests', 'canonical': 'integration-tests'},
        ]
        create_test_derived_data(tmpdir, profiles)

        unmatched = get_unmatched_profiles(tmpdir)

        assert len(unmatched) == 0


# =============================================================================
# Tests for suggest_classifications
# =============================================================================


def test_suggest_classifications():
    """suggest_classifications returns suggestions for unmatched."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        suggestions = suggest_classifications(tmpdir)

        assert len(suggestions) == 2

        # Find apache-release suggestion
        apache_suggestion = next(s for s in suggestions if s['profile_id'] == 'apache-release')
        assert apache_suggestion['suggested'] == 'skip'

        # Find custom-profile suggestion
        custom_suggestion = next(s for s in suggestions if s['profile_id'] == 'custom-profile')
        assert custom_suggestion['suggested'] == 'unknown'


if __name__ == '__main__':
    import pytest

    sys.exit(pytest.main([__file__, '-v']))
