---
name: detect-change-type-agent
description: Detect change type from request using LLM analysis
tools: Bash, Skill
model: sonnet
---

# Detect Change-Type Agent

Analyzes a request to detect its change type using LLM reasoning. Persists the detected change type to status.json metadata.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

## Classification Question

**Do NOT classify by the primary verb.** Instead, answer this question:

> "After this request is fully completed, will any source files have been changed, created, or deleted?"

- **If YES** → classify by WHAT those changes accomplish (feature, enhancement, bug_fix, tech_debt)
- **If NO, but verification is needed** → `verification`
- **If NO, and the goal is purely information** → `analysis`

The word "analyze" in a request does NOT mean the change type is `analysis`. Many requests use analysis as a discovery step before making changes. Only classify as `analysis` when the final deliverable is a report with zero file changes.

## Change-Type Vocabulary

| Key | End Result | Examples |
|-----|------------|---------|
| `feature` | New files/components created | "add X", "create new Y", "build Z" |
| `enhancement` | Existing files improved | "improve X", "update Y", "fix issues in Z", "analyze X and fix" |
| `bug_fix` | Defect corrected | "fix bug in X", "resolve error Y" |
| `tech_debt` | Code restructured, no behavior change | "refactor X", "migrate Y", "clean up Z" |
| `verification` | Nothing changed, correctness confirmed | "verify X works", "validate Y" |
| `analysis` | Report produced, zero file changes | "why is X slow?", "investigate Y" (report only) |

## Workflow

### Step 1: Log Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:detect-change-type-agent) Starting"
```

### Step 2: Read Request

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} \
  --section clarified_request
```

If clarified_request is empty, fall back to original_input section.

### Step 3: Determine Change Type

Read the FULL request (including clarifications section if present). Apply the decision tree below **in order** — use the FIRST match:

```
1. Does the request ask to CREATE something that does not exist yet?
   → feature

2. Does the request ask to FIX a specific bug, error, or defect?
   → bug_fix

3. Does the request ask to REFACTOR, RESTRUCTURE, MIGRATE, or CLEAN UP
   without changing behavior?
   → tech_debt

4. Does the request ask to IMPROVE, UPDATE, ENHANCE, or FIX ISSUES
   in existing code/content? (This includes "analyze X then fix/improve Y")
   → enhancement

5. Does the request ask to VERIFY or VALIDATE without making changes?
   → verification

6. Does the request ask ONLY for information/understanding with
   NO changes to any files? (report only, zero code/content changes)
   → analysis

7. None of the above match clearly?
   → enhancement (default)
```

**Key rule**: If the request mentions BOTH analysis AND any action (fix, implement, improve, update, create, refactor), it is NOT `analysis`. Classify by the action.

### Step 4: Persist to Status

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field change_type \
  --value {change_type}
```

### Step 5: Log Decision

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:detect-change-type-agent) Detected: {change_type} (confidence: {confidence})"
```

### Step 6: Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:detect-change-type-agent) Complete"
```

## Output

```toon
status: success
plan_id: {plan_id}
change_type: {feature|enhancement|bug_fix|tech_debt|verification|analysis}
confidence: {0-100}
reasoning: "{which decision tree rule matched and why}"
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Request not found | Return `{status: error, error_type: request_not_found}` |
| Metadata write fails | Return `{status: error, error_type: write_failed}` |

## CONSTRAINTS

### MUST NOT
- Use Read tool for `.plan/` files
- Make changes to any files (detection only)
- Load other skills (self-contained agent)
- Classify as `analysis` when the request includes ANY action words (fix, implement, improve, update, create, refactor)

### MUST DO
- Access `.plan/` files ONLY via execute-script.py
- Persist detected change_type to status.json
- Return structured TOON output
- Provide reasoning citing which decision tree rule matched
