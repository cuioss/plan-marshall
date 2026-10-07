envelope_version=1
sender_type=plan
sender_id=user-language-and-vocabulary
epic=operator-ux
kind=landing
created=2026-09-03T06:12:01Z

## What landed

user-language-and-vocabulary shipped as #1382 (merged).

```landing-facts
schema=landing-facts/1
plan_id=user-language-and-vocabulary
epic=operator-ux
pr=#1382
merge_state=merged
deliverables_total=2
deliverables_done=2
total_tokens=6683572
total_wall_seconds=54285
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,plan-marshall:automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:done
step.branch-cleanup.merge_commit_sha=219da7b1dbbd73ee4cf74df4d3c09c2e27ecbc52
step.branch-cleanup.merge_route=merge_queue
step.project:finalize-step-deploy-target.emitted_count=1181
step.project:finalize-step-sync-plugin-cache.synced_count=10
step.project:finalize-step-sync-plugin-cache.version=0.1.1584
step.plan-marshall:plan-retrospective.lessons_recorded=6
step.lessons-capture.inbox_messages_written=2
step.finalize-step-preference-emitter.hints_filed=0
loop_back_iterations=2
loop_back_max=5
```

## Residue

Items the epic should track that no step recorded as a fact.

**PLAN-06 delivered its spec in full, and refuted one of its own hypotheses.** The spec's HYPOTHESIS
that a `marshal.json` top-level scalar was the right home for the language setting was refuted on both
horns at outline: `project_dir` is the only bare top-level scalar and is deliberately outside
`get_default_config()` (so a new one would have neither a seed nor a back-fill path), and `plan.*` is
phase-workflow-scoped while the rule also governs `marshall-steward` and `plan-orchestrator` output.
It landed as `project.user_language`. PLAN-07 extends `standards/user-communication.md`, which this
plan CREATED, so the hard sequence PLAN-06→PLAN-07 held.

**One operator decision changed the shape of the deliverable.** The spec's verify-first clause asked
whether sub-agent returns are user-facing for the language rule. The operator settled `display_detail`
as IN scope and chose write-in-the-user's-language-then-ASCII-flatten over the recommended
English-with-jargon-stripped. Rule 1a therefore carries mandated transliteration examples and a
per-summary English fallback for non-Latin scripts, rather than an exemption. Worth carrying to
PLAN-07: the ≤80-char ASCII `display_detail` contract was NOT amended, only constrained.

**Scope grew by one file beyond the spec's declared Expected Surface**, operator-approved:
`_cmd_system_plan.py`. It was needed twice — first for the `_coerce_value` bool-coercion guard on the
write path, then for the field-name guard on the read path that a review round found.

**Review coverage was thinner than the quorum reports.** `participation_complete: true` and
`reviewer_coverage: 3/3` are PARTICIPATION figures. Actual automated review on #1382 was CodeRabbit
alone: `pr-agent` (the sole REQUIRED bot) published an empty Guide on all three rounds, and Sourcery
never reviewed — it is out of its 7-day 250k-diff-char budget with ~4 days remaining. Sourcery reaches
the reviewed-at-all set only because its quota-refusal wording is unmatched by its own declared
`refusal_patterns`; had it matched, the honest figure is 2/3 with one refusal. Second observation of
lesson `2026-09-02-08-001` (#1380, then #1382).

**Six self-review rounds found three defects the bots did not**, in a class CodeRabbit states it is
blind to ("an incremental review system [that] does not re-review already reviewed commits"): a
comment citing a code branch the same plan had deleted; an error-list bullet naming one verb where the
code covers two; and an off-by-one in an audit table whose last row justified a fail-closed claim by
pointing at a blank line. The third was in a file untouched since the delta anchor — only a
full-surface sweep could see it. Run review quality rested on two legs where the configuration
nominally provided four.

**Cost overran its anchor by 2.5x, and the overrun is structural.** `multi_module + feature` anchors at
2.5M; the run spent 6.7M, of which 4.3M (65%) was 6-finalize alone. Cause: each loop-back fix advanced
HEAD, invalidating every head-dependent gate, re-firing the whole settle band. Three full settle-band
passes for two loop-back iterations. Any epic-level estimate for a plan expecting review churn should
assume this multiplier until the verdict-currency surface is declared on more steps.

**A session-pinning gap makes this run's own self-assessment stale.** deploy-target stamped
`0.1.1584` and the cache sync was correct, but this session loads `0.1.1581` — so every agent
dispatched after the sync, including BOTH retrospectives that judged this run, read the pre-change
persona. Filed by plan-retrospective as a new candidate lesson.

**Five active lessons were reproduced in this single run** (`2026-08-25-09-001`, `-09-014`, `-09-009`,
`-09-008`, `2026-09-02-13-005`), all retained by housekeeping as "no coverage" hours earlier, none with
a landed remedy. Routed as a recurrence batch — corpus mutation is the orchestrator's.
