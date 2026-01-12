# Resolution Analysis Standard

Structured approach to analyzing path, reference, and dependency resolution failures.

## Overview

When a path, skill reference, or dependency fails to resolve during verification mode, analyze the resolution chain to identify where and why resolution failed.

## Resolution Types

### Type 1: Path Resolution

**What It Is**: Resolving relative or symbolic paths to absolute file system paths.

**Common Failures**:
- Relative path from wrong base directory
- Symlink broken or missing
- Path separator issues (Windows vs Unix)
- Missing parent directories

**Analysis Approach**:
1. Identify starting point for resolution
2. Trace each path component
3. Find first component that fails
4. Check directory existence and permissions

### Type 2: Script Path Resolution

**What It Is**: Resolving `bundle:skill/scripts/name.py` notation to actual file path.

**Resolution Pattern**:
```
bundle:skill/scripts/name.py
  → marketplace/bundles/{bundle}/skills/{skill}/scripts/name.py
```

**Common Failures**:
- Bundle name misspelled
- Skill name misspelled
- Script file missing
- Wrong scripts directory structure

**Analysis Approach**:
1. Parse bundle:skill notation
2. Verify bundle exists in marketplace
3. Verify skill exists in bundle
4. Verify scripts directory exists
5. Verify script file exists

### Type 3: Skill Reference Resolution

**What It Is**: Resolving `Skill: bundle:skill-name` to loadable skill content.

**Common Failures**:
- Skill not registered in plugin.json
- SKILL.md file missing
- Skill in different scope than expected

**Analysis Approach**:
1. Identify expected skill location
2. Check plugin.json for skill registration
3. Verify SKILL.md exists
4. Check scope (marketplace/global/project)

### Type 4: Dependency Resolution

**What It Is**: Resolving imports, requirements, or cross-references.

**Common Failures**:
- Python import not on sys.path
- Required skill not loaded
- Cross-reference to non-existent component

**Analysis Approach**:
1. Identify dependency chain
2. Check each dependency in order
3. Find first missing dependency
4. Verify installation/availability

## Analysis Template

Use this template for resolution analyses:

```markdown
## RESOLUTION FAILURE Analysis Required

### Issue Detected
[What failed to resolve]

### Resolution Chain
```
Input: [Original reference]
Step 1: [First transformation] → [Result/Status]
Step 2: [Second transformation] → [Result/Status]
Step N: [Final transformation] → FAILED
```

### Failed Component
- **Type**: [Path/Script/Skill/Dependency]
- **Reference**: [Original reference string]
- **Expected Location**: [Where it should be]
- **Actual Status**: [What was found/not found]

### Directory Investigation
```
[ls -la output or Glob results showing actual contents]
```

### Root Cause
[Why resolution failed]

### Resolution Options
1. **Create missing resource**: [What to create and where]
2. **Fix reference**: [How to correct the reference]
3. **Update configuration**: [What config to change]

### Recommended Action
[Specific recommendation]
```

## Common Resolution Issues

### Issue: Bundle Not Found

**Symptom**: `Cannot find bundle 'xyz'`

**Checklist**:
- [ ] Bundle directory exists in marketplace/bundles/
- [ ] Bundle has .claude-plugin/plugin.json
- [ ] Bundle name in plugin.json matches reference
- [ ] No typos in bundle name

### Issue: Skill Not Found

**Symptom**: `Skill 'xyz' not found in bundle`

**Checklist**:
- [ ] Skill directory exists in bundle/skills/
- [ ] SKILL.md file exists in skill directory
- [ ] Skill registered in bundle's plugin.json
- [ ] Skill name matches exactly (case-sensitive)

### Issue: Script Path Not Found

**Symptom**: `Script not found at expected path`

**Checklist**:
- [ ] scripts/ directory exists in skill
- [ ] Script file exists with correct name
- [ ] Script has .py or .sh extension
- [ ] No extra path components

### Issue: Import Failed

**Symptom**: `ModuleNotFoundError` or similar

**Checklist**:
- [ ] sys.path includes required directories
- [ ] Module file exists at expected location
- [ ] __init__.py present if needed
- [ ] No circular imports

## Resolution Strategies

### Strategy 1: Fix at Source

Preferred approach - fix the reference to point to correct location.

**When to Use**:
- Reference has typo
- Reference uses wrong notation
- Reference is outdated

### Strategy 2: Create Missing Resource

Create the resource that should exist.

**When to Use**:
- Resource was never created
- Resource was accidentally deleted
- New component being integrated

### Strategy 3: Update Configuration

Modify configuration to enable resolution.

**When to Use**:
- Component not registered
- Path not in search path
- Permission not granted

## Integration with Verification Mode

When verification mode detects resolution failure:

1. Load this standard: `Read standards/resolution-analysis.md`
2. Identify resolution type
3. Trace resolution chain
4. Identify failure point
5. Format output using template
6. Present to user and wait for decision
