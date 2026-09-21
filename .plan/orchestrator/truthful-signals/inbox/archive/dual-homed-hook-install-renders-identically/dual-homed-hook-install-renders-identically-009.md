envelope_version=1
sender_type=plan
sender_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T10:12:58Z

# Candidate lesson: `build_time` reports an all-zero block for a plan that ran 77 builds — branch-cleanup destroys the oracle before record-metrics reads it

**Component**: `plan-marshall:phase-6-finalize` (step ordering) / `plan-marshall:manage-metrics` (the consumer)
**Source signal**: plan-retrospective report for `dual-homed-hook-install-renders-identically`
**Suggested category**: bug

## Claim

`metrics.md`'s `build_time` block was emitted as all zeros for a plan that actually ran 77 builds. The oracle the block is computed from is the change-ledger, which lives **inside the plan worktree**. `default:branch-cleanup` removes that worktree, and every remaining reporting step runs *after* it — so the reader arrives at a path that no longer exists and reports zeros rather than "unavailable".

## Evidence (first-hand, re-derived in this step)

The ordering is visible in `manage-metrics reconcile-ledgers --plan-id dual-homed-hook-install-renders-identically`, whose 6-finalize rows carry wall-clock timestamps. `branch-cleanup` lands at `2026-09-03T08:01:14`, and **every** subsequent reporting step is later:

| Step | Recorded at |
|---|---|
| `branch-cleanup` | 2026-09-03T08:01:14 |
| `project:finalize-step-deploy-target` | 2026-09-03T08:04:17 |
| `project:finalize-step-sync-plugin-cache` | 2026-09-03T08:10:11 |
| `project:finalize-step-review-retrospective` | 2026-09-03T08:56:51 |
| `plan-marshall:plan-retrospective` | 2026-09-03T09:56:12 |

So the destruction of the worktree-resident oracle strictly precedes the reads that depend on it. This is structural, not incidental to this run: `branch-cleanup` is ordered ahead of the whole post-run-review band by design, and **every worktree-using plan is exposed identically**.

## Why it matters — the two zeros are byte-identical

A plan that genuinely ran no builds and a plan whose build oracle was destroyed produce **the same all-zero block**. There is no discriminator in the artifact, so a reader cannot tell "measured, found nothing" from "could not look". That is the project's own *which-kind-of-zero* rule (`list-stalled`'s `plans_root_state`, `inbox list`'s `inbox_state`, `restore-from-plan`'s four-value `action`) violated at a surface where nobody applied it.

The direction of the error is the damaging one: it under-reports build cost to exactly zero, so any roadmap figure derived from `build_time` treats the most build-heavy plans as free.

## Suggested directive (for the orchestrator to judge)

Two independent halves; do not conflate them.

1. **Snapshot before destruction, or read before cleanup.** Either capture the change-ledger-derived build facts into main-checkout-resident plan state *before* `branch-cleanup` runs, or move the `build_time` derivation ahead of it. Pick one; both are ordering fixes, not new instrumentation.
2. **Make the zero self-describing regardless.** Even with (1) landed, the block must distinguish `builds: 0 (observed)` from `builds: unavailable (oracle absent)`. Without this, the next ordering regression is silent again.

Derive the blast radius rather than assuming `build_time` is the only consumer: enumerate every metrics/report surface whose oracle is worktree-resident and whose reader runs in the post-`branch-cleanup` band. `build_time` is the one this run happened to notice.
