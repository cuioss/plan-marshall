# PLAN-LB-39: Antigravity execution fidelity

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-39-antigravity-execution-fidelity.md` and is queued as one row file,
> `queue/PLAN-LB-39.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief.

## Objective

The first plan run under Google Antigravity (pm-mcp-core PLAN-41, PR #34) ran every task inline in
one session, never read the repository's `CLAUDE.md`, recorded zero tokens as a real number, left no
mark of which harness ran it, reported an incomplete package complete with existing tests weakened,
and pushed a head none of its mandated gates had run on. The same completion failure recurred under
OpenCode (pm-mcp-core PLAN-44, PR #38), and the pushed-head failure recurred twice under Claude Code.
The operator ruled on 2026-10-12 that Antigravity issues are this epic's highest priority, and on
2026-10-13 that the two harness-agnostic failures (`-015`, `-016`) ship in the same plan.

This plan makes a non-Claude run behave like a Claude run where the pipeline assumed Claude: phase 5
dispatches real sub-agents through the harness's own mechanism, the project's standing rules reach
the agent, measurement says "unknown" when nothing was measured, and the run records its harness.
It also closes the two failures that are not Antigravity-specific but were most damaging there: a
plan judged against criteria it rewrote, and a head pushed past its gates.

## Deliverables

Seven deliverables, above the ~6 split guard by operator decision of 2026-10-13 (one plan, `-015`
and `-016` included). Each is graded independently at the functional review.

1. **Phase 5 dispatches a real sub-agent on every harness that has one** (`lessons-routing-011`).
   Every `Task: plan-marshall:execution-context-{level}` dispatch site the orchestrator follows in
   phase 5 (and the main-context `verification-feedback` dispatch) reaches the harness's native
   sub-agent mechanism — Antigravity `invoke_subagent`, OpenCode's sub-agent — through the existing
   `platform-runtime subagent dispatch` seam, carrying the resolved level and returning the leaf's
   TOON plus whatever usage the harness reports. A harness with no sub-agent mechanism runs the
   envelope inline only through an explicit, logged `dispatch_mode: inline` branch that still writes
   one dispatch-boundary row per envelope. Silent inline batch execution is not a reachable path.
   *Done when:* the generated Antigravity and OpenCode phase-5 and `execution.md` documents name the
   native mechanism (not a bare `Task:` line), a fixture asserts the generated text per target, and
   an inline-mode run writes one boundary row per envelope.

2. **Phase boundaries cannot be skipped silently** (`lessons-routing-011`). The phase transition
   refuses to advance over a phase with a start and no end marker (PLAN-41: `4-plan` had no end,
   `5-execute` no start, `any_phase_missing_end_time=true`), and finalize fails closed — or loops
   back with a named finding — when the branch carries commits made during execute but no task
   recorded a completion. *Done when:* fixtures cover both refusals with a matched negative.

3. **The project's standing rules reach a non-Claude agent** (`lessons-routing-012`).
   - Antigravity project setup (and the steward's upgrade path) bridges the repository's `CLAUDE.md`
     into a file Antigravity loads (`AGENTS.md` or `.agents/rules/`), as a generated rule with drift
     detection, never a hand copy; OpenCode is checked for the same gap and covered if it has it.
   - The base persona and the Antigravity target rules carry two rules: build and format commands
     resolve through `architecture resolve` to the project's declared quality gate, never a guessed
     plugin; and an unresolvable plugin prefix (`No plugin found for prefix …`) means the project does
     not use that plugin — stop, never retry it fully qualified.
   Not in scope: a goal guard in `build-maven maven run` (operator ruling 2026-10-12; `-014` is not a
   defect). *Done when:* a fresh Antigravity project setup over a fixture with only `CLAUDE.md`
   produces the bridged rule, re-running it is a no-op, a changed `CLAUDE.md` is reported as drift,
   and both rules are present in the generated Antigravity output.

4. **Per-task verification carries the quality gate the manifest stamped** (`lessons-routing-012`).
   When the manifest stamps `verify:quality-gate=per_task`, `phase-4-plan` synthesizes the
   module-scoped quality gate into each task's `verification.commands`, or phase 5 Step 10b enforces
   it — whichever the outline settles — so the gate cannot run once for the whole phase.
   *Done when:* a fixture manifest with `per_task` yields tasks whose verification includes the gate.

5. **An unmeasured run says so, and every run records its harness** (`lessons-routing-013`,
   `-028`).
   - A runtime with no transcript reports `total_tokens=unknown`, never `0`; the metrics header
     carries a `transcripts: none` capability flag; `landing-check` therefore reports the landing
     incomplete instead of passing it.
   - `phase-1-init` runs the `orchestrator preflight` hook (today nothing on the start path calls it,
     so no archived plan has a `client.toon`) and stamps `harness` into the plan's `status.json`
     metadata; the landing-facts block gains an optional `harness=` key that `landing-check` reports.
   *Done when:* a fixture Antigravity runtime yields `unknown` end to end, a fresh plan carries a
   `client.toon` and a `harness` field, and the landing-payload test reads `harness` back.

6. **A plan is judged against the criteria it was given, not the ones it rewrote**
   (`lessons-routing-015`, `-026`). Builds on PLAN-LB-37's functional review; does not re-implement
   it.
   - The functional review reads the Done-When and success criteria from the request and outline as
     they stood at outline approval, and flags any edit the plan made to them — and to spec or ADR
     documents the request names as the target — as blocking unless an operator decision is cited.
   - An `infeasible` verdict on a specified check must name the work-order sentence it answers, must
     still hold after the paired implementation task is done, and deleting a specified check requires
     a recorded operator decision; the verify-first "drop a refuted gap" clause does not cover it.
   - A changed existing test whose assertions were filtered, relaxed or removed, or whose fixture was
     changed to avoid a rule, is reported as a weakened test, blocking unless a deliverable asks for it.
   - Open Done-When criteria are a standing finalize triage source, so the loop cannot exit at "no
     pending findings" while a criterion is unmet.
   *Done when:* fixtures reproduce PLAN-41's and PLAN-44's patterns — a rewritten Done-When, a deleted
   specified check under `infeasible`, a filtered assertion, an empty bot queue with an open criterion
   — each blocking, each with a matched negative.

7. **The pushed head carries the plan's mandated gates** (`lessons-routing-016`). The pre-push gate
   compares the HEAD its last full gate ran on with the HEAD being pushed and refuses when source
   changes lie between; gates the request or the project's done-rule names (e.g. `verify -Ppre-commit`,
   `-Pcoverage`, `-Pintegration-tests`) are composed into `phase_5.verification_steps` so every
   re-entry re-runs them; and an execute exit is not reported fresh under `required_coverage_unknown`
   for a plan that mandates coverage. *Done when:* fixtures cover a fix commit after the last gate
   (refused), a re-entry that re-runs a request-named gate, and the coverage-unknown exit.

## Claim Labels

- OBSERVED: `marketplace/targets/antigravity/mapping.json:12` maps the `Task` tool to
  `invoke_subagent`, but the `Task:` dispatch-line pattern carries disposition `preserve` (lines
  43-46), and the generated `target/antigravity/skills/plan-marshall-plan-marshall/workflow/execution.md:157`
  still reads `Task: plan-marshall:{target}` — read at HEAD `71971784f`.
- OBSERVED: `platform-runtime/scripts/antigravity_runtime.py` § `subagent_dispatch` (line 812) already
  returns an `invoke_subagent` invocation; nothing in `phase-5-execute` or `plan-marshall/workflow/`
  calls `subagent dispatch` (grep over `marketplace/bundles/plan-marshall/skills/**/*.md`).
- OBSERVED: `antigravity_runtime.py` § `project_initial_setup` (line 154) creates `.plan/` and project
  settings and bridges no `CLAUDE.md`.
- OBSERVED: `antigravity_runtime.py` § `metrics_capture` (line 765) returns a no-op when no token total
  is passed; the zero arises downstream in finalize's `record-metrics` / landing emission.
- OBSERVED: `phase-1-init/SKILL.md` Step 8e runs only the build-server `preflight`; no step calls
  `orchestrator preflight`.
- OBSERVED: `landing-payload-spec.md` already reads `total_tokens=unknown` as missing — once the
  producer stops writing `0`, `landing-check` flags the landing without a spec change.
- OBSERVED: PLAN-LB-37's `phase-6-finalize/workflow/functional-review.md` and `code-review.md` are on
  `main` (four part-PRs, #1754–#1758); PLAN-LB-37 is still running (rollout D9, D15 outstanding).
- HYPOTHESIS: the "phase transition" refusal belongs in `manage-status` § `cmd_transition`
  (`scripts/_cmd_lifecycle.py:791`) — confirm at outline (verify-at-outline).
- HYPOTHESIS: the head-versus-last-gate comparison belongs in `pre-push-quality-gate.md` plus the
  freshness cross-check in `manage-tasks/scripts/_freshness_crosscheck.py` (which already knows
  `required_coverage_unknown`) — confirm at outline (verify-at-outline).
- HYPOTHESIS: pm-mcp-core evidence (PLAN-41, PLAN-44, the two Claude recurrences) rests on the
  lessons-routing ingest and the sender's audit, not re-checked here.
- Verify-first clause 1 — whether OpenCode's generated output has the same `Task:` and `CLAUDE.md`
  gaps; cover it in D1/D3 only if it does, and say which.
- Verify-first clause 2 — what usage `invoke_subagent` returns; if none, D1's usage propagation is
  `unknown` per D5, never `0`.
- Verify-first clause 3 — D4: synthesize in phase 4 or enforce Step 10b; pick one and record why.
- Verify-first clause 4 — D6 sits on PLAN-LB-37's files; rebase onto 37's final landing before
  finalize and do not re-scope 37's own deliverables.

## Expected Surface

- OBSERVED: `marketplace/targets/antigravity/mapping.json` — `Task:` disposition (D1)
- OBSERVED: `marketplace/targets/antigravity/emitter.py` — dispatch-line rewrite (D1)
- HYPOTHESIS: `marketplace/targets/opencode/` — same, if verify-first clause 1 finds the gap (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py` —
  `subagent_dispatch`, `project_initial_setup`, `metrics_capture` (D1, D3, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` (D1, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall-antigravity/skills/target-rules/standards/antigravity-rules.md` (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/SKILL.md` (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py` (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md` (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/record-metrics.md` (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md` (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py` (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md` (D6)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` (D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` (D7)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` (D7)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/` (D7)
- tests: `test/plan-marshall/platform-runtime/`, `test/plan-marshall/phase-6-finalize/`,
  `test/plan-marshall/manage-status/`, `test/plan-marshall/manage-metrics/`,
  `test/plan-marshall/manage-execution-manifest/`, `test/marketplace/targets/` (D1–D7)

## Dependencies and Sequencing

- Depends on: none to start. D6 builds on PLAN-LB-37's functional review (on `main`); rebase onto
  37's final landing before finalize.
- Overlaps with: PLAN-LB-37 (running) on `phase-6-finalize/workflow/functional-review.md` and the
  landing-payload spec; PLAN-LB-26 (staged) on `plan-marshall/workflow/triage.md`; PLAN-LB-27
  (staged, plan footprint) possibly on finalize facts.
- Adjacent to: PLAN-LB-32 (shipped; head-dependent step re-fire) — D7's head-versus-gate check is
  the pre-push half it did not cover; `build-maven maven run` stays untouched (`-014`, not a defect).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-39-antigravity-execution-fidelity.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. See `persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
