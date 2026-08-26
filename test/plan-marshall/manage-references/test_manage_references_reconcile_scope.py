#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``manage-references reconcile-scope``.

The verb compares three independently-asserted file sets — the RECORDED
declaration (``references.affected_files``), the DECLARED derivation (the
outline's structured mutation-intent paths) and the REALIZED footprint (the
shared whole-chain resolver) — pairwise, by symmetric difference. Four
properties carry the weight, each pinned by a test that fails for its own
reason:

* **Symmetric difference, never cardinality** — two equal-size sets sharing no
  member are maximally different, and a size check calls them identical.
* **Three states over a comparison, not two** — ``agree`` needs both sides
  established AND at least one member; two established-but-empty sides report
  ``vacuous``, because a zero difference over nothing certifies nothing.
* **An unmeasured pair publishes no counts at all** — key ABSENCE, so a consumer
  branching on the count finds nothing rather than a zero it reads as clean.
* **Every count names its population** — a side's size, a derivation's walk.
"""

from __future__ import annotations

import json
from argparse import Namespace

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-references', 'manage-references.py')

_reconcile = load_script_module(
    'plan-marshall', 'manage-references', '_cmd_reconcile_scope.py', '_refs_cmd_reconcile_scope'
)

cmd_reconcile_scope = _reconcile.cmd_reconcile_scope
get_references_path = _reconcile.get_references_path

PLAN_ID = 'test-plan'

#: Equal-size sets sharing 22 members and disagreeing on 7 each way.
_SHARED = [f'src/shared_{index:02d}.py' for index in range(22)]
_ONLY_RECORDED = [f'src/only_recorded_{index:02d}.py' for index in range(7)]
_ONLY_DECLARED = [f'src/only_declared_{index:02d}.py' for index in range(7)]
_RECORDED_29 = _SHARED + _ONLY_RECORDED
_DECLARED_29 = _SHARED + _ONLY_DECLARED


def _ns(plan_id: str = PLAN_ID) -> Namespace:
    """Build the Namespace the verb parses from ``--plan-id``."""
    return Namespace(plan_id=plan_id)


def _plan_dir(plan_id: str = PLAN_ID):
    """The plan directory holding both the references file and the outline."""
    path = get_references_path(plan_id).parent
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_references(payload: dict, plan_id: str = PLAN_ID) -> None:
    """Write ``references.json`` verbatim, so key ABSENCE is expressible."""
    (_plan_dir(plan_id) / 'references.json').write_text(json.dumps(payload), encoding='utf-8')


def _write_outline(content: str, plan_id: str = PLAN_ID) -> None:
    """Write ``solution_outline.md`` into the plan directory."""
    (_plan_dir(plan_id) / 'solution_outline.md').write_text(content, encoding='utf-8')


def _outline_declaring(*bullets: str) -> str:
    """One deliverable declaring ``bullets`` under the flat declaration heading.

    No bullet yields a heading PRESENT with nothing under it, which establishes
    the derived side with an empty set.
    """
    body = '\n'.join(bullets)
    return (
        '# Solution: fixture\n\n## Deliverables\n\n### 1. A deliverable\n\n'
        f'**Affected files:**\n{body}\n\n'
        '**Verification:**\n- Command: verify\n- Criteria: passes\n'
    )


def _mutation_bullets(paths) -> tuple[str, ...]:
    """Render ``paths`` as write-intent bullets."""
    return tuple(f'- `{path}` (write-replace)' for path in paths)


def _reconcile_with(recorded, declared, plan_id: str = PLAN_ID) -> dict:
    """Establish sides A and B from real artifacts, then run the verb."""
    _write_references({'branch': 'feature/test', 'affected_files': list(recorded)}, plan_id)
    _write_outline(_outline_declaring(*_mutation_bullets(declared)), plan_id)
    result: dict = cmd_reconcile_scope(_ns(plan_id))
    return result


def _recorded_side_absent() -> dict:
    """Run the verb with side A unbuilt and side B established."""
    _write_references({'branch': 'feature/test'})
    _write_outline(_outline_declaring(*_mutation_bullets(['src/declared.py'])))
    result: dict = cmd_reconcile_scope(_ns())
    return result


class TestMatchedLengthNegativeControl:
    """Equal-size sets that disagree must FAIL the comparison."""

    def test_equal_length_sets_that_disagree_report_a_non_zero_difference(self, plan_context):
        """Two 29-entry sets sharing 22 members disagree, not agree.

        The control for the whole verb: a size or count assertion passes this
        input, since both sides are the same size. Only the two difference
        directions separate them, totalling 14.
        """
        result = _reconcile_with(_RECORDED_29, _DECLARED_29)

        assert len(_RECORDED_29) == len(_DECLARED_29) == 29
        assert result['a_count'] == result['b_count'] == 29
        assert result['a_b_state'] == _reconcile.PAIR_DISAGREE
        assert result['a_b_symmetric_difference_count'] == 14

    def test_each_difference_direction_is_a_named_list_with_its_own_size(self, plan_context):
        """A pair reporting one direction cannot tell a declaration that dropped
        seven paths from one that invented seven.
        """
        result = _reconcile_with(_RECORDED_29, _DECLARED_29)

        assert sorted(result['a_not_b']) == sorted(_ONLY_RECORDED)
        assert sorted(result['b_not_a']) == sorted(_ONLY_DECLARED)
        assert result['a_not_b_count'] == 7
        assert result['b_not_a_count'] == 7

    def test_a_disjoint_pair_of_equal_size_is_maximally_different(self, plan_context):
        """Sharing NO member is the extreme of the same shape."""
        recorded = [f'src/left_{index}.py' for index in range(4)]
        declared = [f'src/right_{index}.py' for index in range(4)]

        result = _reconcile_with(recorded, declared)

        assert result['a_count'] == result['b_count'] == 4
        assert result['a_b_state'] == _reconcile.PAIR_DISAGREE
        assert result['a_b_symmetric_difference_count'] == 8


class TestPairStateTrichotomy:
    """``agree`` / ``disagree`` / ``vacuous`` are three distinct verdicts."""

    def test_identical_non_empty_sides_agree(self, plan_context):
        """The positive control: equal, non-empty, both established."""
        paths = ['src/one.py', 'src/two.py']

        result = _reconcile_with(paths, paths)

        assert result['a_b_state'] == _reconcile.PAIR_AGREE
        assert result['a_b_symmetric_difference_count'] == 0

    def test_two_established_but_empty_sides_are_vacuous_not_agreeing(self, plan_context):
        """The matched negative control for agreement: the same zero symmetric
        difference as the agreeing pair above, and not agreement.
        """
        _write_references({'branch': 'feature/test', 'affected_files': []})
        _write_outline(_outline_declaring())

        result = cmd_reconcile_scope(_ns())

        assert result['a_count'] == 0
        assert result['b_count'] == 0
        assert result['a_b_symmetric_difference_count'] == 0
        assert result['a_b_state'] == _reconcile.PAIR_VACUOUS
        assert result['a_b_state'] != _reconcile.PAIR_AGREE

    def test_one_empty_side_against_a_populated_one_disagrees(self, plan_context):
        """An empty side is a measurement, so it compares rather than abstains."""
        result = _reconcile_with([], ['src/declared.py'])

        assert result['a_b_state'] == _reconcile.PAIR_DISAGREE
        assert result['b_not_a'] == ['src/declared.py']
        assert result['a_not_b'] == []


class TestUnmeasuredPublishesNoCounts:
    """Key absence, never a zero a consumer would read as a clean comparison."""

    def test_an_unmeasured_pair_publishes_no_symmetric_difference_count(self, plan_context):
        """The count key a consumer branches on is ABSENT, not zero."""
        result = _recorded_side_absent()

        assert result['a_b_state'] == _reconcile.PAIR_UNMEASURED
        assert 'a_b_symmetric_difference_count' not in result

    def test_an_unmeasured_pair_publishes_neither_difference_direction(self, plan_context):
        """Neither the lists nor their sizes are emitted for a pair that never ran."""
        result = _recorded_side_absent()

        for key in ('a_not_b', 'b_not_a', 'a_not_b_count', 'b_not_a_count'):
            assert key not in result

    def test_an_unmeasured_pair_names_the_sides_that_were_not_built(self, plan_context):
        """The pair states WHICH side was missing, so the gap is attributable."""
        result = _recorded_side_absent()

        assert result['a_b_unmeasured_sides'] == [_reconcile.SIDE_A]

    def test_an_unmeasured_side_publishes_a_reason_and_no_count(self, plan_context):
        """Exactly one of ``{side}_count`` / ``{side}_unmeasured_reason`` is present."""
        result = _recorded_side_absent()

        assert result['a_state'] == _reconcile.SIDE_UNMEASURED
        assert result['a_unmeasured_reason'] == _reconcile.REASON_AFFECTED_FILES_ABSENT
        assert 'a_count' not in result


class TestRecordedSideKeyStates:
    """``affected_files`` absent and ``affected_files: []`` are different answers."""

    def test_a_missing_affected_files_key_leaves_the_side_unmeasured(self, plan_context):
        """Nothing was ever recorded, so there is no declaration to compare."""
        _write_references({'branch': 'feature/test'})
        _write_outline(_outline_declaring())

        result = cmd_reconcile_scope(_ns())

        assert result['a_state'] == _reconcile.SIDE_UNMEASURED
        assert result['a_unmeasured_reason'] == _reconcile.REASON_AFFECTED_FILES_ABSENT

    def test_an_empty_affected_files_list_establishes_the_side(self, plan_context):
        """The matched counterpart of the absent key above: the same empty set,
        the opposite verdict, separated only by whether the key exists.
        """
        _write_references({'branch': 'feature/test', 'affected_files': []})
        _write_outline(_outline_declaring())

        result = cmd_reconcile_scope(_ns())

        assert result['a_state'] == _reconcile.SIDE_ESTABLISHED
        assert result['a_count'] == 0
        assert 'a_unmeasured_reason' not in result

    def test_an_absent_references_file_is_its_own_reason(self, plan_context):
        """A file that does not exist is told apart from one missing the key."""
        _write_outline(_outline_declaring())

        result = cmd_reconcile_scope(_ns())

        assert result['a_unmeasured_reason'] == _reconcile.REASON_REFERENCES_ABSENT

    def test_a_non_list_affected_files_value_is_unmeasured(self, plan_context):
        """A corrupt key yields no path set, and says so rather than comparing."""
        _write_references({'branch': 'feature/test', 'affected_files': 'not-a-list'})
        _write_outline(_outline_declaring())

        result = cmd_reconcile_scope(_ns())

        assert result['a_unmeasured_reason'] == _reconcile.REASON_AFFECTED_FILES_NOT_A_LIST


class TestDeclaredSide:
    """Side B derives the MUTATION half, and publishes the walk behind it."""

    def test_a_read_intent_path_does_not_enter_the_derived_side(self, plan_context):
        """The near-miss control: the read-intent path is declared in the same
        outline, under the same heading, and still reaches neither side.
        """
        _write_references({'branch': 'feature/test', 'affected_files': ['src/mutated.py']})
        _write_outline(
            _outline_declaring('- `src/mutated.py` (write-replace)', '- `src/consulted.py` (read)')
        )

        result = cmd_reconcile_scope(_ns())

        assert result['b_count'] == 1
        assert result['a_b_state'] == _reconcile.PAIR_AGREE

    def test_the_derived_side_publishes_the_walk_it_was_computed_from(self, plan_context):
        """The derivation's count names the population it walked."""
        result = _reconcile_with(['src/one.py'], ['src/one.py', 'src/two.py'])

        assert result['b_count'] == 2
        assert result['deliverables_scanned'] == 1
        assert result['headings_found'] == 1
        assert result['bullets_parsed'] == 2

    def test_an_unparsed_outline_reports_the_measured_zero_population(self, plan_context):
        """The outline was READ, so its zero population is a measurement."""
        _write_references({'branch': 'feature/test', 'affected_files': ['src/one.py']})
        _write_outline('# Solution\n\n## Summary\n\nProse with no deliverables.\n')

        result = cmd_reconcile_scope(_ns())

        assert result['b_unmeasured_reason'] == _reconcile.REASON_NO_DELIVERABLES_PARSED
        assert result['deliverables_scanned'] == 0

    def test_an_absent_outline_publishes_no_population_at_all(self, plan_context):
        """The matched counterpart of the measured zero above: reporting
        ``deliverables_scanned: 0`` here would claim a walk that never happened.
        """
        _write_references({'branch': 'feature/test', 'affected_files': ['src/one.py']})

        result = cmd_reconcile_scope(_ns())

        assert result['b_unmeasured_reason'] == _reconcile.REASON_OUTLINE_NOT_FOUND
        assert 'deliverables_scanned' not in result


class TestRealizedSideAndRunCoverage:
    """Side C resolves through the shared chain; the run grades its own reach."""

    def test_a_captured_footprint_establishes_the_realized_side(self, plan_context):
        """The recorded capture resolves, and compares against the declaration."""
        _write_references({
            'branch': 'feature/test',
            'affected_files': ['src/one.py', 'src/two.py'],
            'realized_footprint': ['src/two.py', 'src/three.py'],
        })
        _write_outline(_outline_declaring(*_mutation_bullets(['src/one.py', 'src/two.py'])))

        result = cmd_reconcile_scope(_ns())

        assert result['c_state'] == _reconcile.SIDE_ESTABLISHED
        assert result['c_count'] == 2
        assert result['a_c_state'] == _reconcile.PAIR_DISAGREE
        assert result['a_not_c'] == ['src/one.py']
        assert result['c_not_a'] == ['src/three.py']

    def test_an_unresolvable_footprint_leaves_the_realized_side_unmeasured(self, plan_context):
        """No tier answered, so the side carries a reason instead of an empty set."""
        result = _reconcile_with(['src/one.py'], ['src/one.py'])

        assert result['c_state'] == _reconcile.SIDE_UNMEASURED
        assert result['c_unmeasured_reason'] == _reconcile.REASON_FOOTPRINT_UNRESOLVED
        assert 'c_count' not in result

    def test_the_run_grades_its_coverage_against_its_own_rosters(self, plan_context):
        """Every coverage count is published beside the population behind it."""
        result = _reconcile_with(['src/one.py'], ['src/one.py'])

        assert result['side_count'] == len(_reconcile.SIDES)
        assert result['established_side_count'] == 2
        assert result['pair_count'] == len(_reconcile.PAIRS)
        assert result['measured_pair_count'] == 1
        assert result['unmeasured_pair_count'] == 2

    def test_the_rosters_the_sources_and_the_state_population_are_published(self, plan_context):
        """A reader learns what was supposed to be compared and from where, and
        the pair-state population is enumerable so a consumer can branch
        exhaustively over the verdicts a pair may carry.
        """
        result = _reconcile_with(['src/one.py'], ['src/one.py'])

        assert result['sides'] == list(_reconcile.SIDES)
        assert result['pairs'] == ['a_b', 'a_c', 'b_c']
        assert result['primary_pair'] == 'a_b'
        for side in _reconcile.SIDES:
            assert result[f'{side}_source'] == _reconcile.SIDE_SOURCES[side]
        for pair in result['pairs']:
            assert result[f'{pair}_state'] in _reconcile.PAIR_STATES

    def test_the_verb_reports_success_even_when_every_side_is_unmeasured(self, plan_context):
        """An audit that could not evaluate something reports that; it does not fail."""
        result = cmd_reconcile_scope(_ns())

        assert result['status'] == 'success'
        assert result['established_side_count'] == 0
        assert result['measured_pair_count'] == 0

    def test_the_verb_writes_nothing(self, plan_context):
        """Read-only: the references file is byte-identical after the run."""
        _write_references({'branch': 'feature/test', 'affected_files': ['src/one.py']})
        _write_outline(_outline_declaring(*_mutation_bullets(['src/two.py'])))
        before = (_plan_dir() / 'references.json').read_text(encoding='utf-8')

        cmd_reconcile_scope(_ns())

        assert (_plan_dir() / 'references.json').read_text(encoding='utf-8') == before


def test_cli_reconcile_scope_is_registered_on_the_live_argparse_surface():
    """A handler wired into the dispatch map but never registered as a subparser
    is unreachable from the CLI while every direct-import test still passes.
    """
    result = run_script(SCRIPT_PATH, '--help')

    assert result.returncode == 0
    assert 'reconcile-scope' in result.stdout


def test_cli_reconcile_scope_reports_the_equal_length_disagreement(plan_context):
    """End-to-end: the CLI accepts the verb and carries the verdict out as TOON."""
    from toon_parser import parse_toon

    _write_references({'branch': 'feature/test', 'affected_files': _RECORDED_29})
    _write_outline(_outline_declaring(*_mutation_bullets(_DECLARED_29)))

    result = run_script(SCRIPT_PATH, 'reconcile-scope', '--plan-id', PLAN_ID)

    assert result.success, f'Script failed: {result.stderr}'
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['a_b_state'] == _reconcile.PAIR_DISAGREE
    assert data['a_b_symmetric_difference_count'] == 14
