#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the Maven ``resolve-test-scope`` verb.

The pre-push gate asks the resolved build skill for a scoped-test answer before
it decides between a scoped and a whole-tree ``module-tests`` run. ``build-maven``
published no such verb, so on every Maven project the gate took its DEGRADED path
and the scoped/whole-tree divergence class went un-gated.

The verb answers the same question ``build-pyproject`` answers, over Maven's own
shape: a reactor names its modules by directory, so a footprint path is owned by
the longest module directory that contains it — not by a
``marketplace/bundles/<b>`` segment. A path no module directory contains is
reported in ``unresolved_paths`` rather than silently counted as covered, which
routes the gate to the whole tree.
"""

from __future__ import annotations

import argparse
import copy
from unittest.mock import patch

import pytest
from toon_parser import parse_toon

from conftest import load_script_module, parse_ns

_scope_mod = load_script_module(
    'plan-marshall',
    'build-maven',
    '_maven_cmd_resolve_scope.py',
    'maven_resolve_scope_mod',
)
cmd_resolve_test_scope = _scope_mod.cmd_resolve_test_scope

#: The namespace maven.py's OWN parser yields for the verb, built once because
#: ``parse_ns`` re-executes the script module per call.
_SCOPE_ARGS: argparse.Namespace = parse_ns(
    'plan-marshall',
    'build-maven',
    'maven.py',
    'resolve-test-scope',
    '--changed-paths',
    'placeholder',
    register=False,
)

_GLOBS = ['**/*.java', '**/pom.xml', '**/*.md']


def _write_pom(directory, artifact_id, *, packaging='jar', modules=()):
    directory.mkdir(parents=True, exist_ok=True)
    module_block = ''
    if modules:
        module_block = (
            '    <modules>\n' + ''.join(f'        <module>{m}</module>\n' for m in modules) + '    </modules>\n'
        )
    (directory / 'pom.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<project xmlns="http://maven.apache.org/POM/4.0.0">\n'
        '    <modelVersion>4.0.0</modelVersion>\n'
        '    <groupId>com.example</groupId>\n'
        f'    <artifactId>{artifact_id}</artifactId>\n'
        '    <version>1.0.0-SNAPSHOT</version>\n'
        f'    <packaging>{packaging}</packaging>\n'
        f'{module_block}'
        '</project>\n',
        encoding='utf-8',
    )
    if packaging == 'jar':
        for relative in ('src/main/java/com/example/Thing.java', 'src/test/java/com/example/ThingTest.java'):
            target = directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('package com.example;\n', encoding='utf-8')


@pytest.fixture
def reactor(tmp_path):
    """A two-module Maven reactor: modules ``alpha`` and ``beta`` under a root pom."""
    _write_pom(tmp_path, 'parent-project', packaging='pom', modules=('alpha', 'beta'))
    _write_pom(tmp_path / 'alpha', 'alpha')
    _write_pom(tmp_path / 'beta', 'beta')
    return tmp_path


def _args(*, changed_paths=None, plan_id=None, project_dir=None):
    derived = copy.copy(_SCOPE_ARGS)
    derived.changed_paths = changed_paths
    derived.plan_id = plan_id
    derived.project_dir = project_dir
    return derived


def _run(capsys, reactor, *, changed_paths):
    with patch('extension_base._read_build_map_globs', return_value=_GLOBS):
        rc = cmd_resolve_test_scope(_args(changed_paths=changed_paths, project_dir=str(reactor)))
    assert rc == 0
    return parse_toon(capsys.readouterr().out)


def test_two_modules_yield_that_population(capsys, reactor):
    """A footprint in two reactor modules names exactly those two modules."""
    answer = _run(
        capsys,
        reactor,
        changed_paths=('alpha/src/main/java/com/example/Thing.java,beta/src/main/java/com/example/Thing.java'),
    )

    assert answer['status'] == 'success'
    assert answer['scoped_modules'] == ['alpha', 'beta']
    assert answer['divergence_possible'] is True
    assert answer['unresolved_paths'] == []
    assert answer['whole_tree_available'] is True


def test_a_single_module_answers_that_module(capsys, reactor):
    """Each module in isolation resolves to itself as the scoped target."""
    for module in ('alpha', 'beta'):
        answer = _run(capsys, reactor, changed_paths=f'{module}/src/main/java/com/example/Thing.java')

        assert answer['scoped_modules'] == [module]
        assert answer['recommended_target'] == module
        assert answer['divergence_possible'] is False


def test_a_path_outside_every_module_is_reported_unresolved(capsys, reactor):
    """A path no module directory contains is reported, and routes the whole tree."""
    answer = _run(capsys, reactor, changed_paths='alpha/src/main/java/com/example/Thing.java,docs/notes.md')

    assert answer['scoped_modules'] == ['alpha']
    assert answer['unresolved_paths'] == ['docs/notes.md']
    assert answer['divergence_possible'] is True
    assert answer['recommended_target'] is None


def test_a_root_level_file_is_not_owned_by_a_module(capsys, reactor):
    """The reactor root is not a module every path belongs to."""
    answer = _run(capsys, reactor, changed_paths='pom.xml')

    assert answer['scoped_modules'] == []
    assert answer['unresolved_paths'] == ['pom.xml']
    assert answer['divergence_possible'] is True


def test_an_empty_changed_paths_list_is_refused(capsys, reactor):
    """A supplied-but-blank footprint is a caller error, not a no-op scope."""
    with patch('extension_base._read_build_map_globs', return_value=_GLOBS):
        rc = cmd_resolve_test_scope(_args(changed_paths=' , ', project_dir=str(reactor)))

    answer = parse_toon(capsys.readouterr().out)
    assert rc == 2
    assert answer['status'] == 'error'
    assert answer['error'] == 'empty_changed_paths'


def test_a_footprint_source_is_required(capsys):
    """Neither a task footprint nor a plan id means no question was asked."""
    with patch('extension_base._read_build_map_globs', return_value=_GLOBS):
        rc = cmd_resolve_test_scope(_args(project_dir=None))

    answer = parse_toon(capsys.readouterr().out)
    assert rc == 2
    assert answer['status'] == 'error'
    assert answer['error'] == 'footprint_source_required'


def test_an_unresolvable_plan_footprint_fails_closed(capsys, reactor):
    """An unresolvable whole-plan footprint cannot claim a scoped run is safe."""
    with (
        patch('extension_base._read_build_map_globs', return_value=_GLOBS),
        patch('extension_base._resolve_plan_footprint', return_value=None),
    ):
        rc = cmd_resolve_test_scope(_args(plan_id='some-plan', project_dir=str(reactor)))

    answer = parse_toon(capsys.readouterr().out)
    assert rc == 0
    assert answer['status'] == 'success'
    assert answer['footprint_resolvable'] is False
    assert answer['divergence_possible'] is True
    assert answer['recommended_target'] is None
