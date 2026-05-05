---
name: default:automated-review
description: CI automated review
order: 30
---

# Automated Review

Pure executor for the `automated-review` finalize step. Waits for CI, drives the producer-side comment-stage call, then dispatches per-finding through `manage-findings` + the domain-specific `ext-triage-{domain}` extension to decide and act on each PR comment.

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

- **FIX** — Create a fix task via the two-step prepare-add → commit-add flow (see "Handle findings (loop-back)" below). The finding's resolution is recorded after the loop-back fix lands; from this step's perspective, mark the finding `fixed` once the fix task has been recorded:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings resolve \
    --plan-id {plan_id} --hash-id {finding.hash_id} --resolution fixed \
    --detail "{rationale referencing the fix task number}"
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

**On findings** that resolved to **FIX** (one or more `pr-comment` findings closed with `--resolution fixed` and a fix-task reference), `loop_back_needed = true`:

1. Create fix tasks (two-step prepare-add → commit-add flow):

```bash
# Step 1: allocate a scratch path for the pending task (returns draft_id and scratch path)
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks prepare-add \
  --plan-id {plan_id}
```

Write the task YAML to the returned scratch path (title, deliverable: 0, domain, profile: implementation, description, steps), then commit:

```bash
# Step 2: read the prepared file and create TASK-NNN.json
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks commit-add \
  --plan-id {plan_id}
```

2. Loop back to phase-5-execute (iteration + 1):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status set-phase \
  --plan-id {plan_id} --phase 5-execute
```

3. Continue until clean or max iterations (3).

When NO finding resolved to **FIX** (every finding closed as SUPPRESS / ACCEPT / taken_into_account), `loop_back_needed = false` — proceed directly to "Mark Step Complete" Branch A.

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

**Branch C — loop-back recorded** (intermediate pass; used only when a non-terminal iteration must be surfaced in the output): `{iteration}` is the current loop-back iteration number (1..3). This branch is informational — the terminal pass still uses Branch A when review eventually goes clean.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step automated-review --outcome done \
  --display-detail "loop-back iteration {iteration}"
```
