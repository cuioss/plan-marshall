# Change Verification — Generic Outline Instructions

Instructions for `verification` change type. Handles validation and confirmation requests. This is a read-only type — no code changes.

## When Used

Requests with `change_type: verification`:
- "Verify the migration completed successfully"
- "Check that all endpoints return valid JSON"
- "Confirm the refactoring didn't break tests"
- "Validate the configuration is correct"

## Discovery

Based on the request, establish:

1. **What to verify** — The specific thing being checked
2. **Success criteria** — What makes it "correct"
3. **Verification method** — How to check it

Log criteria:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:outline-change-type) Verifying: {target}, criteria: {criteria}"
```

## Analysis

Build a structured checklist:

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| {item1} | {command/inspection} | {what makes it pass} |
| {item2} | {command/inspection} | {what makes it pass} |

## Deliverable Structure

```markdown
### 1. Verify: {Verification Target}

**Metadata:**
- change_type: verification
- execution_mode: automated
- domain: {domain}
- module: {module or "project-wide"}
- depends: none

**Profiles:**
- implementation

**Verification Checklist:**
| Check | Method | Pass Criteria |
|-------|--------|---------------|
| {item1} | {method1} | {criteria1} |
| {item2} | {method2} | {criteria2} |
| {item3} | {method3} | {criteria3} |

**Affected files:**
- `{path/to/file1}` (verification target)
- `{path/to/file2}` (verification target)

**Change per file:**
- `{file1}`: Verify {specific aspect}
- `{file2}`: Verify {specific aspect}

**Verification:**
- Command: {primary verification command}
- Criteria: All checklist items pass

**Success Criteria:**
- All checklist items verified
- Evidence provided for each
- Clear pass/fail determination
```

## Guidelines

- Verification only — do not propose code changes
- Create clear pass/fail criteria
- Document verification methodology
