envelope_version=1
sender_type=plan
sender_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
kind=landing
created=2026-09-03T10:27:21Z

## What landed

dual-homed-hook-install-renders-identically shipped as PR #1384 (merged as 19453cb1b).

```landing-facts
schema=landing-facts/1
plan_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
pr=1384
merge_state=merged
deliverables_total=2
deliverables_done=2
total_tokens=4171248
total_wall_seconds=69885
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
total_worked_seconds=15745
total_billing_weighted=113009997
merge_mechanism=merge_queue
landing_commit=19453cb1b28196414c735d0806db53100ab81f1f
```

## Residue

**The spec's premise was half wrong, and the outline caught it.** PLAN-TRUTH-102 asserted that a
dual-homed install renders identically for BOTH checks. Only `display` did. The `hook` check already
had a dedicated both-files arm discriminating in prose, with `healthy: True` pinned by an existing
test. The hook half shipped as promote-and-name over an existing branch, and its test work was an
amendment rather than an addition.

**Scope grew twice, both operator-approved.** The doc footprint widened from the spec's 3 declared
files to 5 at outline (a content sweep found shipped docs asserting the two-value domain that the
Expected Surface never named), and a `manage-architecture` test-budget fix was added mid-finalize when
that unrelated test blocked the push gate.

**Six candidate-lesson messages (-009..-014) and eight retrospective-routed messages (-001..-008) are
queued for this epic.** The lessons-capture step could NOT verify dedup against -001..-008: no script
surface returns an inbox message body, so its dedup rested on the dispatching prompt's enumeration
rather than a read. That gap is itself candidate -014. If the drain finds an overlap, `inbox supersede`
is the clean disposition and this is the expected failure mode, not a producer error.

**Efficiency, stated against the run rather than the outcome.** `pre-submission-self-review` was 50.6%
of the plan — 1.85M tokens, 10 rounds, 13 defects, none of which reached the PR. Rounds 6-10 cost MORE
than rounds 1-5 for FEWER defects because the orchestrator repeatedly fixed the instance a finding
named rather than the class it belonged to, so each round rediscovered the sibling document. Estimated
avoidable cost ~572K tokens (~15.6% of the plan). The step was also closed `done` WITHOUT a confirming
clean round, at the point where rounds 6-10 had a 5-of-5 residue-hit rate — a deliberate, recorded
deviation from the Branch A precondition.

**Two reviewer-population signals the epic should not read at face value.** Sourcery's
`pct_resolved_as_fixed: 0.0%` is an artefact of a status-summary body being stored as actionable, not a
performance; and `automatic-review` recorded "3 bots reviewed head c9351957" while CodeRabbit's own
coverage marker reads `coveredCommitId=9befeefc` — the final fix commit was reviewed by pr-agent and
sourcery but not by CodeRabbit. The merge was still properly authorized, since pr-agent is the only
required bot and was current.

**A build-infrastructure incident cost significant wall-clock and distorted one lesson.** A marshalld
`timeout` verdict abandons the WAIT but never reaps the BUILD, so each documented "re-run once" stacked
another full pytest suite; three ran concurrently before a process-table scan reaped them. One
`timeout` verdict was also FALSE — the abandoned build had passed, 62 seconds after the budget elapsed.
Latency measured during that window contaminated lesson 2026-09-02-20-001, which has been corrected
in place.
