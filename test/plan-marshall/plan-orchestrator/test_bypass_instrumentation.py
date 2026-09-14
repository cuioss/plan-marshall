#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Red-first guards for the PLAN-08 D4 bypass-enforcement machinery.

Covers the in-epic side of :data:`BYPASS_ENFORCEMENT_POINTS` at both seams
where the recorded epic-slug-fill bypass shape surfaces: the queue-write path
refuses a row whose slug equals the epic slug with NOTHING written, and
``resume-summary`` reports such a row beside the other detectors. The matched
control admits plan-short slugs at both seams. An unscannable queue resolves
to ``indeterminate``, never to a checked negative.

The out-of-epic side is covered by shape tests over the registry itself: every
out-of-epic row must name an owner plus a concrete red-first-testable
predicate, so the registry holds zero prose-only rows. The duplicate-slug
write lint and the N-sharing detector keep their own suites
(``test_orchestrator.py``, ``test_resume_summary_self_validation.py``); this
module proves the D4-new epic-slug arm and the registry contract.
"""

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from conftest import get_script_path, load_script_module, parse_ns

#: The orchestrator script's address, as module-level string constants so the
#: ``parse_ns`` calls below stay statically resolvable.
_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

SCRIPT_PATH = get_script_path(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT)

_orch = load_script_module(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'orchestrator_script')

cmd_queue = _orch.cmd_queue
cmd_resume_summary = _orch.cmd_resume_summary
BYPASS_ENFORCEMENT_POINTS = _orch.BYPASS_ENFORCEMENT_POINTS
BYPASS_SCOPES = _orch.BYPASS_SCOPES
BYPASS_BEHAVIORS = _orch.BYPASS_BEHAVIORS
BYPASS_SCOPE_IN_EPIC = _orch.BYPASS_SCOPE_IN_EPIC
BYPASS_SCOPE_OUT_OF_EPIC = _orch.BYPASS_SCOPE_OUT_OF_EPIC

SLUG = 'fixture-bypass-epic'
FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from a hoisted parser-derived base.

    The base supplies every parser default; ``overrides`` names only the fields
    this call differs in. A shallow copy is enough because a namespace's values
    are the parser's own scalars, and the base must stay unmutated for the other
    callers sharing it.
    """
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


_QUEUE_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'queue',
    '--slug',
    SLUG,
    register=False,
)

_RESUME_SUMMARY_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'resume-summary',
    '--slug',
    SLUG,
    register=False,
)


def _epic_dir(plan_context) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / SLUG


def _row(plan_id: str, slug: str, status: str = 'staged') -> dict:
    return {
        'id': plan_id,
        'slug': slug,
        'workstream': 'WS-01',
        'status': status,
        'plan_marshall_plan_id': '',
        'pr': '',
        'landing': '',
    }


def _write_status(plan_context, rows: list) -> Path:
    doc = {
        'kind': 'orchestrator',
        'title': 'Fixture Bypass Epic',
        'phase': 'orchestrating',
        'workstreams': ['WS-01'],
        'plans': rows,
        'resume_anchor': 'await PLAN-08 landing',
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }
    path = _epic_dir(plan_context) / 'status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


def _read_status_file(path: Path) -> dict:
    return dict(json.loads(path.read_text(encoding='utf-8')))


def _add_row_args(slug_value: str, plan_id: str = 'PLAN-07') -> argparse.Namespace:
    return _variant(
        _QUEUE_ARGS,
        slug=SLUG,
        transition=None,
        status=None,
        set_row=None,
        field=None,
        value=None,
        add_row=plan_id,
        slug_value=slug_value,
        workstream='WS-01',
    )


# =============================================================================
# In-epic gates — the epic-slug-fill bypass shape, refused and redirected
# =============================================================================


class TestEpicSlugGate:
    def test_should_refuse_an_epic_slug_row_leaving_the_queue_unchanged(self, plan_context):
        existing = [_row('PLAN-01', 'plan-one')]
        status_path = _write_status(plan_context, existing)
        before = _read_status_file(status_path)

        result = cmd_queue(_add_row_args(SLUG))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_field'
        assert _read_status_file(status_path) == before

    def test_should_report_an_epic_slug_row_at_resume_summary(self, plan_context):
        rows = [
            _row('PLAN-01', SLUG),
            _row('PLAN-02', 'plan-two'),
        ]
        _write_status(plan_context, rows)

        result = cmd_resume_summary(_RESUME_SUMMARY_ARGS)

        assert result['epic_slug_scan_state'] == 'measured'
        assert result['epic_slug_scanned'] == 2
        assert result['epic_slug_matches_count'] == 1
        assert result['epic_slug_matches'] == [{'id': 'PLAN-01', 'slug': SLUG}]

    def test_should_model_the_recorded_mis_fill_as_refused_and_reported(self, plan_context):
        # The third-occurrence shape: rows already carrying the epic slug (as the
        # model-provisioning ledger did) are reported with every row identity,
        # while a NEW epic-slug append at the write path is refused.
        rows = [_row('PLAN-01', SLUG), _row('PLAN-02', SLUG)]
        status_path = _write_status(plan_context, rows)

        reported = cmd_resume_summary(_RESUME_SUMMARY_ARGS)
        refused = cmd_queue(_add_row_args(SLUG, plan_id='PLAN-03'))

        assert reported['epic_slug_matches_count'] == 2
        assert sorted(match['id'] for match in reported['epic_slug_matches']) == ['PLAN-01', 'PLAN-02']
        assert refused['status'] == 'error'
        assert refused['error'] == 'invalid_field'
        assert len(_read_status_file(status_path)['plans']) == 2

    def test_should_admit_plan_short_slugs_and_stay_silent(self, plan_context):
        # Matched control: the legitimate shape admits at the write path and
        # stays silent at the render path.
        status_path = _write_status(plan_context, [_row('PLAN-01', 'plan-one')])

        admitted = cmd_queue(_add_row_args('plan-seven'))
        reported = cmd_resume_summary(_RESUME_SUMMARY_ARGS)

        assert admitted['status'] == 'success'
        assert [row['slug'] for row in _read_status_file(status_path)['plans']] == [
            'plan-one',
            'plan-seven',
        ]
        assert reported['epic_slug_matches'] == []
        assert reported['epic_slug_matches_count'] == 0
        assert reported['epic_slug_scanned'] == 2, 'the scanned population must be non-empty'
        assert reported['epic_slug_scan_state'] == 'measured'

    def test_unscannable_queue_resolves_to_indeterminate(self):
        findings, scanned, state = _orch._epic_slug_rows({'plans': 'not-a-list'}, SLUG)

        assert state == 'indeterminate'
        assert findings == []
        assert scanned == 0


# =============================================================================
# Registry shape — zero prose-only rows
# =============================================================================


class TestRegistryShape:
    def test_every_row_carries_a_stable_unique_identity(self):
        ids = [row['bypass_id'] for row in BYPASS_ENFORCEMENT_POINTS]

        assert len(ids) == 3
        assert all(isinstance(bypass_id, str) and bypass_id for bypass_id in ids)
        assert len(set(ids)) == len(ids)

    def test_scope_and_behavior_come_from_the_declared_vocabularies(self):
        for row in BYPASS_ENFORCEMENT_POINTS:
            assert row['scope'] in BYPASS_SCOPES, row['bypass_id']
            assert row['behavior'] in BYPASS_BEHAVIORS, row['bypass_id']
            assert row['seam'], row['bypass_id']
            assert row['occurrence'], row['bypass_id']

    def test_in_epic_rows_name_working_gates(self):
        in_epic = [row for row in BYPASS_ENFORCEMENT_POINTS if row['scope'] == BYPASS_SCOPE_IN_EPIC]

        assert in_epic, 'at least one in-epic enforcement point must ship'
        for row in in_epic:
            assert row['gates'], row['bypass_id']
            for gate in row['gates']:
                resolved = getattr(_orch, gate, None)
                assert callable(resolved), (row['bypass_id'], gate)

    def test_out_of_epic_rows_name_an_owner_and_a_concrete_predicate(self):
        out_of_epic = [row for row in BYPASS_ENFORCEMENT_POINTS if row['scope'] == BYPASS_SCOPE_OUT_OF_EPIC]

        assert out_of_epic, 'the lifecycle-owned bypasses must be specified, not dropped'
        for row in out_of_epic:
            assert row['gates'] == (), row['bypass_id']
            assert row['owner'], row['bypass_id']
            assert row['owner'] != 'plan-marshall:plan-orchestrator', row['bypass_id']
            predicate = row['test_predicate']
            assert isinstance(predicate, str) and len(predicate) > 60, row['bypass_id']
            assert 'red' in predicate and 'green' in predicate, row['bypass_id']

    def test_zero_prose_only_rows(self):
        for row in BYPASS_ENFORCEMENT_POINTS:
            if row['scope'] == BYPASS_SCOPE_IN_EPIC:
                assert row['gates'], row['bypass_id']
            else:
                assert row['owner'] and row['test_predicate'], row['bypass_id']
