#!/usr/bin/env python3
"""Tests for profiles.py module.

Seeds project architecture data using the per-module on-disk layout
(``_project.json`` + per-module ``derived.json``) introduced by D2.
The legacy monolithic ``derived-data.json`` shape is intentionally
absent from this surface — TASK-2 removed it from ``_architecture_core``.
"""

import sys
import tempfile

# Direct imports - conftest sets up PYTHONPATH
from _architecture_core import save_module_derived, save_project_meta
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
    """Seed per-module layout (``_project.json`` + per-module ``derived.json``).

    Writes a single Maven module ``module-a`` whose ``metadata.profiles`` is
    the supplied (or default) profile list. Returns the same shape the
    legacy helper returned so call-sites that inspect the dict (none today,
    but kept stable for the test contract) continue to work.
    """
    if profiles is None:
        profiles = [
            {'id': 'jacoco', 'canonical': 'coverage'},
            {'id': 'it-tests', 'canonical': 'integration-tests'},
            {'id': 'apache-release', 'canonical': 'NO-MATCH-FOUND'},
            {'id': 'custom-profile', 'canonical': 'NO-MATCH-FOUND'},
        ]

    module_data = {
        'name': 'module-a',
        'build_systems': ['maven'],
        'paths': {'module': 'module-a'},
        'metadata': {'profiles': profiles},
        'packages': {},
        'dependencies': [],
        'commands': {},
    }

    # _project.json — top-level meta with the modules index. The index is the
    # canonical "which modules exist" source; iter_modules() reads from it.
    save_project_meta(
        {
            'name': 'test-project',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {'module-a': {}},
        },
        tmpdir,
    )
    # Per-module derived.json — production-side helpers (list_profiles,
    # get_unmatched_profiles, suggest_classifications) consume it via
    # load_module_derived().
    save_module_derived('module-a', module_data, tmpdir)

    return {
        'project': {'name': 'test-project'},
        'modules': {'module-a': module_data},
    }


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


def test_classify_e2e():
    """classify_profile identifies e2e-tests as e2e."""
    result = classify_profile('e2e-tests')
    assert result['classification'] == 'e2e'
    assert result['confidence'] == 'high'


def test_classify_acceptance():
    """classify_profile identifies acceptance-tests as e2e."""
    result = classify_profile('acceptance-tests')
    assert result['classification'] == 'e2e'


def test_classify_end_to_end():
    """classify_profile identifies end-to-end as e2e."""
    result = classify_profile('end-to-end')
    assert result['classification'] == 'e2e'


def test_classify_e2e_not_integration():
    """classify_profile does not classify e2e as integration-tests."""
    result = classify_profile('e2e-tests')
    assert result['classification'] != 'integration-tests'


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
