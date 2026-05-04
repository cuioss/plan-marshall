#!/usr/bin/env python3
"""
Regression tests for the phase-5-execute manifest-executor contract.

phase-5-execute is a workflow-driven skill (no Python entry point of its own).
At phase entry it reads the per-plan execution manifest produced by
``manage-execution-manifest`` and dispatches verification steps based on
``phase_5.early_terminate`` and ``phase_5.verification_steps``. These tests
pin the contract phase-5-execute SKILL.md depends on:

1. **Manifest API shape** — synthetic manifests produced by ``cmd_compose``
   round-trip through ``cmd_read`` with the exact fields the executor consumes.
2. **Step dispatch derivation** — for each scenario (empty list, full list,
   just module-tests, early_terminate=true), the executor would fire the
   correct steps and append exactly **one** final ``quality-gate`` sweep when
   ``verification_steps`` is non-empty.
3. **SKILL.md narrative** — the documented workflow inlines the early-terminate
   short-circuit and the manifest-driven Step 11b "Final Quality Sweep".

This suite intentionally does NOT re-test the decision matrix internals
(those live in test_manage_execution_manifest.py); it focuses strictly on
the executor-facing contract.
"""

import importlib.util
from argparse import Namespace

import pytest

from conftest import MARKETPLACE_ROOT, PlanContext

# ---------------------------------------------------------------------------
# Manifest module (Tier 2 direct import via importlib because of the hyphen)
# ---------------------------------------------------------------------------

_MANIFEST_SCRIPT = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
    / 'manage-execution-manifest.py'
)
_spec = importlib.util.spec_from_file_location('mem_for_phase5', str(_MANIFEST_SCRIPT))
assert _spec is not None
_mem = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mem)

cmd_compose = _mem.cmd_compose
cmd_read = _mem.cmd_read
read_manifest = _mem.read_manifest
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Quiet down the best-effort decision-log subprocess so tests don't depend on a
# running executor; mirror manage-execution-manifest test layout.
_mem._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# SKILL.md path for narrative-contract assertions
# ---------------------------------------------------------------------------

_PHASE_5_SKILL_MD = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-5-execute' / 'SKILL.md'


def _compose_ns(
    plan_id: str,
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'quality-gate,module-tests,coverage',
    phase_6_steps: str | None = ','.join(DEFAULT_PHASE_6_STEPS),
    commit_strategy: str | None = None,
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
        commit_strategy=commit_strategy,
    )


def _read_ns(plan_id: str) -> Namespace:
    return Namespace(plan_id=plan_id)


# ---------------------------------------------------------------------------
# Helper — derive the steps the executor would fire from a manifest read.
#
# The executor (phase-5-execute SKILL.md Step 2 + Step 11b) follows this
# ordering:
#   1. If early_terminate: return []  — entire execute loop is skipped.
#   2. Else: dispatch verification_steps in order during the per-task loop.
#   3. After the loop: if verification_steps is non-empty, append exactly one
#      canonical "quality-gate" sweep (Step 11b). If empty, append nothing.
# ---------------------------------------------------------------------------


def _derive_executor_dispatch(manifest: dict) -> list[str]:
    """Return the exact ordered list of verification steps the executor would
    fire for the given manifest, including the Step 11b final sweep."""
    phase_5 = manifest['phase_5']
    if phase_5['early_terminate']:
        return []
    steps = list(phase_5['verification_steps'])
    if steps:
        steps.append('quality-gate')  # Step 11b — final canonical sweep.
    return steps


# ===========================================================================
# Manifest API contract tests
# ===========================================================================


class TestManifestApiContract:
    """The shape phase-5-execute reads via ``manage-execution-manifest read``."""

    def test_read_returns_phase_5_block_with_executor_fields(self):
        with PlanContext(plan_id='p5-read-shape'):
            cmd_compose(_compose_ns('p5-read-shape'))
            result = cmd_read(_read_ns('p5-read-shape'))

            assert result is not None
            assert result['status'] == 'success'
            assert result['plan_id'] == 'p5-read-shape'
            assert 'phase_5' in result, 'phase-5-execute Step 2 reads phase_5 — must be present in read output'
            phase_5 = result['phase_5']
            assert isinstance(phase_5, dict)
            assert isinstance(phase_5.get('early_terminate'), bool)
            assert isinstance(phase_5.get('verification_steps'), list)


# ===========================================================================
# Scenario tests — verify the executor would fire the correct steps for the
# four manifest shapes called out in the task description.
# ===========================================================================


class TestExecutorDispatchScenarios:
    """Synthetic manifests of various shapes — assert the dispatched steps."""

    def test_full_verification_list_appends_one_quality_sweep(self):
        """verification_steps non-empty → all steps fire **in declared order**
        + exactly one canonical 'quality-gate' sweep appended at end.

        Pins coverage target #2 from deliverable 5: manifest with
        [quality-gate, module-tests, coverage] dispatches all three steps in
        that order, then Step 11b appends a single quality-gate sweep.
        """
        with PlanContext(plan_id='p5-full'):
            cmd_compose(
                _compose_ns(
                    'p5-full',
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=12,
                    phase_5_steps='quality-gate,module-tests,coverage',
                )
            )
            manifest = read_manifest('p5-full')
            assert manifest is not None
            # Manifest preserves declared order — Rule 7 default path passes
            # the candidates through verbatim.
            assert manifest['phase_5']['verification_steps'] == [
                'quality-gate',
                'module-tests',
                'coverage',
            ]

            dispatched = _derive_executor_dispatch(manifest)

            # Exact ordered dispatch: the three manifest steps fire in
            # declared order, then the Step 11b sweep is appended at the end.
            assert dispatched == [
                'quality-gate',
                'module-tests',
                'coverage',
                'quality-gate',
            ], f'Full-list manifest must dispatch in declared order with one appended Step 11b sweep, got {dispatched}'
            # Defensive cross-check: the sweep is unconditional when the list
            # is non-empty, even though 'quality-gate' is already in the list.
            assert dispatched.count('quality-gate') == 2
            assert dispatched[-1] == 'quality-gate'

    def test_just_module_tests_fires_module_tests_then_quality_sweep(self):
        """Tests-only candidate set → only module-tests in verification_steps,
        then Step 11b appends a single quality-gate sweep."""
        with PlanContext(plan_id='p5-tests-only'):
            cmd_compose(
                _compose_ns(
                    'p5-tests-only',
                    change_type='verification',
                    scope_estimate='single_module',
                    affected_files_count=4,
                    phase_5_steps='quality-gate,module-tests,coverage',
                )
            )
            manifest = read_manifest('p5-tests-only')
            assert manifest is not None
            assert manifest['phase_5']['verification_steps'] == ['module-tests']

            dispatched = _derive_executor_dispatch(manifest)
            assert dispatched == ['module-tests', 'quality-gate'], (
                f'tests-only manifest must dispatch [module-tests, quality-gate] '
                f'(per-task + Step 11b sweep), got {dispatched}'
            )
            # Exactly ONE quality-gate sweep — Step 11b never doubles up.
            assert dispatched.count('quality-gate') == 1

    def test_empty_verification_list_skips_final_quality_sweep(self):
        """Docs-only plans: verification_steps == [] → no per-task verification
        and **no** Step 11b sweep. Phase 11b skip rule fires."""
        with PlanContext(plan_id='p5-docs-only'):
            cmd_compose(
                _compose_ns(
                    'p5-docs-only',
                    change_type='tech_debt',
                    scope_estimate='surgical',
                    affected_files_count=3,
                    # Docs-only candidate set: no module-tests/coverage.
                    phase_5_steps='quality-gate',
                )
            )
            manifest = read_manifest('p5-docs-only')
            assert manifest is not None
            # Docs-only row of the matrix produces an empty verification list.
            assert manifest['phase_5']['verification_steps'] == []
            assert manifest['phase_5']['early_terminate'] is False

            dispatched = _derive_executor_dispatch(manifest)
            assert dispatched == [], (
                'Empty verification_steps must skip Step 11b sweep entirely '
                f'(no quality-gate appended), got {dispatched}'
            )

    def test_quality_gate_already_last_still_appends_sweep(self):
        """Pins SKILL.md Step 11b contract: when verification_steps is
        non-empty, the final sweep is appended UNCONDITIONALLY — even when
        'quality-gate' is already the last entry in the list.

        SKILL.md Step 11b ("exactly one quality sweep, regardless of whether
        quality-gate already appears in the list") is the binding contract;
        this test catches any future drift toward a "skip if already last"
        optimization that would silently change end-of-phase semantics.
        """
        with PlanContext(plan_id='p5-qg-last'):
            cmd_compose(
                _compose_ns(
                    'p5-qg-last',
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=8,
                    # Order matters — the Rule 7 default path passes
                    # candidates through verbatim, so this manifest will end
                    # with 'quality-gate'.
                    phase_5_steps='module-tests,quality-gate',
                )
            )
            manifest = read_manifest('p5-qg-last')
            assert manifest is not None
            assert manifest['phase_5']['verification_steps'] == [
                'module-tests',
                'quality-gate',
            ], 'Manifest must preserve declared candidate order'

            dispatched = _derive_executor_dispatch(manifest)

            # Sweep is appended even though the list already ends with
            # 'quality-gate' — two quality-gate occurrences in total.
            assert dispatched == [
                'module-tests',
                'quality-gate',
                'quality-gate',
            ], f'Step 11b sweep must append even when manifest list already ends with quality-gate, got {dispatched}'
            assert dispatched.count('quality-gate') == 2

    def test_early_terminate_skips_entire_execute_loop(self):
        """early_terminate=true (analysis with empty affected files) → executor
        transitions directly to phase-6-finalize. ZERO steps fire (no per-task
        verification, no Step 11b sweep)."""
        with PlanContext(plan_id='p5-early-term'):
            cmd_compose(
                _compose_ns(
                    'p5-early-term',
                    change_type='analysis',
                    scope_estimate='none',
                    affected_files_count=0,
                )
            )
            manifest = read_manifest('p5-early-term')
            assert manifest is not None
            assert manifest['phase_5']['early_terminate'] is True

            dispatched = _derive_executor_dispatch(manifest)
            assert dispatched == [], (
                'early_terminate=true must skip entire execute loop including '
                f'Step 11b sweep, got dispatch={dispatched}'
            )
            # Defensive: zero quality-gate dispatches under early_terminate —
            # the sweep is gated on verification_steps non-empty, which is
            # vacuously false here.
            assert 'quality-gate' not in dispatched


# ===========================================================================
# SKILL.md narrative-contract tests — pin the documented workflow that the
# manifest-executor depends on. If a future edit removes these markers, the
# manifest-driven contract has been broken.
# ===========================================================================


class TestSkillMdManifestNarrative:
    """The phase-5-execute SKILL.md must inline the manifest-driven contract."""

    @pytest.fixture(scope='class')
    def skill_md_text(self) -> str:
        return _PHASE_5_SKILL_MD.read_text(encoding='utf-8')

    def test_step_2_reads_execution_manifest(self, skill_md_text: str):
        """Step 2 must read the manifest via manage-execution-manifest read."""
        assert 'manage-execution-manifest' in skill_md_text
        assert 'read --plan-id {plan_id}' in skill_md_text, 'Step 2 must include the canonical manifest read invocation'

    def test_early_terminate_short_circuit_documented(self, skill_md_text: str):
        """Step 2 must document the early_terminate → phase-6 short-circuit."""
        assert 'early_terminate' in skill_md_text
        assert 'phase-6-finalize' in skill_md_text
        # The short-circuit must explicitly skip the execute loop.
        assert 'skip' in skill_md_text.lower()

    def test_step_11b_final_quality_sweep_documented(self, skill_md_text: str):
        """Step 11b must document the single canonical quality-gate sweep."""
        assert 'Step 11b' in skill_md_text, 'Step 11b "Final Quality Sweep" must be documented in SKILL.md'
        assert 'Final Quality Sweep' in skill_md_text or 'quality sweep' in skill_md_text.lower()
        # The sweep must be conditional on verification_steps being non-empty.
        assert 'verification_steps' in skill_md_text
        # Architecture API resolves the canonical quality-gate command.
        assert 'quality-gate' in skill_md_text
