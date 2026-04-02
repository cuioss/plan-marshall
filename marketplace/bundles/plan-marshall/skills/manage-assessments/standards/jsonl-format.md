# Assessments JSONL Format

Storage format specification for component evaluation assessments.

## Storage File

Assessments are stored in `.plan/plans/{plan_id}/artifacts/assessments.jsonl`. Each line is a JSON object representing one component assessment.

## Record Schema

```json
{
  "hash_id": "a3f2c1",
  "timestamp": "2025-12-11T12:14:26Z",
  "file_path": "src/main/java/de/cuioss/auth/jwt/JwtValidator.java",
  "certainty": "CERTAIN_INCLUDE",
  "confidence": 95,
  "agent": "ext-outline-component-agent",
  "detail": "Core validation class directly affected by JWT refactoring",
  "evidence": "Contains validate() method referenced in deliverable 1"
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `hash_id` | string | 6-character hex hash (auto-generated from `file_path + certainty + confidence`) |
| `timestamp` | string | ISO 8601 UTC with Z suffix (auto-generated on add) |
| `file_path` | string | Relative path to the assessed component |
| `certainty` | string | Classification: `CERTAIN_INCLUDE`, `CERTAIN_EXCLUDE`, or `UNCERTAIN` |
| `confidence` | int | Confidence score 0-100 for the certainty classification |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `agent` | string | Identifier of the agent that produced this assessment |
| `detail` | string | Human-readable explanation of why this certainty was chosen |
| `evidence` | string | Specific code/doc references supporting the assessment |

## Certainty Model

| Value | Meaning |
|-------|---------|
| `CERTAIN_INCLUDE` | Component is definitely in scope for the deliverable |
| `CERTAIN_EXCLUDE` | Component is definitely NOT in scope |
| `UNCERTAIN` | Requires further analysis to determine scope |

### Certainty vs Confidence

These are independent dimensions:

- **Certainty** is the classification (in/out/unknown)
- **Confidence** (0-100) measures how sure the agent is about that classification

Examples:
- `UNCERTAIN` + confidence 90 = highly confident the scope is genuinely ambiguous
- `CERTAIN_INCLUDE` + confidence 60 = moderate certainty it belongs
- `CERTAIN_EXCLUDE` + confidence 95 = very confident it's out of scope

## Hash ID Generation

Hash IDs are 6-character hex strings computed deterministically from `file_path + certainty + confidence`. Same inputs always produce the same hash.

## Lifecycle

Assessments are working data during plan execution:

1. **Created** during phase-3-outline by component analysis agents
2. **Queried** by Q-Gate validation agent to verify solution outline coverage
3. **Cleared** before re-assessment (outline agents call `clear` before a fresh pass)
4. **Read-only** after outline phase completes — not modified in later phases
