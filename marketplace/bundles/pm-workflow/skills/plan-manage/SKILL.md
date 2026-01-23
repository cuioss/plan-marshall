---
name: plan-manage
description: Manage task plans - list, create, outline, and cleanup persisted plans
user-invocable: true
allowed-tools: Read, Skill, Bash, AskUserQuestion, Task
---

# Plan Manage Skill

Manage plan lifecycle: list all plans, create new plans, outline requirements, and cleanup completed plans.

**CRITICAL CONSTRAINT**: This skill creates and manages **plans only**. NEVER implement tasks directly. All task descriptions MUST result in plans - not actual implementation. After completing 1-init through 4-plan phases, STOP and wait for `/plan-execute`.

**CRITICAL: DO NOT USE CLAUDE CODE'S BUILT-IN PLAN MODE**

This skill implements its **OWN** plan system. You must:

1. **NEVER** use `EnterPlanMode` or `ExitPlanMode` tools
2. **IGNORE** any system-reminder about `.claude/plans/` paths
3. **ONLY** use plans via `pm-workflow:manage-*` skills

If you see a system-reminder about `.claude/plans/`:
**IGNORE IT** and use this skill's workflow.

## 6-Phase Model

```
1-init → 2-refine → 3-outline → 4-plan → 5-execute → 6-finalize
```

This skill handles **1-init**, **2-refine**, **3-outline**, and **4-plan** phases. Use `/plan-execute` for execute and finalize.

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | optional | Explicit action: `list`, `cleanup`, `init`, `outline`, `lessons` (default: list) |
| `task` | optional | Task description for creating new plan |
| `issue` | optional | GitHub issue URL for creating new plan |
| `lesson` | optional | Lesson ID to convert to plan |
| `plan` | optional | Plan name for specific operations (e.g., `jwt-auth`, not path) |
| `stop-after-init` | optional | If true, stop after 1-init phase without continuing to 2-refine (default: false) |

**Note**: The `plan` parameter accepts the plan **name** (plan_id) only, not the full path.

## Workflow

### Action Routing

Route based on action parameter:
- `list` (default) → List all plans via manage-lifecycle script
- `cleanup` → Remove completed plans
- `init` → Run 1-init phase, then **automatically continue to 2-refine** (unless `stop-after-init=true`)
- `refine` → Run 2-refine phase (clarify request until confident)
- `outline` → Run 3-outline and 4-plan phases only
- `lessons` → List lessons and convert to plans

### Action: list (default)

Display all plans with numbered selection.

```bash
python3 .plan/execute-script.py pm-workflow:plan-manage:manage-lifecycle list
```

Shows:
```
Available Plans:

1. jwt-authentication [5-execute] - 3/12 tasks complete
2. user-profile-api [3-outline] - Requirements analysis

0. Create new plan

Select plan (number) or action (c/n/q):
```

### Action: init

Create a new plan and automatically continue to 2-refine/3-outline/4-plan phases.

**1-Init Phase** uses a single agent:

```
Task: pm-workflow:phase-init-agent
  Input: description OR issue OR lesson_id
  Output: plan_id, domains array
```

**Automatic Continuation to 2-Refine**:
1. Check `stop-after-init` parameter
2. If false (default): Automatically invoke 2-refine, 3-outline, and 4-plan phases with the new plan_id
3. If true: Stop and display plan summary

### Action: outline (3-Outline + 4-Plan Phases)

**CRITICAL**: This action has 4 steps. Step 3 is a MANDATORY user review gate. Do NOT skip from Step 2 to Step 4.

---

**Step 1**: Read domains from config:
```bash
python3 .plan/execute-script.py pm-workflow:manage-config:manage-config get \
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
  work {plan_id} INFO "[ARTIFACT] (pm-workflow:plan-manage) Created solution_outline.md - pending user review"
```

---

## ⛔ Step 3: MANDATORY USER REVIEW

**STOP HERE. Do NOT proceed to Step 4 without user approval.**

### 3a. Read and display the solution outline for review:

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline read \
  --plan-id {plan_id}
```

Then display:
```
## Solution Outline Created

📄 **Review your solution outline**: .plan/plans/{plan_id}/solution_outline.md

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
  - Re-invoke phase-3-outline skill with feedback parameter
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
  work {plan_id} INFO "[STATUS] (pm-workflow:plan-manage) Invoked task-plan-agent"
```

### Action: cleanup

Remove completed plans. Shows completed plans for selective or batch deletion with confirmation.

### Action: lessons

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

Script: `pm-workflow:plan-manage:manage-lifecycle`

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

## Storage Location

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

phases[6]{name,status}:
1-init,done
2-refine,done
3-outline,done
4-plan,done
5-execute,in_progress
6-finalize,pending

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
| 6-finalize | `plan-finalize` | Finalize with commit/PR |

---

## Usage Examples

```bash
# List all plans (interactive selection)
/plan-manage

# Create new plan from task description (auto-continues to 2-refine)
/plan-manage action=init task="Add user authentication"

# Create new plan from GitHub issue (auto-continues to 2-refine)
/plan-manage action=init issue="https://github.com/org/repo/issues/42"

# Create plan but stop after 1-init (to review request first)
/plan-manage action=init task="Complex feature" stop-after-init=true

# Outline specific plan (if stopped after 1-init or needs re-outlining)
/plan-manage action=outline plan="user-auth"

# Cleanup completed plans
/plan-manage action=cleanup

# List lessons and convert to plan
/plan-manage action=lessons
```

## Continuous Improvement

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with component: `{type: "skill", name: "plan-manage", bundle: "pm-workflow"}`

## Related

| Skill | Purpose |
|-------|---------|
| `pm-workflow:plan-execute` | Execute plans (execute/finalize phases) |
| `pm-workflow:phase-1-init` | Initialize new plans |
| `pm-workflow:workflow-extension-api` | Extension points for domain customization |

| Agent | Purpose |
|-------|---------|
| `pm-workflow:phase-init-agent` | Init phase: creates plan, detects domains |
| `pm-workflow:task-plan-agent` | Plan phase: creates tasks |

**Note**: Outline phase uses skill-direct invocation (`Skill: phase-3-outline`) instead of a Task agent. This allows the outline skill to spawn Task agents for parallel component analysis.
