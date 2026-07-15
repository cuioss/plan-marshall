#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-extension classification parity guard for build-maven and build-gradle.

build-maven and build-gradle both claim the SAME shared source layout — the
``src/main`` / ``src/test`` convention for java sources, the Maven-standard
resource trees, and shell scripts. That shared surface is duplicated across two
independent ``_CLASSIFY_PATTERNS`` / ``classify_globs()`` tables, so the two can
silently drift apart when only one is edited.

This module is the regression guard against that drift: over a shared table of
the layout paths both build systems claim, it asserts both extensions return the
SAME role AND the SAME ``classify_path_specificity`` score for every row. It
FAILS if either extension's shared rows are changed without the other.

**Descriptor rows are deliberately EXCLUDED from the parity table.** ``pom.xml``
(build-maven) and ``build.gradle`` / ``build.gradle.kts`` / ``settings.gradle`` /
``settings.gradle.kts`` (build-gradle) are legitimately divergent — each build
system owns its own descriptor — and each is asserted in its own per-extension
unit test (test_maven_extension.py / test_gradle_extension.py). The divergence
test at the bottom of this module pins that exclusion so the boundary stays
honest rather than becoming a silent parity hole.

Each ``extension.py`` shares the module basename ``extension``, so both classes
are loaded via ``importlib.util.spec_from_file_location`` against explicit file
paths to avoid the cross-skill module-name collision.
"""

import importlib.util

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT


def _load_build_extension(skill_name: str, module_name: str):
    """Load a build skill's BuildExtension class by explicit file path."""
    extension_path = (
        MARKETPLACE_ROOT
        / 'plan-marshall'
        / 'skills'
        / skill_name
        / 'scripts'
        / 'extension.py'
    )
    if not extension_path.exists():
        raise FileNotFoundError(f'Extension not found: {extension_path}')

    spec = importlib.util.spec_from_file_location(module_name, extension_path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Could not load module from {extension_path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BuildExtension


MavenBuildExtension = _load_build_extension('build-maven', 'maven_parity_extension')
GradleBuildExtension = _load_build_extension('build-gradle', 'gradle_parity_extension')


# The layout rows BOTH build systems claim. Descriptor rows (pom.xml vs
# build.gradle*) are excluded — they are legitimately divergent and are each
# covered by their own per-extension unit test.
SHARED_LAYOUT_PATHS = [
    # Main resources — bare and nested
    'src/main/resources/application.properties',
    'module-a/src/main/resources/application.properties',
    'src/main/resources/logback.xml',
    'src/main/resources/nested/deep/data.csv',
    # Test resources — bare and nested
    'src/test/resources/fixture.json',
    'module-a/src/test/resources/fixture.json',
    'src/test/resources/nested/deep/fixture.xml',
    # Java production sources — bare and nested
    'src/main/java/com/example/Foo.java',
    'module-a/src/main/java/com/example/Foo.java',
    # Java test sources — bare and nested
    'src/test/java/com/example/FooTest.java',
    'module-a/src/test/java/com/example/FooTest.java',
    # Shell scripts — repo root and nested
    'build.sh',
    'scripts/release.sh',
    'module-a/scripts/release.sh',
    # Shell script inside a resource tree — the resource row must win in both
    'src/main/resources/bin/run.sh',
    'src/test/resources/bin/setup.sh',
    # Unclaimed by both
    'mystery.xyz',
]

ROLES = ('production', 'test', 'documentation', 'config')


def _role_of(ext, path: str) -> str | None:
    """Return the single role bucket claiming ``path``, or None if unclaimed."""
    claims = ext.classify_paths([path])
    claiming = [role for role in ROLES if path in claims[role]]
    assert len(claiming) <= 1, f'{path} claimed by multiple roles: {claiming}'
    return claiming[0] if claiming else None


@pytest.mark.parametrize('path', SHARED_LAYOUT_PATHS)
def test_shared_layout_role_parity(path):
    """Both extensions claim every shared-layout path under the SAME role."""
    maven_role = _role_of(MavenBuildExtension(), path)
    gradle_role = _role_of(GradleBuildExtension(), path)
    assert maven_role == gradle_role, (
        f'role drift for {path}: build-maven={maven_role}, build-gradle={gradle_role}'
    )


@pytest.mark.parametrize('path', SHARED_LAYOUT_PATHS)
def test_shared_layout_specificity_parity(path):
    """Both extensions score every shared-layout path with the SAME specificity."""
    maven_ext = MavenBuildExtension()
    gradle_ext = GradleBuildExtension()

    role = _role_of(maven_ext, path)
    if role is None:
        # Unclaimed rows score 0 for every role in both extensions.
        for probe_role in ROLES:
            assert maven_ext.classify_path_specificity(
                path, probe_role
            ) == gradle_ext.classify_path_specificity(path, probe_role)
        return

    maven_score = maven_ext.classify_path_specificity(path, role)
    gradle_score = gradle_ext.classify_path_specificity(path, role)
    assert maven_score == gradle_score, (
        f'specificity drift for {path} under {role}: '
        f'build-maven={maven_score}, build-gradle={gradle_score}'
    )


def test_shared_layout_resources_outrank_shell_scripts_in_both():
    """A .sh inside a resource tree keeps the tree's role in BOTH extensions."""
    for ext in (MavenBuildExtension(), GradleBuildExtension()):
        assert _role_of(ext, 'src/main/resources/bin/run.sh') == 'production'
        assert _role_of(ext, 'src/test/resources/bin/setup.sh') == 'test'


def test_shared_layout_classify_globs_routes_agree():
    """Both extensions declare the SAME shared-layout classify_globs() routes."""
    shared_routes = {
        ('*/src/main/resources/*', 'production'),
        ('src/main/resources/*', 'production'),
        ('*/src/test/resources/*', 'test'),
        ('src/test/resources/*', 'test'),
        ('*/src/main/*.java', 'production'),
        ('src/main/*.java', 'production'),
        ('*/src/test/*.java', 'test'),
        ('src/test/*.java', 'test'),
        ('*.sh', 'config'),
    }
    maven_routes = set(MavenBuildExtension().classify_globs())
    gradle_routes = set(GradleBuildExtension().classify_globs())
    assert shared_routes <= maven_routes
    assert shared_routes <= gradle_routes


def test_descriptor_rows_are_legitimately_divergent():
    """Descriptor rows diverge by design — this pins the parity-table exclusion.

    Each build system claims only its OWN descriptor. This is the reason the
    descriptor rows are excluded from SHARED_LAYOUT_PATHS; the assertion keeps
    that exclusion honest instead of letting it hide real drift.
    """
    maven_ext = MavenBuildExtension()
    gradle_ext = GradleBuildExtension()

    assert _role_of(maven_ext, 'pom.xml') == 'config'
    assert _role_of(gradle_ext, 'pom.xml') is None

    for descriptor in (
        'build.gradle',
        'build.gradle.kts',
        'settings.gradle',
        'settings.gradle.kts',
    ):
        assert _role_of(gradle_ext, descriptor) == 'config'
        assert _role_of(maven_ext, descriptor) is None


def test_parity_table_excludes_descriptor_rows():
    """The parity table itself carries no descriptor row — the exclusion is structural."""
    descriptors = {
        'pom.xml',
        'build.gradle',
        'build.gradle.kts',
        'settings.gradle',
        'settings.gradle.kts',
    }
    for path in SHARED_LAYOUT_PATHS:
        assert path.split('/')[-1] not in descriptors
