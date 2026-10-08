#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract regression for the pre-submission-self-review severity contract.

The review grades every finding and loops only on the ones that block. The
grading itself is done by a model, so nothing here can execute it; these tests
read the documents that instruct it and assert each rule is stated where the
step will meet it:

* the severity rubric has exactly one home, and the workflow and the extension
  point link to it instead of restating it;
* the returned finding schema carries the grade and its failure scenario, a
  blocking finding is filed under the store's own severity vocabulary, and an
  advisory finding is not filed at all;
* the verifier checks the grading, and the round closes on *no blocking finding
  after regrading* rather than on an empty findings list;
* the behavioural check, the prose screening question and the on-demand
  contract read are present, and the rules they replace are gone.

Each detector that could pass vacuously is fired against a synthetic text that
must trip it, beside the shipped document that must not.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT

_WORKFLOW_DOC = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'workflow' / 'pre-submission-self-review.md'
)
_SURFACING_DOC = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'extension-api' / 'standards' / 'ext-point-self-review-surfacing.md'
)
_SKILL_DOC = MARKETPLACE_ROOT / 'pm-plugin-development' / 'skills' / 'ext-self-review-plan-marshall' / 'SKILL.md'

_SEVERITIES = ('critical', 'high', 'medium', 'low')
_RUBRIC_HEADING = '## Finding-authoring contract (cognitive review pass)'
_RUBRIC_SECTION_NAME = 'Finding-authoring contract'

_FINDING_SCHEMA = 'findings[N]{file,line,defect_class,severity,failure_scenario,rationale,cohort_size}'
_RETIRED_FINDING_SCHEMA = 'findings[N]{file,line,defect_class,rationale,cohort_size}'
_STATE_RULE = '--rule pre-submission-self-review-state'
_NEW_FACTS = ('blocking_count', 'advisory_count', 'screened_out')

#: Sentences the verifier prompt and the termination section no longer carry.
#: Matched against whitespace-normalised text, because the prompt is hard-wrapped.
_RETIRED_SENTENCES = (
    'A round that returned findings is always no',
    'nothing you were given suggests a further round would find',
    'do not soften a no because a further round costs something',
    'a clean verdict that reads as a reviewed diff where the',
    'self-seeding',
    'NEVER to reduce the number of rounds',
)

#: Filing triggers the reworded prose checks no longer carry.
_RETIRED_FILING_TRIGGERS = (
    'could this mean two things?',
    'subtly different wording',
    'contradicts, narrows, or widens',
)

_NUMBER_WORDS = {
    17: 'seventeen',
    18: 'eighteen',
    19: 'nineteen',
    20: 'twenty',
    21: 'twenty-one',
    22: 'twenty-two',
}


def _read(path: Path) -> str:
    text: str = path.read_text(encoding='utf-8')
    return text


def _flat(text: str) -> str:
    """Collapse every whitespace run, so a hard-wrapped sentence matches."""
    return re.sub(r'\s+', ' ', text)


def _section(text: str, heading: str) -> str:
    """Return the body under ``heading`` up to the next heading of its depth or shallower."""
    start = text.index(heading)
    depth = len(heading) - len(heading.lstrip('#'))
    body_start = start + len(heading)
    closer = re.compile(rf'^#{{1,{depth}}}\s', re.MULTILINE)
    match = closer.search(text, body_start)
    return text[body_start : match.start() if match else len(text)]


def _frontmatter(text: str) -> str:
    assert text.startswith('---\n')
    return text[4 : text.index('\n---\n', 4)]


def _body(text: str) -> str:
    return text[text.index('\n---\n', 4) + 5 :]


def _table_first_cells(text: str) -> list[str]:
    """Return the first cell of every Markdown table row in ``text``."""
    cells = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            cells.append(stripped.strip('|').split('|')[0].strip())
    return cells


def _has_rubric_table(text: str) -> bool:
    """True when ``text`` carries a table with one row per severity token."""
    cells = set(_table_first_cells(text))
    return all(f'`{severity}`' in cells for severity in _SEVERITIES)


def _bundle_docs() -> list[Path]:
    docs = sorted(MARKETPLACE_ROOT.rglob('*.md'))
    assert len(docs) > 100, f'bundle walk found only {len(docs)} Markdown files — mis-rooted'
    return docs


def _qgate_add_calls(text: str) -> list[str]:
    """Return every fenced bash block that issues a ``qgate add``."""
    blocks = re.findall(r'```bash\n(.*?)```', text, flags=re.DOTALL)
    return [block for block in blocks if 'qgate add' in block]


def _constant_severity_offenders(calls: list[str]) -> list[str]:
    """Return ``qgate add`` calls passing a constant severity outside the state finding."""
    return [call for call in calls if re.search(r'--severity\s+[a-z]', call) and _STATE_RULE not in call]


def _branch_rows(step_4: str) -> list[tuple[str, str, str]]:
    """Parse the Step 4 branch-selection table into ``(blocking_set, verifier, branch)``."""
    rows = []
    for line in step_4.splitlines():
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) == 3 and cells[0] in ('empty', 'non-empty'):
            rows.append((cells[0], cells[1], cells[2][0]))
    return rows


def _selected_branch(rows: list[tuple[str, str, str]], blocking_set: str, verifier: str) -> str:
    """Evaluate the documented table for one round.

    ``verifier`` is ``closes`` for an accepted verdict with ``may_close: yes``
    and ``does-not-close`` for a refusal, a ``may_close: no`` or no return.
    """
    for row_set, row_verifier, branch in rows:
        if row_set != blocking_set:
            continue
        if row_verifier == 'any':
            return branch
        row_closes = 'may_close: yes' in row_verifier
        if row_closes == (verifier == 'closes'):
            return branch
    raise AssertionError(f'no documented branch for blocking_set={blocking_set!r}, verifier={verifier!r}')


def _step_4() -> str:
    return _section(_read(_WORKFLOW_DOC), '### Step 4: Mark Step Complete (inline)')


def _severity_section() -> str:
    return _section(_read(_WORKFLOW_DOC), '#### Findings carry a severity, and only blocking findings loop')


# ---------------------------------------------------------------------------
# One rubric, stated once
# ---------------------------------------------------------------------------


def test_the_rubric_table_lives_in_exactly_one_bundle_document():
    holders = [doc for doc in _bundle_docs() if _has_rubric_table(_read(doc))]

    assert holders == [_SKILL_DOC], (
        'The severity rubric must be a table in exactly one Markdown file — the '
        f'surfacer skill. Found it in: {[str(h.relative_to(MARKETPLACE_ROOT)) for h in holders]}'
    )


def test_rubric_table_detector_separates_a_table_from_prose():
    table = '| Severity | When |\n|---|---|\n' + ''.join(f'| `{s}` | x |\n' for s in _SEVERITIES)
    prose = 'Graded `critical`, `high`, `medium` or `low` by the rubric.'
    partial = '| Severity | When |\n|---|---|\n| `high` | x |\n| `low` | x |\n'

    assert _has_rubric_table(table)
    assert not _has_rubric_table(prose)
    assert not _has_rubric_table(partial)


def test_the_rubric_sits_in_the_finding_authoring_contract_with_both_rules():
    contract = _section(_read(_SKILL_DOC), _RUBRIC_HEADING)

    assert _has_rubric_table(contract), 'the rubric table is not inside the finding-authoring contract'
    assert '**The failure-scenario test.**' in contract
    assert '**Blocking means `medium` or above.**' in contract

    calibration = contract[contract.index('Calibration examples') :]
    graded = re.findall(r'\|\s*`(critical|high|medium|low)`\s*\|', calibration)
    assert len(graded) >= 6, f'calibration table carries {len(graded)} graded examples'
    assert set(graded) == set(_SEVERITIES), f'calibration covers only {sorted(set(graded))}'


@pytest.mark.parametrize('doc', [_WORKFLOW_DOC, _SURFACING_DOC], ids=['workflow', 'ext-point'])
def test_the_document_links_to_the_rubric_instead_of_restating_it(doc):
    text = _read(doc)
    links = re.findall(r'\]\(([^)]*ext-self-review-plan-marshall/SKILL\.md)\)\s*§\s*"([^"]+)"', text)

    rubric_links = [target for target, section in links if section == _RUBRIC_SECTION_NAME]
    assert rubric_links, f'{doc.name} carries no link to § "{_RUBRIC_SECTION_NAME}" of the surfacer skill'
    for target in rubric_links:
        assert (doc.parent / target).resolve() == _SKILL_DOC.resolve(), f'{doc.name} links to {target}'
    assert _RUBRIC_HEADING in _read(_SKILL_DOC)
    assert not _has_rubric_table(text)


# ---------------------------------------------------------------------------
# Findings carry the grade; only blocking findings are filed
# ---------------------------------------------------------------------------


def test_the_returned_schema_carries_severity_and_failure_scenario():
    text = _read(_WORKFLOW_DOC)
    output = _section(text, '### Dispatched-envelope output (returned from Steps 2–3 to Step 4)')

    assert _FINDING_SCHEMA in output
    assert 'screened_out:' in output
    assert 'contract_sources_read:' in output
    assert 'contract_sources_listed:' in output
    assert 'observations[M]{file,line,defect_class,severity,rationale,out_of_scope}' in output
    assert _RETIRED_FINDING_SCHEMA not in text, 'the schema without a grade is still quoted somewhere'


def test_the_new_facts_are_declared_and_recorded():
    text = _read(_WORKFLOW_DOC)
    block = re.search(r'^records_facts:\n((?:[ \t]+-[ \t]+\w+\n)+)', _frontmatter(text) + '\n', flags=re.MULTILINE)
    assert block, 'records_facts block not parsed'
    declared = re.findall(r'-[ \t]+(\w+)', block.group(1))
    assert 'candidates' not in declared, 'the parse ran on into requires_prompt_fields'

    for fact in _NEW_FACTS:
        assert fact in declared, f'{fact} is not declared in records_facts (declared: {declared})'
        assert f'--fact {fact}=' in _body(text), f'{fact} is declared but no mark-step-done call records it'


def test_the_grade_is_mapped_onto_the_store_vocabulary():
    step_4 = _flat(_step_4())

    assert '`critical` and `high` are filed as `error`' in step_4
    assert '`medium` is filed as `warning`' in step_4
    assert '`info`, is not used, because a `low` finding is not filed' in step_4


def test_no_finding_is_filed_under_a_constant_severity():
    calls = _qgate_add_calls(_read(_WORKFLOW_DOC))
    assert len(calls) >= 2, f'expected the state call and the per-finding call, parsed {len(calls)}'

    assert _constant_severity_offenders(calls) == []
    per_finding = [call for call in calls if _STATE_RULE not in call]
    assert per_finding, 'no per-finding qgate add parsed — the assertion above would be vacuous'
    assert all('--severity {store_severity}' in call for call in per_finding)
    # The state finding describes the round, not a defect, and keeps its constant.
    assert any(_STATE_RULE in call and '--severity warning' in call for call in calls)


def test_constant_severity_detector_fires_on_the_retired_call():
    retired = 'manage-findings qgate add --file-path "{file}" --severity warning\n'
    state = f'manage-findings qgate add {_STATE_RULE} --severity warning\n'
    graded = 'manage-findings qgate add --severity {store_severity}\n'

    assert _constant_severity_offenders([retired]) == [retired]
    assert _constant_severity_offenders([state, graded]) == []


def test_advisory_findings_stay_out_of_the_store():
    text = _read(_WORKFLOW_DOC)
    section = _flat(_severity_section())

    assert '**Advisory findings stay out of the Q-Gate store.**' in section
    assert 'A pending finding blocks the merge and archive gates' in section
    assert 'One decision-log line' in section
    assert 'the facts `blocking_count` and `advisory_count`' in section
    assert "The step's returned TOON" in section
    assert '--severity info' not in text, 'a low finding is being filed to the store'
    assert 'is treated as `low`, and the step logs the downgrade' in section
    assert '`out_of_scope: true`' in section


def test_only_blocking_findings_oblige_a_class_sweep():
    closure = _flat(_section(_read(_WORKFLOW_DOC), '#### Class-closure obligation (fix the class, not the instance)'))

    assert 'The obligation applies to blocking findings only' in closure
    assert 'A `low` finding does not oblige a sweep for its siblings' in closure


def test_found_marks_only_the_blocking_verdict():
    literals = set(re.findall(r'`"(self-review[^"]*)"`', _read(_WORKFLOW_DOC)))
    with_found = sorted(literal for literal in literals if 'found' in literal)

    assert with_found == ['self-review found {B} blocking in {C} classes, {A} advisory']
    assert 'self-review clean: no blocking finding, {A} advisory' in literals


# ---------------------------------------------------------------------------
# The verifier checks the grading and closes when nothing blocks
# ---------------------------------------------------------------------------


def test_the_verifier_prompt_asks_the_two_grading_questions():
    verifier = _section(_read(_WORKFLOW_DOC), '### Step 3b: Independent verification (dispatch)')

    assert '(1) IS THE GRADING SUPPORTED?' in verifier
    assert '(2) MAY THE ROUND CLOSE?' in verifier
    assert 'promote[P]{file,line,defect_class,reason}:' in verifier
    assert 'demote[D]{file,line,defect_class,reason}:' in verifier
    flat = _flat(verifier)
    assert "Set acceptance to refused ONLY when the verdict's counts or its scope statement are wrong" in flat
    assert 'Answer yes when that set is empty AND surface_scope is full' in flat
    assert 'is not a reason to answer no' in flat


@pytest.mark.parametrize('sentence', _RETIRED_SENTENCES)
def test_a_retired_sentence_occurs_nowhere_in_the_bundles(sentence):
    holders = [
        str(path.relative_to(MARKETPLACE_ROOT))
        for path in sorted([*_bundle_docs(), *MARKETPLACE_ROOT.rglob('*.py')])
        if sentence in _flat(path.read_text(encoding='utf-8', errors='replace'))
    ]

    assert holders == []


def test_retired_sentence_scan_reads_through_a_hard_wrap():
    wrapped = 'the findings\n      are fine. A round that returned findings is\n      always no: so'

    assert _RETIRED_SENTENCES[0] in _flat(wrapped)
    assert _RETIRED_SENTENCES[0] not in wrapped


def test_the_closing_branch_is_selected_by_the_regraded_blocking_set():
    step_4 = _flat(_step_4())

    assert (
        'The closing branch is selected by *no blocking finding after regrading*, '
        'never by *the findings list is empty*.'
    ) in step_4
    assert 'Recompute `cohort_size` for every member over the regraded set' in step_4


def test_an_all_low_round_closes_and_one_medium_finding_loops_back():
    rows = _branch_rows(_step_4())
    assert len(rows) >= 3, f'branch table not parsed: {rows}'

    # Same round, same verifier answer; the only difference is one regraded finding.
    assert _selected_branch(rows, 'empty', 'closes') == 'A'
    assert _selected_branch(rows, 'non-empty', 'closes') == 'B'
    assert 'a round whose findings are all `low` selects Branch A' in _flat(_step_4())
    assert 'the same round with one finding regraded to `medium` selects Branch B' in _flat(_step_4())


def test_a_medium_finding_without_a_failure_scenario_is_treated_as_low():
    step_4 = _flat(_step_4())
    section = _flat(_severity_section())

    verifier = _flat(_section(_read(_WORKFLOW_DOC), '### Step 3b: Independent verification (dispatch)'))

    # The rule, and its counterpart: a blocking finding is one that carries a scenario.
    assert 'A finding returned `medium` or above with an empty `failure_scenario` is treated as `low`' in section
    assert 'a finding graded `medium` or above. It carries a `failure_scenario`' in section
    # It is applied before the verifier is dispatched, and the regrading starts after it.
    assert verifier.index('Apply the empty-scenario downgrade first') < verifier.index('Task: plan-marshall:{target}')
    assert 'the findings graded `medium` or above that carry a failure scenario' in step_4
    assert "recompose the author's verdict by the verdict rule" in verifier


def test_promote_turns_an_advisory_round_into_a_loop_back_and_demote_lets_one_close():
    rows = _branch_rows(_step_4())
    step_4 = _flat(_step_4())

    assert 'A verifier `promote` entry turns an advisory-only round into a loop-back' in step_4
    assert 'a `demote` entry on the only blocking finding lets the round close' in step_4
    # Both regrading directions are stated as steps that change the set the table reads.
    assert 'Add every advisory finding the verifier named in `promote[]`, at `medium`' in step_4
    assert 'Remove every finding the verifier named in `demote[]`; it becomes advisory' in step_4
    # No row lets a non-empty set close, whatever the verifier answered.
    assert {branch for row_set, _verifier, branch in rows if row_set == 'non-empty'} == {'B'}


def test_an_absent_verifier_return_does_not_close_the_round():
    rows = _branch_rows(_step_4())
    step_4 = _flat(_step_4())

    assert _selected_branch(rows, 'empty', 'does-not-close') == 'B'
    assert _selected_branch(rows, 'empty', 'closes') == 'A'
    absent_rows = [(row_set, branch) for row_set, verifier, branch in rows if 'no parseable return' in verifier]
    assert absent_rows, 'no branch row names an absent verifier return'
    assert {branch for _set, branch in absent_rows} == {'B'}
    assert 'a verifier return that is absent or unparseable never closes the round' in step_4


def test_branch_table_reader_refuses_an_undocumented_round():
    rows = [('empty', '`acceptance: accepted` AND `may_close: yes`', 'A')]

    assert _selected_branch(rows, 'empty', 'closes') == 'A'
    with pytest.raises(AssertionError):
        _selected_branch(rows, 'non-empty', 'closes')


# ---------------------------------------------------------------------------
# The behavioural check, the screening question, the on-demand contract read
# ---------------------------------------------------------------------------


def _checks_region() -> str:
    text = _read(_WORKFLOW_DOC)
    return text[text.index('### Step 3: Apply') : text.index('### Dispatched-envelope output')]


def test_the_behavioural_check_names_its_four_defect_classes():
    region = _checks_region()
    check = region[region.index('**Behavioural defect check**') :]

    assert '`changed_code_units`' in check
    for defect_class in (
        'fail_open_on_unreadable',
        'untruthful_result',
        'unexercised_branch',
        'unguarded_shared_write',
    ):
        assert f'`{defect_class}`' in check
    assert 'Handle the `changed_code_units` list (check 19) and the `structural` family lists first' in region


def test_the_screening_question_is_stated_once_before_the_numbered_checks():
    text = _read(_WORKFLOW_DOC)
    question = 'is this line an operative statement?'

    assert text.count(question) == 1
    assert text.index(question) < text.index('\n1. **Symmetric pair test-coverage check**')
    assert 'is **screened out**: its check is not applied and no finding is recorded' in text


@pytest.mark.parametrize('trigger', _RETIRED_FILING_TRIGGERS)
def test_a_wording_only_filing_trigger_is_gone(trigger):
    assert trigger not in _flat(_read(_WORKFLOW_DOC))


@pytest.mark.parametrize(
    ('check', 'consequence'),
    [
        ('3. **Wording disambiguation check**', 'would plausibly take a wrong action'),
        ('4. **Duplication scan**', 'give different instructions for the same situation'),
        ('8. **Same-document consistency check**', 'the two cannot both be followed'),
    ],
)
def test_a_reworded_prose_check_files_on_the_consequence(check, consequence):
    region = _checks_region()
    start = region.index(check)
    entry = region[start : region.index('\n\n', start)]

    assert consequence in entry


def test_contract_drift_is_checked_only_for_files_under_examination():
    region = _flat(_checks_region())

    assert 'AND has at least one candidate this round examined' in region
    assert "A `contract_sources` entry none of whose file's candidates was examined is not read" in region


def test_the_changed_units_count_toward_the_gate_and_the_verdicts():
    text = _flat(_read(_WORKFLOW_DOC))

    assert (
        "`total_candidates` as the surfacer's emitted `counts.total` plus its emitted `counts.changed_code_units`"
        in text
    )
    assert 'No finding AND `total_candidates == 0`' in text
    assert 'SELECTED in this order: blocking, then advisory-only, then zero-observation' in text


def test_contract_sources_are_read_on_demand_and_the_coverage_is_reported():
    step_2a = _flat(_section(_read(_WORKFLOW_DOC), '#### Step 2a: Cross-reference setup'))

    assert 'Read them in full' not in step_2a
    assert 'when, and only when, a candidate under examination belongs to the file that entry governs' in step_2a
    assert 'only when a hunk under examination emits or changes that schema' in step_2a
    assert '`contract_sources_listed`' in step_2a
    assert '`contract_sources_read`' in step_2a


# ---------------------------------------------------------------------------
# The texts that said the opposite
# ---------------------------------------------------------------------------


def test_only_blocking_findings_must_be_addressed_before_push():
    step_4 = _flat(_step_4())

    assert 'every finding is addressed' not in _flat(_read(_WORKFLOW_DOC))
    assert 'every blocking finding is addressed before push' in step_4
    assert "Advisory findings are the author's to take or leave" in step_4


def test_the_number_of_checks_is_not_restated_across_the_document():
    body = _body(_read(_WORKFLOW_DOC)).lower()
    checks = len(re.findall(r'^\d+\. \*\*', _checks_region(), flags=re.MULTILINE))
    assert checks in _NUMBER_WORDS, f'derived {checks} numbered checks — extend the word table'

    # The count is derived from the numbered block; neither its word nor the
    # word for a neighbouring count may be scattered through the prose.
    assert body.count(f'{_NUMBER_WORDS[checks]} ') <= 1
    assert f'{_NUMBER_WORDS[checks - 1]} ' not in body
    assert len(re.findall(rf'\b{checks} (?:cognitive |numbered )?checks\b', body)) <= 1
