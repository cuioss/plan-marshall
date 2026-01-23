---
name: ext-outline-plugin
description: Outline extension implementing protocol for plugin development domain
implements: pm-workflow:workflow-extension-api/standards/extensions/outline-extension.md
user-invocable: false
allowed-tools: Read
---

# Plugin Outline Extension

> Extension implementing outline protocol for plugin development domain.

Provides domain-specific knowledge for deliverable creation in marketplace plugin development tasks. Implements the outline extension protocol with defined sections that phase-2-outline calls explicitly.

## Domain Detection

This extension is relevant when:
1. `marketplace/bundles` directory exists
2. Request mentions "skill", "command", "agent", "bundle"
3. Files being modified are in `marketplace/bundles/*/` paths

---

## Assessment Protocol

**Called by**: phase-2-outline Step 3 (Assess Complexity)
**Purpose**: Determine which artifacts and bundles are affected, extract change_type

### Step 1: Spawn Inventory Assessment Agent

The assessment logic is implemented by the `inventory-assessment-agent`:

```
Task: pm-plugin-development:inventory-assessment-agent
  Input:
    plan_id: {plan_id}
    request_text: {request content from request.md}
  Output:
    inventory_file: work/inventory_filtered.toon
    scope: affected_artifacts, bundle_scope
    counts: skills, commands, agents, total
```

The agent:
- Analyzes request to determine affected artifact types and bundle scope
- Runs `scan-marketplace-inventory` with appropriate filters
- Converts skill directories to file paths
- **Persists** inventory to `work/inventory_filtered.toon` in plan directory
- **Stores reference** as `inventory_filtered` in references.toon

**Contract**: After agent returns, `work/inventory_filtered.toon` exists and is linked in references.

### Error Handling

**CRITICAL**: If the agent fails due to API errors (529 overload, timeout, etc.), **HALT the workflow immediately**.

```
IF agent returns API error (529, timeout, connection error):
  HALT with error:
    status: error
    error_type: api_unavailable
    message: "Assessment agent failed due to API error. Retry later."

  DO NOT:
    - Fall back to manual grep/search
    - Attempt simplified analysis
    - Continue with partial data
```

**Rationale**: Fallback approaches produce degraded output (false positives/negatives) that downstream phases cannot detect. Better to fail clearly than produce incorrect results.

### Step 2: Determine Change Type

After agent returns, determine `change_type` from request:

| Request Pattern | change_type |
|-----------------|-------------|
| "add", "create", "new" | create |
| "fix", "update" (localized) | modify |
| "rename", "migrate" | migrate |
| "refactor", "restructure" | refactor |

### Validation

```
IF affected_artifacts is empty:
  ERROR: "No artifacts affected - clarify request"
```

### Step 3: Impact Analysis (Optional)

**Condition**: Run if inventory has < 20 files AND change_type is "modify", "migrate", or "refactor".

**Purpose**: Discover components that directly depend on affected components (1 level only, no transitive chains).

#### 3.1: Convert Paths to Notations

Parse `work/inventory_filtered.toon` and convert file paths:
- `marketplace/bundles/{b}/skills/{s}/SKILL.md` → `{b}:{s}`
- `marketplace/bundles/{b}/commands/{c}.md` → `{b}:commands:{c}`
- `marketplace/bundles/{b}/agents/{a}.md` → `{b}:agents:{a}`

#### 3.2: Resolve and Expand (Single Script Call)

The script handles everything: resolves reverse dependencies, expands inventory, and writes results directly.

```bash
python3 .plan/execute-script.py pm-plugin-development:ext-outline-plugin:filter-inventory \
  impact-analysis --plan-id {plan_id}
```

The script:
1. Reads `work/inventory_filtered.toon` to get primary affected components
2. Converts file paths to component notations
3. Calls resolve-dependencies rdeps for each component
4. Collects unique direct dependents
5. Expands inventory with dependents
6. Writes `work/dependency_analysis.toon` with results
7. Logs decision to decision.log

**Output** (TOON):
```toon
status: success
primary_count: 5
dependents_found: 3
dependents_added: 2  # May be fewer if already in scope
```

**Rationale**: Single script call avoids routing data through context. For operations like renaming, not including dependents would break them - expansion is inherently necessary for correctness.

#### Error Handling

**CRITICAL**: If resolve-dependencies fails, **HALT the workflow immediately**.

```
IF resolve-dependencies returns error or fails:
  HALT with error:
    status: error
    error_type: dependency_resolution_failed
    message: "Impact analysis failed. Retry later."

  DO NOT:
    - Continue without dependency data
    - Fall back to skip impact analysis
    - Proceed with partial scope
```

**Rationale**: Consistent with existing ext-outline-plugin pattern - no workarounds, fail loudly.

### Conditional Standards

| Condition | Additional Standard |
|-----------|---------------------|
| Deliverable involves Python scripts | `standards/script-verification.md` |
| Impact analysis enabled | `standards/impact-analysis.md` |

---

## Workflow

**Called by**: phase-2-outline Step 4 (Execute Workflow)
**Purpose**: Create deliverables based on change_type

### Load Workflow

```
Read standards/workflow.md
```

The workflow routes based on `change_type`:
- **create**: Build deliverables directly (files don't exist yet)
- **modify/migrate/refactor**: Run analysis agents, then build deliverables

### Change Type Mappings

| change_type | execution_mode | Execution Skill |
|-------------|----------------|-----------------|
| create | automated | `pm-plugin-development:plugin-create` |
| modify | automated | `pm-plugin-development:plugin-maintain` |
| migrate | automated | `pm-plugin-development:plugin-maintain` |
| refactor | automated | `pm-plugin-development:plugin-maintain` |

### Grouping Strategy

| Scenario | Grouping |
|----------|----------|
| Creating components | One deliverable per component |
| Script changes | Include script + tests in same deliverable |
| Cross-bundle pattern change | One deliverable per bundle |
| Rename/migration | Group by logical unit |

### Verification Commands

- Components: `/pm-plugin-development:plugin-doctor --component {path}`
- Scripts: `./pw module-tests {bundle}`

---

## Uncertainty Resolution

**Called by**: workflow.md Step 4a (between analysis and aggregation)
**Purpose**: Resolve UNCERTAIN assessments through user clarification

### Uncertainty Grouping

Group UNCERTAIN assessments by ambiguity pattern:

| Pattern | Question Type |
|---------|---------------|
| JSON in workflow context vs output spec | "Should workflow-context JSON be included?" |
| Script output documentation vs skill output | "Should documented script outputs count as skill outputs?" |
| Example format vs actual output format | "Should example formats be treated as outputs?" |

### Question Templates

For each uncertainty group, use AskUserQuestion with specific examples:

```
AskUserQuestion:
  questions:
    - question: "Should files with JSON in workflow context be included?"
      header: "Scope"
      options:
        - label: "Exclude workflow JSON (Recommended)"
          description: "Only include explicit ## Output sections"
        - label: "Include all JSON"
          description: "Include any ```json block regardless of context"
      multiSelect: false
```

**Include actual file examples with confidence**:
```
Examples found:
- manage-adr/SKILL.md (45%): JSON in "## Create ADR" workflow step
- workflow-integration-ci/SKILL.md (52%): JSON in "## Fetch Comments" step
```

### Resolution Application

After user answers:

1. Read UNCERTAIN assessments from assessments.jsonl:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:manage-artifacts \
  assessment query {plan_id} --certainty UNCERTAIN
```

2. For each assessment matching the clarification:
   - If user chose exclusion: UNCERTAIN → CERTAIN_EXCLUDE
   - If user chose inclusion: UNCERTAIN → CERTAIN_INCLUDE

3. Log resolution as new assessment with reference to original:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:manage-artifacts \
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
