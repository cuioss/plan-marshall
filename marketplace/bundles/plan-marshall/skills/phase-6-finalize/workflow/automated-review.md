---
name: default:automated-review
description: CI automated review
order: 30
requires: [ci-complete]
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
configurable:
  - key: review_bot_buffer_seconds
    default: 180
    description: Buffer (seconds) before the automated-review bot comment poll, consumed by the pr wait-for-comments wait.
  - key: re_review_on_loopback
    default: false
    description: Gate (default-off) for re-requesting a fresh bot review after a phase-5 loop-back fix commit advances HEAD past the reviewed_commit_sha of the staged pr-comment findings (trigger B). When false, a loop-back fix commit is NOT re-reviewed by the automated bots.
  - key: re_review_on_branch_cleanup
    default: true
    description: Gate (default-on) for re-requesting a fresh bot review after branch-cleanup rebases and force-pushes the feature branch onto base (trigger A). The automated-review step owns this knob; branch-cleanup reads it to decide whether to re-review the rebased HEAD. When false, the rebased/force-pushed HEAD is NOT re-reviewed.
---

# Automated Review

Pure executor for the `automated-review` finalize step. Drives the consumer-side orchestration for `pr-comment` findings as defined in [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) — this document owns the manifest-step list (review-bot buffer, producer call, gate-keeping query, intra-finalize re-capture, mark-step-done). The per-finding LLM core (decision + action + overflow handling) is dispatched once as `verification-feedback` (`producer=pr-comment`) — see "Dispatch the per-finding triage core" below. Refer to [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) for the architecture-level synthesis (producers, store schema, invariant gate, extension contract).

CI completion is a dispatcher-resolved precondition declared via the frontmatter `requires: [ci-complete]` field — the phase-6-finalize dispatcher invokes its precondition resolver (see [`../SKILL.md`](../SKILL.md) Step 3 § "Precondition resolution") before this body executes and guarantees CI is green. On `wait_failed`, the dispatcher skips this body entirely and marks the step `failed` with `display_detail "ci_failure (precondition)"`. This body therefore never observes a CI-not-ready condition and never needs to poll CI itself.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `automated-review` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

## Timeout Contract

This step runs as inline orchestration (producer fetch + finding enumeration in main context) plus a single `verification-feedback` Task dispatch (`plan-marshall:execution-context-{level}` resolved via `manage-config effort resolve-target --phase phase-6-finalize --role verification-feedback`) under a **15-minute (900 s) per-agent timeout budget** enforced by the SKILL.md Step 3 dispatch loop. The budget is **triage-only**: it covers the review-bot buffer, producer-side comments-stage, per-finding triage dispatch with `producer=pr-comment`, thread replies, and thread resolution. CI wait time is bounded separately by the dispatcher's `ci-complete` precondition resolver (600 s ceiling) — splitting the wait out keeps this triage budget bounded by comment volume rather than CI queue depth.

**Graceful degradation**: When the wrapper expires:

1. The dispatcher logs an ERROR entry at `[ERROR] (plan-marshall:phase-6-finalize) Step default:automated-review timed out after 900s — marking failed and continuing`.
2. The dispatcher marks this step `failed` via `manage-status mark-step-done … --outcome failed --display-detail "timed out after 900s"`.
3. The dispatcher continues with the next manifest step. The pipeline does NOT abort; later steps still run.
4. On the next Phase 6 entry, the resumable re-entry check sees `outcome=failed` and retries this step from scratch (one fresh attempt per invocation).

There is no internal soft-timeout, polling cap, or partial-progress checkpoint inside this document — the wrapper is the only timeout authority. Standards-internal commands (`pr wait-for-comments`) carry their own short polling intervals but never their own outer ceiling. **Pre-emptive overflow handling** lives in [`triage.md`](triage.md) § Step 5: the dispatched triage subagent files a `pr-comment-overflow` finding and returns `status: loop_back` when its budget is nearly exhausted, so high comment volume produces a clean loop-back rather than a wrapper timeout.

## Inputs

- A PR exists (from `create-pr` earlier in the manifest list, or pre-existing on the branch)
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All `ci`, `github_pr`, and build-script invocations below MUST identify the worktree via either `--plan-id {plan_id}` (preferred — auto-resolves through `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (escape hatch / explicit override). The two flags are mutually exclusive. Examples below use the literal `--project-dir {worktree_path}` form; substitute `--plan-id {plan_id}` to use auto-resolution.

## Execution

### Get PR number

Use the `pr_number` from the create-pr step. If not available:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr view
```

Read `pr_number` from the TOON output. If `ci pr view` returns `status: error` (no PR exists for the branch), this step has nothing to process — record `done` with a `display_detail` of `no PR available` (Branch B in "Mark Step Complete" below) and return.

### Re-review after a loop-back fix commit (trigger B)

This step fires on a **re-entry** of `automated-review` after a phase-5 loop-back: a fix commit produced during the loop-back has advanced the worktree HEAD past the `reviewed_commit_sha` stamped on the staged `pr-comment` findings, so the bot reviews on record are stale for the new tree. It is gated by the `re_review_on_loopback` config knob (default `false`) and reuses the D2 `bot_kind`-keyed re-review registry — it does NOT post a duplicate review request for a bot that auto-reviews on push (CodeRabbit), and it explicitly re-triggers a bot that does not (Gemini). The fresh review is then surfaced through the existing `comments-stage` → triage pipeline below — this is NOT a parallel path.

Read the gate from the plan-local execution-manifest step-params snapshot (the same one-stop call used for `review_bot_buffer_seconds`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  step-params get --plan-id {plan_id} --phase 6-finalize --step-id automated-review
```

Read `re_review_on_loopback` off the returned `params` object (default: `false`). **When `re_review_on_loopback == false`**, skip this entire section and proceed directly to "Wait for review-bot comments" below.

**When `re_review_on_loopback == true`**, evaluate the HEAD-vs-`reviewed_commit_sha` advance:

1. Read the most recent `reviewed_commit_sha` and `bot_kind` from the staged `pr-comment` findings. Query the store and read the two fields off the latest finding:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
     --plan-id {plan_id} --type pr-comment
   ```

   If the result's `findings` list is empty, there is no prior reviewed SHA to compare against — skip this section and proceed to "Wait for review-bot comments". Otherwise capture `{reviewed_commit_sha}` and `{bot_kind}` from the most recent finding. A finding with no `bot_kind` (human author) is NOT a bot review — skip the re-review for it.

2. Resolve the current worktree HEAD SHA:

   ```bash
   git -C {worktree_path} rev-parse HEAD
   ```

   Capture stdout as `{head_sha}`. **When `{head_sha} == {reviewed_commit_sha}`**, HEAD has NOT advanced past the reviewed commit — there is nothing new to re-review. Skip this section and proceed to "Wait for review-bot comments".

3. **When `{head_sha} != {reviewed_commit_sha}`** (HEAD advanced past the reviewed commit) AND `{bot_kind}` is set: capture the loop-back fix-commit push time as `{push_time}` (the ISO-8601 commit/push time of the HEAD commit — `git -C {worktree_path} show -s --format=%cI HEAD`), then invoke the D2 re-review registry for the new HEAD. For a CodeRabbit `bot_kind` the `request_fresh_review` is a NO-OP — the loop-back fix-commit push already auto-triggered the review, so no `@coderabbitai review` comment is posted and the await uses `{push_time}` as the trigger time; for a Gemini `bot_kind` the registry posts `/gemini review` then awaits. See [`workflow-integration-github` SKILL.md § Canonical invocations → `github_re_review re-review`](../../workflow-integration-github/SKILL.md#github_re_review-re-review):

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_re_review re-review \
     --pr-number {pr_number} --bot-kind {bot_kind} --head-sha {head_sha} --push-time {push_time} --plan-id {plan_id}
   ```

   Read `matched` from the returned TOON. The fresh review (when matched) is now on the PR; proceed to "Wait for review-bot comments" and "Producer: stage PR comments as findings" below, which re-runs `comments-stage` — this re-stamps every finding's `reviewed_commit_sha` to the new HEAD and re-triages the new comments through the existing per-finding dispatch pipeline. The `reviewed_commit_sha` is updated implicitly by that fresh `comments-stage` run; no separate update call is needed.

### Wait for review-bot comments

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr wait-for-comments \
  --pr-number {pr_number} --timeout {review_bot_buffer_seconds}
```

`{review_bot_buffer_seconds}` is the `default:automated-review` step's `review_bot_buffer_seconds` param, read from the plan-local execution-manifest step-params snapshot in a single one-stop call: `manage-execution-manifest step-params get --plan-id {plan_id} --phase 6-finalize --step-id automated-review` (then read `review_bot_buffer_seconds` off the returned `params` object; default: 180; max-wait ceiling, not a fixed delay). The polling subcommand exits as soon as a new review-bot comment is posted.

| Script Output | Action |
|--------------|--------|
| `status: success`, `timed_out: false` | New comment(s) detected — proceed to producer-stage |
| `status: success`, `timed_out: true` | No new comment within timeout — proceed to producer-stage anyway (the producer will surface whatever is on the PR) |
| `status: error` | Treat as warning, log, proceed to producer-stage best-effort |

### Producer: stage PR comments as findings (entry-point)

Call the producer-side comments-stage subcommand once. It fetches PR review comments, applies pre-filters (already-resolved threads, obvious text noise, and cross-iteration duplicate comments), and writes one `pr-comment` finding per surviving comment into the per-plan findings store.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
  comments-stage --pr-number {pr_number} --plan-id {plan_id}
```

(For GitLab projects the equivalent producer is `plan-marshall:workflow-integration-gitlab:gitlab_pr comments-stage`. Provider selection is whichever matches `manage-providers` for the plan's host; only one of the two is invoked per finalize run.)

The producer is the ONLY surface that fetches and stores `pr-comment` findings. This document does not classify, decide, or act on comments inline — every consumer-side action below reads from the findings store via `manage-findings list`.

### Consumer: enumerate pending pr-comment findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
  --plan-id {plan_id} --type pr-comment --resolution pending
```

If the result's `findings` list is empty, there is nothing to process — proceed directly to "Handle findings (loop-back)" with `loop_back_needed = false`, then "Mark Step Complete" Branch A with `0 comment(s) resolved (no loop-back)`.

### Dispatch the per-finding triage core

When the query above returns one or more pending `pr-comment` findings, dispatch the unified feedback workflow [`verification-feedback.md`](../../plan-marshall/workflow/verification-feedback.md) with `producer=pr-comment`. That workflow's Step 1 verifies the store-only query, then delegates the per-finding LLM-judgement core to [`triage.md`](../../plan-marshall/workflow/triage.md) Steps 1-6 — single source of truth for the smart-grouping algorithm, the per-outcome action bodies (FIX / SUPPRESS / ACCEPT / AskUserQuestion), the overflow / timeout handling, and the Scope-Deviation Escalation guard.

The dispatch is **by reference** — the prompt carries `producer=pr-comment` and `pr_number={pr_number}` only; the subagent issues its own `manage-findings list` against the same store as its first workflow step, so the orchestrator's query above is purely a gate-keeping count (skip dispatch when empty).

Compute the target variant via the role resolver, then dispatch:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase phase-6-finalize --role verification-feedback
```

Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch and the post-resolve log line below.

Emit the standardized post-resolve dispatch log line — see [`../../ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:phase-6-finalize) target={target} level={level} role=verification-feedback workflow=plan-marshall:plan-marshall/workflow/verification-feedback.md plan_id={plan_id}"
```

```
Task: plan-marshall:{target}
  prompt: |
    name: verification-feedback
    plan_id: {plan_id}
    skills[5]:
    - plan-marshall:manage-findings
    - plan-marshall:manage-tasks
    - plan-marshall:manage-architecture
    - plan-marshall:manage-config
    - plan-marshall:tools-integration-ci
    workflow: plan-marshall:plan-marshall/workflow/verification-feedback.md

    producer: pr-comment
    pr_number: {pr_number}
    caller_phase: phase-6-finalize

    WORKTREE: {worktree_path}
```

The subagent's return TOON carries `findings_processed`, `findings_resolved`, `fix_tasks_created`, optional `fix_task_numbers[]`, optional `overflow_deferred`. Capture those values for the "Handle findings (loop-back)" branch below.

When the subagent returns `status: loop_back` it has either created fix tasks (FIX outcomes) or filed an overflow envelope — both require the manifest dispatcher to re-fire `automated-review` on next phase-6-finalize entry.

#### Heartbeat-emission contract (consumer-side observability)

The dispatched `verification-feedback` subagent (with `producer=pr-comment`) MUST emit a `[STATUS] processing comment thread N/M` work-log line every 3-5 comment threads it processes, where `N` is the current thread index (1-based) and `M` is the total pending `pr-comment` count returned by the gate-keeping `manage-findings list` query above. The cadence is normative — emission MAY occur on any thread within the 3-5 window (e.g., every 3rd, 4th, or 5th thread), but the orchestrator MUST observe at least one heartbeat per 5-thread span. The line is written via the standard work-log surface so it lands in the same `work.log` sink the orchestrator polls:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-6-finalize:verification-feedback) processing comment thread {N}/{M}"
```

This contract lets the orchestrator distinguish between an in-progress triage run and a stalled subagent without waiting for the 15-minute dispatch timeout to fire. The instruction is consumer-side documentation — the runtime emission lives in the dispatched triage workflow body, but `automated-review.md` is the doc that names the marker shape, the cadence, and the `N`/`M` semantics so a reader following the phase-6 orchestration flow encounters the contract in context.

### Handle findings (loop-back)

The triage subagent above allocated fix tasks and posted reviewer-facing thread replies inline (see the FIX action body in [`triage.md`](triage.md)). This section only handles the loop-back bookkeeping.

**If the triage subagent returned `status: loop_back`** (one or more `pr-comment` findings closed with `--resolution fixed` and a fix-task reference, an overflow envelope was filed, OR all findings were inline-fixable but the calling step needs replay), `loop_back_needed = true`. Read `loop_back_target` from the triage subagent's return TOON (REQUIRED on every `status: loop_back` return per [`triage.md`](../../plan-marshall/workflow/triage.md) § Step 7):

1. **Conditional `set-phase`** — only call `manage-status set-phase --phase 5-execute` when `loop_back_target == "5-execute"` (full-phase rollback for fix-task-required dispositions). When `loop_back_target == "6-finalize"` (inline replay for inline-fixable dispositions), the persisted `current_phase` stays at `6-finalize` and NO `set-phase` call is issued.

**Loopback target invariant**: the `set-phase` call below fires ONLY for `loop_back_target == "5-execute"`; the `6-finalize` target leaves `current_phase` untouched. See [SKILL.md § Loop-back Target Contract](../SKILL.md#loop-back-target-contract) for the granularity invariant.

```bash
# IF loop_back_target == "5-execute":
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status set-phase \
  --plan-id {plan_id} --phase 5-execute
# IF loop_back_target == "6-finalize": skip the set-phase call entirely.
```

2. Mark this finalize step as a loop-back iteration, forwarding the `loop_back_target` value verbatim to `mark-step-done` (REQUIRED per the manage-status `--loop-back-target` validation contract — omitting it returns `error: missing_loop_back_target`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step automated-review --outcome loop_back \
  --loop-back-target {5-execute|6-finalize} \
  --display-detail "loop-back iteration {iteration} (target={5-execute|6-finalize})"
```

3. Continue until clean or max iterations (3). Iteration counting and the 3-iteration cap are unchanged. The dispatcher's Step 3 § 7b loop-back continuation hook reads the persisted `loop_back_target` and routes between full-phase rollback (`5-execute`) and inline replay (`6-finalize`) deterministically.

When the triage subagent returns `status: success` (every finding closed as SUPPRESS / ACCEPT / `taken_into_account`, or the query returned empty), `loop_back_needed = false` — proceed directly to "Phase Boundary Re-Capture" below.

## Phase Boundary Re-Capture (intra-finalize gate)

Before marking the step complete, run the read-only `phase_handshake findings-check` against the `6-finalize` phase. `findings-check` evaluates ONLY the `pending_findings_blocking_count` invariant — it trips `blocking_findings_present` if any pending blocking-type finding (notably any unresolved `pr-comment`) remains in the store, which guards the documented `automated-review → branch-cleanup` boundary in [`plan-marshall/references/phase-handshake.md`](../../plan-marshall/references/phase-handshake.md#guarded-boundaries). Because it is the single-invariant verb it never runs `phase_steps_complete`, so it cannot short-circuit on `phase_steps_incomplete` at this mid-pipeline checkpoint where downstream finalize steps (`branch-cleanup`, `record-metrics`, `archive-plan`) have not run yet — the failure mode that made the composite `capture` gate inoperative here.

Run the check:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake findings-check \
  --plan-id {plan_id} --phase 6-finalize
```

**On `status: success`** (no pending blocking-type findings): proceed to "Mark Step Complete" below.

**On `status: error` with `error: query_failed`** (the blocking-findings invariant could not be evaluated — a per-type query failed, typically because the executor was unreachable): the gate fails CLOSED. The boundary is NOT satisfied, so do NOT proceed to `branch-cleanup`. This is an environmental failure with no findings to triage — there is nothing to loop back over. Mark the step `failed` (`mark-step-done … --outcome failed --display-detail "findings-check query_failed (gate unevaluable)"`) so the dispatcher halts the pipeline; the operator re-runs finalize once the environment is healthy and the read-only check re-evaluates on re-entry. Do NOT treat `query_failed` as a clean pass — that would reintroduce the fail-open the single-invariant gate exists to prevent.

**On `status: error` with `error: blocking_findings_present`** (the structured envelope is field-for-field identical to the composite `capture` blocking-findings payload — see [`phase-handshake.md` § Capture-time behavior](../../plan-marshall/references/phase-handshake.md#pending_findings_blocking_count-resolution)):

```toon
status: error
error: blocking_findings_present
plan_id: {plan_id}
phase: 6-finalize
blocking_count: {N}
blocking_types[K]:
  - pr-comment
  - …
per_type{pr-comment,…}:
  {N},…
message: "pending_findings_blocking_count failed for phase '6-finalize': …"
```

The check is the structural enforcer of "no unresolved pr-comment findings at branch-cleanup". Loop-back guidance:

1. Read the offending findings via `manage-findings list --type pr-comment --resolution pending` (or whichever type the `per_type` map names).
2. For each pending finding, run the per-finding consumer dispatch defined above (load `ext-triage-{domain}`, decide FIX / SUPPRESS / ACCEPT / `AskUserQuestion`, act, then `manage-findings resolve`). FIX outcomes set `loop_back_needed = true` and re-enter phase-5-execute via the loop-back block in this document; SUPPRESS / ACCEPT / `taken_into_account` resolve in-place without loop-back.
3. After every pending finding is resolved, **re-issue the same `phase_handshake findings-check --phase 6-finalize`** call. The boundary is satisfied only when the check returns `status: success`.
4. Bound the iterations by the existing `automated-review` iteration cap (3); on cap exhaustion mark the step `failed` per the dispatcher contract — the boundary remains gated and `branch-cleanup` does not run.

**Single-invariant verb, not the composite `capture`**: `findings-check` evaluates the blocking-findings invariant in isolation via [`_handshake_commands.cmd_findings_check`](../../plan-marshall/scripts/_handshake_commands.py), reusing the `pending_findings_blocking_count` capture and its `BlockingFindingsPresent` → structured-error translation. It writes no handshake row and never evaluates `phase_steps_complete`, so the mid-pipeline gate works where the composite `capture` would short-circuit on `phase_steps_incomplete`.

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. Mark done only on the terminal pass that returns clean (or on a skip); loop-back iterations do not terminate the step.

`automated-review` is one of the three HEAD-dependent steps (alongside `pre-push-quality-gate` and `sonar-roundtrip`) — see [`phase-6-finalize/SKILL.md`](../SKILL.md) Step 3 "Special case — HEAD-dependent steps". Every `--outcome done` branch below MUST capture the worktree HEAD SHA immediately before the `mark-step-done` call and forward it via `--head-at-completion {sha}`, so the dispatcher's HEAD-dependent resumability check can detect a stale `done` record after a future loop-back commit advances HEAD. The `loop_back` branch does NOT need to persist the SHA — the dispatcher's general resumability handling for `loop_back` treats it as no-record on re-entry regardless of HEAD.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the review outcome. The payload differs by branch:

**Branch A — terminal clean pass** (no loop-back needed): `{N}` is the total count of `pr-comment` findings resolved in the final pass (sum of fixed + suppressed + accepted + taken_into_account from this iteration's `manage-findings resolve` calls). Resolve the HEAD SHA before marking done:

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture stdout as `{sha}` and forward via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step automated-review --outcome done \
  --display-detail "{N} comment(s) resolved (no loop-back)" \
  --head-at-completion {sha}
```

**Branch B — no PR available** (the dispatcher ran this step but no PR exists for the branch — the underlying workflow returned immediately with no comments to process). Resolve the worktree HEAD before marking done:

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture stdout as `{sha}` and forward via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step automated-review --outcome done \
  --display-detail "no PR available" \
  --head-at-completion {sha}
```

**Branch C — loop-back recorded** (intermediate pass; used when a non-terminal iteration must be surfaced and the dispatcher must re-fire this step on the next phase-6-finalize entry): `{iteration}` is the current loop-back iteration number (1..3); `{loop_back_target}` is the granularity classification from the triage subagent's return TOON (`5-execute` for fix-task-required dispositions, `6-finalize` for inline-fixable). This branch records `--outcome loop_back --loop-back-target {value}` so the Step 3 dispatcher table (and the Resumability table below) re-fires the step as a fresh dispatch on next entry AND the continuation hook (§ 7b) routes deterministically. The terminal pass still uses Branch A when review eventually goes clean. Never record `--outcome done` for an intermediate iteration — `done` is terminal and will cause the dispatcher to skip the step on re-entry. The `loop_back` branch does NOT need `--head-at-completion` but DOES require `--loop-back-target` (per the manage-status validation contract — omitting it returns `error: missing_loop_back_target`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step automated-review --outcome loop_back \
  --loop-back-target {5-execute|6-finalize} \
  --display-detail "loop-back iteration {iteration} (target={5-execute|6-finalize})"
```

## Resumability

`automated-review` is one of the three HEAD-dependent steps in `HEAD_DEPENDENT_STEPS` (`pre-push-quality-gate`, `automated-review`, `sonar-roundtrip`) — see [`phase-6-finalize/SKILL.md`](../SKILL.md) Step 3 "Special case — HEAD-dependent steps". The HEAD comparison guards against false-clean re-entry after a downstream loop-back commit (typically produced by `sonar-roundtrip` opening a fix task that produces a new commit, or by an `automated-review` iteration's own FIX dispositions on a previous pass) advances HEAD past the validated tree:

| Persisted state | Live worktree HEAD | Action |
|-----------------|--------------------|--------|
| `outcome == done` AND `head_at_completion == HEAD` | matches | SKIP (steady-state — review already cleared this exact tree) |
| `outcome == done` AND `head_at_completion != HEAD` | differs | RE-FIRE (treat as no record — HEAD has advanced past the validated SHA; re-fetch comments and re-triage against the new tree) |
| `outcome == done` AND `head_at_completion` absent | n/a | RE-FIRE (record is incomplete without a SHA; safe default is to re-run) |
| `outcome == failed` | n/a | RETRY (unchanged — same as the general rule) |
| `outcome == loop_back` | n/a | RE-FIRE (treat as no record — same as the general rule for loop_back) |
| no record | n/a | DISPATCH (unchanged — same as the general rule) |

## Output

```toon
status: success | error | loop_back
display_detail: "<{N} comments resolved, {fix_tasks} fix tasks, {accepted} accepted>"
comments_processed: {N}
comments_resolved: {N}
fix_tasks_created: {N}
```

Orchestrator workflow — the LLM core is delegated to `verification-feedback` (`producer=pr-comment`) via the internal sub-dispatch. The `display_detail` value (≤80 chars, ASCII, no trailing period) is forwarded via `mark-step-done --display-detail`. On `loop_back`, the calling step re-fires on the next phase entry per the HEAD-dependent resumability rules above.
