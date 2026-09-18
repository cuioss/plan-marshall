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

        Under the precondition-resolver model, Row 5 surgical_bug_fix RETAINS
        the review gates — the legacy ``ci-wait`` step is dropped defensively,
        but ``automatic-review`` and ``sonar-roundtrip`` are kept.
        ``knowledge-capture`` stays out of the candidate list here.
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
        assert 'automatic-review' in steps, (
            'surgical bug_fix MUST retain automatic-review under the new precondition-resolver contract'
        )
        assert 'sonar-roundtrip' in steps, (
            'surgical bug_fix MUST retain sonar-roundtrip under the new precondition-resolver contract'
        )
        # ci-wait is defensively narrowed out.
        assert 'ci-wait' not in steps

        dispatched = _derive_executor_dispatch(manifest)
        # Pruned step must NOT appear in dispatch.
        assert 'ci-wait' not in dispatched
        # Retained steps DO appear.
        assert 'push' in dispatched
        assert 'lessons-capture' in dispatched
        assert 'automatic-review' in dispatched
        assert 'sonar-roundtrip' in dispatched

    def test_recipe_path_dispatches_only_recipe_steps(self, plan_context):
        """Recipe-driven manifest must yield a slim dispatch list.

        Under the precondition-resolver contract, Row 2 (recipe) RETAINS
        review gates — ``automatic-review`` and
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
        assert 'automatic-review' in steps, 'recipe row MUST retain automatic-review under the new contract'
        assert 'sonar-roundtrip' in steps, 'recipe row MUST retain sonar-roundtrip under the new contract'
        # Legacy ci-wait defensively dropped.
        assert 'ci-wait' not in steps

        dispatched = _derive_executor_dispatch(manifest)
        assert dispatched == steps


class TestSkillMdManifestNarrative:
    @pytest.fixture(scope='class')
    @classmethod
    def skill_md_text(cls) -> str:
        return cast(str, _PHASE_6_SKILL_MD.read_text(encoding='utf-8'))

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


class TestLoopBackWithoutAskingContract:
    """Pin the symmetric auto-continuation contract:

    1. ``plan.phase-6-finalize.loop_back_without_asking`` field exists with
       default ``True`` in the manage-config defaults surface.
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
    @classmethod
    def phase_6_skill_md_text(cls) -> str:
        return cast(str, _PHASE_6_SKILL_MD.read_text(encoding='utf-8'))

    @pytest.fixture(scope='class')
    @classmethod
    def execution_workflow_text(cls) -> str:
        return cast(str, _EXECUTION_WORKFLOW_MD.read_text(encoding='utf-8'))

    @pytest.fixture(scope='class')
    @classmethod
    def config_defaults_text(cls) -> str:
        return cast(str, _CONFIG_DEFAULTS_PY.read_text(encoding='utf-8'))

    @pytest.fixture(scope='class')
    @classmethod
    def phase_lifecycle_text(cls) -> str:
        return cast(str, _PHASE_LIFECYCLE_MD.read_text(encoding='utf-8'))

    @pytest.fixture(scope='class')
    @classmethod
    def marshal_reference_text(cls) -> str:
        return cast(str, _MARSHAL_JSON_REFERENCE_MD.read_text(encoding='utf-8'))

    @pytest.fixture(scope='class')
    @classmethod
    def manage_config_skill_text(cls) -> str:
        return cast(str, _MANAGE_CONFIG_SKILL_MD.read_text(encoding='utf-8'))

    # ---- Defaults surface ------------------------------------------------

    def test_loop_back_without_asking_default_is_true(self, config_defaults_text: str):
        """``loop_back_without_asking`` MUST default to ``True`` — the
        symmetric counterpart of ``finalize_without_asking=True``. A
        finalize-side fix is corrective work inside a plan the user already
        approved, so the cycle auto-continues in both directions and
        ``max_iterations`` is the ceiling that terminates it. The knob is a
        flat field under ``plan.phase-6-finalize`` — the ``ceremony_policy``
        block was dissolved and every automation knob distributed back into
        its owning phase."""
        # Locate the DEFAULT_PLAN_FINALIZE block and confirm the field is
        # declared with default True.
        assert 'DEFAULT_PLAN_FINALIZE = {' in config_defaults_text, (
            'DEFAULT_PLAN_FINALIZE block must exist in _config_defaults.py'
        )
        block_start = config_defaults_text.index('DEFAULT_PLAN_FINALIZE = {')
        # Find the closing brace of the dict literal.
        block_end = config_defaults_text.index('\n}\n', block_start)
        block = config_defaults_text[block_start : block_end + 3]
        # The field MUST be present and default to True in the finalize block.
        assert "'loop_back_without_asking': True" in block, (
            'DEFAULT_PLAN_FINALIZE must declare loop_back_without_asking with default True'
        )
        # The dissolved ceremony_policy block must not survive.
        assert 'DEFAULT_CEREMONY_POLICY' not in config_defaults_text, (
            'DEFAULT_CEREMONY_POLICY must be gone after the ceremony_policy dissolution'
        )

    def test_loop_back_field_read_through_phase_get(self, manage_config_skill_text: str):
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

    def test_phase_6_skill_md_documents_loop_back_continuation_hook(self, phase_6_skill_md_text: str):
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

    def test_phase_6_skill_md_documents_flag_unset_halt(self, phase_6_skill_md_text: str):
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

    def test_phase_6_skill_md_documents_flag_set_inline_dispatch(self, phase_6_skill_md_text: str):
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

    def test_phase_6_skill_md_documents_max_iterations_cap(self, phase_6_skill_md_text: str):
        """The loop-back hook MUST cap the inline re-entry at
        ``phase-6-finalize.max_iterations`` (default 3). Beyond that, the
        dispatcher halts and prompts the user EVEN WITH the flag set — the
        ceiling is the structural safety valve."""
        text = phase_6_skill_md_text
        # The cap-reached branch must reference max_iterations.
        assert 'max_iterations' in text, 'SKILL.md hook must reference max_iterations as the loop-back ceiling'
        # And must explicitly halt-and-prompt on cap exhaustion.
        text_lower = text.lower()
        assert 'ceiling' in text_lower or 'cap' in text_lower, (
            'SKILL.md hook must document the cap as a structural safety valve'
        )

    def test_phase_6_skill_md_documents_iteration_log_line(self, phase_6_skill_md_text: str):
        """The canonical ``[STATUS] Loop-back iteration {N}/{max}`` work-log
        line MUST be documented so retrospective analysis can grep for it.

        The counter placeholder is the iteration ABOUT to be spent
        (``{loop_back_iteration + 1}``), because the ceiling is an admission
        test rather than a report on an iteration already consumed.
        """
        text = phase_6_skill_md_text
        # The literal line shape — substring match (the runtime substitutes
        # the placeholders).
        assert '[STATUS]' in text, 'SKILL.md must use the canonical [STATUS] log marker'
        assert 'Loop-back iteration' in text, 'SKILL.md must document the "Loop-back iteration" log-line text'
        # The {N}/{max} shape must be visible (placeholders or actual count
        # syntax), in either the admission form or the plain-counter form.
        assert (
            '{loop_back_iteration + 1}/{max_iterations}' in text
            or '{loop_back_iteration}/{max_iterations}' in text
            or '{N}/{max}' in text
        ), 'SKILL.md must show the iteration counter shape ({N}/{max} or named placeholders)'

    # ---- Ceiling enforceability (persisted counter + admission boundary) ---
    #
    # The declared ceiling used to be unenforceable in the DEFAULT
    # configuration for two compounding reasons: the consult sat INSIDE the
    # ``loop_back_without_asking == true`` branch, and the counter lived in
    # model context. With ``loop_back_without_asking: false`` every loop-back
    # halted and prompted, the operator re-ran finalize, and the count started
    # again at zero — so a plan could loop indefinitely, one re-run at a time,
    # while ``max_iterations`` was nominally in force. These three cases pin
    # the fix: the counter is PERSISTED, the ceiling gates BOTH knob branches,
    # and a refusal is reported distinctly from an ordinary halt.

    @staticmethod
    def _loop_back_hook_section(text: str) -> str:
        """The item-7b hook body, bounded so positional claims are real.

        A document-wide substring search cannot distinguish "the ceiling is
        consulted before the knob" from "both strings appear somewhere in a
        1400-line file", so the ordering assertion below is made inside this
        bounded section rather than over the whole text.
        """
        start = text.index('7b. Loop-back continuation hook')
        end = text.index('7c.', start)
        section = text[start:end]
        assert section.strip(), 'Loop-back hook section resolved empty'
        return section

    def test_loop_back_iteration_counter_is_persisted_not_in_model_context(self, phase_6_skill_md_text: str):
        """The counter MUST live in status metadata, not in model context.

        An in-memory counter is reset by every session restart, every phase
        re-entry, and every halt-and-prompt cycle — which is precisely the
        path the default configuration takes on every loop-back.
        """
        text = phase_6_skill_md_text

        assert 'status.metadata.loop_back_iteration' in text, (
            'SKILL.md must name status.metadata.loop_back_iteration as the '
            'counter home — the ceiling is unenforceable without a durable count'
        )
        assert '--set --field loop_back_iteration' in text, (
            'SKILL.md must document persisting the incremented count via '
            'manage-status metadata --set --field loop_back_iteration'
        )
        assert '--get --field loop_back_iteration' in text, (
            'SKILL.md must document reading the count back via manage-status metadata --get --field loop_back_iteration'
        )
        # The retired model-context claims must NOT survive anywhere in the doc.
        for retired in (
            'it is NOT persisted to status.json',
            'starts the counter back at 0',
        ):
            assert retired not in text, (
                f'SKILL.md still carries the retired in-model-context claim '
                f'{retired!r}; a counter described as non-persisted contradicts '
                'the durable-count contract the ceiling depends on'
            )

    def test_ceiling_is_consulted_before_the_knob_on_both_branches(self, phase_6_skill_md_text: str):
        """The ceiling gate MUST precede the ``loop_back_without_asking`` read.

        Position IS the contract here: a ceiling evaluated after the knob read,
        or nested inside one of its branches, bounds only that branch. Asserting
        the order inside the bounded hook section is what makes this a real
        claim rather than a co-occurrence check.
        """
        section = self._loop_back_hook_section(phase_6_skill_md_text)

        # Anchor on the two ACTIONS, not on the two nouns: the nouns appear in
        # surrounding rationale prose in either order, so a bare name search
        # would assert nothing about where the gate actually runs. The gate is
        # the admission comparison; the knob consult is its config read.
        ceiling_at = section.find('Ceiling admission gate')
        knob_at = section.find('plan phase-6-finalize get --field loop_back_without_asking')

        assert ceiling_at != -1, (
            'The loop-back hook declares no "Ceiling admission gate" — the '
            'ceiling must be an admission test with its own named gate'
        )
        assert knob_at != -1, (
            'The loop-back hook does not read loop_back_without_asking through '
            'the documented plan phase-6-finalize get surface'
        )
        assert ceiling_at < knob_at, (
            'The max_iterations ceiling is consulted AFTER the '
            'loop_back_without_asking knob inside the loop-back hook. Nested '
            'that way it bounds only one knob branch, leaving the DEFAULT '
            'configuration (loop_back_without_asking: false) unbounded — the '
            'exact defect this gate was moved to fix.'
        )
        assert 'BOTH knob branches' in section, (
            'The hook must state that the ceiling applies to BOTH knob '
            'branches, so a later edit cannot re-nest it under one'
        )

    def test_ceiling_breach_message_is_distinct_from_the_ordinary_halt(self, phase_6_skill_md_text: str):
        """A refused loop-back MUST NOT read as an ordinary halt-and-prompt.

        The two outcomes mean different things — "a loop-back awaits your
        go-ahead" versus "a loop-back was REFUSED and the work it would have
        reviewed is unreviewed" — so they carry different operator messages.
        """
        section = self._loop_back_hook_section(phase_6_skill_md_text)

        assert 'Loop-back ceiling breached' in section, 'The breach path must carry its own distinct message marker'
        assert 'refusing to admit' in section, (
            'The breach message must state that the iteration was REFUSED, not merely that the run paused'
        )
        # The consequence the breach message must additionally state.
        section_lower = section.lower()
        assert 'no remaining iteration' in section_lower, (
            'The breach message must state that findings raised in the halting '
            'round have no remaining iteration in which their fixes could be '
            'reviewed — otherwise an operator reads the halt as a clean stop'
        )
        # And it must be a DIFFERENT string from the ordinary knob halt.
        assert 'returning control to user (loop_back_without_asking=false)' in section, (
            'The ordinary knob halt message must still exist, so the two '
            'outcomes are genuinely distinguishable rather than collapsed'
        )

    def test_phase_6_skill_md_documents_truth_table(self, phase_6_skill_md_text: str):
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

    def test_execution_workflow_has_loop_back_continuation_subsection(self, execution_workflow_text: str):
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

    def test_execution_workflow_documents_both_branches(self, execution_workflow_text: str):
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
        assert 'stop' in text_lower, 'Flag-unset branch must explicitly STOP rather than continuing'
        # Auto-continue marker for the flag-set branch.
        assert 'auto-continu' in text_lower, 'Flag-set branch must reference auto-continuation'

    def test_execution_workflow_documents_double_gate(self, execution_workflow_text: str):
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

    def test_phase_lifecycle_mentions_loop_back_alongside_forward_gates(self, phase_lifecycle_text: str):
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
            'loop_back_without_asking must be documented next to the existing review gates, not in an unrelated section'
        )

    def test_marshal_json_reference_registers_the_field(self, marshal_reference_text: str):
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
