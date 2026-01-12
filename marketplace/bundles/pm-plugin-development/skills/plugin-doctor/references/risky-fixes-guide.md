# Risky Fixes Guide

Guide for presenting and applying risky fixes that require user confirmation.

## Risky Fix Principles

Risky fixes require confirmation because they:
- May change component behavior
- Involve judgment about what's correct
- Could remove intentional content
- Affect architectural design

## User Prompting Pattern

### Standard Prompt Structure

```
AskUserQuestion:
  question: "Apply fix for {issue_type}?"
  header: "Fix"
  options:
    - label: "Yes"
      description: "Apply this fix to {file}"
    - label: "No"
      description: "Skip this fix"
    - label: "Skip All"
      description: "Skip all remaining risky fixes"
```

### Information to Present

For each risky fix, explain:

1. **What file is affected**
2. **What the issue is**
3. **What the fix will change**
4. **Why this needs confirmation**
5. **Potential consequences**

### Example Presentation

```markdown
## Risky Fix: unused-tool-declared

**File**: agents/my-agent.md
**Issue**: Tool 'WebSearch' is declared but never used in content
**Fix**: Remove 'WebSearch' from tools declaration

**Why This Needs Confirmation**:
- The tool may be intentionally reserved for future use
- Removal changes what tools the agent can access
- If tool is needed, it must be re-added manually

**Current tools**: Read, Write, Edit, WebSearch, Glob
**After fix**: Read, Write, Edit, Glob

Apply this fix?
```

## Fix-Specific Guidance

### unused-tool-declared

**What It Fixes**: Removes tools declared but not used

**User Decision Points**:
- Is the tool actually unused, or is detection incomplete?
- Was the tool intentionally declared for future use?
- Are there plans to use this tool soon?

**Presentation**:
```
Unused tools found: WebSearch, NotebookEdit
These tools are declared but not referenced in the content.
Removing them will:
- Clean up the tools declaration
- Better reflect actual component capabilities
- Require re-adding if needed later
```

### tool-not-declared

**What It Fixes**: Adds tools used but not declared

**User Decision Points**:
- Should this tool actually be used?
- Is the usage accidental and should be removed instead?
- What's the minimal set of tools needed?

**Presentation**:
```
Missing tool declarations found: Grep, Glob
These tools are used in content but not declared.
Adding them will:
- Allow the component to use these tools
- Make the declaration accurate
- Potentially expand component capabilities
```

### rule-6-violation

**What It Fixes**: Removes Task tool from agents

**User Decision Points**:
- How will the agent work without Task?
- Does the agent need restructuring?
- Should this be a command instead?

**Presentation**:
```
Rule 6 Violation: Agent declares Task tool

Rule 6 prohibits agents from using Task to spawn other agents.
Agents should be self-contained and not orchestrate sub-agents.

Removing Task will:
- Make agent compliant with Rule 6
- Require rethinking any sub-agent workflows
- May require converting to command if orchestration needed

Consider: Should this component be a command instead?
```

### rule-7-violation

**What It Fixes**: Removes direct Maven usage from non-maven-builder agents

**User Decision Points**:
- How should Maven builds be triggered?
- Is delegation to maven-builder acceptable?
- Does the agent need this build functionality?

**Presentation**:
```
Rule 7 Violation: Direct Maven execution

Rule 7 restricts Maven execution to the maven-builder agent.
This agent should delegate Maven tasks rather than run them directly.

Fix will:
- Remove direct Maven/mvn commands
- Add delegation pattern to maven-builder
- Require testing build functionality
```

### pattern-22-violation

**What It Fixes**: Changes self-update to caller reporting

**User Decision Points**:
- Is caller-reporting pattern acceptable?
- How should improvements be communicated?
- Does the CI section need complete rewrite?

**Presentation**:
```
Pattern 22 Violation: Self-update pattern

Pattern 22 prohibits agents from updating themselves.
Improvements should be reported to the caller, not self-applied.

Current pattern:
- Uses /plugin-update-agent for self-modification

Fix will change to:
- Report suggested improvements to caller
- Caller decides whether to apply changes

This is a behavioral change in how improvements are handled.
```

## Handling User Responses

### Yes - Apply Fix

```python
result = apply_fix(fix, bundle_dir)
if result['success']:
    log_applied(fix, result)
else:
    report_error(fix, result['error'])
```

### No - Skip Fix

```python
log_skipped(fix, reason="user declined")
continue  # Move to next fix
```

### Skip All - Exit Loop

```python
log_skipped_all(remaining_fixes)
break  # Exit fix loop
```

## Tracking Risky Fix Decisions

```json
{
  "risky_fixes": [
    {
      "type": "unused-tool-declared",
      "file": "agents/my-agent.md",
      "decision": "approved",
      "applied": true,
      "timestamp": "2025-11-21T10:05:00Z"
    },
    {
      "type": "rule-6-violation",
      "file": "agents/task-agent.md",
      "decision": "declined",
      "applied": false,
      "reason": "Agent needs restructuring first"
    }
  ]
}
```

## Post-Fix Recommendations

After applying risky fixes:

1. **Verify immediately**: Run verify-fixes workflow
2. **Test functionality**: Manually test affected components
3. **Review changes**: Use git diff to confirm changes
4. **Document decisions**: Note why fixes were approved/declined

## Rollback Guidance

If risky fix causes problems:

1. **Restore from backup**:
   ```bash
   cp file.md.fix-backup file.md
   ```

2. **Review the issue**: Understand why fix was problematic

3. **Consider alternatives**: May need different approach

## See Also

- `fix-catalog.md` - All fix types reference
- `safe-fixes-guide.md` - Auto-applicable fixes
- `verification-guide.md` - Verify fixes worked
