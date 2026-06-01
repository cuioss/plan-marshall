"""Tests for ``measure-thoroughness.py`` (D5 achieved-thoroughness measurement).

Exercises the HYBRID measurement end-to-end via subprocess (``run_script``):
the deterministic item-coverage footprint (reusing the artifact-consistency
footprint primitive), the floor combination of item-coverage and relation-depth
rungs, and the emitted ``work/coverage-measurement-{phase}.toon`` artifact shape
that the D4 ``coverage_contract`` capture reads.

Cases:
    a. Full footprint (recall >= threshold) → item-coverage meets the full-read
       rung (T2).
    b. Partial footprint (recall < threshold) → item-coverage below (T1).
    c. Floor combination: relation-depth rung below item-coverage floors the
       achieved rung down.
    d. Unaudited relation depth cannot raise the achieved rung above
       item coverage.
    e. The emitted artifact carries the exact fields D4 reads.
    f. Empty declared footprint → trivially full coverage.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

# Need serialize_toon / parse_toon to read the emitted artifact.
_TOON_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-files' / 'scripts'
if str(_TOON_DIR) not in sys.path:
    sys.path.insert(0, str(_TOON_DIR))

from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402

SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'measure-thoroughness.py'


def _build_plan(
    tmp_path: Path,
    monkeypatch,
    plan_id: str,
    declared: list[str],
    modified: list[str],
) -> tuple[str, Path]:
    """Create a minimal plan dir with a controlled declared/actual footprint."""
    base = tmp_path / 'base'
    base.mkdir(exist_ok=True)
    plan_dir = base / 'plans' / plan_id
    plan_dir.mkdir(parents=True)

    bullets = '\n'.join(f'- `{p}`' for p in declared)
    outline = (
        '# Solution: Footprint test\n\n'
        '## Summary\n\nFootprint fixture.\n\n'
        '## Overview\n\nOverview.\n\n'
        '## Deliverables\n\n### 1. One\n\n**Affected files:**\n'
        f'{bullets}\n'
    )
    (plan_dir / 'solution_outline.md').write_text(outline, encoding='utf-8')
    (plan_dir / 'references.json').write_text(
        json.dumps({'modified_files': modified}), encoding='utf-8'
    )
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return plan_id, plan_dir


def _read_artifact(plan_dir: Path, phase: str) -> dict:
    artifact = plan_dir / 'work' / f'coverage-measurement-{phase}.toon'
    assert artifact.is_file(), f'measurement artifact missing at {artifact}'
    return parse_toon(artifact.read_text(encoding='utf-8'))


# =============================================================================
# (a) Full footprint → full-read item-coverage rung
# =============================================================================


def test_full_footprint_meets_full_read_rung(tmp_path, monkeypatch):
    plan_id, plan_dir = _build_plan(
        tmp_path,
        monkeypatch,
        'cov-full',
        declared=['src/a.py', 'src/b.py', 'src/c.py'],
        modified=['src/a.py', 'src/b.py', 'src/c.py'],
    )
    result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live', '--phase', '5-execute')
    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    assert data['item_coverage_rung'] == 'T2'
    assert float(data['deterministic_item_coverage']) == 1.0

    artifact = _read_artifact(plan_dir, '5-execute')
    assert artifact['item_coverage_rung'] == 'T2'


# =============================================================================
# (b) Partial footprint → below (sampled) rung
# =============================================================================


def test_partial_footprint_below_threshold_is_sampled_rung(tmp_path, monkeypatch):
    # 1 of 4 declared touched → recall 0.25, below the 0.70 threshold.
    plan_id, plan_dir = _build_plan(
        tmp_path,
        monkeypatch,
        'cov-partial',
        declared=['src/a.py', 'src/b.py', 'src/c.py', 'src/d.py'],
        modified=['src/a.py'],
    )
    result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live', '--phase', '5-execute')
    assert result.success, result.stderr
    data = result.toon()
    assert data['item_coverage_rung'] == 'T1'
    assert float(data['deterministic_item_coverage']) == 0.25


# =============================================================================
# (c) Floor combination: relation-depth below item-coverage floors down
# =============================================================================


def test_relation_depth_below_item_coverage_floors_achieved(tmp_path, monkeypatch):
    # Full footprint → item-coverage T2, but relation auditor says T1 → floor T1.
    plan_id, plan_dir = _build_plan(
        tmp_path,
        monkeypatch,
        'cov-floor-down',
        declared=['src/a.py'],
        modified=['src/a.py'],
    )
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--plan-id',
        plan_id,
        '--mode',
        'live',
        '--phase',
        '5-execute',
        '--relation-depth-rung',
        'T1',
    )
    assert result.success, result.stderr
    data = result.toon()
    assert data['item_coverage_rung'] == 'T2'
    assert data['relation_depth_verdict'] == 'T1'
    assert data['achieved_thoroughness'] == 'T1', 'achieved must floor to the lower relation-depth rung'


def test_relation_depth_above_item_coverage_does_not_raise_achieved(tmp_path, monkeypatch):
    # Full footprint → item-coverage T2; relation auditor says T4 → floor stays T2.
    plan_id, plan_dir = _build_plan(
        tmp_path,
        monkeypatch,
        'cov-floor-cap',
        declared=['src/a.py'],
        modified=['src/a.py'],
    )
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--plan-id',
        plan_id,
        '--mode',
        'live',
        '--phase',
        '5-execute',
        '--relation-depth-rung',
        'T4',
    )
    assert result.success, result.stderr
    data = result.toon()
    assert data['achieved_thoroughness'] == 'T2', 'item coverage floors the achieved rung at T2'


# =============================================================================
# (d) Unaudited relation depth cannot raise above item coverage
# =============================================================================


def test_unaudited_relation_depth_defaults_to_item_coverage(tmp_path, monkeypatch):
    plan_id, plan_dir = _build_plan(
        tmp_path,
        monkeypatch,
        'cov-unaudited',
        declared=['src/a.py'],
        modified=['src/a.py'],
    )
    result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live', '--phase', '5-execute')
    assert result.success, result.stderr
    data = result.toon()
    assert data['relation_depth_verdict'] == 'unaudited'
    # An unaudited verdict cannot raise the floor — achieved == item coverage.
    assert data['achieved_thoroughness'] == data['item_coverage_rung'] == 'T2'


# =============================================================================
# (e) Emitted artifact carries the fields D4 reads
# =============================================================================


def test_artifact_carries_d4_fields(tmp_path, monkeypatch):
    plan_id, plan_dir = _build_plan(
        tmp_path,
        monkeypatch,
        'cov-artifact',
        declared=['src/a.py'],
        modified=['src/a.py'],
    )
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--plan-id',
        plan_id,
        '--mode',
        'live',
        '--phase',
        '5-execute',
        '--relation-depth-rung',
        'T2',
        '--declared-scope',
        'component',
    )
    assert result.success, result.stderr

    artifact = _read_artifact(plan_dir, '5-execute')
    for field in (
        'deterministic_item_coverage',
        'item_coverage_rung',
        'relation_depth_verdict',
        'achieved_thoroughness',
        'achieved_scope',
    ):
        assert field in artifact, f'artifact must carry {field!r}, got {list(artifact)}'
    assert artifact['achieved_scope'] == 'component'
    assert artifact['achieved_thoroughness'] == 'T2'


# =============================================================================
# (f) Empty declared footprint → trivially full coverage
# =============================================================================


def test_empty_declared_footprint_is_full_coverage(tmp_path, monkeypatch):
    plan_id, plan_dir = _build_plan(
        tmp_path,
        monkeypatch,
        'cov-empty',
        declared=[],
        modified=[],
    )
    result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live', '--phase', '5-execute')
    assert result.success, result.stderr
    data = result.toon()
    assert float(data['deterministic_item_coverage']) == 1.0
    assert data['item_coverage_rung'] == 'T2'
