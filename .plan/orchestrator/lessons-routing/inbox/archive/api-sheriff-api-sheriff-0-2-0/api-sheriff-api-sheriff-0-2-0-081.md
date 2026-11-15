envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-11-05T19:25:33Z

## Six plan-marshall findings from API-Sheriff PLAN-V02-53 (plan-v02-53-plan-15-follow-up-issues, PR #565)

Routed by the api-sheriff-0-2-0 orchestrator drain on 2026-11-05. Each item is the sending plan's own observation, not re-verified on the plan-marshall side. Possible prior items were found by a keyword search of this epic's lessons-archive and inbox archive; treat them as leads for dedup, not as confirmed matches.

### 1. Source plan-v02-53-plan-15-follow-up-issues-003 — possible recurrence of the flag-invention class (lessons-archive INDEX; low/pm-mcp-core-m2-m4-144, -160)

#### Candidate lesson: manage-solution-outline rejected an invented `--number` flag (argparse, x2)

- Source signal: script-failure cluster `plan-marshall:manage-solution-outline` (2 argparse rejections, exit code 2)
- Plan: plan-v02-53-plan-15-follow-up-issues
- Tool surface: plan-marshall (manage-solution-outline CLI)

##### What happened

Two calls to `manage-solution-outline` passed a `--number` flag, which the parser does not declare, and were rejected with `unrecognized arguments` before the script body ran. The calls were reissued with the canonical flag.

##### Candidate rule / fix direction

This is the verb-scoped flag-invention recurrence class. Either the agent-facing docs or workflow text that led to `--number` should name the canonical deliverable selector, or the CLI should accept the alias. Worth checking which workflow text paraphrased the flag.

### 2. Source plan-v02-53-plan-15-follow-up-issues-004 — possible recurrence (filed-live-blockers/lessons-routing-046; medium/TokenSheriff/2026-10-31-13-004)

#### Candidate lesson: execute_commits_unrecorded at the 5-execute to 6-finalize transition after a finalize simplify commit

- Source signal: script-failure cluster `plan-marshall:manage-status` (error `execute_commits_unrecorded` at the 5 to 6 transition)
- Plan: plan-v02-53-plan-15-follow-up-issues
- Tool surface: plan-marshall (manage-status transition guard, phase-6-finalize item 5f, manage-change-ledger)

##### What happened

The 5 to 6 transition refused with `execute_commits_unrecorded`. The unrecorded commit was a5cebaef, the finalize simplify step's commit. It had no `kind=change` ledger row because finalize item 5f commit instrumentation does not append one, yet the transition guard counted it as an execute commit without a ledger record.

##### Candidate rule / fix direction

The guard and the commit producers disagree on which commits must carry a change-ledger row. Either finalize item 5f should append a `kind=change` row for every source-mutating finalize commit, or the guard should exclude commits produced by finalize steps. As it stands the guard fires on a path the pipeline itself produces.

### 3. Source plan-v02-53-plan-15-follow-up-issues-005 — possible recurrence (filed-live-blockers/TokenSheriff/2026-10-31-13-002; sweep-2026-11-01/lessons-routing-060)

#### Candidate lesson: the merge gate ignores an operator `loop-back close --waive-refire` for head-dependent review steps

- Source: orchestrator run observation (not a counted signal record)
- Plan: plan-v02-53-plan-15-follow-up-issues
- Tool surface: plan-marshall (phase-6-finalize merge gate, `merge_candidate_not_gated`, loop-back close)

##### What happened

After the Sonar fix push, the operator was offered `loop-back close --waive-refire` to skip re-running the review steps. The merge gate (`merge_candidate_not_gated`) still refused the merge because the head-dependent review steps had not run on the new head, so the waiver had no effect and all three reviews had to re-run.

##### Candidate rule / fix direction

Offering a waiver the gate will not honour costs an operator decision and buys nothing. Either the waiver should be recorded in a form the gate reads for head-dependent steps, or it should not be offered when the refire set contains head-dependent steps (and the prompt should say why).

### 4. Source plan-v02-53-plan-15-follow-up-issues-006 — possible recurrence (INDEX; inbox archive plan-v02-12-idp-addressing-model-001, plan-v02-46-...-003)

#### Candidate lesson: `git-workflow commit` reports FETCH_FAILURE when nothing is staged

- Source: orchestrator run observation (not a counted signal record)
- Plan: plan-v02-53-plan-15-follow-up-issues
- Tool surface: plan-marshall (workflow-integration-git, `git-workflow commit`)

##### What happened

`git-workflow commit` refused when there was nothing staged, but the error code was `FETCH_FAILURE`, which points at a network or remote problem. The real cause (empty index) had to be found by hand.

##### Candidate rule / fix direction

An empty index should get its own code (for example `NOTHING_TO_COMMIT`) or a no-op success with an explicit discriminator, so callers do not chase a fetch problem that does not exist.

### 5. Source plan-v02-53-plan-15-follow-up-issues-008 — possible recurrence (high/2026-10-12-05-002; filed-live-blockers/pm-mcp-core-m2-m4-235, -253)

#### Candidate lesson: a `pr checks --watch` wait right after a push exits before the new head's checks exist

- Source: orchestrator run observation (not a counted signal record)
- Plan: plan-v02-53-plan-15-follow-up-issues
- Tool surface: plan-marshall (CI wait after push; tools-integration-ci / await-long-running)

##### What happened

A background `pr checks --watch` wait started directly after a push exited immediately: the checks for the new head were not registered yet, so the watch saw the previous head's finished checks (or none) and returned at once, giving a false "done".

##### Candidate rule / fix direction

A CI wait after a push must be bound to the pushed head SHA: wait until checks for that SHA are registered before watching for completion, or verify the head SHA of the reported checks. A wait that is not bound to the head can report a result for the wrong commit.

### 6. Source plan-v02-53-plan-15-follow-up-issues-009 — no prior item found for rewait_bound

#### Candidate lesson: ci_complete_precondition rewait_bound 3 is too small for a 21-45 minute integration-test job

- Source: orchestrator run observation (not a counted signal record)
- Plan: plan-v02-53-plan-15-follow-up-issues
- Surface: plan-marshall finalize CI precondition (`ci_complete_precondition`, `rewait_bound`) together with this repository's CI duration

##### What happened

The finalize CI-completion precondition gives up after 3 re-waits. API-Sheriff's integration-test job takes about 21 to 45 minutes, so the bound ran out while CI was still legitimately running, and the wait had to be driven again by hand.

##### Candidate rule / fix direction

Either make the bound configurable per project (and set it for API-Sheriff to cover the integration-test job), or derive it from the observed CI duration rather than a fixed count.
