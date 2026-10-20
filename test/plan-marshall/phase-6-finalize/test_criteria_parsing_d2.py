#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-70 D2 — spec and citation parsing match real documents.

Five behaviours, each with the nearest input that must NOT misfire:

* a wrapped spec Done-when is read whole, not only its first line;
* a criterion naming "the canonical prefix set" is not read as "pre-fix";
* a backticked citation and a build-log citation are accepted;
* a test file that exists only in the working tree (not at the graded head) is
  refused;
* a ``not_run`` evidence check is surfaced as a finding, never silently accepted.

The tree-dependent behaviours run against a REAL temporary git repository; only
the plan-context worktree resolver is substituted.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import _criteria_snapshot as _snap
import _review_support_attribution as _attr
import _review_support_validate as _validate
import pytest
import review_support

PLAN_ID = 'lb70-criteria-parsing-d2'


@pytest.fixture(autouse=True)
def _no_main_checkout_fallback(monkeypatch):
    """Keep the evidence root off unless a test deliberately supplies a repo."""
    monkeypatch.setattr(review_support, '_main_checkout_root', lambda: None)


#: A fixture copy of the PLAN-LB-52 spec's Deliverables section: deliverable 1's
#: Done-when is WRAPPED prose with no bullet list, the shape the one-line capture
#: truncated.
LB52_SPEC = """# PLAN-LB-52: Criteria integrity

## Deliverables

1. **The criteria are frozen and the verdict is the reviewer's.**
   - At outline approval, a script snapshots the success criteria per deliverable together with
     the request's Done-when text.

   *Done when:* tests: (a) an outline whose criterion was narrowed after approval yields a
   finding; (b) a verdict file edited after the reviewer wrote it is refused; (c) a deleted
   criterion with no operator decision is refused. Each fails at `c8adaf178`.

2. **What the review grades cannot be weakened on the way.**
   - **Weakened tests:** every pre-existing test whose assertions the branch removed.

   *Done when:* tests: a branch deleting an assertion from an existing test yields a finding.
"""

LB52_D1_DONE_WHEN = (
    'tests: (a) an outline whose criterion was narrowed after approval yields a finding; '
    '(b) a verdict file edited after the reviewer wrote it is refused; (c) a deleted criterion '
    'with no operator decision is refused. Each fails at `c8adaf178`.'
)


def _outline(criteria: list[str]) -> str:
    body = '\n'.join(f'- {text}' for text in criteria)
    return (
        '# Solution: parsing\n\n## Deliverables\n\n### 1. Deliver the change\n\n'
        '**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        f'**Success Criteria:**\n{body}\n'
    )


def _plan(plan_context: Any, criteria: list[str], *, freeze: bool = False) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    (plan_dir / 'status.json').write_text(
        json.dumps({'title': 'fixture', 'phases': [], 'current_phase': '6-finalize', 'metadata': {}}),
        encoding='utf-8',
    )
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    (plan_dir / 'solution_outline.md').write_text(_outline(criteria), encoding='utf-8')
    if freeze:
        _snap.write_snapshot(PLAN_ID)
    return plan_dir


def _verdict(criteria: list[str], evidence: list[list[str]]) -> dict[str, Any]:
    return {
        'deliverables': [
            {
                'number': 1,
                'verdict': 'met',
                'criteria': [
                    {'criterion': text, 'status': 'met', 'evidence': ev}
                    for text, ev in zip(criteria, evidence, strict=True)
                ],
            }
        ],
        'unrequested_changes': [],
        'self_reports': [],
        'files_read': ['src/parser.py'],
    }


def _sealed(tmp_path: Path, document: dict[str, Any]) -> str:
    path = tmp_path / 'verdict.json'
    path.write_text(json.dumps(document), encoding='utf-8')
    assert review_support.run_author_verdict(PLAN_ID, 'functional', str(path))['status'] == 'success'
    return str(path)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / 'repo'
    repo.mkdir()
    for args in (('init', '--quiet'), ('symbolic-ref', 'HEAD', 'refs/heads/main')):
        _git(repo, *args)
    for key, value in (('user.email', 't@example.invalid'), ('user.name', 'T'), ('commit.gpgsign', 'false')):
        _git(repo, 'config', key, value)
    return repo


def _commit(repo: Path, files: dict[str, str]) -> str:
    for relative, body in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding='utf-8')
        _git(repo, 'add', relative)
    subprocess.run(
        ['git', '-C', str(repo), 'commit', '--quiet', '--message', 'commit'],
        capture_output=True,
        text=True,
        check=True,
        env={
            **os.environ,
            'GIT_COMMITTER_DATE': '2020-01-01T00:00:00+00:00',
            'GIT_AUTHOR_DATE': '2020-01-01T00:00:00+00:00',
        },
    )
    return _git(repo, 'rev-parse', 'HEAD')


# --- D2 (a): a wrapped spec Done-when is read whole ----------------------------------------


def test_wrapped_spec_done_when_is_read_whole() -> None:
    rows = _snap._spec_deliverables(LB52_SPEC)

    assert rows[0]['done_when'] == LB52_D1_DONE_WHEN


def test_spec_done_when_stops_at_the_next_deliverable() -> None:
    rows = _snap._spec_deliverables(LB52_SPEC)

    assert rows[1]['done_when'] == 'tests: a branch deleting an assertion from an existing test yields a finding.'


# --- D2 (b): "prefix" is not "pre-fix" ------------------------------------------------------


def test_prefix_is_not_a_pre_fix_criterion() -> None:
    assert _validate.is_pre_fix_criterion('uses the canonical prefix set') is False


def test_prefix_criterion_graded_met_stays_met(plan_context, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['uses the canonical prefix set']
    _plan(plan_context, criteria)

    payload = review_support.run_validate(
        PLAN_ID, 'functional', _sealed(tmp_path, _verdict(criteria, [['src/x.py:1']])), None
    )

    assert payload['rewrites'] == []
    assert payload['findings'] == []
    assert payload['facts']['criteria_unevidenced'] == 0


# --- D2 (c): backticked and build-log citations are accepted --------------------------------


def test_backticked_test_citation_is_accepted(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'test/sample_test.py': 'def test_present():\n    assert 1 == 1\n'})
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: repo)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, freeze=True)

    payload = review_support.run_validate(
        PLAN_ID, 'functional', _sealed(tmp_path, _verdict(criteria, [['`test/sample_test.py::test_present`']])), None
    )

    assert payload['valid'] is True
    assert payload['errors'] == []


def test_build_log_citation_is_accepted(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: repo)
    root = tmp_path / 'checkout'
    plan_results = root / '.plan' / 'local' / 'plans' / PLAN_ID / 'build-results'
    log = plan_results / 'python-1.log'
    log.parent.mkdir(parents=True)
    log.write_text('collected 3 items\n', encoding='utf-8')
    monkeypatch.setattr(_validate, 'cwd_checkout_root', lambda: str(root), raising=False)
    monkeypatch.setattr(_validate, 'get_build_results_dir', lambda _plan_id: plan_results, raising=False)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, freeze=True)

    payload = review_support.run_validate(
        PLAN_ID,
        'functional',
        _sealed(tmp_path, _verdict(criteria, [[f'.plan/local/plans/{PLAN_ID}/build-results/python-1.log']])),
        None,
    )

    assert payload['valid'] is True
    assert payload['errors'] == []


def test_plan_local_citation_cannot_escape_the_checkout(plan_context, tmp_path, monkeypatch) -> None:
    """A `.plan/` citation resolves against the checkout and cannot climb out of it."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: repo)
    root = tmp_path / 'checkout'
    root.mkdir()
    (tmp_path / 'secret.log').write_text('secret\n', encoding='utf-8')
    monkeypatch.setattr(_validate, 'cwd_checkout_root', lambda: str(root), raising=False)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, freeze=True)

    payload = review_support.run_validate(
        PLAN_ID, 'functional', _sealed(tmp_path, _verdict(criteria, [['.plan/../../secret.log']])), None
    )

    assert payload['valid'] is False
    assert any('does not exist at the graded head' in error for error in payload['errors'])


def test_evidence_root_falls_back_to_the_main_checkout(plan_context, tmp_path, monkeypatch) -> None:
    """A plan without a worktree is graded against the main checkout, not not-run."""
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    monkeypatch.setattr(review_support, '_main_checkout_root', lambda: tmp_path)

    assert review_support._evidence_root(PLAN_ID) == tmp_path


def test_evidence_root_does_not_fall_back_for_a_missing_worktree_plan(plan_context, tmp_path, monkeypatch) -> None:
    """A declared-but-missing worktree must not be graded against the main checkout."""
    plan_dir = _plan(plan_context, ['parser accepts input'])
    (plan_dir / 'status.json').write_text(
        json.dumps({'title': 'x', 'metadata': {'use_worktree': True, 'worktree_path': '/gone'}}), encoding='utf-8'
    )
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    monkeypatch.setattr(review_support, '_main_checkout_root', lambda: tmp_path)

    assert review_support._evidence_root(PLAN_ID) is None


def test_evidence_root_is_none_when_no_tree_resolves(plan_context, monkeypatch) -> None:
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    monkeypatch.setattr(review_support, '_main_checkout_root', lambda: None)

    assert review_support._evidence_root(PLAN_ID) is None


# --- D2 (d): a test file absent at the graded head is refused -------------------------------


def test_uncommitted_test_file_citation_is_refused(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    (repo / 'test').mkdir()
    (repo / 'test' / 'sample_test.py').write_text('def test_present():\n    assert 1 == 1\n', encoding='utf-8')
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: repo)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, freeze=True)

    payload = review_support.run_validate(
        PLAN_ID, 'functional', _sealed(tmp_path, _verdict(criteria, [['test/sample_test.py::test_present']])), None
    )

    assert payload['valid'] is False
    assert any('does not exist at the graded head' in error for error in payload['errors'])


# --- D2 (e): a not_run evidence check produces a finding ------------------------------------


def test_not_run_evidence_check_produces_a_finding(plan_context, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, freeze=True)

    payload = review_support.run_validate(
        PLAN_ID, 'functional', _sealed(tmp_path, _verdict(criteria, [['src/x.py:1']])), None
    )

    assert payload['evidence_check'] == 'not_run'
    assert any(finding['kind'] == 'evidence_check_not_run' for finding in payload['findings'])
