#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Matched silence controls for ``manage-references reconcile-scope``.

A reconciliation verb earns its keep by staying quiet when there is nothing to
report. That property is the easy one to fake: a check that stopped examining its
input is also silent, and so is one whose sides were never built. These controls
pair the two halves so neither shape can pass for the other:

* the must-NOT-fire half gives the verb a plan whose declared derivation and
  realized footprint LEGITIMATELY agree — the same non-empty path set reached by
  two independent routes, an outline walk and a resolved footprint — and requires
  the verdict to be agreement rather than merely a zero difference;
* the must-FIRE half changes exactly one member of the realized side, keeping its
  CARDINALITY identical, and requires the same pair to report disagreement with
  both directions named.

Equal cardinality across the pair is what makes the fire half a genuine near-miss
rather than a restatement: a size comparison passes it, and only the two
difference directions separate the sets.

Every control asserts the population it exercised — how many sides were
established, how many pairs were compared, and how many members each side
carried. Silence over an unbuilt side, an unparsed outline or an unresolvable
footprint therefore fails here instead of reading as a clean reconciliation,
which is the one way a quiet verdict can lie.
"""

from __future__ import annotations

import json
from argparse import Namespace

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-references', 'manage-references.py')

_reconcile = load_script_module(
    'plan-marshall', 'manage-references', '_cmd_reconcile_scope.py', '_refs_reconcile_scope_control'
)

PLAN_ID = 'agreement-control-plan'

#: The members both routes reach. Non-empty on purpose: agreement over two empty
#: sides is the vacuous verdict, not the silent one, and would certify nothing.
_SHARED = [f'src/shared_{index:02d}.py' for index in range(5)]

#: The declared derivation, and — for the agreeing half — the realized footprint too.
_DECLARED = [*_SHARED, 'src/declared_only.py']

#: The realized footprint of the FIRING half. Same size as ``_DECLARED``, one
#: member swapped, so a cardinality check calls the two identical.
_REALIZED_DISAGREEING = [*_SHARED, 'src/realized_only.py']


def _ns(plan_id: str = PLAN_ID) -> Namespace:
    return Namespace(plan_id=plan_id)


def _plan_dir(plan_id: str = PLAN_ID):
    path = _reconcile.get_references_path(plan_id).parent
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_references(payload: dict, plan_id: str = PLAN_ID) -> None:
    """Write ``references.json`` verbatim, so key absence stays expressible."""
    (_plan_dir(plan_id) / 'references.json').write_text(json.dumps(payload), encoding='utf-8')


def _write_outline(content: str, plan_id: str = PLAN_ID) -> None:
    (_plan_dir(plan_id) / 'solution_outline.md').write_text(content, encoding='utf-8')


def _outline_declaring(paths) -> str:
    """One deliverable declaring ``paths`` as write-intent bullets."""
    body = '\n'.join(f'- `{path}` (write-replace)' for path in paths)
    return (
        '# Solution: agreement control\n\n## Deliverables\n\n### 1. A deliverable\n\n'
        f'**Affected files:**\n{body}\n\n'
        '**Verification:**\n- Command: verify\n- Criteria: passes\n'
    )


def _run(recorded, declared, realized) -> dict:
    """Establish all three sides from real artifacts, then run the verb.

    The realized side is established through ``references.realized_footprint`` —
    the capture tier of the shared resolver — because a fixture plan has no live
    worktree for the chain's first tier to find.
    """
    _write_references(
        {
            'branch': 'feature/agreement-control',
            'affected_files': list(recorded),
            'realized_footprint': list(realized),
        }
    )
    _write_outline(_outline_declaring(declared))
    result: dict = _reconcile.cmd_reconcile_scope(_ns())
    return result


#: The pair this deliverable names: the DECLARED derivation against the REALIZED
#: footprint. Read from the module's own side constants rather than spelled as a
#: literal, so a renamed side cannot leave this control pointing at nothing.
_DECLARED_REALIZED_PAIR = f'{_reconcile.SIDE_B}_{_reconcile.SIDE_C}'


# =============================================================================
# The fixtures' own shape — what makes each half a control rather than a repeat
# =============================================================================


def test_the_two_realized_fixtures_are_the_same_size_and_differ_by_one_each_way():
    """The firing half is a near-miss, not an obviously different input.

    Were the disagreeing fixture merely larger, the pair would separate on size
    alone and the control would stop exercising the symmetric-difference path it
    exists to protect.
    """
    assert len(_DECLARED) == len(_REALIZED_DISAGREEING) == 6
    assert set(_DECLARED) != set(_REALIZED_DISAGREEING)
    assert set(_DECLARED) - set(_REALIZED_DISAGREEING) == {'src/declared_only.py'}
    assert set(_REALIZED_DISAGREEING) - set(_DECLARED) == {'src/realized_only.py'}


def test_the_agreeing_fixture_is_non_empty_so_agreement_cannot_be_vacuous():
    """Agreement over two empty sides is a different verdict entirely."""
    assert len(_DECLARED) > 0


def test_the_pair_under_control_is_declared_by_the_verb(plan_context):
    """The pair name is derived from the verb's own roster, not hand-written."""
    result = _run(_DECLARED, _DECLARED, _DECLARED)

    assert _DECLARED_REALIZED_PAIR in result['pairs']
    assert result[f'{_DECLARED_REALIZED_PAIR}_state'] in _reconcile.PAIR_STATES


# =============================================================================
# Must NOT fire — declared and realized legitimately agree
# =============================================================================


class TestLegitimateAgreementStaysSilent:
    """A plan whose sides genuinely match produces no disagreement anywhere."""

    def test_the_declared_and_realized_sides_agree_rather_than_merely_not_differing(
        self, plan_context
    ):
        """Agreement is the verdict, not a zero difference read as one.

        ``vacuous`` carries the same zero, so asserting the count alone would pass
        for a run that compared nothing.
        """
        result = _run(_DECLARED, _DECLARED, _DECLARED)

        assert result[f'{_DECLARED_REALIZED_PAIR}_state'] == _reconcile.PAIR_AGREE
        assert result[f'{_DECLARED_REALIZED_PAIR}_symmetric_difference_count'] == 0
        assert result[f'{_DECLARED_REALIZED_PAIR}_state'] != _reconcile.PAIR_VACUOUS

    def test_no_pair_reports_a_disagreement_when_all_three_sides_match(self, plan_context):
        """Silence across the whole report, checked pair by pair over the roster."""
        result = _run(_DECLARED, _DECLARED, _DECLARED)

        states = {pair: result[f'{pair}_state'] for pair in result['pairs']}

        assert set(states.values()) == {_reconcile.PAIR_AGREE}
        assert len(states) == len(_reconcile.PAIRS) == 3

    def test_the_silent_run_names_the_population_it_actually_compared(self, plan_context):
        """The counts that separate a silent comparison from an absent one.

        Every side established, every pair measured, and each side carrying the
        fixture's six members: a run that quietly stopped examining its input
        fails one of these instead of reporting a clean reconciliation.
        """
        result = _run(_DECLARED, _DECLARED, _DECLARED)

        assert result['established_side_count'] == result['side_count'] == 3
        assert result['measured_pair_count'] == result['pair_count'] == 3
        assert result['unmeasured_pair_count'] == 0
        for side in _reconcile.SIDES:
            assert result[f'{side}_state'] == _reconcile.SIDE_ESTABLISHED
            assert result[f'{side}_count'] == 6

    def test_the_silent_run_still_publishes_the_outline_walk_behind_the_derivation(
        self, plan_context
    ):
        """The derived side names the walk it came from even when nothing differs.

        A silent verdict whose derivation walked no deliverable would be silence
        about an empty population.
        """
        result = _run(_DECLARED, _DECLARED, _DECLARED)

        assert result['deliverables_scanned'] == 1
        assert result['headings_found'] == 1
        assert result['bullets_parsed'] == 6

    def test_both_difference_directions_are_present_and_empty(self, plan_context):
        """Empty lists, not absent keys: the comparison ran and found nothing.

        The absent-key shape is reserved for a pair that was never compared, so
        the two states stay distinguishable from the outside.
        """
        result = _run(_DECLARED, _DECLARED, _DECLARED)

        assert result[f'{_reconcile.SIDE_B}_not_{_reconcile.SIDE_C}'] == []
        assert result[f'{_reconcile.SIDE_C}_not_{_reconcile.SIDE_B}'] == []
        assert result[f'{_reconcile.SIDE_B}_not_{_reconcile.SIDE_C}_count'] == 0
        assert result[f'{_reconcile.SIDE_C}_not_{_reconcile.SIDE_B}_count'] == 0


# =============================================================================
# Must FIRE — the matched counterpart, one member swapped
# =============================================================================


class TestTheMatchedDisagreementFires:
    """The same fixture, one realized member swapped, must break the silence."""

    def test_an_equal_size_realized_side_that_differs_reports_disagreement(self, plan_context):
        """The near-miss: identical sizes, and the verdict still separates them."""
        result = _run(_DECLARED, _DECLARED, _REALIZED_DISAGREEING)

        assert result[f'{_reconcile.SIDE_B}_count'] == result[f'{_reconcile.SIDE_C}_count'] == 6
        assert result[f'{_DECLARED_REALIZED_PAIR}_state'] == _reconcile.PAIR_DISAGREE
        assert result[f'{_DECLARED_REALIZED_PAIR}_symmetric_difference_count'] == 2

    def test_each_direction_of_the_disagreement_is_named(self, plan_context):
        """A single-direction report cannot tell a dropped path from an added one."""
        result = _run(_DECLARED, _DECLARED, _REALIZED_DISAGREEING)

        assert result[f'{_reconcile.SIDE_B}_not_{_reconcile.SIDE_C}'] == ['src/declared_only.py']
        assert result[f'{_reconcile.SIDE_C}_not_{_reconcile.SIDE_B}'] == ['src/realized_only.py']

    def test_the_firing_run_examined_the_same_population_as_the_silent_one(self, plan_context):
        """The halves differ in verdict only — never in how much they examined.

        Equal coverage across the pair is what licenses reading the silent half as
        a measured agreement rather than as a smaller, quieter run.
        """
        silent = _run(_DECLARED, _DECLARED, _DECLARED)
        firing = _run(_DECLARED, _DECLARED, _REALIZED_DISAGREEING)

        for key in ('established_side_count', 'measured_pair_count', 'deliverables_scanned'):
            assert silent[key] == firing[key]
        assert silent[f'{_DECLARED_REALIZED_PAIR}_state'] != firing[f'{_DECLARED_REALIZED_PAIR}_state']


# =============================================================================
# The silence is not manufactured by an unbuilt side
# =============================================================================


class TestSilenceIsNotAnUnbuiltSide:
    """An unmeasured pair is quiet too — and must never look like agreement."""

    def test_an_unresolvable_realized_side_is_unmeasured_not_agreeing(self, plan_context):
        """Dropping the capture leaves the footprint unresolvable, not empty.

        The matched control for the silent half: the same outline, the same
        declaration, and a verdict that must NOT be agreement.
        """
        _write_references(
            {'branch': 'feature/agreement-control', 'affected_files': list(_DECLARED)}
        )
        _write_outline(_outline_declaring(_DECLARED))

        result = _reconcile.cmd_reconcile_scope(_ns())

        assert result[f'{_reconcile.SIDE_C}_state'] == _reconcile.SIDE_UNMEASURED
        assert result[f'{_reconcile.SIDE_C}_unmeasured_reason'] == _reconcile.REASON_FOOTPRINT_UNRESOLVED
        assert result[f'{_DECLARED_REALIZED_PAIR}_state'] == _reconcile.PAIR_UNMEASURED
        assert result[f'{_DECLARED_REALIZED_PAIR}_state'] != _reconcile.PAIR_AGREE

    def test_an_unmeasured_pair_publishes_no_difference_count_to_misread(self, plan_context):
        """Key absence is what stops a consumer reading the quiet pair as clean."""
        _write_references(
            {'branch': 'feature/agreement-control', 'affected_files': list(_DECLARED)}
        )
        _write_outline(_outline_declaring(_DECLARED))

        result = _reconcile.cmd_reconcile_scope(_ns())

        assert f'{_DECLARED_REALIZED_PAIR}_symmetric_difference_count' not in result
        assert result['unmeasured_pair_count'] == 2
        assert result['measured_pair_count'] == 1


# =============================================================================
# The verdict survives the CLI boundary
# =============================================================================


def test_the_cli_carries_the_silent_agreement_verdict_out_as_toon(plan_context):
    """End-to-end: agreement reaches a consumer as agreement, with its counts.

    An in-process verdict that the serializer flattened into an ambiguous shape
    would leave the consumer unable to tell a silent pair from an unmeasured one.
    """
    from toon_parser import parse_toon

    _write_references(
        {
            'branch': 'feature/agreement-control',
            'affected_files': list(_DECLARED),
            'realized_footprint': list(_DECLARED),
        }
    )
    _write_outline(_outline_declaring(_DECLARED))

    result = run_script(SCRIPT_PATH, 'reconcile-scope', '--plan-id', PLAN_ID)

    assert result.success, f'Script failed: {result.stderr}'
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data[f'{_DECLARED_REALIZED_PAIR}_state'] == _reconcile.PAIR_AGREE
    assert data[f'{_DECLARED_REALIZED_PAIR}_symmetric_difference_count'] == 0
    assert data['established_side_count'] == 3
    assert data['measured_pair_count'] == 3
