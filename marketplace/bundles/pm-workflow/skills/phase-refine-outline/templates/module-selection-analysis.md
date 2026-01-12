# Module Selection Analysis Template

Template for documenting module selection reasoning in solution outlines.

## Usage

Include this analysis in the solution outline when module selection requires justification.

## Template

```markdown
## Module Selection Analysis

**Task**: {task description}

**Candidate Modules**:

| Module | Responsibility | Purpose | Relevance |
|--------|---------------|---------|-----------|
| {module-1} | "{from architecture}" | {purpose} | {HIGH/LOW} |
| {module-2} | "{from architecture}" | {purpose} | {HIGH/LOW} |

**Selected Module**: `{module}`

**Reasoning**: {Why this module matches the task based on responsibility and purpose}
```

## Field Descriptions

| Field | Source | Description |
|-------|--------|-------------|
| `task description` | Request document | The task being analyzed |
| `module` | `architecture info` | Module names from project |
| `responsibility` | `architecture module --name X` | From module data |
| `purpose` | `architecture module --name X` | library, application, extension, test |
| `Relevance` | LLM analysis | HIGH if responsibility/purpose match task |
| `Reasoning` | LLM analysis | Justification for selection |

## Selection Criteria

Score each module using weighted factors:

| Factor | Weight | Score Criteria |
|--------|--------|----------------|
| responsibility match | 3 | Keywords in task match responsibility |
| purpose fit | 2 | Purpose compatible with change type |
| key_packages match | 3 | Task aligns with package descriptions |
| dependency position | 2 | Correct layer for the change |

**Selection threshold**: Modules with weighted score >= 6 are candidates.
