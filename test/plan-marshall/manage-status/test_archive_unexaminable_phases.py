#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""An unexaminable ``phases`` structure is not an empty one — the scan, and what archive does with it.

``_status_core.in_progress_phases`` used to answer two different questions with one
value. A malformed ``phases`` structure and a plan with nothing open both produced
``[]``, so ``cmd_archive``'s ``if not in_progress_phases(status)`` wrote
``current_phase: complete`` onto a record it had failed to read, and the ``census``
verb published ``open_phase_count: 0`` over the same record. The permanent archived
record then asserted a completion nobody established.

Why the shapes are enumerated rather than sampled
-------------------------------------------------
``TestTheScanDiscriminates`` sweeps two named populations — the shapes that cannot be
classified and the shapes that can — and asserts the verdict over every member of
each. A handful of examples would cover the shapes their author happened to think of;
the defect being fixed was invisible precisely because the case that mattered was not
among them. Both population sizes are asserted before the sweeps, so a verdict of
"no failures" is known to have been drawn from a real population rather than from an
enumeration that produced nothing.

The two populations are each other's matched control. Asserting only that malformed
input reports ``examinable: False`` would pass equally against a scan that reported
it for EVERYTHING — which would degrade every cohort and refuse every archive, the
same conflation in the opposite direction.

Why the type refuses ``bool()``
-------------------------------
``test_the_scan_has_no_truth_value`` pins the raise for BOTH an examinable and an
unexaminable scan. There is no truthiness rule that answers ``if not scan:``
correctly for both states, so the type answers neither: a falsy unexaminable result
reinstates the original defect at the first such guard, and a truthy one silently
inverts the completion gate. The raise is what turns the stale idiom into a loud
failure at the call site instead of a false claim in a permanent record.

Why the archive cells come in a matched pair plus a control
-----------------------------------------------------------
``TestArchiveOfAnUnexaminableRecord`` pins the two directions the archiver must
distinguish — a no-reason archive REFUSES (the findings gate cannot establish that
``6-finalize`` is closed, and a guard whose job is to refuse fails closed), while a
deliberate ``--reason`` archive proceeds but PRESERVES the existing lifecycle state.
``test_a_well_formed_record_with_no_open_phase_still_completes`` is the load-bearing
control: without it both cells pass equally against an archiver that refused
everything, or that never wrote ``complete`` at all.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from typing import Any

import _status_core
import pytest
from _manage_status_transition_fixtures import cmd_archive, cmd_create, cmd_update_phase

#: Stands for "the ``phases`` key is not present at all", which no value can express.
_ABSENT = object()

#: The shapes whose open-phase set cannot be established. Each is a whole ``phases``
#: value, and each fails for its own structural reason, so a fix that handles only
#: one of them leaves the others reporting a confident empty set.
_UNEXAMINABLE_SHAPES: dict[str, Any] = {
    'key_absent': _ABSENT,
    'explicit_null': None,
    'a_mapping_not_a_list': {'1-init': 'in_progress'},
    'a_bare_string': 'in_progress',
    'a_row_that_is_a_string': [{'name': '1-init', 'status': 'done'}, 'not-a-phase-record'],
    'a_row_that_is_null': [{'name': '1-init', 'status': 'done'}, None],
    'a_row_with_no_status': [{'name': '1-init', 'status': 'done'}, {'name': '2-refine'}],
    'a_row_outside_the_vocabulary': [{'name': '1-init', 'status': 'done'}, {'name': '2-refine', 'status': 'paused'}],
}

#: The matched control population: shapes that CAN be classified in full. The empty
#: list is the load-bearing member — it is the one legitimate way to reach an empty
#: open-phase set, and the state the malformed shapes above used to be
#: indistinguishable from.
_EXAMINABLE_SHAPES: dict[str, list[dict[str, str]]] = {
    'no_phases_at_all': [],
    'nothing_open': [{'name': '1-init', 'status': 'done'}, {'name': '2-refine', 'status': 'pending'}],
    'one_open': [{'name': '1-init', 'status': 'done'}, {'name': '2-refine', 'status': 'in_progress'}],
    'two_open': [{'name': '5-execute', 'status': 'in_progress'}, {'name': '6-finalize', 'status': 'in_progress'}],
}


def _status_document(phases: Any) -> dict[str, Any]:
    """Wrap one ``phases`` value in an otherwise ordinary status document."""
    document: dict[str, Any] = {'title': 'Unexaminable Phases', 'current_phase': '2-refine'}
    if phases is not _ABSENT:
        document['phases'] = phases
    return document


def _seed_plan_with_an_unreadable_phase_row(plan_context: Any, plan_id: str) -> Path:
    """Create a real plan through ``cmd_create``, then make ONE row unreadable.

    There is deliberately no production verb that yields this state: every writer in
    the skill emits a well-formed row, which is exactly why a malformed one could
    reach the archiver unnoticed. The document is therefore edited directly — the
    same staging the census suite uses for its unparseable member — and only the one
    row is disturbed, so everything else stays the shape a production seed produced.

    Leaves ``1-init`` genuinely ``in_progress`` and ``3-outline`` ``pending``, so the
    cells below can also observe what the archiver does with the phases it DID read.
    """
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Unexaminable Archive',
            phases='1-init,2-refine,3-outline',
            force=False,
        )
    )
    status_path = Path(plan_context.plan_dir_for(plan_id)) / 'status.json'
    document = json.loads(status_path.read_text(encoding='utf-8'))
    document['phases'][1] = 'not-a-phase-record'
    status_path.write_text(json.dumps(document), encoding='utf-8')
    return status_path


class TestTheScanDiscriminates:
    """Two populations, opposite verdicts — neither collapses into the other."""

    def test_both_populations_are_non_trivial_and_disjoint(self) -> None:
        """Pins the sizes the sweeps below draw from, before they draw from them.

        A sweep over an empty (or silently shrunken) population reports zero failures
        and is indistinguishable from a clean one.
        """
        assert len(_UNEXAMINABLE_SHAPES) == 8, sorted(_UNEXAMINABLE_SHAPES)
        assert len(_EXAMINABLE_SHAPES) == 4, sorted(_EXAMINABLE_SHAPES)
        assert not set(_UNEXAMINABLE_SHAPES) & set(_EXAMINABLE_SHAPES), (
            'A shape named in both populations would be asserted to hold two opposite verdicts.'
        )

    def test_every_malformed_shape_reports_that_it_could_not_be_examined(self) -> None:
        """Each malformed shape must say so, and say what it could not read."""
        failures: dict[str, str] = {}
        for name, phases in _UNEXAMINABLE_SHAPES.items():
            scan = _status_core.in_progress_phases(_status_document(phases))
            if scan.examinable:
                failures[name] = 'reported examinable'
            elif not scan.unexaminable:
                failures[name] = 'reported unexaminable but named nothing'

        assert failures == {}, (
            f'Swept {len(_UNEXAMINABLE_SHAPES)} malformed shape(s); each must report '
            f'examinable=False and name what it could not read. Failures: {failures!r}'
        )

    def test_every_well_formed_shape_reports_a_complete_reading(self) -> None:
        """Matched control: a readable structure is never degraded.

        The load-bearing half. Without it the sweep above passes against a scan that
        reports ``examinable: False`` for every input — which would refuse every
        no-reason archive and degrade every census cohort.
        """
        failures: dict[str, tuple[str, ...]] = {}
        for name, phases in _EXAMINABLE_SHAPES.items():
            scan = _status_core.in_progress_phases(_status_document(phases))
            if not scan.examinable:
                failures[name] = scan.unexaminable

        assert failures == {}, (
            f'Swept {len(_EXAMINABLE_SHAPES)} well-formed shape(s); every one must be '
            f'readable in full. Failures: {failures!r}'
        )

    def test_the_open_phase_set_is_still_reported_for_each_readable_shape(self) -> None:
        """The scan reports WHAT IS OPEN, not merely whether it could look.

        Without this, ``examinable: True`` could be reported by a scan that never
        found anything — and the archive's closure loop would silently close nothing.
        """
        observed = {
            name: [phase['name'] for phase in _status_core.in_progress_phases(_status_document(phases)).phases]
            for name, phases in _EXAMINABLE_SHAPES.items()
        }

        assert observed == {
            'no_phases_at_all': [],
            'nothing_open': [],
            'one_open': ['2-refine'],
            'two_open': ['5-execute', '6-finalize'],
        }, observed

    def test_a_partially_malformed_structure_still_reports_the_phases_it_established(self) -> None:
        """One unreadable row does not discard the rows that read cleanly.

        The two facts are independent: ``phases`` carries what WAS established and
        ``unexaminable`` says the set may be incomplete. Dropping the readable half
        would trade a false zero for a different false answer.
        """
        document = _status_document(
            [
                {'name': '5-execute', 'status': 'in_progress'},
                'not-a-phase-record',
                {'name': '6-finalize', 'status': 'pending'},
            ]
        )

        scan = _status_core.in_progress_phases(document)

        assert [phase['name'] for phase in scan.phases] == ['5-execute'], scan.phases
        assert scan.examinable is False, scan
        assert len(scan.unexaminable) == 1, scan.unexaminable
        assert 'phases[1]' in scan.unexaminable[0], scan.unexaminable

    def test_the_reported_phases_are_the_live_records_not_copies(self) -> None:
        """``cmd_archive`` closes a phase by mutating what the scan handed it.

        Returning copies would make the archiver's closure loop a no-op that still
        reported success — the phases would stay ``in_progress`` in the record.
        """
        document = _status_document([{'name': '5-execute', 'status': 'in_progress'}])

        scan = _status_core.in_progress_phases(document)
        scan.phases[0]['status'] = 'done'

        assert document['phases'][0]['status'] == 'done', document

    @pytest.mark.parametrize('shape', ['nothing_open', 'a_row_that_is_a_string'], ids=['examinable', 'unexaminable'])
    def test_the_scan_has_no_truth_value(self, shape: str) -> None:
        """``bool()`` raises for BOTH states, so the retired idiom cannot survive.

        Parametrized over one member of each population deliberately: a type that
        raised only for the unexaminable state would still let ``if not scan:`` read
        as a valid completion test on the ordinary path, leaving the retired idiom
        alive and silently wrong the one time it mattered.
        """
        phases = {**_EXAMINABLE_SHAPES, **_UNEXAMINABLE_SHAPES}[shape]
        scan = _status_core.in_progress_phases(_status_document(phases))

        with pytest.raises(TypeError, match='no truth value'):
            bool(scan)


class TestArchiveOfAnUnexaminableRecord:
    """Refuse without a reason; preserve the lifecycle state with one; never claim complete."""

    def test_a_no_reason_archive_is_refused_and_changes_nothing(self, plan_context: Any) -> None:
        """Fail closed: the findings gate cannot establish that ``6-finalize`` is closed.

        The refusal is asserted together with the untouched document, because a guard
        that returned an error AFTER writing would still have corrupted the record it
        declined to archive.
        """
        plan_id = 'archive-unexaminable-refused'
        status_path = _seed_plan_with_an_unreadable_phase_row(plan_context, plan_id)
        before = status_path.read_text(encoding='utf-8')

        result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

        assert result['status'] == 'error', result
        assert result['error'] == 'phases_unexaminable', result
        assert result['unexaminable'], 'The refusal must name what could not be read.'
        assert 'archived_to' not in result, result
        assert plan_context.plan_dir_for(plan_id).exists(), 'The refused archive must move nothing.'
        assert status_path.read_text(encoding='utf-8') == before, 'The refused archive must write nothing.'

    def test_a_reason_archive_proceeds_but_preserves_the_lifecycle_state(self, plan_context: Any) -> None:
        """A deliberate close is never stranded — but it may not claim ``complete``.

        ``complete`` is the post-finalize sentinel dormant consumers match on, so
        writing it over a record whose open-phase set is unknown asserts a completion
        nothing established. The phases that WERE established open are still closed,
        which is what separates preserving the state from refusing to act.
        """
        plan_id = 'archive-unexaminable-with-reason'
        _seed_plan_with_an_unreadable_phase_row(plan_context, plan_id)

        result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason='superseded_by_another_plan'))

        assert result['status'] == 'success', result
        assert result['phase_closure'] == 'partial', result
        assert result['phase_closure_reason'], 'A partial closure must name its shortfall.'

        archived = json.loads((Path(result['archived_to']) / 'status.json').read_text(encoding='utf-8'))
        assert archived['current_phase'] != 'complete', (
            f'A record whose phases could not be read in full must not be archived as complete; got {archived!r}.'
        )
        assert archived['current_phase'] == '1-init', archived['current_phase']
        readable = {row['name']: row['status'] for row in archived['phases'] if isinstance(row, dict)}
        assert readable['1-init'] == 'done', f'A phase established as open must still be closed; got {readable!r}.'
        assert readable['3-outline'] == 'pending', f'A never-started phase must stay pending; got {readable!r}.'
        assert 'not-a-phase-record' in archived['phases'], 'The unreadable row is preserved, not rewritten.'

    def test_a_well_formed_record_with_no_open_phase_still_completes(self, plan_context: Any) -> None:
        """Matched control: the ordinary no-open-phase archive still reaches ``complete``.

        The load-bearing half of the pair above. Without it, both cells are equally
        consistent with an archiver that refuses everything, or that has simply
        stopped writing the sentinel — and the reader cannot tell a post-condition
        that is SATISFIED from one that is merely unreachable.
        """
        plan_id = 'archive-examinable-control'
        cmd_create(
            Namespace(
                plan_id=plan_id,
                title='Examinable Archive Control',
                phases='1-init,2-refine,3-outline',
                force=False,
            )
        )
        for phase in ('1-init', '2-refine', '3-outline'):
            cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))

        result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

        assert result['status'] == 'success', result
        assert result['phase_closure'] == 'complete', result
        assert 'phase_closure_reason' not in result, f'A complete closure has no shortfall to name; got {result!r}.'
        archived = json.loads((Path(result['archived_to']) / 'status.json').read_text(encoding='utf-8'))
        assert archived['current_phase'] == 'complete', archived['current_phase']
