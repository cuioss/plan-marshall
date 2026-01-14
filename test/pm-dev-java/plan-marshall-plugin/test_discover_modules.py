#!/usr/bin/env python3
"""Unit tests for Maven module discovery parsing functions (internal module testing).

Tests the parsing functions with fixture data. These tests do NOT require Maven.

Note: These tests import internal modules directly for detailed testing.
Public API tests should use extension.py discover_modules() method instead.

For integration tests that test full discover_modules flow against real Maven
projects, see test_discover_modules_integration.py.

Contract requirements tested:
- Only command-line activated profiles are included (Active: false)
- Profiles have id and canonical fields only (no activation field)
- Skip list filters out specified profiles
- Explicit mapping takes precedence over alias matching
- Alias matching uses CANONICAL_COMMANDS from extension_base.py
- dependencies: string format "groupId:artifactId:scope" (not objects)
- coordinates: parsed from dependency:tree header
"""

import sys
from pathlib import Path

# Import shared infrastructure (sets up PYTHONPATH for cross-skill imports)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

FIXTURES_DIR = Path(__file__).parent / 'fixtures'

# Direct imports - conftest sets up PYTHONPATH
from _maven_cmd_discover import (  # noqa: E402
    _build_commands,
    _classify_profile,
    _filter_command_line_profiles,
    _filter_skip_profiles,
    _map_canonical_profiles,
    _parse_coordinates_from_maven_output,
    _parse_dependencies_from_maven_output,
    _parse_profiles_from_maven_output,
)

# =============================================================================
# Fixtures
# =============================================================================


def load_fixture(name: str) -> str:
    """Load fixture file content."""
    fixture_path = FIXTURES_DIR / name
    return fixture_path.read_text()


SAMPLE_LOG = None  # Lazy loaded


def get_sample_log() -> str:
    """Get sample Maven discovery log (lazy loaded)."""
    global SAMPLE_LOG
    if SAMPLE_LOG is None:
        SAMPLE_LOG = load_fixture('sample-maven-discovery.log')
    return SAMPLE_LOG


# =============================================================================
# Unit Tests: Coordinate Parsing
# =============================================================================


def test_parse_coordinates_extracts_group_id():
    """Test that group_id is extracted from dependency:tree header."""
    log = get_sample_log()
    coords = _parse_coordinates_from_maven_output(log)

    assert coords.get('group_id') == 'com.example'


def test_parse_coordinates_extracts_artifact_id():
    """Test that artifact_id is extracted from dependency:tree header."""
    log = get_sample_log()
    coords = _parse_coordinates_from_maven_output(log)

    assert coords.get('artifact_id') == 'my-app'


def test_parse_coordinates_extracts_packaging():
    """Test that packaging is extracted from dependency:tree header."""
    log = get_sample_log()
    coords = _parse_coordinates_from_maven_output(log)

    assert coords.get('packaging') == 'jar'


def test_parse_coordinates_ignores_dependency_lines():
    """Test that dependency lines (with +- prefix) are not parsed as coordinates."""
    log = """[INFO] com.example:parent:pom:1.0.0
[INFO] +- com.example:child:jar:1.0.0:compile
"""
    coords = _parse_coordinates_from_maven_output(log)

    # Should get parent coords, not child
    assert coords.get('artifact_id') == 'parent'
    assert coords.get('packaging') == 'pom'


def test_parse_coordinates_handles_empty_log():
    """Test graceful handling of empty log."""
    coords = _parse_coordinates_from_maven_output('')
    assert coords == {}


# =============================================================================
# Unit Tests: Raw Profile Parsing
# =============================================================================


def test_parse_profiles_extracts_all_raw_profiles():
    """Test that all profiles are extracted from help:all-profiles output."""
    log = get_sample_log()
    profiles = _parse_profiles_from_maven_output(log)

    profile_ids = [p['id'] for p in profiles]
    # Should include ALL profiles, even default-activated ones
    assert 'pre-commit' in profile_ids
    assert 'coverage' in profile_ids
    assert 'integration-tests' in profile_ids
    assert 'jdk17' in profile_ids  # default-activated
    assert 'release' in profile_ids
    assert 'native' in profile_ids
    assert len(profiles) == 6


def test_parse_profiles_includes_activation_status():
    """Test that raw profiles include is_active status."""
    log = get_sample_log()
    profiles = _parse_profiles_from_maven_output(log)

    by_id = {p['id']: p for p in profiles}

    # Command-line activated (Active: false)
    assert by_id['pre-commit']['is_active'] is False
    assert by_id['coverage']['is_active'] is False
    # Default activated (Active: true)
    assert by_id['jdk17']['is_active'] is True


# =============================================================================
# Unit Tests: Command-Line Activation Filter
# =============================================================================


def test_filter_command_line_excludes_default_activated():
    """Test that profiles with Active: true are filtered out."""
    raw_profiles = [
        {'id': 'pre-commit', 'is_active': False},
        {'id': 'jdk17', 'is_active': True},  # Should be excluded
        {'id': 'coverage', 'is_active': False},
    ]

    filtered = _filter_command_line_profiles(raw_profiles)

    profile_ids = [p['id'] for p in filtered]
    assert 'pre-commit' in profile_ids
    assert 'coverage' in profile_ids
    assert 'jdk17' not in profile_ids  # Excluded
    assert len(filtered) == 2


def test_filter_command_line_removes_is_active_field():
    """Test that is_active field is removed after filtering."""
    raw_profiles = [
        {'id': 'pre-commit', 'is_active': False},
    ]

    filtered = _filter_command_line_profiles(raw_profiles)

    assert 'is_active' not in filtered[0]


# =============================================================================
# Unit Tests: Skip List Filtering
# =============================================================================


def test_filter_skip_removes_listed_profiles():
    """Test that profiles in skip list are removed."""
    profiles = [
        {'id': 'pre-commit'},
        {'id': 'release'},
        {'id': 'coverage'},
        {'id': 'native'},
    ]
    skip_list = ['release', 'native']

    filtered = _filter_skip_profiles(profiles, skip_list)

    profile_ids = [p['id'] for p in filtered]
    assert 'pre-commit' in profile_ids
    assert 'coverage' in profile_ids
    assert 'release' not in profile_ids
    assert 'native' not in profile_ids
    assert len(filtered) == 2


def test_filter_skip_handles_empty_skip_list():
    """Test that empty skip list keeps all profiles."""
    profiles = [
        {'id': 'pre-commit'},
        {'id': 'release'},
    ]

    filtered = _filter_skip_profiles(profiles, [])

    assert len(filtered) == 2


def test_filter_skip_handles_none_skip_list():
    """Test that None skip list keeps all profiles."""
    profiles = [
        {'id': 'pre-commit'},
        {'id': 'release'},
    ]

    filtered = _filter_skip_profiles(profiles, None)

    assert len(filtered) == 2


def test_filter_skip_trims_whitespace():
    """Test that skip list entries are trimmed."""
    profiles = [
        {'id': 'release'},
        {'id': 'native'},
    ]
    skip_list = [' release ', 'native']

    filtered = _filter_skip_profiles(profiles, skip_list)

    assert len(filtered) == 0


# =============================================================================
# Unit Tests: Canonical Mapping
# =============================================================================


def test_map_canonical_uses_explicit_mapping_first():
    """Test that explicit mapping takes precedence over aliases."""
    profiles = [
        {'id': 'pre-commit'},
        {'id': 'javadoc'},  # Not in CANONICAL_COMMANDS aliases
    ]
    explicit_mapping = {
        'pre-commit': 'quality-gate',
        'javadoc': 'javadoc',  # CUI-specific, not in aliases
    }

    mapped = _map_canonical_profiles(profiles, explicit_mapping)

    by_id = {p['id']: p for p in mapped}
    assert by_id['pre-commit']['canonical'] == 'quality-gate'
    assert by_id['javadoc']['canonical'] == 'javadoc'


def test_map_canonical_falls_back_to_aliases():
    """Test that alias matching is used when no explicit mapping."""
    profiles = [
        {'id': 'coverage'},  # matches alias
        {'id': 'integration-tests'},  # matches alias
    ]

    mapped = _map_canonical_profiles(profiles, {})

    by_id = {p['id']: p for p in mapped}
    assert by_id['coverage']['canonical'] == 'coverage'
    assert by_id['integration-tests']['canonical'] == 'integration-tests'


def test_map_canonical_sets_no_match_for_unknown():
    """Test that unknown profiles get canonical='NO-MATCH-FOUND'."""
    profiles = [
        {'id': 'custom-profile'},
        {'id': 'release'},
    ]

    mapped = _map_canonical_profiles(profiles, {})

    by_id = {p['id']: p for p in mapped}
    assert by_id['custom-profile']['canonical'] == 'NO-MATCH-FOUND'
    assert by_id['release']['canonical'] == 'NO-MATCH-FOUND'


def test_map_canonical_handles_empty_mapping():
    """Test that None mapping uses only aliases."""
    profiles = [
        {'id': 'pre-commit'},
    ]

    mapped = _map_canonical_profiles(profiles, None)

    assert mapped[0]['canonical'] == 'quality-gate'


# =============================================================================
# Unit Tests: Profile Classification (Alias Matching)
# =============================================================================


def test_classify_profile_quality_gate_aliases():
    """Test quality-gate profile classification via aliases."""
    # These are defined in CANONICAL_COMMANDS["quality-gate"]["aliases"]
    assert _classify_profile('pre-commit') == 'quality-gate'
    assert _classify_profile('precommit') == 'quality-gate'
    assert _classify_profile('sonar') == 'quality-gate'
    assert _classify_profile('lint') == 'quality-gate'
    assert _classify_profile('quality') == 'quality-gate'


def test_classify_profile_coverage_aliases():
    """Test coverage profile classification via aliases."""
    # These are defined in CANONICAL_COMMANDS["coverage"]["aliases"]
    assert _classify_profile('coverage') == 'coverage'
    assert _classify_profile('jacoco') == 'coverage'


def test_classify_profile_integration_tests_aliases():
    """Test integration-tests profile classification via aliases."""
    # These are defined in CANONICAL_COMMANDS["integration-tests"]["aliases"]
    assert _classify_profile('integration-tests') == 'integration-tests'
    assert _classify_profile('integration-test') == 'integration-tests'
    assert _classify_profile('it') == 'integration-tests'
    assert _classify_profile('e2e') == 'integration-tests'


def test_classify_profile_benchmark_aliases():
    """Test benchmark profile classification via aliases."""
    # These are defined in CANONICAL_COMMANDS["benchmark"]["aliases"]
    assert _classify_profile('performance') == 'benchmark'
    assert _classify_profile('jmh') == 'benchmark'
    assert _classify_profile('perf') == 'benchmark'


def test_classify_profile_unknown():
    """Test that unknown profiles return NO-MATCH-FOUND."""
    assert _classify_profile('custom-profile') == 'NO-MATCH-FOUND'
    assert _classify_profile('release') == 'NO-MATCH-FOUND'
    assert _classify_profile('native') == 'NO-MATCH-FOUND'
    assert _classify_profile('javadoc') == 'NO-MATCH-FOUND'  # Not in aliases


def test_classify_profile_no_substring_matching():
    """Test that partial/substring matching does NOT work.

    Only exact alias matches should work, not substring contains.
    """
    # "quality-check" should NOT match "quality" substring
    assert _classify_profile('quality-check') == 'NO-MATCH-FOUND'
    # "jacoco-report" should NOT match "jacoco" substring
    assert _classify_profile('jacoco-report') == 'NO-MATCH-FOUND'
    # "it-tests" should NOT match "it" substring
    assert _classify_profile('it-tests') == 'NO-MATCH-FOUND'


# =============================================================================
# Unit Tests: Dependency Parsing
# =============================================================================


def test_parse_dependencies_extracts_direct_deps():
    """Test that direct dependencies are extracted."""
    log = get_sample_log()
    deps = _parse_dependencies_from_maven_output(log)

    assert len(deps) == 3


def test_parse_dependencies_format():
    """Contract: dependencies must be strings in format 'groupId:artifactId:scope'."""
    log = get_sample_log()
    deps = _parse_dependencies_from_maven_output(log)

    for dep in deps:
        assert isinstance(dep, str), f'dependency must be string, got {type(dep)}'
        parts = dep.split(':')
        assert len(parts) == 3, f"dependency must be 'groupId:artifactId:scope', got '{dep}'"


def test_parse_dependencies_correct_scopes():
    """Test that dependency scopes are correctly extracted."""
    log = get_sample_log()
    deps = _parse_dependencies_from_maven_output(log)

    assert 'org.junit.jupiter:junit-jupiter:test' in deps
    assert 'com.google.guava:guava:compile' in deps
    assert 'org.projectlombok:lombok:provided' in deps


def test_parse_dependencies_ignores_transitive():
    """Test that transitive dependencies (with |) are ignored."""
    log = """[INFO] com.example:my-app:jar:1.0.0
[INFO] +- com.example:direct:jar:1.0.0:compile
[INFO] |  \\- com.example:transitive:jar:1.0.0:compile
"""
    deps = _parse_dependencies_from_maven_output(log)

    assert len(deps) == 1
    assert 'com.example:direct:compile' in deps


# =============================================================================
# Unit Tests: Pom Aggregator Commands
# =============================================================================


def test_pom_aggregator_gets_clean_command():
    """Test that pom aggregators get the clean command."""
    commands = _build_commands(
        module_name='parent-pom', packaging='pom', has_sources=False, has_tests=False, profiles=[], relative_path='.'
    )
    assert 'clean' in commands


def test_pom_aggregator_gets_quality_gate_command():
    """Test that pom aggregators get quality-gate command for aggregate analysis."""
    commands = _build_commands(
        module_name='parent-pom', packaging='pom', has_sources=False, has_tests=False, profiles=[], relative_path='.'
    )
    assert 'quality-gate' in commands


def test_pom_aggregator_gets_verify_command():
    """Test that pom aggregators DO get verify command (needed for reactor builds)."""
    commands = _build_commands(
        module_name='parent-pom', packaging='pom', has_sources=False, has_tests=False, profiles=[], relative_path='.'
    )
    assert 'verify' in commands


def test_pom_aggregator_does_not_get_module_tests():
    """Test that pom aggregators do NOT get module-tests command."""
    commands = _build_commands(
        module_name='parent-pom', packaging='pom', has_sources=False, has_tests=False, profiles=[], relative_path='.'
    )
    assert 'module-tests' not in commands


# =============================================================================
# Integration Tests: Full Pipeline
# =============================================================================


def test_full_profile_pipeline():
    """Test the complete profile extraction -> filter -> skip -> map pipeline."""
    log = get_sample_log()

    # 1. Parse raw profiles
    raw_profiles = _parse_profiles_from_maven_output(log)
    assert len(raw_profiles) == 6

    # 2. Filter to command-line only
    cmd_line = _filter_command_line_profiles(raw_profiles)
    profile_ids = [p['id'] for p in cmd_line]
    assert 'jdk17' not in profile_ids  # default-activated excluded
    assert len(cmd_line) == 5

    # 3. Apply skip list
    skip_list = ['release', 'native']
    filtered = _filter_skip_profiles(cmd_line, skip_list)
    assert len(filtered) == 3

    # 4. Map to canonical
    mapping = {'pre-commit': 'quality-gate'}
    mapped = _map_canonical_profiles(filtered, mapping)

    by_id = {p['id']: p for p in mapped}
    assert by_id['pre-commit']['canonical'] == 'quality-gate'
    assert by_id['coverage']['canonical'] == 'coverage'
    assert by_id['integration-tests']['canonical'] == 'integration-tests'

    # 5. Verify no activation field
    for profile in mapped:
        assert 'activation' not in profile
        assert 'is_active' not in profile


# =============================================================================
# Runner
# =============================================================================
