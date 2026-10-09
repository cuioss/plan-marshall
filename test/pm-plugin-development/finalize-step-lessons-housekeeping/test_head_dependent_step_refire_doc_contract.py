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
