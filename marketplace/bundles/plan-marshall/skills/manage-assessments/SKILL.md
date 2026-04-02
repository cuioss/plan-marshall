---
name: manage-assessments
description: Component evaluation storage with certainty/confidence assessments in JSONL persistence
user-invocable: false
scope: plan
---

# Manage Assessments

Component evaluation storage providing structured JSONL persistence for certainty/confidence assessments from analysis agents.

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse TOON output for status and route accordingly.

**Prohibited actions:**
- Do not modify assessments.jsonl directly; all mutations go through the script API
- Do not invent script arguments not listed in the CLI Commands section
- Do not use invalid certainty values (only CERTAIN_INCLUDE, CERTAIN_EXCLUDE, UNCERTAIN)

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:manage-assessments:manage-assessments {command} {args}`
- Assessments are plan-scoped; always provide `--plan-id`
- Confidence values must be numeric (0-100)

## Scope Distinction

| Scope | Storage | Lifecycle |
|-------|---------|-----------|
| **Project-level** | `.plan/lessons-learned/` | Persists across plans |
| **Plan-level** | `.plan/plans/{plan_id}/artifacts/` | Temporary, read-only after creation |

Assessments are working data during plan execution, consumed by Q-Gate validation and analysis agents.

## Storage

```
.plan/plans/{plan_id}/
└── artifacts/
    └── assessments.jsonl  # Component assessments (certainty, confidence)
```

## Schema

```json
{
  "hash_id": "a3f2c1",
  "timestamp": "...",
  "file_path": "src/File.java",
  "certainty": "CERTAIN_INCLUDE|CERTAIN_EXCLUDE|UNCERTAIN",
  "confidence": 95,
  "agent": "optional",
  "detail": "optional",
  "evidence": "optional"
}
```

**Certainty values**:

| Value | Meaning |
|-------|---------|
| `CERTAIN_INCLUDE` | Component is definitely in scope for the deliverable |
| `CERTAIN_EXCLUDE` | Component is definitely NOT in scope |
| `UNCERTAIN` | Requires further analysis to determine scope |

**Certainty vs confidence**: Certainty is the classification (in/out/unknown). Confidence (0-100) measures how sure the agent is about that classification. An `UNCERTAIN` assessment with confidence 90 means the agent is highly confident the scope is ambiguous; a `CERTAIN_INCLUDE` with confidence 60 means moderate certainty it belongs.

**Timestamp format**: ISO 8601 UTC (e.g., `2025-12-11T12:14:26Z`). Auto-generated on add.

**hash_id**: 6-character hex hash computed deterministically from file_path + certainty + confidence. Same inputs produce the same hash.

## CLI Commands

```bash
# Add assessment
python3 .plan/execute-script.py plan-marshall:manage-assessments:manage-assessments \
  add --plan-id {plan_id} --file-path {file_path} --certainty {certainty} --confidence {confidence} \
  [--agent AGENT] [--detail DETAIL] [--evidence EVIDENCE]

# Optional fields:
#   --agent:    Identifier of the agent that produced this assessment (e.g., "ext-outline-component-agent")
#   --detail:   Human-readable explanation of why this certainty was chosen
#   --evidence: Specific code/doc references supporting the assessment

# Query assessments
python3 .plan/execute-script.py plan-marshall:manage-assessments:manage-assessments \
  query --plan-id {plan_id} [--certainty C] [--min-confidence N] \
  [--max-confidence N] [--file-pattern PATTERN]

# Get single assessment
python3 .plan/execute-script.py plan-marshall:manage-assessments:manage-assessments \
  get --plan-id {plan_id} --hash-id {hash_id}

# Clear assessments (all or by agent)
python3 .plan/execute-script.py plan-marshall:manage-assessments:manage-assessments \
  clear --plan-id {plan_id} [--agent AGENT]
```

## Output Format

All commands return TOON format.

**Add response**:
```toon
status: success
hash_id: a3f2c1
file_path: src/File.java
```

**Query response**:
```toon
status: success
plan_id: my-plan
total_count: 30
filtered_count: 15

assessments[15]{hash_id,file_path,certainty,confidence}:
a3f2c1,src/File.java,CERTAIN_INCLUDE,95
b4e3d2,src/Other.java,CERTAIN_EXCLUDE,80
```

## Error Responses

All errors return TOON with `status: error` and exit code 1.

| Error Code | Cause |
|------------|-------|
| `invalid_certainty` | Certainty not in CERTAIN_INCLUDE, CERTAIN_EXCLUDE, UNCERTAIN |
| `invalid_confidence` | Confidence not a number in 0-100 range |
| `invalid_plan_id` | plan_id contains invalid characters |
| `not_found` | hash_id doesn't exist (get command) |
| `missing_required` | Required argument missing (file_path, certainty, confidence) |

```toon
status: error
plan_id: my-plan
error: invalid_certainty
message: Invalid certainty value: MAYBE (valid: CERTAIN_INCLUDE, CERTAIN_EXCLUDE, UNCERTAIN)
```

## Related Skills

- `manage-findings` — Complementary finding storage (assessments feed into Q-Gate findings)
- `phase-3-outline` — Primary consumer: outline agents produce assessments
- `manage-status` — Plan status tracking

## Integration

### Producers

| Client | Phase | Operation |
|--------|-------|-----------|
| `ext-outline-component-agent` | 3-outline | add (component-level assessments) |
| `ext-outline-inventory-agent` | 3-outline | add (initial scope assessments) |
| Outline skill | 3-outline | clear (reset before re-assessment) |

### Consumers

| Client | Phase | Operation |
|--------|-------|-----------|
| `q-gate-validation-agent` | 3-outline | query (validates outline coverage) |
| Phase orchestration | 3-outline | query (summary for user review) |

### Data Flow

Assessments feed into the Q-Gate validation: outline agents produce assessments → Q-Gate agent queries them to verify the solution outline covers all CERTAIN_INCLUDE components and doesn't include CERTAIN_EXCLUDE ones.
