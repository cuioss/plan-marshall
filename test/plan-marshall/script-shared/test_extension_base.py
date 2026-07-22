#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for extension_base.py module (public API)."""

import importlib.util
import subprocess
import typing
from pathlib import Path

import extension_base
from extension_base import (
    ROLE_CONFIG,
    ROLE_PRODUCTION,
    ROLE_TEST,
    BuildExtensionBase,
    ExtensionBase,
    _pattern_matches_any,
    _tracked_basenames,
    derive_globs_from_tree,
    route_matches,
    should_execute_build,
)

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'script-shared'
    / 'scripts'
    / 'extension'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_extension_constants_mod = _load_module('_extension_constants', '_extension_constants.py')

ALL_CANONICAL_COMMANDS = _extension_constants_mod.ALL_CANONICAL_COMMANDS
APPLICABLE_PROFILES = _extension_constants_mod.APPLICABLE_PROFILES
CANONICAL_COMMANDS = _extension_constants_mod.CANONICAL_COMMANDS
CMD_ARCH_GATE = _extension_constants_mod.CMD_ARCH_GATE
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
    assert CMD_ARCH_GATE == 'arch-gate'
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
        CMD_ARCH_GATE,
        CMD_VERIFY,
        CMD_INSTALL,
        CMD_CLEAN_INSTALL,
        CMD_PACKAGE,
    ]
    assert ALL_CANONICAL_COMMANDS == expected


def test_canonical_commands_only_aliased():
    """CANONICAL_COMMANDS only contains commands with aliases."""
    for cmd_name, meta in CANONICAL_COMMANDS.items():
        assert 'aliases' in meta, f"{cmd_name} missing 'aliases'"
        assert len(meta['aliases']) > 0, f'{cmd_name} has empty aliases'


def test_canonical_commands_expected_keys():
    """CANONICAL_COMMANDS contains the expected command keys."""
    expected = {CMD_INTEGRATION_TESTS, CMD_E2E, CMD_COVERAGE, CMD_BENCHMARK, CMD_QUALITY_GATE}
    assert set(CANONICAL_COMMANDS.keys()) == expected


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
    aliases = ['benchmark', 'performance', 'benchmarks', 'jmh', 'perf', 'load']
    for alias in aliases:
        assert alias in PROFILE_PATTERNS, f"'{alias}' should be in PROFILE_PATTERNS"
        assert PROFILE_PATTERNS[alias] == CMD_BENCHMARK


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


def test_extension_base_default_domain_verb():
    """Default provides_domain_verb returns None — the silent-skip contract."""
    ext = ConcreteExtension()
    assert ext.provides_domain_verb() is None


class DomainVerbExtension(ExtensionBase):
    """Extension declaring a domain-owned executable verb."""

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'test'}, 'profiles': {}}]

    def provides_domain_verb(self) -> dict | None:
        return {'verb': 'marker-detect', 'notation': 'pm-dev-java-cui:search-markers'}


def test_extension_base_domain_verb_descriptor_shape():
    """An overriding extension returns the {'verb', 'notation'} descriptor verbatim."""
    descriptor = DomainVerbExtension().provides_domain_verb()

    assert descriptor == {'verb': 'marker-detect', 'notation': 'pm-dev-java-cui:search-markers'}


def test_extension_base_no_longer_exposes_verify_and_finalize_steps_hooks():
    """The dead provides_verify_steps and provides_finalize_steps hooks are removed from ExtensionBase."""
    ext = ConcreteExtension()
    assert not hasattr(ext, 'provides_verify_steps')
    assert not hasattr(ext, 'provides_finalize_steps')


def test_extension_base_no_longer_exposes_axis_b_methods():
    """ExtensionBase exposes only Axis-A — the four Axis-B build-map methods are gone.

    The file-to-build contract (classify_globs / classify_paths /
    classify_path_specificity / classify_build_class) was relocated onto the
    sibling BuildExtensionBase; ExtensionBase must no longer carry them.
    """
    ext = ConcreteExtension()
    for axis_b in (
        'classify_globs',
        'classify_paths',
        'classify_path_specificity',
        'classify_build_class',
    ):
        assert not hasattr(ext, axis_b), f"ExtensionBase still exposes {axis_b}"
        assert not hasattr(ExtensionBase, axis_b), f"ExtensionBase still declares {axis_b}"


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
    impl = sbp['implementation']
    impl_default_skills = [e['skill'] if isinstance(e, dict) else e for e in impl['defaults']]
    assert 'bundle:core-skill' in impl_default_skills
    assert 'bundle:impl-skill' in impl_default_skills

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


def test_security_profile_in_applicable_profiles():
    """The resolution-only 'security' profile is registered in APPLICABLE_PROFILES."""
    assert 'security' in APPLICABLE_PROFILES


class ExtensionWithSecurityProfile(ExtensionBase):
    """Extension that declares a security profile alongside core/implementation."""

    def get_skill_domains(self) -> list[dict]:
        return [
            {
                'domain': {'key': 'test-security'},
                'profiles': {
                    'core': {
                        'defaults': [{'skill': 'b:core', 'description': 'core'}],
                        'optionals': [],
                    },
                    'implementation': {
                        'defaults': [{'skill': 'b:impl', 'description': 'impl'}],
                        'optionals': [],
                    },
                    'security': {
                        'defaults': [{'skill': 'b:sec', 'description': 'security'}],
                        'optionals': [],
                    },
                },
            }
        ]


def test_security_profile_resolves_when_declared():
    """A domain declaring a security profile resolves its skills under the 'security' key."""
    ext = ExtensionWithSecurityProfile()
    result = ext._build_applicable_result(
        'high',
        ['signal'],
        active_profiles={'security'},
    )

    sbp = result['skills_by_profile']
    assert 'security' in sbp
    sec_default_skills = [e['skill'] if isinstance(e, dict) else e for e in sbp['security']['defaults']]
    assert 'b:sec' in sec_default_skills
    # core is always merged into each resolved profile
    assert 'b:core' in sec_default_skills


def test_security_profile_absent_when_domain_omits_it():
    """A domain that omits the security profile yields no 'security' key."""
    ext = ExtensionWithAllProfiles()
    result = ext._build_applicable_result('high', ['signal'])

    assert 'security' not in result['skills_by_profile']


# derive_globs_from_tree retains a declared route only when at least one
# git-tracked file matches its pattern (fnmatch), pruning dead globs (file types
# absent from the tree) before any consumer sees them. The five scenarios below
# drive the deriver directly against a git-tracked fixture tree. (The broader
# deriver suite — keying, dedup, sort, role filtering — lives in
# test_extension_base_classify_paths.py; this class is the focused
# tree-presence-filter contract for the seed fix.)


class _DeriverRouteExtension(BuildExtensionBase):
    """A build extension declaring one route per resolved role under domain 'minimal'."""

    def get_skill_domains(self) -> list[dict]:
        return [{
            'domain': {'key': 'minimal', 'name': 'Minimal', 'description': 'Test only'},
            'profiles': {},
        }]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [
            ('scripts/*.py', ROLE_PRODUCTION),
            ('test/*.py', ROLE_TEST),
            ('pyproject.toml', ROLE_CONFIG),
        ]


def _git_init_and_track(root, rel_paths: list[str]) -> None:
    """Create + git-add each repo-relative path under ``root`` as a tracked file."""
    subprocess.run(['git', '-C', str(root), 'init', '-q'], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.email', 't@t'], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.name', 'T'], check=True)
    for rel in rel_paths:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('')
    subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)


def test_filter_retains_route_matching_tracked_file(tmp_path):
    """(a) A route whose pattern matches a tracked file is retained."""
    _git_init_and_track(tmp_path, ['scripts/foo.py', 'test/bar.py', 'pyproject.toml'])
    derived = derive_globs_from_tree(str(tmp_path), [_DeriverRouteExtension()])
    assert ('scripts/*.py', 'production') in derived['minimal']


def test_filter_prunes_route_matching_no_tracked_file(tmp_path):
    """(b) A route whose pattern matches NO tracked file is pruned."""
    # Only scripts/ has a matching file — test/ and pyproject.toml routes are dead.
    _git_init_and_track(tmp_path, ['scripts/foo.py'])
    derived = derive_globs_from_tree(str(tmp_path), [_DeriverRouteExtension()])
    assert derived['minimal'] == [('scripts/*.py', 'production')]


def test_filter_omits_domain_when_every_route_is_pruned(tmp_path):
    """(c) A domain whose every route is pruned is omitted from the result."""
    _git_init_and_track(tmp_path, ['README.md'])  # matches none of the routes
    derived = derive_globs_from_tree(str(tmp_path), [_DeriverRouteExtension()])
    assert derived == {}


def test_filter_empty_tracked_set_prunes_all_routes(tmp_path):
    """(d) An empty tracked-file set prunes all routes (returns empty)."""
    _git_init_and_track(tmp_path, [])
    derived = derive_globs_from_tree(str(tmp_path), [_DeriverRouteExtension()])
    assert derived == {}


def test_filter_live_and_dead_route_same_domain_yields_only_live(tmp_path):
    """(e) A live route and a dead route in the same domain yield only the live route."""

    class _MixedExtension(BuildExtensionBase):
        def get_skill_domains(self) -> list[dict]:
            return [{
                'domain': {'key': 'minimal', 'name': 'Minimal', 'description': 'Test only'},
                'profiles': {},
            }]

        def classify_globs(self) -> list[tuple[str, str]]:
            return [
                ('scripts/*.py', ROLE_PRODUCTION),  # live — matches scripts/live.py
                ('vendor/*.py', ROLE_PRODUCTION),  # dead — no vendor/ file tracked
            ]

    _git_init_and_track(tmp_path, ['scripts/live.py'])
    derived = derive_globs_from_tree(str(tmp_path), [_MixedExtension()])
    assert derived['minimal'] == [('scripts/*.py', 'production')]


# =============================================================================
# route_matches() — bare-basename vs path-bearing matching regimes
# =============================================================================
#
# The shared matcher behind the build-map fix. A route pattern with no ``/`` is a
# bare-basename route and matches on the path's BASENAME anywhere in the tree (so
# a config file living only in a subdirectory still matches); a route pattern
# carrying a ``/`` is a path-bearing route and matches against the WHOLE
# repo-relative path. These tests pin both regimes — the unit contract behind the
# bare-basename subdir-matching defect fix.


def test_route_matches_bare_basename_at_repo_root():
    """A bare-basename route matches the file at repo root."""
    assert route_matches('package.json', 'package.json') is True


def test_route_matches_bare_basename_in_subdirectory():
    """A bare-basename route matches the file in a subdirectory (anchored on basename).

    The core defect fix: ``package.json`` (no ``/``) must match
    ``nifi-cuioss-ui/package.json``. The pre-fix full-path fnmatch would have
    returned False and wrongly pruned the subdir-only config route.
    """
    assert route_matches('nifi-cuioss-ui/package.json', 'package.json') is True


def test_route_matches_bare_basename_glob_in_subdirectory():
    """A bare-basename GLOB (e.g. ``*.tsx``) matches by basename anywhere in the tree."""
    assert route_matches('src/components/App.tsx', '*.tsx') is True


def test_route_matches_bare_basename_no_false_positive_on_different_basename():
    """A bare-basename route does NOT match a file whose basename differs.

    Anchoring on the basename keeps the match precise: ``package.json`` must not
    match ``nifi-cuioss-ui/package-lock.json`` (a different basename) even though
    it lives in a subdirectory.
    """
    assert route_matches('nifi-cuioss-ui/package-lock.json', 'package.json') is False


def test_route_matches_path_bearing_matches_full_path():
    """A path-bearing route matches against the whole repo-relative path."""
    assert route_matches('scripts/foo.py', 'scripts/*.py') is True


def test_route_matches_path_bearing_no_false_positive_on_unrelated_dir():
    """A path-bearing route does NOT false-positive on a same-basename file elsewhere.

    The complementary half of the bare-basename fix: a path-bearing glob
    (``scripts/*.py``) stays anchored to its directory, so a file with the same
    basename under an unrelated directory (``vendor/foo.py``) does NOT match.
    """
    assert route_matches('vendor/foo.py', 'scripts/*.py') is False


def test_route_matches_path_bearing_single_star_spans_slash():
    """A single ``*`` in a path-bearing route spans ``/`` (fnmatch semantics)."""
    assert route_matches('marketplace/targets/generate.py', 'marketplace/*.py') is True


def test_derive_globs_retains_bare_basename_subdir_only_config(tmp_path):
    """derive_globs_from_tree retains a bare-basename config route whose file is subdir-only.

    End-to-end regression for the bare-basename subdir-matching defect at the
    deriver: a ``package.json`` config route survives the tree-presence prune even
    though the only tracked ``package.json`` lives in a subdirectory
    (``nifi-cuioss-ui/package.json``), because the deriver matches via
    ``route_matches`` (basename-anchored for bare-basename routes). Before the
    fix the full-path fnmatch pruned it as a dead glob.
    """

    class _SubdirConfigExtension(BuildExtensionBase):
        def get_skill_domains(self) -> list[dict]:
            return [{
                'domain': {'key': 'frontend', 'name': 'Frontend', 'description': 'Test only'},
                'profiles': {},
            }]

        def classify_globs(self) -> list[tuple[str, str]]:
            return [('package.json', ROLE_CONFIG)]

    _git_init_and_track(tmp_path, ['nifi-cuioss-ui/package.json'])
    derived = derive_globs_from_tree(str(tmp_path), [_SubdirConfigExtension()])
    assert derived['frontend'] == [('package.json', 'config')]


# =============================================================================
# _pattern_matches_any() — batch-filter route-presence predicate
# =============================================================================
#
# The batch counterpart to the removed per-element ``any(route_matches(p, pattern)
# for p in tracked)`` truthiness loop. derive_globs_from_tree now prunes routes
# via ``_pattern_matches_any`` (one fnmatch.filter pass) instead of the per-element
# loop. The contract is exact equivalence: for every (pattern, corpus) pair the
# batch helper must return the same boolean the per-element loop produced, under
# BOTH glob regimes (bare-basename and path-bearing). These tests pin that
# equivalence directly so no assertion relies on the removed loop shape while the
# post-fix batch behaviour stays locked.


def _loop_matches_any(pattern: str, tracked: list[str]) -> bool:
    """Reference oracle — the removed per-element loop the batch helper replaced."""
    return any(route_matches(p, pattern) for p in tracked)


def test_pattern_matches_any_bare_basename_at_repo_root():
    """Bare-basename pattern matches a tracked file at repo root."""
    assert _pattern_matches_any('package.json', ['package.json', 'src/app.py']) is True


def test_pattern_matches_any_bare_basename_in_subdirectory():
    """Bare-basename pattern matches a tracked file in a subdirectory (basename-anchored).

    Mirrors the bare-basename regime of the seed-prune fix: ``package.json`` (no
    ``/``) matches ``nifi-cuioss-ui/package.json`` because the helper filters the
    corpus by basename.
    """
    assert _pattern_matches_any('package.json', ['nifi-cuioss-ui/package.json']) is True


def test_pattern_matches_any_bare_basename_glob_in_subdirectory():
    """Bare-basename GLOB matches by basename anywhere in the tree."""
    assert _pattern_matches_any('*.tsx', ['src/components/App.tsx']) is True


def test_pattern_matches_any_bare_basename_no_false_positive():
    """Bare-basename pattern does not match a different basename in a subdirectory."""
    assert _pattern_matches_any('package.json', ['nifi-cuioss-ui/package-lock.json']) is False


def test_pattern_matches_any_path_bearing_matches_full_path():
    """Path-bearing pattern matches against the whole repo-relative path."""
    assert _pattern_matches_any('scripts/*.py', ['scripts/foo.py', 'test/bar.py']) is True


def test_pattern_matches_any_path_bearing_no_false_positive_on_unrelated_dir():
    """Path-bearing pattern stays anchored to its directory (no cross-dir basename match)."""
    assert _pattern_matches_any('scripts/*.py', ['vendor/foo.py']) is False


def test_pattern_matches_any_path_bearing_single_star_spans_slash():
    """A single ``*`` in a path-bearing pattern spans ``/`` (fnmatch semantics)."""
    assert _pattern_matches_any('marketplace/*.py', ['marketplace/targets/generate.py']) is True


def test_pattern_matches_any_empty_corpus_returns_false():
    """An empty tracked corpus never matches — the dead-route prune case."""
    assert _pattern_matches_any('scripts/*.py', []) is False
    assert _pattern_matches_any('package.json', []) is False


def test_pattern_matches_any_equivalent_to_per_element_loop():
    """The batch helper is bit-for-bit equivalent to the removed per-element loop.

    The single load-bearing contract of the refactor: across BOTH regimes, for a
    corpus mixing matching and non-matching paths, ``_pattern_matches_any`` returns
    exactly what ``any(route_matches(p, pattern) for p in tracked)`` produced.
    """
    corpus = [
        'package.json',
        'nifi-cuioss-ui/package.json',
        'nifi-cuioss-ui/package-lock.json',
        'scripts/foo.py',
        'vendor/foo.py',
        'marketplace/targets/generate.py',
        'README.md',
    ]
    patterns = [
        'package.json',            # bare-basename, matches root + subdir
        '*.tsx',                   # bare-basename glob, matches nothing
        'scripts/*.py',            # path-bearing, anchored
        'marketplace/*.py',        # path-bearing, single-star spans /
        'vendor/*.py',             # path-bearing, matches vendor only
        'nonexistent.toml',        # bare-basename, dead route
    ]
    for pattern in patterns:
        assert _pattern_matches_any(pattern, corpus) == _loop_matches_any(pattern, corpus), (
            f'batch/loop mismatch for pattern {pattern!r}'
        )


# =============================================================================
# _tracked_basenames() — lru_cache-backed basename helper
# =============================================================================


def test_tracked_basenames_extracts_basenames():
    """_tracked_basenames returns the basename of each path in the tuple."""
    result = _tracked_basenames(('src/app.py', 'nifi-cuioss-ui/package.json', 'build.py'))
    assert result == ['app.py', 'package.json', 'build.py']


def test_tracked_basenames_empty_tuple():
    """An empty tuple returns an empty list."""
    assert _tracked_basenames(()) == []


def test_tracked_basenames_repo_root_paths():
    """Paths at repo root (no directory separator) return the path itself."""
    result = _tracked_basenames(('README.md', 'pyproject.toml'))
    assert result == ['README.md', 'pyproject.toml']


def test_tracked_basenames_cache_identity():
    """The lru_cache returns the same list object for the same tuple input.

    Calling ``_tracked_basenames`` twice with the same tuple must return the
    identical list object (cache hit) — this confirms the cache is active and
    avoids recomputation on repeated bare-basename pattern evaluation.
    """
    tracked = ('a/b.py', 'c/d.py')
    first = _tracked_basenames(tracked)
    second = _tracked_basenames(tracked)
    assert first is second, 'expected lru_cache hit to return the same object'


# =============================================================================
# should_execute_build() — the sole build/no-build authority
#
# ADR-004 § "Amendment: build-decision is the sole build/no-build authority":
# ``canonical_command`` is an OPTIONAL LABEL on the question, never an input to
# it. The verdict predicate is a pure function of the build_map globs and the
# live footprint, so for a fixed footprint every command — and the command-free
# form — must yield the identical ``decision``/``reason`` pair. The command-free
# form additionally omits the ``canonical_command`` key entirely, which is what
# lets a plan-wide consumer ask "does anything here need a build?" without
# picking an arbitrary representative command (the retired anti-pattern).
# =============================================================================


def _pin_footprint(monkeypatch, globs, footprint):
    """Redirect the two cross-skill readers so the predicate alone is exercised."""
    monkeypatch.setattr(extension_base, '_read_build_map_globs', lambda _root=None: globs)
    monkeypatch.setattr(extension_base, '_resolve_plan_footprint', lambda _plan: footprint)


def test_should_execute_build_accepts_none_command():
    """The signature is widened to ``str | None`` — the command-free form is declared.

    A ``str``-only annotation would make the command-free call a type error even
    though the runtime accepts it, so the annotation is the contract surface a
    consumer reads before passing ``None``.
    """
    hints = typing.get_type_hints(should_execute_build)
    assert hints['canonical_command'] == (str | None)


def test_command_free_build_verdict_omits_canonical_command_key(monkeypatch):
    """A buildable footprint asked command-free returns ``build`` with no label key."""
    # Arrange — footprint touches a registered build glob.
    _pin_footprint(monkeypatch, ['scripts/*.py'], ['scripts/foo.py'])

    # Act
    verdict = should_execute_build(None, 'my-plan')

    # Assert
    assert verdict['decision'] == 'build'
    assert 'canonical_command' not in verdict


def test_command_free_not_necessary_verdict_omits_canonical_command_key(monkeypatch):
    """A non-buildable footprint asked command-free returns ``not_necessary`` with no label key."""
    # Arrange — docs-only footprint intersecting no registered glob.
    _pin_footprint(monkeypatch, ['scripts/*.py'], ['doc/user/configuration.adoc'])

    # Act
    verdict = should_execute_build(None, 'my-plan')

    # Assert
    assert verdict['decision'] == 'not_necessary'
    assert verdict['reason']
    assert 'canonical_command' not in verdict


def test_command_is_a_label_not_an_input_to_the_verdict(monkeypatch):
    """Every command — and no command — yields the identical decision/reason.

    This is the load-bearing property behind the amendment: because the command
    takes no part in the predicate, a consumer that needs a plan-wide answer must
    pass ``None`` rather than nominate a representative command, and a consumer
    that already knows its command gets the same verdict with the label echoed.
    """
    # Arrange — a footprint that resolves not_necessary (so a reason is present
    # to compare, not just the decision).
    _pin_footprint(monkeypatch, ['scripts/*.py'], ['README.md'])

    # Act
    command_free = should_execute_build(None, 'my-plan')
    per_command = {
        cmd: should_execute_build(cmd, 'my-plan')
        for cmd in ('quality-gate', 'verify', 'coverage', 'module-tests')
    }

    # Assert — decision/reason identical everywhere; only the label differs.
    for cmd, verdict in per_command.items():
        assert verdict['decision'] == command_free['decision']
        assert verdict['reason'] == command_free['reason']
        assert verdict['canonical_command'] == cmd
        assert {k: v for k, v in verdict.items() if k != 'canonical_command'} == command_free


def test_command_is_a_label_not_an_input_on_the_build_verdict(monkeypatch):
    """The label-not-input property holds on the ``build`` verdict too."""
    # Arrange — buildable footprint.
    _pin_footprint(monkeypatch, ['scripts/*.py'], ['scripts/foo.py'])

    # Act
    command_free = should_execute_build(None, 'my-plan')
    labelled = should_execute_build('coverage', 'my-plan')

    # Assert
    assert command_free == {'decision': 'build'}
    assert labelled == {'decision': 'build', 'canonical_command': 'coverage'}


def test_command_free_empty_build_map_is_not_necessary(monkeypatch):
    """The no-globs branch is reachable command-free and carries its own reason."""
    # Arrange — project registers no build globs at all.
    _pin_footprint(monkeypatch, [], ['scripts/foo.py'])

    # Act
    verdict = should_execute_build(None, 'my-plan')

    # Assert
    assert verdict['decision'] == 'not_necessary'
    assert 'no globs' in verdict['reason']
    assert 'canonical_command' not in verdict


def test_command_free_empty_footprint_is_not_necessary(monkeypatch):
    """The empty-footprint branch is reachable command-free and carries its own reason.

    This branch is the one that makes a COMPOSE-TIME consultation structurally
    unsafe (the footprint is empty before the worktree materialises), so it must
    stay distinguishable by its reason text rather than collapsing into the
    generic no-match reason.
    """
    # Arrange — globs registered, nothing changed yet.
    _pin_footprint(monkeypatch, ['scripts/*.py'], [])

    # Act
    verdict = should_execute_build(None, 'my-plan')

    # Assert
    assert verdict['decision'] == 'not_necessary'
    assert 'footprint is empty' in verdict['reason']
    assert 'canonical_command' not in verdict
