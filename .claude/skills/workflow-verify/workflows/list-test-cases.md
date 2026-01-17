# List Test Cases Workflow

List available test cases with status.

## Step 1: Discover Test Cases

```bash
ls -d workflow-verification/test-cases/*/ 2>/dev/null | while read dir; do
  test_id=$(basename "$dir")
  echo "$test_id"
done
```

## Step 2: Get Status for Each

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
