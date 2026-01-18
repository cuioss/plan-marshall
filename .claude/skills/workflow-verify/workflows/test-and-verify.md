# Test and Verify Workflows

Two entry points that share common verification steps.

## Workflow: test

Execute the trigger from test-definition, then verify the output. Full automated test.

### Parameters
- `--test-id` (required): Test case identifier

### Step 1: Load Test Case

```bash
TEST_CASE_DIR="workflow-verification/test-cases/{test-id}"

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
{setup_command_1}
{setup_command_2}
```

### Step 3: Execute Trigger

Execute the trigger command from test definition (e.g., `/plan-manage create a new plan: ...`).

**IMPORTANT**: Capture the resulting plan_id from its output.

### Step 4: Run Verification

Proceed to **Shared Verification Steps** below with the plan_id.

---

## Workflow: verify

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
python3 .plan/execute-script.py pm-workflow:manage-lifecycle:manage-lifecycle \
  read --plan-id {plan_id}
```

If plan doesn't exist, report error.

### Step 3: Run Verification

Proceed to **Shared Verification Steps** below with the provided plan_id.

---

## Shared Verification Steps

Used by both `test` and `verify` workflows.

### Step V1: Run Structural Verification

```bash
python3 .claude/skills/workflow-verify/scripts/verify-structure.py \
  --plan-id {plan_id} \
  --test-case workflow-verification/test-cases/{test-id} \
  --output .plan/temp/verify-{test-id}-structure.toon
```

### Step V2: Collect Artifacts

```bash
python3 .claude/skills/workflow-verify/scripts/collect-artifacts.py \
  --plan-id {plan_id} \
  --output .plan/temp/verify-{test-id}-artifacts/
```

### Step V3: Run Semantic Assessment (LLM-as-Judge)

**Read** these files:
- `workflow-verification/test-cases/{test-id}/criteria/semantic.md`
- `workflow-verification/test-cases/{test-id}/criteria/decision-quality.md`
- `workflow-verification/test-cases/{test-id}/golden/verified-result.md`
- `.plan/temp/verify-{test-id}-artifacts/solution_outline.md`

**Perform assessment** for each criterion:
1. Compare actual output against golden reference
2. Score 0-100 with reasoning
3. Identify specific gaps or errors

**Dimensions**:
- **Scope Score**: Correct components analyzed?
- **Completeness Score**: All expected items found?
- **Quality Score**: Decisions well-reasoned?

### Step V4: Generate Assessment Report

```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RESULTS_DIR=".plan/temp/workflow-verification/{test-id}-$TIMESTAMP"
mkdir -p "$RESULTS_DIR"
```

Create `assessment-results.toon`:
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

findings[N]{severity,category,description,location}:
...

missing_items[N]:
...
```

Create `assessment-detail.md` with full narrative.

### Step V5: Display Results

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

**Full Report**: {results_dir}/assessment-detail.md
```

### Step V6: Cleanup (Optional)

For `test` workflow only, if `cleanup.archive_plan: true`:
```bash
rm -rf .plan/plans/{plan_id}
```
