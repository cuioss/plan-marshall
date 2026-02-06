---
name: phase-3-outline
description: Two-track solution outline creation - Simple Track for localized changes, Complex Track for codebase-wide discovery
user-invocable: false
allowed-tools: Read, Glob, Grep, Bash, Task, AskUserQuestion
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
Step 2: Load Inputs → Step 3: Detect Change Type → Step 4: Route by Track → {Simple: Steps 5-7 | Complex: Steps 8-11} → Step 13: Return
```

---

## Step 1: Check for Unresolved Q-Gate Findings

**Purpose**: On re-entry (after Q-Gate or user review flagged issues), address unresolved findings before re-running the outline.

### Query Unresolved Findings

```bash
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  qgate query --plan-id {plan_id} --phase 3-outline --resolution pending
```

### Address Each Finding

If unresolved findings exist (filtered_count > 0):

For each pending finding:
1. Analyze the finding in context of the request and existing outline
2. Address it (revise deliverables, adjust scope, remove false positives, etc.)
3. Resolve:
```bash
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  qgate resolve --plan-id {plan_id} --hash-id {hash_id} --resolution taken_into_account --phase 3-outline \
  --detail "{what was done to address this finding}"
```
4. Log resolution:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:phase-3-outline:qgate) Finding {hash_id} [{source}]: taken_into_account — {resolution_detail}"
```

Then continue with normal Steps 2..13 (phase re-runs with corrections applied).

If no unresolved findings: Continue with normal Steps 2..13 (first entry).

---

## Step 2: Load Inputs

**Purpose**: Load track, request, compatibility, and context from phase-2-refine output and sinks.

**Note**: This skill receives `track`, `track_reasoning`, `scope_estimate`, `compatibility`, and `compatibility_description` from the phase-2-refine return output. These values are passed as input parameters.

### Receive Track from Phase-2-Refine Output

The `track` value (simple | complex) is received from the phase-2-refine return output, not read from references.json.

**If track not provided in input**, extract from decision.log:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  read --plan-id {plan_id} --type decision | grep "(pm-workflow:phase-2-refine) Track:"
```
Parse the output to extract track value from: `(pm-workflow:phase-2-refine) Track: {track} - {reasoning}`

### Read Request

Read request (clarified_request falls back to original_input automatically):

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} \
  --section clarified_request
```

### Read Module Mapping

Read from work directory (persisted by phase-2-refine):

```bash
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files read \
  --plan-id {plan_id} \
  --file work/module_mapping.toon
```

### Read Domains

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get \
  --plan-id {plan_id} --field domains
```

### Receive Compatibility from Phase-2-Refine Output

The `compatibility` and `compatibility_description` values are received from the phase-2-refine return output.

**If compatibility not provided in input**, read from marshal.json:
```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-2-refine get --field compatibility --trace-plan-id {plan_id}
```

Store as `compatibility` and derive `compatibility_description` from the value:
- `breaking` → "Clean-slate approach, no deprecation nor transitionary comments"
- `deprecation` → "Add deprecation markers to old code, provide migration path"
- `smart_and_ask` → "Assess impact and ask user when backward compatibility is uncertain"

### Log Context (to work.log - status, not decision)

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (pm-workflow:phase-3-outline) Starting outline: track={track}, domains={domains}, compatibility={compatibility}"
```

---

## Step 3: Detect Change Type

**Purpose**: Determine the change type for agent routing.

### Spawn Detection Agent

```
Task: pm-workflow:detect-change-type-agent
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
python3 .plan/execute-script.py pm-workflow:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --get \
  --field change_type
```

### Log Detection

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:phase-3-outline) Change type: {change_type} (confidence: {confidence})"
```

---

## Step 4: Route by Track

Based on `track` from Step 2:

If track == simple → go to Step 5. If track == complex → go to Step 8.

---

<!-- ─── Simple Track (Steps 5-7) ─── -->
<!-- For localized changes where targets are already known from module_mapping. -->

## Step 5: Validate Targets (Simple Track)

**Purpose**: Verify target files/modules exist and match domain.

### Validate Target Files Exist

For each target in module_mapping:

```bash
# For file targets
ls -la {target_path}
```

If target doesn't exist, ERROR: "Target not found: {target}"

### Log Validation

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:phase-3-outline) Validated {N} targets in {domain}"
```

---

## Step 6: Create Deliverables (Simple Track)

**Purpose**: Direct mapping from module_mapping to deliverables.

### Build Deliverables from Module Mapping

For each entry in module_mapping:

1. Determine change_type from request (create, modify, migrate, refactor)
2. Determine execution_mode (automated)
3. Map domain from references.json
4. Use module from module_mapping

### Deliverable Structure

Use template from `pm-workflow:manage-solution-outline/templates/deliverable-template.md`:

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
- testing (if module has test infrastructure)

**Affected files:**
- `{explicit/path/to/file1}`
- `{explicit/path/to/file2}`

**Change per file:** {What will be created or modified}

**Verification:**
- Command: {verification command}
- Criteria: {success criteria}

**Success Criteria:**
- {Specific criterion 1}
- {Specific criterion 2}
```

### Log Deliverable Creation

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:phase-3-outline) Created deliverable for {target}"
```

---

## Step 7: Simple Q-Gate

**Purpose**: Lightweight verification for simple track.

### Verify Deliverables

For each deliverable:

1. **Target exists?** - Already validated in Step 5
2. **Deliverable aligns with request intent?** - Compare deliverable scope with request

### Log Q-Gate Result

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:phase-3-outline:qgate) Simple: Deliverable {N}: pass"
```

→ Go to Step 13.

---

<!-- ─── Complex Track (Steps 8-11) ─── -->
<!-- For codebase-wide changes requiring discovery and analysis. -->

## Step 8: Resolve Change-Type Agent (Complex Track)

**Purpose**: Find the appropriate agent for the detected change type and domain.

### Resolve Agent

For the primary domain in references.json:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-change-type-agent --domain {domain} --change-type {change_type} --trace-plan-id {plan_id}
```

**Output** (TOON):
```toon
status: success
domain: {domain}
change_type: {change_type}
agent: pm-plugin-development:change-feature-outline-agent  # or generic fallback
```

**Fallback**: If no domain-specific agent configured, use generic: `pm-workflow:change-{change_type}-agent`

### Log Resolution

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:phase-3-outline) Resolved agent: {agent_notation}"
```

---

## Step 9: Spawn Change-Type Agent (Complex Track)

**Purpose**: Spawn the resolved agent to handle discovery, analysis, and deliverable creation.

### Spawn Agent

```
Task: {resolved_agent_notation}
  Input:
    plan_id: {plan_id}
```

The agent handles the complete Complex Track workflow internally:
- Discovery (running inventory scan)
- Analysis (assessing each component from inventory)
- Persist assessments → assessments.jsonl
- Confirm uncertainties with user
- Group into deliverables
- Write solution_outline.md (must include `compatibility: {value} — {description}` in header metadata)

### Log Agent Spawn

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:phase-3-outline) Spawned {agent} for {domain}"
```

---

## Step 10: Agent Completion (Complex Track)

**Purpose**: Agent returns minimal status; data is in sinks.

### Agent Return Value

```toon
status: success
plan_id: {plan_id}
deliverable_count: {N}
change_type: {change_type}
```

### Log Agent Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:phase-3-outline) Agent complete: {deliverable_count} deliverables"
```

**If agent returns error**: HALT and return error.

---

## Step 11: Q-Gate Verification (Complex Track)

**Purpose**: Verify skill output meets quality standards.

### Spawn Q-Gate Agent

```
Task: pm-workflow:q-gate-validation-agent
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

### Q-Gate Return Value

```toon
status: success
plan_id: {plan_id}
deliverables_verified: {N}
passed: {count}
flagged: {count}
```

### Log Q-Gate Result

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:phase-3-outline:qgate) Full: {passed} passed, {flagged} flagged"
```

### Handle Q-Gate Findings

The Q-Gate agent writes findings to `qgate/3-outline.jsonl`. The phase returns `qgate_pending_count` to the orchestrator:

- If `qgate_pending_count == 0`: Continue to Step 13
- If `qgate_pending_count > 0`: Return with `qgate_pending_count` in output. The orchestrator auto-loops (re-enters this phase) until Q-Gate passes clean. No user prompt — Q-Gate findings are objective quality failures that must be self-corrected

→ Go to Step 13.

---

## Step 12: Generic Workflow (No Domain Agent)

For domains without domain-specific change-type agents, the generic agents in pm-workflow are used.
These generic agents (e.g., `pm-workflow:change-feature-agent`) provide baseline behavior.

### Read Module Mapping

Module mapping from phase-2-refine specifies target modules.

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get \
  --plan-id {plan_id} --field module_mapping
```

### Create Deliverables per Module

For each module in module_mapping:

1. Create deliverable with appropriate profile
2. No discovery needed - modules already identified in phase-2-refine

### Check Module Test Infrastructure

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture modules \
  --command module-tests \
  --trace-plan-id {plan_id}
```

Use result to determine if `testing` profile applies.

### Deliverable Structure

Use same template as Simple Track (Step 6).

### Write Solution Outline

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline write \
  --plan-id {plan_id} <<'EOF'
{solution document with deliverables}
EOF
```

### Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:phase-3-outline) Generic workflow: {N} deliverables"
```

→ Go to Step 13.

---

## Step 13: Write Solution and Return

---

### Write Solution Document (Simple Track only)

For Simple Track, write solution_outline.md:

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline write \
  --plan-id {plan_id} <<'EOF'
# Solution: {title}

plan_id: {plan_id}
compatibility: {compatibility} — {compatibility_description}

## Summary

{2-3 sentence summary of the solution}

## Overview

{ASCII diagram showing solution structure}

## Deliverables

{deliverables from Step 6}
EOF
```

**Note**: Complex Track - skill already wrote solution_outline.md in Step 9.

---

### Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (pm-workflow:phase-3-outline) Created solution_outline.md"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:phase-3-outline) Complete: {N} deliverables, Q-Gate: {pass/fail}"
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
| Agent not found | Fall back to generic: `pm-workflow:change-{change_type}-agent` |
| Agent fails (Complex) | Return error, do not fall back |
| Q-Gate fails | Return with `qgate_passed: false` and findings |
| Request not found | Return `{status: error, message: "Request not found"}` |

**CRITICAL**: If Complex Track agent fails, do NOT fall back to grep/search. Fail clearly.

---

## Integration

**Invoked by**: `pm-workflow:solution-outline-agent` (thin agent)

**Script Notations** (use EXACTLY as shown):
- `pm-workflow:manage-files:manage-files` - Read module_mapping from work/module_mapping.toon
- `pm-workflow:manage-plan-documents:manage-plan-documents` - Read request
- `pm-workflow:manage-references:manage-references` - Read domains
- `pm-workflow:manage-solution-outline:manage-solution-outline` - Write solution document
- `pm-workflow:manage-findings:manage-findings` - Q-Gate findings (qgate add/query/resolve)
- `pm-workflow:manage-status:manage_status` - Read/write change_type metadata
- `plan-marshall:manage-plan-marshall-config:plan-marshall-config` - Resolve change-type agent, read compatibility (fallback)
- `plan-marshall:manage-logging:manage-log` - Decision and work logging

**Spawns** (Complex Track):
- `pm-workflow:detect-change-type-agent` (Step 3 - change type detection)
- Change-type agent (e.g., `pm-plugin-development:change-feature-outline-agent` or `pm-workflow:change-feature-agent`)
- `pm-workflow:q-gate-validation-agent` (Q-Gate verification)

**Consumed By**:
- `pm-workflow:phase-4-plan` skill (reads deliverables for task creation)

---

## Related Documents

- [architecture-diagram.md](references/architecture-diagram.md) - Visual architecture overview (for human readers)
- [change-types.md](../../workflow-architecture/standards/change-types.md) - Change type vocabulary and agent routing
- [deliverable-contract.md](../../manage-solution-outline/standards/deliverable-contract.md) - Deliverable structure
- [workflow-architecture](../../workflow-architecture) - Workflow architecture overview
