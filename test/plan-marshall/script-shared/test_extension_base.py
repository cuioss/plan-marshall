#!/usr/bin/env python3
"""Tests for extension_base.py module (public API)."""

# Tier 2 direct imports via importlib for uniform import style
import importlib.util
import sys
from pathlib import Path

from extension_base import ExtensionBase  # type: ignore[import-not-found]

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'script-shared' / 'scripts' / 'extension'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_extension_constants_mod = _load_module('_extension_constants', '_extension_constants.py')

ALL_CANONICAL_COMMANDS = _extension_constants_mod.ALL_CANONICAL_COMMANDS
CANONICAL_COMMANDS = _extension_constants_mod.CANONICAL_COMMANDS
CMD_BENCHMARK = _extension_constants_mod.CMD_BENCHMARK
CMD_CLEAN = _extension_constants_mod.CMD_CLEAN
CMD_CLEAN_INSTALL = _extension_constants_mod.CMD_CLEAN_INSTALL
CMD_COMPILE = _extension_constants_mod.CMD_COMPILE
CMD_COVERAGE = _extension_constants_mod.CMD_COVERAGE
CMD_INSTALL = _extension_constants_mod.CMD_INSTALL
CMD_E2E = _extension_constants_mod.CMD_E2E
CMD_INTEGRATION_TESTS = _extension_constants_mod.CMD_INTEGRATION_TESTS
CMD_MODULE_TESTS = _extension_constants_mod.CMD_MODULE_TESTS
CMD_PACKAGE = _extension_constants_mod.CMD_PACKAGE
CMD_QUALITY_GATE = _extension_constants_mod.CMD_QUALITY_GATE
CMD_TEST_COMPILE = _extension_constants_mod.CMD_TEST_COMPILE
CMD_VERIFY = _extension_constants_mod.CMD_VERIFY
PROFILE_PATTERNS = _extension_constants_mod.PROFILE_PATTERNS

# =============================================================================
# Tests for CMD_* Constants
# =============================================================================


def test_cmd_constants_values():
    """CMD_* constants have expected string values."""
    assert CMD_CLEAN == 'clean'
    assert CMD_COMPILE == 'compile'
    assert CMD_TEST_COMPILE == 'test-compile'
    assert CMD_MODULE_TESTS == 'module-tests'
    assert CMD_INTEGRATION_TESTS == 'integration-tests'
    assert CMD_E2E == 'e2e'
    assert CMD_COVERAGE == 'coverage'
    assert CMD_BENCHMARK == 'benchmark'
    assert CMD_QUALITY_GATE == 'quality-gate'
    assert CMD_VERIFY == 'verify'
    assert CMD_INSTALL == 'install'
    assert CMD_CLEAN_INSTALL == 'clean-install'
    assert CMD_PACKAGE == 'package'


def test_all_canonical_commands_contains_all():
    """ALL_CANONICAL_COMMANDS contains all CMD_* constants."""
    expected = [
        CMD_CLEAN,
        CMD_COMPILE,
        CMD_TEST_COMPILE,
        CMD_MODULE_TESTS,
        CMD_INTEGRATION_TESTS,
        CMD_E2E,
        CMD_COVERAGE,
        CMD_BENCHMARK,
        CMD_QUALITY_GATE,
        CMD_VERIFY,
        CMD_INSTALL,
        CMD_CLEAN_INSTALL,
        CMD_PACKAGE,
    ]
    assert ALL_CANONICAL_COMMANDS == expected


# =============================================================================
# Tests for CANONICAL_COMMANDS Metadata
# =============================================================================


def test_canonical_commands_only_aliased():
    """CANONICAL_COMMANDS only contains commands with aliases."""
    for cmd_name, meta in CANONICAL_COMMANDS.items():
        assert 'aliases' in meta, f"{cmd_name} missing 'aliases'"
        assert len(meta['aliases']) > 0, f'{cmd_name} has empty aliases'


def test_canonical_commands_expected_keys():
    """CANONICAL_COMMANDS contains the expected command keys."""
    expected = {CMD_INTEGRATION_TESTS, CMD_E2E, CMD_COVERAGE, CMD_BENCHMARK, CMD_QUALITY_GATE}
    assert set(CANONICAL_COMMANDS.keys()) == expected


# =============================================================================
# Tests for PROFILE_PATTERNS
# =============================================================================


def test_profile_patterns_integration_tests():
    """Integration test aliases map to CMD_INTEGRATION_TESTS."""
    aliases = ['integration-tests', 'integration-test', 'it']
    for alias in aliases:
        assert alias in PROFILE_PATTERNS, f"'{alias}' should be in PROFILE_PATTERNS"
        assert PROFILE_PATTERNS[alias] == CMD_INTEGRATION_TESTS


def test_profile_patterns_e2e():
    """E2E aliases map to CMD_E2E."""
    aliases = ['e2e', 'e2e-tests', 'acceptance', 'end-to-end']
    for alias in aliases:
        assert alias in PROFILE_PATTERNS, f"'{alias}' should be in PROFILE_PATTERNS"
        assert PROFILE_PATTERNS[alias] == CMD_E2E


def test_profile_patterns_quality_gate():
    """Quality gate aliases map to CMD_QUALITY_GATE."""
    aliases = ['pre-commit', 'precommit', 'sonar', 'lint', 'check', 'quality']
    for alias in aliases:
        assert alias in PROFILE_PATTERNS, f"'{alias}' should be in PROFILE_PATTERNS"
        assert PROFILE_PATTERNS[alias] == CMD_QUALITY_GATE


def test_profile_patterns_coverage():
    """Coverage aliases map to CMD_COVERAGE."""
    aliases = ['coverage', 'jacoco']
    for alias in aliases:
        assert alias in PROFILE_PATTERNS, f"'{alias}' should be in PROFILE_PATTERNS"
        assert PROFILE_PATTERNS[alias] == CMD_COVERAGE


def test_profile_patterns_benchmark():
    """Benchmark aliases map to CMD_BENCHMARK."""
    aliases = ['benchmark', 'performance', 'jmh', 'perf', 'benchmarks', 'load']
    for alias in aliases:
        assert alias in PROFILE_PATTERNS, f"'{alias}' should be in PROFILE_PATTERNS"
        assert PROFILE_PATTERNS[alias] == CMD_BENCHMARK


# =============================================================================
# Tests for ExtensionBase Class
# =============================================================================


class ConcreteExtension(ExtensionBase):
    """Concrete implementation for testing."""

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'test'}, 'profiles': {}}]


def test_extension_base_abstract_methods():
    """ExtensionBase requires get_skill_domains."""
    ext = ConcreteExtension()
    assert ext.get_skill_domains()[0]['domain']['key'] == 'test'


def test_extension_base_default_discover_modules():
    """Default discover_modules returns empty list."""
    ext = ConcreteExtension()
    assert ext.discover_modules('/some/path') == []


def test_extension_base_default_triage():
    """Default provides_triage returns None."""
    ext = ConcreteExtension()
    assert ext.provides_triage() is None


def test_extension_base_default_outline_skill():
    """Default provides_outline_skill returns None."""
    ext = ConcreteExtension()
    assert ext.provides_outline_skill() is None


def test_extension_base_default_verify_steps():
    """Default provides_verify_steps returns empty list."""
    ext = ConcreteExtension()
    assert ext.provides_verify_steps() == []


# =============================================================================
# Tests for applies_to_module() and _build_applicable_result()
# =============================================================================


def test_extension_base_default_applies_to_module():
    """Default applies_to_module returns not applicable."""
    ext = ConcreteExtension()
    result = ext.applies_to_module({'build_systems': ['maven']})
    assert result['applicable'] is False
    assert result['confidence'] == 'none'
    assert result['signals'] == []
    assert result['additive_to'] is None
    assert result['skills_by_profile'] == {}


class ExtensionWithProfiles(ExtensionBase):
    """Extension with profiles for testing _build_applicable_result."""

    def get_skill_domains(self) -> list[dict]:
        return [
            {
                'domain': {'key': 'test-profiles'},
                'profiles': {
                    'core': {
                        'defaults': [{'skill': 'bundle:core-skill', 'description': 'core'}],
                        'optionals': [{'skill': 'bundle:core-opt', 'description': 'core optional'}],
                    },
                    'implementation': {
                        'defaults': [{'skill': 'bundle:impl-skill', 'description': 'impl'}],
                        'optionals': [],
                    },
                    'module_testing': {
                        'defaults': [{'skill': 'bundle:test-skill', 'description': 'test'}],
                        'optionals': [],
                    },
                },
            }
        ]


def test_build_applicable_result_merges_core():
    """_build_applicable_result merges core into each profile."""
    ext = ExtensionWithProfiles()
    result = ext._build_applicable_result('high', ['test signal'])

    assert result['applicable'] is True
    assert result['confidence'] == 'high'
    assert result['signals'] == ['test signal']
    assert result['additive_to'] is None

    sbp = result['skills_by_profile']
    # implementation should have core defaults + impl defaults
    impl = sbp['implementation']
    impl_default_skills = [e['skill'] if isinstance(e, dict) else e for e in impl['defaults']]
    assert 'bundle:core-skill' in impl_default_skills
    assert 'bundle:impl-skill' in impl_default_skills

    # implementation optionals should include core optionals
    impl_opt_skills = [e['skill'] if isinstance(e, dict) else e for e in impl['optionals']]
    assert 'bundle:core-opt' in impl_opt_skills


def test_build_applicable_result_with_additive_to():
    """_build_applicable_result with additive_to parameter."""
    ext = ExtensionWithProfiles()
    result = ext._build_applicable_result('high', ['signal'], additive_to='parent')

    assert result['additive_to'] == 'parent'


class ExtensionEmptyProfiles(ExtensionBase):
    """Extension with empty profiles."""

    def get_skill_domains(self) -> list[dict]:
        return [
            {
                'domain': {'key': 'empty'},
                'profiles': {},
            }
        ]


def test_build_applicable_result_empty_profiles():
    """_build_applicable_result with empty profiles returns empty skills_by_profile."""
    ext = ExtensionEmptyProfiles()
    result = ext._build_applicable_result('low', ['minimal'])

    assert result['applicable'] is True
    assert result['skills_by_profile'] == {}


# =============================================================================
# Tests for active_profiles filtering (three-layer resolution)
# =============================================================================


class ExtensionWithAllProfiles(ExtensionBase):
    """Extension with all profile types for filtering tests."""

    def get_skill_domains(self) -> list[dict]:
        return [
            {
                'domain': {'key': 'test-all'},
                'profiles': {
                    'core': {
                        'defaults': [{'skill': 'b:core', 'description': 'core'}],
                        'optionals': [],
                    },
                    'implementation': {
                        'defaults': [{'skill': 'b:impl', 'description': 'impl'}],
                        'optionals': [],
                    },
                    'module_testing': {
                        'defaults': [{'skill': 'b:mtest', 'description': 'mtest'}],
                        'optionals': [],
                    },
                    'integration_testing': {
                        'defaults': [{'skill': 'b:itest', 'description': 'itest'}],
                        'optionals': [],
                    },
                    'quality': {
                        'defaults': [{'skill': 'b:quality', 'description': 'quality'}],
                        'optionals': [],
                    },
                    'documentation': {
                        'defaults': [{'skill': 'b:doc', 'description': 'doc'}],
                        'optionals': [],
                    },
                },
            }
        ]


def test_build_applicable_result_active_profiles_filters():
    """active_profiles positive list filters to only specified profiles."""
    ext = ExtensionWithAllProfiles()
    result = ext._build_applicable_result(
        'high',
        ['signal'],
        active_profiles={'implementation', 'module_testing', 'quality'},
    )

    sbp = result['skills_by_profile']
    assert 'implementation' in sbp
    assert 'module_testing' in sbp
    assert 'quality' in sbp
    assert 'integration_testing' not in sbp
    assert 'documentation' not in sbp


def test_build_applicable_result_no_filter_includes_all():
    """Without active_profiles, all defined profiles are included."""
    ext = ExtensionWithAllProfiles()
    result = ext._build_applicable_result('high', ['signal'])

    sbp = result['skills_by_profile']
    assert 'implementation' in sbp
    assert 'module_testing' in sbp
    assert 'integration_testing' in sbp
    assert 'quality' in sbp
    assert 'documentation' in sbp


def test_detect_applicable_profiles_default_returns_none():
    """Default _detect_applicable_profiles returns None (no filtering)."""
    ext = ExtensionWithAllProfiles()
    result = ext._detect_applicable_profiles({}, {})
    assert result is None


class ExtensionWithSignalDetection(ExtensionBase):
    """Extension that overrides _detect_applicable_profiles."""

    def get_skill_domains(self) -> list[dict]:
        return [
            {
                'domain': {'key': 'test-signals'},
                'profiles': {
                    'core': {'defaults': [{'skill': 'b:core', 'description': 'core'}], 'optionals': []},
                    'implementation': {'defaults': [{'skill': 'b:impl', 'description': 'impl'}], 'optionals': []},
                    'integration_testing': {'defaults': [{'skill': 'b:it', 'description': 'it'}], 'optionals': []},
                },
            }
        ]

    def _detect_applicable_profiles(self, profiles, module_data):
        if module_data and 'integration' in module_data.get('name', ''):
            return {'implementation', 'integration_testing'}
        return {'implementation'}


def test_signal_detection_with_it_module():
    """Signal detection includes integration_testing for IT module."""
    ext = ExtensionWithSignalDetection()
    result = ext._build_applicable_result(
        'high',
        ['signal'],
        module_data={'name': 'integration-tests'},
    )
    assert 'integration_testing' in result['skills_by_profile']
    assert 'implementation' in result['skills_by_profile']


def test_signal_detection_without_it_module():
    """Signal detection excludes integration_testing for non-IT module."""
    ext = ExtensionWithSignalDetection()
    result = ext._build_applicable_result(
        'high',
        ['signal'],
        module_data={'name': 'core-lib'},
    )
    assert 'integration_testing' not in result['skills_by_profile']
    assert 'implementation' in result['skills_by_profile']


def test_active_profiles_overrides_signal_detection():
    """active_profiles takes precedence over signal detection."""
    ext = ExtensionWithSignalDetection()
    # Module has IT signals, but active_profiles only allows implementation
    result = ext._build_applicable_result(
        'high',
        ['signal'],
        module_data={'name': 'integration-tests'},
        active_profiles={'implementation'},
    )
    assert 'integration_testing' not in result['skills_by_profile']
    assert 'implementation' in result['skills_by_profile']


def test_applies_to_module_accepts_active_profiles():
    """Base applies_to_module accepts active_profiles parameter."""
    ext = ConcreteExtension()
    result = ext.applies_to_module({'build_systems': []}, active_profiles={'implementation'})
    assert result['applicable'] is False  # ConcreteExtension always returns not applicable


if __name__ == '__main__':
    import traceback

    tests = [
        test_cmd_constants_values,
        test_all_canonical_commands_contains_all,
        test_canonical_commands_only_aliased,
        test_canonical_commands_expected_keys,
        test_profile_patterns_integration_tests,
        test_profile_patterns_quality_gate,
        test_profile_patterns_coverage,
        test_profile_patterns_benchmark,
        test_extension_base_abstract_methods,
        test_extension_base_default_discover_modules,
        test_extension_base_default_triage,
        test_extension_base_default_outline_skill,
        test_extension_base_default_verify_steps,
        test_extension_base_default_applies_to_module,
        test_build_applicable_result_merges_core,
        test_build_applicable_result_with_additive_to,
        test_build_applicable_result_empty_profiles,
        test_build_applicable_result_active_profiles_filters,
        test_build_applicable_result_no_filter_includes_all,
        test_detect_applicable_profiles_default_returns_none,
        test_signal_detection_with_it_module,
        test_signal_detection_without_it_module,
        test_active_profiles_overrides_signal_detection,
        test_applies_to_module_accepts_active_profiles,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception:
            failed += 1
            print(f'FAILED: {test.__name__}')
            traceback.print_exc()
            print()

    print(f'\nResults: {passed} passed, {failed} failed')
    sys.exit(0 if failed == 0 else 1)
