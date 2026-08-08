# Cost Sizing Rubric

**Purpose**: The single source of truth for the six-size T-shirt scale (`XS`/`S`/`M`/`L`/`XL`/`XXL`) and its `predicted_cost_tokens` magnitudes, shared by **two consumers**: planned **tasks** (sized deterministically by `manage-tasks derive-cost-size` at phase-4-plan) and **lane-elements** (phase / finalize-step elements that declare a `cost_size` in their `lane:` frontmatter per [`../../extension-api/standards/ext-point-lane-element.md`](../../extension-api/standards/ext-point-lane-element.md)). The size and predicted cost are stamped onto each task and later consumed by the plan-time bin-packer (`manage-tasks pack-envelopes`) and the phase-5-execute envelope-group executor; for lane-elements the same scale feeds the execution-profile dialogue's per-posture cost preview.

This doc is the **legible, reviewable, and tunable** model. The script is the deterministic default; the doc is what a human reads to understand, review, and tune the model, and what the planner consults to apply judgment when a task's true cost diverges from the mechanical step-count proxy.

The scale is **six sizes**: the original `S`/`M`/`L`/`XL` plus `XS` (deterministic ≈0-token bookkeeping) and `XXL` (the heaviest elements). The four original score bands and token magnitudes are **unchanged**, so the task deriver and bin-packer behave identically for every existing task — `XS`/`XXL` only carve new bands below the old `S` floor and above the old `XL` ceiling.

## Why a planning-time cost model exists

The phase-5-execute continue-vs-yield decision must be made at PLANNING time, not at execution time. A running subagent cannot measure its own context-window usage mid-turn — no tool, environment variable, signal, or API returns "tokens used / remaining" to the model while it executes. The only entity that sees real token counts is the orchestrator, and only AFTER a dispatch returns (the post-return `<usage>` block). Therefore the cost of each task is **predicted at plan time** from signals already present on the task record, and the executor never measures cost at runtime — it only reads a pre-computed envelope grouping.

This rubric predicts **TOKENS**, not wall-clock time. The two are different: a task can be slow (a long build) yet token-cheap, or fast yet token-expensive (heavy generation across many files).

## 1. Signals and weights

A task's cost size is derived from four signals already present on its task record. Each contributes a weighted term to a single deterministic score:

| Signal | Source | Weight | Rationale |
|--------|--------|:------:|-----------|
| `step_count` | `len(task.steps)` | **dominant** | Each step drives a distinct generation/reasoning pass. Step count is the strongest predictor of how much the model must produce, so it carries the largest weight. |
| `profile` | `task.profile` | moderate | `implementation` and `module_testing` generate and reason over production / test code (heavy); `verification` only runs commands and parses output (lightest). |
| `skills_count` | `len(task.skills)` | moderate | Each declared skill is loaded in-context per task (the `execute-task` skill load plus its standards). More skills means a larger fixed per-task context load. |
| `target_file_count` | distinct `steps[].target` | minor | Each distinct target file is read and/or written. Distinct files (not steps) measure the breadth of the file surface the task touches. |

### Weighting

The score is a weighted sum:

```text
score = (W_step          * step_count)
      + (W_profile        * profile_weight(profile))
      + (W_skills         * skills_count)
      + (W_target_files   * target_file_count)
```

with the following canonical weights and the profile-weight map:

| Term | Symbol | Value |
|------|--------|------:|
| Step weight (dominant) | `W_step` | 10 |
| Profile weight | `W_profile` | 1 |
| Skills weight | `W_skills` | 3 |
| Target-file weight | `W_target_files` | 4 |

| `profile` | `profile_weight` |
|-----------|-----------------:|
| `implementation` | 12 |
| `module_testing` | 12 |
| `verification` | 4 |
| (any other / unknown) | 8 |

`step_count` is dominant: with `W_step = 10`, one extra step adds 10 to the score, which is more than one extra skill (3) or one extra target file (4). The profile term is a one-time additive offset that lifts code-bearing profiles above pure verification.

### Why build count is EXCLUDED

The number of build/verify commands a task runs is **deliberately not a signal**. A build is token-cheap — running a build and reading its summary costs on the order of ~100 tokens regardless of how long the build takes in wall-clock time. The cost this rubric predicts is the model's TOKEN consumption (generation + reasoning + in-context skill loads), which is dominated by the work the model itself produces, not by the wall-clock duration of an external build process. Including build count would conflate wall-clock cost with token cost and inflate the size of token-cheap, build-heavy tasks. The deriver therefore takes no build-count input.

## 2. Thresholds

The weighted score maps to a T-shirt size by score band. The bands are:

| Size | Score band | Reading |
|------|-----------|---------|
| `XS` | `score < 30` | Trivial task — a single small step, no skills, no file surface; below the old `S` floor. |
| `S` | `30 <= score < 60` | Small, localized task — a few steps, light profile, few files. |
| `M` | `60 <= score < 150` | Moderate task — several steps or a code profile with a handful of files/skills. |
| `L` | `150 <= score < 300` | Large task — many steps over a code profile with a broad file surface. |
| `XL` | `300 <= score < 700` | Very large task — heavy multi-file refactor or test rewrite; legitimately packs ~1 per envelope. |
| `XXL` | `score >= 700` | The largest tasks — execute on a substantial plan; above the old `XL` ceiling. |

The four original boundaries (`S`/`M`/`L` cutoffs at 60/150/300) are unchanged; `XS` carves the `score < 30` band below the old `S` floor and `XXL` carves the `score >= 700` band above the old `XL` ceiling, so every canonical worked example in §4 still derives the same size it did under the four-size scale.

The bands are monotone: increasing any signal can only raise (never lower) the score, so a task with more steps is never assigned a smaller size than an otherwise-identical task with fewer steps.

## 3. Size → token table

Each size maps to a `predicted_cost_tokens` magnitude. These are the **tunable defaults**, calibrated against the forensic per-dispatch range observed in production (134K–392K tokens per dispatch). The four original magnitudes (`S`/`M`/`L`/`XL`) are unchanged; `XS` and `XXL` are the two new ends:

| Size | `predicted_cost_tokens` (default) | covers |
|------|----------------------------------:|--------|
| `XS` | 5K (5 000) | deterministic ≈0-token bookkeeping (push, branch-cleanup, archive, record-metrics, deploy-target, sync-plugin-cache) |
| `S` | 25K (25 000) | small agent steps |
| `M` | 60K (60 000) | medium |
| `L` | 130K (130 000) | heavy single steps |
| `XL` | 260K (260 000) | the planning phases |
| `XXL` | 520K (520 000) | the largest elements — execute on a substantial plan; any element exceeding XL |

This table is the tunable default. It is sourced from config (`plan.phase-5-execute.cost_size_token_table`); the deriver accepts the table as an injected parameter so it stays a pure function, and the config-backed value is the operator-visible, tunable surface. The magnitude strings (`"25K"`, …) are parsed to integers via `sensible_number.parse_sensible_int`. The orchestrator sees each envelope's real post-return `<usage>` and can feed actual-vs-predicted deltas back to recalibrate this table over time (the calibration loop).

## 4. Worked examples

These examples are calibrated to the bands above and are the canonical cases the deriver MUST agree with.

| Task shape | step_count | profile | skills | target files | score | size | predicted |
|------------|:----------:|---------|:------:|:------------:|:-----:|:----:|----------:|
| 1-step doc-only verify | 1 | `verification` | 0 | 1 | `10·1 + 1·4 + 3·0 + 4·1 = 18` | **XS** | 5K |
| 5-step documentation edit | 5 | `verification` | 1 | 5 | `10·5 + 1·4 + 3·1 + 4·5 = 77` | **M** | 60K |
| 3-step doc-only verify | 3 | `verification` | 0 | 2 | `10·3 + 1·4 + 3·0 + 4·2 = 42` | **S** | 25K |
| 14-step config change | 14 | `implementation` | 2 | 6 | `10·14 + 1·12 + 3·2 + 4·6 = 182` | **L** | 130K |
| 55-step multi-file test refactor | 55 | `module_testing` | 3 | 20 | `10·55 + 1·12 + 3·3 + 4·20 = 651` | **XL** | 260K |
| 70-step multi-module test rewrite | 70 | `module_testing` | 4 | 25 | `10·70 + 1·12 + 3·4 + 4·25 = 824` | **XXL** | 520K |

The worked-example column order (step → profile → skills → target-file term → score → size → predicted) mirrors the deriver's computation exactly. A small task with few steps but unusually large files is the canonical case where the planner applies the consultation contract below rather than trusting the mechanical score alone.

## 5. Consultation contract

The deterministic deriver (`manage-tasks derive-cost-size`, implemented by `_tasks_cost.py`) is the **default** — phase-4-plan stamps every task's `cost_size` and `predicted_cost_tokens` from it without LLM estimation. This doc is what the planner **consults** to MAP or DETERMINE a task's size when the mechanical estimate is ambiguous — for example, a task with few steps but very large target files whose true token cost exceeds what the step-count proxy predicts. In that case the planner may apply judgment within this rubric (e.g. treat the task as one size larger) and record the rationale, rather than blindly trusting the score.

The doc also makes the model reviewable and tunable: the weights (§1), thresholds (§2), and size→token table (§3) are all stated here so they can be inspected and adjusted without reading the implementation.

## Cross-references

- **Deriver (implements this rubric)**: `manage-tasks derive-cost-size` — see [`../../manage-tasks/SKILL.md`](../../manage-tasks/SKILL.md) § "Canonical invocations". The pure module is `manage-tasks/scripts/_tasks_cost.py`.
- **Phase-4-plan stamp step**: phase-4-plan computes the four signals per task, calls `derive-cost-size`, and writes the returned `cost_size` + `predicted_cost_tokens` onto each task record (the deterministic sibling of the `derive-verification` stamp).
- **Bin-packer (consumes `predicted_cost_tokens`)**: `manage-tasks pack-envelopes` packs sized tasks into envelope groups under `per_envelope_budget_tokens`.
- **Config table**: `plan.phase-5-execute.cost_size_token_table` is the tunable size→token map; `plan.phase-5-execute.per_envelope_budget_tokens` is the per-envelope packing budget consumed by the bin-packer. See [`../../manage-config/SKILL.md`](../../manage-config/SKILL.md).
- **Consumer (phase-5-execute)**: the executor reads each task's stamped `envelope_id` (written by the bin-packer) and runs only its assigned envelope group — it performs no runtime cost computation.
