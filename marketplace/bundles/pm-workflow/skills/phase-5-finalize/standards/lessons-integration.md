# Lessons Integration for Triage

How lessons learned inform triage decisions during the finalize phase.

## Purpose

During triage (Step 2 of verification), learned lessons can:
1. **Inform decisions** - Previous similar findings may have documented resolutions
2. **Provide context** - Historical decisions help consistency
3. **Record outcomes** - New triage decisions can become lessons for future reference

## Lesson Query Flow

### Before Triage Decision

Query lessons for similar findings:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons-learned:manage-lessons-learned query \
  --component {finding_source} \
  --category triage
```

**Output**:
```toon
status: success
matches[2]:
  - id: 2025-12-01-001
    summary: "S1192: String literals should not be duplicated - suppress in test code"
    decision: suppress
    context: "Test assertions often duplicate strings intentionally"
  - id: 2025-11-28-003
    summary: "S1192: Duplicate strings in constants acceptable"
    decision: accept
    context: "Constants file deliberately groups related strings"
```

### Apply Learned Decision

If a matching lesson exists:

1. **Evaluate relevance** - Does the lesson context match current situation?
2. **Apply decision** - Use the documented decision (fix/suppress/accept)
3. **Log application** - Record that lesson was applied

```bash
python3 .plan/execute-script.py plan-marshall:logging:manage-log \
  work {plan_id} INFO "[TRIAGE] (pm-workflow:phase-5-finalize) Applied lesson {lesson_id}: {decision} for {finding}"
```

### Record New Lesson

If no matching lesson exists and the triage decision is notable:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons-learned:manage-lessons-learned add \
  --component {triage_extension} \
  --category triage \
  --summary "{finding_type}: {decision} - {reason}" \
  --detail "{detailed_context_and_rationale}"
```

**Notable decisions to record**:
- Non-obvious suppressions with specific context
- Patterns that apply across multiple findings
- Decisions requiring domain expertise
- Exceptions to standard severity rules

## Decision Matrix

| Lesson Exists | Context Matches | Action |
|---------------|-----------------|--------|
| Yes | Yes | Apply lesson decision |
| Yes | No | Make fresh decision (different context) |
| No | - | Apply triage extension rules |
| No | - | Optionally record if notable |

## Recording Criteria

**Record a lesson when**:
- The decision required domain expertise
- The finding will likely recur
- The decision deviates from default severity rules
- Team discussion was needed

**Don't record when**:
- Standard severity rules were applied
- The fix was obvious and mechanical
- The finding is one-off (won't recur)

## Integration with Triage Extensions

Lessons complement triage extensions:

| Source | Content |
|--------|---------|
| Triage extension | Generic rules (severity guidelines, suppression syntax) |
| Lessons learned | Specific cases and contextual decisions |

**Priority**: Lessons override triage extension defaults when:
1. Lesson is more specific to current context
2. Lesson represents team consensus
3. Lesson captures exception to general rule

## Example: Query Before Suppress

```
Finding: S1192 - String literal "application/json" duplicated 5 times

1. Query lessons:
   python3 .plan/execute-script.py plan-marshall:manage-lessons-learned:manage-lessons-learned query \
     --pattern "S1192" --category triage

2. Result: Match found
   - Lesson: "S1192: HTTP content types acceptable to duplicate in test mocks"
   - Decision: accept
   - Context: "Test mock setup often repeats content types"

3. Apply: Accept the finding (don't fix, don't suppress)

4. Log: "[TRIAGE] Applied lesson 2025-12-01-005: accept for S1192 duplicate content-type"
```

## Example: Record New Decision

```
Finding: S3776 - Cognitive complexity too high (method: parseComplexExpression)

1. Query lessons: No match found

2. Apply triage extension (java-triage):
   - Severity: MAJOR
   - Default action: Fix if reasonable effort

3. Decision: Accept with reason
   - Reason: "Parser method inherently complex, no clean decomposition"
   - Alternative would be artificial splitting

4. Record lesson:
   python3 .plan/execute-script.py plan-marshall:manage-lessons-learned:manage-lessons-learned add \
     --component "pm-dev-java:ext-triage-java" \
     --category triage \
     --summary "S3776: Complex parser methods acceptable if decomposition artificial" \
     --detail "Parser methods that handle grammar rules are inherently complex. Splitting into smaller methods just for metrics often obscures the algorithm."
```

## Lessons Storage

Lessons with `category=triage` are stored in:
```
.plan/lessons-learned/{date}-{seq}.md
```

Triage lessons include:
- `component`: The triage extension that applies
- `category`: `triage`
- `summary`: Finding ID and decision summary
- `detail`: Context and rationale

## Query Parameters

| Parameter | Purpose |
|-----------|---------|
| `--pattern` | Match finding ID (e.g., "S1192") |
| `--category triage` | Filter to triage decisions |
| `--component {ext}` | Filter by triage extension |

## Related Documents

- [triage-integration.md](triage-integration.md) - How triage extensions are loaded and applied
- [pm-workflow:workflow-extension-api/standards/extensions/triage-extension.md](../../workflow-extension-api/standards/extensions/triage-extension.md) - Extension contract
- `plan-marshall:manage-lessons-learned` - Lessons storage and query skill
