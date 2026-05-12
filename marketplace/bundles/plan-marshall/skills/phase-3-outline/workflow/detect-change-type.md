---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Detect Change-Type Workflow

LLM-judgement workflow that analyses a plan's clarified request and detects its change type (`feature`, `bug_fix`, `tech_debt`, `enhancement`, `verification`, `analysis`). Used as the LLM-fallback path when the `manage-status:change-type-heuristic` deterministic classifier returns `ambiguous`. No dedicated role key — the LLM call rarely fires and the level is resolved from `models.default`.

## Inputs

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `plan_id` | Yes | Plan identifier. |
| `WORKTREE` | Yes | Repo-relative working directory (`.` for main checkout). |

Skills the caller MUST forward in `skills[]`: `plan-marshall:manage-plan-documents` (request read), `plan-marshall:manage-status` (metadata persist), `plan-marshall:manage-logging` (decision + work entries).

## Change-Type Vocabulary

The six fixed change types (in priority order):

| Key | Description | Indicators |
|-----|-------------|------------|
| `analysis` | Investigate, research, understand | "analyze", "investigate", "understand", "research", "why is X" |
| `feature` | New functionality or component | "add", "create", "new", "implement", "build" |
| `enhancement` | Improve existing functionality | "improve", "enhance", "extend", "update", "upgrade" |
| `bug_fix` | Fix a defect or issue | "fix" + defect object (bug, error, crash, exception, failure, broken, incorrect, regression) |
| `tech_debt` | Refactoring, cleanup, removal | "refactor", "restructure", "clean up", "remove", "migrate", "deprecation", "outdated", "modernize", "obsolete", "warnings" — also "fix" + tech_debt object (deprecations, outdated code, warnings) |
| `verification` | Validate, check, confirm | "verify", "validate", "check", "confirm", "ensure" |

## Workflow

### Step 1: Log start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (execution-context.detect-change-type) Starting"
```

### Step 2: Read the request

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id {plan_id} --section clarified_request
```

If `clarified_request` is empty, fall back to the `original_input` section.

### Step 3: Analyse request intent

Consider:

1. **Primary action words** — what verb dominates the request?
2. **Compound intent** — does the request use analysis as discovery for a downstream action? (E.g., "analyze and fix" = enhancement, not analysis; "analyze and fix deprecations" = tech_debt, not bug_fix.)
3. **Existence of target** — does the thing exist (modify / fix) or not (create)?
4. **Behavioural change** — is functionality changing or just structure?
5. **Request goal** — information gathering vs. code changes vs. verification?

### Step 4: Determine change type

Select the SINGLE change type that best matches the request intent.

**Decision logic** (apply in order; the first matching rule wins):

```
IF request asks to understand/investigate something:
  # Compound intent guard: if the request ALSO asks to fix/implement/improve,
  # then analysis is the discovery method, not the goal.
  # "Analyze X and fix issues" → enhancement; "Analyze X and refactor" → tech_debt.
  IF request also asks to fix/implement/improve/refactor/update/create:
    # Skip analysis — fall through to match the implementation intent below
  ELSE:
    change_type = "analysis"

ELSE IF request describes something that doesn't exist yet:
  change_type = "feature"

ELSE IF request asks to improve/extend existing functionality:
  change_type = "enhancement"

ELSE IF request describes fixing a bug/error/defect:
  # Object disambiguation: "fix" verb + tech_debt object = tech_debt, not bug_fix.
  # Tech_debt objects: deprecation, outdated, warning, obsolete, legacy, cleanup, modernize.
  # Bug_fix objects: bug, error, crash, exception, failure, broken, incorrect, regression.
  IF object of "fix" is tech_debt:
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

### Step 5: Persist to status metadata

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set --field change_type --value {change_type}
```

### Step 6: Log decision

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(execution-context.detect-change-type) Detected: {change_type} (confidence: {confidence})"
```

### Step 7: Log completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (execution-context.detect-change-type) Complete"
```

## Output

```toon
status: success
display_detail: "detected {change_type} (confidence {confidence})"
plan_id: {plan_id}
change_type: {feature|bug_fix|tech_debt|enhancement|verification|analysis}
confidence: {0-100}
reasoning: "{brief explanation of detection logic}"
```

## Error handling

| Scenario | Action |
|----------|--------|
| Request not found | Return `{status: error, error_type: request_not_found}` |
| Metadata write fails | Return `{status: error, error_type: write_failed}` |

## Constraints

- MUST NOT make changes to any files (detection only).
- MUST persist detected `change_type` to status.json.
- MUST return structured TOON output.
- MUST provide reasoning for the detection.
