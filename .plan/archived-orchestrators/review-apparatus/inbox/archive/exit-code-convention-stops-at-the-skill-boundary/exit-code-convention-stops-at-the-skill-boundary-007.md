envelope_version=1
sender_type=plan
sender_id=exit-code-convention-stops-at-the-skill-boundary
epic=review-apparatus
kind=landing
created=2026-09-06T19:44:10Z

# Landing: PLAN-PR-036 — the exit-code convention stops at the skill boundary

Shipped as TWO PRs after a review-driven split. The convention now has exactly one body in the
tree; every other executor-invoking document points at it.

```landing-facts
schema=landing-facts/1
plan_id=exit-code-convention-stops-at-the-skill-boundary
epic=review-apparatus
pr=1429
merge_state=merged
deliverables_total=4
deliverables_done=4
total_tokens=2845626
total_wall_seconds=128056
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done
step.branch-cleanup.pr_part1=1423
step.branch-cleanup.merge_sha_part1=0fde908d03e0a6f0ffef15cede6d71fd6ce83d42
step.branch-cleanup.merge_sha_part2=de10dfa97d7b7d391582cacb5530f9fba49f0236
step.branch-cleanup.superseded_prs=1419,1428
step.automatic-review.coderabbit_findings=7
step.automatic-review.coderabbit_fixed=5
step.automatic-review.coderabbit_taken_into_account=2
step.project:finalize-step-review-retrospective.comparison=indeterminate
step.project:finalize-step-review-retrospective.reviewer_coverage=0/3
```

## Residue

**The plan shipped the OPPOSITE payload to the one it was specified with, and the redirect was the
operator's at the review gate.** D2 originally inserted the three-clause convention block VERBATIM
into 131 documents (+1602/−10). It now states the convention once, at
`tools-script-executor/standards/exit-code-convention.md`, with a one-line reference everywhere
else — a NET REMOVAL of ~549 lines. The spec's D1 as written ("the widened form, verbatim") is what
produced the first shape; the spec was not wrong about the gap, only about the remedy.

**The causal chain behind that six-hour detour is mechanical and is the epic's most valuable
carry-out.** `lessons-consult` ran, succeeded, and searched exactly ONE component
(`tools-integration-ci`) — derived from a 9-file declaration against a realized 158-file footprint.
Lesson `2026-08-27-16-005` carries `component: plan-marshall:phase-6-finalize` and its proposed
action is verbatim what the operator later redirected the plan to do. It came from PR #1356, the
immediately preceding plan, and was invisible because its component fell outside the shrunken
consult set. Under-declared `affected_files` does not merely mis-measure — it gates which lessons a
plan can see.

**CodeRabbit refused the unsplit PR on a hard 100-file cap and the recovery cost ~4.5 hours.** The
refusal message "Review rate limited" names two structurally different conditions with different
remedies: a quota wall (wait) and `@coderabbitai review` being the INCREMENTAL verb with no
unreviewed commit (change the verb). Four attempts were lost to that conflation; three of them were
91–94 minutes apart, which an hourly quota cannot explain. What worked was `@coderabbitai full
review`, accepted in 10 seconds on the same PR and HEAD.

**REFUTED — record this against the epic's own prior belief.** Closing and reopening a PR does NOT
push the CodeRabbit window. Converting the stated ETAs to absolute instants, #1419's `12:49:31 +38m`
and #1428's `13:06:37 +21m` both resolve to `13:27:3x` — the same instant 6 seconds apart, spanning
a close and a fresh open. The window is ORG-scoped, so any other PR in the org spends the same
bucket; no reset mechanism is needed to explain the later shift.

**The size refusal no longer exists.** #1419's original comment said "158 files, 58 over the limit
of 100"; the same `issue_comment` was later EDITED IN PLACE and now carries a rate-limit body
describing a 63-file diff that did not exist when it was posted. A bot refusal is a mutable surface.

**Four defects were found INSIDE guards this plan wrote to close a completeness gap** — a vacuous
`assert X == X`, a false universal, an order-dependent classifier, and a reachability-first test that
would accept a forbidden heading. Two were caught locally, two by CodeRabbit; 43% of CodeRabbit's
findings landed on the coverage claim of the instrument itself.

**Known bounded gap, declared not hidden:** 24 `manage-*`-only documents keep their narrower section
and are dropped by retention rule (c). The canonical standard names this in its § Purpose carve-out,
and rule (c)'s docstring records that the carve-out is a scope boundary, not a sufficiency claim.

**Ten findings filed, all pending, none blocking:** `5a7fff` / `20b4ad` (affected_files under-records
and gates lesson consult), `bef3a0` (refusal_structural escalation unreachable at default config),
`73fd9c` (registry pin gap re-opened AND widened by this finalize's own sync), `01ff9a`
(automatic-review does not follow a PR split — the `pr-comment` store stayed empty), `0e29b2` (bot
refusals are mutable), `260d31` (refusal-message conflation), `7e01ed` (change-ledger has recorded
nothing since 2026-09-04; `pre-commit-verify-freshness` reads it), `bd4eb9` (loop-back leaves no
metrics boundary), `c9c61c` (two confident zeros).
