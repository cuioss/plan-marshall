# Plugin Outline Workflow

Unified workflow for plugin development outline phase. Routes based on change_type, not scope size.

## Critical Requirement

Deliverables MUST contain explicit file paths. A deliverable that says "update all X" without listing the files is INVALID.

## Inputs from Assessment

The Assessment Protocol (SKILL.md) provides these inputs:

| Input | Source | Description |
|-------|--------|-------------|
| `change_type` | Assessment Step 2 | create, modify, migrate, refactor |
| `work/inventory_filtered.toon` | Plan directory | Persisted inventory with scope and file paths |

The `work/inventory_filtered.toon` file contains:
- `scope.affected_artifacts` - Component types to target
- `scope.bundle_scope` - Bundles to target (all or specific list)
- `inventory.skills`, `inventory.commands`, `inventory.agents` - File paths

## Workflow Routing

Route based on `change_type`:

```
IF change_type == "create":
  → Create Flow (files don't exist yet)
ELSE:  # modify, migrate, refactor
  → Modify Flow (discovery + analysis)
```

---

## Create Flow

For creating new components. No discovery needed because files don't exist yet.

### Step 1: Log Decision

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-plugin-development:ext-outline-plugin) Create flow: {affected_artifacts} in {bundle_scope}"
```

### Step 2: Build Deliverables

Create one deliverable per component to create. Use the deliverable template below.

**Execution Skills** (deliverables delegate to these):
- `pm-plugin-development:plugin-create` - For creating new components

---

## Modify Flow

For modifying, migrating, or refactoring existing components. Uses discovery and analysis.

### Step 1: Load Persisted Inventory

The Assessment Protocol (SKILL.md) already ran the ext-outline-inventory-agent which persisted results. Read the filtered inventory from the known location:

```bash
# Check inventory file exists
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files exists \
  --plan-id {plan_id} \
  --file work/inventory_filtered.toon
```

If file does not exist, ERROR: "Assessment incomplete - inventory_filtered not persisted"

```bash
# Read the inventory file
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files read \
  --plan-id {plan_id} \
  --file work/inventory_filtered.toon
```

Parse the TOON content to extract:
- `scope.affected_artifacts` - Component types
- `scope.bundle_scope` - Bundle filter (all or specific)
- `inventory.skills` - Skill file paths
- `inventory.commands` - Command file paths
- `inventory.agents` - Agent file paths

### Step 2: Load Request Text

Read the request text from `request.md` if not already loaded:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id}
```

Extract the request text - this will be passed directly to analysis agents for semantic reasoning.

**Log the analysis start**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-plugin-development:ext-outline-plugin) Starting semantic analysis
  request: \"{request_text}\""
```

### Step 3: Parallel Component Analysis

Analysis uses a single unified agent with component-type-specific context:
- `pm-plugin-development:ext-outline-component-agent` - analyzes all component types

The agent receives `component_type` as input and applies appropriate context for skills, agents, or commands.

**Step 3a: Extract Files by Component Type**

Parse `inventory_filtered.toon` to get file paths grouped by component type:

```python
skills_files = inventory.get('inventory', {}).get('skills', [])
commands_files = inventory.get('inventory', {}).get('commands', [])
agents_files = inventory.get('inventory', {}).get('agents', [])
tests_files = inventory.get('inventory', {}).get('tests', [])
```

Note: Content filtering (if configured) was already applied during discovery (Step 2 via ext-outline-inventory-agent).

**Step 3b: Spawn Analysis Agents with Explicit File Sections**

For each component_type with files, spawn one instance of `ext-outline-component-agent` with the component type and its file list. The agent builds explicit numbered sections internally.

**Spawn Pattern**:

```
FOR each component_type IN [skills, commands, agents]:
  IF component_type has files:
    Task: pm-plugin-development:ext-outline-component-agent
      Input:
        plan_id: {plan_id}
        component_type: {component_type}
        request_text: {request text from Step 2}
        files: {file paths for this component type}
```

**IMPORTANT**: Launch all agent instances in a SINGLE message for true parallelism.

**Agent Responsibility**: The component agent analyzes files against the request using component-type-specific context. For each file, the agent reads it, analyzes against request criteria, executes the logging command, and records the finding. The agent uses the logging command defined in its contract to persist assessments.

**Step 3c: Error Handling**

**CRITICAL**: If ANY analysis agent fails due to API errors, **HALT the workflow immediately**.

```
IF any agent returns API error (529, timeout, connection error):
  HALT with error:
    status: error
    error_type: api_unavailable
    message: "Analysis agent failed due to API error. Retry later."
    failed_agent: {agent_name}
    bundle: {bundle}

  DO NOT:
    - Fall back to grep/search
    - Skip the failed bundle
    - Continue with partial analysis
    - Attempt manual file inspection
```

**Rationale**: Semantic analysis requires LLM reasoning. Simple grep cannot distinguish output specs from config/input JSON, leading to false positives that corrupt downstream deliverables.

### Step 4: Aggregate and Validate

Collect summary counts from each agent (detailed assessments are in `artifacts/assessments.jsonl`):

```
total_analyzed = sum of all agent total_analyzed counts
certain_include = sum of all agent certain_include counts
certain_exclude = sum of all agent certain_exclude counts
uncertain = sum of all agent uncertain counts
```

**Validate completeness**:
```
expected_total = sum of all inventory files

IF total_analyzed != expected_total:
  ERROR: "Analysis incomplete: {total_analyzed}/{expected_total}"

IF certain_include + certain_exclude + uncertain != total_analyzed:
  ERROR: "Count mismatch in agent summaries"
```

**Note**: Agents return summary counts; detailed assessments with reasoning are in `artifacts/assessments.jsonl`.

### Step 4a: Resolve Uncertainties

**Trigger**: Run if `uncertain > 0` from Step 4 aggregation.

**Purpose**: Convert UNCERTAIN findings to CERTAIN through user clarification.

#### 4a.1: Read UNCERTAIN Assessments

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:manage-artifacts \
  assessment query {plan_id} --certainty UNCERTAIN
```

Parse the output to get list of uncertain assessments with:
- `hash_id`: Assessment identifier
- `file_path`: Component path
- `confidence`: Original confidence percentage
- `detail`: Reason for uncertainty

#### 4a.2: Group by Ambiguity Pattern

Group findings by similar uncertainty reasons:

| Ambiguity Pattern | Example |
|-------------------|---------|
| "JSON in workflow context" | manage-adr/SKILL.md, workflow-integration-ci/SKILL.md |
| "Output in examples section" | plugin-create/SKILL.md |
| "Script output documentation" | manage-logging/SKILL.md |

#### 4a.3: Ask Clarification Questions

For each ambiguity group, use AskUserQuestion:

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

Display specific examples with confidence levels to help user decide.

#### 4a.4: Apply Resolutions

For each user answer, update affected findings:

```python
for finding in group_findings:
    if user_chose_exclude:
        new_certainty = "CERTAIN_EXCLUDE"
    else:
        new_certainty = "CERTAIN_INCLUDE"

    # Log resolution
    log_resolution(finding.hash_id, finding.file_path,
                   finding.confidence, new_certainty, user_choice)
```

Log each resolution as new assessment:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:manage-artifacts \
  assessment add {plan_id} {file_path} {new_certainty} 85 \
  --agent pm-plugin-development:ext-outline-plugin \
  --detail "User clarified: {user_choice}" --evidence "From: {original_hash_id}"
```

Also log to decision.log for audit trail:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-plugin-development:ext-outline-plugin) User: {file_path} → {new_certainty}"
```

#### 4a.5: Store Clarifications

Write clarifications to request.md:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents \
  request clarify \
  --plan-id {plan_id} \
  --clarifications "{formatted Q&A pairs}" \
  --clarified-request "{synthesized scope statement}"
```

#### 4a.6: Update Counts

After resolution, recalculate:
```
certain_include = original_certain_include + resolved_to_include
certain_exclude = original_certain_exclude + resolved_to_exclude
uncertain = 0  # All resolved
```

### Step 4b: Verify Assessment Logging

Each analysis agent persists assessments during execution. The parent workflow verifies the data exists.

**Validation**: After agents complete, verify assessments.jsonl has entries:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:manage-artifacts \
  assessment query {plan_id}
```

Check that assessments.jsonl contains:
1. Assessment entries for each analyzed file
2. Resolution entries for each uncertainty resolved (if any)

If entries are missing, agent execution failed to persist properly.

### Step 5: Link Affected Files

Query CERTAIN_INCLUDE assessments and persist for execute phase:

```bash
# Query assessments with certainty=CERTAIN_INCLUDE
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:manage-artifacts \
  assessment query {plan_id} --certainty CERTAIN_INCLUDE
```

Then persist:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references add-list \
  --plan-id {plan_id} \
  --field affected_files \
  --values "{comma-separated-paths-from-CERTAIN_INCLUDE}"
```

**Note**: UNCERTAIN assessments require user clarification before inclusion. See Uncertainty Resolution (Step 4a).

### Step 5.5: Compute Deliverable Dependencies (if available)

Check if dependency analysis was performed:

```bash
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files exists \
  --plan-id {plan_id} \
  --file work/dependency_analysis.toon
```

Parse the TOON output and check `exists: true/false` to determine if the file is present.

If `exists: true`, read it to determine deliverable ordering:

```bash
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files read \
  --plan-id {plan_id} \
  --file work/dependency_analysis.toon
```

**Assign `depends:` field**:
- Components with no dependencies in scope: `depends: none`
- Components depending on earlier deliverables: `depends: N` (deliverable number)

**Ordering Principle**: Primary affected components should be processed before their dependents. When a dependent component references a primary component, the dependent's deliverable should have `depends: N` where N is the primary's deliverable number.

### Step 6: Build Deliverables

Create deliverables from affected files, grouped by bundle (or ~5-8 files per deliverable).

**Execution Skills** (deliverables delegate to these):
- `pm-plugin-development:plugin-maintain` - For modifying existing components

### Step 6.5: Validate Deliverable Verification

**MANDATORY**: Before proceeding, validate each deliverable has proper verification.

For each deliverable:
1. Check that Verification section includes `/plugin-doctor` command
2. If missing: **ERROR** - "Deliverable {N} missing required plugin-doctor verification"

```
FOR each deliverable:
  IF verification.commands does NOT contain pattern "/plugin-doctor":
    HALT with error:
      status: error
      error_type: missing_verification
      message: "Deliverable {N} missing required plugin-doctor verification"
      deliverable: {deliverable_title}

  # Ensure path matches affected files
  IF plugin-doctor path does NOT match any affected_file:
    WARN: "plugin-doctor path should reference affected component paths"
```

**Note**: After this step completes, return to SKILL.md Step 5 which writes solution_outline.md.

---

## Deliverable Template

```markdown
### {N}. {Action Verb} {Component Type}: {Name/Bundle}

**Metadata:**
- change_type: {create|modify|migrate|refactor}
- execution_mode: automated
- domain: plan-marshall-plugin-dev
- module: {bundle-name}
- depends: none

**Profiles:**
- implementation

**Affected files:**
- `{explicit/path/to/file1.md}`
- `{explicit/path/to/file2.md}`

**Change per file:** {What will be created or modified}

**Verification:**
- Command: `/pm-plugin-development:plugin-doctor --component {affected_path}` (REQUIRED for each affected component)
- Command: {additional domain-specific verification} (optional)
- Criteria: No plugin-doctor quality issues, {additional criteria}

**Success Criteria:**
- {Specific criterion 1}
- {Specific criterion 2}
```

### Verification Requirements

**MANDATORY**: Every deliverable MUST include `/plugin-doctor` verification for each affected plugin component.

| Component Type | Required Verification Command |
|----------------|------------------------------|
| Skills | `/pm-plugin-development:plugin-doctor --component marketplace/bundles/{bundle}/skills/{skill}/` |
| Agents | `/pm-plugin-development:plugin-doctor --component marketplace/bundles/{bundle}/agents/{agent}.md` |
| Commands | `/pm-plugin-development:plugin-doctor --component marketplace/bundles/{bundle}/commands/{command}.md` |

Additional domain-specific checks (grep for patterns, format validation) may supplement but NEVER replace plugin-doctor.

### Field Reference

| Field | Valid Values |
|-------|--------------|
| `change_type` | create, modify, migrate, refactor |
| `execution_mode` | automated, manual, mixed |
| `domain` | plan-marshall-plugin-dev |
| `module` | Bundle name (e.g., pm-dev-java, pm-workflow) |
| `depends` | none, or deliverable number(s) |
| `**Profiles:**` | Block with: implementation, testing |

---

## Decomposition Patterns

| Request Pattern | Typical Deliverables |
|-----------------|----------------------|
| "Add new skill" | 1. Create SKILL.md 2. Create standards 3. Update plugin.json |
| "Add new command" | 1. Create command.md 2. Update plugin.json |
| "Rename notation X to Y" | 1-N. Update each affected component |
| "Change output format" | 1-N. Update each producer/consumer |
| "Migrate to new API" | 1-N. Migrate each caller |
