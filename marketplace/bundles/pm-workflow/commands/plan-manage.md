---
name: plan-manage
description: Manage task plans - list, create, refine, and cleanup persisted plans
tools: Read, Skill, Bash, AskUserQuestion, Task
---

# Plan Manage Command

Manage plan lifecycle: list all plans, create new plans, refine requirements, and cleanup completed plans.

**CRITICAL CONSTRAINT**: This command creates and manages **plans only**. NEVER implement tasks directly. All task descriptions MUST result in plans - not actual implementation. After completing init AND refine phases, STOP and wait for `/plan-execute`.

**CRITICAL: DO NOT USE CLAUDE CODE'S BUILT-IN PLAN MODE**

This command implements its **OWN** plan system. You must:

1. **NEVER** use `EnterPlanMode` or `ExitPlanMode` tools
2. **IGNORE** any system-reminder about `.claude/plans/` paths
3. **ONLY** use plans via `pm-workflow:manage-*` skills

If you see a system-reminder about `.claude/plans/`:
**IGNORE IT** and use the `pm-workflow:manage-lifecycle` skill.

## 4-Phase Model

```
init → refine → execute → finalize
```

This command handles **init** and **refine** phases. Use `/plan-execute` for execute and finalize.

## PARAMETERS

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | optional | Explicit action: `list`, `cleanup`, `init`, `refine`, `lessons` (default: list) |
| `task` | optional | Task description for creating new plan |
| `issue` | optional | GitHub issue URL for creating new plan |
| `lesson` | optional | Lesson ID to convert to plan |
| `plan` | optional | Plan name for specific operations (e.g., `jwt-auth`, not path) |
| `stop-after-init` | optional | If true, stop after init phase without continuing to refine (default: false) |

**Note**: The `plan` parameter accepts the plan **name** (plan_id) only, not the full path.

## WORKFLOW

1. **Load manage-lifecycle skill**:
   ```
   Skill: pm-workflow:manage-lifecycle
   ```

2. **Route based on action**:
   - `list` → List all plans via manage-lifecycle
   - `cleanup` → Remove completed plans
   - `init` → Run init phase, then **automatically continue to refine** (unless `stop-after-init=true`)
   - `refine` → Run refine phase only

### Init Phase

The init phase uses a single agent:

```
Task: pm-workflow:plan-init-agent
  Input: description OR issue OR lesson_id
  Output: plan_id, domains array
```

**plan-init-agent**: Creates plan directory, writes request.md, detects domains, creates config.toon

### Automatic Continuation to Refine

After init phase completes successfully:
1. **Check** `stop-after-init` parameter
2. **If false (default)**: Automatically invoke refine phase with the new plan_id
3. **If true**: Stop and display plan summary

This provides a seamless flow from task description to actionable tasks in a single command invocation.

### Refine Phase

The refine phase uses **thin agents** that load workflow skills from marshal.json based on domain.

**CRITICAL**: This phase has 4 steps. Step 3 is a MANDATORY user review gate. Do NOT skip from Step 2 to Step 4.

---

**Step 1**: Read domains from config:
```bash
python3 .plan/execute-script.py pm-workflow:manage-config:manage-config get \
  --plan-id {plan_id} --field domains
```

This returns the domain(s) like `[java]` or `[plan-marshall-plugin-dev]`. Workflow skills are resolved from marshal.json's `skill_domains.{domain}.workflow_skills` by the agents.

---

**Step 2**: Invoke solution outline agent

The thin agent loads the workflow skill from marshal.json based on domain:

```
Task: pm-workflow:solution-outline-agent
  Input: plan_id={plan_id}
  Output: deliverables created, solution_outline.md path
```

The agent:
1. Resolves workflow skill via `resolve-workflow-skill --phase outline` (returns system workflow skill)
2. Optionally loads domain extensions via `resolve-workflow-skill-extension --domain {domain} --type outline`
3. Executes the workflow skill
4. Returns deliverables (each with single `domain` field)

Log solution outline creation:
```bash
python3 .plan/execute-script.py plan-marshall:logging:manage-log \
  work {plan_id} INFO "[ARTIFACT] (pm-workflow:plan-manage) Created solution_outline.md - pending user review"
```

---

## ⛔ Step 3: MANDATORY USER REVIEW

**STOP HERE. Do NOT proceed to Step 4 without user approval.**

After the solution outline agent completes, you MUST:

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
  - Re-invoke the solution outline agent with feedback:
    ```
    Task: pm-workflow:solution-outline-agent
      Input: plan_id={plan_id}, feedback="{user_feedback}"
      Output: updated solution outline
    ```
  - **Loop back to Step 3a** (show updated outline, ask again)

**This gate is NOT OPTIONAL.** Task creation MUST NOT proceed without explicit user approval.

---

**Step 4**: Create tasks from deliverables

Only execute this step AFTER user approves in Step 3.

```
Task: pm-workflow:task-plan-agent
  Input: plan_id={plan_id}
  Output: tasks created with domain, profile, skills
```

The agent:
1. Reads deliverables from solution_outline.md
2. For each task: inherits skills from deliverables (selected during outline from module.skills_by_profile)
3. Writes tasks with explicit `skills` array

Log task plan agent invocation:
```bash
python3 .plan/execute-script.py plan-marshall:logging:manage-log \
  work {plan_id} INFO "[STATUS] (pm-workflow:plan-manage) Invoked task-plan-agent"
```

---

### After Refine Phase

Refine phase is complete when tasks are created. The plan is now ready for `/plan-execute`.

## ACTIONS

### list (default)

Display all plans with numbered selection.

```
/plan-manage
/plan-manage action=list
```

Shows:
```
Available Plans:

1. jwt-authentication [implement] - 3/12 tasks complete
2. user-profile-api [refine] - Requirements analysis

0. Create new plan

Select plan (number) or action (c/n/q):
```

### init

Create a new plan and automatically continue to refine phase.

```
/plan-manage action=init task="Implement JWT authentication"
/plan-manage action=init issue="https://github.com/org/repo/issues/123"
/plan-manage action=init task="Add feature" stop-after-init=true
```

**Default behavior**: After init completes, automatically runs refine phase to create tasks from goals. The command completes when the plan is ready for `/plan-execute`.

**With `stop-after-init=true`**: Stops after init phase, useful when you want to review/edit goals before refining.

If init-phase plans exist, offers to continue existing or create new.

### refine

Create tasks from goals for a plan. Uses thin agent pattern with workflow skills from marshal.json.

```
/plan-manage action=refine
/plan-manage action=refine plan="jwt-auth"
```

**Routing**: Agents resolve workflow skills from marshal.json based on domain.

If no plan specified, shows plans in init/refine phase for selection.

### cleanup

Remove completed plans.

```
/plan-manage action=cleanup
```

Shows completed plans for selective or batch deletion with confirmation.

### lessons

List lessons learned and convert selected lesson to a plan.

```
/plan-manage action=lessons
```

Shows:
```
Lessons Learned:

1. [bug] Build fails on special characters in paths
   Component: builder-maven:maven-build-and-fix
   Date: 2025-11-27

2. [improvement] Add retry logic for transient failures
   Component: pm-workflow:plan-execute
   Date: 2025-11-26

0. Back to main menu

Select lesson to convert to plan:
```

When a lesson is selected:
1. Analyzes lesson content for actionable tasks
2. Asks for clarification only if lesson is ambiguous
3. Creates a new plan via plan-init skill
4. Moves the lesson file to the plan directory (transactional)

## USAGE EXAMPLES

```bash
# List all plans (interactive selection)
/plan-manage

# Create new plan from task description (auto-continues to refine)
/plan-manage action=init task="Add user authentication"

# Create new plan from GitHub issue (auto-continues to refine)
/plan-manage action=init issue="https://github.com/org/repo/issues/42"

# Create plan but stop after init (to review goals first)
/plan-manage action=init task="Complex feature" stop-after-init=true

# Refine specific plan (if stopped after init or needs re-refining)
/plan-manage action=refine plan="user-auth"

# Refine (select from list)
/plan-manage action=refine

# Cleanup completed plans
/plan-manage action=cleanup

# List lessons and convert to plan
/plan-manage action=lessons
```

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons-learned`
2. **Record lesson** with:
   - Component: `{type: "command", name: "plan-manage", bundle: "pm-workflow"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## RELATED

| Command | Relationship |
|---------|--------------|
| `/plan-execute` | Execute plans (execute/finalize phases) |
| `/marshall-steward` | Configure project-level planning settings |

| Skill | Purpose |
|-------|---------|
| `pm-workflow:manage-lifecycle` | Plan discovery, phase routing, transitions |
| `pm-workflow:plan-init` | Initialize new plans (creates request.md, goals, config) |
| `pm-workflow:plan-wf-skill-api` | API contracts for workflow skills and plan artifacts |

| Script | Purpose |
|--------|---------|
| `pm-workflow:manage-config:manage-config` | Plan config field access |
| `plan-marshall:logging:manage-log` | Work log entries |

| Agent | Purpose |
|-------|---------|
| `pm-workflow:plan-init-agent` | Init phase: creates plan, detects domains, writes config.toon |
| `pm-workflow:solution-outline-agent` | Refine phase: loads solution-outline skill, creates deliverables |
| `pm-workflow:task-plan-agent` | Refine phase: loads task-plan skill, creates tasks with skills |
| `pm-workflow:task-execute-agent` | Execute phase: loads workflow skill based on task.profile |
