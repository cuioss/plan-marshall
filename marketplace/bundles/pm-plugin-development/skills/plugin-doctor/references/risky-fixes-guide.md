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

## Simplification rules (confirm-before-apply)

The `SIMPLICITY_*` cluster enforces the "minimum viable code" posture (`plan-marshall:ref-code-quality` `standards/code-organization.md` § `#minimum-viable-code`). Four of the five rules are confirm-before-apply: they are detected (`fixable: false`) and surfaced for human review, with **no auto-apply handler** because each resolution changes a signature or rewrites call sites — a judgement call, not a mechanical edit. (The fifth, `SIMPLICITY_SIGNATURE_DOCSTRING`, IS auto-applicable; see `safe-fixes-guide.md`.)

For each finding below, present the file, the offending construct, the resolution, and the confirmation rationale (following the Standard Prompt Structure above):

- **SIMPLICITY_UNUSED_PARAMETER** — a parameter discarded via `del <param>` (preserved-for-future-use) or tagged `# unused`. **Resolution**: remove it from the signature; add it back against a real caller. **Confirm because**: it changes a public signature; callers passing the argument positionally would break.
- **SIMPLICITY_BACKWARD_COMPAT_REEXPORT** — an import line tagged `# backward compat` / `# re-exported for`. **Resolution**: inline the import at its single call site and delete the shim. **Confirm because**: the live-caller count must be verified to be ≤1 before the shim can be safely removed.
- **SIMPLICITY_DEFENSIVE_CATCHALL** — an `except Exception` handler tagged `# defensive only` / `# pragma: no cover -- defensive`. **Resolution**: let the exception propagate. **Confirm because**: the propagation path and the caller's handling must be verified before removing the guard.
- **SIMPLICITY_THIN_WRAPPER** — a function whose body is a single argument-forwarding `return`. **Resolution**: inline it at the call sites. **Confirm because**: inlining rewrites every caller, which is a cross-file change requiring human review.

Because these have no auto-apply handler, the workflow surfaces them as findings for the user to resolve by hand (or to accept/suppress) rather than offering a one-click apply.

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
