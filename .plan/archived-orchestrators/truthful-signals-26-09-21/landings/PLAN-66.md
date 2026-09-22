# Landing Analysis: PLAN-66 — build_queue FIFO front sampled outside the serialized critical section

epic: truthful-signals
workstream: WS-01
pr: #1008 (https://github.com/cuioss/plan-marshall/pull/1008) — merged as `c22656feb`

> Landing record for one shipped plan. Written by the `analyze` verb after verifying each claim
> against ground truth — the merged commit, the shipped source at HEAD, and the live lessons store.
> The finalize narrative was treated as a lead, not a fact.

## Deliverable Fidelity vs Spec

All three staged deliverables shipped as specified, plus one sanctioned addition.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — confirm the divergence, pick the mirror shape | shipped-as-specified | PR body enumerates all three consuming sites with pre-fix code (`validate_lock_queue` `sorted(key=ts)`, `run_acquire` `sorted(key=ts)`, `run_release` `min(key=ts)`) and settles the verdict: adopt the **append-order-front invariant** rather than moving the sample inside `_mutate`, on the grounds that a second ordering key is a second source of truth that can drift again |
| D2 — single-source FIFO ordering | shipped-as-specified | `build_queue.py:245` `_fifo_front_n(waiting, n)` mirroring `merge_lock._fifo_front`; consumed at all three sites (`:341`, `:426`, `:560`). `ts` is still sampled (`:395`) and stamped, but demoted to informational — the on-disk entry shape is unchanged and the `run_log` audit tail still uses it. `active_since` semantics untouched; the reaper still ages from `active_since`, never `ts` |
| D3 — regression test | shipped-as-specified, **and verified to discriminate** | `TestFifoFrontIsListPositionNotMinTs` covers all three promote sites plus the helper. Fixtures append `[first, second]` with `first.ts = 2.0 > second.ts = 1.0`, so a min-ts selector elects a different entry than list position |
| *(added-unplanned)* residue promotion into the governing standard | shipped-additional, sanctioned | `ref-code-quality/standards/code-organization.md` § TOCTOU / Check-Then-Act Hazards gains a detection bullet (ordering key sampled outside the serialization boundary), **mitigation (d)** one-source-of-truth-for-order, and an adversarial-fixture testing note. Verified in the diff |

**Test quality is worth calling out — this plan avoided the epic's own `test-pins-the-defect`
archetype.** The PR states the fixtures were checked against the *pre-fix* selector: `min(ts)`
elects `plan-second` while `waiting[0]` elects `plan-first`, so every assertion fails against the
old code. It also names why the test is deliberately timing-free: a concurrency stress test only
*flakes* on this class, and a happy-path fixture seeding a monotonic `ts` hides it entirely. That
reasoning is now generalized into the standard's testing note, so the next plan facing an ordering
divergence inherits it.

**Lesson disposition verified against the live store.** `2026-06-21-11-002` returns `not_found` —
retired, not merely claimed retired. Its reusable residue was promoted into the governing standard
*before* retirement, which is exactly the WS-03 consume-and-retire discipline: the lesson leaves
the corpus and its transferable content survives in a doc that future work actually loads.

## Metrics and Anomalies

- Finalize: 18/19 steps done, 1 correctly skipped
- Verification: `quality-gate plan-marshall` green (mypy 263 files clean, ruff clean, SPDX ok),
  `module-tests` green including the 4 new assertions, `verify plan-marshall` green
- Anomalies: none in the plan's own execution. The anomaly this landing surfaced is in the review
  layer — see below.

## Routing and Merge Behavior

- Review: **CodeRabbit reviewed and produced release notes. Sourcery was rate-limited. PR-Agent
  self-cancelled.** Only **1 of 3 configured reviewers actually reviewed the diff.**
- CI/merge: merged as `c22656feb`; main clean and up to date; worktree and branch removed; plan
  archived to `2026-07-26-build-queue-fifo-ordering-nondeterminism` — **relocated 2026-07-26 by the
  archived-plan audit's dormation sweep; the artifacts now live at
  `.plan/temp/dormated-plans/2026-07-26-build-queue-fifo-ordering-nondeterminism`** (a move, not a
  delete; `.plan/local/archived-plans/` is now empty).
- Surface collisions: **none.** PLAN-66 ran concurrently with PLAN-69 and PLAN-51 and stayed inside
  `manage-locks` plus its test module; the one file outside that surface
  (`ref-code-quality/standards/code-organization.md`) is a docs-only residue promotion touched by
  no other in-flight plan. Disjointness call validated by outcome for the second landing running.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated — `launched` → `shipped`, `pr=1008`,
      `landing=landings/PLAN-66.md`
- [x] epic.md queue row reconciled from status.json
- [x] Watch **escalated** — PR-Agent self-cancellation reaches n=3 and changes severity class
- [x] Watch added — reviewer-quorum blindness confirmed live (1 of 3 reviewed, finalize green)
- [x] Lesson `2026-06-21-11-002` confirmed retired from the live store (`not_found`)
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- ⛔ **PR-Agent self-cancellation is now n=3, and this occurrence CHANGES ITS SEVERITY.** The first
  two observations (API-Sheriff #103) happened during a comment storm with an explicit `/review`,
  so the defect read as a comment-path edge case. **#1008 was ordinary PR traffic with no `/review`
  at all** — so the defect fires on routine reviews, not just under an unusual trigger pattern. It
  is no longer an edge case; it is the normal path. Surface remains `.github/workflows/pr-agent.yml`
  (`concurrency` + `cancel-in-progress` + `issue_comment`), owned by **PLAN-70**.
- ⛔ **Reviewer-quorum blindness is now CONFIRMED LIVE, not inferred.** Combined with Sourcery being
  rate-limited, only 1 of 3 configured reviewers reviewed this PR — and finalize still reported
  green across every review step. **A green finalize is not evidence that three bots looked at the
  diff.** This is precisely the hole **PLAN-72** was staged on: the completeness guard counts
  *accounted-for*, not *reviewed* (`automatic-review/SKILL.md:368`), so `complete: true` is
  reachable with zero real reviews. PLAN-72's premise moves from orchestrator-grounded HYPOTHESIS to
  **OBSERVED, with a live instance on this very PR.** Flagged for the emit decision below.
- **Emit-order consideration surfaced (operator's call, not taken unilaterally).** PLAN-70 is the
  pre-approved next emit, and it owns the workflow file carrying the n=3 cancellation defect.
  PLAN-72 now has a live confirming instance and closes the blindness that let a 1-of-3 review pass
  as green. Both strengthened from this landing; they are surface-adjacent (both touch
  `automatic-review`) so they cannot run concurrently in any case, and at the settled cap of 1 the
  question is strictly one of order. Recorded for the operator rather than re-sequenced here.
- No new plan staged — every follow-up this landing surfaced is owned by an already-staged spec.
