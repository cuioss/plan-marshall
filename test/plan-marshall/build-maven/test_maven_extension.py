#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for plan-marshall build-maven BuildExtension (the Maven file-to-build map).

Covers the build-system-owned ``BuildExtension(BuildExtensionBase)`` that ships
in ``build-maven/scripts/extension.py``. This extension owns Axis-B of the
extension contract for the Maven build system: the explicit ``(pattern, role)``
``classify_globs()`` build_map routes plus the ``classify_paths()`` /
``classify_path_specificity()`` lookups the manage-execution-manifest aggregator
and the build_map seed consume.

Central to this deliverable is the resource / shell-script claim contract: the
Maven-standard resource trees classify by LOCATION rather than by extension
(``src/main/resources`` → production, ``src/test/resources`` → test), and shell
scripts are claimed by bare basename (``*.sh`` → config). Because the resource
rows outrank the ``*.sh`` row, a script INSIDE a resource tree keeps that tree's
role — only a script outside every claimed tree falls through to config.

The four build skills (build-pyproject, build-maven, build-gradle, build-npm)
each ship a ``BuildExtension`` subclass; each ``extension.py`` lives under the
respective skill's ``scripts/`` directory and shares the module basename
``extension``, so the class is loaded via ``importlib.util.spec_from_file_location``
against the explicit file path to avoid the cross-skill module-name collision.

The base-class default contract, the aggregator's longest-glob-wins overlap
resolution, and the route deriver / completeness validator are covered separately
in test/plan-marshall/script-shared/test_extension_base_classify_paths.py — this
module covers only the concrete Maven BuildExtension's claims.
"""

import importlib.util
from pathlib import Path

# extension_base is importable: conftest._setup_marketplace_pythonpath() adds
# script-shared/scripts/extension/ to sys.path.
from extension_base import (
    BUILD_MAP_ROLES,
    BuildExtensionBase,
)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
EXTENSION_FILE = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'build-maven'
    / 'scripts'
    / 'extension.py'
)


def _load_maven_build_extension():
    """Load the build-maven BuildExtension class by explicit file path.

    Every build skill ships an ``extension.py`` sharing the module basename
    ``extension``; loading via ``spec_from_file_location`` against the explicit
    path avoids the cross-skill ``import extension`` collision.
    """
    spec = importlib.util.spec_from_file_location(
        'maven_build_extension', EXTENSION_FILE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_EXTENSION_MODULE = _load_maven_build_extension()
BuildExtension = _EXTENSION_MODULE.BuildExtension


def test_build_extension_subclasses_build_extension_base():
    """The Maven BuildExtension is a BuildExtensionBase (Axis-B), not ExtensionBase."""
    assert issubclass(BuildExtension, BuildExtensionBase)


def test_build_extension_is_instantiable():
    """The Maven BuildExtension instantiates with no required arguments."""
    ext = BuildExtension()
    assert isinstance(ext, BuildExtensionBase)


# --- Resource trees: claimed by location, in bare and nested layouts ---------


def test_classify_paths_claims_bare_main_resources_as_production():
    """A resource under the repo-root src/main/resources tree is production."""
    ext = BuildExtension()
    result = ext.classify_paths(['src/main/resources/application.properties'])
    assert result['production'] == ['src/main/resources/application.properties']


def test_classify_paths_claims_nested_main_resources_as_production():
    """A resource under a nested module's src/main/resources tree is production."""
    ext = BuildExtension()
    result = ext.classify_paths(['module-a/src/main/resources/application.properties'])
    assert result['production'] == ['module-a/src/main/resources/application.properties']


def test_classify_paths_claims_bare_test_resources_as_test():
    """A resource under the repo-root src/test/resources tree is test."""
    ext = BuildExtension()
    result = ext.classify_paths(['src/test/resources/fixture.json'])
    assert result['test'] == ['src/test/resources/fixture.json']


def test_classify_paths_claims_nested_test_resources_as_test():
    """A resource under a nested module's src/test/resources tree is test."""
    ext = BuildExtension()
    result = ext.classify_paths(['module-a/src/test/resources/fixture.json'])
    assert result['test'] == ['module-a/src/test/resources/fixture.json']


def test_classify_paths_nested_resources_match_bare_forms():
    """Nested and bare resource layouts classify identically."""
    ext = BuildExtension()
    result = ext.classify_paths([
        'src/main/resources/a.properties',
        'module-a/src/main/resources/b.properties',
        'src/test/resources/c.json',
        'module-a/src/test/resources/d.json',
    ])
    assert result['production'] == [
        'src/main/resources/a.properties',
        'module-a/src/main/resources/b.properties',
    ]
    assert result['test'] == [
        'src/test/resources/c.json',
        'module-a/src/test/resources/d.json',
    ]


def test_classify_paths_claims_resources_regardless_of_extension():
    """A resource's role follows its tree, not its file suffix."""
    ext = BuildExtension()
    result = ext.classify_paths([
        'src/main/resources/logback.xml',
        'src/main/resources/data.csv',
        'src/main/resources/mystery.xyz',
    ])
    assert result['production'] == [
        'src/main/resources/logback.xml',
        'src/main/resources/data.csv',
        'src/main/resources/mystery.xyz',
    ]


# --- Shell scripts: bare-basename config route, root and nested --------------


def test_classify_paths_claims_root_shell_script_as_config():
    """A shell script at the repo root is claimed under config.

    The bare-basename ``*.sh`` route is what covers this case — a ``**/*.sh``
    form would require a leading directory and miss the repo-root script.
    """
    ext = BuildExtension()
    result = ext.classify_paths(['build.sh'])
    assert result['config'] == ['build.sh']


def test_classify_paths_claims_nested_shell_script_as_config():
    """A shell script under a directory is claimed under config."""
    ext = BuildExtension()
    result = ext.classify_paths(['scripts/release.sh'])
    assert result['config'] == ['scripts/release.sh']


def test_classify_paths_resource_tree_outranks_shell_script_route():
    """A .sh inside a resource tree keeps the tree's role — resources outrank *.sh."""
    ext = BuildExtension()
    result = ext.classify_paths(['src/main/resources/bin/run.sh'])
    assert result['production'] == ['src/main/resources/bin/run.sh']
    assert result['config'] == []


def test_classify_paths_test_resource_tree_outranks_shell_script_route():
    """A .sh inside the test resource tree resolves to test, not config."""
    ext = BuildExtension()
    result = ext.classify_paths(['src/test/resources/bin/setup.sh'])
    assert result['test'] == ['src/test/resources/bin/setup.sh']
    assert result['config'] == []


# --- Pre-existing java / pom.xml rows: no regression -------------------------


def test_classify_paths_still_claims_main_java_as_production():
    """The pre-existing src/main java route is unchanged."""
    ext = BuildExtension()
    result = ext.classify_paths(['src/main/java/com/example/Foo.java'])
    assert result['production'] == ['src/main/java/com/example/Foo.java']


def test_classify_paths_still_claims_test_java_as_test():
    """The pre-existing src/test java route is unchanged."""
    ext = BuildExtension()
    result = ext.classify_paths(['src/test/java/com/example/FooTest.java'])
    assert result['test'] == ['src/test/java/com/example/FooTest.java']


def test_classify_paths_still_claims_pom_xml_as_config():
    """The pre-existing pom.xml reactor-descriptor route is unchanged."""
    ext = BuildExtension()
    result = ext.classify_paths(['pom.xml'])
    assert result['config'] == ['pom.xml']


def test_classify_paths_still_claims_nested_pom_xml_as_config():
    """A nested module's pom.xml remains a config claim."""
    ext = BuildExtension()
    result = ext.classify_paths(['module-a/pom.xml'])
    assert result['config'] == ['module-a/pom.xml']


def test_classify_paths_returns_all_four_role_keys():
    """The return always carries the four canonical role keys."""
    ext = BuildExtension()
    result = ext.classify_paths(['anything.txt'])
    assert set(result.keys()) == {'production', 'test', 'documentation', 'config'}


def test_classify_paths_omits_unmatched_paths():
    """A path matching no pattern is omitted from every role bucket."""
    ext = BuildExtension()
    assert ext.classify_paths(['mystery.xyz']) == {
        'production': [],
        'test': [],
        'documentation': [],
        'config': [],
    }


def test_classify_paths_handles_empty_input():
    """An empty path list yields the empty four-role dict."""
    ext = BuildExtension()
    assert ext.classify_paths([]) == {
        'production': [],
        'test': [],
        'documentation': [],
        'config': [],
    }


def test_classify_paths_mixed_input():
    """A mixed input list classifies each path into the right bucket."""
    ext = BuildExtension()
    result = ext.classify_paths([
        'src/main/resources/application.properties',
        'src/main/java/com/example/Foo.java',
        'src/test/resources/fixture.json',
        'src/test/java/com/example/FooTest.java',
        'pom.xml',
        'build.sh',
    ])
    assert result['production'] == [
        'src/main/resources/application.properties',
        'src/main/java/com/example/Foo.java',
    ]
    assert result['test'] == [
        'src/test/resources/fixture.json',
        'src/test/java/com/example/FooTest.java',
    ]
    assert result['config'] == ['pom.xml', 'build.sh']


# --- Specificity ladder: resources 3 > java 2 > pom.xml 1 > *.sh 0 -----------


def test_classify_path_specificity_resources_scores_three():
    """A resource path returns the resource row's specificity of 3."""
    ext = BuildExtension()
    assert (
        ext.classify_path_specificity(
            'src/main/resources/application.properties', 'production'
        )
        == 3
    )
    assert (
        ext.classify_path_specificity('src/test/resources/fixture.json', 'test') == 3
    )


def test_classify_path_specificity_java_scores_two():
    """A java source path returns the java row's specificity of 2."""
    ext = BuildExtension()
    assert (
        ext.classify_path_specificity('src/main/java/com/example/Foo.java', 'production')
        == 2
    )
    assert (
        ext.classify_path_specificity('src/test/java/com/example/FooTest.java', 'test')
        == 2
    )


def test_classify_path_specificity_pom_xml_scores_one():
    """The pom.xml descriptor returns a specificity of 1."""
    ext = BuildExtension()
    assert ext.classify_path_specificity('pom.xml', 'config') == 1


def test_classify_path_specificity_shell_script_scores_zero():
    """A claimed shell script returns the bare-basename row's specificity of 0."""
    ext = BuildExtension()
    assert ext.classify_path_specificity('build.sh', 'config') == 0
    assert ext.classify_path_specificity('scripts/release.sh', 'config') == 0


def test_classify_path_specificity_returns_zero_for_wrong_role():
    """A path claimed under a different role than asked returns 0."""
    ext = BuildExtension()
    assert (
        ext.classify_path_specificity(
            'src/main/resources/application.properties', 'test'
        )
        == 0
    )
    assert ext.classify_path_specificity('pom.xml', 'production') == 0


def test_classify_path_specificity_returns_zero_for_unclaimed_path():
    """A path that matches no pattern returns 0 for any role."""
    ext = BuildExtension()
    assert ext.classify_path_specificity('mystery.xyz', 'production') == 0
    assert ext.classify_path_specificity('README.md', 'documentation') == 0


# --- classify_globs() route table -------------------------------------------


def test_classify_globs_declares_resource_routes():
    """Both bare and nested resource routes are declared under the right roles."""
    ext = BuildExtension()
    routes = ext.classify_globs()
    assert ('*/src/main/resources/*', 'production') in routes
    assert ('src/main/resources/*', 'production') in routes
    assert ('*/src/test/resources/*', 'test') in routes
    assert ('src/test/resources/*', 'test') in routes


def test_classify_globs_declares_shell_script_config_route():
    """The bare-basename *.sh route is declared under config."""
    ext = BuildExtension()
    assert ('*.sh', 'config') in ext.classify_globs()


def test_classify_globs_still_declares_java_and_pom_routes():
    """The pre-existing java and pom.xml routes are unchanged."""
    ext = BuildExtension()
    routes = ext.classify_globs()
    assert ('*/src/main/*.java', 'production') in routes
    assert ('src/main/*.java', 'production') in routes
    assert ('*/src/test/*.java', 'test') in routes
    assert ('src/test/*.java', 'test') in routes
    assert ('pom.xml', 'config') in routes


def test_classify_globs_orders_resource_routes_before_shell_script_route():
    """The *.sh route is declared last so resource trees win the first match."""
    ext = BuildExtension()
    patterns = [pattern for pattern, _role in ext.classify_globs()]
    assert patterns[-1] == '*.sh'
    assert patterns.index('src/main/resources/*') < patterns.index('*.sh')
    assert patterns.index('src/test/resources/*') < patterns.index('*.sh')


def test_classify_globs_every_role_is_a_build_map_role():
    """Each route's role is one of the four resolved BUILD_MAP_ROLES."""
    ext = BuildExtension()
    for _pattern, role in ext.classify_globs():
        assert role in BUILD_MAP_ROLES


def test_classify_globs_uses_single_star_not_recursive():
    """Routes use single-* fnmatch globs (matcher spans /), not recursive ** forms."""
    ext = BuildExtension()
    for pattern, _role in ext.classify_globs():
        assert '**' not in pattern
