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

The Assessment Protocol (SKILL.md) already ran the inventory-assessment-agent which persisted results. Read the filtered inventory:

```bash
# Check reference exists
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references get \
  --plan-id {plan_id} \
  --field inventory_filtered
```

If `inventory_filtered` is not set, ERROR: "Assessment incomplete - inventory_filtered not persisted"

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

Analysis is split into two phases: **script filtering** (deterministic) and **agent analysis** (LLM reasoning).

**Step 3a: Extract Bundles**

Parse `inventory_filtered.toon` to get unique bundles:
```python
bundles = set()
for component_type in ['skills', 'commands', 'agents']:
    for path in inventory.get(component_type, []):
        # path: marketplace/bundles/{bundle}/...
        bundle = path.split('/')[2]
        bundles.add(bundle)
```

**Step 3b: Filter by Bundle (Script)**

For each bundle × component_type combination, run the filter script:

```bash
python3 .plan/execute-script.py pm-plugin-development:ext-outline-plugin:filter-inventory filter \
  --plan-id {plan_id} --bundle {bundle} --component-type {type}
```

**Output** (TOON):
```toon
status: success
bundle: pm-dev-java
component_type: skills
file_count: 17
files[17]:
  marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md
  ...
```

Skip if `file_count: 0`.

**Step 3c: Spawn Analysis Agents with Explicit File Sections**

For each bundle × component_type with files, build an explicit prompt with numbered file sections. Each file gets its own section with a mandatory logging command.

**Build Agent Prompt Pattern**:

For each file from the filter script output (Step 3b), generate a numbered section:

```markdown
## Files to Analyze

Request: {request_text}

Process these files IN ORDER. For EACH file, you MUST:
1. Read the file
2. Analyze it against the request
3. Assess confidence (0-100%) and determine certainty gate
4. Execute the logging bash command IMMEDIATELY (before next file)
5. Track counts for final summary

### File 1: {file_path_1}

**1a. Analyze**: Read and analyze against request. Assess confidence and determine certainty:
- confidence >= 80% AND matches criteria → CERTAIN_INCLUDE
- confidence >= 80% AND doesn't match → CERTAIN_EXCLUDE
- confidence < 80% → UNCERTAIN

**1b. Log (EXECUTE IMMEDIATELY)**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:manage-artifacts \
  assessment add {plan_id} {file_path_1} {CERTAINTY} {CONFIDENCE} \
  --agent {agent_name} --detail "{your_reasoning}" --evidence "{your_evidence}"
```

### File 2: {file_path_2}

**2a. Analyze**: Read and analyze against request. Assess confidence and determine certainty.

**2b. Log (EXECUTE IMMEDIATELY)**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:manage-artifacts \
  assessment add {plan_id} {file_path_2} {CERTAINTY} {CONFIDENCE} \
  --agent {agent_name} --detail "{your_reasoning}" --evidence "{your_evidence}"
```

[...continue for all files...]
```

**Note**: Hash IDs are automatically generated by the logging system from the message content. Agents do not need to compute or include hashes.

**Spawn Pattern**:

```
FOR each bundle where filter returned file_count > 0:
  IF has skills:
    Task: pm-plugin-development:skill-analysis-agent
      Input:
        plan_id: {plan_id}
        request_text: {request text from Step 2}
        files_prompt: {generated prompt with explicit file sections}

  IF has commands:
    Task: pm-plugin-development:command-analysis-agent
      Input:
        plan_id: {plan_id}
        request_text: {request text from Step 2}
        files_prompt: {generated prompt with explicit file sections}

  IF has agents:
    Task: pm-plugin-development:agent-analysis-agent
      Input:
        plan_id: {plan_id}
        request_text: {request text from Step 2}
        files_prompt: {generated prompt with explicit file sections}
```

**IMPORTANT**: Launch all agents in a SINGLE message for true parallelism.

**Agent Responsibility**: Each agent receives explicit numbered file sections from the parent workflow. For each section, the agent reads the file, analyzes it, executes the logging command, and records the finding. The explicit numbered sections with bash commands ensure logging cannot be skipped.

**Step 3d: Error Handling**

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

Collect summary counts from each agent (detailed assessments in assessments.jsonl):

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

**Note**: Agents return summary counts; detailed assessments with reasoning are in assessments.jsonl.

### Step 4a: Resolve Uncertainties

**Trigger**: Run if `uncertain > 0` from Step 4 aggregation.

**Purpose**: Convert UNCERTAIN assessments to CERTAIN through user clarification.

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

For each user answer, update affected assessments:

```python
for assessment in group_assessments:
    if user_chose_exclude:
        new_certainty = "CERTAIN_EXCLUDE"
    else:
        new_certainty = "CERTAIN_INCLUDE"

    # Log new assessment with resolution
    log_assessment(assessment.file_path, new_certainty, 85, user_choice)
```

Log each resolution as a new assessment:
```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:manage-artifacts \
  assessment add {plan_id} {file_path} {new_certainty} 85 \
  --agent pm-plugin-development:ext-outline-plugin \
  --detail "User clarified: {user_choice}" --evidence "From: {original_hash_id}"
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

### Step 4b: Q-Gate Validation (Optional Final Safety Net)

**Trigger**: Run after uncertainty resolution, if `certain_include > 0`.

**Purpose**: Validate remaining CERTAIN_INCLUDE assessments to catch false positives that uncertainty resolution didn't cover.

#### Spawn Q-Gate Agent

```
Task: pm-workflow:q-gate-validation-agent
  Input:
    plan_id: {plan_id}
    domains: {domains from config.toon}
  Output:
    confirmed_count: Files passing validation
    filtered_count: False positives caught
    assessments_validated: Count of validated assessments
```

#### Process Results

The agent validates each CERTAIN_INCLUDE assessment and logs to decision.log:
- `CONFIRMED`: Include in affected_files
- `FILTERED`: Exclude (false positive)

Update counts after Q-Gate:
```
final_affected = confirmed_count
false_positives = filtered_count
```

#### Error Handling

**CRITICAL**: If Q-Gate agent fails, **HALT the workflow** - do not proceed with potentially incorrect affected_files.

### Step 4c: Verify Assessment Logging

Each analysis agent logs its own assessments during execution. The parent workflow verifies the audit trail exists.

**Validation**: After agents complete, verify assessments.jsonl has entries:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:manage-artifacts \
  assessment query {plan_id}
```

Check that total_count matches expected number of analyzed files.

Expected assessment types:
1. Analysis assessments: certainty in {CERTAIN_INCLUDE, CERTAIN_EXCLUDE, UNCERTAIN}
2. Resolution assessments (if any uncertainties resolved): confidence 85%, detail starts with "User clarified"

If count mismatches, agent execution failed to log properly.

### Step 5: Link Affected Files

Read CERTAIN_INCLUDE assessments from assessments.jsonl and persist for execute phase:

```bash
# Read assessments with certainty=CERTAIN_INCLUDE
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:manage-artifacts \
  assessment query {plan_id} --certainty CERTAIN_INCLUDE
```

Extract `file_paths` from the output, then persist:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references add-list \
  --plan-id {plan_id} \
  --field affected_files \
  --values "{comma-separated-file_paths-from-CERTAIN_INCLUDE}"
```

**Note**: UNCERTAIN assessments require user clarification before inclusion. See Uncertainty Resolution (Part 1d in plan).

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
- Command: `/pm-plugin-development:plugin-doctor --component {path}`
- Criteria: No quality issues detected

**Success Criteria:**
- {Specific criterion 1}
- {Specific criterion 2}
```

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
