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
5. For other finding types: address by revising deliverables, adjusting scope, or removing false positives
5. Resolve:
```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate resolve --plan-id {plan_id} --hash-id {hash_id} --resolution taken_into_account --phase 3-outline \
  --detail "{what was done to address this finding}"
```
6. Log resolution:
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

3. Set `change_type` from recipe's `default_change_type` (skip detect-change-type-agent):
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

```
Task: plan-marshall:detect-change-type-agent
  Input:
    plan_id: {plan_id}
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

**Resolve verification command** for each deliverable before writing:
```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command compile --name {module} \
  --trace-plan-id {plan_id}
```
Use the returned `executable` value as the Verification Command. Both Command and Criteria are mandatory — do NOT omit. If architecture has no `compile` command, use the most specific available command (e.g., `verify`, `quality-gate`) or flag for user decision.

#### Log Deliverable Creation

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Created deliverable for {target}"
```

### Step 8: Simple Q-Gate

**Purpose**: Lightweight verification for simple track.

#### Verify Deliverables

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
  resolve-outline-skill --domain {domain} --trace-plan-id {plan_id}
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

### Step 10: Execute Change-Type Workflow and Write Solution

**Purpose**: Execute the loaded change-type instructions, resolve verification commands, and write the solution outline.

#### 10a: Execute Discovery and Analysis

Follow the loaded change-type instructions from Step 9b. These instructions define:
- Discovery approach (inventory scan, targeted search, direct mapping)
- Analysis logic (component assessment, scope determination)
- Deliverable structure (type-specific metadata and sections)

#### 10b: Resolve Verification Commands

For each deliverable, resolve verification commands from architecture:

```bash
# Build/compile verification
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command compile --name {module} \
  --trace-plan-id {plan_id}

# Test verification (for deliverables with module_testing profile)
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command module-tests --name {module} \
  --trace-plan-id {plan_id}
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

#### Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Change-type workflow complete: {N} deliverables ({change_type})"
```

**If workflow fails**: HALT and return error. Do NOT fall back to grep/search.

### Step 11: Q-Gate Verification

**Purpose**: Verify skill output meets quality standards.

#### Spawn Q-Gate Agent

```
Task: plan-marshall:q-gate-validation-agent
  Input:
    plan_id: {plan_id}
```

**Q-Gate reads from**:
- `solution_outline.md` (written by domain skill)
- `artifacts/assessments.jsonl` (written by domain skill)
- `request.md` (clarified_request or body)

**Q-Gate verifies**:
- Each deliverable fulfills request intent
- Deliverables respect architecture constraints
- No false positives (files that shouldn't be changed)
- No missing coverage (files that should be changed but aren't)

**Q-Gate writes**:
- `artifacts/findings.jsonl` - Any triage findings
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
