# PLAN-TRUTH-017: detect-artifacts offers a running plan's own live audit trail as safe-to-delete

> Renamed from **PLAN-201** on 2026-07-30 (see `plan-id-rename-map.md`).

epic: truthful-signals
workstream: WS-01

## Objective

`detect-artifacts` (`workflow-integration-git`) is **documented as excluding gitignored files** from
its safe-to-delete classification. It does not. On one observed run it returned **111,433
"safe-to-delete" entries totalling 19.9 MB**, including the running plan's **own in-flight
`work.log`**. A caller that follows the documented instruction *"for safe artifacts, delete them"*
destroys the audit trail of the run that is still producing it.

⛔ **Highest-severity item either epic surfaced on 2026-07-29.** The failure mode is silent
destruction of evidence: the damage is invisible when it happens and shows up later only as degraded
measurement, because `work.log` is exactly the artifact the dispatch audit and the retrospective read.

## Provenance

Forwarded by `code-intelligence-substrate` as `code-intelligence-substrate-004.md`, under the routing
rule — a documented contract the implementation does not honour is a behaviour/contract signal, so it
is ours even though the damage lands in their measurement substrate. Origin: the
`end-phase-replace-not-accumulate` plan (PR #1059), its candidate-lesson `-003`, self-review finding
`d8fa4a`, triaged `accepted` as out-of-scope for that diff.

⚠ **This is a forwarded LEAD, not a verified fact.** Neither epic has independently re-read
`detect-artifacts`. **D1 re-establishes it at HEAD before anything is changed.**

## Observed (first-party from that run, unverified by us)

- 111,433 entries / 19.9 MB classified safe-to-delete
- includes `.plan/local/plans/{plan_id}/logs/work.log` — **the plan's own live audit trail**
- includes the whole `.mypy_cache/` tree
- **both gitignored, both live at scan time**

## Deliverables

1. **D1 — GATE (mutates nothing): re-establish the defect at HEAD, and DERIVE the exposure.**
   Confirm the gitignore-exclusion contract is stated where the forwarding claims, and confirm the
   classification ignores it. Then enumerate **what a compliant caller would actually delete** —
   the 111,433 figure is one run's number, not the contract's blast radius. ⛔ **Do not fix before
   the exposure is derived**; the `work.log` case is a **SAMPLE**, and the interesting question is
   what else is live-and-gitignored (lock files, in-flight findings, the change ledger, worktree
   state).
2. **D2 — decide the direction, and record why.** Exactly one of:
   - **(a) Honour the documented contract** — genuinely exclude gitignored paths; or
   - **(b) Narrow the doc to actual behaviour AND add a liveness/staleness check** (mtime-based or
     lock-aware) before any gitignored path is offered as safe-to-delete, especially anything under
     an **active plan's own `logs/`**.
   ⛔ **(b) without the liveness check is NOT acceptable** — it documents the data-loss path instead
   of closing it. This constraint comes from the forwarding epic and is adopted verbatim.
3. **D3 — an active plan's own artifacts are never offered.** Whichever direction D2 takes, a path
   belonging to a plan that is currently running MUST NOT appear in a safe-to-delete set. ⭐ **This
   is the invariant, and it is independent of the gitignore question** — even a correctly-classified
   non-gitignored artifact of a live run should not be offered for deletion by that run's own
   finalize.
4. **D4 — find the callers.** Establish whether any caller acts on the classification automatically
   today, and how close this came to firing. A documented instruction with no automatic caller is a
   latent defect; one with an automatic caller is an active one. **The severity of D2/D3 depends on
   this answer — derive it, do not assume the optimistic case.**
5. **D5 — tests, each verified to FAIL pre-fix.** (a) A gitignored path is excluded per the contract
   (or, under D2b, is excluded by the liveness check). (b) A live plan's own `logs/work.log` is never
   in the safe-to-delete set. (c) The exposure derivation from D1 is asserted non-empty and contains
   the known member.

## Claim Labels

- OBSERVED (forwarded, first-party from PR #1059's run; **NOT independently verified**): the 111,433
  / 19.9 MB figure; `work.log` and `.mypy_cache/` in the set; both gitignored and live.
- HYPOTHESIS: the documented gitignore-exclusion contract exists as described — **confirm/refute at
  D1**. **Confirm/refute artifact**: the `detect-artifacts` contract text in
  `workflow-integration-git` and the classification implementation it describes.
- HYPOTHESIS: no caller deletes automatically today — **confirm/refute at D4. Do not assume it.**
- ⚠ No line numbers are asserted here deliberately: this plan's evidence is second-hand.
  **Establish every location by SYMBOL at D1.**

## Expected Surface

- HYPOTHESIS: `plan-marshall/skills/workflow-integration-git/**` — `detect-artifacts` and its
  contract doc (verify-at-outline; this is the whole premise)
- HYPOTHESIS: callers surfaced by D4
- OBSERVED: tests under `test/plan-marshall/workflow-integration-git/**`

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: ⚠ **PLAN-117** and **PLAN-119** touch `branch-cleanup.md`, which is adjacent to
  worktree/artifact teardown — **verify before pairing**. Otherwise disjoint from the current
  in-flight set (`tools-integration-ci`, `manage-status`, `phase-6-finalize`).
- ⭐ Adjacent to the **`worktree-remove` 60s hardcoded ceiling** Open Defect — same teardown surface,
  same bundle. **Consider folding that in at outline** if D1's surface reaches it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-017-detect-artifacts-offers-a-live-audit-trail-as-safe-to-delete.md"
```

## Write-Boundary

This plan MUST NOT create or edit any file under `.plan/local/orchestrator/`. Its only channels back
to the epic are its PR and its `inbox/` OUTBOX.
