# Planning Workflows (Phases 1-4)

Workflows for plan creation and setup phases: init, refine, outline, and plan.

**CRITICAL CONSTRAINT**: These workflows create and manage **plans only**. NEVER implement tasks directly. All task descriptions MUST result in plans - not actual implementation. After completing 1-init through 4-plan phases, STOP and wait for execute action.

## Action Routing

| Action | Workflow |
|--------|----------|
| `list` (default) | List all plans |
| `init` | Create new plan, auto-continue |
| `refine` | Clarify request until confident |
| `outline` | Run 3-outline and 4-plan phases |
| `cleanup` | Remove completed plans |
| `lessons` | List and convert lessons to plans |

---

## Action: list (default)

Display all plans with numbered selection.

```bash
python3 .plan/execute-script.py pm-workflow:manage-lifecycle:manage-lifecycle list
```

Shows:
```
Available Plans:

1. jwt-authentication [5-execute] - 3/12 tasks complete
2. user-profile-api [3-outline] - Requirements analysis

0. Create new plan

Select plan (number) or action (c/n/q):
```

---

## Action: init

Create a new plan and automatically continue to 2-refine/3-outline/4-plan phases.

**1-Init Phase** uses a single agent:

```
Task: pm-workflow:plan-init-agent
  Input: description OR issue OR lesson_id
  Output: plan_id, domains array
```

**Automatic Continuation to 2-Refine**:
1. Check `stop-after-init` parameter
2. If false (default): Automatically invoke 2-refine, 3-outline, and 4-plan phases with the new plan_id
3. If true: Stop and display plan summary

---

## Action: outline (3-Outline + 4-Plan Phases)

**CRITICAL**: This action has 4 steps. Step 3 is a MANDATORY user review gate. Do NOT skip from Step 2 to Step 4.

---

**Step 1**: Read domains from references:
```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get \
  --plan-id {plan_id} --field domains
```

---

**Step 2**: Load outline phase skill directly (maintains main context)

```
Skill: pm-workflow:phase-3-outline
  Arguments: --plan-id {plan_id}
```

The skill runs in main conversation context and CAN spawn Task agents for parallel analysis.

Log solution outline creation:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (pm-workflow:plan-marshall) Created solution_outline.md - pending user review"
```

**Step 2b**: Q-Gate auto-loop (max 3 iterations)

Check if the phase returned Q-Gate findings. If so, auto-loop without user intervention.

```
qgate_iteration = 0
MAX_QGATE_ITERATIONS = 3

WHILE qgate_pending_count > 0 AND qgate_iteration < MAX_QGATE_ITERATIONS:
  qgate_iteration += 1
  1. Log: "(pm-workflow:plan-marshall:qgate) Auto-fix iteration {qgate_iteration}/{MAX_QGATE_ITERATIONS}: {count} findings — re-entering phase-3-outline"
  2. Re-invoke phase-3-outline skill (phase reads findings at Step 1 and addresses them)
  3. Check qgate_pending_count from phase return

IF qgate_pending_count > 0 AND qgate_iteration >= MAX_QGATE_ITERATIONS:
  → STOP: Escalate to user — "Q-Gate auto-loop exhausted after {MAX_QGATE_ITERATIONS} iterations. {count} findings remain unresolved."
  → Present remaining findings and ask user how to proceed
```

This loop runs automatically — do NOT prompt the user for Q-Gate findings unless the max iteration limit is reached. Q-Gate findings are objective quality failures that the phase must self-correct. Only proceed to Step 2c when `qgate_pending_count == 0`.

**Step 2c**: Transition phase after outline completes AND Q-Gate is clean:
```bash
python3 .plan/execute-script.py pm-workflow:manage-lifecycle:manage-lifecycle transition \
  --plan-id {plan_id} --completed 3-outline
```

---

## Step 3: MANDATORY USER REVIEW

**STOP HERE. Do NOT proceed to Step 4 without user approval.**

The outline presented here has already passed Q-Gate verification. The user reviews the quality-verified outline.

### 3a. Read and display the solution outline for review:

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline read \
  --plan-id {plan_id}
```

Then display:
```
## Solution Outline Created

**Review your solution outline**: .plan/plans/{plan_id}/solution_outline.md

Please review the deliverables and architecture before proceeding.
```

### 3b. Ask the user to confirm or request changes:
```
AskUserQuestion:
  questions:
    - question: "Have you reviewed the solution outline? How would you like to proceed?"
      header: "Review"
      options:
        - label: "Proceed to create tasks"
          description: "Solution outline looks good, continue to task planning"
        - label: "Request changes"
          description: "I have feedback to improve the solution outline"
      multiSelect: false
```

### 3c. Handle user response:
- **If "Proceed to create tasks"**: Continue to Step 4
- **If "Request changes"** or user provides custom feedback:
  - Capture the user's feedback
  - Write each feedback point as a Q-Gate finding:
    ```bash
    python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
      qgate add --plan-id {plan_id} --phase 3-outline --source user_review \
      --type triage --title "User: {feedback summary}" \
      --detail "{full feedback text}"
    ```
  - Log feedback capture:
    ```bash
    python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
      decision --plan-id {plan_id} --level INFO --message "(pm-workflow:plan-marshall) User review: {count} change requests recorded to artifacts/qgate-3-outline.jsonl"
    ```
  - Re-invoke phase-3-outline skill (phase reads Q-Gate findings at Step 1)
  - **Loop back to Step 3a**

---

**Step 4**: Create tasks from deliverables

Only execute this step AFTER user approves in Step 3.

```
Task: pm-workflow:task-plan-agent
  Input: plan_id={plan_id}
  Output: tasks created with domain, profile, skills
```

Log task plan agent invocation:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (pm-workflow:plan-marshall) Invoked task-plan-agent"
```

**Step 4b**: Transition phase after tasks created:
```bash
python3 .plan/execute-script.py pm-workflow:manage-lifecycle:manage-lifecycle transition \
  --plan-id {plan_id} --completed 4-plan
```

---

## Action: cleanup

Remove completed plans. Shows completed plans for selective or batch deletion with confirmation.

---

## Action: lessons

List lessons learned and convert selected lesson to a plan.

Shows:
```
Lessons Learned:

1. [bug] Build fails on special characters in paths
   Component: builder-maven:maven-build-and-fix
   Date: 2025-11-27

0. Back to main menu

Select lesson to convert to plan:
```

When a lesson is selected:
1. Analyzes lesson content for actionable tasks
2. Asks for clarification only if lesson is ambiguous
3. Creates a new plan via plan-init skill
4. Moves the lesson file to the plan directory

---

## Script API Reference

Script: `pm-workflow:manage-lifecycle:manage-lifecycle`

| Command | Parameters | Description |
|---------|------------|-------------|
| `read` | `--plan-id` | Read plan status |
| `create` | `--plan-id --title --phases [--force]` | Initialize status.toon |
| `set-phase` | `--plan-id --phase` | Set current phase |
| `update-phase` | `--plan-id --phase --status` | Update phase status |
| `progress` | `--plan-id` | Calculate plan progress |
| `list` | `[--filter]` | Discover all plans |
| `transition` | `--plan-id --completed` | Transition to next phase |
| `archive` | `--plan-id [--dry-run]` | Archive completed plan |
| `route` | `--phase` | Get skill for phase |
| `get-routing-context` | `--plan-id` | Get combined routing context |

---

## Storage

Status is stored in the plan directory:

```
.plan/plans/{plan_id}/status.toon
```

Archived plans:

```
.plan/archived-plans/{yyyy-mm-dd}-{plan-name}/
```

---

## Status File Format

TOON format with phases table:

```toon
title: Implement JWT Authentication
current_phase: 5-execute

phases[7]{name,status}:
1-init,done
2-refine,done
3-outline,done
4-plan,done
5-execute,in_progress
6-verify,pending
7-finalize,pending

created: 2025-12-02T10:00:00Z
updated: 2025-12-02T14:30:00Z
```

### Phase Statuses

| Status | Meaning |
|--------|---------|
| `pending` | Not started |
| `in_progress` | Currently active |
| `done` | Completed |

---

## Phase Routing

The `route` command returns skill names for each phase:

| Phase | Skill | Description |
|-------|-------|-------------|
| 1-init | `plan-init` | Initialize plan structure |
| 2-refine | `request-refine` | Clarify request until confident |
| 3-outline | `solution-outline` | Create solution outline with deliverables |
| 4-plan | `task-plan` | Create tasks from deliverables |
| 5-execute | `plan-execute` | Execute implementation tasks |
| 6-verify | `plan-verify` | Verify implementation quality |
| 7-finalize | `plan-finalize` | Finalize with commit/PR |
