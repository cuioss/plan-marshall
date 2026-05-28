# Aspect: Plan Efficiency

How much time and how many tokens did the plan consume relative to its scope? LLM-driven; inputs come from `metrics.md` and log counts produced by `analyze-logs.py`.

## Inputs

- `metrics.md` — total_duration_seconds, total_tokens, per-phase breakdown.
- `log_analysis` fragment (already computed) — entry counts, script durations.
- `references.json` `affected_files` — scope size.

## TOON Fragment Shape

```toon
aspect: plan_efficiency
status: success
plan_id: {plan_id}
totals:
  duration_seconds: N
  tokens: N
  files_modified: N
  tasks_completed: N
ratios:
  tokens_per_file_modified: N
  seconds_per_task: N
phase_breakdown[*]{phase,duration_seconds,tokens}:
  1-init,N,N
  ...
findings[*]{severity,message}:
  info,"Plan completed in 45 minutes"
  warning,"4-plan consumed 60% of tokens — consider outline refinement"
```

## LLM Interpretation Rules

This section is the authoritative interpretation contract. The four sub-sections below are NOT advisory heuristics — they are MUST-style structural requirements. The LLM that produces the `fragment-plan-efficiency.toon` document MUST walk all four in order before writing any prose.

### 1. Mandatory ratio computation (walk this checklist BEFORE writing any prose)

For every plan, compute and embed the following four ratios explicitly under the `ratios:` block of the TOON fragment. All four are MUST-emit — omitting a field is a structural failure mode regardless of whether any threshold trips.

1. `tokens_per_file_modified` = `totals.tokens / max(totals.files_modified, 1)`
2. `seconds_per_task` = `totals.duration_seconds / max(totals.tasks_completed, 1)`
3. `max_phase_token_share` = `max(phase_breakdown[*].tokens) / totals.tokens` (as a fraction 0.0–1.0; emit two decimals)
4. `total_tokens_per_deliverable` = `totals.tokens / max(deliverable_count, 1)` where `deliverable_count` is the number of deliverables in the originating `solution_outline.md` (read this from the plan's `solution_outline.md` headings of the form `### N.` — count them).

The four computed values MUST appear under `ratios:` in the fragment alongside the `dominant_phase` derived from the `phase_breakdown[*]` row that contributed the most tokens. Do NOT round or truncate; emit the integer or two-decimal value verbatim.

### 2. Calibration anchors table (keyed on `(scope_estimate, change_type)`)

For each plan, look up the row matching the plan's `(scope_estimate, change_type)` combination. The row defines the warning and error thresholds for `total_tokens` against which Section 3 emits `[BUDGET]` findings. When the combination is NOT anchored in the table below, fall back to the four ratio thresholds in Section 1 (`tokens_per_file_modified > 50_000` warning; `seconds_per_task > 900` warning; `max_phase_token_share > 0.50` warning; `total_tokens_per_deliverable > 500_000` warning).

| scope_estimate | change_type | warning at | error at | reference |
|----------------|-------------|-----------:|---------:|-----------|
| surgical | bug_fix | ≥500K tokens / ≥30 min | ≥800K tokens / ≥45 min | `.plan/local/archived-plans/2026-05-27-deploy-target-sentinel-writer-computes-empty-inpu/` (958K incident — the canonical over-budget reference for this row) |
| surgical | feature | ≥600K tokens / ≥45 min | ≥1.0M tokens / ≥75 min | — |
| surgical | refactor | ≥600K tokens / ≥45 min | ≥1.0M tokens / ≥75 min | — |
| single_module | bug_fix | ≥800K tokens / ≥60 min | ≥1.3M tokens / ≥90 min | — |
| single_module | feature | ≥1.0M tokens / ≥75 min | ≥1.6M tokens / ≥120 min | — |
| single_module | refactor | ≥1.0M tokens / ≥75 min | ≥1.6M tokens / ≥120 min | — |
| cross_cutting | bug_fix | ≥1.2M tokens / ≥90 min | ≥2.0M tokens / ≥150 min | — |
| cross_cutting | feature | ≥1.5M tokens / ≥120 min | ≥2.5M tokens / ≥180 min | — |
| cross_cutting | refactor | ≥1.5M tokens / ≥120 min | ≥2.5M tokens / ≥180 min | — |
| complex | feature | ≥2.0M tokens / ≥180 min | ≥3.5M tokens / ≥240 min | — |
| complex | bug_fix | ≥1.5M tokens / ≥120 min | ≥2.5M tokens / ≥180 min | — |
| complex | refactor | ≥2.0M tokens / ≥180 min | ≥3.5M tokens / ≥240 min | — |

The 300K-token figure cited in earlier authoring as a `surgical + bug_fix` "expected ceiling" remains the design baseline — a surgical bug-fix plan that exceeds 300K but stays under 500K is "watch-list" territory and SHOULD prompt a one-line `info` finding even when neither warning nor error trips.

### 3. MANDATORY [BUDGET] finding emission contract

For every ratio in Section 1 that crosses a Section 2 anchor (or, when the row is unanchored, a Section 2 fallback ratio threshold), the fragment MUST include a finding entry with ALL FOUR of the fields below populated. Missing any field is a structural failure mode.

```toon
findings[*]{severity,message,metric,anchor,dominant_phase}:
  warning,"<one-line summary>","<metric name + computed value>","<scope+change_type anchor row + tripped threshold>","<dominant phase row>"
```

Field semantics:

- `severity` — `warning` when the anchor's warning column is tripped; `error` when the error column is tripped. Severity MUST match the column actually crossed.
- `message` — single-line human-readable summary. Include a human-readable summary of the computed value (e.g. `958K observed`); the exact verbatim integer goes in the `metric` field.
- `metric` — the metric name from Section 1 plus the computed value (e.g., `tokens_per_file_modified=479032`).
- `anchor` — the `(scope_estimate, change_type)` row in Section 2 that was matched, plus the tripped threshold (e.g., `surgical+bug_fix warning at 500K`).
- `dominant_phase` — the phase row from `phase_breakdown[*]` that contributed the most tokens, expressed as `{phase_name}={token_count}` (e.g., `5-execute=512000`).

`[BUDGET]` is a marker that retrospective consumers grep for — the literal string MUST appear in the `message` field for any finding emitted by this aspect when ANY anchor trips (e.g., `"[BUDGET] surgical bug-fix exceeded 500K-token warning anchor"`).

### 4. Filler-refusal rule (no "no findings" cop-out)

When `totals.tokens` exceeds ANY warning anchor for the plan's `(scope_estimate, change_type)` bucket (or, when unanchored, exceeds any of the Section 2 fallback ratio warning thresholds), emitting an empty `findings: []` is a structural failure mode. The LLM MUST emit at least one finding citing which anchor tripped — Section 3 mandates the field shape.

Bland descriptive prose like `"Plan completed in 1h54m"`, `"Phase 5 was the dominant contributor"`, or a generic info-severity finding without metric attribution is NOT an acceptable substitute. The filler-refusal rule is the operational counterpart to the MANDATORY emission contract in Section 3: Section 3 says what fields MUST appear when a threshold trips; Section 4 says that bypassing emission by writing only descriptive prose is itself the failure mode.

### Worked example — the 958K-token surgical bug-fix incident

The canonical over-budget reference for this aspect is `.plan/local/archived-plans/2026-05-27-deploy-target-sentinel-writer-computes-empty-inpu/`, a surgical bug-fix plan that consumed `total_tokens=958064` modifying `files_modified=2`. Working the four-section checklist:

1. **Section 1 ratio computation**: `tokens_per_file_modified = 958064 / 2 = 479032`. (Other ratios omitted from this example for brevity.)
2. **Section 2 anchor lookup**: row `surgical + bug_fix` — warning at 500K tokens, error at 800K. `totals.tokens=958064` crosses the **error** column.
3. **Section 3 finding emission**: required fragment entry:

   ```toon
   findings[1]{severity,message,metric,anchor,dominant_phase}:
     error,"[BUDGET] surgical bug-fix exceeded 800K-token error anchor (958K observed)","tokens_per_file_modified=479032","surgical+bug_fix error at 800K","5-execute=512000"
   ```

   Note the canonical naming: the `metric` field carries the Section-1 ratio that drove the decision (here, `tokens_per_file_modified`); the `anchor` field carries the Section-2 row and the tripped column; the `dominant_phase` field is read from the `phase_breakdown[*]` row contributing the largest token share.

4. **Section 4 filler-refusal**: emitting `findings: []` here is forbidden — the 958K total crosses both the warning AND the error anchor; at least one finding MUST be emitted, and a bland `"Plan took 1h54m"` info finding without the four mandatory fields does NOT satisfy the contract.

## Finding Shape

```toon
aspect: plan_efficiency
severity: info|warning|error
message: "{one-line, includes literal [BUDGET] marker on any anchor trip}"
metric: "{Section 1 ratio name = computed value}"
anchor: "{scope_estimate+change_type row + tripped column}"
dominant_phase: "{phase name = token count}"
```

The `anchor` and `dominant_phase` fields are MANDATORY on any finding emitted under the Section 3 contract (i.e., any time an anchor trips). They MAY be omitted from `info`-severity findings that are not driven by an anchor trip (e.g., a one-line summary noting the plan completed under all thresholds).

## Out of Scope

- Root-cause of individual slow scripts — log-analysis surfaces candidates; the detailed analysis is out of the retrospective's scope.
- Comparing against prior plans — this is a single-plan aspect.

## Persistence

After synthesizing the TOON fragment per the shape documented above, the orchestrator writes the fragment to `work/fragment-plan-efficiency.toon` via the `Write` tool and registers it with the bundle:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add \
  --plan-id {plan_id} --aspect plan-efficiency --fragment-file work/fragment-plan-efficiency.toon
```

`compile-report run --fragments-file` consumes the assembled bundle in Step 4 of SKILL.md. The bundle file is auto-deleted on successful report write; on failure it is retained for debugging.
