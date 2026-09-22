# PLAN-02: Build telemetry and lock accounting

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-02-build-telemetry.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT.

## Objective

Attribute every build and lock event instead of dropping it: build_queue release from
worktrees, change-ledger rows per build, daemon-down failover, generator resolution,
and capture-footprint/build_scope evidence. Lessons: G14, G08 + 5 singletons
(9 lessons, archived at `lessons-archive/`).

## Deliverables

1. build_queue release resolving the main checkout from inside a worktree (2026-09-04-14-008).
2. Change-ledger row per build so build time is never unavailable (2026-09-04-17-005).
3. coverage-report exit-1-with-empty-stderr diagnosis (2026-09-13-12-004).
4. Pollution guard distinguishing a concurrent plan's merge.lock write (2026-09-03-18-001).
5. Down-daemon failover so concurrent suites never exhaust memory silently (2026-09-05-16-002).
6. branch-cleanup removing worktree metadata with the worktree (2026-09-08-01-003).
7. Generator interpreter resolution instead of hard-coded uv (2026-08-25-09-008).
8. Named rejected flag in capture-footprint argparse failures (2026-09-14-05-003).
9. Accepted evidence named in build_scope_narrow freshness refusal (2026-09-08-13-009).
10. Daemon job-log path never surfaced as an agent read instruction (operator-observed 2026-09-20, no lesson id): routed legs return the daemon-side job-logs path in log_file and the safety-net message points the agent at it, producing an external-directory Read prompt; inline the excerpt or mirror project-local instead.

(Retired 2026-09-19: merge-mutex reclamation past hold budget — budget-reclaim
verb, stale-holder reclaim and waiter pruning exist at
manage-locks/scripts/merge_lock.py; verified in-tree before retiring.)

## Claim Labels

- OBSERVED: build_queue release fails from inside a worktree with cannot-resolve-main — read at `lessons-archive/2026-09-04-14-008.md` § Context.
- OBSERVED: a down daemon silently removes cross-plan serialization — read at `lessons-archive/2026-09-05-16-002.md` (title/component triage; body verified at outline).
- HYPOTHESIS: main-anchored checkout resolution fixes the worktree release path — confirm/refute at `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/` § build_queue release (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-pyproject/` — build queue, coverage-report.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/` — lock accounting, pollution guard.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/` — per-build rows.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/` — routed log_file path leak into agent-visible output (folded 2026-09-20 in the same act).
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/` — dispatch-boundary rows for finalize-step terminations (landing follow-up PLAN-01, folded from ledger-joins-002 in the same act: 45 execution vs 0 boundary rows in 6-finalize).
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/` — daemon failover.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none (lock/build surfaces are disjoint from ledger aspects).
- Adjacent to: WS-04/PLAN-08 git worktree paths without touching them.
- Landing follow-up (PLAN-01, #1545; folded from ledger-joins-002): stamp one
  dispatch-boundary row per finalize-step dispatch termination, or declare the
  finalize exclusion explicitly in dispatch_boundary_excluded_classes — 6-finalize
  holds 45 execution rows and no boundary file, so pairing and union_rows coverage
  cannot be evaluated there.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-205-build-telemetry.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
