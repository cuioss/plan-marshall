# Outline Workflow Detail

Detailed procedures for the phase-3-outline skill. This document contains the step-by-step instructions for Q-Gate re-entry, recipe detection, change-type detection, and both Simple and Complex track workflows.

For the high-level overview, input/output contract, and track routing logic, see the parent [SKILL.md](../SKILL.md).

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

Step-level exceptions — calls whose non-zero exit is itself the signal (e.g., `manage-files exists` returning `exists: false`) — are documented inline in the step that issues them.

---

## Step 1: Check for Unresolved Q-Gate Findings (Detail)

**Purpose**: On re-entry (after Q-Gate or user review flagged issues), address unresolved findings before re-running the outline.

### List Unresolved Findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate list --plan-id {plan_id} --phase 3-outline --resolution pending
```

### Address Each Finding

If unresolved findings exist (filtered_count > 0):

For each pending finding:
1. Analyze the finding in context of the request and existing outline
2. **If the finding indicates a missing assessment** (title contains "Missing assessment" or "not assessed"):
   a. Extract the file path from the finding's detail or file_path field
   b. **Verify the file exists on disk before creating the assessment**:
   ```bash
   ls {file_path}
   ```
   If the file does NOT exist: Do NOT create an assessment for the wrong path. Instead, find the correct path (check the actual directory structure) and update the deliverable's `Affected files` in solution_outline.md to use the correct path. Then create the assessment with the corrected path.
   c. Create the assessment entry (only after path is verified):
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings assessment \
     add --plan-id {plan_id} --file-path "{file_path}" --certainty CERTAIN_INCLUDE \
     --confidence 90 --agent phase-3-outline --detail "Added via Q-Gate finding resolution"
   ```
   d. Update solution_outline.md if needed (use `update` command — see Step 13)
3. **If the finding indicates a file existence issue** (title contains "File not found"):
   a. Find the correct path by listing the parent directory
   b. Update the deliverable's `Affected files` in solution_outline.md with the correct path
   c. Create or update the assessment with the corrected path
4. **If the finding indicates profile overlap** (title contains "Profile overlap"):
   a. Remove the redundant deliverable from solution_outline.md, OR
   b. Remove the `module_testing` profile from the overlapping deliverable
   c. Use `update` command to persist the corrected outline
5. **If the finding scopes to one peer of a symmetric structure (ladder, parallel-array, peer-set, matrix)** — apply the **symmetric-peer-audit rule**:
   a. **Trigger predicate (tier-agnostic justification)**: ask "would the justification for this fix change if I were looking at `$peer_element` instead?" If the answer is no, the fix is symmetric and MUST propagate to every peer in the same enumerated structure.
   b. **Audit action**: enumerate every peer of the flagged element within the same file/deliverable scope. Examples of symmetric structures: presets like `ECONOMIC` / `BALANCED` / `HIGH_END` in an `effort-preset ladder`; rows of a `parallel-array constant`; entries in a `peer-set enum`; tiers of a `level matrix`. The audit MUST include every peer named in the same enumerated structure, not only the one(s) flagged by the finding.
   c. **Required revision behavior**: apply the same fix to every peer in the same `outline revision`. Do NOT defer peer fixes to a follow-up plan, do NOT split into successor lessons, and do NOT mark the original finding `taken_into_account` until every peer has been corrected in `solution_outline.md`. The single `outline revision` is the contract — partial application is the failure mode this rule exists to prevent.
   d. **Scope rule**: a fix to one tier of a symmetric structure MUST propagate to every peer in the same structure in the same outline revision — defer or partial application is the failure mode this rule exists to prevent.
6. For other finding types: address by revising deliverables, adjusting scope, or removing false positives
7. Resolve:
```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate resolve --plan-id {plan_id} --hash-id {hash_id} --resolution taken_into_account --phase 3-outline \
  --detail "{what was done to address this finding}"
```
8. Log resolution:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline:qgate) Finding {hash_id} [{source}]: taken_into_account — {resolution_detail}"
```

Then continue with normal Steps 2..12 (phase re-runs with corrections applied).

If no unresolved findings: Continue with normal Steps 2..12 (first entry).

---

## Step 3: Recipe Detection (Detail)

**Purpose**: Recipe-sourced plans skip change-type detection and use the recipe skill directly for discovery, analysis, and deliverable creation.

### Check for Recipe Source

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --get \
  --field plan_source
```

**If `plan_source == recipe`**:

1. Read recipe metadata:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --get \
  --field recipe_key

python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --get \
  --field recipe_skill

```

**Built-in recipe only** (`recipe_key == "refactor-to-profile-standards"`): Read the multi-domain field set the built-in recipe's selection flow persists. Skip these for custom recipes — they are not set and will return `field_not_found` errors. The field set is the canonical multi-domain input contract — see [`recipe-refactor-to-profile-standards/SKILL.md` § Input](../../recipe-refactor-to-profile-standards/SKILL.md) for the authoritative definitions; do not inline-copy the field descriptions here.

A single built-in recipe run spans ALL auto-detected domains × one chosen profile, so the field set is `recipe_domains` (comma-separated domain list — replaces the legacy single `recipe_domain`), `recipe_profile`, `recipe_package_source`, plus one `recipe_selected_skills__{domain}` field per detected domain that exposes the chosen profile.

```bash
# Only read these if recipe_key == "refactor-to-profile-standards"
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --get \
  --field recipe_domains

python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --get \
  --field recipe_profile

python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --get \
  --field recipe_package_source
```

Then, for each `{domain}` in the comma-separated `recipe_domains` value, read that domain's user-selected skill set (one field per detected domain — a domain that does not expose the chosen profile contributes no field):

```bash
# Repeat per {domain} in recipe_domains
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --get \
  --field recipe_selected_skills__{domain}
```

2. Resolve recipe to get `default_change_type`:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-recipe --recipe {recipe_key}
```

3. Set `change_type` from recipe's `default_change_type` (skip `manage-status:change-type-heuristic` and any LLM fallback):
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --set \
  --field change_type \
  --value {default_change_type}
```

4. Log decision:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Recipe plan — using recipe skill {recipe_skill} with change_type={default_change_type}"
```

5. Load the recipe skill directly, passing the input field set that matches the recipe kind:

**Built-in recipe** (`recipe_key == "refactor-to-profile-standards"`): pass the multi-domain field set read above — `recipe_domains` (comma-separated), `recipe_profile`, `recipe_package_source`, and one `recipe_selected_skills__{domain}` input per detected domain:

```
Skill: {recipe_skill}
  Input:
    plan_id: {plan_id}
    recipe_domains: {recipe_domains from metadata}
    recipe_profile: {recipe_profile from metadata}
    recipe_package_source: {recipe_package_source from metadata}
    # one line per {domain} in recipe_domains that exposes the chosen profile:
    recipe_selected_skills__{domain}: {recipe_selected_skills__{domain} from metadata}
```

**Custom recipe** (any other `recipe_key`): pass the single-domain field set as before — these recipes carry no multi-domain field set:

```
Skill: {recipe_skill}
  Input:
    plan_id: {plan_id}
    recipe_domain: {recipe_domain from metadata, or empty}
    recipe_profile: {recipe_profile from metadata, or empty}
    recipe_package_source: {recipe_package_source from metadata, or empty}
```

The recipe skill handles: discovery, deliverable creation, and solution outline writing.

6. **Skip Steps 4-11 and Q-Gate**. Jump directly to **Step 12: Write Solution and Return**. Recipe deliverables are deterministic architecture-to-deliverable mappings — Q-Gate checks (request alignment, assessment coverage, missing coverage) validate artifacts that recipes never create. File existence is verified at execution time.

**If `plan_source != recipe` or field not found**: Continue with normal Step 4.

---

## Step 4: Detect Change Type (Detail)

**Purpose**: Determine the change type for agent routing.

### Spawn Detection Agent

Resolve the dispatch target via the resolver — no dedicated role key (the LLM path rarely fires); level is sourced from `effort`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --default
```

Extract the `level` and `target` fields from the TOON output. Use those values as `{level}` and `{target}` in the dispatch and the post-resolve log line below. The resolver returns `target: execution-context` when `level` is `inherit` or empty, and `target: execution-context-{level}` otherwise — the mapping is centralized in the resolver, callers do not branch on level.

Emit the standardized post-resolve dispatch log line — see [`ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:phase-3-outline) target={target} level={level} role=default workflow=plan-marshall:phase-3-outline/workflow/detect-change-type.md plan_id={plan_id}"
```

Dispatch:

```
Task: plan-marshall:{target}
  prompt: |
    name: detect-change-type
    plan_id: {plan_id}
    skills[1]:
    - plan-marshall:manage-status
    workflow: plan-marshall:phase-3-outline/workflow/detect-change-type.md
    WORKTREE: {worktree_path}
```

**Agent Output** (TOON):
```toon
status: success
plan_id: {plan_id}
change_type: enhancement
confidence: 90
reasoning: "Request describes improving existing functionality"
```

### Read Detected Change Type

The agent persists change_type to status.json metadata. Read it:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --get \
  --field change_type
```

### Post-Check: Override `analysis` When Request Includes Actions

If the agent returned `analysis`, verify this is correct by checking the request text (already loaded in Step 2).

**IF `change_type == analysis`**: Scan the request (clarified_request + clarifications) for action words: `fix`, `implement`, `improve`, `update`, `create`, `refactor`, `migrate`, `remove`, `restructure`.

**IF any action word is found**: The request uses analysis as discovery, not as the goal. Override:
- Set `change_type = enhancement` (or `tech_debt` if the action is refactor/migrate/restructure/remove)
- Persist the override:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --set \
  --field change_type \
  --value {corrected_change_type}
```
- Log the override:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Post-check override: analysis → {corrected_change_type} (request contains action word: {word})"
```

**IF no action word found**: Keep `analysis` as-is.

### Log Detection

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Change type: {change_type} (confidence: {confidence})"
```

---

## Simple Track Procedures (Steps 6-8)

For localized changes where targets are already known from module_mapping.

### File-type classifier

**Normative source of truth for per-deliverable profile assignment.** Phase-3-outline (both Simple Track Step 7 and Complex Track Step 10) MUST classify each deliverable's `**Affected files:**` list against the six-bucket table below BEFORE assigning `profiles[]`. The vocabulary is produced by the per-domain extension aggregator (`manage-execution-manifest._classify_paths_via_extensions`) which dispatches each path to every registered `ExtensionBase.classify_paths()` and resolves overlaps via longest-glob-wins; see `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md` § "Overlap resolution policy" and § "Unclaimed paths" for the aggregation contract, and `extension-api/standards/extension-contract.md` § classify_paths() for the per-extension predicates.

The same vocabulary is consumed downstream by `manage-execution-manifest.compose()`, which skips holistic `quality-gate` + `module-tests` verification steps when the plan-wide union of `affected_files` resolves to `documentation_only`.

| Bucket | Predicate (resolved by per-domain extension aggregation) | Profile assignment |
|--------|----------------------------------------------------------|--------------------|
| `production_only` | every claimed path resolves under the `production` role (e.g., `pm-dev-python` `**/scripts/**/*.py`, `pm-dev-java` `src/main/**/*.java`) | `implementation` + `module_testing` |
| `test_only` | every claimed path resolves under the `test` role (e.g., `pm-dev-python` `test/**/*.py`, `pm-dev-java` `src/test/**/*.java`) — test-only deliverable, no production source modified | `module_testing` only |
| `documentation_only` | every claimed path resolves under the `documentation` role (e.g., `pm-documents` `*.md`, `pm-plugin-development` `marketplace/bundles/*/skills/*/SKILL.md`) | `implementation` only — NEVER `module_testing`, NEVER a paired pytest task |
| `mixed_code` | claimed paths include both `production` AND `test` roles (no `documentation`) | `implementation` + `module_testing` |
| `mixed_with_docs` | claimed paths include `production` and/or `test` AND `documentation` | `implementation` + `module_testing`, with `module_testing` scope narrowed to the production/test paths only (declare the narrowed scope in a `**Module_testing scope:**` block above `**Affected files:**`) |
| `unknown` | at least one path is unclaimed by every registered extension — aggregator emits a `[STATUS]` warning naming the unclaimed paths | BLOCKS the deliverable; phase-4-plan emits a Q-Gate finding requiring the user to either add a domain extension claim or correct the path |

**Predicate evaluation rules**:

- The aggregator dispatches each path to every registered extension's `classify_paths()`. Per-path overlap is resolved via longest-glob-wins specificity (highest `classify_path_specificity` score wins; alphabetical domain-key tie-break).
- Per-path roles are then collapsed into the six plan-wide buckets above. The `config` role does NOT influence the plan-wide bucket — config changes ride with whatever production/test/docs surface they accompany.
- A deliverable that touches only paths the registered extensions claim under `documentation` (typical workflow-doc edit) resolves to `documentation_only`.
- A deliverable that touches only `test`-role paths resolves to `test_only` — it MUST NOT carry the `implementation` profile because the deliverable produces no production code.
- A deliverable with at least one unclaimed path resolves to `unknown` and is a hard error requiring user resolution — never silently route to `documentation_only`.

**Required recording**: the resolved bucket MUST be recorded as a comment on the `**Profiles:**` line of the deliverable: `**Profiles:** <!-- bucket: documentation_only -->`. The comment is normative — it is the audit trail that lets Q-Gate, phase-4-plan, and reviewers verify the classifier was applied. A missing or wrong bucket comment is a Q-Gate finding.

**Mixed-scope narrowing rule**: when a deliverable resolves to `mixed_with_docs`, the `module_testing` profile applies ONLY to the production/test paths. The deliverable MUST declare the narrowed scope in a dedicated `**Module_testing scope:**` block listing only the production/test paths. This rule prevents pytest from burning cycles on documentation files and ensures the test plan reflects what is actually testable.

**Glob-predicate examples** (resolved by the per-domain extension aggregator; see `extension-api/standards/extension-contract.md` § classify_paths() for the authoritative per-extension predicates):

- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` → claimed by `pm-dev-python` under `production` → `production_only` component
- `test/plan-marshall/manage-execution-manifest/test_classify_paths_via_extensions.py` → claimed by `pm-dev-python` under `test` → `test_only` component
- `marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md` → claimed by both `pm-documents` (specificity 0) and `pm-plugin-development` (specificity 4) under `documentation`; `pm-plugin-development` wins via longest-glob → `documentation_only` component
- `marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/outline-workflow-detail.md` → claimed by `pm-plugin-development` under `documentation` → `documentation_only` component

**Worked classification — three deliverables from the plan that ships this very classifier** (self-referential meta example: this plan IMPLEMENTS the classifier that fixes the very bug it suffers from):

| Deliverable | `**Affected files:**` | Resolved bucket | Profiles | Module_testing scope |
|-------------|------------------------|-----------------|----------|----------------------|
| D1 — phase-3-outline File-type classifier rules | `SKILL.md`, `standards/outline-workflow-detail.md` (both under `marketplace/bundles/plan-marshall/skills/phase-3-outline/`) | `documentation_only` | `implementation` only | n/a |
| D2 — phase-4-plan contract-violation Q-Gate emission | `SKILL.md` under `marketplace/bundles/plan-marshall/skills/phase-4-plan/` | `documentation_only` | `implementation` only | n/a |
| D3 — manage-execution-manifest docs-only classifier | `scripts/manage-execution-manifest.py`, `standards/decision-rules.md` (mixed paths: one production `.py` + one documentation `.md`) | `mixed_with_docs` | `implementation` + `module_testing` | `scripts/manage-execution-manifest.py` only (the `.md` standards doc carries no `module_testing` scope) |

**Cross-references**:

- Simple Track [Step 7: Create Deliverables](#step-7-create-deliverables) consumes this classifier when mapping module_mapping entries to deliverables.
- Complex Track [Step 10: Execute Change-Type Workflow and Write Solution](#step-10-execute-change-type-workflow-and-write-solution) consumes this classifier when composing deliverables from domain skill discovery.
- `manage-execution-manifest.compose()` applies the same classifier at plan-composer scope (union of all `affected_files`) to decide whether to emit holistic Python verification steps (see `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md`).

### Step 6: Validate Targets

**Purpose**: Verify target files/modules exist and match domain.

#### Validate Target Files Exist

For each target in module_mapping:

```bash
# For file targets
ls -la {target_path}
```

If target doesn't exist, ERROR: "Target not found: {target}"

#### Log Validation

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Validated {N} targets in {domain}"
```

### Step 7: Create Deliverables

**Purpose**: Direct mapping from module_mapping to deliverables.

#### Build Deliverables from Module Mapping

For each entry in module_mapping:

1. Determine change_type from request (create, modify, migrate, refactor)
2. Determine execution_mode (automated)
3. Map domain from references.json
4. Use module from module_mapping

**Render architecture hints (Simple Track)**: when a `get-module-context` result is available, the Simple-Track authoring path renders the same `## Architecture Hints` section described in [Step 10 → 10b-bis: Render architecture hints](#10b-bis-render-architecture-hints) — selecting the plan's declared module(s) plus the `default` module's cross-cutting entries, and omitting the section when all hint lists are empty. The mechanics live once in 10b-bis; do not restate them here.

#### Deliverable Structure

Use template from `plan-marshall:manage-solution-outline/templates/deliverable-template.md`:

```markdown
### {N}. {Action Verb} {Component Type}: {Name}

**Metadata:**
- change_type: {feature|enhancement|tech_debt|bug_fix}
- execution_mode: automated
- domain: {domain}
- module: {module}
- depends: none

**Intent gloss:** {one-sentence disambiguation, max ~15 words — required when title head morpheme is a planning-domain verb (review, check, validate, approve, merge, …)}

**Profiles:**
- implementation
- module_testing (only if this deliverable creates/modifies test files)

**Affected files:**
- `{explicit/path/to/file1}`
- `{explicit/path/to/file2}`

**Change per file:** {What will be created or modified}

**Verification:**
- Command: `{resolved compile command from architecture}`
- Criteria: {success criteria}

**Success Criteria:**
- {Specific criterion 1}
- {Specific criterion 2}
```

#### Design notes for skill-touching deliverables (track-agnostic — mandatory on Simple Track)

For each deliverable whose `**Affected files:**` list touches an existing skill (any `marketplace/bundles/{bundle}/skills/{skill}/**` path, including `standards/**/*.md`), the outline agent MUST run the [Step 9c: Read Target Skill Design Intent](#step-9c-read-target-skill-design-intent) procedure and emit the resulting `**Design notes:**` block on the deliverable. Step 9c is **track-agnostic**: although it lives under the Complex Track Procedures heading, it applies in full to Simple Track Step 7. Emitting the `**Design notes:**` block here is what lets a Simple-Track deliverable self-satisfy the §2.17 Architecture-Mismatch validator on the first validation pass — without it, the validator emits a blocking finding and forces a re-outline round-trip.

#### Intent gloss for compound-word titles

For each deliverable whose title contains a compound word whose head morpheme is a common planning-domain verb (review, check, validate, approve, merge, …), author a single-sentence `**Intent gloss:**` (≤15 words) that restates the deliverable's goal using the tail morpheme's meaning. This gloss is copied verbatim into every derived task.description by phase-4-plan, preventing compound-word mis-interpretation.

**Worked example** — deliverable titled with compound head verb `check`:

```markdown
### 1. Add check-coverage step to phase-6-finalize

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: plan-marshall-plugin-dev
- module: plan-marshall
- depends: none

**Intent gloss:** Check module test coverage produced by this plan against the configured threshold.

**Profiles:**
- implementation
```

Without the gloss, a downstream agent could read `check-coverage` as "verify a check has been written for coverage" rather than the intended "inspect coverage results before acting". The gloss fixes the head-morpheme ambiguity at the source.

#### Consumer sweep for delete/rename deliverables

**Mandatory** before finalizing any deliverable whose `Change per file`, `Refactoring`, or title text contains delete/rename language applied to a public symbol. See [`consumer-sweep.md`](consumer-sweep.md) for the full trigger heuristic, sweep procedure (`architecture find` first, grep fallback for sub-module references), and output format.

The sweep ensures every cross-bundle consumer of the deleted/renamed symbol becomes an explicit entry under the deliverable's `**Affected files:**` list before the outline is written. Run the sweep BEFORE resolving verification commands and writing the deliverable to `solution_outline.md`. When the trigger heuristic does not fire, skip silently (no log entry required).

**Shared-symbol-migration completeness**: the sweep trigger is not limited to outright delete/rename — it applies equally to any deliverable that **refactors a shared symbol or a shared derivation** (a constant, helper, or computed value read from more than one site). When a deliverable changes how a shared derivation is produced or shaped, EVERY read path of that derivation MUST be enumerated and migrated within the same deliverable; migrating one consumer while leaving a parallel read path on the old shape is an incomplete refactor that ships a latent defect. Treat "refactor a shared derivation" as a sweep trigger on the same footing as delete/rename: enumerate the read paths (`architecture find` first, grep fallback) and fold each into the deliverable's `**Affected files:**` list so the refactor and all its consumer migrations form one atomic deliverable.

**Resolve verification command** for each deliverable before writing:
```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command compile --module {module} \
  --audit-plan-id {plan_id}
```
Use the returned `executable` value as the Verification Command. Both Command and Criteria are mandatory — do NOT omit. If architecture has no `compile` command, use the most specific available command (e.g., `verify`, `quality-gate`) or flag for user decision.

#### Log Deliverable Creation

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Created deliverable for {target}"
```

### Step 8: Simple Q-Gate

**Purpose**: Lightweight verification for simple track.

#### Q-Gate Surgical Bypass Rule

**Evaluated BEFORE running the per-deliverable verification checks below.**

Bypass the Simple Q-Gate when ALL of the following predicates hold:

1. `scope_estimate == surgical` (read from references.json — phase-2-refine sets it in Step 13; phase-3-outline MAY refine it in Step 6 after deliverables crystalize).
2. `change_type ∈ {bug_fix, tech_debt, verification}` (read from status.json metadata — set in Step 4 by `manage-status:change-type-heuristic`, with LLM fallback via `effort` when the heuristic is ambiguous).
3. `deliverable_count == 1` (exactly one deliverable was created in Step 7).

When all three predicates hold, emit the bypass decision log entry and skip directly to Step 12 (do NOT execute the per-deliverable checks):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline:qgate-bypass) Q-Gate skipped — scope_estimate=surgical, change_type={change_type}, 1 deliverable"
```

Where `{change_type}` is the literal value (`bug_fix`, `tech_debt`, or `verification`).

**Worked examples — when bypass fires**:

| `scope_estimate` | `change_type` | deliverables | Bypass? | Reason |
|------------------|---------------|--------------|---------|--------|
| `surgical` | `bug_fix` | 1 | YES | All three predicates hold |
| `surgical` | `tech_debt` | 1 | YES | All three predicates hold |
| `surgical` | `verification` | 1 | YES | All three predicates hold |

**Worked examples — when bypass does NOT fire** (Q-Gate runs normally):

| `scope_estimate` | `change_type` | deliverables | Bypass? | Reason |
|------------------|---------------|--------------|---------|--------|
| `surgical` | `feature` | 1 | NO | `feature` is outside the bug_fix/tech_debt/verification set |
| `surgical` | `enhancement` | 1 | NO | `enhancement` is outside the bug_fix/tech_debt/verification set |
| `surgical` | `bug_fix` | 2 | NO | More than one deliverable invalidates the "single surgical change" assumption |
| `single_module` | `bug_fix` | 1 | NO | `scope_estimate` is not `surgical` |
| `multi_module` | `bug_fix` | 1 | NO | `scope_estimate` is not `surgical` |
| `broad` | `tech_debt` | 1 | NO | `scope_estimate` is not `surgical` |
| `none` | `verification` | 1 | NO | `scope_estimate` is not `surgical` |

**Recipe-sourced plans** are unaffected: Step 3 (Recipe Detection) already short-circuits Steps 4-11 (including the Q-Gate dispatch) for `plan_source == recipe`. The bypass rule applies only to non-recipe Simple Track plans that reach Step 8.

**Rationale**: A surgical bug-fix / tech-debt / verification single-deliverable plan is precisely the shape where the Q-Gate's coverage and request-alignment checks add latency without finding new problems — the deliverable's scope is already minimal and pinned, the change type is corrective (not generative), and there is no second deliverable that could compete for the same files. Generative change types (`feature`, `enhancement`) and multi-deliverable plans still go through Q-Gate because their scope can drift.

#### Verify Deliverables

If the bypass rule above did NOT fire, run the per-deliverable checks:

For each deliverable:

1. **Target exists?** - Already validated in Step 6
2. **Deliverable aligns with request intent?** - Compare deliverable scope with request

#### Log Q-Gate Result

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline:qgate) Simple: Deliverable {N}: pass"
```

After Simple Q-Gate, proceed to Step 12.

---

## Complex Track Procedures (Steps 9-11)

For codebase-wide changes requiring discovery and analysis.

**File-type classifier applies here too**: every deliverable composed in Step 10 MUST be classified against the six-bucket [File-type classifier](#file-type-classifier) defined under Simple Track Procedures BEFORE its `profiles[]` block is finalised. The classifier vocabulary, predicates, profile assignments, and required bucket-comment recording are identical across both tracks — Complex Track does not redefine them. The cross-reference in Step 10's `**Affected files:**` composition is mandatory; the bucket comment on the `**Profiles:**` line is the audit trail.

### Step 9: Resolve Domain Skill and Load Change-Type Instructions

**Purpose**: Route to domain-specific or generic change-type instructions for discovery, analysis, and deliverable creation.

#### 9a: Resolve Domain Outline Skill

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-outline-skill --domain {domain} --audit-plan-id {plan_id}
```

**Output** (TOON):
```toon
status: success
domain: {domain}
skill: pm-plugin-development:ext-outline-workflow
source: domain_specific
```

or:

```toon
status: success
domain: {domain}
skill: none
source: generic
```

#### 9b: Load Change-Type Instructions

**IF source == domain_specific** (domain has registered outline_skill):
1. Load the domain skill: `Skill: {resolved_skill}` (e.g., `Skill: pm-plugin-development:ext-outline-workflow`)
2. Log the loaded skill:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-3-outline) Loaded domain skill: {resolved_skill}"
```
3. Read the domain-specific change-type instructions from the skill's standards directory. The file path is: `marketplace/bundles/{bundle}/skills/{skill_name}/standards/change-{change_type}.md`
4. Follow the instructions from that file for discovery, analysis, and deliverable creation

**IF source == generic** (no domain override):
1. Read the generic change-type instructions from this skill's own standards directory: read `standards/change-{change_type}.md` (relative to this skill)
2. Follow the instructions from that file for discovery, analysis, and deliverable creation

### Step 9c: Read Target Skill Design Intent

> **Track-agnostic activation**: although this procedure is documented under the Complex Track Procedures heading for historical reasons, it is **NOT Complex-Track-only**. It applies equally to **Simple Track Step 7** (Create Deliverables): whenever a Simple-Track deliverable touches an existing skill, the outline agent MUST run this same classification procedure and emit the resulting `**Design notes:**` block. Reading and following this procedure on the Simple Track is what lets a Simple-Track deliverable self-satisfy the §2.17 Architecture-Mismatch validator on the first validation pass, eliminating an otherwise-guaranteed re-outline round-trip.

**Purpose**: Before authoring any deliverable that touches an existing skill, classify the target skill's design model so the proposed implementation extends (rather than contradicts) the existing model. The classification is recorded on the deliverable in a `**Design notes:**` block and is the input the q-gate validation agent's `architecture-mismatch-validator` (§2.17, see `plan-marshall/workflow/q-gate-validation.md`) consumes to surface design-model violations as blocking findings.

**When to apply** (track-agnostic): this step fires for every deliverable — on EITHER the Simple Track (Step 7) or the Complex Track (Steps 9-11) — that lists at least one `marketplace/bundles/{bundle}/skills/{skill}/**` path under `**Affected files:**`. Deliverables that touch only standards documentation in an existing skill (`standards/**/*.md`) ALSO count — design-intent classification applies to the standards body, not just executable code. Deliverables that do not touch existing skills (brand-new skill creation, docs-only outside a skill, non-marketplace changes) skip this step.

**Procedure** (run once per qualifying deliverable, before its `**Change per file:**` block is finalised):

1. **Read the target skill's SKILL.md**.

   ```
   Read: marketplace/bundles/{bundle}/skills/{skill}/SKILL.md
   ```

   Skim for the `Role` declaration in the opening paragraph, the `Workflow` / `Standards (Load On-Demand)` section, and any `Enforcement` block.

2. **Read the target skill's design-intent docs** when present. Common locations:

   - `standards/design-intent.md` (explicit design-intent doc; canonical when present)
   - `standards/architecture.md` (when the skill documents its own architecture)
   - The skill's `Role` paragraph plus the `Standards Reference` table (fallback when no dedicated design-intent doc exists)

3. **Classify the design model**. The classification is a single token chosen from three values:

   - **`script-deterministic`** — the skill's logic lives in a Python / shell / TypeScript script under `scripts/{name}.py` (or equivalent). The SKILL.md narrative documents the script's CLI shape, subcommands, and return contract. The skill has zero or near-zero LLM cognitive work — the script does the work, the SKILL.md narrative tells callers how to invoke it.

     *Examples*: `manage-execution-manifest`, `manage-tasks`, `manage-status`, `manage-findings`, `manage-logging` — every `manage-*` skill is script-deterministic by construction.

   - **`LLM-driven`** — the skill has no script entry point. The SKILL.md narrative is the executable definition: an LLM agent loads the skill (via `Skill: {ref}`) and follows the prose steps in-context. The skill may invoke other scripts as steps, but the orchestration logic, the decision-making, and the artifact production are all performed by the LLM.

     *Examples*: `phase-3-outline` (this skill), `phase-4-plan`, `plan-marshall:plan-marshall/workflow/q-gate-validation.md` (dispatched under `--phase phase-N` matching the caller phase), `plugin-doctor`, `plan-retrospective`.

   - **`hybrid`** — the skill has both a Python script and a non-trivial LLM prose body. The script handles a deterministic sub-task (file I/O, validation, dispatch); the LLM prose body handles the remaining cognitive work. Hybrid skills carry both a `scripts/` directory and substantive `Workflow` prose.

     *Examples*: `phase-5-execute` (script-driven task loop + LLM execution of individual tasks), `phase-6-finalize` (script-driven step dispatcher + LLM finalize-step bodies), `phase-2-refine` (script-driven status updates + LLM clarification dialogue).

   **Detection heuristic** (apply in order; first match wins):

   - The skill has a `scripts/` directory containing at least one `*.py` AND the SKILL.md narrative consists primarily of CLI documentation (subcommand tables, parameter lists, return-shape examples) → `script-deterministic`.
   - The skill has no `scripts/` directory at all → `LLM-driven`.
   - The skill has a `scripts/` directory AND the SKILL.md narrative has substantive cognitive prose (workflow steps, decision rules, in-prose dispatch logic that the LLM follows) → `hybrid`.

4. **Record the classification on the deliverable**. Emit a `**Design notes:**` block immediately after the `**Intent gloss:**` block (or after `**Metadata:**` when no intent gloss is required) carrying:

   ```markdown
   **Design notes:** Extends the existing {script-deterministic | LLM-driven | hybrid} design model of `{bundle}:{skill}` — {one-sentence rationale}.
   ```

   The rationale sentence MUST name the specific element of the design model the proposed implementation extends. Generic rationale ("matches the existing model") fails the validator; the sentence has to be specific enough that a reader can verify it.

   **Examples** (illustrative, not normative):

   - `**Design notes:** Extends the existing script-deterministic design model of `plan-marshall:manage-execution-manifest` — adds a new `validate-loadable` CLI subcommand alongside the existing `compose` / `read` / `validate` subcommands.`
   - `**Design notes:** Extends the existing LLM-driven design model of `plan-marshall:phase-3-outline` — adds a new prose step that the outline agent reads and follows; no script entry point is introduced.`
   - `**Design notes:** Extends the existing hybrid design model of `plan-marshall:phase-6-finalize` — adds a new built-in step backed by `standards/{name}.md` for the LLM body and `manage-status mark-step-done` for the script-side termination.`

5. **Detect divergence and reroute**. If the proposed implementation strategy contradicts the target skill's design model, the outline MUST either reroute the implementation to fit the model OR justify the divergence in the `**Design notes:**` block (in which case the q-gate validator will surface the divergence for explicit human approval).

   **Canonical mismatch shapes** (the validator's recurrence signals — see plan-marshall/workflow/q-gate-validation.md §2.17):

   - **Script-side check evaluators proposed for an LLM-driven skill aspect** — e.g., a deliverable adds a Python script that walks SKILL.md prose for a regex match. The aspect is LLM-driven (the SKILL.md narrative is read in-context by the agent); a script-side regex evaluator is the wrong model. **Reroute**: the check belongs in `plan-marshall/workflow/q-gate-validation.md` as a new validator subsection (LLM-driven) OR in `plugin-doctor` if it is a structural-compliance check (also LLM-driven by §-based dispatch).
   - **LLM-driven workflow proposed for a script-deterministic skill aspect** — e.g., a deliverable adds an SKILL.md narrative step that performs file I/O the script already handles. The aspect is script-deterministic; LLM-driven narrative steps that re-do script work are duplication. **Reroute**: extend the script's CLI surface (new subcommand or flag) and replace the proposed narrative step with a single invocation of the new CLI shape.
   - **Hybrid skill change that breaks the script/LLM boundary** — e.g., a deliverable moves deterministic dispatch logic from the script into LLM prose, or moves LLM cognitive work into the script. The skill's hybrid design model has a documented script/LLM boundary; changes that cross the boundary contradict the model. **Reroute**: respect the existing boundary, OR document the boundary shift explicitly in the `**Design notes:**` block as a deliberate refactor (the validator will surface it for review).

   **When divergence is justified**: the `**Design notes:**` block names both the existing model and the divergence rationale. The block MUST take the form:

   ```markdown
   **Design notes:** Diverges from the existing {model} design model of `{bundle}:{skill}` — {one-sentence rationale for the divergence}, {one-sentence statement of how the new model is documented going forward}.
   ```

   The "documented going forward" half is required: a divergence that does not update the skill's own design-intent declaration silently creates two design models in the same skill, which is worse than the original gap. The deliverable's task list MUST include an edit to the skill's design-intent doc (or to SKILL.md's `Role` paragraph) that records the new model.

**Validator linkage**: the `architecture-mismatch-validator` in `plan-marshall/workflow/q-gate-validation.md` (§2.17) parses the `**Design notes:**` block on every deliverable that touches an existing skill and emits an `architecture-mismatch` finding with `severity: blocking` when the block is absent, generic, or contradicts the skill's documented design model. Phase-3-outline's Step 11 auto-loops on blocking findings (see "Step 11: Q-Gate Verification" below), so a missing or contradictory `**Design notes:**` block forces a re-outline pass before phase transition.

### Step 10: Execute Change-Type Workflow and Write Solution

**Purpose**: Execute the loaded change-type instructions, resolve verification commands, and write the solution outline.

#### 10a: Execute Discovery and Analysis

Follow the loaded change-type instructions from Step 9b. These instructions define:
- Discovery approach (inventory scan, targeted search, direct mapping)
- Analysis logic (component assessment, scope determination)
- Deliverable structure (type-specific metadata and sections)

#### 10a-bis: Consumer sweep for delete/rename deliverables

**Mandatory** for every deliverable composed in Step 10a whose `Change per file`, `Refactoring`, or title text contains delete/rename language applied to a public symbol. See [`consumer-sweep.md`](consumer-sweep.md) for the full trigger heuristic, sweep procedure (`architecture find` first, grep fallback for sub-module references), output format, and the worked `load_derived_data` example.

The sweep ensures every cross-bundle consumer of the deleted/renamed symbol becomes an explicit entry under the deliverable's `**Affected files:**` list. Run the sweep BEFORE Step 10b (Resolve Verification Commands) and Step 10c (Write Solution Outline) — the sweep's output feeds both the verification command resolution and the written deliverable. When the trigger heuristic does not fire for a deliverable, skip silently for that deliverable (no log entry required).

#### 10b: Resolve Verification Commands

For each deliverable, resolve verification commands from architecture:

```bash
# Build/compile verification
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command compile --module {module} \
  --audit-plan-id {plan_id}

# Test verification (for deliverables with module_testing profile)
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command module-tests --module {module} \
  --audit-plan-id {plan_id}
```

**Available architecture commands**: `compile`, `test-compile`, `module-tests`, `quality-gate`, `verify`, `coverage`, `clean`. Do NOT use `test` (use `module-tests` instead).

Use the returned `executable` value as the Verification Command.

#### 10b-bis: Render architecture hints

Read the per-module architecture hints and render them into the solution outline so phase-4-plan can consume durable project facts during task derivation. The hints store is populated by the finalize-time KNOWLEDGE-routing step (`architecture enrich tip|insight|best-practice`); this is the consuming side that turns it into a read surface.

1. Call the deterministic reader for the per-module hint inventory:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline get-module-context \
     --plan-id {plan_id}
   ```

   On `status: not_found` (architecture not discovered), skip this sub-step silently — there are no hints to render. On `status: success`, each `modules[]` entry carries the optional `tips`, `insights`, and `best_practices` lists (absent when empty).

2. **Select the relevant entries**: the plan's declared module(s) from `references.json` PLUS the `default` module's entries. The `default` module is the home for cross-cutting (non-module-specific) project facts — fold its `tips`/`insights`/`best_practices` into the section so project-wide knowledge always surfaces, regardless of which module(s) the plan touches.

3. **Render a `## Architecture Hints` section** into `solution_outline.md` (authored in 10c below) listing the non-empty `tips`, `insights`, and `best_practices` for the selected entries. Group by module name; within each module label the three lists. **Omit the entire `## Architecture Hints` section when every selected entry's hint lists are empty** — this keeps the required-section contract unchanged (the section is purely additive and never becomes a required section).

#### 10c: Write Solution Outline

Use `write` on first entry (solution_outline.md does not exist yet).
Use `update` on re-entry (Q-Gate loop — solution_outline.md already exists).

**CRITICAL — Deliverable Heading Format**: Each deliverable MUST use exactly `### N. Title` (e.g., `### 1. Migrate component X`). The validation regex is `^### \d+\. .+$`.

Check first:
```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline exists \
  --plan-id {plan_id}
```

If `exists: false`:
```bash
# 1. Get target path
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}

# 2. Write content directly via Write tool
Write({resolved_path}) with solution outline content including:
  - Header with plan_id and compatibility
  - Summary, Overview, Deliverables sections
  - Each deliverable with Metadata, Profiles, Affected files, Verification, Success Criteria

# 3. Validate
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

If `exists: true`:
```bash
# 1. Read current content, modify as needed
# 2. Write updated content via Write tool to the same path
# 3. Validate
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  update --plan-id {plan_id}
```

#### 10d: Test Helper File Naming

**Rule**: When a deliverable's `**Affected files:**` list references test helpers (shared fixtures, setup utilities, sys.path shims, or any non-test Python module living under a skill test directory), the file MUST be named `_fixtures.py` (or another descriptive `_*.py` name that clearly is not a test collection file). It MUST NOT be named `conftest.py` under any path matching `test/**/` that corresponds to a skill or script test directory.

**Why**: pytest auto-discovers `conftest.py` and evaluates it as a fixture-collection module for every test run. Adding a `conftest.py` under `test/{bundle}/{skill}/` changes pytest collection semantics globally for that bundle's tests, causing hidden coupling, duplicate-fixture warnings, and in the worst case test collection failures unrelated to the plan's intent. Using `_fixtures.py` (imported explicitly by the tests that need it) keeps the helper local, scoped, and reviewable as plain Python.

**Permitted set**: The only `conftest.py` files permitted in this project are the two top-level files `test/conftest.py` and `test/adapters/conftest.py`. These are the only `conftest.py` paths that MAY appear in a deliverable's `**Affected files:**` list. Any other `conftest.py` in an `**Affected files:**` list is a defect. Replace with `_fixtures.py` (or a similarly scoped helper name) and update any `Change per file:` text to describe explicit imports from the tests that consume it. The generic rule is project-invariant: do not name a new test helper `conftest.py`.

**Cross-references**:
- `plan-marshall:dev-general-module-testing` — testing methodology (AAA pattern, coverage, test organization) this rule supports
- `pm-dev-python:pytest-testing` — pytest framework standards including fixture discovery semantics that motivate the `conftest.py` restriction

#### Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Change-type workflow complete: {N} deliverables ({change_type})"
```

**If workflow fails**: HALT and return error. Do NOT fall back to grep/search.

### Special-deliverable-class recognition rules (detail)

These two recognition triggers are track-agnostic siblings to the Step 9c (design-intent) procedure above: they fire at deliverable-authoring time on **both** the Simple Track (Step 7) and the Complex Track (Step 10). Each rule is a thin trigger predicate plus the required authoring action and a pointer to the dev-general-* home where the substance lives. The mitigation menu and the enumeration procedure are NOT restated here — only the trigger and the cross-reference.

#### Cooperative-lock deliverable class

**Trigger predicate**: the deliverable's narrative (`Change per file:` / summary / success criteria) introduces or modifies a cooperative cross-process lock or a shared-state coordination primitive — merge locks, worktree allocation, plan-id reservation, leader election, or any "claim a shared resource" flow where two processes can race for the same slot.

**Required authoring action**: emit a `**Concurrency-correctness note:**` block on the deliverable that (a) names the check-then-act / TOCTOU window the new coordination opens, and (b) points to the mitigation the deliverable will adopt. The note MUST cross-reference the TOCTOU / check-then-act mitigation menu in [`../../dev-general-code-quality/standards/code-organization.md`](../../dev-general-code-quality/standards/code-organization.md#toctou--check-then-act-hazards) for the mitigation substance — **do NOT duplicate the post-write-double-check / deterministic-tiebreaker / atomic-primitive menu here or on the deliverable**.

#### Value-change deliverable class

**Trigger predicate**: the deliverable changes a default value, a named constant, an enum member, or a threshold literal that existing tests may assert against.

**Required authoring action**: scope the old-value test assertions into the deliverable's `**Affected files:**` list so the production change and its test-consumer updates form one atomic deliverable that verifies on the first cut. Cross-reference the enumerate-existing-test-consumers discipline in [`../../dev-general-module-testing/standards/testing-methodology.md`](../../dev-general-module-testing/standards/testing-methodology.md#enumerate-existing-test-consumers-before-changing-a-default--constant--enum-value) for the discovery → classification → atomicity procedure — **do NOT restate the grep-symbol-and-literal / classify / atomic-update sequence here or on the deliverable**.

### Clean-break vs migration-shim decision checklist

This is the canonical detail home for the **Clean-break vs migration-shim deliverable class** recognition trigger declared in [`../SKILL.md` § Special-deliverable-class recognition rules](../SKILL.md#special-deliverable-class-recognition-rules-track-agnostic-thin) (rule 3). The recognition trigger in SKILL.md is thin; the checklist body, per-condition rationale, decision table, and compatibility relationship live here and are NOT duplicated upstream or restated on the deliverable.

**Trigger predicate**: the deliverable's narrative (`Change per file:`, `Refactoring:`, summary, or title) removes an **internal code path** — a function, method, parameter, conditional branch, config knob, or script notation that is consumed only within the codebase. A path is "internal" when it is NOT a published cross-bundle public surface (a documented skill notation other bundles invoke, an exported API, a flag named in a consumer project's config). When the removed surface IS cross-bundle / external, this checklist does not decide the shape on its own — run the [consumer sweep](consumer-sweep.md) first and treat the external consumer as condition (2) failing below.

**Four-condition checklist** (evaluate every condition; record the answer per condition on the deliverable):

| # | Condition | One-line rationale |
|---|-----------|--------------------|
| 1 | Are **all callers** of the removed path in-plan (edited by this same plan)? | A caller left un-updated breaks at runtime the moment the path is gone; the clean break is only safe when the plan owns every call site. |
| 2 | Is there **no external / cross-bundle consumer** of the path? | A shim exists to give consumers a migration window; with zero external consumers there is nobody to migrate, so the window is pure dead weight. |
| 3 | Can the removal land **atomically in a single PR** (old path and its replacement ship together)? | Atomicity means main is never in a half-migrated state; a multi-PR removal needs the old path to survive between PRs, which is what a shim provides. |
| 4 | Are the **old-path tests removed or rewritten** in the same plan? | Tests asserting the old path are themselves consumers; leaving them green against a deleted path is impossible, leaving them red is a broken build — both force same-plan test work. |

**Decision table**:

| Checklist outcome | Chosen shape | What the deliverable does |
|-------------------|--------------|---------------------------|
| ALL four conditions hold | **Clean break** | Remove the internal path outright in this plan. No deprecation marker, no compatibility alias, no transition window. The deliverable's narrative deletes the path and updates every caller and test atomically. |
| ANY condition fails | **Deprecation shim with a documented removal window** | Keep the old path alongside the new one with an explicit deprecation marker; document the removal trigger (the named follow-up plan, the condition under which the old path is dropped). The deliverable that introduces the new path is additive; the removal is deferred to a successor plan/lesson. |

**Relationship to the plan-level `compatibility` setting**: this checklist **informs** which `compatibility` value the deliverable should assume — it augments, it does not replace, the plan-level setting read in Step 2. When all four conditions hold, the deliverable is consistent with `compatibility: breaking` (clean-slate removal). When any condition fails, the deliverable is consistent with `compatibility: deprecation` (old surface retained with a migration path). If the checklist outcome contradicts the plan-level `compatibility` already set (e.g. the plan declares `breaking` but condition (2) fails because an external consumer exists), surface the mismatch: either narrow the deliverable to the additive half and defer the removal, or raise the contradiction to the author rather than silently shipping a breaking removal that strands an external consumer. The checklist is the per-deliverable decision rule; the plan-level `compatibility` is the default the rule refines.

### Survey-scope vs mutation-scope declaration

This is the canonical detail home for the **Survey-scope deliverable class** recognition trigger declared in [`../SKILL.md` § Special-deliverable-class recognition rules](../SKILL.md#special-deliverable-class-recognition-rules-track-agnostic-thin) (rule 4). The recognition trigger in SKILL.md is thin; the field semantics, the worked example, and the `survey_vs_mutation_scope_declared` check live here.

**Trigger keyword set**: a deliverable is a **survey-scope (discovery-style) deliverable** when its title or description contains any of `survey`, `discover`, `classify`, or `case-by-case`. These deliverables share a structural property: the exact set of files they will *mutate* is not fully known at authoring time, because the deliverable's first action is to inspect a candidate pool and decide, file by file, which members actually need changing.

**Two-field declaration semantics**: a survey-scope deliverable MUST declare two fields instead of a single `**Affected files:**` list:

- `**Files to survey:**` — the **candidate pool / analysis scope**: every file the deliverable must read or inspect to decide what to change. This is the broad upper bound of *examination*, and it captures files that are analysed but NOT expected to change.
- `**Files expected to mutate:**` — the **mutation-scope upper bound**: the subset the deliverable expects to actually edit. This is the list that downstream profile classification and the retrospective recall check consume.

**Disjointness requirement**: each file appears under **exactly one** field. List a file under `**Files expected to mutate:**` when you expect to edit it; list it under `**Files to survey:**` only when you need to read/analyse it but do NOT expect to change it. The two lists are therefore disjoint by construction — `Files to survey:` is analysis-only, `Files expected to mutate:` is change-bearing. Conflating them into one `**Affected files:**` blob is the failure mode this convention prevents: a single merged list either over-claims (every surveyed file counted as "affected", which tanks the retrospective recall metric) or under-scopes (the analysis pool hidden, so reviewers cannot see what was examined).

**`affected_files_recall` scope**: the downstream retrospective `affected_files_recall` check (run during plan retrospective) measures actually-mutated files against the declared mutation scope — it runs against the `**Files expected to mutate:**` subset, **NOT** the survey scope. A file surveyed-but-not-mutated never counts against recall; a file mutated-but-not-listed-under-`Files expected to mutate:` does. (This recall check is referenced here for completeness; it is owned by the retrospective workflow and is out of scope for the survey-scope authoring rule itself.)

**Worked example** — a discovery-style deliverable with both fields populated:

```markdown
### 3. Classify and migrate legacy loggers case-by-case

**Metadata:**
- change_type: tech_debt
- execution_mode: automated
- domain: plan-marshall-plugin-dev
- module: plan-marshall

**Files to survey:**
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage_status.py`
- `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/manage_tasks.py`
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage_config.py`

**Files expected to mutate:**
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage_status.py`
```

Here three scripts are surveyed for legacy logging calls, but the deliverable expects to mutate only the one that the survey confirms uses the legacy pattern. The other two are analysed and ruled out — they stay under `**Files to survey:**`. (When the survey confirms a file does need changing, the author moves it from `Files to survey:` to `Files expected to mutate:` before the outline is finalised, preserving disjointness.)

#### `survey_vs_mutation_scope_declared` outline check (LLM-driven)

This is an LLM-driven outline check — prose the outline agent applies in-context during Step 7 / Step 10 deliverable authoring, in the same family as the design-intent check. It is NOT a Python script: the agent reads the rule and the positive/negative examples below and applies the judgement directly.

**Check logic**: for every deliverable whose title or description matches the trigger keyword set (`survey` / `discover` / `classify` / `case-by-case`), assert that the deliverable declares BOTH `**Files to survey:**` AND `**Files expected to mutate:**`. Flag the deliverable when either field is absent (a survey-style deliverable carrying only a flat `**Affected files:**` list, or only one of the two fields).

**Positive example (passes)** — survey-style deliverable declaring both fields:

```markdown
### 2. Survey deprecated config keys and classify each for removal

**Files to survey:**
- `marketplace/bundles/plan-marshall/skills/manage-config/standards/config-schema.md`
- `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/marshall_steward.py`

**Files expected to mutate:**
- `marketplace/bundles/plan-marshall/skills/manage-config/standards/config-schema.md`
```

The title contains `Survey` and `classify`; both fields are present and disjoint → the check passes.

**Negative example (flagged)** — survey-style deliverable with a single flat list:

```markdown
### 2. Survey deprecated config keys and classify each for removal

**Affected files:**
- `marketplace/bundles/plan-marshall/skills/manage-config/standards/config-schema.md`
- `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/marshall_steward.py`
```

The title matches the trigger (`Survey` / `classify`) but the deliverable declares only a flat `**Affected files:**` list with no survey/mutation split → the check flags it. The candidate pool and the expected mutation set are conflated, so the retrospective recall check cannot tell which files were merely examined; the author must split the list into the two disjoint fields before the outline is finalised.

These positive/negative examples ARE the check's test coverage — per the LLM-driven-validator convention, a prose check is exercised by the in-document examples the authoring agent matches against rather than by a pytest suite.

### Retrospective-vs-prospective lesson classification

This is the single shared definition consumed by **two** callers: the [Retrospective-lesson recognition rule in `../SKILL.md`](../SKILL.md#retrospective-lesson-recognition-rule-track-agnostic-thin) and [`recipe-lesson-cleanup` Step 2c](../../recipe-lesson-cleanup/SKILL.md#step-2c-retrospective-vs-prospective-classifier). Both skills read the signals and template defined here rather than restating them, so outline-time and recipe-time classification stay in lockstep.

**Classification signals** — a lesson (or one of its directives) is **retrospective** when ALL of the following hold; otherwise it is **prospective**:

| Signal | Retrospective | Prospective |
|--------|---------------|-------------|
| Fix-shipped state | The corrective code change has **already shipped** (landed on the base branch after the lesson was authored). In `recipe-lesson-cleanup` this is read directly from Step 2b's `redundant` verdict — do NOT re-probe the tree. | The corrective change has **not** yet shipped — the directive describes work still to do. |
| Forward-looking section | The lesson body carries a generalizable rule: a `## Generalisation` / `## Generalization` heading, or a "the general rule is…" / "in future, always…" passage that states a reusable principle beyond the one-off fix. | No forward-looking section — the lesson is a one-off corrective directive with no generalizable rule. |
| Source still editable | The target component's canonical docs (`SKILL.md` / `standards/*.md`) still exist and are editable, so the wisdom has a home to port into. | n/a — prospective lessons route to a code-change deliverable regardless. |

When the fix already shipped but there is **no** forward-looking section (nothing generalizable to port), the lesson is neither retrospective-portable nor prospective — it is simply obsolete, and `recipe-lesson-cleanup` Step 2c's classification drops it (it reads Step 2b's `redundant` verdict but is itself the step that filters the obsolete directive out before Step 3). The retrospective shape applies ONLY when there is generalizable wisdom worth lifting into the docs.

**Apply-the-wisdom / documentation-port deliverable template** — a retrospective directive emits a `documentation_only` deliverable in this shape:

```markdown
### {N}. Apply lesson wisdom: {one-line rule summary}

**Metadata:**
- change_type: enhancement
- execution_mode: automated
- domain: {domain}
- module: {module}

**Design notes:** Extends the existing {LLM-driven | hybrid | script-deterministic} design model of `{bundle}:{skill}` — ports a forward-looking rule into the component's canonical docs; no behavioural code change (the fix already shipped).

**Profiles:** <!-- bucket: documentation_only -->
- implementation

**Affected files:**
- `marketplace/bundles/{bundle}/skills/{skill}/SKILL.md`  # or the relevant standards/*.md

**Change per file:**
- Port the forward-looking rule from lesson `{lesson_id}` into the canonical docs as durable guidance. Capture the rule content only — the lesson ID names the source here (a plan-internal field) but MUST NOT appear in the ported skill prose.

**Verification:**
- Command: `python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace quality-gate --paths marketplace/bundles/{bundle}/skills/{skill} --marketplace-root {worktree_path}/marketplace`
- Criteria: the forward-looking rule content appears in the component's canonical docs; the ported skill prose carries NO narrative lesson-ID citation; the scoped `quality-gate --paths` returns `status: pass` with no `analyze_lesson_id_in_skill_prose` findings.

**Success Criteria:**
- The generalizable rule from lesson `{lesson_id}` is documented in the component's canonical docs as rule content.
- The ported skill prose carries no lesson-ID citation; the lesson `{lesson_id}` cross-reference is confined to this deliverable's plan-internal fields.
```

**Required lesson cross-reference — plan-internal fields ONLY**: the apply-the-wisdom deliverable MUST cross-reference the originating lesson `{lesson_id}` in both the `**Change per file:**` instruction and the `**Success Criteria:**`, so the audit trail from ported guidance back to the source lesson survives. A documentation-port deliverable that lifts a rule without naming its source lesson is incomplete — the cross-reference is what lets a future reader (or the lessons-housekeeping reconciler) confirm the wisdom was ported rather than re-derived.

The lesson-ID cross-reference belongs ONLY in the deliverable's plan-internal fields — `**Change per file:**` and `**Success Criteria:**` — which live in the plan workspace, not in any shipped doc. **The ported skill prose itself MUST NOT carry a narrative lesson-ID citation** (e.g. "documented in lesson `YYYY-MM-DD-HH-NNN`", "this lesson is `YYYY-MM-DD-HH-NNN`", or any equivalent narrative reference to a lesson identifier) inside a `SKILL.md` / `standards/*.md` body. Such a citation trips the marketplace `no-lesson-id-in-skill-prose` rule (`analyze_lesson_id_in_skill_prose`): lesson IDs are internal and ephemeral, not durable cross-reference targets, so they have no place in shipped skill prose. The correct way to honour a lesson in skill prose is to **capture the rule content and drop the lesson-ID citation** — strip the ID and any "lesson" prefix, keep the rule. So a doc-port success criterion MUST be written as "document the rule content", NEVER as "cross-reference the originating lesson `ID`" targeting a skill body; provenance lives in the plan/PR/commit trail, never in the durable doc.

The `**Change per file:**` and `**Verification.Criteria:**` text in the template above accordingly instructs the implementor to port the rule content WITHOUT citing the lesson ID in the ported prose — the lesson-ID naming in those template fields is the plan-internal provenance, and the ported skill prose it produces carries the rule alone.

**Coordination with `recipe-lesson-cleanup`**: the recipe's Step 2c is the lesson-conversion entry point — it classifies each surviving directive and marks retrospective ones `shape: documentation-port` before Step 3 composes the outline. The phase-3-outline recognition rule is the general-plan entry point — it fires when any plan/deliverable (recipe-sourced or not) originates from a retrospective lesson. Both produce the same documentation-port shape from this one template; keeping the definition here ensures a change to the signals or template updates both callers at once.

### State-verification discipline during outline

These rules govern how the outline must verify actual state — defect liveness, on-disk paths, and analyzer scope — before settling a deliverable's classification or `**Affected files:**` list. They share one premise: the outline reasons from a snapshot (a backward-looking signal, a remembered path, a sampled violation set) that may no longer match what is on disk, so each rule requires an empirical check against the live tree before the snapshot is committed into the solution outline.

#### Empirically verify defect liveness before settling on `documentation_only`

**Trigger predicate**: phase-2-refine's `narrative_vs_code_validator` flagged a proposed fix direction as `stale` / already-shipped (the fix the request reasoned from appears, on code-reading, to be already in place), and the outline is about to classify the deliverable as `documentation_only` on that basis.

**Required action**: do NOT settle on `documentation_only` from code-reading alone. First gather two pieces of empirical evidence per reported defect:

1. **Identify the ship PR and merge date of the alleged fix.** The load-bearing code change is the real cutoff — not a workflow-only PR that masquerades as the fix. Locate the commit/PR that actually changed the offending code path and record when it merged.
2. **Check post-fix archived-plan data for plans that ran after the ship date.** A clean cutoff (no recurrence in plans that ran after the fix merged) confirms `fixed → documentation_only`. Persistence past the ship date (the symptom still appears in plans that ran after the fix landed) proves the defect is still live, and a real code fix — not a docs-only port — is in scope.

**When the two halves disagree** (e.g. one reported defect is genuinely fixed but a second is still live), escalate the empirical finding to the user via `AskUserQuestion` before finalizing scope. Do not silently settle the whole plan as `documentation_only` when part of it is still a live defect.

**Generalize beyond lesson-sourced plans**: any plan derived from a backward-looking signal — a lesson, a retrospective, an archived-plan audit, or a prior finding — inherits a premise captured at signal time. That premise may have gone stale between when the signal was authored and when the plan runs. The empirical-liveness check applies to every such plan: confirm the reported defect or gap is still live against the current tree before accepting a classification that assumes it is (or is not) already resolved.

#### Verify the request's own root-cause statement against the live artifacts before designing against it

A request's stated root cause is a **hypothesis, not a fact**. Before authoring an outline against the mechanism a request asserts, verify that assertion against the live artifacts — real token/metric data, the actual source contract, the dormated symptom plan — rather than accepting the narrative at face value. This is especially load-bearing in two cases:

1. **The proposed fix asserts a component does something it was explicitly designed to do.** When a request frames a designed return contract or a deliberate behaviour as a "bug", read the component's source to confirm the behaviour is actually a defect and not the contract. A request that says "the leaf returns bare instead of looping" may be describing the executor's *designed* `next_action: task_complete` return shape, not a fragmentation bug.
2. **The proposed fix asks the runtime to measure something it cannot observe.** A subagent running inside a dispatched envelope **cannot observe its own context-window or token consumption mid-turn** — no tool, environment variable, signal, or API returns tokens-used-so-far to the model while it executes; the `<usage>` block reaches the *orchestrator* only after the dispatch returns. Any design that asks an in-flight envelope to compare its own runtime usage against a budget and decide continue-vs-yield is therefore **structurally unevaluable** — the predicate has no source. When a request proposes a runtime budget sentinel / cost ceiling / self-throttle, recognize it as harness-infeasible at outline time and pivot the design to derive the decision from **planning-time constants the agent CAN evaluate** (a pre-computed per-task cost size and an envelope-group membership check), not runtime self-measurement.

**Required action**: when the request's root-cause statement carries either signature above, read the live source contract and the real metric data at outline time and refute or confirm the claim before committing the design. Refuting a wrong root cause early avoids the iteration cost of designing — and partly building — against a mechanism that does not exist or cannot be evaluated. (extends the empirical-liveness check above to the request's *causal* premise, not just defect liveness.)

#### Verify read-intent affected-file paths exist on disk before writing them into `**Affected files:**`

**Trigger predicate**: the outline is about to write a `read`-intent step into a deliverable's `**Affected files:**` block, pointing at a Python script (or any existing, non-created file) that the deliverable will read rather than author.

**Required action**: verify the exact on-disk path before committing it to the outline. Run `architecture find --pattern {basename}` (or fall back to `Glob` when the architecture verb returns elision) to resolve the file's actual path, and confirm the resolved path matches what is about to be written. A `read`-intent path that does not resolve to a real file on disk is a phantom path: it sails through outline but fails the `files_exist` Q-Gate check in phase-4-plan and forces a corrective `rename-path` round-trip.

**`manage-*` script naming convention** (the most common source of guessed-but-wrong read paths): a `manage-*` skill's scripts follow a fixed naming convention — the entrypoint is `manage-{skill}.py`, and private helpers are named `_cmd_*.py` / `_*_core.py` / `_*_defaults.py`. Do NOT guess a plausible "canonical" monolithic name (e.g. `config.py` for the `manage-config` skill) — the real entrypoint is `manage-config.py`, and the logic the deliverable wants to read may live in a `_*` helper rather than the entrypoint. Resolve the actual filename with `architecture find` before writing it into `**Affected files:**`.

#### Run the widened analyzer during outline to enumerate the FULL newly-in-scope violation set

**Trigger predicate**: a deliverable widens the scope of a deterministic analyzer / lint / regex rule — it makes the rule apply to more files, more directories, a looser match pattern, or a new file class than it covered before.

**Litmus test**: "Does this deliverable make an existing rule apply to files it did not apply to before? If yes, run the rule and list every violation in the newly covered files."

**Required action** (all three steps, in order):

1. **Run the widened rule during outline against the post-change scope and capture the FULL violation list.** Do not sample, survey, or reason from a representative subset — execute the rule with its new (wider) scope and read off every hit.
2. **Enumerate every newly-in-scope violation file in `affected_files`** so each becomes a remediation deliverable. The new-scope violation set is exactly `(widened-rule findings) − (pre-existing narrow-rule findings)`: subtract the violations the rule already reported under its old narrow scope, and what remains is the set the widening newly exposes. Every member of that set must appear in the outline as a file the plan will fix.
3. **Size the plan against the complete count, not a sample.** The plan's effort estimate, task count, and deliverable list must reflect the full newly-in-scope violation count. When the plan is sized against a sample, the enforcement gate it ships cannot reach zero — unremediated newly-in-scope violations remain — and the plan balloons mid-execute via scope-expansion escalations as the missed violations surface one by one.

#### Verify test-file paths against disk before committing `affected_files`, disambiguating top-level vs subdirectory locations

**Trigger predicate**: the outline is about to commit an `**Affected files:**` entry that references a test file (`test_*.py`).

**Required action** (apply in order):

1. **Run `architecture find --pattern {basename}`** to locate the file's actual path.
2. **If the architecture verb returns elision or no result** (typical for a new test file the plan will create), use `Glob: test/**/{basename}.py` to confirm the parent directory exists and to see whether a same-named file already lives elsewhere in the tree.
3. **For existing test files that must be modified**, verify the path resolves to a real file on disk before including it.

**Top-level vs subdirectory disambiguation**: a test file may exist BOTH at a top-level path (`test/{bundle}/`) AND in a subdirectory (`test/{bundle}/{skill}/`). When a basename appears at two distinct paths, treat the two paths as different files — they are not interchangeable. Be explicit in the deliverable about which directory the intent applies to. Reversing the two (writing the top-level path when the subdirectory path was meant, or vice versa) produces a `files_exist` Q-Gate failure in phase-4-plan and a corrective `rename-path` round-trip. Resolving the basename against disk and naming the exact directory before the outline is written is what prevents the swap.

#### Validate cited lesson-ID tokens against the live inventory before writing the outline

**Trigger predicate**: the outline is about to write a `YYYY-MM-DD-HH-NNN`-shaped lesson-ID token into any deliverable body field — `**Success Criteria:**`, `**Change per file:**`, or any narrative field in the composed deliverable.

**Required action** (apply in order):

1. **Validate each cited token against the live inventory.** A bare lesson-ID citation is only legitimate when the ID resolves to a registered lesson. Confirm registration with the deterministic `manage-lessons` read verb:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons get --lesson-id {id}
   ```

   A registered ID returns the lesson; an unregistered ID returns the canonical error shape (`status: error` with `error: not_found`). To enumerate the full registered set in one call (e.g. when several tokens are being validated at once), use `python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list`.

2. **On a not-found result, choose one of two resolutions** (do NOT write the bare ID):

   - **(a) Drop-and-reword** — omit the bare ID from the deliverable body and reference the lesson by its logical role (what the lesson is *about*), not its identifier. This is the default for any field whose text would otherwise carry the bare token as narrative.
   - **(b) Confine to plan-internal fields** — when the ID must be retained as provenance, keep it ONLY in the deliverable's plan-internal fields (`**Change per file:**`, `**Success Criteria:**`), which live in the plan workspace and never ship in a skill body. Never write the bare ID into a field that will be lifted verbatim into shipped prose.

3. **Do NOT register the plan's own plan-source lesson to make a citation resolve.** When the unregistered ID is the plan's own plan-source lesson, it lives as a plan-local copy and is intentionally absent from the inventory. Registering it first is wrong: under the three-gate lesson-creation policy, Gate 2 finds the current plan IS the covering active plan and directs a fold-into-plan, not a create. Resolve the citation via resolution (a) or (b) instead.

**Why this is the upstream complement to the write-time safety net**: `manage-tasks batch-add` / `commit-add` already reject unregistered lesson IDs at task-write time (`lesson_id_not_found`), but that write-time validation scans `title + description` ONLY — the `steps[]` affected-path field carrying a lesson ID inside a filename is NOT scanned and is safe. The write-time net therefore catches an unregistered citation in a phase-4 task body, but only after the outline has already committed it. Running this check at outline time catches the unregistered citation where it originates — in the composed deliverable body — so the failure never surfaces downstream at `manage-tasks batch-add`.

This detail-standard prose carries the rule content; per the marketplace `no-lesson-id-in-skill-prose` rule (`analyze_lesson_id_in_skill_prose`) it MUST NOT cite the raw plan-source lesson-ID token in narrative — the wisdom is captured, the bare ID is not.

### Step 11: Q-Gate Verification

**Purpose**: Verify skill output meets quality standards.

#### Q-Gate Surgical Bypass Rule

**Evaluated BEFORE spawning the Q-Gate validation agent.**

The same predicate that gates the Simple Track Q-Gate (Step 8) ALSO gates the Complex Track Q-Gate (Step 11). Bypass when ALL of:

1. `scope_estimate == surgical` (phase-3-outline MAY refine `scope_estimate` in Step 10 after Complex Track discovery — e.g., `multi_module` → `single_module` → `surgical` once final Affected files are known).
2. `change_type ∈ {bug_fix, tech_debt, verification}`.
3. `deliverable_count == 1`.

When all three predicates hold, emit the bypass decision log entry, set `qgate_validation_required: false` in the phase return TOON, and skip directly to Step 12 (do NOT signal Q-Gate validation):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline:qgate-bypass) Q-Gate skipped — scope_estimate=surgical, change_type={change_type}, 1 deliverable"
```

The worked-examples table in Step 8 (above) applies verbatim to Step 11 — the rule, predicates, and log message are identical across both tracks. Recipe plans never reach Step 11 (Step 3 short-circuits them).

#### Signal Q-Gate Validation Requirement

If the bypass rule above did NOT fire, the phase records the requirement by setting `qgate_validation_required: true` in its return TOON (see `SKILL.md` § Return Output). The orchestrator (`plan-marshall:plan-marshall/workflow/planning-outline.md`) reads that flag after the phase returns and dispatches `q-gate-validation` as a sibling top-level `Task: plan-marshall:{target}` invocation — the phase body does NOT spawn `q-gate-validation` itself because the `Task` tool is unavailable inside an `execution-context-{level}` subagent. Aggregation of the validator's `qgate_pending_count` into the phase aggregate also moves to the orchestrator; this step only signals intent.

Log the intent so the run record shows the activation:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-3-outline) qgate_validation_required=true — orchestrator will dispatch q-gate-validation after phase return"
```

**Q-Gate reads from**:
- `solution_outline.md` (written by domain skill)
- `artifacts/findings/assessments.jsonl` (written by domain skill)
- `request.md` (clarified_request or body)

**Q-Gate verifies**:
- Each deliverable fulfills request intent
- Deliverables respect architecture constraints
- No false positives (files that shouldn't be changed)
- No missing coverage (files that should be changed but aren't)

##### Validator activation reference (phase-3-outline)

The agent applies the following mechanical validators automatically when invoked from this phase. Each validator is documented in `plan-marshall/workflow/q-gate-validation.md` with its activation condition, detection logic, finding emission template, and positive/negative examples. The activation is dispatched by the agent based on phase context — phase-3-outline does not pass validator names; the agent reads `phase: 3-outline` from the audit and runs the applicable subset.

| Validator (`plan-marshall/workflow/q-gate-validation.md` §) | Artifact consumed | Finding `--source` |
|---------------------------------------|-------------------|--------------------|
| Consumer Sweep Completeness (§ 2.9) | `solution_outline.md`, worktree grep results | `qgate` (unscoped source) |
| Argparse Validator (§ 2.10) | `solution_outline.md` (every embedded `python3 .plan/execute-script.py ...` invocation), live `--help` output of each cited script | `qgate-argparse` |
| Tier-Delta Validator (§ 2.13) | `solution_outline.md` (tiered/variant section pairs and their delta tables) | `qgate-tier-delta` |

The remaining validators (`module-mapping`, `scope-criterion`, `narrative-vs-code`) are scoped to other phases (4-plan or 2-refine) and do NOT activate when the agent is invoked from phase-3-outline. See `plan-marshall/workflow/q-gate-validation.md` for their canonical activation conditions.

Findings emitted by these validators flow into the same `qgate_pending_count` aggregate as the existing checks (Sections 2.1–2.7 and the missing-coverage sweep), so the orchestrator's existing 3-iteration auto-loop handles re-entry uniformly regardless of which validator emitted the finding.

**Q-Gate writes**:
- See [`findings-pipeline.md` § Store](../../ref-workflow-architecture/standards/findings-pipeline.md#store) for the per-type write layout.
- `logs/decision.log` - Q-Gate verification results

#### Q-Gate Return Value

```toon
status: success
plan_id: {plan_id}
deliverables_verified: {N}
passed: {count}
flagged: {count}
```

#### Log Q-Gate Result

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline:qgate) Full: {passed} passed, {flagged} flagged"
```

#### Handle Q-Gate Findings

The Q-Gate agent writes findings to `artifacts/qgate-3-outline.jsonl`. The phase returns `qgate_pending_count` to the orchestrator:

- If `qgate_pending_count == 0`: Continue to Step 12
- If `qgate_pending_count > 0`: Return with `qgate_pending_count` in output. The orchestrator auto-loops (re-enters this phase) until Q-Gate passes clean. No user prompt — Q-Gate findings are objective quality failures that must be self-corrected

After Complex Q-Gate, proceed to Step 12.

---

## ADR consultation (loop-invariant input)

The ADR-consultation step is a loop-invariant context read performed once at phase entry, alongside the other invariant inputs the `SKILL.md` § "Loop-invariant inputs (cached at phase entry)" block enumerates. It surfaces the established architectural decisions relevant to the plan's scope so deliverable authoring aligns with them and treats any superseded or deprecated decision as a constraint. The progressive-disclosure metadata that makes this read cheap is authored per the `manage-adr` skill — see `marketplace/bundles/plan-marshall/skills/manage-adr/SKILL.md` for the scan subcommand contract; this section is the consultation procedure, not the scan contract.

### Which filters to use

Scope the scan to the plan's declared footprint so the read stays cheap and relevant:

- **By module** — for each module in the plan's `domains` / `module_mapping` / declared scope, run `manage-adr scan --affects {module}`. The `affects` metadata field is the module-overlap dimension, so this returns exactly the ADRs whose decisions bear on the modules the plan touches.
- **By topic** — when the plan's request narrative centres on a named concern (a subsystem, a pattern, a cross-cutting capability), additionally run `manage-adr scan --tag {topic}` to pick up decisions that are topic-relevant but not module-scoped.
- **Whole corpus** — when the plan's scope is broad (`multi_module` or wider) or the module mapping is not yet resolved, run `manage-adr scan` with no filter and read all `summary` fields.

Read only the `summary` fields first. Load a full ADR (via `manage-adr read --number N`) only when a summary indicates the decision directly constrains a deliverable being authored.

### How ADR summaries fold into deliverable authoring

For each deliverable being composed:

1. Cross-reference the deliverable's intent against the loaded ADR summaries.
2. When a deliverable aligns with an established decision, the deliverable narrative SHOULD name the ADR (e.g. "aligns with ADR-NNN: {summary}") so the alignment is auditable.
3. When a deliverable would act against a `Superseded` or `Deprecated` ADR, treat that ADR as a constraint — prefer the superseding decision, and do not re-introduce the superseded shape.

### Contradiction is a design signal, not a hard gate

A deliverable that contradicts an `Accepted` ADR is a **design signal to surface**, not a hard gate that blocks the outline in this plan's scope. When a contradiction is unavoidable (the request genuinely requires revisiting an established decision), the outline SHOULD note the contradiction in the deliverable narrative so the reviewer — and the downstream finalize `adr-propose` step — can decide whether the decision warrants a new or superseding ADR. The outline does not auto-block on the contradiction; it makes the tension visible.
