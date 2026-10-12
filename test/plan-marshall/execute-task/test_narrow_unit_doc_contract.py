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

#: The branch Step 5 (b) decides first: the whole tree, whatever the scope holds.
WHOLE_TREE_BRANCH = '**`divergence_possible: true`**'

#: The only condition under which Step 5 (b) runs no pytest — both halves.
NO_PYTEST_BRANCH = '**`divergence_possible: false` and `scoped_modules` is empty**'

#: What Step 5 (b) tells a leaf whose own change list is empty, in order: omit
#: the flag, resolve from the plan alone, and never hand the resolver an empty list.
EMPTY_CHANGE_LIST_MARKERS = (
    'omit `--changed-paths`',
    'resolve with `--plan-id` alone',
    'Never pass an empty `--changed-paths`',
)

#: The refusal Step 5 (b) names for an empty list — the resolver's own error code.
EMPTY_CHANGE_LIST_REFUSAL = '`empty_changed_paths`'

#: The plan-footprint-only resolve the empty-change-list case runs: the
#: ``resolve-test-scope`` call carrying ``--plan-id`` and no ``--changed-paths``.
PLAN_ONLY_RESOLVE = 'resolve-test-scope \\\n        --plan-id "{plan_id}"'


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


def test_step_5b_decides_the_whole_tree_before_it_skips_pytest_for_an_empty_scope() -> None:
    """Step 5 (b) skips pytest only for an empty scope that cannot diverge, and decides the whole tree first."""
    document, start, end = PASSAGES[0]
    passage = _passage(document, start, end)

    whole_tree = passage.find(WHOLE_TREE_BRANCH)
    no_pytest = passage.find(NO_PYTEST_BRANCH)

    assert -1 < whole_tree < no_pytest


def empty_change_list_gaps(passage: str) -> list[str]:
    """Name every part of the empty-change-list instruction ``passage`` does not state.

    The three markers count only in order, and the refusal and the plan-only
    resolve must each appear, so a passage that drops or reorders any part
    reports it.
    """
    gaps = []
    position = 0
    for marker in EMPTY_CHANGE_LIST_MARKERS:
        found = passage.find(marker, position)
        if found == -1:
            gaps.append(f'instruction: {marker}')
        else:
            position = found + len(marker)
    if EMPTY_CHANGE_LIST_REFUSAL not in passage:
        gaps.append(f'refusal: {EMPTY_CHANGE_LIST_REFUSAL}')
    if PLAN_ONLY_RESOLVE not in passage:
        gaps.append('resolve: plan-only')
    return gaps


def test_step_5b_tells_an_empty_change_list_to_resolve_from_the_plan_footprint() -> None:
    """Step 5 (b) says: omit the flag, resolve with ``--plan-id`` alone, never pass an empty list."""
    document, start, end = PASSAGES[0]
    passage = _passage(document, start, end)

    assert empty_change_list_gaps(passage) == []


def test_step_5b_states_the_empty_change_list_instruction_before_it_branches() -> None:
    """The instruction sits with the resolve, ahead of the branch that runs no pytest.

    A leaf reads the branches in order, so an instruction placed after the
    no-pytest branch would be read only once that branch had already decided.
    """
    document, start, end = PASSAGES[0]
    passage = _passage(document, start, end)

    instruction = passage.find(EMPTY_CHANGE_LIST_MARKERS[0])
    no_pytest = passage.find(NO_PYTEST_BRANCH)

    assert -1 < instruction < no_pytest


def test_a_passage_that_drops_one_empty_change_list_part_reports_exactly_that_part() -> None:
    """Matched control: removing any one part of the instruction is reported, and nothing else is."""
    document, start, end = PASSAGES[0]
    passage = _passage(document, start, end)
    removals = [(marker, f'instruction: {marker}') for marker in EMPTY_CHANGE_LIST_MARKERS]
    removals += [(EMPTY_CHANGE_LIST_REFUSAL, f'refusal: {EMPTY_CHANGE_LIST_REFUSAL}')]
    removals += [(PLAN_ONLY_RESOLVE, 'resolve: plan-only')]

    reported = [empty_change_list_gaps(passage.replace(needle, '')) for needle, _ in removals]

    assert reported == [[gap] for _, gap in removals]


def test_an_empty_scope_alone_does_not_tell_nothing_to_run_from_the_whole_tree() -> None:
    """A footprint no target owns and an empty footprint both resolve to no module; only the first can diverge."""
    registered = frozenset({'plan-marshall'})

    unowned = resolve_test_scope(['pyproject.toml'], [], registered, bundle_modules=registered)
    empty = resolve_test_scope([], [], registered, bundle_modules=registered)

    assert (unowned.scoped_modules, unowned.divergence_possible) == ((), True)
    assert (empty.scoped_modules, empty.divergence_possible) == ((), False)
