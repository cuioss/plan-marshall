---
name: default:record-metrics
description: Record final plan metrics before archive
order: 990
---

# Record Metrics

Close out the 6-finalize phase and produce the final plan metrics report before the plan is archived. This step performs three sequenced `manage-metrics` invocations — `end-phase`, `enrich`, `generate` — and emits the `mark-step-done` handshake. All three writes MUST land on the live plan directory; the consolidated finalize output (step outcomes, end-state verification, and plan-complete summary) is rendered by the dedicated template in `standards/output-template.md`.

**CRITICAL**: `default:record-metrics` MUST immediately precede `default:archive-plan` in the pipeline. All three metrics commands (`end-phase`, `enrich`, `generate`) write inside `.plan/plans/{plan_id}/` — `end-phase` updates `work/metrics.toon`, `enrich` supplements the same TOON with JSONL session tokens, and `generate` renders `metrics.md`. `default:archive-plan` then moves that directory to `.plan/archived-plans/{date}-{plan_id}/`. If archive runs first, the live directory no longer exists and any of the three commands would recreate it as a post-archive orphan.

## Record Phase End for 6-Finalize

Close out the 6-finalize phase timing/token ledger using the running totals aggregated by the SKILL.md Step 3 FOR loop for every agent-dispatched step (`create-pr`, `automated-review`, `sonar-roundtrip`, `knowledge-capture`, `lessons-capture`). The loop maintains `{total_tokens, tool_uses, duration_ms}` running sums in model context; pass those accumulated values here.

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics end-phase \
  --plan-id {plan_id} --phase 6-finalize \
  --total-tokens {sum of total_tokens from agent-dispatched step <usage> tags} \
  --tool-uses {sum of tool_uses from agent-dispatched step <usage> tags} \
  --duration-ms {sum of duration_ms from agent-dispatched step <usage> tags}
```

If no agent-dispatched steps ran (all configured steps were inline-only), omit the three token/duration flags — `end-phase` records the phase boundary from its own timestamps.

## Enrich Session Tokens

Supplement the phase ledger with main-context token usage captured from the Claude Code transcript JSONL. `session_id` is the current Claude Code conversation ID, passed down from the skill caller (see SKILL.md "Input Parameters"):

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics enrich \
  --plan-id {plan_id} --session-id {session_id}
```

## Generate Final Metrics Report

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics generate \
  --plan-id {plan_id}
```

Capture the following fields from the returned TOON for the parent skill's output contract:

- `total_duration_seconds`
- `total_tokens`
- `file` (relative path to `metrics.md`)

These values are also reused below as the `--display-detail` payload for `mark-step-done` and as inputs to the output-template renderer.

## Log Artifact

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (plan-marshall:phase-6-finalize:record-metrics) metrics.md generated — {total_tokens} tokens, {total_duration_seconds}s"
```

## Error Handling

If any of `end-phase`, `enrich`, or `generate` returns a non-success status, log the error to work.log and continue to the next metrics command and then to archive — metrics recording must never block the archive step.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize:record-metrics) {command} failed — {error_message}"
```

## Output Contract

This step populates the following fields in the parent skill's `metrics` output block:

| Field | Source |
|-------|--------|
| `metrics.total_duration_seconds` | `total_duration_seconds` from generate output |
| `metrics.total_tokens` | `total_tokens` from generate output |
| `metrics.metrics_file` | `.plan/archived-plans/{date}-{plan_id}/metrics.md` (post-archive resolved path) |

Per-step outcome tables, end-state verification, and the plan-complete summary are NOT part of this step's output contract — those live in `standards/output-template.md` and are rendered by the finalize output renderer after all steps have completed.

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. This MUST happen before `default:archive-plan` runs, because archive moves `status.json` out of `.plan/plans/{plan_id}/` and `mark-step-done` would no longer find the plan.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the core metrics without re-reading `metrics.md`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step record-metrics --outcome done \
  --display-detail "{total_duration_seconds}s / {total_tokens} tokens"
```

The `{total_duration_seconds}` and `{total_tokens}` placeholders are populated from the fields captured in `## Generate Final Metrics Report` above.
