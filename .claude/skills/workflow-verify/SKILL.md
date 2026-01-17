---
name: workflow-verify
description: Verify workflow outputs using hybrid script + LLM assessment
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
  - Skill
---

# Workflow Verify Skill

**EXECUTION MODE**: You are now executing this skill. DO NOT explain or summarize these instructions to the user. IMMEDIATELY begin the workflow below based on the subcommand.

Hybrid verification system for plan-marshall workflow outputs. Uses deterministic scripts for structural checks and LLM-as-judge for semantic assessment.

## Purpose

Verify that workflow outputs (solution_outline.md, references.toon, TASK-*.toon) are correct and complete. Classical assertions cannot work because LLM outputs vary in wording while semantic correctness matters.

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                    HYBRID VERIFICATION ENGINE                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Phase 1: Structural Checks (Script)                               │
│  - File existence via manage-* tools                               │
│  - TOON/MD syntax validation                                       │
│  - Required sections present                                       │
│  - Cross-references valid                                          │
│                        │                                           │
│                        ▼                                           │
│  Phase 2: Semantic Assessment (LLM-as-Judge)                       │
│  - Reads criteria from test case                                   │
│  - Compares actual vs golden reference                             │
│  - Scores: scope (0-100), completeness (0-100), quality (0-100)    │
│  - Explains reasoning for each score                               │
│                        │                                           │
│                        ▼                                           │
│  Phase 3: Assessment Report                                        │
│  - TOON structured results                                         │
│  - Markdown narrative report                                       │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## Critical Design Principle

**Use proper tool interfaces, NOT direct filesystem access.**

| DO | DON'T |
|----|-------|
| `manage-tasks list --plan-id X` | Read `.plan/plans/X/tasks/*.toon` directly |
| `manage-solution-outline list-deliverables` | Parse `solution_outline.md` directly |
| `manage-logging read --plan-id X` | Read `work.log` directly |
| `manage-config get-domains` | Parse `config.toon` directly |

**Rationale**: We're verifying workflow outputs through the same interfaces the workflow uses.

## Directory Structure

```
workflow-verification/                    # Test cases (version-controlled)
├── test-cases/
│   └── {test-id}/
│       ├── test-definition.toon         # Input, trigger, setup
│       ├── expected-artifacts.toon      # Expected files + standard refs
│       ├── criteria/
│       │   ├── semantic.md              # LLM-as-judge criteria
│       │   └── decision-quality.md      # Expected decisions
│       └── golden/
│           └── verified-result.md       # Expert-verified reference

.plan/temp/workflow-verification/         # Run results (gitignored, ephemeral)
└── {test-id}-{timestamp}/
    ├── actual-artifacts/                # Snapshot of output
    ├── assessment-results.toon          # Structured scores
    ├── assessment-detail.md             # Full narrative
    └── comparison-diff.md               # Actual vs Expected

.claude/skills/workflow-verify/          # Skill implementation
├── SKILL.md                             # This file
├── scripts/
│   ├── verify-structure.py              # Structural checks
│   └── collect-artifacts.py             # Artifact collection
├── standards/
│   ├── test-case-format.md              # Test case specification
│   ├── criteria-format.md               # Criteria authoring guide
│   └── scoring-guide.md                 # Scoring rubric
└── templates/
    ├── test-definition.toon             # Template for new test cases
    ├── expected-artifacts.toon          # Template for expected artifacts
    ├── semantic-criteria.md             # Template for semantic criteria
    └── assessment-results.toon          # Template for results
```

## Workflow Decision Tree

**MANDATORY**: Select workflow based on subcommand and execute IMMEDIATELY.

### If subcommand = "test"
→ **EXECUTE** Workflow 1: Test Workflow (execute trigger + verify)

### If subcommand = "verify" (with --plan-id)
→ **EXECUTE** Workflow 2: Verify Plan (verify existing plan)

### If subcommand = "create"
→ **EXECUTE** Workflow 3: Create Test Case

### If subcommand = "list"
→ **EXECUTE** Workflow 4: List Test Cases

---

## Workflow 1: Test Workflow

Execute the trigger from test-definition, then verify the output. Full automated test.

### Parameters
- `--test-id` (required): Test case identifier

### Step 1: Load Test Case

```bash
TEST_CASE_DIR="workflow-verification/test-cases/{test-id}"

# Verify test case exists
if [[ ! -d "$TEST_CASE_DIR" ]]; then
  echo "Error: Test case not found: {test-id}"
  echo "Available test cases:"
  ls workflow-verification/test-cases/
  exit 1
fi
```

Read test definition:
```
Read: workflow-verification/test-cases/{test-id}/test-definition.toon
```

### Step 2: Setup Environment

If test definition includes setup_commands:
```bash
# Execute each setup command
{setup_command_1}
{setup_command_2}
```

### Step 3: Execute Trigger

Execute the trigger command from test definition. The trigger specifies a command like `/plan-manage create a new plan: ...`.

**IMPORTANT**: Execute this command and capture the resulting plan_id from its output.

### Step 4: Run Verification

Once plan_id is captured, proceed to **Shared Verification Steps** below with the plan_id.

---

## Workflow 2: Verify Plan

Verify an existing plan against test case criteria. No trigger execution.

### Parameters
- `--test-id` (required): Test case identifier
- `--plan-id` (required): Existing plan to verify

### Step 1: Load Test Case

```bash
TEST_CASE_DIR="workflow-verification/test-cases/{test-id}"

if [[ ! -d "$TEST_CASE_DIR" ]]; then
  echo "Error: Test case not found: {test-id}"
  exit 1
fi
```

### Step 2: Validate Plan Exists

```bash
# Verify the plan exists
python3 .plan/execute-script.py pm-workflow:manage-lifecycle:manage-lifecycle \
  status --plan-id {plan_id}
```

If plan doesn't exist, report error.

### Step 3: Run Verification

Proceed to **Shared Verification Steps** below with the provided plan_id.

---

## Shared Verification Steps

These steps are used by both Workflow 1 (test) and Workflow 2 (verify).

### Step V1: Run Structural Verification (Script)

Execute structural verification script:

```bash
python3 .claude/skills/workflow-verify/scripts/verify-structure.py \
  --plan-id {plan_id} \
  --test-case workflow-verification/test-cases/{test-id} \
  --output .plan/temp/verify-{test-id}-structure.toon
```

Parse output for structural check results.

### Step V2: Collect Artifacts

Collect actual artifacts via manage-* interfaces:

```bash
python3 .claude/skills/workflow-verify/scripts/collect-artifacts.py \
  --plan-id {plan_id} \
  --output .plan/temp/verify-{test-id}-artifacts/
```

### Step V3: Run Semantic Assessment (LLM-as-Judge)

**READ** the semantic criteria:
```
Read: workflow-verification/test-cases/{test-id}/criteria/semantic.md
```

**READ** the decision quality criteria:
```
Read: workflow-verification/test-cases/{test-id}/criteria/decision-quality.md
```

**READ** the golden reference:
```
Read: workflow-verification/test-cases/{test-id}/golden/verified-result.md
```

**READ** the actual output:
```
Read: .plan/temp/verify-{test-id}-artifacts/solution_outline.md
```

**Perform LLM-as-Judge Assessment**:

For each semantic criterion:
1. Compare actual output against golden reference
2. Score on scale 0-100
3. Explain reasoning for score
4. Identify specific gaps or errors

Assessment dimensions:
- **Scope Score (0-100)**: Did it analyze the correct components?
- **Completeness Score (0-100)**: Are all expected items found?
- **Quality Score (0-100)**: Are decisions well-reasoned?

### Step V4: Generate Assessment Report

Create timestamp for results:
```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RESULTS_DIR=".plan/temp/workflow-verification/{test-id}-$TIMESTAMP"
mkdir -p "$RESULTS_DIR"
```

**Create assessment-results.toon**:

```toon
test_id: {test-id}
timestamp: {timestamp}
plan_id: {plan_id}
overall_status: {pass|fail}
overall_score: {weighted_average}

structural_checks:
  status: {pass|fail}
  passed: {count}
  failed: {count}

semantic_assessment:
  scope_score: {0-100}
  completeness_score: {0-100}
  quality_score: {0-100}
  overall_score: {average}

findings[N]{severity,category,description,location}:
{severity},{category},{description},{location}
...

missing_items[N]:
{missing_item_1}
{missing_item_2}
...

recommendations[N]:
{recommendation_1}
{recommendation_2}
...
```

**Create assessment-detail.md**:

Full narrative report with:
- Executive summary
- Structural check details
- Semantic assessment reasoning
- Specific findings with locations
- Recommendations

### Step V5: Display Results

Show verification summary:
```
## Verification Results: {test-id}

**Overall Status**: {PASS|FAIL}
**Overall Score**: {score}/100

### Structural Checks
- Passed: {count}
- Failed: {count}

### Semantic Assessment
| Dimension | Score |
|-----------|-------|
| Scope | {scope}/100 |
| Completeness | {completeness}/100 |
| Quality | {quality}/100 |

### Key Findings
{findings_list}

### Missing Items
{missing_items_list}

**Full Report**: {results_dir}/assessment-detail.md
```

### Step V6: Cleanup (Optional)

If test definition specifies `cleanup.archive_plan: true` (only for Workflow 1: test):
```bash
# Archive or delete the test plan
rm -rf .plan/plans/{plan_id}
```

---

## Workflow 3: Create Test Case

Interactive wizard to create a new verification test case.

### Parameters
- `--test-id` (required): Unique identifier for test case (kebab-case)

### Step 1: Validate Test ID

```bash
# Check test-id format
if [[ ! "$TEST_ID" =~ ^[a-z][a-z0-9-]+$ ]]; then
  echo "Error: test-id must be kebab-case"
  exit 1
fi

# Check if already exists
if [[ -d "workflow-verification/test-cases/$TEST_ID" ]]; then
  echo "Error: Test case $TEST_ID already exists"
  exit 1
fi
```

### Step 2: Gather Trigger Information

```
AskUserQuestion:
  question: "What command triggers this workflow?"
  header: "Trigger"
  options:
    - label: "/plan-manage create" description: "Create a new plan"
    - label: "Custom command" description: "Specify a different command"
```

Then ask:

```
AskUserQuestion:
  question: "Which phase(s) should be verified?"
  header: "Phases"
  options:
    - label: "2-outline" description: "Verify solution outline only"
    - label: "3-plan" description: "Verify task planning only"
    - label: "both" description: "Verify outline and planning"
```

### Step 3: Execute and Capture

```
AskUserQuestion:
  question: "Execute the trigger command now to capture artifacts?"
  header: "Execute"
  options:
    - label: "Yes" description: "Run the workflow and capture output"
    - label: "No" description: "Skip execution, create empty test case"
```

If "Yes":
1. Create a temporary plan directory
2. Execute the trigger command
3. Capture artifacts via manage-* tools:

```bash
# Capture solution outline via manage-* interface
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline \
  list-deliverables --plan-id {temp_plan_id}

# Capture config
python3 .plan/execute-script.py pm-workflow:manage-config:manage-config \
  read --plan-id {temp_plan_id}

# Capture tasks (if phase includes 3-plan)
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks \
  list --plan-id {temp_plan_id} --phase execute
```

### Step 4: Review and Approve as Golden Reference

Display captured output summary:
- Deliverable count
- Affected files count
- Task count (if applicable)
- Key decisions from work log

```
AskUserQuestion:
  question: "Is this the CORRECT expected output?"
  header: "Approve"
  options:
    - label: "Yes" description: "Save as golden reference"
    - label: "Edit" description: "Modify before saving"
    - label: "Cancel" description: "Discard and exit"
```

If "Yes" or after editing:
- Copy actual output to `golden/verified-result.md`
- Create `expected-artifacts.toon` from artifact list

### Step 5: Define Semantic Criteria

```
AskUserQuestion:
  question: "What semantic criteria should be verified?"
  header: "Criteria"
  multiSelect: true
  options:
    - label: "Scope correctness" description: "All component types analyzed"
    - label: "Completeness" description: "All affected files found"
    - label: "Decision quality" description: "Exclusions have rationale"
    - label: "Custom" description: "Add custom criteria"
```

Create `criteria/semantic.md` with selected criteria.

### Step 6: Create Test Case Files

Create directory and files:

```bash
mkdir -p workflow-verification/test-cases/{test-id}/criteria
mkdir -p workflow-verification/test-cases/{test-id}/golden
```

Write files using templates from `templates/`:
- `test-definition.toon`
- `expected-artifacts.toon`
- `criteria/semantic.md`
- `criteria/decision-quality.md`
- `golden/verified-result.md`

### Step 7: Display Summary

Show created test case location and next steps:
```
Test case created: workflow-verification/test-cases/{test-id}/

Files created:
- test-definition.toon
- expected-artifacts.toon
- criteria/semantic.md
- criteria/decision-quality.md
- golden/verified-result.md

To run verification:
  /verify-workflow test --test-id {test-id}
  /verify-workflow verify --test-id {test-id} --plan-id {existing-plan}
```

---

## Workflow 4: List Test Cases

List available test cases with status.

### Step 1: Discover Test Cases

```bash
ls -d workflow-verification/test-cases/*/ 2>/dev/null | while read dir; do
  test_id=$(basename "$dir")
  echo "$test_id"
done
```

### Step 2: Get Status for Each

For each test case, check:
- Has golden reference?
- Has recent results?
- Last run status?

```bash
for test_id in $(ls workflow-verification/test-cases/); do
  has_golden="No"
  [[ -f "workflow-verification/test-cases/$test_id/golden/verified-result.md" ]] && has_golden="Yes"

  last_run="Never"
  last_result=$(ls -t .plan/temp/workflow-verification/${test_id}-* 2>/dev/null | head -1)
  [[ -n "$last_result" ]] && last_run=$(basename "$last_result" | cut -d'-' -f2-)

  echo "$test_id|$has_golden|$last_run"
done
```

### Step 3: Display Summary

```
## Available Test Cases

| Test ID | Golden Ref | Last Run | Status |
|---------|------------|----------|--------|
| {test_id} | {Yes/No} | {timestamp} | {status} |
...

To run verification:
  /verify-workflow run --test-id <test-id>

To create new test case:
  /verify-workflow create --test-id <new-test-id>
```

---

## Scripts Reference

### verify-structure.py

Runs structural checks using manage-* tool interfaces.

```bash
python3 .claude/skills/workflow-verify/scripts/verify-structure.py \
  --plan-id {plan_id} \
  --test-case {test_case_dir} \
  --output {output_path}
```

**Checks performed**:
- File existence via manage-* exists commands
- Format validation via manage-* validate commands
- Required sections present
- Cross-reference validity

**Output format (TOON)**:
```toon
status: {pass|fail}
plan_id: {plan_id}
checks[N]{name,status,message}:
solution_outline_exists,pass,File exists
solution_outline_valid,pass,Validation passed
...
findings[N]{severity,message}:
error,Missing required section: Overview
warning,Deliverable D3 missing verification command
...
```

### collect-artifacts.py

Collects artifacts via manage-* interfaces for comparison.

```bash
python3 .claude/skills/workflow-verify/scripts/collect-artifacts.py \
  --plan-id {plan_id} \
  --output {output_dir}
```

**Artifacts collected**:
- solution_outline.md (via manage-solution-outline read --raw)
- config.toon (via manage-config read)
- status.toon (via manage-lifecycle status)
- references.toon (via manage-references read)
- tasks/*.toon (via manage-tasks list/get)
- work.log extracts (via manage-logging read)

---

## Scoring Guide

### Scope Score (0-100)

| Score | Criteria |
|-------|----------|
| 90-100 | All expected component types analyzed, correct scope boundaries |
| 70-89 | Most components analyzed, minor scope issues |
| 50-69 | Significant scope gaps, missing component types |
| 0-49 | Wrong scope, major component types missing |

### Completeness Score (0-100)

| Score | Criteria |
|-------|----------|
| 90-100 | All expected items found, no missing files |
| 70-89 | Most items found, 1-2 minor omissions |
| 50-69 | Significant omissions, 3+ missing items |
| 0-49 | Many missing items, incomplete analysis |

### Quality Score (0-100)

| Score | Criteria |
|-------|----------|
| 90-100 | Clear decisions, well-documented rationale |
| 70-89 | Good decisions, some rationale gaps |
| 50-69 | Questionable decisions, missing rationale |
| 0-49 | Poor decisions, no rationale documented |

---

## Non-Prompting Requirements

This skill uses project-level paths that require Read/Write permissions:

**File Operations**:
- `Read(workflow-verification/**)` - Read test cases
- `Read(.claude/skills/**)` - Read skill files
- `Read(.plan/**)` - Read plan artifacts
- `Write(.plan/temp/**)` - Write results and temporary files

**Script Execution**:
- Scripts in `.claude/skills/workflow-verify/scripts/`

**Skill Invocations**:
- None required (project-level skill)
