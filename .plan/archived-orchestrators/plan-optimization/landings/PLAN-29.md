# Landing Analysis: PLAN-29 — Platform-Agnostic Waiting Standard

epic: plan-optimization
workstream: WS-10
pr: #969 (`ca8a044b0`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Verified against merge commit `ca8a044b0` (23 files, +1816/-43). **4/4 shipped.**

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1 — ADR resolving the §6 fork | shipped-as-specified | **ADR-011**, resolved as a **HYBRID**: the waiting *policy* is a target-neutral standard rendering on every target; the waiting *primitive* is a Runtime op declining via `no-op` + `alternative` where no background-watch analog exists. This is the third option the spec offered, not either pole |
| D2 — classify `Monitor` in the target machinery | shipped-**modified** | `opencode/mapping.json` (+7), `frontmatter.py` (+26/-…), `emitter.py` (+5/-…), 3 test files. ⚠ **The spec's proposed `_UNMAPPED_TOOLS` route was WRONG** — see below |
| D3 — author the waiting standard | shipped-as-specified | `plan-marshall/standards/waiting.md` (+92) + `workflow/await-long-running.md` (+2) |
| D4 — specify the mechanism + decide build-vs-split | shipped, **built not split** | `wait_for` Runtime op across `runtime_base.py` (+56), `claude_runtime.py` (+180), `_claude_runtime_impl.py` (+124), `opencode_runtime.py` (+35), `platform_runtime.py` (+26), `contract.md` (+89), plus ~670 lines of new tests |

**The D4 split guard did NOT fire** — D1 chose the Runtime-op route (the narrower one the spec said MAY ship in-plan) rather than the `targets:` filter, so no follow-up generator plan is owed. That question is now closed.

## ⚠⚠ verify-before-implement reaches n=3 — and a lesson is filed against THIS orchestrator

**Three consecutive plans with a correct symptom and a falsified orchestrator-inferred
mechanism**: PLAN-24 (#963), PLAN-26 (#964), and now PLAN-29. Captured as lesson
**`2026-07-21-22-001` against `marshall-orchestrator`**, prescribing that **inferred mechanisms
be labelled as hypotheses with a named confirm/refute artifact** rather than asserted as fact.

**This is a direct instruction to the orchestrator's spec-authoring practice and is adopted.**
Every future spec whose mechanism is orchestrator-inferred must mark it as a hypothesis and
name the artifact that would confirm or refute it. The three existing verify-first clauses were
ad-hoc prose; this makes it structural.

**What was falsified this time — twice, at two different phases:**

1. **At refine**, three design inputs were corrected: the Runtime ABC has **23 ops, not "~22"**;
   the admission test lives in `01-finish-portability.md`, **not** the cross-reference the spec
   cited; and — most consequentially — **`_UNMAPPED_TOOLS` is Claude-scoped**, so the spec's
   proposed D2 route of adding `Monitor` there **would have been actively wrong**, not merely
   suboptimal.
2. **At execute**, ADR-011's *own* claim was falsified: that Claude implements the primitive over
   the background-watch mechanism. That affordance is **agent-level, with no Python API a runtime
   subprocess can register against.** Rather than ship an always-`unknown` stub, **the executor
   stopped and escalated**; the operator narrowed the op to a concrete observable (build-job) and
   **ADR-011 was amended in-plan to record the falsification.**

Point 2 is the strongest single datapoint in this epic for design-first plans: the ADR was
*wrong in its own delivered artifact*, caught at implementation, and corrected in-flight rather
than shipped. An ADR is not self-validating.

## Metrics and Anomalies

- Tokens: **3.1M** · Duration: **2h31m**
- Finalize: 22/22; plugin-doctor clean (4 skills); self-review **142 candidates** (largest in the
  epic); `finalize-step-simplify` 0 edits over 23 files; **0 review comments, nothing to compare**
- Deploy: 1109 files; 10 bundles synced, executor regenerated
- Retrospective ran: 14 aspects, 3 lessons

## Routing and Merge Behavior

- **Review**: **0 bot comments.** Every finding on this plan came from *local* gates — refine,
  execute-time escalation, self-review. Consistent with the standing observation that local
  gates outperform bots on design/contract work.
- **CI/merge**: all green, merged via queue, cleanup complete, `main` at `ca8a044b0`.
- **Surface collisions**: none. Ran concurrently with PLAN-31 (landed) and PLAN-32 (session died).

## Reconciliation Actions

- [x] status.json `plans[]` updated (`shipped`, pr `969`, landing `landings/PLAN-29.md`)
- [x] epic.md queue row reconciled
- [x] **D4 split-guard question CLOSED** — Runtime-op route chosen, no follow-up generator plan owed
- [x] **ADR-011 allocation CONFIRMED correct** — re-checked at outline (main at 009) and again
      mid-run when PLAN-25 landed 010 during planning. The orchestrator's ADR-011 instruction held
- [x] `verify-before-implement` → **n=3**, lesson `2026-07-21-22-001` filed against
      `marshall-orchestrator`; hypothesis-labelling adopted into spec-authoring practice
- [x] Three new defects recorded (below)
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- **⚠ NEW DEFECT — `pre-push-quality-gate` bundle-derivation maps `test/marketplace/**` to a
  non-existent `marketplace` bundle**, hard-failing the gate on a *clean* tree
  (lesson `2026-07-21-21-002`). Worked **around, not through**: whole-tree quality-gate was run
  instead — a strict superset, and it passed. **The gate as written would halt any future plan
  touching those tests.** Not staged (draining); candidate for the next queue review.
- **⚠ `pre-submission-self-review` completion-guard violation — 7th recurrence of that lesson
  family.** It returned successfully *with a real finding* but never called `mark-step-done`.
  Correctly recorded as `failed` per contract, the finding fixed inline (a stray PLAN-29 plan-id
  had leaked into a durable architecture doc), and retried once — the retry recorded cleanly.
  **Seven recurrences is well past the plan-worthy bar**; the family needs an owner rather than
  another tally increment.
- **⚠ `dispatch-inline-split.md` claims a 17-step roster against this plan's 22-step manifest**,
  leaving **five steps invisible to its own coverage check** (lesson `2026-07-21-22-002`). Same
  shape as the stale-count-prose class; a coverage check that cannot see a third of the roster is
  not a coverage check.
- **Stray plan-id in a durable doc** — worth noting as a pattern seed: plan-scoped identifiers
  leaking into durable architecture docs is exactly what `no-lesson-id-in-skill-prose` governs
  for lesson IDs. Whether plan-ids deserve the same lint is an open question, n=1.
