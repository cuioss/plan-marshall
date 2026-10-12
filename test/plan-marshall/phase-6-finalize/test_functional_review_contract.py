#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract test for the ``default:functional-review`` finalize step body.

``phase-6-finalize/workflow/functional-review.md`` is an LLM-driven step body, so
nothing executes it in a test. What CAN be pinned is the contract it states, and
each assertion below pins one clause of it against an independent source:

* the frontmatter facts the composer, the dispatcher and the registry read;
* the recording order — the author brief records nothing, and every terminal
  ``mark-step-done`` call sits after the verifier dispatch;
* the verdict schema the step tells the author to write equals the schema
  ``review_support validate --kind functional`` checks (its module docstring);
* the inputs — every script call is a ``manage-*`` verb or the step's own
  ``review_support`` helper, and every other command is ``git``;
* the body names no extension point and no candidate surfacer, and has no
  language- or build-system-conditional step;
* ``records_facts`` covers every fact ``validate`` derives.

Every extractor carries a control that proves it finds what it targets, so a
broken parser fails here instead of passing vacuously.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import _review_support_validate as _val
import extension_discovery
import review_support
from _manifest_lanes import _read_frontmatter_lane
from extension_discovery import find_implementors

_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'
_STEP = 'default:functional-review'

#: The facts the step records beyond the ones ``validate`` derives.
_STEP_OWN_FACTS = {'acceptance', 'may_close', 'work_performed', 'round_kind'}

#: The only script notations the body may call: the manage-* family and the
#: step's own deterministic helper.
_HELPER_NOTATION = 'plan-marshall:phase-6-finalize:review_support'

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

_NOTATION_RE = re.compile(r'execute-script\.py\s+(\S+)')
_JSON_KEY_RE = re.compile(r'"([a-z_]+)"\s*:')
_FENCE_RE = re.compile(r'^```(\w*)\s*$')


def _doc_path() -> Path:
    for record in find_implementors(_EXT_POINT):
        if record.get('name') == _STEP:
            return Path(record['path'])
    raise AssertionError(f'{_STEP} is not a discovered {_EXT_POINT} implementor, so no assertion has a doc to read.')


def _record() -> dict:
    for record in find_implementors(_EXT_POINT):
        if record.get('name') == _STEP:
            return record
    raise AssertionError(f'{_STEP} is not a discovered {_EXT_POINT} implementor.')


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
    """The JSON keys of one schema (``functional`` / ``verifier``) in ``review_support``'s docstring."""
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
    assert record['order'] == 6
    assert record['default_on'] is True
    assert record['presets'] == []
    assert record['source'] == 'built-in'
    assert Path(record['path']).name == 'functional-review.md'
    assert Path(record['path']).parent.name == 'workflow'


def test_frontmatter_facts_match_the_contract():
    fields = _fields('mutates_source', 'head_dependent', 'implements')
    assert fields.get('mutates_source') is False
    assert fields.get('head_dependent') is True
    assert set(fields.get('implements') or []) == {
        'plan-marshall:extension-api/standards/ext-point-execution-context-workflow',
        _EXT_POINT,
    }


def test_lane_is_adversarial_and_large():
    lane = _read_frontmatter_lane(_doc_path())
    assert lane is not None, 'the lane block must parse, or the class assertion below proves nothing'
    assert lane.get('class') == 'adversarial'
    assert lane.get('cost_size') == 'L'


def test_records_facts_cover_every_fact_validate_derives():
    declared = set(_fields('records_facts').get('records_facts') or [])
    derived = set(_val.FUNCTIONAL_FACT_KEYS) | set(_val.SHARED_FACT_KEYS)
    assert derived, 'control: validate must derive a non-empty fact set'
    assert derived <= declared, f'records_facts misses facts validate derives: {sorted(derived - declared)}'
    assert _STEP_OWN_FACTS <= declared, f'records_facts misses the step-own facts: {sorted(_STEP_OWN_FACTS - declared)}'


# ---------------------------------------------------------------------------
# Recording order
# ---------------------------------------------------------------------------


def test_author_brief_carries_no_recording_clause():
    """The author's whole procedure (Step 3) records no outcome and files no finding."""
    author = _section('## Step 3: Author the verdict')
    assert author.strip(), 'control: the author section must be found, or the scan below reads nothing'
    assert 'mark-step-done' not in author
    assert 'qgate add' not in author
    assert 'record-before-return' not in _body().lower()


def test_every_terminal_record_follows_the_verifier_dispatch():
    """No ``mark-step-done`` call is written before the verifier is dispatched.

    Branch C — the not-run record — sits after the verifier too: it is the one
    record written without a verifier answer, and it records ``loop_back``, never
    a close.
    """
    body = _body()
    record_heading = body.index('## Step 6: Record the outcome (inline)')
    before, after = body[:record_heading], body[record_heading:]
    assert 'name: functional-review-verifier' in _section('## Step 5: Verifier (dispatch from the inline context)'), (
        'the verifier dispatch must sit in Step 5, the step before the recording step'
    )
    assert before.index('name: functional-review-verifier') < record_heading
    assert any('mark-step-done' in command for command in _commands(after)), (
        'control: the body must carry terminal mark-step-done calls in the recording step'
    )
    early = [command for command in _commands(before) if 'mark-step-done' in command]
    assert not early, (
        f'a mark-step-done call precedes the verifier dispatch, so a round could record unverified: {early}'
    )


def test_dispatched_workflow_notation_is_the_registry_entry():
    """The author dispatch names this step's own registry document, never a composed path."""
    record = _record()
    doc = Path(record['path'])
    notation = f'plan-marshall:phase-6-finalize/{doc.parent.name}/{doc.name}'
    body = _body()
    workflows = set(re.findall(r'workflow: (\S+)', body)) | set(re.findall(r'--workflow (\S+)', body))
    assert workflows, 'control: the body must name the workflow it dispatches'
    assert workflows == {notation}


# ---------------------------------------------------------------------------
# Verdict schema
# ---------------------------------------------------------------------------


def test_verdict_schema_equals_the_schema_validate_checks():
    blocks = _fenced_blocks(_section('## Verdict schema'), 'json')
    assert len(blocks) == 1, 'the Verdict schema section must carry exactly one JSON block'
    workflow_keys = _json_keys(json.loads(blocks[0]))
    validated_keys = _docstring_schema_keys('functional')
    assert validated_keys, 'control: the review_support docstring must yield the functional schema keys'
    assert workflow_keys == validated_keys


def test_verifier_answer_equals_the_schema_validate_checks():
    step_5 = _section('## Step 5: Verifier (dispatch from the inline context)')
    blocks = _fenced_blocks(step_5, 'json')
    assert len(blocks) == 1, 'Step 5 must carry exactly one JSON verifier-answer block'
    assert _json_keys(json.loads(blocks[0])) == _docstring_schema_keys('verifier')


def test_schema_extractor_control():
    """The docstring extractor separates the two schemas rather than reading them as one."""
    functional = _docstring_schema_keys('functional')
    verifier = _docstring_schema_keys('verifier')
    assert 'deliverables' in functional
    assert 'grading_supported' in verifier
    assert 'deliverables' not in verifier
    assert 'findings' not in functional, 'the code schema leaked into the functional key set'


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


def test_body_names_no_extension_point_and_no_surfacer():
    body = _body().lower()
    assert 'ext-point' not in body
    assert not re.search(r'\bsurfac(?:er|ers|ing)\b', body), 'the body names a candidate surfacer'
    review_gates = set(re.findall(r'\b([a-z]+_review)\b', body))
    assert review_gates == {'functional_review'}, (
        f'the body must name its own ceremony gate and no other review gate: {sorted(review_gates)}'
    )
    assert re.search(r'\bsurfac(?:er|ers|ing)\b', 'the candidate surfacer'), 'control: the surfacer scan must match'
    assert 'ext-point' in _text().lower(), 'control: the frontmatter does name its ext-points'


def test_body_has_no_language_conditional_step():
    body = _body().lower()
    named = [token for token in _LANGUAGE_TOKENS if re.search(rf'\b{token}\b', body)]
    assert not named, f'the body names a language or build system, so a step may branch on it: {named}'
    assert re.search(r'\bpython\b', 'a python change'), 'control: the token scan must match a whole word'
