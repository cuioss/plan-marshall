---
name: default:finalize-step-print-phase-breakdown
description: Optional finalize-summary supplement that captures the Phase Breakdown table from metrics.md, writes it directly to work/phase-breakdown-output.txt, and lets the renderer append it after the per-step [OK] list
order: 995
---

# Finalize Step: print-phase-breakdown

Pure executor for the `default:finalize-step-print-phase-breakdown` finalize step. Drives `manage-metrics print-phase-breakdown`, which extracts the verbatim `## Phase Breakdown` table from `metrics.md` and writes it directly to `work/phase-breakdown-output.txt`. The renderer appends the captured content after the per-step `[OK]` Finalize-steps block.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — the failure mode documented in lesson `2026-04-29-23-002` (silent swallowing of `wrong_parameters` rejections). "Log and continue" is the prohibited anti-pattern.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `finalize-step-print-phase-breakdown` in `manifest.phase_6.steps` (bare name — the manifest holds un-prefixed step ids; the dispatcher prepends `default:` when looking up the dispatch-table row). When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

## Purpose

Optional finalize-summary supplement. When the step is in `manifest.phase_6.steps` (and runs successfully), the `phase-6-finalize` output renderer appends the captured breakdown content as an additional section AFTER the default per-step `[OK]` Finalize-steps block. Useful for users who want the compact per-phase metrics view alongside the per-step list. The per-step list (including the `record-metrics` row) emits unchanged — the breakdown supplements it rather than substituting for any row.

The step is the **producer** in the cross-deliverable contract documented in `output-template.md` (the consumer/renderer side). Both ends MUST reference the same artifact path verbatim:

- **Producer (this step)** — invokes `manage-metrics print-phase-breakdown`, which writes `work/phase-breakdown-output.txt` directly.
- **Consumer (renderer)** — reads `work/phase-breakdown-output.txt` during the snapshot procedure, BEFORE `default:archive-plan` runs. The captured content is appended as an additional section after the Finalize-steps block; the per-step list emits unchanged.

## Ordering constraint

`order: 995` places this step AFTER `default:record-metrics` (order 990, which produces `metrics.md`) and BEFORE `default:archive-plan` (order 1000, which moves the plan directory). Do NOT relocate this step outside that window — the producer relies on `metrics.md` existing under `.plan/local/plans/{plan_id}/`, and the consumer (renderer snapshot) reads `work/phase-breakdown-output.txt` from the same live directory before archive moves it.

## Workflow

### Step 1: Capture and persist the Phase Breakdown table

Invoke `manage-metrics print-phase-breakdown`. The script reads `metrics.md`, extracts the verbatim `## Phase Breakdown` section, writes it directly to `work/phase-breakdown-output.txt` under the live plan directory, and returns a TOON envelope:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics print-phase-breakdown \
  --plan-id {plan_id}
```

The success envelope shape is `{status: success, plan_id, file: work/phase-breakdown-output.txt, bytes_written}`. Capture `bytes_written` from the returned TOON. On non-zero exit (the script emitted an error TOON), proceed to Step 3 — Error Handling.

### Step 2: Log artifact and mark step done

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[ARTIFACT] (plan-marshall:phase-6-finalize:finalize-step-print-phase-breakdown) work/phase-breakdown-output.txt written ({bytes_written} bytes)"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step finalize-step-print-phase-breakdown --outcome done \
  --display-detail "Phase Breakdown table captured ({bytes_written} bytes)"
```

The `display_detail` string appears in the renderer's per-step `[OK]` row for this step; the captured breakdown content is emitted as an additional section after the Finalize-steps block (the per-step list, including the `record-metrics` row, emits unchanged). The detail is also recorded for the manifest/handshake invariants.

### Step 3: Error handling

When `manage-metrics print-phase-breakdown` returns an error (metrics.md missing, section missing, invalid output path, or any other non-success TOON):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARN \
  --message "[WARN] (plan-marshall:phase-6-finalize:finalize-step-print-phase-breakdown) print-phase-breakdown failed: {error_message} — renderer will fall back to default Finalize-steps block"
```

Mark the step `failed` with a brief detail; the renderer's supplement-activation rule requires both manifest presence AND non-`None` captured content, so a failed step naturally suppresses the appended breakdown section (the per-step Finalize-steps block emits unchanged either way):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step finalize-step-print-phase-breakdown --outcome failed \
  --display-detail "{error_message}"
```

Finalize MUST continue — this step is presentation-only and never blocks plan completion.

## Error Handling

| Scenario | Action |
|----------|--------|
| `metrics.md` missing under live plan dir | Log `[WARN]`, mark `failed`, continue |
| `## Phase Breakdown` heading missing in `metrics.md` | Log `[WARN]`, mark `failed`, continue |
| `manage-metrics print-phase-breakdown` returns any other error TOON | Log `[WARN]`, mark `failed`, continue |
| Generator/script raises unhandled exception | Same — non-fatal |

## Related

- [../../manage-metrics/SKILL.md](../../manage-metrics/SKILL.md) — `print-phase-breakdown` subcommand (the producer that writes the artifact directly)
- [output-template.md](output-template.md) — renderer (the consumer that reads `work/phase-breakdown-output.txt` and appends the supplement section)
- [record-metrics.md](record-metrics.md) — the previous-order step (990) that produces `metrics.md`
