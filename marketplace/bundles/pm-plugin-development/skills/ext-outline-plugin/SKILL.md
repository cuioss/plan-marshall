---
name: ext-outline-plugin
description: Outline extension skill for plugin development domain - discovery, analysis, deliverable creation
implements: pm-workflow:workflow-extension-api/standards/extensions/outline-extension.md
user-invocable: false
allowed-tools: Read, Bash, AskUserQuestion, Task
---

# Plugin Outline Extension

Domain-specific outline workflow for marketplace plugin development. Handles discovery, analysis, uncertainty resolution, and deliverable creation for Complex Track requests.

**Loaded by**: `pm-workflow:phase-3-outline` (Complex Track)

---

## Input

```toon
plan_id: {plan_id}
```

All other data read from sinks (references.toon, config.toon, request.md).

---

## Workflow Overview

```
Step 1: Load Context      → Read request, module_mapping, domains
Step 2: Discovery         → Spawn ext-outline-inventory-agent
Step 3: Determine Type    → Extract change_type from request
Step 4: Execute Workflow  → Route based on change_type (Create/Modify Flow)
Step 5: Write Solution    → Persist solution_outline.md
```

**Detailed workflow**: Load `standards/workflow.md` for Create Flow and Modify Flow logic.

---

## Step 1: Load Context

Read request (uses clarified_request if available):

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} \
  --section clarified_request
```

Read module_mapping (for bundle filtering hints):

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get \
  --plan-id {plan_id} --field module_mapping
```

Read domains:

```bash
python3 .plan/execute-script.py pm-workflow:manage-config:manage-config get \
  --plan-id {plan_id} --key domains
```

Log context:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-plugin-development:ext-outline-plugin) Context loaded: domains={domains}"
```

---

## Step 2: Discovery

Spawn ext-outline-inventory-agent to discover and filter marketplace components:

```
Task: pm-plugin-development:ext-outline-inventory-agent
  Input:
    plan_id: {plan_id}
    request_text: {request content from Step 1}
  Output:
    inventory_file: work/inventory_filtered.toon
    scope: affected_artifacts, bundle_scope
    counts: skills, commands, agents, total
```

The agent:
- Analyzes request to determine affected artifact types and bundle scope
- Runs `scan-marketplace-inventory` with appropriate filters
- Uses `--bundles` filter if module_mapping specifies specific bundles
- Persists inventory to `work/inventory_filtered.toon`
- Stores reference as `inventory_filtered` in references.toon

**Contract**: After agent returns, `work/inventory_filtered.toon` exists.

### Error Handling

**CRITICAL**: If agent fails due to API errors, **HALT immediately**.

```
IF agent returns API error (529, timeout, connection error):
  HALT with error:
    status: error
    error_type: api_unavailable
    message: "Discovery agent failed. Retry later."

  DO NOT:
    - Fall back to grep/search
    - Continue with partial data
```

---

## Step 3: Determine Change Type

Extract `change_type` from request:

| Request Pattern | change_type |
|-----------------|-------------|
| "add", "create", "new" | create |
| "fix", "update" (localized) | modify |
| "rename", "migrate" | migrate |
| "refactor", "restructure" | refactor |

Log decision:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-plugin-development:ext-outline-plugin) Change type: {change_type}"
```

### Validation

```
IF affected_artifacts is empty:
  ERROR: "No artifacts affected - clarify request"
```

---

## Step 4: Execute Workflow

Load detailed workflow:

```
Read standards/workflow.md
```

The workflow routes based on `change_type`:

| change_type | Flow | Description |
|-------------|------|-------------|
| create | Create Flow | Build deliverables directly (files don't exist) |
| modify, migrate, refactor | Modify Flow | Analysis → Uncertainty → Grouping → Deliverables |

### Create Flow Summary

- No analysis needed (files don't exist yet)
- Build deliverables directly from request
- One deliverable per component to create

### Modify Flow Summary

- Load persisted inventory
- Spawn analysis agents per bundle/type
- Persist assessments to `artifacts/assessments.jsonl`
- Resolve uncertainties via AskUserQuestion
- Group into deliverables
- Write solution_outline.md

---

## Step 5: Write Solution Outline

After deliverables are built, write solution_outline.md:

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline write \
  --plan-id {plan_id} --deliverables "{deliverables_json}"
```

Log completion:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-plugin-development:ext-outline-plugin) Complete: {N} deliverables"
```

---

## Output

Return minimal status - all data in sinks:

```toon
status: success
plan_id: {plan_id}
deliverable_count: {N}
```

---

## Sinks Written

| Sink | Content | API |
|------|---------|-----|
| `work/inventory_filtered.toon` | Filtered marketplace inventory | via ext-outline-inventory-agent |
| `artifacts/assessments.jsonl` | Component assessments (Modify Flow) | `artifact_store assessment add` |
| `logs/decision.log` | All decisions | `manage-log decision` |
| `solution_outline.md` | Final deliverables | `manage-solution-outline write` |

---

## Impact Analysis (Optional)

**Condition**: Run if inventory has < 20 files AND change_type is "modify", "migrate", or "refactor".

**Purpose**: Discover components that depend on affected components.

```bash
python3 .plan/execute-script.py pm-plugin-development:ext-outline-plugin:filter-inventory \
  impact-analysis --plan-id {plan_id}
```

For detailed rules, see `standards/impact-analysis.md`.

---

## Uncertainty Resolution

**Trigger**: Run if `uncertain > 0` after analysis.

**Purpose**: Convert UNCERTAIN findings to CERTAIN through user clarification.

### Grouping Patterns

| Pattern | Question Type |
|---------|---------------|
| JSON in workflow context vs output spec | "Should workflow-context JSON be included?" |
| Script output documentation vs skill output | "Should documented script outputs count?" |
| Example format vs actual output format | "Should example formats be treated as outputs?" |

### Resolution Application

1. Query UNCERTAIN assessments:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:artifact_store \
  assessment query {plan_id} --certainty UNCERTAIN
```

2. Use AskUserQuestion with specific file examples
3. Log resolutions as new assessments:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:artifact_store \
  assessment add {plan_id} {file_path} {new_certainty} 85 \
  --agent pm-plugin-development:ext-outline-plugin \
  --detail "User clarified: {user_choice}" --evidence "From: {original_hash_id}"
```

4. Store clarifications in request.md:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents \
  request clarify \
  --plan-id {plan_id} \
  --clarifications "{formatted Q&A}" \
  --clarified-request "{synthesized request}"
```

---

## Error Handling

**CRITICAL**: If any operation fails, HALT immediately.

| Failure | Action |
|---------|--------|
| Discovery fails | `status: error, error_type: discovery_failed` |
| Analysis agent fails | `status: error, error_type: api_unavailable` |
| Write fails | `status: error, error_type: write_failed` |

**DO NOT**: Fall back to grep/search, skip failed bundles, continue with partial data.

---

## Conditional Standards

| Condition | Standard |
|-----------|----------|
| Deliverable involves Python scripts | `standards/script-verification.md` |
| Impact analysis enabled | `standards/impact-analysis.md` |
| Component analysis details | `standards/component-analysis-contract.md` |

---

## Related

- [workflow.md](standards/workflow.md) - Create Flow and Modify Flow details
- [outline-extension.md](../../../pm-workflow/skills/workflow-extension-api/standards/extensions/outline-extension.md) - Contract this skill implements
- [component-analysis-contract.md](standards/component-analysis-contract.md) - Analysis agent contract
