---
name: task-implement
description: Implement GitHub issues or standalone tasks with full verification
allowed-tools: Skill, Read, Write, Edit, Glob, Grep, Bash, Task, AskUserQuestion, SlashCommand
---

# Task Implementation Command

Implement tasks through goal-based workflow with automatic mode selection and verification.

## CONTINUOUS IMPROVEMENT RULE

Record improvements: `Skill: plan-marshall:manage-lessons` with component `{type: "command", name: "task-implement", bundle: "pm-workflow"}`

## PARAMETERS

- **task** (required): GitHub issue number/URL or task description
- **language** (optional): java|javascript (auto-detects if not specified)
- **quick** (optional): Skip review/plan, execute directly (default: false)
- **push** (optional): Auto-push after successful implementation (default: false)
- **handoff** (optional): Handoff structure from previous task (JSON)

## PREREQUISITES

Load required skills:
```
Skill: pm-workflow:cui-task-planning
Skill: pm-workflow:workflow-patterns
Skill: plan-marshall:manage-memories
```

## WORKFLOW

### Step 0: Process Handoff Input

If `handoff` parameter provided: Parse JSON, extract artifacts/decisions/constraints, load memory refs.

### Step 1: Determine Mode

```
If task matches /^\d+$/ or "github.com/*/issues/" → FULL mode (Review → Plan → Execute)
If quick=true → QUICK mode (Execute only)
Otherwise → PLAN mode (Plan → Execute)
```

### Step 2: Check Memory for Pending Workflow

```bash
python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory list --category handoffs
```
If pending found: Prompt "[R]esume / [S]tart fresh / [A]bort"

### Step 3: Execute Mode-Specific Workflow

**FULL**: Load issue (`gh issue view`), Review (cui-task-planning), Plan (cui-task-planning), Execute tasks, save progress to memory.

**PLAN**: Plan (cui-task-planning), Execute tasks, save progress to memory.

**QUICK**: Execute task directly (cui-task-planning).

### Step 4: Verify Implementation

Auto-detect language: `pom.xml` → Java, `package.json` → JavaScript

Run `SlashCommand(/pm-dev-builder:maven-build-and-fix)`. Iterate up to 3 times if fails.

### Step 5: Commit and Push

If verification succeeds: Commit via `git-workflow` skill (Commit workflow).

If push=true: Run `git push`.

### Step 6: Cleanup and Return Handoff

Cleanup memory: `python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory cleanup --category handoffs --pattern "workflow-*"`

Return structured result with handoff using `workflow-patterns/templates/handoff-standard.json` format.

## USAGE EXAMPLES

**Full workflow with GitHub issue:**
```
/task-implement task=123
```

**Quick execution (no planning):**
```
/task-implement task="Add validation to User.java" quick
```

**Java task with auto-push:**
```
/task-implement task=456 language=java push
```

**Task description with pm-workflow:**
```
/task-implement task="Implement user authentication service"
```

## ARCHITECTURE

Delegates to skills:
```
/task-implement (orchestrator)
  ├─> cui-task-planning skill (Review/Plan/Execute workflows)
  ├─> workflow-patterns skill (handoff protocols)
  ├─> manage-memories skill (state persistence)
  └─> SlashCommand(/maven-build-and-fix) [verification]
```

## RELATED

- **cui-task-planning** skill - Review, Plan, Execute workflows
- **workflow-patterns** skill - Handoff protocols and templates
- **manage-memories** skill - State persistence for recovery
- `/pr-doctor` command - Fix PR issues after implementation
