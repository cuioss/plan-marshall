---
name: phase-execute-implementation
description: Domain-agnostic implementation task execution with two-tier skill loading
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Phase Execute Implementation Skill

**Role**: Domain-agnostic workflow skill for executing implementation tasks (profile=implementation). Loaded by `pm-workflow:task-execute-agent` when `task.profile` is `implementation`.

**Key Pattern**: Agent loads this skill via `resolve-workflow-skill --domain {domain} --phase implementation`. Skill executes a generic workflow: understand context → plan → implement → verify. Domain-specific knowledge comes from `task.skills` (loaded by agent).

## Contract Compliance

**MANDATORY**: Follow the execution contract defined in:

| Contract | Location | Purpose |
|----------|----------|---------|
| Task Execution Skill Contract | `pm-workflow:plan-wf-skill-api/standards/phase-execute-contract.md` | Skill responsibilities |
| Task Contract | `pm-workflow:manage-tasks/standards/task-contract.md` | Task structure |

## Two-Tier Skill Loading

See [pm-workflow-architecture:skill-loading](../pm-workflow-architecture/standards/skill-loading.md) for the complete two-tier skill loading pattern with visual diagrams.

**Summary**: Agent loads Tier 1 (system skills) automatically, then Tier 2 (domain skills from `task.skills`). This workflow skill defines HOW the agent executes.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `task_number` | number | Yes | Task number to execute |

## Output

```toon
status: success | error
plan_id: {echo}
task_number: {echo}
execution_summary:
  steps_completed: N
  steps_total: M
  files_modified: [paths]
verification:
  passed: true | false
  command: "{cmd}"
next_action: task_complete | requires_attention
message: {error message if status=error}
```

## Workflow

### Step 1: Load Task Context

Read the task file to understand what needs to be done:

```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks get \
  --plan-id {plan_id} \
  --task-number {task_number}
```

Extract key fields:
- `domain`: Domain for this task
- `profile`: Should be `implementation`
- `skills`: Domain skills to apply (already loaded by agent)
- `description`: What to implement
- `steps`: File paths to work on
- `verification`: How to verify success
- `depends_on`: Dependencies (should be complete)

### Step 2: Understand Context

Before implementing, understand the codebase context:

**Read affected files** (from steps):
```bash
# For each step (file path)
Read {step.title}  # If file exists
```

**Read related files**:
```bash
# Find related components
Grep "{component_name}" --type {language}
Glob {pattern}
Read {related_file}
```

**Apply domain knowledge**:
- Reference patterns from loaded domain skills
- Understand project conventions
- Identify dependencies and integration points

### Step 3: Plan Implementation

For each step (file path), determine:
- What changes are needed
- How to apply domain skill patterns
- Order of modifications
- Integration considerations

**Mark step as in-progress**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks update-step \
  --plan-id {plan_id} \
  --task-number {task_number} \
  --step-number {N} \
  --status in_progress
```

### Step 4: Implement Changes

For each step (file path):

**Create new file**:
```bash
Write {file_path}
# Apply patterns from domain skills
# Follow project conventions
```

**Modify existing file**:
```bash
Edit {file_path}
# Apply changes following domain skill patterns
# Maintain existing code style
```

**Apply domain patterns**:
- Use patterns from loaded skills (java-core, javascript-core, etc.)
- Follow CDI/injection patterns if applicable
- Add proper logging, error handling
- Include documentation comments

### Step 5: Mark Step Complete

After each step:
```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks update-step \
  --plan-id {plan_id} \
  --task-number {task_number} \
  --step-number {N} \
  --status completed
```

### Step 6: Run Verification

After all steps complete, run task verification:

```bash
# Execute verification commands from task
{verification.commands[0]}
{verification.commands[1]}
...
```

**Verification patterns by domain**:
- Java: `mvn test -pl {module}` or `./gradlew test`
- JavaScript: `npm test` or `npm run build`
- General: Domain-specific commands from task

### Step 7: Handle Verification Results

**If verification passes**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks update \
  --plan-id {plan_id} \
  --task-number {task_number} \
  --status completed
```

**If verification fails**:
1. Analyze error output
2. Identify failing component
3. Fix the issue
4. Re-run verification
5. Iterate until pass (max 3 iterations)

If still failing after 3 iterations:
```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks update \
  --plan-id {plan_id} \
  --task-number {task_number} \
  --status blocked \
  --notes "Verification failing after 3 attempts: {error summary}"
```

### Step 8: Record Lessons

On issues or unexpected patterns:
```bash
python3 .plan/execute-script.py plan-marshall:lessons-learned:manage-lesson add \
  --component-type skill \
  --component-name task-implementation \
  --category observation \
  --title "{issue summary}" \
  --detail "{context and resolution}"
```

### Step 9: Return Results

```toon
status: success
plan_id: {plan_id}
task_number: {task_number}
execution_summary:
  steps_completed: {N}
  steps_total: {M}
  files_modified:
    - {path1}
    - {path2}
verification:
  passed: true
  command: "{verification command}"
next_action: task_complete
```

## Implementation Patterns

### File Creation Pattern

```
1. Determine target path from step
2. Check if parent directory exists
3. Create file with proper structure
4. Apply domain patterns:
   - Package/module declaration
   - Imports/dependencies
   - Class/function structure
   - Documentation
5. Format according to project style
```

### File Modification Pattern

```
1. Read existing file
2. Identify modification points
3. Apply changes using Edit tool
4. Preserve existing style
5. Update related components if needed
6. Update documentation if needed
```

### Verification Iteration Pattern

```
1. Run verification command
2. If pass → complete
3. If fail → analyze output
4. Identify failing assertion/error
5. Fix specific issue
6. Re-run verification
7. Repeat (max 3 times)
8. If still failing → block task
```

## Error Handling

### Missing Dependency

If a file depends on code not yet implemented:
- Check if dependency is in later step
- If yes, reorder steps
- If no, create minimal stub and note

### Verification Timeout

If verification command hangs:
- Kill after 5 minutes
- Record timeout in notes
- Try with reduced scope

### Conflicting Changes

If changes conflict with existing code:
- Analyze conflict
- Prefer preserving existing behavior
- Ask for clarification if needed

## Integration

**Invoked by**: `pm-workflow:task-execute-agent` (when task.profile = implementation)

**Skill Loading**: Agent loads this skill from `config.workflow_skills.{domain}.implementation`

**Script Notations** (use EXACTLY as shown):
- `pm-workflow:manage-tasks:manage-tasks` - Task operations (get, update, update-step)
- `plan-marshall:lessons-learned:manage-lesson` - Record lessons (add)

**Domain Skills Applied** (loaded by agent from task.skills):
- Java: `pm-dev-java:java-core`, `pm-dev-java:java-cdi`, etc.
- JavaScript: `pm-dev-frontend:cui-javascript`, etc.
- Apply patterns from whatever domain skills are listed in task.skills
