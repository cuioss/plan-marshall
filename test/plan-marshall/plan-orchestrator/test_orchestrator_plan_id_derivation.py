#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for WHERE the orchestrator gets a plan id from.

Subject: the call-site half of the suffixed-id collapse. The grammar half — what
``epic_spec_parser`` resolves one spec NAME to — is the sibling module
``test/plan-marshall/script-shared/test_epic_spec_parser_notation.py``; this one
asserts that the orchestrator does not ask the grammar at all where a queue row
already carries the answer.

The defect both halves close: ``PLAN_ID_SEGMENT``'s two forms terminate in
mandatory digits, so before the terminator existed a letter-suffixed id matched
only through its digits and the trailing letter was absorbed by whatever followed
the segment. Any id RE-DERIVED from a filename therefore collapsed onto its
unsuffixed sibling. A queue row carries the exact id string as data, so the
re-derivation was never necessary — which is why the call-site fix holds whatever
the grammar does.

Every assertion is a **matched pair** over two ids differing in exactly one
trailing letter (:data:`UNSUFFIXED_ID` / :data:`SUFFIXED_ID`), each with its own
spec file, so a site cannot pass by being right about one of them. Two controls
keep the pair honest:

- the **anti-vacuity control** — the rendered Plan column must NOT carry the
  matched spec's filename stem. That assertion FAILS against the pre-fix code,
  which rendered ``spec.stem``, so the pair is exercising the converted site
  rather than agreeing with both versions of it.
- the **spec-still-resolved control** — the Surface column must still be derived
  from that same spec. The fix removed a filename-derived IDENTITY, not the spec
  lookup, and without this control a site that stopped resolving specs entirely
  would pass every other assertion here.

Everything runs against a SCAFFOLDED FIXTURE EPIC under ``PLAN_BASE_DIR``
isolation — never a live orchestrator tree.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from conftest import load_script_module, parse_ns

#: The subject scripts, addressed by module-level string constants so every
#: loader call stays statically resolvable to the loader-contract walker.
_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

#: ``register=False`` on the two supporting modules: only the returned object is
#: needed here, and publishing either under its own stem would displace the
#: binding its own suites rely on.
_orch = load_script_module(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'orchestrator_plan_id_derivation_script')
_inbox = load_script_module(_ORCH_BUNDLE, _ORCH_SKILL, '_orchestrator_inbox.py', register=False)
_spec_parser = load_script_module(_ORCH_BUNDLE, 'script-shared', 'epic_spec_parser.py', register=False)

cmd_resume_summary = _orch.cmd_resume_summary

SLUG = 'fixture-plan-id-epic'
FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'

#: The matched pair. The two ids differ in EXACTLY the trailing ``B``, which is
#: the one variable every assertion below turns on.
UNSUFFIXED_ID = 'PLAN-TRUTH-025'
SUFFIXED_ID = 'PLAN-TRUTH-025B'

#: Each id's own spec file. The stems deliberately differ from the ids by more
#: than the suffix (``-alpha`` / ``-beta``), so a Plan cell rendered from the
#: FILE is distinguishable from one rendered from the ROW at a glance.
UNSUFFIXED_SPEC = f'{UNSUFFIXED_ID}-alpha.md'
SUFFIXED_SPEC = f'{SUFFIXED_ID}-beta.md'

#: One declared surface entry per spec. Both are ROOTED — their first segment is
#: a real top-level repository entry — because the single reader derives
#: rootedness from the tree, and an unrooted entry would be recorded as
#: unresolved and render as a derivation class instead of the path.
UNSUFFIXED_SURFACE = 'test/alpha/a.py'
SUFFIXED_SURFACE = 'test/beta/b.py'

#: The epic slug the pointer cases below are addressed to. It names no fixture
#: on disk: :func:`_orchestrator_inbox.classify_source_id` is a pure grammar
#: check over the pointer STRING and reads no store tree.
_POINTER_EPIC = 'my-epic'

_RESUME_ARGS = parse_ns(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'resume-summary', '--slug', SLUG, register=False)


# =============================================================================
# Fixture builders
# =============================================================================


def _epic_dir(plan_context) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / SLUG


def _row(plan_id: str, status: str = 'staged', workstream: str = 'WS-01') -> dict[str, Any]:
    return {
        'id': plan_id,
        'slug': plan_id.lower(),
        'workstream': workstream,
        'status': status,
        'plan_marshall_plan_id': '',
        'pr': '',
        'landing': '',
    }


def _write_status(plan_context, rows: list[dict[str, Any]]) -> Path:
    doc = {
        'kind': 'orchestrator',
        'title': 'Fixture Plan-Id Epic',
        'phase': 'orchestrating',
        'workstreams': ['WS-01'],
        'plans': rows,
        'resume_anchor': 'await nothing',
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }
    path = _epic_dir(plan_context) / 'status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


def _write_spec(plan_context, name: str, surface: str) -> Path:
    body = f'# Fixture spec\n\n## Expected Surface\n\n- Adds `{surface}`\n'
    path = _epic_dir(plan_context) / 'plans' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')
    return path


def _matched_pair_epic(plan_context) -> None:
    """Both ids queued, each with its own spec — the shared fixture state."""
    _write_status(plan_context, [_row(UNSUFFIXED_ID), _row(SUFFIXED_ID)])
    _write_spec(plan_context, UNSUFFIXED_SPEC, UNSUFFIXED_SURFACE)
    _write_spec(plan_context, SUFFIXED_SPEC, SUFFIXED_SURFACE)


def _queue() -> str:
    """The rendered Ordered Queue table, through the public verb.

    Driven through ``resume-summary`` rather than through the renderer directly,
    so what is asserted is the table a caller actually receives.
    """
    result: dict[str, Any] = cmd_resume_summary(_RESUME_ARGS)
    assert result['status'] == 'success', result
    return str(result['ordered_queue'])


def _plan_cells(queue: str) -> list[str]:
    """The Plan column of every DATA row, derived from the rendered table.

    Derived rather than pattern-matched for one id at a time: the population is
    the rows the renderer emitted, so an assertion over it states how many rows
    it was computed from instead of quietly reading zero.
    """
    cells: list[str] = []
    for line in queue.split('\n'):
        columns = [column.strip() for column in line.split('|')]
        # A data row is ``| # | Plan | ... |`` whose first cell is the position
        # integer; the header and the divider are not.
        if len(columns) >= 4 and columns[1].isdigit():
            cells.append(columns[2])
    return cells


# =============================================================================
# The converted site: the Ordered Queue Plan column
# =============================================================================


class TestOrderedQueuePlanCell:
    def test_each_row_renders_its_own_id_and_the_pair_stays_distinct(self, plan_context):
        _matched_pair_epic(plan_context)

        cells = _plan_cells(_queue())

        assert cells == [UNSUFFIXED_ID, SUFFIXED_ID]
        # Stated separately from the equality above: the pair's whole point is
        # that the two rows are told apart, and an equality over a list would
        # also hold if both constants were the same string.
        assert UNSUFFIXED_ID != SUFFIXED_ID
        assert len(set(cells)) == len(cells)

    def test_the_plan_cell_is_not_derived_from_the_matched_spec_filename(self, plan_context):
        """The anti-vacuity control: this FAILS against the pre-fix ``spec.stem``.

        Both stems are absent from the Plan column while both specs are present
        on disk and matched — so the cell is the row's field, not the file's
        name. Without this assertion the pair above would also pass against the
        old code for the unsuffixed row, whose stem merely starts with its id.
        """
        _matched_pair_epic(plan_context)

        cells = _plan_cells(_queue())

        stems = {Path(UNSUFFIXED_SPEC).stem, Path(SUFFIXED_SPEC).stem}
        assert stems.isdisjoint(cells)
        assert len(stems) == 2  # non-vacuity: two distinct stems were compared

    def test_the_surface_cell_is_still_derived_from_the_matched_spec(self, plan_context):
        """The matched control for the assertion above: the spec IS still read.

        The fix removed a filename-derived identity, not the spec lookup. A site
        that stopped resolving specs altogether would satisfy every
        *not-the-filename* assertion here while silently emptying the column the
        spec legitimately owns.
        """
        _matched_pair_epic(plan_context)

        queue = _queue()

        assert UNSUFFIXED_SURFACE in queue
        assert SUFFIXED_SURFACE in queue

    def test_a_row_with_no_spec_at_all_renders_the_same_id(self, plan_context):
        """The second matched control: the id does not change with spec presence.

        The row id is the cell whether or not a spec matched, so the two arms of
        the spec-presence branch cannot report different identities for one row.
        """
        _write_status(plan_context, [_row(UNSUFFIXED_ID), _row(SUFFIXED_ID)])
        assert not (_epic_dir(plan_context) / 'plans').exists()

        cells = _plan_cells(_queue())

        assert cells == [UNSUFFIXED_ID, SUFFIXED_ID]


# =============================================================================
# The composed pointer seam
# =============================================================================


class TestPointerGrammarComposition:
    def test_the_pointer_grammar_still_composes_from_the_shared_segment(self):
        """One definition of the plan-id form, consumed rather than re-spelled."""
        assert _spec_parser.PLAN_ID_SEGMENT
        assert _spec_parser.PLAN_ID_SEGMENT in _inbox._SOURCE_ID_RE.pattern

    def test_a_suffixed_pointer_is_refused_where_its_sibling_is_accepted(self):
        """The matched pair at the seam that composes the segment.

        The refusal is the POINT: a suffixed pointer is reported through the
        existing ``unrecognised_id`` token — orchestrator-SHAPED, id segment
        matching no accepted form — instead of being silently classified as its
        unsuffixed sibling's pointer.
        """
        accepted = _inbox.classify_source_id(f'.plan/orchestrator/{_POINTER_EPIC}/plans/{UNSUFFIXED_SPEC}')
        refused = _inbox.classify_source_id(f'.plan/orchestrator/{_POINTER_EPIC}/plans/{SUFFIXED_SPEC}')

        assert (accepted.orchestrated, accepted.detection) == (True, 'orchestrated')
        assert accepted.epic == _POINTER_EPIC
        assert (refused.orchestrated, refused.epic, refused.detection) == (False, None, 'unrecognised_id')
        assert refused.detection in _inbox.DETECTION_TOKENS
