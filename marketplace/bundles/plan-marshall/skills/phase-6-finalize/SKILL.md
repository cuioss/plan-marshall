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
- Never skip config gate checks (Steps 3-8 each have an IF gate)
- Never skip phase transitions — use `manage-lifecycle transition`, never set status directly
- Never improvise script subcommands — use only those documented in this skill's workflow steps

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

| Field | Type | Gates | Description |
|-------|------|-------|-------------|
| `1_commit_push` | boolean | Step 3 | Whether to commit and push |
| `2_create_pr` | boolean | Step 4 | Whether to create a pull request |
| `3_automated_review` | boolean | Step 5 | Whether to run CI review |
| `4_sonar_roundtrip` | boolean | Step 6 | Whether to run Sonar analysis |
| `5_knowledge_capture` | boolean | Step 7 | Whether to capture learnings |
| `6_lessons_capture` | boolean | Step 8 | Whether to record lessons |
| `review_bot_buffer_seconds` | integer | — | Seconds to wait after CI for review bots (default: 300) |
| `max_iterations` | integer | — | Maximum finalize-verify loops (default: 3) |

Cross-phase settings:

| Source | Field | Description |
|--------|-------|-------------|
| phase-5-execute | `commit_strategy` | per_deliverable/per_plan/none |
| phase-1-init | `branch_strategy` | feature/direct |

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

**After reading configuration**, log the finalize strategy decision:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Finalize strategy: commit={commit_strategy}, PR={create_pr}, branch={branch_strategy}"
```

### Step 3: Commit and Push (if enabled)

**Config gate**: `1_commit_push` from phase-6-finalize config

IF `1_commit_push == true`:
  Read `standards/commit-push.md` and follow all steps.

ELSE:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Commit+Push skipped: 1_commit_push=false"
```

### Step 4: Create PR (if enabled)

**Config gate**: `2_create_pr` from phase-6-finalize config

IF `2_create_pr == true`:
  Read `standards/create-pr.md` and follow all steps.

ELSE:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) PR creation skipped: 2_create_pr=false"
```

### Step 5: Automated Review (if enabled)

**Config gate**: `3_automated_review` from phase-6-finalize config

IF `3_automated_review == true` AND a PR exists:
  Read `standards/automated-review.md` and follow all steps.

ELSE:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Automated review skipped: 3_automated_review=false"
```

### Step 6: Sonar Roundtrip (if enabled)

**Config gate**: `4_sonar_roundtrip` from phase-6-finalize config

IF `4_sonar_roundtrip == true`:
  Read `standards/sonar-roundtrip.md` and follow all steps.

ELSE:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Sonar roundtrip skipped: 4_sonar_roundtrip=false"
```

### Step 7: Knowledge Capture (if enabled)

**Config gate**: `5_knowledge_capture` from phase-6-finalize config

IF `5_knowledge_capture == true`:
  Read `standards/knowledge-capture.md` and follow all steps.

ELSE:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Knowledge capture skipped: 5_knowledge_capture=false"
```

### Step 8: Lessons Capture (if enabled)

**Config gate**: `6_lessons_capture` from phase-6-finalize config

IF `6_lessons_capture == true`:
  Read `standards/lessons-capture.md` and follow all steps.

ELSE:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Lessons capture skipped: 6_lessons_capture=false"
```

### Step 9: Mark Plan Complete

```bash
python3 .plan/execute-script.py plan-marshall:manage-lifecycle:manage-lifecycle transition \
  --plan-id {plan_id} \
  --completed 6-finalize
```

### Step 10: Mark Lesson Applied (conditional)

If the plan originated from a lesson, mark that lesson as applied.

**IMPORTANT**: This step MUST run before archive (Step 11), because archive moves plan files and makes `request read` fail.

Read the request source:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} --section source
```

**IF `source == "lesson"`**: Read `source_id` and mark applied:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} --section source_id
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lesson update \
  --id {source_id} --applied true
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Lesson {source_id} marked as applied"
```

**ELSE**: Skip — plan did not originate from a lesson.

### Step 11: Archive Plan

```bash
python3 .plan/execute-script.py plan-marshall:manage-lifecycle:manage-lifecycle archive \
  --plan-id {plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Plan archived: {plan_id}"
```

### Step 12: Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Plan completed: commit={commit_hash}, PR={pr_url|skipped}"
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
  knowledge_capture: done
  lessons_capture: done
  archive: done
  lesson_applied: {done|skipped}

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

Config gates (checked first — take priority):
- `1_commit_push == false` → skip Step 3
- `2_create_pr == false` → skip Step 4
- `3_automated_review == false` → skip Step 5
- `4_sonar_roundtrip == false` → skip Step 6
- `5_knowledge_capture == false` → skip Step 7
- `6_lessons_capture == false` → skip Step 8

State checks (for enabled steps):

1. **Uncommitted changes?** `git status --porcelain` — empty → skip Step 3
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
