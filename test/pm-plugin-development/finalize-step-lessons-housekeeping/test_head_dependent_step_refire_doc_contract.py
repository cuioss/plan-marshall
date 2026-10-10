# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-contract tests for the lessons-housekeeping finalize step's footprint read.

``references.modified_files`` is a retired field: a ``manage-references get
--field modified_files`` call returns ``field_retired``. The housekeeping step
derives the plan's realized footprint with ``compute-footprint`` instead.

Two independent assertions guard that, because neither sees what the other does:

* a **call-shape** sweep over every markdown document in the two skill trees,
  which catches an instruction to read the retired field wherever it appears;
* a **name-keyed** check over the three passages that describe the housekeeping
  step in prose, which catches a statement the call-shape sweep cannot see.

A third group pins the step's decision-log contract (Step 6): one entry per
lesson the firing changed — removed, promoted, adapted — and exactly one
aggregate entry per firing that counts the lessons examined, carried over and
retained, naming the recorded HEAD on a delta firing. A retained lesson gets no
entry of its own.

A fourth group pins that the currency standard, the extension-point contract
and the two step documents tell one story: the standard names the third lever,
what separates it from delta-scoping and which step uses or refused it; the
extension point makes every no-change-list outcome a full run; and each step's
refusal section still declares no surface while the housekeeping delta rule
claims no dispatcher skip.

A fifth group pins what the housekeeping step records after a per-lesson
action failed: Step 7 withholds the ``classified_at`` fact, each of the three
failure rows states that consequence, and the two downgrade rows do not.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT

_STEP_ID = 'project:finalize-step-lessons-housekeeping'
_RETIRED_FIELD = 'modified_files'

_PROJECT_SKILLS_ROOT = PROJECT_ROOT / '.claude' / 'skills'
_BUNDLE_SKILLS_ROOT = PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills'
_SWEPT_ROOTS = (_PROJECT_SKILLS_ROOT, _BUNDLE_SKILLS_ROOT)

_STEP_DOC = _PROJECT_SKILLS_ROOT / 'finalize-step-lessons-housekeeping' / 'SKILL.md'
_FINALIZE_STANDARDS = _BUNDLE_SKILLS_ROOT / 'phase-6-finalize' / 'standards'
_VERDICT_CURRENCY_DOC = _FINALIZE_STANDARDS / 'verdict-currency.md'
_PUSHABILITY_DOC = _FINALIZE_STANDARDS / 'source-edit-pushability.md'

# The retired read as a caller writes it: the flag, then the field, on one line
# or `=`-joined. A prose mention of the field name alone is deliberately NOT
# matched here — the name-keyed passage check below owns that.
_RETIRED_READ = re.compile(r'--field[ \t=]+modified_files\b')

_COMPUTE_FOOTPRINT_ERRORS = (
    'worktree_not_found',
    'references_not_found',
    'not_a_git_worktree',
    'git_error',
    'files_out_refused',
    'files_out_unwritable',
)


def _markdown_docs(root: Path) -> list[Path]:
    return sorted(root.rglob('*.md'))


def _retired_read_hits(root: Path) -> list[str]:
    """Return ``path:line`` for every line under ``root`` that reads the retired field."""
    hits: list[str] = []
    for doc in _markdown_docs(root):
        for number, line in enumerate(doc.read_text(encoding='utf-8').splitlines(), start=1):
            if _RETIRED_READ.search(line):
                hits.append(f'{doc.relative_to(PROJECT_ROOT)}:{number}')
    return hits


def _footprint_call_block(content: str) -> str:
    """Return the fenced block of the step document that invokes ``compute-footprint``."""
    blocks: list[str] = re.findall(r'```bash\n(.*?)```', content, re.DOTALL)
    matching = [block for block in blocks if 'compute-footprint' in block]
    assert len(matching) == 1, (
        f'expected exactly one fenced compute-footprint call in {_STEP_DOC.name}, found {len(matching)}'
    )
    return matching[0]


def _whole_document(content: str) -> list[str]:
    return [content]


def _table_rows_naming_step(content: str) -> list[str]:
    return [line for line in content.splitlines() if line.startswith('|') and _STEP_ID in line]


def _paragraphs_naming_step(content: str) -> list[str]:
    return [paragraph for paragraph in re.split(r'\n\s*\n', content) if _STEP_ID in paragraph]


@pytest.mark.parametrize('root', _SWEPT_ROOTS, ids=lambda root: str(root.relative_to(PROJECT_ROOT)))
def test_swept_tree_enumerates_documents(root: Path) -> None:
    """Non-vacuity guard: a sweep over an empty tree would pass having read nothing."""
    # Act
    docs = _markdown_docs(root)

    # Assert
    assert docs, f'{root} enumerated no markdown document, so the retired-read sweep would be vacuous'


@pytest.mark.parametrize('root', _SWEPT_ROOTS, ids=lambda root: str(root.relative_to(PROJECT_ROOT)))
def test_no_document_reads_the_retired_field(root: Path) -> None:
    # Act
    hits = _retired_read_hits(root)

    # Assert
    assert not hits, (
        f'`--field {_RETIRED_FIELD}` reads a retired field (the call returns field_retired); '
        f'use `manage-references compute-footprint` instead. Hits: {hits}'
    )


def test_retired_read_pattern_matches_the_call_shape() -> None:
    """Positive control: the sweep's pattern must match the shape it claims to forbid."""
    # Arrange
    single_line = 'manage-references get --plan-id {plan_id} --field modified_files'
    continued = '  --plan-id {plan_id} --field modified_files'
    prose = 'the plan outcome is reasoned from modified_files'
    other_field = 'manage-references get --plan-id {plan_id} --field affected_files'

    # Act / Assert
    assert _RETIRED_READ.search(single_line)
    assert _RETIRED_READ.search(continued)
    assert not _RETIRED_READ.search(prose)
    assert not _RETIRED_READ.search(other_field)


def test_step_footprint_read_names_compute_footprint_with_both_flags() -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    block = _footprint_call_block(content)

    # Assert
    assert 'plan-marshall:manage-references:manage-references compute-footprint' in block
    assert '--plan-id {plan_id}' in block
    assert '--worktree-path {worktree_path}' in block


@pytest.mark.parametrize('error', _COMPUTE_FOOTPRINT_ERRORS)
def test_step_names_each_compute_footprint_error(error: str) -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    rows = [line for line in content.splitlines() if line.startswith(f'| `{error}` |')]

    # Assert
    assert len(rows) == 1, f'{_STEP_DOC.name} must carry exactly one action row for `{error}`, found {len(rows)}'
    action = rows[0].rstrip('|').split('|')[-1].strip()
    assert action, f'the `{error}` row in {_STEP_DOC.name} states no action'


@pytest.mark.parametrize(
    ('doc', 'locate'),
    [
        (_STEP_DOC, _whole_document),
        (_VERDICT_CURRENCY_DOC, _table_rows_naming_step),
        (_PUSHABILITY_DOC, _paragraphs_naming_step),
    ],
    ids=['step-document', 'verdict-currency-refusal-row', 'pushability-worked-case'],
)
def test_passage_describing_the_step_does_not_name_the_retired_field(
    doc: Path, locate: Callable[[str], list[str]]
) -> None:
    # Arrange
    content = doc.read_text(encoding='utf-8')
    assert _STEP_ID in content, f'{doc.name} no longer names {_STEP_ID}, so its passage cannot be located'

    # Act
    passages = locate(content)

    # Assert
    assert passages, f'no passage naming {_STEP_ID} was located in {doc.name}'
    offending = [passage for passage in passages if _RETIRED_FIELD in passage]
    assert not offending, f'{doc.name} still describes {_STEP_ID} in terms of `{_RETIRED_FIELD}`: {offending}'


# ---------------------------------------------------------------------------
# Step 6 — the decision-log contract
# ---------------------------------------------------------------------------

_MUTATING_OUTCOMES = ('removed', 'promoted', 'adapted')
_AGGREGATE_COUNTS = ('examined', 'carried_over', 'retained')
_AGGREGATE_MARKER = 'firing summary:'

# A per-lesson entry as the step writes it: an outcome alternation in braces,
# followed by the lesson id placeholder.
_PER_LESSON_ENTRY = re.compile(r'\{([a-z|]+)\}\s+\{id\}')

# An instruction to give a retained lesson an entry of its own, in either of
# the two shapes it can take: `retained` offered as a per-lesson outcome, or
# prose telling the reader to log the decision not to act.
_PER_LESSON_RETAIN = re.compile(
    r'\{[a-z|]*\bretained\b[a-z|]*\}\s+\{id\}|no-action decision|every\*{0,2} deliberate retain'
)


def _section(content: str, heading: str) -> str:
    """Return the body of the section opened by ``heading``, up to the next peer heading."""
    level = heading.split(' ', 1)[0]
    start = content.find(f'\n{heading}')
    assert start != -1, f'the document carries no `{heading}` heading'
    body_start = content.index('\n', start + 1)
    peers = [match.start() for match in re.finditer(rf'\n#{{1,{len(level)}}} ', content[body_start:])]
    end = body_start + peers[0] if peers else len(content)
    return content[body_start:end]


def _step6(content: str) -> str:
    return _section(content, '### Step 6')


def _decision_calls(section: str) -> list[str]:
    """Return every fenced ``manage-logging decision`` call in ``section``."""
    blocks: list[str] = re.findall(r'```bash\n(.*?)```', section, re.DOTALL)
    return [block for block in blocks if 'manage-logging' in block and 'decision' in block.split()]


def _aggregate_calls(section: str) -> list[str]:
    return [call for call in _decision_calls(section) if _AGGREGATE_MARKER in call]


def test_step6_carries_decision_log_calls() -> None:
    """Non-vacuity guard: every Step 6 assertion below ranges over these calls."""
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    calls = _decision_calls(_step6(content))

    # Assert
    assert len(calls) == 3, (
        f'Step 6 of {_STEP_DOC.name} should carry one per-lesson call and two aggregate calls '
        f'(full run, delta firing); found {len(calls)}'
    )


def test_step6_per_lesson_entry_covers_exactly_the_three_mutating_outcomes() -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')
    per_lesson = [call for call in _decision_calls(_step6(content)) if _AGGREGATE_MARKER not in call]
    assert len(per_lesson) == 1, f'expected exactly one per-lesson decision call in Step 6, found {len(per_lesson)}'

    # Act
    alternations = _PER_LESSON_ENTRY.findall(per_lesson[0])

    # Assert
    assert len(alternations) == 1, f'the per-lesson call must name its outcome once, found {alternations}'
    assert set(alternations[0].split('|')) == set(_MUTATING_OUTCOMES)


@pytest.mark.parametrize('outcome', ['removal', 'promote-then-retire', 'adaptation'])
def test_step6_requires_one_entry_for_each_mutating_outcome(outcome: str) -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    section = _step6(content)

    # Assert
    assert f'**every** {outcome}' in section, f'Step 6 no longer requires an entry for every {outcome}'


def test_document_does_not_require_a_per_lesson_entry_for_a_retain() -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    hits = [
        f'{number}: {line.strip()}'
        for number, line in enumerate(content.splitlines(), start=1)
        if _PER_LESSON_RETAIN.search(line)
    ]

    # Assert
    assert not hits, f'{_STEP_DOC.name} still instructs a per-lesson entry for a retained lesson: {hits}'


def test_per_lesson_retain_pattern_matches_the_shapes_it_forbids() -> None:
    """Positive control: the pattern must match the retired instructions and nothing current."""
    # Arrange
    retired_call = '--message "(step) {removed|promoted|adapted|retained} {id}: {reason}"'
    retired_prose = 'Leave untouched (bias to retain) and log the no-action decision.'
    retired_step = '**every** adaptation, **and every** deliberate retain.'
    current_call = '--message "(step) {removed|promoted|adapted} {id}: {reason}"'
    current_aggregate = '--message "(step) firing summary: examined={E} carried_over={X} retained={K} mode=delta"'

    # Act / Assert
    assert _PER_LESSON_RETAIN.search(retired_call)
    assert _PER_LESSON_RETAIN.search(retired_prose)
    assert _PER_LESSON_RETAIN.search(retired_step)
    assert not _PER_LESSON_RETAIN.search(current_call)
    assert not _PER_LESSON_RETAIN.search(current_aggregate)


@pytest.mark.parametrize('count', _AGGREGATE_COUNTS)
def test_step6_aggregate_entry_names_each_count_on_every_route(count: str) -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    aggregates = _aggregate_calls(_step6(content))

    # Assert
    assert len(aggregates) == 2, f'expected a full-run and a delta aggregate call, found {len(aggregates)}'
    for call in aggregates:
        assert f'{count}=' in call, f'an aggregate entry in Step 6 does not name `{count}`: {call.strip()}'


def test_step6_aggregate_entry_names_the_recorded_head_on_a_delta_firing_only() -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')
    aggregates = _aggregate_calls(_step6(content))

    # Act
    delta = [call for call in aggregates if 'mode=delta' in call]
    full = [call for call in aggregates if 'mode=full' in call]

    # Assert
    assert len(delta) == 1 and len(full) == 1, 'Step 6 must carry one delta and one full-run aggregate call'
    assert 'recorded_head={recorded_head}' in delta[0]
    assert 'recorded_head' not in full[0], 'a full run has no recorded HEAD to start from'
    assert 'carried_over=0' in full[0], 'a full run carries nothing over'


def test_step6_states_the_aggregate_entry_is_written_exactly_once_per_firing() -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    section = _step6(content)

    # Assert
    assert 'Exactly one aggregate entry per firing' in section


def test_purpose_does_not_promise_a_per_retain_record() -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    purpose = _section(content, '## Purpose')

    # Assert
    assert 'or deliberate retain — is recorded' not in purpose
    assert 'not logged per lesson' in purpose
    assert 'aggregate entry' in purpose


def test_coverage_ambiguous_row_writes_no_entry_of_its_own() -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    rows = [line for line in content.splitlines() if line.startswith('| Coverage ambiguous')]

    # Assert
    assert len(rows) == 1, f'expected exactly one `Coverage ambiguous` row, found {len(rows)}'
    action = rows[0].rstrip('|').split('|')[-1]
    assert 'manage-logging decision' not in action
    assert 'aggregate' in action
    assert 'retained' in action


# ---------------------------------------------------------------------------
# The currency standard, the extension-point contract and the two step documents
# ---------------------------------------------------------------------------

_PLUGIN_DOCTOR_STEP_ID = 'project:finalize-step-plugin-doctor'
_PLUGIN_DOCTOR_DOC = _PROJECT_SKILLS_ROOT / 'finalize-step-plugin-doctor' / 'SKILL.md'
_EXT_POINT_DOC = _BUNDLE_SKILLS_ROOT / 'extension-api' / 'standards' / 'ext-point-finalize-step.md'

_LEVERS_HEADING = '## Three levers, two columns'
_REFUSAL_HEADING = '### Verdict-input surface — deliberately undeclared'
_DELTA_RULE_HEADING = '### Step 2b'
_CHANGE_LIST_HEADING = '#### Reading the change list since the last `done` firing'

_THIRD_LEVER = 'Change-list narrowing'
_COST_COLUMN = 'the cost of EACH re-run'
_NO_CHANGE_LIST_OUTCOMES = ('first_firing', 'last_firing_not_done', 'diff_unavailable')
_STEP_DOCS = {_STEP_ID: _STEP_DOC, _PLUGIN_DOCTOR_STEP_ID: _PLUGIN_DOCTOR_DOC}

# A claim that the dispatcher skips the step. `skip Steps 3 to 5` — the step
# skipping part of its own body — is deliberately not matched.
_DISPATCHER_SKIP_CLAIM = re.compile(r'dispatcher(?:-side)?\s+(?:may\s+|can\s+|will\s+)?skips?\b', re.IGNORECASE)


def _levers_section() -> str:
    return _section(_VERDICT_CURRENCY_DOC.read_text(encoding='utf-8'), _LEVERS_HEADING)


def _unwrapped(text: str) -> str:
    """Collapse whitespace so a phrase is found wherever the prose happens to wrap."""
    return ' '.join(text.split())


def _lever_rows(section: str) -> dict[str, list[str]]:
    """Map each lever named in the levers table to the cells of its row."""
    rows: dict[str, list[str]] = {}
    for line in section.splitlines():
        match = re.match(r'\|\s*\*\*([^*]+)\*\*\s+—', line)
        if match:
            rows[match.group(1)] = [cell.strip() for cell in line.strip().strip('|').split('|')]
    return rows


def _frontmatter(doc: Path) -> str:
    match = re.match(r'^---\s*\n(.*?)\n---', doc.read_text(encoding='utf-8'), re.DOTALL)
    assert match, f'no YAML frontmatter found in {doc}'
    return match.group(1)


def test_levers_table_names_three_levers() -> None:
    # Act
    rows = _lever_rows(_levers_section())

    # Assert
    assert set(rows) == {'Delta-scoping', 'Re-stale classification', _THIRD_LEVER}


def test_third_lever_bounds_the_cost_of_each_rerun_not_their_number() -> None:
    # Arrange
    section = _levers_section()

    # Act
    rows = _lever_rows(section)

    # Assert
    assert rows[_THIRD_LEVER][1] == _COST_COLUMN
    assert rows['Delta-scoping'][1] == _COST_COLUMN
    assert rows['Re-stale classification'][1] == 'the NUMBER of re-runs'
    prose = _unwrapped(section)
    assert 'neither reduces the number of re-runs' in prose
    assert 'Only re-stale classification bounds the number' in prose


def test_levers_section_does_not_present_three_independent_levers() -> None:
    # Act
    section = _unwrapped(_levers_section())

    # Assert
    assert 'two columns, not three' in section
    assert 'they are independent' not in section
    assert 'not three independent' in section


@pytest.mark.parametrize(
    'phrase',
    ['`head_at_completion`', '`changed-paths`', '`classified_at`', 'not in the tree difference at all'],
    ids=['step-record-anchor', 'read-through-changed-paths', 'carry-over-fact', 'selection-outside-the-diff'],
)
def test_levers_section_names_what_separates_the_third_lever_from_delta_scoping(phrase: str) -> None:
    # Act
    section = _unwrapped(_levers_section())

    # Assert
    assert phrase in section, f'the levers section no longer states `{phrase}`'


@pytest.mark.parametrize(
    ('step', 'disposition'),
    [(_STEP_ID, 'Used'), (_PLUGIN_DOCTOR_STEP_ID, 'Examined and refused')],
    ids=['housekeeping-uses-it', 'plugin-doctor-refused-it'],
)
def test_levers_section_names_each_step_with_its_disposition(step: str, disposition: str) -> None:
    # Arrange
    section = _levers_section()

    # Act
    rows = [line for line in section.splitlines() if line.startswith('|') and f'`{step}`' in line]

    # Assert
    assert len(rows) == 1, f'the levers section must name {step} in exactly one row, found {len(rows)}'
    assert rows[0].startswith(f'| **{disposition}** |')


@pytest.mark.parametrize(
    ('step', 'cited'),
    [
        (_STEP_ID, '### Step 2b: Select what this firing judges (the delta rule)'),
        (_PLUGIN_DOCTOR_STEP_ID, '#### The narrower rule that was examined, and why it is refused'),
    ],
    ids=['housekeeping', 'plugin-doctor'],
)
def test_section_the_levers_table_cites_exists_in_the_step_document(step: str, cited: str) -> None:
    # Arrange
    title = cited.split(' ', 1)[1]
    assert f'§ "{title}"' in _levers_section(), f'the levers section no longer cites § "{title}"'

    # Act
    headings = _STEP_DOCS[step].read_text(encoding='utf-8').splitlines()

    # Assert
    assert cited in headings, f'{_STEP_DOCS[step].name} carries no `{cited}` heading'


def test_standard_documents_the_changed_paths_verb_beside_classify() -> None:
    # Arrange
    content = _VERDICT_CURRENCY_DOC.read_text(encoding='utf-8')

    # Act
    blocks: list[str] = re.findall(r'```bash\n(.*?)```', content, re.DOTALL)
    calls = {block.split('verdict_currency', 1)[1].split()[0]: block for block in blocks if 'verdict_currency' in block}

    # Assert
    assert set(calls) == {'classify', 'changed-paths'}
    for flag in ('--plan-id', '--step', '--worktree-path'):
        assert flag in calls['changed-paths'], f'the documented changed-paths call omits {flag}'


def test_standard_still_states_that_no_step_declares_a_surface() -> None:
    # Act
    content = _VERDICT_CURRENCY_DOC.read_text(encoding='utf-8')

    # Assert
    assert 'No finalize step currently declares `verdict_inputs`' in content
    assert 'admitting a *derived* surface' in content


@pytest.mark.parametrize('outcome', _NO_CHANGE_LIST_OUTCOMES)
def test_extension_point_makes_each_no_change_list_outcome_a_full_run(outcome: str) -> None:
    # Arrange
    section = _section(_EXT_POINT_DOC.read_text(encoding='utf-8'), _CHANGE_LIST_HEADING)

    # Act
    rows = [line for line in section.splitlines() if line.startswith(f'| `{outcome}` |')]

    # Assert
    assert len(rows) == 1, f'expected exactly one `{outcome}` row in the change-list section, found {len(rows)}'
    assert rows[0].rstrip('|').split('|')[-1].strip() == 'Run in full'


def test_extension_point_forbids_reading_a_missing_change_list_as_no_change() -> None:
    # Act
    section = _section(_EXT_POINT_DOC.read_text(encoding='utf-8'), _CHANGE_LIST_HEADING)

    # Assert
    assert 'MAY read which tracked paths changed' in section
    assert 'MUST NOT read a missing `changed_paths` as "nothing changed"' in section
    assert 'not a `verdict_inputs` declaration' in section
    assert 'buys no dispatcher-side skip' in section


def test_housekeeping_names_the_commit_restamp_as_a_route_into_its_third_full_run_condition() -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    delta_rule = _section(content, _DELTA_RULE_HEADING)

    # Assert
    assert 'There are exactly three full-run conditions' in delta_rule
    assert 'The commit re-stamp is a known, accepted route into the third condition' in delta_rule
    assert '`classified_at_absent`' in delta_rule


@pytest.mark.parametrize('step', sorted(_STEP_DOCS), ids=lambda step: step.split(':', 1)[1])
def test_refusal_section_still_says_no_surface_is_declared(step: str) -> None:
    # Arrange
    content = _STEP_DOCS[step].read_text(encoding='utf-8')

    # Act
    refusal = _section(content, _REFUSAL_HEADING)

    # Assert
    assert 'declares **no** `verdict_inputs`' in refusal
    assert 'every HEAD advance' in refusal


@pytest.mark.parametrize('step', sorted(_STEP_DOCS), ids=lambda step: step.split(':', 1)[1])
def test_step_document_declares_no_verdict_inputs_in_its_frontmatter(step: str) -> None:
    # Act
    keys = [line.split(':', 1)[0] for line in _frontmatter(_STEP_DOCS[step]).splitlines() if re.match(r'^\w', line)]

    # Assert
    assert 'head_dependent' in keys, f'{step} frontmatter was not read: {keys}'
    assert 'verdict_inputs' not in keys


def test_housekeeping_delta_rule_never_claims_a_dispatcher_skip() -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    delta_rule = _section(content, _DELTA_RULE_HEADING)
    refusal = _section(content, _REFUSAL_HEADING)

    # Assert
    assert not _DISPATCHER_SKIP_CLAIM.search(delta_rule), 'Step 2b claims the dispatcher skips the step'
    assert 'buys no dispatcher-side skip' in refusal
    assert 'delta rule (Step 2b)' in refusal


def test_dispatcher_skip_pattern_matches_a_claim_and_not_the_steps_own_skip() -> None:
    """Positive control for the pattern the delta-rule assertion relies on."""
    # Act / Assert
    assert _DISPATCHER_SKIP_CLAIM.search('so the dispatcher skips the step on a clean delta')
    assert _DISPATCHER_SKIP_CLAIM.search('this buys a dispatcher-side skip')
    assert not _DISPATCHER_SKIP_CLAIM.search('skip Steps 3 to 5 entirely')
    assert not _DISPATCHER_SKIP_CLAIM.search('the dispatcher commits the edit and re-stamps the step record')


@pytest.mark.parametrize(
    'named',
    ['`targets-scope-invalid`', '`marketplace/targets/*/__init__.py`', '`.claude-plugin/plugin.json`'],
    ids=['rule', 'target-registrations', 'bundle-manifest'],
)
def test_plugin_doctor_refusal_names_its_counter_example(named: str) -> None:
    # Arrange
    content = _PLUGIN_DOCTOR_DOC.read_text(encoding='utf-8')

    # Act
    refusal = _section(content, _REFUSAL_HEADING)

    # Assert
    assert named in refusal, f'the plugin-doctor refusal section no longer names {named}'


def test_plugin_doctor_refusal_admits_no_skip_predicate() -> None:
    # Arrange
    content = _PLUGIN_DOCTOR_DOC.read_text(encoding='utf-8')

    # Act
    refusal = _section(content, _REFUSAL_HEADING)

    # Assert
    assert 'No skip predicate is admitted' in refusal
    assert 'every HEAD advance re-runs the gate' in refusal


# ---------------------------------------------------------------------------
# Step 7 — the carry-over anchor after a failed per-lesson action
# ---------------------------------------------------------------------------

_WITHHOLD_MARKER = 'Withhold `classified_at` after a failed per-lesson action'
_WITHHOLD_CONSEQUENCE = 'Step 7 withholds `classified_at`'
_FAILED_ACTIONS = ('removal', 'promotion', 'adaptation')

_FAILED_ACTION_ROWS = (
    '| `manage-lessons remove` failure on one lesson |',
    '| Promotion `Edit` failure (Step 4b.1) on one lesson |',
    '| Adaptation `Edit` failure on one lesson |',
)
_DOWNGRADE_ROWS = (
    '| `manage-lessons remove` **evidence rejection** on one lesson',
    '| Independent-reconfirmation gate failure (Step 4.1 or Step 4b.2) on one lesson |',
)


def _error_handling_row(content: str, opening: str) -> str:
    """Return the action cell of the one Error Handling row that opens with ``opening``."""
    table = _section(content, '## Error Handling')
    rows = [line for line in table.splitlines() if line.startswith(opening)]
    assert len(rows) == 1, f'expected exactly one Error Handling row opening `{opening}`, found {len(rows)}'
    return rows[0].rstrip('|').split('|')[-1]


def _withhold_paragraph(content: str) -> str:
    """Return the Step 7 paragraph that states when ``classified_at`` is withheld."""
    paragraphs = [
        paragraph
        for paragraph in re.split(r'\n\s*\n', _section(content, '### Step 7'))
        if _WITHHOLD_MARKER in paragraph
    ]
    assert len(paragraphs) == 1, (
        f'Step 7 of {_STEP_DOC.name} must state once that classified_at is withheld after a failed '
        f'per-lesson action, found {len(paragraphs)} such paragraph(s)'
    )
    return paragraphs[0]


@pytest.mark.parametrize('action', _FAILED_ACTIONS)
def test_step7_withholds_classified_at_after_each_failed_per_lesson_action(action: str) -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    paragraph = _withhold_paragraph(content)

    # Assert
    assert action in paragraph, f'Step 7 no longer withholds classified_at after a failed {action}'
    assert 'omit `--fact classified_at=…`' in paragraph
    assert '`classified_at_absent`' in paragraph


def test_step7_keeps_the_rest_of_the_record_when_it_withholds_classified_at() -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    paragraph = _withhold_paragraph(content)

    # Assert
    assert '`--outcome done`' in paragraph
    assert '`--fact work_performed=true`' in paragraph
    assert 'downgrades, not failed actions' in paragraph


def test_step7_omit_sentence_names_the_failed_action_beside_the_missing_payload() -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    sentences = [
        paragraph
        for paragraph in re.split(r'\n\s*\n', _section(content, '### Step 7'))
        if paragraph.startswith('Omit `--fact classified_at=…` only when')
    ]

    # Assert
    assert len(sentences) == 1, f'expected exactly one `Omit … only when` sentence in Step 7, found {len(sentences)}'
    for action in _FAILED_ACTIONS:
        assert action in sentences[0], f'the `Omit … only when` sentence does not name a failed {action}'
    assert 'no payload at all' in sentences[0]


@pytest.mark.parametrize('opening', _FAILED_ACTION_ROWS, ids=['remove', 'promotion-edit', 'adaptation-edit'])
def test_failed_per_lesson_action_row_states_classified_at_is_withheld(opening: str) -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    action = _error_handling_row(content, opening)

    # Assert
    assert _WITHHOLD_CONSEQUENCE in action, f'the row opening `{opening}` does not say classified_at is withheld'
    assert 'the next firing judges the whole corpus' in action


@pytest.mark.parametrize('opening', _DOWNGRADE_ROWS, ids=['evidence-rejection', 'reconfirmation-gate'])
def test_downgrade_row_does_not_withhold_classified_at(opening: str) -> None:
    """Negative control: a downgrade ends in a trim or a retain, so it is no failed action."""
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    action = _error_handling_row(content, opening)

    # Assert
    assert _WITHHOLD_CONSEQUENCE not in action
    assert 'A downgrade is not a failed action' in action


def test_step_completes_row_shows_classified_at_as_conditional() -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    action = _error_handling_row(content, '| Step completes |')

    # Assert
    assert '--fact work_performed=true`' in action
    assert 'Add `--fact classified_at={firing_started_at}` only when' in action
    for failed in _FAILED_ACTIONS:
        assert failed in action, f'the `Step completes` row does not name a failed {failed}'


def test_delta_rule_names_the_failed_action_route_beside_the_commit_restamp() -> None:
    # Arrange
    content = _STEP_DOC.read_text(encoding='utf-8')

    # Act
    delta_rule = _section(content, _DELTA_RULE_HEADING)

    # Assert
    assert 'A failed per-lesson action is a second route' in delta_rule
    assert 'Step 7 therefore withholds the `classified_at` fact' in delta_rule
    assert 'downgrades that end in a trim or a deliberate retain, not failed actions' in delta_rule
