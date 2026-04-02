---
name: manage-tasks
description: Manage implementation tasks with sequential sub-steps within a plan
user-invocable: false
scope: plan
---

# Manage Tasks Skill

Manage implementation tasks with sequential sub-steps within a plan. Each task references deliverables from the solution document and contains ordered steps for execution.

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse TOON output for status and route accordingly.

**Prohibited actions:**
- Do not modify TASK-*.json files directly; all mutations go through the script API
- Do not invent script arguments not listed in the Operations table
- Do not bypass dependency checking unless explicitly using `--ignore-deps`

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks {command} {args}`
- Task numbering is sequential and immutable (TASK-001, TASK-002, etc.)
- The `add` command reads TOON content from `--content` argument with `\n` encoding
- Step finalization requires explicit `--outcome` (done or skipped)

## What This Skill Provides

- Individual JSON file storage for each task (TOON output for LLM efficiency)
- Sequential, immutable numbering (TASK-1, TASK-2, etc.)
- Deliverable references (M:N relationship to solution_outline.md)
- Delegation context (skill + workflow for execution)
- Verification commands and criteria
- Step management with status tracking
- Simple execution loop via `next` query

## When to Activate This Skill

Activate this skill when:
- Creating or managing implementation tasks for a plan
- Querying next actionable task/step
- Marking steps as started/completed/skipped
- Tracking implementation progress

---

## Storage Location

Tasks are stored in the plan directory:

```
{plan_dir}/tasks/
  TASK-001.json
  TASK-002.json
  TASK-003.json
```

**Filename format**: `TASK-{NNN}.json` (task type is stored in the JSON `type` field)

---

## File Format (Summary)

Tasks are stored as JSON and output as TOON (LLM-optimized):

```json
{
  "number": 1,
  "title": "Update misc agents to TOON output",
  "status": "pending",
  "domain": "plan-marshall-plugin-dev",
  "profile": "implementation",
  "origin": "plan",
  "skills": [
    "pm-plugin-development:plugin-maintain",
    "pm-plugin-development:plugin-architecture"
  ],
  "deliverable": 1,
  "depends_on": [],
  "description": "Migrate miscellaneous agents from JSON to TOON output format.",
  "steps": [
    {"number": 1, "target": "pm-plugin-development/agents/tool-coverage-agent.md", "status": "pending"},
    {"number": 2, "target": "pm-dev-builder/agents/gradle-builder.md", "status": "pending"},
    {"number": 3, "target": "pm-dev-frontend/skills/javascript/SKILL.md", "status": "pending"}
  ],
  "verification": {
    "commands": ["grep -L '```json' {files} | wc -l"],
    "criteria": "No JSON blocks remain",
    "manual": false
  },
  "current_step": 1
}
```

**New Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `domain` | string | Task domain (arbitrary string, e.g., java, javascript, my-domain) |
| `profile` | string | Task profile (e.g., `implementation`, `module_testing`) |
| `skills` | list | Pre-resolved skills for task execution |
| `origin` | string | Task origin: `plan`, `fix`, `sonar`, `pr`, `lint`, `security`, or `documentation` |

---

## Operations

Script: `plan-marshall:manage-tasks:manage-tasks`

| Command | Parameters | Description |
|---------|------------|-------------|
| `add` | `--plan-id --content` | Add a new task (TOON in --content with \n encoding) |
| `update` | `--plan-id --number [--title] [--description] [--depends-on] [--status] [--domain] [--profile] [--skills] [--deliverable]` | Update task metadata |
| `remove` | `--plan-id --number` | Remove a task |
| `list` | `--plan-id [--status] [--deliverable] [--ready]` | List all tasks |
| `get` | `--plan-id --number` | Get single task details |
| `next` | `--plan-id [--include-context] [--ignore-deps]` | Get next pending task/step |
| `tasks-by-domain` | `--plan-id --domain` | List tasks filtered by domain |
| `tasks-by-profile` | `--plan-id --profile` | List tasks filtered by profile |
| `next-tasks` | `--plan-id` | Get all tasks ready for parallel execution |
| `finalize-step` | `--plan-id --task --step --outcome [--reason]` | Complete step with outcome (done/skipped) |
| `add-step` | `--plan-id --task --target [--after]` | Add step to task |
| `remove-step` | `--plan-id --task --step` | Remove step from task |

### Add Command (--content CLI argument)

The `add` command reads the task definition from the `--content` CLI argument in TOON format. Newlines are encoded as literal `\n` (two characters) which Python decodes at runtime. This keeps the entire command on a single line, matching the `Bash(python3 .plan/execute-script.py *)` permission pattern.

**Content format**:

```toon
title: My Task Title
deliverable: 1
domain: plan-marshall-plugin-dev
profile: implementation
origin: plan
description: |
  Multi-line task description here.
  Can include any characters.

skills:
  - pm-plugin-development:plugin-maintain
  - pm-plugin-development:plugin-architecture

steps:
  - First step to execute
  - Second step to execute
  - Third step to execute

depends_on: none

verification:
  commands:
    - grep -l '```json' marketplace/bundles/*.md | wc -l
    - mvn verify
  criteria: All grep commands return 0 (no JSON blocks remain)
  manual: false
```

**Required fields**: `title`, `deliverable`, `domain`, `profile`, `skills`, `steps`

**Optional fields**: `description`, `depends_on`, `verification`, `origin` (default: plan)

**Field values**:
- `deliverable`: Single positive integer (one deliverable per task, 1:1 constraint)
- `domain`: Domain from references.json (e.g., `java`, `javascript`, `plan-marshall-plugin-dev`)
- `profile`: Profile key from marshal.json. Standard profiles: `implementation`, `module_testing`, `integration_testing`, `quality`, `verification`, `standalone`
- `skills`: Array of `bundle:skill` format strings
- `depends_on`: `none` or task references like `TASK-1, TASK-2`
- `origin`: `plan` (from task-plan), `fix` (from verify), `sonar`, `pr`, `lint`, `security`, or `documentation`

### List/Next Filters

| Parameter | Description |
|-----------|-------------|
| `--deliverable` | Filter by deliverable number |
| `--ready` | Only tasks with satisfied dependencies |
| `--ignore-deps` | (next only) Ignore dependency constraints |

---

## Quick Examples

### Add a task

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks add \
  --plan-id my-feature \
  --content "title: Update misc agents to TOON\ndeliverable: 1\ndomain: java\ndescription: Migrate miscellaneous agents from JSON to TOON output format.\nsteps:\n  - file1.md\n  - file2.md\n  - file3.md\nverification:\n  commands:\n    - mvn verify\n  criteria: Build passes"
```

### Add a task with dependencies

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks add \
  --plan-id my-feature \
  --content "title: Write integration tests\ndeliverable: 3\ndomain: java-testing\ndescription: Add integration tests for new endpoint\nsteps:\n  - Create test class\n  - Add test methods\n  - Run tests\ndepends_on: TASK-1, TASK-2\nverification:\n  commands:\n    - mvn verify -Pintegration\n  criteria: All tests pass"
```

### Add a task with complex verification commands

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks add \
  --plan-id migrate-json-to-toon \
  --content "title: Migrate skill outputs to TOON\ndeliverable: 1\ndomain: plan-marshall-plugin-dev\ndescription: Update skills to use TOON format instead of JSON.\nsteps:\n  - Update recipe-doc-verify SKILL.md\nverification:\n  commands:\n    - grep -l '```json' marketplace/bundles/pm-documents/skills/recipe-doc-verify/*.md | wc -l\n  criteria: All grep commands return 0 (no JSON blocks remain)"
```

### Get next task/step (respects dependencies)

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks next \
  --plan-id my-feature
```

### List ready tasks only

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list \
  --plan-id my-feature \
  --ready
```

### Finalize step (mark done or skipped)

```bash
# Mark step as done
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id my-feature \
  --task 2 \
  --step 3 \
  --outcome done

# Skip step with reason
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id my-feature \
  --task 2 \
  --step 3 \
  --outcome skipped \
  --reason "File already exists"
```

---

## Integration Points

### With phase-agent (phase-4-plan)

Task-plan agents create tasks during plan refinement using `--content`:
```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks add \
  --plan-id {plan_id} \
  --content "title: {task_title}\ndeliverable: {deliverable_number}\ndomain: {domain}\nsteps:\n  - {step1}\n  - {step2}\ndepends_on: none"
```

### With plan-execute

Plan-execute iterates through tasks:
```
LOOP:
  1. manage-tasks next --plan-id {plan_id}
  2. IF no next: DONE
  3. SPAWN implement agent
  4. CONTINUE
```

### With implement-agent

Implement agents execute steps:
```
1. manage-tasks get --plan-id {plan_id} --number {N}
2. FOR EACH step: execute → finalize-step --outcome done
3. RUN verification
```

---

## Deliverable-to-Task Relationship

Tasks reference deliverables from `solution_outline.md` using the `deliverable` field in stdin.

**Constraint**: Each task maps to exactly **one** deliverable (the `deliverable` field is a single integer, not a list). However, one deliverable can produce multiple tasks.

| Pattern | Description | Example |
|---------|-------------|---------|
| Simple | One task per deliverable | TASK-1 has `deliverable: 1`, TASK-2 has `deliverable: 2` |
| Multi-profile | One deliverable, multiple tasks | TASK-1 (implementation) and TASK-2 (module_testing) both have `deliverable: 1` |

**Multi-profile pattern**: When a deliverable needs both implementation and testing, phase-4-plan creates separate tasks per profile. Each task gets its own skill set and executor.

---

## Dependency Management

Tasks can depend on other tasks using the `depends_on` field in stdin:

```yaml
# Task 3 waits for Task 1 and Task 2 to complete
depends_on: TASK-1, TASK-2

# No dependencies
depends_on: none
```

**Dependency enforcement**:
- `next` command only returns tasks with satisfied dependencies
- Use `--ignore-deps` to bypass dependency checking
- Use `--ready` filter to list only ready tasks

**Blocked output**: When tasks are blocked by dependencies, `next` returns:

```toon
next: null
blocked_tasks[2]{number,title,waiting_for}:
1,Write tests,TASK-3
2,Deploy,TASK-3, TASK-4
```

---

## Status Model

**Task Status**: `pending` → `in_progress` → `done` (or `blocked`)

**Step Status**: `pending` → `in_progress` → `done` (or `skipped`)

---

## Verification

The `verification` field is optional. When present:
- `commands`: List of shell commands to run after implementation (copied verbatim from deliverable's Verification field by phase-4-plan)
- `criteria`: Human-readable success criteria
- `manual`: If `true`, verification requires human judgment (automated commands may still run but results need review)

If a deliverable has no Verification section, the task is created without `verification`.

---

## Error Responses

All errors return TOON with `status: error` and exit code 1.

| Error Code | Cause |
|------------|-------|
| `invalid_plan_id` | plan_id format invalid |
| `task_not_found` | Task number doesn't exist |
| `step_not_found` | Step number doesn't exist in task |
| `invalid_content` | TOON content parsing failed or missing required fields |
| `missing_required` | Required field missing (title, deliverable, domain, profile, skills, steps) |
| `circular_dependency` | Task dependency creates a cycle (detected during `next`) |
| `invalid_outcome` | Step outcome not `done` or `skipped` |
| `plan_dir_not_found` | Plan directory doesn't exist |

```toon
status: error
plan_id: my-feature
error: task_not_found
number: 99
message: Task TASK-99 not found
```

---

