# Execution Manifest — Decision Rules

This standard codifies the decision matrix used by `manage-execution-manifest compose` to derive the per-plan execution manifest. The composer evaluates the rows in order; the **first matching row wins** and a single `decision.log` entry is emitted with the rule key, naming exactly which row fired.

## Inputs

| Input | Source | Type |
|-------|--------|------|
| `change_type` | `solution_outline.md` deliverable metadata | enum: `analysis|feature|enhancement|bug_fix|tech_debt|verification` |
| `track` | `phase-3-outline` | enum: `simple|complex` |
| `scope_estimate` | `solution_outline.md` solution-level metadata (deliverable 2) | enum: `none|surgical|single_module|multi_module|broad` |
| `recipe_key` | `status.json` `plan_source` metadata when sourced via a recipe | string or absent |
| `affected_files_count` | `references.json::affected_files` length | int (≥0) |
| `commit_strategy` | `manage-config plan phase-5-execute get --field commit_strategy` | enum: `per_plan|per_deliverable|none` (default: `per_plan`) |
| `phase_5_candidates` | `marshal.json::plan.phase-5-execute.steps` | list[string] |
| `phase_6_candidates` | `marshal.json::plan.phase-6-finalize.steps` | list[string] |

## Outputs

For each rule the composer emits:

- `phase_5.early_terminate` — bool. When `true`, Phase 5 transitions directly to Phase 6 without running tasks.
- `phase_5.verification_steps` — ordered list[string] subset of `phase_5_candidates`.
- `phase_6.steps` — ordered list[string] subset of `phase_6_candidates`.

## Pre-Filter: `commit_strategy_none`

Before evaluating the seven-row matrix below, the composer applies a pre-filter to the `phase_6_candidates` list:

**Condition**: `commit_strategy == none`.

**Effect**: `commit-push` is removed from `phase_6_candidates` before the rows are evaluated. Every row that emits a Phase 6 list (whether by intersection, subtraction, or pass-through) operates on the already-filtered list, so the resulting `phase_6.steps` will never contain `commit-push` when this pre-filter fires.

**Why a pre-filter (not an eighth row)**: `commit_strategy` is configuration known at outline time and is orthogonal to the row matrix's change-type / scope / recipe inputs. A row would have to either short-circuit (and re-implement the seven rows' Phase 5 logic) or duplicate the filter into every row. Modeling it as a pre-filter keeps the seven-row matrix unchanged and lets the composer emit one extra `decision.log` entry naming the omission.

**Decision log line** (in addition to the row's own log line):

```
(plan-marshall:manage-execution-manifest:compose) commit-push omitted — commit_strategy=none
```

When `commit_strategy ∈ {per_plan, per_deliverable}` (or absent — the default is `per_plan`), the pre-filter is a no-op and emits no log entry.

## The Seven-Row Matrix

The seven rows below are evaluated top-down; the first match wins. They operate on the (possibly pre-filtered) `phase_6_candidates` list described above.

### Row 1 — `early_terminate_analysis`

**Condition**: `change_type == analysis` AND `affected_files_count == 0`.

**Outcome**:
- `phase_5.early_terminate = true`
- `phase_5.verification_steps = []`
- `phase_6.steps` = `phase_6_candidates ∩ {knowledge-capture, lessons-capture, archive-plan}`

**Why**: A pure-analysis plan with no source-file impact has nothing to verify. Phase 6 still runs lessons + knowledge capture so the analysis findings don't leak silently, and `archive-plan` finalizes the plan record.

### Row 2 — `recipe`

**Condition**: `recipe_key` is present (non-empty).

**Outcome**:
- `phase_5.early_terminate = false`
- `phase_5.verification_steps = phase_5_candidates ∩ {quality-gate, module-tests}`
- `phase_6.steps = phase_6_candidates − {automated-review, sonar-roundtrip, knowledge-capture}`

**Why**: Recipe-driven plans (currently `recipe-refactor-to-profile-standards` and the upcoming `recipe-lesson-cleanup` from deliverable 7) follow deterministic, surgical-style patterns. Drop the heavy review steps that target broad code changes; keep the build/test gate and the bookkeeping/PR steps.

### Row 3 — `docs_only`

**Condition**: `scope_estimate ∈ {surgical, single_module}` AND `change_type ∈ {tech_debt, enhancement}` AND `affected_files_count > 0` AND `phase_5_candidates` lacks both `module-tests` and `coverage`.

**Outcome**:
- `phase_5.early_terminate = false`
- `phase_5.verification_steps = []`
- `phase_6.steps = phase_6_candidates − {automated-review, sonar-roundtrip}`

**Why**: A docs-shaped plan never needs to run tests or coverage. The candidate set already reflects this (no `module-tests`/`coverage`), so the manifest empties Phase 5's verification list and skips the heavy review steps. We keep `commit-push`, `create-pr`, `knowledge-capture`, `lessons-capture`, `branch-cleanup`, and `archive-plan` so the doc change is committed, surfaced, and recorded.

### Row 4 — `tests_only`

**Condition**: `change_type == verification` AND `affected_files_count > 0`.

**Outcome**:
- `phase_5.early_terminate = false`
- `phase_5.verification_steps = phase_5_candidates ∩ {module-tests}`
- `phase_6.steps = phase_6_candidates` (full set)

**Why**: The plan only changes tests; we want the test suite to run but `quality-gate` is overkill since no production code moved. Phase 6 stays unconditional because new test signal benefits from the full review cycle.

### Row 5 — `surgical_bug_fix` / `surgical_tech_debt`

**Condition**: `scope_estimate == surgical` AND `change_type ∈ {bug_fix, tech_debt}`. The rule key encodes the change_type for log clarity.

**Outcome**:
- `phase_5.early_terminate = false`
- `phase_5.verification_steps = phase_5_candidates ∩ {quality-gate, module-tests}`
- `phase_6.steps = phase_6_candidates − {automated-review, sonar-roundtrip, knowledge-capture}`

**Why**: Surgical bug fixes and tech-debt nudges have already passed the Q-Gate bypass at outline time (deliverable 4). The full review army (`automated-review` + `sonar-roundtrip`) adds latency without commensurate signal on a one-line fix; `knowledge-capture` is overkill for a focused fix. We keep `lessons-capture` so any lesson observed during execution is still captured.

### Row 6 — `verification_no_files`

**Condition**: `change_type == verification` AND `affected_files_count == 0`.

**Outcome**:
- `phase_5.early_terminate = false`
- `phase_5.verification_steps = phase_5_candidates` (full)
- `phase_6.steps = phase_6_candidates ∩ {knowledge-capture, lessons-capture, archive-plan}`

**Why**: A verification plan with no affected files is a "run the existing checks" plan — keep Phase 5 fully wired (since the goal is verification) but trim Phase 6 down to the records-and-archive triad since nothing was committed.

### Row 7 — `default`

**Condition**: Any plan that doesn't match rows 1–6.

**Outcome**:
- `phase_5.early_terminate = false`
- `phase_5.verification_steps = phase_5_candidates` (full)
- `phase_6.steps = phase_6_candidates` (full)

**Why**: This is the safe baseline for code-shaped features and broader changes. The full canonical Phase 5 verification fires; Phase 6 dispatches every step `marshal.json` lists.

## Decision Log Format

For each rule fired, the composer emits one line via `manage-logging decision`:

```
(plan-marshall:manage-execution-manifest:compose) Rule {rule_key} fired — early_terminate={bool}, phase_5.verification_steps={list}, phase_6.steps={list}
```

The component prefix `(plan-marshall:manage-execution-manifest:compose)` is mandatory so that `plan-retrospective` (deliverable 9) can correlate manifest content with the reasoning entries.

## Determinism

The decision matrix is deterministic given its inputs — re-running `compose` with the same arguments produces an identical manifest and identical decision-log entry. The composer truncates / overwrites previous manifests on re-invocation; callers (currently only `phase-4-plan` Step 8b) are responsible for re-entry semantics.
