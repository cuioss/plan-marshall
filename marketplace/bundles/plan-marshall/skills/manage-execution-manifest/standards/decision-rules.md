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
| `activation_globs` | `marshal.json::plan.phase-6-finalize.pre_push_quality_gate.activation_globs` | list[string] (default: empty) |
| `modified_files` | `references.json::modified_files` | list[string] (default: empty) |
| `phase_5_candidates` | `marshal.json::plan.phase-5-execute.steps` | list[string] |
| `phase_6_candidates` | `marshal.json::plan.phase-6-finalize.steps` | list[string] |
| `affected_files` | `references.json::affected_files` | list[string] (read directly by the composer; empty by default in the current pipeline) |
| `modified_files` | `references.json::modified_files` | list[string] (read directly by the composer; see "Bundle source detection" below for the union semantics with `affected_files` and the solution-outline fallback) |
| `outline_affected_files` | `solution_outline.md` deliverable `**Affected files:**` blocks (flattened across deliverables) | list[string] (read directly by the composer as the canonical pre-execute fallback when references-side fields are empty; see "Bundle source detection" below) |

## Outputs

For each rule the composer emits:

- `phase_5.early_terminate` — bool. When `true`, Phase 5 transitions directly to Phase 6 without running tasks.
- `phase_5.verification_steps` — ordered list[string] subset of `phase_5_candidates`.
- `phase_6.steps` — ordered list[string] subset of `phase_6_candidates`.

## Pre-Filters

Before evaluating the seven-row matrix below, the composer applies a fixed sequence of pre-filters to the `phase_6_candidates` list. Each pre-filter is independent of the row matrix's change-type / scope / recipe inputs, so modeling them as pre-filters keeps the seven-row matrix orthogonal and lets the composer emit one dedicated `decision.log` entry per fired pre-filter.

The pre-filters run in this order:

1. **`commit_strategy_none`** — drops `commit-push`, `pre-push-quality-gate`, AND `pre-submission-self-review` when no push will occur.
2. **`pre_push_quality_gate_inactive`** — drops `pre-push-quality-gate` when activation conditions fail.
3. **`pre_submission_self_review_inactive`** — drops `pre-submission-self-review` when `references.modified_files` is empty.

Each row that emits a Phase 6 list (whether by intersection, subtraction, or pass-through) operates on the already-filtered candidate list, so the resulting `phase_6.steps` will never contain a step removed by an earlier pre-filter.

After the seven-row matrix runs, a single composition-time guard (`bot_enforcement_guard`) inspects the final `phase_6.steps` list. On GitHub/GitLab plans where `default:automated-review` is missing, the guard remediates in-place by appending it back to the list (defense-in-depth, not assertion). The guard is documented in its own subsection below the pre-filter sections.

### Pre-Filter: `commit_strategy_none`

**Condition**: `commit_strategy == none`.

**Effect**: `commit-push`, `pre-push-quality-gate`, AND `pre-submission-self-review` are all removed from `phase_6_candidates` before the rows are evaluated. The pre-filter removes the two pre-push gating steps because they are meaningless without a downstream push — they exist solely to gate code that will be sent to remote CI.

**Why a pre-filter (not an eighth row)**: `commit_strategy` is configuration known at outline time and is orthogonal to the row matrix's change-type / scope / recipe inputs. A row would have to either short-circuit (and re-implement the seven rows' Phase 5 logic) or duplicate the filter into every row. Modeling it as a pre-filter keeps the seven-row matrix unchanged and lets the composer emit one extra `decision.log` entry naming the omission.

**Decision log line** (in addition to the row's own log line):

```
(plan-marshall:manage-execution-manifest:compose) commit-push omitted — commit_strategy=none
```

When `commit_strategy ∈ {per_plan, per_deliverable}` (or absent — the default is `per_plan`), the pre-filter is a no-op and emits no log entry.

### Pre-Filter: `pre_push_quality_gate_inactive`

**Condition**: At least one of:

- `marshal.json::plan.phase-6-finalize.pre_push_quality_gate.activation_globs` is missing or empty, OR
- `references.json::modified_files` is empty, OR
- No entry in `modified_files` matches any glob in `activation_globs` (using `fnmatch.fnmatch`).

**Effect**: `pre-push-quality-gate` is removed from `phase_6_candidates` before the rows are evaluated. When `pre-push-quality-gate` was already removed by `commit_strategy_none`, this pre-filter is a no-op and emits no log entry.

**Why a pre-filter (not an eighth row)**: Activation is project configuration paired with a glob match against `modified_files`, both orthogonal to the change-type / scope / recipe inputs that the seven-row matrix consumes. A row would either have to short-circuit and re-implement Phase 5 logic, or duplicate the filter into every row. Keeping it as a pre-filter preserves the seven-row matrix verbatim and adds exactly one independent decision-log line.

**Decision log line** (in addition to the row's own log line and any other pre-filter log line):

```
(plan-marshall:manage-execution-manifest:compose) pre-push-quality-gate omitted — activation_globs empty or no modified_files match
```

When all three activation conditions are satisfied (non-empty globs, non-empty modified_files, at least one glob match), the pre-filter is a no-op and emits no log entry; `pre-push-quality-gate` survives into the seven-row matrix.

**Evaluation order vs. the seven-row matrix**: This pre-filter runs *after* `commit_strategy_none` and *before* every row of the seven-row matrix. The pre-filter is therefore observable independently — Row 7 (default), Row 5 (surgical_bug_fix / surgical_tech_debt), and Row 2 (recipe) all see a Phase 6 candidate list that already has `pre-push-quality-gate` removed if either pre-filter fired.

### Pre-Filter: `pre_submission_self_review_inactive`

**Condition**: `references.json::modified_files` is empty.

**Effect**: `pre-submission-self-review` is removed from `phase_6_candidates` before the rows are evaluated. When `pre-submission-self-review` was already removed by `commit_strategy_none`, this pre-filter is a no-op and emits no log entry.

**Why a pre-filter (not an eighth row)**: Activation depends only on `modified_files` being non-empty (the four cognitive checks have no diff to inspect when the plan touched zero files). The condition is orthogonal to the change-type / scope / recipe inputs the seven-row matrix consumes. There is no `activation_globs` config knob — the four structural-defect classes the step targets (symmetric pairs, regex over-fit, wording, duplication) apply to any code or doc change, and gating by file extension would mean missing the very wording/duplication defects the lesson cites for `.md` files.

**Decision log line** (in addition to the row's own log line and any other pre-filter log line):

```
(plan-marshall:manage-execution-manifest:compose) pre-submission-self-review omitted — empty modified_files
```

When `modified_files` is non-empty, the pre-filter is a no-op and emits no log entry; `pre-submission-self-review` survives into the seven-row matrix.

**Evaluation order vs. the seven-row matrix**: This pre-filter runs *after* `pre_push_quality_gate_inactive` and *before* every row of the seven-row matrix. The pre-filter is observable independently of the row matrix — every row sees a Phase 6 candidate list that has `pre-submission-self-review` removed if any of the prior pre-filters fired.

## Bot-Enforcement Guard

**Type**: Composition-time defense-in-depth remediation (NOT a pre-filter, NOT an assertion). Runs *after* the seven-row matrix has produced the final `phase_6.steps` list, *before* the manifest is persisted.

**Condition**: `ci_provider ∈ {github, gitlab}` AND `default:automated-review` is NOT in the assembled `phase_6.steps` list.

**Effect**: Appends `default:automated-review` to the final `phase_6.steps` list in-place and emits a decision-log entry recording the remediation. The composition continues normally and the manifest is written with `automated-review` restored. The guard preserves matrix orthogonality — Row 5's subtraction logic (and any future pre-filter or row that legitimately drops `automated-review`) stays unchanged; the guard puts the step back so the final manifest is GitHub/GitLab-compliant.

**Why remediation rather than assertion**: The original assertion-style guard deadlocked every `surgical+{bug_fix, tech_debt}` plan that finalized through GitHub or GitLab — Row 5 of the seven-row matrix legitimately drops `automated-review` for those plans, and the assertion then refused to write the manifest. Lesson `2026-04-28-10-001` documents the deadlock and the chosen remediation strategy (Option 2: keep Row 5's subtraction intact, convert the guard from assertion to remediation). The matrix's documented orthogonality (its inputs are change_type / scope / recipe only) is preserved.

**Why retained after the deadlock fix (defense-in-depth)**: Lesson `2026-04-27-18-003` requires `automated-review` to be effectively mandatory on plans that finalize through GitHub or GitLab — review bots catch a class of structural defects the local gates systematically miss, and silently dropping the bot-review step (e.g., via a future pre-filter, a recipe interaction, or a row addition we haven't designed yet) would defeat the entire pre-submission-self-review story. The guard is now defense-in-depth alongside `phase-6-finalize/standards/required-steps.md` — the required-steps file ensures completion semantics for the handshake invariant; this guard ensures the step is even scheduled in the first place, and self-heals if anything upstream drops it.

**Decision log line** (emitted whenever the guard remediates; one entry per remediation):

```
(plan-marshall:manage-execution-manifest:compose) bot-enforcement guard remediated — ci_provider=github, automated-review re-added to phase_6.steps
```

When `ci_provider` is neither `github` nor `gitlab`, OR `default:automated-review` is already present in `phase_6.steps`, the guard is a no-op and emits no log entry.

**Safety-net error path**: The function still has a non-`None` return contract (`str | None`) and the caller (`cmd_compose`) still translates a non-`None` return into a `bot_enforcement_violation` error TOON. In current code this branch is unreachable — the guard either no-ops (returns `None`) or remediates and returns `None`. The branch is retained as a hook for any future logic that detects a non-remediable violation (e.g., a malformed `phase_6_steps` list), so the legacy `bot-enforcement guard fired` log line and error TOON shape remain documented in the codebase even though they are not exercised by the current control flow.

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

## Stacked Rule — `bundle_self_modification`

After the seven-row matrix has selected a base manifest, the composer applies one stacked rule that mutates `phase_6.steps` independently of the row that fired. This rule does NOT replace any row — it stacks an extra step on top of whatever the matrix produced.

**Condition**: any entry in the **union** of three sources (see "Bundle source detection" below) matches one of the bundle source globs:

- `marketplace/bundles/*/agents/*` (or `**`)
- `marketplace/bundles/*/commands/*` (or `**`)
- `marketplace/bundles/*/skills/*` (or `**`)

Globs are matched with `fnmatch.fnmatchcase` (POSIX semantics, no regex).

**Effect**: `project:finalize-step-sync-plugin-cache` is inserted into `phase_6.steps` immediately before the **earliest** entry in the resolved list whose **bare name** belongs to the agent-dispatched set:

- `create-pr`
- `automated-review`
- `sonar-roundtrip`
- `knowledge-capture`
- `lessons-capture`

The matcher strips an optional `default:` prefix before checking membership, so the rule fires regardless of whether the resolved candidate list arrived prefixed (production marshal.json passes `default:create-pr`, etc.) or bare (the script's `DEFAULT_PHASE_6_STEPS` fallback emits `create-pr`, etc.).

If the resolved `phase_6.steps` contains no agent-dispatched step, the rule does not fire (no insertion, no log line). If `project:finalize-step-sync-plugin-cache` already sits immediately before the first agent-dispatched step, the rule is idempotent and skips reinsertion. The existing late-stage occurrence (when present in `phase_6_candidates`) is preserved verbatim — the rule stacks an additional early occurrence rather than relocating the late one.

**Why this stacks instead of replacing a row**: cached plugin definitions under `~/.claude/plugins/cache/` are the runtime source of truth for Task agent dispatch. When the plan's diff edits bundled agents, commands, or skills, the worktree-side fix never reaches the cache until `project:finalize-step-sync-plugin-cache` runs — which by default sits late in the manifest (post `branch-cleanup`). That ordering is correct in the steady state ("publish after commit"), but when the in-flight finalize itself dispatches agents loaded from that cache (`create-pr`, `automated-review`, `knowledge-capture`, `lessons-capture`), it sees the *pre-fix* definitions for the duration of the run. The stacked rule closes the staleness window by inserting an early sync immediately before the first agent dispatch. The existing late-stage occurrence is preserved verbatim — duplicate occurrences are intentional (early sync feeds the in-flight run; late sync publishes the post-commit state).

**Why a stacked rule, not an eighth row**: the seven-row matrix is keyed off change-type / scope / recipe semantics — orthogonal to which bundle surfaces the diff touches. Adding a `bundle_self_modification` row would force every other row to negotiate with it; modeling it as a post-matrix mutation keeps the matrix focused and lets multiple base rows benefit from the early-sync insertion.

**Decision log line** (in addition to the row's own log line):

```
(plan-marshall:manage-execution-manifest:compose) Rule bundle_self_modification fired — inserted project:finalize-step-sync-plugin-cache before {first_agent_step}
```

**Bundle source detection**: the composer reads from three sources, unions their entries (de-duplicated, order-preserving), and matches the union against the bundle source globs:

1. `references.json::affected_files` — populated by upstream phases when they explicitly persist the outline-derived list to references. Empty by default in the current pipeline (no phase writes it today).
2. `references.json::modified_files` — populated by `manage-status transition` on Phase 5 completion. Empty at the first `compose` invocation but becomes non-empty for any later re-compose (e.g., a finalize-loop fix task that re-enters Phase 4).
3. **Solution-outline fallback** — when neither references field surfaces bundle paths, the composer parses `solution_outline.md`, walks every deliverable's `**Affected files:**` block, and flattens those lists into the union. This source is the canonical pre-execute view of the diff at `phase-4-plan` Step 8b time and is the only source guaranteed to be populated for normal plans on the first compose.

Reading all three sources and unioning their entries closes the timing gap so the rule fires on the first compose (via the solution-outline fallback) AND on any later re-compose (via `modified_files`). Relying on `references.json::affected_files` alone would silently no-op for normal plans because nothing in the current pipeline persists outline-derived `Affected files:` bullets to that field. The fallback degrades gracefully: when `solution_outline.md` is missing, malformed, or `_plan_parsing` is unavailable on `sys.path`, the helper returns an empty list and the rule simply does not fire.

**Cross-references**: lesson `2026-04-26-23-003` (the recurrence that drove this rule), lesson `2026-04-27-21-001` (the empirical reproducer where `references.json::affected_files` was unset and the rule no-opped), lesson `2026-04-24-17-002` (parent — agents falling back to `python -c open(...)` due to missing tools, which this rule prevents from re-occurring under stale-cache dispatch).

## Decision Log Format

For each rule fired, the composer emits one line via `manage-logging decision`:

```
(plan-marshall:manage-execution-manifest:compose) Rule {rule_key} fired — early_terminate={bool}, phase_5.verification_steps={list}, phase_6.steps={list}
```

The component prefix `(plan-marshall:manage-execution-manifest:compose)` is mandatory so that `plan-retrospective` (deliverable 9) can correlate manifest content with the reasoning entries.

## Determinism

The decision matrix is deterministic given its inputs — re-running `compose` with the same arguments produces an identical manifest and identical decision-log entry. The composer truncates / overwrites previous manifests on re-invocation; callers (currently only `phase-4-plan` Step 8b) are responsible for re-entry semantics.
