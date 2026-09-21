envelope_version=1
sender_type=plan
sender_id=every-test-runs-and-the-suite-does-not-slow-down
epic=test-quality
kind=landing
created=2026-09-06T10:22:13Z

## What landed

every-test-runs-and-the-suite-does-not-slow-down shipped as #1426 (merged).

```landing-facts
schema=landing-facts/1
plan_id=every-test-runs-and-the-suite-does-not-slow-down
epic=test-quality
pr=#1426
merge_state=merged
deliverables_total=7
deliverables_done=7
total_tokens=7240427
total_wall_seconds=116483
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:done
step.record-metrics.total_tokens=7240427
step.record-metrics.total_wall_seconds=116483
step.record-metrics.any_phase_missing_end_time=false
step.branch-cleanup.merge_state=merged
step.branch-cleanup.merge_mechanism=merge_queue
step.create-pr.pr_number=1426
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=1
```

## Residue

**D6's owed run-condition commands.** `test/README.md` now carries a literal runnable
command for run condition 3 (skipped count) and run condition 4 (wall-clock), both
readable off the canonical `module-tests` command because `-rsfE` was added to the
pytest `addopts` that already carried `--durations=25`. The epic ledger's
run-conditions note still needs these mirrored in; that mirroring is the
orchestrator's write, not this plan's.

**The epic's premise figure moved.** The epic's landed reports record `… 14 skipped`
four times. The live baseline at plan start was **11**, and the after figure is also
11 — equal to the size of D5's enumerated exception list. The 14 was never
re-derived by this plan and should not be carried forward unchecked.

**Measured outcome against run condition 4.** 276.44s → 220.19s on the same command
while gaining 35 tests (24570 → 24605 collected). That is −56.25s, above the
measurement protocol's stated 20-second detection limit. One interval inside the run
went the other way (+21.95s, D6 → final), also above the limit, with two unisolated
causes (+30 tests, machine state). Every figure is single-run.

**Scope-creep measurement was unavailable for the whole run.** `references.json`
carries no `plan_creation_sha`, so `scope_creep_check` returned `could_not_look` on
every task and `residual_count` is ABSENT, not zero. The one run that most needed it
carried an operator-authorised write-boundary widening into 7 `marketplace/bundles/**`
files.

**Operator-authorised write-boundary widening.** The plan spec put
`marketplace/bundles/**` out of scope ("a production defect found here is recorded,
never fixed"). The operator explicitly chose to fix two build-tooling defects there:
a pytest collection error reported as `failed=0` with an empty failure list (the
pre-fix parse surface reported `build_status=SUCCESS` over a log carrying 16
collection errors), and the build-server routing layer discarding the inner wrapper's
per-test structured errors. Recorded expansion, not drift — PLAN-090, which owns that
surface, had already landed.

**Three skip sites survive in classes the plan set out to empty**, all unreachable in
practice (which is why the run is green at 11), plus a sixth class was added on
operator decision for in-suite policy / data-driven skips that fit none of the
original five.

**The strict serial reverse-order hermeticity arm was NOT run** (~53 min CPU). The
perturbed-order arm ran and passed, with proof the reversal reached pytest.

**A loop-back ceiling breach.** All 3 iterations were consumed and a 4th was requested
by the re-review; the operator's standing unattended instruction overrode the halt.
Recorded at WARNING, without mutating `max_iterations`. The retrospective's follow-up
finding is that the 4th cycle bypassed `set-phase`, so three head-dependent gates never
re-armed and stayed anchored to superseded commits while still reading `done` — lesson
`2026-09-06-10-001`.

**Lessons routed to the global store, not this inbox.** The orchestration verdict was
resolved late in this run, so `project:finalize-step-review-retrospective`,
`plan-marshall:plan-retrospective` and `lessons-capture` each ran with
`orchestrated=false` and wrote to the global lessons corpus rather than emitting
`kind: candidate-lesson` here. Nothing is lost — `2026-09-06-10-001`,
`2026-09-06-10-002`, and recurrence sections appended to six live lessons
(`2026-08-25-09-001/003/004/009`, `2026-09-04-14-007`, `2026-09-04-17-004`,
`2026-09-06-08-001`, `2026-09-04-17-014`, `2026-09-03-11-002`) — but the epic did not
receive them through the inbox channel and may want to drain them from the corpus.

**Main is red on the local whole-tree quality-gate, pre-existing.** Two errors at
`build-server-client/SKILL.md:161` claim `--timeout` is undeclared on
`build_server submit`. The claim is false — `--help` declares it — so this is a
plugin-doctor false positive, and both failures reproduce on the parent commit
`0fde908d0`. Lesson `2026-09-06-10-002`.
