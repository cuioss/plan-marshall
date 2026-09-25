#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the manage-execution-manifest pre-filters and finalize selection.

Covers:

- ``pre_push_quality_gate_inactive`` — re-pointed onto the centralized
  build-decision API (``extension_base.should_execute_build``). The pre-filter
  drops ``pre-push-quality-gate`` ONLY on the positive ``not_necessary`` verdict;
  ``build`` and ``unknown`` both KEEP it. The decision logic itself is
  exhaustively covered in ``manage-config/test_build_decision.py``; here we
  assert the consumer-site wiring (verdict → keep/drop).
- ``pre-submission-self-review``'s survival through compose. There is no
  footprint-gated pre-filter for this step: the vacuous
  ``pre_submission_self_review_inactive`` predicate (which structurally never
  fired) has been removed outright, so the step is subtracted only by
  ``commit_push_disabled`` when no push will occur.
- The six-row decision matrix's SUBTRACTION RECORDS: every narrowing row returns
  one ``{step, reason}`` record per candidate it removed, so a row can no longer
  narrow the candidate list silently.
- The absence of any bot-enforcement guard: ``automatic-review`` is governed
  purely by its configured candidacy / ``lane`` — compose never force-adds nor
  re-orders it.
- The task-queue-aware ``early_terminate`` predicate.
"""

import json
from argparse import Namespace
from pathlib import Path

import extension_base
import pytest

from conftest import PlanContext, load_script_module

# =============================================================================
# Module loading (the script filename has hyphens, so it is loaded by identity)
# =============================================================================


_mem = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    'manage-execution-manifest.py',
    module_name='_mem_script_decision_rules',
)
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS
_decide = _mem._decide

# Silence the best-effort decision-log subprocess in tests.
#
# Each assignment below MUST name an emitter that still exists. ``setattr`` on a
# module succeeds for a name that was never defined, so a stale entry here does
# not fail loudly — it silently resurrects a dead attribute and leaves a live
# reference to a removed function in the tree. ``TestNoRemovedSelfReviewSymbols``
# asserts the absence explicitly rather than relying on these patches to fail.
_mem._log_decision = lambda *a, **kw: None
_mem._log_commit_push_omitted = lambda *a, **kw: None
_mem._log_pre_push_quality_gate_omitted = lambda *a, **kw: None
_mem._log_pre_push_quality_gate_kept_unknown = lambda *a, **kw: None
_mem._emit_decision_log = lambda *a, **kw: None

# =============================================================================
# Helpers
# =============================================================================


def _phase_6_with_self_review() -> str:
    """Return the comma-separated default phase-6-finalize steps with pre-submission-self-review added."""
    steps = list(DEFAULT_PHASE_6_STEPS) + ['pre-submission-self-review']
    return ','.join(steps)


def _compose_ns(
    plan_id: str = 'test-plan',
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'quality-gate,module-tests',
    phase_6_steps: str | None = None,
    commit_and_push: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps,
        phase_6_steps=phase_6_steps if phase_6_steps is not None else _phase_6_with_self_review(),
        commit_and_push=commit_and_push,
    )


def _seed_marshal(ci_provider: str | None = 'github') -> Path:
    """Write a minimal marshal.json at PLAN_BASE_DIR/marshal.json for the test.

    Pre-push-quality-gate activation derives from ``build.map``
    globs (D7/D8), so the seed carries a build_map entry whose ``**/*.py`` glob
    keeps the gate active against a matching footprint.
    """
    from file_ops import get_marshal_path

    marshal: dict = {
        'plan': {'phase-6-finalize': {}},
        'build': {
            'map': {
                'python': [
                    {'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'},
                ],
            },
        },
    }
    if ci_provider:
        marshal['providers'] = [{'skill_name': f'plan-marshall:workflow-integration-{ci_provider}', 'category': 'ci'}]
    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2))
    return marshal_path


def _stub_footprint(footprint: list[str] | None) -> None:
    """Stub ``_resolve_footprint`` so the activation pre-filters see the given state.

    The composer derives the live plan footprint on demand via
    ``compute_plan_branch_diff`` rather than reading a seeded
    ``references.modified_files`` ledger. Tests inject the resolver's THREE-state
    return: ``None`` (unresolvable — no evidence), ``[]`` (resolvable and
    genuinely empty), or a non-empty path list. The module-scoped autouse
    ``_restore_footprint_resolver`` fixture restores the original after each test.
    """
    _mem._resolve_footprint = lambda plan_id: None if footprint is None else list(footprint)


# =============================================================================
# Test: pre-submission-self-review survival (the removed vacuous pre-filter)
# =============================================================================


@pytest.fixture(autouse=True)
def _restore_footprint_resolver():
    """Restore ``_resolve_footprint`` after any test that stubbed it.

    ``_stub_footprint`` replaces the module-level resolver in-place; this
    module-scoped autouse fixture snapshots and restores it so a stub installed
    by one test never leaks into the next.
    """
    original = _mem._resolve_footprint
    yield
    _mem._resolve_footprint = original


# =============================================================================
# Helpers — read manifest after a successful compose
# =============================================================================


def result_phase_6_steps(result: dict) -> list[str]:
    """Read the persisted manifest after a successful compose and return phase_6.steps."""
    plan_id = result['plan_id']
    manifest = read_manifest(plan_id)
    assert manifest is not None
    return list(manifest.get('phase_6', {}).get('steps', []))


# =============================================================================
# Test: task-queue-aware early_terminate predicate
# =============================================================================


def _seed_task_file(plan_id: str, task_number: int, status: str) -> None:
    """Write a minimal TASK-{NNN}.json with the given status under the plan's tasks/ dir.

    Used to exercise the composer's task-queue read: Rule 1's
    ``early_terminate`` predicate now ANDs the existing
    ``affected_files_count==0`` condition with "no pending or in-progress task
    on disk". A test that seeds at least one pending task forces the
    short-circuit to fall through to Rule 7 (default).
    """
    from file_ops import get_plan_dir

    tasks_dir = get_plan_dir(plan_id) / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'number': task_number,
        'title': f'stub task {task_number}',
        'status': status,
        'steps': [],
    }
    (tasks_dir / f'TASK-{task_number:03d}.json').write_text(json.dumps(payload, indent=2))


# =============================================================================
# Test: security_class_inactive pre-filter (direct helper unit coverage)
#
# ``_apply_security_class_inactive`` is NOT the peer of
# ``_apply_simplify_inactive`` — it shares no helper and no gate. It drops a
# security-class step (the caller-derived population) from the phase-6 candidate
# list ONLY when ``affected_files_count == 0`` AND ``live_footprint_count == 0``.
# There is no ``change_type`` leg, so the gate fails toward INCLUSION: an unknown
# or misleading change shape keeps the security sweep. These tests exercise the
# helper directly (no compose round-trip) so the gate's truth table, the
# population contract, and the no-op-when-absent contract are pinned at the unit
# boundary. See standards/decision-rules.md § Pre-Filter: security_class_inactive.
# =============================================================================


_apply_security_class_inactive = _mem._apply_security_class_inactive

_SECURITY_CLASS = frozenset({'finalize-step-security-audit'})


# =============================================================================
# Test: unresolved_ask_provider_drop pre-filter (D6, direct helper coverage)
#
# ``_apply_unresolved_ask_provider_drop`` drops an UNRESOLVED ``lane:ask`` infra
# element (automatic-review / sonar-roundtrip) from the phase-6 candidate list
# when its provider is absent. The seed lane for both elements is ``ask``; a
# steward answer overwrites the override to off/standard/full, so an effective tier
# still equal to ``ask`` at compose is the unresolved case. These tests exercise
# the pure helper directly (no compose round-trip) so the full truth table and
# the no-op contracts are pinned at the unit boundary. See
# standards/decision-rules.md § Pre-Filter: unresolved_ask_provider_drop.
# =============================================================================


_apply_unresolved_ask_provider_drop = _mem._apply_unresolved_ask_provider_drop
_read_sonar_provider = _mem._read_sonar_provider


def _override_map(ar_lane: str | None = None, sr_lane: str | None = None) -> dict[str, dict]:
    """Build a marshal-style phase-6 step map with per-element lane overrides.

    Keys mirror the seeded marshal shape: ``plan-marshall:automatic-review`` and
    ``default:sonar-roundtrip`` (the D1 seed keys). Only elements with a non-None
    lane are included.
    """
    m: dict[str, dict] = {}
    if ar_lane is not None:
        m['plan-marshall:automatic-review'] = {'lane': ar_lane}
    if sr_lane is not None:
        m['default:sonar-roundtrip'] = {'lane': sr_lane}
    return m


# =============================================================================
# Test: scope_gated_finalize declared-lane immunity (direct helper coverage)
#
# The implicit scope gate must never silently override an explicit per-element
# ``lane`` declaration. The rule is load-bearing because the pre-filter runs at
# the candidate-narrowing stage — before ceremony selection and before lane
# resolution — and the ceremony ``always`` re-add path covers only the four
# ceremony gates. For any other step (canonically
# ``plan-marshall:plan-retrospective``) a drop here makes the declared lane
# structurally UNREACHABLE, not merely outvoted. See standards/decision-rules.md
# § Pre-Filter: scope_gated_finalize.
# =============================================================================


_apply_scope_gated_finalize = _mem._apply_scope_gated_finalize
_has_declared_lane_override = _mem._has_declared_lane_override

_RETROSPECTIVE = 'plan-marshall:plan-retrospective'


def _lane_map(step_id: str, lane: str) -> dict[str, dict]:
    """Build a marshal-style phase-6 step map declaring one element's lane."""
    return {step_id: {'lane': lane}}
