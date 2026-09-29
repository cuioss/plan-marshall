#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``transition`` refuses an unexaminable ``phases`` structure instead of crashing on it.

``cmd_transition`` reads each phase row by its ``name`` to find the phase that
follows the completed one. A row that is not a mapping, or that carries no
readable ``name``, has no answer to that question, so the verb refuses with
``error: phases_unexaminable`` BEFORE any mutation: ``status.json`` is left
byte-identical and the refusal names every malformed part in ``unexaminable``.

Why the malformed shapes are swept as a population
--------------------------------------------------
The shapes come from the archive suite's ``_UNEXAMINABLE_SHAPES`` — the same
population the shared ``in_progress_phases`` predicate is pinned against — so
``transition`` is held to the exact malformation set ``archive`` and ``census``
already refuse or degrade on. The population size is asserted at module level,
where it runs even if the parametrization were to come back empty.

Why a well-formed control and a CLI arm ride along
--------------------------------------------------
``test_a_well_formed_record_still_transitions`` is the matched control: without
it every refusal cell passes equally against a verb that refused everything.
The CLI arm drives the real dispatcher, because the defect the refusal replaces
was an exception escaping into ``safe_main`` — an exit-1 crash with no refusal
code — and only the dispatcher boundary shows which of the two a caller sees.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest
from _manage_status_archive_unexaminable_phases_fixtures import (
    _ABSENT,
    _EXPECTED_UNEXAMINABLE_SIZE,
    _UNEXAMINABLE_SHAPES,
)
from _manage_status_main_dispatch_fixtures import _PHASES, _parse, _run
from _manage_status_transition_fixtures import cmd_create, cmd_transition

#: The malformed-shape names, bound once. Guarded at module level — an assertion
#: inside the parametrized test body never runs when the set is empty. The
#: truthiness conjunct is the non-vacuity guarantee on its own: the size pin
#: compares against an imported name, which an empty population satisfies too
#: whenever that expected size is itself zero.
_SHAPE_NAMES: list[str] = sorted(_UNEXAMINABLE_SHAPES)
assert _SHAPE_NAMES and len(_SHAPE_NAMES) == _EXPECTED_UNEXAMINABLE_SIZE, (
    f'expected {_EXPECTED_UNEXAMINABLE_SIZE} unexaminable phases shapes, derived {len(_SHAPE_NAMES)}: {_SHAPE_NAMES}'
)


def _seed_plan(plan_id: str) -> None:
    """Create an ordinary plan through the production ``create`` verb."""
    cmd_create(Namespace(plan_id=plan_id, title='Phases Shape Refusal', phases=_PHASES, force=False))


def _replace_phases(plan_context: Any, plan_id: str, phases: Any) -> Path:
    """Overwrite the plan's ``phases`` value (or drop the key) and return the status path.

    No production writer emits a malformed ``phases`` value, which is why the
    document is edited directly; everything else stays the shape ``create`` wrote.
    """
    status_path = Path(plan_context.plan_dir_for(plan_id)) / 'status.json'
    document = json.loads(status_path.read_text(encoding='utf-8'))
    if phases is _ABSENT:
        document.pop('phases')
    else:
        document['phases'] = phases
    status_path.write_text(json.dumps(document), encoding='utf-8')
    return status_path


@pytest.mark.parametrize('shape', _SHAPE_NAMES)
def test_an_unexaminable_phases_structure_is_refused_without_a_write(plan_context, shape):
    """Every malformed ``phases`` shape yields ``phases_unexaminable`` and leaves the file untouched."""
    plan_id = 'phases-shape-refusal'
    _seed_plan(plan_id)
    status_path = _replace_phases(plan_context, plan_id, _UNEXAMINABLE_SHAPES[shape])
    before = status_path.read_bytes()

    result = cmd_transition(Namespace(plan_id=plan_id, completed='1-init'))

    assert result['status'] == 'error', f'{shape}: a malformed phases structure must refuse, got {result}'
    assert result['error'] == 'phases_unexaminable', f'{shape}: the refusal must carry its code, got {result}'
    assert result['unexaminable'], f'{shape}: the refusal must name the malformed part'
    assert 'mailbox' not in result, f'{shape}: a refused transition carries no mailbox block'
    assert status_path.read_bytes() == before, f'{shape}: a refused transition must write nothing'


def test_a_row_without_a_name_is_named_in_the_refusal(plan_context):
    """The refusal's ``unexaminable`` notes identify the offending row by index."""
    plan_id = 'phases-shape-nameless'
    _seed_plan(plan_id)
    _replace_phases(plan_context, plan_id, _UNEXAMINABLE_SHAPES['a_row_with_no_name'])

    result = cmd_transition(Namespace(plan_id=plan_id, completed='1-init'))

    assert result['unexaminable'] == ['phases[1] carries name None, not a non-empty string'], (
        'the note must point at the nameless row, index 1'
    )


def test_a_well_formed_record_still_transitions(plan_context):
    """The matched control: a record ``create`` wrote advances past ``1-init`` as before."""
    plan_id = 'phases-shape-control'
    _seed_plan(plan_id)

    result = cmd_transition(Namespace(plan_id=plan_id, completed='1-init'))

    assert result['status'] == 'success', f'a well-formed record must transition, got {result}'
    assert result['next_phase'] == '2-refine', 'the phase after 1-init must be read off the phases list'


def test_the_cli_reports_the_refusal_as_toon_at_exit_zero(plan_context, monkeypatch, capsys):
    """Through the dispatcher, a malformed row yields a TOON refusal at exit 0, not a crash.

    ``phases_unexaminable`` is an operation refusal, not a blocking-boundary
    refusal, so the exit-1 wrapper does not fire; the refusal is loud because it
    carries a code on stdout.
    """
    plan_id = 'phases-shape-cli'
    _seed_plan(plan_id)
    _replace_phases(plan_context, plan_id, _UNEXAMINABLE_SHAPES['a_row_that_is_a_string'])

    code, out, _ = _run(monkeypatch, capsys, ['transition', '--plan-id', plan_id, '--completed', '1-init'])

    assert code == 0, 'an operation refusal exits 0 under the exit-code convention'
    data = _parse(out)
    assert data['status'] == 'error', f'stdout must carry the refusal, got {out!r}'
    assert data['error'] == 'phases_unexaminable', f'stdout must carry the refusal code, got {out!r}'
