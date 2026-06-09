#!/usr/bin/env python3
"""Tests for pm-dev-java Extension.classify_paths()."""

import importlib.util
from pathlib import Path

_EXT_PATH = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'pm-dev-java'
    / 'skills'
    / 'plan-marshall-plugin'
    / 'extension.py'
)


def _load_extension():
    spec = importlib.util.spec_from_file_location('pm_dev_java_extension', _EXT_PATH)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.Extension()


_ext = _load_extension()


def test_main_java_is_production():
    result = _ext.classify_paths([
        'src/main/java/com/example/Foo.java',
        'module-a/src/main/java/Bar.java',
    ])
    assert 'src/main/java/com/example/Foo.java' in result['production']
    assert 'module-a/src/main/java/Bar.java' in result['production']


def test_test_java_is_test():
    result = _ext.classify_paths([
        'src/test/java/com/example/FooTest.java',
        'module-a/src/test/java/BarIT.java',
    ])
    assert 'src/test/java/com/example/FooTest.java' in result['test']
    assert 'module-a/src/test/java/BarIT.java' in result['test']


def test_pom_xml_is_config():
    result = _ext.classify_paths(['pom.xml', 'module-a/pom.xml'])
    assert 'pom.xml' in result['config']
    assert 'module-a/pom.xml' in result['config']


def test_gradle_files_are_config():
    result = _ext.classify_paths([
        'build.gradle',
        'build.gradle.kts',
        'settings.gradle',
        'settings.gradle.kts',
    ])
    for path in ('build.gradle', 'build.gradle.kts', 'settings.gradle', 'settings.gradle.kts'):
        assert path in result['config']


def test_java_outside_src_is_unclaimed():
    result = _ext.classify_paths(['random/Foo.java'])
    for role in ('production', 'test', 'documentation', 'config'):
        assert 'random/Foo.java' not in result[role]


def test_specificity_for_main_java_higher_than_zero():
    assert _ext.classify_path_specificity('src/main/java/Foo.java', 'production') > 0


# =============================================================================
# build_class per claimed role
# =============================================================================

_BUILD_CLASSES = frozenset({'compile', 'module-tests', 'docs-validate', 'verify', 'none'})


def test_production_path_build_class_is_compile():
    assert _ext.classify_build_class('src/main/java/Foo.java', 'production') == 'compile'


def test_test_path_build_class_is_module_tests():
    assert _ext.classify_build_class('src/test/java/FooTest.java', 'test') == 'module-tests'


def test_config_path_build_class_is_verify():
    assert _ext.classify_build_class('pom.xml', 'config') == 'verify'
    assert _ext.classify_build_class('build.gradle', 'config') == 'verify'


def test_every_claimed_path_yields_a_build_class_in_the_closed_set():
    """Each path this domain claims resolves to a member of the closed 5-value enum."""
    paths = [
        'src/main/java/com/example/Foo.java',
        'src/test/java/com/example/FooTest.java',
        'pom.xml',
        'build.gradle',
        'settings.gradle.kts',
    ]
    claims = _ext.classify_paths(paths)
    for role, claimed in claims.items():
        for path in claimed:
            assert _ext.classify_build_class(path, role) in _BUILD_CLASSES


# =============================================================================
# classify_globs() vocabulary (build_map seed source)
# =============================================================================
#
# classify_globs() now returns the portable (suffix, role_heuristic) vocabulary
# consumed by the script-shared tree-deriver — NOT literal path-globs. The
# `.java` suffix is declared under both production-by-location and
# test-by-location (the deriver splits them via the src/test convention); the
# Maven/Gradle build descriptors are declared by exact basename under config.

_ROLE_HEURISTICS = frozenset(
    {'production-by-location', 'test-by-location', 'documentation', 'config'}
)


def test_classify_globs_declares_java_under_both_location_heuristics():
    """The .java suffix appears under both production-by-location and test-by-location."""
    vocabulary = _ext.classify_globs()
    assert ('.java', 'production-by-location') in vocabulary
    assert ('.java', 'test-by-location') in vocabulary


def test_classify_globs_declares_build_descriptor_basenames():
    """The Maven/Gradle build descriptors are declared by exact basename under config."""
    vocabulary = _ext.classify_globs()
    for descriptor in (
        'pom.xml',
        'build.gradle',
        'build.gradle.kts',
        'settings.gradle',
        'settings.gradle.kts',
    ):
        assert (descriptor, 'config') in vocabulary


def test_classify_globs_uses_only_role_heuristic_names():
    """Every vocabulary tuple's second element is a role-heuristic name."""
    for _suffix, role_heuristic in _ext.classify_globs():
        assert role_heuristic in _ROLE_HEURISTICS


def test_classify_globs_does_not_return_literal_path_globs():
    """The vocabulary carries bare suffixes/basenames, not the old src/main literal globs."""
    suffixes = {suffix for suffix, _ in _ext.classify_globs()}
    for stale in ('**/src/main/**/*.java', 'src/main/**/*.java', '**/src/test/**/*.java'):
        assert stale not in suffixes


def test_classify_globs_is_nonempty():
    """The java domain owns buildable file types, so the vocabulary is non-empty."""
    assert _ext.classify_globs()
