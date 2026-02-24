# Risky Fixes Guide

Guide for presenting and applying risky fixes that require user confirmation. See `fix-catalog.md` for the complete list of risky fix types and their detection patterns.

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

**Current tools**: Read, Write, Edit, WebSearch, Glob
**After fix**: Read, Write, Edit, Glob

Apply this fix?
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
      "applied": true
    },
    {
      "type": "agent-task-tool-prohibited",
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

- `fix-catalog.md` - All fix types reference with detection and fix strategies
- `safe-fixes-guide.md` - Auto-applicable fix process
- `verification-guide.md` - Verify fixes worked
