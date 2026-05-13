# Models Submenu — UX Contract

> Wizard contract for editing the `models` block of `.plan/marshal.json` from the `marshall-steward` Main Menu.

## Overview

The Effort submenu is a single preset-picker. The user chooses one of three named presets — `economic`, `balanced`, `high-end` — and the wizard delegates to `manage-config effort apply-preset`, which **completely overwrites** the `models` block with the preset payload. Per-role values come from the `EffortPresets` constant-class in [`plan-marshall/scripts/effort_presets.py`](../../plan-marshall/scripts/effort_presets.py); validation against the level enum from [`plan-marshall:plan-marshall/standards/effort-levels.md`](../../plan-marshall/standards/effort-levels.md) is enforced at constant-class construction (an import-time `_validate_preset` self-check) and re-validated defense-in-depth at write time inside `manage-config`. The new preset takes effect on the next dispatch — the resolver reads `marshal.json` fresh per call, so no Claude Code restart is required.

> For per-role fine-tuning beyond the three presets, edit `.plan/marshal.json` directly. The wizard intentionally does not expose per-role editing — the preset-then-manual-edit split keeps the wizard small and the tweak point obvious.

This document is the contract. The wizard implementation in `SKILL.md` (Main Menu Option 4) loads this file when the user picks "Models".

## Entry Point

The Effort submenu is reached from the Main Menu (Option 4 — see `SKILL.md` § Main Menu). When the user selects it:

```
Read standards/effort-menu.md
```

Then execute the workflow described below.

## Workflow

### Step 1: Show Current State

Read the current `models` block from `.plan/marshal.json` and identify which preset (if any) it matches by deep-equality against `EffortPresets.ECONOMIC`, `EffortPresets.BALANCED`, and `EffortPresets.HIGH_END`. Display one of:

- `Current: economic preset` — when the on-disk block is exactly equal to `EffortPresets.ECONOMIC`.
- `Current: balanced preset` — when the on-disk block is exactly equal to `EffortPresets.BALANCED`.
- `Current: high-end preset` — when the on-disk block is exactly equal to `EffortPresets.HIGH_END`.
- `Current: custom (manually edited)` — when a `models` block exists but does not match any preset.
- `Current: not configured — defaults apply` — when the `models` block is absent or empty.

The display walks `EffortPresets.all_names()` to produce the deep-equality comparison set, so any future preset added to `effort_presets.py` is automatically picked up here without further wizard changes.

### Step 2: Preset Selection

Single `AskUserQuestion` with four options. Each preset's description is sourced verbatim from `EffortPresets.describe(name)` so the wizard never duplicates the preset's per-role rationale.

```
AskUserQuestion:
  question: "Effort submenu — pick a preset"
  header: "Models"
  options:
    - label: "Apply economic preset"
      description: <EffortPresets.describe("economic")>
    - label: "Apply balanced preset"
      description: <EffortPresets.describe("balanced")>
    - label: "Apply high-end preset"
      description: <EffortPresets.describe("high-end")>
    - label: "Back to Main Menu"
      description: "Return without changes"
  multiSelect: false
```

### Step 3: Persist

When the user picks any of the three preset options, call:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  models apply-preset --preset <name>
```

with `<name>` set to the canonical preset name (`economic`, `balanced`, or `high-end`). The script completely overwrites the `models` block — any keys present in the previous block but absent from the preset are gone after the write.

After a successful save:

1. Print the confirmation: `Saved: applied preset '<name>'`.
2. Return to the **Main Menu** (not back into the Effort submenu — the user is now done).

When the user picks "Back to Main Menu" in Step 2, return to the Main Menu without making any changes.

## Cross-References

| Document | Content |
|----------|---------|
| [`effort-levels.md`](../../plan-marshall/standards/effort-levels.md) | Level enum and primitive binding. |
| [`effort-roles.md`](../../plan-marshall/standards/effort-roles.md) | Role registry that the presets cover. |
| [`effort-variants.md`](../../plan-marshall/standards/effort-variants.md) | User-facing centralised guide cross-linked from save confirmations. |
| [`effort_presets.py`](../../plan-marshall/scripts/effort_presets.py) | `EffortPresets` constant-class — per-preset payloads, `get`, `all_names`, `describe`. |
| `manage-config:_cmd_effort.py` | Resolver that reads the same `models` block written by this wizard, plus `apply-preset` writer. |
