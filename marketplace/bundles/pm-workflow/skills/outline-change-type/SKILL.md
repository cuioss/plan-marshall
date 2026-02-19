---
name: outline-change-type
description: Common workflow for change-type outline creation with conditional routing by change_type and domain
user-invocable: false
allowed-tools: Read, Glob, Grep, Bash, AskUserQuestion
---

# Outline Change-Type Skill

Common workflow for creating solution outlines based on change_type. Routes to domain-specific or generic sub-skill instructions based on the detected change type and domain configuration.

**Loaded by**: `pm-workflow:solution-outline-agent` (inline execution, no separate agent spawn)

---

## Workflow

### Step 1: Read Change Type from Metadata

```bash
python3 .plan/execute-script.py pm-workflow:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --get \
  --field change_type
```

Store as `{change_type}`. If not set, STOP and return error.

### Step 2: Load Context (COMMON)

Read request:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} \
  --section clarified_request
```

Read domains:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get \
  --plan-id {plan_id} --field domains
```

Read compatibility:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-2-refine get --field compatibility --trace-plan-id {plan_id}
```

Derive `compatibility_description` from the compatibility value:
- `breaking` -> "Clean-slate approach, no deprecation nor transitionary comments"
- `deprecation` -> "Add deprecation markers to old code, provide migration path"
- `smart_and_ask` -> "Assess impact and ask user when backward compatibility is uncertain"

Read module mapping (optional):

```bash
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files exists \
  --plan-id {plan_id} --file work/module_mapping.toon
# If exists: true, read it:
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files read \
  --plan-id {plan_id} --file work/module_mapping.toon
```

Log context:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:outline-change-type) Context loaded: change_type={change_type}, compatibility={compatibility}"
```

### Step 3: Resolve Domain Skill

Resolve whether a domain provides a domain-specific outline skill:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
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

### Step 4: Load Change-Type Instructions

Based on Step 3 resolution:

**IF source == domain_specific** (domain has registered outline_skill):
1. Load the domain skill: `Skill: {resolved_skill}` (e.g., `Skill: pm-plugin-development:ext-outline-workflow`)
2. Log the loaded skill:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (pm-workflow:outline-change-type) Loaded domain skill: {resolved_skill}"
```
3. Read the domain-specific change-type instructions from the skill's standards directory. The file path is: `marketplace/bundles/{bundle}/skills/{skill_name}/standards/change-{change_type}.md`
4. Follow the instructions from that file for discovery, analysis, and deliverable creation

**IF source == generic** (no domain override):
1. Read the generic change-type instructions from this skill's own standards directory: read `standards/change-{change_type}.md` (relative to this skill)
2. Follow the instructions from that file for discovery, analysis, and deliverable creation

### Step 5: Execute Change-Type Workflow

Follow the loaded change-type instructions from Step 4. These instructions define:
- Discovery approach (inventory scan, targeted search, direct mapping)
- Analysis logic (component assessment, scope determination)
- Deliverable structure (type-specific metadata and sections)

### Step 6: Resolve Verification Commands (COMMON)

For each deliverable, resolve verification commands from architecture:

```bash
# Build/compile verification
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture \
  resolve --command compile --name {module} \
  --trace-plan-id {plan_id}

# Test verification (for deliverables with module_testing profile)
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture \
  resolve --command module-tests --name {module} \
  --trace-plan-id {plan_id}
```

**Available architecture commands**: `compile`, `test-compile`, `module-tests`, `quality-gate`, `verify`, `coverage`, `clean`. Do NOT use `test` (use `module-tests` instead).

Use the returned `executable` value as the Verification Command.

### Step 7: Write Solution Outline (COMMON)

Use `write` on first entry (solution_outline.md does not exist yet).
Use `update` on re-entry (Q-Gate loop — solution_outline.md already exists).

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
- change_type: {change_type}
- execution_mode: {automated|manual|mixed}
- domain: {domain}
- module: {module}
- depends: {none|N|N,M}

**Profiles:**
- implementation
- {module_testing - only if this deliverable creates/modifies test files}

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
EOF
```

If `exists: true`:
```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline update \
  --plan-id {plan_id} <<'EOF'
{updated solution document}
EOF
```

**CRITICAL — Deliverable Heading Format**: Each deliverable MUST use exactly `### N. Title` (e.g., `### 1. Migrate component X`). The validation regex is `^### \d+\. .+$`.

### Step 8: Log Completion and Return (COMMON)

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:outline-change-type) Complete: {N} deliverables ({change_type})"
```

Return TOON output:

```toon
status: success
plan_id: {plan_id}
deliverable_count: {N}
change_type: {change_type}
domain: {domain or "generic"}
```

---

## Constraints

### MUST NOT
- Use Read tool for `.plan/` files
- Skip verification command resolution
- Skip solution outline writing

### MUST DO
- Access `.plan/` files ONLY via execute-script.py
- Load domain skill when domain provides outline_skill
- Follow change-type sub-skill instructions exactly
- Return structured TOON output
- Every deliverable MUST include ALL 6 required sections (Metadata, Profiles, Affected files, Change per file, Verification, Success Criteria)

---

## Integration

**Invoked by**: `pm-workflow:solution-outline-agent` (inline execution during Complex Track)

**Script Notations** (use EXACTLY as shown):
- `pm-workflow:manage-plan-documents:manage-plan-documents` - Read request
- `pm-workflow:manage-references:manage-references` - Read domains
- `pm-workflow:manage-status:manage_status` - Read change_type metadata
- `pm-workflow:manage-files:manage-files` - Read module_mapping
- `pm-workflow:manage-solution-outline:manage-solution-outline` - Write solution document
- `pm-workflow:manage-assessments:manage-assessments` - Log assessments (domain skills)
- `plan-marshall:manage-plan-marshall-config:plan-marshall-config` - Resolve change-type skill, read compatibility
- `plan-marshall:manage-logging:manage-log` - Decision and work logging
- `plan-marshall:analyze-project-architecture:architecture` - Resolve verification commands
