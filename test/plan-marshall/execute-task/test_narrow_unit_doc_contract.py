# SPDX-License-Identifier: FSL-1.1-ALv2
"""The two step documents state one order for a module test run a leaf cannot run whole.

``execute-task/SKILL.md`` (implementation profile, Step 5 (b)) and
``phase-5-execute/SKILL.md`` (the orchestrator-tier yield paragraph) both tell a
leaf what to do when the wider ``module-tests`` run resolves to the orchestrator
tier: resolve the scope, run the narrow units inline, then hand back only what
is left. They are read by the same agent in the same run, so they name the same
resolver fields and state the three parts in the same order.
"""

from pathlib import Path

import pytest
from _test_scope_divergence import resolve_test_scope

from conftest import MARKETPLACE_ROOT

_SKILLS = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'

#: The three parts of the order, as both documents word them, in order.
ORDER_MARKERS = ('resolve the scope', 'run the narrow units inline', 'hand back only')

#: The resolver fields both documents name, as inline code.
RESOLVER_FIELDS = ('narrow_units', 'narrow_unit_module', 'recommended_target', 'execution_tier')

#: The module placeholder a narrow-unit resolve carries in both documents. It is
#: the field that is non-null whenever a narrow unit is listed.
NARROW_UNIT_RESOLVE = '--module {narrow_unit_module}'

#: The placeholder a narrow-unit resolve must never carry: that field is null
#: whenever the wider run is the whole tree, while narrow units are still listed.
NULLABLE_MODULE_RESOLVE = '--module {recommended_target}'

#: ``(document, start, end)`` — the passage of each document that states the
#: order runs from the first occurrence of ``start`` up to the next ``end``.
PASSAGES = (
    (_SKILLS / 'execute-task' / 'SKILL.md', '**(b) Task-scoped breakable-test gate**', '**Seam reconciliation**'),
    (_SKILLS / 'phase-5-execute' / 'SKILL.md', '- **`tier == orchestrator`**', '\n'),
)

#: What the amended Step 5 (b) answers, read alone, to: the module test command
#: resolves to the orchestrator tier and the resolver lists one narrow unit.
WORKED_CASE_ANSWER = 'run the narrow unit inline, then hand back the module-wide run'


def _passage(document: Path, start: str, end: str) -> str:
    """Return the text of ``document`` from ``start`` up to the next ``end``."""
    text = document.read_text(encoding='utf-8')
    begin = text.index(start)
    return text[begin : text.index(end, begin + len(start))]


def contract_gaps(passage: str) -> list[str]:
    """Name every part of the contract ``passage`` does not state.

    A marker counts only when it follows the marker before it, so a passage
    that mentions all three parts in another order still reports a gap.
    """
    gaps = []
    position = 0
    for marker in ORDER_MARKERS:
        found = passage.find(marker, position)
        if found == -1:
            gaps.append(f'order: {marker}')
        else:
            position = found + len(marker)
    gaps.extend(f'field: {field}' for field in RESOLVER_FIELDS if f'`{field}`' not in passage)
    return gaps


@pytest.mark.parametrize('document,start,end', PASSAGES, ids=[document.parent.name for document, _, _ in PASSAGES])
def test_document_states_the_order_and_names_the_resolver_fields(document: Path, start: str, end: str) -> None:
    """Each document states the three parts in order and names all three fields."""
    passage = _passage(document, start, end)

    gaps = contract_gaps(passage)

    assert gaps == [], f'{document.parent.name}/SKILL.md does not state: {gaps}'


@pytest.mark.parametrize('document,start,end', PASSAGES, ids=[document.parent.name for document, _, _ in PASSAGES])
def test_a_narrow_unit_is_resolved_against_the_field_that_is_never_null_beside_it(
    document: Path, start: str, end: str
) -> None:
    """Each document resolves a narrow unit against ``narrow_unit_module``, never ``recommended_target``."""
    passage = _passage(document, start, end)

    assert NARROW_UNIT_RESOLVE in passage
    assert NULLABLE_MODULE_RESOLVE not in passage


def test_the_resolver_names_the_narrow_unit_module_when_the_recommended_target_is_null() -> None:
    """The field the documents interpolate is set in the case the nullable one is not.

    One bundle module plus a path no target owns: the whole tree is warranted,
    so ``recommended_target`` is null, and a narrow unit is still listed.
    """
    skill_path = 'marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md'

    resolution = resolve_test_scope(
        [skill_path, 'doc/developer/build.adoc'],
        [],
        frozenset({'plan-marshall'}),
        test_directories=frozenset({'plan-marshall/execute-task'}),
        bundle_modules=frozenset({'plan-marshall'}),
    )

    assert resolution.narrow_units == ('plan-marshall/execute-task',)
    assert resolution.recommended_target is None
    assert resolution.narrow_unit_module == 'plan-marshall'


def test_a_passage_that_drops_one_part_reports_exactly_that_part() -> None:
    """Matched control: removing any one marker or field is reported, and nothing else is."""
    document, start, end = PASSAGES[0]
    passage = _passage(document, start, end)
    removals = [(marker, f'order: {marker}') for marker in ORDER_MARKERS]
    removals += [(f'`{field}`', f'field: {field}') for field in RESOLVER_FIELDS]

    reported = [contract_gaps(passage.replace(needle, '')) for needle, _ in removals]

    assert reported == [[gap] for _, gap in removals]


def test_a_passage_that_states_the_parts_out_of_order_reports_a_gap() -> None:
    """The three parts are an order: the same words in another sequence do not satisfy it."""
    in_order = ', '.join(ORDER_MARKERS) + ' ' + ' '.join(f'`{field}`' for field in RESOLVER_FIELDS)
    reversed_order = ', '.join(reversed(ORDER_MARKERS)) + ' ' + ' '.join(f'`{field}`' for field in RESOLVER_FIELDS)

    assert contract_gaps(in_order) == []
    assert contract_gaps(reversed_order) != []


def test_step_5b_answers_the_worked_case_on_its_own() -> None:
    """Step 5 (b) says, in one sentence, to run the narrow unit inline and hand back the module-wide run."""
    document, start, end = PASSAGES[0]

    passage = _passage(document, start, end)

    assert WORKED_CASE_ANSWER in passage
