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
notation the resolve returns is the one whose CLI publishes
``resolve-test-scope``, which is what makes the arm's branch 1 reachable instead
of its DEGRADED branch.
"""

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, parse_ns, run_script

_ARCH_BUNDLE = 'plan-marshall'
_ARCH_SKILL = 'manage-architecture'
_ARCH_SCRIPT = 'architecture.py'

_cmd_client = load_script_module(_ARCH_BUNDLE, _ARCH_SKILL, '_cmd_client.py', '_cmd_client')
_maven_discover = load_script_module(_ARCH_BUNDLE, 'build-maven', '_maven_cmd_discover.py', '_maven_cmd_discover')

cmd_resolve = _cmd_client.cmd_resolve
cmd_derive_verification = _cmd_client.cmd_derive_verification
discover_maven_modules = _maven_discover.discover_maven_modules

#: The build skill notation a Maven reactor's canonicals resolve to.
_MAVEN_NOTATION = 'plan-marshall:build-maven:maven'

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

#: The ``derive-verification`` namespace, from the same parser.
_DERIVE_ARGS = parse_ns(
    _ARCH_BUNDLE,
    _ARCH_SKILL,
    _ARCH_SCRIPT,
    '--project-dir',
    '.',
    'derive-verification',
    '--changed-artifacts',
    '',
    register=False,
)

#: The build map a Maven consumer's domain extension contributes for the file
#: the reactor ROOT owns. ``verify`` is the root's own gate class.
_ROOT_POM_BUILD_MAP = {
    'plan-marshall-plugin-dev': [
        {'glob': 'pom.xml', 'role': 'production', 'build_class': 'verify'},
    ],
}

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

_PLAIN_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>probe</groupId>
  <artifactId>plain</artifactId>
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
    """Write a Maven reactor whose root is a ``pom`` aggregator with a tested module.

    ``plain`` is a module with NO test source, so the reactor also carries the
    case a ``resolve --command module-tests --module plain`` now cascades from.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / 'pom.xml').write_text(_ROOT_POM, encoding='utf-8')
    core = root / 'core'
    (core / 'src' / 'test' / 'java' / 'probe').mkdir(parents=True)
    (core / 'pom.xml').write_text(_CORE_POM, encoding='utf-8')
    (core / 'src' / 'test' / 'java' / 'probe' / 'CoreTest.java').write_text(
        'package probe;\n\nclass CoreTest {}\n', encoding='utf-8'
    )
    (root / 'plain').mkdir()
    (root / 'plain' / 'pom.xml').write_text(_PLAIN_POM, encoding='utf-8')


def _persist_modules(project_dir: Path, modules: list) -> None:
    """Write a discovered module set in the on-disk architecture shape.

    ``project_dir`` holds no build files of its own, so the resolver's crawl
    finds no modules and reads this persisted view — which is what makes it a
    persisted architecture rather than a live crawl.
    """
    architecture = project_dir / '.plan' / 'project-architecture'
    for module in modules:
        target = architecture / module['name']
        target.mkdir(parents=True, exist_ok=True)
        (target / 'derived.json').write_text(json.dumps(module), encoding='utf-8')


def _resolve_default_scope(root: Path, command: str) -> Any:
    """Resolve ``command`` at default scope the way the gate's step 0 does."""
    return cmd_resolve(_variant(_RESOLVE_ARGS, project_dir=str(root), module=None, resolve_command=command))


def test_maven_reactor_root_resolves_module_tests_at_default_scope(tmp_path: Path) -> None:
    """Step 0's default-scope resolve succeeds instead of reaching the DEGRADED branch."""
    _write_reactor(tmp_path)

    result = _resolve_default_scope(tmp_path, 'module-tests')

    assert result['status'] == 'success', result
    # The whole reactor, with no module argument: the root module emits no -pl.
    assert result['executable'].endswith('--command-args "test"')
    assert _MAVEN_NOTATION in result['executable']


def test_maven_reactor_root_resolves_test_compile_at_default_scope(tmp_path: Path) -> None:
    """The whole-tree ``test-compile`` probe succeeds, so no module argument is removed.

    The gate's fallback widens a module-scoped ``test-compile -pl X -am`` by
    removing the module argument. What that removal leaves for a Maven command
    was observed to be a bare ``-am`` with no ``-pl`` for it to modify — the
    command the probe in this plan's own run showed, not a general claim about
    every Maven invocation. A default-scope answer means the fallback is never
    reached for a reactor root.
    """
    _write_reactor(tmp_path)

    result = _resolve_default_scope(tmp_path, 'test-compile')

    assert result['status'] == 'success', result
    assert result['executable'].endswith('--command-args "test-compile"')
    assert '-pl' not in result['executable']


def test_derive_verification_for_a_root_owned_pom_still_derives_verify(tmp_path: Path) -> None:
    """A change to the reactor root's own ``pom.xml`` still derives the root's ``verify``.

    The deliverable adds two canonicals to the root; it must not move the
    build-class derivation for the file the root owns.
    """
    _write_reactor(tmp_path)
    marshal = tmp_path / '.plan' / 'marshal.json'
    marshal.parent.mkdir(parents=True, exist_ok=True)
    marshal.write_text(json.dumps({'build': {'map': _ROOT_POM_BUILD_MAP}}), encoding='utf-8')

    result = cmd_derive_verification(_variant(_DERIVE_ARGS, project_dir=str(tmp_path), changed_artifacts='pom.xml'))

    assert result['status'] == 'success', result
    verbs = [command for command in result['commands'] if command.get('command') == 'verify']
    assert verbs, result
    assert verbs[0]['executable'].endswith('--command-args "verify"')
    assert verbs[0]['path'] == 'pom.xml'


def test_the_resolved_notation_publishes_the_scope_verb_the_arm_calls_next(tmp_path: Path) -> None:
    """The notation step 0 captures peers to a ``resolve-test-scope`` that ANSWERS.

    The arm's branch 1 calls that verb on the notation it took from the resolved
    executable, so an executable naming a skill without the verb would still
    reach the missing-verb degradation. Checking the help surface alone proves
    the parser registers the name, not that the verb resolves a real reactor —
    so this calls it over the fixture reactor and asserts the response the gate
    reads its routing branches from.
    """
    _write_reactor(tmp_path)
    result = _resolve_default_scope(tmp_path, 'module-tests')
    assert result['status'] == 'success', result
    assert _MAVEN_NOTATION in result['executable']

    scope = run_script(
        get_script_path('plan-marshall', 'build-maven', 'maven.py'),
        'resolve-test-scope',
        '--project-dir',
        str(tmp_path),
        '--changed-paths',
        'core/src/main/java/probe/CoreTest.java',
        cwd=str(tmp_path),
    )

    assert scope.returncode == 0, scope.stderr
    answer = parse_toon(scope.stdout)
    assert answer['status'] == 'success', answer
    assert answer['scoped_modules'] == ['core'], answer
    assert answer['whole_tree_available'] is True, answer


def test_a_persisted_maven_architecture_resolves_module_tests_at_default_scope(tmp_path: Path) -> None:
    """The PERSISTED architecture view resolves step 0 too.

    The consumer's read path is a live crawl; a ``project-architecture`` tree on
    disk is the resolver's fallback for a project whose checkout exposes no build
    files (the synthetic-project seam, which is also what test fixtures use). It
    is NOT a durability guarantee: ``derived.json`` is never the source of
    current state where a live crawl finds modules. Seeding it from a REAL
    discovery of a Maven reactor keeps the fixture honest: the persisted rows
    carry exactly the command map the shipped discovery emits, so the resolve is
    answered from a view a live crawl could also have produced.
    """
    source = tmp_path / 'source'
    _write_reactor(source)
    persisted = tmp_path / 'persisted'
    _persist_modules(persisted, discover_maven_modules(str(source)))

    result = _resolve_default_scope(persisted, 'module-tests')

    assert result['status'] == 'success', result
    assert result['executable'].endswith('--command-args "test"')
    assert _MAVEN_NOTATION in result['executable']


def test_a_module_without_tests_cascades_to_the_reactor_roots_run(tmp_path: Path) -> None:
    """A module with no test canonical of its own cascades to the root's whole-reactor run.

    This is a consumer-visible consequence of giving the root the canonical: the
    resolver's root cascade (`resolve_command`) now answers a test-less module
    with the whole reactor instead of ``Command not found``. The direction is
    coverage-increasing — the run can only execute more than asked, never less —
    and it is pinned here rather than left implicit.
    """
    source = tmp_path / 'source'
    _write_reactor(source)
    persisted = tmp_path / 'persisted'
    _persist_modules(persisted, discover_maven_modules(str(source)))

    result = cmd_resolve(_variant(_RESOLVE_ARGS, project_dir=str(persisted), module='plain'))

    assert result['status'] == 'success', result
    assert result['module'] == 'probe-parent'
    assert result['executable'].endswith('--command-args "test"')


def test_the_gate_record_names_an_unreadable_pom_as_its_cause() -> None:
    """An unreadable POM is a NAMED cause behind the gate's DEGRADED record.

    Discovery carries ``pom_error: pom_unreadable`` and grants no canonical, so the
    module-tests arm falls to branch 0. The gate document binds that token to the
    branch-0 WARNING and to the DEGRADED verdict, so a reader of the step record
    can tell a broken descriptor from a project that simply has no tests.
    """
    from conftest import MARKETPLACE_ROOT

    doc = (
        MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards' / 'pre-push-quality-gate.md'
    ).read_text(encoding='utf-8')
    marker = 'pom_error: pom_unreadable'
    assert marker in doc

    passage = doc[doc.index(marker) :]
    assert 'MUST name `pom_unreadable`' in passage
    assert 'module-tests DEGRADED' in doc
