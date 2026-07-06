# Plan Overwrite Behavior

This standard defines how to handle existing plans when creating a new plan with the same ID.

## Scenario

When `create-or-reference` returns `action: exists`, the dispatched phase-1-init leaf cannot prompt (it returns the `plan_exists_prompt` early-return envelope — see SKILL.md Step 3). The **orchestrator** (`plan-marshall/workflow/planning.md` § Action: init) fires the `AskUserQuestion` and resolves one of three options:

1. **Resume** - Continue with the existing plan (no init re-run)
2. **Replace** - Delete existing plan and re-dispatch a fresh init
3. **Rename** - Re-dispatch init under a different plan_id

## Replace Flow

When the orchestrator resolves "Replace", it executes the following steps:

### Step 1: Delete Existing Plan

Use the `delete-plan` command to remove the entire plan directory:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status delete-plan \
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

### Step 2: Re-dispatch a Fresh Init

After successful deletion, the orchestrator re-dispatches the **1-Init Phase** dispatch (`plan-marshall/workflow/planning.md` § Action: init). The fresh init's `create-or-reference` now returns `action: created`, so init runs to completion normally.

### Step 3: Resume the Init Flow

The re-dispatched init proceeds through Step 4 (Get Task Content) and the subsequent steps as a first-time run — the orchestrator does NOT feed a resolution input back into the same leaf.

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
- `plan-marshall:manage-status:manage-status delete-plan` - Script command
- `plan-marshall:phase-1-init` - Skill workflow (Step 3)
- `plan-marshall:execution-context` - Generic execution-context dispatcher (canonical + 5 level variants)
