# PLAN-39: Manifest Execution-Tier Stamp Diverges From Live Resolution

epic: plan-optimization
workstream: WS-10

> Staged 2026-07-22, promoted from lesson `2026-07-22-00-002` after its **third independent
> sighting** (PLAN-32 run, PLAN-33 at 1221s, PLAN-36 at 946s). Sibling of PLAN-20
> (execution-accounting-integrity). Written under the binding practice
> (lesson `2026-07-21-22-001`): mechanisms labelled OBSERVED / HYPOTHESIS with named artifacts.

## Objective

The compose-time `phase_5.step_execution_tier` stamp for `verify:coverage` reads **`per_task`**
while a **live `architecture resolve` at execution time returns `orchestrator` /
`exceeds_bash_ceiling`** (946s and 1221s observed, both above the 600s Bash cap). The stamp is
meant as **structural enforcement** of the leaf-no-background-build invariant; when it
under-reports, a leaf that trusts it would run a build **inline that is guaranteed to be killed**.
Three runs survived only because the leaf **defensively re-resolved** — i.e. the structural
enforcement has silently degraded to a convention the leaf must double-check.

## Root cause — the SEAM is OBSERVED, the CAUSE is HYPOTHESIS

**OBSERVED (read at HEAD 6a6312db0):**

- `manage-execution-manifest.py:1085` `_resolve_step_execution_tier` subprocesses
  `architecture resolve --command {canonical}` and reads `execution_tier`, returning
  `'per_task'` or `'orchestrator'`.
- **`:1092-1097` — ANY failure (unresolvable executor, non-zero exit, unparseable TOON,
  non-success status, absent/unknown tier) defaults to `'per_task'`.** The docstring calls
  `per_task` "the safe floor." **That floor is the suspect**: it makes a *resolution failure*
  indistinguishable from a *genuine per_task verdict*.
- The stamp is written once at compose (`_stamp_phase_5_step_execution_tier` `:1106`); the leaf
  reads it at execute time. So the two reads are separated in time.

**HYPOTHESIS — two candidate causes, and they need DIFFERENT fixes. D1 must settle which (or
both):**

- **(A) Masked resolution failure.** Compose-time resolve *failed* and silently defaulted to
  `per_task`; execute-time resolve *succeeded* and got `orchestrator`. If so, the defect is the
  **silent default** — `per_task`-on-failure is a fail-*open* floor for an invariant that should
  fail *loud*. **Confirm/refute artifact**: reproduce a compose against `verify:coverage`, capture
  whether `_invoke_architecture_resolve` returns None/error at compose time on this repo.
- **(B) Snapshot of a volatile value.** The `exceeds_bash_ceiling` verdict derives from the
  **learned/adaptive coverage duration**, which grows as the suite grows. Under the ceiling at
  compose, over it by execute. The stamp is then a *correct snapshot of a value that legitimately
  changed* — the defect is **stamping a volatile quantity as if durable**, the exact class Q-Gate
  caught in PLAN-32 (232s → 216s on re-read). **Confirm/refute artifact**: read where
  `exceeds_bash_ceiling` is computed and whether its input is the learned run-config duration;
  compare the learned `verify:coverage` duration at two reads.

**These are not mutually exclusive** — a volatile value (B) can also push a borderline resolve
into the timeout-and-default path (A). D1 records which is operative here.

## Deliverables

1. **Reproduce and settle A vs B (GATE).** Do NOT fix on the hypothesis — this epic has four
   consecutive falsified inferred mechanisms. Establish whether the compose-time stamp diverged
   because resolve *failed-and-defaulted* (A) or because the underlying duration *crossed the
   ceiling between reads* (B), using the named artifacts. Record the verdict; it determines D2.
2. **Make the divergence impossible or truthful** (shape gated by D1):
   - If **A**: the `per_task`-on-failure default must stop masking failures for *this* field —
     a resolution failure should be diagnosable (`unknown`/fail-loud per ADR-009), not silently
     floored to `per_task`, because here `per_task` is the *dangerous* value, not the safe one.
   - If **B**: the stamp must not present a volatile quantity as durable — either the leaf
     re-resolves at execute time (making the stamp advisory, which matches what the leaf already
     does defensively), or the ceiling verdict is computed from a stable input, not the learned
     duration.
   Either way: **align the compose stamp and the execute-time reality so the leaf need not
   defend against its own manifest.**
3. **Regression pinning the invariant.** A `verify:coverage` (or any whole-tree step) that
   resolves `orchestrator`/`exceeds_bash_ceiling` at execute time must never be stamped `per_task`
   at compose in a way the leaf would trust into an inline build. Use a real resolved shape, not
   a hand-built fixture.

Three deliverables, under the split guard. D1 gates D2.

## Expected Surface

- `manage-execution-manifest/scripts/manage-execution-manifest.py` (`:1085` resolve, `:1092`
  default, `:1106` stamp)
- the `architecture resolve` `execution_tier` / `exceeds_bash_ceiling` computation (locate at D1)
- the leaf read-site of `phase_5.step_execution_tier` (execute-task — locate at D1)
- run-config learned-duration input, if D1 finds cause B
- tests under the manage-execution-manifest / execute-task suites

## Dependencies and Sequencing

- Depends on: none.
- **Re-ground against PLAN-20 (#961)** at outline — it shipped the execution-accounting /
  `step_id` work this stamp lives beside; this is its sibling, not a redo. And **PLAN-32 (#972)**
  for the volatile-learned-timeout pattern D1 hypothesis B leans on.
- Overlaps with: **none in flight** — disjoint from PLAN-34 (marshall-steward), PLAN-37
  (manage-providers/sonar), PLAN-38 (phase-1-init/domain-detect). ⚠ Adjacent-in-theme to the
  harness-side timeout-floor follow-up (lesson `2026-07-22-00-001`) and to PLAN-35's build-verdict
  consolidation, but different files; flag if scope converges.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-39-manifest-tier-truthful-stamp.md"

BINDING PRACTICE (lesson 2026-07-21-22-001, verify-before-implement now n=4 in this epic): the SEAM is OBSERVED, the ROOT CAUSE is a HYPOTHESIS with two candidates that need different fixes. Deliverable 1 is a GATE — do not fix on either hypothesis before reading its named artifact. OBSERVED at HEAD 6a6312db0: manage-execution-manifest.py:1085 _resolve_step_execution_tier subprocesses `architecture resolve --command {canonical}` and reads execution_tier; :1092-1097 defaults to 'per_task' on ANY failure, calling it "the safe floor" — but here per_task is the DANGEROUS value (it puts a >600s build inline where it gets killed), so that floor is the prime suspect. The stamp is written once at compose (:1106) and read by the leaf at execute time, so the two reads are separated in time. HYPOTHESIS A — masked resolution failure: compose-time resolve failed and silently defaulted to per_task while execute-time succeeded and got orchestrator; artifact = reproduce a compose against verify:coverage and capture whether _invoke_architecture_resolve returns None/error at compose. HYPOTHESIS B — snapshot of a volatile value: exceeds_bash_ceiling derives from the learned/adaptive coverage duration which grows as the suite grows (under the ceiling at compose, over it by execute); the stamp is then a correct snapshot of a value that legitimately changed — same class Q-Gate caught in PLAN-32 (232s->216s on re-read); artifact = read where exceeds_bash_ceiling is computed and whether its input is the learned run-config duration. They are NOT mutually exclusive (B can push a borderline resolve into A's timeout-default). Settle which is operative, THEN fix: if A, stop masking the failure (unknown/fail-loud per ADR-009, not silent per_task); if B, stop presenting a volatile quantity as durable (leaf re-resolves / advisory stamp, or compute the ceiling from a stable input). Either way align compose-stamp with execute-reality so the leaf need not defend against its own manifest. Deliverable 3 regression must use a REAL resolved shape, not a hand-built fixture. Three plans run concurrently (PLAN-34 marshall-steward, PLAN-37 manage-providers, PLAN-38 phase-1-init/domain-detect) — all disjoint from your manage-execution-manifest + architecture-resolve footprint; if scope converges with PLAN-35 (build-verdict consolidation, staged not running) or the harness-timeout-floor follow-up, flag rather than absorb.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-39.md is recorded}
