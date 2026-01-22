# Component Analysis Contract

Defines the input/output contract for component analysis agents used in the Modify Flow of `workflow.md`.

## Purpose

Component analysis agents evaluate each component against the original request using semantic reasoning. By passing the actual request (not derived criteria), agents can reason about intent and context rather than pattern matching.

## Input Parameters

Agents receive the request text directly for semantic reasoning.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | str | Yes | Plan identifier for script access and logging |
| `bundle` | str | Yes | Bundle name to analyze (e.g., `pm-dev-java`) |
| `request_text` | str | Yes | The original request text from request.md |

## Agent Step 0: Load File Paths via Script

Each agent runs the filter script to get its file paths:

```bash
python3 .plan/execute-script.py pm-plugin-development:ext-outline-plugin:filter-inventory filter \
  --plan-id {plan_id} --bundle {bundle} --component-type {skills|commands|agents}
```

**Output** (TOON):
```toon
status: success
bundle: pm-dev-java
component_type: skills
file_count: 17
files[17]:
  - marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md
  - ...
```

Parse the `files` array. These are the paths to analyze.

**Note**: Bundle-level batching keeps file counts manageable (~5-20 files per bundle×type). No internal batching needed.

## Output Contract

All analysis agents MUST return this summary structure (detailed findings are in decision.log):

```toon
status: success
bundle: {bundle}
total_analyzed: {count}
certain_include: {count}
certain_exclude: {count}
uncertain: {count}

# Full findings available in decision.log
decision_log_entries: {count}
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `status` | enum | `success` or `error` |
| `bundle` | str | Bundle that was analyzed |
| `total_analyzed` | int | Must equal file count from filter script |
| `certain_include` | int | Files clearly matching request criteria (confidence >= 80%) |
| `certain_exclude` | int | Files clearly not matching (confidence >= 80%) |
| `uncertain` | int | Files needing clarification (confidence < 80%) |
| `decision_log_entries` | int | Number of entries written to decision.log |

### Certainty Definitions

| Certainty | Confidence Range | Meaning |
|-----------|------------------|---------|
| `CERTAIN_INCLUDE` | 80-100% | Clearly matches request criteria |
| `CERTAIN_EXCLUDE` | 80-100% | Clearly does not match |
| `UNCERTAIN` | 20-79% | Ambiguous - needs user clarification |

### Confidence Guidelines

- **90-100%**: Strong evidence, multiple indicators align
- **80-89%**: Good evidence, minor ambiguity
- **50-79%**: Mixed signals, context-dependent
- **20-49%**: Weak evidence, significant ambiguity

### Gate Assignment Rule

- confidence >= 80% AND matches criteria → `CERTAIN_INCLUDE`
- confidence >= 80% AND doesn't match → `CERTAIN_EXCLUDE`
- confidence < 80% → `UNCERTAIN`

## Logging Contract

Each finding MUST be logged to decision.log with a unique hash ID:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "[FINDING:{hash_id}] ({agent_name}) {file_path}: {certainty} ({confidence}%)
  detail: {reasoning}
  evidence: {evidence}"
```

**Hash ID Computation**: 6-digit hash from complete log message content.

```python
import hashlib
def log_entry_id(message: str) -> str:
    return hashlib.sha256(message.encode()).hexdigest()[:6]
```

### Logging Examples

```
[FINDING:a3f2c1] (skill-analysis-agent) path/skill.md: CERTAIN_INCLUDE (95%)
  detail: Has ## Output section with ```json block
  evidence: Lines 45-60

[FINDING:b7e4d9] (skill-analysis-agent) path/skill2.md: UNCERTAIN (45%)
  detail: Has JSON but in ## Workflow section - unclear if output spec
  evidence: Line 125: ```json in ## Workflow step
```

## Validation Rules

The calling workflow MUST validate agent output:

1. **Completeness**: `decision_log_entries == total_analyzed` - no skipping
2. **Consistency**: `certain_include + certain_exclude + uncertain == total_analyzed`
3. **Status check**: `status` must be `success` for results to be used
4. **Log verification**: Read decision.log entries to verify all findings logged

### Validation Failure Handling

If validation fails:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} ERROR "[VALIDATION] (pm-plugin-development:ext-outline-plugin) Agent validation failed: {bundle}
  expected_entries: {file_count}
  actual_entries: {decision_log_entries}
  action: Retry or escalate"
```

## Agent Implementation Requirements

### Critical Rules

1. **MUST** analyze every file returned by filter script - no skipping allowed
2. **MUST** read each file completely before evaluating
3. **MUST** reason about whether the component needs modification for the request
4. **MUST** provide specific reasoning explaining the decision
5. **MUST** provide specific evidence (line numbers, section names)
6. **MUST NOT** assume behavior based on component type name
7. **MUST NOT** return without completing all files
8. **MUST NOT** use categorical exclusions

### Analysis Approach (Semantic Reasoning with Confidence)

For each file, answer: **"Does this component need to be modified to fulfill the request?"** with a confidence level.

```
FOR each file_path from filter script:
  content = READ(file_path)

  # Semantic Analysis with Confidence
  reasoning, evidence = REASON_ABOUT(
    request_text,
    content,
    questions=[
      "What is this component's purpose?",
      "Does it have content relevant to the request?",
      "Would modifying it help fulfill the request?",
      "Is there context that makes it NOT applicable?",
      "How confident am I in this assessment?"
    ]
  )

  # Assess confidence (0-100%)
  confidence = ASSESS_CONFIDENCE(reasoning, evidence)

  # Determine certainty gate based on confidence
  IF confidence >= 80% AND matches request criteria:
    certainty = "CERTAIN_INCLUDE"
  ELIF confidence >= 80% AND does not match:
    certainty = "CERTAIN_EXCLUDE"
  ELSE:
    certainty = "UNCERTAIN"

  # Log finding to decision.log with hash ID
  message = format_log_message(file_path, certainty, confidence, reasoning, evidence)
  hash_id = sha256(message)[:6]
  LOG_TO_DECISION_LOG(plan_id, message)

  # Track counts for summary
  counts[certainty] += 1
```

**Key Points**:
1. **Full request context** - agents see the original request, not derived patterns
2. **Semantic reasoning** - agents reason about intent, not pattern match
3. **Context-aware** - agents can distinguish output specs from documentation examples
4. **Explicit reasoning** - every decision includes explanation
5. **Confidence assessment** - explicit numeric confidence drives certainty gate
6. **Traceability** - hash IDs enable linking decisions across stages

## Usage in Modify Flow

The Modify Flow in `workflow.md` Step 3c spawns analysis agents with this contract:

```
Task: pm-plugin-development:skill-analysis-agent
  Input:
    plan_id: migrate-json-to-toon
    bundle: pm-dev-java
    request_text: "Migrate agent/command/skill outputs from JSON to TOON format"
```

## Agents Implementing This Contract

| Agent | Component Type |
|-------|----------------|
| `skill-analysis-agent` | SKILL.md files |
| `command-analysis-agent` | Command .md files |
| `agent-analysis-agent` | Agent .md files |

Each agent uses semantic reasoning to evaluate components against the request.
