envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=landing
created=2026-08-24T20:18:45Z

## What landed

metrics-ledger-readers-and-timestamp-provenance shipped as #1342 (merged).

```landing-facts
schema=landing-facts/1
plan_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
pr=#1342
merge_state=merged
deliverables_total=9
deliverables_done=9
total_tokens=7003398
total_wall_seconds=126004
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.action=merged
step.create-pr.pr_number=1342
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=5
total_billing_weighted=94666978
total_worked_seconds=26841
merge_commit=91bbe7470
```

## Residue

**A SECOND `kind: landing` message exists for this plan and is SUPERSEDED by this one.**
Message `metrics-ledger-readers-and-timestamp-provenance-015.md` was written by
`lessons-capture` at `order: 991`. The current contract moved the landing to this
dedicated terminal step precisely so it could carry facts produced after 991 —
`record-metrics` closes the token ledger at 998. Message 015 therefore cannot carry
`total_tokens`, `total_wall_seconds`, or the outcomes of steps 992-999. It was emitted
because this session's skill registry is pinned at plugin cache `0.1.1240` while the
executor resolves `0.1.1542`, so `lessons-capture` was served a body that still owned
the landing. **Drain THIS message and discard 015.**

**Steps whose verdict is narrower than it looks.**
- `automatic-review` reads `0 comment(s) found`, which is the third firing at the final
  head, not the run's review total. Across three firings the PR drew 8 findings: 6 from
  CodeRabbit (4 Major) and 1 from pr-agent, plus meta. 2 were fixed, 4 declined on
  evidence.
- Only 2 of 3 configured reviewers ever read this diff. `sourcery` is `unmeasurable`,
  not clean — it refused structurally on a 150000-diff-character ceiling against a
  measured 2737 changed lines, at every head.
- `pre-submission-self-review` shows 8 firings, 7 `failed`. That is the loop working:
  9 contract-drift defects found and fixed, closing CONVERGED on a full-surface clean
  pass. The rounds that converged were the ones resolved by DELETION.

**Unfixed, recorded, out of this plan's footprint** — eight findings for the epic to
route. The highest-value three are all this epic's own theme:
- `5af193` the routed build reports `tests_run: 0` on every GREEN run while the inner
  log records thousands; green-path only, which is the dangerous direction.
- `21cc74` for most of this PR's life CI verified NOTHING — zero `pull_request` runs,
  every push run skipping the heavy verify, required check green throughout. A review
  bot caught a real test failure CI structurally could not. Resolved only at the final
  force-pushed head, where `verify / verify` ran 792s and passed.
- `2f0994` `scope_creep_check` emits `residual_count: 0` with `reason: no_baseline_sha`
  — an unmeasured comparison rendered identically to a clean one.
Also: `e0e2c8`, `b2153c`, `dfcad2`, `10d566`, `7579da`, and `191008` (still `pending`).

**Residue on disk.** `worktree-remove` timed out twice on a 60s git budget — the
worktree at `.plan/local/worktrees/metrics-ledger-readers-and-timestamp-provenance`
survives, and the local branch cannot be deleted while it holds it. Cause established:
`.plan/temp/pytest-basetemp` is large enough that `git clean -ndx` produced an 11.3 MB
listing, much of it nested git repositories from test fixtures. Plan state is safe —
`integrate_into_main` moved the plan dir back to main first.

**Budget.** 7.00M tokens / 94.67M billing-weighted against a 2.0M error anchor for
`multi_module+bug_fix` — 3.3x. The self-review loop alone consumed ~1.4M across 7
rounds and found 9 real defects with zero false positives; the plan retrospective a
further 310K. `total_worked_seconds` is an n=5/6 floor: one phase carries no worked
measurement.
