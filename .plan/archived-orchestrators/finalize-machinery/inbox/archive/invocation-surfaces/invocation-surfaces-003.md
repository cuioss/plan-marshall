envelope_version=1
sender_type=plan
sender_id=invocation-surfaces
epic=finalize-machinery
kind=landing
created=2026-09-17T07:49:12Z

## What landed

invocation-surfaces shipped as #1507 (merged).

```landing-facts
schema=landing-facts/1
plan_id=invocation-surfaces
epic=finalize-machinery
pr=#1507
merge_state=merged
cleanup_owed=false
deliverables_total=n/a
deliverables_done=n/a
total_tokens=0
total_wall_seconds=37299.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-security-audit:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,sonar-roundtrip:done,adr-propose:skipped,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:skipped,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done
```

## Residue

- No solution outline was ever composed (outline/plan phases collapsed at plan start), so deliverables ride `n/a` keys and the landing reads INCOMPLETE there. The 4 orchestrator-spec deliverables all shipped on the merged PR: executor reject messages naming flag plus sibling verb, ci/github_pr router-position acceptance, manage-plan-documents read redirect, and the measured-diff-size contract (already correct at HEAD, verified not re-broken). Three CodeRabbit follow-up findings on the first HEAD were fixed in a loop-back commit and re-reviewed clean.
- Process failure documented mid-run in inbox message `invocation-surfaces-001.md` (kind: finding): implementation began on the main checkout with the worktree unmaterialized; remediated via snapshot patch relocation into the worktree and Step 2.5 materialization before any commit.
- Metrics totals are a floor (0 tokens): phase boundaries for 2-refine/3-outline/4-plan were never stamped and no session identity exists on this target, both recorded in the record-metrics detail and work log.
- One candidate lesson was proposed by plan-retrospective to epic finalize-machinery (lessons_proposed: 1, recorded: 0) for orchestrator-side pickup.
