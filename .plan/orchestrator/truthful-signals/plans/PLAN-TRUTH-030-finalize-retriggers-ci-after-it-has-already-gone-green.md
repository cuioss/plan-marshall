# PLAN-TRUTH-030: finalize re-triggers CI after it has already gone green

epic: truthful-signals
workstream: WS-01

## Objective

Finalize pushes commits **after** the PR's CI has already passed, forcing a second full CI run per plan.
Measured over the 39-plan archived corpus: **58 CI runs for 36 plans — a 61 % overhead**, with 16 plans
(44 %) running CI more than once. Collapse the re-triggers so a plan pays one CI run in the common case.

Two independent re-trigger sources, both addressable:

1. **Finalize's own `mutates_source: true` steps commit and push after `create-pr`.** The clearest is
   `project:finalize-step-era-stamp-fill` — by design it *"resolves the PR-PENDING era-stamp sentinel to
   the real PR number … committing and pushing the correction before the merge gate"*, which **cannot
   happen before the PR exists** and therefore guarantees a post-green push. It ran in **27 of 39**
   archived plans.
2. **Triage loop-backs fire per producer.** `ci-verify`, `automatic-review` and `sonar-roundtrip` are
   separate finding producers, each able to loop back independently; two plans recorded **3 loop-backs**.
   Collecting findings across all producers behind ONE barrier turns N rounds into one commit and one
   CI run.

⭐ **Secondary benefit the operator flagged: token cost.** Consolidating the per-producer loop-backs into
a single triage round means one `execution-context` envelope instead of N — the dispatch overhead, the
skill loading, and the re-read of plan state are paid once. **This is a hypothesis, not a measured
claim** — D0 must size it rather than assert it.

## Provenance

Operator request, 2026-08-01, following the orchestrator's D0 measurement over the archived corpus
(recorded as a Watch in `epic.md` and in `logs/decision.log`). This plan replaces the deleted
`PLAN-TRUTH-029`, whose premise (rebase staleness) the same measurement refuted. ⛔ **Do not resurrect
the rebase-placement direction** — the early rebase is a conflict pre-filter that keeps conflict
resolution OUTSIDE the merge mutex; moving it later is counter-indicated.

## Deliverables

1. **D0 — GATE (mutates nothing): attribute the 22 excess runs to their causes.** Split the excess
   between (a) post-green finalize-internal pushes, (b) triage loop-back commits, (c) anything else.
   ⛔ **The corroborating evidence is a matched pair per plan**: two `artifacts/ci-runs/{run_id}/
   manifest.toon` records with the **same `pr_number` and different `head_sha`** is a genuine re-run
   (verified on `resolver-ext-point-seam`: PR #1067, heads `405b05f0…` then `1e57cf7c…`, 59 minutes
   apart, **both `final_status: success`** — a green run followed by another green run). ⚠ **Do NOT
   count runs from the work-log step markers** — see the blocking caveat below.
   ⚠ Also size the **token** side of the loop-back consolidation here, so D2's benefit is measured
   rather than assumed.
2. **D1 — stop the post-green push where it is avoidable.** For each finalize-internal `mutates_source`
   step that commits after `create-pr`, decide and record: can its mutation be computed BEFORE the PR
   exists, batched into the pre-PR commit, or deferred to the merge commit? ⛔ **`era-stamp-fill` is the
   hard case and must be reasoned about explicitly, not waved through**: it needs the real PR number, so
   it genuinely cannot run pre-PR. The question is whether its correction must be *pushed as its own
   commit* or can ride an existing one. ⚠ It is **meta-project-only** (`project:` prefix), so this
   deliverable's benefit is ours, not our consumers'.
3. **D2 — one loop-back barrier across all finding producers.** Collect `ci-verify` / `automatic-review`
   / `sonar-roundtrip` findings behind a single triage-and-loop-back decision so one round of fix
   commits is produced instead of one per producer. ⛔ **This must not weaken fail-closed behaviour** —
   a barrier that batches findings must still block the merge on any unresolved one; batching is about
   *when the loop-back fires*, never about *whether a finding gates*. ⚠ Check the interaction with
   `PLAN-TRUTH-001` (running), which owns gate re-firing over the loop-back diff.
4. **D3 — tests, each verified to FAIL pre-fix.** (a) A plan whose only post-PR mutation is the
   era-stamp produces ONE CI run, not two. (b) Findings from two different producers in the same
   finalize produce ONE loop-back round. (c) A fail-closed case still blocks: an unresolved finding from
   any single producer still prevents merge under the batched barrier.

Four deliverables — under the split guard.

## Claim Labels

- **OBSERVED**: 39 archived plans; 36 with persisted `ci-runs/`; distribution 20×1, 11×2, 4×3, 1×4 = 58
  runs / 36 plans. 16 of 36 re-ran CI.
- **OBSERVED**: a genuine re-run pair on `resolver-ext-point-seam` — same `pr_number: "1067"`, heads
  `405b05f069…` and `1e57cf7c01…`, `fetched_at` 11:30:28Z and 12:29:00Z, **both `final_status: success`**.
  ⇒ green-then-commit-then-green is a real, observed pattern.
- **OBSERVED**: `project:finalize-step-era-stamp-fill` logged **27** step executions across the corpus;
  `lessons-housekeeping` 21, `finalize-step-simplify` 16, `finalize-step-preference-emitter` 16 — all
  `mutates_source: true`.
- **OBSERVED**: `push.md` already names this class — *"Finalize-internal re-stale (known-safe) — a
  finalize-internal `mutates_source: true` step (`era-stamp-fill`, `lessons-capture`) committed DURING
  finalize"* — and the dispatcher carries a documented **"Post-PR re-push"** fast path. ⇒ **The behaviour
  is known and sanctioned; what is missing is that nobody costed it.**
- **OBSERVED**: all 16 multi-run plans also recorded a `Loop-back iteration`; a search for >1 CI run with
  ZERO loop-backs returned none.
- ⛔ **OBSERVED — BLOCKING CAVEAT FOR ANY COUNTING**: finalize step execution is **not uniformly logged**.
  Across 39 plans the `Executing step` marker appears 33× for `sync-baseline` but only 22× for
  `pre-push-quality-gate`, 19× for `push`, 18× for `ci-verify`, and **1×** for `sonar-roundtrip`.
  **Absence of a marker does NOT mean the step did not run.** Any count derived from these markers is a
  floor, not a measurement — which is why D0 is pinned to the CI manifests instead.
- **HYPOTHESIS**: the excess runs are dominated by (a) post-green finalize pushes rather than (b) triage
  loop-backs. **Confirm/refute at D0.** The green→green pair above is one confirming instance, not a
  distribution. ⚠ Both causes are real; **the split between them is unmeasured.**
- **HYPOTHESIS**: consolidating per-producer loop-backs yields a material token saving by collapsing N
  dispatch envelopes into one. **Confirm/refute at D0** — the operator raised it as a likely benefit,
  and this epic's rule is that a plausible mechanism is not evidence.
- **Verify-first clause**: D2 assumes the three producers can be made to share one barrier without
  reordering `ci-verify`'s `requires: [ci-complete]` precondition. Confirm against the dispatcher's
  precondition resolution before scoping; a barrier that forces `ci-complete` earlier would trade a CI
  re-run for a longer serial wait.

## Expected Surface

- **HYPOTHESIS**: `.claude/skills/finalize-step-era-stamp-fill/**` (project-local, meta-project-only)
- **HYPOTHESIS**: `plan-marshall/skills/phase-6-finalize/SKILL.md` — the dispatcher's commit
  instrumentation (item 5f) and the "Post-PR re-push" fast path (verify-at-outline)
- **HYPOTHESIS**: `phase-6-finalize/standards/ci-verify.md`, the `automatic-review` skill, and
  `phase-6-finalize/workflow/sonar-roundtrip.md` for the D2 barrier (verify-at-outline)
- **OBSERVED**: `phase-6-finalize/standards/push.md` — already documents the finalize-internal re-stale
  class
- **HYPOTHESIS**: finalize tests under `test/plan-marshall/phase-6-finalize/**`

## Dependencies and Sequencing

- ⛔ **CANNOT EMIT WHILE PLAN-TRUTH-001 IS RUNNING** — it holds `phase-6-finalize` and specifically owns
  gate re-firing over the loop-back diff, which D2 touches directly. **Sequence after it lands, and
  re-ground D2 against whatever it changed.**
- ⚠ **PLAN-TRUTH-031** (structured finalize step records) is the **observability prerequisite** for
  D0's attribution being repeatable. This plan can proceed on the CI manifests alone, but 031 is what
  makes the answer re-derivable later. Prefer 031 first if both are queued.
- ⚠ **PLAN-TRUTH-028** also edits `phase-6-finalize` standards — sequence, do not pair.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-030-finalize-retriggers-ci-after-it-has-already-gone-green.md"
```

## ⭐⭐ MERGED 2026-08-08 — this plan ABSORBS -048

**Component:** `phase-6-finalize (finalize spends what it need not)` · **Deliverables after merge: 10** (raised cap is 12).

Both are finalize burning cost it cannot justify, on the same phase, measured over the same corpus.

- **`-030`** — commits are pushed *after* CI has already gone green, forcing a second full CI run per
  plan.
- **`-048`** — `pre-submission-self-review` spent **709,472 tokens (13% of one plan's entire spend)** on
  a single step and still missed the rule that fired.

⚠ **They are merged for the component and the measurement substrate, not because one causes the other.**
Both are quantified from the archived corpus and both change `phase-6-finalize` step ordering/scoping,
so they share the re-measurement work — which is the expensive part and would otherwise be done twice.
⛔ `-048`'s RATIOS remain blocked behind the measurement; its ABSOLUTE numbers are solid.

⛔ **The absorbed spec(s) are `superseded` and retained as the record — do not implement or emit them.**
⚠ **Re-count deliverables at outline.** The figure above is the sum of the pre-merge counts; overlapping deliverables should COLLAPSE rather than concatenate, and a merged plan that still reads as two plans stapled together has not been merged.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.


---

## ⭐ FOLDED FROM THE 2026-08-09 INBOX DRAIN — 2 messages (absorbed-TRUTH-048 self-review surface)

**`daemon-...-014` (candidate-lesson).** *Pre-submission self-review passed **clean** over a
docstring-vs-code overclaim **in a plan whose whole subject was docstring-vs-code overclaims**.*
⇒ ⭐⭐ **The strongest single datum this surface has**: the detector was blind to the exact defect class
the plan was written to fix, on that plan's own diff. **A clean self-review verdict is not evidence the
class was checked** — and here the class was maximally salient and still missed.

**`two-producers-...-003` (candidate-lesson).** *Self-review findings are **queried at 5-execute but
filed at 6-finalize**, so absence is inferred from the wrong phase.* ⇒ this supplies a **mechanism** for
the blindness above: the query runs against a phase in which the findings do not yet exist, so
**"no findings" is structurally guaranteed rather than measured.** ⛔ **A zero from the wrong phase is
`could not look`, not `looked and found nothing`** — the epic's shared archetype, inside the tool that
is supposed to catch it.

⇒ Together they answer a question this spec could not settle alone: the refuted arm reads as a gap
**because the query is phase-mismatched**, not because the reviewer is weak. Fix the phase before
scoping any strengthening of the detector.
