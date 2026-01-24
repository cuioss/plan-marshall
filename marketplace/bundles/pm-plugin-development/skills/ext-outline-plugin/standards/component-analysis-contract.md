# Component Analysis Contract

Defines the input/output contract for component analysis agents used in the analysis step (Step 3) of `ext-outline-plugin`.

## Purpose

Component analysis agents evaluate each component against the original request using semantic reasoning. By passing the actual request (not derived criteria), agents can reason about intent and context rather than pattern matching.

## Input Parameters

Agents receive explicit file sections from the parent workflow (ext-outline-plugin).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | str | Yes | Plan identifier for script access and logging |
| `request_text` | str | Yes | The original request text from request.md |
| `files_prompt` | str | Yes | Pre-generated prompt with explicit numbered file sections |

## Input Format

The parent workflow (ext-outline-plugin) generates a `files_prompt` containing explicit numbered file sections. Each section includes:
- File path to analyze
- Pre-generated logging command with placeholders

**Expected prompt structure**:
```markdown
## Files to Analyze

Request: {request_text}

Process these files IN ORDER. For EACH file, you MUST:
1. Read the file
2. Analyze it against the request
3. Assess confidence (0-100%) and determine certainty gate
4. Execute the logging bash command IMMEDIATELY (before next file)
5. Track counts for final summary

### File 1: {path}
**1a. Analyze**: [instructions]
**1b. Log (EXECUTE IMMEDIATELY)**: [bash command]

### File 2: {path}
...
```

**Note**: The parent workflow runs the filter script and builds `files_prompt`. Agents do NOT run filter scripts themselves.

## Output Contract

All analysis agents MUST return this summary structure (detailed assessments in assessments.jsonl):

```toon
status: success
bundle: {bundle}
total_analyzed: {count}
certain_include: {count}
certain_exclude: {count}
uncertain: {count}

# Full assessments available in artifacts/assessments.jsonl
assessments_logged: {count}
```

### Critical Output Rule

**Agents MUST NOT output verbose text.** All reasoning and analysis details belong in `assessments.jsonl`, not in the agent's text output.

- Do NOT narrate what you're doing ("Now I'll analyze...")
- Do NOT output per-file analysis text
- Do NOT explain decisions in text output
- ONLY output the final TOON summary block

The `artifacts/assessments.jsonl` receives all detailed assessments via the artifact_store commands.

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `status` | enum | `success` or `error` |
| `bundle` | str | Bundle that was analyzed |
| `total_analyzed` | int | Must equal file count from filter script |
| `certain_include` | int | Files clearly matching request criteria (confidence >= 80%) |
| `certain_exclude` | int | Files clearly not matching (confidence >= 80%) |
| `uncertain` | int | Files needing clarification (confidence < 80%) |
| `assessments_logged` | int | Number of assessments written to assessments.jsonl |

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

Each finding MUST be logged as an assessment via `manage-plan-artifacts`. Hash IDs are automatically generated.

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-artifacts:artifact_store \
  assessment add {plan_id} {file_path} {certainty} {confidence} \
  --agent {agent_name} --detail "{reasoning}" --evidence "{evidence}"
```

**Note**: The system automatically generates a 6-digit hash ID for each assessment.

### Logging Examples

Output format (TOON):
```toon
status: success
hash_id: a3f2c1
file_path: path/skill.md
```

Assessments are stored in `.plan/plans/{plan_id}/artifacts/assessments.jsonl`.

## Validation Rules

The calling workflow MUST validate agent output:

1. **Completeness**: `assessments_logged == total_analyzed` - no skipping
2. **Consistency**: `certain_include + certain_exclude + uncertain == total_analyzed`
3. **Status check**: `status` must be `success` for results to be used
4. **Log verification**: Query assessments.jsonl to verify all assessments logged

### Validation Failure Handling

If validation fails:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} ERROR "[VALIDATION] (pm-plugin-development:ext-outline-plugin) Agent validation failed: {bundle}
  expected_entries: {file_count}
  actual_entries: {assessments_logged}
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

  # Log assessment to assessments.jsonl (hash auto-generated)
  LOG_ASSESSMENT(plan_id, file_path, certainty, confidence, agent_name, reasoning, evidence)

  # Track counts for summary
  counts[certainty] += 1
```

**Key Points**:
1. **Full request context** - agents see the original request, not derived patterns
2. **Semantic reasoning** - agents reason about intent, not pattern match
3. **Context-aware** - agents can distinguish output specs from documentation examples
4. **Explicit reasoning** - every decision includes explanation
5. **Confidence assessment** - explicit numeric confidence drives certainty gate
6. **Traceability** - auto-generated hash IDs enable linking decisions across stages

## Usage in Analysis Step

The analysis step in `ext-outline-plugin` (Step 3, via workflow.md) spawns analysis agents with this contract:

```
Task: pm-plugin-development:ext-outline-component-agent
  Input:
    plan_id: migrate-json-to-toon
    component_type: skills
    request_text: "Migrate agent/command/skill outputs from JSON to TOON format"
    files: [list of skill file paths]
```

The parent workflow (ext-outline-plugin) spawns one agent instance per component type (skills, commands, agents) in parallel.

## Agent Implementing This Contract

| Agent | Component Types |
|-------|-----------------|
| `ext-outline-component-agent` | skills, commands, agents (via `component_type` parameter) |

The unified agent receives `component_type` as input and applies appropriate context for each type. See the agent definition for component-specific analysis context.
