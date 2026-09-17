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
        """A failed sonar-roundtrip or automatic-review must NOT prevent
        lessons-capture from firing — it is dispatched independently."""
        plan_context.plan_dir_for('p6-lessons-with-failures')
        cmd_compose(_compose_ns('p6-lessons-with-failures'))
        manifest = read_manifest('p6-lessons-with-failures')
        assert manifest is not None

        state = {
            'sonar-roundtrip': {'outcome': 'failed', 'display_detail': 'gate failed'},
            'automatic-review': {'outcome': 'failed', 'display_detail': 'timed out'},
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


class TestAutomatedReviewCiSignalAndOverflow:
    """Pin the documented contract: ``automatic-review`` declares
    ``requires: [ci-complete]`` in its frontmatter so the dispatcher resolves
    the precondition before the body runs (no inline CI poll, no
    manage-status signal hand-off). On near-budget exhaustion the triage
    workflow files a ``pr-comment-overflow`` finding while recording
    ``--outcome loop_back``.

    These are narrative-pinning tests on the standards docs because the
    automatic-review step body is markdown-driven (no Python entry point); the
    contract is enforced at agent dispatch time, and the standards doc IS the
    source of truth. If a future edit removes any of these contract markers,
    the documented overflow + precondition contract has been silently
    broken.
    """

    @pytest.fixture(scope='class')
    @classmethod
    def automated_review_text(cls) -> str:
        return cast(str, _AUTOMATED_REVIEW_MD.read_text(encoding='utf-8'))

    @pytest.fixture(scope='class')
    @classmethod
    def jsonl_format_text(cls) -> str:
        return cast(str, _JSONL_FORMAT_MD.read_text(encoding='utf-8'))

    @pytest.fixture(scope='class')
    @classmethod
    def triage_text(cls) -> str:
        return cast(str, _TRIAGE_MD.read_text(encoding='utf-8'))

    # ---- Precondition declaration ---------------------------------------

    def test_automated_review_declares_requires_ci_complete_in_frontmatter(self, automated_review_text: str):
        """``automatic-review.md`` MUST declare ``requires: [ci-complete]``
        in its YAML frontmatter so the dispatcher invokes the precondition
        resolver before the body runs.
        """
        head, sep, _rest = automated_review_text.partition('\n---\n')
        assert sep == '\n---\n', 'automatic-review.md must start with a YAML frontmatter block'
        assert 'requires: [ci-complete]' in head, 'automatic-review.md frontmatter MUST declare requires: [ci-complete]'

    def test_automated_review_does_not_poll_ci_inline(self, automated_review_text: str):
        """The legacy ``ci wait --pr-number`` polling primitive MUST NOT
        appear in the automatic-review step body — that responsibility is
        owned by the dispatcher's precondition resolver. A reappearance
        would mean the consumer is double-polling CI.
        """
        assert 'ci wait \\\n  --pr-number' not in automated_review_text, (
            'automatic-review.md must not invoke `ci wait --pr-number` inline; '
            'the precondition resolver owns that primitive'
        )
        # The legacy section headings MUST be gone.
        assert '### Wait for CI' not in automated_review_text, (
            'automatic-review.md must not have a "Wait for CI" subsection'
        )
        assert '### Read completed-CI signal' not in automated_review_text, (
            'automatic-review.md must not have a "Read completed-CI signal" '
            'subsection — CI completion is now a dispatcher-resolved precondition'
        )

    def test_automated_review_does_not_read_ci_wait_outcome_record(self, automated_review_text: str):
        """``automatic-review.md`` MUST NOT read the legacy
        ``phase_steps["6-finalize"]["ci-wait"]`` outcome record. The
        precondition resolver runs ahead of the body and surfaces
        ``wait_failed`` to the dispatcher, not to the body.
        """
        assert 'phase_steps["6-finalize"]["ci-wait"]' not in automated_review_text, (
            'automatic-review.md must not read the legacy ci-wait outcome record'
        )

    def test_timeout_contract_describes_precondition_split(self, automated_review_text: str):
        """The 900 s budget is now ``FIND-only`` — triage and RESPOND moved out
        of this step and run once at the dispatcher level as the unified
        wait-region triage. CI wait wall-clock is bounded separately by the
        dispatcher's **per-signal review-arm** precondition resolver (600 s
        ceiling), NOT the old global ``ci-complete`` colour gate. The contract
        MUST say so explicitly so a future edit doesn't restore the combined
        triage-budget shape or the global-CI gate.
        """
        text_lower = automated_review_text.lower()
        assert 'find-only' in text_lower, (
            'Timeout Contract must declare the 900 s budget as FIND-only '
            '(triage/RESPOND moved to the dispatcher-level unified triage)'
        )
        assert 'triage-only' not in text_lower, (
            'the legacy triage-only combined-budget shape must be gone — the 900 s budget is now FIND-only'
        )
        assert 'precondition' in text_lower, (
            'Timeout Contract must reference the precondition resolver as the CI wait-time owner'
        )
        assert 'review arm' in text_lower or 'review-arm' in text_lower, (
            'the precondition must be gated on the per-signal review arm, not '
            'global CI colour — a red CI unrelated to the review signal no '
            'longer skips the comment FIND'
        )

    # ---- Overflow handling -----------------------------------------------

    def test_overflow_section_documented_in_triage(self, triage_text: str):
        """The overflow handling section MUST exist in the shared triage
        workflow so the contract is reachable from every call site that
        dispatches `cross.triage` (automatic-review, sonar-roundtrip,
        phase-5-execute verification/quality-gate triage, pr-doctor)."""
        # The triage workflow numbers its steps; overflow lives at Step 5.
        assert 'Overflow' in triage_text and 'timeout' in triage_text.lower(), (
            'triage.md must document overflow / timeout handling'
        )

    def test_overflow_files_pr_comment_overflow_finding(self, triage_text: str):
        """When the per-iteration budget is nearly exhausted, the triage
        workflow MUST file exactly one ``{finding_type}-overflow`` envelope
        finding (via ``manage-findings add``) carrying the unprocessed
        hash_ids in ``detail``. The pr-comment-specific shape (used by
        automatic-review) is named explicitly in the documentation."""
        text = triage_text
        assert 'pr-comment-overflow' in text, 'triage.md must reference the pr-comment-overflow finding type by name'
        # The documented add command uses the parameterised type form so
        # every finding_type has its own overflow envelope shape.
        assert '--type {finding_type}-overflow' in text or '--type pr-comment-overflow' in text, (
            'triage.md must invoke `manage-findings add --type {finding_type}-overflow`'
        )
        assert 'unprocessed' in text.lower() and 'hash_id' in text.lower(), (
            'triage.md must document carrying the unprocessed hash_ids in --detail'
        )

    def test_overflow_returns_loop_back_outcome(self, triage_text: str):
        """The overflow path MUST return ``outcome: loop_back`` so the
        calling manifest step (automatic-review / sonar-roundtrip /
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

    def test_overflow_threshold_is_conservative(self, triage_text: str):
        """The documented overflow heuristic MUST trigger before the wrapper
        fires — the 75 % threshold leaves enough budget for the overflow
        capture itself plus a safety margin."""
        text = triage_text
        assert '75' in text and 'budget' in text.lower(), (
            'triage.md must document a 75% budget threshold so capture happens before wrapper timeout'
        )

    # ---- pr-comment-overflow finding type contract ------------------------

    def test_pr_comment_overflow_registered_in_jsonl_format(self, jsonl_format_text: str):
        """The ``pr-comment-overflow`` finding type MUST be enumerated in
        ``manage-findings/standards/jsonl-format.md`` so producers can ``add``
        it without an unknown-type error."""
        text = jsonl_format_text
        # Per-type file list.
        assert 'findings/pr-comment-overflow.jsonl' in text, (
            'jsonl-format.md must list pr-comment-overflow.jsonl in the per-type file enumeration'
        )
        # Required-fields type taxonomy.
        assert 'pr-comment-overflow' in text, 'jsonl-format.md must include pr-comment-overflow in the type taxonomy'
        # Promotion table — non-promotable.
        assert '| `pr-comment-overflow` | Not promotable' in text, (
            'jsonl-format.md must list pr-comment-overflow as Not promotable in the promotion table'
        )

    def test_pr_comment_overflow_contract_documented(self, jsonl_format_text: str):
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

    def test_pr_comment_overflow_is_non_blocking(self, jsonl_format_text: str):
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
