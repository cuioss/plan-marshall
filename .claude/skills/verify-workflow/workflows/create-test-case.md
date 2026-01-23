# Create Test Case Workflow

Interactive wizard to create a new verification test case.

## Parameters
- `--test-id` (required): Unique identifier (kebab-case)

## Step 1: Validate Test ID

```bash
if [[ ! "$TEST_ID" =~ ^[a-z][a-z0-9-]+$ ]]; then
  echo "Error: test-id must be kebab-case"
  exit 1
fi

if [[ -d "workflow-verification/test-cases/$TEST_ID" ]]; then
  echo "Error: Test case $TEST_ID already exists"
  exit 1
fi
```

## Step 2: Gather Trigger Information

```
AskUserQuestion:
  question: "What command triggers this workflow?"
  header: "Trigger"
  options:
    - label: "/plan-manage create" description: "Create a new plan"
    - label: "Custom command" description: "Specify a different command"
```

Then:

```
AskUserQuestion:
  question: "Which phase(s) should be verified?"
  header: "Phases"
  options:
    - label: "3-outline" description: "Verify solution outline only"
    - label: "4-plan" description: "Verify task planning only"
    - label: "both" description: "Verify outline and planning"
```

## Step 3: Execute and Capture

```
AskUserQuestion:
  question: "Execute the trigger command now to capture artifacts?"
  header: "Execute"
  options:
    - label: "Yes" description: "Run the workflow and capture output"
    - label: "No" description: "Skip execution, create empty test case"
```

If "Yes":
1. Execute the trigger command
2. Capture artifacts via manage-* tools:

```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline \
  list-deliverables --plan-id {temp_plan_id}

python3 .plan/execute-script.py pm-workflow:manage-config:manage-config \
  read --plan-id {temp_plan_id}
```

## Step 4: Review and Approve as Golden Reference

Display captured output summary:
- Deliverable count
- Affected files count
- Task count (if applicable)

```
AskUserQuestion:
  question: "Is this the CORRECT expected output?"
  header: "Approve"
  options:
    - label: "Yes" description: "Save as golden reference"
    - label: "Edit" description: "Modify before saving"
    - label: "Cancel" description: "Discard and exit"
```

## Step 5: Define Semantic Criteria

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

## Step 6: Create Test Case Files

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

## Step 7: Display Summary

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
