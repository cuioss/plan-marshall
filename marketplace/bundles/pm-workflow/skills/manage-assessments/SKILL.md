---
name: manage-assessments
description: Component evaluation storage with certainty/confidence assessments in JSONL persistence
user-invocable: false
allowed-tools: Bash
---

# Manage Assessments

Component evaluation storage providing structured JSONL persistence for certainty/confidence assessments from analysis agents.

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

**Certainty values**: `CERTAIN_INCLUDE`, `CERTAIN_EXCLUDE`, `UNCERTAIN`

## CLI Commands

```bash
# Add assessment
python3 .plan/execute-script.py pm-workflow:manage-assessments:manage-assessments \
  add {plan_id} {file_path} {certainty} {confidence} \
  [--agent AGENT] [--detail DETAIL] [--evidence EVIDENCE]

# Query assessments
python3 .plan/execute-script.py pm-workflow:manage-assessments:manage-assessments \
  query {plan_id} [--certainty C] [--min-confidence N] \
  [--max-confidence N] [--file-pattern PATTERN]

# Get single assessment
python3 .plan/execute-script.py pm-workflow:manage-assessments:manage-assessments \
  get {plan_id} {hash_id}

# Clear assessments (all or by agent)
python3 .plan/execute-script.py pm-workflow:manage-assessments:manage-assessments \
  clear {plan_id} [--agent AGENT]
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

## Integration

### Producers

| Client | Operation |
|--------|-----------|
| Analysis agents | add |
| Outline agents | add, clear |

### Consumers

| Client | Operation |
|--------|-----------|
| Q-Gate agent | query |
| Workflow orchestration | query |
