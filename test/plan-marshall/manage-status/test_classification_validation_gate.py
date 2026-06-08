#!/usr/bin/env python3
"""Tests for the deterministic classification-validation gate.

The gate cross-checks a plan's ``change_type`` and ``scope_estimate`` against
cheap request signals and emits a phase-1-init Q-Gate finding (recorded against
``2-refine``) on a mismatch. It is **flag-not-block** — it never gates routing.

Two mismatch classes, both chosen to raise zero false positives:

1. ``feature_as_bug_fix`` — ``change_type == bug_fix`` while the deterministic
   change-type heuristic resolves a non-ambiguous ``feature`` winner.
2. ``non_empty_affected_files_with_null_scope`` — ``affected_files`` non-empty
   while ``scope_estimate`` is null / empty / ``none``.

Coverage:
- No-signal / valid input yields no finding (no false positives).
- Each mismatch class fires its finding in isolation.
- Both mismatches together produce two findings.
- The gate never blocks (``blocked`` is always ``False``; ``status`` success).
- Re-running the gate dedups (no duplicate findings).
- The gate is folded into ``planning-lane route`` as a pre-route pass and never
  changes the resolved lane.
"""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

from conftest import PROJECT_ROOT

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


_gate = _load_module('_cmd_classification_validate_under_test', '_cmd_classification_validate.py')
run_classification_validation = _gate.run_classification_validation
cmd_classification_validate = _gate.cmd_classification_validate

_lane = _load_module('_cmd_planning_lane_for_classification_test', '_cmd_planning_lane.py')
cmd_planning_lane_route = _lane.cmd_planning_lane_route


# =============================================================================
# Fixture authoring helpers
# =============================================================================

# A request body that clearly reads as a feature ("add / create / implement a
# new X"), so the change-type heuristic resolves a non-ambiguous feature winner.
_FEATURE_BODY = 'Add a new export command that creates and implements a fresh report generator.'

# A request body that clearly reads as a bug fix, so the heuristic does NOT
# resolve feature (no feature-as-bug_fix false positive).
_BUGFIX_BODY = 'The parser crashes on empty input — this is a regression; fix the broken exception path.'


def _write_request(plan_dir: Path, body: str) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    content = (
        '# Request\n\n'
        '## Original Input\n\n'
        '(unused)\n\n'
        '## Clarified Request\n\n'
        f'{body}\n'
    )
    (plan_dir / 'request.md').write_text(content, encoding='utf-8')


def _write_status(plan_dir: Path, metadata: dict | None = None) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_dir.name, 'phases': [], 'metadata': metadata or {}}),
        encoding='utf-8',
    )


def _write_references(
    plan_dir: Path,
    *,
    scope_estimate: str | None,
    affected_files: list[str] | None = None,
) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    refs: dict = {'base_branch': 'main'}
    if scope_estimate is not None:
        refs['scope_estimate'] = scope_estimate
    if affected_files is not None:
        refs['affected_files'] = affected_files
    (plan_dir / 'references.json').write_text(json.dumps(refs), encoding='utf-8')


def _write_marshal(fixture_dir: Path) -> None:
    config = {
        'plan': {'phase-2-refine': {'compatibility': 'deprecation'}},
        'ceremony_policy': {'planning': {'deep_lane': 'auto'}},
    }
    (fixture_dir / 'marshal.json').write_text(json.dumps(config, indent=2), encoding='utf-8')


def _ns(plan_id: str) -> Namespace:
    return Namespace(plan_id=plan_id)


def _ns_route(plan_id: str):
    return Namespace(plan_id=plan_id, lane_override=None, persist=False)


# =============================================================================
# No false positives — valid input
# =============================================================================


def test_no_mismatch_on_valid_bug_fix(plan_context):
    """A bug_fix stamp over a bug-shaped request with a scope estimate yields no finding."""
    # Arrange — bug_fix, bug-shaped narrative, scope set, no affected_files gap.
    plan_dir = plan_context.plan_dir_for('cv-valid-bugfix')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='surgical')

    # Act
    result = run_classification_validation('cv-valid-bugfix')

    # Assert
    assert result['status'] == 'success'
    assert result['mismatch_count'] == 0
    assert result['findings_emitted'] == 0
    assert result['blocked'] is False


def test_no_mismatch_when_scope_set_with_affected_files(plan_context):
    """A non-empty affected_files WITH a scope estimate does not trip mismatch class 2."""
    # Arrange
    plan_dir = plan_context.plan_dir_for('cv-valid-scope')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='single_module', affected_files=['a/b.py'])

    # Act
    result = run_classification_validation('cv-valid-scope')

    # Assert
    assert result['mismatch_count'] == 0
    assert result['findings_emitted'] == 0


def test_no_mismatch_when_no_metadata(plan_context):
    """A plan with no change_type and no affected_files produces no finding."""
    # Arrange — minimal plan, nothing to cross-check.
    plan_dir = plan_context.plan_dir_for('cv-empty')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={})
    _write_references(plan_dir, scope_estimate=None)

    # Act
    result = run_classification_validation('cv-empty')

    # Assert
    assert result['mismatch_count'] == 0
    assert result['blocked'] is False


# =============================================================================
# Mismatch class 1 — feature-as-bug_fix
# =============================================================================


def test_feature_as_bug_fix_fires(plan_context):
    """change_type=bug_fix over a feature-shaped narrative flags one finding."""
    # Arrange
    plan_dir = plan_context.plan_dir_for('cv-feat-bug')
    _write_request(plan_dir, _FEATURE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='surgical')

    # Act
    result = run_classification_validation('cv-feat-bug')

    # Assert
    assert result['mismatch_count'] == 1
    assert result['mismatches'][0]['mismatch'] == 'feature_as_bug_fix'
    assert result['findings_emitted'] == 1
    assert result['blocked'] is False


def test_feature_as_bug_fix_does_not_fire_for_feature_change_type(plan_context):
    """A feature-shaped narrative correctly stamped change_type=feature is not flagged."""
    # Arrange
    plan_dir = plan_context.plan_dir_for('cv-feat-ok')
    _write_request(plan_dir, _FEATURE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'feature'})
    _write_references(plan_dir, scope_estimate='multi_module')

    # Act
    result = run_classification_validation('cv-feat-ok')

    # Assert — no feature-as-bug_fix flag (change_type already matches).
    classes = {m['mismatch'] for m in result['mismatches']}
    assert 'feature_as_bug_fix' not in classes


# =============================================================================
# Mismatch class 2 — affected_files without scope_estimate
# =============================================================================


def test_affected_files_without_scope_fires(plan_context):
    """Non-empty affected_files with a null scope_estimate flags one finding."""
    # Arrange — affected_files set, scope_estimate absent.
    plan_dir = plan_context.plan_dir_for('cv-files-noscope')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate=None, affected_files=['x/y.py', 'x/z.py'])

    # Act
    result = run_classification_validation('cv-files-noscope')

    # Assert
    classes = {m['mismatch'] for m in result['mismatches']}
    assert classes == {'non_empty_affected_files_with_null_scope'}
    assert result['findings_emitted'] == 1
    assert result['blocked'] is False


def test_affected_files_with_none_scope_string_fires(plan_context):
    """The literal scope_estimate 'none' counts as null for mismatch class 2."""
    # Arrange
    plan_dir = plan_context.plan_dir_for('cv-files-nonescope')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='none', affected_files=['x/y.py'])

    # Act
    result = run_classification_validation('cv-files-nonescope')

    # Assert
    classes = {m['mismatch'] for m in result['mismatches']}
    assert 'non_empty_affected_files_with_null_scope' in classes


# =============================================================================
# Both mismatches together
# =============================================================================


def test_both_mismatches_fire_two_findings(plan_context):
    """A plan tripping both classes records two distinct findings without blocking."""
    # Arrange — bug_fix over a feature narrative AND affected_files without scope.
    plan_dir = plan_context.plan_dir_for('cv-both')
    _write_request(plan_dir, _FEATURE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate=None, affected_files=['a/b.py'])

    # Act
    result = run_classification_validation('cv-both')

    # Assert
    classes = {m['mismatch'] for m in result['mismatches']}
    assert classes == {'feature_as_bug_fix', 'non_empty_affected_files_with_null_scope'}
    assert result['mismatch_count'] == 2
    assert result['findings_emitted'] == 2
    assert result['blocked'] is False


# =============================================================================
# Dedup on re-run
# =============================================================================


def test_rerun_dedups_findings(plan_context):
    """Re-running the gate does not record duplicate findings (title dedup)."""
    # Arrange
    plan_dir = plan_context.plan_dir_for('cv-dedup')
    _write_request(plan_dir, _FEATURE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='surgical')

    # Act — run twice.
    first = run_classification_validation('cv-dedup')
    second = run_classification_validation('cv-dedup')

    # Assert — first records the finding; the second dedups (0 new emitted).
    assert first['findings_emitted'] == 1
    assert second['mismatch_count'] == 1
    assert second['findings_emitted'] == 0
    assert second['mismatches'][0]['finding_status'] == 'deduplicated'


# =============================================================================
# Subcommand wrapper + missing-plan handling
# =============================================================================


def test_cmd_returns_error_for_missing_plan(plan_context):
    """The subcommand returns a structured error when the plan dir is absent."""
    # Act — no plan dir created.
    result = cmd_classification_validate(_ns('cv-nonexistent'))

    # Assert
    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


# =============================================================================
# Folded into planning-lane route — pre-route pass, never blocks the lane
# =============================================================================


def test_route_surfaces_classification_without_blocking(plan_context):
    """planning-lane route runs the gate as a pre-route pass and still resolves a lane."""
    # Arrange — a plan that trips a mismatch (affected_files without scope).
    plan_dir = plan_context.plan_dir_for('cv-route')
    _write_request(plan_dir, _BUGFIX_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate=None, affected_files=['a/b.py'])
    _write_marshal(plan_context.fixture_dir)

    # Act
    result = cmd_planning_lane_route(_ns_route('cv-route'))

    # Assert — routing succeeded and resolved a lane; the gate result rides along.
    assert result['status'] == 'success'
    assert result['planning_lane'] in ('light', 'deep')
    cv = result['classification_validation']
    assert cv['mismatch_count'] >= 1
    assert 'non_empty_affected_files_with_null_scope' in {m['mismatch'] for m in cv['mismatches']}
