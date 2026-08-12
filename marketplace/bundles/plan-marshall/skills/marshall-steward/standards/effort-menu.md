# Effort Submenu — UX Contract

> Wizard contract for editing the per-phase `effort` attributes of `.plan/marshal.json` from the `marshall-steward` Main Menu.

## Overview

The Effort submenu is a single preset-picker. The user chooses one of three named presets — `economic`, `balanced`, `high-end` — and the wizard delegates to `manage-config effort apply-preset`, which **completely overwrites** the per-phase effort configuration with the preset payload. Per-role values come from the `EffortPresets` constant-class in [`plan-marshall/scripts/effort_presets.py`](../../plan-marshall/scripts/effort_presets.py); validation against the level enum from [`plan-marshall:plan-marshall/standards/effort-levels.md`](../../plan-marshall/standards/effort-levels.md) is enforced at constant-class construction (an import-time `_validate_preset` self-check) and re-validated defense-in-depth at write time inside `manage-config`. The new preset takes effect on the next dispatch — the resolver reads `marshal.json` fresh per call, so no Claude Code restart is required.

> For per-role fine-tuning beyond the three presets, edit `.plan/marshal.json` directly. The wizard intentionally does not expose per-role editing — the preset-then-manual-edit split keeps the wizard small and the tweak point obvious.

This document is the contract. The wizard implementation in `SKILL.md` (Main Menu Option 4) loads this file when the user picks "Effort".

## Entry Point

The Effort submenu is reached from the Main Menu (Option 4 — see `SKILL.md` § Main Menu). When the user selects it:

```text
Read standards/effort-menu.md
```

Then execute the workflow described below.

## Workflow

### Step 1: Show Current State

Classify the project's current per-phase `effort` configuration with the deterministic recogniser — do **not** eyeball the deep-equality yourself:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config effort identify
```

It reconstructs the `{default, roles}` payload from `.plan/marshal.json` (the `plan.effort` plan-wide fallback plus every `plan.<phase>.effort` attribute) and returns a `match` verdict and a ready-to-print `message`. **Print the returned `message` verbatim.** It is one of:

- `Current: economic preset` / `Current: balanced preset` / `Current: high-end preset` — the on-disk config matches that current preset exactly (`match: current`).
- `Current: <name> preset (previous ladder) — the effort values predate the ladder re-spread; re-apply '<name>' to adopt the current values` — the config matches a **pre-respread** preset shape (`match: previous-ladder`). The configuration still works as-is; re-applying the named preset in Step 2 adopts the current (re-spread) values, which may raise that tier's cost, so it is the user's opt-in. Surface the named preset as the recommended choice.
- `Current: custom (manually edited)` — an effort configuration exists but matches no preset (`match: custom`).
- `Current: not configured — defaults apply` — no `effort` attributes are present (`match: not_configured`).

`effort identify` matches the current presets first and then the pre-respread shapes recorded in `EffortPresets._LEGACY_PRESETS`, so a value re-spread never silently reclassifies a working config as `custom`. The recogniser walks `EffortPresets.all_names()`, so any future preset added to `effort_presets.py` is picked up here without further wizard changes.

### Step 2: Preset Selection

Single `AskUserQuestion` with four options. Each preset's description is sourced verbatim from `EffortPresets.describe(name)` so the wizard never duplicates the preset's per-role rationale.

When Step 1 reported `match: previous-ladder`, mark the matching preset's option as the recommended choice (e.g. append `(recommended — re-applies the updated <name> values)` to its label) so the re-apply that adopts the re-spread values is the obvious pick.

```text
AskUserQuestion:
  question: "Effort submenu — pick a preset"
  header: "Effort"
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
  effort apply-preset --preset <name>
```

with `<name>` set to the canonical preset name (`economic`, `balanced`, or `high-end`). The script completely overwrites the per-phase effort configuration — any `effort` attributes present in the previous configuration but absent from the preset are gone after the write.

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
| `manage-config:_cmd_effort.py` | Resolver that reads the same per-phase `effort` configuration written by this wizard, plus `apply-preset` writer. |
