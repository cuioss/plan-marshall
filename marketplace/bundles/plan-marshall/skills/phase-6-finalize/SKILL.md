---
name: phase-6-finalize
description: Complete plan execution with git workflow and PR management
user-invocable: false
---

# Phase Finalize Skill

**Role**: Finalize phase skill. Handles shipping workflow (commit, push, PR) and plan completion. Verification tasks have already been executed within phase-5-execute.

**Key Pattern**: Shipping-focused execution. No verification steps—all quality checks run as verification tasks within phase-5-execute before reaching this phase.

## Enforcement

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
- Never skip phase transitions — use `manage-lifecycle transition`, never set status directly
- Never improvise script subcommands — use only those documented in this skill's workflow steps
- Never skip config-gated steps based on PR state (approval, merge status, or CI status). The ONLY valid skip condition for each step is its config gate being `false`. Standards documents have their own user confirmation gates that handle runtime state decisions.

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
| `review_bot_buffer_seconds` | integer | Seconds to wait after CI for review bots (default: 300) |
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
| **built-in** | `default:` prefix (e.g., `default:commit_push`) | Strip prefix, read `standards/{name}.md` (using dispatch table below) and follow all steps |
| **project** | `project:` prefix (e.g., `project:finalize-step-foo`) | `Skill: {notation}` with interface contract parameters |
| **skill** | fully-qualified `bundle:skill` (e.g., `pm-dev-java:java-post-pr`) | `Skill: {notation}` with interface contract parameters |

**Type detection logic**:
- Starts with `default:` -> built-in type (strip prefix, validate against dispatch table)
- Starts with `project:` -> project type
- Contains `:` (other) -> fully-qualified skill type

### Built-in Step Dispatch Table

| Step Name | Standards Document | Description |
|-----------|-------------------|-------------|
| `default:commit_push` | `standards/commit-push.md` | Commit and push changes |
| `default:create_pr` | `standards/create-pr.md` | Create pull request |
| `default:automated_review` | `standards/automated-review.md` | CI automated review |
| `default:sonar_roundtrip` | `standards/sonar-roundtrip.md` | Sonar analysis roundtrip |
| `default:knowledge_capture` | `standards/knowledge-capture.md` | Capture learnings to memory |
| `default:lessons_capture` | `standards/lessons-capture.md` | Record lessons learned |
| `default:branch_cleanup` | `standards/branch-cleanup.md` | Merge PR (with --delete-branch) and pull latest |
| `default:archive` | `standards/archive.md` | Archive the completed plan |

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

### Step 1: Check Q-Gate Findings and Log Start

#### Log Phase Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
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
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
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
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Finalize strategy: commit={commit_strategy}, steps={steps_count}, branch={branch_strategy}"
```

### Step 3: Execute Step Pipeline

Iterate over the `steps` list from config. For each step reference:

```
FOR each step_ref in steps:
  1. Log step start:
     python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
       work --plan-id {plan_id} --level INFO --message "[STEP] (plan-marshall:phase-6-finalize) Executing step: {step_ref}"

  2. Determine step type:
     - IF step_ref starts with "default:" -> BUILT-IN type (strip prefix for dispatch table lookup)
     - ELSE IF step_ref starts with "project:" -> PROJECT type
     - ELSE IF step_ref contains ":" -> SKILL type

  3. Dispatch:
     - BUILT-IN: Strip `default:` prefix, read the standards document from dispatch table and follow all steps
     - PROJECT/SKILL: Load the skill with interface contract:
       Skill: {step_ref}
         Arguments: --plan-id {plan_id} --iteration {iteration}

  4. Log step completion:
     python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
       work --plan-id {plan_id} --level INFO --message "[STEP] (plan-marshall:phase-6-finalize) Completed step: {step_ref}"
END FOR
```

**Built-in step notes**:
- `default:branch_cleanup`: Do NOT preemptively skip based on PR state. The `standards/branch-cleanup.md` standard has its own `AskUserQuestion` confirmation gate.
- `default:archive`: This step MUST be last in the default order because it moves plan files (including status.json), which breaks manage-* scripts. All plan operations must complete before archive.

### Step 4: Mark Plan Complete

```bash
python3 .plan/execute-script.py plan-marshall:manage-lifecycle:manage-lifecycle transition \
  --plan-id {plan_id} \
  --completed 6-finalize
```

### Step 5: Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Plan completed: {steps_count} steps executed"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  separator --plan-id {plan_id} --type work
```

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
  lesson_applied: {done|skipped}
  branch_cleanup: {done|skipped|declined}

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
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
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

| Standard | Config Gate | Purpose |
|----------|------------|---------|
| `standards/commit-push.md` | `1_commit_push` | Commit strategy, git status, workflow-integration-git delegation |
| `standards/create-pr.md` | `2_create_pr` | PR existence check, body generation, CI pr create |
| `standards/automated-review.md` | `3_automated_review` | CI wait, review triage, loop-back on findings |
| `standards/sonar-roundtrip.md` | `4_sonar_roundtrip` | Sonar quality gate, issue resolution |
| `standards/knowledge-capture.md` | `5_knowledge_capture` | manage-memories save command |
| `standards/lessons-capture.md` | `6_lessons_capture` | manage-lesson add command |
| `standards/branch-cleanup.md` | `8_branch_cleanup` | Merge PR (with --delete-branch), pull latest, with user confirmation |
| `standards/validation.md` | — | Configuration requirements, error scenarios |
| `standards/lessons-integration.md` | — | Conceptual guidance on lesson capture |

---

## Templates

| Template | Purpose |
|----------|---------|
| `templates/pr-template.md` | PR body format |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [references/workflow-overview.md](references/workflow-overview.md) | Visual diagrams: 6-Phase Model and Shipping Pipeline |

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `plan-marshall:dev-general-practices` | Bash safety rules, tool usage patterns |
| `plan-marshall:workflow-integration-git` | Commit, push workflow |
| `plan-marshall:tools-integration-ci` | PR operations, CI status |
| `plan-marshall:workflow-integration-ci` | CI monitoring, review handling |
| `plan-marshall:workflow-integration-sonar` | Sonar quality gate |
| `plan-marshall:phase-5-execute` | Loop-back target for fix task execution |
| `plan-marshall:manage-memories` | Knowledge capture |
| `plan-marshall:manage-lessons` | Lessons capture |
