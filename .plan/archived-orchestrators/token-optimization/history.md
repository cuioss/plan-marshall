# History: Token-Optimization Roadmap — EPIC CLOSED (frozen record)

epic: token-optimization

## Epic Close (2026-07-21)

**The whole epic is now closed, not just WS-01.** At close the ledger had been stale since
2026-07-16: `status.json` still showed 6 `launched` / 5 `staged` / 3 `parked` plans, none of
which reflected reality — every one had shipped or migrated in the intervening five days and
the queue was never reconciled. `landings/` and `plans/` were both empty, so the epic carried
no per-plan landing records at all.

**All 15 plans verified against `git log main` before closing** — none were dropped:

| Plan | Outcome | Evidence |
|------|---------|----------|
| PLAN-01 p1-finalize-commit-integrity | shipped | PR #914 |
| PLAN-02 p2-unified-finalize-triage | shipped | PR #920 |
| PLAN-03 p3-architecture-resolution | shipped | PR #917 |
| PLAN-04 p4-execution-manifest-gaps | shipped | PR #916 |
| PLAN-05 p5-consumer-domain-standards | shipped | PR #918 |
| PLAN-06 p6-small-tooling-batch | shipped | PR #921 (+ residue promoted via #924) |
| PLAN-07 p7-docs-contract-consistency | **migrated** → `plan-optimization` PLAN-04 | PR #930 |
| PLAN-08 p8-merge-queue-squash-reconcile | shipped | PR #919 |
| PLAN-09 p9-metrics-corpus-integrity | shipped | PR #922 |
| PLAN-10 ss-survivor-sweep | shipped | PR #913 |
| PLAN-11 tt-terminal-title-stale-build-busy | **migrated** → `plan-optimization` PLAN-05 | PR #931 |
| PLAN-12 marshall-orchestrator-skill | shipped | PR #915 |
| PLAN-13 rung1-global-home-root | shipped | PR #923 (seeded the `plan-server` epic) |
| PLAN-14 ci-pr-safe-merge | **migrated** → `plan-optimization` PLAN-06 | PR #929 |
| PLAN-15 consumer-upgrade-migrations | **migrated** → `plan-optimization` WS-02 (parked) | — |

Migrated plans are marked `resolved` rather than `shipped`: the work left this epic's
ownership rather than completing under it. Nothing is carried forward as an open lead — the
four migrated items are live in their successor epics' ledgers, and WS-01's own carried
watches were absorbed by the successor when it took over on 2026-07-17.

**Closing rationale.** The epic was superseded in fact but not in bookkeeping. Its successor
(`plan-optimization`, created 2026-07-17) has been the sole active orchestration surface since,
and its WS-10 continues the pipeline-integrity work. Leaving `token-optimization` in
`orchestrating` phase with a false queue was an active hazard: a resuming session would have
read six in-flight plans that do not exist. Closed and archived as part of the 2026-07-21
cleanup sweep.

**Successor**: `plan-optimization` (and, for the build-server track seeded by PLAN-13,
`plan-server`).

> Frozen record of the CLOSED core token-optimization roadmap (WS-01), migrated from the
> hand-run ledger at `.plan/plan-optimization/` as part of the marshall-orchestrator D10
> dogfood. The authoritative full historical record remains
> `.plan/plan-optimization/HISTORY.md` (three frozen snapshots) plus the shipped ledger in
> `.plan/plan-optimization/HANDOVER.md` §3 — this file freezes the epic-level outcome and
> points there rather than duplicating the per-plan rows.

## Outcome

The core cost-driver roadmap ran from the lane-feature design (#811) to the finale plan-8
context-trim (#899, 2026-07-15) — every data-driven cost-driver plan shipped. The effort's
premise (lesson 2026-06-30-08-001, 58-plan token audit): ~73% of every plan's tokens are
framework overhead, a hard ~1.0M per-plan floor, and the edit is the smallest cost bucket.

- Targets armed: surgical ≤1.2M, single_module ≤1.5M, multi_module ≤2.5M (comparable basis).
- At-target proof: #866 (1.11M, minimal posture) and #883 (1.17M, auto posture INCLUDING
  bot review + sonar).
- Cost driver "leaf-backgrounded builds": RESOLVED (plan-6 D6 #893 compose-time
  execution_tier guard, verified live). Initial-envelope call-site coverage gap remains an
  open defect (epic.md).
- Cost driver "finalize wait-loops under queue traffic": ADDRESSED (plan-8 #899 Cluster B,
  one concurrent barrier + detach); D6 before/after delta confirmation is a live watch.
- The "concurrent siblings reap each other's background builds" residual was FALSIFIED —
  the killer is the HARNESS; mitigated by BK #912 (truthful ledger status +
  classify-outcome no-blind-retry verdict).

## Shipped ledger

The complete per-plan shipped table (design #811 through the tail: #899 finale, #906 EV,
#908 upgrade-regen-safety, #909 build-maven-classify, #910 HS, #911 WT/ADR-006, #912 BK)
is frozen in `.plan/plan-optimization/HANDOVER.md` §3 and `HISTORY.md` Snapshots 1-3.
Notable structural outcomes:

- Dispatch topology contract: init inline; refine/outline/plan exactly ONE
  execution-context each; adversarial validators are the only sanctioned sibling
  dispatches; finalize consolidated to one find → one triage → one respond.
- Lane/routing machinery DONE: light lane, minimal/auto/full postures, escalation ratchet,
  classify-before-route — all proven live.
- #908 shipped with its own bookkeeping destroyed (worktree-remove before
  integrate_into_main; no metrics datapoint) — the enforcement gap graduated into P1.
- Roadmap cost data is known-lossy on two axes (harness kills absorbed as idle; #908's
  missing datapoint) — idle/wall figures are floors; P9 owns the corpus-integrity work.

## What succeeded this ledger

The remaining tail (P1-P9, SS, TT, the plan-server/orchestration track, consumer
migrations) is orchestrated as workstreams WS-02..WS-06 of this epic — see `epic.md` and
`status.json` (the machine authority).
