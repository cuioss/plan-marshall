# Architecture Overview

Contract specification for the 5-phase workflow execution model.

**Visual diagrams and detailed explanations**: See [pm-workflow-architecture](../../pm-workflow-architecture/SKILL.md). This document provides **API contracts** only.

---

## 5-Phase Execution Model

| Phase | Agent Call | Purpose | Output |
|-------|------------|---------|--------|
| **init** | `plan-phase-agent phase=init` | Initialize plan | config.toon, status.toon, request.md |
| **outline** | `plan-phase-agent phase=outline` | Create solution outline | solution_outline.md |
| **plan** | `plan-phase-agent phase=plan` | Decompose into tasks | TASK-*.toon |
| **execute** | `plan-phase-agent phase=execute task_id=TASK-001` | Run implementation | Modified project files |
| **finalize** | `plan-phase-agent phase=finalize` | Commit, PR, quality | Git commit, PR |

### Phase Transitions

| From | To | Trigger |
|------|------|---------|
| init | outline | Auto-continue (unless `stop-after=init`) |
| outline | plan | User approval of solution outline |
| plan | execute | Auto-continue (unless `stop-after=plan`) |
| execute | finalize | All tasks completed |
| finalize | execute | Findings detected → create fix tasks |
| finalize | COMPLETE | No findings |

---

## Component Responsibilities

For visual diagrams of component interactions, see:
- [pm-workflow-architecture:agents](../../pm-workflow-architecture/standards/agents.md) - Orchestrator and agent responsibilities

### Agent Input Contract

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `phase` | string | Yes | Phase: init, outline, plan, execute, finalize |
| `task_id` | string | Execute only | Task identifier (required when phase=execute), format: `TASK-{SEQ}` |
| `deliverable_id` | integer | Plan only | Deliverable sequence number (required when phase=plan), e.g., `1`, `2`, `3` |

### Workflow Skills

| Phase | Workflow Skill | Specification |
|-------|----------------|---------------|
| **init** | `pm-workflow:phase-init` | [phase-init-contract.md](phase-init-contract.md) |
| **outline** | `pm-workflow:phase-refine-outline` | [phase-outline-contract.md](phase-outline-contract.md) |
| **plan** | `pm-workflow:phase-refine-plan` | [phase-plan-contract.md](phase-plan-contract.md) |
| **execute** | `pm-workflow:phase-execute` | [phase-execute-contract.md](phase-execute-contract.md) |
| **finalize** | `pm-workflow:phase-finalize` | [phase-finalize-contract.md](phase-finalize-contract.md) |

---

## Domain Flow

For visual diagrams of domain propagation through phases, see:
- [pm-workflow-architecture:skill-loading](../../pm-workflow-architecture/standards/skill-loading.md) - Domain resolution and skill loading
- [pm-workflow-architecture:phases](../../pm-workflow-architecture/standards/phases.md) - Phase transitions

### Domain Source by Phase

| Phase | Domain Source | How Determined |
|-------|---------------|----------------|
| **init** | None | No domain knowledge needed |
| **outline** | All from marshal.json | Claude decides which are relevant (LLM reasoning) |
| **plan** | From deliverable | Script reads `deliverable.domain` |
| **execute** | From task | Script reads `task.domain`, `task.profile` |
| **finalize** | From config.toon | Script reads `config.toon.domains` |

### Skill Resolution

| Skill Type | Resolution | When Loaded |
|------------|------------|-------------|
| **System workflow** | `resolve-workflow-skill --phase {phase}` | Always (phase-based) |
| **Domain knowledge** | `module.skills_by_profile` (from architecture) | Outline → deliverable → task |
| **Extensions** | `resolve-workflow-skill-extension --domain {domain} --type {type}` | By workflow skill |

---

## Extension Model

Extensions add domain-specific knowledge without replacing workflow skills.

| Extension Type | Phase | Purpose |
|----------------|-------|---------|
| `outline` | outline | Domain detection, deliverable patterns |
| `triage` | finalize | Finding decision-making (fix/suppress/accept) |

### Extension Loading

```
Workflow skill reads config.toon.domains
       │
       └─ For each domain:
            └─ resolve-workflow-skill-extension --domain {domain} --type {type}
                  │
                  └─ Returns skill notation or null (if not configured)
```

See [extension-api.md](extension-api.md) for complete extension specification.

---

## Error Handling

### Error Response Contract

All errors MUST return structured TOON:

```toon
status: error
error_type: {skill_error|script_error|timeout|validation}
error: "Human-readable message"
recoverable: {true|false}
```

### Error Types

| Error Type | Handling | Status Update |
|------------|----------|---------------|
| **Agent failure** | Orchestrator captures error, updates status | `status: failed`, `error: {message}` |
| **Skill loading failure** | Agent returns error | `status: failed`, `error: skill_not_found` |
| **User abort** | Orchestrator updates status | `status: aborted` |
| **Script error** | Workflow skill captures, returns error | `status: failed`, `error: {script_output}` |

### Recovery

| Scenario | Recovery Action |
|----------|-----------------|
| Phase failed | Resume from failed phase after fix |
| Task failed | Resume continues from failed task |
| Partial completion | Status tracks completed vs pending tasks |

---

## Constraints

### Agent Constraints

| Constraint | Rationale |
|------------|-----------|
| Agents must NOT spawn other agents | Prevents complexity explosion, keeps control in orchestrator |
| Agents must NOT invoke commands | Commands are user-facing, agents are internal workers |
| Agents must be highly specialized | Single responsibility, predictable behavior |
| Domain is explicit input (not derived internally for multi-domain) | Clear contracts, testable |

### Architectural Constraints

| Constraint | Rationale |
|------------|-----------|
| Breaking changes are acceptable | New system, no backwards compatibility burden |
| Future domains expected (requirements, documentation) | Design must be extensible |
| Agent can have complexity when needed | Thin pattern is guideline, not dogma |

---

## Related Documents

- [phase-init-contract.md](phase-init-contract.md) - Init phase contract
- [phase-outline-contract.md](phase-outline-contract.md) - Outline phase contract
- [phase-plan-contract.md](phase-plan-contract.md) - Plan phase contract
- [phase-execute-contract.md](phase-execute-contract.md) - Execute phase contract
- [phase-finalize-contract.md](phase-finalize-contract.md) - Finalize phase contract
- [extension-api.md](extension-api.md) - Extension mechanism
- [deliverable-contract.md](../../manage-solution-outline/standards/deliverable-contract.md) - Deliverable structure
- [task-contract.md](../../manage-tasks/standards/task-contract.md) - Task structure
- [pm-workflow-architecture:artifacts](../../pm-workflow-architecture/standards/artifacts.md) - Artifact formats (TOON)
