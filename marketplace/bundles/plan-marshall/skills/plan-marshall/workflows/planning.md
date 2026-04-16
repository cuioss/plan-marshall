# Planning Workflows (Phases 1-4)

Workflows for plan creation and setup phases: init, refine, outline, and plan.

> **cwd for `.plan/execute-script.py` calls**: `manage-*` scripts (Bucket A) resolve `.plan/` via `git rev-parse --git-common-dir` and work from any cwd — do **NOT** pin cwd, do **NOT** pass `--project-dir`, and never use `env -C`. Build / CI / Sonar scripts (Bucket B) take `--project-dir {worktree_path}` explicitly when a worktree is active. See `plan-marshall:tools-script-executor/standards/cwd-policy.md`.

**CRITICAL CONSTRAINT**: These workflows create and manage **plans only**. NEVER implement tasks directly. All task descriptions MUST result in plans - not actual implementation. After completing 1-init through 4-plan phases, check `execute_without_asking` config. If false (default): STOP and wait for execute action. If true: Auto-continue to execute phase.

## Action Routing

| Action | Workflow |
|--------|----------|
| `list` (default) | List all plans |
| `init` | Create new plan, auto-continue |
| `refine` | Clarify request until confident |
| `outline` | Run 3-outline and 4-plan phases |
| `cleanup` | Remove completed plans |
| `lessons` | List and convert lessons to plans |
| `recipe` | Create plan from recipe (routes to `workflows/recipe.md`) |

---

## Action: list (default)

Display all plans with numbered selection, recipe option, and conditional lessons.

**Step 1**: Get existing plans:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status list
```

**Step 2**: Check if lessons exist:
```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list
```
Parse `total` from output. If `total > 0`, lessons are available.

**Step 3**: Present interactive menu using `AskUserQuestion`:

Build options dynamically from Step 1 and Step 2 results:

```
AskUserQuestion:
  questions:
    - question: "Which plan would you like to work on?"
      header: "Plans"
      options:
        # For each plan from Step 1 (dynamic):
        - label: "{plan_name} [{phase}]"
          description: "{task_count} tasks - {title or summary}"
        # Always include these static options:
        - label: "Create new plan"
          description: "Start a new plan from a task description or GitHub issue"
        - label: "Create plan from recipe"
          description: "Start a new plan using a project recipe"
        # Only include if Step 2 returned total > 0:
        - label: "List lessons"
          description: "Browse lessons learned and convert to plans"
      multiSelect: false
```

- Always include "Create new plan" and "Create plan from recipe" as options
- Only include "List lessons" when Step 2 returned `total > 0`
- Maximum 4 options per `AskUserQuestion` — if plans + static options exceed 4, present plans first with a "More actions..." option, then show static options in a follow-up question

**Step 4**: Handle selection:
- **Plan selected**: Auto-detect action from plan's current phase
- **"Create new plan"**: Route to `Action: init`
- **"Create plan from recipe"**: Route to `Action: recipe` (load `workflows/recipe.md`)
- **"List lessons"**: Route to `Action: lessons`

---

## Action: init

Create a new plan and automatically continue to 2-refine/3-outline/4-plan phases.

**1-Init Phase** uses a single agent:

```
Task: plan-marshall:phase-agent
  Input: skill=plan-marshall:phase-1-init, source={source}, content={content}
  Output: plan_id, domains array
```

**Metrics**: After agent completes and `plan_id` is known, record phase metrics with token data from `<usage>` tag:
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics end-phase \
  --plan-id {plan_id} --phase 1-init \
  --total-tokens {total_tokens from <usage>} \
  --duration-ms {duration_ms from <usage>} \
  --tool-uses {tool_uses from <usage>}
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics generate \
  --plan-id {plan_id}
```

**Automatic Continuation**:
1. Check `stop-after-init` parameter
2. If true: Stop and display plan summary
3. If false (default): Continue through 2-refine, 3-outline, and 4-plan phases with the new plan_id

**2-Refine Phase**: Load refine phase skill directly (maintains main context for user interaction)

**Metrics**: Record phase start:
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics start-phase \
  --plan-id {plan_id} --phase 2-refine
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:plan-marshall) Loading plan-marshall:phase-2-refine"
```

```
Skill: plan-marshall:phase-2-refine
  Arguments: --plan-id {plan_id}
```

The skill runs in main conversation context so `AskUserQuestion` works directly with the user. Do NOT run this as a Task agent — the 12-step workflow requires too many tool calls for a subagent turn budget, and Step 9 (user clarification) needs direct user access.

**Metrics**: After refine completes, record phase end (no token data — main context):
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics end-phase \
  --plan-id {plan_id} --phase 2-refine
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics generate \
  --plan-id {plan_id}
```

Then continue to **Action: outline** with the same plan_id.

---

## Action: outline (3-Outline + 4-Plan Phases)

**CRITICAL**: This action has 4 steps. Step 3 is a user review gate controlled by `plan_without_asking` config. If false (default): MANDATORY user review — do NOT skip. If true: Auto-proceed to Step 4.

---

**Step 1**: Read domains from references:
```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} --field domains
```

---

**Step 2**: Load outline phase skill directly (maintains main context)

**Metrics**: Record phase start:
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics start-phase \
  --plan-id {plan_id} --phase 3-outline
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:plan-marshall) Loading plan-marshall:phase-3-outline"
```

```
Skill: plan-marshall:phase-3-outline
  Arguments: --plan-id {plan_id}
```

The skill runs in main conversation context and CAN spawn Task agents for parallel analysis.

Log solution outline creation:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (plan-marshall:plan-marshall) Created solution_outline.md - pending user review"
```

**Step 2b**: Q-Gate auto-loop (max 3 iterations)

Check if the phase returned Q-Gate findings. If so, auto-loop without user intervention.

```
qgate_iteration = 0
MAX_QGATE_ITERATIONS = 3

WHILE qgate_pending_count > 0 AND qgate_iteration < MAX_QGATE_ITERATIONS:
  qgate_iteration += 1
  1. Log: "(plan-marshall:plan-marshall:qgate) Auto-fix iteration {qgate_iteration}/{MAX_QGATE_ITERATIONS}: {count} findings — re-entering phase-3-outline"
  2. Re-invoke phase-3-outline skill (phase reads findings at Step 1 and addresses them)
  3. Check qgate_pending_count from phase return

IF qgate_pending_count > 0 AND qgate_iteration >= MAX_QGATE_ITERATIONS:
  → STOP: Escalate to user — "Q-Gate auto-loop exhausted after {MAX_QGATE_ITERATIONS} iterations. {count} findings remain unresolved."
  → Present remaining findings and ask user how to proceed
```

This loop runs automatically — do NOT prompt the user for Q-Gate findings unless the max iteration limit is reached. Q-Gate findings are objective quality failures that the phase must self-correct. Only proceed to Step 2c when `qgate_pending_count == 0`.

**Step 2c**: Transition phase after outline completes AND Q-Gate is clean:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition \
  --plan-id {plan_id} --completed 3-outline
```

**Metrics**: After outline completes, record phase end with aggregated token data from agents spawned during this phase (detect-change-type-agent and q-gate-validation-agent). Sum `total_tokens`, `tool_uses`, and `duration_ms` from each agent's `<usage>` tag:
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics end-phase \
  --plan-id {plan_id} --phase 3-outline \
  --total-tokens {sum of total_tokens from all agent <usage> tags} \
  --tool-uses {sum of tool_uses from all agent <usage> tags} \
  --duration-ms {sum of duration_ms from all agent <usage> tags}
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics generate \
  --plan-id {plan_id}
```

**Step 2d**: Auto-open solution outline in IDE for user review:

Resolve the solution outline path:
```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
```

Extract `{resolved_path}` from the `path` field in the command output. Open in the current IDE using `TERM_PROGRAM` env var detection:
- If `TERM_PROGRAM=vscode`: `code {resolved_path}`
- On macOS: `open {resolved_path}`
- On Linux: `xdg-open {resolved_path}`

---

## Step 3: USER REVIEW GATE

The outline presented here has already passed Q-Gate verification. The user reviews the quality-verified outline.

**Config check** — Read `plan_without_asking` to determine gate behavior:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-3-outline get --field plan_without_asking --trace-plan-id {plan_id}
```

**IF `plan_without_asking == true`**:
- Log: `"(plan-marshall:plan-marshall) Config: plan_without_asking=true — auto-proceeding to task creation"`
- Skip Steps 3a-3c, continue directly to Step 4

**ELSE (default)**: **STOP HERE. Do NOT proceed to Step 4 without user approval.**

### 3a. Read and display the solution outline for review:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline read \
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
    python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
      qgate add --plan-id {plan_id} --phase 3-outline --source user_review \
      --type triage --title "User: {feedback summary}" \
      --detail "{full feedback text}"
    ```
  - Log feedback capture:
    ```bash
    python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
      decision --plan-id {plan_id} --level INFO --message "(plan-marshall:plan-marshall) User review: {count} change requests recorded to artifacts/qgate-3-outline.jsonl"
    ```
  - Re-invoke phase-3-outline skill (phase reads Q-Gate findings at Step 1)
  - **Loop back to Step 3a**

---

**Step 4**: Create tasks from deliverables

Only execute this step AFTER user approves in Step 3.

**Metrics**: Record phase start before agent invocation:
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics start-phase \
  --plan-id {plan_id} --phase 4-plan
```

```
Task: plan-marshall:phase-agent
  Input: skill=plan-marshall:phase-4-plan, plan_id={plan_id}
  Output: tasks created with domain, profile, skills
```

**Metrics**: After agent completes, record phase end with token data from `<usage>` tag:
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics end-phase \
  --plan-id {plan_id} --phase 4-plan \
  --total-tokens {total_tokens from <usage>} \
  --duration-ms {duration_ms from <usage>} \
  --tool-uses {tool_uses from <usage>}
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics generate \
  --plan-id {plan_id}
```

Log task plan agent invocation:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:plan-marshall) Invoked phase-agent for phase-4-plan"
```

**Step 4b**: Transition phase after tasks created:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition \
  --plan-id {plan_id} --completed 4-plan
```

**Step 4c**: Check `execute_without_asking` config to determine next action:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-4-plan get --field execute_without_asking --trace-plan-id {plan_id}
```

**IF `execute_without_asking == true`**:
- Log: `"(plan-marshall:plan-marshall) Config: execute_without_asking=true — auto-continuing to execute"`
- Load `workflows/execution.md` and follow **Action: execute** with `plan_id`

**ELSE (default)**:
- Display: `"Tasks created. Ready to execute."`
- Display: `"Run '/plan-marshall action=execute plan={plan_id}' when ready."`
- **STOP** (current behavior)

---

## Action: cleanup

Remove completed plans. Shows completed plans for selective or batch deletion with confirmation.

---

## Action: lessons

List lessons learned with options to convert to plan or analyze all.

### Menu

**Step 1**: List all lessons:
```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list
```

**Step 2**: Present options using `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "What would you like to do with lessons?"
      header: "Lessons"
      options:
        # For each lesson from list (dynamic):
        - label: "[{category}] {title}"
          description: "Component: {component} — Convert to plan"
        # Always include:
        - label: "Analyze all lessons"
          description: "Review validity, find done/combinable lessons, cleanup"
        - label: "Back to main menu"
          description: "Return to plan list"
      multiSelect: false
```

### Convert lesson to plan

When a specific lesson is selected, convert it to a plan using the canonical `phase-agent` invocation with a `lesson_id` reference:

```
Task: plan-marshall:phase-agent
  Input: skill=plan-marshall:phase-1-init, lesson_id={lesson_id}
  Output: plan_id, domain
```

Passing `lesson_id` triggers `phase-1-init` Step 4 ("From Lesson") to resolve the lesson body from `lessons-learned/` and Step 5b ("Move Lesson File Into Plan Directory") to relocate the lesson file into the new plan directory via `manage-lessons convert-to-plan`. Both side effects are automatic — the caller only supplies `lesson_id`.

**Anti-pattern (prohibited):** Never invoke `phase-agent` with `skill=phase-1-init, source=lesson, content={verbatim lesson text}`. Inline `content` is the `description` source path and causes `phase-1-init` to treat the input as a free-form description — Step 5b is skipped and the original lesson file is orphaned in `lessons-learned/` instead of being archived inside the plan directory. Always reference the lesson by `lesson_id`; never paste its body.

### Analyze all lessons

When "Analyze all lessons" is selected, run the analyze workflow. This is an interactive LLM workflow — no plan is created.

**Step 1**: Get all lessons with full body content:
```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list --full
```

**Step 2**: For each lesson, verify validity against the current codebase:
- Read the component/file referenced in the lesson
- Check whether the described fix, improvement, or anti-pattern mitigation has already been implemented
- Check whether other lessons reference the same component and root cause (combination candidates)

Classify each lesson into one of three categories:
- **Close** — the fix/improvement has already landed in code
- **Merge** — two or more lessons share the same root cause and should be combined (specify target lesson)
- **Keep open** — still actionable, not yet addressed

**Step 3**: Present a single batch summary via `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: |
        ## Lessons Analysis

        ### Close (already done):
        {for each close candidate:}
        - {id}: {title} — {reasoning}

        ### Merge:
        {for each merge group:}
        - {source_id} → {target_id}: {reasoning}

        ### Keep open:
        {for each open lesson:}
        - {id}: {title}

        Proceed with these actions?
      options:
        - label: "Proceed"
          description: "Execute all proposed close and merge actions"
        - label: "Cancel"
          description: "Make no changes"
      multiSelect: false
```

**Step 4**: If user selects "Proceed", execute actions and log:

For each **close** action:
1. Delete the lesson file (it lives in `.plan/local/lessons-learned/{id}.md`)
2. Log:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO --message "(plan-marshall:lessons-analyze) Closed lesson {id}: {title} — {reasoning}"
```

For each **merge** action:
1. Read the target lesson file content
2. Append the source lesson's key content to the target lesson body
3. Update the target lesson's title if needed to reflect the broader scope
4. Delete the source lesson file
5. Log:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id global --level INFO --message "(plan-marshall:lessons-analyze) Merged lesson {source_id} into {target_id}: {reasoning}"
```

**Step 5**: Display summary of actions taken.

---

## Script API Reference

Script: `plan-marshall:manage-status:manage_status`

| Command | Parameters | Description |
|---------|------------|-------------|
| `read` | `--plan-id` | Read plan status |
| `create` | `--plan-id --title --phases [--force]` | Initialize status.json |
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
.plan/plans/{plan_id}/status.json
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
| 5-execute | `plan-execute` | Execute implementation tasks + verification |
| 6-finalize | `plan-finalize` | Finalize with commit/PR |
