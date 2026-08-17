# Check: input-integrity (per-plan health + corpus data_confidence summary)

The **no-false-healthy FOUNDATION** for the whole audit. Every other check reads
a subset of a plan's structured inputs and reports the signals it derives from
them. If those inputs are absent or under-recorded, a peer check's "no findings"
verdict is a **FALSE HEALTHY** — the check saw nothing because there was nothing
to see, not because the plan was clean. This check makes that distinction
explicit and deterministic.

It is a **per-plan** check (one health row per scanned plan) that ALSO emits a
corpus `data_confidence` summary header. The deterministic computation lives in
`scripts/audit.py` (`check_input_integrity` / `emit_input_integrity_block`); this
sub-document is the interpretation guide and the source of the standing
cross-check obligation every other check owes this verdict.

## Inputs the check reads

The canonical per-plan input set — the artifacts the downstream checks depend on:

| Input | Path | Consumed by |
|-------|------|-------------|
| Execution manifest | `execution.toon` | execution-context-manifest |
| Per-phase metrics | `work/metrics.toon` | metrics, token-efficiency-trend, token-economics, global-log windows |
| References / footprint | `references.json` | scope-estimate-accuracy, task-count-efficiency, token-economics |
| Tasks | `tasks/TASK-*.json` | task-count-efficiency, token-economics |
| Findings | `artifacts/findings/*.jsonl` | quality-verification-report, recurring-pattern-detector, quality-chain |
| Script-execution log | `logs/script-execution.log` | sequence-and-build-minimality |
| Work log | `logs/work.log` | sequence-and-build-minimality phase attribution |

## Per-plan health columns

Presence/health booleans (`true` / `false`) for the canonical input set:

| Column | True when |
|--------|-----------|
| `has_execution` | `execution.toon` is present. |
| `has_metrics` | `work/metrics.toon` is present. |
| `has_references` | `references.json` is present. |
| `has_tasks` | `tasks/` exists with at least one `TASK-*.json`. |
| `has_findings` | `artifacts/findings/` exists with at least one `*.jsonl`. |
| `has_script_log` | `logs/script-execution.log` is present and non-empty. |

`has_findings` is the one OPTIONAL artifact: a clean plan may legitimately have
recorded zero findings, so an absent findings dir alone does NOT fire a flag or
escalate the `data_confidence` bucket. The other five inputs are expected on any
plan that ran a full lifecycle.

## The three flags

These are the input-health defects that silently FLOOR every downstream check:

| Flag | Fires when | Why it floors downstream checks |
|------|------------|---------------------------------|
| `metrics_blind` | Any data-bearing phase (`4-plan`, `5-execute`, `6-finalize`) recorded **zero** tokens **that #812's `phases_missing_end_time` markers do NOT explain**. The cell lists the genuinely-blind phase names (`;`-joined). | A zero-token phase means every token-economics and token-trend number for that phase is under-counted. The **5-execute** case is load-bearing — a genuinely-blind execute escalates the plan to the `blind` data_confidence bucket. A phase listed in `phases_missing_end_time` was never closed by design (see the #812 note below) and is EXCLUDED from this flag. On an `old-schema` or `pre-#812` record no phase is explained, so a zero-token phase there DOES fire this flag — read it alongside `metrics_marker_schema`. A phase that ran entirely inline is not blind either — see the inline-phase carve-out below for why that holds without a branch in this check. |
| `incomplete_lifecycle` | The plan never recorded a `5-execute` OR a `6-finalize` section in `metrics.toon`. The cell lists the missing phase names. | The plan did not run to completion through the recorded lifecycle, so completeness-dependent checks (pr-merge-velocity, quality-chain resolution) read a truncated history. |
| `missing_dispatch_markers` | `logs/work.log` carries no `[DISPATCH] role=phase-N` line. | The sequence-and-build-minimality phase attribution cannot bucket calls into phases — it folds everything into `1-init` (the finalize-fold conflation caveat in that check's sub-doc). |

## Corpus data_confidence summary

A three-bucket tally over the scanned plans, emitted as summary lines above the
per-plan rows:

| Bucket | A plan lands here when |
|--------|-----------------------|
| `fully-recorded` | No flag fired: every canonical input present, no blind phase, a complete lifecycle, dispatch markers present, **and** the #812 marker record readable (`metrics_marker_schema: current`). |
| `partial` | At least one input absent, or a non-execute zero-token phase / incomplete lifecycle / missing dispatch markers — **but the 5-execute phase DID record a usable token figure** (not blind); OR the 5-execute phase's missing figure is one #812's `phases_missing_end_time` markers explain; OR the marker record is UNREADABLE (`old-schema` / `pre-#812`). |
| `blind` | The **5-execute** phase carries no usable token figure — it recorded zero tokens, **or it is absent from `metrics.toon` entirely** — and the #812 markers do NOT explain it. Every downstream number for these plans is a FLOOR. |

The bucket precedence is `blind` > `partial` > `fully-recorded`: a genuinely-blind
execute wins regardless of other inputs. A #812-marker-explained missing execute
figure is `partial`, NEVER `blind` and NEVER the false-healthy `fully-recorded`.

⛔ **An ABSENT 5-execute phase is blind, not merely partial**, and the ordering is
the reason. The predicate previously tested the recorded value for equality with
zero, which is false when the phase is absent — so its precondition was the
presence of the very record whose absence it exists to detect, leaving it vacuous
at exactly the value it was written to catch. The result was an inverted severity:
a plan recording `5-execute` at zero graded `blind`, while a plan with no
`5-execute` section at all — strictly less recorded — graded only `partial`.
Absence is never better-recorded than a recorded zero, so it can never grade
milder.

`metrics_blind` still lists only phases that RECORDED a zero; an absent phase is
reported by `incomplete_lifecycle`, which is a different fact. The two columns stay
distinct — it is the confidence BUCKET that must not rank absence below a zero.

**An unreadable marker record can never be `fully-recorded`.** When
`metrics_marker_schema` is `old-schema` or `pre-#812`, the check could not
establish that the plan is fully recorded — and "could not establish" is not
"established clean". Such a plan is bucketed `partial` with its schema named in
its own column, so the reason is visible rather than inferred.

### The inline-phase carve-out (why a zero-dispatch phase is not blind)

`metrics_blind` reads `total_tokens` as the evidence that a phase recorded
something. That field does **not** always measure the dispatched-subagent
population: on a phase that dispatched nothing, `manage-metrics enrich` folds the
phase window's main-context `message.usage` sum into `total_tokens`, and the row
carries `total_tokens_population: inline` to say so (see
`manage-metrics/standards/data-format.md` § "Inline Main-Context Attribution").

That fold is what keeps this check correct, and the dependency runs one way:

- An inline-only phase really did cost tokens — it ran in the orchestrator's own
  context instead of a dispatched leaf. Its cost is a recorded measurement, not a
  gap, so it must NOT read as blind.
- The fold is what makes `total_tokens` non-zero for such a phase, so
  `metrics_blind` does not fire on it. This check therefore gets the inline
  carve-out **for free from the recorder** — it needs no inline-specific branch
  of its own, and it deliberately has none.
- `4-plan` and `5-execute` are dispatch-driven, so the load-bearing execute
  blindness signal is unaffected either way. The carve-out is reachable only for
  a `6-finalize` whose configured steps all ran inline.

**Standing coupling — do not remove the fold without changing this check first.**
If `enrich` ever stops folding the inline sum into `total_tokens` (leaving the
figure only under `inline_main_context_tokens`), every inline-only data-bearing
phase would start reporting zero and `metrics_blind` would fire corpus-wide on
plans that recorded their cost correctly. The predicate would then need to read
`total_tokens_population` and treat an `inline` row carrying a non-zero
`inline_main_context_tokens` as recorded. Until that happens the predicate stays
as written: this note records the dependency so the coupling is visible from the
consumer side, where the breakage would surface.

### #812 `end_time`-presence markers, and the three schema states

`manage-metrics` (#812) stamps top-level `any_phase_missing_end_time` /
`phases_missing_end_time` scalars on `metrics.toon`: a canonical phase whose row
carries no `end_time` boundary marker is listed in `phases_missing_end_time`.
This check reads them via `parse_metrics_end_time_presence` and consumes the
signal instead of inferring blindness from zero tokens alone. The distinction is
load-bearing for no-false-healthy: an execute figure the recorder deliberately
declared never-closed is an **explained gap** (bucket `partial`), whereas an
UNEXPLAINED missing execute figure — recorded-zero or absent alike — is genuine
**blindness** (bucket `blind`).

The markers report one predicate — `end_time` presence — and nothing wider. A
phase absent from `phases_missing_end_time` carries its boundary marker; that is
not a statement that its figures are complete or internally consistent.

The reader is **three-state**, and this check reports the state in its own
`metrics_marker_schema` column:

| `metrics_marker_schema` | Meaning | Effect here |
|--------------------------|---------|-------------|
| `current` | the new keys are present | markers read normally |
| `old-schema` | the new keys are absent AND a retired `partial` / `unrecorded_phases` key is present | NO phase is explained, and the plan cannot be `fully-recorded`. The record HAS markers, under retired names this reader deliberately does not interpret — a re-read of the archive could still recover them |
| `pre-#812` | neither the new nor the retired keys are present | NO phase is explained, and the plan cannot be `fully-recorded`. Nothing to recover — the record predates the markers |

The two unreadable states are reported **separately and never collapsed**.
Reading an `old-schema` record as the `pre-#812` degrade — or either as a clean
verdict — would manufacture a verdict from an absent key.

**Name collision — do NOT rename the bucket.** The `data_confidence` bucket value
`partial` in this check is an audit-local bucket name with no relation to the
retired `metrics.toon` key of the same spelling. It is unchanged by the #812
rename and must stay `partial`; renaming it would corrupt this taxonomy.

## Emitted columns

```
plans_scanned: N
data_confidence_fully_recorded: F
data_confidence_partial: P
data_confidence_blind: B
blind_plan_ids: "id1;id2"
genuine_signal_count: G
rows[N]{plan_id,has_execution,has_metrics,has_references,has_tasks,has_findings,has_script_log,metrics_blind,incomplete_lifecycle,missing_dispatch_markers,data_confidence,metrics_marker_schema,severity}
```

| Column | Meaning |
|--------|---------|
| `has_*` | The six presence/health booleans above. |
| `metrics_blind` | `;`-joined blind data-bearing phase names, or empty. |
| `incomplete_lifecycle` | `;`-joined missing lifecycle phase names (`5-execute` / `6-finalize`), or empty. |
| `missing_dispatch_markers` | `true` when no dispatch marker exists, else empty. |
| `data_confidence` | The per-plan bucket (`fully-recorded` / `partial` / `blind`). |
| `metrics_marker_schema` | Which of the three #812 marker states the plan's `metrics.toon` was in (`current` / `old-schema` / `pre-#812`). Anything but `current` bars the `fully-recorded` bucket. |
| `severity` | Uniform D1 severity column: `genuine` when any of the three flags fired, `informational` otherwise. |

`genuine_signal_count` counts the rows with a real input-health defect. A
`fully-recorded` plan, or a plan whose only gap is the optional findings file, is
`informational`.

## The cross-check obligation (standing rule for EVERY other check)

This check's verdict is the **deterministic foundation for no-false-healthy
enforcement**. Every other check MUST consume it:

1. **Annotate floored rows.** Any row a peer check derives from a plan this check
   marks `metrics_blind` (especially a `blind`-bucket plan) MUST be annotated
   **"floor, not truth"** in the adjudication. A token-economics or token-trend
   number computed over a blind execute is an under-count, not a measurement.
2. **No "all healthy" over blind-input plans.** A check MAY NOT conclude "all
   healthy" / "no findings" for the corpus while `data_confidence_blind > 0`. The
   blind plans' downstream rows are floors — absence of a signal there is absence
   of *recorded data*, not absence of a problem. The conclusion must instead read
   "no findings among fully-recorded plans; the N blind plans are floored and
   cannot be cleared".
3. **Name the blind plans.** When dismissing a blind plan's row as "no signal",
   the dismissal MUST cite this check's `blind_plan_ids` list as the reason the
   row cannot be cleared, not generalize it to a healthy verdict.

This obligation is mirrored in SKILL.md's Step 3 (per-row adjudication) and Step
4b (the review-completeness gate): the gate cannot truthfully reach "no findings"
while any plan is `blind` here.

## How the orchestrator interprets the rows

- **`data_confidence: blind`** — highest-priority structural signal. The plan's
  execute phase recorded zero tokens **with no #812 marker to explain it**; every
  downstream token number for it is a floor. Do NOT clear any of the plan's
  peer-check rows as healthy. If the blind recording recurs across plans created
  after a metrics-recording fix shipped, that recurrence is the file-worthy signal
  (the recording defect itself), routed through the three-gate policy. A
  marker-explained zero-token execute is NOT here — it is `partial`, and the gap
  is a recorded design fact, not a defect to file.
- **`metrics_marker_schema: old-schema` / `pre-#812`** — the plan's marker record
  could not be read, so nothing about it was established. Read the plan as
  `partial` and every figure derived from it as a floor. `old-schema` is the
  actionable one: the record HAS markers under retired names, so a re-read of the
  archive could recover them. `pre-#812` is terminal history. Do NOT treat either
  as a clean verdict, and do NOT collapse them into one "unreadable" note — the
  distinction is what tells you which archives are recoverable.
- **`metrics_blind` (non-execute phase)** — a `4-plan` or `6-finalize` zero-token
  recording. Flags the specific phase as under-counted; the plan stays `partial`
  (not `blind`) because the load-bearing execute phase still recorded data.
  Annotate the affected phase's downstream numbers as floored.
- **`incomplete_lifecycle`** — the plan stopped before recording execute or
  finalize. Cross-read with pr-merge-velocity (likely `applicable: false`) and
  quality-chain (truncated resolution history); do not read a missing PR as "no
  PR was needed".
- **`missing_dispatch_markers`** — the sequence-and-build-minimality phase graph
  for this plan folds into `1-init`. Read that check's per-phase attribution for
  the plan as unreliable (the finalize-fold conflation caveat).
- **`fully-recorded` / `informational`** — a clean input surface. The plan's peer
  rows can be read at face value. Still adjudicate each peer row on its own
  merits; a clean input surface clears the *floor*, not the *signals*.

Per the SKILL.md Step-3 contract, EVERY emitted row is adjudicated with a stated
verdict and cited evidence; a row may be dismissed as informational/expected ONLY
with a cited reason (the `severity: informational` cell, or the
`fully-recorded` bucket).

## Critical rules

- The script is the single source of truth for the input presence checks, the
  three flags, and the `data_confidence` bucketing. Do not re-stat the plan dirs
  or re-derive a flag in chat.
- The data-bearing phase set, the load-bearing execute phase, and the
  dispatch-marker grammar are module constants
  (`_II_DATA_BEARING_PHASES`, `_II_EXECUTE_PHASE`, `_II_DISPATCH_RE`). The #812
  `end_time`-presence markers are read by `parse_metrics_end_time_presence`
  (shared with the `metrics` and `billing-composition` checks). If the recorded
  lifecycle or the marker schema changes, edit `scripts/audit.py` rather than
  substituting a different reading.
- `total_tokens` is a population-discriminated field, not a dispatched-only one.
  A consumer that needs to know which population a phase's figure measures reads
  the row's `total_tokens_population` (`dispatched` / `inline` / `mixed`) — never
  the field name. `parse_metrics_toon` whitelists the keys it consumes, so the
  discriminator is currently ignored here by design (see the inline-phase
  carve-out for why this check does not need it).
- The cross-check obligation is NOT optional: a peer check that claims "all
  healthy" while this check reports a `blind` plan is producing a false healthy —
  the exact failure mode this check exists to block.
- This check is read-only; it never edits `.plan/` files.
