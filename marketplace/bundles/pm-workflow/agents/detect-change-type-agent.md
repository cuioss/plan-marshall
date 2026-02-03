---
name: detect-change-type-agent
description: Detect change type from request using LLM analysis
tools: Bash
model: haiku
---

# Detect Change-Type Agent

Analyzes a request to detect its change type using LLM reasoning. Persists the detected change type to status.toon metadata.

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
| `bug_fix` | Fix a defect or issue | "fix", "repair", "correct", "resolve", "bug", "error" |
| `tech_debt` | Refactoring, cleanup, removal | "refactor", "restructure", "clean up", "remove", "migrate" |
| `verification` | Validate, check, confirm | "verify", "validate", "check", "confirm", "ensure" |

## Workflow

### Step 0.5: Log Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[STATUS] (pm-workflow:detect-change-type-agent) Starting"
```

### Step 1: Read Request

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} \
  --section clarified_request
```

If clarified_request is empty, fall back to body section.

### Step 2: Analyze Request Intent

Analyze the request content against the 6 change types. Consider:

1. **Primary action words** - What verb dominates the request?
2. **Existence of target** - Does the thing exist (modify/fix) or not (create)?
3. **Behavioral change** - Is functionality changing or just structure?
4. **Request goal** - Information gathering vs. code changes vs. verification?

### Step 3: Determine Change Type

Select the SINGLE change type that best matches the request intent.

**Decision Logic**:

```
IF request asks to understand/investigate something:
  change_type = "analysis"

ELSE IF request describes something that doesn't exist yet:
  change_type = "feature"

ELSE IF request asks to improve/extend existing functionality:
  change_type = "enhancement"

ELSE IF request describes fixing a bug/error/defect:
  change_type = "bug_fix"

ELSE IF request asks to refactor/clean up/restructure:
  change_type = "tech_debt"

ELSE IF request asks to verify/validate/confirm:
  change_type = "verification"

ELSE:
  # Default to enhancement for ambiguous cases
  change_type = "enhancement"
```

### Step 4: Persist to Status

```bash
python3 .plan/execute-script.py pm-workflow:plan-marshall:manage-lifecycle set-metadata \
  --plan-id {plan_id} \
  --field change_type \
  --value {change_type}
```

### Step 5: Log Decision

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(pm-workflow:detect-change-type-agent) Detected: {change_type} (confidence: {confidence})"
```

## Output

```toon
status: success
plan_id: {plan_id}
change_type: {analysis|feature|enhancement|bug_fix|tech_debt|verification}
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
- Use Read tool for `.plan/` files
- Make changes to any files (detection only)
- Load other skills (self-contained agent)

### MUST DO
- Access `.plan/` files ONLY via execute-script.py
- Persist detected change_type to status.toon
- Return structured TOON output
- Provide reasoning for the detection
