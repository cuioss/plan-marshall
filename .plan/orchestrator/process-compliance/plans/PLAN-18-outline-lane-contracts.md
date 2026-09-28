# PLAN-18: Outline-lane contract defects

> ✅ **Staged 2026-09-28 under the standing operator directive ("issues about current problems are to be fixed,
> not relayed to PM-MCP").** Emittable; NOT subject to the PM-MCP parking of 2026-09-26.

epic: process-compliance
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-18-outline-lane-contracts.md` and is queued in the epic's `queue/`
> row files. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Close the contract defects the PLAN-12 and PLAN-13 runs hit between 2-refine and 5-execute,
each of which forced the orchestrator or a leaf to improvise: phase leaves transition the plan
themselves while the orchestrator's gates for that boundary are still open; the Q-Gate
re-run economy depends on content hashes that no script computes; the "one batched question"
rule is unsatisfiable above the question tool's per-call limit; and three pairs of documents
state contradictory rules.

## Deliverables

1. **One owner per phase transition.** The phase-2-refine, phase-3-outline and phase-4-plan
   leaves each transitioned the plan themselves, including when the return carried an
   `outline_prompt` (3 operator questions) or `qgate_validation_required: true`. That
   happened before the orchestrator's operator question, sibling Q-Gate, auto-loop, handshake
   capture and clean-main assertion ran, all of which `planning.md` / `planning-outline.md`
   place ahead of the transition. Choose one owner per boundary. Either the leaf never
   transitions when its return still requires orchestrator work, or the orchestrator docs drop
   their transition calls and gate the leaf. Add a return-shape assertion: `outline_prompt`
   present ⇒ status still reads `3-outline` (and the refine/plan equivalents). Also document
   the re-plan path the operator used: fixing Q-Gate findings after a 4-plan return had no
   documented route once status read `5-execute`.
2. **Deterministic outline hashing.** `q-gate-validation.md` Step 3.5 requires per-deliverable
   and `__whole_outline__` hashes in `work/deliverable-hashes.toon`, and
   `planning-outline.md` Step 2b decides whether to skip a re-dispatch by comparing them. No
   verb computes them. Three passes of one run used three normalisations and two throwaway
   helper scripts under `.plan/temp/`, so the skip gate can never fire, or can fire wrongly.
   Add a deterministic `manage-solution-outline` verb that computes and persists the hashes
   from the parsed outline, and call it from Step 3.5 and Step 2b. Regression test: same
   outline gives identical hashes; a one-deliverable edit changes only that deliverable's
   hash and the whole-outline hash.
3. **Batched operator questions paginate.** `planning-outline.md` (`outline_prompt`) and
   `planning.md` (`refine_prompt`) require "ONE batched `AskUserQuestion` covering EVERY
   question". The question tool takes at most 4 per call, and a phase-3-outline leaf returned 6.
   Either cap the leaf contract at 4 questions, or state the pagination rule, as phase-1-init
   Step 5c does for recipe options.
4. **Doc-contract contradictions resolved.** (a) `planning.md` § Action: outline says 3-outline
   is "loaded directly in main context" (line 548 at HEAD). `planning-outline.md` Step 2
   dispatches it as an `execution-context-{level}` Task. One of the two is stale. (b) The
   phase-3-outline Step 9c design-model check calls a skill with no `scripts/` LLM-driven,
   while its own worked example calls `phase-2-refine` (no `scripts/`) hybrid. The rule and
   the example disagree, so the validator exempts by example. Fix each pair so that one
   statement is derived from the other.
5. **Outline-rule gaps a leaf cannot satisfy.** (a) `change-type-heuristic` ambiguity (feature
   2 vs bug_fix 1) names an LLM fallback, `detect-change-type`, which the leaf cannot
   dispatch. `planning-outline.md` has no return signal for it, although its Metrics section
   mentions it. Either give the fallback a return signal or make it inline. (b) The plugin-dev
   `bug_fix` rule says "Always exactly 2 deliverables", with no branch for a request carrying
   several independent defects (PLAN-13 carries 5). Add the multi-defect branch.

## Claim Labels

- OBSERVED: phase-2/3/4 leaves self-transitioned while the return required orchestrator gates — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-007.md` § Observed (orchestrator-side report of three leaf returns in one run)
- OBSERVED: three hash normalisations and two helper scripts across three Q-Gate passes — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-008.md` § Observed
- OBSERVED: 6-question `outline_prompt` split 4 + 2 — cited at `inbox/archive/plan-13-finalize-mechanism-defects/plan-13-finalize-mechanism-defects-003.md` § 1
- OBSERVED: `planning.md` line 548 says "loaded directly in main context"; `planning-outline.md` Step 2 dispatches — confirmed at HEAD by the orchestrator (grep); cited at `plan-13-finalize-mechanism-defects-003.md` § 2
- OBSERVED: `pm-plugin-development/skills/ext-outline-workflow/standards/change-types.md` lines 55/72 state "Always exactly 2 deliverables" — confirmed at HEAD by the orchestrator; cited at `plan-13-finalize-mechanism-defects-003.md` § 4
- HYPOTHESIS: Step 9c rule/example disagreement — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md` § Step 9c (verify-at-outline); cited at `plan-12-tool-triage-008.md` § Related inconsistency
- HYPOTHESIS: no return signal exists for the `detect-change-type` fallback — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md` § Metrics (verify-at-outline); leaf-reported, not independently verified

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` — refine transition ownership, `refine_prompt` batching, § Action: outline wording
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md` — Step 2 / 2b / 2c / 3c / 4, `outline_prompt` batching, Metrics
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md` — Step 3.5
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-2-refine/` — leaf transition
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-3-outline/` — leaf transition, Step 9c
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-4-plan/` — leaf transition
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/` — hash verb
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-outline-workflow/standards/change-types.md` — multi-defect bug_fix branch
- OBSERVED: `test/plan-marshall/manage-solution-outline/` — hash determinism test
- OBSERVED: `test/plan-marshall/plan-marshall/` — return-shape assertion test

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-17 (shares `planning.md`, `planning-outline.md`, `test/plan-marshall/plan-marshall/`), PLAN-10 (shares `planning.md`), PLAN-16 (planning-lane neighbours). Sequence behind PLAN-17; do not parallelize.
- Scope-bloat guard: 5 deliverables, under the ~6 presumption.

## Folded inbox material (same act)

- `plan-12-tool-triage-007.md` (finding): deliverable 1
- `plan-12-tool-triage-008.md` (finding): deliverable 2, deliverable 4b
- `plan-13-finalize-mechanism-defects-003.md` items 1, 2, 4a, 4b (finding): deliverables 3, 4a, 5a, 5b

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-18-outline-lane-contracts.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
