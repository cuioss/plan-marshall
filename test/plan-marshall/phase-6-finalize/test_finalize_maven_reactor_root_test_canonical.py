#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The pre-push gate's step 0 reaches a Maven reactor root's ``module-tests``.

The whole-tree module-tests divergence gate (``pre-push-quality-gate.md``
§ "Whole-tree module-tests divergence gate" step 0) resolves ``module-tests`` at
DEFAULT scope first, and the default scope answers from the reactor root module.
For a Maven reactor that root is a ``pom`` aggregator, so the resolve succeeds
only once discovery gives the aggregator the whole-reactor ``test`` canonical.
Its second step then calls ``resolve-test-scope`` on the notation the resolved
executable carries.

This test drives the REAL resolver over a REAL Maven-shaped project tree — the
crawl runs the shipped discovery, no stub and no hand-seeded command map — so it
fails on the defect rather than on a model of it. It then checks that the
notation the resolve returns is the one whose SKILL.md publishes
``resolve-test-scope``, which is what makes the arm's branch 1 reachable instead
of its DEGRADED branch.
"""

import argparse
import copy
from pathlib import Path
from typing import Any

from conftest import MARKETPLACE_ROOT, load_script_module, parse_ns

_ARCH_BUNDLE = 'plan-marshall'
_ARCH_SKILL = 'manage-architecture'
_ARCH_SCRIPT = 'architecture.py'

_cmd_client = load_script_module(_ARCH_BUNDLE, _ARCH_SKILL, '_cmd_client.py', '_cmd_client')

cmd_resolve = _cmd_client.cmd_resolve

#: The ``resolve`` namespace, built by ``architecture.py``'s own parser so it
#: carries every production default. ``register=False`` because only the
#: namespace is wanted.
_RESOLVE_ARGS = parse_ns(
    _ARCH_BUNDLE,
    _ARCH_SKILL,
    _ARCH_SCRIPT,
    '--project-dir',
    '.',
    'resolve',
    '--command',
    'module-tests',
    register=False,
)

_ROOT_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>probe</groupId>
  <artifactId>probe-parent</artifactId>
  <version>1.0.0</version>
  <packaging>pom</packaging>
  <modules>
    <module>core</module>
  </modules>
</project>
"""

_CORE_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>probe</groupId>
  <artifactId>core</artifactId>
  <version>1.0.0</version>
  <packaging>jar</packaging>
</project>
"""


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from the parser-derived base for one call."""
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


def _write_reactor(root: Path) -> None:
    """Write a Maven reactor whose root is a ``pom`` aggregator with a tested module."""
    (root / 'pom.xml').write_text(_ROOT_POM, encoding='utf-8')
    core = root / 'core'
    (core / 'src' / 'test' / 'java' / 'probe').mkdir(parents=True)
    (core / 'pom.xml').write_text(_CORE_POM, encoding='utf-8')
    (core / 'src' / 'test' / 'java' / 'probe' / 'CoreTest.java').write_text(
        'package probe;\n\nclass CoreTest {}\n', encoding='utf-8'
    )


def _resolve_default_scope_module_tests(root: Path) -> Any:
    """Resolve ``module-tests`` at default scope the way the gate's step 0 does."""
    return cmd_resolve(_variant(_RESOLVE_ARGS, project_dir=str(root), module=None))


def test_maven_reactor_root_resolves_module_tests_at_default_scope(tmp_path: Path) -> None:
    """Step 0's default-scope resolve succeeds instead of reaching the DEGRADED branch."""
    _write_reactor(tmp_path)

    result = _resolve_default_scope_module_tests(tmp_path)

    assert result['status'] == 'success', result
    # The whole reactor, with no module argument: the root module emits no -pl.
    assert result['executable'].endswith('--command-args "test"')
    assert 'plan-marshall:build-maven:maven' in result['executable']


def test_the_resolved_notation_publishes_the_scope_verb_the_arm_calls_next(tmp_path: Path) -> None:
    """The notation step 0 captures is one whose SKILL.md publishes ``resolve-test-scope``."""
    _write_reactor(tmp_path)
    result = _resolve_default_scope_module_tests(tmp_path)
    assert result['status'] == 'success', result

    skill_root = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'build-maven'
    skill_text = (skill_root / 'SKILL.md').read_text(encoding='utf-8')

    assert '### resolve-test-scope' in skill_text
    assert (skill_root / 'scripts' / '_maven_cmd_resolve_scope.py').is_file()
