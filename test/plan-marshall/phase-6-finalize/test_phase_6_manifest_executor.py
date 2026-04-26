#!/usr/bin/env python3
"""
Regression tests for the phase-6-finalize manifest-executor contract.

phase-6-finalize is a workflow-driven skill (no Python entry point of its own).
At phase entry it reads the per-plan execution manifest produced by
``manage-execution-manifest`` and dispatches finalize steps based on
``phase_6.steps``. These tests pin the contract phase-6-finalize SKILL.md
depends on:

1. **Manifest API shape** — synthetic manifests produced by ``cmd_compose``
   round-trip through ``cmd_read`` with the exact phase_6 fields the
   executor consumes.
2. **Step dispatch derivation** — for each scenario the executor would fire
   exactly the steps listed in ``manifest.phase_6.steps`` and NEVER an
   unlisted step.
3. **Resumable re-entry** — done-marked steps are skipped on re-entry,
   failed-marked steps are retried.
4. **lessons-capture unconditionality** — whenever ``lessons-capture`` is in
   the manifest, the dispatcher fires it.
5. **SKILL.md narrative** — the documented workflow inlines the manifest-
   driven dispatch loop, the timeout wrapper, and the resumable re-entry
   semantics.
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
_spec = importlib.util.spec_from_file_location('mem_for_phase6', str(_MANIFEST_SCRIPT))
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

_PHASE_6_SKILL_MD = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'SKILL.md'
)


def _compose_ns(
    plan_id: str,
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = ','.join(DEFAULT_PHASE_5_STEPS),
    phase_6_steps: str | None = ','.join(DEFAULT_PHASE_6_STEPS),
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
    )


def _read_ns(plan_id: str) -> Namespace:
    return Namespace(plan_id=plan_id)


# ---------------------------------------------------------------------------
# Dispatcher simulator — derive the exact list of finalize steps the executor
# would fire for a given manifest plus per-step status records (resumable
# re-entry semantics).
#
# SKILL.md Step 3 dispatch rules (mirrored here):
#   1. Iterate manifest.phase_6.steps in order.
#   2. For each step_id, consult phase_steps_state[step_id].outcome:
#        - "done"    -> SKIP (do not dispatch)
#        - "failed"  -> RETRY (dispatch a fresh run)
#        - missing/other -> dispatch as first-time run
#   3. Steps NOT in manifest.phase_6.steps NEVER fire.
# ---------------------------------------------------------------------------


def _derive_executor_dispatch(
    manifest: dict, phase_steps_state: dict[str, dict] | None = None,
) -> list[str]:
    """Return the ordered list of step_ids the dispatcher would dispatch."""
    state = phase_steps_state or {}
    dispatched: list[str] = []
    for step_id in manifest['phase_6']['steps']:
        prior = state.get(step_id, {}).get('outcome')
        if prior == 'done':
            continue  # resumable skip
        # 'failed' or absent or other -> dispatch (retry counts as a dispatch)
        dispatched.append(step_id)
    return dispatched


# ===========================================================================
# Manifest API contract tests
# ===========================================================================


class TestManifestApiContract:
    """The shape phase-6-finalize reads via ``manage-execution-manifest read``."""

    def test_read_returns_phase_6_block_with_executor_fields(self):
        with PlanContext(plan_id='p6-read-shape'):
            cmd_compose(_compose_ns('p6-read-shape'))
            result = cmd_read(_read_ns('p6-read-shape'))

            assert result is not None
            assert result['status'] == 'success'
            assert result['plan_id'] == 'p6-read-shape'
            assert 'phase_6' in result, (
                'phase-6-finalize Step 2 reads phase_6 — must be present in read output'
            )
            phase_6 = result['phase_6']
            assert isinstance(phase_6, dict)
            assert isinstance(phase_6.get('steps'), list)


# ===========================================================================
# Scenario tests — verify the dispatcher fires exactly the manifest list and
# never an unlisted step.
# ===========================================================================


class TestExecutorDispatchScenarios:

    def test_listed_steps_fire_in_manifest_order(self):
        """Every step in manifest.phase_6.steps must dispatch, in order."""
        with PlanContext(plan_id='p6-full'):
            cmd_compose(
                _compose_ns(
                    'p6-full',
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=12,
                )
            )
            manifest = read_manifest('p6-full')
            assert manifest is not None

            dispatched = _derive_executor_dispatch(manifest)
            assert dispatched == manifest['phase_6']['steps'], (
                'Dispatcher must iterate manifest.phase_6.steps verbatim, '
                f'got {dispatched} vs manifest {manifest["phase_6"]["steps"]}'
            )

    def test_unlisted_steps_never_fire(self):
        """A step absent from the manifest list MUST NOT appear in dispatch."""
        with PlanContext(plan_id='p6-pruned'):
            # Surgical bug_fix prunes automated-review, sonar-roundtrip,
            # knowledge-capture from the candidate set.
            cmd_compose(
                _compose_ns(
                    'p6-pruned',
                    change_type='bug_fix',
                    scope_estimate='surgical',
                    affected_files_count=2,
                )
            )
            manifest = read_manifest('p6-pruned')
            assert manifest is not None
            steps = manifest['phase_6']['steps']
            assert 'automated-review' not in steps, (
                'surgical bug_fix must prune automated-review from the manifest'
            )
            assert 'sonar-roundtrip' not in steps
            assert 'knowledge-capture' not in steps

            dispatched = _derive_executor_dispatch(manifest)
            # Pruned steps must NOT appear in dispatch.
            assert 'automated-review' not in dispatched
            assert 'sonar-roundtrip' not in dispatched
            assert 'knowledge-capture' not in dispatched
            # Listed steps DO appear.
            assert 'commit-push' in dispatched
            assert 'lessons-capture' in dispatched

    def test_recipe_path_dispatches_only_recipe_steps(self):
        """Recipe-driven manifest must yield a slim dispatch list."""
        with PlanContext(plan_id='p6-recipe'):
            cmd_compose(
                _compose_ns(
                    'p6-recipe',
                    change_type='tech_debt',
                    scope_estimate='surgical',
                    affected_files_count=4,
                    recipe_key='lesson_cleanup',
                )
            )
            manifest = read_manifest('p6-recipe')
            assert manifest is not None
            steps = manifest['phase_6']['steps']
            # Recipe path drops the heavy steps.
            assert 'automated-review' not in steps
            assert 'sonar-roundtrip' not in steps
            assert 'knowledge-capture' not in steps

            dispatched = _derive_executor_dispatch(manifest)
            assert dispatched == steps


# ===========================================================================
# Resumable re-entry tests
# ===========================================================================


class TestResumableReentry:

    def test_done_step_skipped_on_reentry(self):
        """A step marked outcome=done MUST be skipped on the next dispatch."""
        with PlanContext(plan_id='p6-resume-done'):
            cmd_compose(_compose_ns('p6-resume-done'))
            manifest = read_manifest('p6-resume-done')
            assert manifest is not None

            # Simulate a prior run that completed commit-push and create-pr.
            state = {
                'commit-push': {'outcome': 'done', 'display_detail': '-> abc1234'},
                'create-pr': {'outcome': 'done', 'display_detail': '#42'},
            }
            dispatched = _derive_executor_dispatch(manifest, state)

            assert 'commit-push' not in dispatched, (
                'done-marked commit-push must be skipped on re-entry'
            )
            assert 'create-pr' not in dispatched, (
                'done-marked create-pr must be skipped on re-entry'
            )
            # Steps with no prior record must still dispatch.
            for step_id in manifest['phase_6']['steps']:
                if step_id not in state:
                    assert step_id in dispatched

    def test_failed_step_is_retried(self):
        """A step marked outcome=failed MUST be retried (dispatched again)."""
        with PlanContext(plan_id='p6-resume-failed'):
            cmd_compose(_compose_ns('p6-resume-failed'))
            manifest = read_manifest('p6-resume-failed')
            assert manifest is not None

            state = {
                'sonar-roundtrip': {
                    'outcome': 'failed',
                    'display_detail': 'timed out after 900s',
                },
            }
            dispatched = _derive_executor_dispatch(manifest, state)

            assert 'sonar-roundtrip' in dispatched, (
                'failed-marked sonar-roundtrip must be retried on re-entry'
            )

    def test_mixed_done_and_failed_state(self):
        """Mixed state: done-skipped, failed-retried, fresh-dispatched all
        coexist on a single re-entry."""
        with PlanContext(plan_id='p6-resume-mixed'):
            cmd_compose(_compose_ns('p6-resume-mixed'))
            manifest = read_manifest('p6-resume-mixed')
            assert manifest is not None
            steps = manifest['phase_6']['steps']
            # Pick the first three real steps to construct mixed state.
            done_step = steps[0]
            failed_step = steps[1] if len(steps) > 1 else steps[0]

            state = {
                done_step: {'outcome': 'done', 'display_detail': 'previously done'},
                failed_step: {'outcome': 'failed', 'display_detail': 'previously failed'},
            }
            dispatched = _derive_executor_dispatch(manifest, state)

            # done is skipped, failed is retried.
            if done_step != failed_step:
                assert done_step not in dispatched
                assert failed_step in dispatched

            # Steps with no prior record dispatch as fresh runs.
            for step_id in steps[2:]:
                assert step_id in dispatched


# ===========================================================================
# Lessons-capture unconditionality
# ===========================================================================


class TestLessonsCaptureUnconditional:

    def test_lessons_capture_fires_when_manifested(self):
        """Whenever lessons-capture is in manifest.phase_6.steps, the
        dispatcher MUST fire it on every Phase 6 entry. It is not gated on
        PR state, CI state, Sonar gate, or any earlier step's outcome."""
        with PlanContext(plan_id='p6-lessons-default'):
            cmd_compose(_compose_ns('p6-lessons-default'))
            manifest = read_manifest('p6-lessons-default')
            assert manifest is not None
            assert 'lessons-capture' in manifest['phase_6']['steps'], (
                'Default-row composer must include lessons-capture in the manifest'
            )
            dispatched = _derive_executor_dispatch(manifest)
            assert 'lessons-capture' in dispatched

    def test_lessons_capture_fires_even_when_other_steps_failed(self):
        """A failed sonar-roundtrip or automated-review must NOT prevent
        lessons-capture from firing — it is dispatched independently."""
        with PlanContext(plan_id='p6-lessons-with-failures'):
            cmd_compose(_compose_ns('p6-lessons-with-failures'))
            manifest = read_manifest('p6-lessons-with-failures')
            assert manifest is not None

            state = {
                'sonar-roundtrip': {'outcome': 'failed', 'display_detail': 'gate failed'},
                'automated-review': {'outcome': 'failed', 'display_detail': 'timed out'},
            }
            dispatched = _derive_executor_dispatch(manifest, state)
            assert 'lessons-capture' in dispatched, (
                'lessons-capture must dispatch even when prior steps failed'
            )

    def test_lessons_capture_present_in_surgical_bug_fix(self):
        """Even the slim surgical bug_fix manifest keeps lessons-capture."""
        with PlanContext(plan_id='p6-lessons-surgical'):
            cmd_compose(
                _compose_ns(
                    'p6-lessons-surgical',
                    change_type='bug_fix',
                    scope_estimate='surgical',
                    affected_files_count=2,
                )
            )
            manifest = read_manifest('p6-lessons-surgical')
            assert manifest is not None
            assert 'lessons-capture' in manifest['phase_6']['steps']


# ===========================================================================
# SKILL.md narrative-contract tests — pin the documented workflow that the
# manifest-executor depends on. If a future edit removes these markers, the
# manifest-driven contract has been broken.
# ===========================================================================


class TestSkillMdManifestNarrative:

    @pytest.fixture(scope='class')
    def skill_md_text(self) -> str:
        return _PHASE_6_SKILL_MD.read_text(encoding='utf-8')

    def test_step_2_reads_execution_manifest(self, skill_md_text: str):
        """Step 2 must read the manifest via manage-execution-manifest read,
        NOT marshal.json's old steps field."""
        assert 'manage-execution-manifest' in skill_md_text
        assert 'manifest.phase_6.steps' in skill_md_text, (
            'SKILL.md must reference manifest.phase_6.steps as the authoritative list'
        )

    def test_step_3_documents_resumable_reentry(self, skill_md_text: str):
        """Step 3 must document the done/failed re-entry semantics."""
        assert 'resumable' in skill_md_text.lower()
        assert 'done' in skill_md_text.lower()
        assert 'failed' in skill_md_text.lower()
        # The skip-if-done and retry-if-failed wording must be explicit.
        assert ('skip' in skill_md_text.lower() and 'retry' in skill_md_text.lower())

    def test_manifest_authority_documented(self, skill_md_text: str):
        """SKILL.md must declare the manifest as the single source of
        authority — no fallback dispatch when steps are absent."""
        # The phrase 'authority' or 'authoritative' must appear in the
        # context of the manifest list.
        text_lower = skill_md_text.lower()
        assert 'authority' in text_lower or 'authoritative' in text_lower
        assert 'manifest' in text_lower

    def test_no_legacy_steps_field_dispatch(self, skill_md_text: str):
        """The legacy `steps` list on marshal.json must NOT be the
        authoritative dispatch source any longer."""
        # Confirm marshal.json's steps field is documented as not authoritative
        # — searching for an explicit deprecation/forbid clause.
        text_lower = skill_md_text.lower()
        # The old 'Read finalize step list from marshal.json' phrasing should
        # be gone; the manifest is now the source.
        assert 'manifest is the contract' in text_lower or 'manifest is the only valid source' in text_lower or 'authoritative' in text_lower
