---
name: default:automated-review
description: CI automated review
order: 30
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Automated Review

Pure executor for the `automated-review` finalize step. Drives the consumer-side orchestration for `pr-comment` findings as defined in [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) — this document owns the manifest-step list (consume completed-CI signal, review-bot buffer, producer call, gate-keeping query, intra-finalize re-capture, mark-step-done). The per-finding LLM core (decision + action + overflow handling) is dispatched once as `verification-feedback` (`producer=pr-comment`) — see "Dispatch the per-finding triage core" below. Refer to [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) for the architecture-level synthesis (producers, store schema, invariant gate, extension contract).

This step does NOT poll CI itself — CI completion is the responsibility of the preceding `ci-wait` step (see [`ci-wait.md`](ci-wait.md)). `automated-review` reads the completed-CI signal from `manage-status` (the `phase_steps["6-finalize"]["ci-wait"].outcome=done` record with a `final_status: success` display detail) and proceeds to comment triage when the signal is present. When the signal is absent (no `ci-wait` record) or `outcome=failed` (CI failure), `automated-review` surfaces `ci_failure` for loop-back without attempting to fetch comments.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `automated-review` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

## Timeout Contract

This step runs as inline orchestration (producer fetch + finding enumeration in main context) plus a single `verification-feedback` Task dispatch (`plan-marshall:execution-context-{level}` resolved via `manage-config models resolve-target --phase phase-6 --role verification-feedback`) under a **15-minute (900 s) per-agent timeout budget** enforced by the SKILL.md Step 3 dispatch loop. The budget is **triage-only**: it covers the review-bot buffer, producer-side comments-stage, per-finding triage dispatch with `producer=pr-comment`, thread replies, and thread resolution. CI wait time is bounded separately by the preceding `ci-wait` step's 1800 s budget — splitting CI-wait out keeps this triage budget bounded by comment volume rather than CI queue depth.

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

### Read completed-CI signal

CI completion was already verified by the preceding `ci-wait` step. Read its terminal record from `manage-status` to confirm CI is green before proceeding to comment triage:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read \
  --plan-id {plan_id}
```

Locate the `phase_steps["6-finalize"]["ci-wait"]` record in the returned TOON and read its `outcome` and `display_detail` fields.

| Signal State | Action |
|--------------|--------|
| `outcome: done` with display detail starting `CI success` | CI is green — proceed to "Wait for review-bot comments" |
| `outcome: done` with display detail `no PR available` | No PR exists — record `done` with display detail `no PR available` (Branch B in "Mark Step Complete" below) and return |
| `outcome: failed` (CI failure or `ci-wait` wrapper timeout) | Treat as a CI failure — surface `ci_failure` to the caller for loop-back; this step does NOT proceed to comment processing |
| record absent (no `ci-wait` step in manifest, or earlier dispatcher skip) | Treat as a CI-not-ready condition — surface `ci_failure` to the caller for loop-back |

### Wait for review-bot comments

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr wait-for-comments \
  --pr-number {pr_number} --timeout {review_bot_buffer_seconds}
```

`{review_bot_buffer_seconds}` is sourced from the `phase-6-finalize.review_bot_buffer_seconds` config (default: 180; max-wait ceiling, not a fixed delay). The polling subcommand exits as soon as a new review-bot comment is posted.

| Script Output | Action |
|--------------|--------|
| `status: success`, `timed_out: false` | New comment(s) detected — proceed to producer-stage |
| `status: success`, `timed_out: true` | No new comment within timeout — proceed to producer-stage anyway (the producer will surface whatever is on the PR) |
| `status: error` | Treat as warning, log, proceed to producer-stage best-effort |

### Producer: stage PR comments as findings (entry-point)

Call the producer-side comments-stage subcommand once. It fetches PR review comments, applies pre-filters (resolved threads, plan author's own replies, etc.), and writes one `pr-comment` finding per surviving comment into the per-plan findings store.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
  --project-dir {worktree_path} comments-stage --pr-number {pr_number} --plan-id {plan_id}
```

(For GitLab projects the equivalent producer is `plan-marshall:workflow-integration-gitlab:gitlab_pr comments-stage`. Provider selection is whichever matches `manage-providers` for the plan's host; only one of the two is invoked per finalize run.)

The producer is the ONLY surface that fetches and stores `pr-comment` findings. This document does not classify, decide, or act on comments inline — every consumer-side action below reads from the findings store via `manage-findings query`.

### Consumer: enumerate pending pr-comment findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings query \
  --plan-id {plan_id} --type pr-comment --resolution pending
```

If the result's `findings` list is empty, there is nothing to process — proceed directly to "Handle findings (loop-back)" with `loop_back_needed = false`, then "Mark Step Complete" Branch A with `0 comment(s) resolved (no loop-back)`.

### Dispatch the per-finding triage core

When the query above returns one or more pending `pr-comment` findings, dispatch the unified feedback workflow [`verification-feedback.md`](../../plan-marshall/workflow/verification-feedback.md) with `producer=pr-comment`. That workflow's Step 1 verifies the store-only query, then delegates the per-finding LLM-judgement core to [`triage.md`](../../plan-marshall/workflow/triage.md) Steps 1-6 — single source of truth for the smart-grouping algorithm, the per-outcome action bodies (FIX / SUPPRESS / ACCEPT / AskUserQuestion), the overflow / timeout handling, and the Scope-Deviation Escalation guard.

The dispatch is **by reference** — the prompt carries `producer=pr-comment` and `pr_number={pr_number}` only; the subagent issues its own `manage-findings query` against the same store as its first workflow step, so the orchestrator's query above is purely a gate-keeping count (skip dispatch when empty).

Compute the target variant via the role resolver, then dispatch:

```bash
target=$(python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  models resolve-target --phase phase-6 --role verification-feedback)
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
    caller_phase: phase-6

    WORKTREE: {worktree_path}
```

The subagent's return TOON carries `findings_processed`, `findings_resolved`, `fix_tasks_created`, optional `fix_task_numbers[]`, optional `overflow_deferred`. Capture those values for the "Handle findings (loop-back)" branch below.

When the subagent returns `status: loop_back` it has either created fix tasks (FIX outcomes) or filed an overflow envelope — both require the manifest dispatcher to re-fire `automated-review` on next phase-6 entry.

### Handle findings (loop-back)

The triage subagent above allocated fix tasks and posted reviewer-facing thread replies inline (see the FIX action body in [`triage.md`](triage.md)). This section only handles the loop-back bookkeeping.

**If the triage subagent returned `status: loop_back`** (one or more `pr-comment` findings closed with `--resolution fixed` and a fix-task reference, OR an overflow envelope was filed), `loop_back_needed = true`:

1. Set the plan back to phase-5-execute so the orchestrator picks the freshly-allocated fix tasks up on the next iteration:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status set-phase \
  --plan-id {plan_id} --phase 5-execute
```

2. Mark this finalize step as a loop-back iteration (the dispatcher will re-fire it on the next phase-6 entry):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step automated-review --outcome loop_back \
  --display-detail "loop-back iteration {iteration}"
```

3. Continue until clean or max iterations (3). Iteration counting and the 3-iteration cap are unchanged.

When the triage subagent returns `status: success` (every finding closed as SUPPRESS / ACCEPT / `taken_into_account`, or the query returned empty), `loop_back_needed = false` — proceed directly to "Phase Boundary Re-Capture" below.

## Phase Boundary Re-Capture (intra-finalize gate)

Before marking the step complete, re-issue the `phase_handshake capture` against the `6-finalize` phase. The orchestrator's `_BLOCKING_BOUNDARIES` set guards `6-finalize` — re-issuing capture here trips `BlockingFindingsPresent` if any pending blocking-type finding (notably any unresolved `pr-comment`) remains in the store, which guards the documented `automated-review → branch-cleanup` boundary in [`plan-marshall/references/phase-handshake.md`](../../plan-marshall/references/phase-handshake.md#guarded-boundaries).

Run the capture:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake capture \
  --plan-id {plan_id} --phase 6-finalize
```

**On `status: success`** (no pending blocking-type findings): proceed to "Mark Step Complete" below.

**On `status: error` with `error: blocking_findings_present`** (the structured envelope mirrors the TOON shape in [`phase-handshake.md` § Capture-time behavior](../../plan-marshall/references/phase-handshake.md#pending_findings_blocking_count-resolution)):

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

The capture is the structural enforcer of "no unresolved pr-comment findings at branch-cleanup". Loop-back guidance:

1. Read the offending findings via `manage-findings query --type pr-comment --resolution pending` (or whichever type the `per_type` map names).
2. For each pending finding, run the per-finding consumer dispatch defined above (load `ext-triage-{domain}`, decide FIX / SUPPRESS / ACCEPT / `AskUserQuestion`, act, then `manage-findings resolve`). FIX outcomes set `loop_back_needed = true` and re-enter phase-5-execute via the loop-back block in this document; SUPPRESS / ACCEPT / `taken_into_account` resolve in-place without loop-back.
3. After every pending finding is resolved, **re-issue the same `phase_handshake capture --phase 6-finalize`** call. The boundary is satisfied only when capture returns `status: success`.
4. Bound the iterations by the existing `automated-review` iteration cap (3); on cap exhaustion mark the step `failed` per the dispatcher contract — the boundary remains gated and `branch-cleanup` does not run.

**No `_BLOCKING_BOUNDARIES` change required**: re-issuing capture under the `6-finalize` phase value reuses the existing single-phase guard from [`_invariants.py`](../../plan-marshall/scripts/_invariants.py).

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. Mark done only on the terminal pass that returns clean (or on a skip); loop-back iterations do not terminate the step.

`automated-review` is one of the four HEAD-dependent steps (alongside `pre-push-quality-gate`, `ci-wait`, `sonar-roundtrip`) — see [`phase-6-finalize/SKILL.md`](../SKILL.md) Step 3 "Special case — HEAD-dependent steps". Every `--outcome done` branch below MUST capture the worktree HEAD SHA immediately before the `mark-step-done` call and forward it via `--head-at-completion {sha}`, so the dispatcher's HEAD-dependent resumability check can detect a stale `done` record after a future loop-back commit advances HEAD. The `loop_back` branch does NOT need to persist the SHA — the dispatcher's general resumability handling for `loop_back` treats it as no-record on re-entry regardless of HEAD.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the review outcome. The payload differs by branch:

**Branch A — terminal clean pass** (no loop-back needed): `{N}` is the total count of `pr-comment` findings resolved in the final pass (sum of fixed + suppressed + accepted + taken_into_account from this iteration's `manage-findings resolve` calls). Resolve the HEAD SHA before marking done:

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture stdout as `{sha}` and forward via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step automated-review --outcome done \
  --display-detail "no PR available" \
  --head-at-completion {sha}
```

**Branch C — loop-back recorded** (intermediate pass; used when a non-terminal iteration must be surfaced and the dispatcher must re-fire this step on the next phase-6 entry): `{iteration}` is the current loop-back iteration number (1..3). This branch records `--outcome loop_back` so the Step 3 dispatcher table (and the Resumability table below) re-fires the step as a fresh dispatch on next entry. The terminal pass still uses Branch A when review eventually goes clean. Never record `--outcome done` for an intermediate iteration — `done` is terminal and will cause the dispatcher to skip the step on re-entry. The `loop_back` branch does NOT need `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step automated-review --outcome loop_back \
  --display-detail "loop-back iteration {iteration}"
```

## Resumability

`automated-review` is one of the four HEAD-dependent steps in `HEAD_DEPENDENT_STEPS` (`pre-push-quality-gate`, `ci-wait`, `automated-review`, `sonar-roundtrip`) — see [`phase-6-finalize/SKILL.md`](../SKILL.md) Step 3 "Special case — HEAD-dependent steps". The HEAD comparison guards against false-clean re-entry after a downstream loop-back commit (typically produced by `sonar-roundtrip` opening a fix task that produces a new commit, or by an earlier `automated-review` iteration's own FIX dispositions) advances HEAD past the validated tree:

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
