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
