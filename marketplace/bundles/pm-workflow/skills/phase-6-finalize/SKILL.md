---
name: phase-6-finalize
description: Complete plan execution with git workflow and PR management
user-invocable: false
allowed-tools: Read, Bash, Glob, Skill, Task
---

# Phase Finalize Skill

**Role**: Finalize phase skill. Handles shipping workflow (commit, push, PR) and plan completion. Verification tasks have already been executed within phase-5-execute.

**Key Pattern**: Shipping-focused execution. No verification steps—all quality checks run as verification tasks within phase-5-execute before reaching this phase.

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

Finalize configuration comes from marshal.json phase sections:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-6-finalize get --trace-plan-id {plan_id}
```

Cross-phase settings (also from marshal.json):
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-5-execute get --trace-plan-id {plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-1-init get --trace-plan-id {plan_id}
```

**Config Fields Used**:

| Source | Field | Description |
|--------|-------|-------------|
| phase-6-finalize | `1_commit_push` | Whether to commit and push |
| phase-6-finalize | `2_create_pr` | Whether to create a pull request |
| phase-6-finalize | `3_automated_review` | Whether to run CI review |
| phase-6-finalize | `4_sonar_roundtrip` | Whether to run Sonar analysis |
| phase-6-finalize | `5_knowledge_capture` | Whether to capture learnings |
| phase-6-finalize | `6_lessons_capture` | Whether to record lessons |
| phase-6-finalize | `max_iterations` | Maximum finalize-verify loops |
| phase-5-execute | `commit_strategy` | per_deliverable/per_plan/none |
| phase-1-init | `branch_strategy` | feature/direct |

---

## Operation: finalize

**Input**: `plan_id`

### Step 1: Check Q-Gate Findings and Log Start

### Log Phase Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (pm-workflow:phase-6-finalize) Starting finalize phase"
```

### Query Unresolved Findings

```bash
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  qgate query --plan-id {plan_id} --phase 6-finalize --resolution pending
```

If unresolved findings exist from a previous iteration (filtered_count > 0):

For each pending finding:
1. Check if it was addressed by the fix tasks that just ran
2. Resolve:
```bash
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  qgate resolve --plan-id {plan_id} --hash-id {hash_id} --resolution fixed --phase 6-finalize \
  --detail "{fix task reference or description}"
```
3. Log:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:phase-6-finalize:qgate) Finding {hash_id} [qgate]: fixed — {resolution_detail}"
```

### Step 2: Read Configuration

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-6-finalize get --trace-plan-id {plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-5-execute get --trace-plan-id {plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-1-init get --trace-plan-id {plan_id}
```

Also read references context for branch and issue information:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get-context \
  --plan-id {plan_id}
```

Returns: `branch`, `base_branch`, `issue_url`, `build_system`, and file counts in a single call.

**After reading configuration**, log the finalize strategy decision:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:phase-6-finalize) Finalize strategy: commit={commit_strategy}, PR={create_pr}, branch={branch_strategy}"
```

### Step 3: Conditional Commit Workflow

**If `commit_strategy == none`**: Skip commit entirely.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:phase-6-finalize) Commit skipped: commit_strategy=none"
```

Proceed directly to Step 4.

**If `commit_strategy == per_deliverable`**: Only commit if there are uncommitted changes remaining (some changes may already be committed per-deliverable during execute phase).

**If `commit_strategy == per_plan`**: Commit all changes as a single commit (current default behavior).

For `per_deliverable` and `per_plan`, load the git-workflow skill:

```
Skill: pm-workflow:workflow-integration-git
```

The git-workflow skill handles:
- Artifact detection and cleanup (*.class, *.temp files)
- Commit message generation following conventional commits
- Stage, commit, and push operations

**Parameters** (from config and request):
- `message`: Generated from request.md summary
- `push`: true (always push in finalize)
- `create-pr`: from `create_pr` config field

### Step 4: Create PR (if enabled)

If `create_pr == true`, the git-workflow skill creates the PR with:
- Title from request.md
- Body using `templates/pr-template.md`
- Issue link from references.json (`Closes #{issue}` if present)

### Step 5: Automated Review (if PR created)

If PR was created:

```
Skill: pm-workflow:workflow-integration-ci
```

This monitors CI status and handles review comments.

**On findings** (CI failures, review comments):
1. Persist each finding to Q-Gate:
```bash
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 6-finalize --source qgate \
  --type {pr-comment|build-error} --title "{finding title}" \
  --detail "{finding details}"
```
2. Create fix tasks via manage-tasks
3. Loop back to phase-5-execute (iteration + 1)
4. Continue until clean or max iterations (3)

```bash
# Check iteration count from status
# If issues and iteration < max_iterations, loop back to execute
python3 .plan/execute-script.py pm-workflow:manage-status:manage_status set-phase \
  --plan-id {plan_id} --phase 5-execute
```

### Step 6: Sonar Roundtrip (if configured)

If Sonar integration is enabled:

```
Skill: pm-workflow:workflow-integration-sonar
```

Handles Sonar quality gate and issue resolution. On findings, follows same loop-back pattern as Step 5.

### Step 7: Knowledge Capture (Advisory)

```
Skill: plan-marshall:manage-memories
```

Records any significant patterns discovered during implementation. Advisory only—does not block.

### Step 8: Lessons Capture (Advisory)

```
Skill: plan-marshall:manage-lessons
```

Records lessons learned from the implementation. Advisory only—does not block.

### Step 9: Mark Plan Complete

Transition to complete:

```bash
python3 .plan/execute-script.py pm-workflow:manage-lifecycle:manage-lifecycle transition \
  --plan-id {plan_id} \
  --completed 6-finalize
```

### Step 10: Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (pm-workflow:phase-6-finalize) Plan completed: commit={commit_hash}, PR={pr_url|skipped}"
```

**Add visual separator** after END log:

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
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (pm-workflow:phase-6-finalize) {step} failed - {error_type}: {error_context}"
```

### Git Commit Failure

```toon
status: error
step: commit
message: Nothing to commit or merge conflict
recovery: Resolve conflicts, then re-run finalize
```

### Push Failure

```toon
status: error
step: push
message: Remote rejected push
recovery: Pull changes, resolve conflicts, then re-run finalize
```

### PR Creation Failure

```toon
status: error
step: pr
message: PR already exists or branch not pushed
recovery: Check existing PRs or push branch first
```

### Max Iterations Reached

```toon
status: error
step: iteration_limit
message: Max finalize iterations (3) reached
recovery: Manual intervention required - review remaining PR issues
```

---

## Resumability

The skill checks current state before each step:

1. **Are there uncommitted changes?** Skip commit if clean
2. **Is branch pushed?** Skip push if remote is current
3. **Does PR exist?** Skip creation if PR exists
4. **Is automated review complete?** Skip if already processed
5. **Is Sonar roundtrip complete?** Skip if already processed
6. **Is plan already complete?** Skip if finalize done

---

## Shipping Pipeline

See [references/workflow-overview.md](references/workflow-overview.md) for the visual shipping pipeline diagram.

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [references/workflow-overview.md](references/workflow-overview.md) | Visual diagrams: 6-Phase Model and Shipping Pipeline flowchart |

---

## Standards (Load On-Demand)

### Validation
```
Read standards/validation.md
```
Contains: Configuration requirements, step-by-step validation checklist, output format examples

### Lessons Integration
```
Read standards/lessons-integration.md
```
Contains: How lessons are captured at plan completion, knowledge extraction patterns

---

## Templates

| Template | Purpose |
|----------|---------|
| `templates/pr-template.md` | PR body format |

---

## Integration

### Phase Routing

This skill is invoked when plan is in `6-finalize` phase:

```
pm-workflow:manage-lifecycle:manage-lifecycle route --phase 6-finalize → pm-workflow:phase-6-finalize
```

### Loop-Back to Execute

On PR issues (CI failures, review comments, Sonar findings):
1. Create fix tasks via `pm-workflow:manage-tasks`
2. Increment `finalize_iteration` counter
3. Transition to `5-execute` phase
4. Fix tasks run within `5-execute`, then return to `6-finalize`
5. Repeat until clean or max iterations (3)

### Command Integration

- **/plan-marshall action=finalize** - Invokes this skill
- **/pr-doctor** - Used during automated review step

### Related Skills

| Skill | Purpose |
|-------|---------|
| `pm-workflow:workflow-integration-git` | Commit, push, PR creation |
| `pm-workflow:workflow-integration-ci` | CI monitoring, review handling |
| `pm-workflow:workflow-integration-sonar` | Sonar quality gate |
| `pm-workflow:phase-5-execute` | Loop-back target for fix task execution |
| `pm-workflow:plan-marshall` | Phase transitions (manage-lifecycle script) |
| `plan-marshall:manage-memories` | Knowledge capture |
| `plan-marshall:manage-lessons` | Lessons capture |
