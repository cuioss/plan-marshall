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

from argparse import Namespace
from typing import cast

import pytest

from conftest import MARKETPLACE_ROOT, load_script_module

# ---------------------------------------------------------------------------
# Manifest module (Tier 2 direct load — the filename is hyphenated, so it is
# resolved by (bundle, skill, file) rather than imported. Unregistered, so this
# copy cannot displace one another suite holds.)
# ---------------------------------------------------------------------------

_mem = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    'manage-execution-manifest.py',
    'mem_for_phase6',
    register=False,
)

cmd_compose = _mem.cmd_compose
cmd_read = _mem.cmd_read
read_manifest = _mem.read_manifest
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Quiet down the best-effort decision-log subprocess so tests don't depend on a
# running executor; mirror manage-execution-manifest test layout.
_mem._log_decision = lambda *a, **kw: None


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


_AUTOMATED_REVIEW_FRONTMATTER = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'automatic-review' / 'SKILL.md'

_SONAR_ROUNDTRIP_FRONTMATTER = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'workflow' / 'sonar-roundtrip.md'
)

_AUTOMATED_REVIEW_MD = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'automatic-review' / 'SKILL.md'

_JSONL_FORMAT_MD = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-findings' / 'standards' / 'jsonl-format.md'

_TRIAGE_MD = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow' / 'triage.md'

_CONFIG_DEFAULTS_PY = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-config' / 'scripts' / '_config_defaults.py'
)

_EXECUTION_WORKFLOW_MD = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow' / 'execution.md'

_PHASE_LIFECYCLE_MD = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'ref-workflow-architecture' / 'standards' / 'phase-lifecycle.md'
)

_MARSHAL_JSON_REFERENCE_MD = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'extension-api' / 'standards' / 'marshal-json-reference.md'
)

_MANAGE_CONFIG_SKILL_MD = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-config' / 'SKILL.md'


class TestResumableReentry:
    def test_done_step_skipped_on_reentry(self, plan_context):
        """A step marked outcome=done MUST be skipped on the next dispatch."""
        plan_context.plan_dir_for('p6-resume-done')
        cmd_compose(_compose_ns('p6-resume-done'))
        manifest = read_manifest('p6-resume-done')
        assert manifest is not None

        # Simulate a prior run that completed push and create-pr.
        state = {
            'push': {'outcome': 'done', 'display_detail': '-> abc1234'},
            'create-pr': {'outcome': 'done', 'display_detail': '#42'},
        }
        dispatched = _derive_executor_dispatch(manifest, state)

        assert 'push' not in dispatched, 'done-marked push must be skipped on re-entry'
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
        """``automatic-review.md`` frontmatter MUST declare
        ``requires: [ci-complete]`` so the dispatcher resolves the
        precondition before invoking the consumer body.
        """
        text = _AUTOMATED_REVIEW_FRONTMATTER.read_text(encoding='utf-8')
        # Limit the scan to the YAML frontmatter block (the leading --- ... ---).
        head, sep, _rest = text.partition('\n---\n')
        # head is "---\nname: ..."; the second --- is the closing fence we
        # captured via sep. Inspect head for the requires: line.
        assert sep == '\n---\n', 'automatic-review.md must start with a YAML frontmatter block'
        assert 'requires: [ci-complete]' in head, (
            'automatic-review.md frontmatter MUST declare requires: [ci-complete]; got head=\n' + head
        )

    def test_sonar_roundtrip_declares_requires_ci_complete(self):
        """``sonar-roundtrip.md`` frontmatter MUST declare
        ``requires: [ci-complete]`` so the dispatcher resolves the
        precondition before invoking the consumer body.
        """
        text = _SONAR_ROUNDTRIP_FRONTMATTER.read_text(encoding='utf-8')
        head, sep, _rest = text.partition('\n---\n')
        assert sep == '\n---\n', 'sonar-roundtrip.md must start with a YAML frontmatter block'
        assert 'requires: [ci-complete]' in head, (
            'sonar-roundtrip.md frontmatter MUST declare requires: [ci-complete]; got head=\n' + head
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
        assert 'ci-wait' not in steps, f'default-row composer MUST NOT emit ci-wait; got steps {steps}'
        assert 'automatic-review' in steps, 'default-row composer must still include automatic-review'

    def test_recipe_path_retains_review_gates(self, plan_context):
        """Row 2 (recipe) — review gates RETAINED. The legacy ``ci-wait``
        step ID is defensively narrowed out when present in the candidate
        list, but ``automatic-review`` and ``sonar-roundtrip`` are never
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
        assert 'automatic-review' in steps, (
            'recipe row MUST retain automatic-review — review gates are never silently suppressed'
        )
        assert 'sonar-roundtrip' in steps, (
            'recipe row MUST retain sonar-roundtrip — review gates are never silently suppressed'
        )
        assert 'ci-wait' not in steps, 'recipe row MUST defensively drop legacy ci-wait step ID'

    def test_surgical_tech_debt_retains_review_gates(self, plan_context):
        """Row 5 (surgical_tech_debt variant) — review gates RETAINED. Same
        retention contract as Rules 2 and the surgical_bug_fix variant below:
        review bots run even on surgical tech-debt plans.
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
        assert 'automatic-review' in steps, 'surgical_tech_debt row MUST retain automatic-review'
        assert 'sonar-roundtrip' in steps, 'surgical_tech_debt row MUST retain sonar-roundtrip'
        assert 'ci-wait' not in steps, 'surgical_tech_debt row MUST defensively drop legacy ci-wait step ID'

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
        assert 'automatic-review' in steps, 'surgical_bug_fix row MUST retain automatic-review'
        assert 'sonar-roundtrip' in steps, 'surgical_bug_fix row MUST retain sonar-roundtrip'
        assert 'ci-wait' not in steps, 'surgical_bug_fix row MUST defensively drop legacy ci-wait step ID'

    def test_automated_review_md_does_not_read_ci_wait_outcome(self):
        """The ``automatic-review.md`` body MUST NOT include the legacy
        sibling-step prose that read the ``phase_steps["6-finalize"]["ci-wait"].outcome``
        signal from ``manage-status``. CI completion is now a precondition
        guaranteed by the dispatcher before the body executes.
        """
        text = _AUTOMATED_REVIEW_FRONTMATTER.read_text(encoding='utf-8')
        # The "Read completed-CI signal" section header must be gone.
        assert '### Read completed-CI signal' not in text, (
            'automatic-review.md MUST NOT carry a "Read completed-CI signal" '
            'section — that contract is now owned by the dispatcher precondition'
        )
        # The specific phase_steps signal lookup string must be gone.
        assert 'phase_steps["6-finalize"]["ci-wait"]' not in text, (
            'automatic-review.md MUST NOT read phase_steps["6-finalize"]["ci-wait"] '
            'outcome record — that signal model has been retired'
        )
