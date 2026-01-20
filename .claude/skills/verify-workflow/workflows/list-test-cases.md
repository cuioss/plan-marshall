# List Test Cases Workflow

List available test cases with status.

## Step 1: Discover Test Cases

Find all test case directories:
```
Glob: workflow-verification/test-cases/*/test-definition.toon
```

Extract test IDs from the parent directory of each matched path.

## Step 2: Get Status for Each

For each test case, check:
- Has golden reference?
- Has recent results?
- Last run status?

**Check for golden reference:**
```
Read: workflow-verification/test-cases/{test_id}/golden/verified-result.md
```
- If file exists: `has_golden = "Yes"`
- If Read returns error (file not found): `has_golden = "No"`

**Check for recent results:**
```
Glob: .plan/temp/workflow-verification/{test_id}-*/assessment-results.toon
```
- If matches found: Extract timestamp from most recent (Glob returns sorted by mtime)
- If no matches: `last_run = "Never"`

**Check last run status:**
If recent results exist:
```
Read: {most_recent_results_dir}/assessment-results.toon
```
Extract `overall_status` field.

## Step 3: Display Summary

```
## Available Test Cases

| Test ID | Golden Ref | Last Run | Status |
|---------|------------|----------|--------|
| {test_id} | {Yes/No} | {timestamp} | {status} |
...

To run verification:
  /verify-workflow test --test-id <test-id>

To create new test case:
  /verify-workflow create --test-id <new-test-id>
```

## Example Output

```
## Available Test Cases

| Test ID | Golden Ref | Last Run | Status |
|---------|------------|----------|--------|
| migrate-json-to-toon | Yes | 20250119-103000 | pass |
| add-new-domain | Yes | Never | - |
| complex-refactor | No | 20250118-142500 | fail |

To run verification:
  /verify-workflow test --test-id <test-id>

To create new test case:
  /verify-workflow create --test-id <new-test-id>
```
