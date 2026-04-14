---
name: verification-mode
description: Verification mode that stops and analyzes on failures, workarounds, or resolution issues
user-invocable: false
---

# Verification Skill

When this skill is loaded, you are in VERIFICATION MODE. This modifies your behavior for ALL subsequent operations. You MUST follow the verification protocols below.

Verification mode ensures quality by stopping execution on any failure, workaround, or resolution issue to perform root cause analysis before proceeding.

## CRITICAL: Process vs Data Priority

**Verification mode exists to validate and fix the PROCESS — never the data it produces.**

Plans, tasks, outlines, status files — these are all **outputs** of the process. They are symptoms, not causes. When something is wrong with an output, the bug is in the component (skill, agent, command, script) that produced it.

| Aspect | Normal Mode | Verification Mode |
|--------|-------------|-------------------|
| **Priority** | Complete the task | Validate the process |
| **On error** | Fix the data/result, continue | Fix the PROCESS (agent/skill/command) |
| **Success metric** | Task completed | Process works correctly |
| **Retry behavior** | Acceptable if result correct | STOP - investigate why retry was needed |
| **Fix target** | Output files (`.plan/plans/**`) | Source components (`marketplace/bundles/**`) |

### The Fix-Target Gate (Mandatory)

Before proposing ANY fix, you MUST pass this gate:

```
┌─────────────────────────────────────────────────┐
│  DOES MY PROPOSED FIX MODIFY FILES UNDER:       │
│                                                  │
│    .plan/plans/**    → STOP. This is data.       │
│    .plan/logs/**     → STOP. This is data.       │
│    .plan/temp/**     → STOP. This is data.       │
│                                                  │
│  THE ONLY VALID FIX TARGETS ARE:                 │
│                                                  │
│    marketplace/bundles/**/skills/**              │
│    marketplace/bundles/**/agents/**              │
│    marketplace/bundles/**/commands/**            │
│    marketplace/bundles/**/scripts/**             │
│    .plan/execute-script.py                       │
│                                                  │
│  If your fix targets data → trace back to the    │
│  component that PRODUCED the bad data and fix    │
│  THAT instead.                                   │
└─────────────────────────────────────────────────┘
```

**Apply this gate at every decision point.** If you catch yourself about to edit, recreate, or patch a plan file — stop, trace the data back to its source component, and fix the component.

### Trace-Back Protocol

When bad data is found, trace it to its source:

1. **Identify the bad output** — Which file has wrong content? What's wrong with it?
2. **Find the producer** — Which script/agent/skill created or last modified this file? Check the script-execution log and work-log.
3. **Read the producer's source** — Open the SKILL.md, agent.md, or script that produced the output.
4. **Locate the defect** — Find the instruction, template, logic, or validation that allowed the bad output.
5. **Fix the producer** — Edit the component source so it produces correct output.
6. **Re-run the process** — Let the fixed component regenerate the data naturally.

Never shortcut this by editing the output directly — that leaves the broken component in place to produce bad data again on the next run.

For detailed wrong-vs-right examples, see `references/fix-target-examples.md`.

### The Core Question

When an error occurs, always ask:

> "Which COMPONENT (agent, skill, command, script) in `marketplace/bundles/` caused this, and how do I fix IT?"

Never ask:

> "How do I fix the data so I can continue?"

## What This Skill Provides

- **Failure Detection** - Stop on script failures, tool errors, or unexpected outputs
- **Resolution Analysis** - Stop when resolving paths, references, or dependencies fails
- **Workaround Detection** - Stop when using alternative approaches instead of intended methods
- **Root Cause Analysis** - Structured analysis of what failed and why
- **User Presentation** - Clear presentation of findings before proceeding

## When to Activate This Skill

Activate this skill when:
- **Testing new workflows** - Verifying skills, commands, or agents work correctly
- **Debugging issues** - Finding root causes of failures
- **Quality assurance** - Ensuring scripts and tools function as documented
- **Integration testing** - Verifying component interactions

## Activation Scopes

The skill supports different verification scopes via the `scope` parameter:

### Base Verification (default)

```
Skill: pm-plugin-development:verification-mode
```

Applies: Script failures, resolution failures, workaround detection

### Planning Verification

```
Skill: pm-plugin-development:verification-mode
scope: planning
```

Applies: All base checks PLUS:
- No direct .plan file access (must use manage-* scripts)
- Work-log population after each operation
- Status consistency after phase transitions
- **Post-Phase Verification Protocol (4 steps) after EVERY phase completes**
- **Workflow Skill API Contract Verification (Step 3) is MANDATORY**

Use this scope when testing `/plan-marshall` or any planning-related skills.

**CRITICAL**: After each phase completes, you MUST execute ALL 4 steps of the Post-Phase Verification Protocol, including verifying artifacts against workflow skill API contracts. See "After Each Phase Completes" section below.

## Verification Mode Behavior

**CRITICAL**: When this skill is loaded, you MUST modify your behavior as follows:

### On Script Failure

When any script returns non-zero exit code or produces error output:

1. **STOP** - Do not continue with the workflow
2. **ANALYZE** - Perform failure analysis (see standards/failure-analysis.md)
3. **PRESENT** - Show analysis to user with structured format
4. **WAIT** - Ask user how to proceed before continuing

### On Resolution Failure

When resolving paths, skill references, or dependencies fails:

1. **STOP** - Do not use fallback or alternative paths
2. **ANALYZE** - Perform resolution analysis (see standards/resolution-analysis.md)
3. **PRESENT** - Show what failed to resolve and why
4. **WAIT** - Ask user for guidance before proceeding

### On Workaround Usage

When you would use an alternative approach instead of the documented method:

1. **STOP** - Do not silently use the workaround
2. **DETECT** - Recognize you are about to use a workaround
3. **ANALYZE** - Explain why the intended method failed
4. **PRESENT** - Show both intended method and workaround
5. **WAIT** - Ask user to approve workaround or fix the issue

## Analysis Output Format

All analyses MUST use this structured format:

```
## [TYPE] Analysis Required

### Issue Detected
[Clear description of what triggered the stop]

### Context
- **Operation**: [What was being attempted]
- **Component**: [Which script/skill/command]
- **Expected**: [What should have happened]
- **Actual**: [What actually happened]

### Root Cause Analysis
[Analysis of why this occurred]

### Source Component (Mandatory)
- **Component**: [Full path to the skill/agent/command/script that caused the issue]
- **Defect location**: [Specific section, line, or logic in the component]
- **Fix-Target Gate**: [PASS: fix targets marketplace/bundles/** | FAIL: fix targets .plan/** — if FAIL, redo analysis]

### Impact Assessment
| Aspect | Impact |
|--------|--------|
| Blocking | Yes/No |
| Data Loss Risk | Yes/No |
| Workaround Available | Yes/No |

### Options
1. [Option 1 — must target a process component, not data]
2. [Option 2 — must target a process component, not data]
3. [Option 3 — must target a process component, not data]

### Recommendation
[Your recommended next step — must pass Fix-Target Gate]

---
**Verification Mode Active** - Awaiting user decision before proceeding.
```

## Workflow

### Step 1: Environment Preparation (Clean Slate)

**CRITICAL**: Before verification mode activates, prepare a clean environment.

Execute cleanup:

```bash
# Clear all log files
find .plan/logs -type f -delete

# Clear all existing plans (remove subdirectories)
find .plan/plans -mindepth 1 -maxdepth 1 -exec rm -r {} +
```

**Verification**: Confirm both directories are empty.

**Output**:
```
Environment prepared - logs and plans cleared for clean slate verification.
```

**Note**: If cleanup fails, STOP and report the issue.

### Step 2: Acknowledge Verification Mode

After Step 1 completes, acknowledge:

```
Environment prepared - logs and plans cleared.
Verification Mode Active - All operations will stop on failures, resolution issues, or workarounds for analysis.
```

If `scope: planning` was specified, add:

```
Planning Scope Active - Additional checks: .plan access patterns, work-log population, status consistency.
```

### Step 3: Execute with Vigilance

For each operation:
1. Check if it's a script execution, resolution, or potential workaround
2. Monitor for failure conditions
3. Apply appropriate verification protocol if triggered

### Step 4: Analyze Failures

When verification protocol triggers:
1. Load appropriate analysis standard
2. Perform structured analysis
3. Format output per template
4. Present to user and wait

### Step 5: Resume After User Decision

Only after user provides direction:
1. Execute user's chosen option
2. Continue verification mode for subsequent operations
3. Track all verification stops in session

### Step 6: Post-Workflow Log Error Verification

**When**: After tested workflow completes.

**Purpose**: Catch errors in the **global** log that failed before reaching plan-scoped logging (typically missing `--plan-id` or `--trace-plan-id`).

**A. Scan Plan-Scoped Log**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging read --plan-id {plan_id} --type script
```

Review the output for `[ERROR]` entries. This uses the manage-log API (the designed access pattern for `.plan` files) and avoids shell metacharacters that trigger Claude Code security prompts.

**B. If Errors Found**:

1. Load `standards/log-error-analysis.md` for common causes
2. Use `standards/failure-analysis.md` for full analysis
3. Trace origin to the calling component
4. Fix the missing/incorrect plan parameter

**C. Resolution Options**:
1. Apply fix to calling component
2. Record as lesson
3. Skip (with reason)

## Standards Organization

```
standards/
├── failure-analysis.md      (Script and tool failure analysis - real-time)
├── resolution-analysis.md   (Path and reference resolution issues)
├── workaround-detection.md  (Detecting and analyzing workarounds)
├── planning-compliance.md   (Planning command/skill access patterns)
└── log-error-analysis.md    (Post-workflow log error analysis)
```

## Verification Triggers

### Script Failures
- Non-zero exit code
- Error output (stderr)
- Unexpected output format
- Missing expected output
- Timeout conditions

### Resolution Failures
- Path not found
- Skill not found
- Reference not resolved
- Dependency missing
- Configuration missing

### Workaround Indicators
- Using alternative path
- Falling back to different method
- Skipping documented step
- Substituting different tool
- Manual intervention where automation expected

### Planning Compliance Violations (scope: planning only)

These checks apply ONLY when `scope: planning` is specified:

**Single Allowed `.plan` Access Pattern**:
```bash
python3 .plan/execute-script.py {notation} {subcommand} {args...}
```

This is the ONLY allowed way to interact with `.plan` files. All other access is a violation.

**Allowed Direct Write Pattern**:
- `Write(.plan/plans/{plan_id}/solution_outline.md)` is permitted when the path
  was obtained via `manage-solution-outline resolve-path` and is immediately
  followed by `manage-solution-outline validate` (or `write`/`update`). This replaces heredoc stdin.

**Prohibited `.plan` Access** (ALL violations):
- Direct Read/Write/Edit of ANY `.plan/**` file (except via execute-script.py invocation or the allowed direct write pattern above)
- Direct Read/Write/Edit of `.plan/plans/*/status.toon`
- Direct Read/Write/Edit of `.plan/plans/*/references.json`
- Direct Read/Write/Edit of `.plan/plans/*/work.log`
- Direct Read/Write/Edit of `.plan/local/marshall-state.toon`
- Direct Read/Write/Edit of `.plan/local/logs/*.log`
- Direct Read/Write/Edit of `.plan/local/lessons-learned/*.md`
- Direct access to goals/tasks directories
- Glob patterns targeting `.plan/**`
- Bash find/ls/cat commands accessing `.plan/` structure
- Missing work.log entry after significant operation
- Status not updated after phase transition
- Artifacts created without manage-* scripts

**Rationale**: All `.plan` access must go through manage-* scripts to ensure:
- Consistent audit trail via script execution logging
- Validation and error handling
- Single source of truth for file format changes

## Tool Access

**Read**: Load analysis standards on-demand

No other tools required - this skill modifies behavioral patterns.

## Integration Pattern

This skill is designed to be loaded alongside other skills:

```
Skill: pm-plugin-development:verification-mode
Skill: plan-marshall:phase-3-outline
```

When both are loaded, verification mode applies to all solution-outline operations.

## Quality Indicators

Verification mode is working correctly when:
- All script failures produce structured analysis
- Resolution issues are caught before fallbacks
- Workarounds are flagged before execution
- User is always asked before proceeding
- No silent failures or alternative paths taken

## Example Session

```
User: Run the init phase for my-plan

Claude: Verification Mode Active - All operations will stop on failures, resolution issues, or workarounds for analysis.

Executing plan-init for my-plan...

## SCRIPT FAILURE Analysis Required

### Issue Detected
Script plan-marshall:manage-status:manage_status returned non-zero exit code (1)

### Context
- **Operation**: Create plan status
- **Component**: plan-marshall:plan-manage
- **Expected**: status: success with plan created
- **Actual**: status: error with invalid_domain

### Root Cause Analysis
The domain "java-main" is not a valid domain identifier.
Script expects one of: java, javascript, plugin, generic.

### Impact Assessment
| Aspect | Impact |
|--------|--------|
| Blocking | Yes |
| Data Loss Risk | No |
| Workaround Available | Yes |

### Options
1. Fix the calling code to use valid domain identifier
2. Manually run with correct domain
3. Extend VALID_DOMAINS if new domain needed

### Recommendation
Fix option 1 - Update calling code to use valid domain "java"

---
**Verification Mode Active** - Awaiting user decision before proceeding.
```

## Planning-Specific Verification (scope: planning)

When `scope: planning` is specified, load the planning verification protocol:

```
Read standards/planning-verification.md
```

This provides:
- Pre-operation .plan access checks
- Post-phase verification protocol (4 mandatory steps after every phase transition)
- Compliance violation detection (prohibited .plan access patterns)
- Post-operation audit trail verification
- Examples of planning violations and audit output

## Deactivation

Verification mode remains active for the entire session once loaded.

To run without verification:
- Start a new session without loading this skill
- Or explicitly acknowledge: "Disable verification mode for this operation"

## Related Skills

### Deep Failure Analysis

For post-hoc analysis of script failures with origin tracing and fix proposals:

```
Skill: pm-plugin-development:tools-analyze-script-failures
```

Or invoke via command:
```
/pm-plugin-development:tools-analyze-script-failures
```

**When to use**: After verification mode catches a failure, use analyze-script-failures to:
- Trace which component (command/agent/skill) triggered the failure
- Analyze how instructions led to the incorrect script call
- Get specific code fix proposals
- Record findings as lessons learned

**Difference**: Verification mode stops and analyzes in real-time; analyze-script-failures performs deep post-hoc analysis with origin tracing.
