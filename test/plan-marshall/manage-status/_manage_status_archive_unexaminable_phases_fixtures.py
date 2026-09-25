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

Why the valid cases are DERIVED rather than listed
--------------------------------------------------
The examinable population is built from ``constants.VALID_PHASE_STATUSES`` — one shape
per declared status — its expected size is computed from that set, and the invalid
sentinel is constructed to sit outside it. A hand-written roster of statuses is the
same weakness one level down: a status added to the vocabulary would enter the codebase
with no case here, and the sweep would report no failures over a population that had
quietly stopped covering the declared set. ``test_both_populations_are_non_trivial_and_disjoint``
additionally asserts that every declared status is exercised by some shape, so the
coverage claim is derived from the vocabulary rather than asserted about it.

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
from constants import PHASE_STATUS_DONE, PHASE_STATUS_IN_PROGRESS, VALID_PHASE_STATUSES

#: Stands for "the ``phases`` key is not present at all", which no value can express.
_ABSENT = object()

#: The declared phase-status vocabulary, read from ``constants`` rather than spelled as
#: a literal triple. Every population below is derived from it, so a status ADDED to the
#: vocabulary widens this module automatically instead of entering the codebase with no
#: case here — a fixed roster is exactly how a sweep silently loses coverage while still
#: reporting no failures.
_VOCABULARY: tuple[str, ...] = tuple(sorted(VALID_PHASE_STATUSES))

#: A status value guaranteed OUTSIDE the vocabulary, CONSTRUCTED from it rather than
#: picked as a plausible-looking literal. A hand-picked sentinel (``paused``) is one
#: ``VALID_PHASE_STATUSES`` addition away from becoming valid, at which point the shape
#: it stands for quietly stops being malformed and the sweep loses a case without
#: failing. This spelling cannot collide by construction, and the assertion in
#: ``test_both_populations_are_non_trivial_and_disjoint`` states that as a fact.
_OUTSIDE_THE_VOCABULARY = 'not-' + '-nor-'.join(_VOCABULARY)


def _row(name: str, status: str) -> dict[str, str]:
    """One well-formed phase record — the shape every production writer emits."""
    return {'name': name, 'status': status}


#: The shapes whose open-phase set cannot be established. Each is a whole ``phases``
#: value, and each fails for its own structural reason, so a fix that handles only
#: one of them leaves the others reporting a confident empty set. Three of them are the
#: name shapes: a row nobody can identify is a part of the structure that was not read,
#: and without the check the projection renders it as the phase named ``''``.
_UNEXAMINABLE_SHAPES: dict[str, Any] = {
    'key_absent': _ABSENT,
    'explicit_null': None,
    'a_mapping_not_a_list': {'1-init': PHASE_STATUS_IN_PROGRESS},
    'a_bare_string': PHASE_STATUS_IN_PROGRESS,
    'a_row_that_is_a_string': [_row('1-init', PHASE_STATUS_DONE), 'not-a-phase-record'],
    'a_row_that_is_null': [_row('1-init', PHASE_STATUS_DONE), None],
    'a_row_with_no_status': [_row('1-init', PHASE_STATUS_DONE), {'name': '2-refine'}],
    'a_row_outside_the_vocabulary': [
        _row('1-init', PHASE_STATUS_DONE),
        {'name': '2-refine', 'status': _OUTSIDE_THE_VOCABULARY},
    ],
    'a_row_with_no_name': [_row('1-init', PHASE_STATUS_DONE), {'status': PHASE_STATUS_IN_PROGRESS}],
    'a_row_with_an_empty_name': [_row('1-init', PHASE_STATUS_DONE), {'name': '', 'status': PHASE_STATUS_IN_PROGRESS}],
    'a_row_with_a_non_string_name': [
        _row('1-init', PHASE_STATUS_DONE),
        {'name': 5, 'status': PHASE_STATUS_IN_PROGRESS},
    ],
}

#: Hand-maintained count of the structural classes above, kept as a literal BECAUSE it
#: is not vocabulary-derived: these shapes are ways a ``phases`` structure can be
#: malformed, and adding one is a deliberate act. Deriving it from ``len()`` of the dict
#: it guards would be vacuous; its job is to fail when a member is silently dropped.
_EXPECTED_UNEXAMINABLE_SIZE = 11

#: The matched control population: shapes that CAN be classified in full. One
#: single-status shape per DECLARED status, so every value in the vocabulary is swept,
#: plus the empty list and a two-open shape. The empty list is the load-bearing member —
#: it is the one legitimate way to reach an empty open-phase set, and the state the
#: malformed shapes above used to be indistinguishable from.
_EXAMINABLE_SHAPES: dict[str, list[dict[str, Any]]] = {
    'no_phases_at_all': [],
    **{f'only_{status}': [_row('1-init', status)] for status in _VOCABULARY},
    'two_open': [_row('5-execute', PHASE_STATUS_IN_PROGRESS), _row('6-finalize', PHASE_STATUS_IN_PROGRESS)],
}

#: DERIVED from the vocabulary: one shape per declared status, plus the two shapes that
#: are about structure rather than about a status value. A status added to
#: ``VALID_PHASE_STATUSES`` moves this number and the population together.
_EXPECTED_EXAMINABLE_SIZE = len(_VOCABULARY) + 2

#: What each examinable shape must report as OPEN. Derived alongside the population from
#: the same vocabulary, but stating independently which status means "open" — that is
#: the production predicate, and asserting it here is what stops the control population
#: from being a shape sweep that never checks the answer.
_EXPECTED_OPEN_NAMES: dict[str, list[str]] = {
    'no_phases_at_all': [],
    **{f'only_{status}': (['1-init'] if status == PHASE_STATUS_IN_PROGRESS else []) for status in _VOCABULARY},
    'two_open': ['5-execute', '6-finalize'],
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
