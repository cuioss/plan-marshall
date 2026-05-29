---
name: phase-3-outline
description: Two-track solution outline creation - Simple Track for localized changes, Complex Track for codebase-wide discovery
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Phase Outline Skill

**Role**: Two-track workflow skill for creating solution outlines. Routes based on track selection from phase-2-refine.

**Prerequisite**: Request must be refined (phase-2-refine completed) with track field set.

## Foundational Practices

```
Skill: plan-marshall:dev-agent-behavior-rules
```

## Enforcement

> **Shared lifecycle patterns**: See [phase-lifecycle.md](../ref-workflow-architecture/standards/phase-lifecycle.md) for entry protocol, completion protocol, and error handling convention.

**Execution mode**: Follow workflow steps sequentially. Each step that invokes a script has an explicit bash code block.

**Prohibited actions:**
- Never access `.plan/` files directly — all access must go through `python3 .plan/execute-script.py` manage-* scripts
- Never skip the phase transition — use `manage-status transition`
- Never improvise script subcommands — use only those documented below
- Never fall back to simple track if complex track fails — return error
- **Never mutate source files outside `.plan/local/plans/{plan_id}/`** during outline. The outline phase is strictly analytical: it discovers, classifies, and writes solution documents into the plan workspace. Edits to any path under `marketplace/`, `target/`, `.claude/`, `test/`, `doc/`, or any other repository directory are categorically forbidden — those mutations are the responsibility of phase-5-execute. If a recipe or domain workflow proposes a fix, capture it as a deliverable in `solution_outline.md` rather than applying it directly.
- **Never invoke any `*-doctor` tool (e.g., `plugin-doctor`, `plan-doctor`) carrying `fix`, `apply`, `--apply`, or `--fix`** during outline. Doctor tools may only be invoked in their read-only modes (`verify`, `check`, no flags) to surface findings. The `apply`/`fix`/`--fix`/`--apply` surfaces mutate source files and bypass the per-plan workspace boundary above — they are reserved for phase-5-execute task bodies that the planner explicitly authorized via a deliverable. This applies equally to `Bash`, `Skill:`, and `SlashCommand:` invocation shapes.

**Constraints:**
- Strictly comply with all rules from dev-agent-behavior-rules, especially tool usage and workflow step discipline

## Dispatched workflows vs inline steps

This phase dispatches under one role key: **`phase-3-outline`** (resolves through `phase-3-outline.default`; `track={simple|complex}` is a runtime input — both tracks share the envelope and resolver lookup). The Complex Track bundles Steps 9c (per-deliverable design-intent classification), 10 (the heavyweight design body), and 10b (self-modifying classification) into one `phase-3-outline` envelope — the per-deliverable loop iterates *inside* the dispatch. Mechanical sub-procedures stay inline: Step 4 detect-change-type uses `manage-status:change-type-heuristic` (heuristic-first, dispatches via `effort read --default` when ambiguous); Simple Track Step 6 target validation is a Bash one-liner; Complex Track Step 9 domain-resolution and Step 10b consumer-sweep run as scripts. Step 11 Q-Gate validation activation is *signaled* by setting `qgate_validation_required: true` in the phase return TOON; the orchestrator (`plan-marshall:plan-marshall/workflow/planning-outline.md`) reads that flag and issues q-gate-validation as a sibling top-level `Task: plan-marshall:{target}` dispatch — the phase body cannot spawn it directly because the `Task` tool is unavailable inside an `execution-context-{level}` subagent. The flag is set to `false` (no orchestrator dispatch) when the surgical-bypass predicate holds (`scope_estimate == surgical` AND `change_type ∈ {bug_fix, tech_debt, verification}` AND `deliverable_count == 1`). For the rationale see [dispatch-granularity.md](../extension-api/standards/dispatch-granularity.md) § 3–4 (bundle when steps share context; per-iteration only when models differ or parallel).

### Loop-invariant inputs (cached at phase entry)

The Complex Track per-deliverable loop (Steps 9c + 10 + 10b) iterates over the deliverable list — but the *inputs* feeding the per-deliverable design body are loop-invariant: they are written before the loop begins (phase-2-refine, phase-3-outline entry, Step 9 domain-resolution) and are not mutated by the loop body. The dispatched agent MUST read each of the following inputs ONCE at phase entry and reference the cached values throughout every per-deliverable iteration:

- The clarified request narrative (read via `manage-plan-documents read --plan-id {plan_id} --document request`).
- `domains` and `compatibility` (read via `manage-files read --plan-id {plan_id} --file references.json`).
- `module_mapping.toon` if present at `.plan/local/plans/{plan_id}/module_mapping.toon`.
- The architecture topology (read via `manage-architecture topology` at phase entry).
- The resolved domain outline skill notation (resolved once via Step 9 domain-resolution).

**Prohibited actions:**
- Never re-read loop-invariant inputs inside the per-deliverable loop body — re-reading inside the loop is envelope-cost waste; resolve all invariant inputs before the loop begins.

See [`extension-api/standards/dispatch-granularity.md`](../extension-api/standards/dispatch-granularity.md) § 5.1 (Heuristic 2 — bundle when steps share context) for the granularity rationale.

## cwd for `.plan/execute-script.py` calls

> `manage-*` scripts (Bucket A) resolve `.plan/` via `git rev-parse --git-common-dir` and work from any cwd — do **NOT** pin cwd, do **NOT** pass routing flags, and never use `env -C`. Build / CI / Sonar scripts (Bucket B) accept `--plan-id {plan_id}` (preferred — auto-resolves the worktree via `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (explicit override / escape hatch); the two flags are mutually exclusive. See `plan-marshall:tools-script-executor/standards/cwd-policy.md`.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call documented below carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes. **`exit 0` does NOT imply the operation succeeded** — the `manage-*` scripts follow the canonical output contract (`pm-plugin-development:plugin-script-architecture/standards/output-contract.md`), under which an *operation* failure (`file_not_found`, `field_not_found`, `plan_not_found`, validation rejection, already-exists, etc.) exits `0` and carries the verdict in the stdout TOON `status: error` payload. Branch on the TOON `status` / `value` field to detect operation failures; never infer "the field was present" or "the plan exists" from a zero exit code.
- **`exit_code != 0`**: STOP the phase and return an error TOON to the orchestrator carrying the script's stderr verbatim. A non-zero exit is reserved for a genuine **script crash** (exit 1 — uncaught exception, corrupt/non-dict payload, missing required file) or an `argparse_rejection` (exit 2 — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern). The phase MUST NOT proceed on a non-zero exit; "log and continue" is equally forbidden.

Step-level exceptions to this default — calls whose non-zero exit is itself the signal (e.g., `manage-files exists` returning `exists: false`, or `manage-status get-worktree-path` returning an empty `worktree_path`) — are documented inline in the step that issues them. Treat the absence of an inline exception as the default "hard-stop" behaviour above.

**Operation-failure carve-out (`manage-*` read verbs):** Because operation failures exit `0`, a step that reads a `manage-*` read verb (`get`, `read`, `get-context`, `set-list`, and the like) to discover whether a field/plan/file is present MUST detect the not-found / validation outcome by inspecting the TOON `status` (`status: error` plus the precise `error` code) — NOT by testing `exit_code != 0`. Reserving `exit_code != 0` for crash/argparse detection and reading the TOON for operation-failure detection are two distinct branches; conflating them (treating any non-zero exit as "field absent") regresses the contract and is forbidden.

---

## Two-Track Design

| Track | When Used | Approach |
|-------|-----------|----------|
| **Simple** | Localized changes (single_file, single_module, few_files) | Direct deliverable creation from module_mapping |
| **Complex** | Codebase-wide changes (multi_module, codebase_wide) | Load domain skill for discovery/analysis |

**Track determined by**: phase-2-refine (stored in references.json)

---

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

---

## Phase-Entry Worktree Assertion

The Phase Entry Protocol's `phase_handshake verify --phase 2-refine --strict` call (see [`ref-workflow-architecture/standards/phase-lifecycle.md`](../ref-workflow-architecture/standards/phase-lifecycle.md#phase-handshake-verify-phases-2-6)) asserts the tri-state worktree-resolution contract before any phase-3-outline work begins. When `metadata.use_worktree==true` AND `metadata.worktree_path` is empty, the assertion treats this as the deferred-materialization window and passes — phases 2-3-4 run on the main checkout / current feature-branch intent until phase-5-execute Step 2.5 materializes the artifacts. The strict path-not-found / path-stale failures still fire when `worktree_path` is set but does not resolve cleanly. Phases 5-6 retain the original strict semantics. Plans with `metadata.use_worktree==false` skip the assertion (main-checkout flow). See [`workflow-integration-git/standards/worktree-handling.md`](../workflow-integration-git/standards/worktree-handling.md) for the canonical lifecycle contract and the underlying `_resolve_worktree_assertion` implementation in `phase_handshake.py`.

---

## Workflow Overview

```
Step 2: Load Inputs → Step 3: Recipe Detection → Step 4: Detect Change Type → Step 5: Route by Track → {Simple: Steps 6-8 | Complex: Steps 9-11} → Step 12: Return
```

---

## Step 1: Check for Unresolved Q-Gate Findings

**Purpose**: On re-entry (after Q-Gate or user review flagged issues), address unresolved findings before re-running the outline.

Query pending findings for phase `3-outline`. For each finding: analyze context, verify file paths exist on disk, create assessments or update deliverables as needed, then resolve the finding with `taken_into_account`. Continue with normal Steps 2..12 after corrections are applied. When a finding scopes to one peer of a symmetric data structure (ladder, parallel-array, peer-set, matrix), apply the **symmetric-peer-audit rule**: audit every peer in the same structure for the same defect and apply the same fix in the same outline revision — see [`standards/outline-workflow-detail.md` § symmetric-peer-audit](standards/outline-workflow-detail.md#step-1-check-for-unresolved-q-gate-findings-detail).

For detailed procedures (query commands, finding-type handling, resolution logging), see [`standards/outline-workflow-detail.md`](standards/outline-workflow-detail.md#step-1-check-for-unresolved-q-gate-findings-detail).

---

## Step 2: Load Inputs

**Purpose**: Load track, request, compatibility, and context from phase-2-refine output and sinks.

**Note**: This skill receives `track`, `track_reasoning`, `scope_estimate`, `compatibility`, and `compatibility_description` from the phase-2-refine return output. These values are passed as input parameters.

### Receive Track from Phase-2-Refine Output

The `track` value (simple | complex) is received from the phase-2-refine return output, not read from references.json.

**If track not provided in input**, extract from decision.log:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  read --plan-id {plan_id} --type decision | grep "(plan-marshall:phase-2-refine) Track:"
```
Parse the output to extract track value from: `(plan-marshall:phase-2-refine) Track: {track} - {reasoning}`

### Read Request

Read request (clarified_request falls back to original_input automatically):

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} \
  --section clarified_request
```

### Read Module Mapping (optional)

Check existence first (file is created by phase-2-refine and may not exist):

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files exists \
  --plan-id {plan_id} \
  --file work/module_mapping.toon
```

If `exists: true`, read it:
```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
  --plan-id {plan_id} \
  --file work/module_mapping.toon
```

If `exists: false`, continue without module mapping — downstream steps will use discovery or request context instead.

### Read Domains

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} --field domains
```

### Receive Compatibility from Phase-2-Refine Output

The `compatibility` and `compatibility_description` values are received from the phase-2-refine return output.

**If compatibility not provided in input**, read from marshal.json:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine get --field compatibility --audit-plan-id {plan_id}
```

Store as `compatibility` and derive `compatibility_description` from the value:
- `breaking` → "Clean-slate approach, no deprecation nor transitionary comments"
- `deprecation` → "Add deprecation markers to old code, provide migration path"
- `smart_and_ask` → "Assess impact and ask user when backward compatibility is uncertain"

### Receive Simplicity from Phase-2-Refine Output

The `simplicity` and `simplicity_description` values are received from the phase-2-refine return output.

**If simplicity not provided in input**, read from marshal.json (default `lean` when unconfigured):
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine get --field simplicity --audit-plan-id {plan_id}
```

Store as `simplicity` and derive `simplicity_description` from the value:
- `lean` → "Implement the strict minimum; remove or inline surplus structure"
- `pragmatic` → "Prefer minimal, but keep low-risk structure that aids readability"
- `defensive` → "Retain belt-and-suspenders structure (guards, abstraction seams) where uncertain"

### Log Context (to work.log - status, not decision)

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-3-outline) Starting outline: track={track}, domains={domains}, compatibility={compatibility}"
```

---

## Step 3: Recipe Detection

**Purpose**: Recipe-sourced plans skip change-type detection and use the recipe skill directly for discovery, analysis, and deliverable creation.

Check `plan_source` metadata. If `recipe`: read recipe metadata (`recipe_key`, `recipe_skill`, and built-in-only fields), resolve `default_change_type` from recipe config, load the recipe skill with input parameters, then skip Steps 4-11 and jump directly to Step 12. Recipe deliverables are deterministic architecture-to-deliverable mappings — Q-Gate is skipped.

If `plan_source != recipe` or field not found: continue with normal Step 4.

For detailed procedures (metadata reads, recipe resolution, skill loading), see [`standards/outline-workflow-detail.md`](standards/outline-workflow-detail.md#step-3-recipe-detection-detail).

---

## Step 4: Detect Change Type

**Purpose**: Determine the change type for agent routing.

Run the deterministic classifier first; only dispatch the LLM workflow on the ambiguous branch.

**Step 4a — Heuristic classifier (deterministic, no envelope):**

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  change-type-heuristic --plan-id {plan_id} --persist
```

The script reads `clarified_request` (falling back to `original_input`) from `request.md`, scores it against the fixed keyword tables, applies the compound-intent guard and the bug-fix-vs-tech-debt object disambiguation, and either:

- returns one of `feature` / `bug_fix` / `tech_debt` / `enhancement` / `verification` / `analysis` with `ambiguous=false` (and persists to `status.metadata.change_type` with `--persist`), OR
- returns `ambiguous=true` when no keyword fires, the top two scores tie, or confidence falls below `0.7`.

**Step 4b — LLM fallback (only when `ambiguous=true`):**

Dispatch the `detect-change-type` workflow (`plan-marshall:phase-3-outline/workflow/detect-change-type.md` via `execution-context-{level}` resolved from `effort`). The workflow persists `change_type` to status.json metadata itself. Skip this dispatch when Step 4a resolved without ambiguity — the heuristic already wrote the value.

For detailed procedures (agent spawning, metadata read, post-check override logic), see [`standards/outline-workflow-detail.md`](standards/outline-workflow-detail.md#step-4-detect-change-type-detail).

---

## Step 5: Route by Track

Based on `track` from Step 2:

If track == simple → go to Step 6. If track == complex → go to Step 9.

---

## Simple Track (Steps 6-8)

For localized changes where targets are already known from module_mapping.

| Step | Purpose | Key Action |
|------|---------|------------|
| **6. Validate Targets** | Verify target files/modules exist | `ls -la {target_path}` for each target |
| **7. Create Deliverables** | Map module_mapping to deliverables | **MUST classify each deliverable's `affected_files` against the [File-type classifier](standards/outline-workflow-detail.md#file-type-classifier) (six buckets: `production_only` / `test_only` / `documentation_only` / `mixed_code` / `mixed_with_docs` / `unknown`) BEFORE assigning `profiles[]`.** **For any deliverable that touches an existing skill, MUST also run the [Step 9c design-intent classification](standards/outline-workflow-detail.md#step-9c-read-target-skill-design-intent) and emit the resulting `**Design notes:**` block** — this is track-agnostic and applies on the Simple Track too, so the deliverable self-satisfies §2.17 (Architecture-Mismatch) on the first validation pass. Use deliverable template, resolve verification commands via `architecture resolve`. The resolved bucket MUST be recorded as a comment in the `**Profiles:**` block (see Deliverable Template below). |
| **8. Simple Q-Gate** | Lightweight verification (with surgical bypass) | Bypass when surgical+bug_fix/tech_debt/verification+1 deliverable; otherwise check target existence + request alignment |

### File-type classifier (normative)

Before assigning `profiles[]` to any deliverable, every author MUST classify the deliverable's `**Affected files:**` list against the six-bucket file-type classifier. The buckets, predicates, profile assignments, and verification commands are documented in [`standards/outline-workflow-detail.md` § File-type classifier](standards/outline-workflow-detail.md#file-type-classifier). The rule is normative — assigning `module_testing` to a `documentation_only` deliverable is a contract violation that phase-4-plan refuses to translate into a paired pytest task and instead emits a Q-Gate finding back to this phase. The aggregator that produces the bucket lives in `manage-execution-manifest._classify_paths_via_extensions`; per-domain predicates are owned by each bundle's `ExtensionBase.classify_paths()` override.

The canonical doctor invocation cited in all `documentation_only` deliverable Verification fields is `pm-plugin-development:plugin-doctor:doctor-marketplace scan --paths {skill-dir}` (NOT the stale `:plugin-doctor:plugin-doctor`).

**Step 6 may also refine `scope_estimate`**: After deliverables crystalize and the concrete Affected files lists are known, phase-3-outline MAY downgrade `scope_estimate` (e.g., `single_module` → `surgical`) when the final deliverable composition narrows the actual scope. Persist any change via `manage-references set --field scope_estimate`. Refinement happens BEFORE Step 8 so the bypass rule sees the refined value.

**Step 8 — Q-Gate surgical bypass rule** (evaluated BEFORE dispatching the lightweight Q-Gate checks):

Bypass Q-Gate when ALL of the following are true:
- `scope_estimate == surgical`, AND
- `change_type ∈ {bug_fix, tech_debt, verification}`, AND
- `deliverable_count == 1` (exactly one deliverable was created in Step 7)

When bypass fires, log the decision and skip directly to Step 12:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline:qgate-bypass) Q-Gate skipped — scope_estimate=surgical, change_type={change_type}, 1 deliverable"
```

Otherwise, run the Simple Q-Gate checks documented in the detail standards. After Step 8, proceed to Step 12.

For detailed procedures (validation commands, deliverable template, verification resolution, Q-Gate checks, bypass rule examples), see [`standards/outline-workflow-detail.md`](standards/outline-workflow-detail.md#simple-track-procedures-steps-6-8).

---

## Complex Track (Steps 9-11)

For codebase-wide changes requiring discovery and analysis.

| Step | Purpose | Key Action |
|------|---------|------------|
| **9. Resolve Domain Skill** | Route to domain-specific or generic instructions | `resolve-outline-skill --domain {domain}`, then load `change-{change_type}.md` |
| **9c. Read Target Skill Design Intent** *(track-agnostic — also runs from Simple Track Step 7)* | For each deliverable that touches an existing skill, classify the skill's design model and record it on the deliverable | Read the target skill's `SKILL.md` and design-intent docs; classify as `script-deterministic`, `LLM-driven`, or `hybrid`; record the classification in the deliverable's `**Design notes:**` block; reroute or justify when the proposed implementation contradicts the model. **This classification is NOT Complex-Track-only** — the Simple Track runs the same procedure from Step 7 when a deliverable touches an existing skill, so the resulting `**Design notes:**` block lets the deliverable self-satisfy §2.17 on the first pass. Detailed procedure: [`standards/outline-workflow-detail.md`](standards/outline-workflow-detail.md#step-9c-read-target-skill-design-intent). |
| **10. Execute Workflow** | Run discovery, analysis, write solution | Follow change-type instructions, resolve verification commands, write `solution_outline.md`. **For each composed deliverable, MUST apply the [File-type classifier](standards/outline-workflow-detail.md#file-type-classifier) to its `affected_files` BEFORE assigning `profiles[]`** — the resolved bucket MUST be recorded as a comment in the `**Profiles:**` block (see Deliverable Template below). Step 10 includes a consumer-sweep when the deliverable deletes/renames a public symbol — see [`consumer-sweep.md`](standards/consumer-sweep.md). |
| **10b. Self-Modifying Classification** | Classify deliverables that touch plan-marshall runtime infrastructure and surface phasing decision | When predicate fires (path heuristic + `compatibility: breaking` + hard-cutover language), prompt author via `AskUserQuestion` for split / inline-rationale / additive-mode resolution. Standard: [`ref-workflow-architecture/standards/self-modifying-classification.md`](../ref-workflow-architecture/standards/self-modifying-classification.md). |
| **11. Q-Gate Verification** | Signal q-gate-validation requirement (with surgical bypass) | Bypass when surgical+bug_fix/tech_debt/verification+1 deliverable → set `qgate_validation_required: false`; otherwise set `qgate_validation_required: true` in the return TOON so the orchestrator dispatches `plan-marshall:plan-marshall/workflow/q-gate-validation.md` as a sibling top-level Task after the phase returns (see [`standards/outline-workflow-detail.md`](standards/outline-workflow-detail.md) for the activation contract). The orchestrator-dispatched workflow runs phase-3-applicable validators: existing checks 2.1-2.7, consumer-sweep §2.9, **argparse-validator §2.10**, **tier-delta-validator §2.13**, **self-modifying-phased-rollout-validator §2.16**, **architecture-mismatch-validator §2.17**. |

**Step 10 may also refine `scope_estimate`**: After Complex Track discovery and deliverable composition, the concrete Affected files lists may narrow the actual scope. Phase-3-outline MAY downgrade `scope_estimate` (e.g., `multi_module` → `single_module`, or `single_module` → `surgical`) and persist via `manage-references set --field scope_estimate`. Refinement happens BEFORE Step 11 so the bypass rule sees the refined value.

**Step 11 — Q-Gate surgical bypass rule** (evaluated BEFORE signaling the Q-Gate validation requirement):

Bypass Q-Gate when ALL of the following are true:
- `scope_estimate == surgical`, AND
- `change_type ∈ {bug_fix, tech_debt, verification}`, AND
- `deliverable_count == 1` (exactly one deliverable was created in Step 10)

When bypass fires, log the decision, set `qgate_validation_required: false` in the return TOON, and skip directly to Step 12:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline:qgate-bypass) Q-Gate skipped — scope_estimate=surgical, change_type={change_type}, 1 deliverable"
```

Otherwise, set `qgate_validation_required: true` in the return TOON. The orchestrator (`plan-marshall:plan-marshall/workflow/planning-outline.md`) reads that flag after the phase returns and dispatches `plan-marshall:plan-marshall/workflow/q-gate-validation.md` as a sibling top-level Task. The orchestrator aggregates the validator's `qgate_pending_count` into the phase's running count before re-evaluating the existing 3-iteration auto-loop predicate.

### Special-deliverable-class recognition rules (track-agnostic, thin)

Two deliverable classes carry a recurring engineering hazard that the outline MUST recognize at authoring time and route to its canonical dev-general home. These rules fire on **both** tracks — Simple Track Step 7 and Complex Track Step 10 — when a deliverable being authored matches the trigger. They are recognition triggers ONLY: the substance (mitigation menu, enumeration procedure) lives once in the dev-general-* standards and MUST NOT be restated here or in the deliverable.

1. **Cooperative-lock deliverable class** — Trigger: the deliverable's narrative introduces or modifies a cooperative cross-process lock or shared-state coordination primitive (merge locks, worktree allocation, plan-id reservation, leader election, any "claim a shared resource" flow). Required authoring action: emit a `**Concurrency-correctness note:**` block on the deliverable that names the check-then-act / TOCTOU window and points to the chosen mitigation. The note MUST cross-reference the TOCTOU / check-then-act mitigation menu in [`dev-general-code-quality/standards/code-organization.md`](../dev-general-code-quality/standards/code-organization.md) — **do NOT duplicate the mitigation menu**.

2. **Value-change deliverable class** — Trigger: the deliverable changes a default value, constant, or enum member that tests may assert against. Required authoring action: scope the old-value test assertions into the deliverable's `**Affected files:**` so the production change and its test-consumer updates form one atomic deliverable. The note MUST cross-reference the enumeration discipline in [`dev-general-module-testing/standards/testing-methodology.md`](../dev-general-module-testing/standards/testing-methodology.md) — **do NOT duplicate the enumeration procedure**.

The matching trigger predicates and authoring actions are documented as track-agnostic siblings to the Step 9c / Step 10b procedures in [`standards/outline-workflow-detail.md`](standards/outline-workflow-detail.md#special-deliverable-class-recognition-rules-detail).

**CRITICAL**: If Complex Track skill workflow fails, do NOT fall back to grep/search. Fail clearly.

- Domain-specific ext-outline-workflow skills MUST emit `**Intent gloss:**` per the deliverable template when a deliverable title contains a compound word whose head morpheme is a planning-domain verb (review, check, validate, approve, merge, …). The gloss is a single sentence (≤15 words) that restates the deliverable's goal using the tail morpheme's meaning, and phase-4-plan copies it verbatim into every derived task.description.

For detailed procedures (skill resolution, change-type loading, solution writing, Q-Gate agent interaction), see [`standards/outline-workflow-detail.md`](standards/outline-workflow-detail.md#complex-track-procedures-steps-9-11).

---

## Step 12: Write Solution and Return

---

### Deliverable Template (inline reference)

Each deliverable in solution_outline.md MUST follow this field order. The authoritative schema is in `manage-solution-outline/templates/deliverable-template.md`:

```markdown
### {N}. {Deliverable Title}

**Metadata:**
- change_type: {feature|enhancement|tech_debt|bug_fix|analysis|verification}
- execution_mode: {automated|manual|mixed}
- domain: {domain}
- module: {module}
- depends: {none|N|N,M}

**Intent gloss:** {one-sentence disambiguation, max ~15 words — required when title head morpheme is a planning-domain verb (review, check, validate, approve, merge, …)}

**Design notes:** {required on BOTH the Simple and Complex Tracks for any deliverable that touches an existing skill — names the target skill's design model — `script-deterministic`, `LLM-driven`, or `hybrid` — and a one-sentence rationale showing the proposed implementation extends, not contradicts, that model. The track does NOT gate emission: a Simple-Track deliverable touching an existing skill MUST emit this block just as a Complex-Track one does, so the deliverable self-satisfies the §2.17 Architecture-Mismatch validator on the first validation pass. See Step 9c (Read Target Skill Design Intent), which applies to Simple Track Step 7 as well as Complex Track, and [`standards/outline-workflow-detail.md`](standards/outline-workflow-detail.md#step-9c-read-target-skill-design-intent) for the procedure. Omit only when the deliverable does not touch an existing skill (e.g., docs-only with no skill target, brand-new skill).}

**Profiles:** <!-- bucket: {production_only|test_only|documentation_only|mixed_code|mixed_with_docs|unknown} -->
- implementation
- {module_testing - only if the resolved bucket is production_only, test_only, mixed_code, or mixed_with_docs; never for documentation_only; unknown BLOCKS the deliverable}

**Affected files:**
- `{explicit/path/to/file1}`

**Change per file:** {what changes}

**Verification:**
- Command: `{resolved command}`
- Criteria: {criteria}

**Success Criteria:**
- {criterion 1}
```

`**Intent gloss:**` is copied verbatim by phase-4-plan into every derived task.description, so the sentence must stand alone without relying on the surrounding deliverable context.

The `<!-- bucket: ... -->` comment on the `**Profiles:**` line is REQUIRED and records the resolved file-type bucket from the [File-type classifier](standards/outline-workflow-detail.md#file-type-classifier). The bucket determines which profiles are valid for the deliverable:

- `documentation_only` → `implementation` only; never paired with `module_testing`. Verification cites `pm-plugin-development:plugin-doctor:doctor-marketplace scan --paths {skill-dir}`.
- `production_only` → `implementation` + `module_testing`. Verification cites the resolved `quality-gate` and `module-tests` commands.
- `test_only` → `module_testing` only (test-only deliverable). Verification cites the resolved `module-tests` command.
- `mixed_code` → `implementation` + `module_testing` (production + test paths, no documentation). Verification cites the resolved `quality-gate` and `module-tests` commands.
- `mixed_with_docs` → `implementation` + `module_testing`, with `module_testing` scope narrowed to the production/test paths only (declare the narrowed scope in a `**Module_testing scope:**` block above `**Affected files:**`).
- `unknown` → BLOCKS the deliverable. Phase-4-plan emits a Q-Gate finding requiring the user to add a domain-extension claim for the unclaimed path(s) or correct the affected-files list. Never silently route to `documentation_only`.

---

### Write Solution Document (Simple Track only)

For Simple Track, write solution_outline.md. Use `write` on first entry, `update` on re-entry (Q-Gate loop):

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline exists \
  --plan-id {plan_id}
```

If `exists: false` (first entry):
```bash
# 1. Get target path
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}

# 2. Write content directly via Write tool
Write({resolved_path}) with solution outline content including title, plan_id,
compatibility header, Summary, Overview, and Deliverables from Step 6

# 3. Validate
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

If `exists: true` (Q-Gate re-entry):
```bash
# 1. Update content via Write tool to the same path
# 2. Validate
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  update --plan-id {plan_id}
```

**Note**: Complex Track - skill already wrote solution_outline.md in Step 10.

---

### Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (plan-marshall:phase-3-outline) Created solution_outline.md"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Complete: {N} deliverables, Q-Gate: {pass/fail}"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-3-outline) Outline phase complete - {N} deliverables, Q-Gate: {pass/fail}"
```

**Add visual separator** after END log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  separator --plan-id {plan_id} --type work
```

---

### Transition Phase

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status transition \
  --plan-id {plan_id} \
  --completed 3-outline
```

---

### Return Results

Return minimal status - all data is in sinks:

```toon
status: success
plan_id: {plan_id}
track: {simple|complex}
deliverable_count: {N}
qgate_passed: {true|false}
qgate_pending_count: {0 if no findings}
qgate_validation_required: {true|false}
```

`qgate_validation_required` is `true` when the phase decided q-gate-validation must run (surgical-bypass predicate did NOT fire), and `false` otherwise (bypass fired or recipe path short-circuited at Step 3). The orchestrator (`plan-marshall:plan-marshall/workflow/planning-outline.md`) reads this flag after the phase returns and dispatches `q-gate-validation` as a sibling top-level Task when it is `true`.

---

## Output

The "Return Results" block above (under Step 12) is the single source of truth for the return TOON. The minimum contract every workflow doc that implements `ext-point-execution-context-workflow` MUST return is:

```toon
status: success | error
display_detail: "<track {track}, {deliverable_count} deliverables, {qgate_pending_count} pending>"
qgate_validation_required: {true|false}
```

`display_detail` shape on success: `"track {track}, {deliverable_count} deliverables, {qgate_pending_count} pending"` (e.g. `"track complex, 5 deliverables, 0 pending"`); ≤80 chars, ASCII, no trailing period. On error, carries the short error label from § Error Handling.

All other fields (`plan_id`, `track`, `deliverable_count`, `qgate_passed`, `qgate_pending_count`, `qgate_validation_required`) are documented in "Return Results" above.

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Track not set | Return `{status: error, message: "phase-2-refine incomplete - track not set"}` |
| Target not found (Simple) | Return error with invalid target |
| Change type not detected | Return `{status: error, message: "detect-change-type workflow failed to determine change type"}` |
| Skill workflow fails (Complex) | Return error, do not fall back |
| Q-Gate fails | Return with `qgate_passed: false` and findings |
| Request not found | Return `{status: error, message: "Request not found"}` |

**CRITICAL**: If Complex Track skill workflow fails, do NOT fall back to grep/search. Fail clearly.

---

## Integration

**Invoked by**: `plan-marshall:plan-marshall` skill (loaded directly in main context)

**Script Notations** (use EXACTLY as shown):
- `plan-marshall:manage-files:manage-files` - Read module_mapping from work/module_mapping.toon
- `plan-marshall:manage-plan-documents:manage-plan-documents` - Read request
- `plan-marshall:manage-references:manage-references` - Read domains
- `plan-marshall:manage-solution-outline:manage-solution-outline` - Write solution document
- `plan-marshall:manage-findings:manage-findings` - Q-Gate findings (qgate add/query/resolve)
- `plan-marshall:manage-status:manage-status` - Read/write change_type metadata
- `plan-marshall:manage-logging:manage-logging` - Decision and work logging
- `plan-marshall:manage-config:manage-config` - Resolve outline skill, read compatibility
- `plan-marshall:manage-architecture:architecture` - Resolve verification commands
- `plan-marshall:manage-findings:manage-findings assessment` - Log assessments (domain skills)

**Spawns** (Complex Track):
- `plan-marshall:phase-3-outline/workflow/detect-change-type.md` workflow (Step 4 — change type detection)

**Signals to orchestrator** (Complex Track):
- `qgate_validation_required: true|false` in the return TOON. The orchestrator (`plan-marshall:plan-marshall/workflow/planning-outline.md`) dispatches `plan-marshall:plan-marshall/workflow/q-gate-validation.md` as a sibling top-level Task when the flag is `true` (Step 11 — Q-Gate verification).

**Loads Skills** (Recipe path):
- `{recipe_skill}` (Step 3 - recipe skill with input parameters, built-in or custom)

**Loads Skills** (Complex Track):
- Domain outline skill via `resolve-outline-skill` (Step 9a, e.g., `pm-plugin-development:ext-outline-workflow`)
- Change-type instructions from `standards/change-{change_type}.md` (Step 9b, generic fallback)

**Consumed By**:
- `plan-marshall:phase-4-plan` skill (reads deliverables for task creation)

---

## Related

- [architecture-diagram.md](references/architecture-diagram.md) - Change-type routing architecture (normal plans)
- [recipe-flow.md](references/recipe-flow.md) - Recipe flow architecture (built-in and custom recipes)
- [change-types.md](../../ref-workflow-architecture/standards/change-types.md) - Change type vocabulary and agent routing
- [solution-outline-standard.md](../../manage-solution-outline/standards/solution-outline-standard.md) - Deliverable structure
- [workflow-architecture](../../ref-workflow-architecture) - Workflow architecture overview
- [outline-workflow-detail.md](standards/outline-workflow-detail.md) - Detailed track procedures (Q-Gate re-entry, recipe detection, change-type detection, Simple/Complex track steps)
- [consumer-sweep.md](standards/consumer-sweep.md) - Outline-time procedure that enumerates cross-bundle consumers of deleted/renamed public symbols before deliverable finalization (mandatory when delete/rename language applies to a public symbol)
- [dispatch-granularity.md](../extension-api/standards/dispatch-granularity.md) - Dispatch granularity heuristics (10K rule, script-over-dispatch, bundle-over-iterate) — orienting reference for why the Complex Track bundles Steps 9c + 10 + 10b into one `phase-3-outline` dispatch rather than dispatching per-deliverable

### Phase-boundary metric bookkeeping

This skill does not invoke `manage-metrics` itself. The orchestrator
(`plan-marshall:plan-marshall` workflows) records the `3-outline → 4-plan`
boundary via the fused `manage-metrics phase-boundary` call — see
`marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md` §
`phase-boundary` for the API.
