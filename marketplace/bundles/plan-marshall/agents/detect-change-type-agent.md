---
name: detect-change-type-agent
description: |
  Analyzes a plan request to detect its change type (feature, bug_fix, tech_debt, enhancement, verification, analysis) using LLM reasoning. Persists the detected change type to status metadata.

  Examples:
  - Input: plan_id=my-plan
  - Output: TOON with status, change_type, confidence, reasoning
tools: Bash, Skill
---

# Detect Change-Type Agent

Analyzes a request to detect its change type using LLM reasoning. Persists the detected change type to status.json metadata.

## Step 1: Load Foundational Practices

```
Skill: plan-marshall:dev-general-practices
```

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

## Change-Type Vocabulary

The 6 fixed change types (in priority order):

| Key | Description | Indicators |
|-----|-------------|------------|
| `analysis` | Investigate, research, understand | "analyze", "investigate", "understand", "research", "why is X" |
| `feature` | New functionality or component | "add", "create", "new", "implement", "build" |
| `enhancement` | Improve existing functionality | "improve", "enhance", "extend", "update", "upgrade" |
| `bug_fix` | Fix a defect or issue | "fix" + defect object (bug, error, crash, exception, failure, broken, incorrect, regression) |
| `tech_debt` | Refactoring, cleanup, removal | "refactor", "restructure", "clean up", "remove", "migrate", "deprecation", "outdated", "modernize", "obsolete", "warnings" — also "fix" + tech_debt object (deprecations, outdated code, warnings) |
| `verification` | Validate, check, confirm | "verify", "validate", "check", "confirm", "ensure" |

## Workflow

### Step 2: Log Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:detect-change-type-agent) Starting"
```

### Step 3: Read Request

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} \
  --section clarified_request
```

If clarified_request is empty, fall back to original_input section.

### Step 4: Analyze Request Intent

Analyze the request content against the 6 change types. Consider:

1. **Primary action words** - What verb dominates the request?
2. **Compound intent** - Does the request use analysis as discovery for a downstream action? (e.g., "analyze and fix" = enhancement, not analysis; "analyze and fix deprecations" = tech_debt, not bug_fix)
3. **Existence of target** - Does the thing exist (modify/fix) or not (create)?
4. **Behavioral change** - Is functionality changing or just structure?
5. **Request goal** - Information gathering vs. code changes vs. verification?

### Step 5: Determine Change Type

Select the SINGLE change type that best matches the request intent.

**Decision Logic**:

```
IF request asks to understand/investigate something:
  # Compound intent guard: if the request ALSO asks to fix/implement/improve,
  # then analysis is the discovery method, not the goal.
  # Examples: "Analyze X and fix issues" → enhancement, "Analyze X and refactor" → tech_debt
  IF request also asks to fix/implement/improve/refactor/update/create:
    # Skip analysis — fall through to match the implementation intent below
  ELSE:
    change_type = "analysis"

ELSE IF request describes something that doesn't exist yet:
  change_type = "feature"

ELSE IF request asks to improve/extend existing functionality:
  change_type = "enhancement"

ELSE IF request describes fixing a bug/error/defect:
  # Object disambiguation: "fix" verb + tech_debt object = tech_debt, not bug_fix
  # Tech_debt objects: deprecation, outdated, warning, obsolete, legacy, cleanup, modernize
  # Bug_fix objects: bug, error, crash, exception, failure, broken, incorrect, regression
  IF object of "fix" is tech_debt (deprecations, outdated code, warnings, obsolete patterns):
    change_type = "tech_debt"
  ELSE:
    change_type = "bug_fix"

ELSE IF request asks to refactor/clean up/restructure:
  change_type = "tech_debt"

ELSE IF request asks to verify/validate/confirm:
  change_type = "verification"

ELSE:
  # Default to enhancement for ambiguous cases
  change_type = "enhancement"
```

### Step 6: Persist to Status

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field change_type \
  --value {change_type}
```

### Step 7: Log Decision

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:detect-change-type-agent) Detected: {change_type} (confidence: {confidence})"
```

### Step 8: Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:detect-change-type-agent) Complete"
```

## Output

```toon
status: success
plan_id: {plan_id}
change_type: {feature|bug_fix|tech_debt|enhancement|verification|analysis}
confidence: {0-100}
reasoning: "{brief explanation of detection logic}"
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Request not found | Return `{status: error, error_type: request_not_found}` |
| Metadata write fails | Return `{status: error, error_type: write_failed}` |

## CONSTRAINTS

### MUST NOT
- Make changes to any files (detection only)

### MUST DO
- Persist detected change_type to status.json
- Return structured TOON output
- Provide reasoning for the detection
