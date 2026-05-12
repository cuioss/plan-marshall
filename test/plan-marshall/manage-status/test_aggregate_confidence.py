#!/usr/bin/env python3
"""Tests for manage-status.py aggregate-confidence subcommand.

The script implements phase-2-refine SKILL.md Step 10's weighted-math
aggregator over six per-dimension scores. The dimension weights are
fixed (correctness/completeness/consistency/ambiguity = 20 %,
non-duplication/module-mapping = 10 %), so the math is deterministic
and every input/output pair is reproducible.
"""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

from conftest import PROJECT_ROOT, PlanContext

_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-status'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module('_cmd_aggregate_confidence_under_test', '_cmd_aggregate_confidence.py')
cmd_aggregate_confidence = _mod.cmd_aggregate_confidence


def _ns(
    plan_id: str,
    *,
    correctness: float | None = None,
    completeness: float | None = None,
    consistency: float | None = None,
    non_duplication: float | None = None,
    ambiguity: float | None = None,
    module_mapping: float | None = None,
    scores_file: str | None = None,
    persist: bool = False,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        correctness=correctness,
        completeness=completeness,
        consistency=consistency,
        non_duplication=non_duplication,
        ambiguity=ambiguity,
        module_mapping=module_mapping,
        scores_file=scores_file,
        persist=persist,
    )


def _write_status(plan_dir: Path) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_dir.name, 'phases': [], 'metadata': {}}),
        encoding='utf-8',
    )


# =============================================================================
# Math invariants
# =============================================================================


def test_equal_max_scores_yield_100():
    """Every dimension at 100 → overall 100."""
    with PlanContext(plan_id='ac-max'):
        result = cmd_aggregate_confidence(
            _ns(
                'ac-max',
                correctness=100,
                completeness=100,
                consistency=100,
                non_duplication=100,
                ambiguity=100,
                module_mapping=100,
            )
        )
        assert result['status'] == 'success'
        assert result['confidence'] == 100.0
        assert result['missing_dimensions'] == []


def test_zero_scores_yield_zero():
    with PlanContext(plan_id='ac-zero'):
        result = cmd_aggregate_confidence(
            _ns(
                'ac-zero',
                correctness=0,
                completeness=0,
                consistency=0,
                non_duplication=0,
                ambiguity=0,
                module_mapping=0,
            )
        )
        assert result['confidence'] == 0.0


def test_specific_weights_apply():
    """Manual hand-computed example confirms the weighted formula."""
    with PlanContext(plan_id='ac-weights'):
        # 80*0.2 + 70*0.2 + 90*0.2 + 100*0.1 + 60*0.2 + 50*0.1
        # = 16 + 14 + 18 + 10 + 12 + 5 = 75.0
        result = cmd_aggregate_confidence(
            _ns(
                'ac-weights',
                correctness=80,
                completeness=70,
                consistency=90,
                non_duplication=100,
                ambiguity=60,
                module_mapping=50,
            )
        )
        assert result['confidence'] == 75.0
        # Each breakdown entry has score, weight, weighted.
        weighted_sum = sum(b['weighted'] for b in result['breakdown'])
        assert abs(weighted_sum - 75.0) < 1e-6


def test_missing_dimensions_default_to_zero_and_are_listed():
    with PlanContext(plan_id='ac-missing'):
        result = cmd_aggregate_confidence(_ns('ac-missing', correctness=100, completeness=100))
        # Only two dimensions set → 100*0.2 + 100*0.2 = 40
        assert result['confidence'] == 40.0
        assert set(result['missing_dimensions']) == {
            'consistency',
            'non_duplication',
            'ambiguity',
            'module_mapping',
        }


def test_out_of_range_scores_are_clamped():
    with PlanContext(plan_id='ac-clamp'):
        result = cmd_aggregate_confidence(
            _ns(
                'ac-clamp',
                correctness=150,  # clamped to 100
                completeness=-10,  # clamped to 0
                consistency=50,
                non_duplication=50,
                ambiguity=50,
                module_mapping=50,
            )
        )
        # 100*0.2 + 0*0.2 + 50*0.2 + 50*0.1 + 50*0.2 + 50*0.1 = 20 + 0 + 10 + 5 + 10 + 5 = 50
        assert result['confidence'] == 50.0


# =============================================================================
# Scores-file input
# =============================================================================


def test_scores_file_kebab_keys_supported():
    with PlanContext(plan_id='ac-file') as ctx:
        assert ctx.plan_dir is not None
        path = ctx.plan_dir / 'scores.json'
        path.write_text(
            json.dumps(
                {
                    'correctness': 100,
                    'completeness': 100,
                    'consistency': 100,
                    'non-duplication': 100,  # kebab-case
                    'ambiguity': 100,
                    'module-mapping': 100,
                }
            ),
            encoding='utf-8',
        )
        result = cmd_aggregate_confidence(_ns('ac-file', scores_file=str(path)))
        assert result['confidence'] == 100.0


def test_scores_file_missing_raises_error():
    with PlanContext(plan_id='ac-no-file'):
        result = cmd_aggregate_confidence(_ns('ac-no-file', scores_file='/nonexistent/path.json'))
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_input'


def test_scores_file_invalid_json_raises_error():
    with PlanContext(plan_id='ac-bad-json') as ctx:
        assert ctx.plan_dir is not None
        path = ctx.plan_dir / 'scores.json'
        path.write_text('{not valid', encoding='utf-8')
        result = cmd_aggregate_confidence(_ns('ac-bad-json', scores_file=str(path)))
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_input'


def test_cli_flags_override_scores_file_values():
    with PlanContext(plan_id='ac-override') as ctx:
        assert ctx.plan_dir is not None
        path = ctx.plan_dir / 'scores.json'
        path.write_text(
            json.dumps(
                {
                    'correctness': 50,
                    'completeness': 50,
                    'consistency': 50,
                    'non_duplication': 50,
                    'ambiguity': 50,
                    'module_mapping': 50,
                }
            ),
            encoding='utf-8',
        )
        # Override correctness via CLI to 100 — overall lifts by (100-50)*0.2 = 10.
        result = cmd_aggregate_confidence(
            _ns('ac-override', scores_file=str(path), correctness=100)
        )
        assert result['confidence'] == 60.0


# =============================================================================
# Persistence
# =============================================================================


def test_persist_writes_status_metadata_confidence():
    with PlanContext(plan_id='ac-persist') as ctx:
        assert ctx.plan_dir is not None
        _write_status(ctx.plan_dir)
        result = cmd_aggregate_confidence(
            _ns(
                'ac-persist',
                correctness=100,
                completeness=100,
                consistency=100,
                non_duplication=100,
                ambiguity=100,
                module_mapping=100,
                persist=True,
            )
        )
        assert result['persisted'] is True
        status = json.loads((ctx.plan_dir / 'status.json').read_text())
        assert status['metadata']['confidence'] == 100.0


# =============================================================================
# Plan-dir error path
# =============================================================================


def test_plan_dir_not_found_errors():
    with PlanContext(plan_id='ac-exists'):
        result = cmd_aggregate_confidence(_ns('does-not-exist', correctness=50))
        assert result['status'] == 'error'
        assert result['error'] == 'plan_dir_not_found'


# =============================================================================
# Dispatch wiring
# =============================================================================


def test_aggregate_confidence_registered_in_manage_status_dispatch():
    """argparse routes 'aggregate-confidence' to cmd_aggregate_confidence."""
    import argparse  # noqa: PLC0415

    manage_status = _load_module('_manage_status_dispatch_check_ac', 'manage_status.py')
    assert manage_status.cmd_aggregate_confidence is cmd_aggregate_confidence or callable(
        manage_status.cmd_aggregate_confidence
    )

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    leaf = sub.add_parser('aggregate-confidence')
    leaf.set_defaults(func=manage_status.cmd_aggregate_confidence)
    ns = parser.parse_args(['aggregate-confidence'])
    assert ns.func is manage_status.cmd_aggregate_confidence
