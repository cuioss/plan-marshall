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

import tempfile
from pathlib import Path

# discover_descriptors lives in script-shared/scripts/extension/, which conftest
# already places on sys.path at import time (it scans immediate scripts/ subdirectories).
from _build_discover import discover_descriptors

from conftest import load_script_module

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


_maven_cmd_discover_mod = load_script_module('plan-marshall', 'build-maven', '_maven_cmd_discover.py', '_maven_cmd_discover')

_build_commands = _maven_cmd_discover_mod._build_commands
discover_maven_modules = _maven_cmd_discover_mod.discover_maven_modules

_classify_profile = _maven_cmd_discover_mod._classify_profile
_parse_coordinates_from_maven_output = _maven_cmd_discover_mod._parse_coordinates_from_maven_output
_parse_dependencies_from_maven_output = _maven_cmd_discover_mod._parse_dependencies_from_maven_output
_parse_profiles_from_maven_output = _maven_cmd_discover_mod._parse_profiles_from_maven_output
_filter_command_line_profiles = _maven_cmd_discover_mod.filter_command_line_profiles
_filter_skip_profiles = _maven_cmd_discover_mod.filter_skip_profiles
_map_canonical_profiles = _maven_cmd_discover_mod.map_canonical_profiles

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


def test_classify_profile_e2e_aliases():
    """Test e2e profile classification via aliases."""
    # These are defined in CANONICAL_COMMANDS["e2e"]["aliases"]
    assert _classify_profile('e2e') == 'e2e'
    assert _classify_profile('acceptance') == 'e2e'
    assert _classify_profile('end-to-end') == 'e2e'


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
# Unit Tests: Quality-Gate Profile Conflict Detection
# =============================================================================


def test_single_quality_gate_profile_no_conflict():
    """Test that a single quality-gate profile produces no conflict."""
    profiles = [{'id': 'pre-commit', 'canonical': 'quality-gate'}]
    commands = _build_commands(
        module_name='my-module', packaging='jar', has_sources=True, has_tests=True, profiles=profiles, relative_path='.'
    )
    assert 'quality-gate' in commands
    assert 'pre-commit' in commands['quality-gate']
    assert 'conflicts' not in commands


def test_two_quality_gate_profiles_first_wins():
    """Test that when two profiles map to quality-gate, the first match wins."""
    profiles = [
        {'id': 'pre-commit', 'canonical': 'quality-gate'},
        {'id': 'sonar', 'canonical': 'quality-gate'},
    ]
    commands = _build_commands(
        module_name='my-module', packaging='jar', has_sources=True, has_tests=True, profiles=profiles, relative_path='.'
    )
    assert 'quality-gate' in commands
    assert 'pre-commit' in commands['quality-gate']
    assert 'sonar' not in commands['quality-gate']


def test_two_quality_gate_profiles_report_conflict():
    """Test that when two profiles map to quality-gate, a conflict is reported."""
    profiles = [
        {'id': 'pre-commit', 'canonical': 'quality-gate'},
        {'id': 'sonar', 'canonical': 'quality-gate'},
    ]
    commands = _build_commands(
        module_name='my-module', packaging='jar', has_sources=True, has_tests=True, profiles=profiles, relative_path='.'
    )
    assert 'conflicts' in commands
    assert 'quality-gate' in commands['conflicts']
    assert commands['conflicts']['quality-gate'] == ['pre-commit', 'sonar']


def test_no_profile_conflict_for_different_canonicals():
    """Test that profiles mapping to different canonicals produce no conflict."""
    profiles = [
        {'id': 'pre-commit', 'canonical': 'quality-gate'},
        {'id': 'integration', 'canonical': 'integration-tests'},
    ]
    commands = _build_commands(
        module_name='my-module', packaging='jar', has_sources=True, has_tests=True, profiles=profiles, relative_path='.'
    )
    assert 'conflicts' not in commands


# =============================================================================
# Unit Tests: Nested Module -pl Argument
# =============================================================================


def test_nested_module_uses_relative_path_for_pl():
    """Test that nested modules use relative_path (not artifact ID) for -pl argument.

    Maven requires -pl to use the directory path relative to reactor root,
    not the artifact ID. For nested modules like benchmarking/benchmark-core,
    the artifact ID (benchmark-core) differs from the relative path.

    The -pl selector must also carry -am (--also-make) so the module's upstream
    reactor dependencies build first on a clean checkout.
    """
    commands = _build_commands(
        module_name='benchmark-core',
        packaging='jar',
        has_sources=True,
        has_tests=True,
        profiles=[],
        relative_path='benchmarking/benchmark-core',
    )
    # The -pl argument must use the relative path, not the artifact ID, and
    # must be followed by -am.
    assert '-pl benchmarking/benchmark-core -am' in commands['compile']
    assert '-pl benchmark-core' not in commands['compile']


def test_nested_module_pl_in_all_commands():
    """Test that non-root module commands use -pl with -am, except clean.

    clean uses -pl WITHOUT -am to avoid wiping upstream reactor target dirs.
    All other commands use -pl -am so upstream deps are built first.
    """
    commands = _build_commands(
        module_name='oauth-sheriff-quarkus',
        packaging='jar',
        has_sources=True,
        has_tests=True,
        profiles=[],
        relative_path='oauth-sheriff-quarkus-parent/oauth-sheriff-quarkus',
    )
    for cmd_name in ['compile', 'verify', 'module-tests', 'quality-gate']:
        assert '-pl oauth-sheriff-quarkus-parent/oauth-sheriff-quarkus -am' in commands[cmd_name], (
            f'{cmd_name} should use relative_path for -pl with -am'
        )
    # clean uses -pl without -am to avoid cleaning upstream reactor dependencies
    assert '-pl oauth-sheriff-quarkus-parent/oauth-sheriff-quarkus' in commands['clean']
    assert '-am' not in commands['clean']


def test_root_module_has_no_pl_arg():
    """Test that root module commands do not include -pl argument."""
    commands = _build_commands(
        module_name='parent-pom', packaging='jar', has_sources=True, has_tests=True, profiles=[], relative_path='.'
    )
    assert '-pl' not in commands['compile']


def test_nested_module_pl_includes_also_make():
    """Test that the test-ladder commands carry -am for a non-root module.

    -am (--also-make) on the test ladder (test-compile, module-tests) is the
    exact fix: without it, a module that depends on a sibling-produced test-jar
    fails at test-compile / test on a clean checkout because the upstream
    reactor module was never built. These rungs are the ones the bug broke.
    """
    commands = _build_commands(
        module_name='oauth-sheriff-quarkus',
        packaging='jar',
        has_sources=True,
        has_tests=True,
        profiles=[],
        relative_path='oauth-sheriff-quarkus-parent/oauth-sheriff-quarkus',
    )
    for cmd_name in ['test-compile', 'module-tests']:
        assert cmd_name in commands, f'{cmd_name} should be present for a non-root module with tests'
        assert '-pl oauth-sheriff-quarkus-parent/oauth-sheriff-quarkus -am' in commands[cmd_name], (
            f'{cmd_name} must emit -am after the -pl selector'
        )


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
# Unit Tests: Subprocess-Free Discovery (POM parse, no Maven binary)
# =============================================================================


def _make_module_tree(parent_dirs: dict[str, str]) -> Path:
    """Create a tmp project tree from {relative_dir: pom_content} and return root.

    A relative_dir of '.' plants the pom at the project root. Each pom is
    written verbatim; ``src/main/java`` is NOT created unless the test seeds it.
    """
    root = Path(tempfile.mkdtemp())
    for rel, content in parent_dirs.items():
        target = root if rel == '.' else root / rel
        target.mkdir(parents=True, exist_ok=True)
        (target / 'pom.xml').write_text(content)
    return root


_JAR_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>leaf-app</artifactId>
  <version>1.0.0</version>
  <packaging>jar</packaging>
</project>
"""

_AGGREGATOR_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>parent-agg</artifactId>
  <version>1.0.0</version>
  <packaging>pom</packaging>
</project>
"""


def test_discover_no_maven_binary_produces_command_map():
    """Discovery against a pom.xml fixture yields a full command map — no Maven.

    The cheap path must produce compile/verify/quality-gate without any
    subprocess; this test runs in an environment with no Maven invocation.
    """
    root = _make_module_tree({'.': _JAR_POM})
    modules = discover_maven_modules(str(root))

    assert len(modules) == 1
    commands = modules[0]['commands']
    for canonical in ('compile', 'verify', 'quality-gate', 'clean', 'package', 'install'):
        assert canonical in commands, f'{canonical} missing from cheap command map'


def test_discover_packaging_and_name_from_xml_parse():
    """Packaging + module name come from the XML parse, not Maven output."""
    root = _make_module_tree({'.': _JAR_POM})
    module = discover_maven_modules(str(root))[0]

    assert module['name'] == 'leaf-app'
    assert module['metadata']['packaging'] == 'jar'
    assert module['metadata']['group_id'] == 'com.example'


def test_discover_pom_aggregator_exposes_compile():
    """A pom aggregator exposes a compile command (reactor passthrough)."""
    root = _make_module_tree({'.': _AGGREGATOR_POM})
    module = discover_maven_modules(str(root))[0]

    assert module['metadata']['packaging'] == 'pom'
    assert 'compile' in module['commands']
    assert 'package' in module['commands']
    # pom aggregators still never expose module-tests (no own tests).
    assert 'module-tests' not in module['commands']


def test_discover_dependencies_empty_on_cheap_path():
    """The cheap crawl leaves dependencies empty (enrich path fills them)."""
    root = _make_module_tree({'.': _JAR_POM})
    module = discover_maven_modules(str(root))[0]
    assert module['dependencies'] == []


def test_discover_does_not_invoke_get_maven_metadata(monkeypatch):
    """The default discovery path never calls _get_maven_metadata / enrich.

    Spy on both the private Maven entry and the public enrich seam and assert a
    full discover run touches neither — the subprocess is enrich-path only.
    """
    metadata_calls = []
    enrich_calls = []

    def _spy_metadata(*args, **kwargs):
        metadata_calls.append(args)
        return None

    def _spy_enrich(*args, **kwargs):
        enrich_calls.append(args)
        return None

    monkeypatch.setattr(_maven_cmd_discover_mod, '_get_maven_metadata', _spy_metadata)
    monkeypatch.setattr(_maven_cmd_discover_mod, 'enrich_maven_module', _spy_enrich)

    root = _make_module_tree({'.': _AGGREGATOR_POM, 'core': _JAR_POM})
    modules = discover_maven_modules(str(root))

    assert len(modules) == 2
    assert metadata_calls == [], 'cheap discovery must not call _get_maven_metadata'
    assert enrich_calls == [], 'cheap discovery must not call enrich_maven_module'


def test_enrich_maven_module_is_the_only_subprocess_seam(monkeypatch):
    """enrich_maven_module is the explicit (and only) subprocess entry.

    It delegates to _get_maven_metadata for ONE module — confirm the call
    reaches the spied private entry exactly once.
    """
    metadata_calls = []

    def _spy_metadata(module_path, project_root):
        metadata_calls.append((module_path, project_root))
        return {'artifact_id': 'x', 'group_id': 'g', 'packaging': 'jar', 'profiles': [], 'dependencies': []}

    monkeypatch.setattr(_maven_cmd_discover_mod, '_get_maven_metadata', _spy_metadata)

    root = _make_module_tree({'.': _JAR_POM})
    result = _maven_cmd_discover_mod.enrich_maven_module(str(root), str(root))

    assert result is not None
    assert len(metadata_calls) == 1


# =============================================================================
# Unit Tests: Discovery Walk Exclusion Invariant (deliverable 3)
# =============================================================================


def test_discovery_never_descends_into_excluded_dirs():
    """The discovery walk must skip target/, node_modules/, and build/.

    Plants decoy pom.xml / package.json descriptors inside excluded build-output
    directories plus one real module under src/, then asserts neither
    discover_descriptors nor discover_maven_modules surfaces the decoys.
    """
    root = Path(tempfile.mkdtemp())

    # Real module at the root with a real src/ tree.
    (root / 'pom.xml').write_text(_JAR_POM)
    src = root / 'src' / 'main' / 'java' / 'com' / 'example'
    src.mkdir(parents=True)
    (src / 'App.java').write_text('package com.example; class App {}')

    # Decoy descriptors inside excluded dirs — must NEVER be discovered.
    for excluded in ('target', 'node_modules', 'build'):
        decoy_dir = root / excluded / 'nested'
        decoy_dir.mkdir(parents=True)
        (decoy_dir / 'pom.xml').write_text(_JAR_POM)
        (decoy_dir / 'package.json').write_text('{"name": "decoy"}')

    # discover_descriptors must only surface the real root pom.
    descriptors = discover_descriptors(str(root), 'pom.xml')
    descriptor_strs = [str(p) for p in descriptors]
    assert len(descriptors) == 1, f'expected only the real pom, got {descriptor_strs}'
    assert not any('target' in s or 'node_modules' in s or 'build' in s for s in descriptor_strs)

    # discover_maven_modules must surface exactly the one real module.
    modules = discover_maven_modules(str(root))
    assert len(modules) == 1
    assert modules[0]['name'] == 'leaf-app'
    module_paths = [m['paths']['module'] for m in modules]
    assert not any('target' in p or 'node_modules' in p or 'build' in p for p in module_paths)


# =============================================================================
# Runner
# =============================================================================
