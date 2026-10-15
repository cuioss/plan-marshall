#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D10 doc contract: findings reopen opt-in and termination hand-back field.

Deliverable 4 states two documentation agreements from the document side:

* (a) ``manage-findings/SKILL.md`` states that ``qgate add`` reopens a
  resolved finding only with the named ``--reopen`` opt-in, and the listed
  status values equal ``QGATE_PERSIST_OK``. A rewording that drops a status
  fails here instead of letting the doc and the code drift apart unnoticed.
* (b) ``plan-marshall/workflow/execution.md`` carries ``pending_verify_steps``
  inside the termination-cause table rows, so every classified return states
  the hand-back field it owns. A row without the field fails here.
"""

from __future__ import annotations

from pathlib import Path

from conftest import PROJECT_ROOT, load_script_module

_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core_qgate_doc')
QGATE_PERSIST_OK = _findings_core.QGATE_PERSIST_OK

MANAGE_FINDINGS_MD = (
    PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-findings' / 'SKILL.md'
)
EXECUTION_MD = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'plan-marshall'
    / 'workflow'
    / 'execution.md'
)

#: The four persist-ok statuses the doc must list. Fixed, not code-derived:
#: the agreement names them, and the code constant is asserted equal to them.
EXPECTED_PERSIST_OK = frozenset({'success', 'deduplicated', 'reopened', 'kept'})


def test_qgate_doc_states_reopen_opt_in_and_lists_all_persist_ok_statuses():
    """Contract (a): the reopen opt-in is named and every status is listed."""
    text = MANAGE_FINDINGS_MD.read_text(encoding='utf-8')

    assert '--reopen' in text, 'manage-findings/SKILL.md must name the --reopen opt-in'
    assert 'QGATE_PERSIST_OK' in text, 'manage-findings/SKILL.md must name QGATE_PERSIST_OK'
    for status in sorted(EXPECTED_PERSIST_OK):
        assert f'`{status}`' in text, f'manage-findings/SKILL.md must list status `{status}`'

    assert set(QGATE_PERSIST_OK) == set(EXPECTED_PERSIST_OK), (
        'code QGATE_PERSIST_OK drifted from the documented four statuses'
    )


def test_termination_table_carries_pending_verify_steps_in_every_row():
    """Contract (b): every termination-cause table row carries the hand-back field."""
    text = EXECUTION_MD.read_text(encoding='utf-8')

    lines = text.splitlines()
    header = '| Cause | Detection rule | pending_verify_steps |'
    start = lines.index(header) + 2  # skip the header row and its separator row
    rows = []
    for line in lines[start:]:
        if not line.startswith('|'):
            break
        if line.startswith('| `'):
            rows.append(line)
    assert len(rows) == 7, f'termination-cause table must carry 7 rows, found {len(rows)}'
    for row in rows:
        assert 'pending_verify_steps' in row, f'termination table row carries no hand-back field: {row[:80]}'
