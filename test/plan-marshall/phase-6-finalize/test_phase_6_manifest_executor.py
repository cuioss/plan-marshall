#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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

from conftest import MARKETPLACE_ROOT

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

_PHASE_6_SKILL_MD = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'SKILL.md'


def _compose_ns(
    plan_id: str,
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = ','.join(DEFAULT_PHASE_5_STEPS),
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
    manifest: dict,
    phase_steps_state: dict[str, dict] | None = None,
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

    def test_read_returns_phase_6_block_with_executor_fields(self, plan_context):
        plan_context.plan_dir_for('p6-read-shape')
        cmd_compose(_compose_ns('p6-read-shape'))
        result = cmd_read(_read_ns('p6-read-shape'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['plan_id'] == 'p6-read-shape'
        assert 'phase_6' in result, 'phase-6-finalize Step 2 reads phase_6 — must be present in read output'
        phase_6 = result['phase_6']
        assert isinstance(phase_6, dict)
        assert isinstance(phase_6.get('steps'), list)


# ===========================================================================
# Scenario tests — verify the dispatcher fires exactly the manifest list and
# never an unlisted step.
# ===========================================================================


class TestExecutorDispatchScenarios:
    def test_listed_steps_fire_in_manifest_order(self, plan_context):
        """Every step in manifest.phase_6.steps must dispatch, in order."""
        plan_context.plan_dir_for('p6-full')
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

    def test_unlisted_steps_never_fire(self, plan_context):
        """A step absent from the manifest list MUST NOT appear in dispatch.

        Under the new precondition-resolver model (lesson 2026-05-15-14-002),
        Row 5 surgical_bug_fix RETAINS the review gates — the legacy
        ``ci-wait`` step is dropped defensively, but ``automated-review``
        and ``sonar-roundtrip`` are kept. ``knowledge-capture`` is unrelated
        to this lesson's contract; it stays out of the candidate list here.
        """
        plan_context.plan_dir_for('p6-pruned')
        # Inject legacy ci-wait (not in default set after the lesson)
        # to test that the defensive narrowing drops it from dispatch.
        candidates = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
        cmd_compose(
            _compose_ns(
                'p6-pruned',
                change_type='bug_fix',
                scope_estimate='surgical',
                affected_files_count=2,
                phase_6_steps=','.join(candidates),
            )
        )
        manifest = read_manifest('p6-pruned')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # Row 5 retains the review gates under the new contract.
        assert 'automated-review' in steps, (
            'surgical bug_fix MUST retain automated-review under the new '
            'precondition-resolver contract'
        )
        assert 'sonar-roundtrip' in steps, (
            'surgical bug_fix MUST retain sonar-roundtrip under the new '
            'precondition-resolver contract'
        )
        # ci-wait is defensively narrowed out.
        assert 'ci-wait' not in steps

        dispatched = _derive_executor_dispatch(manifest)
        # Pruned step must NOT appear in dispatch.
        assert 'ci-wait' not in dispatched
        # Retained steps DO appear.
        assert 'commit-push' in dispatched
        assert 'lessons-capture' in dispatched
        assert 'automated-review' in dispatched
        assert 'sonar-roundtrip' in dispatched

    def test_recipe_path_dispatches_only_recipe_steps(self, plan_context):
        """Recipe-driven manifest must yield a slim dispatch list.

        Under the new precondition-resolver contract (lesson 2026-05-15-14-002)
        Row 2 (recipe) RETAINS review gates — ``automated-review`` and
        ``sonar-roundtrip`` survive. Only the legacy ``ci-wait`` step ID is
        defensively narrowed out when present in the candidate list.
        """
        plan_context.plan_dir_for('p6-recipe')
        candidates = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
        cmd_compose(
            _compose_ns(
                'p6-recipe',
                change_type='tech_debt',
                scope_estimate='surgical',
                affected_files_count=4,
                recipe_key='lesson_cleanup',
                phase_6_steps=','.join(candidates),
            )
        )
        manifest = read_manifest('p6-recipe')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # Review gates RETAINED under the new contract.
        assert 'automated-review' in steps, (
            'recipe row MUST retain automated-review under the new contract'
        )
        assert 'sonar-roundtrip' in steps, (
            'recipe row MUST retain sonar-roundtrip under the new contract'
        )
        # Legacy ci-wait defensively dropped.
        assert 'ci-wait' not in steps

        dispatched = _derive_executor_dispatch(manifest)
        assert dispatched == steps


# ===========================================================================
# Resumable re-entry tests
# ===========================================================================


class TestResumableReentry:
    def test_done_step_skipped_on_reentry(self, plan_context):
        """A step marked outcome=done MUST be skipped on the next dispatch."""
        plan_context.plan_dir_for('p6-resume-done')
        cmd_compose(_compose_ns('p6-resume-done'))
        manifest = read_manifest('p6-resume-done')
        assert manifest is not None

        # Simulate a prior run that completed commit-push and create-pr.
        state = {
            'commit-push': {'outcome': 'done', 'display_detail': '-> abc1234'},
            'create-pr': {'outcome': 'done', 'display_detail': '#42'},
        }
        dispatched = _derive_executor_dispatch(manifest, state)

        assert 'commit-push' not in dispatched, 'done-marked commit-push must be skipped on re-entry'
        assert 'create-pr' not in dispatched, 'done-marked create-pr must be skipped on re-entry'
        # Steps with no prior record must still dispatch.
        for step_id in manifest['phase_6']['steps']:
            if step_id not in state:
                assert step_id in dispatched

    def test_failed_step_is_retried(self, plan_context):
        """A step marked outcome=failed MUST be retried (dispatched again)."""
        plan_context.plan_dir_for('p6-resume-failed')
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

        assert 'sonar-roundtrip' in dispatched, 'failed-marked sonar-roundtrip must be retried on re-entry'

    def test_mixed_done_and_failed_state(self, plan_context):
        """Mixed state: done-skipped, failed-retried, fresh-dispatched all
        coexist on a single re-entry."""
        plan_context.plan_dir_for('p6-resume-mixed')
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
    def test_lessons_capture_fires_when_manifested(self, plan_context):
        """Whenever lessons-capture is in manifest.phase_6.steps, the
        dispatcher MUST fire it on every Phase 6 entry. It is not gated on
        PR state, CI state, Sonar gate, or any earlier step's outcome."""
        plan_context.plan_dir_for('p6-lessons-default')
        cmd_compose(_compose_ns('p6-lessons-default'))
        manifest = read_manifest('p6-lessons-default')
        assert manifest is not None
        assert 'lessons-capture' in manifest['phase_6']['steps'], (
            'Default-row composer must include lessons-capture in the manifest'
        )
        dispatched = _derive_executor_dispatch(manifest)
        assert 'lessons-capture' in dispatched

    def test_lessons_capture_fires_even_when_other_steps_failed(self, plan_context):
        """A failed sonar-roundtrip or automated-review must NOT prevent
        lessons-capture from firing — it is dispatched independently."""
        plan_context.plan_dir_for('p6-lessons-with-failures')
        cmd_compose(_compose_ns('p6-lessons-with-failures'))
        manifest = read_manifest('p6-lessons-with-failures')
        assert manifest is not None

        state = {
            'sonar-roundtrip': {'outcome': 'failed', 'display_detail': 'gate failed'},
            'automated-review': {'outcome': 'failed', 'display_detail': 'timed out'},
        }
        dispatched = _derive_executor_dispatch(manifest, state)
        assert 'lessons-capture' in dispatched, 'lessons-capture must dispatch even when prior steps failed'

    def test_lessons_capture_present_in_surgical_bug_fix(self, plan_context):
        """Even the slim surgical bug_fix manifest keeps lessons-capture."""
        plan_context.plan_dir_for('p6-lessons-surgical')
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
        assert 'skip' in skill_md_text.lower() and 'retry' in skill_md_text.lower()

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
        assert (
            'manifest is the contract' in text_lower
            or 'manifest is the only valid source' in text_lower
            or 'authoritative' in text_lower
        )


# ===========================================================================
# CI-precondition contract tests — replace the obsolete sibling-step model.
# CI completion is now a dispatcher-resolved precondition declared via
# requires: [ci-complete] on consumer step frontmatters (automated-review,
# sonar-roundtrip). These tests assert (1) ci-wait is absent from the
# default candidate list, (2) automated-review and sonar-roundtrip carry
# the requires: [ci-complete] declaration in frontmatter, (3) the composer
# does not emit ci-wait before automated-review, (4) Rules 2/3/5 retain
# both review gates rather than silently dropping them with ci-wait.
# ===========================================================================


_AUTOMATED_REVIEW_FRONTMATTER = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'workflow'
    / 'automated-review.md'
)
_SONAR_ROUNDTRIP_FRONTMATTER = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'workflow'
    / 'sonar-roundtrip.md'
)


class TestCIPreconditionContract:
    """Dispatcher-resolved precondition replaces the sibling ci-wait step."""

    def test_ci_wait_absent_from_default_phase_6_steps(self):
        """The default candidate list MUST NOT contain ``ci-wait`` — CI
        completion is now a dispatcher-resolved precondition, not a step.
        """
        assert 'ci-wait' not in DEFAULT_PHASE_6_STEPS, (
            'ci-wait must not appear in DEFAULT_PHASE_6_STEPS — CI completion '
            'is resolved via requires: [ci-complete] on consumer steps'
        )

    def test_automated_review_declares_requires_ci_complete(self):
        """``automated-review.md`` frontmatter MUST declare
        ``requires: [ci-complete]`` so the dispatcher resolves the
        precondition before invoking the consumer body.
        """
        text = _AUTOMATED_REVIEW_FRONTMATTER.read_text(encoding='utf-8')
        # Limit the scan to the YAML frontmatter block (the leading --- ... ---).
        head, sep, _rest = text.partition('\n---\n')
        # head is "---\nname: ..."; the second --- is the closing fence we
        # captured via sep. Inspect head for the requires: line.
        assert sep == '\n---\n', (
            'automated-review.md must start with a YAML frontmatter block'
        )
        assert 'requires: [ci-complete]' in head, (
            'automated-review.md frontmatter MUST declare requires: '
            '[ci-complete]; got head=\n' + head
        )

    def test_sonar_roundtrip_declares_requires_ci_complete(self):
        """``sonar-roundtrip.md`` frontmatter MUST declare
        ``requires: [ci-complete]`` so the dispatcher resolves the
        precondition before invoking the consumer body.
        """
        text = _SONAR_ROUNDTRIP_FRONTMATTER.read_text(encoding='utf-8')
        head, sep, _rest = text.partition('\n---\n')
        assert sep == '\n---\n', (
            'sonar-roundtrip.md must start with a YAML frontmatter block'
        )
        assert 'requires: [ci-complete]' in head, (
            'sonar-roundtrip.md frontmatter MUST declare requires: '
            '[ci-complete]; got head=\n' + head
        )

    def test_composer_does_not_emit_ci_wait_before_automated_review(self, plan_context):
        """On a default-row plan, the composed manifest MUST NOT carry
        ``ci-wait`` anywhere — the legacy sibling-step ordering is gone.
        """
        plan_context.plan_dir_for('p6-precond-default')
        cmd_compose(
            _compose_ns(
                'p6-precond-default',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=8,
            )
        )
        manifest = read_manifest('p6-precond-default')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        assert 'ci-wait' not in steps, (
            f'default-row composer MUST NOT emit ci-wait; got steps {steps}'
        )
        assert 'automated-review' in steps, (
            'default-row composer must still include automated-review'
        )

    def test_recipe_path_retains_review_gates(self, plan_context):
        """Row 2 (recipe) — review gates RETAINED. The legacy ``ci-wait``
        step ID is defensively narrowed out when present in the candidate
        list, but ``automated-review`` and ``sonar-roundtrip`` are never
        silently suppressed by the planner.
        """
        plan_context.plan_dir_for('p6-precond-recipe')
        # Inject legacy ci-wait to test defensive narrowing.
        candidates = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
        cmd_compose(
            _compose_ns(
                'p6-precond-recipe',
                change_type='tech_debt',
                scope_estimate='surgical',
                affected_files_count=4,
                recipe_key='lesson_cleanup',
                phase_6_steps=','.join(candidates),
            )
        )
        manifest = read_manifest('p6-precond-recipe')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        assert 'automated-review' in steps, (
            'recipe row MUST retain automated-review — review gates are '
            'never silently suppressed'
        )
        assert 'sonar-roundtrip' in steps, (
            'recipe row MUST retain sonar-roundtrip — review gates are '
            'never silently suppressed'
        )
        assert 'ci-wait' not in steps, (
            'recipe row MUST defensively drop legacy ci-wait step ID'
        )

    def test_docs_only_retains_review_gates(self, plan_context):
        """Row 3 (docs_only) — review gates RETAINED. Same retention contract
        as Rules 2 and 5: review bots run even on docs-only plans.
        """
        plan_context.plan_dir_for('p6-precond-docs')
        candidates = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
        cmd_compose(
            _compose_ns(
                'p6-precond-docs',
                change_type='tech_debt',
                scope_estimate='surgical',
                affected_files_count=3,
                phase_5_steps='quality-gate',
                phase_6_steps=','.join(candidates),
            )
        )
        manifest = read_manifest('p6-precond-docs')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        assert 'automated-review' in steps, (
            'docs_only row MUST retain automated-review'
        )
        assert 'sonar-roundtrip' in steps, (
            'docs_only row MUST retain sonar-roundtrip'
        )
        assert 'ci-wait' not in steps, (
            'docs_only row MUST defensively drop legacy ci-wait step ID'
        )

    def test_surgical_bug_fix_retains_review_gates(self, plan_context):
        """Row 5 (surgical_bug_fix / surgical_tech_debt) — review gates
        RETAINED. The bots' job is to catch what humans miss on one-line
        fixes; silently dropping the review gates would defeat that.
        """
        plan_context.plan_dir_for('p6-precond-surgical-bug')
        candidates = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
        cmd_compose(
            _compose_ns(
                'p6-precond-surgical-bug',
                change_type='bug_fix',
                scope_estimate='surgical',
                affected_files_count=2,
                phase_6_steps=','.join(candidates),
            )
        )
        manifest = read_manifest('p6-precond-surgical-bug')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        assert 'automated-review' in steps, (
            'surgical_bug_fix row MUST retain automated-review'
        )
        assert 'sonar-roundtrip' in steps, (
            'surgical_bug_fix row MUST retain sonar-roundtrip'
        )
        assert 'ci-wait' not in steps, (
            'surgical_bug_fix row MUST defensively drop legacy ci-wait step ID'
        )

    def test_automated_review_md_does_not_read_ci_wait_outcome(self):
        """The ``automated-review.md`` body MUST NOT include the legacy
        sibling-step prose that read the ``phase_steps["6-finalize"]["ci-wait"].outcome``
        signal from ``manage-status``. CI completion is now a precondition
        guaranteed by the dispatcher before the body executes.
        """
        text = _AUTOMATED_REVIEW_FRONTMATTER.read_text(encoding='utf-8')
        # The "Read completed-CI signal" section header must be gone.
        assert '### Read completed-CI signal' not in text, (
            'automated-review.md MUST NOT carry a "Read completed-CI signal" '
            'section — that contract is now owned by the dispatcher precondition'
        )
        # The specific phase_steps signal lookup string must be gone.
        assert 'phase_steps["6-finalize"]["ci-wait"]' not in text, (
            'automated-review.md MUST NOT read phase_steps["6-finalize"]["ci-wait"] '
            'outcome record — that signal model has been retired'
        )


# ===========================================================================
# Automated-review precondition declaration + overflow handling tests —
# pin the documented contract: ``automated-review`` declares
# ``requires: [ci-complete]`` in its YAML frontmatter so the phase-6-finalize
# dispatcher resolves the precondition before the body runs (no inline CI
# poll, no manage-status signal hand-off). When per-iteration budget would
# be exhausted before all pr-comment findings can be triaged, the triage
# workflow files a single ``pr-comment-overflow`` finding carrying the
# unprocessed pr-comment hash_ids and records ``--outcome loop_back`` rather
# than ``done``.
# ===========================================================================


_AUTOMATED_REVIEW_MD = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'workflow'
    / 'automated-review.md'
)
_JSONL_FORMAT_MD = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'manage-findings'
    / 'standards'
    / 'jsonl-format.md'
)
_TRIAGE_MD = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-marshall'
    / 'workflow'
    / 'triage.md'
)


class TestAutomatedReviewCiSignalAndOverflow:
    """Pin the documented contract: ``automated-review`` declares
    ``requires: [ci-complete]`` in its frontmatter so the dispatcher resolves
    the precondition before the body runs (no inline CI poll, no
    manage-status signal hand-off). On near-budget exhaustion the triage
    workflow files a ``pr-comment-overflow`` finding while recording
    ``--outcome loop_back``.

    These are narrative-pinning tests on the standards docs because the
    automated-review step body is markdown-driven (no Python entry point); the
    contract is enforced at agent dispatch time, and the standards doc IS the
    source of truth. If a future edit removes any of these contract markers,
    the documented overflow + precondition contract has been silently
    broken.
    """

    @pytest.fixture(scope='class')
    def automated_review_text(self) -> str:
        return _AUTOMATED_REVIEW_MD.read_text(encoding='utf-8')

    @pytest.fixture(scope='class')
    def jsonl_format_text(self) -> str:
        return _JSONL_FORMAT_MD.read_text(encoding='utf-8')

    @pytest.fixture(scope='class')
    def triage_text(self) -> str:
        return _TRIAGE_MD.read_text(encoding='utf-8')

    # ---- Precondition declaration ---------------------------------------

    def test_automated_review_declares_requires_ci_complete_in_frontmatter(
        self, automated_review_text: str
    ):
        """``automated-review.md`` MUST declare ``requires: [ci-complete]``
        in its YAML frontmatter so the dispatcher invokes the precondition
        resolver before the body runs.
        """
        head, sep, _rest = automated_review_text.partition('\n---\n')
        assert sep == '\n---\n', (
            'automated-review.md must start with a YAML frontmatter block'
        )
        assert 'requires: [ci-complete]' in head, (
            'automated-review.md frontmatter MUST declare requires: [ci-complete]'
        )

    def test_automated_review_does_not_poll_ci_inline(
        self, automated_review_text: str
    ):
        """The legacy ``ci wait --pr-number`` polling primitive MUST NOT
        appear in the automated-review step body — that responsibility is
        owned by the dispatcher's precondition resolver. A reappearance
        would mean the consumer is double-polling CI.
        """
        assert 'ci wait \\\n  --pr-number' not in automated_review_text, (
            'automated-review.md must not invoke `ci wait --pr-number` inline; '
            'the precondition resolver owns that primitive'
        )
        # The legacy section headings MUST be gone.
        assert '### Wait for CI' not in automated_review_text, (
            'automated-review.md must not have a "Wait for CI" subsection'
        )
        assert '### Read completed-CI signal' not in automated_review_text, (
            'automated-review.md must not have a "Read completed-CI signal" '
            'subsection — CI completion is now a dispatcher-resolved precondition'
        )

    def test_automated_review_does_not_read_ci_wait_outcome_record(
        self, automated_review_text: str
    ):
        """``automated-review.md`` MUST NOT read the legacy
        ``phase_steps["6-finalize"]["ci-wait"]`` outcome record. The
        precondition resolver runs ahead of the body and surfaces
        ``wait_failed`` to the dispatcher, not to the body.
        """
        assert 'phase_steps["6-finalize"]["ci-wait"]' not in automated_review_text, (
            'automated-review.md must not read the legacy ci-wait outcome record'
        )

    def test_timeout_contract_describes_precondition_split(
        self, automated_review_text: str
    ):
        """The 900 s budget remains ``triage-only``; CI wait wall-clock is
        now bounded by the dispatcher's ``ci-complete`` precondition
        resolver (600 s ceiling). The contract MUST say so explicitly so a
        future edit doesn't restore the combined-budget shape.
        """
        text_lower = automated_review_text.lower()
        assert 'triage-only' in text_lower, (
            'Timeout Contract must declare the 900 s budget as triage-only'
        )
        assert 'precondition' in text_lower, (
            'Timeout Contract must reference the ci-complete precondition '
            'resolver as the CI wait-time owner'
        )

    # ---- Overflow handling -----------------------------------------------

    def test_overflow_section_documented_in_triage(
        self, triage_text: str
    ):
        """The overflow handling section MUST exist in the shared triage
        workflow so the contract is reachable from every call site that
        dispatches `cross.triage` (automated-review, sonar-roundtrip,
        phase-5-execute verification/quality-gate triage, pr-doctor)."""
        # The triage workflow numbers its steps; overflow lives at Step 5.
        assert 'Overflow' in triage_text and 'timeout' in triage_text.lower(), (
            'triage.md must document overflow / timeout handling'
        )

    def test_overflow_files_pr_comment_overflow_finding(
        self, triage_text: str
    ):
        """When the per-iteration budget is nearly exhausted, the triage
        workflow MUST file exactly one ``{finding_type}-overflow`` envelope
        finding (via ``manage-findings add``) carrying the unprocessed
        hash_ids in ``detail``. The pr-comment-specific shape (used by
        automated-review) is named explicitly in the documentation."""
        text = triage_text
        assert 'pr-comment-overflow' in text, (
            'triage.md must reference the pr-comment-overflow finding type by name'
        )
        # The documented add command uses the parameterised type form so
        # every finding_type has its own overflow envelope shape.
        assert '--type {finding_type}-overflow' in text or '--type pr-comment-overflow' in text, (
            'triage.md must invoke `manage-findings add --type {finding_type}-overflow`'
        )
        assert 'unprocessed' in text.lower() and 'hash_id' in text.lower(), (
            'triage.md must document carrying the unprocessed hash_ids in --detail'
        )

    def test_overflow_returns_loop_back_outcome(
        self, triage_text: str
    ):
        """The overflow path MUST return ``outcome: loop_back`` so the
        calling manifest step (automated-review / sonar-roundtrip /
        phase-5-execute Step 11) re-fires the dispatch on the next phase entry."""
        text = triage_text
        # Locate the overflow section (between Step 5 header and Step 6).
        if 'Step 5' in text and 'Step 6' in text:
            start = text.index('Step 5')
            end = text.index('Step 6', start)
            overflow_section = text[start:end]
        else:
            overflow_section = text

        assert 'loop_back' in overflow_section, (
            'Overflow section in triage.md must return outcome: loop_back so the calling step re-fires'
        )

    def test_overflow_threshold_is_conservative(
        self, triage_text: str
    ):
        """The documented overflow heuristic MUST trigger before the wrapper
        fires — the 75 % threshold leaves enough budget for the overflow
        capture itself plus a safety margin."""
        text = triage_text
        assert '75' in text and 'budget' in text.lower(), (
            'triage.md must document a 75% budget threshold so capture happens before wrapper timeout'
        )

    # ---- pr-comment-overflow finding type contract ------------------------

    def test_pr_comment_overflow_registered_in_jsonl_format(
        self, jsonl_format_text: str
    ):
        """The ``pr-comment-overflow`` finding type MUST be enumerated in
        ``manage-findings/standards/jsonl-format.md`` so producers can ``add``
        it without an unknown-type error."""
        text = jsonl_format_text
        # Per-type file list.
        assert 'findings/pr-comment-overflow.jsonl' in text, (
            'jsonl-format.md must list pr-comment-overflow.jsonl in the per-type file enumeration'
        )
        # Required-fields type taxonomy.
        assert 'pr-comment-overflow' in text, (
            'jsonl-format.md must include pr-comment-overflow in the type taxonomy'
        )
        # Promotion table — non-promotable.
        assert '| `pr-comment-overflow` | Not promotable' in text, (
            'jsonl-format.md must list pr-comment-overflow as Not promotable in the promotion table'
        )

    def test_pr_comment_overflow_contract_documented(
        self, jsonl_format_text: str
    ):
        """The ``pr-comment-overflow`` type's purpose, ``detail`` shape, and
        resolution semantics MUST be documented in jsonl-format.md so the
        consumer's contract is greppable."""
        text = jsonl_format_text
        # Dedicated subsection.
        assert '### `pr-comment-overflow`' in text, (
            'jsonl-format.md must have a dedicated `pr-comment-overflow` subsection documenting the contract'
        )
        # Purpose: carries unprocessed pr-comment IDs from a budget-exhausted iteration.
        text_lower = text.lower()
        assert 'unprocessed' in text_lower and 'budget' in text_lower, (
            'pr-comment-overflow contract must document the budget-exhausted unprocessed-IDs purpose'
        )
        # Detail shape: list of hash_ids.
        assert 'hash_id' in text_lower and 'detail' in text_lower, (
            'pr-comment-overflow contract must document the detail shape (list of hash_ids)'
        )
        # Resolution semantics: pending until processed in subsequent iteration.
        assert 'pending' in text_lower and 'subsequent' in text_lower, (
            'pr-comment-overflow contract must document the resolution lifecycle (pending until subsequent iteration processes them)'
        )

    def test_pr_comment_overflow_is_non_blocking(
        self, jsonl_format_text: str
    ):
        """``pr-comment-overflow`` MUST be documented as non-blocking — the
        deferred work is handled by ``loop_back`` re-entry, not by gating the
        phase boundary. Marking it blocking would defeat the whole point of
        deferring overflow to the next iteration."""
        text = jsonl_format_text
        # Find the dedicated subsection and confirm the non-blocking note.
        start = text.index('### `pr-comment-overflow`')
        # Slice up to the next H2 or H3 to bound the section.
        rest = text[start:]
        # Take everything up to next "## " or "### " heading after the start.
        next_h2 = rest.find('\n## ', 1)
        next_h3 = rest.find('\n### ', 1)
        end_candidates = [c for c in (next_h2, next_h3) if c > 0]
        section = rest if not end_candidates else rest[: min(end_candidates)]
        text_lower = section.lower()
        assert 'blocking partition' in text_lower or 'does not block' in text_lower, (
            'pr-comment-overflow subsection must document non-blocking semantics so '
            'the overflow finding does not gate the phase boundary'
        )


# ===========================================================================
# Symmetric auto-continuation tests (loop_back_without_asking) — pin the
# documented contract introduced when a phase-6-finalize step's outcome=loop_back can
# re-dispatch the execute pipeline inline rather than halting and prompting
# the user. The flag is the reverse-direction symmetric counterpart to the
# forward `plan.phase-6-finalize.finalize_without_asking` knob (both are flat
# fields under plan.phase-6-finalize).
#
# Test surface mirrors the rest of this file: pin SKILL.md / workflow /
# config-defaults narrative markers because the orchestrator is workflow-
# driven (no Python entry point). The contract is enforced at dispatch time;
# the documented standards are the authoritative source.
# ===========================================================================


_CONFIG_DEFAULTS_PY = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
    / '_config_defaults.py'
)
_EXECUTION_WORKFLOW_MD = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-marshall'
    / 'workflow'
    / 'execution.md'
)
_PHASE_LIFECYCLE_MD = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'ref-workflow-architecture'
    / 'standards'
    / 'phase-lifecycle.md'
)
_MARSHAL_JSON_REFERENCE_MD = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'extension-api'
    / 'standards'
    / 'marshal-json-reference.md'
)
_MANAGE_CONFIG_SKILL_MD = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'SKILL.md'
)


class TestLoopBackWithoutAskingContract:
    """Pin the symmetric auto-continuation contract:

    1. ``plan.phase-6-finalize.loop_back_without_asking`` field exists with
       default ``False`` in the manage-config defaults surface.
    2. ``phase-6-finalize/SKILL.md`` Step 3 dispatch loop documents the
       flag-set, flag-unset, and cap-reached branches.
    3. The canonical ``[STATUS] Loop-back iteration {N}/{max}`` work-log
       line is documented.
    4. ``plan-marshall/workflow/execution.md`` carries a "Loop-back
       continuation" subsection mirroring the forward
       ``finalize_without_asking`` block.
    5. ``ref-workflow-architecture/standards/phase-lifecycle.md`` mentions
       the new flag alongside the existing forward gates.
    6. ``extension-api/standards/marshal-json-reference.md`` registers the
       config-flags row.
    """

    @pytest.fixture(scope='class')
    def phase_6_skill_md_text(self) -> str:
        return _PHASE_6_SKILL_MD.read_text(encoding='utf-8')

    @pytest.fixture(scope='class')
    def execution_workflow_text(self) -> str:
        return _EXECUTION_WORKFLOW_MD.read_text(encoding='utf-8')

    @pytest.fixture(scope='class')
    def config_defaults_text(self) -> str:
        return _CONFIG_DEFAULTS_PY.read_text(encoding='utf-8')

    @pytest.fixture(scope='class')
    def phase_lifecycle_text(self) -> str:
        return _PHASE_LIFECYCLE_MD.read_text(encoding='utf-8')

    @pytest.fixture(scope='class')
    def marshal_reference_text(self) -> str:
        return _MARSHAL_JSON_REFERENCE_MD.read_text(encoding='utf-8')

    @pytest.fixture(scope='class')
    def manage_config_skill_text(self) -> str:
        return _MANAGE_CONFIG_SKILL_MD.read_text(encoding='utf-8')

    # ---- Defaults surface ------------------------------------------------

    def test_loop_back_without_asking_default_is_false(
        self, config_defaults_text: str
    ):
        """``loop_back_without_asking`` MUST default to ``False`` — the
        asymmetric counterpart of ``finalize_without_asking=True``. Forward
        auto-continue is the common case (default ``True``); reverse
        loop-back surfaces a control return to the user so unattended runs
        cannot silently re-enter execute on a finalize-side fix. The full
        unattended cycle remains opt-in via ``loop_back_without_asking=True``.
        The knob is a flat field under ``plan.phase-6-finalize`` — the
        ``ceremony_policy`` block was dissolved and every automation knob
        distributed back into its owning phase."""
        # Locate the DEFAULT_PLAN_FINALIZE block and confirm the field is
        # declared with default False.
        assert "DEFAULT_PLAN_FINALIZE = {" in config_defaults_text, (
            'DEFAULT_PLAN_FINALIZE block must exist in _config_defaults.py'
        )
        block_start = config_defaults_text.index("DEFAULT_PLAN_FINALIZE = {")
        # Find the closing brace of the dict literal.
        block_end = config_defaults_text.index("\n}\n", block_start)
        block = config_defaults_text[block_start : block_end + 3]
        # The field MUST be present and default to False in the finalize block.
        assert "'loop_back_without_asking': False" in block, (
            'DEFAULT_PLAN_FINALIZE must declare loop_back_without_asking with default False'
        )
        # The dissolved ceremony_policy block must not survive.
        assert 'DEFAULT_CEREMONY_POLICY' not in config_defaults_text, (
            'DEFAULT_CEREMONY_POLICY must be gone after the ceremony_policy dissolution'
        )

    def test_loop_back_field_read_through_phase_get(
        self, manage_config_skill_text: str
    ):
        """The field MUST be readable via the standard
        ``plan phase-6-finalize get --field loop_back_without_asking`` shape
        (the distributed runtime read surface). The SKILL.md must document the
        flat field explicitly so callers know it is a valid surface."""
        text = manage_config_skill_text
        assert 'loop_back_without_asking' in text, (
            'manage-config SKILL.md must document loop_back_without_asking as a configurable field'
        )
        # The runtime read shape must be documented via the standard phase get verb.
        assert 'plan phase-6-finalize get --field loop_back_without_asking' in text, (
            'manage-config SKILL.md must document the '
            'plan phase-6-finalize get --field loop_back_without_asking read surface'
        )

    # ---- SKILL.md dispatch loop documentation ----------------------------

    def test_phase_6_skill_md_documents_loop_back_continuation_hook(
        self, phase_6_skill_md_text: str
    ):
        """``phase-6-finalize/SKILL.md`` Step 3 MUST declare a "Loop-back
        continuation hook" that fires when a step's recorded outcome is
        ``loop_back``."""
        text = phase_6_skill_md_text
        assert 'Loop-back continuation hook' in text, (
            'phase-6-finalize SKILL.md must declare a "Loop-back continuation hook" inside Step 3'
        )
        # Place the hook inside the Step 3 dispatch loop body — between
        # "### Step 3" and "### Step 4".
        step_3_start = text.index('### Step 3:')
        step_4_start = text.index('### Step 4:')
        step_3_body = text[step_3_start:step_4_start]
        assert 'Loop-back continuation hook' in step_3_body, (
            'Loop-back continuation hook must appear inside the Step 3 dispatch loop body, not somewhere else'
        )

    def test_phase_6_skill_md_documents_flag_unset_halt(
        self, phase_6_skill_md_text: str
    ):
        """When ``loop_back_without_asking == false`` (default), the
        dispatcher MUST halt the FOR loop and return control to the user —
        no inline re-dispatch."""
        text = phase_6_skill_md_text
        # The flag-unset branch must mention halting / returning control.
        text_lower = text.lower()
        assert 'loop_back_without_asking' in text_lower, (
            'SKILL.md must reference loop_back_without_asking by name in the hook'
        )
        # Both branches must be documented: false → halt, true → continue.
        assert 'returning control to user' in text_lower or 'return control to' in text_lower, (
            'SKILL.md must document the flag-unset halt-and-return-to-user behaviour'
        )

    def test_phase_6_skill_md_documents_flag_set_inline_dispatch(
        self, phase_6_skill_md_text: str
    ):
        """When ``loop_back_without_asking == true``, the dispatcher MUST
        re-dispatch the execute pipeline inline (Skill: phase-5-execute) and
        re-enter the FOR loop."""
        text = phase_6_skill_md_text
        # The flag-set branch must reference dispatching phase-5-execute inline.
        assert 'Skill: plan-marshall:phase-5-execute' in text, (
            'SKILL.md flag-set branch must dispatch Skill: plan-marshall:phase-5-execute inline'
        )
        # And it must re-enter the FOR loop (resumable re-entry semantics).
        text_lower = text.lower()
        assert 're-enter' in text_lower and 'for loop' in text_lower, (
            'SKILL.md flag-set branch must document re-entering the FOR loop after the inline execute returns'
        )

    def test_phase_6_skill_md_documents_max_iterations_cap(
        self, phase_6_skill_md_text: str
    ):
        """The loop-back hook MUST cap the inline re-entry at
        ``phase-6-finalize.max_iterations`` (default 3). Beyond that, the
        dispatcher halts and prompts the user EVEN WITH the flag set — the
        ceiling is the structural safety valve."""
        text = phase_6_skill_md_text
        # The cap-reached branch must reference max_iterations.
        assert 'max_iterations' in text, (
            'SKILL.md hook must reference max_iterations as the loop-back ceiling'
        )
        # And must explicitly halt-and-prompt on cap exhaustion.
        text_lower = text.lower()
        assert 'ceiling' in text_lower or 'cap' in text_lower, (
            'SKILL.md hook must document the cap as a structural safety valve'
        )

    def test_phase_6_skill_md_documents_iteration_log_line(
        self, phase_6_skill_md_text: str
    ):
        """The canonical ``[STATUS] Loop-back iteration {N}/{max}`` work-log
        line MUST be documented so retrospective analysis can grep for it."""
        text = phase_6_skill_md_text
        # The literal line shape — substring match (the runtime substitutes
        # the placeholders).
        assert '[STATUS]' in text, 'SKILL.md must use the canonical [STATUS] log marker'
        assert 'Loop-back iteration' in text, (
            'SKILL.md must document the "Loop-back iteration" log-line text'
        )
        # The {N}/{max} shape must be visible (placeholders or actual count
        # syntax).
        assert (
            '{loop_back_iteration}/{max_iterations}' in text
            or '{N}/{max}' in text
        ), (
            'SKILL.md must show the iteration counter shape ({N}/{max} or named placeholders)'
        )

    def test_phase_6_skill_md_documents_truth_table(
        self, phase_6_skill_md_text: str
    ):
        """The four-corner truth table for the symmetric flag pair MUST be
        documented so the interaction with ``finalize_without_asking`` is
        explicit (forward + reverse)."""
        text = phase_6_skill_md_text
        text_lower = text.lower()
        # Every corner of the table must be reachable in prose.
        assert 'symmetric auto-continuation' in text_lower, (
            'SKILL.md must document a "symmetric auto-continuation" invariant block'
        )
        # The two flags must be cross-referenced.
        assert 'finalize_without_asking' in text and 'loop_back_without_asking' in text, (
            'SKILL.md truth table must reference both flags'
        )

    # ---- workflow/execution.md "Loop-back continuation" subsection -----

    def test_execution_workflow_has_loop_back_continuation_subsection(
        self, execution_workflow_text: str
    ):
        """``plan-marshall/workflow/execution.md`` MUST carry a "Loop-back
        continuation" subsection that mirrors the existing forward
        ``finalize_without_asking`` block."""
        text = execution_workflow_text
        assert '### Loop-back continuation' in text, (
            'execution.md must declare a "### Loop-back continuation" subsection'
        )
        # The new subsection must live in the Finalize Phase region.
        finalize_start = text.index('## Finalize Phase')
        loopback_pos = text.index('### Loop-back continuation')
        assert loopback_pos > finalize_start, (
            'Loop-back continuation must appear inside the Finalize Phase region of execution.md'
        )

    def test_execution_workflow_documents_both_branches(
        self, execution_workflow_text: str
    ):
        """The "Loop-back continuation" subsection MUST document both the
        flag-set (auto-continue) and flag-unset (STOP and prompt) branches —
        the same shape as the forward ``finalize_without_asking`` block."""
        text = execution_workflow_text
        start = text.index('### Loop-back continuation')
        # Slice to the end of the section (next heading).
        rest = text[start:]
        next_section_idx = rest.find('\n### ', 1)
        if next_section_idx < 0:
            next_section_idx = rest.find('\n## ', 1)
        section = rest if next_section_idx < 0 else rest[:next_section_idx]
        text_lower = section.lower()
        # Branch markers.
        assert 'loop_back_without_asking == true' in text_lower, (
            'Loop-back continuation must document the flag-set branch'
        )
        assert 'else' in text_lower or 'otherwise' in text_lower, (
            'Loop-back continuation must document the flag-unset branch'
        )
        # Halt marker for the flag-unset branch.
        assert 'stop' in text_lower, (
            'Flag-unset branch must explicitly STOP rather than continuing'
        )
        # Auto-continue marker for the flag-set branch.
        assert 'auto-continu' in text_lower, (
            'Flag-set branch must reference auto-continuation'
        )

    def test_execution_workflow_documents_double_gate(
        self, execution_workflow_text: str
    ):
        """The Loop-back continuation subsection MUST document that symmetric
        loop-back is doubly-gated by both flags in series — both
        ``loop_back_without_asking`` AND ``finalize_without_asking`` must be
        ``true`` for full unattended cycles."""
        text = execution_workflow_text
        start = text.index('### Loop-back continuation')
        rest = text[start:]
        next_section_idx = rest.find('\n### ', 1)
        if next_section_idx < 0:
            next_section_idx = rest.find('\n## ', 1)
        section = rest if next_section_idx < 0 else rest[:next_section_idx]
        # The double-gate is the load-bearing semantic: both flags appear
        # together in this section.
        assert 'finalize_without_asking' in section, (
            'Loop-back continuation must reference finalize_without_asking to document the double-gate'
        )

    # ---- Sibling notes in cross-references --------------------------------

    def test_phase_lifecycle_mentions_loop_back_alongside_forward_gates(
        self, phase_lifecycle_text: str
    ):
        """``ref-workflow-architecture/standards/phase-lifecycle.md`` MUST
        mention ``loop_back_without_asking`` alongside the existing forward
        gates (``plan_without_asking`` / ``execute_without_asking`` /
        ``finalize_without_asking``) so the reverse-direction sibling is
        discoverable from the lifecycle reference."""
        text = phase_lifecycle_text
        assert 'loop_back_without_asking' in text, (
            'phase-lifecycle.md must mention loop_back_without_asking as a config flag'
        )
        # The mention must be near the existing review-gates list.
        gates_idx = text.index('plan_without_asking')
        loopback_idx = text.index('loop_back_without_asking')
        # Within ~600 characters of the existing gates list.
        assert abs(loopback_idx - gates_idx) < 600, (
            'loop_back_without_asking must be documented next to the existing review gates, '
            'not in an unrelated section'
        )

    def test_marshal_json_reference_registers_the_field(
        self, marshal_reference_text: str
    ):
        """``extension-api/standards/marshal-json-reference.md`` MUST register
        ``plan.phase-6-finalize.loop_back_without_asking`` near the existing
        ``finalize_without_asking`` row.

        The three auto-continuation knobs are flat fields under
        ``plan.phase-6-finalize`` — the ``ceremony_policy`` block was dissolved
        and every automation knob distributed back into its owning phase."""
        text = marshal_reference_text
        assert 'plan.phase-6-finalize.loop_back_without_asking' in text, (
            'marshal-json-reference.md must list plan.phase-6-finalize.loop_back_without_asking'
        )
        # Adjacency check: the reverse row must sit near the forward row to
        # mirror the forward/reverse pairing.
        forward_idx = text.index('plan.phase-6-finalize.finalize_without_asking')
        reverse_idx = text.index('plan.phase-6-finalize.loop_back_without_asking')
        assert abs(reverse_idx - forward_idx) < 800, (
            'loop_back_without_asking row must sit near finalize_without_asking row in marshal-json-reference.md'
        )
        # The dissolved ceremony_policy paths must NOT survive in the reference doc.
        assert 'ceremony_policy' not in text, (
            'the dissolved ceremony_policy block must not survive in marshal-json-reference.md'
        )
