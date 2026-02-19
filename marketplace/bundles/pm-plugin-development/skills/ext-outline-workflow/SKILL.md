---
name: ext-outline-workflow
description: Shared workflow steps and verification knowledge for plugin development outline, loaded by outline-change-type skill
user-invocable: false
allowed-tools: Read
---

# Plugin Development Outline Workflow

Shared workflow steps for plugin development outline, loaded by the `outline-change-type` skill when the domain is `plan-marshall-plugin-dev`. Change-type-specific instructions are in `standards/change-{type}.md`.

## Context Loading

Read request, domains, and compatibility:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} \
  --section clarified_request

python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get \
  --plan-id {plan_id} --field domains

python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-2-refine get --field compatibility --trace-plan-id {plan_id}
```

Derive `compatibility_description` from the compatibility value.

Log context:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "({agent_name}) Context loaded: compatibility={compatibility}"
```

## Inventory Scan

Create work directory and run full inventory scan:

```bash
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files mkdir \
  --plan-id {plan_id} --dir work
# Output includes: path: /absolute/path/to/.plan/plans/{plan_id}/work
# Use the returned `path` value as {work_dir_path} below

python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} \
  --resource-types {comma_separated_types} \
  --bundles {bundle_scope} \
  --include-tests \
  --full \
  --output {work_dir_path}/inventory_raw.toon
```

**Important**: `{work_dir_path}` is the `path` value returned by the `mkdir` command above. Do NOT hardcode the path.

**Important**: `--resource-types` takes a **comma-separated** string (e.g., `skills,agents,commands`). Do NOT use spaces between types.

Omit `--bundles` only if scanning all bundles.

Read and extract file paths:

```bash
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files read \
  --plan-id {plan_id} --file work/inventory_raw.toon --trace-plan-id {plan_id}
```

Path conventions:
- **Skills**: `{bundle_path}/skills/{skill_name}/SKILL.md`
- **Commands**: `{bundle_path}/commands/{command_name}.md`
- **Agents**: `{bundle_path}/agents/{agent_name}.md`
- **Tests**: Use `path` field from inventory directly

## Assessment Pattern

### Clear stale assessments

```bash
python3 .plan/execute-script.py pm-workflow:manage-assessments:manage-assessments \
  clear --plan-id {plan_id} --agent {agent_name}
```

### Log assessment per file

```bash
python3 .plan/execute-script.py pm-workflow:manage-assessments:manage-assessments \
  add --plan-id {plan_id} --file-path {file_path} --certainty {CERTAINTY} --confidence {CONFIDENCE} \
  --agent {agent_name} --detail "{reasoning}" --evidence "{evidence}"
```

Where:
- `CERTAINTY`: CERTAIN_INCLUDE, CERTAIN_EXCLUDE, or UNCERTAIN
- `CONFIDENCE`: 0-100

### Assessment Gate

**STOP** before proceeding. Verify assessments were persisted:

```bash
python3 .plan/execute-script.py pm-workflow:manage-assessments:manage-assessments \
  query --plan-id {plan_id}
```

Gate checks:
1. `total_count` MUST be > 0 — if zero, report failure
2. Compare against inventory `total_resources`
3. If `total_count < total_resources`: STOP — "Assessment incomplete: {total_count}/{total_resources}"

Log gate result:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "({agent_name}) Assessment gate: {total_count} assessments written"
```

## Uncertainty Resolution

Query UNCERTAIN assessments and ask user:

```bash
python3 .plan/execute-script.py pm-workflow:manage-assessments:manage-assessments \
  query --plan-id {plan_id} --certainty UNCERTAIN
```

Group by pattern and use AskUserQuestion. Log resolution:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "({agent_name}) Resolved {N} uncertainties: {decision}"
```

## Deliverable Validation

**MANDATORY** before writing solution_outline.md — verify EVERY deliverable has ALL 6 required sections (from deliverable-contract.md):

| Section | Check |
|---------|-------|
| `**Metadata:**` with change_type, execution_mode, domain, module, depends | Present and valid. `execution_mode` must be one of: `automated`, `manual`, `mixed` (NOTE: `verification` is a valid change_type but NOT a valid execution_mode) |
| `**Profiles:**` | At least one profile listed |
| `**Affected files:**` | Explicit paths, no wildcards, no glob patterns. **Every path MUST exist on disk** (verify with `ls`). Use paths from inventory scan — do NOT guess or construct paths from component names. |
| `**Change per file:**` | Entry for each affected file |
| `**Verification:**` | Both Command and Criteria present |
| `**Success Criteria:**` | At least one criterion |

If ANY section is missing, add it before proceeding.

## Verification Commands

### Component Verification (Plugin-Doctor)

| Component Type | Scope | Parameter | Full Command |
|----------------|-------|-----------|--------------|
| Skills | `scope=skills` | `skill-name={name}` | `/pm-plugin-development:plugin-doctor scope=skills skill-name={name}` |
| Agents | `scope=agents` | `agent-name={name}` | `/pm-plugin-development:plugin-doctor scope=agents agent-name={name}` |
| Commands | `scope=commands` | `command-name={name}` | `/pm-plugin-development:plugin-doctor scope=commands command-name={name}` |
| Scripts | `scope=scripts` | `script-name={name}` | `/pm-plugin-development:plugin-doctor scope=scripts script-name={name}` |

Parameter values: `{name}` is the component name without path or extension.

Common mistakes: Do NOT use `--component {path}`, file paths as scope parameters, or omit the scope parameter.

### Test and Bundle Verification

| Purpose | Command |
|---------|---------|
| Run module tests | `./pw module-tests {bundle}` |
| Full bundle verification | `./pw verify {bundle}` |

### Decision Guide

**Primary factor**: The deliverable's **Profiles** list determines verification. Since `phase-4-plan` copies verification verbatim to ALL tasks from a deliverable, choose the command that covers the most demanding profile.

**Profile-based priority** (highest wins):

| Profiles Include | Verification Command | Rationale |
|------------------|---------------------|-----------|
| `module_testing` | Resolve `module-tests` from architecture | Tests passing implicitly verifies implementation |
| `implementation` only (scripts) | Resolve `compile` from architecture | Type-check without running tests |
| `implementation` only (markdown) | Plugin-doctor for the component | Structural/standards check |
| `verification` only | Deliverable-specific command | As defined in deliverable |

**Scope-based secondary guidance** (when profile-based priority doesn't differentiate):

| Deliverable Scope | Verification Pattern |
|-------------------|---------------------|
| Single component (markdown only) | Plugin-doctor for specific component type |
| Single component (scripts + tests) | Resolve `module-tests` from architecture |
| Multiple components in one bundle | `./pw verify {bundle}` for final deliverable |
| Cross-bundle changes | `./pw verify {bundle}` per affected bundle |
| Plugin.json registration | Plugin-doctor for the registered component |

### Deliverable Verification Templates

**Markdown-only deliverable** (implementation profile, no tests):
```markdown
**Verification:**
- Command: `/pm-plugin-development:plugin-doctor scope={component_type}s {component_type}-name={name}`
- Criteria: No errors, structure compliant
```

**Script deliverable with tests** (implementation + module_testing profiles):
```markdown
**Verification:**
- Command: `{resolved module-tests command from architecture}`
- Criteria: All tests pass, no regressions
```

## Test Deliverable vs module_testing Profile

**CRITICAL**: Do NOT create a separate "update tests" or "consolidate tests" deliverable when individual deliverables already have `module_testing` in their Profiles block.

The 1:N profile mapping (deliverable-contract.md) means each deliverable with `module_testing` profile automatically generates a separate test task. Creating an additional test deliverable for the same test files causes **redundant tasks** that modify identical files.

| Scenario | Correct Approach |
|----------|-----------------|
| D1-D4 each have `Profiles: implementation, module_testing` | Do NOT add D5 "Update all tests" — D1-D4 already generate test tasks |
| Tests span multiple deliverables and need cross-cutting integration | Create a separate integration test deliverable (different test files) |
| A final verification-only deliverable (no file changes) | Use `change_type: verification` with `Profiles: verification` — this is NOT redundant |

**Anti-pattern**:
```
D1: Migrate component A (Profiles: implementation, module_testing)
D2: Migrate component B (Profiles: implementation, module_testing)
D3: Update tests for A and B  ← REDUNDANT — D1 and D2 already cover testing
```

**Correct pattern**:
```
D1: Migrate component A (Profiles: implementation, module_testing)
D2: Migrate component B (Profiles: implementation, module_testing)
D3: Verify bundle integrity (Profiles: verification)  ← OK — verification only, no file overlap
```

## Markdown vs Script Verification

Plugin development deliverables have different verification depending on content type:

| Deliverable Content | Profiles | Implementation Verification | Module_testing Verification |
|---------------------|----------|---------------------------|----------------------------|
| Markdown components (skills/agents/commands) | `implementation` only | plugin-doctor | N/A |
| Scripts without test files | `implementation` only | `plan-marshall:analyze-project-architecture:architecture resolve --command compile --name {module} --trace-plan-id {plan_id}` | N/A |
| Scripts with test files | `implementation`, `module_testing` | `plan-marshall:analyze-project-architecture:architecture resolve --command compile --name {module} --trace-plan-id {plan_id}` | `plan-marshall:analyze-project-architecture:architecture resolve --command module-tests --name {module} --trace-plan-id {plan_id}` |

Resolve commands from architecture (`plan-marshall:analyze-project-architecture:architecture`) — do NOT hardcode build tool invocations. Always pass `--trace-plan-id {plan_id}` for execution logging.

**Key rule**: Markdown-only deliverables never get `module_testing` — there are no tests to run. Only deliverables that create or modify Python/Bash test files should include the `module_testing` profile.

## Write Solution Outline

Use `write` on first entry (solution_outline.md does not exist yet).
Use `update` on re-entry (Q-Gate loop — solution_outline.md already exists).

**CRITICAL — Deliverable Heading Format**: Each deliverable MUST use exactly `### N. Title` (e.g., `### 1. Migrate component X`). The validation regex is `^### \d+\. .+$`. Any other heading format (e.g., `## Deliverable 1:`, `**1. Title**`, `### Deliverable 1`) will fail validation.

Check first:
```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline exists \
  --plan-id {plan_id}
```

If `exists: false`:
```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline write \
  --plan-id {plan_id} <<'EOF'
# Solution: {Title}

plan_id: {plan_id}
compatibility: {compatibility} — {compatibility_description}

## Summary

{2-3 sentence summary}

## Overview

{Concise description. Include ASCII diagram if helpful.}

## Deliverables

### 1. {First deliverable title}

**Metadata:**
- change_type: {analysis|feature|enhancement|bug_fix|tech_debt|verification}
- execution_mode: {automated|manual|mixed}
- domain: {single domain from config.domains}
- module: {module name from architecture}
- depends: {none|N|N,M}

**Profiles:**
- implementation
- {module_testing - only if this deliverable creates/modifies test files (e.g., pytest scripts)}

**Affected files:**
- `{explicit/path/to/file1.ext}`
- `{explicit/path/to/file2.ext}`

**Change per file:** {What changes in these files}

**Verification:**
- Command: `{resolved command from architecture}`
- Criteria: {success criteria}

**Success Criteria:**
- {criterion 1}
- {criterion 2}

### 2. {Second deliverable title}

{Same structure — ALL 6 sections above are MANDATORY for every deliverable}
EOF
```

If `exists: true`:
```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline update \
  --plan-id {plan_id} <<'EOF'
{updated solution document}
EOF
```

## Completion

Log completion and return TOON output:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "({agent_name}) Complete: {N} deliverables"
```

```toon
status: success
plan_id: {plan_id}
deliverable_count: {N}
change_type: {type}
domain: plan-marshall-plugin-dev
```

## Shared Constraints

- Access `.plan/` files ONLY via execute-script.py
- Log assessments to assessments.jsonl for Q-Gate verification
- Select verification commands using the profile-based priority (see Decision Guide above)
- Return structured TOON output
- Every deliverable MUST include ALL required fields from deliverable-contract.md
