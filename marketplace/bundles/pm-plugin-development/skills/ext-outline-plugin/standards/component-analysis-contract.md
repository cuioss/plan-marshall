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

All analysis agents MUST return this structure:

```toon
status: success
bundle: {bundle}
total_analyzed: {count}
affected_count: {count}
not_affected_count: {count}

findings[N]{file_path,status,reasoning,evidence}:
  {path},affected,Component has JSON output specification that needs migration,Lines 45-50 contain JSON in Output section
  {path},not_affected,JSON is workflow documentation not component output,Lines 30-40 show JSON as example in workflow
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `status` | enum | `success` or `error` |
| `bundle` | str | Bundle that was analyzed |
| `total_analyzed` | int | Must equal file count from filter script |
| `affected_count` | int | Files that need modification |
| `not_affected_count` | int | Files that don't need modification |
| `findings` | table | One row per file analyzed |

### Finding Fields

| Field | Description |
|-------|-------------|
| `file_path` | Full path to analyzed file |
| `status` | `affected` or `not_affected` |
| `reasoning` | Why the component does or does not need modification for this request |
| `evidence` | Specific line numbers, section names, or content excerpts |

## Validation Rules

The calling workflow MUST validate agent output:

1. **Completeness**: `findings.length == total_analyzed` - no skipping
2. **Reasoning required**: Each finding MUST have `reasoning` populated
3. **Evidence required**: Each finding MUST have `evidence` populated
4. **Consistency**: `affected_count + not_affected_count == total_analyzed`
5. **Status check**: `status` must be `success` for results to be used

### Validation Failure Handling

If validation fails:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} ERROR "[VALIDATION] (pm-plugin-development:ext-outline-plugin) Agent validation failed: {bundle}
  expected_findings: {file_count}
  actual_findings: {findings.length}
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

### Analysis Approach (Semantic Reasoning)

For each file, answer the question: **"Does this component need to be modified to fulfill the request?"**

```
FOR each file_path from filter script:
  content = READ(file_path)

  # Semantic Analysis
  # Consider the request intent and the component's actual content

  reasoning = REASON_ABOUT(
    request_text,
    content,
    questions=[
      "What is this component's purpose?",
      "Does it have content relevant to the request?",
      "Would modifying it help fulfill the request?",
      "Is there context that makes it NOT applicable?"
    ]
  )

  # Decision based on semantic understanding
  IF component needs modification for request:
    status = "affected"
    evidence = specific lines/sections that need change
  ELSE:
    status = "not_affected"
    evidence = why the component is not applicable

  findings.append({file_path, status, reasoning, evidence})
```

**Key Points**:
1. **Full request context** - agents see the original request, not derived patterns
2. **Semantic reasoning** - agents reason about intent, not pattern match
3. **Context-aware** - agents can distinguish output specs from documentation examples
4. **Explicit reasoning** - every decision includes explanation

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
