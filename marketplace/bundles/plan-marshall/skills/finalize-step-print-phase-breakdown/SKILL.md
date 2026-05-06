---
name: finalize-step-print-phase-breakdown
description: Optional finalize-summary mode that captures the Phase Breakdown table from metrics.md and writes it to work/phase-breakdown-output.txt for the renderer to inline in place of the per-step [OK] list
user-invocable: false
allowed-tools: Bash
order: 995
---

# Finalize Step: print-phase-breakdown

## Purpose

Optional finalize-summary mode that replaces the per-step `[OK]` Finalize-steps block with the verbatim `## Phase Breakdown` table content from `metrics.md`. When this skill is present in `manifest.phase_6.steps` (and runs successfully), the `phase-6-finalize` output renderer enters override mode and emits the captured breakdown content in place of the default per-step list. Useful for users who prefer the compact per-phase metrics view over the redundant `[OK]` summary.

The skill is a **producer** in the cross-deliverable contract documented in `phase-6-finalize/standards/output-template.md` (the consumer/renderer side). Both ends MUST reference the same artifact path verbatim:

- **Producer (this skill)** — writes `work/phase-breakdown-output.txt`.
- **Consumer (renderer)** — reads `work/phase-breakdown-output.txt` during the snapshot procedure, BEFORE `default:archive-plan` runs.

## Interface Contract

Invoked by `plan-marshall:phase-6-finalize` for projects that include `plan-marshall:finalize-step-print-phase-breakdown` in their `phase-6-finalize.steps` list.

Accepts the standard finalize-step arguments:

- `--plan-id` — plan identifier (required, used to scope all `manage-*` calls)
- `--iteration` — finalize iteration counter (accepted for contract compliance, no effect)

**Ordering constraint**: `order: 995` places this step AFTER `default:record-metrics` (order 990, which produces `metrics.md`) and BEFORE `default:archive-plan` (order 1000, which moves the plan directory). Do NOT relocate this step outside that window — the producer relies on `metrics.md` existing under `.plan/local/plans/{plan_id}/`, and the consumer (renderer snapshot) reads `work/phase-breakdown-output.txt` from the same live directory before archive moves it.

## Workflow

### Step 1: Capture the Phase Breakdown table

Invoke `manage-metrics print-phase-breakdown`, which reads `metrics.md` and prints the verbatim `## Phase Breakdown` section to stdout (no TOON status on success):

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics print-phase-breakdown \
  --plan-id {plan_id}
```

Capture stdout into a model-context variable `{breakdown_content}`. On non-zero exit code (script emitted error TOON to stdout instead of section content), proceed to Step 4 — Error Handling.

### Step 2: Persist captured content to work/phase-breakdown-output.txt

Write the captured content to the cross-deliverable artifact path so the renderer's snapshot procedure can read it before archive:

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files write \
  --plan-id {plan_id} --file work/phase-breakdown-output.txt --content "{breakdown_content}"
```

Capture `bytes_written` from the returned TOON.

### Step 3: Log artifact and mark step done

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[ARTIFACT] (plan-marshall:finalize-step-print-phase-breakdown) work/phase-breakdown-output.txt written ({bytes_written} bytes)"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step finalize-step-print-phase-breakdown --outcome done \
  --display-detail "Phase Breakdown table captured ({bytes_written} bytes)"
```

The `display_detail` string would normally appear in the renderer's per-step `[OK]` row, but in override mode the row is suppressed — the captured breakdown content is emitted instead. The detail is still recorded for the manifest/handshake invariants.

### Step 4: Error handling

When `manage-metrics print-phase-breakdown` returns an error (metrics.md missing, section missing, or any other non-success TOON):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARN \
  --message "[WARN] (plan-marshall:finalize-step-print-phase-breakdown) print-phase-breakdown failed: {error_message} — renderer will fall back to default Finalize-steps block"
```

Mark the step `failed` with a brief detail; the renderer's override-activation rule requires both manifest presence AND non-`None` captured content, so a failed step naturally falls back to the default block:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step finalize-step-print-phase-breakdown --outcome failed \
  --display-detail "{error_message}"
```

Finalize MUST continue — this step is presentation-only and never blocks plan completion.

## Error Handling

| Scenario | Action |
|----------|--------|
| `metrics.md` missing under live plan dir | Log `[WARN]`, mark `failed`, continue |
| `## Phase Breakdown` heading missing in `metrics.md` | Log `[WARN]`, mark `failed`, continue |
| `manage-files write` fails | Log `[WARN]`, mark `failed`, continue |
| Generator/script raises unhandled exception | Same — non-fatal |

## Related

- [marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md](../manage-metrics/SKILL.md) — `print-phase-breakdown` subcommand (the producer's data source)
- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/output-template.md](../phase-6-finalize/standards/output-template.md) — renderer (the consumer that reads `work/phase-breakdown-output.txt` and emits the override block)
- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/record-metrics.md](../phase-6-finalize/standards/record-metrics.md) — the previous-order step (990) that produces `metrics.md`
