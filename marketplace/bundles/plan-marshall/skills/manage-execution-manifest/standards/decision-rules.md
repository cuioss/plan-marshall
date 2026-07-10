# Execution Manifest — Decision Rules

This standard codifies the decision matrix used by `manage-execution-manifest compose` to derive the per-plan execution manifest. The composer evaluates the rows in order; the **first matching row wins** and a single `decision.log` entry is emitted with the rule key, naming exactly which row fired.

## Inputs

| Input | Source | Type |
|-------|--------|------|
| `change_type` | `solution_outline.md` deliverable metadata | enum: `analysis|feature|enhancement|bug_fix|tech_debt|verification` |
| `track` | `phase-3-outline` | enum: `simple|complex` |
| `scope_estimate` | `solution_outline.md` solution-level metadata (deliverable 2) | enum: `none|surgical|single_module|multi_module|broad` |
| `recipe_key` | `--recipe-key` argument when supplied, else read by the composer from `status.json::metadata.plan_source` (falling back to `metadata.recipe_key`) | string or absent |
| `affected_files_count` | `references.json::affected_files` length | int (≥0) |
| `commit_and_push` | `manage-config plan phase-5-execute get --field commit_and_push` | bool (default: `true`) |
| `build_map_globs` | derived from `marshal.json::build.map` — the union of every entry's `glob` across all domains | list[string] (default: empty when build_map absent) |
| `live_footprint` | derived on demand from the worktree (`{base}...HEAD` ∪ porcelain via `compute_plan_branch_diff`); empty before the worktree is materialized | list[string] (default: empty) |
| `phase_5_candidates` | `marshal.json::plan.phase-5-execute.verification_steps` (phase-aware list-field — see [Phase-aware step source](#phase-aware-step-source)) | list[string] |
| `phase_6_candidates` | `marshal.json::plan.phase-6-finalize.steps` | list[string] |
| `live_footprint` (canonical-verify gate) | derived on demand from the worktree via `_resolve_footprint` (empty before the worktree is materialized) | list[string] |
| `affected_files` | `references.json::affected_files` | list[string] (read directly by the composer; empty by default in the current pipeline) |
| `modified_files` (legacy back-compat) | `references.json::modified_files` | list[string] (read by Bundle source detection only, as a back-compat fallback for archived plans that still carry the key; see "Bundle source detection" below for the union semantics with `affected_files` and the solution-outline fallback) |
| `outline_affected_files` | `solution_outline.md` deliverable `**Affected files:**` blocks (flattened across deliverables) | list[string] (read directly by the composer as the canonical pre-execute fallback when references-side fields are empty; see "Bundle source detection" below) |

## Phase-aware step source

The composer reads each phase's candidate step list from `marshal.json` via `_read_marshal_phase_steps(phase_key)`. The list-field name read under the phase block is **phase-aware** (resolved by `_marshal_steps_field`):

| Phase key | marshal.json list-field |
|-----------|-------------------------|
| `phase-5-execute` | `verification_steps` |
| `phase-6-finalize` (and any other phase) | `steps` |

The phase-5 block stores its verification step list under `verification_steps` (renamed from the generic `steps` so the phase-5 list is self-describing and distinct from phase-6's finalize `steps`). For backward compatibility with project `marshal.json` files that have not yet migrated the phase-5 block, the reader falls back to the generic `steps` key when `verification_steps` is absent.

## Outputs

For each rule the composer emits:

- `phase_5.early_terminate` — bool. When `true`, Phase 5 transitions directly to Phase 6 without running tasks.
- `phase_5.verification_steps` — ordered list[string] subset of `phase_5_candidates`.
- `phase_6.steps` — ordered list[string] subset of `phase_6_candidates`.

## The `execution_log` Section (record-step)

The `execution_log[]` section is a runtime append log that is **separate from the decision matrix** — `compose` never reads or writes it. It is populated exclusively by the `record-step` subcommand, one row appended per invocation, capturing per-step execution outcome plus token attribution into the manifest. This makes per-step execution metadata loggable per-plan deterministically rather than relying on the fragile orchestrator `<usage>`-forwarding boundary call.

**Section shape** (TOON):

```toon
execution_log[K]{step_id,phase,outcome,total_tokens,tool_uses,duration_ms,timestamp}:
  - quality_check,5-execute,executed,12000,8,4200,2026-06-08T10:15:00+00:00
  - create-pr,6-finalize,skipped,0,0,0,2026-06-08T10:42:00+00:00
```

**Row fields:**

| Field | Type | Description |
|-------|------|-------------|
| `step_id` | string | The dispatched step identifier (a phase-5 verification step ID or a phase-6 finalize step ID). |
| `phase` | enum | `5-execute` or `6-finalize` — the phase the step ran in. |
| `outcome` | enum | `executed` (the step ran), `skipped` (the step was gated off), or `error` (the step errored). |
| `total_tokens` | int (≥0) | Total tokens attributed to the step; default `0` when omitted. |
| `tool_uses` | int (≥0) | Tool-use count attributed to the step; default `0` when omitted. |
| `duration_ms` | int (≥0) | Wall-clock duration in milliseconds; default `0` when omitted. |
| `timestamp` | string | ISO-8601 UTC timestamp generated at record time (`datetime.now(UTC).isoformat()`). |

**Record-step contract:**

- The manifest MUST already exist (composed at `phase-4-plan` Step 8b). `record-step` against a missing manifest returns `file_not_found` — it never composes a fresh manifest.
- Each call appends **exactly one** row. `execution_log[]` is an ordered append log, NOT a keyed map — re-invocation with the same `step_id` appends another row, so every dispatch attempt of a step is recorded (a step that runs, errors, then re-runs produces three rows in order).
- The token-attribution triple defaults to `0` when the caller omits the flags: a `skipped` step legitimately consumes no tokens, and a step dispatched without a `<usage>` tag reports zeros rather than a missing column.
- Invalid `--phase` (not in `{5-execute, 6-finalize}`) returns `invalid_phase`; invalid `--outcome` (not in `{executed, skipped, error}`) returns `invalid_outcome` — both before any manifest read or write.
- One `decision.log` line is emitted per record via the in-process `_emit_decision_log` helper (the same helper the composer uses), so the line lands in the plan's own `logs/decision.log` alongside `execution.toon`:

```text
(plan-marshall:manage-execution-manifest:record-step) Recorded {step_id} phase={phase} outcome={outcome} — total_tokens={N}, tool_uses={N}, duration_ms={N}
```

**Producers:** `phase-5-execute` (per verification step) and `phase-6-finalize` (per finalize step). The composer (`phase-4-plan`) is NOT a producer of `execution_log` — it writes only `phase_5` / `phase_6`.

## Pre-Filters

Before evaluating the seven-row matrix below, the composer applies a fixed sequence of pre-filters to the `phase_6_candidates` list. Each pre-filter is independent of the row matrix's change-type / scope / recipe inputs, so modeling them as pre-filters keeps the seven-row matrix orthogonal and lets the composer emit one dedicated `decision.log` entry per fired pre-filter.

The pre-filters run in this order:

1. **`commit_push_disabled`** — drops `push`, `pre-push-quality-gate`, AND `pre-submission-self-review` when no push will occur.
2. **`pre_push_quality_gate_inactive`** — drops `pre-push-quality-gate` when activation conditions fail.
3. **`pre_submission_self_review_inactive`** — drops `pre-submission-self-review` when the live plan footprint is empty.
4. **`simplify_inactive`** — drops `finalize-step-simplify` when `change_type ∉ {feature, bug_fix, tech_debt}` OR `affected_files_count == 0`.
4b. **`security_audit_inactive`** — drops `finalize-step-security-audit` on the same gate as `simplify_inactive` (`change_type ∉ {feature, bug_fix, tech_debt}` OR `affected_files_count == 0`).
5. **`scope_gated_finalize`** — drops heavyweight phase-6 review/audit steps by `scope_estimate`: `surgical` drops `plan-retrospective`, `pre-submission-self-review`, and `plugin-doctor`; `single_module` drops only `plan-retrospective`. `plan-marshall:automatic-review` is dropped ONLY via the explicit `drop_review_on_scope_gate` opt-in, never by the implicit scope gate.

Each row that emits a Phase 6 list (whether by intersection, subtraction, or pass-through) operates on the already-filtered candidate list, so the resulting `phase_6.steps` will never contain a step removed by any pre-filter that ran before the row matrix.

After the seven-row matrix runs, four post-matrix transforms inspect the matrix output before the manifest is persisted, in this order:

1. **`ceremony_finalize_selection`** — applies the four `plan.phase-6-finalize` run-at-all gates (`self_review` / `qgate` / `simplify` / `security_audit`, each `always|never|auto`) to the final `phase_6.steps`, forcing each gate's step in (`always`), out (`never`), or deferring (`auto`). It NEVER touches `plan-marshall:automatic-review`. Documented in its own subsection below.
2. **Execution-profile lane resolution** — applies the `minimal ⊏ auto ⊏ full` posture cutoff from `status.metadata.execution_profile` to the lane-participating steps, dropping every element whose effective tier exceeds the posture. Documented in its own subsection below.
3. **`bot_enforcement_guard`** — on GitHub/GitLab plans where `plan-marshall:automatic-review` is missing from the final `phase_6.steps`, the guard remediates in-place by appending it back to the list (defense-in-depth, not assertion). The guard is documented in its own subsection below the pre-filter sections.
4. **`frontmatter_order_sort`** — reorders the final `phase_6.steps` into ascending frontmatter `order` (stable sort via `_sort_steps_by_frontmatter_order`; order-unresolvable entries stay pinned at their original index), so `archive-plan` (order 1000) is the terminal barrier regardless of seed order. Runs after the bot-enforcement guard and before the compose-time placement validator. Documented in its own subsection below.

### Pre-Filter: `commit_push_disabled`

**Condition**: `commit_and_push == false`.

**Effect**: `push`, `pre-push-quality-gate`, AND `pre-submission-self-review` are all removed from `phase_6_candidates` before the rows are evaluated. The pre-filter removes the two pre-push gating steps because they are meaningless without a downstream push — they exist solely to gate code that will be sent to remote CI.

**Why a pre-filter (not an eighth row)**: `commit_and_push` is configuration known at outline time and is orthogonal to the row matrix's change-type / scope / recipe inputs. A row would have to either short-circuit (and re-implement the seven rows' Phase 5 logic) or duplicate the filter into every row. Modeling it as a pre-filter keeps the seven-row matrix unchanged and lets the composer emit one extra `decision.log` entry naming the omission.

**Decision log line** (in addition to the row's own log line):

```text
(plan-marshall:manage-execution-manifest:compose) push omitted — commit_and_push=false
```

When `commit_and_push == true` (or absent — the default is `true`), the pre-filter is a no-op and emits no log entry.

### Pre-Filter: `pre_push_quality_gate_inactive`

**Condition**: At least one of:

- `marshal.json::build.map` is absent or carries no `glob` entries, OR
- the live plan footprint is empty, OR
- No entry in the live footprint matches any glob in `build_map_globs` (using `fnmatch.fnmatch`).

**Effect**: `pre-push-quality-gate` is removed from `phase_6_candidates` before the rows are evaluated. When `pre-push-quality-gate` was already removed by `commit_push_disabled`, this pre-filter is a no-op and emits no log entry.

**Why a pre-filter (not an eighth row)**: Activation is derived from `build.map` (the single source of truth for buildable file types) paired with a glob match against the live footprint, both orthogonal to the change-type / scope / recipe inputs that the seven-row matrix consumes. A row would either have to short-circuit and re-implement Phase 5 logic, or duplicate the filter into every row. Keeping it as a pre-filter preserves the seven-row matrix verbatim and adds exactly one independent decision-log line.

**Decision log line** (in addition to the row's own log line and any other pre-filter log line):

```text
(plan-marshall:manage-execution-manifest:compose) pre-push-quality-gate omitted — no build_map globs or no footprint match
```

When all three activation conditions are satisfied (non-empty build_map globs, non-empty footprint, at least one glob match), the pre-filter is a no-op and emits no log entry; `pre-push-quality-gate` survives into the seven-row matrix.

**Evaluation order vs. the seven-row matrix**: This pre-filter runs *after* `commit_push_disabled` and *before* every row of the seven-row matrix. The pre-filter is therefore observable independently — Row 7 (default), Row 5 (surgical_bug_fix / surgical_tech_debt), and Row 2 (recipe) all see a Phase 6 candidate list that already has `pre-push-quality-gate` removed if either pre-filter fired.

### Pre-Filter: `pre_submission_self_review_inactive`

**Condition**: the live plan footprint is empty.

**Effect**: `pre-submission-self-review` is removed from `phase_6_candidates` before the rows are evaluated. When `pre-submission-self-review` was already removed by `commit_push_disabled`, this pre-filter is a no-op and emits no log entry.

**Why a pre-filter (not an eighth row)**: Activation depends only on the live footprint being non-empty (the four cognitive checks have no diff to inspect when the plan touched zero files). The condition is orthogonal to the change-type / scope / recipe inputs the seven-row matrix consumes. Unlike `pre-push-quality-gate` (which gates on the `build.map` globs), this step has no glob gate — the four structural-defect classes it targets (symmetric pairs, regex over-fit, wording, duplication) apply to any code or doc change, and gating by file extension would mean missing the very wording/duplication defects the lesson cites for `.md` files.

**Decision log line** (in addition to the row's own log line and any other pre-filter log line):

```text
(plan-marshall:manage-execution-manifest:compose) pre-submission-self-review omitted — empty footprint
```

When the footprint is non-empty, the pre-filter is a no-op and emits no log entry; `pre-submission-self-review` survives into the seven-row matrix.

**Evaluation order vs. the seven-row matrix**: This pre-filter runs *after* `pre_push_quality_gate_inactive` and *before* every row of the seven-row matrix. The pre-filter is observable independently of the row matrix — every row sees a Phase 6 candidate list that has `pre-submission-self-review` removed if any of the prior pre-filters fired.

### Pre-Filter: `simplify_inactive`

**Condition**: `change_type ∉ {feature, bug_fix, tech_debt}` OR `affected_files_count == 0`.

**Effect**: `finalize-step-simplify` is removed from `phase_6_candidates` before the rows are evaluated. Equivalently — phrased as the activation gate — `default:finalize-step-simplify` lands in `phase_6.steps` **whenever `change_type ∈ {feature, bug_fix, tech_debt}` AND `affected_files_count > 0`** (and the step is present in the candidate set). The pre-filter is the subtraction-only expression of that gate: the step is a candidate by default and dropped when the gate fails, matching the manifest architecture where rows and pre-filters only ever narrow the candidate list.

**Enum reconciliation**: the source plan phrased the gate in branch-prefix terms `{feature, fix, chore}`. The manifest's `change_type` vocabulary (see Inputs table) uses `feature` / `bug_fix` / `tech_debt`. The mapping is explicit: branch-prefix `fix` → `change_type: bug_fix`, branch-prefix `chore` → `change_type: tech_debt`, `feature` → `feature` unchanged. The gate is therefore `change_type ∈ {feature, bug_fix, tech_debt}` — the three code-touching change types — excluding `analysis`, `enhancement`, and `verification`.

**Why a pre-filter (not an eighth row)**: Activation depends only on `change_type` and `affected_files_count` and uses no language detection — it is domain-agnostic by construction (the cognitive simplification pass applies to any code or doc change in scope). The gate is orthogonal to the scope / recipe inputs the seven-row matrix consumes, and expressing it as a pre-filter keeps the seven-row matrix unchanged.

**Decision log line** (in addition to the row's own log line and any other pre-filter log line):

```text
(plan-marshall:manage-execution-manifest:compose) finalize-step-simplify omitted — change_type={value} affected_files_count={N}
```

When the gate passes (`change_type ∈ {feature, bug_fix, tech_debt}` AND `affected_files_count > 0`), the pre-filter is a no-op and emits no log entry; `finalize-step-simplify` survives into the seven-row matrix.

**Evaluation order vs. the seven-row matrix**: This pre-filter runs *after* `pre_submission_self_review_inactive` and *before* every row of the seven-row matrix.

### Pre-Filter: `security_audit_inactive`

**Condition**: `change_type ∉ {feature, bug_fix, tech_debt}` OR `affected_files_count == 0` — the same gate as `simplify_inactive`.

**Effect**: `finalize-step-security-audit` is removed from `phase_6_candidates` before the rows are evaluated. Equivalently — phrased as the activation gate — `default:finalize-step-security-audit` lands in `phase_6.steps` **whenever `change_type ∈ {feature, bug_fix, tech_debt}` AND `affected_files_count > 0`** (and the step is present in the candidate set). The proactive security sweep has no change surface to audit on a pure-analysis / verification plan or a zero-files plan, so the gate is identical to `simplify_inactive` — a subtraction-only expression matching the manifest architecture where rows and pre-filters only ever narrow the candidate list.

**Why a pre-filter (not an eighth row)**: Activation depends only on `change_type` and `affected_files_count`, orthogonal to the scope / recipe inputs the seven-row matrix consumes. The branch-prefix enum reconciliation (`fix → bug_fix`, `chore → tech_debt`) documented for `simplify_inactive` applies verbatim. Expressing it as a pre-filter keeps the seven-row matrix unchanged.

**Decision log line** (in addition to the row's own log line and any other pre-filter log line):

```text
(plan-marshall:manage-execution-manifest:compose) finalize-step-security-audit omitted — change_type={value} affected_files_count={N}
```

When the gate passes (`change_type ∈ {feature, bug_fix, tech_debt}` AND `affected_files_count > 0`), the pre-filter is a no-op and emits no log entry; `finalize-step-security-audit` survives into the seven-row matrix.

**Evaluation order vs. the seven-row matrix**: This pre-filter runs immediately *after* `simplify_inactive` (its symmetric peer) and *before* `scope_gated_finalize` and every row of the seven-row matrix.

### Pre-Filter: `scope_gated_finalize`

**Condition**: `scope_estimate ∈ {surgical, single_module}`. This is the sole entry condition for the pre-filter. `drop_review_on_scope_gate == true` is a *modifier* that only takes effect when the scope condition already holds — it is never a standalone trigger, so on `multi_module` / `broad` / `none` plans the override is inert.

**Effect**: heavyweight phase-6 review/audit steps are removed from `phase_6_candidates` by scope before the rows are evaluated:

- **`scope_estimate == 'surgical'`** — drops `plan-marshall:plan-retrospective`, pre-submission-self-review, and `project:finalize-step-plugin-doctor`. Every bare and prefixed form is matched: for pre-submission-self-review this covers the built-in `default:pre-submission-self-review` (normalized to bare `pre-submission-self-review` at intake). The candidate list is `default:`-namespace-normalized at intake, but `project:` / `bundle:skill` prefixes are preserved verbatim.
- **`scope_estimate == 'single_module'`** — drops only `plan-marshall:plan-retrospective`.
- **`scope_estimate ∈ {none, multi_module, broad}`** — no implicit subtraction; the full candidate set survives into the matrix.

**The deliberate `plan-marshall:automatic-review` carve-out**: the implicit scope gate NEVER drops `plan-marshall:automatic-review`. The active `bot_enforcement_guard` (documented below) re-adds `plan-marshall:automatic-review` in-place on any GitHub/GitLab plan where it is missing, so an implicit drop would be a silently-undone no-op — and dropping it would contradict the documented invariant that "review gates a project opted into are NEVER silently suppressed by the planner". The only path that suppresses `plan-marshall:automatic-review` is the explicit `drop_review_on_scope_gate` opt-in: when `marshal.json`'s `plan.phase-6-finalize.drop_review_on_scope_gate` is `true` **and** the plan is itself scope-gated (`scope_estimate ∈ {surgical, single_module}`), the scope gate additionally drops `plan-marshall:automatic-review`. The override is scoped, not global — on `multi_module` / `broad` / `none` plans it is inert, so flipping the project-wide knob can never silently disable bot review on a large plan. The default (`false`) keeps the bot-review invariant intact. This resolves the request's "exclude plan-marshall:automatic-review for surgical scope" instruction by extending — not contradicting — the bot-enforcement model: the exclusion is opt-in and explicit, never implicit.

**Why a pre-filter (not an eighth row)**: the subtraction depends only on `scope_estimate` (and the `drop_review_on_scope_gate` config knob), both orthogonal to the change-type / recipe inputs the seven-row matrix consumes. Modeling it as a pre-filter keeps the seven-row matrix unchanged and is consistent with the composer's "rows and pre-filters only ever narrow the candidate list" architecture. It runs after `simplify_inactive` and before the matrix and the bot-enforcement guard, so every row — and the guard — sees a candidate list already narrowed by the scope gate.

**Decision log line** (one per subtraction, in addition to the row's own log line and any other pre-filter log line):

```text
(plan-marshall:manage-execution-manifest:compose) scope_gated_finalize subtraction — scope_estimate={value}, dropped {step} from phase_6.steps
```

When `scope_estimate ∈ {none, multi_module, broad}` and `drop_review_on_scope_gate == false`, the pre-filter is a no-op and emits no log entry; the full candidate set survives into the seven-row matrix.

**Evaluation order vs. the seven-row matrix**: This pre-filter runs *after* `simplify_inactive` and *before* every row of the seven-row matrix and the bot-enforcement guard.

## Generic documentation recognition (no build owner)

Documentation is **not** a build-system concern and has **no build-extension owner**. Doc-change recognition is therefore a generic, extension-agnostic file-suffix fact owned by the aggregator itself, not a build-extension claim. Before any build-extension iteration, the aggregator tags every path ending in one of `_DOC_SUFFIXES` (`.md` / `.adoc` / `.asciidoc`) with the `documentation` footprint role and removes it from the set handed to the build extensions. A documentation path is therefore:

- never claimed or contested by a build extension (it is split out before they run),
- never subject to longest-glob-wins overlap resolution (no extension competes for it),
- never tagged `unknown` (the generic suffix rule always recognizes it).

The build extensions (`build-pyproject` / `build-maven` / `build-gradle` / `build-npm`) supply only the production / test / config roles; documentation is sourced exclusively by the generic suffix rule. This keeps the `documentation_only` / `mixed_with_docs` bucket vocabulary unchanged — only the SOURCE of doc recognition is the generic inline rule rather than an extension.

## Overlap resolution policy

When the path union contains a **non-documentation** path claimed by more than one build extension (e.g., two build systems serving the same domain both claim a production source path), the aggregator resolves the conflict via **longest-glob-wins specificity**:

1. For each claiming extension, the aggregator calls `classify_path_specificity(path, role)` — a companion method on `BuildExtensionBase` documented in `extension-api/standards/extension-contract.md`. Each extension returns a non-negative integer score equal to the count of non-wildcard path-segment tokens in the glob that matched `path` for `role`.
2. The extension with the **highest** specificity score wins the path under its declared role.
3. Ties break **alphabetically on the extension's domain key** (`d.get('domain', {}).get('key')`) — deterministic and order-independent.

Order-independence is structural: the aggregator collects every build extension's claims first, then resolves overlaps. Extension load order is irrelevant. Documentation paths never enter this resolution — they are recognized generically (see above) before the build extensions run.

## Unclaimed paths

A **non-documentation** path no build extension claims is tagged `unknown` by the aggregator AND surfaces as a `[STATUS]` decision-log warning naming each unclaimed path. Documentation paths are never unclaimed — the generic suffix rule always recognizes them. The aggregator **never** silently falls back to `documentation_only` for unclaimed code paths. The `unknown` tag forces the plan-wide bucket to `unknown`, which downstream guards (e.g., the `phase-3-outline` File-type classifier section) treat as a hard error requiring user resolution.

**Decision log line** (emitted at most once per compose call when at least one path is unclaimed):

```text
(plan-marshall:manage-execution-manifest:classify) [STATUS] Unclaimed paths tagged unknown: [<list of paths>]
```

The never-silently-drop policy is load-bearing: an unclassified path indicates either a missing domain extension OR a brand-new file type the project has not yet declared, and silently routing it to `documentation_only` would suppress the holistic Python verification that the path may actually need. Surfacing `unknown` forces the user (or the future Q-Gate finding) to declare the path's role explicitly.

## plan.phase-6-finalize Selection

**Type**: Composition-time post-matrix transform (NOT a pre-filter). Runs *after* the seven-row matrix has produced the final `phase_6.steps` list and *after* `execution_tier` routing, *before* the `bot_enforcement_guard`.

**Inputs**: the four `plan.phase-6-finalize` run-at-all gates, read directly from `marshal.json::plan.phase-6-finalize`:

| Gate | Finalize step it controls | Run-at-all values |
|------|---------------------------|-------------------|
| `self_review` | `default:pre-submission-self-review` | `always` \| `never` \| `auto` (default) |
| `qgate` | `pre-push-quality-gate` (finalize blocking-findings re-capture) | `always` \| `never` \| `auto` (default) |
| `simplify` | `finalize-step-simplify` (holistic post-implementation simplification sweep) | `always` \| `never` \| `auto` (default) |
| `security_audit` | `finalize-step-security-audit` (proactive security sweep) | `always` \| `never` \| `auto` (default) |

**Gate resolution**: the composer reads `marshal.json::plan.phase-6-finalize.<gate>` directly (merging the canonical `auto` default under any absent gate). `qgate` is a flat phase-local knob; `simplify`, `self_review`, and `security_audit` are folded under their owning step's nested param object in `phase-6-finalize.steps`. There is no condition-scoped override layer.

**Effect** (per gate, against the matrix-produced `phase_6.steps`):

- **`never`** — every match-set form of the gate's step (bare and `project:`-prefixed) is removed from `phase_6.steps`. A no-op when already absent. The composer applies the resolved value directly.
- **`always`** — the gate's canonical step is ensured present, inserted before the plan-mutating tail (`archive-plan` / `record-metrics` / `branch-cleanup` / `plan-marshall:plan-retrospective`) when absent. A no-op when any match-set form is already present. `always` is the **only** path that can re-add a step the relevant pre-filter dropped — that is the point: an operator-set `always` overrides the implicit gate. For `self_review` / `qgate` the overridden pre-filter is `scope_gated_finalize`; for `simplify` it is `simplify_inactive`; for `security_audit` it is `security_audit_inactive`.
- **`auto`** (the default) — defer to the existing decision machinery already applied before this transform. For `self_review` / `qgate` that is the `scope_gated_finalize` pre-filter and the seven-row matrix; for `simplify` it is the `simplify_inactive` pre-filter and for `security_audit` the `security_audit_inactive` pre-filter (both drop the step when `change_type ∉ {feature, bug_fix, tech_debt}` OR `affected_files_count == 0`). No-op in every case.

**The deliberate `plan-marshall:automatic-review` carve-out**: this transform's gate map contains only the four finalize steps (`default:pre-submission-self-review`, `pre-push-quality-gate`, `finalize-step-simplify`, `finalize-step-security-audit`). It NEVER adds or drops `plan-marshall:automatic-review`, so the bot-review invariant (`bot_enforcement_guard`) is structurally preserved regardless of any gate value. The two transforms are orthogonal: finalize selection forces the four review/simplify/security gates per operator policy; the bot guard independently ensures `plan-marshall:automatic-review` is scheduled on GitHub/GitLab plans.

**Why a post-matrix transform (not a pre-filter)**: `always` must be able to re-add a step that `scope_gated_finalize` removed before the matrix ran. A pre-filter runs before the matrix, so it cannot express force-include against a subtraction the scope gate already applied. Running after the matrix lets the transform see the final list and override both the scope gate and any row-level narrowing.

**Decision log line** (one per forced change, in addition to the row's own log line and any pre-filter log lines):

```text
(plan-marshall:manage-execution-manifest:compose) ceremony_finalize selection — finalize.{gate}={value}, {added|dropped} {step} {to|from} phase_6.steps
```

When all four gates resolve to `auto` (the default), the transform is a no-op and emits no log entry.

**Cross-reference**: the gate schema (run-at-all enum, defaults) is owned by [`manage-config/standards/data-model.md`](../../manage-config/standards/data-model.md) § phase-6-finalize — this section documents only how the composer consumes the four finalize gates. Do not restate the schema here.

## Execution-profile lane resolution

**Type**: Composition-time post-matrix transform (NOT a pre-filter). Runs *after* the seven-row matrix, the change-type / scope pre-filters, and `ceremony_finalize_selection` have produced the final `phase_6.steps`, and *before* the `bot_enforcement_guard`.

**Posture source**: `status.metadata.execution_profile`, one of `minimal` / `auto` / `full`. An absent or invalid value resolves to `full`, which is a no-op — every plan that never chose a posture composes exactly as it did before the lane mechanism existed (the back-compat default).

**Contract ownership**: the closed `lane.class` enum (`derived-state` / `core` / `adversarial` / `prunable`), the class→default-tier table, the resolution lattice `minimal ⊏ auto ⊏ full`, the per-element override vocabulary (`off | minimal | auto | full | ask`), and the `cost_size` binding are owned by [`extension-api/standards/ext-point-lane-element.md`](../../extension-api/standards/ext-point-lane-element.md). This section documents only how the composer consumes them. Do not restate the enums here.

**Per-element resolution**: for each step in `phase_6.steps` the composer resolves the element's `lane:` frontmatter block (built-in steps via the standards / workflow doc; `project:` steps via the project-local `{bare}/SKILL.md`). It then resolves the effective tier — per-element `marshal.json` `lane` override ▸ declared `lane.tier` ▸ class default — and keeps the element iff `effective_tier ⊑ posture`:

- `minimal` keeps only the tier-`minimal` floor (`core` / `derived-state`, plus the `minimal`-deviated `lessons-capture` / `lessons-housekeeping`);
- `auto` additionally keeps tier-`auto` elements and drops tier-`full` ones (`security-audit`, `plan-retrospective`);
- `full` keeps everything.

An element with no `lane:` block is not lane-participating and is always kept. An `off` override drops the element; when it weakens a `derived-state` / `core` floor element the drop is **honored but emits a correctness warning** (the lane-selection design §5 — `minimal` must never *silently* drop required derived state). An `ask` effective tier keeps the element at compose time (the `phase-1-init` dialogue owns the per-element prompt).

**Why before the bot guard**: a `minimal` posture drops the adversarial `plan-marshall:automatic-review` step, but the `bot_enforcement_guard` (next section) re-adds it for GitHub/GitLab plans. Running the lane pass first means the adversarial-floor / bot-review invariant re-asserts `plan-marshall:automatic-review` on CI plans even under `minimal` — exactly the §4.9 precedence (operator posture < coverage-cell adversarial floor). **The q-gate is never a phase-6 finalize step, so the lane pass never touches it** — the adversarial q-gate is always kept.

**Twice-compose timing**: `compose` runs at init (provisional `auto` footprint prunes) and again at end-of-phase-4 (idempotent re-compose with firm signals). The posture and the `minimal` / `full` shapes are fixed at init; only `auto`'s footprint-gated prunes can move on the second call, in the safe more-validation direction, and that refinement is **logged, never re-prompted**.

**Decision log lines** (in addition to the row + pre-filter lines):

```text
(plan-marshall:manage-execution-manifest:compose) lane_resolution — execution_profile={posture}, dropped {steps} from phase_6.steps (tier above posture cutoff)
(plan-marshall:manage-execution-manifest:compose) lane_resolution warning — {step}: override 'off' drops {class} floor element — honored, but weakening a required element
```

When the posture is `full` (or no lane-participating element is above the cutoff), the transform is a no-op and emits no log entry. The composer surfaces `execution_profile`, `lane_dropped`, and `lane_warnings` in the `compose` result for observability.

## Bot-Enforcement Guard

**Type**: Composition-time defense-in-depth remediation (NOT a pre-filter, NOT an assertion). Runs *after* the seven-row matrix has produced the final `phase_6.steps` list, *before* the manifest is persisted.

**Condition**: `ci_provider ∈ {github, gitlab}` AND `plan-marshall:automatic-review` is NOT in the assembled `phase_6.steps` list.

**Effect**: Appends `plan-marshall:automatic-review` to the final `phase_6.steps` list in-place and emits a decision-log entry recording the remediation. The composition continues normally and the manifest is written with `plan-marshall:automatic-review` restored. The guard preserves matrix orthogonality — Row 5's subtraction logic (and any future pre-filter or row that legitimately drops `plan-marshall:automatic-review`) stays unchanged; the guard puts the step back so the final manifest is GitHub/GitLab-compliant.

**Why remediation rather than assertion**: The original assertion-style guard deadlocked every `surgical+{bug_fix, tech_debt}` plan that finalized through GitHub or GitLab — Row 5 of the seven-row matrix legitimately drops `plan-marshall:automatic-review` for those plans, and the assertion then refused to write the manifest. The remediation strategy (Option 2) keeps Row 5's subtraction intact and converts the guard from assertion to remediation. The matrix's documented orthogonality (its inputs are change_type / scope / recipe only) is preserved.

**Why retained after the deadlock fix (defense-in-depth)**: `plan-marshall:automatic-review` is effectively mandatory on plans that finalize through GitHub or GitLab — review bots catch a class of structural defects the local gates systematically miss, and silently dropping the bot-review step (e.g., via a future pre-filter, a recipe interaction, or a row addition we haven't designed yet) would defeat the entire pre-submission-self-review story. The guard is now defense-in-depth alongside `phase-6-finalize/standards/required-steps.md` — the required-steps file ensures completion semantics for the handshake invariant; this guard ensures the step is even scheduled in the first place, and self-heals if anything upstream drops it.

**Decision log line** (emitted whenever the guard remediates; one entry per remediation):

```text
(plan-marshall:manage-execution-manifest:compose) bot-enforcement guard remediated — ci_provider=github, plan-marshall:automatic-review re-added to phase_6.steps
```

When `ci_provider` is neither `github` nor `gitlab`, OR `plan-marshall:automatic-review` is already present in `phase_6.steps`, the guard is a no-op and emits no log entry.

**Safety-net error path**: The function still has a non-`None` return contract (`str | None`) and the caller (`cmd_compose`) still translates a non-`None` return into a `bot_enforcement_violation` error TOON. In current code this branch is unreachable — the guard either no-ops (returns `None`) or remediates and returns `None`. The branch is retained as a hook for any future logic that detects a non-remediable violation (e.g., a malformed `phase_6_steps` list), so the legacy `bot-enforcement guard fired` log line and error TOON shape remain documented in the codebase even though they are not exercised by the current control flow.

## Frontmatter-Order Sort

**Type**: Composition-time post-matrix transform (NOT a pre-filter, NOT an assertion). Runs *after* the `bot_enforcement_guard` (so a guard-re-added `plan-marshall:automatic-review` participates in the sort) and *before* the compose-time placement validator (`_validate_automatic_review_placement`) and manifest persistence, so the validator asserts against the final, sorted layout.

**Condition**: unconditional — the transform runs on every compose. It is a no-op (identity reorder) when the list is already in ascending frontmatter `order`.

**Effect**: `phase_6.steps` is reordered into ascending frontmatter `order` via `_sort_steps_by_frontmatter_order` (`_manifest_validation.py`):

- Every entry whose `_resolve_step_order` is not `None` is sorted into ascending resolved-order position; the stable sort preserves the relative sequence of entries sharing an equal `order` value.
- Entries whose order resolves to `None` — non-string entries and external `bundle:skill` steps with no resolvable source file — keep their exact original index, acting as fixed pins that the sortable entries flow around (the same "skipped, does not participate" convention as `_check_ascending_order`).
- Because every finalize step's declared `order` is below `archive-plan`'s 1000 (nearest tail: `record-metrics` 998, `finalize-step-print-phase-breakdown` 999), the sort makes `archive-plan` the terminal barrier by construction — no order-resolvable step follows it unless its own frontmatter documents a post-archive `order >= 1000` (currently none do).

**Why**: the composer treats the marshal.json `phase_6.steps` id-keyed map (or the default candidate list) as authoritative for execution order, and `manage-config sync-defaults` back-fills a missing default-on step by dict assignment — appending the new key at the END of the map regardless of its frontmatter `order`. That landed e.g. `finalize-step-preference-emitter` (order 80) after `archive-plan` (order 1000), a layout that fails at dispatch time because archive moves the plan directory. The sort is the single terminal choke-point correcting any upstream seed or insertion misordering (sync-defaults appends, manual marshal.json edits, forced insertions). It is the compose-time companion of the `_check_ascending_order` validator: the composer sorts so the barrier invariant holds; the validator asserts the sort held.

**Interaction with anchor-based insertion helpers**: the ceremony-finalize and bot-enforcement insertion helpers anchor before the plan-mutating tail, and `plan-marshall:automatic-review` (order 30) sorts below that tail, so the sort preserves — rather than competes with — those placement intents. The placement validator sees the sorted list and passes by construction for order-resolvable steps; it remains defense-in-depth for order-unresolvable ones.

**Decision log line**: none — the transform is deterministic, unconditional, and emits no dedicated log entry; the composed `phase_6.steps` in the rule's own decision-log line reflects the sorted order.

## execution_tier Routing

**Type**: Composition-time per-task routing pass. Runs *after* the seven-row matrix has produced the body's `phase_5.verification_steps` and `phase_6.steps`, *before* the bot-enforcement guard. Mutates both the manifest body and the plan's `TASK-*.json` files.

**Inputs** (per task):

| Input | Source | Type |
|-------|--------|------|
| `verification.commands` | `{plan_dir}/tasks/TASK-*.json` | list[string] |
| Resolve TOON | `architecture resolve --command {verb} --module {module}` (subprocessed via the executor) | dict — see [the augmented resolve contract](../../manage-architecture/standards/resolve-command.md) |

**Routing predicate** (per command):

- **`execution_tier == 'orchestrator'`**: the command's adaptive Bash timeout has crossed the 600s host ceiling. The composer maps the build verb to the matching boundary-normalized canonical-verify step ID (`quality-gate → verify:quality-gate`, `verify` / `module-tests → verify:module-tests`, `coverage → verify:coverage`), appends it (de-duped) to `phase_5.verification_steps`, and drops the command from the task's `verification.commands`. A task whose entire `verification.commands` list routes to orchestrator ends up with an empty list — that is the correct "all orchestrator" signal.
- **`execution_tier == 'per_task'`**: the command fits inside the Bash ceiling. The composer writes `bash_timeout_seconds` into the task's `verification` dict alongside `commands` so the dispatched sub-agent reads the numeric timeout directly. When a task has multiple `per_task` commands, the maximum `bash_timeout_seconds` wins (the sub-agent honours the most-demanding command).
- **No `execution_tier` field** (non-build executable — raw shell, `grep`, `manage-*` notation): the command stays in the task and no `bash_timeout_seconds` annotation is added. Today's behaviour is preserved.

**Idempotence**: every compose call re-derives the routing from the live `architecture resolve` output. Re-composing after a tier shift converges deterministically — orchestrator commands stay pruned, `bash_timeout_seconds` is overwritten when its value changes, and the stale annotation is stripped when no `per_task` commands survive.

**Decision log line** (emitted on every compose, regardless of mutation count):

```text
(plan-marshall:manage-execution-manifest:compose) execution_tier routing — mutated_tasks={N}, phase_5.verification_steps={list}
```

**Cross-references**: `manage-architecture/standards/resolve-command.md` (the four-field augmented resolve TOON and the ≈600K-token re-dispatch failure mode that motivated it); `persona-plan-marshall-agent` (the sub-agent rule that consumes `bash_timeout_seconds`).

## Role-Field Intersection

Rows 2, 3, 5, and 6 intersect the `phase_5_candidates` list against a set of canonical roles (`{quality-gate}`, `{module-tests}`, `{quality-gate, module-tests}`) rather than against literal step IDs. The mechanism is structural: each phase-5 step standards file under `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/` declares its role in YAML frontmatter (e.g., `role: quality-gate` on `quality_check.md`, `role: module-tests` on `build_verify.md`, `role: coverage` on `coverage_check.md`). At compose time the composer resolves each candidate step ID to its source file and reads the `role:` value; intersection is `candidate_role ∈ {target_role, ...}` rather than `candidate_id ∈ {literal_id, ...}`.

This decouples canonical names from intersection logic. The composer never compares candidate step IDs directly against literal strings like `'quality-gate'` — those names are role values, not step IDs. Step IDs are arbitrary handles (e.g., `default:verify:quality-gate`, `default:verify:module-tests`) whose intersection-meaningful attribute is the role derived from their canonical segment.

**External steps** (`project:` and `bundle:skill` prefixes) have no role file and resolve to `role = None`; they are therefore never selected by any role-based intersection. This is the correct behavior: Rows 2/3/5/6 select built-in verify steps only.

**Drift enforcement**: A `MISSING_ROLE_FIELD` analyzer in `pm-plugin-development:plugin-doctor` flags any phase-5 step standards file missing the `role:` frontmatter field at edit time, preventing future name-drift defects.

### Role derivation for canonical-verify steps

The single parameterized canonical-verify step (`default:verify:{canonical}`; see [`phase-5-execute/standards/canonical_verify.md`](../../phase-5-execute/standards/canonical_verify.md)) has **no per-canonical role-file**. Its matrix `role:` is derived by `_role_of` from the trailing `{canonical}` segment via the `_CANONICAL_TO_ROLE` table — the composer's copy of the canonical→role mapping owned by `canonical_verify.md`:

| canonical segment | derived `role:` |
|-------------------|-----------------|
| `quality-gate` | `quality-gate` |
| `verify` / `module-tests` | `module-tests` |
| `coverage` | `coverage` |
| `integration-tests` | `integration` |
| `e2e` | `e2e` |

A `default:verify:{canonical}` (or its bare `verify:{canonical}`) ID is recognized before the role-file read path; an unrecognized canonical resolves to `role = None` (and is therefore never role-selected), preserving the "missing data → step is never role-selected" convention. This is the generalization that lets the role intersection (Rows 2/3/5/6) and the docs-only heuristic operate on the parameterized canonical-verify vocabulary without a per-canonical role-file for each command.

## Generic footprint pre-filter (`canonical_verify_inactive`)

**Type**: Composition-time phase-5 pre-filter. Runs *after* the seven-row matrix and `execution_tier` routing have produced the final `phase_5.verification_steps` list — so it sees every canonical-verify step that will be persisted, including any appended by orchestrator-tier routing.

**Condition**: a `default:verify:{canonical}` step whose derived role is a **footprint-gated whole-tree role** (`integration` / `e2e`) is dropped when the live footprint is **non-empty** AND carries **no path** of that role. The gate is canonical-agnostic — it is driven entirely by the `_CANONICAL_TO_ROLE` derivation plus the `_FOOTPRINT_GATED_CANONICAL_ROLES` membership table, with no per-canonical branch in the code path. The core roles (`quality-gate` / `module-tests` / `coverage`) are NEVER footprint-gated; they always run when present.

**Safety against compose-time emptiness**: during early compose (phase-4-plan, before the worktree is materialized) the live footprint is empty, so the pre-filter is a **no-op** and every canonical survives. The gate only fires against a non-empty footprint that genuinely lacks the gating role's paths — a project with no integration/e2e sources never schedules those whole-tree gates, while every code-shaped plan keeps its core verification.

**Decision log line** (emitted only when at least one step is dropped):

```text
(plan-marshall:manage-execution-manifest:compose) canonical_verify_inactive — dropped {steps} from phase_5.verification_steps (no matching footprint role)
```

## The Seven-Row Matrix

The seven rows below are evaluated top-down; the first match wins. They operate on the (possibly pre-filtered) `phase_6_candidates` list described above. Rows 2, 3, 5, and 6 use the structural role intersection described above for their `phase_5.verification_steps` outputs; Rows 1, 4, and 7 do not consult roles (Row 1 produces an empty list, Row 4 still matches a single literal role, Row 7 passes the candidate list through unchanged).

### Row 1 — `early_terminate_analysis`

**Condition**: `change_type == analysis` AND `affected_files_count == 0`.

**Outcome**:
- `phase_5.early_terminate = true`
- `phase_5.verification_steps = []`
- `phase_6.steps` = `phase_6_candidates ∩ {lessons-capture, archive-plan}`

**Why**: A pure-analysis plan with no source-file impact has nothing to verify. Phase 6 still runs lessons capture so the analysis findings don't leak silently, and `archive-plan` finalizes the plan record.

### Row 2 — `recipe`

**Condition**: `recipe_key` is present (non-empty). The composer resolves `recipe_key` from the explicit `--recipe-key` argument when supplied, and otherwise reads it directly from `status.json::metadata.plan_source` (the raw lesson id for lesson-derived plans, or the literal `"recipe"` for recipe-routed plans), falling back to `metadata.recipe_key`. Reading the provenance from status metadata — rather than depending solely on the caller forwarding the flag — is what keeps lesson- and recipe-derived plans on this row; the prior flag-only path silently dropped them to Row 7 (`default`) whenever the planner omitted `--recipe-key`. The composer's surrogate matches the `audit-archived-plan-retrospectives` re-derivation, so a fresh recipe/lesson plan reports `actual_rule = recipe` against its `expected_rule`.

**Outcome**:
- `phase_5.early_terminate = false`
- `phase_5.verification_steps` = the candidates from `phase_5_candidates` whose declared `role:` ∈ `{quality-gate, module-tests}` (see [Role-Field Intersection](#role-field-intersection))
- `phase_6.steps = phase_6_candidates − {ci-wait}`

**Why**: Recipe-driven plans (currently `recipe-refactor-to-profile-standards` and the upcoming `recipe-lesson-cleanup` from deliverable 7) follow deterministic, surgical-style patterns. The only subtraction here is the legacy `ci-wait` step ID — kept as a defensive narrowing against project marshal.json files that still list it as a candidate. Review gates a project opted into (`plan-marshall:automatic-review`, `sonar-roundtrip`) are NEVER silently suppressed by the planner: the recipe label is exactly the case where the bots' job is to catch what humans miss. CI completion is now a dispatcher-resolved precondition (declared via `requires: [ci-complete]` on consumer step frontmatters), not a sibling step.

### Row 3 — `docs_only`

**Condition**: `scope_estimate ∈ {surgical, single_module}` AND `change_type ∈ {tech_debt, enhancement}` AND `affected_files_count > 0` AND no candidate in `phase_5_candidates` declares `role: module-tests` or `role: coverage` (see [Role-Field Intersection](#role-field-intersection)).

**Outcome**:
- `phase_5.early_terminate = false`
- `phase_5.verification_steps = []`
- `phase_6.steps = phase_6_candidates − {ci-wait}`

**Why**: A docs-shaped plan never needs to run tests or coverage. The candidate set already reflects this (no `module-tests`/`coverage`), so the manifest empties Phase 5's verification list. The only subtraction here is the legacy `ci-wait` step ID — kept as a defensive narrowing against project marshal.json files that still list it as a candidate. Review gates a project opted into (`plan-marshall:automatic-review`, `sonar-roundtrip`) are NEVER silently suppressed by the planner: a docs-only label is exactly the case where the bots' job is to catch what humans miss. We keep `push`, `create-pr`, `lessons-capture`, `branch-cleanup`, `archive-plan`, AND the review gates so the doc change is reviewed, committed, surfaced, and recorded.

### Row 4 — `tests_only`

**Condition**: `change_type == verification` AND `affected_files_count > 0`.

**Outcome**:
- `phase_5.early_terminate = false`
- `phase_5.verification_steps` = the candidates from `phase_5_candidates` whose declared `role:` == `module-tests` (see [Role-Field Intersection](#role-field-intersection))
- `phase_6.steps = phase_6_candidates` (full set)

**Why**: The plan only changes tests; we want the test suite to run but `quality-gate` is overkill since no production code moved. Phase 6 stays unconditional because new test signal benefits from the full review cycle.

### Row 5 — `surgical_bug_fix` / `surgical_tech_debt`

**Condition**: `scope_estimate == surgical` AND `change_type ∈ {bug_fix, tech_debt}`. The rule key encodes the change_type for log clarity.

**Outcome**:
- `phase_5.early_terminate = false`
- `phase_5.verification_steps` = the candidates from `phase_5_candidates` whose declared `role:` ∈ `{quality-gate, module-tests}` (see [Role-Field Intersection](#role-field-intersection))
- `phase_6.steps = phase_6_candidates − {ci-wait}`

**Why**: Surgical bug fixes and tech-debt nudges have already passed the Q-Gate bypass at outline time (deliverable 4). The only subtraction here is the legacy `ci-wait` step ID — kept as a defensive narrowing against project marshal.json files that still list it as a candidate. Review gates a project opted into (`plan-marshall:automatic-review`, `sonar-roundtrip`) are NEVER silently suppressed by the planner: surgical bug_fix / tech_debt is exactly the case where the bots' job is to catch what humans miss on a one-line fix. We keep `lessons-capture` so any lesson observed during execution is still captured. CI completion is now a dispatcher-resolved precondition (declared via `requires: [ci-complete]` on consumer step frontmatters), not a sibling step.

### Row 6 — `verification_no_files`

**Condition**: `change_type == verification` AND `affected_files_count == 0`.

**Outcome**:
- `phase_5.early_terminate = false`
- `phase_5.verification_steps = phase_5_candidates` (full)
- `phase_6.steps = phase_6_candidates ∩ {lessons-capture, archive-plan}`

**Why**: A verification plan with no affected files is a "run the existing checks" plan — keep Phase 5 fully wired (since the goal is verification) but trim Phase 6 down to the records-and-archive pair since nothing was committed.

### Row 7 — `default`

**Condition**: Any plan that doesn't match rows 1–6.

**Outcome**:
- `phase_5.early_terminate = false`
- `phase_5.verification_steps = phase_5_candidates` (full)
- `phase_6.steps = phase_6_candidates` (full)

**Why**: This is the safe baseline for code-shaped features and broader changes. The full canonical Phase 5 verification fires; Phase 6 dispatches every step `marshal.json` lists.

## Decision Log Format

For each rule fired, the composer emits one line via `manage-logging decision`:

```text
(plan-marshall:manage-execution-manifest:compose) Rule {rule_key} fired — early_terminate={bool}, phase_5.verification_steps={list}, phase_6.steps={list}
```

The component prefix `(plan-marshall:manage-execution-manifest:compose)` is mandatory so that `plan-retrospective` (deliverable 9) can correlate manifest content with the reasoning entries.

## Determinism

The decision matrix is deterministic given its inputs — re-running `compose` with the same arguments produces an identical manifest and identical decision-log entry. The composer truncates / overwrites previous manifests on re-invocation; callers (currently only `phase-4-plan` Step 8b) are responsible for re-entry semantics.
