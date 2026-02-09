---
name: ext-outline-workflow
description: Shared workflow steps and verification knowledge for plugin development outline agents
user-invocable: false
allowed-tools: Read
---

# Plugin Development Outline Workflow

Shared workflow steps for the 4 `change-{type}-outline-agent` agents. Each agent loads this skill and only documents its unique discovery/analysis logic.

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
  --plan-id {plan_id} --dir work --trace-plan-id {plan_id}

python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} \
  --resource-types {component_types} \
  --bundles {bundle_scope} \
  --include-tests \
  --full \
  --output {work_dir_path}/inventory_raw.toon
```

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
| `**Metadata:**` with change_type, execution_mode, domain, module, depends | Present and valid |
| `**Profiles:**` | At least one profile listed |
| `**Affected files:**` | Explicit paths, no wildcards, no glob patterns |
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

| Deliverable Scope | Verification Pattern |
|-------------------|---------------------|
| Single component | Plugin-doctor for specific component type |
| Single test file | `./pw module-tests {bundle}` |
| Multiple components in one bundle | `./pw verify {bundle}` for final deliverable |
| Cross-bundle changes | `./pw verify {bundle}` per affected bundle |
| Plugin.json registration | Plugin-doctor for the registered component |

### Deliverable Verification Template

```markdown
**Verification:**
- Command: `/pm-plugin-development:plugin-doctor scope={component_type}s {component_type}-name={name}`
- Criteria: No errors, structure compliant
```

## Write Solution Outline

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

{deliverables}
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
- Include plugin-doctor verification commands (see Verification Commands above)
- Return structured TOON output
- Every deliverable MUST include ALL required fields from deliverable-contract.md
