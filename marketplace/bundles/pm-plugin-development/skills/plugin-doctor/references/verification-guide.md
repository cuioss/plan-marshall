# Verification Guide

Guide for verifying that applied fixes successfully resolved the identified issues.

## Verification Principles

Verification confirms:
- The fix was applied correctly
- The original issue is no longer present
- No new issues were introduced
- The component still functions correctly

## Using verify-fix.sh

```bash
scripts/verify-fix.sh {fix_type} {component_path}
```

**Output**:
```json
{
  "verified": true,
  "issue_resolved": true,
  "details": "Description of verification result"
}
```

**Fields**:
- `verified`: Whether verification completed (script ran successfully)
- `issue_resolved`: Whether the original issue is now fixed
- `details`: Human-readable explanation

## Fix-Type Verification Strategies

### Frontmatter Fixes

**Verifies**: missing-frontmatter, missing-*-field, invalid-yaml, array-syntax-tools

**Strategy**: Check frontmatter structure

```bash
# Check frontmatter exists
head -1 "$file" | grep -q "^---$"

# Check required fields
awk '/^---$/...' "$file" | grep -q "^name:"
awk '/^---$/...' "$file" | grep -q "^description:"

# Check no array syntax
! grep -q "^tools:.*\[" "$file"
```

**Success Criteria**:
- File starts with `---`
- Required fields present
- YAML is valid
- Syntax is correct

### Tool Declaration Fixes

**Verifies**: unused-tool-declared, tool-not-declared, rule-6-violation

**Strategy**: Re-run tool coverage analysis

```bash
analyze-tool-coverage.sh "$file"
```

**Check Results**:
```python
result = run_tool_coverage(file)
if fix_type == "unused-tool-declared":
    success = result['unused_count'] == 0
elif fix_type == "tool-not-declared":
    success = result['missing_count'] == 0
elif fix_type == "rule-6-violation":
    success = not result['has_task_tool']
```

### Pattern Violation Fixes

**Verifies**: pattern-22-violation, ci-rule-self-update

**Strategy**: Check for prohibited patterns

```bash
# Pattern 22: No self-update commands
! grep -qi "/plugin-update-agent\|/plugin-update-command" "$file"
```

**Success Criteria**:
- Self-update patterns not found
- Caller-reporting pattern present (optional)

### Whitespace Fixes

**Verifies**: trailing-whitespace, improper-indentation

**Strategy**: Check for whitespace issues

```bash
# No trailing whitespace
! grep -q '[[:space:]]$' "$file"
```

## Batch Verification

For multiple fixes, verify each:

```python
results = []
for fix in applied_fixes:
    result = verify_fix(fix['type'], fix['file'])
    results.append({
        'fix': fix,
        'verification': result
    })

# Summary
resolved = sum(1 for r in results if r['verification']['issue_resolved'])
total = len(results)
print(f"Verified: {resolved}/{total} fixes resolved issues")
```

## Verification Report Format

```json
{
  "verification_timestamp": "2025-11-21T10:10:00Z",
  "bundle": "bundle-name",
  "fixes_verified": 5,
  "issues_resolved": 4,
  "issues_remaining": 1,
  "results": [
    {
      "fix_type": "missing-frontmatter",
      "file": "agents/my-agent.md",
      "verified": true,
      "issue_resolved": true
    },
    {
      "fix_type": "rule-6-violation",
      "file": "agents/task-agent.md",
      "verified": true,
      "issue_resolved": false,
      "details": "Task tool still present in declaration"
    }
  ]
}
```

## Handling Verification Failures

### Issue Not Resolved

**Possible Causes**:
- Fix didn't apply correctly
- Multiple instances of issue
- Related issue still present

**Actions**:
1. Check backup to see original state
2. Re-run diagnostic to see current state
3. Apply fix again or investigate manually

### Verification Script Failed

**Possible Causes**:
- File no longer exists
- Script error
- Permissions issue

**Actions**:
1. Check file exists
2. Check script permissions
3. Run diagnostic manually

### New Issues Introduced

**Possible Causes**:
- Fix broke YAML structure
- Content accidentally removed
- Unintended side effects

**Actions**:
1. Restore from backup
2. Apply fix more carefully
3. Consider manual fix instead

## Re-Running Diagnostics

After verification, consider full re-diagnosis:

```bash
# Re-run full diagnostic
plugin-diagnose:diagnose-agents {bundle_dir}
```

This catches:
- Issues fix didn't address
- New issues from fixes
- Related issues now visible

## Quality Checklist

After verification:

- [ ] All applied fixes verified
- [ ] Issue resolution status known for each
- [ ] Any failures investigated
- [ ] Re-diagnosis considered
- [ ] Backup files cleaned up (optional)

## Cleanup

After successful verification:

```bash
# Remove backup files (optional)
find {bundle_dir} -name "*.fix-backup" -delete
```

Only do this after confirming fixes work correctly.

## Integration with Workflow

Verification is the final step:

```
1. diagnose → identify issues
2. analyze-and-categorize → categorize fixes
3. apply-safe-fixes → auto-apply safe
4. apply-risky-fixes → user-approved risky
5. verify-fixes → CONFIRM RESOLUTION ← You are here
6. (optional) re-diagnose → check for more issues
```

## See Also

- `fix-catalog.md` - All fix types
- `safe-fixes-guide.md` - Safe fix details
- `risky-fixes-guide.md` - Risky fix handling
