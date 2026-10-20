#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-70 D1 — the finalize gate refuses only genuinely open criteria.

PLAN-LB-52 gated the 6-finalize exit on the frozen criteria, but the gate
refused legitimate work: a plan whose functional review the manifest dropped can
never finalize, an operator-authorized deletion stays open forever, and a
superseded deliverable blocks. A verdict row answers its criterion by
``criterion_id`` or exact text; a paraphrase that carries neither is the author's
to correct, not a positional guess.

Each Done-when here is driven over a real sandboxed plan directory and the real
``open_criteria`` / ``_finalize_findings_refusal`` code paths.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import _criteria_snapshot as _snap
import review_support

from conftest import load_script_module

PLAN_ID = 'lb70-criteria-gate-d1'
_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_lb70_d1_lifecycle')


def _outline(criteria: list[str]) -> str:
    body = '\n'.join(f'- {text}' for text in criteria)
    return (
        '# Solution: criteria gate completion\n\n## Summary\n\nFixture plan.\n\n## Deliverables\n\n'
        '### 1. Deliver the change\n\n**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        f'**Success Criteria:**\n{body}\n'
    )


def _plan(plan_context: Any, criteria: list[str], *, freeze_from: list[str] | None = None) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    # The freeze binds its digest in the status record, so the plan must have one.
    _status(plan_dir)
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    (plan_dir / 'solution_outline.md').write_text(_outline(criteria), encoding='utf-8')
    if freeze_from is not None:
        (plan_dir / 'solution_outline.md').write_text(_outline(freeze_from), encoding='utf-8')
        _snap.write_snapshot(PLAN_ID)
        (plan_dir / 'solution_outline.md').write_text(_outline(criteria), encoding='utf-8')
    return plan_dir


def _manifest(plan_dir: Path, steps: list[str]) -> None:
    """Write an ``execution.toon`` whose phase-6 step list is ``steps``."""
    head = f'manifest_version: 1\nplan_id: {PLAN_ID}\nphase_6:\n  steps[{len(steps)}]:\n'
    body = ''.join(f'    - {step}\n' for step in steps)
    (plan_dir / 'execution.toon').write_text(head + body, encoding='utf-8')


def _status(plan_dir: Path, metadata: dict[str, Any] | None = None) -> None:
    status = {
        'title': 'fixture',
        'phases': [{'name': '6-finalize', 'status': 'pending'}],
        'current_phase': '6-finalize',
        'metadata': metadata if metadata is not None else {'use_worktree': False},
    }
    (plan_dir / 'status.json').write_text(json.dumps(status), encoding='utf-8')


def _sealed(tmp_path: Path, document: dict[str, Any]) -> dict[str, Any]:
    path = tmp_path / 'verdict.json'
    path.write_text(json.dumps(document), encoding='utf-8')
    assert review_support.run_author_verdict(PLAN_ID, 'functional', str(path))['status'] == 'success'
    parsed: dict[str, Any] = json.loads(Path(path).read_text(encoding='utf-8'))
    return parsed


def _write_verdict(plan_dir: Path, document: dict[str, Any]) -> None:
    work = plan_dir / 'work'
    work.mkdir(parents=True, exist_ok=True)
    (work / 'functional-review-verdict.json').write_text(json.dumps(document), encoding='utf-8')


def _sealed_live(plan_dir: Path, tmp_path: Path, document: dict[str, Any]) -> None:
    """Seal ``document`` and put the SEALED form in the plan's verdict slot."""
    _write_verdict(plan_dir, _sealed(tmp_path, document))


# --- D1 (a): a plan whose functional review was dropped completes finalize -----------------


def test_surgical_plan_without_a_review_completes_finalize(plan_context, tmp_path, monkeypatch) -> None:
    plan_dir = _plan(plan_context, ['parser accepts input'], freeze_from=['parser accepts input'])
    # A surgical scope drops functional-review from the composed manifest.
    _manifest(plan_dir, ['pre-push-quality-gate', 'sonar-roundtrip'])
    _status(plan_dir, {'use_worktree': False, 'scope_estimate': 'surgical'})
    monkeypatch.setattr(_lifecycle, 'assert_finalize_findings_clean', lambda *_a, **_k: 0)
    monkeypatch.setattr(_lifecycle, 'log_entry', lambda *_a, **_k: None)
    monkeypatch.setattr(_lifecycle, '_surface_drive', lambda *_a, **_k: None)

    result = _lifecycle.cmd_transition(
        argparse.Namespace(plan_id=PLAN_ID, completed='6-finalize', allow_bare_transition=False, bare_reason=None)
    )

    assert result is not None and result['status'] == 'success', result
    assert result['criteria_gate'].startswith('not_applicable'), result


def test_plan_whose_review_is_scheduled_still_refuses_an_open_criterion(plan_context, tmp_path, monkeypatch) -> None:
    plan_dir = _plan(plan_context, ['parser accepts input'], freeze_from=['parser accepts input'])
    _manifest(plan_dir, ['functional-review', 'pre-push-quality-gate'])
    _status(plan_dir)
    monkeypatch.setattr(_lifecycle, 'assert_finalize_findings_clean', lambda *_a, **_k: 0)
    monkeypatch.setattr(_lifecycle, 'log_entry', lambda *_a, **_k: None)
    monkeypatch.setattr(_lifecycle, '_surface_drive', lambda *_a, **_k: None)

    result = _lifecycle.cmd_transition(
        argparse.Namespace(plan_id=PLAN_ID, completed='6-finalize', allow_bare_transition=False, bare_reason=None)
    )

    assert result is not None and result['error'] == 'open_done_when_criteria', result


# --- D1 (b): open_criteria honours authorized changes, superseded and closures --------------


def test_operator_authorized_deleted_criterion_is_closed(plan_context, tmp_path) -> None:
    plan_dir = _plan(
        plan_context, ['parser accepts input'], freeze_from=['parser accepts input', 'parser rejects garbage']
    )
    assert _snap.authorize_change(PLAN_ID, 1, 'parser rejects garbage', 'operator: the gap is refuted')['status'] == (
        'success'
    )
    _sealed_live(
        plan_dir,
        tmp_path,
        {
            'deliverables': [
                {
                    'number': 1,
                    'verdict': 'met',
                    'criteria': [
                        {'criterion': 'parser accepts input', 'status': 'met', 'evidence': ['src/parser.py:1']}
                    ],
                }
            ],
            'unrequested_changes': [],
            'self_reports': [],
            'files_read': ['src/parser.py'],
        },
    )

    payload = _snap.open_criteria(PLAN_ID)

    assert payload['open_count'] == 0, payload


def test_superseded_deliverable_criteria_do_not_block(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context, ['a', 'b'], freeze_from=['a', 'b'])
    _sealed_live(
        plan_dir,
        tmp_path,
        {
            'deliverables': [{'number': 1, 'verdict': 'superseded', 'superseded_by': 'operator decision X'}],
            'unrequested_changes': [],
            'self_reports': [],
            'files_read': [],
        },
    )

    payload = _snap.open_criteria(PLAN_ID)

    assert payload['open_count'] == 0, payload


def test_closed_review_criteria_do_not_block(plan_context, tmp_path) -> None:
    """The operator closed the review past its round cap: its criteria are not open."""
    plan_dir = _plan(plan_context, ['a', 'b'], freeze_from=['a', 'b'])
    metadata = {
        'use_worktree': False,
        'functional_review_override_heads': ['abc1234'],
        'phase_steps': {'6-finalize': {'functional-review': {'facts': {'may_close': 'operator_override'}}}},
    }
    _status(plan_dir, metadata)

    payload = _snap.open_criteria(PLAN_ID)

    assert payload['open_count'] == 0, payload


def test_closed_review_closes_criteria_even_with_a_sealed_verdict(plan_context, tmp_path) -> None:
    """The production shape: the last round wrote a sealed verdict, then the operator closed."""
    plan_dir = _plan(plan_context, ['a', 'b'], freeze_from=['a', 'b'])
    _sealed_live(
        plan_dir,
        tmp_path,
        {
            'deliverables': [
                {
                    'number': 1,
                    'verdict': 'met',
                    'criteria': [{'criterion': 'a', 'status': 'met', 'evidence': ['src/parser.py:1']}],
                }
            ],
            'unrequested_changes': [],
            'self_reports': [],
            'files_read': ['src/parser.py'],
        },
    )
    _status(plan_dir, {'use_worktree': False, 'functional_review_override_heads': ['abc1234']})

    payload = _snap.open_criteria(PLAN_ID)

    assert payload['open_count'] == 0, payload


# --- D1 (c): a verdict row matches its criterion by a stable id ----------------------------


def test_paraphrased_verdict_row_grades_its_criterion(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context, ['the parser rejects garbage'], freeze_from=['the parser rejects garbage'])
    _sealed_live(
        plan_dir,
        tmp_path,
        {
            'deliverables': [
                {
                    'number': 1,
                    'verdict': 'met',
                    'criteria': [
                        {
                            'criterion': 'junk input is refused by the reader',
                            'criterion_id': 'C1',
                            'status': 'met',
                            'evidence': ['src/parser.py:1'],
                        }
                    ],
                }
            ],
            'unrequested_changes': [],
            'self_reports': [],
            'files_read': ['src/parser.py'],
        },
    )

    payload = _snap.open_criteria(PLAN_ID)

    assert payload['open_count'] == 0, payload


# --- D1 negative control: one genuinely unmet criterion is still refused --------------------


def test_one_genuinely_unmet_criterion_is_still_refused(plan_context, tmp_path) -> None:
    plan_dir = _plan(plan_context, ['a', 'b'], freeze_from=['a', 'b'])
    _sealed_live(
        plan_dir,
        tmp_path,
        {
            'deliverables': [
                {
                    'number': 1,
                    'verdict': 'met',
                    'criteria': [
                        {'criterion': 'a', 'status': 'met', 'evidence': ['src/parser.py:1']},
                        {'criterion': 'b', 'status': 'not_met', 'evidence': []},
                    ],
                }
            ],
            'unrequested_changes': [],
            'self_reports': [],
            'files_read': ['src/parser.py'],
        },
    )

    payload = _snap.open_criteria(PLAN_ID)

    assert payload['open_count'] == 1, payload
    assert payload['open'][0]['criterion'] == 'b'
