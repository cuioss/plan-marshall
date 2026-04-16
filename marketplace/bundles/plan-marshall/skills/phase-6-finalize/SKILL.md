---
name: phase-6-finalize
description: Complete plan execution with git workflow and PR management
user-invocable: false
---

# Phase Finalize Skill

**Role**: Finalize phase skill. Handles shipping workflow (commit, push, PR) and plan completion. Verification tasks have already been executed within phase-5-execute.

**Key Pattern**: Shipping-focused execution. No verification steps—all quality checks run as verification tasks within phase-5-execute before reaching this phase.

**Required steps declaration**: This skill opts in to the `phase_steps_complete` handshake invariant. The canonical list of steps that MUST be marked done on `status.metadata.phase_steps["6-finalize"]` before the phase transitions is maintained in [standards/required-steps.md](standards/required-steps.md). Each built-in step's standards document terminates with a `manage-status mark-step-done` call whose `--step` value matches an entry in that file.

## Enforcement

> **Shared lifecycle patterns**: See [phase-lifecycle.md](../ref-workflow-architecture/standards/phase-lifecycle.md) for entry protocol, completion protocol, and error handling convention.

**Execution mode**: Follow workflow steps sequentially, respecting config gates. Each config-gated step dispatches to a standards/ document.

**Required skill load** (before any operation):
```
Skill: plan-marshall:dev-general-practices
Skill: plan-marshall:workflow-integration-git
Skill: plan-marshall:tools-integration-ci
```

**Prohibited actions:**
- Never access `.plan/` files directly — all access must go through `python3 .plan/execute-script.py` manage-* scripts
- Never skip config gate checks (Steps 3-10 each have an IF gate)
- Never skip phase transitions — use `manage-status transition`, never set status directly
- Never improvise script subcommands — use only those documented in this skill's workflow steps
- Never skip config-gated steps based on PR state (approval, merge status, or CI status). The ONLY valid skip condition for each step is its config gate being `false`. Standards documents have their own user confirmation gates that handle runtime state decisions.
- Never issue a raw `git` Bash call without `git -C {worktree_path}` (pre-worktree-removal) or `git -C {main_checkout}` (post-worktree-removal). No `cd` chaining, no implicit cwd. `{worktree_path}` and `{main_checkout}` MUST be resolved by the Step 0 entry step before any standards document runs.
- Never invoke a build, CI, Sonar, or GitHub/GitLab script (`ci`, `python_build`, `sonar`, `workflow-integration-*`) without forwarding `--project-dir {worktree_path}` (or `--project-dir {main_checkout}` after worktree removal). The executor is cwd-pass-through; cwd control is explicit at the call site.

**Constraints:**
- Strictly comply with all rules from dev-general-practices, especially tool usage and workflow step discipline

## When to Activate This Skill

Activate when:
- Execute phase has completed (all implementation and verification tasks passed)
- Ready to commit and potentially create PR
- Plan is in `6-finalize` phase

---

## Phase Position in 6-Phase Model

See [references/workflow-overview.md](references/workflow-overview.md) for the visual phase flow diagram.

**Iteration limit**: 3 cycles max for PR issue resolution.

---

## Configuration Source

All config is read in Step 2 as a single TOON response:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get --trace-plan-id {plan_id}
```

**Config Fields Used**:

| Field | Type | Description |
|-------|------|-------------|
| `steps` | list | Ordered list of step references to execute |
| `review_bot_buffer_seconds` | integer | Max seconds to wait after CI for new review-bot comments (used as `--timeout` for `pr wait-for-comments`; ceiling, not fixed delay; default: 180) |
| `max_iterations` | integer | Maximum finalize-verify loops (default: 3) |

A step is active if it appears in the `steps` list. Absent steps are skipped. The order of steps in the list is the execution order.

Cross-phase settings:

| Source | Field | Description |
|--------|-------|-------------|
| phase-5-execute | `commit_strategy` | per_deliverable/per_plan/none |
| phase-1-init | `branch_strategy` | feature/direct |

---

## Step Types

Three step types are supported, distinguished by prefix notation:

| Type | Notation | Resolution |
|------|----------|------------|
| **built-in** | `default:` prefix (e.g., `default:commit-push`) | Strip prefix, read `standards/{name}.md` and follow all steps |
| **project** | `project:` prefix (e.g., `project:finalize-step-foo`) | `Skill: {notation}` with interface contract parameters |
| **skill** | fully-qualified `bundle:skill` (e.g., `pm-dev-java:java-post-pr`) | `Skill: {notation}` with interface contract parameters |

**Type detection logic**:
- Starts with `default:` -> built-in type (strip prefix, validate against dispatch table)
- Starts with `project:` -> project type
- Contains `:` (other) -> fully-qualified skill type

### Built-in Step Dispatch Table

| Step Name | Standards Document | Description |
|-----------|-------------------|-------------|
| `default:commit-push` | `standards/commit-push.md` | Commit and push changes |
| `default:create-pr` | `standards/create-pr.md` | Create pull request |
| `default:automated-review` | `standards/automated-review.md` | CI automated review |
| `default:sonar-roundtrip` | `standards/sonar-roundtrip.md` | Sonar analysis roundtrip |
| `default:knowledge-capture` | `standards/knowledge-capture.md` | Capture learnings to memory |
| `default:lessons-capture` | `standards/lessons-capture.md` | Record lessons learned |
| `default:branch-cleanup` | `standards/branch-cleanup.md` | Branch cleanup — adapts to PR mode or local-only based on create-pr step presence |
| `default:record-metrics` | `standards/record-metrics.md` | Record final plan metrics before archive |
| `default:archive-plan` | `standards/archive-plan.md` | Archive the completed plan |

### Interface Contract for External Steps

Project and skill steps receive these parameters:

```
Skill: {step_reference}
  Arguments: --plan-id {plan_id} --iteration {iteration}
```

The step skill can access the plan's context via manage-* scripts (references, status, config).

---

## Operation: finalize

**Input**: `plan_id`

### Step 0: Resolve Worktree and Main Checkout Paths

**This step runs before any other finalize step** and makes `{worktree_path}` and `{main_checkout}` available to every subsequent step and standards document. All git Bash calls and all build/CI/sonar/github/gitlab script invocations in the finalize workflow depend on these two values — no standards document may resolve them independently.

Read the plan status and extract the worktree path from metadata:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read \
  --plan-id {plan_id}
```

Extract `metadata.worktree_path`:

- **If present**: the plan ran in an isolated worktree. Capture the value as `{worktree_path}`. The main checkout is the parent of `.claude/worktrees/{plan_id}/` — derive `{main_checkout}` by stripping the trailing `/.claude/worktrees/{plan_id}` segment from `{worktree_path}`, or resolve it explicitly:

```bash
git -C {worktree_path} rev-parse --path-format=absolute --git-common-dir
```

The `git-common-dir` output ends with `/.git` inside the main checkout — `{main_checkout}` is its parent directory.

- **If absent** (pre-worktree plan or `use_worktree == false`): there is no worktree. Set `{worktree_path}` equal to `{main_checkout}`, where `{main_checkout}` is the repository root resolved via:

```bash
git rev-parse --show-toplevel
```

Log the resolved paths so they remain visible in model context for every subsequent Edit/Write/Read/Bash call:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Finalize cwd context: worktree_path={worktree_path} main_checkout={main_checkout} — all git calls MUST use 'git -C' with one of these paths, all script calls MUST pass '--project-dir'"
```

From this point on, every standards document loaded by the finalize pipeline inherits `{worktree_path}` and `{main_checkout}` from this step. Standards documents MUST NOT re-resolve these values.

### Step 1: Check Q-Gate Findings and Log Start

#### Log Phase Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Starting finalize phase"
```

#### Query Unresolved Findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate query --plan-id {plan_id} --phase 6-finalize --resolution pending
```

If unresolved findings exist from a previous iteration (filtered_count > 0):

For each pending finding:
1. Check if it was addressed by the fix tasks that just ran
2. Resolve:
```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate resolve --plan-id {plan_id} --hash-id {hash_id} --resolution fixed --phase 6-finalize \
  --detail "{fix task reference or description}"
```
3. Log:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize:qgate) Finding {hash_id} [qgate]: fixed — {resolution_detail}"
```

### Step 2: Read Configuration

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get --trace-plan-id {plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --trace-plan-id {plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init get --trace-plan-id {plan_id}
```

Also read references context for branch and issue information:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get-context \
  --plan-id {plan_id}
```

Extract the `steps` list from phase-6-finalize config. This is the ordered list of step references to execute.

**After reading configuration**, log the finalize strategy decision:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Finalize strategy: commit={commit_strategy}, steps={steps_count}, branch={branch_strategy}"
```

### Step 3: Execute Step Pipeline

Iterate over the `steps` list from config. For each step reference:

**Agent-suitable built-in steps** (self-contained, no user interaction):
- `create-pr`, `automated-review`, `sonar-roundtrip`, `knowledge-capture`, `lessons-capture`

**Inline-only built-in steps** (require user interaction or sequential dependency):
- `commit-push` (git working directory state), `branch-cleanup` (AskUserQuestion), `record-metrics` (must run immediately before `archive-plan` on the still-live plan directory), `archive-plan` (must be last, moves plan files)

```
FOR each step_ref in steps:
  1. Log step start:
     python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
       work --plan-id {plan_id} --level INFO --message "[STEP] (plan-marshall:phase-6-finalize) Executing step: {step_ref}"

  2. Determine step type:
     - IF step_ref starts with "default:" -> BUILT-IN type (strip prefix for dispatch table lookup)
     - ELSE IF step_ref starts with "project:" -> PROJECT type
     - ELSE IF step_ref contains ":" -> SKILL type

  3. Dispatch:
     - BUILT-IN (agent-suitable: create-pr, automated-review, sonar-roundtrip, knowledge-capture, lessons-capture):
       Run as Task agent — read the standards document and execute all steps within the agent context.
     - BUILT-IN (inline-only: commit-push, branch-cleanup, record-metrics, archive-plan):
       Read the standards document from dispatch table and follow all steps in main context.
     - PROJECT/SKILL: Load the skill with interface contract:
       Skill: {step_ref}
         Arguments: --plan-id {plan_id} --iteration {iteration}

  4. Log step completion:
     python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
       work --plan-id {plan_id} --level INFO --message "[STEP] (plan-marshall:phase-6-finalize) Completed step: {step_ref}"
END FOR
```

**Built-in step notes**:
- `default:branch-cleanup`: Do NOT preemptively skip based on PR state. The `standards/branch-cleanup.md` standard has its own `AskUserQuestion` confirmation gate.
- `default:record-metrics`: MUST immediately precede `default:archive-plan`. `manage-metrics generate` writes `metrics.md` inside the live plan directory; if archive runs first, the target directory no longer exists.
- `default:archive-plan`: This step MUST be last in the default order because it moves plan files (including status.json), which breaks manage-* scripts. All plan operations must complete before archive.

### Step 4: Mark Plan Complete

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition \
  --plan-id {plan_id} \
  --completed 6-finalize
```

### Step 5: Log Phase Completion

Final metrics are already recorded inside the Step 3 pipeline by `default:record-metrics` (which runs immediately before `default:archive-plan`). This step only logs phase completion to work.log.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Plan completed: {steps_count} steps executed"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  separator --plan-id {plan_id} --type work
```

**Note**: `manage-logging` operates on log files, not the plan directory, so these calls remain valid after `default:archive-plan` has moved the plan state.

---

## Output

**Success**:

```toon
status: success
plan_id: {plan_id}

actions:
  commit: {commit_hash}
  push: success
  pr: {created #{number}|skipped}
  automated_review: {completed|skipped|loop_back}
  sonar: {passed|skipped|loop_back}
  knowledge_capture: {done|skipped}
  lessons_capture: {done|skipped}
  archive: {done|skipped}
  branch_cleanup: {done|skipped|declined}

metrics:
  total_duration_seconds: {total from metrics generate}
  total_tokens: {total from metrics generate}
  metrics_file: .plan/archived-plans/{date}-{plan_id}/metrics.md

next_state: complete
```

**Loop Back** (PR issues found, iteration < 3):

```toon
status: loop_back
plan_id: {plan_id}
iteration: {current_iteration}
reason: {ci_failure|review_comments|sonar_issues}
next_phase: 5-execute
fix_tasks_created: {count}
```

**Error**:

```toon
status: error
plan_id: {plan_id}
step: {commit|push|pr|automated_review|sonar}
message: {error_description}
recovery: {recovery_suggestion}
```

---

## Error Handling

On any error, **first log the error** to work-log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) {step} failed - {error_type}: {error_context}"
```

See `standards/validation.md` for specific error scenarios and recovery actions.

---

## Resumability

Step activation is determined by presence in the `steps` list — absent steps are not executed.

State checks (for present steps):

1. **Uncommitted changes?** `git status --porcelain` — empty → skip commit_push
2. **Branch pushed?** `git log @{u}..HEAD --oneline` — empty → skip push
3. **PR exists?** `ci pr view` — `status: success` → skip creation, use returned `pr_number`
4. **Plan complete?** `manage-status read` — `current_phase: complete` → skip all

---

## Standards (Load On-Demand)

| Standard | Step Name | Purpose |
|----------|-----------|---------|
| `standards/commit-push.md` | `default:commit-push` | Commit strategy, git status, workflow-integration-git delegation |
| `standards/create-pr.md` | `default:create-pr` | PR existence check, body generation, CI pr create |
| `standards/automated-review.md` | `default:automated-review` | CI wait, review triage, loop-back on findings |
| `standards/sonar-roundtrip.md` | `default:sonar-roundtrip` | Sonar quality gate, issue resolution |
| `standards/knowledge-capture.md` | `default:knowledge-capture` | manage-memories save command |
| `standards/lessons-capture.md` | `default:lessons-capture` | manage-lesson add command |
| `standards/branch-cleanup.md` | `default:branch-cleanup` | Branch cleanup with user confirmation — PR mode (merge + CI) or local-only (switch + pull) |
| `standards/record-metrics.md` | `default:record-metrics` | Record final plan metrics before archive |
| `standards/archive-plan.md` | `default:archive-plan` | Archive the completed plan |
| `standards/required-steps.md` | — | Canonical list of steps enforced by the `phase_steps_complete` handshake invariant |
| `standards/validation.md` | — | Configuration requirements, error scenarios |
| `standards/lessons-integration.md` | — | Conceptual guidance on lesson capture |

---

## Templates

| Template | Purpose |
|----------|---------|
| `templates/pr-template.md` | PR body format |

---

## Related

| Resource | Purpose |
|----------|---------|
| [references/workflow-overview.md](references/workflow-overview.md) | Visual diagrams: 6-Phase Model and Shipping Pipeline |
| `plan-marshall:dev-general-practices` | Bash safety rules, tool usage patterns |
| `plan-marshall:workflow-integration-git` | Commit, push workflow |
| `plan-marshall:tools-integration-ci` | PR operations, CI status |
| `plan-marshall:workflow-integration-github` | CI monitoring, review handling (GitHub) |
| `plan-marshall:workflow-integration-sonar` | Sonar quality gate |
| `plan-marshall:phase-5-execute` | Loop-back target for fix task execution |
| `plan-marshall:manage-memories` | Knowledge capture |
| `plan-marshall:manage-lessons` | Lessons capture |
