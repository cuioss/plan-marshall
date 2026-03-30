# Component Analysis Agent Contract

Interface contract for domain-specific component analysis agents spawned during the outline phase. Agents implementing this contract analyze component files against a request using semantic reasoning and persist assessments for downstream deliverable creation.

## Implementors

- `pm-plugin-development:ext-outline-component-agent` — marketplace plugin components (skills, agents, commands)

## Invocation Context

```
phase-3-outline (Complex Track)
  → Step 9: Resolve domain or generic change-type instructions
    → domain outline skill (e.g., ext-outline-workflow)
      → Task: {component-analysis-agent}   ← this contract
```

The agent runs as a Task (subagent) spawned by the domain outline skill. It has context isolation and cannot spawn further agents.

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier for assessment logging |
| `component_type` | string | Yes | Type of components: `skills`, `agents`, `commands`, or `tests` |
| `request_text` | string | Yes | The clarified request describing what needs to be changed |
| `files` | list | Yes | Explicit file paths to analyze (from inventory scan) |

### Prompt Structure

The parent workflow provides explicit numbered file sections:

```
## Files to Analyze

Component Type: {component_type}
Request: {request_text}

### File 1: {path}
**1a. Analyze**: [instructions]

### File 2: {path}
...
```

## Task Steps

For each file in the provided list, in order:

1. **Read** the file at the specified path using the Read tool
2. **Analyze** the file content against the request, applying component-type-specific context
3. **Classify** as CERTAIN_INCLUDE, CERTAIN_EXCLUDE, or UNCERTAIN
4. **Assess confidence** (0-100)
5. **Log** the assessment immediately via `plan-marshall:manage-assessments:manage-assessments add`
6. **Track counts** for the final summary

Each assessment MUST be logged before moving to the next file.

## Classification Rules

| Certainty | Meaning | Typical Confidence |
|-----------|---------|-------------------|
| `CERTAIN_INCLUDE` | File clearly needs modification for this request | 80-100 |
| `CERTAIN_EXCLUDE` | File clearly does not need modification | 80-100 |
| `UNCERTAIN` | Ambiguous — requires human resolution | 20-79 |

## Assessment Logging

Each assessment MUST be persisted via:

```bash
python3 .plan/execute-script.py plan-marshall:manage-assessments:manage-assessments add \
  --plan-id {plan_id} --file-path {file_path} \
  --certainty {CERTAINTY} --confidence {CONFIDENCE} \
  --agent {agent_name}/{component_type} \
  --detail "{reasoning}" --evidence "{evidence}"
```

## Output Format

Single TOON summary — no other text output. All analysis detail is persisted to assessments.jsonl.

```toon
status: success
component_type: {component_type}
bundle: {bundle}
total_analyzed: {count}
certain_include: {count}
certain_exclude: {count}
uncertain: {count}
assessments_logged: {count}
```

## Critical Rules

1. **No text output** except the final TOON summary — all reasoning goes to assessments.jsonl
2. **Sequential processing** — log each assessment before proceeding to the next file
3. **Script-only logging** — use `plan-marshall:manage-assessments:manage-assessments add` exclusively
4. **No ad-hoc discovery** — analyze only the files provided in the input list
5. **Read tool for component files only** — use `manage-files` scripts for `.plan/` file operations
6. **No agent spawning** — runs as a leaf-level Task (subagent constraint)
