#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-118 D3 — a re-file re-arms what the review superseded, never an operator decision.

A loop-back round resolves its own findings `taken_into_account` through the rule-keyed
resolver, which records `resolution_source: rule`. Only such a record is re-armed by an
identical re-file. A triage Hold records the same resolution through the single-finding
resolver and carries no source, so it stays resolved.
"""

from __future__ import annotations

import json
from pathlib import Path

import _findings_core

PLAN_ID = 'lb118-reobservation-d3'
PHASE = '6-finalize'
RULE = 'functional-review'
TITLE = 'ambiguous_wording at doc/a.md:12'
DETAIL = 'the section says one thing and the table another [fix_kind correction]'


def _plan(plan_context) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    (plan_dir / 'status.json').write_text(
        json.dumps({'title': 'fixture', 'phases': [], 'current_phase': '6-finalize', 'metadata': {}}),
        encoding='utf-8',
    )
    return plan_dir


def _file(reopen: bool = False):
    return _findings_core.add_qgate_finding(
        PLAN_ID,
        PHASE,
        'qgate',
        'bug',
        TITLE,
        DETAIL,
        rule=RULE,
        reopen=reopen,
    )


def _records():
    queried = _findings_core.query_qgate_findings(PLAN_ID, PHASE)
    assert queried['status'] == 'success', queried
    return {finding['hash_id']: finding for finding in queried['findings']}


def test_a_triage_hold_record_is_kept_on_an_identical_refile(plan_context) -> None:
    _plan(plan_context)
    first = _file()
    hold = _findings_core.resolve_qgate_finding(
        PLAN_ID, PHASE, first['hash_id'], 'taken_into_account', detail='operator Hold for a later plan'
    )
    assert hold['status'] == 'success', hold

    again = _file()

    assert again['status'] == 'kept', again
    assert again['not_reopened'] == 'taken_into_account', again
    assert _records()[first['hash_id']]['resolution'] == 'taken_into_account'


def test_a_loop_back_rule_record_is_reopened_on_an_identical_refile(plan_context) -> None:
    _plan(plan_context)
    first = _file()
    resolved = _findings_core.resolve_qgate_findings_by_rule(
        PLAN_ID, PHASE, RULE, 'taken_into_account', 'superseded by the round at the new head'
    )
    assert resolved['status'] == 'success', resolved

    again = _file()

    assert again['status'] == 'reopened', again
    assert again['previous_resolution'] == 'taken_into_account'
    assert _records()[first['hash_id']]['resolution'] == 'pending'


def test_the_rule_resolver_marks_its_resolution_source(plan_context) -> None:
    _plan(plan_context)
    first = _file()
    _findings_core.resolve_qgate_findings_by_rule(PLAN_ID, PHASE, RULE, 'taken_into_account', 'superseded')

    assert _records()[first['hash_id']]['resolution_source'] == _findings_core.RULE_RESOLUTION_SOURCE


def test_reopen_against_a_triage_hold_record_is_kept(plan_context) -> None:
    """The opt-in never re-arms an operator Hold."""
    _plan(plan_context)
    first = _file()
    _findings_core.resolve_qgate_finding(PLAN_ID, PHASE, first['hash_id'], 'taken_into_account', detail='Hold')

    again = _file(reopen=True)

    assert again['status'] == 'kept', again
    assert again['not_reopened'] == 'taken_into_account', again
    assert _records()[first['hash_id']]['resolution'] == 'taken_into_account'
