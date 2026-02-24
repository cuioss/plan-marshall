# Safe Fixes Guide

Detailed guide for applying safe fixes automatically without user confirmation. See `fix-catalog.md` for the complete list of safe fix types and their detection patterns.

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

**Priority Order** (see fix-catalog.md for full list):
1. missing-frontmatter (required for others)
2. invalid-yaml
3. missing-*-field (name, description, user-invocable, tools)
4. array-syntax-tools
5. agent-skill-tool-visibility
6. trailing-whitespace
7. improper-indentation

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

1. **Applying to Wrong Component Type**: Check path for `/agents/`, `/commands/`, `/skills/`
2. **Overwriting Existing Content**: Check for field before adding
3. **Breaking YAML Structure**: Validate YAML after insertion
4. **Empty File Handling**: Check file has content before fixing

## See Also

- `fix-catalog.md` - Complete fix type reference with detection and fix strategies
- `verification-guide.md` - Verify fixes worked
