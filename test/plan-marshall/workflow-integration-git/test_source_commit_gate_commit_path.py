#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D2 — the finalize commit gate is wired into the real commit path.

The gate predicate (``evaluate_source_commit_gate``) existed but had no caller,
so no commit was ever refused. These tests drive the REAL commit path — the
``git-workflow commit`` verb — and pin the five Done-when clauses:

* (a) a finalize-phase source commit with no sanction is refused;
* (b) a review-rubric section-6 loop-back correction commit passes;
* (c) a settle-band ``--step`` commit passes;
* (d) a ``.plan/``-only commit passes;
* (e) a refusal exits non-zero.

The verb judges the STAGED commit (``git diff --cached``), so each test stages
what it means to commit. A refusal is asserted as a NON-ZERO exit, never as
``status: success, allowed: false``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

# Loaded for the pure-predicate settle-band pin; ``register=False`` publishes
# nothing, so it cannot collide with the other module's registration.
git_workflow = load_script_module(
    'plan-marshall',
    'workflow-integration-git',
    'git-workflow.py',
    module_name='git_workflow_commit_path',
    register=False,
)


def _run(args: list[str]) -> tuple[str, str, int]:
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    subprocess.run(['git', 'init', str(root)], check=True, capture_output=True)
    _git(root, 'config', 'user.email', 'test@example.com')
    _git(root, 'config', 'user.name', 'Test')
    (root / 'baseline.txt').write_text('baseline\n', encoding='utf-8')
    _git(root, 'add', 'baseline.txt')
    _git(root, 'commit', '-m', 'baseline')


def _write_status(root: Path, plan_id: str, phase: str) -> Path:
    plan_dir = root / '.plan' / 'local' / 'plans' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(json.dumps({'plan_id': plan_id, 'phase': phase}), encoding='utf-8')
    return plan_dir


def _stage(root: Path, name: str, content: str = 'x\n') -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    _git(root, 'add', name)


def _commit_count(root: Path) -> int:
    return len([line for line in _git(root, 'log', '--oneline').stdout.splitlines() if line.strip()])


def test_finalize_source_commit_refused_through_commit_verb(tmp_path: Path) -> None:
    """(a) + (e): a finalize source commit with no sanction is refused, exit non-zero."""
    _init_repo(tmp_path)
    _stage(tmp_path, 'src/a.py')

    stdout, _stderr, code = _run(
        ['commit', '--project-dir', str(tmp_path), '--phase', '6-finalize', '--message', 'fix: a thing']
    )

    result = parse_toon(stdout)
    assert result.get('refused') is True, f'expected a refusal payload, got {result!r}'
    assert result['reason'] == 'no_sanction'
    assert code != 0, 'a refusal must exit non-zero, not report status: success, allowed: false'
    assert _commit_count(tmp_path) == 1, 'the refused commit must not have been created'


def test_section6_loop_back_correction_commit_passes(tmp_path: Path) -> None:
    """(b): a review-rubric section-6 inline-correction record sanctions the commit."""
    _init_repo(tmp_path)
    plan_dir = _write_status(tmp_path, 'P', '6-finalize')
    findings = plan_dir / 'artifacts' / 'findings'
    findings.mkdir(parents=True, exist_ok=True)
    (findings / 'qgate-6-finalize.jsonl').write_text(
        json.dumps(
            {
                'title': 'Code review finding per review-rubric section 6',
                'detail': 'inline-correction applied for the section-6 loop-back',
            }
        )
        + '\n',
        encoding='utf-8',
    )
    _stage(tmp_path, 'src/a.py')

    stdout, _stderr, code = _run(['commit', '--project-dir', str(tmp_path), '--message', 'fix: correction'])

    result = parse_toon(stdout)
    assert result['status'] == 'success', f'{result!r}'
    assert result['reason'] == 'section6_record'
    assert code == 0
    assert _commit_count(tmp_path) == 2, 'the sanctioned commit must have been created'


def test_settle_band_step_commit_passes(tmp_path: Path) -> None:
    """(c): a settle-band ``--step`` sanctions the source commit (quality-gate autofix)."""
    _init_repo(tmp_path)
    _stage(tmp_path, 'src/a.py')

    stdout, _stderr, code = _run(
        [
            'commit',
            '--project-dir',
            str(tmp_path),
            '--phase',
            '6-finalize',
            '--step',
            'pre-push-quality-gate',
            '--message',
            'style: apply quality-gate autofix',
        ]
    )

    result = parse_toon(stdout)
    assert result['status'] == 'success', f'{result!r}'
    assert result['reason'] == 'settle_band_step'
    assert code == 0
    assert _commit_count(tmp_path) == 2


def test_plan_only_commit_passes(tmp_path: Path) -> None:
    """(d): a ``.plan/``-only commit passes with no sanction."""
    _init_repo(tmp_path)
    _stage(tmp_path, '.plan/local/plans/P/status.json', '{}\n')

    stdout, _stderr, code = _run(
        ['commit', '--project-dir', str(tmp_path), '--phase', '6-finalize', '--message', 'chore: plan state']
    )

    result = parse_toon(stdout)
    assert result['status'] == 'success', f'{result!r}'
    assert result['reason'] == 'plan_only'
    assert code == 0
    assert _commit_count(tmp_path) == 2


def test_pure_gate_sanctions_a_settle_step_identity() -> None:
    """The predicate sanctions by STEP IDENTITY, not by finding text."""
    verdict = git_workflow.evaluate_source_commit_gate(
        '6-finalize', ['src/a.py'], [], [], step='finalize-step-simplify'
    )
    assert verdict['allowed'] is True
    assert verdict['reason'] == 'settle_band_step'
    assert verdict['step'] == 'finalize-step-simplify'


def test_non_finalize_commit_passes_through_the_verb(tmp_path: Path) -> None:
    """Outside 6-finalize the verb commits a source change untouched."""
    _init_repo(tmp_path)
    _stage(tmp_path, 'src/a.py')

    stdout, _stderr, code = _run(
        ['commit', '--project-dir', str(tmp_path), '--phase', '5-execute', '--message', 'feat: work']
    )

    result = parse_toon(stdout)
    assert result['status'] == 'success', f'{result!r}'
    assert result['reason'] == 'not_finalize'
    assert code == 0
