# Safe Fixes Guide

Detailed guide for applying safe fixes automatically without user confirmation.

## Safe Fix Principles

Safe fixes are mechanical transformations that:
- Don't lose information
- Don't change component behavior
- Have deterministic outcomes
- Are always correct to apply

## Applying Safe Fixes

### General Process

1. **Create Backup**: Always backup before modifying
2. **Apply Fix**: Use appropriate strategy for fix type
3. **Validate Result**: Ensure fix was applied correctly
4. **Track Changes**: Record what was changed

### Using fix.py apply subcommand

```bash
echo '{"type": "fix-type", "file": "path/to/file.md"}' | \
  python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:fix apply --fix -
```

Output:
```json
{
  "success": true,
  "fix_type": "fix-type",
  "file": "path/to/file.md",
  "changes": ["Description of change"],
  "backup_created": "path/to/file.md.fix-backup"
}
```

## Fix-Specific Strategies

### missing-frontmatter

**Strategy**: Prepend generated frontmatter

**Agent Template**:
```yaml
---
name: {filename}
description: [Description needed]
tools: Read, Write, Edit
model: sonnet
---

```

**Command Template**:
```yaml
---
name: {filename}
description: [Description needed]
---

```

**Implementation**:
1. Determine component type from path
2. Extract filename for name field
3. Generate frontmatter from template
4. Prepend to existing content

### array-syntax-tools

**Strategy**: Regex replacement in frontmatter

**Pattern**: `^tools:\s*\[([^\]]+)\]`
**Replacement**: `tools: \1`

**Examples**:
- `tools: [Read, Write]` → `tools: Read, Write`
- `tools: [Read]` → `tools: Read`

**Implementation**:
1. Read file content
2. Apply regex substitution
3. Write back

### missing-*-field

**Strategy**: Insert field at appropriate position

**Insertion Order**:
1. `name` - After opening `---`
2. `description` - After `name`
3. `tools` - After `description`

**Implementation**:
1. Find frontmatter boundaries
2. Determine insertion point
3. Insert field with default value
4. Preserve existing content

### rule-11-violation

**Strategy**: Append Skill to existing tools declaration

**Detection**: Agent has `tools:` or `allowed-tools:` field without `Skill`

**Implementation**:
1. Read file content
2. Find the `tools:` or `allowed-tools:` line in frontmatter
3. Append `, Skill` to end of the line
4. Write back

**Examples**:
- `tools: Read, Write` → `tools: Read, Write, Skill`
- `tools: Read, Write, Edit, Grep` → `tools: Read, Write, Edit, Grep, Skill`

**Edge Cases**:
- If `Skill` already present → no change (fix returns success=False)
- If no `tools:` field → no violation (inherits all tools)

### trailing-whitespace

**Strategy**: Strip trailing characters from each line

**Pattern**: `[[:space:]]+$` per line
**Replacement**: Empty string

**Implementation**:
1. Read all lines
2. Strip trailing whitespace from each
3. Write back preserving line count

### improper-indentation

**Strategy**: Normalize whitespace

**Rules**:
- YAML: 2-space indentation
- Lists: Consistent bullet alignment
- Code blocks: Preserve as-is

**Implementation**:
1. Detect indentation style
2. Convert to standard (2-space)
3. Preserve code block indentation

## Batch Application

When applying multiple safe fixes to same file:

```python
# Optimal order
fixes = sorted(fixes, key=lambda f: FIX_PRIORITY.get(f['type'], 99))

for fix in fixes:
    result = apply_fix(fix, bundle_dir)
    if not result['success']:
        # Log error, continue with next fix
        continue
```

**Priority Order**:
1. missing-frontmatter (required for others)
2. invalid-yaml
3. missing-name-field
4. missing-description-field
5. missing-tools-field
6. array-syntax-tools
7. rule-11-violation
8. trailing-whitespace
9. improper-indentation

## Error Recovery

### Backup Restoration

If fix fails mid-application:
```bash
# Backup is at original_file.md.fix-backup
cp file.md.fix-backup file.md
```

`fix apply` does this automatically on error.

### Validation After Fix

After each fix, validate:
- File is still readable
- YAML is valid (if frontmatter fix)
- No content was accidentally removed

## Tracking Applied Fixes

Maintain tracking JSON:

```json
{
  "bundle": "bundle-name",
  "timestamp": "2025-11-21T10:00:00Z",
  "fixes_applied": [
    {
      "type": "missing-frontmatter",
      "file": "agents/my-agent.md",
      "success": true,
      "backup": "agents/my-agent.md.fix-backup"
    }
  ],
  "summary": {
    "total": 5,
    "successful": 5,
    "failed": 0
  }
}
```

## Common Pitfalls

### 1. Applying to Wrong Component Type

**Problem**: Agent frontmatter applied to command
**Solution**: Check path for `/agents/`, `/commands/`, `/skills/`

### 2. Overwriting Existing Content

**Problem**: Fix adds field that already exists
**Solution**: Check for field before adding

### 3. Breaking YAML Structure

**Problem**: Insertion breaks YAML indentation
**Solution**: Validate YAML after insertion

### 4. Empty File Handling

**Problem**: File is empty or only whitespace
**Solution**: Check file has content before fixing

## Quality Checklist

Before marking safe fix as complete:

- [ ] Backup created successfully
- [ ] Fix applied without errors
- [ ] File still readable
- [ ] YAML still valid (if applicable)
- [ ] No unintended changes to other content
- [ ] Changes recorded in tracking

## See Also

- `fix-catalog.md` - Complete fix type reference
- `verification-guide.md` - Verify fixes worked
