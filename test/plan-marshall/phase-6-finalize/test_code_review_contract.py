#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract test for the ``default:code-review`` finalize step body.

``phase-6-finalize/workflow/code-review.md`` is an LLM-driven step body, so
nothing executes it in a test. What CAN be pinned is the contract it states, and
each assertion below pins one clause of it against an independent source:

* the frontmatter facts the composer, the dispatcher and the registry read;
* the recording order — the author brief records nothing, and every terminal
  ``mark-step-done`` call sits after the verifier dispatch;
* the findings schema the step tells the author to write equals the schema
  ``review_support validate --kind code`` checks (its module docstring);
* ``records_facts`` covers every fact ``validate`` derives for a code verdict;
* the inputs — every script call is a ``manage-*`` verb or the step's own
  ``review_support`` helper, and every other command is ``git``;
* the body has no language- or build-system-conditional step;
* the rule-source selection the body states — the profiles it reads and the
  skills it excludes — applied to the real domain declarations through the
  real ``get-skills-by-profile`` resolver: a Python-only plan of this
  repository resolves the ``plan-marshall-plugin-dev`` and ``python`` rule
  sources, a Java-only plan resolves ``java`` and ``java-cui``, and neither
  resolves a security skill.

Every extractor carries a control that proves it finds what it targets, so a
broken parser fails here instead of passing vacuously.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import _review_support_validate as _val
import extension_discovery
import pytest
import review_support
from _manifest_lanes import _read_frontmatter_lane
from extension_discovery import find_implementors

from conftest import load_script_module

#: The real ``get-skills-by-profile`` handler, loaded without a ``sys.modules``
#: registration: the manage-config tests publish ``_cmd_skill_resolution`` under
#: its stem, and this module only needs the returned object.
_cmd_skill_resolution = load_script_module('plan-marshall', 'manage-config', '_cmd_skill_resolution.py', register=False)

_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'
_STEP = 'default:code-review'

#: The facts the step records beyond the ones ``validate`` derives.
_STEP_OWN_FACTS = {'acceptance', 'may_close', 'work_performed', 'round_kind'}

#: The only script notations the body may call: the manage-* family and the
#: step's own deterministic helper.
_HELPER_NOTATION = 'plan-marshall:phase-6-finalize:review_support'

#: The code-review spine — the rule source every round carries.
_SPINE_SKILL = 'plan-marshall:ref-code-quality'

#: The security skill the body excludes by name, beside the ``-security`` suffix.
_SECURITY_PERSONA = 'plan-marshall:persona-security-expert'

#: Language and build-system names a language-conditional step would have to name.
_LANGUAGE_TOKENS = (
    'java',
    'python',
    'javascript',
    'typescript',
    'kotlin',
    'maven',
    'gradle',
    'npm',
    'pytest',
    'junit',
    'jest',
)

#: The two fixture plans of request D11, each as the domain set its footprint
#: resolves to, with the bundle that declares each domain.
_PYTHON_ONLY_PLAN = {'plan-marshall-plugin-dev': 'pm-plugin-development', 'python': 'pm-dev-python'}
_JAVA_ONLY_PLAN = {'java': 'pm-dev-java', 'java-cui': 'pm-dev-java-cui'}

_NOTATION_RE = re.compile(r'execute-script\.py\s+(\S+)')
_JSON_KEY_RE = re.compile(r'"([a-z_]+)"\s*:')
_FENCE_RE = re.compile(r'^```(\w*)\s*$')
_PROFILES_RE = re.compile(r'its ((?:`[a-z_]+`(?:, | and ))+`[a-z_]+`) profiles name')
_SUFFIX_RE = re.compile(r'every skill whose name ends in `(-[a-z]+)`')
_EXCLUDED_NOTATION_RE = re.compile(r'^- `([a-z-]+:[a-z-]+)`\.$', re.MULTILINE)


def _record() -> dict:
    for record in find_implementors(_EXT_POINT):
        if record.get('name') == _STEP:
            return record
    raise AssertionError(f'{_STEP} is not a discovered {_EXT_POINT} implementor, so no assertion has a doc to read.')


def _doc_path() -> Path:
    return Path(_record()['path'])


def _text() -> str:
    return _doc_path().read_text(encoding='utf-8')


def _body() -> str:
    """The document after its frontmatter block."""
    text = _text()
    assert text.startswith('---\n'), 'the step doc must open with a frontmatter block'
    end = text.index('\n---\n', 4)
    return text[end + 5 :]


def _fields(*keys: str) -> dict:
    return extension_discovery._read_frontmatter_fields(_doc_path(), keys)


def _section(heading: str) -> str:
    """The text of one ``##`` / ``###`` section, up to the next heading of the same or higher level."""
    body = _body()
    level = len(heading) - len(heading.lstrip('#'))
    start = body.index(heading + '\n')
    rest = body[start + len(heading) + 1 :]
    stop = re.search(rf'^#{{1,{level}}} ', rest, re.MULTILINE)
    return rest[: stop.start()] if stop else rest


def _fenced_blocks(text: str, language: str) -> list[str]:
    """Every fenced block of ``language`` in ``text``, as its content."""
    blocks: list[str] = []
    current: list[str] | None = None
    current_language = ''
    for line in text.splitlines():
        match = _FENCE_RE.match(line)
        if match and current is None:
            current, current_language = [], match.group(1)
            continue
        if match and current is not None:
            if current_language == language:
                blocks.append('\n'.join(current))
            current = None
            continue
        if current is not None:
            current.append(line)
    return blocks


def _commands(text: str) -> list[str]:
    """Every command in the ``bash`` blocks of ``text``, continuation lines joined."""
    commands: list[str] = []
    for block in _fenced_blocks(text, 'bash'):
        joined = block.replace('\\\n', ' ')
        commands.extend(line.strip() for line in joined.splitlines() if line.strip())
    return commands


def _docstring_schema_keys(section: str) -> set[str]:
    """The JSON keys of one schema (``code`` / ``verifier``) in ``review_support``'s docstring."""
    doc = review_support.__doc__ or ''
    start = doc.index(f'    {section}:\n')
    rest = doc[start + len(section) + 6 :]
    stop = re.search(r'^    \w+:\n|^\S', rest, re.MULTILINE)
    return set(_JSON_KEY_RE.findall(rest[: stop.start()] if stop else rest))


def _json_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in _json_keys(item)}
    if isinstance(value, list):
        return {key for item in value for key in _json_keys(item)}
    return set()


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


def test_registry_record_carries_the_declared_identity():
    record = _record()
    assert record['order'] == 7
    assert record['default_on'] is True
    assert record['presets'] == []
    assert record['source'] == 'built-in'
    assert Path(record['path']).name == 'code-review.md'
    assert Path(record['path']).parent.name == 'workflow'


def test_frontmatter_facts_match_the_contract():
    fields = _fields('mutates_source', 'head_dependent', 'implements')
    assert fields.get('mutates_source') is False
    assert fields.get('head_dependent') is True
    assert set(fields.get('implements') or []) == {
        'plan-marshall:extension-api/standards/ext-point-execution-context-workflow',
        _EXT_POINT,
    }


def test_lane_is_adversarial():
    lane = _read_frontmatter_lane(_doc_path())
    assert lane is not None, 'the lane block must parse, or the class assertion below proves nothing'
    assert lane.get('class') == 'adversarial'


def test_records_facts_cover_every_fact_validate_derives():
    declared = set(_fields('records_facts').get('records_facts') or [])
    derived = set(_val.CODE_FACT_KEYS) | set(_val.SHARED_FACT_KEYS)
    assert derived, 'control: validate must derive a non-empty fact set'
    assert derived <= declared, f'records_facts misses facts validate derives: {sorted(derived - declared)}'
    assert _STEP_OWN_FACTS <= declared, f'records_facts misses the step-own facts: {sorted(_STEP_OWN_FACTS - declared)}'


def test_records_facts_name_no_functional_fact():
    """The two reviews record disjoint verdict facts; a functional fact here would be a copy-paste slip."""
    declared = set(_fields('records_facts').get('records_facts') or [])
    functional_only = set(_val.FUNCTIONAL_FACT_KEYS) - set(_val.CODE_FACT_KEYS)
    assert functional_only, 'control: the functional fact set must differ from the code fact set'
    assert not declared & functional_only


# ---------------------------------------------------------------------------
# Recording order
# ---------------------------------------------------------------------------


def test_author_brief_carries_no_recording_clause():
    """The author's whole procedure (Step 3) records no outcome and files no finding."""
    author = _section('## Step 3: Author the findings')
    assert author.strip(), 'control: the author section must be found, or the scan below reads nothing'
    assert 'mark-step-done' not in author
    assert 'qgate add' not in author
    assert 'record-before-return' not in _body().lower()


def test_every_terminal_record_follows_the_verifier_dispatch():
    """No ``mark-step-done`` call is written before the verifier is dispatched."""
    body = _body()
    record_heading = body.index('## Step 6: Record the outcome (inline)')
    before, after = body[:record_heading], body[record_heading:]
    assert 'name: code-review-verifier' in _section('## Step 5: Verifier (dispatch from the inline context)'), (
        'the verifier dispatch must sit in Step 5, the step before the recording step'
    )
    assert any('mark-step-done' in command for command in _commands(after)), (
        'control: the body must carry terminal mark-step-done calls in the recording step'
    )
    early = [command for command in _commands(before) if 'mark-step-done' in command]
    assert not early, (
        f'a mark-step-done call precedes the verifier dispatch, so a round could record unverified: {early}'
    )


def test_dispatched_workflow_notation_is_the_registry_entry():
    """The author dispatch names this step's own registry document, never a composed path."""
    doc = _doc_path()
    notation = f'plan-marshall:phase-6-finalize/{doc.parent.name}/{doc.name}'
    body = _body()
    workflows = set(re.findall(r'workflow: (\S+)', body)) | set(re.findall(r'--workflow (\S+)', body))
    assert workflows, 'control: the body must name the workflow it dispatches'
    assert workflows == {notation}


def test_author_dispatch_loads_the_code_reviewer_identity():
    step_2 = _section('## Step 2: Choose where the author runs (inline)')
    dispatch = next(block for block in _fenced_blocks(step_2, 'text') if 'name: code-review-author' in block)
    assert 'plan-marshall:persona-code-reviewer' in dispatch
    assert 'Skill: plan-marshall:persona-code-reviewer' in step_2, 'the inline author must load the identity too'


# ---------------------------------------------------------------------------
# Findings schema
# ---------------------------------------------------------------------------


def test_findings_schema_equals_the_schema_validate_checks():
    blocks = _fenced_blocks(_section('## Findings schema'), 'json')
    assert len(blocks) == 1, 'the Findings schema section must carry exactly one JSON block'
    workflow_keys = _json_keys(json.loads(blocks[0]))
    validated_keys = _docstring_schema_keys('code')
    assert validated_keys, 'control: the review_support docstring must yield the code schema keys'
    assert workflow_keys == validated_keys


def test_findings_schema_enumerates_the_validated_vocabularies():
    """The citation forms and failure classes the schema offers are the ones validate accepts."""
    finding = json.loads(_fenced_blocks(_section('## Findings schema'), 'json')[0])['findings'][0]
    forms = {form.strip() for form in finding['rule']['form'].split('|')}
    classes = {value.strip() for value in finding['failure_class'].split('|')}
    assert forms == set(_val.CITATION_FORMS)
    assert classes == set(_val.FAILURE_CLASSES)


def test_verifier_answer_equals_the_schema_validate_checks():
    step_5 = _section('## Step 5: Verifier (dispatch from the inline context)')
    blocks = _fenced_blocks(step_5, 'json')
    assert len(blocks) == 1, 'Step 5 must carry exactly one JSON verifier-answer block'
    assert _json_keys(json.loads(blocks[0])) == _docstring_schema_keys('verifier')


def test_schema_extractor_control():
    """The docstring extractor separates the code schema from its neighbours."""
    code = _docstring_schema_keys('code')
    assert 'findings' in code
    assert 'failure_scenario' in code
    assert 'deliverables' not in code, 'the functional schema leaked into the code key set'
    assert 'grading_supported' not in code, 'the verifier schema leaked into the code key set'


def test_validate_is_called_with_the_code_kind_only():
    kinds = {
        match
        for command in _commands(_body())
        if 'review_support validate' in command
        for match in re.findall(r'--kind (\S+)', command)
    }
    assert kinds == {'code'}


# ---------------------------------------------------------------------------
# Inputs and scope
# ---------------------------------------------------------------------------


def test_every_script_call_is_a_manage_verb_or_the_helper():
    notations = [match for command in _commands(_body()) for match in _NOTATION_RE.findall(command)]
    assert notations, 'control: the body must carry script calls'
    offenders = sorted({n for n in notations if n != _HELPER_NOTATION and not n.split(':')[1].startswith('manage-')})
    assert not offenders, f'the body calls scripts outside the manage-* family and its helper: {offenders}'


def test_every_other_command_is_git():
    others = [command for command in _commands(_body()) if 'execute-script.py' not in command]
    assert others, 'control: the body must carry git commands'
    offenders = [command for command in others if not command.startswith('git -C ')]
    assert not offenders, f'the body runs commands that are neither a script call nor git: {offenders}'


def test_body_has_no_language_conditional_step():
    body = _body().lower()
    named = [token for token in _LANGUAGE_TOKENS if re.search(rf'\b{token}\b', body)]
    assert not named, f'the body names a language or build system, so a step may branch on it: {named}'
    assert re.search(r'\bpython\b', 'a python change'), 'control: the token scan must match a whole word'


def test_body_names_both_skills_it_must_not_be_confused_with():
    body = _body()
    assert 'plan-marshall:recipe-code-review' in body
    assert 'plan-marshall:persona-code-reviewer' in body


# ---------------------------------------------------------------------------
# Rule-source selection (request D11)
# ---------------------------------------------------------------------------


def _rulebook_section() -> str:
    return _section('### 1b. The rulebook this round applies')


def _stated_profiles() -> list[str]:
    match = _PROFILES_RE.search(_rulebook_section())
    assert match, 'the rulebook section must state which profiles it reads'
    return re.findall(r'`([a-z_]+)`', match.group(1))


def _stated_exclusions() -> tuple[str, list[str]]:
    section = _rulebook_section()
    suffix = _SUFFIX_RE.search(section)
    assert suffix, 'the rulebook section must state the security-suffix exclusion'
    return suffix.group(1), _EXCLUDED_NOTATION_RE.findall(section)


def _select(skills_by_profile: dict[str, list[str]]) -> list[str]:
    """The selection rule exactly as the rulebook section states it."""
    suffix, excluded = _stated_exclusions()
    selected: list[str] = []
    for profile in _stated_profiles():
        for notation in skills_by_profile.get(profile, []):
            if notation.endswith(suffix) or notation in excluded or notation in selected:
                continue
            selected.append(notation)
    return selected


def _resolved_profiles(monkeypatch: pytest.MonkeyPatch, domain: str, bundle: str) -> dict[str, list[str]]:
    """The domain's ``skills_by_profile`` through the real ``get-skills-by-profile`` handler."""
    monkeypatch.setattr(_cmd_skill_resolution, 'require_initialized', lambda: None)
    monkeypatch.setattr(_cmd_skill_resolution, 'load_config', lambda: {'skill_domains': {domain: {'bundle': bundle}}})
    result = _cmd_skill_resolution.cmd_get_skills_by_profile(type('Args', (), {'domain': domain})())
    assert result.get('status') == 'success', f'{domain}: the resolver failed: {result}'
    profiles: dict[str, list[str]] = result['skills_by_profile']
    assert profiles, f'control: {domain} must resolve at least one profile'
    return profiles


def _plan_rule_sources(monkeypatch: pytest.MonkeyPatch, plan: dict[str, str]) -> dict[str, list[str]]:
    return {domain: _select(_resolved_profiles(monkeypatch, domain, bundle)) for domain, bundle in plan.items()}


def _is_security_skill(notation: str) -> bool:
    return notation.endswith('-security') or notation == _SECURITY_PERSONA


def test_the_stated_selection_reads_the_three_review_profiles():
    assert _stated_profiles() == ['implementation', 'module_testing', 'quality']
    suffix, excluded = _stated_exclusions()
    assert suffix == '-security'
    assert excluded == [_SECURITY_PERSONA]
    assert 'The `security` profile is not read at all.' in _rulebook_section()


def test_the_spine_is_always_a_rule_source():
    toon = next(block for block in _fenced_blocks(_rulebook_section(), 'toon') if 'skills[' in block)
    assert f'  - {_SPINE_SKILL}' in toon


def test_python_only_plan_resolves_its_two_domains_and_no_security_skill(monkeypatch):
    sources = _plan_rule_sources(monkeypatch, _PYTHON_ONLY_PLAN)

    assert set(sources) == {'plan-marshall-plugin-dev', 'python'}
    assert all(sources.values()), f'a domain resolved no rule source: {sources}'
    assert 'pm-dev-python:python-core' in sources['python']
    assert 'pm-dev-python:pytest-testing' in sources['python']
    flat = [notation for notations in sources.values() for notation in notations]
    assert not [notation for notation in flat if _is_security_skill(notation)]


def test_java_only_plan_resolves_its_two_domains_and_no_security_skill(monkeypatch):
    sources = _plan_rule_sources(monkeypatch, _JAVA_ONLY_PLAN)

    assert set(sources) == {'java', 'java-cui'}
    assert all(sources.values()), f'a domain resolved no rule source: {sources}'
    assert 'pm-dev-java:java-core' in sources['java']
    flat = [notation for notations in sources.values() for notation in notations]
    assert not [notation for notation in flat if _is_security_skill(notation)]


def test_the_fixture_domains_do_declare_security_skills(monkeypatch):
    """Control: the security skills exist in these domains, so their absence above is the selection's doing."""
    plans = {**_PYTHON_ONLY_PLAN, **_JAVA_ONLY_PLAN}
    security = {
        domain: [
            n for n in _resolved_profiles(monkeypatch, domain, bundle).get('security', []) if _is_security_skill(n)
        ]
        for domain, bundle in plans.items()
        if domain in ('python', 'java')
    }
    assert all(security.values()), f'control: python and java must declare a security skill: {security}'


def test_the_exclusion_bites_on_a_security_skill_in_a_read_profile():
    """Control: a security skill placed in a read profile is filtered out by the stated rule."""
    profiles = {
        'implementation': ['pm-x:x-core', 'pm-x:x-security'],
        'module_testing': [_SECURITY_PERSONA, 'pm-x:x-testing'],
        'security': ['pm-x:x-hardening'],
    }
    assert _select(profiles) == ['pm-x:x-core', 'pm-x:x-testing']
