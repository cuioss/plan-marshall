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

_BUILD_CLASSES = frozenset({'prod-compile', 'test-run', 'docs-validate', 'build-config-full', 'none'})


def test_production_path_build_class_is_prod_compile():
    assert _ext.classify_build_class('src/main/java/Foo.java', 'production') == 'prod-compile'


def test_test_path_build_class_is_test_run():
    assert _ext.classify_build_class('src/test/java/FooTest.java', 'test') == 'test-run'


def test_config_path_build_class_is_build_config_full():
    assert _ext.classify_build_class('pom.xml', 'config') == 'build-config-full'
    assert _ext.classify_build_class('build.gradle', 'config') == 'build-config-full'


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
# classify_globs() inventory (build_map seed source)
# =============================================================================


def test_classify_globs_derives_glob_role_pairs_from_patterns():
    """Tuple-shape extension: classify_globs derives (glob, role) from _CLASSIFY_PATTERNS."""
    expected = [(glob, role) for glob, role, _ in _ext._CLASSIFY_PATTERNS]
    assert _ext.classify_globs() == expected


def test_classify_globs_roles_resolve_to_build_classes():
    """Every (glob, role) in the inventory derives a build_class in the closed set."""
    inventory = _ext.classify_globs()
    assert inventory  # the java domain claims file types
    for glob, role in inventory:
        assert _ext.classify_build_class(glob, role) in _BUILD_CLASSES


def test_classify_globs_covers_production_test_config_roles():
    """The java glob inventory claims production, test, and config roles."""
    roles = {role for _, role in _ext.classify_globs()}
    assert roles == {'production', 'test', 'config'}
