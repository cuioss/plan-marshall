#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``compose`` subcommand of manage-execution-manifest.py.

Split from test_manage_execution_manifest.py — tier 2 direct-import tests for
the compose path (decision matrix, boundary normalization, commit-and-push,
pre-push-quality-gate, frontmatter-order sort, and marshal.json
source-of-truth) plus the relevant CLI plumbing tests.
"""

import contextlib
import importlib.util
import json
from argparse import Namespace
from collections.abc import Callable
from pathlib import Path

import pytest

from conftest import get_script_path, run_script

# Script path for subprocess (CLI plumbing) tests.
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py')

# Tier 2 direct imports via importlib (scripts loaded via PYTHONPATH at runtime).
_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None, f'Failed to load module spec for {filename}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


# Lane-block fixture, loaded via importlib per the _fixtures.py convention (a
# sibling conftest.py is banned). The basename is bundle-unique.
_FIXTURES_PATH = Path(__file__).parent / '_execution_manifest_fixtures.py'
_fixtures_spec = importlib.util.spec_from_file_location(
    '_execution_manifest_fixtures_compose_tests', _FIXTURES_PATH
)
assert _fixtures_spec is not None and _fixtures_spec.loader is not None
_fixtures_mod = importlib.util.module_from_spec(_fixtures_spec)
_fixtures_spec.loader.exec_module(_fixtures_mod)
fake_lane_blocks = _fixtures_mod.fake_lane_blocks


_mem = _load_module('_mem_script', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest
get_manifest_path = _mem.get_manifest_path
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS
DEFAULT_ENVELOPE_COUNT = _mem.DEFAULT_ENVELOPE_COUNT
_role_of = _mem._role_of

# Execution-profile lane resolver surface (deliverable 5).
cmd_lanes_preview = _mem.cmd_lanes_preview
_apply_lane_resolution = _mem._apply_lane_resolution
_lane_keep_decision = _mem._lane_keep_decision
_effective_lane_tier = _mem._effective_lane_tier
_read_execution_profile = _mem._read_execution_profile
_parse_cost_magnitude = _mem._parse_cost_magnitude
_sum_lane_cost = _mem._sum_lane_cost

# Quiet down the best-effort decision-log subprocess so tests don't depend on a
# running executor. The handler is wrapped in try/except so failures are
# already silent, but we replace it with a no-op for clarity and speed.
_mem._log_decision = lambda *a, **kw: None

@contextlib.contextmanager
def _capture_decision_log():
    """Capture ``_emit_decision_log`` calls; yield the (plan_id, message) list."""
    captured: list[tuple[str, str]] = []
    original = _mem._emit_decision_log
    _mem._emit_decision_log = lambda pid, msg: captured.append((pid, msg))
    try:
        yield captured
    finally:
        _mem._emit_decision_log = original


# =============================================================================
# Namespace Helpers
# =============================================================================


def _compose_ns(
    plan_id: str = 'test-plan',
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'quality-gate,module-tests',
    phase_6_steps: str | None = ','.join(DEFAULT_PHASE_6_STEPS),
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
        phase_6_steps=phase_6_steps,
        commit_and_push=commit_and_push,
    )


# =============================================================================
# Decision Matrix Tests — table-driven cases (one per row of the matrix +
# the requested 8th case for early_terminate analysis-with-empty-files)
# =============================================================================


def test_default_code_shaped_feature_runs_full_phases(plan_context):
    """Row 7 — default: feature plan gets the full Phase 5 and Phase 6 sets."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-default',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=12,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['rule_fired'] == 'default'
    assert result['phase_5']['early_terminate'] is False
    assert result['phase_5']['verification_steps_count'] == 2  # quality-gate + module-tests
    assert result['phase_6']['steps_count'] == len(DEFAULT_PHASE_6_STEPS)


def test_early_terminate_analysis_with_empty_files(plan_context):
    """Row 1 — analysis with affected_files_count=0 → early_terminate=true."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-analysis',
            change_type='analysis',
            scope_estimate='none',
            affected_files_count=0,
        )
    )
    assert result is not None and result['rule_fired'] == 'early_terminate_analysis'
    assert result['phase_5']['early_terminate'] is True
    assert result['phase_5']['verification_steps_count'] == 0
    # Phase 6 keeps the records-and-archive trio: lessons-capture, adr-propose
    # (an analysis plan that made a decision can still propose an ADR), and
    # archive-plan.
    assert result['phase_6']['steps_count'] == 3


def test_early_terminate_analysis_falls_through_when_task_queue_pending(plan_context):
    """Row 1 task-queue guard — analysis + 0 files + pending task → Rule 7 default.

    End-to-end exercise of the task-queue-aware predicate (lesson
    ``2026-05-24-17-001``): a pending TASK-001 on disk forces Rule 1 to fall
    through to Rule 7 so phase-5 iterates the queue normally. The fixture
    seeds a stub task file in ``{plan_dir}/tasks/TASK-001.json``.
    """
    plan_id = 'matrix-analysis-pending-task'
    tasks_dir = plan_context.plan_dir_for(plan_id) / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / 'TASK-001.json').write_text(
        json.dumps({'number': 1, 'status': 'pending', 'steps': []}, indent=2)
    )
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='analysis',
            scope_estimate='none',
            affected_files_count=0,
        )
    )
    assert result is not None and result['rule_fired'] == 'default'
    assert result['phase_5']['early_terminate'] is False


def test_recipe_path_retains_review_gates_drops_only_legacy_ci_wait(plan_context):
    """Row 2 — recipe_key present → ONLY defensively drop legacy 'ci-wait'.

    Review gates (automatic-review, sonar-roundtrip) are NEVER silently
    suppressed by the planner — the recipe label is exactly the case
    where the bots' job is to catch what humans miss. CI completion is
    now a dispatcher-resolved precondition declared via requires:
    [ci-complete] on consumer step frontmatters, not a sibling step.
    """
    # Inject the legacy ci-wait into the candidate list to assert the
    # defensive narrowing still drops it. The default candidate set no
    # longer contains it.
    candidates_with_legacy = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-recipe',
            change_type='tech_debt',
            scope_estimate='surgical',
            recipe_key='lesson_cleanup',
            affected_files_count=2,
            phase_6_steps=','.join(candidates_with_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'recipe'
    manifest = read_manifest('matrix-recipe')
    assert manifest is not None
    # Review gates RETAINED — never silently suppressed.
    assert 'automatic-review' in manifest['phase_6']['steps']
    assert 'sonar-roundtrip' in manifest['phase_6']['steps']
    # Legacy ci-wait still defensively narrowed out.
    assert 'ci-wait' not in manifest['phase_6']['steps']
    assert 'push' in manifest['phase_6']['steps']


def test_docs_shaped_candidates_keep_phase_5_and_retain_review_gates(plan_context):
    """A docs-shaped candidate set no longer empties Phase 5 by inference.

    The retired ``docs_only`` row read "no module-tests / coverage role among the
    candidates" as proof the plan was docs-only and cleared Phase 5 on that
    inference. Build necessity is settled by the footprint authority, never by the
    shape of a candidate list, so this input now falls through to the scope row
    and KEEPS its ``quality-gate`` candidate.

    Review gates (automatic-review, sonar-roundtrip) are RETAINED either way, and
    only the legacy 'ci-wait' step ID is defensively narrowed out (against project
    marshal.json files that still list it).
    """
    # Inject legacy ci-wait into candidates to assert defensive narrowing.
    candidates_with_legacy = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-docs',
            change_type='tech_debt',
            scope_estimate='surgical',
            affected_files_count=3,
            # docs-shaped candidate set: only quality-gate, no module-tests/coverage.
            phase_5_steps='verify:quality-gate',
            phase_6_steps=','.join(candidates_with_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
    assert result['phase_5']['verification_steps_count'] == 1
    manifest = read_manifest('matrix-docs')
    assert manifest is not None
    # Review gates RETAINED.
    assert 'automatic-review' in manifest['phase_6']['steps']
    assert 'sonar-roundtrip' in manifest['phase_6']['steps']
    # Legacy ci-wait still defensively narrowed out.
    assert 'ci-wait' not in manifest['phase_6']['steps']


def test_tests_only_runs_module_tests_and_full_phase_6(plan_context):
    """Row 4 — verification change_type with affected files → role:module-tests + full Phase 6.

    Row 4 intersects ``phase_5_candidates`` by ``role: module-tests`` (see
    decision-rules.md § Role-Field Intersection). ``verify:quality-gate`` (role
    ``quality-gate``) and ``verify:coverage`` (role ``coverage``) are dropped;
    ``verify:module-tests`` (role ``module-tests``) is kept.
    """
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-tests',
            change_type='verification',
            scope_estimate='single_module',
            affected_files_count=4,
            phase_5_steps='verify:quality-gate,verify:module-tests,verify:coverage',
        )
    )
    assert result is not None and result['rule_fired'] == 'tests_only'
    manifest = read_manifest('matrix-tests')
    assert manifest is not None
    assert manifest['phase_5']['verification_steps'] == ['verify:module-tests']
    # finalize-step-simplify AND finalize-step-security-audit are both dropped by
    # their respective pre-filters (simplify_inactive / security_audit_inactive):
    # change_type=verification is not in the shared code-bearing change-type set.
    dropped = {'finalize-step-simplify', 'finalize-step-security-audit'}
    expected_phase_6 = [s for s in DEFAULT_PHASE_6_STEPS if s not in dropped]
    assert manifest['phase_6']['steps'] == expected_phase_6


def test_surgical_bug_fix_retains_review_gates(plan_context):
    """Row 5 — surgical+bug_fix: review gates RETAINED, legacy ci-wait dropped defensively.

    Review gates are NEVER silently suppressed — surgical bug_fix is
    exactly the case where the bots' job is to catch what humans miss
    on a one-line fix. Only the legacy 'ci-wait' step ID is defensively
    narrowed out.
    """
    candidates_with_legacy = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-bug',
            change_type='bug_fix',
            scope_estimate='surgical',
            affected_files_count=1,
            phase_6_steps=','.join(candidates_with_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_bug_fix'
    manifest = read_manifest('matrix-bug')
    assert manifest is not None
    # Review gates RETAINED.
    for retained in ('automatic-review', 'sonar-roundtrip'):
        assert retained in manifest['phase_6']['steps']
    # Legacy ci-wait dropped defensively.
    assert 'ci-wait' not in manifest['phase_6']['steps']
    assert 'lessons-capture' in manifest['phase_6']['steps']


def test_surgical_tech_debt_retains_review_gates(plan_context):
    """Row 5 — surgical+tech_debt: review gates RETAINED, legacy ci-wait dropped defensively.

    Mirror of surgical_bug_fix — same retention contract, distinct rule
    key. Review gates are never silently suppressed.
    """
    candidates_with_legacy = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-tech',
            change_type='tech_debt',
            scope_estimate='surgical',
            affected_files_count=2,
            # Need code-shaped candidate set (role: module-tests present) so
            # we don't fall into the docs_only row first. verify:module-tests
            # derives role: module-tests from its canonical segment.
            phase_5_steps='verify:quality-gate,verify:module-tests',
            phase_6_steps=','.join(candidates_with_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
    manifest = read_manifest('matrix-tech')
    assert manifest is not None
    assert 'push' in manifest['phase_6']['steps']
    # Review gates RETAINED.
    for retained in ('automatic-review', 'sonar-roundtrip'):
        assert retained in manifest['phase_6']['steps']
    # Legacy ci-wait dropped defensively.
    assert 'ci-wait' not in manifest['phase_6']['steps']


# =============================================================================
# Boundary-Normalization Regression Tests
#
# `phase_6_candidates` may arrive prefixed (`default:foo` from marshal.json's
# step registry) or bare (`foo` from DEFAULT_PHASE_6_STEPS). Lesson
# ``2026-04-27-23-004`` closed the prefix-handling gap by normalizing both
# ``phase_5_candidates`` and ``phase_6_candidates`` once at the
# ``cmd_compose`` boundary — every leading ``default:`` is stripped a single
# time at intake, so the six-row matrix and the pre-filter helpers all see
# bare names. Manifest output and result fields are bare strings throughout.
#
# These tests feed prefixed candidates and assert the resulting manifest
# carries bare-name entries, with each cascade rule (Rule 1, 2, 4, 5, 6)
# dropping or including the right steps. They previously asserted that the
# prefix survived verbatim into the manifest output — that contract has been
# retired in favor of the boundary-normalization contract pinned by
# ``test_boundary_normalization_strips_prefix_for_all_downstream_consumers``.
# =============================================================================


_PREFIXED_PHASE_6 = (
    'default:pre-push-quality-gate',
    'default:push',
    'default:create-pr',
    'plan-marshall:automatic-review',
    'default:lessons-capture',
    'default:branch-cleanup',
    'default:archive-plan',
)


def test_rule_1_early_terminate_analysis_with_prefixed_candidates(plan_context):
    """Rule 1 (early_terminate_analysis) — prefixed candidates: include only lessons/archive (bare)."""
    result = cmd_compose(
        _compose_ns(
            plan_id='prefix-rule-1',
            change_type='analysis',
            scope_estimate='none',
            affected_files_count=0,
            phase_6_steps=','.join(_PREFIXED_PHASE_6),
        )
    )
    assert result is not None and result['rule_fired'] == 'early_terminate_analysis'
    manifest = read_manifest('prefix-rule-1')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    # Boundary normalization strips `default:` at intake — output is bare.
    assert set(steps) == {'lessons-capture', 'archive-plan'}
    # No `default:`-prefixed entries survive anywhere in the manifest.
    assert not any(s.startswith('default:') for s in steps)
    # Heavy steps that would have leaked through pre-fix are absent.
    for excluded in ('push', 'create-pr', 'automatic-review', 'pre-push-quality-gate', 'branch-cleanup'):
        assert excluded not in steps


def test_rule_2_recipe_with_prefixed_candidates(plan_context):
    """Rule 2 (recipe) — prefixed candidates: review gates RETAINED, legacy ci-wait dropped (bare output)."""
    prefixed_with_review_and_legacy = _PREFIXED_PHASE_6 + (
        'default:sonar-roundtrip',
        'default:ci-wait',
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='prefix-rule-2',
            change_type='tech_debt',
            scope_estimate='surgical',
            recipe_key='lesson_cleanup',
            affected_files_count=2,
            phase_6_steps=','.join(prefixed_with_review_and_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'recipe'
    manifest = read_manifest('prefix-rule-2')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    # No `default:` prefix in output — boundary-normalized at intake.
    assert not any(s.startswith('default:') for s in steps)
    # Review gates RETAINED — never silently suppressed.
    for retained in ('automatic-review', 'sonar-roundtrip'):
        assert retained in steps
    # Legacy ci-wait dropped defensively.
    assert 'ci-wait' not in steps
    # Non-heavy steps survive (bare).
    assert 'push' in steps
    assert 'create-pr' in steps
    assert 'lessons-capture' in steps


def test_surgical_tech_debt_with_prefixed_candidates(plan_context):
    """Scope row — prefixed candidates: review gates RETAINED, legacy ci-wait dropped (bare output)."""
    prefixed_with_review_and_legacy = _PREFIXED_PHASE_6 + (
        'default:sonar-roundtrip',
        'default:ci-wait',
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='prefix-rule-3',
            change_type='tech_debt',
            scope_estimate='surgical',
            affected_files_count=3,
            # docs-shaped candidate set: only quality-gate, no module-tests/coverage.
            phase_5_steps='quality-gate',
            phase_6_steps=','.join(prefixed_with_review_and_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
    manifest = read_manifest('prefix-rule-3')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    assert not any(s.startswith('default:') for s in steps)
    # Review gates RETAINED.
    for retained in ('sonar-roundtrip', 'automatic-review'):
        assert retained in steps
    # Legacy ci-wait dropped defensively.
    assert 'ci-wait' not in steps
    # Non-review steps survive (bare).
    assert 'push' in steps
    assert 'lessons-capture' in steps


def test_rule_5_surgical_bug_fix_with_prefixed_candidates(plan_context):
    """Rule 5 (surgical_bug_fix) — prefixed candidates: review gates RETAINED, legacy ci-wait dropped (bare output)."""
    prefixed_with_review_and_legacy = _PREFIXED_PHASE_6 + (
        'default:sonar-roundtrip',
        'default:ci-wait',
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='prefix-rule-5-bug',
            change_type='bug_fix',
            scope_estimate='surgical',
            affected_files_count=1,
            phase_6_steps=','.join(prefixed_with_review_and_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_bug_fix'
    manifest = read_manifest('prefix-rule-5-bug')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    assert not any(s.startswith('default:') for s in steps)
    # Review gates RETAINED.
    for retained in ('automatic-review', 'sonar-roundtrip'):
        assert retained in steps
    # Legacy ci-wait dropped defensively.
    assert 'ci-wait' not in steps
    assert 'lessons-capture' in steps
    assert 'push' in steps


def test_rule_5_surgical_tech_debt_with_prefixed_candidates(plan_context):
    """Rule 5 (surgical_tech_debt) — prefixed candidates: same retention as bug_fix (bare output)."""
    prefixed_with_review_and_legacy = _PREFIXED_PHASE_6 + (
        'default:sonar-roundtrip',
        'default:ci-wait',
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='prefix-rule-5-tech',
            change_type='tech_debt',
            scope_estimate='surgical',
            affected_files_count=2,
            # Code-shaped candidate set (role: module-tests present) so we
            # don't fall into docs_only first.
            phase_5_steps='verify:quality-gate,verify:module-tests',
            phase_6_steps=','.join(prefixed_with_review_and_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
    manifest = read_manifest('prefix-rule-5-tech')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    assert not any(s.startswith('default:') for s in steps)
    # Review gates RETAINED.
    for retained in ('automatic-review', 'sonar-roundtrip'):
        assert retained in steps
    # Legacy ci-wait dropped defensively.
    assert 'ci-wait' not in steps
    assert 'push' in steps


def test_rule_6_verification_no_files_with_prefixed_candidates(plan_context):
    """Rule 6 (verification_no_files) — prefixed candidates: include only lessons/archive (bare output)."""
    result = cmd_compose(
        _compose_ns(
            plan_id='prefix-rule-6',
            change_type='verification',
            scope_estimate='none',
            affected_files_count=0,
            phase_6_steps=','.join(_PREFIXED_PHASE_6),
        )
    )
    assert result is not None and result['rule_fired'] == 'verification_no_files'
    manifest = read_manifest('prefix-rule-6')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    # Boundary normalization strips `default:` at intake — output is bare.
    assert set(steps) == {'lessons-capture', 'archive-plan'}
    assert not any(s.startswith('default:') for s in steps)
    for excluded in ('push', 'create-pr', 'automatic-review', 'pre-push-quality-gate', 'branch-cleanup'):
        assert excluded not in steps


def test_prefix_normalization_no_op_for_bare_candidates(plan_context):
    """Sanity: boundary normalization is a no-op for bare candidates.

    The bare-name path (DEFAULT_PHASE_6_STEPS) must continue to work identically
    to the prefixed path. Rule 5 with bare candidates pins the bare-name shape
    end-to-end — boundary stripping at ``cmd_compose`` intake leaves bare names
    unchanged, so the cascade-rule layer sees and emits the same bare strings.

    Review gates are retained under Rule 5; only the legacy 'ci-wait' step ID
    is defensively narrowed out when present in the candidate list.
    """
    bare = (
        'push',
        'create-pr',
        'automatic-review',
        'sonar-roundtrip',
        'ci-wait',  # legacy; should be defensively narrowed out.
        'lessons-capture',
        'branch-cleanup',
        'archive-plan',
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='prefix-noop-bare',
            change_type='bug_fix',
            scope_estimate='surgical',
            affected_files_count=1,
            phase_6_steps=','.join(bare),
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_bug_fix'
    manifest = read_manifest('prefix-noop-bare')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    # Review gates RETAINED.
    for retained in ('automatic-review', 'sonar-roundtrip'):
        assert retained in steps
    # Legacy ci-wait dropped defensively.
    assert 'ci-wait' not in steps
    assert 'push' in steps
    assert 'lessons-capture' in steps


def test_boundary_normalization_strips_prefix_for_all_downstream_consumers(plan_context):
    """Boundary contract — every entry the cascade-rule layer + downstream output sees is bare.

    Pins the boundary-normalization invariant introduced by lesson
    ``2026-04-27-23-004``: ``cmd_compose`` strips a single leading ``default:``
    from each ``phase_5_candidates`` and ``phase_6_candidates`` entry once at
    intake (via ``canonicalize_step_key``), and every downstream site — the
    six-row matrix, ``_apply_commit_push_disabled``,
    ``_apply_pre_push_quality_gate_inactive``, and
    ``_apply_pre_submission_self_review_inactive`` — consumes those already-bare
    strings without any per-site ``canonicalize_step_key`` call.

    The test feeds a deliberately MIXED candidate list (some entries
    prefixed, some bare, plus a project-prefixed entry to demonstrate the
    ``project:`` prefix is preserved verbatim) to ``cmd_compose``, then
    asserts that every default-domain entry in the resulting
    ``phase_6.steps`` is bare. The only entry that retains its leading
    prefix is the ``project:`` step — its prefix is the canonical
    typed-step notation and is NOT stripped by ``canonicalize_step_key``
    (which only normalizes the ``default:`` namespace).

    This invariant guards against regressions where a future contributor
    re-introduces a per-site ``canonicalize_step_key`` call that masks a
    boundary leak: with the prefix stripped at intake, a per-site strip
    becomes dead code, and a missing intake strip becomes a visible test
    failure here rather than a silent functional drift.
    """
    mixed = [
        # Prefixed default entries.
        'default:push',
        'default:create-pr',
        'plan-marshall:automatic-review',
        # Bare default entries (no prefix to strip).
        'lessons-capture',
        # Typed-step entry (project: prefix is preserved verbatim).
        'project:finalize-step-plugin-doctor',
        # More prefixed defaults.
        'default:branch-cleanup',
        'default:archive-plan',
    ]
    mixed_phase_5 = [
        'default:quality-gate',  # prefixed
        'module-tests',  # bare
    ]
    # Use a Row 7 (default) shape so the cascade-rule output preserves
    # candidates verbatim (modulo boundary normalization). No CI configured.
    result = cmd_compose(
        _compose_ns(
            plan_id='boundary-mixed',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=10,
            phase_5_steps=','.join(mixed_phase_5),
            phase_6_steps=','.join(mixed),
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['rule_fired'] == 'default'

    manifest = read_manifest('boundary-mixed')
    assert manifest is not None
    phase_5_steps = manifest['phase_5']['verification_steps']
    phase_6_steps = manifest['phase_6']['steps']

    # Every default-domain entry is bare — no `default:` prefix anywhere
    # in either phase's output.
    assert not any(s.startswith('default:') for s in phase_5_steps), (
        f'phase_5 leaked `default:`-prefixed entry: {phase_5_steps!r}'
    )
    assert not any(s.startswith('default:') for s in phase_6_steps), (
        f'phase_6 leaked `default:`-prefixed entry: {phase_6_steps!r}'
    )

    # Phase 5 carries the bare normalization of both inputs.
    assert phase_5_steps == ['quality-gate', 'module-tests']

    # Every Phase-6 default-domain entry from the input survives as a bare
    # string after Row 7 (no cascade-rule subtractions on the default rule).
    for bare_default in (
        'push',
        'create-pr',
        'automatic-review',
        'lessons-capture',
        'branch-cleanup',
        'archive-plan',
    ):
        assert bare_default in phase_6_steps, (
            f'expected bare {bare_default!r} in phase_6 but got: {phase_6_steps!r}'
        )

    # The non-default-namespace `project:` prefix is preserved verbatim —
    # boundary normalization strips ONLY the `default:` namespace.
    assert 'project:finalize-step-plugin-doctor' in phase_6_steps


# =============================================================================
# Bundle-self-modification tests removed
#
# The ``bundle_self_modification`` stacked rule was retired by cluster 02
# deliverable 9 — the new built-in ``default:sync-plugin-cache`` step
# (order 14) sits unconditionally between ``default:deploy-target`` (order 12)
# and the agent-dispatched steps in the canonical Phase 6 ordering, which
# subsumes the rule's previous job. Tests pinning the removed rule have been
# deleted with the rule itself.
# =============================================================================


def test_verification_no_files_keeps_full_phase_5_trims_phase_6(plan_context):
    """Row 6 — verification w/o files: full Phase 5, Phase 6 trimmed to records+archive."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-vnofiles',
            change_type='verification',
            scope_estimate='none',
            affected_files_count=0,
            phase_5_steps='quality-gate,module-tests,coverage',
        )
    )
    assert result is not None and result['rule_fired'] == 'verification_no_files'
    manifest = read_manifest('matrix-vnofiles')
    assert manifest is not None
    assert manifest['phase_5']['verification_steps'] == ['quality-gate', 'module-tests', 'coverage']
    assert set(manifest['phase_6']['steps']) == {'lessons-capture', 'adr-propose', 'archive-plan'}


# =============================================================================
# adr-propose registration tests (deliverable 3)
#
# adr-propose is the writing-hook sibling of lessons-capture. It rides the
# same post-run-review role and is registered in DEFAULT_PHASE_6_STEPS plus
# the Rule 1 (early_terminate_analysis) and Rule 6 (verification_no_files)
# minimal intersection sets, so an analysis/verification plan that settled a
# decision can still propose an ADR.
# =============================================================================


def test_adr_propose_in_default_phase_6_steps():
    """adr-propose is registered in DEFAULT_PHASE_6_STEPS, between
    lessons-capture and branch-cleanup (matching its order: 62 frontmatter)."""
    assert 'adr-propose' in DEFAULT_PHASE_6_STEPS
    steps = list(DEFAULT_PHASE_6_STEPS)
    assert steps.index('lessons-capture') < steps.index('adr-propose')
    assert steps.index('adr-propose') < steps.index('branch-cleanup')


def test_adr_propose_kept_in_rule_1_early_terminate_minimal_set(plan_context):
    """Rule 1 (early_terminate_analysis) keeps adr-propose alongside
    lessons-capture and archive-plan when it is in the candidate set."""
    result = cmd_compose(
        _compose_ns(
            plan_id='adr-rule-1',
            change_type='analysis',
            scope_estimate='none',
            affected_files_count=0,
        )
    )
    assert result is not None and result['rule_fired'] == 'early_terminate_analysis'
    manifest = read_manifest('adr-rule-1')
    assert manifest is not None
    assert set(manifest['phase_6']['steps']) == {'lessons-capture', 'adr-propose', 'archive-plan'}


def test_adr_propose_kept_in_rule_6_verification_no_files_minimal_set(plan_context):
    """Rule 6 (verification_no_files) keeps adr-propose alongside
    lessons-capture and archive-plan when it is in the candidate set."""
    result = cmd_compose(
        _compose_ns(
            plan_id='adr-rule-6',
            change_type='verification',
            scope_estimate='none',
            affected_files_count=0,
        )
    )
    assert result is not None and result['rule_fired'] == 'verification_no_files'
    manifest = read_manifest('adr-rule-6')
    assert manifest is not None
    assert set(manifest['phase_6']['steps']) == {'lessons-capture', 'adr-propose', 'archive-plan'}


def test_adr_propose_present_in_default_feature_phase_6(plan_context):
    """A default feature plan (Rule 7) carries adr-propose in its phase-6 set
    — the docs-only and surgical pre-filters pass it through unless explicitly
    subtracted."""
    result = cmd_compose(
        _compose_ns(
            plan_id='adr-default-feature',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=12,
        )
    )
    assert result is not None and result['rule_fired'] == 'default'
    manifest = read_manifest('adr-default-feature')
    assert manifest is not None
    assert 'adr-propose' in manifest['phase_6']['steps']


def test_adr_propose_kept_in_surgical_tech_debt_phase_6(plan_context):
    """The scope row passes phase_6_candidates through unchanged except
    the simplify/whole-tree gates, so adr-propose survives."""
    result = cmd_compose(
        _compose_ns(
            plan_id='adr-docs-only',
            change_type='tech_debt',
            scope_estimate='surgical',
            affected_files_count=3,
            # docs-shaped candidate set: only quality-gate, no module-tests/coverage.
            phase_5_steps='quality-gate',
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
    manifest = read_manifest('adr-docs-only')
    assert manifest is not None
    assert 'adr-propose' in manifest['phase_6']['steps']


# =============================================================================
# Schema + I/O tests
# =============================================================================


def test_compose_writes_manifest_to_expected_path(plan_context):
    cmd_compose(_compose_ns(plan_id='io-write'))
    manifest_path = get_manifest_path('io-write')
    assert manifest_path.exists()
    manifest = read_manifest('io-write')
    assert manifest is not None
    assert manifest['manifest_version'] == 1
    assert manifest['plan_id'] == 'io-write'
    assert isinstance(manifest['phase_5']['verification_steps'], list)
    assert isinstance(manifest['phase_6']['steps'], list)


# =============================================================================
# Input validation tests
# =============================================================================


@pytest.mark.parametrize(
    'field,value,error_code',
    [
        ('change_type', 'unknown_type', 'invalid_change_type'),
        ('scope_estimate', 'massive', 'invalid_scope_estimate'),
        ('track', 'twisty', 'invalid_track'),
    ],
)
def test_compose_rejects_invalid_enum_values(plan_context, field, value, error_code):
    kwargs = {field: value}
    result = cmd_compose(_compose_ns(plan_id='val-enum', **kwargs))
    assert result is not None and result['status'] == 'error'
    assert result['error'] == error_code


def test_compose_clamps_negative_affected_files_count(plan_context):
    """Negative affected_files_count should be clamped to 0 (no crash)."""
    result = cmd_compose(
        _compose_ns(
            plan_id='val-negfiles',
            change_type='analysis',
            scope_estimate='none',
            affected_files_count=-5,
        )
    )
    # With clamp to 0, analysis+0 → early_terminate.
    assert result is not None and result['status'] == 'success'
    assert result['rule_fired'] == 'early_terminate_analysis'


# =============================================================================
# Rule precedence + edge-case coverage
# =============================================================================


def test_early_terminate_wins_over_recipe_when_both_match(plan_context):
    """Rule 1 evaluates before Rule 2 — analysis + recipe_key + 0 files → early_terminate."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-precedence-er',
            change_type='analysis',
            scope_estimate='none',
            recipe_key='lesson_cleanup',
            affected_files_count=0,
        )
    )
    assert result is not None and result['rule_fired'] == 'early_terminate_analysis'


def test_recipe_wins_over_the_scope_row_when_both_match(plan_context):
    """The recipe row evaluates first — recipe_key short-circuits the scope row."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-precedence-rd',
            change_type='tech_debt',
            scope_estimate='surgical',
            recipe_key='lesson_cleanup',
            affected_files_count=2,
            # Docs-only candidate set; recipe rule should still win.
            phase_5_steps='quality-gate',
        )
    )
    assert result is not None and result['rule_fired'] == 'recipe'


# =============================================================================
# Recipe / lesson provenance from status metadata (recipe→default drift fix)
# =============================================================================


def _write_status_metadata(plan_context, plan_id: str, metadata: dict) -> None:
    """Seed ``{plan_dir}/status.json`` with the given ``metadata`` block."""
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_id, 'metadata': metadata}, indent=2),
        encoding='utf-8',
    )


def test_recipe_detected_from_status_plan_source_lesson_id(plan_context):
    """Lesson-derived plan (plan_source=lesson_id, no --recipe-key) fires Row 2.

    Reproduces the archived-plan audit's recipe→default drift: phase-1-init seeds
    ``status.metadata.plan_source`` with a raw lesson id, but the phase-4-plan
    agent omitted ``--recipe-key``. The composer now reads the provenance itself.
    """
    plan_id = 'recipe-from-plan-source'
    _write_status_metadata(plan_context, plan_id, {'plan_source': '2026-06-01-10-001'})
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='enhancement',
            scope_estimate='single_module',
            recipe_key=None,
            affected_files_count=3,
        )
    )
    assert result is not None and result['rule_fired'] == 'recipe'


def test_recipe_detected_from_status_recipe_key_fallback(plan_context):
    """metadata.recipe_key (no plan_source) also fires Row 2 via the fallback."""
    plan_id = 'recipe-from-recipe-key'
    _write_status_metadata(plan_context, plan_id, {'recipe_key': 'lesson_cleanup'})
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            recipe_key=None,
            affected_files_count=4,
        )
    )
    assert result is not None and result['rule_fired'] == 'recipe'


def test_recipe_literal_plan_source_fires_row_2(plan_context):
    """plan_source set to the literal 'recipe' string also selects Row 2."""
    plan_id = 'recipe-literal-source'
    _write_status_metadata(plan_context, plan_id, {'plan_source': 'recipe'})
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            recipe_key=None,
            affected_files_count=4,
        )
    )
    assert result is not None and result['rule_fired'] == 'recipe'


def test_no_plan_source_falls_to_default(plan_context):
    """Status metadata without provenance keys does NOT spuriously fire Row 2."""
    plan_id = 'no-provenance-default'
    _write_status_metadata(plan_context, plan_id, {'change_type': 'feature'})
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            recipe_key=None,
            affected_files_count=4,
        )
    )
    assert result is not None and result['rule_fired'] == 'default'


def test_missing_status_json_falls_to_default(plan_context):
    """A plan with no status.json reads no provenance and falls to Row 7."""
    result = cmd_compose(
        _compose_ns(
            plan_id='no-status-default',
            change_type='feature',
            scope_estimate='multi_module',
            recipe_key=None,
            affected_files_count=4,
        )
    )
    assert result is not None and result['rule_fired'] == 'default'


def test_explicit_recipe_key_overrides_absent_status(plan_context):
    """An explicit --recipe-key still fires Row 2 with no status metadata present."""
    result = cmd_compose(
        _compose_ns(
            plan_id='explicit-recipe-key',
            change_type='feature',
            scope_estimate='multi_module',
            recipe_key='lesson_cleanup',
            affected_files_count=4,
        )
    )
    assert result is not None and result['rule_fired'] == 'recipe'


def test_read_recipe_source_unit(plan_context):
    """Direct unit coverage of the status-metadata provenance surrogate."""
    read_recipe_source = _mem._read_recipe_source

    # No status.json → None.
    assert read_recipe_source('rrs-missing') is None

    # plan_source wins over recipe_key; whitespace trimmed.
    _write_status_metadata(
        plan_context, 'rrs-both', {'plan_source': '  2026-06-02-08-002  ', 'recipe_key': 'lesson_cleanup'}
    )
    assert read_recipe_source('rrs-both') == '2026-06-02-08-002'

    # recipe_key fallback when plan_source absent.
    _write_status_metadata(plan_context, 'rrs-key', {'recipe_key': 'lesson_cleanup'})
    assert read_recipe_source('rrs-key') == 'lesson_cleanup'

    # Empty / blank provenance values are treated as absent.
    _write_status_metadata(plan_context, 'rrs-blank', {'plan_source': '   ', 'recipe_key': ''})
    assert read_recipe_source('rrs-blank') is None


def test_read_recipe_source_malformed_status_degrades_to_none(plan_context):
    """A corrupt-but-present status.json degrades to None instead of crashing."""
    plan_dir = plan_context.plan_dir_for('rrs-malformed')
    (plan_dir / 'status.json').write_text('{ this is not: valid json', encoding='utf-8')
    assert _mem._read_recipe_source('rrs-malformed') is None


def test_compose_tolerates_malformed_status_json(plan_context):
    """compose still succeeds (Row 7) when status.json cannot be parsed."""
    plan_id = 'compose-malformed-status'
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text('not json at all', encoding='utf-8')
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            recipe_key=None,
            affected_files_count=4,
        )
    )
    assert result is not None and result['rule_fired'] == 'default'


# =============================================================================
# Decision-log emission lands in the plan's own logs/decision.log (loggability fix)
# =============================================================================


def test_emit_decision_log_writes_in_process(plan_context):
    """``_emit_decision_log`` writes directly to the plan's decision.log.

    Regression guard for the ``unloggable`` defect: the composer runs from the
    plugin cache (outside the project tree), so the former
    executor-subprocess emission silently dropped every line. The in-process
    write via ``plan_logging.log_entry`` must land the entry in
    ``{plan_dir}/logs/decision.log``. status.json must exist for the log path
    to resolve plan-scoped rather than to the global fallback.
    """
    plan_id = 'decision-log-in-process'
    _write_status_metadata(plan_context, plan_id, {'change_type': 'feature'})
    message = '(plan-marshall:manage-execution-manifest:compose) Rule default fired — sentinel'

    _mem._emit_decision_log(plan_id, message)

    decision_log = plan_context.plan_dir_for(plan_id) / 'logs' / 'decision.log'
    assert decision_log.is_file(), 'decision.log was not written in-process'
    assert message in decision_log.read_text(encoding='utf-8')


def test_surgical_enhancement_with_code_candidates_falls_to_default(plan_context):
    """The scope row only matches bug_fix/tech_debt; surgical+enhancement → default."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-surgical-enh',
            change_type='enhancement',
            scope_estimate='surgical',
            affected_files_count=2,
            phase_5_steps='verify:quality-gate,verify:module-tests',
        )
    )
    assert result is not None and result['rule_fired'] == 'default'
    manifest = read_manifest('matrix-surgical-enh')
    assert manifest is not None
    # Default keeps the full phase_6 candidate list — enhancement is a member of
    # the code-touching activation set {feature, bug_fix, tech_debt, enhancement},
    # so with affected_files_count > 0 the simplify_inactive /
    # security_audit_inactive pre-filters keep both ceremony steps.
    assert manifest['phase_6']['steps'] == list(DEFAULT_PHASE_6_STEPS)


def test_surgical_enhancement_with_docs_candidates_falls_to_default(plan_context):
    """surgical+enhancement with a docs-shaped candidate set now reaches the default row.

    This input used to be intercepted by the retired ``docs_only`` row purely
    because the candidate list lacked a module-tests / coverage role. The
    candidate list's shape says nothing about whether the change needs a build,
    so the row is gone and the ordinary matrix path applies: the scope row does
    not match ``enhancement``, so the default row fires and KEEPS the candidate.
    """
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-surgical-enh-docs',
            change_type='enhancement',
            scope_estimate='surgical',
            affected_files_count=1,
            phase_5_steps='verify:quality-gate',
        )
    )
    assert result is not None and result['rule_fired'] == 'default'
    assert result['phase_5']['verification_steps_count'] == 1


def test_single_module_tech_debt_with_docs_candidates_falls_to_default(plan_context):
    """The retired row also covered ``single_module`` scope; that path is gone too.

    ``single_module`` + ``tech_debt`` misses the scope row (which requires
    ``surgical``), so with no docs_only row to catch it the default row fires.
    """
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-single-mod-docs',
            change_type='tech_debt',
            scope_estimate='single_module',
            affected_files_count=4,
            phase_5_steps='verify:quality-gate',
        )
    )
    assert result is not None and result['rule_fired'] == 'default'
    assert result['phase_5']['verification_steps_count'] == 1


def test_recipe_with_partial_phase_5_candidates_filters_to_known_steps(plan_context):
    """Recipe rule intersects phase_5 candidates by role ∈ {quality-gate, module-tests}.

    See decision-rules.md § Role-Field Intersection. ``verify:coverage``
    (role ``coverage``) and ``exotic-step`` (no role) are dropped;
    ``verify:quality-gate`` (role ``quality-gate``) and ``verify:module-tests``
    (role ``module-tests``) are kept.
    """
    cmd_compose(
        _compose_ns(
            plan_id='matrix-recipe-filter',
            change_type='tech_debt',
            scope_estimate='surgical',
            recipe_key='lesson_cleanup',
            affected_files_count=2,
            # Pass an unknown candidate alongside the known ones.
            phase_5_steps='verify:quality-gate,verify:module-tests,verify:coverage,exotic-step',
        )
    )
    manifest = read_manifest('matrix-recipe-filter')
    assert manifest is not None
    # Recipe keeps candidates whose role ∈ {quality-gate, module-tests};
    # verify:coverage (role: coverage) and exotic-step (no role) dropped.
    assert manifest['phase_5']['verification_steps'] == ['verify:quality-gate', 'verify:module-tests']


def test_compose_is_idempotent_and_deterministic(plan_context):
    """Re-composing with identical inputs overwrites and yields identical manifest."""
    first = cmd_compose(_compose_ns(plan_id='matrix-idempotent'))
    manifest_first = read_manifest('matrix-idempotent')
    second = cmd_compose(_compose_ns(plan_id='matrix-idempotent'))
    manifest_second = read_manifest('matrix-idempotent')
    assert first is not None and second is not None
    assert first['rule_fired'] == second['rule_fired']
    assert manifest_first == manifest_second


def test_compose_default_phase_6_steps_when_csv_omitted(plan_context):
    """When --phase-6-steps is None, DEFAULT_PHASE_6_STEPS is used."""
    cmd_compose(
        Namespace(
            plan_id='matrix-default-csv',
            change_type='feature',
            track='complex',
            scope_estimate='multi_module',
            recipe_key=None,
            affected_files_count=12,
            phase_5_steps=None,  # Falls back to DEFAULT_PHASE_5_STEPS.
            phase_6_steps=None,  # Falls back to DEFAULT_PHASE_6_STEPS.
            commit_and_push=None,
        )
    )
    manifest = read_manifest('matrix-default-csv')
    assert manifest is not None
    assert manifest['phase_5']['verification_steps'] == list(DEFAULT_PHASE_5_STEPS)
    assert manifest['phase_6']['steps'] == list(DEFAULT_PHASE_6_STEPS)


# =============================================================================
# Ascending frontmatter-order emission (archive-order barrier fix)
#
# cmd_compose never re-sorted the marshal.json ``phase_6.steps`` map by
# frontmatter order, so ``manage-config sync-defaults`` back-filling a missing
# default-on step by APPENDING it landed the new step after ``archive-plan``
# (order 1000) regardless of its own order. cmd_compose now sorts the FINAL
# ``phase_6.steps`` by resolved frontmatter order before persistence, so
# ``archive-plan`` sorts last among order-resolvable steps automatically.
# =============================================================================


def test_compose_sorts_phase_6_steps_by_frontmatter_order(plan_context):
    """Regression: a candidate list placing ``archive-plan`` BEFORE a lower-order
    step emits the lower-order step first in the composed manifest.

    Reproduces the live bug: ``finalize-step-preference-emitter`` (order 80) was
    appended AFTER ``archive-plan`` (order 1000) by ``manage-config
    sync-defaults``. cmd_compose now sorts ``phase_6.steps`` by resolved
    frontmatter order, so the preference-emitter (80) is emitted strictly before
    ``archive-plan`` (1000), which sorts last among order-resolvable steps.
    """
    # Bug-reproducing candidate order: archive-plan (order 1000) precedes the
    # lower-order preference-emitter (order 80) — exactly the layout
    # sync-defaults produced by appending the back-filled default-on step.
    candidates = [
        'push',
        'create-pr',
        'lessons-capture',
        'archive-plan',  # order 1000
        'finalize-step-preference-emitter',  # order 80 — appended AFTER archive-plan
    ]
    result = cmd_compose(
        _compose_ns(
            plan_id='order-barrier-fix',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=5,
            phase_6_steps=','.join(candidates),
        )
    )
    assert result is not None and result['status'] == 'success'
    manifest = read_manifest('order-barrier-fix')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    assert 'archive-plan' in steps and 'finalize-step-preference-emitter' in steps
    # The composer sorted by frontmatter order: the low-order step now precedes
    # archive-plan even though the input placed it after.
    assert steps.index('finalize-step-preference-emitter') < steps.index('archive-plan')
    # archive-plan (order 1000, the highest) sorts last among order-resolvable steps.
    assert steps[-1] == 'archive-plan'


def test_compose_places_settle_steps_before_push_and_wait_steps_after(plan_context):
    """D3 mutation-settling reorder: the composer's ``_sort_steps_by_frontmatter_order``
    places every local-settleable HEAD-changing step (order < 10) BEFORE
    ``default:push`` (order 10) and every post-push WAIT step (order > 10) AFTER
    it — the settle → push once → wait contract expressed purely via step-doc
    ``order:`` frontmatter. Pins the D3 move of ``architecture-refresh`` from the
    post-push region (order 25) into the pre-push settle band (order 9).
    """
    # Deliberately SCRAMBLED input: push first, wait steps and architecture-refresh
    # ahead of the other settle steps — the composer must re-sort by resolved
    # frontmatter order so the barrier holds regardless of candidate-list order.
    scrambled = [
        'push',  # order 10 (the single push barrier)
        'ci-verify',  # wait (> 10)
        'sonar-roundtrip',  # wait (> 10)
        'architecture-refresh',  # settle (order 9) — the D3 move
        'finalize-step-security-audit',  # settle (order 9)
        'finalize-step-simplify',  # settle (order 8)
        'pre-push-quality-gate',  # settle (order 5)
        'finalize-step-sync-baseline',  # settle (order 3)
        'create-pr',  # wait (> 10)
        'automatic-review',  # wait (> 10)
        'branch-cleanup',  # merge (order 70)
    ]
    # ``pre-push-quality-gate`` is order-band-3 settle, but it is also governed by
    # the orthogonal build-necessity pre-filter (``should_execute_build``): a
    # footprint-less compose would drop it before the sort can place it. To assert
    # the ORDERING of the settle step it must survive, so seed a build_map glob and
    # a matching live footprint. The two monkeypatched seams are restored in the
    # ``finally`` block so the stub never leaks to sibling tests.
    import extension_base

    _original_resolve_footprint = _mem._resolve_footprint
    _original_plan_footprint = extension_base._resolve_plan_footprint
    _write_marshal(plan_context.fixture_dir, activation_globs=['marketplace/bundles/**/*.py'])
    _stub_footprint(['marketplace/bundles/plan-marshall/skills/foo.py'])
    try:
        result = cmd_compose(
            _compose_ns(
                plan_id='settle-before-push',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=10,
                phase_6_steps=','.join(scrambled),
            )
        )
    finally:
        _mem._resolve_footprint = _original_resolve_footprint
        extension_base._resolve_plan_footprint = _original_plan_footprint
    assert result is not None and result['status'] == 'success'
    manifest = read_manifest('settle-before-push')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    push_idx = steps.index('push')
    # Every local-settleable HEAD-changing step sorts BEFORE the single push.
    for settle in (
        'finalize-step-sync-baseline',
        'pre-push-quality-gate',
        'finalize-step-simplify',
        'finalize-step-security-audit',
        'architecture-refresh',
    ):
        assert steps.index(settle) < push_idx, f'{settle!r} must sort before push; got {steps!r}'
    # architecture-refresh (order 9) now sits in the settle band, not the
    # post-push region it occupied at order 25.
    assert steps.index('architecture-refresh') < push_idx
    # Every post-push WAIT step sorts AFTER the single push.
    for wait in ('create-pr', 'ci-verify', 'automatic-review', 'sonar-roundtrip'):
        assert steps.index(wait) > push_idx, f'{wait!r} must sort after push; got {steps!r}'


# =============================================================================
# commit_and_push pre-filter tests
# =============================================================================


@pytest.mark.parametrize(
    'commit_and_push,expect_commit_push,expect_omitted',
    [
        ('true', True, False),
        (None, True, False),  # Absent flag defaults to true.
        ('false', False, True),
    ],
)
def test_commit_and_push_pre_filter(plan_context, commit_and_push, expect_commit_push, expect_omitted):
    """Pre-filter: commit_and_push=false drops push; true retains it."""
    slug = commit_and_push or 'absent'
    plan_id = f'matrix-cap-{slug}'
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
            commit_and_push=commit_and_push,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['commit_push_omitted'] is expect_omitted
    manifest = read_manifest(plan_id)
    assert manifest is not None
    if expect_commit_push:
        assert 'push' in manifest['phase_6']['steps']
    else:
        assert 'push' not in manifest['phase_6']['steps']


def test_commit_and_push_false_emits_decision_log_message(plan_context):
    """commit_and_push=false triggers the dedicated decision-log emission helper."""
    captured: list[str] = []
    original_helper = _mem._log_commit_push_omitted

    def _capture(plan_id):
        captured.append(plan_id)

    _mem._log_commit_push_omitted = _capture
    try:
        cmd_compose(
            _compose_ns(
                plan_id='matrix-cap-log',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=4,
                commit_and_push='false',
            )
        )
    finally:
        _mem._log_commit_push_omitted = original_helper
    assert captured == ['matrix-cap-log']


def test_commit_and_push_false_decision_log_message_matches_contract(plan_context):
    """commit_and_push=false emits the exact decision-log line from the deliverable contract."""
    captured: list[tuple[str, str]] = []
    original_emit = _mem._emit_decision_log

    def _capture(plan_id, message):
        captured.append((plan_id, message))

    _mem._emit_decision_log = _capture
    try:
        cmd_compose(
            _compose_ns(
                plan_id='matrix-cap-msg',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=4,
                commit_and_push='false',
            )
        )
    finally:
        _mem._emit_decision_log = original_emit

    # Expect at least the omission entry; the rule-fired entry is also emitted.
    omission_entries = [(pid, msg) for pid, msg in captured if 'push omitted' in msg]
    assert len(omission_entries) == 1, f'expected one omission entry, got {captured!r}'
    pid, msg = omission_entries[0]
    assert pid == 'matrix-cap-msg'
    assert msg == ('(plan-marshall:manage-execution-manifest:compose) push omitted — commit_and_push=false')


def test_commit_and_push_default_does_not_emit_omission_log(plan_context):
    """When commit_and_push is absent (defaults to true), no omission log fires."""
    captured: list[str] = []
    original_helper = _mem._log_commit_push_omitted

    def _capture(plan_id):
        captured.append(plan_id)

    _mem._log_commit_push_omitted = _capture
    try:
        cmd_compose(
            _compose_ns(
                plan_id='matrix-cap-default-nolog',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=4,
                commit_and_push=None,
            )
        )
    finally:
        _mem._log_commit_push_omitted = original_helper
    assert captured == []


def test_commit_and_push_invalid_value_rejected(plan_context):
    """Invalid commit_and_push values produce a structured error response."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-cap-bad',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=2,
            commit_and_push='nope',
        )
    )
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'invalid_commit_and_push'


def test_commit_and_push_false_with_recipe_still_drops_commit_push(plan_context):
    """Pre-filter applies before the row matrix — recipe rule still loses push."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-cap-recipe',
            change_type='tech_debt',
            scope_estimate='surgical',
            recipe_key='lesson_cleanup',
            affected_files_count=2,
            commit_and_push='false',
        )
    )
    assert result is not None and result['rule_fired'] == 'recipe'
    manifest = read_manifest('matrix-cap-recipe')
    assert manifest is not None
    assert 'push' not in manifest['phase_6']['steps']


def test_commit_and_push_false_with_prefixed_input_drops_commit_push_and_pre_push(plan_context):
    """Regression — _apply_commit_push_disabled drops both gates with prefixed input.

    Pins the latent bug fixed by lesson ``2026-04-27-23-004``: before boundary
    normalization, ``_apply_commit_push_disabled`` compared candidate entries
    against the bare-name set ``{push, pre-push-quality-gate,
    pre-submission-self-review}``. When ``marshal.json`` emitted prefixed
    candidates (e.g., ``default:push``), the comparison silently failed
    and the gate steps survived in the manifest despite ``commit_and_push=false``.

    Boundary normalization in ``cmd_compose`` strips the ``default:`` prefix
    once at intake, so ``_apply_commit_push_disabled`` now sees bare strings
    and the membership check works regardless of how the caller spelled the
    candidate IDs. This test feeds a fully prefixed candidate list to
    ``cmd_compose`` with ``commit_and_push=false`` and asserts both gate steps
    are dropped and the manifest output is bare.
    """
    prefixed = [
        'default:pre-push-quality-gate',
        'default:push',
        'default:create-pr',
        'plan-marshall:automatic-review',
        'default:lessons-capture',
        'default:branch-cleanup',
        'default:archive-plan',
    ]
    result = cmd_compose(
        _compose_ns(
            plan_id='cap-false-prefixed',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=4,
            phase_6_steps=','.join(prefixed),
            commit_and_push='false',
        )
    )
    assert result is not None and result['status'] == 'success'
    # commit_push omitted flag is True — pre-filter fired on the prefixed input.
    assert result['commit_push_omitted'] is True

    manifest = read_manifest('cap-false-prefixed')
    assert manifest is not None
    steps = manifest['phase_6']['steps']

    # Both gate steps are dropped (the latent bug — they would have
    # survived as `default:push` / `default:pre-push-quality-gate`
    # before the boundary normalization landed).
    assert 'push' not in steps
    assert 'pre-push-quality-gate' not in steps

    # Output is bare — no `default:` prefix anywhere.
    assert not any(s.startswith('default:') for s in steps), f'phase_6 leaked `default:`-prefixed entry: {steps!r}'

    # Other steps from the input survive as bare strings.
    for kept in (
        'create-pr',
        'automatic-review',
        'lessons-capture',
        'branch-cleanup',
        'archive-plan',
    ):
        assert kept in steps, f'expected bare {kept!r} in phase_6 but got: {steps!r}'


# =============================================================================
# CLI plumbing (subprocess) tests — keep small, just confirm wiring
# =============================================================================


def test_cli_compose_then_read_roundtrip(plan_context):
    result = run_script(
        SCRIPT_PATH,
        'compose',
        '--plan-id',
        'cli-rt',
        '--change-type',
        'feature',
        '--track',
        'complex',
        '--scope-estimate',
        'multi_module',
        '--affected-files-count',
        '10',
    )
    assert result.success, f'compose failed: stderr={result.stderr!r}'
    compose_data = result.toon()
    assert compose_data['status'] == 'success'

    read_result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'cli-rt')
    assert read_result.success
    read_data = read_result.toon()
    assert read_data['plan_id'] == 'cli-rt'
    assert read_data['manifest_version'] == 1


def test_cli_compose_invalid_change_type_emits_toon_error(plan_context):
    result = run_script(
        SCRIPT_PATH,
        'compose',
        '--plan-id',
        'cli-bad',
        '--change-type',
        'nonsense',
        '--track',
        'simple',
        '--scope-estimate',
        'surgical',
    )
    # Script exits 0 on validation errors (TOON contract); error in stdout.
    assert result.returncode == 0
    data = result.toon()
    assert data['status'] == 'error'
    assert data['error'] == 'invalid_change_type'


def test_cli_compose_with_all_optional_flags_roundtrips(plan_context):
    """CLI accepts --recipe-key, --affected-files-count, and both step CSVs."""
    result = run_script(
        SCRIPT_PATH,
        'compose',
        '--plan-id',
        'cli-allflags',
        '--change-type',
        'tech_debt',
        '--track',
        'simple',
        '--scope-estimate',
        'surgical',
        '--recipe-key',
        'lesson_cleanup',
        '--affected-files-count',
        '2',
        '--phase-5-steps',
        'quality-gate,module-tests',
        '--phase-6-steps',
        'push,create-pr,branch-cleanup',
    )
    assert result.success, f'compose failed: stderr={result.stderr!r}'
    data = result.toon()
    assert data['status'] == 'success'
    assert data['rule_fired'] == 'recipe'


def test_cli_compose_commit_and_push_false_omits_commit_push(plan_context):
    """CLI accepts --commit-and-push false and emits a manifest without push."""
    result = run_script(
        SCRIPT_PATH,
        'compose',
        '--plan-id',
        'cli-cap-false',
        '--change-type',
        'feature',
        '--track',
        'complex',
        '--scope-estimate',
        'multi_module',
        '--commit-and-push',
        'false',
    )
    assert result.success, f'compose failed: stderr={result.stderr!r}'
    compose_data = result.toon()
    assert compose_data['status'] == 'success'
    # TOON parser may coerce the bool — accept both shapes defensively.
    assert compose_data['commit_push_omitted'] in (True, 'true', 1)

    read_result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'cli-cap-false')
    assert read_result.success
    manifest = read_result.toon()
    assert 'push' not in manifest['phase_6']['steps']


# =============================================================================
# pre-push-quality-gate pre-filter tests
# =============================================================================


def _write_marshal(
    fixture_dir: Path, *, activation_globs: list[str] | None = None, include_pre_push_key: bool = True
) -> None:
    """Write a marshal.json whose pre-push activation derives from build.map.

    Pre-push-quality-gate activation now reads the per-entry globs from
    ``build.map`` (D7/D8) — there is no separate
    ``pre_push_quality_gate.activation_globs`` source. ``activation_globs`` here
    names the globs the seeded build_map should carry:

    - ``include_pre_push_key=False`` → omit the ``build.map`` block
      entirely (simulates the "absent" branch → gate dropped).
    - ``activation_globs is None`` (with the block present) → seed a build_map
      whose single entry carries no usable glob (also "absent" → gate dropped).
    - ``activation_globs == []`` → seed an empty build_map (no globs → dropped).
    - ``activation_globs == [g, ...]`` → seed one build_map entry per glob so
      ``_read_build_map_globs`` collects exactly those globs.
    """
    marshal_path = fixture_dir / 'marshal.json'
    data: dict = {'plan': {'phase-6-finalize': {}}, 'build': {}}
    if include_pre_push_key:
        globs = activation_globs if activation_globs is not None else []
        entries = [
            {'glob': glob, 'role': 'production', 'build_class': 'compile'} for glob in globs
        ]
        data['build']['map'] = {'python': entries}
    marshal_path.write_text(json.dumps(data), encoding='utf-8')


def _stub_footprint(footprint: list[str]) -> None:
    """Stub the footprint seams so the activation pre-filters see the given set.

    The compose pre-filters derive the live plan footprint on demand instead of
    reading a seeded ``references.modified_files`` ledger. Two distinct seams are
    in play: the self-review pre-filter reads the manifest module's
    ``_resolve_footprint``, while the pre-push-quality-gate pre-filter delegates
    to ``extension_base.should_execute_build``, which resolves the footprint via
    the extension_base module's ``_resolve_plan_footprint``. Both are replaced so
    the injected footprint drives every activation decision. The
    ``TestPrePushQualityGatePreFilter`` autouse fixture restores both after each
    test.
    """
    import extension_base

    _mem._resolve_footprint = lambda plan_id: list(footprint)
    extension_base._resolve_plan_footprint = lambda plan_id: list(footprint)


def _candidate_phase_6_with_pre_push() -> str:
    """Return a Phase 6 candidate CSV that includes pre-push-quality-gate.

    The default candidate set does NOT include pre-push-quality-gate, so tests
    that exercise the pre-filter must opt the step in via the candidate CSV.
    """
    return ','.join(list(DEFAULT_PHASE_6_STEPS) + ['pre-push-quality-gate'])


class TestPrePushQualityGatePreFilter:
    """Activation-driven pre-filter for ``pre-push-quality-gate``.

    Each test asserts BOTH the resulting ``phase_6.steps`` content AND the
    decision-log line presence/absence. The decision-log emitter is patched on
    ``_mem._emit_decision_log`` and entries are captured into a list per test.
    The live plan footprint is injected via ``_stub_footprint`` (which replaces
    ``_mem._resolve_footprint``); the autouse fixture below restores the original
    resolver after every test so the stub never leaks.
    """

    @pytest.fixture(autouse=True)
    def _restore_footprint_resolver(self):
        import extension_base

        original = _mem._resolve_footprint
        original_plan_footprint = extension_base._resolve_plan_footprint
        yield
        _mem._resolve_footprint = original
        extension_base._resolve_plan_footprint = original_plan_footprint

    # The emitter no longer composes a reason of its own — it forwards the
    # build-decision verdict's OWN reason text, which varies by which
    # not_necessary branch fired. Tests therefore match the stable prefix and
    # assert the forwarded tail separately (see
    # ``test_omit_line_forwards_the_verdict_reason``). A hardcoded full line here
    # would re-pin the retired invented reason.
    _OMIT_PREFIX = (
        '(plan-marshall:manage-execution-manifest:compose) pre-push-quality-gate omitted — '
    )

    @staticmethod
    def _capture_decision_log() -> tuple[list[tuple[str, str]], Callable[[str, str], None]]:
        """Install a capturing replacement for ``_emit_decision_log``.

        Returns the capture list plus the original function so the caller can
        restore it in a ``finally`` block.
        """
        captured: list[tuple[str, str]] = []
        original = _mem._emit_decision_log

        def _capture(plan_id: str, message: str) -> None:
            captured.append((plan_id, message))

        _mem._emit_decision_log = _capture
        return captured, original

    @classmethod
    def _omit_entries(cls, captured: list[tuple[str, str]]) -> list[tuple[str, str]]:
        return [entry for entry in captured if entry[1].startswith(cls._OMIT_PREFIX)]

    def test_omit_when_activation_globs_absent(self, plan_context):
        """Config key missing → step removed and omission line emitted."""
        plan_id = 'pp-globs-absent'
        # marshal.json exists but lacks the pre_push_quality_gate key entirely.
        _write_marshal(plan_context.fixture_dir, include_pre_push_key=False)
        _stub_footprint(['marketplace/bundles/plan-marshall/skills/foo.py'])

        captured, original = self._capture_decision_log()
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=4,
                    phase_6_steps=_candidate_phase_6_with_pre_push(),
                )
            )
        finally:
            _mem._emit_decision_log = original

        assert result is not None and result['status'] == 'success'
        assert result['pre_push_quality_gate_omitted'] is True
        manifest = read_manifest(plan_id)
        assert manifest is not None
        assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']
        # All other DEFAULT_PHASE_6_STEPS preserved.
        for step in DEFAULT_PHASE_6_STEPS:
            assert step in manifest['phase_6']['steps']
        omit_entries = self._omit_entries(captured)
        assert len(omit_entries) == 1
        assert omit_entries[0][0] == plan_id

    def test_omit_line_forwards_the_verdict_reason(self, plan_context):
        """The omission line states the reason the VERDICT gave, not an invented one.

        The emitter used to hardcode 'no build_map globs or no footprint match' —
        a disjunction that names both branches at once and so is wrong about
        which one actually fired. Forwarding the verdict's own text keeps the log
        truthful and keeps the reason vocabulary owned by the single authority.
        """
        plan_id = 'pp-reason-forwarded'
        _write_marshal(plan_context.fixture_dir, activation_globs=['**/*.py'])
        # A non-empty footprint that intersects no build_map glob — this selects a
        # SPECIFIC not_necessary branch with its own distinct reason text.
        _stub_footprint(['doc/user/configuration.adoc'])

        captured, original = self._capture_decision_log()
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=1,
                    phase_6_steps=_candidate_phase_6_with_pre_push(),
                )
            )
        finally:
            _mem._emit_decision_log = original

        assert result is not None and result['pre_push_quality_gate_omitted'] is True
        omit_entries = self._omit_entries(captured)
        assert len(omit_entries) == 1
        reason = omit_entries[0][1][len(self._OMIT_PREFIX):]
        # The verdict's own wording for the footprint-touches-no-glob branch.
        assert 'touches no build_map glob' in reason
        # And emphatically NOT the retired invented disjunction.
        assert reason != 'no build_map globs or no footprint match'

    def test_pre_filter_consults_the_authority_command_free(self, plan_context):
        """The pre-filter asks the plan-wide question — it nominates no command.

        "Does this plan need pre-push-quality-gate at all?" is plan-wide. The
        verdict does not vary by command, so passing one (the retired
        ``'quality-gate'`` representative) implies a command-sensitivity that does
        not exist and invites a future reader to pick a different one. This pins
        the actual argument at the authority boundary.
        """
        plan_id = 'pp-command-free'
        _write_marshal(plan_context.fixture_dir, activation_globs=['**/*.py'])
        _stub_footprint(['doc/user/configuration.adoc'])

        import extension_base

        calls: list[tuple] = []
        original_should = extension_base.should_execute_build

        def _record(canonical_command, plan_id_, *args, **kwargs):
            calls.append((canonical_command, plan_id_))
            return original_should(canonical_command, plan_id_, *args, **kwargs)

        extension_base.should_execute_build = _record
        _captured, original = self._capture_decision_log()
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=1,
                    phase_6_steps=_candidate_phase_6_with_pre_push(),
                )
            )
        finally:
            _mem._emit_decision_log = original
            extension_base.should_execute_build = original_should

        assert result is not None and result['pre_push_quality_gate_omitted'] is True
        assert calls, 'the pre-filter never consulted the build-decision authority'
        assert all(command is None for command, _ in calls), calls

    def test_omit_when_activation_globs_empty(self, plan_context):
        """activation_globs: [] → same behavior as missing config."""
        plan_id = 'pp-globs-empty'
        _write_marshal(plan_context.fixture_dir, activation_globs=[])
        _stub_footprint(['marketplace/bundles/plan-marshall/skills/foo.py'])

        captured, original = self._capture_decision_log()
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=4,
                    phase_6_steps=_candidate_phase_6_with_pre_push(),
                )
            )
        finally:
            _mem._emit_decision_log = original

        assert result is not None and result['pre_push_quality_gate_omitted'] is True
        manifest = read_manifest(plan_id)
        assert manifest is not None
        assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']
        for step in DEFAULT_PHASE_6_STEPS:
            assert step in manifest['phase_6']['steps']
        assert len(self._omit_entries(captured)) == 1

    def test_omit_when_modified_files_empty(self, plan_context):
        """Globs configured but references.modified_files empty → step removed."""
        plan_id = 'pp-mod-empty'
        _write_marshal(plan_context.fixture_dir, activation_globs=['marketplace/bundles/**/*.py'])
        _stub_footprint([])  # empty footprint

        captured, original = self._capture_decision_log()
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=4,
                    phase_6_steps=_candidate_phase_6_with_pre_push(),
                )
            )
        finally:
            _mem._emit_decision_log = original

        assert result is not None and result['pre_push_quality_gate_omitted'] is True
        manifest = read_manifest(plan_id)
        assert manifest is not None
        assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']
        assert len(self._omit_entries(captured)) == 1

    def test_omit_when_no_glob_matches(self, plan_context):
        """Globs configured, modified_files contains only non-matching paths → step removed."""
        plan_id = 'pp-no-match'
        _write_marshal(plan_context.fixture_dir, activation_globs=['marketplace/bundles/**/*.py'])
        # All paths fall outside marketplace/bundles/.
        _stub_footprint(['doc/readme.md', 'CHANGELOG.txt'])

        captured, original = self._capture_decision_log()
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=2,
                    phase_6_steps=_candidate_phase_6_with_pre_push(),
                )
            )
        finally:
            _mem._emit_decision_log = original

        assert result is not None and result['pre_push_quality_gate_omitted'] is True
        manifest = read_manifest(plan_id)
        assert manifest is not None
        assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']
        assert len(self._omit_entries(captured)) == 1

    def test_keep_when_glob_matches(self, plan_context):
        """At least one modified_file matches → step retained, no omission line."""
        plan_id = 'pp-match'
        _write_marshal(plan_context.fixture_dir, activation_globs=['marketplace/bundles/**/*.py'])
        _stub_footprint(
            [
                'doc/readme.md',  # non-match
                'marketplace/bundles/plan-marshall/skills/foo.py',  # match
            ]
        )

        captured, original = self._capture_decision_log()
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=2,
                    phase_6_steps=_candidate_phase_6_with_pre_push(),
                )
            )
        finally:
            _mem._emit_decision_log = original

        assert result is not None and result['pre_push_quality_gate_omitted'] is False
        manifest = read_manifest(plan_id)
        assert manifest is not None
        assert 'pre-push-quality-gate' in manifest['phase_6']['steps']
        # No omission entry emitted.
        assert self._omit_entries(captured) == []

    def test_commit_and_push_false_strips_pre_push_too(self, plan_context):
        """commit_and_push=false strips both push and pre-push-quality-gate.

        The commit_push_disabled pre-filter runs FIRST and removes both steps, so
        the downstream pre-push-quality-gate filter sees the step already gone and
        is a no-op (no omission line emitted by the pre-push filter, regardless
        of glob match).
        """
        plan_id = 'pp-cap-false'
        # Configure globs and matching modified_files — the gate WOULD be
        # active, but commit_and_push=false must strip it anyway.
        _write_marshal(plan_context.fixture_dir, activation_globs=['marketplace/bundles/**/*.py'])
        _stub_footprint(['marketplace/bundles/plan-marshall/skills/foo.py'])

        captured, original = self._capture_decision_log()
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=4,
                    phase_6_steps=_candidate_phase_6_with_pre_push(),
                    commit_and_push='false',
                )
            )
        finally:
            _mem._emit_decision_log = original

        assert result is not None and result['status'] == 'success'
        assert result['commit_push_omitted'] is True
        # The pre-push-quality-gate filter is a no-op once the commit_push_disabled
        # filter has already removed the step.
        assert result['pre_push_quality_gate_omitted'] is False
        manifest = read_manifest(plan_id)
        assert manifest is not None
        assert 'push' not in manifest['phase_6']['steps']
        assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']
        # Pre-push-quality-gate omission line is NOT emitted (the commit_push_disabled
        # filter handled the removal).
        assert self._omit_entries(captured) == []

    def test_pre_filter_order_independent_of_six_row_matrix(self, plan_context):
        """Pre-filter runs before Row 1/Row 2/Row 7 — observable via decision-log ordering.

        The composer calls (in order):
          1. _apply_commit_push_disabled
          2. _apply_pre_push_quality_gate_inactive
          3. _decide() — which selects a row (Row 1: early_terminate, Row 2:
             recipe, Row 7: default, etc.)
          4. _log_commit_push_omitted (if fired)
          5. _log_pre_push_quality_gate_omitted (if fired)
          6. _log_decision (always — rule line)

        Even though log emission happens after _decide, the row matrix already
        sees the filtered candidate list, which means the omission line MUST be
        captured before the rule line, and the rule line MUST reflect the
        absence of pre-push-quality-gate from phase_6.steps.

        This test temporarily replaces ``_log_decision`` (which the module-level
        setup stubs out for speed) with a capturing implementation that mirrors
        the production message contract, so the rule-fired line is observable.
        """
        plan_id = 'pp-order'
        # Activation_globs absent → pre-filter fires.
        _write_marshal(plan_context.fixture_dir, include_pre_push_key=False)
        _stub_footprint(['marketplace/bundles/plan-marshall/skills/foo.py'])

        captured: list[tuple[str, str]] = []
        original_emit = _mem._emit_decision_log
        original_log_decision = _mem._log_decision

        def _capture(plan_id_: str, message: str) -> None:
            captured.append((plan_id_, message))

        # Capturing replacement for _log_decision that mirrors the contract
        # in scripts/manage-execution-manifest.py::_log_decision().
        def _log_decision_capture(plan_id_, rule, body):
            phase_5 = body.get('phase_5', {})
            phase_6 = body.get('phase_6', {})
            p5_steps = phase_5.get('verification_steps', [])
            p6_steps = phase_6.get('steps', [])
            early = phase_5.get('early_terminate', False)
            message = (
                f'(plan-marshall:manage-execution-manifest:compose) Rule {rule} fired — '
                f'early_terminate={early}, phase_5.verification_steps={p5_steps}, '
                f'phase_6.steps={p6_steps}'
            )
            _capture(plan_id_, message)

        _mem._emit_decision_log = _capture
        _mem._log_decision = _log_decision_capture
        try:
            # Use a Row 7 (default) shape — feature + multi_module + files.
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=10,
                    phase_6_steps=_candidate_phase_6_with_pre_push(),
                )
            )
        finally:
            _mem._emit_decision_log = original_emit
            _mem._log_decision = original_log_decision

        assert result is not None and result['rule_fired'] == 'default'
        assert result['pre_push_quality_gate_omitted'] is True

        # Ordering: omission line precedes rule-fired line.
        messages = [msg for _, msg in captured]
        omit_idx = next(
            (i for i, m in enumerate(messages) if m.startswith(self._OMIT_PREFIX)),
            None,
        )
        rule_idx = next(
            (i for i, m in enumerate(messages) if 'Rule default fired' in m),
            None,
        )
        assert omit_idx is not None, f'omission line missing in {messages!r}'
        assert rule_idx is not None, f'rule line missing in {messages!r}'
        assert omit_idx < rule_idx, (
            f'pre-filter omission line must precede rule line; got omit_idx={omit_idx}, rule_idx={rule_idx}'
        )

        # Rule line reflects filtered phase_6.steps (no pre-push-quality-gate).
        rule_msg = messages[rule_idx]
        assert 'pre-push-quality-gate' not in rule_msg

        # Manifest content also reflects the pre-filter outcome.
        manifest = read_manifest(plan_id)
        assert manifest is not None
        assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']

    # =========================================================================
    # Boundary-normalization regression cases (lesson 2026-04-27-23-004)
    #
    # The activation-failure branches of ``_apply_pre_push_quality_gate_inactive``
    # compare candidate entries against the bare literal
    # ``'pre-push-quality-gate'``. Before boundary normalization landed, a
    # ``default:pre-push-quality-gate`` candidate would silently bypass the
    # filter — the membership check ``'pre-push-quality-gate' in candidates``
    # returned ``False`` even with the prefixed entry in the list, so the gate
    # survived the manifest with the prefix attached.
    #
    # Boundary normalization in ``cmd_compose`` strips the ``default:`` prefix
    # at intake, so the pre-filter sees bare names regardless of how the
    # caller spelled the candidate IDs. These regressions exercise all three
    # activation-failure branches with a fully prefixed input list and assert
    # the gate is dropped + the manifest output is bare.
    # =========================================================================

    def test_omit_when_activation_globs_empty_with_prefixed_input(self, plan_context):
        """Regression — activation_globs=[] drops prefixed pre-push-quality-gate."""
        plan_id = 'pp-prefixed-globs-empty'
        prefixed = [
            'default:pre-push-quality-gate',
            'default:push',
            'default:create-pr',
            'default:archive-plan',
        ]
        _write_marshal(plan_context.fixture_dir, activation_globs=[])
        _stub_footprint(['marketplace/bundles/plan-marshall/skills/foo.py'])

        captured, original = self._capture_decision_log()
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=4,
                    phase_6_steps=','.join(prefixed),
                )
            )
        finally:
            _mem._emit_decision_log = original

        assert result is not None and result['status'] == 'success'
        assert result['pre_push_quality_gate_omitted'] is True

        manifest = read_manifest(plan_id)
        assert manifest is not None
        steps = manifest['phase_6']['steps']

        # Gate dropped despite prefixed input — boundary normalization
        # made the membership check work.
        assert 'pre-push-quality-gate' not in steps
        assert 'default:pre-push-quality-gate' not in steps

        # Output is fully bare.
        assert not any(s.startswith('default:') for s in steps), (
            f'phase_6 leaked `default:`-prefixed entry: {steps!r}'
        )

        # Other steps from the input survive as bare strings.
        for kept in ('push', 'create-pr', 'archive-plan'):
            assert kept in steps

        # Omission line emitted exactly once.
        assert len(self._omit_entries(captured)) == 1

    def test_omit_when_modified_files_empty_with_prefixed_input(self, plan_context):
        """Regression — empty live footprint drops prefixed pre-push-quality-gate."""
        plan_id = 'pp-prefixed-mod-empty'
        prefixed = [
            'default:pre-push-quality-gate',
            'default:push',
            'default:create-pr',
            'default:archive-plan',
        ]
        _write_marshal(plan_context.fixture_dir, activation_globs=['marketplace/bundles/**/*.py'])
        _stub_footprint([])  # empty footprint

        captured, original = self._capture_decision_log()
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=4,
                    phase_6_steps=','.join(prefixed),
                )
            )
        finally:
            _mem._emit_decision_log = original

        assert result is not None and result['pre_push_quality_gate_omitted'] is True

        manifest = read_manifest(plan_id)
        assert manifest is not None
        steps = manifest['phase_6']['steps']

        assert 'pre-push-quality-gate' not in steps
        assert 'default:pre-push-quality-gate' not in steps
        assert not any(s.startswith('default:') for s in steps)

        assert len(self._omit_entries(captured)) == 1

    def test_omit_when_no_glob_matches_with_prefixed_input(self, plan_context):
        """Regression — non-matching modified_files drops prefixed pre-push-quality-gate."""
        plan_id = 'pp-prefixed-no-match'
        prefixed = [
            'default:pre-push-quality-gate',
            'default:push',
            'default:create-pr',
            'default:archive-plan',
        ]
        _write_marshal(plan_context.fixture_dir, activation_globs=['marketplace/bundles/**/*.py'])
        # All paths fall outside the configured glob.
        _stub_footprint(['doc/readme.md', 'CHANGELOG.txt'])

        captured, original = self._capture_decision_log()
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=2,
                    phase_6_steps=','.join(prefixed),
                )
            )
        finally:
            _mem._emit_decision_log = original

        assert result is not None and result['pre_push_quality_gate_omitted'] is True

        manifest = read_manifest(plan_id)
        assert manifest is not None
        steps = manifest['phase_6']['steps']

        assert 'pre-push-quality-gate' not in steps
        assert 'default:pre-push-quality-gate' not in steps
        assert not any(s.startswith('default:') for s in steps)

        assert len(self._omit_entries(captured)) == 1


# =============================================================================
# Pre-Filter: simplify_inactive (finalize-step-simplify gate)
#
# finalize-step-simplify is a candidate by default (it sits in
# DEFAULT_PHASE_6_STEPS). The simplify_inactive pre-filter DROPS it unless
# BOTH change_type ∈ {feature, bug_fix, tech_debt, enhancement}
# AND affected_files_count > 0.
# These tests enforce the merged plan's never-checked criterion: a
# code-touching plan composes the step into phase_6.steps; a docs-only /
# zero-affected-files plan does NOT; and the drop-only decision-log line fires
# only on the dropped branch.
#
# See standards/decision-rules.md § Pre-Filter: simplify_inactive.
# =============================================================================


@pytest.mark.parametrize(
    'change_type,affected_files_count,expect_present,expect_omitted',
    [
        # Gate passes: all four code-touching change types with files > 0.
        ('feature', 5, True, False),
        ('bug_fix', 1, True, False),
        ('tech_debt', 3, True, False),
        ('enhancement', 5, True, False),
        # Gate fails on change_type: not a code-touching type.
        ('analysis', 5, False, True),
        ('verification', 5, False, True),
        # Gate fails on affected_files_count == 0 (even for a code-touching type).
        ('feature', 0, False, True),
        ('bug_fix', 0, False, True),
        ('enhancement', 0, False, True),
    ],
)
def test_simplify_inactive_gate(
    plan_context, change_type, affected_files_count, expect_present, expect_omitted
):
    """finalize-step-simplify lands only when change_type ∈ {feature, bug_fix, tech_debt, enhancement} AND files > 0."""
    slug = f'{change_type}-{affected_files_count}'.replace('_', '-')
    plan_id = f'matrix-simplify-{slug}'
    # Use a non-surgical, code-shaped scope so the surgical Row 5 path
    # doesn't intersect-narrow phase_6.steps and confuse the assertion.
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type=change_type,
            scope_estimate='multi_module',
            affected_files_count=affected_files_count,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['simplify_omitted'] is expect_omitted
    manifest = read_manifest(plan_id)
    assert manifest is not None
    if expect_present:
        assert 'finalize-step-simplify' in manifest['phase_6']['steps']
    else:
        assert 'finalize-step-simplify' not in manifest['phase_6']['steps']


def test_simplify_inactive_noop_when_step_absent_from_candidates(plan_context):
    """When finalize-step-simplify is not a candidate, the pre-filter is a no-op even on a failing gate."""
    candidates_without_simplify = [s for s in DEFAULT_PHASE_6_STEPS if s != 'finalize-step-simplify']
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-simplify-absent',
            change_type='analysis',  # gate would fail
            scope_estimate='multi_module',
            affected_files_count=0,  # gate would fail
            phase_6_steps=','.join(candidates_without_simplify),
        )
    )
    assert result is not None and result['status'] == 'success'
    # No-op: the step was never present, so the pre-filter did not "fire".
    assert result['simplify_omitted'] is False
    manifest = read_manifest('matrix-simplify-absent')
    assert manifest is not None
    assert 'finalize-step-simplify' not in manifest['phase_6']['steps']


def test_simplify_inactive_emits_decision_log_only_on_drop(plan_context):
    """The drop-only decision-log line fires exactly once on the dropped branch and not on the kept branch."""
    captured: list[tuple[str, str]] = []
    original_emit = _mem._emit_decision_log

    def _capture(plan_id, message):
        captured.append((plan_id, message))

    _mem._emit_decision_log = _capture
    try:
        # Dropped branch: analysis change_type fails the gate.
        cmd_compose(
            _compose_ns(
                plan_id='matrix-simplify-drop',
                change_type='analysis',
                scope_estimate='multi_module',
                affected_files_count=3,
            )
        )
    finally:
        _mem._emit_decision_log = original_emit

    drop_entries = [(pid, msg) for pid, msg in captured if 'finalize-step-simplify omitted' in msg]
    assert len(drop_entries) == 1, f'expected one simplify omission entry, got {captured!r}'
    pid, msg = drop_entries[0]
    assert pid == 'matrix-simplify-drop'
    assert msg == (
        '(plan-marshall:manage-execution-manifest:compose) finalize-step-simplify omitted — '
        'change_type=analysis affected_files_count=3'
    )


def test_simplify_inactive_no_decision_log_on_kept_branch(plan_context):
    """No simplify-omission log fires when the gate passes (step retained)."""
    captured: list[tuple[str, str]] = []
    original_emit = _mem._emit_decision_log

    def _capture(plan_id, message):
        captured.append((plan_id, message))

    _mem._emit_decision_log = _capture
    try:
        cmd_compose(
            _compose_ns(
                plan_id='matrix-simplify-kept',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=4,
            )
        )
    finally:
        _mem._emit_decision_log = original_emit

    drop_entries = [(pid, msg) for pid, msg in captured if 'finalize-step-simplify omitted' in msg]
    assert drop_entries == []


# =============================================================================
# Pre-Filter: security_audit_inactive (finalize-step-security-audit gate)
#
# finalize-step-security-audit is a candidate by default (it sits in
# DEFAULT_PHASE_6_STEPS). The security_audit_inactive pre-filter is the symmetric
# peer of simplify_inactive — it DROPS the step unless BOTH
# change_type ∈ {feature, bug_fix, tech_debt, enhancement} AND
# affected_files_count > 0. The
# proactive security sweep has no change surface to audit on a pure-analysis /
# verification plan or a zero-files plan. These tests enforce: a code-touching
# plan composes the step into phase_6.steps; a docs-only / zero-affected-files
# plan does NOT; and the drop-only decision-log line fires only on the dropped
# branch.
#
# See standards/decision-rules.md § Pre-Filter: security_audit_inactive.
# =============================================================================


@pytest.mark.parametrize(
    'change_type,affected_files_count,expect_present,expect_omitted',
    [
        # Gate passes: all four code-touching change types with files > 0.
        ('feature', 5, True, False),
        ('bug_fix', 1, True, False),
        ('tech_debt', 3, True, False),
        ('enhancement', 5, True, False),
        # Gate fails on change_type: not a code-touching type.
        ('analysis', 5, False, True),
        ('verification', 5, False, True),
        # Gate fails on affected_files_count == 0 (even for a code-touching type).
        ('feature', 0, False, True),
        ('bug_fix', 0, False, True),
        ('enhancement', 0, False, True),
    ],
)
def test_security_audit_inactive_gate(
    plan_context, change_type, affected_files_count, expect_present, expect_omitted
):
    """finalize-step-security-audit lands only when change_type ∈ {feature, bug_fix, tech_debt, enhancement} AND files > 0."""
    slug = f'{change_type}-{affected_files_count}'.replace('_', '-')
    plan_id = f'matrix-secaudit-{slug}'
    # Use a non-surgical, code-shaped scope so the surgical Row 5 path
    # doesn't intersect-narrow phase_6.steps and confuse the assertion.
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type=change_type,
            scope_estimate='multi_module',
            affected_files_count=affected_files_count,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['security_audit_omitted'] is expect_omitted
    manifest = read_manifest(plan_id)
    assert manifest is not None
    if expect_present:
        assert 'finalize-step-security-audit' in manifest['phase_6']['steps']
    else:
        assert 'finalize-step-security-audit' not in manifest['phase_6']['steps']


def test_security_audit_inactive_noop_when_step_absent_from_candidates(plan_context):
    """When finalize-step-security-audit is not a candidate, the pre-filter is a no-op even on a failing gate."""
    candidates_without_secaudit = [
        s for s in DEFAULT_PHASE_6_STEPS if s != 'finalize-step-security-audit'
    ]
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-secaudit-absent',
            change_type='analysis',  # gate would fail
            scope_estimate='multi_module',
            affected_files_count=0,  # gate would fail
            phase_6_steps=','.join(candidates_without_secaudit),
        )
    )
    assert result is not None and result['status'] == 'success'
    # No-op: the step was never present, so the pre-filter did not "fire".
    assert result['security_audit_omitted'] is False
    manifest = read_manifest('matrix-secaudit-absent')
    assert manifest is not None
    assert 'finalize-step-security-audit' not in manifest['phase_6']['steps']


def test_security_audit_inactive_emits_decision_log_only_on_drop(plan_context):
    """The drop-only decision-log line fires exactly once on the dropped branch."""
    captured: list[tuple[str, str]] = []
    original_emit = _mem._emit_decision_log

    def _capture(plan_id, message):
        captured.append((plan_id, message))

    _mem._emit_decision_log = _capture
    try:
        # Dropped branch: analysis change_type fails the gate.
        cmd_compose(
            _compose_ns(
                plan_id='matrix-secaudit-drop',
                change_type='analysis',
                scope_estimate='multi_module',
                affected_files_count=3,
            )
        )
    finally:
        _mem._emit_decision_log = original_emit

    drop_entries = [
        (pid, msg) for pid, msg in captured if 'finalize-step-security-audit omitted' in msg
    ]
    assert len(drop_entries) == 1, f'expected one security-audit omission entry, got {captured!r}'
    pid, msg = drop_entries[0]
    assert pid == 'matrix-secaudit-drop'
    assert msg == (
        '(plan-marshall:manage-execution-manifest:compose) finalize-step-security-audit omitted — '
        'change_type=analysis affected_files_count=3'
    )


def test_security_audit_inactive_no_decision_log_on_kept_branch(plan_context):
    """No security-audit-omission log fires when the gate passes (step retained)."""
    captured: list[tuple[str, str]] = []
    original_emit = _mem._emit_decision_log

    def _capture(plan_id, message):
        captured.append((plan_id, message))

    _mem._emit_decision_log = _capture
    try:
        cmd_compose(
            _compose_ns(
                plan_id='matrix-secaudit-kept',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=4,
            )
        )
    finally:
        _mem._emit_decision_log = original_emit

    drop_entries = [
        (pid, msg) for pid, msg in captured if 'finalize-step-security-audit omitted' in msg
    ]
    assert drop_entries == []


def _write_marshal_with_ci(fixture_dir: Path, *, provider: str) -> None:
    """Write a marshal.json whose ``providers[]`` resolves to the given CI provider.

    ``_read_ci_provider`` maps the ``providers[]`` entry whose ``category == 'ci'``
    to a short identifier (``plan-marshall:workflow-integration-github`` ->
    ``github``, ``plan-marshall:workflow-integration-gitlab`` -> ``gitlab``). Tests
    for the github/gitlab branch must materialize this entry; the no-CI baseline
    simply omits ``providers[]``.
    """
    skill_name = f'plan-marshall:workflow-integration-{provider}'
    marshal_path = fixture_dir / 'marshal.json'
    data: dict = {
        'providers': [{'skill_name': skill_name, 'category': 'ci'}],
        'plan': {'phase-6-finalize': {}},
    }
    marshal_path.write_text(json.dumps(data), encoding='utf-8')


# =============================================================================
# _read_ci_provider — direct regression coverage for the dissolved ci block
# (D3 — ci.provider read-path removal)
#
# The legacy ``ci.provider`` short-identifier read-path is gone. The provider
# is now resolved exclusively from the ``providers[]`` entry whose
# ``category == 'ci'``. These tests pin that contract directly against
# ``_read_ci_provider`` (rather than only end-to-end through the guard).
# =============================================================================


def test_read_ci_provider_resolves_github_from_providers_no_ci_block(plan_context):
    """``providers[]`` github entry resolves to 'github' with NO ci block present."""
    _write_marshal_with_ci(plan_context.fixture_dir, provider='github')
    assert _mem._read_ci_provider() == 'github'


def test_read_ci_provider_resolves_gitlab_from_providers_no_ci_block(plan_context):
    """``providers[]`` gitlab entry resolves to 'gitlab' with NO ci block present."""
    _write_marshal_with_ci(plan_context.fixture_dir, provider='gitlab')
    assert _mem._read_ci_provider() == 'gitlab'


def test_read_ci_provider_ignores_legacy_ci_provider_block(plan_context):
    """A stale ``ci.provider`` block alone resolves to None — the read-path is removed.

    Before D3, ``ci.provider`` was a first-match-wins source. After dissolution
    the composer ignores the ``ci`` block entirely; only ``providers[]`` is
    consulted. A marshal.json carrying ONLY the legacy block must resolve to
    None so a stale field can never silently re-activate the guard.
    """
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps({'ci': {'provider': 'github'}}), encoding='utf-8')
    assert _mem._read_ci_provider() is None


def test_read_ci_provider_returns_none_when_no_providers(plan_context):
    """No ``providers[]`` and no ci block -> None (the no-CI baseline)."""
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps({'plan': {'phase-6-finalize': {}}}), encoding='utf-8')
    assert _mem._read_ci_provider() is None


# =============================================================================
# Compose-time frontmatter-order sort (lesson 2026-04-28-13-002)
#
# ``automatic-review`` (frontmatter order 30) must land before every
# plan-mutating step (``archive-plan``, ``record-metrics``, ``branch-cleanup``,
# ``plan-marshall:plan-retrospective``). The ``_sort_steps_by_frontmatter_order``
# choke-point is the SOLE ordering authority (the bot-enforcement placement
# validator was removed): a misordered candidate list is sorted back into
# frontmatter ``order:`` sequence, so ``automatic-review`` lands strictly before
# every plan-mutating anchor and compose succeeds (``status='success'``).
#
# Construction: we pass an explicit ``--phase-6-steps`` candidate list where
# ``automatic-review`` is already present in the wrong position; Row 7 (default)
# preserves the candidate ordering verbatim, so the misplacement reaches the sort
# choke-point, which reorders it ahead of the anchor.
# =============================================================================


class TestAutomatedReviewPlacement:
    """Compose-time frontmatter-order sort places ``automatic-review`` before plan-mutating anchors."""

    @staticmethod
    def _candidates_with_review_after(anchor: str) -> str:
        """Build a phase_6 candidate CSV where ``automatic-review`` follows ``anchor``.

        The candidate list mirrors the canonical ordering for the steps that
        always remain (push, create-pr, lessons-capture) so the manifest
        is otherwise plausible; only the ``automatic-review`` / ``anchor`` pair
        is deliberately misordered. The anchor is inserted before
        ``automatic-review`` so the sort choke-point must reorder it back ahead
        of the parametrized anchor.
        """
        return ','.join(['push', 'create-pr', 'lessons-capture', anchor, 'automatic-review'])

    def test_compose_sorts_automated_review_before_archive_plan(self, plan_context):
        """Misplaced ``automatic-review`` after ``archive-plan`` → sorted before it, compose succeeds."""
        plan_id = 'placement-archive-plan'
        # GitHub provider — the misplacement reaches the sort choke-point, which
        # reorders automatic-review ahead of the anchor.
        _write_marshal_with_ci(plan_context.fixture_dir, provider='github')

        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=5,
                phase_6_steps=self._candidates_with_review_after('archive-plan'),
            )
        )

        assert result is not None
        # The sort choke-point corrects the misplacement, so compose succeeds.
        assert result['status'] == 'success', f'expected success status, got {result!r}'
        # The persisted manifest sorts ``automatic-review`` strictly before the
        # ``archive-plan`` anchor.
        manifest = read_manifest(plan_id)
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        assert 'automatic-review' in steps
        assert 'archive-plan' in steps
        assert steps.index('automatic-review') < steps.index('archive-plan'), (
            f'automatic-review must sort before archive-plan: {steps!r}'
        )

    @pytest.mark.parametrize(
        'anchor',
        ['record-metrics', 'branch-cleanup', 'plan-marshall:plan-retrospective'],
    )
    def test_compose_sorts_automated_review_before_other_plan_mutating_steps(self, plan_context, anchor: str):
        """Misplaced ``automatic-review`` after each remaining anchor → sorted before it, compose succeeds.

        Parametrized over the three plan-mutating anchors NOT covered by the
        ``archive-plan`` test above. Together these cover the full plan-mutating
        anchor set the sort must place ``automatic-review`` ahead of:
        ``archive-plan``, ``record-metrics``, ``branch-cleanup``,
        ``plan-marshall:plan-retrospective``.
        """
        # Plan IDs must be kebab-case; the colon-prefixed retrospective anchor
        # would otherwise leak a ``:`` into the directory name.
        anchor_slug = anchor.replace(':', '-').replace('plan-marshall-', 'pm-')
        plan_id = f'placement-{anchor_slug}'
        _write_marshal_with_ci(plan_context.fixture_dir, provider='github')

        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=5,
                phase_6_steps=self._candidates_with_review_after(anchor),
            )
        )

        assert result is not None
        # The sort choke-point corrects the misplacement, so compose succeeds
        # for every anchor.
        assert result['status'] == 'success', f'expected success status for anchor={anchor!r}, got {result!r}'
        # The persisted manifest sorts ``automatic-review`` strictly before the
        # parametrized anchor.
        manifest = read_manifest(plan_id)
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        assert 'automatic-review' in steps
        assert anchor in steps
        assert steps.index('automatic-review') < steps.index(anchor), (
            f'automatic-review must sort before anchor={anchor!r}: {steps!r}'
        )


# =============================================================================
# Default phase-6 ordering — finalize-step-simplify precedes the push barrier
#
# The dispatcher's commit instrumentation commits each ``mutates_source: true``
# step's output before advancing, so the correct ordering (simplify before the
# pure ``push`` barrier) falls out of plain ``order:`` values with no special
# placement invariant. This test pins the default ordering so a regression that
# swaps the two in ``DEFAULT_PHASE_6_STEPS`` is caught.
# =============================================================================


class TestDefaultPhase6Ordering:
    """``finalize-step-simplify`` composes at an index earlier than ``push``."""

    def test_default_compose_places_simplify_before_push(self, plan_context):
        # A default code-shaped feature compose (change_type=feature, files>0, so
        # simplify_inactive keeps the step) MUST emit ``finalize-step-simplify`` at
        # an earlier index than the ``push`` barrier.
        result = cmd_compose(_compose_ns(plan_id='default-order-simplify-before-push'))

        assert result is not None
        assert result['status'] == 'success', f'expected success, got {result!r}'

        manifest = read_manifest('default-order-simplify-before-push')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # Both steps survive the default feature compose.
        assert 'push' in steps
        assert 'finalize-step-simplify' in steps
        # The ordering invariant: simplify precedes the push barrier.
        assert steps.index('finalize-step-simplify') < steps.index('push')


# =============================================================================
# marshal.json source-of-truth tests
#
# The composer prefers ``plan.phase-{5,6}-{execute,finalize}.steps`` from
# marshal.json over the agent-supplied ``--phase-{5,6}-steps`` CSV. This
# defends against agent-built CSVs that historically stripped ``project:`` and
# ``bundle:skill`` prefixes (producing manifests with bare names the
# phase-6-finalize dispatcher then mis-routed as built-in steps).
# =============================================================================


def _write_full_marshal(
    fixture_dir: Path,
    *,
    phase_6_steps: list[str],
    phase_5_steps: list[str] | None = None,
) -> None:
    """Write a marshal.json with the given phase-5/6 step lists.

    The phase-5 list is optional — when omitted, only ``phase-6-finalize.steps``
    is populated. The id lists are converted to the id-keyed map schema
    (``{step_id: {}, ...}`` — key insertion order is the execution order, empty
    param objects), matching the live on-disk shape ``_read_marshal_phase_steps``
    reads. Prefixes are preserved. No CI provider is declared for these fixtures.
    """
    marshal_path = fixture_dir / 'marshal.json'
    plan_block: dict = {
        'phase-6-finalize': {'steps': {step_id: {} for step_id in phase_6_steps}}
    }
    if phase_5_steps is not None:
        # phase-5-execute stores its verification step map under the
        # ``verification_steps`` key (the keyed-map schema);
        # ``_read_marshal_phase_steps`` reads ``verification_steps`` for the
        # phase-5 block. Writing the keyed map here matches the live composer
        # contract.
        plan_block['phase-5-execute'] = {
            'verification_steps': {step_id: {} for step_id in phase_5_steps}
        }
    data = {'plan': plan_block}
    marshal_path.write_text(json.dumps(data), encoding='utf-8')


def test_marshal_json_preferred_over_csv_preserves_project_prefixes(plan_context):
    """When marshal.json declares project: steps, the manifest preserves them even if CSV strips them.

    Regression for the lesson-2026-05-15-21-002 finalize abort: the phase-4-plan
    agent built a CSV with prefixes stripped, producing a manifest of bare names
    the dispatcher then mis-routed as built-in default: steps. The composer now
    treats marshal.json as the source of truth — agent CSV is fallback only.
    """
    full_phase_6 = [
        'default:push',
        'project:finalize-step-deploy-target',
        'project:finalize-step-sync-plugin-cache',
        'default:create-pr',
        'plan-marshall:automatic-review',
        'default:lessons-capture',
        'project:finalize-step-plugin-doctor',
        'default:branch-cleanup',
        'default:record-metrics',
        'plan-marshall:plan-retrospective',
        'default:archive-plan',
    ]
    # The CSV the agent built (prefixes stripped). marshal.json should win.
    bad_csv = ','.join(
        [
            'push',
            'deploy-target',
            'sync-plugin-cache',
            'create-pr',
            'automatic-review',
            'lessons-capture',
            'plugin-doctor',
            'branch-cleanup',
            'record-metrics',
            'plan-retrospective',
            'archive-plan',
        ]
    )
    _write_full_marshal(plan_context.fixture_dir, phase_6_steps=full_phase_6)
    result = cmd_compose(
        _compose_ns(
            plan_id='marshal-source-of-truth',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=11,
            phase_6_steps=bad_csv,  # noise — should be ignored
        )
    )
    assert result is not None and result['status'] == 'success'
    manifest = read_manifest('marshal-source-of-truth')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    # Prefixes from marshal.json are preserved (except `default:` which
    # is stripped at the boundary normalization step).
    assert 'project:finalize-step-deploy-target' in steps
    assert 'project:finalize-step-sync-plugin-cache' in steps
    assert 'project:finalize-step-plugin-doctor' in steps
    assert 'plan-marshall:plan-retrospective' in steps
    # Bare names from the CSV must not appear in the manifest output.
    assert 'deploy-target' not in steps
    assert 'sync-plugin-cache' not in steps
    assert 'plugin-doctor' not in steps
    assert 'plan-retrospective' not in steps
    # `default:` prefixes ARE stripped by boundary normalization.
    assert 'push' in steps
    assert 'default:push' not in steps


def test_csv_fallback_when_marshal_json_missing(plan_context):
    """Without marshal.json, the composer falls back to the CSV input verbatim.

    Backward-compat: existing tests that don't stage a marshal.json continue
    to drive composition via the ``--phase-{5,6}-steps`` flag.
    """
    # No marshal.json is written.
    result = cmd_compose(
        _compose_ns(
            plan_id='csv-fallback',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=5,
            phase_6_steps=','.join(DEFAULT_PHASE_6_STEPS),
        )
    )
    assert result is not None and result['status'] == 'success'
    manifest = read_manifest('csv-fallback')
    assert manifest is not None
    # All DEFAULT_PHASE_6_STEPS survive (no marshal.json to override).
    steps = manifest['phase_6']['steps']
    for expected in ('push', 'create-pr', 'lessons-capture', 'archive-plan'):
        assert expected in steps


def test_compose_snapshots_resolved_step_params_from_keyed_map(plan_context):
    """compose snapshots each selected step's resolved params from the marshal keyed map.

    Seeds a marshal.json whose phase-6-finalize steps map carries nested params
    on default:branch-cleanup and default:sonar-roundtrip. The composer must
    snapshot those resolved params into body.phase_6.step_params, keyed by the
    bare in-manifest step id (the default: prefix is stripped at the boundary),
    for every selected step. Steps with no marshal-side params snapshot as {}.
    """
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    phase_6_map = {
        'default:push': {},
        'default:create-pr': {},
        'plan-marshall:automatic-review': {'review_bot_buffer_seconds': 240},
        'default:sonar-roundtrip': {
            'touched_file_cleanup': 'touched_files_zero',
            'do_transition': True,
            'ce_wait_timeout_seconds': 720,
        },
        'default:lessons-capture': {},
        'default:branch-cleanup': {
            'pr_merge_strategy': 'rebase',
            'final_merge_without_asking': True,
            'auto_rebase_threshold': 'no_overlap_only',
        },
        'default:record-metrics': {},
        'default:archive-plan': {},
    }
    data = {'plan': {'phase-6-finalize': {'steps': phase_6_map}}}
    marshal_path.write_text(json.dumps(data), encoding='utf-8')

    result = cmd_compose(
        _compose_ns(
            plan_id='snapshot-params',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=11,
        )
    )
    assert result is not None and result['status'] == 'success'

    manifest = read_manifest('snapshot-params')
    assert manifest is not None
    step_params = manifest['phase_6']['step_params']
    # the snapshot is keyed by the bare in-manifest step id (default: stripped)
    # and carries the resolved nested params for selected steps
    assert step_params['branch-cleanup'] == {
        'pr_merge_strategy': 'rebase',
        'final_merge_without_asking': True,
        'auto_rebase_threshold': 'no_overlap_only',
    }
    assert step_params['sonar-roundtrip'] == {
        'touched_file_cleanup': 'touched_files_zero',
        'do_transition': True,
        'ce_wait_timeout_seconds': 720,
    }
    assert step_params['automatic-review'] == {'review_bot_buffer_seconds': 240}
    # an ownerless selected step snapshots as the empty param object
    assert step_params['push'] == {}
    # every in-manifest step has a snapshot entry
    assert set(step_params.keys()) == set(manifest['phase_6']['steps'])


# =============================================================================
# Keyed-map marshal.json read-through
#
# ``_read_marshal_phase_step_map`` / ``_read_marshal_phase_steps`` read the
# canonical keyed-map on-disk form, normalizing each value to the internal
# id-keyed map. These tests feed the keyed map through the composer end-to-end
# and assert the manifest snapshots the resolved params and the composed step
# sets. (The manifest's own ``step_params`` snapshot is an id-keyed dict; the
# manifest's ``steps`` / ``verification_steps`` are bare-name id lists.)
# =============================================================================


def test_compose_reads_keyed_map_marshal_preserves_prefixes(plan_context):
    """A keyed-map marshal.json composes the declared step set, preserving project: prefixes.

    The keyed map is the sole on-disk form; the composer reads it and preserves
    the ``project:`` prefix (only ``default:`` is stripped at intake).
    """
    phase_6 = [
        'default:push',
        'project:finalize-step-deploy-target',
        'default:create-pr',
        'default:lessons-capture',
        'default:branch-cleanup',
        'default:record-metrics',
        'default:archive-plan',
    ]
    phase_5 = ['verify:quality-gate', 'verify:module-tests']

    _write_full_marshal(
        plan_context.fixture_dir, phase_6_steps=phase_6, phase_5_steps=phase_5
    )
    cmd_compose(
        _compose_ns(
            plan_id='keyed-map-marshal',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=11,
        )
    )
    keyed_manifest = read_manifest('keyed-map-marshal')
    assert keyed_manifest is not None

    # the project: prefix survives the keyed-map read (only default: is stripped)
    assert 'project:finalize-step-deploy-target' in keyed_manifest['phase_6']['steps']
    # the phase-5 verification step set is composed from the keyed map
    assert keyed_manifest['phase_5']['verification_steps'] == phase_5


def test_compose_snapshots_step_params_from_keyed_map(plan_context):
    """compose snapshots resolved params from a keyed-map marshal.json.

    Seeds a marshal.json whose phase-6-finalize steps are the keyed-map form with
    param-bearing values on branch-cleanup and sonar-roundtrip. The composer
    snapshots the resolved params into body.phase_6.step_params (keyed by the
    bare in-manifest step id). Config-less steps snapshot as {}.
    """
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    phase_6_map = {
        'default:push': {},
        'default:create-pr': {},
        'plan-marshall:automatic-review': {'review_bot_buffer_seconds': 240},
        'default:sonar-roundtrip': {
            'touched_file_cleanup': 'touched_files_zero',
            'do_transition': True,
            'ce_wait_timeout_seconds': 720,
        },
        'default:lessons-capture': {},
        'default:branch-cleanup': {
            'pr_merge_strategy': 'rebase',
            'final_merge_without_asking': True,
            'auto_rebase_threshold': 'no_overlap_only',
        },
        'default:record-metrics': {},
        'default:archive-plan': {},
    }
    data = {'plan': {'phase-6-finalize': {'steps': phase_6_map}}}
    marshal_path.write_text(json.dumps(data), encoding='utf-8')

    result = cmd_compose(
        _compose_ns(
            plan_id='snapshot-params-keyed',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=11,
        )
    )
    assert result is not None and result['status'] == 'success'

    manifest = read_manifest('snapshot-params-keyed')
    assert manifest is not None
    step_params = manifest['phase_6']['step_params']
    # the snapshot is keyed by the bare in-manifest step id (default: stripped)
    assert step_params['branch-cleanup'] == {
        'pr_merge_strategy': 'rebase',
        'final_merge_without_asking': True,
        'auto_rebase_threshold': 'no_overlap_only',
    }
    assert step_params['sonar-roundtrip'] == {
        'touched_file_cleanup': 'touched_files_zero',
        'do_transition': True,
        'ce_wait_timeout_seconds': 720,
    }
    assert step_params['automatic-review'] == {'review_bot_buffer_seconds': 240}
    # a config-less selected step snapshots as the empty param object
    assert step_params['push'] == {}
    # every in-manifest step has a snapshot entry
    assert set(step_params.keys()) == set(manifest['phase_6']['steps'])


def test_compose_reads_keyed_map_phase_5_verification_steps(plan_context):
    """The keyed-map read-through applies to phase-5 verification_steps as well.

    Mirrors the phase-6 read-through for the phase-5 verification_steps key —
    marshal.json is the source of truth over the agent CSV.
    """
    phase_5 = ['verify:quality-gate', 'verify:module-tests', 'verify:coverage']
    _write_full_marshal(
        plan_context.fixture_dir,
        phase_6_steps=list(DEFAULT_PHASE_6_STEPS),
        phase_5_steps=phase_5,
    )
    cmd_compose(
        _compose_ns(
            plan_id='keyed-map-phase-5',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
            phase_5_steps='WRONG,STUFF',  # noise — marshal.json keyed map should win
        )
    )
    manifest = read_manifest('keyed-map-phase-5')
    assert manifest is not None
    # marshal.json keyed map wins over the agent CSV
    assert manifest['phase_5']['verification_steps'] == phase_5


# =============================================================================
# Role-loader and role-based intersection (deliverable 2)
#
# The composer derives a phase-5 candidate step's ``role:`` purely in-code from
# the trailing ``{canonical}`` segment of its ``verify:{canonical}`` step ID via
# ``_role_of`` (the ``_CANONICAL_TO_ROLE`` table) and uses the role for
# intersection in Rows 2, 3, 4, and 5 of the decision matrix. The tests below cover:
#
# (a) role-loader correctness for each canonical-verify step ID (and the
#     negative cases: external steps, unknown canonicals, retired fixed-name IDs)
# (b) Row 5 intersection produces the expected non-empty list when project
#     candidates carry the canonical-verify step IDs (e.g., ``verify:quality-gate``,
#     ``verify:module-tests``)
# (c) decision-log line shape (the canonical Rule N fired line) is byte-
#     identical to its pre-refactor form for at least one Row 5 fixture
# =============================================================================


class TestRoleLoader:
    """``_role_of`` resolves a phase-5 canonical-verify step ID to its derived role.

    Resolution is purely in-code via the ``_CANONICAL_TO_ROLE`` table, keyed on
    the trailing ``{canonical}`` segment of a ``verify:{canonical}`` step ID — no
    per-step role-file is read. The legacy fixed-name IDs (``quality_check`` /
    ``build_verify`` / ``coverage_check``) are gone and now resolve to None.
    """

    def test_verify_quality_gate_resolves_to_quality_gate_role(self):
        cache: dict[str, str | None] = {}
        assert _role_of('verify:quality-gate', cache) == 'quality-gate'

    def test_verify_module_tests_resolves_to_module_tests_role(self):
        cache: dict[str, str | None] = {}
        assert _role_of('verify:module-tests', cache) == 'module-tests'

    def test_verify_coverage_resolves_to_coverage_role(self):
        cache: dict[str, str | None] = {}
        assert _role_of('verify:coverage', cache) == 'coverage'

    def test_default_prefix_is_stripped_during_resolution(self):
        """``default:verify:quality-gate`` resolves to the same role as the bare form."""
        cache: dict[str, str | None] = {}
        assert _role_of('default:verify:quality-gate', cache) == 'quality-gate'

    def test_legacy_fixed_name_id_resolves_to_none(self):
        """The retired fixed-name IDs no longer resolve to a role."""
        cache: dict[str, str | None] = {}
        assert _role_of('quality_check', cache) is None
        assert _role_of('build_verify', cache) is None
        assert _role_of('coverage_check', cache) is None

    def test_external_step_resolves_to_none(self):
        """``project:`` / ``bundle:skill`` candidates have no derived role."""
        cache: dict[str, str | None] = {}
        assert _role_of('project:finalize-step-plugin-doctor', cache) is None
        assert _role_of('my-bundle:my-verify-step', cache) is None

    def test_unknown_canonical_resolves_to_none(self):
        """A ``verify:{canonical}`` whose canonical is not in the table → None."""
        cache: dict[str, str | None] = {}
        assert _role_of('verify:does-not-exist', cache) is None

    def test_cache_returns_same_value_on_second_lookup(self):
        """The per-compose cache short-circuits the second call for the same step."""
        cache: dict[str, str | None] = {}
        first = _role_of('verify:quality-gate', cache)
        # Mutate cache to a sentinel — second call MUST observe the cached value,
        # not re-derive the role.
        cache['verify:quality-gate'] = 'mutated-sentinel'
        second = _role_of('verify:quality-gate', cache)
        assert first == 'quality-gate'
        assert second == 'mutated-sentinel'


class TestRoleBasedIntersection:
    """Rows 2, 4, and 5 intersect by ``role:`` rather than by literal step ID."""

    def test_row_5_surgical_bug_fix_with_built_in_candidates_produces_non_empty_phase_5(self, plan_context):
        """Row 5 + canonical-verify candidate IDs → both quality-gate and module-tests retained.

        Pins the regression: before this refactor the composer compared
        candidate IDs against literal {'quality-gate', 'module-tests'}, which
        never matched the step IDs callers actually pass. Role-based intersection
        derives each candidate's role from its ``verify:{canonical}`` segment and
        matches against `{quality-gate, module-tests}`.
        """
        result = cmd_compose(
            _compose_ns(
                plan_id='role-row-5-bug',
                change_type='bug_fix',
                scope_estimate='surgical',
                affected_files_count=1,
                phase_5_steps='verify:quality-gate,verify:module-tests',
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_bug_fix'
        manifest = read_manifest('role-row-5-bug')
        assert manifest is not None
        # Both candidates derive roles in {quality-gate, module-tests} →
        # both survive the intersection.
        assert manifest['phase_5']['verification_steps'] == ['verify:quality-gate', 'verify:module-tests']

    def test_row_5_surgical_tech_debt_with_prefixed_built_in_candidates_produces_non_empty_phase_5(self, plan_context):
        """Row 5 + ``default:``-prefixed canonical-verify IDs → boundary normalized + roles match.

        Exercises the joint contract of boundary normalization (the existing
        `canonicalize_step_key` pass at intake) and role derivation: prefixed
        candidates lose the prefix at cmd_compose intake, then role lookup
        derives the role from each bare ``verify:{canonical}`` segment.
        """
        result = cmd_compose(
            _compose_ns(
                plan_id='role-row-5-tech-prefixed',
                change_type='tech_debt',
                scope_estimate='surgical',
                affected_files_count=2,
                phase_5_steps='default:verify:quality-gate,default:verify:module-tests',
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
        manifest = read_manifest('role-row-5-tech-prefixed')
        assert manifest is not None
        # Boundary normalization strips `default:`; role intersection
        # then matches both bare step IDs.
        assert manifest['phase_5']['verification_steps'] == ['verify:quality-gate', 'verify:module-tests']

    def test_row_5_drops_coverage_role_from_phase_5(self, plan_context):
        """Row 5's role set is {quality-gate, module-tests} — coverage role is dropped."""
        result = cmd_compose(
            _compose_ns(
                plan_id='role-row-5-drop-coverage',
                change_type='bug_fix',
                scope_estimate='surgical',
                affected_files_count=1,
                phase_5_steps='verify:quality-gate,verify:module-tests,verify:coverage',
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_bug_fix'
        manifest = read_manifest('role-row-5-drop-coverage')
        assert manifest is not None
        assert manifest['phase_5']['verification_steps'] == ['verify:quality-gate', 'verify:module-tests']
        assert 'verify:coverage' not in manifest['phase_5']['verification_steps']

    def test_row_5_drops_external_step_without_role(self, plan_context):
        """External (project: / bundle:skill) candidates have no role → dropped by intersection."""
        result = cmd_compose(
            _compose_ns(
                plan_id='role-row-5-drop-external',
                change_type='bug_fix',
                scope_estimate='surgical',
                affected_files_count=1,
                phase_5_steps='verify:quality-gate,project:my-verify-step,verify:module-tests',
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_bug_fix'
        manifest = read_manifest('role-row-5-drop-external')
        assert manifest is not None
        # External step has no role → dropped; canonical-verify steps survive.
        assert manifest['phase_5']['verification_steps'] == ['verify:quality-gate', 'verify:module-tests']

    def test_row_4_tests_only_matches_only_module_tests_role(self, plan_context):
        """Row 4's role set is {module-tests} — only verify:module-tests (role: module-tests) survives."""
        result = cmd_compose(
            _compose_ns(
                plan_id='role-row-4',
                change_type='verification',
                scope_estimate='single_module',
                affected_files_count=4,
                phase_5_steps='verify:quality-gate,verify:module-tests,verify:coverage',
            )
        )
        assert result is not None and result['rule_fired'] == 'tests_only'
        manifest = read_manifest('role-row-4')
        assert manifest is not None
        assert manifest['phase_5']['verification_steps'] == ['verify:module-tests']

    def test_absent_module_tests_role_no_longer_diverts_the_matrix(self, plan_context):
        """A candidate set without a module-tests / coverage role takes the ordinary path.

        The retired ``docs_only`` row treated the ABSENCE of those roles as proof
        the plan was docs-only and emptied phase 5. The role intersection is a
        mechanism for selecting steps, never evidence about the footprint, so the
        row is gone: the same input now reaches the scope row and keeps its
        ``quality-gate`` candidate.
        """
        result = cmd_compose(
            _compose_ns(
                plan_id='role-row-3-docs',
                change_type='tech_debt',
                scope_estimate='surgical',
                affected_files_count=3,
                # Only verify:quality-gate (role: quality-gate) — no module-tests / coverage role.
                phase_5_steps='verify:quality-gate',
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
        manifest = read_manifest('role-row-3-docs')
        assert manifest is not None
        assert manifest['phase_5']['verification_steps'] == ['verify:quality-gate']

    def test_same_row_fires_whether_or_not_a_module_tests_role_is_present(self, plan_context):
        """Presence or absence of a module-tests role selects the SAME row now.

        Under the retired row these two inputs diverged (``docs_only`` vs the
        scope row) on nothing but the candidate list's composition. The rule key
        must now be identical — only the selected step list differs.
        """
        result = cmd_compose(
            _compose_ns(
                plan_id='role-row-3-skip',
                change_type='tech_debt',
                scope_estimate='surgical',
                affected_files_count=3,
                phase_5_steps='verify:quality-gate,verify:module-tests',
            )
        )
        assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
        manifest = read_manifest('role-row-3-skip')
        assert manifest is not None
        assert manifest['phase_5']['verification_steps'] == [
            'verify:quality-gate',
            'verify:module-tests',
        ]


class TestDecisionLogShapePreserved:
    """Decision-log line shape is byte-identical to its pre-refactor form."""

    def test_row_5_decision_log_message_matches_canonical_shape(self, plan_context):
        """``Rule {rule_key} fired — early_terminate=…, phase_5.verification_steps=…, phase_6.steps=…``."""
        captured: list[tuple[str, str]] = []
        original_emit = _mem._emit_decision_log
        original_log_decision = _mem._log_decision

        def _capture(plan_id_: str, message: str) -> None:
            captured.append((plan_id_, message))

        def _log_decision_capture(plan_id_, rule, body):
            phase_5 = body.get('phase_5', {})
            phase_6 = body.get('phase_6', {})
            p5_steps = phase_5.get('verification_steps', [])
            p6_steps = phase_6.get('steps', [])
            early = phase_5.get('early_terminate', False)
            message = (
                f'(plan-marshall:manage-execution-manifest:compose) Rule {rule} fired — '
                f'early_terminate={early}, phase_5.verification_steps={p5_steps}, '
                f'phase_6.steps={p6_steps}'
            )
            _capture(plan_id_, message)

        _mem._emit_decision_log = _capture
        _mem._log_decision = _log_decision_capture
        try:
            cmd_compose(
                _compose_ns(
                    plan_id='role-log-shape',
                    change_type='bug_fix',
                    scope_estimate='surgical',
                    affected_files_count=1,
                    phase_5_steps='verify:quality-gate,verify:module-tests',
                )
            )
        finally:
            _mem._emit_decision_log = original_emit
            _mem._log_decision = original_log_decision

        rule_messages = [msg for _, msg in captured if 'Rule surgical_bug_fix fired' in msg]
        assert len(rule_messages) == 1, f'expected exactly one Row 5 rule line, got: {captured!r}'
        msg = rule_messages[0]
        # Canonical shape segments.
        assert msg.startswith('(plan-marshall:manage-execution-manifest:compose) Rule surgical_bug_fix fired — ')
        assert 'early_terminate=False' in msg
        # phase_5.verification_steps reflects role-based intersection output.
        assert "phase_5.verification_steps=['verify:quality-gate', 'verify:module-tests']" in msg
        # phase_6.steps is present (we don't pin the full list here — other tests do).
        assert 'phase_6.steps=' in msg


def test_marshal_json_phase_5_steps_also_preferred(plan_context):
    """The marshal.json source-of-truth path applies to phase-5 steps as well as phase-6."""
    custom_phase_5 = ['quality-gate', 'module-tests']
    full_phase_6 = ['default:push', 'default:create-pr', 'plan-marshall:automatic-review', 'default:archive-plan']
    _write_full_marshal(
        plan_context.fixture_dir,
        phase_5_steps=custom_phase_5,
        phase_6_steps=full_phase_6,
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='marshal-phase-5',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=3,
            phase_5_steps='WRONG,STUFF',  # noise — marshal.json should win
        )
    )
    assert result is not None and result['status'] == 'success'
    manifest = read_manifest('marshal-phase-5')
    assert manifest is not None
    assert set(manifest['phase_5']['verification_steps']) == set(custom_phase_5)


# =============================================================================
# execution_tier Routing Tests (lesson 2026-05-27-20-003)
# =============================================================================
#
# The composer walks plan tasks and classifies each ``verification.commands``
# entry via ``architecture resolve``. The tests below monkeypatch
# ``_resolve_command_tier`` to return a synthetic resolve TOON so the routing
# logic is exercised deterministically without depending on a live
# ``run-configuration.json`` or the persisted timeout state.


def _write_task(plans_root: Path, plan_id: str, number: int, commands: list[str]) -> Path:
    """Write a minimal TASK-*.json with the supplied verification commands.

    The shape mirrors what phase-4-plan emits: a ``verification`` dict with a
    ``commands`` list plus the structural ``steps`` array. Only the fields
    the composer's routing pass reads are populated.
    """
    task = {
        'number': number,
        'title': f'Task {number}',
        'status': 'pending',
        'verification': {'commands': list(commands), 'manual': False},
        'steps': [],
    }
    tasks_dir = plans_root / plan_id / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    task_path = tasks_dir / f'TASK-{number:03d}.json'
    task_path.write_text(json.dumps(task, indent=2) + '\n', encoding='utf-8')
    return task_path


def _read_task(plans_root: Path, plan_id: str, number: int) -> dict:
    task_path = plans_root / plan_id / 'tasks' / f'TASK-{number:03d}.json'
    data: dict = json.loads(task_path.read_text(encoding='utf-8'))
    return data


def _make_tier_stub(
    orchestrator_verbs: set[str] | None = None,
    per_task_timeout: int = 360,
) -> Callable[[str, str], dict | None]:
    """Build a fake ``_resolve_command_tier`` that branches by verb.

    Commands whose verb appears in ``orchestrator_verbs`` resolve to the
    ``orchestrator`` tier; every other build verb resolves to ``per_task``
    with the supplied ``bash_timeout_seconds`` (default 360s — comfortably
    under the 600s ceiling). Non-build commands (the helper's parse
    returns ``None``) resolve to ``None`` so the composer leaves them
    untouched.
    """
    orch = set(orchestrator_verbs or ())

    def _stub(cmd: str, plan_id: str) -> dict | None:
        parsed = _mem._parse_verification_command(cmd)
        if parsed is None:
            return None
        verb, _ = parsed
        if verb in orch:
            return {
                'status': 'success',
                'bash_timeout_seconds': 900,
                'exceeds_bash_ceiling': True,
                'execution_tier': 'orchestrator',
                'hint': 'Exceeds Bash ceiling; orchestrator-tier only',
            }
        return {
            'status': 'success',
            'bash_timeout_seconds': per_task_timeout,
            'exceeds_bash_ceiling': False,
            'execution_tier': 'per_task',
            'hint': f'Bash timeout={per_task_timeout * 1000}ms',
        }

    return _stub


def test_orchestrator_tier_routes_to_phase_5_and_drops_per_task(plan_context, monkeypatch):
    """Case (a): a deliverable whose verification resolves to ``orchestrator``
    appends the mapped phase-5 step ID to ``phase_5.verification_steps`` and
    removes the command from the task's verification list."""
    plan_id = 'tier-orchestrator'
    _write_task(
        plan_context.plans_dir,
        plan_id,
        1,
        [
            'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
            '--command-args "verify plan-marshall"',
        ],
    )
    monkeypatch.setattr(_mem, '_resolve_command_tier', _make_tier_stub(orchestrator_verbs={'verify'}))

    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=3,
        )
    )

    assert result is not None and result['status'] == 'success'
    manifest = read_manifest(plan_id)
    assert manifest is not None
    # The routed step ID is the BARE canonical-verify form (no ``default:``
    # prefix) — ``_VERB_TO_PHASE_5_STEP`` maps the ``verify`` verb to
    # ``verify:module-tests`` so the appended ID matches the boundary-normalized
    # phase-5 list and never produces a ``default:``-prefixed stray.
    assert 'verify:module-tests' in manifest['phase_5']['verification_steps']
    assert 'default:verify:module-tests' not in manifest['phase_5']['verification_steps']
    task = _read_task(plan_context.plans_dir, plan_id, 1)
    assert task['verification']['commands'] == []
    assert 'bash_timeout_seconds' not in task['verification']


def test_per_task_tier_annotates_task_with_bash_timeout_seconds(plan_context, monkeypatch):
    """Case (b): a per_task verification keeps its command and gains a
    ``bash_timeout_seconds`` annotation derived from the resolve TOON."""
    plan_id = 'tier-per-task'
    _write_task(
        plan_context.plans_dir,
        plan_id,
        1,
        [
            'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
            '--command-args "module-tests plan-marshall"',
        ],
    )
    monkeypatch.setattr(_mem, '_resolve_command_tier', _make_tier_stub(per_task_timeout=420))

    result = cmd_compose(_compose_ns(plan_id=plan_id, affected_files_count=2))

    assert result is not None and result['status'] == 'success'
    task = _read_task(plan_context.plans_dir, plan_id, 1)
    assert len(task['verification']['commands']) == 1
    assert task['verification']['bash_timeout_seconds'] == 420


def test_mixed_tier_routes_to_both_locations(plan_context, monkeypatch):
    """Case (c): a task with two verification commands — one ``orchestrator``,
    one ``per_task`` — routes to both locations simultaneously."""
    plan_id = 'tier-mixed'
    _write_task(
        plan_context.plans_dir,
        plan_id,
        1,
        [
            'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
            '--command-args "verify plan-marshall"',
            'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
            '--command-args "quality-gate plan-marshall"',
        ],
    )
    monkeypatch.setattr(
        _mem,
        '_resolve_command_tier',
        _make_tier_stub(orchestrator_verbs={'verify'}, per_task_timeout=360),
    )

    result = cmd_compose(_compose_ns(plan_id=plan_id, affected_files_count=2))

    assert result is not None and result['status'] == 'success'
    manifest = read_manifest(plan_id)
    assert manifest is not None
    # The routed step ID is BARE — see test_orchestrator_tier_routes_to_phase_5.
    assert 'verify:module-tests' in manifest['phase_5']['verification_steps']
    assert 'default:verify:module-tests' not in manifest['phase_5']['verification_steps']
    task = _read_task(plan_context.plans_dir, plan_id, 1)
    # Orchestrator command pruned; per_task command retained.
    assert len(task['verification']['commands']) == 1
    assert 'quality-gate' in task['verification']['commands'][0]
    assert task['verification']['bash_timeout_seconds'] == 360


def test_non_build_command_passes_through_unchanged(plan_context, monkeypatch):
    """Case (d): a non-build verification command (raw shell ``grep``)
    receives no ``execution_tier`` field from the resolver, so the composer
    leaves the command in place and adds no annotation."""
    plan_id = 'tier-non-build'
    raw = 'grep -nE "TODO" CLAUDE.md'
    _write_task(plan_context.plans_dir, plan_id, 1, [raw])
    # ``_resolve_command_tier`` already returns ``None`` for non-build
    # commands via the existing parse short-circuit — no monkeypatch needed.

    result = cmd_compose(_compose_ns(plan_id=plan_id, affected_files_count=1))

    assert result is not None and result['status'] == 'success'
    task = _read_task(plan_context.plans_dir, plan_id, 1)
    assert task['verification']['commands'] == [raw]
    assert 'bash_timeout_seconds' not in task['verification']


def test_duplicate_orchestrator_routings_are_deduped(plan_context, monkeypatch):
    """Case (e): two tasks routing the same verb to ``orchestrator`` produce
    a single bare ``verify:module-tests`` entry in ``phase_5.verification_steps``."""
    plan_id = 'tier-dedupe'
    same_cmd = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
        '--command-args "verify plan-marshall"'
    )
    _write_task(plan_context.plans_dir, plan_id, 1, [same_cmd])
    _write_task(plan_context.plans_dir, plan_id, 2, [same_cmd])
    monkeypatch.setattr(_mem, '_resolve_command_tier', _make_tier_stub(orchestrator_verbs={'verify'}))

    result = cmd_compose(_compose_ns(plan_id=plan_id, affected_files_count=4))

    assert result is not None and result['status'] == 'success'
    manifest = read_manifest(plan_id)
    assert manifest is not None
    steps = manifest['phase_5']['verification_steps']
    # The bare verify:module-tests appears exactly once (deduped); no prefixed stray.
    assert steps.count('verify:module-tests') == 1
    assert 'default:verify:module-tests' not in steps


def test_task_command_survives_when_compose_fails_unresolvable_step(plan_context, monkeypatch):
    """Regression (8ae9e7): a task's original verification command MUST survive
    on disk when compose fails ``unresolvable_step`` on a routed ``verify:{verb}``.

    An orchestrator-tier command with a NON-canonical verb routes to the
    generalized bare ``verify:{verb}`` step, which the composer's routing pass
    also drops from the task's ``verification.commands``. The trailing verb is
    not in ``_verify_canonicals_universe()``, so the compose-time resolution gate
    (``check_emitted_steps_resolvable``) fails the whole compose with
    ``unresolvable_step`` — AFTER the routing pass ran. Because the task-file
    rewrite is now STAGED and only persisted once the gate passes, the original
    command is still on disk for the retry; the previous unconditional in-loop
    write silently dropped it (a genuine data-loss bug, not just a doc issue).
    """
    plan_id = 'tier-unresolvable-command-survives'
    original_cmd = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
        '--command-args "bogus-canonical plan-marshall"'
    )
    _write_task(plan_context.plans_dir, plan_id, 1, [original_cmd])
    # The non-canonical verb resolves to the orchestrator tier, so routing maps
    # it to the bare ``verify:bogus-canonical`` step and stages dropping the
    # command from the task.
    monkeypatch.setattr(
        _mem, '_resolve_command_tier', _make_tier_stub(orchestrator_verbs={'bogus-canonical'})
    )

    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=3,
        )
    )

    # Compose fails loud on the unresolvable routed step.
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'unresolvable_step'
    assert result['phase'] == 'phase_5'
    assert result['step_id'] == 'verify:bogus-canonical'
    # No manifest is written on the fail-loud path.
    assert read_manifest(plan_id) is None
    # THE REGRESSION ASSERTION: the original verification command is NOT lost —
    # the staged rewrite was never committed because the gate failed.
    task = _read_task(plan_context.plans_dir, plan_id, 1)
    assert task['verification']['commands'] == [original_cmd]


# =============================================================================
# scope_gated_finalize pre-filter tests
#
# Deliverable 2: the composer drops heavyweight phase-6 review/audit steps by
# scope. surgical drops the three review/audit steps (plan-retrospective,
# pre-submission-self-review, plugin-doctor) but RETAINS automatic-review by
# default (the implicit scope gate never drops it — its presence is governed by
# its configured lane); drop_review_on_scope_gate=true additionally drops
# automatic-review; single_module drops only plan-retrospective.
# multi_module/broad retain the full set. One decision-log line per subtraction.
# =============================================================================


# Candidate set covering the three scope-gated steps in their canonical
# prefixed forms plus the review gates and a few baseline steps. The composer
# boundary-normalizes only the `default:` namespace, so `project:` /
# `plan-marshall:` prefixes survive intake and the scope gate matches them
# against its match-sets.
_SCOPE_GATE_PHASE_6 = (
    'push',
    'create-pr',
    'automatic-review',
    'sonar-roundtrip',
    'default:pre-submission-self-review',
    'project:finalize-step-plugin-doctor',
    'lessons-capture',
    'plan-marshall:plan-retrospective',
    'branch-cleanup',
    'archive-plan',
)


def _write_drop_review_marshal(fixture_dir: Path, *, override: bool) -> None:
    """Write a marshal.json with the drop_review_on_scope_gate knob set.

    The knob folded out of its former flat-sibling location into its owning
    finalize step's nested param object: it lives under
    ``phase-6-finalize.steps['default:pre-submission-self-review']``
    in the id-keyed step map the composer reads via ``_read_step_owned_knob``.

    The composer treats a marshal.json ``steps`` map as the AUTHORITATIVE phase-6
    candidate list (preferred over the ``--phase-6-steps`` CSV), so the seeded
    ``steps`` map carries the FULL ``_SCOPE_GATE_PHASE_6`` candidate set — every
    candidate becomes a key (ownerless steps map to ``None``), with the
    ``drop_review_on_scope_gate`` knob nested onto its owning self-review step.
    This keeps the composed candidate list identical to the ``_compose_ns`` CSV
    while routing the knob through its new step-owned home.
    """
    steps: dict[str, dict | None] = dict.fromkeys(_SCOPE_GATE_PHASE_6)
    steps['default:pre-submission-self-review'] = {
        'drop_review_on_scope_gate': override,
    }
    marshal_path = fixture_dir / 'marshal.json'
    data = {'plan': {'phase-6-finalize': {'steps': steps}}}
    marshal_path.write_text(json.dumps(data), encoding='utf-8')


class TestScopeGatedFinalizePreFilter:
    """Scope-gated phase-6 subtraction pre-filter (scope_gated_finalize)."""

    def test_surgical_drops_three_non_guarded_steps_retains_automated_review(self, plan_context):
        """surgical scope drops plan-retrospective, pre-submission-self-review,
        and plugin-doctor — but RETAINS automatic-review by default."""
        # Use change_type=feature so the surgical row matrix does not pre-empt
        # the candidate list; the scope gate runs before the matrix regardless.
        result = cmd_compose(
            _compose_ns(
                plan_id='scope-surgical',
                change_type='feature',
                scope_estimate='surgical',
                affected_files_count=2,
                phase_5_steps='verify:quality-gate,verify:module-tests',
                phase_6_steps=','.join(_SCOPE_GATE_PHASE_6),
            )
        )
        assert result is not None and result['status'] == 'success'
        manifest = read_manifest('scope-surgical')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # Three non-guarded steps dropped.
        assert 'plan-marshall:plan-retrospective' not in steps
        assert 'pre-submission-self-review' not in steps
        assert 'project:finalize-step-plugin-doctor' not in steps
        # automatic-review RETAINED by default (no override).
        assert 'automatic-review' in steps
        # Baseline steps survive.
        assert 'push' in steps
        assert 'lessons-capture' in steps

    def test_surgical_drops_generic_default_self_review_form(self, plan_context):
        """A consuming project listing the GENERIC default:pre-submission-self-review
        step (normalized to bare pre-submission-self-review at intake) must also be
        dropped on surgical scope — the surgical drop-set covers the normalized
        bare form, not only the meta-project project: wrapper. Regression for the
        drop-set that omitted the bare form after the canonical was generalized."""
        candidates = _SCOPE_GATE_PHASE_6
        result = cmd_compose(
            _compose_ns(
                plan_id='scope-surgical-generic-selfreview',
                change_type='feature',
                scope_estimate='surgical',
                affected_files_count=2,
                phase_5_steps='verify:quality-gate,verify:module-tests',
                phase_6_steps=','.join(candidates),
            )
        )
        assert result is not None and result['status'] == 'success'
        manifest = read_manifest('scope-surgical-generic-selfreview')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # The normalized bare form must be dropped by the surgical scope gate.
        assert 'pre-submission-self-review' not in steps
        assert 'default:pre-submission-self-review' not in steps
        # Baseline steps survive.
        assert 'push' in steps

    def test_drop_review_additionally_drops_automated_review(self, plan_context):
        """drop_review_on_scope_gate=true additionally drops automatic-review."""
        _write_drop_review_marshal(plan_context.fixture_dir, override=True)
        result = cmd_compose(
            _compose_ns(
                plan_id='scope-surgical-override',
                change_type='feature',
                scope_estimate='surgical',
                affected_files_count=2,
                phase_5_steps='verify:quality-gate,verify:module-tests',
                phase_6_steps=','.join(_SCOPE_GATE_PHASE_6),
            )
        )
        assert result is not None and result['status'] == 'success'
        manifest = read_manifest('scope-surgical-override')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # automatic-review dropped under the explicit override.
        assert 'automatic-review' not in steps
        # Three non-guarded steps still dropped.
        assert 'plan-marshall:plan-retrospective' not in steps
        assert 'pre-submission-self-review' not in steps
        assert 'project:finalize-step-plugin-doctor' not in steps

    def test_drop_review_inert_on_non_scope_gated(self, plan_context):
        """drop_review_on_scope_gate=true is INERT on a non-scope-gated plan:
        automatic-review is retained on multi_module scope even with the
        override set, so flipping the project-wide knob cannot silently disable
        bot review on a large plan (PR #551 reviewer finding)."""
        _write_drop_review_marshal(plan_context.fixture_dir, override=True)
        result = cmd_compose(
            _compose_ns(
                plan_id='scope-multi-override',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=10,
                phase_5_steps='verify:quality-gate,verify:module-tests',
                phase_6_steps=','.join(_SCOPE_GATE_PHASE_6),
            )
        )
        assert result is not None and result['status'] == 'success'
        manifest = read_manifest('scope-multi-override')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # Override is inert at multi_module scope — automatic-review RETAINED.
        assert 'automatic-review' in steps
        # No scope subtraction at multi_module — the scope-gated steps survive.
        assert 'plan-marshall:plan-retrospective' in steps
        assert 'project:finalize-step-plugin-doctor' in steps
        # pre-submission-self-review SURVIVES: the pre_submission_self_review_inactive
        # pre-filter no longer drops on empty compose-time footprint (it self-gates at
        # run time), and the inert multi_module scope gate makes no subtraction.
        assert 'pre-submission-self-review' in steps

    def test_single_module_drops_only_plan_retrospective(self, plan_context):
        """single_module SCOPE gate drops only plan-retrospective; plugin-doctor
        and automatic-review are retained by the scope gate.

        pre-submission-self-review SURVIVES: the pre_submission_self_review_inactive
        pre-filter no longer drops on an empty compose-time footprint (it self-gates
        at run time), and the single_module scope gate does not drop it."""
        result = cmd_compose(
            _compose_ns(
                plan_id='scope-single-module',
                change_type='feature',
                scope_estimate='single_module',
                affected_files_count=4,
                phase_5_steps='verify:quality-gate,verify:module-tests',
                phase_6_steps=','.join(_SCOPE_GATE_PHASE_6),
            )
        )
        assert result is not None and result['status'] == 'success'
        manifest = read_manifest('scope-single-module')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # Only plan-retrospective is dropped by the single_module scope gate.
        assert 'plan-marshall:plan-retrospective' not in steps
        # pre-submission-self-review survives — the pre-filter no longer drops on an
        # empty compose-time footprint, and the single_module scope gate keeps it.
        assert 'pre-submission-self-review' in steps
        # plugin-doctor + automatic-review survive the single_module scope gate.
        assert 'project:finalize-step-plugin-doctor' in steps
        assert 'automatic-review' in steps

    def test_multi_module_retains_full_set(self, plan_context):
        """multi_module SCOPE gate makes no subtraction — the scope-gated steps
        and automatic-review are retained by the scope gate.

        pre-submission-self-review SURVIVES too: the pre_submission_self_review_inactive
        pre-filter no longer drops on an empty compose-time footprint (it self-gates at
        run time), and the inert multi_module scope gate makes no subtraction."""
        result = cmd_compose(
            _compose_ns(
                plan_id='scope-multi-module',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=10,
                phase_5_steps='verify:quality-gate,verify:module-tests',
                phase_6_steps=','.join(_SCOPE_GATE_PHASE_6),
            )
        )
        assert result is not None and result['status'] == 'success'
        manifest = read_manifest('scope-multi-module')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # The scope gate makes no subtraction at multi_module scope — the
        # scope-gated steps and automatic-review are RETAINED by the scope gate.
        assert 'plan-marshall:plan-retrospective' in steps
        assert 'project:finalize-step-plugin-doctor' in steps
        assert 'automatic-review' in steps
        # pre-submission-self-review survives — the pre-filter no longer drops on an
        # empty compose-time footprint, and the multi_module scope gate is inert.
        assert 'pre-submission-self-review' in steps

    def test_surgical_emits_one_decision_log_per_subtraction(self, plan_context):
        """surgical scope emits one decision-log line per SCOPE-GATE-dropped step.

        The pre_submission_self_review_inactive pre-filter no longer drops on an
        empty compose-time footprint, so pre-submission-self-review now reaches the
        surgical scope gate and is subtracted there alongside the two other
        non-guarded candidates (plan-retrospective + plugin-doctor) — three
        scope-gate subtractions in total."""
        captured: list[tuple[str, str]] = []
        original = _mem._emit_decision_log

        def _capture(plan_id: str, message: str) -> None:
            captured.append((plan_id, message))

        _mem._emit_decision_log = _capture
        try:
            cmd_compose(
                _compose_ns(
                    plan_id='scope-surgical-log',
                    change_type='feature',
                    scope_estimate='surgical',
                    affected_files_count=2,
                    phase_5_steps='verify:quality-gate,verify:module-tests',
                    phase_6_steps=','.join(_SCOPE_GATE_PHASE_6),
                )
            )
        finally:
            _mem._emit_decision_log = original

        subtraction_entries = [
            (pid, msg) for pid, msg in captured if 'scope_gated_finalize subtraction' in msg
        ]
        # All three non-guarded steps (plan-retrospective + plugin-doctor +
        # pre-submission-self-review) reach the surgical scope gate and are dropped
        # there → three decision-log lines. pre-submission-self-review now survives
        # the footprint pre-filter, so it too emits a scope_gated subtraction line.
        assert len(subtraction_entries) == 3
        for pid, msg in subtraction_entries:
            assert pid == 'scope-surgical-log'
            assert 'scope_estimate=surgical' in msg

    def test_result_carries_scope_gated_observability_fields(self, plan_context):
        """The compose result exposes scope_gated_finalize_dropped and
        drop_review_on_scope_gate for observability."""
        result = cmd_compose(
            _compose_ns(
                plan_id='scope-observability',
                change_type='feature',
                scope_estimate='surgical',
                affected_files_count=2,
                phase_5_steps='verify:quality-gate,verify:module-tests',
                phase_6_steps=','.join(_SCOPE_GATE_PHASE_6),
            )
        )
        assert result is not None and result['status'] == 'success'
        assert result['drop_review_on_scope_gate'] is False
        dropped = result['scope_gated_finalize_dropped']
        assert 'plan-marshall:plan-retrospective' in dropped
        assert 'project:finalize-step-plugin-doctor' in dropped
        # pre-submission-self-review now survives the footprint pre-filter and
        # reaches the surgical scope gate, which drops it — so it IS reported in the
        # scope-gate's dropped set alongside the other two non-guarded steps.
        assert 'pre-submission-self-review' in dropped
        # automatic-review NOT in the dropped set without the override.
        assert 'automatic-review' not in dropped


# =============================================================================
# envelope_count tests (TASK-16 wiring-gap fix)
#
# compose accepts an optional ``--envelope-count`` input and persists it into
# the composed manifest's ``phase_5`` block as ``envelope_count`` — the
# orchestrator's read-side signal for how many phase-5 execution-context
# envelopes to plan for. When the flag is absent the value defaults to
# ``DEFAULT_ENVELOPE_COUNT`` (1), reproducing the single-envelope behaviour, so
# existing callers that omit the flag are unaffected and a manifest read back
# without the key is interpreted by every reader as this same default. A
# non-positive value is clamped to the default. The field is written across
# every decision-matrix rule (including ``early_terminate``) so the phase_5
# block always carries it.
#
# ``_compose_ns`` deliberately omits ``envelope_count`` from its Namespace —
# the composer reads it via ``getattr(args, 'envelope_count', None)`` — so the
# bare helper exercises the absent-flag (backward-compatibility) path directly.
# The supplied-value path builds a Namespace with the attribute set.
# =============================================================================


def _compose_ns_with_envelope_count(envelope_count, **kwargs) -> Namespace:
    """``_compose_ns`` plus an explicit ``envelope_count`` attribute.

    Used by the supplied-value tests; the bare ``_compose_ns`` is reused for
    the absent-flag (backward-compatibility) path so both code paths in the
    composer's ``getattr(args, 'envelope_count', None)`` branch are covered.
    """
    ns = _compose_ns(**kwargs)
    ns.envelope_count = envelope_count
    return ns


def test_envelope_count_persisted_when_supplied(plan_context):
    """A supplied --envelope-count lands verbatim in the phase_5 block and result."""
    result = cmd_compose(
        _compose_ns_with_envelope_count(
            4,
            plan_id='envelope-supplied',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['phase_5']['envelope_count'] == 4
    manifest = read_manifest('envelope-supplied')
    assert manifest is not None
    assert manifest['phase_5']['envelope_count'] == 4


def test_envelope_count_defaults_when_absent(plan_context):
    """Omitting --envelope-count defaults to DEFAULT_ENVELOPE_COUNT (backward compat).

    ``_compose_ns`` builds a Namespace with no ``envelope_count`` attribute, so
    this exercises the ``getattr(args, 'envelope_count', None) is None`` branch
    — the path every pre-TASK-16 caller takes. The composed manifest and result
    both carry the single-envelope default.
    """
    result = cmd_compose(
        _compose_ns(
            plan_id='envelope-absent',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['phase_5']['envelope_count'] == DEFAULT_ENVELOPE_COUNT
    manifest = read_manifest('envelope-absent')
    assert manifest is not None
    assert manifest['phase_5']['envelope_count'] == DEFAULT_ENVELOPE_COUNT


def test_envelope_count_none_value_defaults(plan_context):
    """An explicit envelope_count=None (argparse default) also yields the default.

    Distinct from the absent-attribute path above: here the attribute is
    present but ``None`` (the argparse ``default=None``). Both must resolve to
    DEFAULT_ENVELOPE_COUNT.
    """
    result = cmd_compose(
        _compose_ns_with_envelope_count(
            None,
            plan_id='envelope-none',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['phase_5']['envelope_count'] == DEFAULT_ENVELOPE_COUNT
    manifest = read_manifest('envelope-none')
    assert manifest is not None
    assert manifest['phase_5']['envelope_count'] == DEFAULT_ENVELOPE_COUNT


@pytest.mark.parametrize('raw,expected', [(0, 1), (-3, 1)])
def test_envelope_count_non_positive_clamped_to_default(plan_context, raw, expected):
    """Non-positive envelope_count is clamped — the orchestrator always plans at least one envelope."""
    plan_id = f'envelope-clamp-{raw}'
    result = cmd_compose(
        _compose_ns_with_envelope_count(
            raw,
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['phase_5']['envelope_count'] == expected
    manifest = read_manifest(plan_id)
    assert manifest is not None
    assert manifest['phase_5']['envelope_count'] == expected


def test_envelope_count_written_on_early_terminate_rule(plan_context):
    """envelope_count is written across every decision-matrix rule — including early_terminate.

    Rule 1 (early_terminate_analysis) produces a minimal phase_5 block; the
    composer still stamps envelope_count onto it so the phase_5 block always
    carries the key regardless of which rule fired.
    """
    result = cmd_compose(
        _compose_ns_with_envelope_count(
            3,
            plan_id='envelope-early-terminate',
            change_type='analysis',
            scope_estimate='none',
            affected_files_count=0,
        )
    )
    assert result is not None and result['rule_fired'] == 'early_terminate_analysis'
    assert result['phase_5']['early_terminate'] is True
    assert result['phase_5']['envelope_count'] == 3
    manifest = read_manifest('envelope-early-terminate')
    assert manifest is not None
    assert manifest['phase_5']['envelope_count'] == 3


def test_envelope_count_round_trip_read(plan_context):
    """compose → read round-trip: the read subcommand surfaces envelope_count.

    cmd_read returns the full persisted manifest, so phase_5.envelope_count is
    visible to the orchestrator's read-side consumer exactly as composed.
    """
    cmd_compose(
        _compose_ns_with_envelope_count(
            5,
            plan_id='envelope-round-trip',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
        )
    )
    read_result = _mem.cmd_read(Namespace(plan_id='envelope-round-trip'))
    assert read_result is not None and read_result['status'] == 'success'
    assert read_result['phase_5']['envelope_count'] == 5


def test_envelope_count_absent_reads_cleanly_round_trip(plan_context):
    """A manifest composed without --envelope-count reads back with the default — no KeyError."""
    cmd_compose(
        _compose_ns(
            plan_id='envelope-absent-round-trip',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
        )
    )
    read_result = _mem.cmd_read(Namespace(plan_id='envelope-absent-round-trip'))
    assert read_result is not None and read_result['status'] == 'success'
    assert read_result['phase_5']['envelope_count'] == DEFAULT_ENVELOPE_COUNT


# =============================================================================
# Execution-profile lane resolution (deliverable 5)
# =============================================================================
#
# The lane resolver projects the operator posture (minimal / auto / full) over
# each phase-6 element's self-declared ``lane:`` frontmatter block. The unit
# cases below exercise the pure resolution helpers with canned lane blocks; the
# integration cases drive ``cmd_compose`` / ``cmd_lanes_preview`` end-to-end with
# the element-lane resolver monkeypatched to deterministic blocks.

# Canned lane blocks spanning all four classes + both tier deviations (shared
# fixture in _execution_manifest_fixtures.py).
_LANE_BLOCKS = fake_lane_blocks()
_LANE_STEPS = list(_LANE_BLOCKS)


def _patch_element_lane(monkeypatch, blocks=None):
    """Monkeypatch ``_resolve_element_lane`` to return canned blocks per step id."""
    table = _LANE_BLOCKS if blocks is None else blocks
    monkeypatch.setattr(_mem, '_resolve_element_lane', lambda step: table.get(step))


# --- Pure resolution helpers -------------------------------------------------


@pytest.mark.parametrize(
    'lane,override,expected',
    [
        ({'class': 'core'}, None, ('minimal', False)),         # class default
        ({'class': 'adversarial'}, None, ('auto', False)),     # class default
        ({'class': 'adversarial', 'tier': 'full'}, None, ('full', False)),  # declared tier
        ({'class': 'core'}, 'full', ('full', False)),          # override wins
        ({'class': 'core'}, 'off', ('minimal', False)),        # immune floor: off ignored → class default
        ({'class': 'derived-state'}, 'off', ('minimal', False)),  # immune floor: off ignored → class default
        ({'class': 'adversarial'}, 'off', (None, True)),       # non-floor off drops (real opt-out)
        ({'class': 'prunable'}, 'off', (None, True)),          # non-floor off drops (real opt-out)
        ({'class': 'prunable'}, 'ask', ('ask', False)),        # ask sentinel
    ],
)
def test_effective_lane_tier_precedence(lane, override, expected):
    """Effective tier resolves override ▸ declared tier ▸ class default.

    A weakening ``off`` on a ``core`` / ``derived-state`` floor class is immune —
    the ``off`` is ignored and resolution falls through to the class default.
    """
    assert _effective_lane_tier(lane, override) == expected


@pytest.mark.parametrize(
    'lane,posture,expected_keep',
    [
        ({'class': 'core', 'tier': 'minimal'}, 'minimal', True),     # floor runs everywhere
        ({'class': 'prunable', 'tier': 'auto'}, 'minimal', False),  # auto tier above minimal
        ({'class': 'prunable', 'tier': 'auto'}, 'auto', True),      # auto tier at auto
        ({'class': 'adversarial', 'tier': 'full'}, 'auto', False),  # full tier above auto
        ({'class': 'adversarial', 'tier': 'full'}, 'full', True),   # full tier at full
    ],
)
def test_lane_keep_decision_cutoff(lane, posture, expected_keep):
    """An element runs iff effective_tier ⊑ posture on the lattice."""
    keep, warning = _lane_keep_decision(lane, None, posture)
    assert keep is expected_keep
    assert warning is None


def test_lane_keep_off_override_immune_for_derived_state_floor():
    """An ``off`` override of a derived-state floor element is IMMUNE — the element
    is KEPT and an informational warning records the neutralized override."""
    keep, warning = _lane_keep_decision({'class': 'derived-state', 'tier': 'minimal'}, 'off', 'minimal')

    assert keep is True
    assert warning is not None
    assert 'derived-state' in warning
    assert 'immune' in warning


def test_lane_keep_off_override_immune_for_core_floor():
    """An ``off`` override of a core floor element is IMMUNE — KEPT with a warning."""
    keep, warning = _lane_keep_decision({'class': 'core', 'tier': 'minimal'}, 'off', 'minimal')

    assert keep is True
    assert warning is not None
    assert 'core' in warning
    assert 'immune' in warning


def test_lane_keep_off_override_drops_adversarial_cleanly():
    """An ``off`` override of a non-floor adversarial element drops it — no warning (real opt-out)."""
    keep, warning = _lane_keep_decision({'class': 'adversarial', 'tier': 'auto'}, 'off', 'auto')

    assert keep is False
    assert warning is None


def test_lane_keep_off_override_drops_prunable_cleanly():
    """An ``off`` override of a non-floor prunable element drops it — no warning (real opt-out)."""
    keep, warning = _lane_keep_decision({'class': 'prunable', 'tier': 'auto'}, 'off', 'auto')

    assert keep is False
    assert warning is None


def test_lane_keep_minimal_override_force_keeps_under_every_posture():
    """A ``minimal`` override force-keeps an otherwise-full element at minimal posture."""
    keep, warning = _lane_keep_decision({'class': 'adversarial', 'tier': 'full'}, 'minimal', 'minimal')

    assert keep is True
    assert warning is None


@pytest.mark.parametrize(
    'raw,expected',
    [('5K', 5000), ('130K', 130000), ('520K', 520000), ('1.3M', 1300000), ('garbage', 0)],
)
def test_parse_cost_magnitude(raw, expected):
    """Cost magnitudes parse K/M suffixes; an unparseable value degrades to 0."""
    assert _parse_cost_magnitude(raw) == expected


# --- _apply_lane_resolution --------------------------------------------------


def test_apply_lane_resolution_full_is_noop(monkeypatch):
    """The full posture keeps every element (no pruning)."""
    _patch_element_lane(monkeypatch)
    kept, dropped, warnings = _apply_lane_resolution(_LANE_STEPS, 'full', None, 'p')

    assert kept == _LANE_STEPS
    assert dropped == []
    assert warnings == []


def test_apply_lane_resolution_minimal_keeps_only_floor(monkeypatch):
    """Minimal keeps only the tier-minimal floor; auto/full-tier elements drop."""
    _patch_element_lane(monkeypatch)
    kept, dropped, _warnings = _apply_lane_resolution(_LANE_STEPS, 'minimal', None, 'p')

    assert kept == ['push', 'archive-plan', 'project:finalize-step-deploy-target']
    assert set(dropped) == {'sonar-roundtrip', 'finalize-step-security-audit', 'plan-marshall:plan-retrospective'}


def test_apply_lane_resolution_auto_drops_only_full_tier(monkeypatch):
    """Auto keeps minimal + auto tiers and drops the two full-tier elements."""
    _patch_element_lane(monkeypatch)
    kept, dropped, _warnings = _apply_lane_resolution(_LANE_STEPS, 'auto', None, 'p')

    assert set(dropped) == {'finalize-step-security-audit', 'plan-marshall:plan-retrospective'}
    assert 'sonar-roundtrip' in kept
    assert 'project:finalize-step-deploy-target' in kept


def test_apply_lane_resolution_keeps_unblocked_elements(monkeypatch):
    """An element with no lane: block is not lane-participating and is always kept."""
    monkeypatch.setattr(_mem, '_resolve_element_lane', lambda step: None)
    kept, dropped, _warnings = _apply_lane_resolution(['no-block-step'], 'minimal', None, 'p')

    assert kept == ['no-block-step']
    assert dropped == []


def test_apply_lane_resolution_derived_state_off_override_is_immune(monkeypatch):
    """An ``off`` marshal override of a derived-state floor element is IMMUNE — the
    element is KEPT with an informational warning (the mandatory floor cannot be weakened)."""
    _patch_element_lane(monkeypatch)
    overrides = {'project:finalize-step-deploy-target': {'lane': 'off'}}
    kept, dropped, warnings = _apply_lane_resolution(_LANE_STEPS, 'minimal', overrides, 'p')

    assert 'project:finalize-step-deploy-target' in kept
    assert kept == ['push', 'archive-plan', 'project:finalize-step-deploy-target']
    assert 'project:finalize-step-deploy-target' not in dropped
    assert any(
        step == 'project:finalize-step-deploy-target' and 'immune' in warning
        for step, warning in warnings
    )


def test_apply_lane_resolution_adversarial_off_override_drops_cleanly(monkeypatch):
    """An ``off`` marshal override of a non-floor adversarial element drops it with NO
    warning — the opt-out is a real drop (auto posture would otherwise keep it)."""
    _patch_element_lane(monkeypatch)
    overrides = {'sonar-roundtrip': {'lane': 'off'}}
    kept, dropped, warnings = _apply_lane_resolution(_LANE_STEPS, 'auto', overrides, 'p')

    assert 'sonar-roundtrip' in dropped
    assert 'sonar-roundtrip' not in kept
    assert all(step != 'sonar-roundtrip' for step, _ in warnings)


def test_meta_project_minimal_keeps_derived_state_without_override(monkeypatch):
    """Meta-project invariant: a minimal posture keeps derived-state by default (never SILENTLY dropped)."""
    _patch_element_lane(monkeypatch)
    kept, dropped, warnings = _apply_lane_resolution(
        ['project:finalize-step-deploy-target'], 'minimal', None, 'p'
    )

    assert kept == ['project:finalize-step-deploy-target']
    assert dropped == []
    assert warnings == []


# --- cmd_lanes_preview -------------------------------------------------------


def _lanes_preview_ns(plan_id: str, steps: list[str]) -> Namespace:
    return Namespace(plan_id=plan_id, phase_6_steps=','.join(steps))


def test_lanes_preview_resolves_all_three_postures(plan_context, monkeypatch):
    """lanes preview returns the minimal/auto/full step sets + cost sums in one result."""
    _patch_element_lane(monkeypatch)
    result = cmd_lanes_preview(_lanes_preview_ns('lanes-preview', _LANE_STEPS))

    assert result is not None and result['status'] == 'success'
    lanes = result['lanes']
    assert lanes['full']['phase_6_steps'] == _LANE_STEPS
    assert lanes['minimal']['phase_6_steps'] == ['push', 'archive-plan', 'project:finalize-step-deploy-target']
    assert set(lanes['auto']['phase_6_steps']) == {
        'push', 'archive-plan', 'sonar-roundtrip', 'project:finalize-step-deploy-target',
    }
    # Cost sums: XS=5K, L=130K → full=405K, auto=145K, minimal=15K.
    assert lanes['full']['cost_sum_tokens'] == 405000
    assert lanes['auto']['cost_sum_tokens'] == 145000
    assert lanes['minimal']['cost_sum_tokens'] == 15000


def test_lanes_preview_agrees_with_apply_lane_resolution(plan_context, monkeypatch):
    """The preview projection is the SAME one compose applies (one projection feeds both)."""
    _patch_element_lane(monkeypatch)
    result = cmd_lanes_preview(_lanes_preview_ns('lanes-agree', _LANE_STEPS))
    assert result is not None

    for posture in ('minimal', 'auto', 'full'):
        kept, _dropped, _warnings = _apply_lane_resolution(_LANE_STEPS, posture, None, 'lanes-agree')
        assert result['lanes'][posture]['phase_6_steps'] == kept


# --- compose integration -----------------------------------------------------


def test_compose_absent_profile_defaults_to_full_no_pruning(plan_context):
    """A plan with no execution_profile composes as full — the back-compat no-prune path."""
    result = cmd_compose(_compose_ns(plan_id='lane-absent-profile'))

    assert result is not None
    assert result['execution_profile'] == 'full'
    assert result['lane_dropped'] == []
    assert result['lane_warnings'] == []


def test_compose_minimal_profile_prunes_phase_6_to_floor(plan_context, monkeypatch):
    """A minimal posture prunes the auto/full-tier finalize steps from phase_6.steps."""
    _patch_element_lane(monkeypatch)
    plan_id = 'lane-minimal-compose'
    _write_status_metadata(plan_context, plan_id, {'execution_profile': 'minimal'})

    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=5,
            phase_6_steps=','.join(_LANE_STEPS),
        )
    )

    assert result is not None
    assert result['execution_profile'] == 'minimal'
    manifest = read_manifest(plan_id)
    # The D1 sort choke-point places archive-plan (order 1000) terminal among
    # the order-resolvable steps, so it now trails deploy-target.
    assert manifest['phase_6']['steps'] == ['push', 'project:finalize-step-deploy-target', 'archive-plan']
    assert set(result['lane_dropped']) == {
        'sonar-roundtrip', 'finalize-step-security-audit', 'plan-marshall:plan-retrospective',
    }


def test_compose_auto_profile_drops_only_full_tier(plan_context, monkeypatch):
    """An auto posture keeps tier-auto finalize steps and drops only the full-tier ones."""
    _patch_element_lane(monkeypatch)
    plan_id = 'lane-auto-compose'
    _write_status_metadata(plan_context, plan_id, {'execution_profile': 'auto'})

    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=5,
            phase_6_steps=','.join(_LANE_STEPS),
        )
    )

    assert result is not None
    assert result['execution_profile'] == 'auto'
    manifest = read_manifest(plan_id)
    assert 'sonar-roundtrip' in manifest['phase_6']['steps']
    assert 'finalize-step-security-audit' not in manifest['phase_6']['steps']
    assert 'plan-marshall:plan-retrospective' not in manifest['phase_6']['steps']


def test_read_execution_profile_defaults_full_when_absent(plan_context):
    """_read_execution_profile returns full when status.json is absent."""
    assert _read_execution_profile('no-such-plan') == 'full'


def test_read_execution_profile_reads_persisted_posture(plan_context):
    """_read_execution_profile returns the persisted status.metadata.execution_profile."""
    _write_status_metadata(plan_context, 'lane-read-posture', {'execution_profile': 'minimal'})
    assert _read_execution_profile('lane-read-posture') == 'minimal'


# =============================================================================
# Compose-time step-resolution gate (deliverable 1)
#
# `compose` resolves every FINAL emitted phase-5/6 step id and fails loud
# (`status: error`, `error: unresolvable_step`) on the first that resolves to no
# built-in doc, project-local skill, or bundle discovery-registry entry — closing
# the hole `validate-loadable` left by short-circuiting every external step to
# `loadable: true`. These fixtures cover the three fail-loud shapes (never-existed
# bundle:skill, never-existed built-in, never-existed project:) and the all-resolve
# success path (built-in + project: + promoted `plan-marshall:automatic-review` +
# opt-in `plan-marshall:plan-retrospective`). The CSV-fallback compose path carries
# no marshal.json keyed map, so the reported `marshal_key` degrades to the emitted
# step id (which still names the offending key verbatim).
# =============================================================================


def test_compose_rejects_unresolvable_bundle_skill_step(plan_context):
    """A never-existed bundle:skill finalize step fails compose loud, naming the key.

    `plan-marshall:ghost-review` is preserved verbatim through boundary
    normalization (external prefixes are never stripped) and survives the Row 7
    default rule, so it reaches the resolution gate. The finalize-step discovery
    registry has no such implementor, so `compose` returns `unresolvable_step`.
    """
    candidates = (
        'push',
        'create-pr',
        'automatic-review',
        'plan-marshall:ghost-review',  # never-existed bundle:skill finalize step
        'archive-plan',
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='resolve-gate-ghost-bundle',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=6,
            phase_6_steps=','.join(candidates),
        )
    )
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'unresolvable_step'
    assert result['phase'] == 'phase_6'
    assert result['step_id'] == 'plan-marshall:ghost-review'
    assert result['marshal_key'] == 'plan-marshall:ghost-review'
    assert 'plan-marshall:ghost-review' in result['message']
    # No manifest is written on the fail-loud path.
    assert read_manifest('resolve-gate-ghost-bundle') is None


def test_compose_rejects_unresolvable_builtin_step(plan_context):
    """A never-existed bare built-in step fails compose loud (no standards/workflow doc)."""
    candidates = ('push', 'create-pr', 'ghost-builtin-step', 'archive-plan')
    result = cmd_compose(
        _compose_ns(
            plan_id='resolve-gate-ghost-builtin',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=6,
            phase_6_steps=','.join(candidates),
        )
    )
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'unresolvable_step'
    assert result['phase'] == 'phase_6'
    assert result['step_id'] == 'ghost-builtin-step'
    assert 'ghost-builtin-step' in result['message']


def test_compose_rejects_unresolvable_project_step(plan_context):
    """A never-existed project: finalize step fails compose loud (no project-local SKILL.md)."""
    candidates = ('push', 'create-pr', 'project:finalize-step-ghost', 'archive-plan')
    result = cmd_compose(
        _compose_ns(
            plan_id='resolve-gate-ghost-project',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=6,
            phase_6_steps=','.join(candidates),
        )
    )
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'unresolvable_step'
    assert result['phase'] == 'phase_6'
    assert result['step_id'] == 'project:finalize-step-ghost'
    assert 'project:finalize-step-ghost' in result['message']


def test_compose_rejects_unresolvable_phase_5_canonical(plan_context):
    """A never-existed phase-5 canonical (`verify:{bogus}`) fails compose loud.

    The verify-canonicals universe (the composer `_CANONICAL_TO_ROLE` keys unioned
    with every `ext-point-build-verify-step` implementor's `canonicals`) does not
    contain `bogus-canonical`, so the phase-5 gate rejects it before phase-6 is
    even reached.
    """
    result = cmd_compose(
        _compose_ns(
            plan_id='resolve-gate-ghost-canonical',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=6,
            phase_5_steps='verify:quality-gate,verify:bogus-canonical',
        )
    )
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'unresolvable_step'
    assert result['phase'] == 'phase_5'
    assert result['step_id'] == 'verify:bogus-canonical'
    assert 'bogus-canonical' in result['message']


def test_compose_succeeds_when_every_step_resolves(plan_context):
    """The gate passes for a fully-resolvable step list.

    Covers all four resolution branches: built-in (`push`/`create-pr`/…), the
    promoted `plan-marshall:automatic-review` (boundary-normalized to the bare
    `automatic-review` built-in), a project-local `project:finalize-step-plugin-doctor`,
    and the opt-in `plan-marshall:plan-retrospective` bundle:skill finalize step,
    plus phase-5 canonical-verify steps. `multi_module` scope keeps
    `plan-marshall:plan-retrospective` (the scope gate only drops it on
    surgical/single_module), so it reaches — and passes — the gate.
    """
    resolvable = (
        'push',
        'create-pr',
        'plan-marshall:automatic-review',  # promoted → normalizes to bare automatic-review
        'project:finalize-step-plugin-doctor',  # project-local skill
        'lessons-capture',
        'plan-marshall:plan-retrospective',  # opt-in bundle:skill finalize step
        'branch-cleanup',
        'archive-plan',
    )
    result = cmd_compose(
        _compose_ns(
            plan_id='resolve-gate-pass',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=8,
            phase_5_steps='verify:quality-gate,verify:module-tests',
            phase_6_steps=','.join(resolvable),
        )
    )
    assert result is not None and result['status'] == 'success'
    manifest = read_manifest('resolve-gate-pass')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    # The promoted bundle id normalized to bare; the opt-in bundle step and the
    # project step survived verbatim — all resolved by the gate.
    assert 'automatic-review' in steps
    assert 'project:finalize-step-plugin-doctor' in steps
    assert 'plan-marshall:plan-retrospective' in steps
    # Phase-5 canonical-verify steps resolved too.
    assert manifest['phase_5']['verification_steps'] == ['verify:quality-gate', 'verify:module-tests']


# =============================================================================
# Regression: project: steps resolve via the cwd-relative working-tree root, not
# the Path(__file__)-derived _REPO_ROOT. When the executor runs the deployed
# plugin-cache copy, Path(__file__) lives under ~/.claude/plugins/cache/..., so
# resolve_bundles_root(__file__).parent.parent (_REPO_ROOT) lands at
# ~/.claude/plugins — a directory with no .claude/skills. A base=_REPO_ROOT
# project-skill probe therefore reported EVERY project: finalize/verify step
# falsely unresolvable, blocking compose for every meta-project plan. The fix
# anchors project-local resolution on the uniform cwd-relative resolver
# (_project_local_skills_root → _find_plan_root_from_cwd). The existing gate
# tests can't catch this because they run from source, where _REPO_ROOT
# coincidentally equals the real repo root; this test forces _REPO_ROOT to a
# skill-less directory to reproduce the cache anchor.
# =============================================================================


def test_project_step_resolves_from_working_tree_not_file_anchor(monkeypatch, tmp_path):
    """`project:` step resolution ignores a cache-anchored _REPO_ROOT and uses cwd."""
    import _manifest_validation as _mv

    # Fake working tree under cwd: .plan/local anchors the cwd walk-up, and
    # .claude/skills holds the project-local step's SKILL.md.
    (tmp_path / '.plan' / 'local').mkdir(parents=True)
    skill_dir = tmp_path / '.claude' / 'skills' / 'finalize-step-cache-probe'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('---\norder: 77\n---\n# probe\n', encoding='utf-8')

    # Simulate the deployed-cache anchor: _REPO_ROOT points at a dir with no
    # .claude/skills (as ~/.claude/plugins does in production).
    cache_like = tmp_path / 'plugins-cache-root'
    cache_like.mkdir()
    monkeypatch.setattr(_mv, '_REPO_ROOT', cache_like)
    monkeypatch.chdir(tmp_path)

    # Resolvability resolves from the cwd working tree despite the bogus _REPO_ROOT.
    resolvable = _mv._check_step_resolvable('project:finalize-step-cache-probe', 'phase_6')
    assert resolvable['resolvable'] is True

    # A genuinely-absent project step still fails loud (guards against the fix
    # degrading into an unconditional pass).
    missing = _mv._check_step_resolvable('project:finalize-step-does-not-exist', 'phase_6')
    assert missing['resolvable'] is False

    # Order resolution reads the frontmatter from the cwd working tree too.
    assert _mv._resolve_step_order('project:finalize-step-cache-probe') == 77


# =============================================================================
# D6 — compose-time drop-when-no-provider for an unresolved lane:ask infra element
#
# Both adversarial infra elements (automatic-review, sonar-roundtrip) seed
# ``lane: ask``. A steward-persisted answer overwrites the override to
# off/auto/full; an effective tier still equal to ``ask`` at compose means the
# operator never answered (UNRESOLVED). When unresolved AND the corresponding
# provider is absent (no CI provider for automatic-review; no Sonar provider for
# sonar-roundtrip), the ``_apply_unresolved_ask_provider_drop`` pre-filter drops
# the element at the candidate-narrowing stage. A resolved (off/auto/full) ask
# and a provider-configured ask both survive. These compose round-trip tests
# exercise the pre-filter end-to-end through cmd_compose; the pure-function truth
# table is pinned directly in test_decision_rules.py.
# =============================================================================


def _seed_marshal_with_finalize_steps(
    steps_map: dict[str, dict],
    *,
    ci_provider: str | None = None,
    sonar_provider: bool = False,
) -> Path:
    """Seed marshal.json with a ``phase-6-finalize.steps`` keyed map + providers.

    ``steps_map`` becomes the candidate source (its keys ARE the phase-6
    candidate list) and the per-element ``lane`` override map the D6 pre-filter
    reads. ``ci_provider`` (``'github'``/``'gitlab'``/``None``) and
    ``sonar_provider`` control the ``providers[]`` list so the two provider
    readers resolve deterministically.
    """
    from file_ops import get_marshal_path

    providers: list[dict] = []
    if ci_provider:
        providers.append(
            {'skill_name': f'plan-marshall:workflow-integration-{ci_provider}', 'category': 'ci'}
        )
    if sonar_provider:
        providers.append(
            {'skill_name': 'plan-marshall:workflow-integration-sonar', 'category': 'sonar'}
        )
    marshal: dict = {'plan': {'phase-6-finalize': {'steps': steps_map}}}
    if providers:
        marshal['providers'] = providers
    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2))
    return marshal_path


class TestUnresolvedAskProviderDropCompose:
    """End-to-end compose round-trip of the D6 unresolved-ask provider-drop pre-filter."""

    def test_unresolved_ask_automatic_review_drops_when_no_ci_provider(self, plan_context):
        """{automatic-review: ask, no CI provider} → dropped from phase_6.steps."""
        steps_map = {
            'push': {},
            'plan-marshall:automatic-review': {'lane': 'ask'},
            'archive-plan': {},
        }
        _seed_marshal_with_finalize_steps(steps_map, ci_provider=None)
        result = cmd_compose(_compose_ns(plan_id='d6-ar-drop', phase_6_steps=None))
        assert result is not None and result['status'] == 'success'
        # The compose pipeline boundary-normalizes every candidate to its bare
        # form before the pre-filters run (``canonicalize_step_key``), so the
        # promoted ``plan-marshall:automatic-review`` candidate is carried — and
        # dropped/reported — as bare ``automatic-review`` (the same bare form the
        # manifest stores, per the keep-case assertion below).
        assert 'automatic-review' in result['unresolved_ask_provider_dropped']
        manifest = read_manifest('d6-ar-drop')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        assert 'automatic-review' not in steps and 'plan-marshall:automatic-review' not in steps
        # Non-infra candidates survive.
        assert 'push' in steps and 'archive-plan' in steps

    def test_unresolved_ask_automatic_review_kept_when_ci_provider_present(self, plan_context):
        """{automatic-review: ask, CI provider present} → kept."""
        steps_map = {
            'push': {},
            'plan-marshall:automatic-review': {'lane': 'ask'},
            'archive-plan': {},
        }
        _seed_marshal_with_finalize_steps(steps_map, ci_provider='github')
        result = cmd_compose(_compose_ns(plan_id='d6-ar-keep', phase_6_steps=None))
        assert result is not None and result['status'] == 'success'
        assert result['unresolved_ask_provider_dropped'] == []
        steps = read_manifest('d6-ar-keep')['phase_6']['steps']
        assert 'automatic-review' in steps

    def test_unresolved_ask_sonar_roundtrip_drops_when_no_sonar_provider(self, plan_context):
        """{sonar-roundtrip: ask, no Sonar provider} → dropped."""
        steps_map = {
            'push': {},
            'default:sonar-roundtrip': {'lane': 'ask'},
            'archive-plan': {},
        }
        _seed_marshal_with_finalize_steps(steps_map, sonar_provider=False)
        result = cmd_compose(_compose_ns(plan_id='d6-sr-drop', phase_6_steps=None))
        assert result is not None and result['status'] == 'success'
        assert 'sonar-roundtrip' in result['unresolved_ask_provider_dropped']
        steps = read_manifest('d6-sr-drop')['phase_6']['steps']
        assert 'sonar-roundtrip' not in steps
        assert 'push' in steps and 'archive-plan' in steps

    def test_unresolved_ask_sonar_roundtrip_kept_when_sonar_provider_present(self, plan_context):
        """{sonar-roundtrip: ask, Sonar provider present} → kept."""
        steps_map = {
            'push': {},
            'default:sonar-roundtrip': {'lane': 'ask'},
            'archive-plan': {},
        }
        _seed_marshal_with_finalize_steps(steps_map, sonar_provider=True)
        result = cmd_compose(_compose_ns(plan_id='d6-sr-keep', phase_6_steps=None))
        assert result is not None and result['status'] == 'success'
        assert result['unresolved_ask_provider_dropped'] == []
        steps = read_manifest('d6-sr-keep')['phase_6']['steps']
        assert 'sonar-roundtrip' in steps

    def test_resolved_full_ask_with_provider_survives(self, plan_context):
        """A full-resolved ask (override overwritten to ``full``) with a configured
        provider is never dropped by this pre-filter."""
        steps_map = {
            'push': {},
            'plan-marshall:automatic-review': {'lane': 'full'},
            'default:sonar-roundtrip': {'lane': 'full'},
            'archive-plan': {},
        }
        _seed_marshal_with_finalize_steps(steps_map, ci_provider='github', sonar_provider=True)
        result = cmd_compose(_compose_ns(plan_id='d6-resolved-full', phase_6_steps=None))
        assert result is not None and result['status'] == 'success'
        assert result['unresolved_ask_provider_dropped'] == []
        steps = read_manifest('d6-resolved-full')['phase_6']['steps']
        assert 'automatic-review' in steps and 'sonar-roundtrip' in steps

    def test_resolved_auto_ask_survives_even_without_provider(self, plan_context):
        """An auto-resolved ask survives even when the provider is absent — only an
        UNRESOLVED ``ask`` is provider-gated by this pre-filter."""
        steps_map = {
            'push': {},
            'plan-marshall:automatic-review': {'lane': 'auto'},
            'default:sonar-roundtrip': {'lane': 'auto'},
            'archive-plan': {},
        }
        _seed_marshal_with_finalize_steps(steps_map, ci_provider=None, sonar_provider=False)
        result = cmd_compose(_compose_ns(plan_id='d6-resolved-auto', phase_6_steps=None))
        assert result is not None and result['status'] == 'success'
        assert result['unresolved_ask_provider_dropped'] == []
        steps = read_manifest('d6-resolved-auto')['phase_6']['steps']
        assert 'automatic-review' in steps and 'sonar-roundtrip' in steps


# =============================================================================
# build_verdict_contradiction — the post-matrix assertion's wiring into compose
#
# The assertion itself is unit-tested in
# ``test_build_verdict_contradiction_guard.py``; these cases pin that the
# composer actually CONSULTS it on the final step lists and converts a finding
# into a fail-loud compose that writes no manifest — the same shape the
# ``unresolvable_step`` / ``non_canonical_step`` siblings use.
# =============================================================================


class TestBuildVerdictContradictionWiring:
    """``cmd_compose`` rejects a manifest that contradicts the build verdict."""

    @staticmethod
    def _stub_verdict_inputs(footprint: list[str], verdict: dict | None) -> tuple:
        """Pin both assertion inputs; returns the originals for restoration."""
        original_footprint = _mem._resolve_footprint
        original_verdict = _mem._command_free_build_verdict
        _mem._resolve_footprint = lambda plan_id: list(footprint)
        _mem._command_free_build_verdict = lambda plan_id: verdict
        return original_footprint, original_verdict

    @staticmethod
    def _restore(originals: tuple) -> None:
        _mem._resolve_footprint, _mem._command_free_build_verdict = originals

    def test_compose_fails_loud_on_a_contradiction(self, plan_context):
        """A not_necessary verdict over a real footprint + a composed build step → error."""
        plan_id = 'verdict-contradiction'
        originals = self._stub_verdict_inputs(
            ['marketplace/bundles/plan-marshall/skills/foo/scripts/foo.py'],
            {'decision': 'not_necessary', 'reason': 'plan footprint touches no build_map glob'},
        )
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=3,
                    phase_5_steps='verify:quality-gate,verify:module-tests',
                )
            )
        finally:
            self._restore(originals)

        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'build_verdict_contradiction'
        assert result['phase'] == 'phase_5'
        assert result['step_id'] == 'verify:module-tests'
        # The verdict's own reason is forwarded, not an invented one.
        assert result['reason'] == 'plan footprint touches no build_map glob'

    def test_failed_assertion_writes_no_manifest(self, plan_context):
        """Like its sibling gates, the assertion returns BEFORE write_manifest.

        A partial manifest persisted by a rejected compose would be read as
        authoritative by phase-5, so the fail-loud path must leave no artifact.
        """
        plan_id = 'verdict-contradiction-no-write'
        originals = self._stub_verdict_inputs(
            ['scripts/foo.py'],
            {'decision': 'not_necessary', 'reason': 'plan footprint touches no build_map glob'},
        )
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=3,
                    phase_5_steps='verify:quality-gate,verify:module-tests',
                )
            )
        finally:
            self._restore(originals)

        assert result is not None and result['status'] == 'error'
        assert read_manifest(plan_id) is None

    def test_compose_succeeds_when_the_verdict_agrees(self, plan_context):
        """A ``build`` verdict over the same inputs composes normally."""
        plan_id = 'verdict-consistent'
        originals = self._stub_verdict_inputs(['scripts/foo.py'], {'decision': 'build'})
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=3,
                    phase_5_steps='verify:quality-gate,verify:module-tests',
                )
            )
        finally:
            self._restore(originals)

        assert result is not None and result['status'] == 'success'
        assert read_manifest(plan_id) is not None

    def test_early_compose_with_an_empty_footprint_composes_normally(self, plan_context):
        """Anti-vacuity at the WIRING level: the ordinary first compose must succeed.

        This is the case that would break every plan if the composer consulted
        the assertion without its non-empty-footprint precondition: at
        phase-4-plan time the footprint is empty, the verdict is therefore
        ``not_necessary``, and the composed list is the full build/verify set.
        """
        plan_id = 'verdict-early-compose'
        originals = self._stub_verdict_inputs(
            [],  # early compose — worktree not yet materialized
            {'decision': 'not_necessary', 'reason': 'plan footprint is empty — no changed files to build'},
        )
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=3,
                    phase_5_steps='verify:quality-gate,verify:module-tests,verify:coverage',
                )
            )
        finally:
            self._restore(originals)

        assert result is not None and result['status'] == 'success'
        manifest = read_manifest(plan_id)
        assert manifest is not None
        assert 'verify:module-tests' in manifest['phase_5']['verification_steps']

    def test_unobtainable_verdict_composes_normally(self, plan_context):
        """A ``None`` verdict cannot prove a contradiction, so compose proceeds."""
        plan_id = 'verdict-unobtainable'
        originals = self._stub_verdict_inputs(['scripts/foo.py'], None)
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=3,
                    phase_5_steps='verify:quality-gate,verify:module-tests',
                )
            )
        finally:
            self._restore(originals)

        assert result is not None and result['status'] == 'success'
