---
name: default:automated-review
description: CI automated review
order: 30
---

# Automated Review

Pure executor for the `automated-review` finalize step. Drives the consumer-side dispatch for `pr-comment` findings as defined in [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) — this document owns the step list (CI wait, producer call, per-finding decision loop, intra-finalize re-capture, mark-step-done). Refer to [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) for the architecture-level synthesis (producers, store schema, invariant gate, extension contract).

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `automated-review` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

## Timeout Contract

This step runs as a Task agent (`plan-marshall:automated-review-agent`) under a **15-minute (900 s) per-agent timeout budget** enforced by the SKILL.md Step 3 dispatch loop. The budget covers the full sequence: CI wait, review-bot buffer, producer-side comments-stage, per-finding triage dispatch, thread replies, and thread resolution.

**Graceful degradation**: When the wrapper expires:

1. The dispatcher logs an ERROR entry at `[ERROR] (plan-marshall:phase-6-finalize) Step default:automated-review timed out after 900s — marking failed and continuing`.
2. The dispatcher marks this step `failed` via `manage-status mark-step-done … --outcome failed --display-detail "timed out after 900s"`.
3. The dispatcher continues with the next manifest step. The pipeline does NOT abort; later steps still run.
4. On the next Phase 6 entry, the resumable re-entry check sees `outcome=failed` and retries this step from scratch (one fresh attempt per invocation).

There is no internal soft-timeout, polling cap, or partial-progress checkpoint inside this document — the wrapper is the only timeout authority. Standards-internal commands (CI wait, `pr wait-for-comments`) carry their own short polling intervals but never their own outer ceiling.

## Inputs

- A PR exists (from `create-pr` earlier in the manifest list, or pre-existing on the branch)
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All `ci`, `github_pr`, and build-script invocations below MUST pass `--project-dir {worktree_path}`.

## Execution

### Get PR number

Use the `pr_number` from the create-pr step. If not available:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr view
```

Read `pr_number` from the TOON output. If `ci pr view` returns `status: error` (no PR exists for the branch), this step has nothing to process — record `done` with a `display_detail` of `no PR available` (Branch B in "Mark Step Complete" below) and return.

### Wait for CI

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} ci wait \
  --pr-number {pr_number}
```

| Script Output | Action |
|--------------|--------|
| `final_status: success` | Proceed to "Wait for review-bot comments" |
| `final_status: failure` | Treat as a CI failure — surface `ci_failure` to the caller for loop-back; this step does NOT proceed to comment processing |
| `status: timeout` | Ask user (continue / skip / abort) via `AskUserQuestion` |

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

### Per-finding dispatch loop (consumer-side triage)

For each finding in the query result, perform the following sequence. Process findings sequentially — never batch the per-finding decision through a single LLM call.

**1. Detect domain** from the finding's `file_path`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture which-module \
  --path {finding.file_path}
```

Read the resolved domain key from the TOON output. If the path falls outside any registered module (e.g., `which-module` returns `module: null`), default to the project's primary domain as recorded in `marshal.json` `skill_domains` — the operator can refine this later via lessons-learned.

**2. Resolve the triage extension skill for the domain**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-workflow-skill-extension --domain {detected_domain} --type triage
```

Read the returned `skill` reference (e.g., `pm-dev-java:ext-triage-java`).

**3. Load the resolved triage extension into the main context**:

```
Skill: {bundle}:ext-triage-{domain}
```

The loaded extension brings its `standards/severity.md`, `standards/suppression.md`, and `standards/pr-comment-disposition.md` into context — these are the authoritative per-domain inputs to the per-finding decision.

**4. Decide per-finding** using the loaded standards. The decision table is owned by the loaded ext-triage skill (`pr-comment-disposition.md`). The four canonical outcomes are:

| Decision | Meaning |
|----------|---------|
| **FIX** | The comment identifies a real defect. Create a fix task and loop back. |
| **SUPPRESS** | The comment is correct in pattern-match terms, but the loaded standards justify suppressing it (false positive, framework-mandated pattern, generated code, etc.). Apply the domain-specific annotation. |
| **ACCEPT** | The comment is informational, addresses an acceptable trade-off, or is out of scope for this plan. Reply with rationale and resolve the thread. |
| **AskUserQuestion** | The loaded standards leave the call genuinely ambiguous. Ask the user — one question per finding, never batched. |

The `AskUserQuestion` outcome is reserved for the cases where domain-skill rules do not deterministically resolve the call. Do not use it as a default — the loaded `pr-comment-disposition.md` table is expected to cover the typical cases.

**5. Act on the decision**:

- **FIX** — The comment identifies a real defect that requires a follow-up commit. The action body emits a fix task allocation, a thread-reply chain pointing the reviewer at that task, and finally a `manage-findings resolve` record. Order is load-bearing: the task number must be allocated FIRST so the thread reply can name it.

  Step 1 — allocate the fix task via the two-step prepare-add → commit-add flow:

  ```bash
  # Allocate a scratch path for the pending task (returns draft_id and scratch path)
  python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks prepare-add \
    --plan-id {plan_id}
  ```

  Write the task YAML to the returned scratch path (title, deliverable: 0, domain matching the finding, profile: implementation, description referencing the comment, steps targeting `{finding.file_path}`), then commit:

  ```bash
  # Read the prepared file and create TASK-NNN.json — capture the returned task number as {N}
  python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks commit-add \
    --plan-id {plan_id}
  ```

  Step 2 — emit the thread-reply chain pointing at TASK-{N}. Allocate a scratch path for the reply body:

  ```bash
  python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr prepare-comment \
    --plan-id {plan_id} --pr-number {pr_number}
  ```

  Write the reply body to the returned scratch path via the Write tool. The body MUST reference the freshly-allocated fix-task number, e.g. `Will be addressed by TASK-{N}; see follow-up commit on this branch`. Then post and resolve the thread:

  ```bash
  python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr thread-reply \
    --pr-number {pr_number} --thread-id {finding.thread_id} --plan-id {plan_id}
  ```

  ```bash
  python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr resolve-thread \
    --pr-number {pr_number} --thread-id {finding.thread_id}
  ```

  Step 3 — record the finding as fixed. Mark resolved only after the task allocation and thread chain have completed, so the resolution rationale can name the task number:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings resolve \
    --plan-id {plan_id} --hash-id {finding.hash_id} --resolution fixed \
    --detail "Will be addressed by TASK-{N}; see follow-up commit on this branch"
  ```

- **SUPPRESS** — Apply the domain-specific suppression annotation to the source location identified by `{finding.file_path}:{finding.line}`, using the syntax from the loaded `suppression.md`. Then:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings resolve \
    --plan-id {plan_id} --hash-id {finding.hash_id} --resolution suppressed \
    --detail "{rationale referencing the loaded standard rule}"
  ```

  Reply on the thread to acknowledge the suppression and resolve the thread:

  ```bash
  python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr prepare-comment \
    --plan-id {plan_id} --pr-number {pr_number}
  ```

  Write the reply body to the returned scratch path via the Write tool, then:

  ```bash
  python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr thread-reply \
    --pr-number {pr_number} --thread-id {finding.thread_id} --plan-id {plan_id}
  ```

  ```bash
  python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr resolve-thread \
    --pr-number {pr_number} --thread-id {finding.thread_id}
  ```

- **ACCEPT** — Reply on the thread with the rationale (using the same `prepare-comment` → `thread-reply` flow as SUPPRESS), resolve the thread, then:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings resolve \
    --plan-id {plan_id} --hash-id {finding.hash_id} --resolution accepted \
    --detail "{rationale}"
  ```

- **AskUserQuestion** — Ask the user via the `AskUserQuestion` tool. Then act on the user's answer using the matching path above. After acting:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings resolve \
    --plan-id {plan_id} --hash-id {finding.hash_id} --resolution {fixed|suppressed|accepted|taken_into_account} \
    --detail "{user's stated rationale}"
  ```

### Handle findings (loop-back)

The per-finding loop above already allocated fix tasks and posted reviewer-facing thread replies inline (see the FIX action body). This section only handles the loop-back bookkeeping after that loop has finished.

**If any FIX disposition fired during the per-finding loop** (one or more `pr-comment` findings closed with `--resolution fixed` and a fix-task reference), `loop_back_needed = true`:

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

When NO finding resolved to **FIX** (every finding closed as SUPPRESS / ACCEPT / taken_into_account), `loop_back_needed = false` — proceed directly to "Phase Boundary Re-Capture" below.

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

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the review outcome. The payload differs by branch:

**Branch A — terminal clean pass** (no loop-back needed): `{N}` is the total count of `pr-comment` findings resolved in the final pass (sum of fixed + suppressed + accepted + taken_into_account from this iteration's `manage-findings resolve` calls).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step automated-review --outcome done \
  --display-detail "{N} comment(s) resolved (no loop-back)"
```

**Branch B — no PR available** (the dispatcher ran this step but no PR exists for the branch — the underlying workflow returned immediately with no comments to process):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step automated-review --outcome done \
  --display-detail "no PR available"
```

**Branch C — loop-back recorded** (intermediate pass; used when a non-terminal iteration must be surfaced and the dispatcher must re-fire this step on the next phase-6 entry): `{iteration}` is the current loop-back iteration number (1..3). This branch records `--outcome loop_back` so the Step 3 dispatcher table (and the Resumability table in `phase-6-finalize/SKILL.md`) re-fires the step as a fresh dispatch on next entry. The terminal pass still uses Branch A when review eventually goes clean. Never record `--outcome done` for an intermediate iteration — `done` is terminal and will cause the dispatcher to skip the step on re-entry.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step automated-review --outcome loop_back \
  --display-detail "loop-back iteration {iteration}"
```
