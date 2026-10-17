#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D3 tests: the queue row's ``lane`` and the runbook lane's orchestration.

The runbook lane runs one staged plan without the ``/plan-marshall`` lifecycle.
The orchestrator meets it in four places, and each is asserted here directly
rather than inferred:

* the queue row carries a ``lane`` (``plan-marshall``, the default, or
  ``runbook``), settable with ``--add-row --lane`` and ``--set-row --field lane``
  and rendered in the Ordered Queue's Lane column;
* ``next`` emits by lane — the runbook form for a ``runbook`` row, the unchanged
  plan-marshall form for every other row;
* a runbook landing reconciles to its row through the lane's ``rb-{plan}``
  sender id, and a landing whose sender equals a row's stamped
  ``plan_marshall_plan_id`` reconciles to that row;
* ``status`` flags a ``staged`` runbook row whose lane worktree already exists,
  and writes nothing while doing so.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _ledger_fixtures import write_ledger

from conftest import get_script_path, load_script_module

_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

SCRIPT_PATH = get_script_path(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT)
SKILL_MD_PATH = Path(SCRIPT_PATH).parent.parent / 'SKILL.md'
ORCHESTRATE_MD_PATH = Path(SCRIPT_PATH).parent.parent / 'workflow' / 'orchestrate.md'

_ORCH = load_script_module(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'orchestrator_lane_rows')
_INBOX = load_script_module(_ORCH_BUNDLE, _ORCH_SKILL, '_orchestrator_inbox.py', '_orchestrator_inbox_lane_rows')

cmd_queue = _ORCH.cmd_queue
cmd_resume_summary = _ORCH.cmd_resume_summary
render_queue_view = _ORCH.render_queue_view
VALID_LANE_VOCABULARY = _ORCH.VALID_LANE_VOCABULARY
LANE_PLAN_MARSHALL = _ORCH.LANE_PLAN_MARSHALL
LANE_RUNBOOK = _ORCH.LANE_RUNBOOK
STARTED_NOT_TRANSITIONED = _ORCH.STARTED_NOT_TRANSITIONED

_LANE_VOCABULARY_ANCHOR = '`--lane` vocabulary (mirrors `VALID_LANE_VOCABULARY`):'
_BACKTICKED_RE = re.compile(r'`([^`]+)`')

_SLUG = 'lane-epic'


def _args(slug: str = _SLUG, **overrides) -> argparse.Namespace:
    """A complete ``queue`` namespace, so every flag attribute is present."""
    base = {
        'slug': slug,
        'transition': None,
        'status': None,
        'set_row': None,
        'field': None,
        'value': None,
        'add_row': None,
        'slug_value': None,
        'workstream': None,
        'lane': None,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _epic_dir(plan_context, slug: str = _SLUG) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _seed(plan_context, rows: list[dict], slug: str = _SLUG) -> None:
    write_ledger(
        _epic_dir(plan_context, slug),
        {'kind': 'orchestrator', 'phase': 'orchestrating', 'resume_anchor': '', 'plans': rows},
    )


def _row(plan_id: str, status: str = 'staged', lane: str = LANE_PLAN_MARSHALL, **extra) -> dict:
    return {
        'id': plan_id,
        'slug': extra.pop('slug', plan_id.lower()),
        'workstream': 'WS-01',
        'status': status,
        'lane': lane,
        'plan_marshall_plan_id': extra.pop('plan_marshall_plan_id', ''),
        'pr': '',
        'landing': '',
        **extra,
    }


def _documented_lane_vocabulary() -> list[str]:
    for line in SKILL_MD_PATH.read_text(encoding='utf-8').splitlines():
        if line.startswith(_LANE_VOCABULARY_ANCHOR):
            tokens = _BACKTICKED_RE.findall(line)
            # The first two backticked tokens are the flag's own name and the
            # mirrored CONSTANT's name; the vocabulary follows them.
            return tokens[2:]
    return []


# =============================================================================
# The lane field
# =============================================================================


def test_documented_lane_vocabulary_matches_declaration():
    documented = _documented_lane_vocabulary()
    assert documented, f'SKILL.md publishes no line behind {_LANE_VOCABULARY_ANCHOR!r}'
    assert set(documented) == set(VALID_LANE_VOCABULARY)


def test_add_row_seeds_the_default_lane(plan_context):
    _seed(plan_context, [])

    result = cmd_queue(_args(add_row='PLAN-07', slug_value='seven', workstream='WS-01'))

    assert result['status'] == 'success'
    assert result['row']['lane'] == LANE_PLAN_MARSHALL


def test_add_row_honours_a_runbook_lane(plan_context):
    _seed(plan_context, [])

    result = cmd_queue(_args(add_row='PLAN-07', slug_value='seven', workstream='WS-01', lane=LANE_RUNBOOK))

    assert result['status'] == 'success'
    assert result['row']['lane'] == LANE_RUNBOOK


def test_add_row_refuses_an_unknown_lane(plan_context):
    _seed(plan_context, [])

    result = cmd_queue(_args(add_row='PLAN-07', slug_value='seven', workstream='WS-01', lane='ci'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_field'


def test_set_row_moves_a_row_to_the_runbook_lane(plan_context):
    _seed(plan_context, [_row('PLAN-01')])

    result = cmd_queue(_args(set_row='PLAN-01', field='lane', value=LANE_RUNBOOK))

    assert result['status'] == 'success'
    persisted = cmd_queue(_args())['plans'][0]
    assert persisted['lane'] == LANE_RUNBOOK


def test_set_row_refuses_an_unknown_lane_value(plan_context):
    _seed(plan_context, [_row('PLAN-01')])

    result = cmd_queue(_args(set_row='PLAN-01', field='lane', value='nope'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_field'


def test_the_ordered_queue_renders_the_lane_column():
    view = {
        'phase': 'orchestrating',
        'resume_anchor': '',
        'plans': [{**_row('PLAN-01', lane=LANE_RUNBOOK), 'seq': 1}],
    }

    rendered = render_queue_view(view, {}, slug=_SLUG)

    assert '| # | Plan | Workstream | Status | Surface (expected) | Lane |' in rendered
    assert f'| {LANE_RUNBOOK} |' in rendered


def test_an_absent_lane_reads_as_the_default():
    """A row staged before the field existed still renders under the default."""
    view = {
        'phase': 'orchestrating',
        'resume_anchor': '',
        'plans': [{'id': 'PLAN-01', 'slug': 'one', 'status': 'staged', 'seq': 1}],
    }

    rendered = render_queue_view(view, {}, slug=_SLUG)

    assert f'| {LANE_PLAN_MARSHALL} |' in rendered


# =============================================================================
# status: a started runbook row that was never transitioned
# =============================================================================


def _make_lane_worktree(plan_context, plan_name: str) -> Path:
    """Create the lane worktree directory the detector reads.

    Created through the SAME accessor production uses when it looks for it, so
    the fixture cannot pass by placing the directory somewhere the detector never
    looks.
    """
    worktree = Path(_ORCH.get_worktree_root()) / plan_name
    worktree.mkdir(parents=True, exist_ok=True)
    return worktree


def test_status_flags_a_started_runbook_row(plan_context):
    _seed(plan_context, [_row('PLAN-LB-66', slug='runbook-lane-skill', lane=LANE_RUNBOOK)])
    _make_lane_worktree(plan_context, 'lb-66-runbook-lane-skill')

    data = cmd_resume_summary(argparse.Namespace(slug=_SLUG))

    assert data['status'] == 'success'
    assert data['started_not_transitioned_count'] == 1
    row = data['started_not_transitioned'][0]
    assert row['id'] == 'PLAN-LB-66'
    assert row['plan'] == 'lb-66-runbook-lane-skill'
    assert STARTED_NOT_TRANSITIONED in data['summary']


def test_status_does_not_flag_a_staged_plan_marshall_row(plan_context):
    _seed(plan_context, [_row('PLAN-LB-66', slug='runbook-lane-skill')])
    _make_lane_worktree(plan_context, 'lb-66-runbook-lane-skill')

    data = cmd_resume_summary(argparse.Namespace(slug=_SLUG))

    assert data['started_not_transitioned_count'] == 0
    assert STARTED_NOT_TRANSITIONED not in data['summary']


def test_status_writes_nothing(plan_context):
    _seed(plan_context, [_row('PLAN-LB-66', slug='runbook-lane-skill', lane=LANE_RUNBOOK)])
    _make_lane_worktree(plan_context, 'lb-66-runbook-lane-skill')
    before = sorted(p.name for p in _epic_dir(plan_context).rglob('*'))

    cmd_resume_summary(argparse.Namespace(slug=_SLUG))

    assert sorted(p.name for p in _epic_dir(plan_context).rglob('*')) == before


# =============================================================================
# next: the emitted form follows the lane
# =============================================================================


def test_orchestrate_documents_the_lane_branch_and_both_forms():
    text = ORCHESTRATE_MD_PATH.read_text(encoding='utf-8')

    assert 'the emitted form follows the row' in text.lower()
    assert '/plan-marshall task="implement .plan/orchestrator/{slug}/plans/PLAN-NN-{plan_slug}.md"' in text
    assert '/plan-marshall-runbook-lane plan=.plan/orchestrator/{slug}/plans/PLAN-NN-{plan_slug}.md' in text
    assert LANE_RUNBOOK in text


# =============================================================================
# landing correlation
# =============================================================================


def test_runbook_sender_id_is_rb_prefixed():
    row = _row('PLAN-LB-66', slug='runbook-lane-skill', lane=LANE_RUNBOOK)

    # The lane strips the row's own ``PLAN-`` marker as it strips the spec
    # basename's, so the sender names the plan and not its queue id.
    assert _INBOX.runbook_plan_name(row) == 'lb-66-runbook-lane-skill'
    assert _INBOX.runbook_sender_id(row) == 'rb-lb-66-runbook-lane-skill'


def test_a_runbook_sender_reconciles_to_its_row():
    row = _row('PLAN-LB-66', slug='runbook-lane-skill', status='running', lane=LANE_RUNBOOK)
    sender = _INBOX.runbook_sender_id(row)

    reconciliation = _INBOX.reconcile_queue_vs_landings([row], {sender})
    owed = _INBOX.classify_owed_landing(_INBOX._running_plan_ids([row]), {sender})

    assert reconciliation['queue_without_landing'] == []
    assert reconciliation['landing_without_queue'] == []
    assert owed['state'] == 'owed'
    assert owed['owed_plans'] == [sender]


def test_a_stamped_plan_id_sender_reconciles_to_its_row():
    row = _row('PLAN-LB-66', slug='runbook-lane-skill', status='running', plan_marshall_plan_id='lb-66')
    sender = 'lb-66'

    reconciliation = _INBOX.reconcile_queue_vs_landings([row], {sender})
    owed = _INBOX.classify_owed_landing(_INBOX._running_plan_ids([row]), {sender})

    assert reconciliation['queue_without_landing'] == []
    assert reconciliation['landing_without_queue'] == []
    assert owed['state'] == 'owed'


def test_a_plain_plan_marshall_row_answers_to_its_id_only():
    """The lane identity is additive: a default row keeps today's identities."""
    row = _row('PLAN-01', status='running')

    assert _INBOX._row_identities(row) == {'PLAN-01'}
