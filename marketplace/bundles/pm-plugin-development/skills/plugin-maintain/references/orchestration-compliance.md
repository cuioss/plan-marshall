# Orchestration Compliance Guide

Mandatory compliance patterns for bundle-by-bundle orchestration workflows.

## Purpose

This guide ensures diagnose commands follow proper orchestration:
- Complete all steps for each bundle
- Don't skip workflow steps
- Verify fixes before proceeding
- Use mandatory completion checklists

## Bundle Processing Rules

### Sequential Processing

Process bundles one at a time:
```
For each bundle:
  Complete ALL steps before moving to next bundle
```

**Never**:
- Process partial bundle subsets
- Jump ahead to summary
- Skip verification steps

### Stop Points

Explicit stop points in workflow:
1. After analysis (Step 5a-5d)
2. After fix application (Step 5e-5i)
3. After verification (Step 5j)

### Completion Gates

Before proceeding to next bundle:
- All components analyzed
- All fixes attempted
- Verification completed
- Checklist confirmed

## Mandatory Completion Checklist

**Before proceeding to next bundle**, verify:

1. [ ] All components in bundle discovered
2. [ ] Each component analyzed
3. [ ] Issues categorized (safe/risky)
4. [ ] Safe fixes applied
5. [ ] Risky fixes presented to user
6. [ ] User responses recorded
7. [ ] Post-fix verification run
8. [ ] Git status checked
9. [ ] Results documented
10. [ ] No critical issues remaining unaddressed

## Anti-Skip Protections

### Warning Format

When tempted to skip, display:
```
⚠️ ANTI-SKIP WARNING
Step {X} is mandatory for bundle integrity.
Skipping will result in incomplete/invalid results.
Continue with step? [Y/abort]
```

### Protected Steps

**Never skip**:
- Step 5a: Load orchestration patterns
- Step 5b: Reference validation
- Step 5e: Safe fix application
- Step 5f: Risky fix presentation
- Step 5j: Completion checklist

### Consequences of Skipping

| Step Skipped | Consequence |
|--------------|-------------|
| Analysis | Issues not detected |
| Categorization | Wrong fix type applied |
| Safe fixes | Automatable issues remain |
| Verification | Unknown fix success |
| Checklist | Incomplete bundle processing |

## Post-Fix Verification

### Git Status Check

After applying fixes, verify with git:

```bash
git status
```

**Check for**:
- Modified files (fixes applied)
- New files (if created)
- No unexpected changes

### Verification Pattern

```markdown
### Step 5h: Post-Fix Verification

**MANDATORY: Verify fixes were applied**

Run git status:
```
Bash: git status
```

Parse output:
- Count modified files
- Verify expected files changed
- Check for unexpected changes

If expected ≠ actual:
- Report discrepancy
- Investigate cause
- Do not proceed until resolved
```

## Implementing Compliance

### In Diagnose Commands

Add to Step 1:
```markdown
**Load orchestration compliance:**
```
Read: references/orchestration-compliance.md
```
```

### At Step 5 Start

```markdown
### Step 5: Process Bundles (Bundle-by-Bundle)

**CRITICAL: Follow bundle-orchestration-compliance patterns**

For EACH bundle (sequential, complete one before starting next):
```

### At Step Transitions

```markdown
**[CHECKPOINT]** Before proceeding:
- Verify previous step completed
- Apply anti-skip protection
- Confirm no critical blockers
```

### At Bundle End

```markdown
### Step 5j: Mandatory Completion Checklist

**STOP: Complete before next bundle**

Verify each item (from orchestration-compliance):
1. [ ] All components discovered: {count}
2. [ ] Each analyzed: {analyzed_count}/{total}
...
```

## Enforcement Mechanisms

### Explicit Warnings

Display before potentially skippable steps:
```
This step is protected by orchestration compliance.
Skipping is not permitted.
```

### Stop Points

Clear indicators:
```
[STOP POINT] Do not proceed until:
- X is verified
- Y is completed
- Z is confirmed
```

### Verification Gates

Must verify before proceeding:
```
Verification required: {check_name}
Status: {PASSED/FAILED}
{if FAILED: Block progression, report issue}
```

### Checklists

Mandatory checklist completion:
```
Completion Checklist for {bundle_name}:
[x] Component discovery
[x] Analysis complete
[x] Safe fixes applied
[ ] Risky fixes handled  ← NOT COMPLETE
[x] Verification done

⚠️ Cannot proceed: Not all items checked
```

## Integration Pattern

### Loading Compliance

At workflow start:
```markdown
### Step 1: Load Diagnostic Patterns

**Required patterns:**
```
Skill: plan-marshall:ref-development-standards
```

**Orchestration compliance:**
```
Read: references/orchestration-compliance.md
```
```

### Referencing Throughout

At critical points:
```markdown
**Per orchestration-compliance**: {specific rule}
```

### Final Verification

At workflow end:
```markdown
### Step 6: Final Summary

**Compliance verification:**
- Bundles processed: {count}
- All completed fully: {yes/no}
- Violations: {count}
```

## Quality Standards

### Compliance Patterns Must Be

- **Enforceable**: Clear actionable checks
- **Observable**: Use git status, counts
- **Unambiguous**: No room for interpretation
- **Complete**: Cover all critical steps

### Warnings Must Include

- What step is protected
- Why skipping is problematic
- Consequences of violation
- How to proceed correctly

### Checklists Must Be

- Exhaustive: Cover all requirements
- Verifiable: Each item checkable
- Sequential: Order matters
- Documented: Record completion

## Related Resources

- **plugin-diagnose skill** - Uses these patterns
- **plugin-fix skill** - Fix application patterns
- **component-update-guide.md** - Component updates

