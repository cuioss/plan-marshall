#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``_parse_pom_xml`` — the subprocess-free POM coordinate parse.

``discover_maven_modules`` no longer shells out to Maven for the cheap module
shape: ``_parse_pom_xml`` extracts packaging / artifactId / groupId (with
parent fallback) / declared profile ids / description / parent GAV / own
dependencies from the ``pom.xml`` with stdlib ``xml.etree``. These tests pin that parse against both
namespaced (the usual ``http://maven.apache.org/POM/4.0.0`` declaration) and
namespace-less POMs. No Maven binary is required.
"""

import tempfile
from pathlib import Path

from conftest import load_script_module

_maven_cmd_discover = load_script_module(
    'plan-marshall', 'build-maven', '_maven_cmd_discover.py', '_maven_cmd_discover'
)

_parse_pom_xml = _maven_cmd_discover._parse_pom_xml


def _write_pom(content: str) -> Path:
    """Write ``content`` to a ``pom.xml`` in a fresh tmp dir and return the path."""
    tmpdir = Path(tempfile.mkdtemp())
    pom = tmpdir / 'pom.xml'
    pom.write_text(content)
    return pom


# Namespaced POM (the canonical Maven shape).
_NS_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>my-app</artifactId>
  <version>1.0.0</version>
  <packaging>war</packaging>
  <description>My example application</description>
  <profiles>
    <profile><id>coverage</id></profile>
    <profile><id>integration-tests</id></profile>
  </profiles>
</project>
"""

# Namespace-less POM (legacy / hand-written shape — no xmlns).
_NO_NS_POM = """<project>
  <groupId>org.legacy</groupId>
  <artifactId>legacy-mod</artifactId>
  <version>2.0</version>
  <profiles>
    <profile><id>release</id></profile>
  </profiles>
</project>
"""

# Child POM that omits its own groupId — it must inherit from <parent>.
_PARENT_FALLBACK_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>com.parent</groupId>
    <artifactId>parent-pom</artifactId>
    <version>1.0.0</version>
  </parent>
  <artifactId>child-mod</artifactId>
</project>
"""


# =============================================================================
# packaging
# =============================================================================


def test_parse_pom_xml_packaging_explicit():
    """Explicit <packaging> is returned verbatim."""
    pom = _write_pom(_NS_POM)
    assert _parse_pom_xml(pom)['packaging'] == 'war'


def test_parse_pom_xml_packaging_defaults_to_jar():
    """A POM with no <packaging> defaults to 'jar'."""
    pom = _write_pom(_NO_NS_POM)
    assert _parse_pom_xml(pom)['packaging'] == 'jar'


# =============================================================================
# artifactId / groupId / parent
# =============================================================================


def test_parse_pom_xml_namespaced_coordinates():
    """artifactId + groupId parse from a namespaced POM."""
    result = _parse_pom_xml(_write_pom(_NS_POM))
    assert result['artifact_id'] == 'my-app'
    assert result['group_id'] == 'com.example'


def test_parse_pom_xml_namespace_less_coordinates():
    """artifactId + groupId parse from a namespace-less POM."""
    result = _parse_pom_xml(_write_pom(_NO_NS_POM))
    assert result['artifact_id'] == 'legacy-mod'
    assert result['group_id'] == 'org.legacy'


def test_parse_pom_xml_group_id_falls_back_to_parent():
    """A child omitting <groupId> inherits the parent's groupId."""
    result = _parse_pom_xml(_write_pom(_PARENT_FALLBACK_POM))
    assert result['artifact_id'] == 'child-mod'
    assert result['group_id'] == 'com.parent'
    assert result['parent'] == 'com.parent:parent-pom'


def test_parse_pom_xml_parent_none_when_absent():
    """A POM with no <parent> reports parent=None."""
    assert _parse_pom_xml(_write_pom(_NS_POM))['parent'] is None


# =============================================================================
# description
# =============================================================================


def test_parse_pom_xml_description():
    """<description> text is extracted."""
    assert _parse_pom_xml(_write_pom(_NS_POM))['description'] == 'My example application'


def test_parse_pom_xml_description_none_when_absent():
    """A POM with no <description> reports description=None."""
    assert _parse_pom_xml(_write_pom(_NO_NS_POM))['description'] is None


# =============================================================================
# declared profile ids
# =============================================================================


def test_parse_pom_xml_declared_profile_ids_namespaced():
    """Declared /project/profiles/profile/id values parse (namespaced)."""
    result = _parse_pom_xml(_write_pom(_NS_POM))
    assert result['profile_ids'] == ['coverage', 'integration-tests']


def test_parse_pom_xml_declared_profile_ids_namespace_less():
    """Declared profile ids parse from a namespace-less POM."""
    result = _parse_pom_xml(_write_pom(_NO_NS_POM))
    assert result['profile_ids'] == ['release']


def test_parse_pom_xml_no_profiles_yields_empty_list():
    """A POM with no <profiles> block yields an empty profile_ids list."""
    assert _parse_pom_xml(_write_pom(_PARENT_FALLBACK_POM))['profile_ids'] == []


# =============================================================================
# malformed POM degrades gracefully
# =============================================================================


def test_parse_pom_xml_malformed_returns_defaults():
    """A malformed POM degrades to packaging='jar' with empty/None fields."""
    pom = _write_pom('<project><artifactId>broken')  # unclosed tags
    result = _parse_pom_xml(pom)
    assert result['packaging'] == 'jar'
    assert result['artifact_id'] is None
    assert result['profile_ids'] == []


def test_parse_pom_xml_malformed_exact_shape():
    """The malformed-POM default carries every key, dependencies as an empty list."""
    result = _parse_pom_xml(_write_pom('<project><artifactId>broken'))
    assert result == {
        'packaging': 'jar',
        'artifact_id': None,
        'group_id': None,
        'profile_ids': [],
        'description': None,
        'parent': None,
        'dependencies': [],
    }


# =============================================================================
# exact shape
# =============================================================================


def test_parse_pom_xml_exact_shape_namespaced():
    """The full parse result for a namespaced POM, including the dependencies key."""
    assert _parse_pom_xml(_write_pom(_NS_POM)) == {
        'packaging': 'war',
        'artifact_id': 'my-app',
        'group_id': 'com.example',
        'profile_ids': ['coverage', 'integration-tests'],
        'description': 'My example application',
        'parent': None,
        'dependencies': [],
    }


def test_parse_pom_xml_exact_shape_parent_fallback():
    """The full parse result for a child POM inheriting its groupId."""
    assert _parse_pom_xml(_write_pom(_PARENT_FALLBACK_POM)) == {
        'packaging': 'jar',
        'artifact_id': 'child-mod',
        'group_id': 'com.parent',
        'profile_ids': [],
        'description': None,
        'parent': 'com.parent:parent-pom',
        'dependencies': [],
    }


# =============================================================================
# own dependencies
# =============================================================================

# Child POM declaring dependencies in its own <dependencies>, in
# <dependencyManagement>, and inside a profile — only the first are read.
_DEPENDENCIES_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>com.parent</groupId>
    <artifactId>parent-pom</artifactId>
    <version>1.0.0</version>
  </parent>
  <groupId>com.child</groupId>
  <artifactId>client</artifactId>
  <dependencies>
    <dependency>
      <groupId>com.child</groupId>
      <artifactId>validation</artifactId>
      <version>1.0.0</version>
      <classifier>generators</classifier>
      <scope>test</scope>
    </dependency>
    <dependency>
      <groupId>com.child</groupId>
      <artifactId>fixtures</artifactId>
      <version>1.0.0</version>
      <type>test-jar</type>
      <scope>test</scope>
    </dependency>
    <dependency>
      <groupId>${project.groupId}</groupId>
      <artifactId>api</artifactId>
    </dependency>
    <dependency>
      <groupId>${project.parent.groupId}</groupId>
      <artifactId>bom-member</artifactId>
    </dependency>
    <dependency>
      <groupId>${custom.group}</groupId>
      <artifactId>custom</artifactId>
    </dependency>
    <dependency>
      <artifactId>no-group</artifactId>
    </dependency>
  </dependencies>
  <dependencyManagement>
    <dependencies>
      <dependency>
        <groupId>com.managed</groupId>
        <artifactId>managed-only</artifactId>
        <classifier>generators</classifier>
      </dependency>
    </dependencies>
  </dependencyManagement>
  <profiles>
    <profile>
      <id>extra</id>
      <dependencies>
        <dependency>
          <groupId>com.profile</groupId>
          <artifactId>profile-only</artifactId>
          <type>test-jar</type>
        </dependency>
      </dependencies>
    </profile>
  </profiles>
</project>
"""


def _dependencies_by_artifact() -> dict[str, dict]:
    """Parse ``_DEPENDENCIES_POM`` and key its dependencies by artifactId."""
    return {d['artifact_id']: d for d in _parse_pom_xml(_write_pom(_DEPENDENCIES_POM))['dependencies']}


def test_parse_pom_xml_dependency_with_classifier():
    """A classified dependency carries its classifier and keeps the default jar type."""
    assert _dependencies_by_artifact()['validation'] == {
        'group_id': 'com.child',
        'artifact_id': 'validation',
        'type': 'jar',
        'classifier': 'generators',
        'scope': 'test',
    }


def test_parse_pom_xml_dependency_with_test_jar_type():
    """A test-jar dependency carries its type and no classifier."""
    assert _dependencies_by_artifact()['fixtures'] == {
        'group_id': 'com.child',
        'artifact_id': 'fixtures',
        'type': 'test-jar',
        'classifier': None,
        'scope': 'test',
    }


def test_parse_pom_xml_dependency_defaults_type_and_scope():
    """An undeclared type and scope take Maven's defaults (jar, compile)."""
    api = _dependencies_by_artifact()['api']
    assert api['type'] == 'jar'
    assert api['scope'] == 'compile'
    assert api['classifier'] is None


def test_parse_pom_xml_dependency_interpolates_project_group_id():
    """${project.groupId} resolves to the module's own groupId."""
    assert _dependencies_by_artifact()['api']['group_id'] == 'com.child'


def test_parse_pom_xml_dependency_interpolates_project_parent_group_id():
    """${project.parent.groupId} resolves to the parent's groupId."""
    assert _dependencies_by_artifact()['bom-member']['group_id'] == 'com.parent'


def test_parse_pom_xml_dependency_project_group_id_uses_inherited_group():
    """A child without its own groupId interpolates ${project.groupId} to the inherited one."""
    pom = """<project>
  <parent>
    <groupId>com.parent</groupId>
    <artifactId>parent-pom</artifactId>
  </parent>
  <artifactId>child</artifactId>
  <dependencies>
    <dependency>
      <groupId>${project.groupId}</groupId>
      <artifactId>sibling</artifactId>
      <type>test-jar</type>
    </dependency>
  </dependencies>
</project>
"""
    dependencies = _parse_pom_xml(_write_pom(pom))['dependencies']
    assert [(d['group_id'], d['artifact_id']) for d in dependencies] == [('com.parent', 'sibling')]


def test_parse_pom_xml_dependency_other_property_stays_literal():
    """Any other property is left uninterpolated."""
    assert _dependencies_by_artifact()['custom']['group_id'] == '${custom.group}'


def test_parse_pom_xml_dependency_without_group_id_is_skipped():
    """A dependency lacking a groupId is not reported."""
    assert 'no-group' not in _dependencies_by_artifact()


def test_parse_pom_xml_dependencies_exclude_management_and_profiles():
    """Only /project/dependencies is read, in declared order."""
    artifact_ids = [d['artifact_id'] for d in _parse_pom_xml(_write_pom(_DEPENDENCIES_POM))['dependencies']]
    assert artifact_ids == ['validation', 'fixtures', 'api', 'bom-member', 'custom']
