envelope_version=1
sender_type=plan
sender_id=build-gates-test-suite-confidence-ci-workflow-lint
epic=truthful-signals
kind=landing
created=2026-08-25T15:01:38Z

# Landing — build-gates-test-suite-confidence-ci-workflow-lint

Build gates, test-suite confidence and CI workflow lint now report what they actually
checked. Landed as PR #1340, squash-merged through the platform merge queue to
`b5ee8fac7`.

```landing-facts
schema=landing-facts/1
plan_id=build-gates-test-suite-confidence-ci-workflow-lint
epic=truthful-signals
pr=#1340
merge_state=merged
deliverables_total=9
deliverables_done=9
total_tokens=11170290
total_wall_seconds=191926
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:done
step.create-pr.pr_number=1340
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.finalize-step-sync-baseline.action=rebased
step.record-metrics.total_tokens=11170290
step.record-metrics.total_wall_seconds=191926
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

Facts this run produced that no step recorded as a typed fact, carried as prose rather
than fabricated into one:

- **A mid-finalize rebase was required and hand-resolved.** The branch was found
  `mergeable: conflicting` against a main that had advanced 7 commits. 24 commits were
  replayed; 3 carried conflicts across 7 files (the `script-shared` build modules,
  `extension-api/standards/build-api-reference.md`, and two test files). No step records
  that this happened — `finalize-step-sync-baseline` had already recorded `done` against
  an earlier base and was skipped as not head-dependent.

- **The loop-back ceiling was raised 3 → 8 mid-run by operator decision**, and 6
  iterations were spent. The raise leaves no step record and no decision-log entry — only
  a `.plan/marshal.json` edit inside the plan's own footprint, which committed with the
  PR. A plan that needed its budget more than doubled currently reads identically to one
  that converged inside it.

- **The self-review round loop was self-seeding and was terminated rather than converged.**
  Three rounds (4 + 4 + 2 findings); 6 of the 10 settle-band findings were authored by the
  previous round's own fix. Rounds 1–2 re-seeded by rewriting an over-claim into a new
  claim; round 3 re-seeded despite adopting deletion, because removing interior sentences
  silently re-pointed a pronoun's antecedent. The loop's own termination condition
  ("a round found nothing new") cannot distinguish convergence from oscillation.

- **8 plugin-doctor findings were stale-executor artifacts, not source defects.** They
  pointed at a skill that arrived from upstream during the rebase; the worktree executor
  predated it. Regenerating cleared all 8 with zero source edits.

- **A required bot's participation needed an explicit trigger the loop could not reach.**
  `pr-agent` resolved `participated_stale`; Trigger B selects from the most recent
  bot-authored finding, which by then stamped the current HEAD, so it would have skipped
  forever. An explicit `/review` was fired manually.

- **CodeRabbit did not review the merge candidate.** It exhausted its 1-review-per-hour
  budget on the parent commit `e4eb22d0d`. Its `SUCCESS` CI check is a check conclusion,
  not review participation. The unreviewed delta is a 4-line test refactor that CodeRabbit
  itself requested.

- **Sourcery reviewed nothing at any point** — one structural size refusal on the first
  HEAD, then silence across six later HEADs. `participation_complete: true` therefore
  proves participation only: of three reviewers, one published an empty clean guide, one
  is credited on stale evidence, and one refused.

- **The daemon reconcile is owed, not done.** `marshalld` was busy at cache-sync time, so
  the upgrade deferred (`owed: true`, `defer_count: 1`) rather than draining a live build.

- **28 modified files sit outside every deliverable's declared surface**, 14 of them one
  coherent new skill (`pm-plugin-development:tools-epic-surface-partition`) that no
  deliverable names. Declared-surface recall itself was 100% (44/44).

- **Two live instrument defects were found by the review retrospective** and are not
  fixed: an un-ingested finding (empty top-level `body`) defaults to `actionable` because
  the meta test is a positive match, inflating `actionable_count` 18→20; and the
  retrospective cannot see `cuioss-review-bot` even though `automatic-review`'s
  `display_detail` holds the classification one step away.

- **Three of five operator turns were bare nudges** (`retry`, `contniue`, `contniue`) —
  the run stalled and needed hand-restarting three times, which no metric or step record
  captures.
