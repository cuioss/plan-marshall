envelope_version=1
sender_type=plan
sender_id=detector-and-auditor-integrity
epic=code-intelligence-substrate
kind=landing
created=2026-08-31T08:36:53Z
revision=1
amended=2026-08-31T08:38:05Z

# PLAN-CIS-051 landed — detectors now publish what they measured

```landing-facts
schema=landing-facts/1
plan_id=detector-and-auditor-integrity
epic=code-intelligence-substrate
pr=#1370
merge_state=merged
deliverables_total=9
deliverables_done=9
total_tokens=9415265
total_wall_seconds=157846
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:skipped,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:done
step.create-pr.pr_number=1370
step.branch-cleanup.action=merged
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.branch-cleanup.work_performed=true
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=4
merge_commit_sha=7845a4b9a383a4d58c9314bfce89970ced67c4f7
merged_at=2026-08-31T07:47:15Z
spec_id=PLAN-CIS-051
workstream=WS-07
tasks_completed=26
loop_back_iterations=2
files_modified=54
final_verify=green
final_verify_tests=23631
billing_weighted_total=244268269
```

## What shipped

Nine deliverables. Every detector this plan touched now publishes the measurement
its verdict rests on:

- `check-dispatch-audit`'s `ran_inline` is no longer a fall-through default. A
  measured zero, a dispatched step whose `<usage>` never arrived, and a row with
  no `total_tokens` column at all were collapsing into one grade; they are now
  distinguishable, and `not_evaluated` exists as a fourth grade.
- `compile-report` decides section emptiness by ONE discriminator across the emit
  and non-emit paths, so a clean run stops being reported as a dropped section —
  and a non-dict fragment carrying real prose stops being lost the other way.
- The archived-plan auditor's documented key precedence is operative for the first
  time, and its main-anchored vs cwd-scoped resolver split is explicit rather than
  collapsed.
- `check-routing-decisions`' summary totals over the statuses its own code emits
  (`inconclusive` included).
- The marketplace dependency validator partitions unresolved rows by reason and
  gained a verb-set-drift analyzer — which found 2 genuinely unresolved rows the
  old validator could not see.
- A self-review delta round publishes per-class coverage counts, six classes each
  seeded to zero so a missing key reads as "not measured" and a zero reads as
  "measured, none found".

Deliverable 9 ran 42 mutations across deliverables 2-8. Four killed no test; each
was given a killing test, proven RED under its re-applied mutation and GREEN after
restore, both observations recorded. 42/42 now bite.

## Findings carried forward — already filed, not re-raised here

- `detector-and-auditor-integrity-001.md` — qgate `3e7381`
  (`pre-commit-verify-freshness` is canonical-blind: it marked a tree fresh on a
  test-compile row while that tree's module-tests timed out with no verdict) and
  qgate `00d481` (footprint sites 2 and 4 emit a bare count with no basis).
- `-002.md` — `phase-3-outline/SKILL.md:480` normatively promises a phase-4-plan
  Q-Gate finding that phase-4-plan does not implement. The divergence predates
  this plan (`git diff main...HEAD` over both files is empty); only the one false
  restatement was this plan's, and it was deleted.
- `-003.md` .. `-012.md` — ten candidate-lessons from the retrospective, including
  two more instances of this plan's own subject found in its own instrumentation
  after it landed.
- `-013.md` — one owed `architecture enrich` best-practice hint, plus the
  preference-emitter admissibility gap it exposed.

## Residue — facts no step recorded

**The merge mutex was overridden on operator instruction** after ~50 minutes
blocked by a sibling plan, and the cost materialised: the first enqueue was
EJECTED when four upstream PRs landed during the queue wait, forcing a rebase, a
re-derived constant, a full re-verify, a force-push and a re-review to clear a
required bot gone stale. No step records this; it is operator narrative.

**The rebase conflict could not be merged, only measured.** `EXPECTED_MARKER_ANCHORS`
was 24 upstream and 26 here; the truth on the merged tree was 25. A three-way merge
picking either literal would have shipped a false measurement into a test whose
purpose is to publish a real one.

**The reviewer asymmetry.** `pr-agent` — the one REQUIRED bot — returned "No major
issues detected" in all three rounds, on a diff that grew to 9651 changed lines and
against which CodeRabbit (OPTIONAL) filed 25 findings with zero false positives. It
satisfied the quorum every time while corroborating nothing. Sourcery refused
structurally on diff size in every round and never reviewed. The quorum proves
participation; it is not evidence the diff was reviewed.

**A producer disagreement, unresolved.** A re-review returned
`head_sha_verified: false` while its matched body named the current HEAD and its
`updated_at` post-dated the trigger; the subsequent `fetch_findings` classified the
same event as current participation. Two producers, one event, opposite verdicts.

## Instrument gaps the epic should weigh

Coverage boundaries, not clean zeros:

- `scope_creep_check` returned `could_not_look` / `no_baseline_sha` on EVERY call
  for the entire plan — `references.json` carries no `plan_creation_sha`, so no
  scope-creep guard ran at any point.
- `references.affected_files` under-recorded the real write set on at least seven
  occasions. Any figure derived from that field understates.
- `review_commitments reconcile` returned `clear` twice — first over a population
  of 0, then over 17 commitments with 0 deletions considered. Both vacuous; one of
  the 17 was unanchored and outside the seam's reach entirely.
- The context-cost channel measured 0 of 33 rows, on a plan where cache_read is
  ~99% of billing weight.
- `documented-verb-set-drift` is opt-in and absent from the 37-rule quality gate,
  so the three-defect fix in `_declares_main_guard` was exercised by its module
  tests and a corpus sweep — not by the green gate run.
- Plan-time `execution_tier` stamps were stale for every `module-tests` form.
- `metrics.toon` records `re_entered_phases: []` and `5-execute close_count: 1`
  despite two recorded loop-back iterations, so the `6-finalize` token figure
  covers both loop-back execute passes as well as finalize.
