# Test Case Format Standard

This document defines the format for workflow verification test cases.

## Directory Structure

Each test case is a directory under `workflow-verification/test-cases/`:

```
workflow-verification/test-cases/{test-id}/
├── test-definition.toon      # Required: Test metadata and trigger
├── expected-artifacts.toon   # Required: Expected outputs
├── criteria/
│   ├── semantic.md           # Required: LLM-as-judge criteria
│   └── decision-quality.md   # Optional: Decision quality criteria
└── golden/
    └── verified-result.md    # Required: Expert-verified reference
```

## Test Definition (test-definition.toon)

Defines the test case metadata and trigger configuration.

```toon
id: {test-id}
name: {Human-readable test name}
workflow_phase: {1-init|2-refine|3-outline|4-plan|5-execute|6-finalize|comma-separated}

trigger:
  command: {Command that triggers the workflow}
  args: {Command arguments}

setup_commands[N]:
  {setup command 1}
  {setup command 2}

cleanup:
  archive_plan: {true|false}
  delete_on_success: {true|false}
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier (kebab-case) |
| `name` | Yes | Human-readable description |
| `workflow_phase` | Yes | Phase(s) to verify (comma-separated). Passed to collect-artifacts.py `--phases` parameter. |
| `trigger.command` | Yes | Command to execute |
| `trigger.args` | No | Arguments for the command |
| `setup_commands` | No | Commands to run before trigger |
| `cleanup.archive_plan` | No | Archive plan after verification |
| `cleanup.delete_on_success` | No | Delete plan if verification passes |

### Workflow Phases

The 6-phase model supports verification at each stage:

| Phase | Artifacts Collected | Verification Checks |
|-------|---------------------|---------------------|
| `1-init` | config.toon, status.toon, request.md | Files exist, proper structure |
| `2-refine` | request.md, work.log | Clarifications present, [REFINE:*] log entries, domains in config |
| `3-outline` | solution_outline.md, deliverables, references.toon | Structure valid, deliverable count, affected files |
| `4-plan` | TASK-*.toon files | Tasks exist, match deliverables |
| `5-execute` | references.toon with modified files | Affected files tracked |
| `6-finalize` | git commit artifacts | (Not verified by script - use git commands) |

**Common combinations**:
- `3-outline,4-plan` - Verify outline and planning phases together
- `1-init,2-refine,3-outline` - Verify early phases including request refinement

## Expected Artifacts (expected-artifacts.toon)

Defines expected output files and their validation standards.

```toon
# Reference existing skill standards - do not duplicate
artifacts[N]{file,standard_ref}:
solution_outline.md,pm-workflow:manage-solution-outline:deliverable-contract
config.toon,pm-workflow:manage-config:config-schema
status.toon,pm-workflow:manage-lifecycle:status-schema
references.toon,pm-workflow:manage-references:references-schema

# Expected counts
deliverable_count: {N}
task_count: {N}

# Expected affected files
affected_files[N]:
{file_path_1}
{file_path_2}
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `artifacts` | Yes | Files to verify with standard references |
| `deliverable_count` | No | Expected number of deliverables |
| `task_count` | No | Expected number of tasks |
| `affected_files` | No | Expected affected files list |

## Semantic Criteria (criteria/semantic.md)

Natural language criteria for LLM-as-judge assessment.

```markdown
# Semantic Verification Criteria

## Scope Correctness

The workflow must analyze the correct scope:
- [ ] All component types mentioned in request are analyzed
- [ ] Scope boundaries are correctly determined
- [ ] Explicit scope decisions are logged

## Completeness

All expected items must be found:
- [ ] All affected files are identified
- [ ] No false negatives (missing items)
- [ ] Count matches expected range

## Decision Quality

Decisions must have clear rationale:
- [ ] Exclusion decisions are explicitly documented
- [ ] Rationale explains the "why" not just the "what"
- [ ] Decision trail is traceable in work log
```

## Decision Quality Criteria (criteria/decision-quality.md)

Specific expected decisions for this test case.

```markdown
# Expected Decisions

## Scope Decision

Expected: {description of expected scope decision}
Rationale should explain: {what the rationale should cover}

## Exclusion Decisions

If items are excluded, expect:
- {Item type}: {Expected reasoning}

## Aggregation/Split Decisions

If deliverables are combined or split:
- {Expected decision with reasoning}
```

## Golden Reference (golden/verified-result.md)

Expert-verified expected output for semantic comparison.

This file contains the CORRECT expected assessment that the workflow should produce. It serves as the reference for LLM-as-judge comparison.

Structure follows the actual workflow output format but represents the IDEAL result.

## Best Practices

1. **Use Standard References**: Don't duplicate validation rules - reference existing skill standards
2. **Be Specific**: Criteria should be concrete and verifiable
3. **Document Rationale**: Explain why certain decisions are expected
4. **Keep Golden Current**: Update golden reference when standards change
5. **Test the Test**: Run verification against known-good and known-bad outputs
