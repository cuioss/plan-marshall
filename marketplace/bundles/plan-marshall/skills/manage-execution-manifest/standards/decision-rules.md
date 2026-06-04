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
| `live_footprint` | derived on demand from the worktree (`{base}...HEAD` ∪ porcelain via `compute_plan_branch_diff`); empty before the worktree is materialized | list[string] (default: empty) |
| `phase_5_candidates` | `marshal.json::plan.phase-5-execute.steps` | list[string] |
| `phase_6_candidates` | `marshal.json::plan.phase-6-finalize.steps` | list[string] |
| `affected_files` | `references.json::affected_files` | list[string] (read directly by the composer; empty by default in the current pipeline) |
| `modified_files` (legacy back-compat) | `references.json::modified_files` | list[string] (read by Bundle source detection only, as a back-compat fallback for archived plans that still carry the key; see "Bundle source detection" below for the union semantics with `affected_files` and the solution-outline fallback) |
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
3. **`pre_submission_self_review_inactive`** — drops `pre-submission-self-review` when the live plan footprint is empty.
4. **`simplify_inactive`** — drops `finalize-step-simplify` when `change_type ∉ {feature, bug_fix, tech_debt}` OR `affected_files_count == 0`.
5. **`scope_gated_finalize`** — drops heavyweight phase-6 review/audit steps by `scope_estimate`: `surgical` drops `plan-retrospective`, `pre-submission-self-review`, and `plugin-doctor`; `single_module` drops only `plan-retrospective`. `automated-review` is dropped ONLY via the explicit `lightweight_track_override` opt-in, never by the implicit scope gate.

Each row that emits a Phase 6 list (whether by intersection, subtraction, or pass-through) operates on the already-filtered candidate list, so the resulting `phase_6.steps` will never contain a step removed by any pre-filter that ran before the row matrix.

After the seven-row matrix runs, two post-matrix transforms inspect the matrix output before the manifest is persisted:

1. **Docs-only classifier (post-matrix)** — when the plan-wide union of every deliverable's `affected_files` resolves to the `documentation_only` bucket via the six-bucket file-type classifier (per-domain extension aggregation; see "Overlap resolution policy" and "Unclaimed paths" below), holistic Python verification steps (`quality-gate`, `module-tests`, `coverage`) are suppressed from `phase_5.verification_steps`. See "Post-Matrix Rule: docs-only classifier" below.
2. **`bot_enforcement_guard`** — on GitHub/GitLab plans where `default:automated-review` is missing from the final `phase_6.steps`, the guard remediates in-place by appending it back to the list (defense-in-depth, not assertion). The guard is documented in its own subsection below the pre-filter sections.

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
- the live plan footprint is empty, OR
- No entry in the live footprint matches any glob in `activation_globs` (using `fnmatch.fnmatch`).

**Effect**: `pre-push-quality-gate` is removed from `phase_6_candidates` before the rows are evaluated. When `pre-push-quality-gate` was already removed by `commit_strategy_none`, this pre-filter is a no-op and emits no log entry.

**Why a pre-filter (not an eighth row)**: Activation is project configuration paired with a glob match against the live footprint, both orthogonal to the change-type / scope / recipe inputs that the seven-row matrix consumes. A row would either have to short-circuit and re-implement Phase 5 logic, or duplicate the filter into every row. Keeping it as a pre-filter preserves the seven-row matrix verbatim and adds exactly one independent decision-log line.

**Decision log line** (in addition to the row's own log line and any other pre-filter log line):

```
(plan-marshall:manage-execution-manifest:compose) pre-push-quality-gate omitted — activation_globs empty or no footprint match
```

When all three activation conditions are satisfied (non-empty globs, non-empty footprint, at least one glob match), the pre-filter is a no-op and emits no log entry; `pre-push-quality-gate` survives into the seven-row matrix.

**Evaluation order vs. the seven-row matrix**: This pre-filter runs *after* `commit_strategy_none` and *before* every row of the seven-row matrix. The pre-filter is therefore observable independently — Row 7 (default), Row 5 (surgical_bug_fix / surgical_tech_debt), and Row 2 (recipe) all see a Phase 6 candidate list that already has `pre-push-quality-gate` removed if either pre-filter fired.

### Pre-Filter: `pre_submission_self_review_inactive`

**Condition**: the live plan footprint is empty.

**Effect**: `pre-submission-self-review` is removed from `phase_6_candidates` before the rows are evaluated. When `pre-submission-self-review` was already removed by `commit_strategy_none`, this pre-filter is a no-op and emits no log entry.

**Why a pre-filter (not an eighth row)**: Activation depends only on the live footprint being non-empty (the four cognitive checks have no diff to inspect when the plan touched zero files). The condition is orthogonal to the change-type / scope / recipe inputs the seven-row matrix consumes. There is no `activation_globs` config knob — the four structural-defect classes the step targets (symmetric pairs, regex over-fit, wording, duplication) apply to any code or doc change, and gating by file extension would mean missing the very wording/duplication defects the lesson cites for `.md` files.

**Decision log line** (in addition to the row's own log line and any other pre-filter log line):

```
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

```
(plan-marshall:manage-execution-manifest:compose) finalize-step-simplify omitted — change_type={value} affected_files_count={N}
```

When the gate passes (`change_type ∈ {feature, bug_fix, tech_debt}` AND `affected_files_count > 0`), the pre-filter is a no-op and emits no log entry; `finalize-step-simplify` survives into the seven-row matrix.

**Evaluation order vs. the seven-row matrix**: This pre-filter runs *after* `pre_submission_self_review_inactive` and *before* every row of the seven-row matrix.

### Pre-Filter: `scope_gated_finalize`

**Condition**: `scope_estimate ∈ {surgical, single_module}`. This is the sole entry condition for the pre-filter. `lightweight_track_override == true` is a *modifier* that only takes effect when the scope condition already holds — it is never a standalone trigger, so on `multi_module` / `broad` / `none` plans the override is inert.

**Effect**: heavyweight phase-6 review/audit steps are removed from `phase_6_candidates` by scope before the rows are evaluated:

- **`scope_estimate == 'surgical'`** — drops `plan-marshall:plan-retrospective`, `project:finalize-step-pre-submission-self-review`, and `project:finalize-step-plugin-doctor`. Both bare and prefixed forms are matched (the candidate list is `default:`-namespace-normalized at intake, but `project:` / `bundle:skill` prefixes are preserved verbatim, so the match-set lists both forms).
- **`scope_estimate == 'single_module'`** — drops only `plan-marshall:plan-retrospective`.
- **`scope_estimate ∈ {none, multi_module, broad}`** — no implicit subtraction; the full candidate set survives into the matrix.

**The deliberate `automated-review` carve-out**: the implicit scope gate NEVER drops `automated-review`. The active `bot_enforcement_guard` (documented below) re-adds `automated-review` in-place on any GitHub/GitLab plan where it is missing, so an implicit drop would be a silently-undone no-op — and dropping it would contradict the documented invariant that "review gates a project opted into are NEVER silently suppressed by the planner". The only path that suppresses `automated-review` is the explicit `lightweight_track_override` opt-in: when `marshal.json`'s `plan.phase-6-finalize.lightweight_track_override` is `true` **and** the plan is itself scope-gated (`scope_estimate ∈ {surgical, single_module}`), the scope gate additionally drops `automated-review`. The override is scoped, not global — on `multi_module` / `broad` / `none` plans it is inert, so flipping the project-wide knob can never silently disable bot review on a large plan. The default (`false`) keeps the bot-review invariant intact. This resolves the request's "exclude automated-review for surgical scope" instruction by extending — not contradicting — the bot-enforcement model: the exclusion is opt-in and explicit, never implicit.

**Why a pre-filter (not an eighth row)**: the subtraction depends only on `scope_estimate` (and the `lightweight_track_override` config knob), both orthogonal to the change-type / recipe inputs the seven-row matrix consumes. Modeling it as a pre-filter keeps the seven-row matrix unchanged and is consistent with the composer's "rows and pre-filters only ever narrow the candidate list" architecture. It runs after `simplify_inactive` and before the matrix and the bot-enforcement guard, so every row — and the guard — sees a candidate list already narrowed by the scope gate.

**Decision log line** (one per subtraction, in addition to the row's own log line and any other pre-filter log line):

```
(plan-marshall:manage-execution-manifest:compose) scope_gated_finalize subtraction — scope_estimate={value}, dropped {step} from phase_6.steps
```

When `scope_estimate ∈ {none, multi_module, broad}` and `lightweight_track_override == false`, the pre-filter is a no-op and emits no log entry; the full candidate set survives into the seven-row matrix.

**Evaluation order vs. the seven-row matrix**: This pre-filter runs *after* `simplify_inactive` and *before* every row of the seven-row matrix and the bot-enforcement guard.

## Post-Matrix Rule: docs-only classifier

**Activation**: runs unconditionally after the seven-row matrix and before the bot-enforcement guard. The rule inspects the plan-wide union of every deliverable's `affected_files` and classifies it via the per-domain extension aggregator (`_classify_paths_via_extensions`). The aggregator dispatches each path to every registered `ExtensionBase.classify_paths()` and resolves overlaps via longest-glob-wins specificity (see "Overlap resolution policy" below). The bucket vocabulary and per-bucket profile assignments are the normative source of truth in `marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/outline-workflow-detail.md` § File-type classifier — this rule consumes the same vocabulary at composer scope.

**Predicate**: `_classify_paths_via_extensions(union_of_affected_files) == "documentation_only"`, where:

- `union_of_affected_files` is the result of `_read_bundle_change_paths(plan_id)` — the union of `references.json::affected_files`, the legacy `references.json::modified_files` key (read only as a back-compat fallback for older plans that still carry it), and the deliverable-level `**Affected files:**` blocks in `solution_outline.md` (the same fallback chain Row 3's `_looks_docs_only` heuristic does not see, because that heuristic keys on phase-5 candidate roles rather than actual file paths).
- The six buckets and the per-domain predicates that produce them are documented centrally in `extension-api/standards/extension-contract.md` § classify_paths() — do NOT inline-copy them here.

**Effect**: every entry in `phase_5.verification_steps` whose `role:` frontmatter resolves to `quality-gate`, `module-tests`, or `coverage` is removed. Other entries (e.g., `pre-submission-self-review`, future role types) pass through unchanged. The rule is a no-op when:

- The plan-wide bucket is not `documentation_only` (i.e., the plan touches at least one production or test file; config-only plans still collapse to `documentation_only`).
- The seven-row matrix already produced an empty `phase_5.verification_steps` (Row 1 `early_terminate_analysis`, Row 3 `docs_only`).
- The matrix's surviving entries carry no holistic Python roles (the rule still runs but filters nothing).

**Rationale**: the composer-layer docs-only branch and the per-deliverable classifier at phase-3-outline converge on the same six-bucket vocabulary. The per-deliverable classifier at outline time refuses to assign `module_testing` to a `documentation_only` deliverable; this post-matrix rule extends the same logic to the plan-wide composition layer, where the union of every deliverable's affected files determines whether holistic Python verification has any meaningful target. Without this rule, a `feature`-type plan whose deliverables all happen to be docs-only would emit holistic `quality-gate` and `module-tests` steps that burn execution time on files that are not testable Python.

**Why post-matrix (not a new row)**: the seven-row matrix keys on `change_type` / `track` / `scope_estimate` / `recipe_key` / `affected_files_count` — none of which can read the actual file paths. The plan-wide bucket is a path-content predicate that is orthogonal to the row inputs. Modeling it as a post-matrix transform keeps the seven-row matrix unchanged and lets the composer emit one extra `decision.log` entry naming the suppression. The rule layers on TOP of Row 3 (`docs_only`) — Row 3 keys on the role heuristic and catches plans where the candidate set itself signals docs-only; this rule catches plans where the candidate set looks code-shaped but the actual affected files are all docs.

**Worked example** — a plan with `change_type: bug_fix`, `scope_estimate: surgical`, `affected_files_count: 3`, and `affected_files: ["a/SKILL.md", "b/outline-workflow-detail.md", "c/SKILL.md"]`:

1. Seven-row matrix evaluates: Row 5 (`surgical_bug_fix`) fires → `phase_5.verification_steps = ['quality_check', 'build_verify']` (the intersection by role with `quality-gate` and `module-tests`).
2. Post-matrix docs-only classifier runs: `_classify_paths_via_extensions(["a/SKILL.md", "b/outline-workflow-detail.md", "c/SKILL.md"]) == "documentation_only"` (every path claimed by `pm-documents` or `pm-plugin-development` under the `documentation` role).
3. Effect: both `quality_check` (role `quality-gate`) and `build_verify` (role `module-tests`) are suppressed → `phase_5.verification_steps = []`.
4. Decision log emits TWO entries: one for the row that fired (`surgical_bug_fix`) and one for the post-matrix rule (`docs_only_classifier`).

**Decision log line** (in addition to the row's own log line):

```
(plan-marshall:manage-execution-manifest:compose) docs-only classifier fired — plan-wide affected_files (N paths) resolved to documentation_only bucket; holistic quality-gate + module-tests steps suppressed from phase_5.verification_steps. See lesson 2026-05-28-10-001.
```

**Composer output fields**: the post-matrix rule surfaces two additional fields in the `compose` success TOON:

- `docs_only_classifier_fired: true|false` — `true` when the rule suppressed at least one step.
- `plan_wide_bucket: production_only|test_only|documentation_only|mixed_code|mixed_with_docs|unknown` — the resolved bucket for the plan-wide union.

These fields make the rule's behavior observable from a single TOON inspection without re-reading `decision.log`.

## Overlap resolution policy

When the path union contains a path claimed by more than one domain extension (e.g., `pm-documents` claims `*.md`, `pm-plugin-development` claims `marketplace/bundles/*/skills/*/SKILL.md`), the aggregator resolves the conflict via **longest-glob-wins specificity**:

1. For each claiming extension, the aggregator calls `classify_path_specificity(path, role)` — a companion method on `ExtensionBase` documented in `extension-api/standards/extension-contract.md`. Each extension returns a non-negative integer score equal to the count of non-wildcard path-segment tokens in the glob that matched `path` for `role`.
2. The extension with the **highest** specificity score wins the path under its declared role.
3. Ties break **alphabetically on the extension's domain key** (`d.get('domain', {}).get('key')`) — deterministic and order-independent.

Order-independence is structural: the aggregator collects every extension's claims first, then resolves overlaps. Extension load order is irrelevant.

**Worked overlap** — for the path `marketplace/bundles/foo/skills/bar/SKILL.md`:

- `pm-documents` claims it under `documentation` with `classify_path_specificity(...) == 0` (its glob `*.md` has zero explicit segments).
- `pm-plugin-development` claims it under `documentation` with `classify_path_specificity(...) == 4` (its glob `marketplace/bundles/*/skills/*/SKILL.md` has four explicit segments).
- Resolution: `pm-plugin-development` wins; the path is tagged `documentation` from `pm-plugin-development`.

## Unclaimed paths

Paths no extension claims are tagged `unknown` by the aggregator AND surface as a `[STATUS]` decision-log warning naming each unclaimed path. The aggregator **never** silently falls back to `documentation_only` for unclaimed paths. The `unknown` tag forces the plan-wide bucket to `unknown`, which downstream guards (e.g., the `phase-3-outline` File-type classifier section) treat as a hard error requiring user resolution.

**Decision log line** (emitted at most once per compose call when at least one path is unclaimed):

```
(plan-marshall:manage-execution-manifest:classify) [STATUS] Unclaimed paths tagged unknown: [<list of paths>]
```

The never-silently-drop policy is load-bearing: an unclassified path indicates either a missing domain extension OR a brand-new file type the project has not yet declared, and silently routing it to `documentation_only` would suppress the holistic Python verification that the path may actually need. Surfacing `unknown` forces the user (or the future Q-Gate finding) to declare the path's role explicitly.

## Bot-Enforcement Guard

**Type**: Composition-time defense-in-depth remediation (NOT a pre-filter, NOT an assertion). Runs *after* the seven-row matrix has produced the final `phase_6.steps` list, *before* the manifest is persisted.

**Condition**: `ci_provider ∈ {github, gitlab}` AND `default:automated-review` is NOT in the assembled `phase_6.steps` list.

**Effect**: Appends `default:automated-review` to the final `phase_6.steps` list in-place and emits a decision-log entry recording the remediation. The composition continues normally and the manifest is written with `automated-review` restored. The guard preserves matrix orthogonality — Row 5's subtraction logic (and any future pre-filter or row that legitimately drops `automated-review`) stays unchanged; the guard puts the step back so the final manifest is GitHub/GitLab-compliant.

**Why remediation rather than assertion**: The original assertion-style guard deadlocked every `surgical+{bug_fix, tech_debt}` plan that finalized through GitHub or GitLab — Row 5 of the seven-row matrix legitimately drops `automated-review` for those plans, and the assertion then refused to write the manifest. The remediation strategy (Option 2) keeps Row 5's subtraction intact and converts the guard from assertion to remediation. The matrix's documented orthogonality (its inputs are change_type / scope / recipe only) is preserved.

**Why retained after the deadlock fix (defense-in-depth)**: `automated-review` is effectively mandatory on plans that finalize through GitHub or GitLab — review bots catch a class of structural defects the local gates systematically miss, and silently dropping the bot-review step (e.g., via a future pre-filter, a recipe interaction, or a row addition we haven't designed yet) would defeat the entire pre-submission-self-review story. The guard is now defense-in-depth alongside `phase-6-finalize/standards/required-steps.md` — the required-steps file ensures completion semantics for the handshake invariant; this guard ensures the step is even scheduled in the first place, and self-heals if anything upstream drops it.

**Decision log line** (emitted whenever the guard remediates; one entry per remediation):

```
(plan-marshall:manage-execution-manifest:compose) bot-enforcement guard remediated — ci_provider=github, automated-review re-added to phase_6.steps
```

When `ci_provider` is neither `github` nor `gitlab`, OR `default:automated-review` is already present in `phase_6.steps`, the guard is a no-op and emits no log entry.

**Safety-net error path**: The function still has a non-`None` return contract (`str | None`) and the caller (`cmd_compose`) still translates a non-`None` return into a `bot_enforcement_violation` error TOON. In current code this branch is unreachable — the guard either no-ops (returns `None`) or remediates and returns `None`. The branch is retained as a hook for any future logic that detects a non-remediable violation (e.g., a malformed `phase_6_steps` list), so the legacy `bot-enforcement guard fired` log line and error TOON shape remain documented in the codebase even though they are not exercised by the current control flow.

## execution_tier Routing

**Type**: Composition-time per-task routing pass. Runs *after* the seven-row matrix has produced the body's `phase_5.verification_steps` and `phase_6.steps`, *before* the bot-enforcement guard. Mutates both the manifest body and the plan's `TASK-*.json` files.

**Inputs** (per task):

| Input | Source | Type |
|-------|--------|------|
| `verification.commands` | `{plan_dir}/tasks/TASK-*.json` | list[string] |
| Resolve TOON | `architecture resolve --command {verb} --module {module}` (subprocessed via the executor) | dict — see [the augmented resolve contract](../../manage-architecture/standards/resolve-command.md) |

**Routing predicate** (per command):

- **`execution_tier == 'orchestrator'`**: the command's adaptive Bash timeout has crossed the 600s host ceiling. The composer maps the build verb to the matching phase-5 step ID (`quality-gate → default:quality_check`, `verify` / `module-tests → default:build_verify`, `coverage → default:coverage_check`), appends it (de-duped) to `phase_5.verification_steps`, and drops the command from the task's `verification.commands`. A task whose entire `verification.commands` list routes to orchestrator ends up with an empty list — that is the correct "all orchestrator" signal.
- **`execution_tier == 'per_task'`**: the command fits inside the Bash ceiling. The composer writes `bash_timeout_seconds` into the task's `verification` dict alongside `commands` so the dispatched sub-agent reads the numeric timeout directly. When a task has multiple `per_task` commands, the maximum `bash_timeout_seconds` wins (the sub-agent honours the most-demanding command).
- **No `execution_tier` field** (non-build executable — raw shell, `grep`, `manage-*` notation): the command stays in the task and no `bash_timeout_seconds` annotation is added. Today's behaviour is preserved.

**Idempotence**: every compose call re-derives the routing from the live `architecture resolve` output. Re-composing after a tier shift converges deterministically — orchestrator commands stay pruned, `bash_timeout_seconds` is overwritten when its value changes, and the stale annotation is stripped when no `per_task` commands survive.

**Decision log line** (emitted on every compose, regardless of mutation count):

```
(plan-marshall:manage-execution-manifest:compose) execution_tier routing — mutated_tasks={N}, phase_5.verification_steps={list}
```

**Cross-references**: `manage-architecture/standards/resolve-command.md` (the four-field augmented resolve TOON and the ≈600K-token re-dispatch failure mode that motivated it); `dev-agent-behavior-rules` (the sub-agent rule that consumes `bash_timeout_seconds`).

## Role-Field Intersection

Rows 2, 3, 5, and 6 intersect the `phase_5_candidates` list against a set of canonical roles (`{quality-gate}`, `{module-tests}`, `{quality-gate, module-tests}`) rather than against literal step IDs. The mechanism is structural: each phase-5 step standards file under `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/` declares its role in YAML frontmatter (e.g., `role: quality-gate` on `quality_check.md`, `role: module-tests` on `build_verify.md`, `role: coverage` on `coverage_check.md`). At compose time the composer resolves each candidate step ID to its source file and reads the `role:` value; intersection is `candidate_role ∈ {target_role, ...}` rather than `candidate_id ∈ {literal_id, ...}`.

This decouples canonical names from intersection logic. The composer never compares candidate step IDs directly against literal strings like `'quality-gate'` — those names are role values, not step IDs. Step IDs are arbitrary handles (e.g., `default:quality_check`, `default:build_verify`) whose intersection-meaningful attribute is the role declared in their source file.

**External steps** (`project:` and `bundle:skill` prefixes) have no role file and resolve to `role = None`; they are therefore never selected by any role-based intersection. This is the correct behavior: Rows 2/3/5/6 select built-in verify steps only.

**Drift enforcement**: A `MISSING_ROLE_FIELD` analyzer in `pm-plugin-development:plugin-doctor` flags any phase-5 step standards file missing the `role:` frontmatter field at edit time, preventing future name-drift defects.

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

**Condition**: `recipe_key` is present (non-empty).

**Outcome**:
- `phase_5.early_terminate = false`
- `phase_5.verification_steps` = the candidates from `phase_5_candidates` whose declared `role:` ∈ `{quality-gate, module-tests}` (see [Role-Field Intersection](#role-field-intersection))
- `phase_6.steps = phase_6_candidates − {ci-wait}`

**Why**: Recipe-driven plans (currently `recipe-refactor-to-profile-standards` and the upcoming `recipe-lesson-cleanup` from deliverable 7) follow deterministic, surgical-style patterns. The only subtraction here is the legacy `ci-wait` step ID — kept as a defensive narrowing against project marshal.json files that still list it as a candidate. Review gates a project opted into (`automated-review`, `sonar-roundtrip`) are NEVER silently suppressed by the planner: the recipe label is exactly the case where the bots' job is to catch what humans miss. CI completion is now a dispatcher-resolved precondition (declared via `requires: [ci-complete]` on consumer step frontmatters), not a sibling step.

### Row 3 — `docs_only`

**Condition**: `scope_estimate ∈ {surgical, single_module}` AND `change_type ∈ {tech_debt, enhancement}` AND `affected_files_count > 0` AND no candidate in `phase_5_candidates` declares `role: module-tests` or `role: coverage` (see [Role-Field Intersection](#role-field-intersection)).

**Outcome**:
- `phase_5.early_terminate = false`
- `phase_5.verification_steps = []`
- `phase_6.steps = phase_6_candidates − {ci-wait}`

**Why**: A docs-shaped plan never needs to run tests or coverage. The candidate set already reflects this (no `module-tests`/`coverage`), so the manifest empties Phase 5's verification list. The only subtraction here is the legacy `ci-wait` step ID — kept as a defensive narrowing against project marshal.json files that still list it as a candidate. Review gates a project opted into (`automated-review`, `sonar-roundtrip`) are NEVER silently suppressed by the planner: a docs-only label is exactly the case where the bots' job is to catch what humans miss. We keep `commit-push`, `create-pr`, `lessons-capture`, `branch-cleanup`, `archive-plan`, AND the review gates so the doc change is reviewed, committed, surfaced, and recorded.

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

**Why**: Surgical bug fixes and tech-debt nudges have already passed the Q-Gate bypass at outline time (deliverable 4). The only subtraction here is the legacy `ci-wait` step ID — kept as a defensive narrowing against project marshal.json files that still list it as a candidate. Review gates a project opted into (`automated-review`, `sonar-roundtrip`) are NEVER silently suppressed by the planner: surgical bug_fix / tech_debt is exactly the case where the bots' job is to catch what humans miss on a one-line fix. We keep `lessons-capture` so any lesson observed during execution is still captured. CI completion is now a dispatcher-resolved precondition (declared via `requires: [ci-complete]` on consumer step frontmatters), not a sibling step.

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

```
(plan-marshall:manage-execution-manifest:compose) Rule {rule_key} fired — early_terminate={bool}, phase_5.verification_steps={list}, phase_6.steps={list}
```

The component prefix `(plan-marshall:manage-execution-manifest:compose)` is mandatory so that `plan-retrospective` (deliverable 9) can correlate manifest content with the reasoning entries.

## Determinism

The decision matrix is deterministic given its inputs — re-running `compose` with the same arguments produces an identical manifest and identical decision-log entry. The composer truncates / overwrites previous manifests on re-invocation; callers (currently only `phase-4-plan` Step 8b) are responsible for re-entry semantics.
