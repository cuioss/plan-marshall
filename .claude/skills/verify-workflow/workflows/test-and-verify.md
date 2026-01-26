# Test and Verify Workflows

Two entry points that share common verification steps.

## Workflow: test

Execute the trigger from test-definition, then verify the output. Full automated test.

### Parameters
- `--test-id` (optional): Test case identifier

### Step 1: Load Test Case

**If `--test-id` not provided**, discover available test cases:
```
Glob: workflow-verification/test-cases/*/test-definition.toon
```

- If exactly **one** test case exists: auto-select it and continue
- If **zero** test cases exist: display error and exit
- If **multiple** test cases exist: display list and ask user to specify `--test-id`

**If `--test-id` provided**, verify test case exists:
```
Glob: workflow-verification/test-cases/{test-id}/test-definition.toon
```

If no match found, list available test cases and display error.

If test case exists, read test definition:
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

Execute the trigger command from test definition (e.g., `/plan-marshall create a new plan: ...`).

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

Verify test case exists:
```
Glob: workflow-verification/test-cases/{test-id}/test-definition.toon
```

If no match found, report error and exit.

### Step 2: Validate Plan Exists

```bash
python3 .plan/execute-script.py pm-workflow:plan-marshall:manage-lifecycle \
  read --plan-id {plan_id}
```

If plan doesn't exist, report error.

### Step 3: Run Verification

Proceed to **Shared Verification Steps** below with the provided plan_id.

---

## Shared Verification Steps

Used by both `test` and `verify` workflows.

### Step V0: Create Results Directory

Create the results directory for all verification outputs:

```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RESULTS_DIR=".plan/temp/workflow-verification/{test-id}-$TIMESTAMP"
mkdir -p "$RESULTS_DIR"
```

All subsequent steps use `{results_dir}` to store outputs.

### Step V1: Collect Artifacts

Collect all artifacts to local directory first. All subsequent verification reads from this copy.

Read the `workflow_phase` from test-definition.toon to determine which phases to collect.

**6-Phase Model Artifact Collection:**

| Phase | Artifacts Collected |
|-------|---------------------|
| `1-init` | config.toon, status.toon, request.md |
| `2-refine` | request.md (with clarifications), work.log |
| `3-outline` | solution_outline.md, deliverables.toon, config.toon, status.toon, references.toon, work.log, decision.log |
| `4-plan` | TASK-*.toon files, tasks-list.toon |
| `5-execute` | references.toon (with modified files), work.log |
| `6-verify` | (quality checks - not collected by script) |
| `7-finalize` | (git artifacts - not collected by script) |

**Common combinations:**
- `3-outline` → collect outline artifacts only
- `4-plan` → collect planning artifacts only
- `3-outline,4-plan` → collect both outline and planning artifacts
- `1-init,2-refine,3-outline` → verify early phases including request refinement

```bash
python3 .plan/execute-script.py local:verify-workflow:collect-artifacts \
  --plan-id {plan_id} \
  --output {results_dir}/artifacts/ \
  --phases {workflow_phase from test-definition}
```

**Note**: The `--phases` parameter must match the `workflow_phase` field in test-definition.toon. Tasks are only collected when `4-plan` is included.

### Step V1.5: Trace Components

Collect all components used during workflow execution.

```
Read: workflows/trace-components.md
```

Execute the trace-components workflow to generate:
- `{results_dir}/component-trace.md`

This creates sequential component IDs (C1, C2, ...) for later attribution.

### Step V2: Run Structural Verification

Verify against the locally collected artifacts (from Step V1).

```bash
python3 .plan/execute-script.py local:verify-workflow:verify-structure \
  --plan-id {plan_id} \
  --test-case workflow-verification/test-cases/{test-id} \
  --artifacts-dir {results_dir}/artifacts/ \
  --output {results_dir}/structural-checks.toon \
  --phases {workflow_phase from test-definition}
```

Parse the output to determine structural check status.

### Step V2.5: Analyze Structural Failures (Conditional)

**Only execute if Step V2 reports failures.**

Read structural check results:
```
Read: {results_dir}/structural-checks.toon
```

If `status: fail`:
```
Read: workflows/analyze-failures.md
```

Execute the analyze-failures workflow to generate:
- `{results_dir}/structural-analysis.toon`

This produces categorized failure analysis with origins and fix proposals.

### Step V2.6: Analyze Script Failures

Check for script execution errors during workflow execution.

**Read script execution log:**
```
Read: .plan/plans/{plan_id}/script-execution.log
```

**Parse for ERROR entries:**
Extract lines matching pattern `[ERROR]` with subsequent indented lines (exit_code, args, stderr).

**For each error found:**
1. Extract: script notation, exit_code, args, stderr message
2. Categorize error type:
   - `Missing API`: "invalid choice" or "unrecognized arguments"
   - `Invalid Parameters`: "Invalid", "Must be one of"
   - `Script Bug`: Other execution errors
3. Trace origin using component-trace.md (which component called this script)

**If errors exist, optionally invoke deep analysis:**
```
Skill: pm-plugin-development:tools-analyze-script-failures
```

This provides detailed root cause analysis and fix proposals.

**Output:**
Add to `{results_dir}/assessment-results.toon`:
```toon
script_errors:
  count: {N}
  errors[N]{script,exit_code,category,message}:
  {notation},{code},{category},{short_message}
```

Add script errors to `findings[]` array with severity `error`.

### Step V3: Run Semantic Assessment (LLM-as-Judge)

**Read** these files:
- `workflow-verification/test-cases/{test-id}/criteria/semantic.md`
- `workflow-verification/test-cases/{test-id}/criteria/decision-quality.md`
- `workflow-verification/test-cases/{test-id}/golden/verified-result.md`
- `{results_dir}/artifacts/solution_outline.md`

**Perform assessment** for each criterion:
1. Compare actual output against golden reference
2. Score 0-100 with reasoning
3. Identify specific gaps or errors

**Dimensions**:
- **Scope Score**: Correct components analyzed?
- **Completeness Score**: All expected items found?
- **Quality Score**: Decisions well-reasoned?

### Step V4: Generate Assessment Report

Create `{results_dir}/assessment-results.toon`:
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

structural_analysis:
  status: {analyzed|skipped}
  failure_count: {count}

  failures[N]{check_name,category,origin,description,fix_proposal}:
  ...

script_errors:
  count: {N}
  errors[N]{script,exit_code,category,message}:
  ...

semantic_assessment:
  scope_score: {0-100}
  completeness_score: {0-100}
  quality_score: {0-100}

findings[N]{severity,category,description,location}:
...

missing_items[N]:
...
```

Create `{results_dir}/assessment-detail.md` with full narrative.

### Step V4.5: Analyze Issues (Conditional)

**Only execute if findings exist.**

Check if findings array has entries in the assessment results.

If findings exist:
```
Read: workflows/analyze-issues.md
```

Execute the analyze-issues workflow to generate:
- `{results_dir}/issue-analysis.md`

This traces findings back to specific components using the component trace IDs.

### Step V5: Display Results

```
## Verification Results: {test-id}

**Overall Status**: {PASS|FAIL}
**Overall Score**: {score}/100

### Structural Checks
- Passed: {count}
- Failed: {count}

### Structural Analysis (if failures exist)
| Check | Category | Origin | Fix |
|-------|----------|--------|-----|
| {check_name} | {category} | {origin} | {fix_proposal} |
...

### Script Errors (if any)
| Script | Exit Code | Category | Message |
|--------|-----------|----------|---------|
| {script} | {code} | {category} | {message} |
...

### Semantic Assessment
| Dimension | Score |
|-----------|-------|
| Scope | {scope}/100 |
| Completeness | {completeness}/100 |
| Quality | {quality}/100 |

### Key Findings
{findings_list}

### Issue Analysis (if findings exist)
| Issue | Origin | Confidence | Component |
|-------|--------|------------|-----------|
| {issue} | C{n} | {level} | {name} |
...

### Results Directory
All outputs: {results_dir}/
- assessment-results.toon
- assessment-detail.md
- component-trace.md
- structural-checks.toon
- structural-analysis.toon (if failures)
- script-errors.toon (if script errors)
- issue-analysis.md (if findings)
- artifacts/
```

### Step V6: Cleanup (Optional)

For `test` workflow only, if `cleanup.archive_plan: true`:
```bash
rm -rf .plan/plans/{plan_id}
```
