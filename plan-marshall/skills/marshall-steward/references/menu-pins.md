# Pin Models — Operator Flow

> Wizard contract for materializing per-level model pins from the machine-local effort-to-model map. Reached from the Main Menu (Option 5 — see `SKILL.md` § Main Menu).

## Overview

The Pin models flow provisions this machine's models into the per-level dispatch chain. It reads the machine-local pin map, materializes which model each level provisions, emits the `level=model` pairs via `effort_pins` for the PLAN-01 post-resolve harness provisioning seam to apply, and spot-checks the `inherit` fallback on one unpinned slot. The levels themselves are chosen by the sibling Effort flow (see [effort-menu.md](../standards/effort-menu.md)); this flow only provisions models for them.

The map contract — machine-local location, PLAN-01 schema, both entry kinds, inherit preservation, and the never-escalate guard — lives in [pin-provisioning.md](../standards/pin-provisioning.md) and is not restated here.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Entry Point

The Pin models flow is reached from the Main Menu Page 2 (Option 5 — see `SKILL.md` § Main Menu). When the user selects it:

```text
Read references/menu-pins.md
```

Then execute the workflow described below.

## Workflow

### Step 1: Validate or Seed the Ladder

Check the machine-local effort ladder is readable and schema-valid before materializing anything:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:effort_pins validate
```

- **`status: success`** → the ladder is readable; `entries` names how many levels carry pins. Continue to Step 2.
- **`status: error`** → missing or malformed ladder. When missing, seed the standard default ladder:
  ```bash
  python3 .plan/execute-script.py plan-marshall:marshall-steward:effort_pins ensure-defaults
  ```
  This seeds Option 1 for Antigravity, canonical for Claude, and inherit for OpenCode into `.plan/local/effort-ladder.json`. A malformed map fails closed: report the `detail`, fix the file, and re-run this step.

### Step 2: Materialize

Emit the per-level pins for the active harness class or target:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:effort_pins materialize --harness open
```

The emitter is read-only — it writes nothing itself. `pins` carries one `level=model` pair per level; any level the map does not pin reads `inherit`. `guard_hits` counts entries the never-escalate guard held back to `inherit`. On the Claude target the flow returns `untouched` instead: the fixed alias-palette flow is never modified.

### Step 3: Hand Off to the Harness Provisioning Seam

Hand each emitted `level=model` pair to the harness provisioning seam, under the write-path rule [`pin-provisioning.md`](../standards/pin-provisioning.md) § Delegation Seam owns — including which surface may persist a pin and which may not. Follow it there; it is not restated here.

### Step 4: Verify the Inherit Fallback

Confirm one slot's unpinned level still resolves to the session model:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config effort resolve-target --phase phase-5-execute --role default
```

When the map leaves this slot's level unpinned, the call must return the canonical (`inherit`) target. A provisioned model the level was never pinned to is a defect — re-run Step 1 against the current map rather than editing the resolution. The per-level picture is Step 2's `pins`, not this call.

### Step 5: Re-Run on Map Change

The map is machine-local and may change at any time (a new local model, a rotated provider route). Re-run this flow whenever the map changes — materialization is idempotent, so re-running over an unchanged map is a no-op that reports the same pins.

After the flow completes, return to the **Main Menu** (not back into this flow).

## Cross-References

| Document | Content |
|----------|---------|
| [`pin-provisioning.md`](../standards/pin-provisioning.md) | Map contract — location, schema, entry kinds, never-escalate guard. |
| [`effort-menu.md`](../standards/effort-menu.md) | Sibling Effort preset-picker — chooses the levels this flow provisions. |
| [`effort_pins.py`](../scripts/effort_pins.py) | Deterministic pin-materialization script with the TOON output contract. |
