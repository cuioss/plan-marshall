#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Gradle's coverage by the Maven derivation resolver — and the one form it misses.

Gradle registers **no** Axis-C resolver of its own. It does not need one for the
coordinate case: Gradle discovery publishes `metadata.group_id` /
`metadata.artifact_id` exactly as Maven's does and emits
``groupId:artifactId:compile`` dependency strings, so the `maven` resolver joins
Gradle modules unchanged — a second reference implementation of the coordinate
join rather than a second implementor of it.

That claim is asserted in three consumer-facing places
(`ext-point-derivation-resolver.md` § "Gradle rides the Maven join",
`doc/concepts/code-intelligence.adoc`, `doc/user/dependency-intelligence.adoc`),
so it is pinned here rather than left to prose. Its **limitation** is pinned in
the same place and for the same reason: an inter-project dependency declared the
idiomatic way (``implementation project(':core')``) is rendered by
``gradle dependencies`` as ``+--- project :core`` and extracted as
``project:core:compile``, whose first two colon-separated parts are the literal
``project:core`` — matching no module's published coordinate, so no edge.

**No Gradle daemon runs here.** Discovery's Gradle path shells out, so the two
halves are exercised separately against real code: the console text is fed to the
REAL ``_parse_dependencies_output``, and its output is fed to the REAL Maven
resolver over a module map shaped exactly as ``_extract_gradle_module`` returns.
Only the console text itself is transcribed — from the format that parser's own
docstring documents.
"""

import importlib.util

from conftest import PROJECT_ROOT, load_script_module

_gradle_cmd_discover = load_script_module(
    'plan-marshall', 'build-gradle', '_gradle_cmd_discover.py', '_gradle_cmd_discover'
)

_MAVEN_EXTENSION_FILE = (
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
    """Load the build-maven BuildExtension by explicit file path.

    Every build skill ships an ``extension.py`` sharing the module basename
    ``extension``; loading via ``spec_from_file_location`` against the explicit
    path avoids the cross-skill ``import extension`` collision.
    """
    spec = importlib.util.spec_from_file_location('maven_build_extension_for_gradle', _MAVEN_EXTENSION_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MavenBuildExtension = _load_maven_build_extension().BuildExtension


#: A real ``gradle :app:dependencies --configuration compileClasspath`` rendering,
#: in the format ``_parse_dependencies_output``'s docstring documents. Carries all
#: four shapes at once: an inter-project dependency, an internal dependency named
#: by full coordinate, an external dependency with a resolved version, a
#: transitive (``|``-prefixed) line that must be skipped, and a final ``\\---``
#: entry.
GRADLE_COMPILE_CLASSPATH = """
compileClasspath - Compile classpath for source set 'main'.
+--- project :core
+--- com.example:shared:1.0.0
+--- org.springframework.boot:spring-boot-starter -> 3.0.0
|    +--- org.springframework:spring-core:6.0.0
\\--- com.google.guava:guava:31.1-jre
"""


def _gradle_module(name: str, dependencies: list[str]) -> dict:
    """A module dict shaped as ``_extract_gradle_module`` returns one.

    ``artifact_id`` is the module name and ``group_id`` the Gradle ``group`` —
    the same coordinate pair Maven discovery publishes, which is precisely why
    the Maven resolver can consume it.
    """
    return {
        'name': name,
        'build_systems': ['gradle'],
        'metadata': {
            'artifact_id': name,
            'group_id': 'com.example',
            'packaging': 'jar',
            'description': None,
        },
        'dependencies': dependencies,
    }


def _parsed_dependencies() -> list[str]:
    # The discoverer is loaded by file location, so it carries no type
    # information; declaring the binding keeps the helper's contract explicit
    # rather than propagating ``Any`` into every caller.
    parsed: list[str] = _gradle_cmd_discover._parse_dependencies_output(GRADLE_COMPILE_CLASSPATH)
    return parsed


def _edges() -> list[tuple[str, str]]:
    modules = {
        'app': _gradle_module('app', _parsed_dependencies()),
        'core': _gradle_module('core', []),
        'shared': _gradle_module('shared', []),
    }
    edges: list[tuple[str, str]]
    edges, _ = MavenBuildExtension().derive_edges(modules, {})
    return edges


# =============================================================================
# The extraction half
# =============================================================================


def test_coordinate_dependency_is_extracted_as_a_maven_style_triple():
    assert 'com.example:shared:compile' in _parsed_dependencies()


def test_inter_project_dependency_is_extracted_with_a_literal_project_segment():
    """This extraction is what makes the form unjoinable — pinned as the cause.

    A future change that emitted ``com.example:core:compile`` here would close
    the gap; this assertion is what would notice.
    """
    assert 'project:core:compile' in _parsed_dependencies()


def test_transitive_lines_are_not_extracted():
    assert all('spring-core' not in dependency for dependency in _parsed_dependencies())


# =============================================================================
# The join half
# =============================================================================


def test_gradle_modules_carry_the_coordinate_pair_the_maven_join_reads():
    """The premise of the whole claim: Gradle publishes what Maven publishes."""
    metadata = _gradle_module('core', [])['metadata']
    assert metadata['group_id'] and metadata['artifact_id']


def test_coordinate_declared_dependency_yields_an_edge():
    """Gradle rides the Maven join — the claim, asserted end to end."""
    assert ('app', 'shared') in _edges()


def test_inter_project_declared_dependency_yields_no_edge():
    """The recorded limitation. NOT a wish — a pin on current behaviour.

    If a later change makes this edge derivable, this test fails and the sites
    that state the limitation have to be revisited with it:
    ``ext-point-derivation-resolver.md`` § "Gradle rides the Maven join",
    ``build-maven/SKILL.md`` § "Module-edge derivation", and
    ``doc/user/dependency-intelligence.adoc`` § "The Gradle limitation".
    """
    assert ('app', 'core') not in _edges()


def test_the_gradle_edge_set_is_exactly_the_coordinate_form():
    assert _edges() == [('app', 'shared')]
