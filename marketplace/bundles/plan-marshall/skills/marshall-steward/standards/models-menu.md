# Models Submenu — UX Contract

> Wizard contract for editing the `models` block of `.plan/marshal.json` from the `marshall-steward` Main Menu.

## Overview

The Models submenu lets users configure per-role model variant routing without hand-editing JSON. It walks the role registry from [`plan-marshall:plan-marshall/standards/model-roles.md`](../../plan-marshall/standards/model-roles.md), validates every level value against the enum from [`plan-marshall:plan-marshall/standards/model-levels.md`](../../plan-marshall/standards/model-levels.md), and prints the **restart hint** after any successful save (Claude Code loads agent files at session start, so new variant routing applies only after restart).

This document is the contract. The wizard implementation in `SKILL.md` (Main Menu Option 4) loads this file when the user picks "Models".

## Entry Point

The Models submenu is reached from the Main Menu (Option 4 — see `SKILL.md` § Main Menu). When the user selects it:

```
Read standards/models-menu.md
```

Then execute the workflow described below.

## Workflow

### Step 1: Show Current State

Read the current `models` block via `manage-config`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  models read --role <any_role_used_for_status>
```

Display one of:

- `(not configured — defaults apply)` — when `models` block is absent or empty.
- The current `default` (or `(unset)`) plus a table of `roles.<role> = <level>` entries grouped by **effective** vs **pending** status.

The display walks the registry from `model-roles.md` so pending and unset roles are surfaced (not hidden) — users see what could be configured, not just what is.

### Step 2: Sub-menu Choice

```
AskUserQuestion:
  question: "Models submenu — what would you like to do?"
  header: "Models"
  options:
    - label: "1. Edit default level"
      description: "Set the plan-wide default level (used when a role is unset)"
    - label: "2. Edit per-role levels"
      description: "Walk the role registry and set per-role overrides"
    - label: "3. Clear all"
      description: "Remove the models block entirely (revert to inherit-everywhere)"
    - label: "4. Back to Main Menu"
      description: "Return without changes"
  multiSelect: false
```

### Step 3a: Edit Default Level

When user picks "1. Edit default level":

```
AskUserQuestion:
  question: "Pick a default level (applies to every role unless overridden)"
  header: "models.default"
  options:
    - label: "low"
      description: "Haiku — mechanical tasks, log scrubbing"
    - label: "medium"
      description: "Sonnet medium — routine code edits, doc updates"
    - label: "high"
      description: "Sonnet high — analytical work, multi-file reasoning"
    - label: "xhigh"
      description: "Opus high — heavy reasoning, complex refactors"
    - label: "xxhigh"
      description: "Opus xhigh — top tier (Opus-4.7-only)"
    - label: "inherit"
      description: "Sentinel — dispatch canonical, runtime inherits parent model"
    - label: "(unset)"
      description: "Remove models.default entirely"
  multiSelect: false
```

Persist the choice via `manage-config` (the wizard manipulates `marshal.json` through the script, never directly).

### Step 3b: Edit Per-Role Levels

When user picks "2. Edit per-role levels":

Walk the **effective** rows from `model-roles.md` first, then the **pending** rows. For each role, present the same level palette as Step 3a plus an `(unset — fall back to default)` option.

For **pending** roles, prefix the question with:

> "(pending — set, but not effective until wrapping work lands)"

so the user understands the configuration is preserved but produces no runtime effect today.

### Step 3c: Clear All

When user picks "3. Clear all":

Confirm via `AskUserQuestion`, then remove the `models` block from `marshal.json`. This reverts every dispatch site to `inherit` (canonical no-suffix variant, runtime inherits parent model).

## Validation

Validation rules are identical to the resolver in `manage-config models read --role`:

| Rule | Failure Mode |
|------|--------------|
| Level value is one of `low`, `medium`, `high`, `xhigh`, `xxhigh`, `inherit` | Refuse save; show error inline; re-prompt. |
| `max` is reserved (future-additive) | Refuse save with explicit "use `xxhigh` for the current top tier" message. |
| Role key is in the registry | Warn (not refuse) for unknown roles — the registry can rename without breaking saved configs. |

The wizard MUST NOT permit saving an invalid value at any step. The user sees the rejection and is re-prompted from the same question.

## Persistence

After every successful save (Steps 3a, 3b, 3c):

1. The wizard writes through `manage-config` (which round-trips JSON cleanly — no formatting drift).
2. Print confirmation: `"Saved: models.<key> = <value>"`.
3. **Print the restart hint verbatim**:

   > **Restart Claude Code to pick up new variant routing.** Agent files load at session start; mid-session edits don't apply until you exit and re-enter.

   The hint fires unconditionally after any Models save — even when the only change was setting a pending role (the user might restart anyway, and clarity beats cleverness).

4. Return to the Models submenu (Step 2) so the user can make further edits or back out.

## Pending-Role Hint

When the user sets a value on a **pending** role, append this hint to the save confirmation:

> Note: `<role>` is currently pending — the value is saved but produces no runtime effect until the wrapping work lands. See `model-roles.md` for status.

This makes the schema-validates-but-no-effect distinction explicit at save time, not just in the read display.

## Cross-References

| Document | Content |
|----------|---------|
| [`model-levels.md`](../../plan-marshall/standards/model-levels.md) | Level enum and primitive binding. |
| [`model-roles.md`](../../plan-marshall/standards/model-roles.md) | Role registry walked by Step 3b. |
| [`role-variants.md`](../../plan-marshall/standards/role-variants.md) | User-facing centralised guide cross-linked from save confirmations. |
| `manage-config:_cmd_models.py` | Resolver that reads the same `models` block written by this wizard. |
