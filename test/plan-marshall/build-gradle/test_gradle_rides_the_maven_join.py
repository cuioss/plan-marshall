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

from _build_extension_fixtures import load_build_extension

from conftest import load_script_module

_gradle_cmd_discover = load_script_module(
    'plan-marshall', 'build-gradle', '_gradle_cmd_discover.py', '_gradle_cmd_discover'
)

# Loaded under a name distinct from every other Maven-extension load site, so
# this module's copy stays independent of theirs.
MavenBuildExtension = load_build_extension('build-maven', 'maven_build_extension_for_gradle')


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


def _real_gradle_module(tmp_path, gradle_data: dict) -> dict:
    """Call the REAL ``_extract_gradle_module`` hermetically.

    The extractor takes ``gradle_data`` as a PARAMETER and runs no subprocess, so
    a temp directory holding an empty build file plus a literal metadata dict is a
    complete call. The "it needs a Gradle daemon" escape applies to discovery's
    shelling-out path, not to this function.

    The build-file name is read off the discoverer's own constant rather than
    spelled here, so a rename cannot leave this fixture silently unable to produce
    a module (which would turn every assertion below vacuous).
    """
    module_dir = tmp_path / 'core'
    module_dir.mkdir()
    (module_dir / _gradle_cmd_discover.BUILD_GRADLE).write_text('', encoding='utf-8')
    module: dict = _gradle_cmd_discover._extract_gradle_module(module_dir, tmp_path, 'core', gradle_data, [])
    return module


def test_gradle_modules_carry_the_coordinate_pair_the_maven_join_reads(tmp_path):
    """The premise of the whole claim: Gradle publishes what Maven publishes.

    Asserted against the REAL extractor. The previous form read the coordinate
    pair back out of ``_gradle_module``, a helper in this same file that hard-codes
    both values — so it asserted that a literal dict contains the keys the literal
    was written with, and would have stayed green if the shipped extractor stopped
    publishing a coordinate entirely.
    """
    module = _real_gradle_module(tmp_path, {'name': 'core', 'group_id': 'com.example'})

    metadata = module['metadata']
    assert metadata['artifact_id'] == 'core'
    assert metadata['group_id'] == 'com.example'


def test_gradle_module_without_a_group_publishes_no_joinable_coordinate(tmp_path):
    """The no-``group`` case: a Gradle build declaring no ``group`` yields no join key.

    ``group`` is optional in Gradle, and the extractor passes ``group_id`` through
    as ``None`` when it is absent. The Maven join keys on ``groupId:artifactId``,
    so such a module publishes no coordinate for a dependent to match — the same
    "no edge" outcome as the inter-project form, reached by a different route.
    """
    module = _real_gradle_module(tmp_path, {'name': 'core'})

    metadata = module['metadata']
    assert metadata['artifact_id'] == 'core'
    assert metadata['group_id'] is None


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
