# Outline Workflow Detail

Detailed procedures for the phase-3-outline skill. This document contains the step-by-step instructions for Q-Gate re-entry, recipe detection, change-type detection, and both Simple and Complex track workflows.

For the high-level overview, input/output contract, and track routing logic, see the parent [SKILL.md](../SKILL.md).

---

## Step 1: Check for Unresolved Q-Gate Findings (Detail)

**Purpose**: On re-entry (after Q-Gate or user review flagged issues), address unresolved findings before re-running the outline.

### Query Unresolved Findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate query --plan-id {plan_id} --phase 3-outline --resolution pending
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
   d. **Back-reference**: this rule originates from lesson `lesson-2026-05-18-10-001` and the post-PR review of `PR #407` (`reanchor-effort-presets-ladder`), where a literal-expansion fix to the `BALANCED` preset was not applied to `ECONOMIC` and `HIGH_END` until an automated review forced a loop-back iteration.
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --get \
  --field plan_source
```

**If `plan_source == recipe`**:

1. Read recipe metadata:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --get \
  --field recipe_key

python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --get \
  --field recipe_skill

```

**Built-in recipe only** (`recipe_key == "refactor-to-profile-standards"`): Read additional fields. Skip these for custom recipes — they are not set and will return `field_not_found` errors.

```bash
# Only read these if recipe_key == "refactor-to-profile-standards"
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --get \
  --field recipe_domain

python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --get \
  --field recipe_profile

python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --get \
  --field recipe_package_source
```

2. Resolve recipe to get `default_change_type`:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-recipe --recipe {recipe_key}
```

3. Set `change_type` from recipe's `default_change_type` (skip `manage-status:change-type-heuristic` and any LLM fallback):
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
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

5. Load the recipe skill directly:
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
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

**Purpose**: Before authoring any deliverable that adds capability to an existing skill, classify the target skill's design model so the proposed implementation extends (rather than contradicts) the existing model. The classification is recorded on the deliverable in a `**Design notes:**` block and is the input the q-gate validation agent's `architecture-mismatch-validator` (§2.17, see `plan-marshall/workflow/q-gate-validation.md`) consumes to surface design-model violations as blocking findings.

**When to apply**: this step fires for every deliverable that lists at least one `marketplace/bundles/{bundle}/skills/{skill}/**` path under `**Affected files:**`. Deliverables that touch only standards documentation in an existing skill (`standards/**/*.md`) ALSO count — design-intent classification applies to the standards body, not just executable code. Deliverables that do not touch existing skills (brand-new skill creation, docs-only outside a skill, non-marketplace changes) skip this step.

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

**Validator linkage**: the `architecture-mismatch-validator` in `plan-marshall/workflow/q-gate-validation.md` (§2.17 — added by deliverable 9 of this plan) parses the `**Design notes:**` block on every deliverable that touches an existing skill and emits an `architecture-mismatch` finding with `severity: blocking` when the block is absent, generic, or contradicts the skill's documented design model. Phase-3-outline's Step 11 auto-loops on blocking findings (see "Step 11: Q-Gate Verification" below), so a missing or contradictory `**Design notes:**` block forces a re-outline pass before phase transition.

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

**Allow-list**: Only two `conftest.py` files are permitted in this repository and MUST NOT be added to or duplicated by deliverables:
- `test/conftest.py` — top-level pytest configuration for the whole suite
- `test/adapters/conftest.py` — sys.path shim required by the adapters package

Any other `conftest.py` in an `**Affected files:**` list is a defect. Replace with `_fixtures.py` (or a similarly scoped helper name) and update any `Change per file:` text to describe explicit imports from the tests that consume it.

**Cross-references**:
- `plan-marshall:dev-general-module-testing` — testing methodology (AAA pattern, coverage, test organization) this rule supports
- `pm-dev-python:pytest-testing` — pytest framework standards including fixture discovery semantics that motivate the `conftest.py` restriction

#### Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Change-type workflow complete: {N} deliverables ({change_type})"
```

**If workflow fails**: HALT and return error. Do NOT fall back to grep/search.

### Step 10b: Self-Modifying Classification

**Purpose**: Classify each deliverable as self-modifying (touches plan-marshall runtime infrastructure) and surface the phasing decision before Q-Gate locks the outline. The classification rule, path heuristic, and phasing-rationale contract live in [`../../ref-workflow-architecture/standards/self-modifying-classification.md`](../../ref-workflow-architecture/standards/self-modifying-classification.md) — this step wires that standard into outline workflow.

**Activation**: Runs after Step 10 (Execute Change-Type Workflow and Write Solution) and BEFORE Step 11 (Q-Gate Verification). Applies to every deliverable in `solution_outline.md`, regardless of track (Simple or Complex) or change type.

#### Detection

For each deliverable, scan its `**Affected files:**` block for paths matching the path heuristic. The path list is the single source of truth in [`../../ref-workflow-architecture/standards/self-modifying-classification.md` § Path Heuristic](../../ref-workflow-architecture/standards/self-modifying-classification.md#path-heuristic) — do not duplicate the list inline; read it from the standard. Treat the standard as authoritative for both the path patterns and the per-pattern rationale.

A deliverable is **self-modifying + breaking** when ALL three predicates hold:

1. At least one affected path matches the heuristic from the standard, AND
2. The plan declares `compatibility: breaking` (read once for the whole plan from the solution outline header), AND
3. The deliverable's `Change per file:` or surrounding narrative contains hard-cutover language. The full keyword list is owned by the q-gate validator — see [plan-marshall/workflow/q-gate-validation.md § 2.16 Self-Modifying Phased-Rollout Validator](../../../agents/plan-marshall/workflow/q-gate-validation.md) Detection Logic step 2 for the canonical phrasing list (`remove ... entirely`, `delete the ...`, `drop the ...`, `retire the ...`, `no escape hatch`, `no transition window`, `zero-hit grep`, `zero hits`, `returns zero`, or equivalent applied to a public surface). Both the validator and this step consume the same list to keep outline-time and q-gate-time detection in lockstep.

#### Author Prompt (when all three hold)

When the predicate fires AND the deliverable does NOT already contain a `**Phasing Rationale:**` block, prompt the author via `AskUserQuestion`:

```yaml
question: |
  Deliverable {N} ({title}) is self-modifying and declares a breaking deletion/cutover.

  **Affected runtime path(s):** {matched paths}
  **Compatibility:** breaking
  **Hard-cutover signal:** {one-line — what the deliverable removes}

  Without a phasing strategy this combination historically descopes silently. How should the plan proceed?

header: "Self-Modifying"
options:
  - label: "Split into PLAN A + PLAN B"
    description: "Recommended. PLAN A ships only the additive surface; PLAN B (a follow-up plan) ships the deletion against the already-merged additive base. The current plan retains only additive deliverables; the deletion seeds a successor lesson via manage-lessons add."
  - label: "Document phasing rationale inline"
    description: "Single-plan path. Add a `**Phasing Rationale:**` block to deliverable {N} addressing all three points from self-modifying-classification.md (cache-sync ordering, verification-gate target, narrative consistency). Q-Gate validator §2.16 verifies the block content."
  - label: "Switch compatibility to additive"
    description: "Change the plan-level `compatibility:` from `breaking` to `deprecation`. The deliverable retains both surfaces with explicit deprecation markers; the hard-cutover language is dropped from the narrative."
multiSelect: false
```

#### Resolution Handling

| Option | Side Effect |
|--------|-------------|
| **Split into PLAN A + PLAN B** | Remove the deletion-bearing portion of the deliverable from `solution_outline.md` (or remove the entire deliverable when it is purely deletion). Capture the removed scope as a successor lesson via `manage-lessons add`. Re-emit the outline with only the additive scope. |
| **Document phasing rationale inline** | Insert a `**Phasing Rationale:**` block into the deliverable. The block MUST address the three points from `self-modifying-classification.md` § Phasing-Rationale Contract. Re-write the outline with the new block in place. |
| **Switch compatibility to additive** | Edit the solution outline header to set `compatibility: deprecation — Add deprecation markers to old code, provide migration path`. Strip hard-cutover language from the affected deliverable's narrative. The classification predicate no longer fires (compatibility is no longer `breaking`); Step 11 proceeds normally. |

Log the resolution to `decision.log`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-3-outline) Self-modifying classification fired for deliverable {N} ({title}); resolution: {chosen_option}"
```

When the predicate does NOT fire (deliverable is additive or matches the heuristic but is not breaking), no prompt is raised — proceed directly to Step 11.

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
| Self-Modifying Phased-Rollout Validator (§ 2.16) | `solution_outline.md` (each deliverable's Affected files + compatibility header + narrative), `self-modifying-classification.md` heuristic | `qgate-self-modifying-rollout` |

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
