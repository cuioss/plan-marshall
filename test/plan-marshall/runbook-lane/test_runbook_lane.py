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

import json
import re
from pathlib import Path
from typing import Any

from conftest import (
    MARKETPLACE_ROOT,
    PROJECT_ROOT,
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
_MAVEN_EXEC = 'python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args "{args}"'


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
    spec_text: str = '# staged spec\n',
    base_branch: str | None = None,
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
                },
                **({'project': {'default_base_branch': base_branch}} if base_branch else {}),
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
    _write(spec, spec_text)
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

#: This repository's own footprint opt-in, as `.github/workflows/python-verify.yml`
#: declares it. Seeded into a fixture so the classifier is exercised against the
#: repository's real rule rather than against the repository tree.
_VERIFY_WORKFLOW = (
    'name: Python Verify\n'
    '\n'
    'jobs:\n'
    '  verify:\n'
    '    with:\n'
    '      skip-on-docs-only: true\n'
    '      extra-buildable: >-\n'
    '        .plan/marshal.json\n'
    '        .claude/**\n'
    '        marketplace/**/*.md\n'
    '        test/**/*.md\n'
    '      pre-verify-goals: generate\n'
)


def _seed_footprint(tmp_path: Path, *, opt_in: bool = True) -> Path:
    _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')
    _write(
        tmp_path / '.github' / 'workflows' / 'python-verify.yml',
        _VERIFY_WORKFLOW if opt_in else 'name: Other\n',
    )
    return tmp_path


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
        ('ci pr comments', 'ci pr reviews', 'ci pr thread-reply', 'ci pr resolve-thread', '`sleep`'),
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
