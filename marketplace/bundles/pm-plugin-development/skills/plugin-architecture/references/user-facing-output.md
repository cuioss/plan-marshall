# User-Facing Output Standards

This reference defines standards for what users see during skill and command execution. The goal: progress visibility without implementation detail overload.

## Core Concept

**Show status, not process.** Users care about progress and outcomes, not internal operations.

---

## Pattern: Structured Status Output

Display progress as structured summaries with clear fields:

```
plan_status:
  current_phase: 5-execute
  current_task: task-1
  phase_completed: init

next_action: Execute analysis tasks (Task 1: Analyze component)
```

### Required Fields

| Field | Purpose |
|-------|---------|
| current_phase | Where in the workflow |
| current_task | What's being worked on |
| next_action | What happens next |

### Optional Fields

| Field | Purpose |
|-------|---------|
| completed_count | Progress indicator (e.g., "3/7") |
| artifacts | Files/outputs created |
| warnings | Non-blocking issues |

---

## Pattern: Phase Transition Messages

When transitioning between phases, output must include:

1. **Completion Summary** - What was accomplished
2. **Artifacts Created** - Files/outputs produced
3. **Current State** - Where in the workflow
4. **Next Action** - Clear direction for continuation

### Example

```
Plan created successfully:

domain: generic
artifacts:
  plan_directory: <plan-storage>/feature-auth/
  plan_file: <plan-storage>/feature-auth/plan.md
  config_file: <plan-storage>/feature-auth/config.md
plan_status:
  current_phase: 1-init
  current_task: task-1
next_action: Complete init phase, then start execute phase
```

---

## Pattern: Configuration Display

Show configuration summaries for user confirmation before proceeding:

```
## Detected Configuration

**Domain**: generic (3-phase: init->execute->finalize)
**Branch**: feature/auth-improvements
**Issue**: #123
**Build System**: maven
**Technology**: java

**Defaults Applied**:
- Compatibility: breaking
- Commit Strategy: per_deliverable
- Finalizing: commit-only

Proceed with this configuration? (yes/no)
```

---

## Pattern: Progress Tables

Use markdown tables for phase/task overview:

```markdown
| Phase | Status | Tasks | Completed |
|-------|--------|-------|-----------|
| init | completed | 2 | 2/2 |
| execute | in_progress | 5 | 1/5 |
| finalize | pending | 2 | 0/2 |
```

---

## Pattern: Issue Detection Output

When problems occur, structure output clearly with problem/fix pairing:

```
ISSUES DETECTED:

1. Type mismatch in UserService
   - Expected: String userId
   - Found: Integer user_id
   FIX: Update to use String type

2. Missing null check in processOrder()
   - Location: line 47
   FIX: Add null validation before access
```

---

## Pattern: Final Metrics Display

On completion, show measurable outcomes:

```
Completed successfully:

metrics:
- Tests passed: 47/47 OK
- Coverage: 92% (requirement: 80%) OK
- Build time: 23s OK
- Lint errors: 0 OK

artifacts:
- Created: src/auth/UserService.java
- Modified: src/config/SecurityConfig.java
- Tests: src/test/auth/UserServiceTest.java
```

---

## Anti-Patterns: What NOT to Display

### 1. Internal Step Numbers

**Bad:**
```
Step 1-2: Determine Domain
Step 3: Load Simple Init Standards
Step 6: Present Configuration
Steps 7-10: Create Plan Structure
```

**Good:**
```
Analyzing task requirements...
Configuration ready for review.
```

### 2. Skill Loading Messages

**Bad:**
```
> The "plan-init" skill is loading
  Allowed 5 tools for this command
> The "plan-files" skill is loading
  Allowed 5 tools for this command
```

**Good:**
(No output - skill loading is internal)

### 3. Tool Execution Details

**Bad:**
```
Bash(test -d <plan-storage>/analyze-task/ && echo "exists" || echo "not-exists")
  not-exists
Bash(mkdir -p <plan-storage>/analyze-task/)
  (No content)
Write(<plan-storage>/analyze-task/config.md)
  Wrote 36 lines to <plan-storage>/analyze-task/config.md
```

**Good:**
```
Created plan directory: <plan-storage>/analyze-task/
```

### 4. Line-by-Line Edit Diffs

**Bad:**
```
Update(<plan-storage>/analyze-task/plan.md)
  Updated with 2 additions and 2 removals
    33    **Checklist**:
    34    - [x] Check current git branch
    35    - [x] Understand task scope
    36 -  - [ ] Identify files to analyze
    36 +  - [x] Identify files to analyze
```

**Good:**
```
Updated plan: marked "Identify files to analyze" complete
```

Or simply:
```
Phase transition: init -> execute
```

### 5. Operation Labels

**Bad:**
```
Operation: create-directory
Operation: write-config
Operation: write-plan
Operation: write-references
```

**Good:**
```
Plan files created.
```

### 6. Internal Script Paths

**Bad:**
```
Bash(python3 {discover-plans.py} <plan-storage>/)
```

**Good:**
```
Scanning for existing plans...
```

---

## Output Filtering Rules

### MUST Display

- Final status/outcome
- User decision points (confirmations)
- Errors requiring user action
- Created/modified artifacts (summarized)
- Next action guidance

### MUST NOT Display

- Internal step numbers
- Skill/tool loading messages
- Tool permission grants
- Raw bash/script commands
- Line-by-line file diffs
- Operation labels
- Internal file paths

### MAY Display (Context Dependent)

- Progress indicators for long operations
- Intermediate status for multi-phase work
- Warnings that don't block progress

---

## Output by Component Type

### Commands

Commands are thin orchestrators - minimal output:

```
Routing to quality workflow...

[skill output appears here]

Complete. Use /next-command to continue.
```

### Skills

Skills produce structured output per workflow:

| Workflow Type | Output Focus |
|---------------|--------------|
| init | Configuration summary + artifact locations |
| analyze | Findings summary + issue count |
| fix | Changes made + verification status |
| verify | Pass/fail status + metrics |
| finalize | Completion summary + deliverables |

### Agents

Agents coordinate skills - output is aggregated status:

```
Analysis complete:
- Files scanned: 47
- Issues found: 3
- Auto-fixed: 2
- Manual review: 1

See details: <plan-storage>/reports/analysis.md
```

---

## Implementation Checklist

When designing user-facing output:

- [ ] Status uses structured format (key: value)
- [ ] Phase transitions include all 4 required elements
- [ ] Configurations displayed before proceeding
- [ ] Progress shown via tables for multi-item work
- [ ] Issues paired with fixes
- [ ] Final output includes measurable outcomes
- [ ] No internal step numbers visible
- [ ] No skill loading messages visible
- [ ] No raw tool commands visible
- [ ] No line-by-line diffs visible
- [ ] Next action always clear

---

---

## Technical Implementation: Status Blocks

The mechanism for user-facing output is **structured status blocks** - YAML-like formatted text that provides scannable, consistent information.

### Status Block Format

```
<status_type>:
  <key>: <value>
  <key>: <value>

<next_element>: <description>
```

### Core Status Block Types

#### 1. Plan Status Block

Used after plan operations (create, transition, complete):

```
plan_status:
  current_phase: 5-execute
  current_task: task-1
  init_completed: true

next_action: Execute analysis tasks (Task 1: Analyze component)
```

#### 2. Completion Block

Used when a phase or task completes:

```
Phase completed: init

artifacts:
  plan_directory: <plan-storage>/feature-auth/
  plan_file: <plan-storage>/feature-auth/plan.md
  config_file: <plan-storage>/feature-auth/config.md

plan_status:
  current_phase: 5-execute
  current_task: task-1

next_action: Begin execute phase
```

#### 3. Creation Block

Used when artifacts are created:

```
Plan created successfully:

domain: generic
artifacts:
  plan_directory: <plan-storage>/feature-auth/
  plan_file: <plan-storage>/feature-auth/plan.md
  config_file: <plan-storage>/feature-auth/config.toon
  references_file: <plan-storage>/feature-auth/references.toon

plan_status:
  current_phase: 1-init
  current_task: task-1

next_action: Complete init phase, then start execute phase
```

#### 4. Metrics Block

Used for verification/completion results:

```
Verification complete:

metrics:
  tests_passed: 47/47
  coverage: 92%
  build_time: 23s
  lint_errors: 0

status: all_passed
next_action: Ready for finalize phase
```

#### 5. Error Block

Used when errors require user action:

```
ERROR: Build failed

details:
  type: compilation_error
  file: src/auth/UserService.java
  line: 47
  message: Cannot resolve symbol 'UserRepository'

action_required: Fix import or add dependency
```

### Status Block Rules

1. **Top-level key ends with colon** - `plan_status:`, `artifacts:`, `metrics:`
2. **Nested values indented 2 spaces** - consistent YAML-like structure
3. **Blank line between blocks** - visual separation
4. **`next_action:` always last** - tells user what happens next
5. **No prose between blocks** - pure structured data

### What Goes IN Status Blocks

| Include | Example |
|---------|---------|
| Current state | `current_phase: 5-execute` |
| Completed items | `tasks_completed: 3/5` |
| Created artifacts | `plan_file: <plan-storage>/x/plan.md` |
| Measurable outcomes | `coverage: 92%` |
| Next action | `next_action: Run verification` |
| Errors needing action | `ERROR: Build failed` |

### What Stays OUT of Status Blocks

| Exclude | Why |
|---------|-----|
| Tool commands | Internal process |
| Step numbers | Internal process |
| File diffs | Too verbose |
| Script paths | Internal detail |
| Skill loading | Internal process |
| Intermediate results | Only final matters |

### Skill Implementation

In SKILL.md, define output templates using status blocks:

```markdown
## Output Format

On phase completion, output:
​```
Phase completed: {phase_name}

artifacts:
  - {file_1}
  - {file_2}

plan_status:
  current_phase: {next_phase}
  current_task: task-1

next_action: {description}
​```

Work silently during execution. Do not output tool usage or intermediate steps.
```

---

## Summary

**Principle**: Users need to know WHAT happened and WHAT'S NEXT, not HOW it happened internally.

**Test**: If output looks like a debug log, it's wrong. If output looks like a status report, it's right.

**Implementation**: Output filtering is achieved through prompt design - explicit instructions in SKILL.md telling Claude what to display vs suppress.
