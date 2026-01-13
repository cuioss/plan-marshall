# Plan Execute Workflow

## Execution Pattern

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DUMB TASK RUNNER                                    │
│                                                                          │
│      ┌──────────────────────────────────────────────────────────┐       │
│      │                                                          │       │
│      │  1. LOCATE    →  Find current task via manage-tasks      │       │
│      │       │                                                  │       │
│      │       ▼                                                  │       │
│      │  2. EXECUTE   →  Run checklist items (delegate as       │       │
│      │       │           specified in item text)                │       │
│      │       ▼                                                  │       │
│      │  3. UPDATE    →  Mark items [x], call update-progress   │       │
│      │       │                                                  │       │
│      │       ▼                                                  │       │
│      │  4. NEXT      →  Move to next task or phase             │       │
│      │                                                          │       │
│      └──────────────────────────────────────────────────────────┘       │
│                                                                          │
│  NO BUSINESS LOGIC - just sequential execution of checklists.            │
└─────────────────────────────────────────────────────────────────────────┘
```

## Phases Handled

| Phase | Typical Tasks |
|-------|---------------|
| execute | Code implementation, test creation, build verification |
| finalize | Quality checks, commit, PR creation, completion |

## Task Execution

### Reading Tasks

```
Skill: pm-workflow:manage-tasks
operation: next
plan_id: {plan_id}

Returns next task with status pending or in_progress
```

### Executing Checklist Items

For each `- [ ]` item:
1. **Parse** - Understand what action is needed
2. **Delegate** - If item specifies agent/skill/command, invoke it
3. **Execute** - Perform the action
4. **Update** - Mark item `[x]` via manage-tasks script

### Progress Update

After each step completion:
```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks step-done \
  --plan-id {plan_id} \
  --task {task_number} \
  --step {step_number}
```

## Phase Transition

When all tasks in phase complete:

1. **Automatic file collection** (execute phase):
   - `manage-lifecycle transition` collects modified files
   - Updates `references.toon` with changed files
   ```bash
   python3 .plan/execute-script.py pm-workflow:manage-lifecycle:manage-lifecycle transition --plan-id {plan_id} --completed {phase}
   ```

2. **Auto-transition** to next phase:
   - execute → finalize
   - finalize → complete

3. **No user prompt** for transitions (continuous execution)

## Auto-Continue Rules

**Continue without prompting**:
- Task completion
- Phase transition
- Routine operations

**Stop and prompt when**:
- Error blocks progress
- Multiple valid approaches exist
- User explicitly requested confirmation

## Pre-Implemented Work

Before executing, check if deliverables already exist:
1. Verify files/components exist
2. Check acceptance criteria met
3. If pre-implemented: Still mark progress, then skip to next task
