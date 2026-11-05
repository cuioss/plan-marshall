#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-105 D3 — a re-observed blocking finding has one visible outcome.

At HEAD an operator cannot accept a finding the review keeps re-filing: the full
round resolves the earlier findings ``taken_into_account``, the re-filed identical
finding is ``kept`` (so it is not pending), it still blocks ``validate``, and
``loop-back close --accept`` refuses it with ``finding_not_pending``.

After this plan a re-observed blocking finding is pending again through an
explicit, documented outcome, ``--reopen`` says WHY when it does not re-arm, and a
re-observation alone never re-arms an operator-accepted record.
"""

from __future__ import annotations

import json
import subprocess
from argparse import Namespace
from pathlib import Path
from typing import Any

import _cmd_loop_back as _loop_back
import _findings_core
import pytest

from conftest import get_skill_dir, load_script_module

PLAN_ID = 'lb105-reobservation-d3'
PHASE = '6-finalize'
RULE = 'functional-review'

#: Git environment inherited from an outer repository would re-point the fixture
#: repos' ``git -C`` calls at that repository and its index.
_GIT_REPO_ENV_VARS = (
    'GIT_DIR',
    'GIT_WORK_TREE',
    'GIT_COMMON_DIR',
    'GIT_INDEX_FILE',
    'GIT_OBJECT_DIRECTORY',
    'GIT_ALTERNATE_OBJECT_DIRECTORIES',
    'GIT_PREFIX',
)


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch):
    for name in _GIT_REPO_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_lb105_d3_lifecycle')

#: The workflow's own `qgate add` tiles, exactly as functional-review.md Branch B
#: spells them. The re-add must match the record field for field.
_TITLE = 'ambiguous_wording at doc/a.md:12'
_DETAIL = 'the section says one thing and the table another [fix_kind correction]'


def _plan(plan_context: Any) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    (plan_dir / 'status.json').write_text(
        json.dumps({'title': 'fixture', 'phases': [], 'current_phase': '6-finalize', 'metadata': {}}),
        encoding='utf-8',
    )
    return plan_dir


def _file(reopen: bool = False) -> dict[str, Any]:
    return _findings_core.add_qgate_finding(
        PLAN_ID,
        PHASE,
        'qgate',
        'bug',
        _TITLE,
        _DETAIL,
        rule=RULE,
        reopen=reopen,
    )


def _pending() -> list[dict[str, Any]]:
    queried = _findings_core.query_qgate_findings(PLAN_ID, PHASE, resolution='pending')
    assert queried['status'] == 'success', queried
    findings: list[dict[str, Any]] = queried['findings']
    return findings


def _records() -> dict[str, dict[str, Any]]:
    queried = _findings_core.query_qgate_findings(PLAN_ID, PHASE)
    assert queried['status'] == 'success', queried
    return {finding['hash_id']: finding for finding in queried['findings']}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / 'repo'
    repo.mkdir()
    for args in (('init', '--quiet'), ('symbolic-ref', 'HEAD', 'refs/heads/main')):
        _git(repo, *args)
    for key, value in (('user.email', 't@example.invalid'), ('user.name', 'T'), ('commit.gpgsign', 'false')):
        _git(repo, 'config', key, value)
    (repo / 'README.md').write_text('readme\n', encoding='utf-8')
    _git(repo, 'add', 'README.md')
    _git(repo, 'commit', '--quiet', '--message', 'one')
    return repo


# --- D3 (a): the re-filed finding is pending, and a close can accept it ---------------------


def test_a_refiled_blocking_finding_is_pending_and_can_be_accepted(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo)
    _lifecycle.cmd_create(
        Namespace(
            plan_id=PLAN_ID,
            title='Re-observation',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    _plan(plan_context)
    first = _file()
    assert first['status'] == 'success', first
    resolved = _findings_core.resolve_qgate_findings_by_rule(
        PLAN_ID, PHASE, RULE, 'taken_into_account', 'superseded by the round at the new head'
    )
    assert resolved['status'] == 'success', resolved
    assert [entry['hash_id'] for entry in resolved['resolved']] == [first['hash_id']]

    again = _file()

    assert again['status'] == 'reopened', again
    assert again['previous_resolution'] == 'taken_into_account'
    pending = _pending()
    assert [finding['hash_id'] for finding in pending] == [first['hash_id']]

    closed = _loop_back.cmd_loop_back_close(
        Namespace(
            plan_id=PLAN_ID,
            step=_loop_back.FUNCTIONAL_REVIEW_STEP,
            head=_git(repo, 'rev-parse', 'HEAD'),
            accept=[first['hash_id']],
            rationale='the finding is accepted after the re-observation',
            waive_refire=[],
        )
    )

    assert closed is not None and closed['status'] == 'success', closed
    assert _records()[first['hash_id']]['resolution'] == 'accepted'


# --- D3 (b): --reopen names why it did not re-arm -------------------------------------------


def test_reopen_against_a_taken_into_account_record_names_the_not_reopened_outcome(plan_context) -> None:
    _plan(plan_context)
    first = _file()
    _findings_core.resolve_qgate_findings_by_rule(PLAN_ID, PHASE, RULE, 'taken_into_account', 'superseded')

    result = _file(reopen=True)

    assert result['status'] == 'kept', result
    assert result['not_reopened'] == 'taken_into_account', result
    assert _records()[first['hash_id']]['resolution'] == 'taken_into_account'


# --- D3 (c): Branch B reads the QGATE_PERSIST_OK partition ---------------------------------


def test_branch_b_reads_the_qgate_persist_ok_partition() -> None:
    """Every document that restates the partition names all four values in place."""
    finalize = get_skill_dir('plan-marshall', 'phase-6-finalize')
    documents = {
        'phase-6-finalize/workflow/functional-review.md': finalize / 'workflow' / 'functional-review.md',
        'phase-6-finalize/workflow/code-review.md': finalize / 'workflow' / 'code-review.md',
        'manage-findings/SKILL.md': get_skill_dir('plan-marshall', 'manage-findings') / 'SKILL.md',
    }
    for label, path in documents.items():
        text = path.read_text(encoding='utf-8')
        line = next(
            (entry for entry in text.splitlines() if 'QGATE_PERSIST_OK' in entry and 'deduplicated' in entry),
            '',
        )
        assert line, label
        for value in sorted(_findings_core.QGATE_PERSIST_OK):
            assert f'`{value}`' in line, (label, value)


# --- D3 controls ---------------------------------------------------------------------------


def test_an_identical_add_against_a_pending_record_is_deduplicated(plan_context) -> None:
    _plan(plan_context)
    first = _file()

    again = _file()

    assert again['status'] == 'deduplicated', again
    assert again['hash_id'] == first['hash_id']
    assert len(_records()) == 1


def test_an_operator_accepted_record_is_not_rearmed_by_an_observation(plan_context) -> None:
    _plan(plan_context)
    first = _file()
    _findings_core.resolve_qgate_finding(PLAN_ID, PHASE, first['hash_id'], 'accepted', detail='operator decision')

    again = _file()

    assert again['status'] == 'kept', again
    assert _records()[first['hash_id']]['resolution'] == 'accepted'
