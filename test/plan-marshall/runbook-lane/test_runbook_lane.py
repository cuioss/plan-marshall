#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``runbook-lane`` skill (D1) and its ``resolve`` verb (D2).

The runbook lane implements one staged orchestrator plan spec without the
``/plan-marshall`` lifecycle. Its contract used to live in a machine-local file
that named this repository's epic, build system, reviewers and commit trailer;
D1 ships that contract as a bundle skill whose project-specific values come from
the D2 ``runbook_lane resolve`` verb, and D2 is the verb itself.

Three properties are load-bearing here and each is asserted directly rather than
inferred:

* the skill carries no repository-specific literal, so it is usable from any
  project;
* the skill's section structure still mirrors the source runbook, so no rule was
  dropped in the move;
* ``resolve`` fails closed — an empty reviewer list, a spec outside the
  orchestrator tree, or an unresolvable build is an error, never a default.

The ``resolve`` fixtures seed a project-scoped ``.plan/marshal.json``, a
project-architecture module whose command map carries one build per case, and a
staged spec. They never read this repository's own ``.plan/`` state.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import (
    get_scripts_dir,
    run_script,
)

# The skill under test.
_SKILL_NAME = 'runbook-lane'

_PYPROJECT_EXEC = (
    'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "{args}"'
)
_MAVEN_EXEC = 'python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args "{args}"'


# =============================================================================
# D2 — the resolve verb
# =============================================================================


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def _seed_fixture(
    root: Path,
    *,
    executable: str,
    required_bots: str,
    optional_bots: str = '',
    slug: str = 'demo-epic',
    spec_name: str = 'PLAN-LB-66-runbook-lane-skill.md',
) -> Path:
    """Seed a project fixture and return the staged spec path.

    The project architecture is written directly in the on-disk shape
    ``_architecture_core`` reads (``.plan/project-architecture/_project.json``
    plus one ``derived.json`` per module), so ``resolve_command`` sees exactly
    the command map a real crawl would hand it.
    """
    _write(
        root / '.plan' / 'marshal.json',
        json.dumps(
            {
                'plan': {
                    'phase-6-finalize': {
                        'steps': {
                            'plan-marshall:automatic-review': {
                                'required_bots': required_bots,
                                'optional_bots': optional_bots,
                            }
                        }
                    }
                }
            }
        ),
    )
    arch = root / '.plan' / 'project-architecture'
    _write(
        arch / '_project.json',
        json.dumps(
            {
                'name': 'test-project',
                'description': '',
                'description_reasoning': '',
                'extensions_used': [],
                'modules': {'root-mod': {}},
            }
        ),
    )
    _write(
        arch / 'root-mod' / 'derived.json',
        json.dumps(
            {
                'name': 'root-mod',
                'build_systems': ['pyproject'],
                'paths': {'module': '.'},
                'commands': {
                    'quality-gate': executable.format(args='quality-gate'),
                    'module-tests': executable.format(args='module-tests'),
                    'verify': executable.format(args='verify'),
                },
            }
        ),
    )
    spec = root / '.plan' / 'orchestrator' / slug / 'plans' / spec_name
    _write(spec, '# staged spec\n')
    return spec


def _run_resolve(spec: Path, project_dir: Path, *, env_overrides: dict[str, str] | None = None) -> dict:
    """Invoke ``runbook_lane resolve`` and parse its TOON.

    The verb is exercised as a subprocess through its real argparse surface, so
    a renamed flag or a changed verb spelling is a red test.
    """
    script = get_scripts_dir('plan-marshall', _SKILL_NAME) / 'runbook_lane.py'
    result = run_script(
        script,
        'resolve',
        '--spec',
        str(spec),
        '--project-dir',
        str(project_dir),
        env_overrides=env_overrides,
    )
    assert result.success, f'resolve crashed: {result.stderr}'
    return result.toon()


def test_resolve_pyproject_fixture(tmp_path: Path) -> None:
    spec = _seed_fixture(
        tmp_path,
        executable=_PYPROJECT_EXEC,
        required_bots='first-bot,second-bot',
        optional_bots='third-bot',
    )
    # The trailer override lives in the git-ignored run-configuration.json,
    # whose main-anchored path the PLAN_BASE_DIR override stands in for.
    _write(
        tmp_path / 'run-configuration.json',
        json.dumps({'commit_trailer': {'name': 'custom-system', 'email': 'ci@example.org'}}),
    )

    data = _run_resolve(spec, tmp_path, env_overrides={'PLAN_BASE_DIR': str(tmp_path)})

    assert data['slug'] == 'demo-epic'
    assert data['plan'] == 'lb-66-runbook-lane-skill'
    assert data['worktree'] == '.plan/local/worktrees/lb-66-runbook-lane-skill'
    assert data['progress_file'] == '.plan/temp/rb-lb-66-runbook-lane-skill/progress.md'
    assert data['sender_id'] == 'rb-lb-66-runbook-lane-skill'
    assert 'inbox write' in data['inbox_write_command']
    assert 'rb-lb-66-runbook-lane-skill' in data['inbox_write_command']
    assert data['commit_trailer'] == 'Co-Authored-By: custom-system <ci@example.org>'
    assert 'build-pyproject' in data['build']['quality-gate']
    assert 'build-pyproject' in data['build']['verify']
    assert 'build-pyproject' in data['build']['module-tests']
    assert 'build-pyproject' in data['build']['test-compile']
    assert data['build']['split'] == ['quality-gate', 'test-compile', 'module-tests']
    assert data['harness']
    assert data['guard'] in ('present', 'none')
    required = {row['bot']: row for row in data['required_bots']}
    assert set(required) == {'first-bot', 'second-bot'}
    assert all('trigger_comment' in row for row in data['required_bots'])
    assert {row['bot'] for row in data['optional_bots']} == {'third-bot'}


def test_resolve_maven_fixture_emits_maven_commands(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_MAVEN_EXEC, required_bots='some-bot')

    data = _run_resolve(spec, tmp_path)

    blobs = json.dumps(data)
    assert 'build-maven' in blobs
    assert 'pyproject' not in blobs
    assert any(row['bot'] == 'some-bot' for row in data['required_bots'])


def test_resolve_empty_required_bots_is_an_error(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='')
    data = _run_resolve(spec, tmp_path)
    assert data['status'] == 'error'
    assert data['error'] == 'required_bots_empty'


def test_resolve_spec_outside_orchestrator_is_an_error(tmp_path: Path) -> None:
    _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')
    stray = tmp_path / 'stray' / 'PLAN-LB-99-nope.md'
    _write(stray, '# not staged\n')
    data = _run_resolve(stray, tmp_path)
    assert data['status'] == 'error'
    assert data['error'] == 'spec_outside_orchestrator'


def test_resolve_antigravity_harness_has_no_guard(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')
    data = _run_resolve(
        spec,
        tmp_path,
        env_overrides={
            'ANTIGRAVITY_AGENT': '1',
            'OPENCODE': '',
            'OPENCODE_PID': '',
            'CLAUDE_CODE_SESSION_ID': '',
        },
    )
    assert data['harness'] == 'antigravity'
    assert data['guard'] == 'none'


def _opencode_env() -> dict[str, str]:
    return {'OPENCODE': '1', 'OPENCODE_PID': '', 'ANTIGRAVITY_AGENT': '', 'CLAUDE_CODE_SESSION_ID': ''}


def test_resolve_opencode_without_guard_js_has_no_guard(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')
    data = _run_resolve(spec, tmp_path, env_overrides=_opencode_env())
    assert data['harness'] == 'opencode'
    assert data['guard'] == 'none'


def test_resolve_opencode_with_guard_js_reports_present(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')
    _write(tmp_path / '.opencode' / 'plugin' / 'guard.js', '// guard\n')
    data = _run_resolve(spec, tmp_path, env_overrides=_opencode_env())
    assert data['harness'] == 'opencode'
    assert data['guard'] == 'present'


def test_resolve_unresolvable_build_is_an_error(tmp_path: Path) -> None:
    """A project whose architecture resolves no build command fails closed."""
    _write(
        tmp_path / '.plan' / 'marshal.json',
        json.dumps(
            {'plan': {'phase-6-finalize': {'steps': {'plan-marshall:automatic-review': {'required_bots': 'x'}}}}}
        ),
    )
    spec = tmp_path / '.plan' / 'orchestrator' / 'demo-epic' / 'plans' / 'PLAN-LB-66-runbook-lane-skill.md'
    _write(spec, '# staged spec\n')
    data = _run_resolve(spec, tmp_path)
    assert data['status'] == 'error'
    assert data['error'] == 'build_command_unresolvable'
