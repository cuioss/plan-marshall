envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-11-06T16:29:22Z

# Four plan-marshall findings from api-sheriff PLAN-V02-56 (plan-v02-56-final-cleanup), drained 2026-11-06

001 is a RECURRENCE of the re-fire-waiver vs merge-gate finding routed from PLAN-V02-53 in api-sheriff-api-sheriff-0-2-0-081.

---
# Candidate lesson: operator re-fire waiver does not satisfy the pre-merge gate

- component: plan-marshall:phase-6-finalize
- category (suggested): bug
- signal source: decision log (phase-6-finalize, pre_merge_gate)

## Observation

At final head 2a6d1a1c the operator waived the re-fire of finalize-step-simplify,
finalize-step-security-audit and code-review for a test-only commit (Sonar S5778 fix),
and that waiver was recorded in the decision log. When branch-cleanup then ran
`pre_merge_gate merge`, the gate refused with `merge_candidate_not_gated` because the
three steps were recorded at the previous head d8b84c67. The waiver did not count
toward the gate. The merge mutex had to be released, all three steps were re-run
narrowly over the single commit d8b84c67..2a6d1a1c, and the merge was attempted again
(it then succeeded).

## Defect shape

Two contracts disagree. The loop-back / re-fire waiver lets an operator skip the
re-fire of head-dependent steps, but the merge gate demands that those steps be
recorded at the merge-candidate HEAD. So the waiver only postpones the work and costs
a mutex acquire/release cycle. The decision log records the gate's own reasoning as
"an authorization never covers an unexamined tree".

## Suggested corrective direction

Either make the waiver flow warn up front that the merge gate will still require a
narrow re-run at the final HEAD, or run that narrow re-run as part of the waiver.
Then the operator does not discover the refusal only after taking the merge mutex.

---
# Candidate lesson: run finalize simplify and security-audit serially, not in parallel

- component: plan-marshall:phase-6-finalize
- category (suggested): anti-pattern
- signal source: decision log (manage-execution-manifest record-step, freshness-reconcile)

## Observation

In one finalize round, finalize-step-security-audit was recorded at 06:33:11. At
06:33:23 the freshness-reconcile entry logged that finalize-step-simplify had committed
955b174b, which moved the worktree HEAD past the tree the audit had examined. The
security audit then had to be recorded a second time, at 06:34:18. The two steps were
run at the same time. Simplify is the step that changes source (mutates_source), so its
commit makes any head-bound step running alongside it stale.

## Defect shape

When a step that commits source runs in parallel with a head-bound review step, the
review step goes stale and has to be re-run narrowly. This adds a dispatch round and
spreads head-binding drift into the merge gate.

## Suggested corrective direction

Dispatch finalize-step-simplify (and any other step that commits source) on its own
and wait for its commit to land. Only then dispatch the head-bound steps
(security-audit, code-review). Alternatively, have the dispatcher refuse to run a
source-committing step in parallel with a head-bound one.

---
# Candidate lesson: builds for an unlearned command key are clipped at the 300s default timeout

- component: plan-marshall:build-maven (dispatch via plan-marshall:build-server-client)
- category (suggested): bug
- signal source: decision log (phase-5-execute orchestrator-verify) and script execution log

## Observation

In phase 5, the quality gate for a new command key (verify -Ppre-commit scoped to
api-sheriff and deployment) timed out at the 300s default. The decision log says "new
command key"; when it was clipped, 5973 tests had passed and 0 had failed. Re-running
it with `--timeout 1200` passed in 404s. The script log shows the same 300s ceiling
again in finalize: `build-maven:maven run` returned at 300.84s (10:26:33) and at
300.72s (12:58:53). Each time, a second run that took 575-633s had to finish the build.
The build-server wait loop reported `job_status=running elapsed=299/300` with an ETA of
120-180s still to go.

## Defect shape

A command key with no learned duration gets a fixed 300s timeout. That is shorter than
a normal reactor quality gate in this project (about 400-630s), so the first run of any
new key is clipped and has to be repeated. A clipped build looks like a timeout and not
like a failure, but it still costs a full rebuild.

## Suggested corrective direction

Seed the default for an unlearned key from the architecture-resolved
`bash_timeout_seconds`, or from the longest learned duration of a sibling key in the
same module. Another option is to let the build-server wait continue while the daemon
reports the job as running with an ETA, instead of returning at the fixed ceiling.

---
# Candidate lesson: review_completeness rejects bare bot names in --participated-bots

- component: plan-marshall:phase-6-finalize (caller of plan-marshall:automatic-review:review_completeness)
- category (suggested): anti-pattern
- signal source: script_failure marker in the work log and the script execution log (13:49:14)

## Observation

During the branch-cleanup pre-merge review barrier, the following call exited 1 with
`error: malformed_bot_flag`:

    review_completeness check --plan-id ... --required-bots coderabbit --optional-bots sourcery --participated-bots coderabbit --refused-bots sourcery ...

The verb expects `bot_kind:evidence_kind` pairs (for example `coderabbit:inline`). It
rejects a bare `coderabbit` on purpose, because dropping it silently would make the bot
count as absent and block the merge for no real reason. The retry with a pair passed
three seconds later.

## Defect shape

The caller wrote `--participated-bots` with the same bare-name shape as
`--required-bots` / `--optional-bots` / `--refused-bots`. In the same argument list,
the participation flag alone needs pairs. Nothing in the call site shows this
asymmetry.

## Suggested corrective direction

In the phase-6-finalize pre-merge barrier instructions, put the pair form
(`bot_kind:evidence_kind`, for example `coderabbit:inline`) next to the
`--participated-bots` flag in the documented invocation. Or let
`malformed_bot_flag` list the accepted evidence_kind values, so the retry can be
built directly from the error.
