#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``_parse_pom_xml`` — the subprocess-free POM coordinate parse.

``discover_maven_modules`` no longer shells out to Maven for the cheap module
shape: ``_parse_pom_xml`` extracts packaging / artifactId / groupId (with
parent fallback) / declared profile ids / description / parent GAV from the
``pom.xml`` with stdlib ``xml.etree``. These tests pin that parse against both
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
