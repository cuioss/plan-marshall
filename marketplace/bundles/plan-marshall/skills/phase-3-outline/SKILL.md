---
name: phase-3-outline
description: Two-track solution outline creation - Simple Track for localized changes, Complex Track for codebase-wide discovery
user-invocable: false
---

# Phase Outline Skill

**Role**: Two-track workflow skill for creating solution outlines. Routes based on track selection from phase-2-refine.

**Prerequisite**: Request must be refined (phase-2-refine completed) with track field set.

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

## Workflow Overview

```
Step 2: Load Inputs → Step 3: Recipe Detection → Step 4: Detect Change Type → Step 5: Route by Track → {Simple: Steps 6-8 | Complex: Steps 9-11} → Step 12: Return
```

---

## Step 1: Check for Unresolved Q-Gate Findings

**Purpose**: On re-entry (after Q-Gate or user review flagged issues), address unresolved findings before re-running the outline.

Query pending findings for phase `3-outline`. For each finding: analyze context, verify file paths exist on disk, create assessments or update deliverables as needed, then resolve the finding with `taken_into_account`. Continue with normal Steps 2..12 after corrections are applied.

For detailed procedures (query commands, finding-type handling, resolution logging), see [`standards/outline-workflow-detail.md`](standards/outline-workflow-detail.md#step-1-check-for-unresolved-q-gate-findings-detail).

---

## Step 2: Load Inputs

**Purpose**: Load track, request, compatibility, and context from phase-2-refine output and sinks.

**Note**: This skill receives `track`, `track_reasoning`, `scope_estimate`, `compatibility`, and `compatibility_description` from the phase-2-refine return output. These values are passed as input parameters.

### Receive Track from Phase-2-Refine Output

The `track` value (simple | complex) is received from the phase-2-refine return output, not read from references.json.

**If track not provided in input**, extract from decision.log:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
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
  plan phase-2-refine get --field compatibility --trace-plan-id {plan_id}
```

Store as `compatibility` and derive `compatibility_description` from the value:
- `breaking` → "Clean-slate approach, no deprecation nor transitionary comments"
- `deprecation` → "Add deprecation markers to old code, provide migration path"
- `smart_and_ask` → "Assess impact and ask user when backward compatibility is uncertain"

### Log Context (to work.log - status, not decision)

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
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

Spawn `plan-marshall:detect-change-type-agent` which persists `change_type` to status.json metadata. After detection, apply post-check: if agent returned `analysis` but request contains action words (`fix`, `implement`, `improve`, `update`, `create`, `refactor`, `migrate`, `remove`, `restructure`), override to `enhancement` or `tech_debt` as appropriate.

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
| **7. Create Deliverables** | Map module_mapping to deliverables | Use deliverable template, resolve verification commands via `architecture resolve` |
| **8. Simple Q-Gate** | Lightweight verification | Check target existence + request alignment |

After Step 8, proceed to Step 12.

For detailed procedures (validation commands, deliverable template, verification resolution, Q-Gate checks), see [`standards/outline-workflow-detail.md`](standards/outline-workflow-detail.md#simple-track-procedures-steps-6-8).

---

## Complex Track (Steps 9-11)

For codebase-wide changes requiring discovery and analysis.

| Step | Purpose | Key Action |
|------|---------|------------|
| **9. Resolve Domain Skill** | Route to domain-specific or generic instructions | `resolve-outline-skill --domain {domain}`, then load `change-{change_type}.md` |
| **10. Execute Workflow** | Run discovery, analysis, write solution | Follow change-type instructions, resolve verification commands, write `solution_outline.md` |
| **11. Q-Gate Verification** | Full quality verification | Spawn `plan-marshall:q-gate-validation-agent`, auto-loop on pending findings |

**CRITICAL**: If Complex Track skill workflow fails, do NOT fall back to grep/search. Fail clearly.

For detailed procedures (skill resolution, change-type loading, solution writing, Q-Gate agent interaction), see [`standards/outline-workflow-detail.md`](standards/outline-workflow-detail.md#complex-track-procedures-steps-9-11).

---

## Step 12: Write Solution and Return

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
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (plan-marshall:phase-3-outline) Created solution_outline.md"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Complete: {N} deliverables, Q-Gate: {pass/fail}"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-3-outline) Outline phase complete - {N} deliverables, Q-Gate: {pass/fail}"
```

**Add visual separator** after END log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  separator --plan-id {plan_id} --type work
```

---

### Transition Phase

```bash
python3 .plan/execute-script.py plan-marshall:manage-lifecycle:manage-lifecycle transition \
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
```

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Track not set | Return `{status: error, message: "phase-2-refine incomplete - track not set"}` |
| Target not found (Simple) | Return error with invalid target |
| Change type not detected | Return `{status: error, message: "detect-change-type-agent failed to determine change type"}` |
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
- `plan-marshall:manage-status:manage_status` - Read/write change_type metadata
- `plan-marshall:manage-logging:manage-log` - Decision and work logging
- `plan-marshall:manage-config:manage-config` - Resolve outline skill, read compatibility
- `plan-marshall:manage-architecture:architecture` - Resolve verification commands
- `plan-marshall:manage-assessments:manage-assessments` - Log assessments (domain skills)

**Spawns** (Complex Track):
- `plan-marshall:detect-change-type-agent` (Step 4 - change type detection)
- `plan-marshall:q-gate-validation-agent` (Step 11 - Q-Gate verification)

**Loads Skills** (Recipe path):
- `{recipe_skill}` (Step 3 - recipe skill with input parameters, built-in or custom)

**Loads Skills** (Complex Track):
- Domain outline skill via `resolve-outline-skill` (Step 9a, e.g., `pm-plugin-development:ext-outline-workflow`)
- Change-type instructions from `standards/change-{change_type}.md` (Step 9b, generic fallback)

**Consumed By**:
- `plan-marshall:phase-4-plan` skill (reads deliverables for task creation)

---

## Related Documents

- [architecture-diagram.md](references/architecture-diagram.md) - Change-type routing architecture (normal plans)
- [recipe-flow.md](references/recipe-flow.md) - Recipe flow architecture (built-in and custom recipes)
- [change-types.md](../../ref-workflow-architecture/standards/change-types.md) - Change type vocabulary and agent routing
- [deliverable-contract.md](../../manage-solution-outline/standards/deliverable-contract.md) - Deliverable structure
- [workflow-architecture](../../ref-workflow-architecture) - Workflow architecture overview
- [outline-workflow-detail.md](standards/outline-workflow-detail.md) - Detailed track procedures (Q-Gate re-entry, recipe detection, change-type detection, Simple/Complex track steps)
