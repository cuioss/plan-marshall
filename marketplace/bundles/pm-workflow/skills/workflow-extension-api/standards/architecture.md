# Architecture Overview

Contract specification for the 7-phase workflow execution model.

**Visual diagrams and detailed explanations**: See [workflow-architecture](../../workflow-architecture/SKILL.md). This document provides **API contracts** only.

---

## 7-Phase Execution Model

| Phase | Agent Call | Purpose | Output |
|-------|------------|---------|--------|
| **1-init** | `plan-phase-agent phase=1-init` | Initialize plan | config.toon, status.toon, request.md |
| **2-refine** | `plan-phase-agent phase=2-refine` | Clarify request | Refined request with confidence score |
| **3-outline** | `plan-phase-agent phase=3-outline` | Create solution outline | solution_outline.md |
| **4-plan** | `plan-phase-agent phase=4-plan` | Decompose into tasks | TASK-*.toon |
| **5-execute** | `plan-phase-agent phase=5-execute task_id=TASK-001` | Run implementation | Modified project files |
| **6-verify** | `plan-phase-agent phase=6-verify` | Verify quality | Verification results |
| **7-finalize** | `plan-phase-agent phase=7-finalize` | Commit, PR, triage | Git commit, PR |

### Phase Transitions

| From | To | Trigger |
|------|------|---------|
| 1-init | 2-refine | Auto-continue |
| 2-refine | 3-outline | Confidence threshold reached |
| 3-outline | 4-plan | User approval of solution outline |
| 4-plan | 5-execute | Auto-continue (unless `stop-after=4-plan`) |
| 5-execute | 6-verify | All tasks completed |
| 6-verify | 7-finalize | All verification passed |
| 6-verify | 5-execute | Findings detected → create fix tasks |
| 7-finalize | COMPLETE | Commit/PR done (or no findings) |
| 7-finalize | 5-execute | Findings detected → create fix tasks |

---

## Component Responsibilities

For visual diagrams of component interactions, see:
- [workflow-architecture:agents](../../workflow-architecture/standards/agents.md) - Orchestrator and agent responsibilities

### Agent Input Contract

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `phase` | string | Yes | Phase: 1-init, 2-refine, 3-outline, 4-plan, 5-execute, 6-verify, 7-finalize |
| `task_id` | string | 5-execute only | Task identifier (required when phase=5-execute), format: `TASK-{SEQ}` |
| `deliverable_id` | integer | 4-plan only | Deliverable sequence number (required when phase=4-plan), e.g., `1`, `2`, `3` |

### Workflow Skills

| Phase | Workflow Skill | Specification |
|-------|----------------|---------------|
| **1-init** | `pm-workflow:phase-1-init` | `pm-workflow:phase-1-init/SKILL.md` |
| **2-refine** | `pm-workflow:phase-2-refine` | `pm-workflow:phase-2-refine/SKILL.md` |
| **3-outline** | `pm-workflow:phase-3-outline` | [phase-3-outline-contract.md](phase-3-outline-contract.md) |
| **4-plan** | `pm-workflow:phase-4-plan` | [phase-4-plan-contract.md](phase-4-plan-contract.md) |
| **5-execute** | `pm-workflow:phase-5-execute` | `pm-workflow:manage-tasks/standards/task-execution-contract.md` |
| **6-verify** | `pm-workflow:phase-6-verify` | [phase-6-verify-contract.md](phase-6-verify-contract.md) |
| **7-finalize** | `pm-workflow:phase-7-finalize` | [phase-7-finalize-contract.md](phase-7-finalize-contract.md) |

---

## Domain Flow

For visual diagrams of domain propagation through phases, see:
- [workflow-architecture:skill-loading](../../workflow-architecture/standards/skill-loading.md) - Domain resolution and skill loading
- [workflow-architecture:phases](../../workflow-architecture/standards/phases.md) - Phase transitions

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
| `outline` | 3-outline | Domain detection, deliverable patterns |
| `triage` | 6-verify, 7-finalize | Finding decision-making (fix/suppress/accept) |

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

- `pm-workflow:phase-1-init/SKILL.md` - Init phase skill
- `pm-workflow:phase-2-refine/SKILL.md` - Refine phase skill
- [phase-3-outline-contract.md](phase-3-outline-contract.md) - Outline phase contract
- [phase-4-plan-contract.md](phase-4-plan-contract.md) - Plan phase contract
- `pm-workflow:manage-tasks/standards/task-execution-contract.md` - Task execution contract
- [phase-6-verify-contract.md](phase-6-verify-contract.md) - Verify phase contract
- [phase-7-finalize-contract.md](phase-7-finalize-contract.md) - Finalize phase contract
- [extension-api.md](extension-api.md) - Extension mechanism
- [deliverable-contract.md](../../manage-solution-outline/standards/deliverable-contract.md) - Deliverable structure
- [task-contract.md](../../manage-tasks/standards/task-contract.md) - Task structure
- [workflow-architecture:artifacts](../../workflow-architecture/standards/artifacts.md) - Artifact formats (TOON)
