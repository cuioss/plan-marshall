#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``phase-6-finalize/scripts/review_support.py`` and its two internal modules.

Attribution and domains run against a REAL temporary git repository: the realized
footprint, the branch commit list and the delta-round tree difference are all
computed by git. Only three seams are substituted — the plan-context worktree
resolver, the change-ledger reader and the marshal.json loader — plus the status
document the delta round's verdict-currency lookup reads. Validation runs on real
verdict files over a real outline written into the sandboxed plan directory.

Each behaviour is pinned by a matched pair: the input that should produce a finding
and the nearest input that should not.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import _review_support_attribution as _attr
import _review_support_validate as _val
import _status_core
import pytest
import review_support
from toon_parser import parse_toon

PLAN_ID = 'review-support-plan'
STEP = 'functional-review'
TITLES = {1: 'Add the parser', 2: 'Document the parser'}
CRITERIA = {1: ['parser accepts input', 'parser rejects garbage'], 2: ['usage documented']}
PY_FILES = {
    1: [('src/parser.py', 'write-new'), ('test/test_parser.py', 'write-new'), ('README.md', 'read')],
    2: [('doc/parser.md', 'write-replace')],
}
JAVA_FILES = {
    1: [
        ('src/main/java/Parser.java', 'write-new'),
        ('src/test/java/ParserTest.java', 'write-new'),
        ('README.md', 'read'),
    ],
    2: [('doc/parser.md', 'write-replace')],
}
SKILL_DOMAINS = {
    'python': {'file_globs': ['**/*.py']},
    'documentation': {'file_globs': ['**/*.md']},
    'java': {'file_globs': ['**/*.java']},
    'system': {'file_globs': ['**']},
}


def _outline(files: dict[int, list[tuple[str, str]]], criteria_by_number: dict[int, list[str]] = CRITERIA) -> str:
    blocks = []
    for number, entries in files.items():
        affected = '\n'.join(f'- `{path}` ({intent})' for path, intent in entries)
        criteria = '\n'.join(f'- {text}' for text in criteria_by_number[number])
        blocks.append(
            f'### {number}. {TITLES[number]}\n\n**Affected files:**\n{affected}\n\n**Success Criteria:**\n{criteria}\n'
        )
    return '# Solution: review support\n\n## Summary\n\nFixture plan.\n\n## Deliverables\n\n' + '\n'.join(blocks)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


class Env:
    """One sandboxed plan plus the git repository its worktree resolves to."""

    def __init__(self, plan_context: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.plan_context, self.tmp_path, self.monkeypatch = plan_context, tmp_path, monkeypatch
        self.ledger: list[dict[str, Any]] = []
        self.worktree: Path = tmp_path
        monkeypatch.setattr(_attr, 'read_entries', lambda *_a, **_k: list(self.ledger))
        monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: self.worktree)
        monkeypatch.setattr(_attr, 'load_config', lambda *_a, **_k: {'skill_domains': SKILL_DOMAINS})

    def plan(
        self,
        files: dict[int, list[tuple[str, str]]] = PY_FILES,
        plan_id: str = PLAN_ID,
        criteria: dict[int, list[str]] = CRITERIA,
        **refs: Any,
    ) -> None:
        plan_dir = self.plan_context.plan_dir_for(plan_id)
        (plan_dir / _attr.SOLUTION_FILE).write_text(_outline(files, criteria), encoding='utf-8')
        (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main', **refs}), encoding='utf-8')

    def repo(self, name: str = 'repo') -> str:
        """A repository on ``feature`` branched from a one-commit ``main``; returns the base SHA."""
        self.worktree = self.tmp_path / name
        self.worktree.mkdir()
        for args in (('init', '--quiet'), ('symbolic-ref', 'HEAD', 'refs/heads/main')):
            _git(self.worktree, *args)
        for key, value in (('user.email', 't@example.invalid'), ('user.name', 'T'), ('commit.gpgsign', 'false')):
            _git(self.worktree, 'config', key, value)
        base = self.commit({'README.md': 'readme\n'})
        _git(self.worktree, 'checkout', '--quiet', '-b', 'feature')
        return base

    def commit(self, files: dict[str, str]) -> str:
        for relative, body in files.items():
            target = self.worktree / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding='utf-8')
            _git(self.worktree, 'add', relative)
        _git(self.worktree, 'commit', '--quiet', '-m', 'commit')
        return _git(self.worktree, 'rev-parse', 'HEAD')

    def anchor(self, head: str | None) -> None:
        """Record ``head`` as the delta step's completion anchor (``None``: never fired)."""
        steps = {} if head is None else {STEP: {'outcome': 'done', 'display_detail': 'ok', 'head_at_completion': head}}
        status = {'title': 'fixture', 'metadata': {'phase_steps': {'6-finalize': steps}}}
        self.monkeypatch.setattr(_status_core, 'read_status', lambda _plan_id: status)

    def write(self, name: str, payload: dict[str, Any]) -> str:
        path = self.tmp_path / name
        path.write_text(json.dumps(payload), encoding='utf-8')
        return str(path)


@pytest.fixture
def env(plan_context: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Env:
    return Env(plan_context, tmp_path, monkeypatch)


def _change_row(deliverable: Any, sha: str, paths: list[str]) -> dict[str, Any]:
    return {'kind': _attr.KIND_CHANGE, 'deliverable_id': deliverable, 'commit_sha': sha, 'changed_paths': paths}


def _criteria(number: int, evidence: bool = True) -> list[dict[str, Any]]:
    return [
        {'criterion': text, 'status': 'met', 'evidence': [f'src/parser.py:{index}'] if evidence else []}
        for index, text in enumerate(CRITERIA[number], start=1)
    ]


def _functional(**overrides: Any) -> dict[str, Any]:
    verdict: dict[str, Any] = {
        'deliverables': [
            {'number': 1, 'verdict': 'met', 'criteria': _criteria(1)},
            {'number': 2, 'verdict': 'met', 'criteria': _criteria(2)},
        ],
        'unrequested_changes': [],
        'self_reports': [],
        'files_read': ['src/parser.py', 'doc/parser.md'],
    }
    verdict.update(overrides)
    return verdict


def _code_finding(**overrides: Any) -> dict[str, Any]:
    finding = {
        'rule': {'form': 'pack_rule', 'ref': 'python.R1'},
        'location': 'src/parser.py:12',
        'failure_scenario': 'an empty input returns the previous parse',
        'failure_class': 'wrong_result',
        'fix_kind': 'correction',
        'title': 'stale parse returned',
    }
    finding.update(overrides)
    return finding


ACCEPT = {'grading_supported': True, 'may_close': True, 'reason': 'grading holds'}


def _validate(env: Env, verdict: dict[str, Any], kind: str = 'functional', verifier: dict | None = None) -> dict:
    verifier_file = env.write('verifier.json', verifier) if verifier is not None else None
    return review_support.run_validate(PLAN_ID, kind, env.write('verdict.json', verdict), verifier_file)


# --- request D2: a criterion without evidence is unevidenced -------------------------------


def test_met_criterion_without_evidence_is_rewritten_unevidenced_and_blocks(env: Env) -> None:
    env.plan()
    verdict = _functional()
    verdict['deliverables'][0]['criteria'][0]['evidence'] = []

    payload = _validate(env, verdict)

    assert payload['valid'] is True
    assert payload['rewrites'] == [{'deliverable': 1, 'criterion': 1, 'from': 'met', 'to': 'unevidenced'}]
    assert [(f['kind'], f['ref'], f['severity'], f['fix_kind']) for f in payload['findings']] == [
        ('unevidenced_criterion', 'D1.C1', 'blocking', 'implementation')
    ]
    assert payload['facts']['criteria_unevidenced'] == 1


def test_evidenced_criteria_produce_no_rewrite_and_no_finding(env: Env) -> None:
    env.plan()

    payload = _validate(env, _functional())

    assert payload['rewrites'] == []
    assert payload['findings'] == []
    assert payload['facts']['criteria_unevidenced'] == 0
    assert payload['facts']['criteria_checked'] == 3


@pytest.mark.parametrize('verdict', ['met', 'met_with_residuals'])
def test_delivered_verdict_without_any_criterion_row_is_invalid_when_the_outline_has_none(
    env: Env, verdict: str
) -> None:
    """With no parsed outline criterion the row-count check is vacuous, so an empty list must not pass."""
    env.plan(criteria={1: CRITERIA[1], 2: []})
    row: dict[str, Any] = {'number': 2, 'verdict': verdict, 'criteria': []}
    if verdict == 'met_with_residuals':
        row['residuals'] = [{'description': 'example missing', 'consequential': False}]
    verdict_doc = _functional()
    verdict_doc['deliverables'][1] = row

    payload = _validate(env, verdict_doc)

    assert payload['valid'] is False
    assert f'deliverable 2: a {verdict} deliverable evaluates no success criterion' in payload['errors']
    assert not {'findings', 'facts', 'loop_back_target'} & set(payload)


def test_evidenced_criterion_row_satisfies_a_criteria_less_deliverable(env: Env) -> None:
    env.plan(criteria={1: CRITERIA[1], 2: []})
    verdict_doc = _functional()
    verdict_doc['deliverables'][1]['criteria'] = [
        {'criterion': 'usage documented', 'status': 'met', 'evidence': ['doc/parser.md:1']}
    ]

    payload = _validate(env, verdict_doc)

    assert payload['valid'] is True
    assert payload['errors'] == []
    assert payload['facts']['criteria_checked'] == 3


# --- request D3: unrequested changes and false self-reports --------------------------------


def test_undeclared_footprint_file_is_an_unrequested_candidate_and_declared_files_are_not(env: Env) -> None:
    env.plan()
    env.repo()
    env.commit(
        {'src/parser.py': 'p\n', 'test/test_parser.py': 't\n', 'doc/parser.md': 'd\n', 'scripts/extra.sh': 'x\n'}
    )

    payload = _attr.compute_attribution(PLAN_ID, None)

    assert payload['footprint_source'] == _attr.FOOTPRINT_LIVE
    assert payload['unrequested_candidates'] == ['scripts/extra.sh']


def test_false_claim_a_reader_acts_on_is_blocking_and_a_true_claim_is_not_reported(env: Env) -> None:
    env.plan()
    reports = [
        {
            'source': 'TASK-3 note',
            'claim': 'all tests pass',
            'holds': False,
            'reader_acts_on': True,
            'fix_kind': 'correction',
        },
        {'source': 'TASK-4 note', 'claim': 'docs updated', 'holds': True},
        {'source': 'TASK-5 note', 'claim': 'lint clean', 'holds': False, 'reader_acts_on': False},
    ]

    payload = _validate(env, _functional(self_reports=reports))

    assert [(f['kind'], f['ref'], f['severity']) for f in payload['findings']] == [
        ('false_self_report', 'TASK-3 note', 'blocking'),
        ('false_self_report', 'TASK-5 note', 'advisory'),
    ]
    assert payload['facts']['false_self_reports'] == 2


def test_unrequested_change_is_graded_on_its_consequence(env: Env) -> None:
    env.plan()
    changes = [
        {'path': 'scripts/extra.sh', 'consequential': True, 'reason': 'ships a script', 'fix_kind': 'correction'},
        {'path': 'doc/typo.md', 'consequential': False, 'reason': 'typo fix'},
    ]

    payload = _validate(env, _functional(unrequested_changes=changes))

    assert [(f['ref'], f['severity']) for f in payload['findings']] == [
        ('scripts/extra.sh', 'blocking'),
        ('doc/typo.md', 'advisory'),
    ]


# --- request D4: loop-back target and closure ----------------------------------------------


def test_implementation_gap_loops_back_to_execute_and_cannot_close(env: Env) -> None:
    env.plan()
    verdict = _functional()
    verdict['deliverables'][0] = {'number': 1, 'verdict': 'not_met', 'criteria': _criteria(1)}

    payload = _validate(env, verdict, verifier=ACCEPT)

    assert payload['loop_back_target'] == review_support.TARGET_EXECUTE
    assert payload['may_close'] is False


def test_correction_only_blocking_finding_loops_back_to_finalize(env: Env) -> None:
    env.plan()
    reports = [
        {
            'source': 'PR body',
            'claim': 'no API change',
            'holds': False,
            'reader_acts_on': True,
            'fix_kind': 'correction',
        }
    ]

    payload = _validate(env, _functional(self_reports=reports), verifier=ACCEPT)

    assert payload['loop_back_target'] == review_support.TARGET_FINALIZE
    assert payload['may_close'] is False


@pytest.mark.parametrize(
    ('verifier', 'status', 'may_close'),
    [
        (ACCEPT, _val.VERIFIER_ACCEPTED, True),
        (None, _val.VERIFIER_ABSENT, False),
        ({'grading_supported': True, 'may_close': False, 'reason': 'unsure'}, _val.VERIFIER_DECLINED, False),
        ({'grading_supported': 'yes'}, _val.VERIFIER_MALFORMED, False),
    ],
    ids=['accepted', 'absent', 'declined', 'malformed'],
)
def test_clean_round_closes_only_with_an_accepting_verifier(env: Env, verifier, status, may_close) -> None:
    env.plan()

    payload = _validate(env, _functional(), verifier=verifier)

    assert payload['loop_back_target'] == review_support.TARGET_NONE
    assert payload['verifier'] == status
    assert payload['may_close'] is may_close


# --- request D5: a delta round covers only the deliverables its change touches -------------


def test_delta_round_keeps_only_the_deliverable_declaring_the_changed_file(env: Env) -> None:
    env.plan()
    env.repo()
    anchor = env.commit({'src/parser.py': 'p\n', 'doc/parser.md': 'd\n'})
    env.commit({'doc/parser.md': 'd2\n'})
    env.anchor(anchor)

    payload = _attr.compute_attribution(PLAN_ID, STEP)

    assert payload['round_kind'] == _attr.ROUND_DELTA
    assert payload['changed_paths'] == ['doc/parser.md']
    assert [row['number'] for row in payload['deliverables']] == [2]
    assert payload['deliverable_count'] == 1
    assert {row['path'] for row in payload['files']} == {'doc/parser.md'}
    assert payload['unrequested_candidates'] == []


def test_delta_round_keeps_the_deliverable_the_ledger_attributes_the_changed_file_to(env: Env) -> None:
    env.plan()
    env.repo()
    anchor = env.commit({'src/parser.py': 'p\n', 'src/helper.py': 'h\n'})
    env.ledger = [_change_row('D1', anchor, ['src/parser.py', 'src/helper.py'])]
    env.commit({'src/helper.py': 'h2\n'})
    env.anchor(anchor)

    payload = _attr.compute_attribution(PLAN_ID, STEP)

    assert [row['number'] for row in payload['deliverables']] == [1]
    row = payload['deliverables'][0]
    assert (row['declared_count'], row['attributed_count']) == (2, 2)


def test_delta_step_without_an_anchored_firing_is_a_full_round(env: Env) -> None:
    env.plan()
    env.repo()
    env.commit({'src/parser.py': 'p\n'})
    env.anchor(None)

    payload = _attr.compute_attribution(PLAN_ID, STEP)

    assert (payload['round_kind'], payload['round_reason']) == (_attr.ROUND_FULL, 'first_firing')
    assert 'changed_paths' not in payload
    assert payload['deliverable_count'] == 2


# --- request D12: an uncited code finding is rejected --------------------------------------


def test_uncited_code_finding_is_rejected_and_the_verdict_is_invalid(env: Env) -> None:
    verdict = {'findings': [_code_finding(rule={})], 'domains_reviewed': ['python'], 'files_read': ['src/parser.py']}

    payload = _validate(env, verdict, kind='code')

    assert payload['valid'] is False
    assert payload['rejected_findings'] == [{'finding': 1, 'missing': 'rule'}]
    assert not {'findings', 'facts', 'loop_back_target'} & set(payload)


def test_cited_code_finding_is_accepted_and_graded(env: Env) -> None:
    verdict = {'findings': [_code_finding()], 'domains_reviewed': ['python'], 'files_read': ['src/parser.py']}

    payload = _validate(env, verdict, kind='code')

    assert payload['valid'] is True
    assert payload['rejected_findings'] == []
    assert [(f['ref'], f['severity']) for f in payload['findings']] == [('src/parser.py:12', 'blocking')]
    assert payload['facts'] == {
        'domains_reviewed': 1,
        'files_read': 1,
        'rules_cited': 1,
        'blocking_count': 1,
        'advisory_count': 0,
    }
    assert payload['loop_back_target'] == review_support.TARGET_FINALIZE


# --- clause 5: ledger attribution needs the commit on the branch ---------------------------


def test_ledger_attribution_holds_on_branch_and_falls_back_when_the_commit_is_off_branch(env: Env) -> None:
    env.plan()
    base = env.repo()
    sha = env.commit({'src/parser.py': 'p\n', 'src/helper.py': 'h\n', 'doc/parser.md': 'd\n'})
    env.ledger = [_change_row('D1', sha, ['src/parser.py', 'src/helper.py']), _change_row(2, base, ['doc/parser.md'])]

    payload = _attr.compute_attribution(PLAN_ID, None)

    rows = {row['number']: row for row in payload['deliverables']}
    assert (rows[1]['attribution_source'], rows[1]['reason']) == (_attr.SOURCE_LEDGER, _attr.REASON_NONE)
    assert (rows[2]['attribution_source'], rows[2]['reason']) == (
        _attr.SOURCE_DECLARED_ONLY,
        _attr.REASON_COMMIT_NOT_ON_BRANCH,
    )
    origins = {row['path']: row['origin'] for row in payload['files'] if row['deliverable'] == 1}
    assert origins == {'src/helper.py': 'ledger', 'src/parser.py': 'both', 'test/test_parser.py': 'declared'}
    assert payload['unrequested_candidates'] == []


def test_ledger_rows_for_another_deliverable_only_name_the_absent_id(env: Env) -> None:
    env.plan()
    env.repo()
    sha = env.commit({'src/parser.py': 'p\n'})
    env.ledger = [_change_row('D1', sha, ['src/parser.py'])]

    rows = {row['number']: row for row in _attr.compute_attribution(PLAN_ID, None)['deliverables']}

    assert rows[2]['reason'] == _attr.REASON_DELIVERABLE_ID_ABSENT


def test_unresolvable_worktree_omits_the_candidates_and_names_why_the_ledger_is_unused(
    env: Env, outside_repo_dir: Path
) -> None:
    env.plan()
    env.worktree = outside_repo_dir
    env.ledger = [_change_row('D1', 'a' * 40, ['src/parser.py'])]

    payload = _attr.compute_attribution(PLAN_ID, None)

    assert payload['footprint_source'] == _attr.FOOTPRINT_UNRESOLVED
    assert 'unrequested_candidates' not in payload
    assert payload['deliverables'][0]['reason'] == _attr.REASON_BRANCH_UNRESOLVED


def test_captured_footprint_is_the_fallback_when_the_worktree_is_gone(env: Env, outside_repo_dir: Path) -> None:
    env.plan(realized_footprint=['src/parser.py', 'scripts/extra.sh'])
    env.worktree = outside_repo_dir

    payload = _attr.compute_attribution(PLAN_ID, None)

    assert payload['footprint_source'] == _attr.FOOTPRINT_CAPTURED
    assert payload['unrequested_candidates'] == ['scripts/extra.sh']


# --- clause D: declared domains united with footprint-matched ones -------------------------


def test_domains_unite_declared_and_footprint_matched_with_provenance(env: Env) -> None:
    env.plan(domains=['python', 'oci'])
    env.repo()
    env.commit({'src/parser.py': 'p\n', 'doc/parser.md': 'd\n'})

    payload = _attr.compute_domains(PLAN_ID)

    assert payload['domains'] == [
        {'domain': 'documentation', 'provenance': _attr.PROVENANCE_FOOTPRINT},
        {'domain': 'oci', 'provenance': _attr.PROVENANCE_DECLARED},
        {'domain': 'python', 'provenance': _attr.PROVENANCE_BOTH},
    ]
    assert payload['domain_count'] == 3


def test_domains_match_the_captured_footprint_when_the_worktree_is_gone(env: Env, outside_repo_dir: Path) -> None:
    env.plan(domains=['oci'], realized_footprint=['src/parser.py'])
    env.worktree = outside_repo_dir

    payload = _attr.compute_domains(PLAN_ID)

    assert payload['footprint_source'] == _attr.FOOTPRINT_CAPTURED
    assert payload['domains'] == [
        {'domain': 'oci', 'provenance': _attr.PROVENANCE_DECLARED},
        {'domain': 'python', 'provenance': _attr.PROVENANCE_FOOTPRINT},
    ]


# --- request D1: the output shape does not depend on the language --------------------------


def _shape(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _shape(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_shape(value[0])] if value else []
    return type(value).__name__


def test_java_only_and_python_only_plans_produce_the_same_output_shape(env: Env) -> None:
    shapes = []
    for plan_id, files in (('python-only-plan', PY_FILES), ('java-only-plan', JAVA_FILES)):
        env.plan(files, plan_id=plan_id)
        env.repo(plan_id)
        env.commit(
            {path: 'x\n' for path, intent in files[1] + files[2] if intent != 'read'} | {'scripts/extra.sh': 'x\n'}
        )
        attribution = _attr.compute_attribution(plan_id, None)
        verifier = env.write('verifier.json', ACCEPT)
        validation = review_support.run_validate(
            plan_id, 'functional', env.write('verdict.json', _functional()), verifier
        )
        shapes.append((_shape(attribution), _shape(validation)))

    assert shapes[0] == shapes[1]


# --- error envelopes and the CLI ------------------------------------------------------------


def test_unreadable_verdict_and_missing_outline_are_named_errors(env: Env) -> None:
    missing = review_support.run_validate(PLAN_ID, 'code', str(env.tmp_path / 'absent.json'), None)
    no_outline = _validate(env, _functional())

    assert (missing['status'], missing['error']) == ('error', 'verdict_file_unreadable')
    assert (no_outline['status'], no_outline['error']) == ('error', 'outline_not_found')


def test_cli_validate_emits_toon_and_exits_zero(env: Env, monkeypatch, capsys) -> None:
    env.plan()
    argv = ['review_support.py', 'validate', '--plan-id', PLAN_ID, '--kind', 'functional']
    argv += ['--verdict-file', env.write('verdict.json', _functional()), '--verifier-file', env.write('v.json', ACCEPT)]
    monkeypatch.setattr(sys, 'argv', argv)

    exit_code = review_support.main()

    parsed = parse_toon(capsys.readouterr().out)
    assert exit_code == 0
    assert (parsed['status'], parsed['valid'], parsed['may_close']) == ('success', True, True)
    assert parsed['facts']['deliverables_met'] == 2
