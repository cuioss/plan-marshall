---
lane:
  class: core
  cost_size: XS
name: default:record-metrics
description: Record final plan metrics before archive
order: 998
default_on: true
presets:
  - local
  - standard
  - full
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Record Metrics

Pure executor for the `record-metrics` finalize step. Closes out the 6-finalize phase and produces the final plan metrics report before the plan is archived.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `record-metrics` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

 This step performs three sequenced `manage-metrics` invocations — `end-phase`, `enrich`, `generate` — and emits the `mark-step-done` handshake. The `generate` invocation now reconciles all six canonical phases explicitly and returns a first-class completeness verdict; when that verdict is partial, the step also surfaces the unrecorded-phase gap as a `[WARN]` work-log line (see `## Surface Unrecorded-Phase Gaps`). All three writes MUST land on the live plan directory; the consolidated finalize output (step outcomes, end-state verification, and plan-complete summary) is rendered by the dedicated template in `standards/output-template.md`.

**CRITICAL**: `default:record-metrics` MUST be the LAST token-accounting step in the pipeline — it runs AFTER all token-consuming finalize steps (`plan-marshall:plan-retrospective`, `project:finalize-step-lessons-housekeeping`) and BEFORE the read-only `default:finalize-step-print-phase-breakdown` / `default:archive-plan` tail. This ordering is what lets `end-phase` fold the token spend of every dispatched finalize step — including retrospective and lessons-housekeeping — into the closed `6-finalize` phase row: those steps persist their `<usage>` totals to `work/metrics-accumulator-6-finalize.toon` before this step runs, so `end-phase`'s accumulator read captures the full phase total. All three metrics commands (`end-phase`, `enrich`, `generate`) write inside `.plan/plans/{plan_id}/` — `end-phase` updates `work/metrics.toon`, `enrich` supplements the same TOON with JSONL session tokens, and `generate` renders `metrics.md`. All three writes MUST land on the live (pre-archive) plan directory: `default:archive-plan` then moves that directory to `.plan/archived-plans/{date}-{plan_id}/`, so if archive ran first the live directory would no longer exist and any of the three commands would recreate it as a post-archive orphan.

## Record Phase End for 6-Finalize

Close out the 6-finalize phase timing/token ledger. The agent-dispatched steps (`create-pr`, `automated-review`, `sonar-roundtrip`, `lessons-capture`) persist their `<usage>` totals to `.plan/plans/{plan_id}/work/metrics-accumulator-6-finalize.toon` via `manage-metrics accumulate-agent-usage` from SKILL.md Step 3 step 5b. `end-phase` reads that accumulator file as a fallback when no explicit token flags are passed:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics end-phase \
  --plan-id {plan_id} --phase 6-finalize
```

The script reads `work/metrics-accumulator-6-finalize.toon` and incorporates its `total_tokens` / `tool_uses` / `duration_ms` into the closed phase row. It ALSO resolves `retrospective_tokens` from the same accumulator fallback: when the opt-in retrospective step ran, SKILL.md Step 3 step 5b forwarded its `<usage>` total via `accumulate-agent-usage --retrospective-tokens`, so the accumulator carries a non-zero `retrospective_tokens` value that `end-phase` reads back into the closed phase row as `[6-finalize].retrospective_tokens`. No `--retrospective-tokens` flag is added to the `end-phase` call above — the value is picked up from the accumulator exactly like the other token fields. When no retrospective ran, the accumulator carries no `retrospective_tokens` (or zero) and the field is absent from the closed phase row — the documented degrade where the audit's `effective = total_tokens - retrospective_tokens` exclusion subtracts nothing. The accumulator file is left in `work/` for audit (see `manage-metrics/standards/data-format.md` § "Per-Phase Subagent Accumulator"). If no agent-dispatched steps ran (all configured steps were inline-only), the accumulator file is absent and `end-phase` records the phase boundary from its own timestamps only — no special handling required.

## Enrich Session Tokens

Supplement the phase ledger with main-context token usage captured from the host-platform transcript JSONL. `session_id` is the current host-platform session id, passed down from the skill caller (see SKILL.md "Input Parameters"):

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics enrich \
  --plan-id {plan_id} --session-id {session_id}
```

An **inline** 6-finalize step (one that runs in the orchestrator's own context rather than a dispatched subagent) produces no `<usage>` envelope and no accumulator contribution — there is no per-step `<usage>` source to read. Its cost is nonetheless captured by `enrich`'s phase-window attribution: `enrich` sums the parent-window `message.usage` (input/output/cache_read/cache_creation) into the `6-finalize` row. When a phase carries BOTH a dispatched `total_tokens` (from the agent-dispatched steps above) AND non-zero four-field usage (the inline signature), `enrich` surfaces the inline contribution as a distinct `inline_main_context_tokens` field — `input + output + cache_creation`, excluding `cache_read` to match the dispatched-`<usage>` total definition. This field is surfaced ALONGSIDE the dispatched `total_tokens` (explicit-wins — it never overwrites it) and rendered as a reconciliation line under the phase total in `metrics.md`. See `manage-metrics/standards/data-format.md` § "Inline Main-Context Attribution" for the field schema. Inline step cost is therefore attributed via this phase-window path, NOT via a per-step `<usage>` (which does not exist for an inline step).

## Generate Final Metrics Report

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics generate \
  --plan-id {plan_id}
```

`generate` reconciles **all six canonical phases** explicitly rather than silently summing whichever boundary rows happen to be present: it folds each phase's durable `work/metrics-accumulator-{phase}.toon` into the phase row when no boundary closed it, and it stamps a first-class completeness verdict (`partial` + `unrecorded_phases`) computed over the canonical-six baseline. This is what lets an interrupted / loop-back / never-reached `6-finalize` close surface its accrued tokens and its gap instead of producing a complete-looking under-count. The reconciliation behavior and the partiality field schema are owned by `manage-metrics` — see `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md` § "Partiality (Completeness Verdict)" for the field schema, the recorded-phase predicate, and the floor-not-truth semantics; this step consumes the returned verdict, it does not re-derive it.

Capture the following fields from the returned TOON for the parent skill's output contract:

- `total_duration_seconds` — raw integer/float seconds, kept for the output contract's machine-readable column.
- `total_tokens` — raw integer count, kept for the output contract's machine-readable column.
- `total_duration_formatted` — human-readable string produced by `format_duration` (e.g. `1h46m`, `9m32s`).
- `total_tokens_formatted` — abbreviated string produced by `format_tokens_short` (e.g. `599K`, `1.2M`).
- `partial` — bool completeness verdict; `true` when at least one canonical phase lacks a recorded boundary. Drives the gap-surfacing `[WARN]` step below and the `partial` field in the output contract.
- `unrecorded_phases` — list of canonical phases lacking a recorded boundary (empty when `partial` is `false`). Named in the `[WARN]` log line and surfaced in the output contract.
- `file` — relative path to `metrics.md`.

The two `_formatted` fields are the canonical inputs for the `--display-detail` payload below. The raw fields remain available to consumers (and to the output-template renderer) that need machine-readable values.

## Surface Unrecorded-Phase Gaps

`generate` returns a first-class completeness verdict (see `## Generate Final Metrics Report` above). When `partial` is `true`, at least one canonical phase was never closed by its boundary — the canonical case is a `6-finalize` whose terminal `record-metrics` close never folded its durable accumulator in (interrupt / loop-back / never-reached). Surface the gap as a `[WARN]` work-log entry naming the unrecorded phases so the dropped attribution is visible in the audit trail instead of being silently archived:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING --message "[WARN] (plan-marshall:phase-6-finalize:record-metrics) Partial metrics — unrecorded canonical phases: {unrecorded_phases}. Aggregate totals are a floor, not a complete accounting."
```

Emit this line ONLY when the captured `partial` is `true`. When `partial` is `false` (all six canonical phases recorded), skip it — there is no gap to surface. Surfacing the gap NEVER blocks archive: the `[WARN]` line is informational, and the step proceeds to `## Log Artifact` and on to `default:archive-plan` regardless.

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

A `partial: true` verdict from a **successful** `generate` is NOT an error condition — it is the expected first-class signal that a canonical phase boundary was dropped, not a script failure. The gap is recorded as the `partial` flag (persisted in `metrics.toon` and surfaced in this step's output contract) plus the `[WARN]` work-log line from `## Surface Unrecorded-Phase Gaps`, never as a silent omission. The never-block-archive guarantee holds uniformly across all three outcomes: a non-success status logs `[ERROR]` and continues; a partial-but-successful generate logs `[WARN]` and continues; a fully-recorded generate logs neither. Archive always proceeds.

## Output Contract

This step populates the following fields in the parent skill's `metrics` output block:

| Field | Source |
|-------|--------|
| `metrics.total_duration_seconds` | `total_duration_seconds` from generate output (raw seconds) |
| `metrics.total_tokens` | `total_tokens` from generate output (raw count) |
| `metrics.total_duration_formatted` | `total_duration_formatted` from generate output (e.g. `1h46m`) |
| `metrics.total_tokens_formatted` | `total_tokens_formatted` from generate output (e.g. `599K`) |
| `metrics.partial` | `partial` from generate output (bool completeness verdict; `true` when a canonical phase boundary was dropped) |
| `metrics.unrecorded_phases` | `unrecorded_phases` from generate output (canonical phases lacking a recorded boundary; empty when `partial` is `false`) |
| `metrics.metrics_file` | `.plan/archived-plans/{date}-{plan_id}/metrics.md` (post-archive resolved path) |

Per-step outcome tables, end-state verification, and the plan-complete summary are NOT part of this step's output contract — those live in `standards/output-template.md` and are rendered by the finalize output renderer after all steps have completed.

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. This MUST happen before `default:archive-plan` runs, because archive moves `status.json` out of `.plan/plans/{plan_id}/` and `mark-step-done` would no longer find the plan.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the core metrics without re-reading `metrics.md`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step record-metrics --outcome done \
  --display-detail "{total_duration_formatted} / {total_tokens_formatted} tokens"
```

The `{total_duration_formatted}` and `{total_tokens_formatted}` placeholders are populated from the fields captured in `## Generate Final Metrics Report` above. Use the formatted variants — never the raw `{total_duration_seconds}s / {total_tokens} tokens` template, which produces the unformatted `6381s / 599089 tokens` row that the central formatter exists to replace.

When the captured `partial` is `true`, append a ` (partial: {unrecorded_phases})` suffix to the `--display-detail` value so the dropped-phase gap is visible in the finalize output (e.g. `"9m32s / 86.8K tokens (partial: 6-finalize)"`). When `partial` is `false`, use the unsuffixed form.
