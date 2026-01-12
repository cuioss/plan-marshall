# Plan Overwrite Behavior

This standard defines how to handle existing plans when creating a new plan with the same ID.

## Scenario

When `create-or-reference` returns `action: exists`, the user has three options:

1. **Resume** - Continue with the existing plan
2. **Replace** - Delete existing plan and create new
3. **Rename** - Use a different plan_id

## Replace Flow

When user selects "Replace", execute the following steps:

### Step 1: Delete Existing Plan

Use the `delete-plan` command to remove the entire plan directory:

```bash
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files delete-plan \
  --plan-id {plan_id}
```

**Output** (TOON format):
```toon
status: success
plan_id: my-feature
action: deleted
path: /path/to/.plan/plans/my-feature
files_removed: 5
```

### Step 2: Re-run Create-or-Reference

After successful deletion, re-run `create-or-reference`:

```bash
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files create-or-reference \
  --plan-id {plan_id}
```

This should now return `action: created`.

### Step 3: Continue with Init Flow

Continue with Step 4 (Get Task Content) and subsequent steps.

## Safety Considerations

The `delete-plan` command:
- Only deletes directories under `.plan/plans/`
- Validates plan_id format (kebab-case)
- Returns TOON output with file count for audit trail
- Does NOT prompt for confirmation (caller handles user confirmation)

## Error Handling

If deletion fails:

```toon
status: error
plan_id: my-feature
error: delete_failed
message: Failed to delete plan directory: {reason}
```

Possible errors:
- `plan_not_found` - Plan directory doesn't exist
- `permission_denied` - Filesystem permissions issue
- `delete_failed` - Other filesystem error

## Integration

This standard is implemented by:
- `pm-workflow:manage-files:manage-files delete-plan` - Script command
- `pm-workflow:plan-init` - Skill workflow (Step 3)
- `pm-workflow:plan-init-agent` - Agent implementation
