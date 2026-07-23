#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for profiles.py module.

Seeds project architecture data using the per-module on-disk layout
(``_project.json`` + per-module ``derived.json``).
"""

import tempfile
from argparse import Namespace

# Direct imports - conftest sets up PYTHONPATH
from _architecture_core import save_module_derived, save_project_meta
from _config_core import ext_defaults_set
from profiles import (
    classify_profile,
    cmd_classify,
    cmd_list,
    cmd_suggest,
    cmd_unmatched,
    get_configured_mapped_profiles,
    get_configured_skip_profiles,
    get_unmatched_profiles,
    list_profiles,
    suggest_classifications,
)

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('pm-dev-java', 'manage-maven-profiles', 'profiles.py')

# =============================================================================
# Helper Functions
# =============================================================================


def create_test_derived_data(tmpdir: str, profiles: list | None = None) -> dict:
    """Seed per-module layout (``_project.json`` + per-module ``derived.json``).

    Writes a single Maven module ``module-a`` whose ``metadata.profiles`` is
    the supplied (or default) profile list. Returns a dict mirroring the
    seeded data for call-sites that inspect it.
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


# =============================================================================
# Multi-module seeding helper (list_profiles edge behaviors)
# =============================================================================


def _seed_project(tmpdir: str, modules: dict) -> None:
    """Seed ``_project.json`` plus per-module ``derived.json`` for ``modules``.

    ``modules`` maps module name -> ``(build_systems, profiles)``. A module
    whose payload is ``None`` is listed in the project index but has NO
    ``derived.json`` written on disk — the pruned/half-written case
    ``list_profiles`` must skip via its ``DataNotFoundError`` guard.
    """
    save_project_meta(
        {
            'name': 'test-project',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {name: {} for name in modules},
        },
        tmpdir,
    )
    for name, payload in modules.items():
        if payload is None:
            continue
        build_systems, profiles = payload
        save_module_derived(
            name,
            {
                'name': name,
                'build_systems': build_systems,
                'paths': {'module': name},
                'metadata': {'profiles': profiles},
                'packages': {},
                'dependencies': [],
                'commands': {},
            },
            tmpdir,
        )


# =============================================================================
# list_profiles — module-skip behaviors
# =============================================================================


def test_list_profiles_skips_non_maven_modules():
    """A module whose build_systems lacks 'maven' contributes no profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(tmpdir, {'gradle-mod': (['gradle'], [{'id': 'jacoco', 'canonical': 'coverage'}])})

        result = list_profiles(tmpdir)

        assert result['modules'] == []
        assert result['total_profiles'] == 0


def test_list_profiles_skips_maven_module_with_no_profiles():
    """A Maven module declaring an empty profile list is omitted from the result."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(tmpdir, {'maven-mod': (['maven'], [])})

        result = list_profiles(tmpdir)

        assert result['modules'] == []
        assert result['total_profiles'] == 0


def test_list_profiles_skips_module_whose_derived_data_is_missing():
    """A module in the project index but without a derived.json on disk is
    skipped silently — the project index, not disk presence, is the source of
    truth, and a half-written/pruned entry must not abort the listing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_project(
            tmpdir,
            {
                'ghost': None,  # indexed, but no derived.json written
                'real': (['maven'], [{'id': 'jacoco', 'canonical': 'coverage'}]),
            },
        )

        result = list_profiles(tmpdir)

        assert [m['name'] for m in result['modules']] == ['real']
        assert result['total_profiles'] == 1


# =============================================================================
# Configured skip / mapped profiles (run-configuration.json)
# =============================================================================


def test_get_configured_skip_profiles_empty_when_unset():
    """With no configured skip list, the skip set is empty (never raises)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert get_configured_skip_profiles(tmpdir) == set()


def test_get_configured_skip_profiles_parses_comma_separated_stripping_whitespace():
    """The skip value is a comma-separated list with surrounding whitespace and
    empty entries tolerated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ext_defaults_set('build.maven.profiles.skip', ' apache-release , custom , ', tmpdir)

        assert get_configured_skip_profiles(tmpdir) == {'apache-release', 'custom'}


def test_get_configured_mapped_profiles_empty_when_unset():
    """With no configured canonical map, the mapped set is empty."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert get_configured_mapped_profiles(tmpdir) == set()


def test_get_configured_mapped_profiles_extracts_profile_ids_from_pairs():
    """Each ``profile:canonical`` pair contributes its profile id to the set."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ext_defaults_set('build.maven.profiles.map.canonical', 'p1:e2e, p2:coverage', tmpdir)

        assert get_configured_mapped_profiles(tmpdir) == {'p1', 'p2'}


def test_get_configured_mapped_profiles_ignores_entries_without_a_colon():
    """A malformed entry lacking a colon is not a mapping and is ignored."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ext_defaults_set('build.maven.profiles.map.canonical', 'p1:e2e,noColonHere', tmpdir)

        assert get_configured_mapped_profiles(tmpdir) == {'p1'}


def test_get_unmatched_excludes_profiles_configured_to_skip():
    """A configured skip profile is filtered out of the unmatched list so it is
    never re-prompted for classification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)  # unmatched: apache-release, custom-profile
        ext_defaults_set('build.maven.profiles.skip', 'custom-profile', tmpdir)

        assert get_unmatched_profiles(tmpdir) == ['apache-release']


def test_get_unmatched_excludes_profiles_with_a_configured_canonical_mapping():
    """A profile that already has an explicit canonical mapping is filtered out
    of the unmatched list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)
        ext_defaults_set('build.maven.profiles.map.canonical', 'apache-release:skip', tmpdir)

        assert get_unmatched_profiles(tmpdir) == ['custom-profile']


# =============================================================================
# CLI surface (main dispatch + cmd_* handlers, via real subprocess)
# =============================================================================


def test_cli_classify_reports_classification():
    """``classify --profile-id`` prints the pattern-matched classification.

    ``--project-dir`` is a top-level option and must precede the subcommand.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_script(SCRIPT_PATH, '--project-dir', tmpdir, 'classify', '--profile-id', 'jacoco')

        assert result.success, result.stderr
        assert 'classification: coverage' in result.stdout


def test_cli_list_reports_seeded_profiles():
    """``list`` prints the total/unmatched counts for seeded data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        result = run_script(SCRIPT_PATH, '--project-dir', tmpdir, 'list')

        assert result.success, result.stderr
        assert 'total_profiles: 4' in result.stdout
        assert 'unmatched_count: 2' in result.stdout


def test_cli_unmatched_reports_count_and_profiles():
    """``unmatched`` prints the deduplicated unmatched count."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        result = run_script(SCRIPT_PATH, '--project-dir', tmpdir, 'unmatched')

        assert result.success, result.stderr
        assert 'count: 2' in result.stdout


def test_cli_suggest_reports_count():
    """``suggest`` prints a suggestion count for unmatched profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        result = run_script(SCRIPT_PATH, '--project-dir', tmpdir, 'suggest')

        assert result.success, result.stderr
        assert 'count: 2' in result.stdout


def test_cli_rejects_project_dir_and_plan_id_together():
    """Supplying both --project-dir and --plan-id is a mutually-exclusive
    rejection (exit code 2), never a silent resolution of one over the other."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_script(
            SCRIPT_PATH, '--project-dir', tmpdir, '--plan-id', 'some-plan', 'list'
        )

        assert result.returncode == 2
        assert result.stdout.strip()


# =============================================================================
# CLI handlers in-process (cmd_* bodies — coverage the subprocess run cannot
# reach, since the coverage plugin does not instrument spawned subprocesses)
# =============================================================================


def test_cmd_classify_prints_fields_and_returns_zero(capsys):
    """cmd_classify prints the four classification fields and returns 0."""
    rc = cmd_classify(Namespace(profile_id='jmh', project_dir='.'))

    assert rc == 0
    out = capsys.readouterr().out
    assert 'profile_id: jmh' in out
    assert 'classification: benchmark' in out
    assert 'confidence: high' in out


def test_cmd_list_prints_totals_and_module_table(capsys):
    """cmd_list prints the totals header and a per-module profile table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        rc = cmd_list(Namespace(project_dir=tmpdir, module=None))

        assert rc == 0
        out = capsys.readouterr().out
        assert 'total_profiles: 4' in out
        assert 'unmatched_count: 2' in out
        assert 'module: module-a' in out


def test_cmd_list_on_greenfield_reports_zero_profiles(capsys):
    """cmd_list against a dir with no discoverable modules reports zero totals
    (the empty-crawl branch), not an error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rc = cmd_list(Namespace(project_dir=tmpdir, module=None))

        assert rc == 0
        assert 'total_profiles: 0' in capsys.readouterr().out


def test_cmd_unmatched_prints_count_and_profiles(capsys):
    """cmd_unmatched prints the deduplicated unmatched count and profile list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        rc = cmd_unmatched(Namespace(project_dir=tmpdir))

        assert rc == 0
        assert 'count: 2' in capsys.readouterr().out


def test_cmd_suggest_prints_count_and_suggestion_table(capsys):
    """cmd_suggest prints the suggestion count for unmatched profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_derived_data(tmpdir)

        rc = cmd_suggest(Namespace(project_dir=tmpdir))

        assert rc == 0
        assert 'count: 2' in capsys.readouterr().out
