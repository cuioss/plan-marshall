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
    assert start != -1, f'{_STEP_DOC.name} carries no `{heading}` heading'
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
