#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``runbook-lane`` skill (D1, D3–D6) and its ``resolve`` verb (D2, D4, D6).

The runbook lane implements one staged orchestrator plan spec without the
``/plan-marshall`` lifecycle. Its contract used to live in a machine-local file
that named this repository's epic, build system, reviewers and commit trailer;
the skill now carries the contract and every project-specific value comes from
the ``runbook_lane resolve`` verb.

Five properties are load-bearing here and each is asserted directly rather than
inferred:

* the skill carries no repository-specific literal, so it is usable from any
  project;
* the merge gate's standing review authorization, the persona standards and the
  per-deliverable skill declarations are present as written;
* the restored rule set survives at RULE granularity, not merely as headings;
* ``resolve`` fails closed — an empty reviewer list, a spec outside the
  orchestrator tree, an unresolvable build, or a named skill that is not
  installed is an error, never a default;
* the build classifier and the two target emitters answer per the project's own
  footprint rule and the targets' own tool vocabulary.

The ``resolve`` fixtures seed a project-scoped ``.plan/marshal.json``, a
project-architecture module whose command map carries one build per case, and a
staged spec. They never read this repository's own ``.plan/`` state.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import json
import re
import shutil
import socket
import sqlite3
import struct
import tempfile
import threading
from pathlib import Path
from typing import Any

from conftest import (
    MARKETPLACE_ROOT,
    PROJECT_ROOT,
    get_script_path,
    get_scripts_dir,
    load_script_module,
    run_script,
)

# The skill under test. Everything D1 asserts is read from these paths.
_SKILL_NAME = 'runbook-lane'
_SKILL_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / _SKILL_NAME

#: The eight repository-specific literals the shipped skill must not contain.
_FORBIDDEN_LITERALS = (
    'live-blockers',
    'PLAN-LB',
    'build-pyproject',
    'pyproject_build',
    'cuioss-review-bot',
    'coderabbit',
    'sourcery',
    'noreply@cuioss.de',
)

#: The source runbook's top-level headings. Quoted as fixed strings on purpose:
#: the test must never read ``.plan/local`` — the lane's source file is
#: machine-local and absent from a fresh clone.
_SOURCE_HEADINGS = (
    '## 0. Input',
    '## 0a. Progress file and resume (do this first, every session)',
    '## 1. Rules (every one binds; breaking one fails the run)',
    '## 2. Set up the worktree',
    '## 3. Implement, deliverable by deliverable',
    '## 4. Build gate',
    '## 5. Self-review before the PR',
    '## 6. Pull request and reviews',
    '## 7. Merge gate',
    '## 8. Landing message (the last step, after the merge)',
)

#: The wording a harness without a tool-call guard must produce.
_UNENFORCED_GUARD_WORDING = 'guard: none on this harness (unenforced)'

_PYPROJECT_EXEC = (
    'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "{args}"'
)


# =============================================================================
# D1 — the skill carries the lane contract
# =============================================================================


def _skill_files() -> list[Path]:
    return sorted(p for p in _SKILL_DIR.rglob('*') if p.is_file())


def test_skill_exists_and_is_user_invocable() -> None:
    skill_md = _SKILL_DIR / 'SKILL.md'
    assert skill_md.is_file(), f'expected {skill_md}'
    text = skill_md.read_text(encoding='utf-8')
    assert text.startswith('---'), 'SKILL.md must open with YAML frontmatter'
    assert 'name: runbook-lane' in text
    assert 'user-invocable: true' in text


def test_skill_passes_plugin_doctor() -> None:
    """The skill satisfies the checks plugin-doctor owns for a skill document.

    The whole-tree plugin-doctor gate is exercised by the repository's own
    ``quality-gate`` (which runs it) and therefore by CI's ``verify`` job; invoking
    that tree-wide gate from inside the suite was both slow and, under the full
    suite's contention, able to crash plugin-doctor's own tree walker — a
    false negative about the skill. What this test pins is the part that belongs
    to the skill document itself: the frontmatter plugin-doctor requires, the
    canonical-invocations block it demands of a skill that owns an in-scope
    script, the exit-code convention it demands of an executor-invoking document,
    and the parsed-shape rules for its fenced blocks.
    """
    text = (_SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8')

    assert text.startswith('---\n'), 'frontmatter must open the document'
    assert '## Canonical invocations' in text
    assert '### resolve' in text
    assert 'exit-code-convention.md' in text

    # Every fenced block declares a language (the ``fenced-code-no-language`` rule).
    fences = [line for line in text.splitlines() if line.startswith('```')]
    assert len(fences) % 2 == 0, 'unbalanced fenced block'
    for opening in fences[0::2]:
        assert opening != '```', 'a fenced block opens with no language info-string'


def test_skill_contains_no_repository_specific_literal() -> None:
    files = _skill_files()
    assert files, f'no files found under {_SKILL_DIR}'
    offenders: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding='utf-8').lower()
        except UnicodeDecodeError:
            continue
        for literal in _FORBIDDEN_LITERALS:
            if literal.lower() in text:
                offenders.append(f'{path.relative_to(_SKILL_DIR)}: {literal}')
    assert not offenders, f'repository-specific literals found: {offenders}'


def test_skill_sections_mirror_the_source_runbook() -> None:
    text = (_SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8')
    missing = [heading for heading in _SOURCE_HEADINGS if heading not in text]
    assert not missing, f'source runbook sections dropped from the skill: {missing}'


def test_skill_states_the_unenforced_guard_wording() -> None:
    text = (_SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8')
    assert _UNENFORCED_GUARD_WORDING in text


def test_skill_is_registered_in_plugin_json() -> None:
    plugin = json.loads(
        (MARKETPLACE_ROOT / 'plan-marshall' / '.claude-plugin' / 'plugin.json').read_text(encoding='utf-8')
    )
    assert './skills/runbook-lane' in plugin['skills']


# -----------------------------------------------------------------------------
# D1 — the standing review authorization in the merge gate
# -----------------------------------------------------------------------------


def _skill_text() -> str:
    return str((_SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8'))


def _section(heading: str) -> str:
    """Return one ``## `` section of the skill, from *heading* to the next one.

    Whitespace-normalised, so an assertion is about the wording rather than about
    where the author happened to wrap a line.
    """
    text = _skill_text()
    start = text.index(heading)
    rest = text[start + len(heading) :]
    end = rest.find('\n## ')
    return ' '.join((heading + (rest if end == -1 else rest[:end])).split())


def _sentences(text: str) -> list[str]:
    """Split whitespace-normalised prose into sentences at ``.``/``!``/``?``."""
    return [part.strip() for part in re.split(r'(?<=[.!?])\s+', text) if part.strip()]


#: The four conditions the standing authorization replaces "reviewed the current
#: head" with. Each is a distinct requirement, so each is asserted separately.
_STANDING_CONDITIONS = (
    'a qualifying review exists',
    'every finding is handled',
    'it was re-triggered once after the last push',
    'every other gate condition holds on the current head',
)


def test_merge_gate_names_the_four_standing_authorization_conditions() -> None:
    gate = _section('## 7. Merge gate')
    for condition in _STANDING_CONDITIONS:
        assert condition in gate, f'the merge gate does not name the condition {condition!r}'


def test_quota_policy_is_conditional_on_no_qualifying_review() -> None:
    gate = _section('## 7. Merge gate')
    assert 'applies only while no qualifying review exists' in gate


def test_standing_authorization_scope_excludes_non_quota_limited_reviewers() -> None:
    gate = _section('## 7. Merge gate')
    assert 'never applies to a reviewer that is not quota-limited' in gate


def test_landing_report_requires_the_standing_authorization_evidence() -> None:
    landing = _section('## 8. Landing message (the last step, after the merge)')
    assert 'the head it reviewed' in landing
    assert 'the current head' in landing
    assert 'how it was handled' in landing


def test_standing_authorization_stays_repository_neutral() -> None:
    gate = _section('## 7. Merge gate')
    # Anchored to the new section so this assertion fails before the change and
    # then guards the added wording against a repository-specific literal.
    assert 'standing review authorization' in gate.lower()
    lowered = gate.lower()
    for literal in _FORBIDDEN_LITERALS:
        assert literal.lower() not in lowered, f'repository-specific literal in the merge gate: {literal}'


# -----------------------------------------------------------------------------
# PLAN-LB-73 — each rule is stated once, and a clean summary review qualifies
# -----------------------------------------------------------------------------


def _branch_row() -> str:
    """Return the ``| branch |`` row of the section 0 field table."""
    for line in _raw_section('## 0. Input').splitlines():
        if line.startswith('| branch |'):
            return ' '.join(line.split())
    raise AssertionError('section 0 carries no branch row')


def test_branch_rule_states_one_set_of_prefixes() -> None:
    """The row names ONE set: the canonical prefixes PLUS the project's own.

    A row that calls the canonical set closed and then requires the chosen
    prefix to be declared by ``working_prefixes`` makes the project's list the
    sole source, which is the contradiction this closes.
    """
    row = _branch_row()

    for prefix in ('feature/', 'fix/', 'chore/'):
        assert prefix in row, f'the branch row drops the canonical prefix {prefix}'
    assert "the project's configured `working_prefixes`" in row
    assert 'plus' in row, 'the branch row does not join the two sets into one'
    assert 'must be one the project' not in row, 'the row still makes working_prefixes the sole source'
    assert 'only extension' not in row, 'the row still calls working_prefixes a mere extension'
    assert 'own set wins' not in row, 'the row lets the project set replace the canonical prefixes'


def test_progress_template_carries_the_order_slot() -> None:
    """The §0a template records the evidence ORDER, not a bare "failed before fix"."""
    progress = _raw_section('## 0a. Progress file and resume (do this first, every session)')
    template = next(
        (block for block in _fenced_blocks(progress) if 'setup: worktree' in block),
        None,
    )
    assert template is not None, 'section 0a carries no progress template'
    test_lines = [line for line in template.splitlines() if line.startswith('D{n} test:')]
    assert test_lines, 'the template carries no per-Done-when test line'
    for line in test_lines:
        assert 'order' in line, f'the template line omits the order slot: {line}'
        assert 'failed before fix' not in line, f'the template words every order as a pre-fix failure: {line}'
    assert 'test-first' in template and 'mutation-after' in template and 'none' in template


def test_rules_state_the_order_grading_once() -> None:
    """§1 owns the grading rule; §3 and §6 refer to it instead of restating it."""
    rules = _section('## 1. Rules (every one binds; breaking one fails the run)')
    for phrase in ('`test-first` is met', '`mutation-after` is met', '`none`', 'not met as written'):
        assert phrase in rules, f'§1 does not state the grading rule for {phrase!r}'
    assert 'reserved' in rules, '§1 does not reserve the fail-first wording for test-first'

    for heading in ('## 3. Implement, deliverable by deliverable', '## 6. Pull request and reviews'):
        section = _section(heading)
        assert 'order' in section, f'{heading} does not refer to the order rule'
        assert 'not met as written' not in section, f'{heading} restates the §1 grading rule'
        assert '`test-first` is met' not in section, f'{heading} restates the §1 grading rule'

    implementation = _section('## 3. Implement, deliverable by deliverable')
    assert 'test-first' not in implementation, '§3 still mandates test-first as the only order'


def test_pr_body_requires_the_failing_run_only_for_orders_that_have_one() -> None:
    pr_body = _section('## 6. Pull request and reviews')
    assert 'failing run' in pr_body
    assert 'only where' in pr_body, '§6 still requires a failing run for every order'
    assert 'not `none`' in pr_body, '§6 does not exempt the `none` order'


def test_build_gate_states_the_docs_only_test_compile_rule() -> None:
    gate = _section('## 4. Build gate')
    assert 'docs-only head' in gate, '§4 does not state the rule for a docs-only head'
    assert 'no `module-tests` and no `test-compile`' in gate, '§4 does not say whether test-compile applies'


def test_merge_gate_counts_the_marker_bearing_summary_comment() -> None:
    """A clean CodeRabbit review is published only as a marker-bearing summary comment."""
    gate = _section('## 7. Merge gate')

    assert 'marker-bearing summary comment' in gate
    for field in ('sourceCommitId', 'coveredCommitId', 'kind=reviewed'):
        assert field in gate, f'the gate does not name the summary marker field {field}'
    assert 'not quota-limited' in gate and 'current head' in gate


#: The merge-gate state PLAN-LB-72 shipped: both required bots reported clean,
#: ``ci pr reviews`` is empty, and CodeRabbit's clean-review summary comment
#: covers the head. A clean review has no formal review body, so the comment is
#: the only artifact that names the reviewed head.
_PLAN_LB_72_GATE_STATE: dict[str, Any] = {
    'head': 'cf28a05db',
    'review_count': 0,
    'reviews': [],
    'summary_comments': [
        {
            'author': 'coderabbitai',
            'body': (
                '<!-- final_review_risk_coverage:'
                '{"sourceCommitId":"cf28a05db","coveredCommitId":"cf28a05db",'
                '"kind":"reviewed"} -->'
            ),
        }
    ],
}


def _summary_review_state_qualifies(state: dict[str, Any]) -> bool:
    """Whether a pull request's review state satisfies the summary-comment leg.

    Derived from the state ALONE: a formal review is absent, and one summary
    comment carries the marker whose covered commit is the head and whose kind
    is ``reviewed``.
    """
    if state['review_count'] or state['reviews']:
        return False
    for comment in state['summary_comments']:
        marker = re.search(r'final_review_risk_coverage:(\{.*?\})', comment['body'])
        if marker is None:
            continue
        fields = json.loads(marker.group(1))
        if fields.get('coveredCommitId') == state['head'] and fields.get('kind') == 'reviewed':
            return True
    return False


def test_the_plan_lb_72_merge_gate_state_qualifies_as_a_review() -> None:
    assert _PLAN_LB_72_GATE_STATE['review_count'] == 0, 'the fixture must model an empty ci pr reviews'
    assert _summary_review_state_qualifies(_PLAN_LB_72_GATE_STATE), 'the fixture is not a qualifying state'

    gate = _section('## 7. Merge gate')
    # The text must accept exactly the shape the fixture models.
    assert 'a qualifying review exists' in gate
    assert 'marker-bearing summary comment' in gate
    assert '`ci pr reviews`' in gate, 'the formal-review leg is gone'


def test_merge_gate_question_rereads_the_review_surfaces() -> None:
    gate = _section('## 7. Merge gate')

    assert '`ci pr comments`' in gate and '`ci pr reviews`' in gate
    assert 'in the same step as the question' in gate
    assert 'immediately before the enqueue' in gate
    assert 'invalidate' in gate, 'a review that arrived after the question does not invalidate the answer'


def test_merge_gate_blocks_on_an_open_thread_or_outside_diff_finding() -> None:
    gate = _section('## 7. Merge gate')

    assert 'unresolved review thread' in gate
    assert 'outside-diff' in gate
    assert 'blocks the standing authorization' in gate


def test_base_moved_merge_carries_the_commit_trailer() -> None:
    gate = _section('## 7. Merge gate')

    assert '{commit_trailer}' in gate, 'the base-moved merge commit carries no trailer'
    assert 'merge origin/{base_branch}' in gate
    assert '-m "' in gate, 'the merge instruction carries no message argument'


# =============================================================================
# D2 — the resolve verb
# =============================================================================


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def _seed_fixture(
    root: Path,
    *,
    required_bots: str,
    executable: str = _PYPROJECT_EXEC,
    optional_bots: str = '',
    slug: str = 'demo-epic',
    spec_name: str = 'PLAN-LB-66-runbook-lane-skill.md',
    spec_text: str = '# staged spec\n',
    base_branch: str | None = None,
    module_path: str = '.',
    documentation_path: str = 'doc',
    documentation_files: tuple[str, ...] = ('doc/developer/build.adoc', 'doc/user/usage.md'),
    commands: dict[str, str] | None = None,
    build_systems: tuple[str, ...] = ('pyproject',),
    credentials_config: dict[str, Any] | None = None,
) -> Path:
    """Seed a project fixture and return the staged spec path.

    The project architecture is written directly in the on-disk shape
    ``_architecture_core`` reads (``.plan/project-architecture/_project.json``
    plus one ``derived.json`` per module), so ``resolve_command`` sees exactly
    the command map a real crawl would hand it.

    ``commands`` overrides the root module's command map verbatim, so a test can
    seed the per-canonical forms discovery writes for a real build system
    (Maven's ``--command-args "verify -Ppre-commit"``, pyproject's
    ``--command-args "quality-gate"``) instead of one template applied to every
    canonical. ``executable`` is the template the DEFAULT map is built from; it
    is unused when ``commands`` is supplied. ``build_systems`` carries the
    marker the build system's own discovery writes, so a Maven fixture is not
    labelled pyproject.
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
                },
                **({'project': {'default_base_branch': base_branch}} if base_branch else {}),
                **({'credentials_config': credentials_config} if credentials_config is not None else {}),
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
                'modules': {'root-mod': {}, 'documentation': {}},
            }
        ),
    )
    _write(
        arch / 'root-mod' / 'derived.json',
        json.dumps(
            {
                'name': 'root-mod',
                'build_systems': list(build_systems),
                'paths': {'module': module_path},
                'commands': commands
                if commands is not None
                else {
                    # The root map pyproject discovery emits for a module WITH
                    # tests. ``test-compile`` is deliberately absent: pyproject's
                    # discovery never publishes it, and a fixture that invented
                    # one would hide the lane hard-requiring a canonical the
                    # project does not have.
                    'quality-gate': executable.format(args='quality-gate'),
                    'module-tests': executable.format(args='module-tests'),
                    'verify': executable.format(args='verify'),
                },
            }
        ),
    )
    # The project's prose surface: the architecture's own non-building classes, so
    # the classifier derives them from project data rather than from a literal. The
    # `build_systems` marker is what the documentation extension writes on a
    # prose-only module.
    _write(
        arch / 'documentation' / 'derived.json',
        json.dumps(
            {
                'name': 'documentation',
                'build_systems': ['documentation'],
                'paths': {'module': documentation_path},
                'files': {'doc': list(documentation_files)},
            }
        ),
    )
    spec = root / '.plan' / 'orchestrator' / slug / 'plans' / spec_name
    _write(spec, spec_text)
    return spec


def _run_resolve(spec: Path, project_dir: Path, *, env_overrides: dict[str, str] | None = None) -> dict:
    """Invoke ``runbook_lane resolve`` and parse its TOON.

    The verb is exercised as a subprocess through its real argparse surface, so
    a renamed flag or a changed verb spelling is a red test.

    ``PLAN_MARSHALL_HOME`` is isolated inside the fixture project by default: the
    verb reports the build server's preflight state, and a test must decide that
    state (see :class:`_BuildServerState`) rather than read the machine's real
    registry and daemon.
    """
    env = {'PLAN_MARSHALL_HOME': str(project_dir / '.machine-home')}
    if env_overrides:
        env.update(env_overrides)
    script = get_scripts_dir('plan-marshall', _SKILL_NAME) / 'runbook_lane.py'
    result = run_script(
        script,
        'resolve',
        '--spec',
        str(spec),
        '--project-dir',
        str(project_dir),
        env_overrides=env,
    )
    assert result.success, f'resolve crashed: {result.stderr}'
    data: dict[str, Any] = result.toon()
    return data


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
    # pyproject publishes no ``test-compile``, so the lane must not invent one.
    assert 'test-compile' not in data['build']
    assert data['build']['split'] == ['quality-gate', 'module-tests']
    assert data['harness']
    assert data['guard'] in ('present', 'none')
    required = {row['bot']: row for row in data['required_bots']}
    assert set(required) == {'first-bot', 'second-bot'}
    assert all('trigger_comment' in row for row in data['required_bots'])
    assert {row['bot'] for row in data['optional_bots']} == {'third-bot'}


def test_resolve_maven_fixture_emits_maven_commands(tmp_path: Path) -> None:
    spec = _seed_fixture(
        tmp_path, build_systems=('maven',), required_bots='some-bot', commands=_maven_architecture_commands()
    )

    data = _run_resolve(spec, tmp_path)

    blobs = json.dumps(data)
    assert 'build-maven' in blobs
    assert 'pyproject' not in blobs
    assert any(row['bot'] == 'some-bot' for row in data['required_bots'])


def _maven_architecture_commands() -> dict[str, str]:
    """The command map discovery writes for the ROOT Maven module with tests.

    Mirrors ``_maven_cmd_discover._build_commands`` for the root module
    (``relative_path`` empty, so ``pl_arg`` is empty), rendered by the shared
    ``build_canonical_commands``: the Maven wrapper takes the COMPLETE Maven
    arguments inside ``--command-args``, and ``quality-gate`` is the
    profile-overridden verify. The ``-pl {module} -am`` forms belong to non-root
    modules and never to the root, so seeding them would be a fixture no crawl
    produces.
    """
    prefix = 'python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args'
    return {
        'quality-gate': f'{prefix} "verify -Ppre-commit"',
        'module-tests': f'{prefix} "test"',
        'test-compile': f'{prefix} "test-compile"',
        'verify': f'{prefix} "verify"',
    }


def test_resolve_maven_quality_gate_is_the_architecture_command(tmp_path: Path) -> None:
    commands = _maven_architecture_commands()
    spec = _seed_fixture(tmp_path, build_systems=('maven',), required_bots='some-bot', commands=commands)

    data = _run_resolve(spec, tmp_path)

    assert data['status'] == 'success'
    assert data['build']['quality-gate'] == commands['quality-gate']
    assert data['build']['verify'] == commands['verify']
    # The composed form is gone: a bare canonical handed to the Maven wrapper is
    # read as an unknown lifecycle phase. Only the two canonicals whose Maven
    # arguments DIFFER from their own name can witness that — for ``verify`` and
    # ``test-compile`` the canonical name IS the Maven goal, so the composed and
    # the architecture form coincide there by construction.
    blob = json.dumps(data)
    for canonical in ('quality-gate', 'module-tests'):
        assert f'--command-args \\"{canonical}\\"' not in blob


def test_resolve_maven_module_tests_and_test_compile_are_the_architecture_commands(tmp_path: Path) -> None:
    commands = _maven_architecture_commands()
    spec = _seed_fixture(tmp_path, build_systems=('maven',), required_bots='some-bot', commands=commands)

    data = _run_resolve(spec, tmp_path)

    assert data['build']['module-tests'] == commands['module-tests']
    assert data['build']['test-compile'] == commands['test-compile']
    assert data['build']['split'] == ['quality-gate', 'test-compile', 'module-tests']


def test_resolve_unresolvable_gate_canonical_fails_closed_and_names_it(tmp_path: Path) -> None:
    """A project with NO gate canonical is a named error, and no build map.

    ``quality-gate`` and ``verify`` are the gate; each build system publishes
    them conditionally, so the lane refuses only when BOTH are absent. The error
    names the pair it could not resolve — there is no composed fall-back and no
    default build.
    """
    commands = _maven_architecture_commands()
    del commands['quality-gate']
    del commands['verify']
    spec = _seed_fixture(tmp_path, build_systems=('maven',), required_bots='some-bot', commands=commands)

    data = _run_resolve(spec, tmp_path)

    assert data['status'] == 'error'
    assert data['error'] == 'build_command_unresolvable'
    assert data['canonicals'] == 'quality-gate, verify'
    assert 'build' not in data


def test_resolve_accepts_a_project_that_publishes_only_one_gate_canonical(tmp_path: Path) -> None:
    """npm publishes ``quality-gate`` only for a lint script and ``verify`` only
    for a test script, so a project with tests and no lint has one gate.

    Failing closed here would make the lane unable to run in a real npm consumer
    repository, which is the plan's whole objective; the lane gates with the one
    canonical the project publishes.
    """
    commands = {
        'verify': 'python3 .plan/execute-script.py plan-marshall:build-npm:npm run --command-args "run test"',
        'module-tests': 'python3 .plan/execute-script.py plan-marshall:build-npm:npm run --command-args "run test"',
    }
    spec = _seed_fixture(tmp_path, build_systems=('npm',), required_bots='some-bot', commands=commands)

    data = _run_resolve(spec, tmp_path)

    assert data['status'] == 'success', data
    assert set(data['build']) == {'verify', 'module-tests', 'split'}
    assert data['build']['split'] == ['module-tests']


def test_resolve_pyproject_commands_stay_on_the_pyproject_wrapper(tmp_path: Path) -> None:
    """Preservation guard: the real pyproject map resolves through its wrapper.

    The map is the one ``_pyproject_cmd_discover._build_commands`` emits for a
    root module with tests — no ``test-compile``. The lane resolves only its OWN
    canonicals out of that larger map (``clean``, ``compile`` and ``coverage``
    belong to other consumers), so the assertion is per lane canonical. A lane
    that hard-required ``test-compile`` would fail here, which is the
    consumer-repository defect restated for the pyproject wrapper.
    """
    commands = {
        canonical: _PYPROJECT_EXEC.format(args=canonical)
        for canonical in ('clean', 'compile', 'quality-gate', 'verify', 'module-tests', 'coverage')
    }
    spec = _seed_fixture(tmp_path, required_bots='some-bot', commands=commands)

    data = _run_resolve(spec, tmp_path)

    assert data['status'] == 'success', data
    for canonical in ('quality-gate', 'verify', 'module-tests'):
        assert data['build'][canonical] == commands[canonical]
    assert 'test-compile' not in data['build'], 'the lane synthesized a canonical the project does not publish'
    assert data['build']['split'] == ['quality-gate', 'module-tests']


def test_resolve_omits_a_test_conditional_canonical_the_project_does_not_publish(tmp_path: Path) -> None:
    """A project that publishes no test entry still resolves and still gates.

    ``module-tests`` and ``test-compile`` are test-conditional in the
    architecture's contract, so their absence is an answer rather than a defect:
    the lane builds and gates with what the project actually publishes.
    """
    commands = {canonical: _PYPROJECT_EXEC.format(args=canonical) for canonical in ('quality-gate', 'verify')}
    spec = _seed_fixture(tmp_path, required_bots='some-bot', commands=commands)

    data = _run_resolve(spec, tmp_path)

    assert data['status'] == 'success', data
    assert set(data['build']) == {'quality-gate', 'verify', 'split'}
    assert data['build']['split'] == ['quality-gate']


# -----------------------------------------------------------------------------
# D2 — resolve reports the build server state
# -----------------------------------------------------------------------------

#: The framed reply a protocol-1 daemon gives to the client's ``ping``. The
#: frame is a 4-byte big-endian length prefix plus a UTF-8 JSON object; written
#: out here so the stub does not import the client it is standing in for.
_PING_REPLY = {'status': 'ok', 'version': '1', 'pid': 4242}


class _BuildServerState:
    """Seed the machine-global build-server state for a fixture project.

    The state lives in a short-lived temp home of its own rather than under the
    fixture project: the client's socket path is ``$PLAN_MARSHALL_HOME/marshalld/
    socket`` and a pytest ``tmp_path`` already spends most of AF_UNIX's ~108-byte
    path budget. A test decides the preflight outcome by what this seeds:
    nothing (unenrolled), a registry entry without a socket (enrolled, daemon
    down), or a registry entry plus a ping-answering socket (enrolled, reachable).
    """

    def __init__(self, project_dir: Path, *, registered: bool, daemon: bool = False) -> None:
        self.project_dir = project_dir
        self.registered = registered
        self.daemon = daemon
        self.home = Path(tempfile.mkdtemp(prefix='pm-bs-'))
        self.state_dir = self.home / 'marshalld'
        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def __enter__(self) -> dict[str, str]:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if self.registered:
            root = str(self.project_dir.resolve())
            _write(
                self.state_dir / 'registry.json',
                json.dumps(
                    {
                        'version': 1,
                        'projects': {root: {'canonical_root': root, 'worktree_containers': []}},
                    }
                ),
            )
        if self.daemon:
            self._start()
        return {'PLAN_MARSHALL_HOME': str(self.home)}

    def __exit__(self, *_exc: object) -> None:
        # Stop first, then join, then close. On Linux ``close()`` does not
        # reliably wake a blocking ``accept()`` in another thread (the blocked
        # call holds a reference to the open file description), so a close-only
        # teardown can leave the loop parked and the join expiring with the
        # thread still alive.
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        if self._server is not None:
            self._server.close()
            self._server = None
        shutil.rmtree(self.home, ignore_errors=True)

    def _start(self) -> None:
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.bind(str(self.state_dir / 'socket'))
        except OSError:
            server.close()
            raise
        server.listen(4)
        # A short timeout makes the accept loop poll the stop flag, so teardown
        # never depends on close() waking a blocked accept().
        server.settimeout(0.2)
        self._server = server
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        server = self._server
        if server is None:
            return
        while not self._stop.is_set():
            try:
                conn, _ = server.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            with conn:
                header = conn.recv(4)
                if len(header) != 4:
                    continue
                (length,) = struct.unpack('>I', header)
                remaining = length
                while remaining:
                    chunk = conn.recv(remaining)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                reply = json.dumps(_PING_REPLY).encode('utf-8')
                conn.sendall(struct.pack('>I', len(reply)) + reply)


def test_resolve_reports_build_server_disabled_for_an_unenrolled_project(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')

    with _BuildServerState(tmp_path, registered=False) as env:
        data = _run_resolve(spec, tmp_path, env_overrides=env)

    assert data['status'] == 'success'
    assert data['build_server'] == 'disabled'
    assert 'build_server_reason' not in data


def test_resolve_reports_build_server_ready_for_a_reachable_daemon(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')

    with _BuildServerState(tmp_path, registered=True, daemon=True) as env:
        data = _run_resolve(spec, tmp_path, env_overrides=env)

    assert data['status'] == 'success'
    assert data['build_server'] == 'ready'
    assert 'build_server_reason' not in data


def test_resolve_reports_build_server_down_with_its_reason(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')

    with _BuildServerState(tmp_path, registered=True) as env:
        data = _run_resolve(spec, tmp_path, env_overrides=env)

    assert data['status'] == 'success'
    assert data['build_server'] == 'down'
    assert data['build_server_reason'] == 'socket_absent'


def test_resolve_reports_a_preflight_failure_with_its_message(tmp_path: Path, monkeypatch) -> None:
    """A preflight that cannot run is ``down`` with the client's OWN message.

    The type alone would make a client-side defect (a changed signature, say)
    indistinguishable from a daemon outage in the landing.
    """
    import build_server

    def _boom(_namespace: argparse.Namespace) -> dict[str, Any]:
        raise RuntimeError('client signature changed')

    monkeypatch.setattr(build_server, 'run_preflight', _boom)
    spec = _seed_fixture(tmp_path, required_bots='x')
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path / '.machine-home'))
    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)

    data = module.cmd_resolve(argparse.Namespace(spec=str(spec), project_dir=str(tmp_path)))

    assert data['status'] == 'success', data
    assert data['build_server'] == 'down'
    assert 'RuntimeError' in data['build_server_reason']
    assert 'client signature changed' in data['build_server_reason']


def _raw_section(heading: str) -> str:
    """Return one ``## `` section verbatim, so a fenced block can be parsed."""
    text = _skill_text()
    start = text.index(heading)
    rest = text[start + len(heading) :]
    end = rest.find('\n## ')
    return heading + (rest if end == -1 else rest[:end])


def _fenced_blocks(section: str) -> list[str]:
    return re.findall(r'```[a-z-]*\n(.*?)```', section, re.DOTALL)


def test_skill_does_not_forbid_the_build_daemon() -> None:
    """The old blanket prohibition and its wrong premise are gone."""
    text = _skill_text()
    lowered = text.lower()
    assert 'Never use the daemon' not in text
    assert 'never drop `--execution-mode in_process`' not in text
    assert 'worktree has no executor' not in lowered
    assert 'has no executor' not in lowered
    # The positive premise, not just the absence of the wrong one: a routed job
    # re-runs the worktree's OWN executor, which worktree creation supplies.
    assert "the worktree's own `.plan/execute-script.py`" in text


def test_skill_does_not_require_a_test_conditional_canonical() -> None:
    """The gate runs the canonicals the project publishes, not a fixed ladder.

    ``module-tests`` and ``test-compile`` are test-conditional in the
    architecture's contract, so a lane that must run ``test-compile`` cannot run
    in a pyproject or npm project at all.
    """
    text = _skill_text()
    assert 'Never omit the test-compile part' not in text
    gate = _raw_section('## 4. Build gate')
    assert 'test-conditional' in gate, 'section 4 does not say the test canonicals are conditional'
    assert '`split`' in gate


def test_skill_build_gate_commands_use_the_default_routing() -> None:
    gate = _raw_section('## 4. Build gate')
    commands = [block for block in _fenced_blocks(gate) if '{build.' in block]
    assert commands, 'section 4 carries no build-command fence'
    for block in commands:
        assert '--execution-mode' not in block, f'the build gate still forces a routing mode:\n{block}'


def test_skill_states_the_preflight_degraded_and_killed_rules() -> None:
    text = _skill_text()
    for phrase in (
        'build_server: ready|disabled|down',
        '`degraded`',
        '`killed`',
        'never blind-retried',
        '`running`',
    ):
        assert phrase in text, f'the skill does not state {phrase!r}'


def test_skill_states_the_one_daemon_routed_build_rule() -> None:
    lowered = _skill_text().lower()
    assert 'one daemon-routed build at a time' in lowered
    assert 'sub-agents included' in lowered


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


def test_resolve_refuses_a_same_shaped_spec_nested_elsewhere(tmp_path: Path) -> None:
    """The staged-spec pattern is anchored at the project root, not suffix-matched."""
    _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')
    nested = tmp_path / 'archive' / '.plan' / 'orchestrator' / 'demo-epic' / 'plans'
    _write(nested / 'PLAN-LB-66-runbook-lane-skill.md', '# archived\n')
    data = _run_resolve(nested / 'PLAN-LB-66-runbook-lane-skill.md', tmp_path)
    assert data['status'] == 'error'
    assert data['error'] == 'spec_outside_orchestrator'


def test_resolve_reads_a_relative_spec_against_project_dir(tmp_path: Path) -> None:
    """A relative --spec is resolved against --project-dir, not the process cwd."""
    _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')
    script = get_scripts_dir('plan-marshall', _SKILL_NAME) / 'runbook_lane.py'
    result = run_script(
        script,
        'resolve',
        '--spec',
        '.plan/orchestrator/demo-epic/plans/PLAN-LB-66-runbook-lane-skill.md',
        '--project-dir',
        str(tmp_path),
        env_overrides=_claude_env(),
    )
    data = result.toon()
    assert data['status'] == 'success', data
    assert data['plan'] == 'lb-66-runbook-lane-skill'


def _claude_env() -> dict[str, str]:
    return {'CLAUDE_CODE_SESSION_ID': '1', 'OPENCODE': '', 'OPENCODE_PID': '', 'ANTIGRAVITY_AGENT': ''}


def test_resolve_claude_guard_requires_a_registered_hook(tmp_path: Path) -> None:
    """A settings file alone is not enforcement; a locally registered hook is."""
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')
    _write(tmp_path / '.claude' / 'settings.json', json.dumps({'permissions': {}}))

    data = _run_resolve(spec, tmp_path, env_overrides=_claude_env())
    assert data['guard'] == 'none'

    # A DECLARED but empty hook list is still not enforcement.
    _write(
        tmp_path / '.claude' / 'settings.json',
        json.dumps({'hooks': {'PreToolUse': []}}),
    )
    data = _run_resolve(spec, tmp_path, env_overrides=_claude_env())
    assert data['guard'] == 'none'

    # A hook carrying a command, registered in the MACHINE-LOCAL file, enforces.
    _write(
        tmp_path / '.claude' / 'settings.local.json',
        json.dumps(
            {
                'hooks': {
                    'PreToolUse': [{'matcher': 'Bash', 'hooks': [{'type': 'command', 'command': 'python3 gate.py'}]}]
                }
            }
        ),
    )
    data = _run_resolve(spec, tmp_path, env_overrides=_claude_env())
    assert data['guard'] == 'present'


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


# -----------------------------------------------------------------------------
# D2 — the per-reviewer quota-limited flag
# -----------------------------------------------------------------------------


def test_resolve_reports_a_quota_limited_reviewer(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='coderabbit')
    data = _run_resolve(spec, tmp_path)
    row = next(row for row in data['required_bots'] if row['bot'] == 'coderabbit')
    assert row['quota_limited'] is True


def test_resolve_reports_a_reviewer_that_is_not_quota_limited(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='cuioss-review-bot')
    data = _run_resolve(spec, tmp_path)
    row = next(row for row in data['required_bots'] if row['bot'] == 'cuioss-review-bot')
    assert row['quota_limited'] is False


def test_bot_standard_without_a_declaration_resolves_not_quota_limited(tmp_path: Path) -> None:
    """The authorization stays OFF by default: an undeclared bot is not quota-limited."""
    standards = tmp_path / 'standards'
    _write(
        standards / 'fixture-bot.md',
        '# Fixture bot\n\n```yaml\nbot_kind: fixture-bot\ntrigger_comment: "@fixture review"\n```\n',
    )
    registry = load_script_module('plan-marshall', 'automatic-review', 'bot_registry.py', register=False)
    assert registry.BotRegistry(standards).quota_limited('fixture-bot') is False


def test_optional_reviewers_also_carry_the_flag(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x', optional_bots='sourcery')
    data = _run_resolve(spec, tmp_path)
    assert data['optional_bots'][0]['quota_limited'] is True


# =============================================================================
# D3 — engineering personas, loaded as standards
# =============================================================================

#: The lane steps that write code, tests or docs, or that review — and the
#: persona each must name.
_WRITING_OR_REVIEWING_STEP_PERSONAS = (
    ('## 3. Implement, deliverable by deliverable', ('persona-implementer', 'persona-module-tester')),
    ('## 5. Self-review before the PR', ('persona-code-reviewer',)),
    ('## 6. Pull request and reviews', ('persona-code-reviewer',)),
)


def test_each_writing_or_reviewing_step_names_its_persona() -> None:
    for heading, personas in _WRITING_OR_REVIEWING_STEP_PERSONAS:
        section = _section(heading)
        for persona in personas:
            assert persona in section, f'{heading} does not name {persona}'


def test_self_review_and_pr_triage_name_adversarial_refute() -> None:
    for heading in ('## 5. Self-review before the PR', '## 6. Pull request and reviews'):
        assert 'adversarial-refute' in _section(heading), f'{heading} does not name adversarial-refute'


def test_personas_are_loaded_as_standards_only() -> None:
    text = _skill_text()
    assert 'standards only' in ' '.join(text.split()).lower()
    assert 'manage-personas' in text


def test_landing_report_requires_the_persona_list() -> None:
    landing = _section('## 8. Landing message (the last step, after the merge)')
    assert 'persona' in landing.lower()
    assert 'per step' in landing.lower()


def test_every_named_persona_resolves_to_a_bundle_skill() -> None:
    named = sorted(set(re.findall(r'persona-[a-z][a-z-]*[a-z]', _skill_text())))
    assert named, 'the skill names no persona'
    missing = [p for p in named if not (MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / p / 'SKILL.md').is_file()]
    assert not missing, f'named personas that do not resolve: {missing}'


# =============================================================================
# D4 — per-deliverable skills and personas, with an existence check
# =============================================================================


def test_setup_names_the_skill_existence_check_and_the_stop_and_ask() -> None:
    setup = _section('## 2. Set up the worktree')
    assert 'must exist in the installed bundles' in setup
    assert 'stops and asks the operator' in setup


def test_landing_report_requires_per_deliverable_skills_and_drift_additions() -> None:
    landing = _section('## 8. Landing message (the last step, after the merge)').lower()
    assert 'per deliverable' in landing
    assert 'skills added:' in landing
    assert 'reason:' in landing


_DECLARED_SPEC = (
    '## Deliverables\n\n'
    '1. **First deliverable**\n'
    '   - Skills: plan-marshall:runbook-lane\n'
    '   - Persona: implementer\n'
    '2. **Second deliverable**\n'
    '   - Skills: plan-marshall:manage-files\n'
    '   - Persona: module-tester\n'
)


def test_resolve_reports_each_deliverables_skills_and_persona(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x', spec_text=_DECLARED_SPEC)
    data = _run_resolve(spec, tmp_path)
    rows = data['deliverables']
    assert [str(row['number']) for row in rows] == ['1', '2']
    assert rows[0]['skills'] == 'plan-marshall:runbook-lane'
    assert rows[0]['persona'] == 'persona-implementer'
    assert rows[1]['persona'] == 'persona-module-tester'
    assert data['skills_note'] == 'declared'


def test_resolve_fails_on_a_nonexistent_named_skill(tmp_path: Path) -> None:
    spec_text = '## Deliverables\n\n1. **First**\n   - Skills: plan-marshall:no-such-skill\n'
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x', spec_text=spec_text)
    data = _run_resolve(spec, tmp_path)
    assert data['status'] == 'error'
    assert data['error'] == 'named_skill_not_found'


def test_resolve_fails_on_a_nonexistent_named_persona(tmp_path: Path) -> None:
    spec_text = '## Deliverables\n\n1. **First**\n   - Persona: no-such-persona\n'
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x', spec_text=spec_text)
    data = _run_resolve(spec, tmp_path)
    assert data['status'] == 'error'
    assert data['error'] == 'named_skill_not_found'


def test_spec_without_skill_or_persona_lines_says_none_named(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')
    data = _run_resolve(spec, tmp_path)
    assert data['skills_note'] == 'none named'


# =============================================================================
# D5 — a docs-only change skips the full local build
# =============================================================================

#: This repository's own footprint opt-in, READ from the real workflow file so the opt-in and the
#: ``extra-buildable`` matching cases run against the project's actual file. This repository's
#: workflow holds NO readable non-building class (it delegates via ``uses:``), so the cases that
#: exercise the architecture fallback are driven by the fixture's documentation module.
_VERIFY_WORKFLOW_FILE = PROJECT_ROOT / '.github' / 'workflows' / 'python-verify.yml'


def _seed_footprint(
    tmp_path: Path,
    *,
    opt_in: bool = True,
    module_path: str = '.',
    documentation_path: str = 'doc',
    documentation_files: tuple[str, ...] = ('doc/developer/build.adoc', 'doc/user/usage.md'),
) -> Path:
    _seed_fixture(
        tmp_path,
        executable=_PYPROJECT_EXEC,
        required_bots='x',
        module_path=module_path,
        documentation_path=documentation_path,
        documentation_files=documentation_files,
    )
    _write(
        tmp_path / '.github' / 'workflows' / 'python-verify.yml',
        _VERIFY_WORKFLOW_FILE.read_text(encoding='utf-8') if opt_in else 'name: Other\n',
    )
    return tmp_path


def _seed_local_ci_rule(root: Path, paths_ignore: list[str]) -> Path:
    """Write a self-contained CI workflow whose non-building rule the repository HOLDS.

    ``paths-ignore`` is the CI's own declaration of the paths it does not build.
    A workflow that carries it is READABLE — unlike this repository's, whose rule
    lives in a reusable workflow the checkout does not hold — and the classifier
    must prefer it to the architecture's hint.
    """
    body = [
        'name: Verify',
        'on:',
        '  pull_request:',
        '    paths-ignore:',
        *[f"      - '{glob}'" for glob in paths_ignore],
        'jobs:',
        '  verify:',
        '    uses: example/reusable.yml@0123456789abcdef',
        '    with:',
        '      skip-on-docs-only: true',
    ]
    _write(root / '.github' / 'workflows' / 'local-verify.yml', '\n'.join(body) + '\n')
    return root


def _build_classify(project_dir: Path, paths: str) -> dict:
    script = get_scripts_dir('plan-marshall', _SKILL_NAME) / 'runbook_lane.py'
    result = run_script(script, 'build-classify', '--project-dir', str(project_dir), '--paths', paths)
    assert result.success, f'build-classify crashed: {result.stderr}'
    data: dict[str, Any] = result.toon()
    return data


def test_build_classify_treats_a_docs_only_diff_as_docs_only(tmp_path: Path) -> None:
    data = _build_classify(_seed_footprint(tmp_path), 'doc/developer/build.adoc')
    assert data['kind'] == 'docs-only'
    assert data['source'] == 'ci-workflow'


def test_build_classify_treats_a_bundle_markdown_change_as_buildable(tmp_path: Path) -> None:
    data = _build_classify(
        _seed_footprint(tmp_path),
        'marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md',
    )
    assert data['kind'] == 'buildable'


def test_build_classify_treats_a_python_change_as_buildable(tmp_path: Path) -> None:
    data = _build_classify(_seed_footprint(tmp_path), 'build.py')
    assert data['kind'] == 'buildable'


def test_build_classify_without_an_opt_in_falls_back_to_the_architecture(tmp_path: Path) -> None:
    data = _build_classify(_seed_footprint(tmp_path, opt_in=False), 'doc/developer/build.adoc')
    assert data['source'] == 'architecture'
    # The fixture architecture has a root module (``paths.module: '.'``), so every
    # path lies inside a building module and the fallback answers buildable —
    # the fail-closed direction rather than a docs-only skip nobody declared.
    assert data['kind'] == 'buildable'


def test_skill_build_gate_documents_the_docs_only_path() -> None:
    gate = _section('## 4. Build gate')
    assert 'docs-only' in gate
    assert 'build-gate: docs-only' in gate


def test_build_classify_does_not_invent_a_document_class(tmp_path: Path) -> None:
    """A `.txt` file is not a document class of the gate, so it must build."""
    data = _build_classify(_seed_footprint(tmp_path), 'notes/plain.txt')
    assert data['kind'] == 'buildable'


def test_build_classify_keeps_an_unlisted_build_file_buildable(tmp_path: Path) -> None:
    """Architecture silence about a root build file must not become a docs-only skip."""
    project = _seed_footprint(tmp_path, opt_in=False, module_path='core')
    data = _build_classify(project, 'pyproject.toml')
    assert data['source'] == 'architecture'
    assert data['kind'] == 'buildable'


def test_build_classify_builds_a_document_outside_the_doc_module(tmp_path: Path) -> None:
    """Architecture silence outside the documentation module must build.

    The old rule let ANY document suffix classify a path docs-only even when the
    architecture named no documentation module for it — the fail-open shape
    deliverable 1 closes. Prose is now admitted only inside the documentation
    module the architecture reports, so this path builds.
    """
    project = _seed_footprint(tmp_path, opt_in=False, module_path='core')
    data = _build_classify(project, 'notes/readme.md')
    assert data['kind'] == 'buildable'


# -----------------------------------------------------------------------------
# PLAN-LB-72 D1 — the classifier never skips what the project's CI would build
# -----------------------------------------------------------------------------


def test_build_classify_reads_the_ci_skip_rule_when_the_repository_holds_it(tmp_path: Path) -> None:
    """A readable CI rule wins over the architecture's documentation module.

    The fixture's architecture says ``docs/`` is the documentation module, but
    the CI rule it holds names only ``doc/**``. The CI would build
    ``docs/guide.md``, so the classifier must too: the architecture is a hint
    that can only make a change BUILD, never skip one.
    """
    project = _seed_footprint(tmp_path, opt_in=False, documentation_path='docs')
    _seed_local_ci_rule(project, ['doc/**'])

    data = _build_classify(project, 'docs/guide.md')

    assert data['source'] == 'ci-workflow'
    assert data['kind'] == 'buildable'


def test_build_classify_matches_document_suffixes_case_sensitively(tmp_path: Path) -> None:
    """``.MD`` is not ``.md``: the CI's path filter is case-sensitive.

    ``README.MD`` builds because it lies outside the documentation module;
    ``doc/guide.MD`` is the assertion that pins CASE, since it lies inside the
    module and would be docs-only if the suffix were folded.
    """
    project = _seed_footprint(tmp_path)

    assert _build_classify(project, 'README.MD')['kind'] == 'buildable'
    assert _build_classify(project, 'doc/guide.MD')['kind'] == 'buildable'


def test_build_classify_builds_asciidoc_unless_the_ci_rule_names_it(tmp_path: Path) -> None:
    """A prose extension does not, by itself, make a path docs-only.

    The architecture's prose class is consulted only INSIDE the documentation
    module it belongs to, so a root-level ``guide.asciidoc`` builds; the CI rule
    is the only thing that can name it non-building.
    """
    unnamed = _seed_footprint(
        tmp_path / 'unnamed',
        documentation_path='docs',
        documentation_files=('docs/guide.asciidoc',),
    )

    assert _build_classify(unnamed, 'guide.asciidoc')['kind'] == 'buildable'

    named = _seed_footprint(
        tmp_path / 'named',
        opt_in=False,
        documentation_path='docs',
        documentation_files=('docs/guide.asciidoc',),
    )
    _seed_local_ci_rule(named, ['**/*.asciidoc'])

    assert _build_classify(named, 'guide.asciidoc')['kind'] == 'docs-only'


def test_paths_ignore_reads_the_pull_request_block_not_a_push_only_one() -> None:
    """A push-only filter must not drive the classification of a PR diff."""
    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)
    lines = [
        'on:',
        '  push:',
        '    paths-ignore:',
        "      - 'push-only/**'",
        '  pull_request:',
        '    paths-ignore:',
        "      - 'pr-only/**'",
    ]

    assert module._paths_ignore_globs(lines) == ['pr-only/**']


# =============================================================================
# D6 — the restored runbook rules
# =============================================================================

#: Rule-level parity: one entry per section, each carrying the rules that section
#: must keep. A heading-only parity check cannot catch a rule lost inside a
#: surviving heading; this table can, which is the whole point of restoring parity
#: at rule granularity rather than at heading granularity.
_RULE_PARITY: tuple[tuple[str, tuple[str, ...]], ...] = (
    ('## 0. Input', ('{branch}', '{prefix}{plan}', 'feature/', 'fix/', 'chore/')),
    (
        '## 1. Rules (every one binds; breaking one fails the run)',
        ('`sleep`', '`gh`', '`glab`', '`ruff`', '`mypy`', '`pytest`', '{guard_log}'),
    ),
    ('## 4. Build gate', ('{build_timeout_seconds}', '{base_branch}')),
    ('## 5. Self-review before the PR', ('{base_branch}', '`Task`')),
    (
        '## 6. Pull request and reviews',
        ('ci pr comments', 'ci pr reviews', 'ci pr thread-reply', 'ci pr resolve-thread', 'never `sleep`'),
    ),
    ('## 7. Merge gate', ('`verify`', 'origin/{base_branch}', 'pending', 'qualifying review')),
    ('## 8. Landing message (the last step, after the merge)', ('{guard_log}', '```landing-facts')),
)


def test_rule_level_parity_per_section() -> None:
    for heading, keywords in _RULE_PARITY:
        section = _section(heading)
        for keyword in keywords:
            assert keyword in section, f'{heading} lost {keyword!r}'


def test_skill_never_spells_the_base_branch_literally() -> None:
    text = _skill_text()
    assert 'origin/main' not in text, 'the skill spells the base branch literally'
    assert '--base main' not in text, 'the skill spells the base branch literally'


def _emitted_body(target: str) -> str:
    from marketplace.targets.body_transform_engine import load_transform_rules, make_body_transformer

    rules = load_transform_rules(PROJECT_ROOT / 'marketplace' / 'targets' / target / 'mapping.json')
    return make_body_transformer({}, rules)(_skill_text(), 'plan-marshall', 'skill')


def test_the_subagent_tool_is_rewritten_for_opencode_and_antigravity() -> None:
    # Claude IS the source format, so its name needs no rewrite; the two
    # emitting targets are the ones that must carry their own tool name.
    assert '`Task`' in _skill_text(), 'the source skill does not name the sub-agent tool'
    assert '`subagent`' in _emitted_body('opencode')
    assert '`invoke_subagent`' in _emitted_body('antigravity')


def test_the_skill_landing_facts_example_parses_with_no_dropped_line() -> None:
    inbox = load_script_module(
        'plan-marshall', 'plan-orchestrator', '_orchestrator_inbox.py', 'rb_lb67_orchestrator_inbox'
    )
    text = _skill_text()
    assert '```landing-facts' in text
    facts = inbox.parse_landing_facts(text)
    assert facts is not None, 'the skill carries no landing-facts fence'
    assert facts['schema'] == 'landing-facts/1'
    block = text.split('```landing-facts', 1)[1].split('```', 1)[0]
    lines = [line for line in block.splitlines() if line.strip()]
    assert all('=' in line for line in lines), 'a facts line carries no key=value pair'
    assert len(lines) == len(facts), 'a facts line was dropped by the parser'


def test_resolve_returns_the_base_branch_and_build_timeout(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x', base_branch='develop')
    data = _run_resolve(spec, tmp_path)
    assert data['base_branch'] == 'develop'
    assert isinstance(data['build_timeout_seconds'], int)
    assert data['build_timeout_seconds'] > 0
    assert data['guard_log'] == '.plan/temp/guard.log'


# =============================================================================
# D1 — the skill-existence check in every deployed layout
# =============================================================================

#: A flat-deployed lane records its ``{bundle}-{skill}`` identity in the skill's
#: own frontmatter (the flat emitters write it), which is the only way a
#: dash-joined directory can be attributed back to a bundle.
_FLAT_LANE_SKILL = (
    '---\nname: runbook-lane\nmetadata:\n  bundle: plan-marshall\n  skill: runbook-lane\n---\n\n# Runbook Lane\n'
)


def _flat_persona_skill(name: str) -> str:
    return f'---\nname: {name}\nmetadata:\n  bundle: plan-marshall\n  skill: {name}\n---\n\n# {name}\n'


def _install_lane(install_root: Path, *, layout: str, identity: bool = True) -> Path:
    """Copy the lane script into a fixture install and return the copied script.

    ``flat`` lays the lane at ``{root}/skills/plan-marshall-runbook-lane/``
    (OpenCode and Antigravity); ``nested`` lays it in a versioned bundle cache
    (``{root}/plan-marshall/0.1.0/skills/runbook-lane/``). Either way the script
    is copied, because ``_lane_skills_root`` is derived from the script's own
    path.

    ``identity=False`` writes a flat ``SKILL.md`` WITHOUT the ``metadata``
    identity the flat emitters record, which is the shape that cannot attribute
    the dash-joined directory back to a bundle.
    """
    source = get_scripts_dir('plan-marshall', _SKILL_NAME) / 'runbook_lane.py'
    if layout == 'flat':
        skill_dir = install_root / 'skills' / 'plan-marshall-runbook-lane'
        _write(
            skill_dir / 'SKILL.md',
            _FLAT_LANE_SKILL if identity else '---\nname: runbook-lane\n---\n\n# Runbook Lane\n',
        )
    else:
        skill_dir = install_root / 'plan-marshall' / '0.1.0' / 'skills' / 'runbook-lane'
        _write(install_root / 'plan-marshall' / '0.1.0' / '.claude-plugin' / 'plugin.json', '{}\n')
    scripts = skill_dir / 'scripts'
    scripts.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, scripts / 'runbook_lane.py')
    return scripts / 'runbook_lane.py'


#: A spec naming a bundle-qualified persona AND its bare form — both must resolve.
_TWO_BUNDLE_PERSONA_SPEC = (
    '## Deliverables\n\n'
    '1. **First**\n   - Persona: plan-marshall:persona-implementer\n'
    '2. **Second**\n   - Persona: persona-implementer\n'
)


def test_resolve_resolves_bundle_and_bare_persona_in_a_flat_install(tmp_path: Path) -> None:
    install = tmp_path / 'install'
    script = _install_lane(install, layout='flat')
    _write(
        install / 'skills' / 'plan-marshall-persona-implementer' / 'SKILL.md',
        _flat_persona_skill('persona-implementer'),
    )
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x', spec_text=_TWO_BUNDLE_PERSONA_SPEC)

    result = run_script(script, 'resolve', '--spec', str(spec), '--project-dir', str(tmp_path))

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success', data
    assert [row['persona'] for row in data['deliverables']] == [
        'plan-marshall:persona-implementer',
        'persona-implementer',
    ]


def test_resolve_resolves_a_cross_bundle_skill_in_a_nested_cache(tmp_path: Path) -> None:
    cache = tmp_path / 'cache'
    script = _install_lane(cache, layout='nested')
    _write(cache / 'pm-dev-python' / '0.1.0' / '.claude-plugin' / 'plugin.json', '{}\n')
    _write(cache / 'pm-dev-python' / '0.1.0' / 'skills' / 'python-core' / 'SKILL.md', '---\nname: python-core\n---\n')
    spec_text = '## Deliverables\n\n1. **First**\n   - Skills: pm-dev-python:python-core\n'
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x', spec_text=spec_text)

    result = run_script(script, 'resolve', '--spec', str(spec), '--project-dir', str(tmp_path))

    assert result.success, result.stderr
    assert result.toon()['status'] == 'success', result.toon()


def test_skill_exists_resolves_the_source_tree_across_two_bundles() -> None:
    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)

    assert module._skill_exists('plan-marshall:persona-implementer', 'plan-marshall')
    assert module._skill_exists('persona-implementer', 'plan-marshall')
    assert module._skill_exists('pm-dev-python:python-core', 'plan-marshall')


def test_resolve_passes_with_skills_from_two_bundles(tmp_path: Path) -> None:
    spec_text = '## Deliverables\n\n1. **First**\n   - Skills: plan-marshall:runbook-lane, pm-dev-python:python-core\n'
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x', spec_text=spec_text)

    data = _run_resolve(spec, tmp_path)

    assert data['status'] == 'success', data


def test_resolve_missing_skill_names_every_probed_path(tmp_path: Path) -> None:
    spec_text = '## Deliverables\n\n1. **First**\n   - Skills: plan-marshall:no-such-skill\n'
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x', spec_text=spec_text)

    data = _run_resolve(spec, tmp_path)

    assert data['status'] == 'error'
    assert data['error'] == 'named_skill_not_found'
    assert 'no-such-skill' in data['missing']
    assert 'skills/no-such-skill/SKILL.md' in data['probed']


# -----------------------------------------------------------------------------
# PLAN-LB-72 D2 — the existence check and its tests can fail for their reason
# -----------------------------------------------------------------------------


def test_resolve_missing_skill_names_every_probed_layout(tmp_path: Path) -> None:
    """A name absent from EVERY layout reports a path for each layout.

    The fixture carries both deployed shapes (the flat ``skills/`` root and a
    versioned nested cache), and the name exists in neither; the source-tree
    layout is read from the real module. Dropping either deployed layout's probe
    from the error — or the source-tree candidate from the enumeration — fails
    this test.
    """
    install = tmp_path / 'install'
    script = _install_lane(install, layout='flat')
    _write(install / 'plan-marshall' / '0.1.0' / '.claude-plugin' / 'plugin.json', '{}\n')
    spec_text = '## Deliverables\n\n1. **First**\n   - Skills: plan-marshall:absent-everywhere\n'
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x', spec_text=spec_text)

    result = run_script(script, 'resolve', '--spec', str(spec), '--project-dir', str(tmp_path))

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'error', data
    assert data['error'] == 'named_skill_not_found'
    probed = data['probed']
    assert 'skills/plan-marshall-absent-everywhere/SKILL.md' in probed, 'the flat layout is not named'
    assert 'plan-marshall/0.1.0/skills/absent-everywhere/SKILL.md' in probed, 'the VERSIONED nested layout is not named'
    assert 'plan-marshall/skills/absent-everywhere/SKILL.md' not in probed, (
        'the unversioned fallback is named for a versioned cache'
    )

    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)
    tree_probed = [
        path.as_posix() for path in module._skill_probe_paths('plan-marshall:absent-everywhere', 'plan-marshall')
    ]
    assert any(
        path.endswith('marketplace/bundles/plan-marshall/skills/absent-everywhere/SKILL.md') for path in tree_probed
    ), f'the source-tree layout is not named: {tree_probed}'


def test_resolve_resolves_a_cross_bundle_skill_in_a_flat_install(tmp_path: Path) -> None:
    """A flat install resolves ``pm-dev-python:python-core`` as a dash-joined peer.

    The flat emitters deploy the cross-bundle skill as
    ``pm-dev-python-python-core``; a bare per-bundle directory does not exist.
    """
    install = tmp_path / 'install'
    script = _install_lane(install, layout='flat')
    _write(
        install / 'skills' / 'pm-dev-python-python-core' / 'SKILL.md',
        '---\nname: python-core\nmetadata:\n  bundle: pm-dev-python\n  skill: python-core\n---\n',
    )
    spec_text = '## Deliverables\n\n1. **First**\n   - Skills: pm-dev-python:python-core\n'
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x', spec_text=spec_text)

    result = run_script(script, 'resolve', '--spec', str(spec), '--project-dir', str(tmp_path))

    assert result.success, result.stderr
    assert result.toon()['status'] == 'success', result.toon()


def test_resolve_refuses_a_bare_name_in_a_flat_install_without_an_identity(tmp_path: Path) -> None:
    """A flat ``SKILL.md`` with no identity is a named error, not a silent miss.

    The dash-joined directory cannot be split back into bundle and skill, so the
    lane cannot resolve ANY bare name. Returning a wrong-bundle probed miss for
    every one of them hides the real cause; the refusal names it.
    """
    install = tmp_path / 'install'
    script = _install_lane(install, layout='flat', identity=False)
    spec_text = '## Deliverables\n\n1. **First**\n   - Persona: persona-implementer\n'
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x', spec_text=spec_text)

    result = run_script(script, 'resolve', '--spec', str(spec), '--project-dir', str(tmp_path))

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'error', data
    assert data['error'] == 'flat_skill_identity_missing', data


# =============================================================================
# D2 — the docs-only classifier derives its rule from the project
# =============================================================================


def test_build_classify_globstar_matches_a_direct_child(tmp_path: Path) -> None:
    data = _build_classify(_seed_footprint(tmp_path), 'test/README.md')
    assert data['kind'] == 'buildable'


def test_build_classify_globstar_matches_a_marketplace_root_markdown(tmp_path: Path) -> None:
    data = _build_classify(_seed_footprint(tmp_path), 'marketplace/README.md')
    assert data['kind'] == 'buildable'


def test_build_classify_keeps_a_doc_as_docs_only(tmp_path: Path) -> None:
    data = _build_classify(_seed_footprint(tmp_path), 'doc/developer/build.adoc')
    assert data['kind'] == 'docs-only'
    assert data['source'] == 'ci-workflow'


def test_build_classify_treats_an_unreadable_rule_as_buildable(tmp_path: Path) -> None:
    project = _seed_footprint(tmp_path)
    # The workflow cannot be decoded, so the rule cannot be read: every path must
    # build rather than a skip being guessed.
    (project / '.github' / 'workflows' / 'python-verify.yml').write_bytes(b'\xff\xfe\x00 not utf-8\n')

    data = _build_classify(project, 'doc/developer/build.adoc')

    assert data['kind'] == 'buildable'
    assert 'python-verify.yml' in data['reason']
    assert 'UnicodeDecodeError' in data['reason']


def test_build_classify_architecture_fallback_treats_a_doc_module_as_prose(tmp_path: Path) -> None:
    project = _seed_footprint(tmp_path, opt_in=False, module_path='core')

    data = _build_classify(project, 'doc/developer/build.adoc')

    assert data['source'] == 'architecture'
    assert data['kind'] == 'docs-only'


def _classify_with_a_failing_glob_import(tmp_path: Path, monkeypatch, error: BaseException) -> dict:
    """Classify two paths while the shared glob translator cannot be imported.

    The import is blocked at the INTERPRETER primitive, so the failure happens
    where the real helper is imported rather than by replacing the lane's own
    wrapper with a stub.
    """
    project = _seed_footprint(tmp_path)
    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)
    real_import = builtins.__import__

    def _blocked(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == '_cmd_manage':
            raise error
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', _blocked)
    return module.cmd_build_classify(
        argparse.Namespace(
            paths='doc/developer/build.adoc,marketplace/bundles/plan-marshall/skills/x/SKILL.md',
            project_dir=str(project),
        )
    )


def test_build_classify_builds_every_path_when_the_glob_helper_is_absent(tmp_path: Path, monkeypatch) -> None:
    data = _classify_with_a_failing_glob_import(tmp_path, monkeypatch, ImportError("No module named '_cmd_manage'"))

    assert all(row['kind'] == 'buildable' for row in data['paths']), 'an absent translator skipped a build'
    assert data['reason'] == 'glob helper unavailable: ImportError'


def test_build_classify_builds_every_path_when_the_glob_helper_import_fails_otherwise(
    tmp_path: Path, monkeypatch
) -> None:
    """A non-ImportError failure at import is named, not propagated."""
    data = _classify_with_a_failing_glob_import(tmp_path, monkeypatch, RuntimeError('translator exploded'))

    assert all(row['kind'] == 'buildable' for row in data['paths']), 'a broken translator skipped a build'
    assert data['reason'] == 'glob helper unavailable: RuntimeError'


# =============================================================================
# PLAN-LB-73 D3 — the executor may not predate the lane text it runs
# =============================================================================


def _executor_with_version(path: Path, version: str) -> Path:
    _write(path, f"MARSHALL_VERSION = '{version}'\n")
    return path


def _versioned_lane_dir(tmp_path: Path, version: str) -> Path:
    lane = tmp_path / 'cache' / 'plan-marshall' / version / 'skills' / _SKILL_NAME
    lane.mkdir(parents=True, exist_ok=True)
    return lane


def test_input_checks_executor_skew_before_resolve() -> None:
    section = _raw_section('## 0. Input')

    assert 'executor-skew' in section, 'section 0 carries no executor-skew check'
    assert section.index('executor-skew') < section.index('runbook_lane resolve --spec'), (
        'the skew check does not run before the resolve call'
    )
    assert 'blocked' in section, 'the skew outcome is not named as blocked'
    assert 'regenerate the executor' in section, 'the check names no remedy'
    assert 'could_not_check' in section
    assert 'never read as' in section, 'an unmakeable comparison is not distinguished from no skew'


def test_executor_skew_detects_an_older_executor(tmp_path: Path) -> None:
    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)
    executor = _executor_with_version(tmp_path / 'execute-script.py', '0.1.1961')
    lane = _versioned_lane_dir(tmp_path, '0.1.1977')

    assert module._executor_skew(executor, lane) == 'skew'


def test_executor_skew_matches_equal_versions(tmp_path: Path) -> None:
    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)
    executor = _executor_with_version(tmp_path / 'execute-script.py', '0.1.1977')
    lane = _versioned_lane_dir(tmp_path, '0.1.1977')

    assert module._executor_skew(executor, lane) == 'match'


def test_executor_skew_cannot_check_an_unreadable_executor(tmp_path: Path) -> None:
    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)
    lane = _versioned_lane_dir(tmp_path, '0.1.1977')

    verdict = module._executor_skew(tmp_path / 'absent-execute-script.py', lane)

    assert verdict == 'could_not_check'
    assert verdict != 'match', 'an unreadable executor is read as no skew'


def test_extra_buildable_globs_drops_a_block_indicator_and_unwraps_quotes() -> None:
    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)

    literal = module._extra_buildable_globs(['      extra-buildable: |', '        marketplace/**/*.md'])
    quoted = module._extra_buildable_globs(['      extra-buildable: "test/**/*.md"'])

    assert literal == ['marketplace/**/*.md']
    assert quoted == ['test/**/*.md']


#: The written-as-a-suffix shapes a document-suffix list carries. Listed here,
#: in the TEST, so the classifier itself need not spell one — which is the
#: property under test.
_DOCUMENT_SUFFIX_LITERALS = frozenset({'.md', '.adoc', '.asciidoc', '.rst', '.txt'})


def _document_suffix_lists(source: str) -> list[int]:
    """Return the lines of document-suffix collections in the module, if any.

    Detected STRUCTURALLY and anywhere in the module — a module-level constant, a
    renamed list (``_DOC_SUFFIXES``), or an inline ``{'.md', '.adoc'}`` — because
    a name grep cannot catch any of those. The membership test is
    case-insensitive, so ``('.MD',)`` is caught too: case-folding is exactly the
    fail-open shape deliverable 1 closes.
    """
    offenders: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            continue
        literals = [element.value for element in node.elts if isinstance(element, ast.Constant)]
        if not literals or len(literals) != len(node.elts):
            continue
        if any(isinstance(literal, str) and literal.lower() in _DOCUMENT_SUFFIX_LITERALS for literal in literals):
            offenders.append(node.lineno)
    return offenders


def test_classifier_source_holds_no_workflow_name_or_suffix_list() -> None:
    source = (get_scripts_dir('plan-marshall', _SKILL_NAME) / 'runbook_lane.py').read_text(encoding='utf-8')

    assert 'python-verify.yml' not in source, 'the classifier names this repository workflow'
    assert '_NON_BUILDING_SUFFIXES' not in source, 'the classifier hard-codes non-building suffixes'
    assert "'.adoc'" not in source, 'the classifier hard-codes a document extension'
    suffix_lists = _document_suffix_lists(source)
    assert not suffix_lists, f'the classifier hard-codes a document-suffix collection at lines {suffix_lists}'


def test_glob_matching_does_not_treat_a_pattern_as_a_directory_prefix() -> None:
    """A CI path filter matches a FILE path; a matched directory does not cover its contents."""
    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)

    assert module._matches_glob('docs/a.md', 'docs/*')
    assert not module._matches_glob('docs/a/b.md', 'docs/*'), 'the gitignore directory tail was not removed'


def test_prose_extensions_do_not_leak_across_documentation_modules() -> None:
    """A suffix one documentation module files as prose must not skip in another's prefix."""
    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)
    surfaces = [('docs/', {'.md'}), ('site/', {'.html'})]

    assert module._is_project_doc('docs/a.md', surfaces)
    assert module._is_project_doc('site/a.html', surfaces)
    assert not module._is_project_doc('docs/a.html', surfaces), "site/'s extension leaked into docs/"


# =============================================================================
# D3 — the restored rules read the same everywhere and the parity tests can fail
# =============================================================================


def test_evidence_order_field_is_closed_and_reserved() -> None:
    """The order vocabulary is closed and the reserved wording lives in §1.

    A run that produced its failing output by mutating or reverting the fix must
    have a label that says so; the words "fail-first" and "observed failing
    before the fix" are truthful only for ``test-first``. §1 owns the rule; §8
    consumes it and §6 refers to it.
    """
    rules = _section('## 1. Rules (every one binds; breaking one fails the run)')
    landing = _section('## 8. Landing message (the last step, after the merge)')

    for name, section in (('§1', rules), ('§8', landing)):
        assert '`order`' in section, f'{name} does not require an order field'
        for value in ('`test-first`', '`mutation-after`', '`none`'):
            assert value in section, f'{name} does not name the order value {value}'
        assert 'reserved' in section, f'{name} does not reserve the fail-first wording'
        assert 'observed failing before the fix' in section, f'{name} does not name the reserved phrase'
        assert 'failing run' in section, f'{name} does not require the failing run evidence'
        assert 'output identifier' in section, f'{name} does not require an output identifier'


def test_a_test_runs_at_every_pushed_head_and_is_reported() -> None:
    gate = _section('## 4. Build gate')
    landing = _section('## 8. Landing message (the last step, after the merge)')

    assert 'every head pushed to a PR' in gate, 'the gate still lets a pushed head skip its test run'
    # The rule is conditional on what the project publishes, so the test pins the
    # conditional phrasing rather than the bare key: a silent drop of the
    # condition would otherwise still pass.
    assert '{build.module-tests}` where the resolve result supplies it' in gate, (
        'the per-head rule does not say the test command is the one the project publishes'
    )
    # The `test-compile` token must sit beside the sha requirement, not merely
    # appear somewhere in the section where a pre-existing `{sha}` placeholder
    # would satisfy a bare word check.
    per_head = [sentence for sentence in _sentences(landing) if 'test-compile' in sentence]
    assert per_head, 'the landing does not report the per-head test-compile run'
    assert any('sha' in sentence for sentence in per_head), 'the test-compile token is not beside the sha placeholder'


def test_self_review_clear_is_not_permitted_with_an_open_finding() -> None:
    review = _section('## 5. Self-review before the PR')

    assert '`self-review: clear` is never permitted while any finding is open' in review


def test_a_done_when_without_failing_evidence_is_reported_not_met() -> None:
    """The `order` vocabulary is coupled to the met/not-met verdict."""
    rules = _section('## 1. Rules (every one binds; breaking one fails the run)')
    landing = _section('## 8. Landing message (the last step, after the merge)')

    for name, section in (('§1', rules), ('§8', landing)):
        assert 'not met as written' in section, f'{name} does not require a not-met verdict without failing evidence'
    assert 'counts only fully met deliverables' in rules, 'the not-met verdict is not tied to the done count'


def test_unknown_verb_rule_names_its_landing_record() -> None:
    gate = _section('## 4. Build gate')
    landing = _section('## 8. Landing message (the last step, after the merge)')

    assert 'unknown subcommand' in gate, 'the unknown-verb rule is gone'
    assert 'question tool' in gate, 'the unknown-verb rule does not name the question tool'
    assert 'the answer it got' in gate, 'the unknown-verb rule does not require the answer to be recorded'
    assert 'no question tool was available' in landing, 'the landing cannot report a harness without a question tool'


def test_guard_state_has_one_location_in_rules_and_landing() -> None:
    rules = _section('## 1. Rules (every one binds; breaking one fails the run)')
    landing = _section('## 8. Landing message (the last step, after the merge)')

    assert 'prose beside the fence' in rules
    assert 'prose beside the fence' in landing
    assert 'facts block' not in rules, 'the rules section still places the guard state in the facts block'


def test_branch_rule_keeps_the_closed_set_neutral() -> None:
    row = _branch_row()

    for prefix in ('feature/', 'fix/', 'chore/'):
        assert prefix in row
    assert 'closed set' in row, 'the branch rule no longer states that the prefix set is closed'
    assert 'own set wins' not in row, 'the branch rule lets the project set replace the canonical prefixes'


def test_quota_policy_step_names_the_no_qualifying_review_condition() -> None:
    reviews = _section('## 6. Pull request and reviews')

    assert 'no qualifying review exists' in reviews


def test_sleep_parity_keyword_is_the_qualifier_free_sentence() -> None:
    keywords = {heading: set(entries) for heading, entries in _RULE_PARITY}
    reviews_keywords = keywords['## 6. Pull request and reviews']

    assert 'never `sleep`' in reviews_keywords, 'the sleep parity keyword is not the qualifier-free sentence'
    reviews = _section('## 6. Pull request and reviews')
    assert 'never `sleep`' in reviews, 'the qualifier-free sleep sentence is not present for the keyword to match'


def test_build_timeout_comes_from_the_architecture_stamp(tmp_path: Path, monkeypatch) -> None:
    """``resolve`` reports the stamp the REAL delegation reads.

    The test drives ``cmd_resolve`` and leaves the REAL
    ``_cmd_client._augment_resolved`` in place; only the lookup it READS —
    ``_lookup_bash_timeout`` — is replaced, so the function's own augmentation
    still runs. A raising real function leaves the lane's 1800 fallback in place
    and the assertion below fails, which a fixed-value stub of the function
    could never show.
    """
    client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py')
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')
    # Patch the lookup in the globals of the REAL function the lane calls, so the
    # real augmentation still runs and only what it READS is replaced.
    monkeypatch.setitem(
        client._augment_resolved.__globals__,
        '_lookup_bash_timeout',
        lambda tool, args, project: (1234, True),
    )
    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)

    data = module.cmd_resolve(argparse.Namespace(spec=str(spec), project_dir=str(tmp_path)))

    assert data['status'] == 'success', data
    assert data['build_timeout_seconds'] == 1234


# =============================================================================
# D3 — the landing carries the runtime stamp
# =============================================================================

#: The landing's consumer. The required-key set is READ from it rather than
#: restated, so the fence contract below cannot drift from the drain.
_inbox = load_script_module(
    'plan-marshall', 'plan-orchestrator', '_orchestrator_inbox.py', 'rb_lb78_orchestrator_inbox'
)


def _landing_fence_keys() -> list[str]:
    """Return the keys of the section 8 ``landing-facts`` fence, in order."""
    section = _raw_section('## 8. Landing message (the last step, after the merge)')
    fences = [block for block in _fenced_blocks(section) if 'schema=landing-facts/1' in block]
    assert len(fences) == 1, 'section 8 does not carry exactly one landing-facts fence'
    return [line.partition('=')[0].strip() for line in fences[0].splitlines() if line.strip()]


def test_landing_facts_fence_carries_every_required_key_except_total_tokens() -> None:
    """The lane's own template supplies what its consumer requires.

    Parsed from the fence as written, so a key the fence drops is a red test
    here rather than an INCOMPLETE landing discovered by the drain.
    """
    keys = set(_landing_fence_keys())

    assert {'effort', 'plugin_version'} <= keys, 'the section 8 fence names no effort or plugin_version'
    required = set(_inbox.LANDING_REQUIRED_KEYS) - {'total_tokens'}
    assert required <= keys, f'the section 8 fence omits {sorted(required - keys)}'


#: Runtime-info payloads in the shape ``collect_runtime_info`` returns: one
#: measured single-model tree, one mixed tree whose models changed while the
#: variant held (the collector records the measured effort there), one mixed tree
#: whose variants DIFFER (the collector then carries no ``effort`` at all — a flag
#: or an environment value is not this run's effort), and one read that produced
#: no stamp at all.
_MEASURED_RUNTIME_INFO: dict[str, Any] = {
    'harness': 'opencode',
    'transcripts': 'full',
    'model': 'deepseek-v4.1-flash',
    'variant': 'high',
    'model_source': 'measured',
    'effort': 'high',
    'effort_source': 'measured',
    'bundle_version': '0.1.1919',
    'executor_version': '0.1.1919',
}
_MIXED_RUNTIME_INFO: dict[str, Any] = {
    'harness': 'opencode',
    'transcripts': 'full',
    'model': 'mixed',
    'models': 'deepseek-v4.1-flash/high,claude-opus-5-5/high',
    'model_source': 'measured',
    'variant': 'high',
    'effort': 'high',
    'bundle_version': '0.1.1919',
}
_MIXED_VARIANTS_RUNTIME_INFO: dict[str, Any] = {
    'harness': 'opencode',
    'transcripts': 'full',
    'model': 'mixed',
    'models': 'deepseek-v4.1-flash/high,deepseek-v4.1-flash/max',
    'model_source': 'measured',
    'bundle_version': '0.1.1919',
}
_ABSENT_RUNTIME_INFO: dict[str, Any] = {'harness': 'opencode', 'transcripts': 'none'}


def _force_opencode(project_dir: Path, monkeypatch, db_path: Path, session_id: str) -> None:
    """Make the fixture project resolve to OpenCode and point the measurement at a DB.

    The lane measures the OpenCode model from ``opencode.db`` for a session id,
    so a test exercising the real seam supplies both. The env tier of
    ``target_context.resolve_target`` outranks the local config, so the ambient
    harness markers are cleared and the machine-local config names OpenCode.
    """
    for name in ('ANTIGRAVITY_AGENT', 'OPENCODE', 'CLAUDE_CODE_SESSION_ID'):
        monkeypatch.delenv(name, raising=False)
    _write(
        project_dir / '.plan' / 'local' / 'harness' / 'opencode.json',
        json.dumps({'schema_version': 1, 'harness': 'opencode'}),
    )
    monkeypatch.setenv('OPENCODE_DB_PATH', str(db_path))
    monkeypatch.setenv('OPENCODE_SESSION_ID', session_id)


def _write_session_db(db_path: Path, rows: list[tuple[str, str | None, str]]) -> None:
    """Create a fixture ``session_v2`` table with ``(id, parent_id, model_json)`` rows."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute('CREATE TABLE session_v2 (id TEXT, parent_id TEXT, model TEXT)')
        conn.executemany('INSERT INTO session_v2 (id, parent_id, model) VALUES (?, ?, ?)', rows)
        conn.commit()
    finally:
        conn.close()


def _model_json(model_id: str, variant: str, provider: str = 'opencode') -> str:
    return json.dumps({'id': model_id, 'providerID': provider, 'variant': variant})


def _resolve_with_runtime_info(
    tmp_path: Path, monkeypatch, info: dict[str, Any]
) -> tuple[dict[str, Any], list[tuple[str, dict[str, Any]]]]:
    """Run ``cmd_resolve`` in-process against a fixture runtime-info payload.

    ``collect_runtime_info`` is replaced on the REAL ``runtime_info`` module —
    the object the lane's deferred ``from runtime_info import …`` binds — so the
    test exercises ``cmd_resolve`` rather than an extracted seam. The harnesses
    it was asked to stamp, and the measurement inputs it was handed, are
    collected, so the test can assert both the harness ``resolve`` reported and
    the OpenCode wiring. The MEASURED path itself is covered separately by
    :func:`test_resolve_measures_the_opencode_model_from_the_session_db`.
    """
    import runtime_info

    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path / '.machine-home'))
    _force_opencode(tmp_path, monkeypatch, tmp_path / 'opencode.db', 'ses_lane_test')
    stamped: list[tuple[str, dict[str, Any]]] = []

    def _collect(harness: str, **kwargs: Any) -> dict[str, Any]:
        stamped.append((harness, kwargs))
        return dict(info)

    monkeypatch.setattr(runtime_info, 'collect_runtime_info', _collect)
    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)

    return module.cmd_resolve(argparse.Namespace(spec=str(spec), project_dir=str(tmp_path))), stamped


def test_resolve_returns_the_measured_runtime_stamp(tmp_path: Path, monkeypatch) -> None:
    data, stamped = _resolve_with_runtime_info(tmp_path, monkeypatch, _MEASURED_RUNTIME_INFO)

    assert data['status'] == 'success', data
    assert [harness for harness, _ in stamped] == [data['harness']], (
        'the stamp was not read for the harness resolve reported'
    )
    assert data['harness'] == 'opencode'
    _, kwargs = stamped[0]
    assert kwargs.get('opencode_db_path') == tmp_path / 'opencode.db', 'no database was handed to the measurement'
    assert kwargs.get('opencode_session_id') == 'ses_lane_test', 'no session was handed to the measurement'
    assert data['model'] == 'deepseek-v4.1-flash/high'
    assert data['effort'] == 'high'
    assert data['plugin_version'] == '0.1.1919'
    assert data['executor_version'] == '0.1.1919'


def test_resolve_scopes_the_opencode_environment(tmp_path: Path, monkeypatch) -> None:
    """The measurement is handed a target-scoped environment, not ``os.environ``.

    A Claude-specific variable leaking into the environment must never be
    attributed to an OpenCode stamp, which is why ``opencode_runtime``'s own
    collector call passes only the variables that target may resolve.
    """
    monkeypatch.setenv('CLAUDE_CODE_MODEL', 'claude-opus-5-5')
    monkeypatch.setenv('MODEL_NAME', 'generic-model')

    data, stamped = _resolve_with_runtime_info(tmp_path, monkeypatch, _MEASURED_RUNTIME_INFO)

    assert data['status'] == 'success', data
    env = stamped[0][1].get('env')
    assert isinstance(env, dict), 'the collector was handed no environment at all'
    assert 'CLAUDE_CODE_MODEL' not in env, 'a Claude-only variable was handed to the OpenCode measurement'
    assert env.get('MODEL_NAME') == 'generic-model', 'a variable the target may resolve was filtered out'


def test_resolve_degrades_a_failing_runtime_seam_to_unknown(tmp_path: Path, monkeypatch) -> None:
    """A landing field never aborts setup: a raising seam is ``unknown``.

    ``resolve`` runs at setup, before any work; failing it over a landing field
    would stop the run for a value the landing already has wording for. The
    degradation is not silent: the reason travels beside the stamp.
    """
    import runtime_info

    def _boom(harness: str, **_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError('seam exploded')

    monkeypatch.setattr(runtime_info, 'collect_runtime_info', _boom)
    spec = _seed_fixture(tmp_path, required_bots='x')
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path / '.machine-home'))
    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)

    data = module.cmd_resolve(argparse.Namespace(spec=str(spec), project_dir=str(tmp_path)))

    assert data['status'] == 'success', data
    assert data['model'] == 'unknown'
    assert data['effort'] == 'unknown'
    assert data['plugin_version'] == 'unknown'
    assert 'RuntimeError' in data['runtime_stamp_reason']
    assert 'seam exploded' in data['runtime_stamp_reason']


def test_resolve_measures_the_opencode_model_from_the_session_db(tmp_path: Path, monkeypatch) -> None:
    """The stamp is MEASURED over the session tree, not read from a flag.

    The database carries a root session and a child that ran the same model and
    variant; the lane must record that measured model and variant as its
    ``model`` and ``effort``. The old seam never handed the collector the
    database or the session id, so this read produced ``unknown`` in production.
    """
    db_path = tmp_path / 'opencode.db'
    _write_session_db(
        db_path,
        [
            ('ses_lane_test', None, _model_json('deepseek-v4.1-flash', 'high')),
            ('ses_child', 'ses_lane_test', _model_json('deepseek-v4.1-flash', 'high')),
        ],
    )
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path / '.machine-home'))
    _force_opencode(tmp_path, monkeypatch, db_path, 'ses_lane_test')
    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)

    data = module.cmd_resolve(argparse.Namespace(spec=str(spec), project_dir=str(tmp_path)))

    assert data['status'] == 'success', data
    assert data['harness'] == 'opencode'
    assert data['model'] == 'deepseek-v4.1-flash/high', 'the measured session model did not reach the stamp'
    assert data['effort'] == 'high', 'the measured variant did not reach the stamp'


def test_resolve_returns_the_mixed_model_as_its_list_form(tmp_path: Path, monkeypatch) -> None:
    data, _ = _resolve_with_runtime_info(tmp_path, monkeypatch, _MIXED_RUNTIME_INFO)

    assert data['status'] == 'success', data
    assert data['model'] == 'deepseek-v4.1-flash/high,claude-opus-5-5/high'
    assert data['effort'] == 'high'
    assert data['plugin_version'] == '0.1.1919'


def test_resolve_keeps_effort_unknown_when_a_mixed_tree_has_no_single_variant(tmp_path: Path, monkeypatch) -> None:
    """A tree that ran more than one variant has no measured effort.

    The collector then carries no ``effort`` at all — a flag or an environment
    value is not this run's effort — so the stamp must say ``unknown`` rather
    than pick one of the variants.
    """
    data, _ = _resolve_with_runtime_info(tmp_path, monkeypatch, _MIXED_VARIANTS_RUNTIME_INFO)

    assert data['status'] == 'success', data
    assert data['model'] == 'deepseek-v4.1-flash/high,deepseek-v4.1-flash/max'
    assert data['effort'] == 'unknown'


def test_resolve_returns_unknown_when_the_runtime_stamp_is_absent(tmp_path: Path, monkeypatch) -> None:
    data, _ = _resolve_with_runtime_info(tmp_path, monkeypatch, _ABSENT_RUNTIME_INFO)

    assert data['status'] == 'success', data
    assert data['model'] == 'unknown'
    assert data['effort'] == 'unknown'
    assert data['plugin_version'] == 'unknown'
    assert 'executor_version' not in data, 'an unread executor version was stamped anyway'


#: A real value for every key of the section 8 template. A key with no entry
#: fails the test, so a fence line cannot enter the template without the test
#: saying what a real value for it is.
_TEMPLATE_FACT_VALUES: dict[str, str] = {
    'schema': 'landing-facts/1',
    'plan_id': 'rb-lb-78-runbook-lane-build-resolution',
    'epic': 'demo-epic',
    'pr': '#78',
    'merge_state': 'merged',
    'cleanup_owed': 'false',
    'deliverables_total': '3',
    'deliverables_done': '3',
    'total_tokens': 'unknown',
    'harness': 'opencode',
    'model': 'deepseek-v4.1-flash/high',
    'effort': 'high',
    'plugin_version': '0.1.1919',
    'executor_version': '0.1.1919',
    'steps': 'setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done',
    'step.sonar-roundtrip.open_issue_count': '0',
    'step.sonar-roundtrip.open_issue_rules': 'none',
}


def _landing_from_the_section_8_template() -> str:
    """Fill the section 8 fence with real values, as a landing writes it."""
    keys = _landing_fence_keys()
    unmapped = [key for key in keys if key not in _TEMPLATE_FACT_VALUES]
    assert not unmapped, f'the section 8 fence carries {unmapped}, for which this test has no real value'
    facts = '\n'.join(f'{key}={_TEMPLATE_FACT_VALUES[key]}' for key in keys)
    return f'```landing-facts\n{facts}\n```\n\n## Deliverables\n\nEvery Done-when met.\n'


def test_a_landing_from_the_section_8_template_is_complete_except_total_tokens(plan_context, tmp_path: Path) -> None:
    """The lane's own template drains as complete on every fact it can measure.

    Only ``total_tokens`` stays open: it is PLAN-LB-49's, and no runbook-lane
    run measures it today.
    """
    env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
    script = get_script_path('plan-marshall', 'plan-orchestrator', 'orchestrator.py')
    run_script(script, 'scaffold', '--slug', 'demo-epic', env_overrides=env)
    payload = tmp_path / 'landing.md'
    payload.write_text(_landing_from_the_section_8_template(), encoding='utf-8')
    run_script(
        script,
        'inbox',
        'write',
        '--slug',
        'demo-epic',
        '--sender-type',
        'plan',
        '--sender-id',
        'rb-lb-78-runbook-lane-build-resolution',
        '--kind',
        'landing',
        '--payload-file',
        str(payload),
        env_overrides=env,
    )

    result = run_script(
        script,
        'inbox',
        'landing-check',
        '--slug',
        'demo-epic',
        '--message',
        'rb-lb-78-runbook-lane-build-resolution-001.md',
        env_overrides=env,
    )

    assert result.returncode == 0, result.stderr
    data = result.toon()
    assert data['complete'] is False
    assert data['missing_keys'] == ['total_tokens']
