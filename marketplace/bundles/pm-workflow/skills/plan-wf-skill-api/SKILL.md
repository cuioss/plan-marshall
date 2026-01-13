---
name: plan-wf-skill-api
description: Defines the unified API contracts for workflow skills. Workflow skills provide domain-agnostic operations that load domain knowledge from marshal.json.
allowed-tools: Read
---

# Plan Workflow Skill API

**Role**: API contract definition for workflow skills. This skill defines the interface contracts for the 5-phase workflow execution model.

**Key Principle**: Workflow skills are **domain-agnostic**. Domain knowledge comes from `module.skills_by_profile` (via `analyze-project-architecture`) and is selected during solution-outline phase when module is chosen.

**Visual Overview**: See [pm-workflow-architecture](../pm-workflow-architecture/SKILL.md) for high-level diagrams covering phases, agents, data layer, and skill loading patterns.

## 5-Phase Execution Model

See [pm-workflow-architecture:phases](../pm-workflow-architecture/standards/phases.md) for detailed visual diagrams.

| Phase | Agent | Purpose | Output |
|-------|-------|---------|--------|
| **init** | `plan-phase-agent phase=init` | Initialize plan | config.toon, status.toon, request.md |
| **outline** | `plan-phase-agent phase=outline` | Create solution outline | solution_outline.md |
| **plan** | `plan-phase-agent phase=plan` | Decompose into tasks | TASK-*.toon |
| **execute** | `plan-phase-agent phase=execute` | Run implementation | Modified project files |
| **finalize** | `plan-phase-agent phase=finalize` | Verify, commit, PR | Git commit, PR |

## Contract Standards

| Contract | Purpose | Document |
|----------|---------|----------|
| **Architecture Overview** | 5-phase model, component responsibilities, domain flow | [standards/architecture-overview.md](standards/architecture-overview.md) |
| **Plan-Init Skill** | Initialize plan and write config.toon | [standards/phase-init-contract.md](standards/phase-init-contract.md) |
| **Solution Outline Skill** | Request → Solution Outline with deliverables | [standards/phase-outline-contract.md](standards/phase-outline-contract.md) |
| **Task Plan Skill** | Solution Outline → Tasks with domain/profile | [standards/phase-plan-contract.md](standards/phase-plan-contract.md) |
| **Task Execution Skill** | Task execution with two-tier skill loading | [standards/phase-execute-contract.md](standards/phase-execute-contract.md) |
| **Plan-Finalize Skill** | Verification, findings triage, commit/PR | [standards/phase-finalize-contract.md](standards/phase-finalize-contract.md) |
| **Deliverable Contract** | Deliverable structure in solution outline | `pm-workflow:manage-solution-outline/standards/deliverable-contract.md` |
| **Task Contract** | Task structure with domain, profile, skills | `pm-workflow:manage-tasks/standards/task-contract.md` |
| **Extension API** | Domain-specific extensions for outline and triage | [standards/extension-api.md](standards/extension-api.md) |
| **Config TOON Format** | config.toon structure with domains and settings | `pm-workflow:manage-config/standards/config-toon-format.md` |
| **User Review Protocol** | Mandatory review before task creation | [standards/user-review-protocol.md](standards/user-review-protocol.md) |
| **Artifact Formats** | TOON file structures for plan artifacts | `pm-workflow-architecture:artifacts` |

## Routing Flow

```
Request → [init] → [outline] → User Review → [plan] → Tasks → [execute] → [finalize]
              ↓          ↓            ↓            ↓            ↓            ↓
         config.toon  solution     approval     TASK-*.toon   project    commit/PR
         status.toon  outline.md    gate        files         files
```

1. `plan-phase-agent phase=init` creates plan, writes config.toon and status.toon
2. `plan-phase-agent phase=outline` analyzes request, determines domains, creates deliverables
3. User approves solution outline (mandatory gate)
4. `plan-phase-agent phase=plan` creates tasks with domain, profile, skills fields
5. `plan-phase-agent phase=execute` executes tasks with two-tier skill loading
6. `plan-phase-agent phase=finalize` runs verification, triages findings, commits/creates PR

## Thin Agent Pattern

See [pm-workflow-architecture:agents](../pm-workflow-architecture/standards/agents.md) for visual diagrams of agent structure and delegation.

All phases use a single parameterized agent (`plan-phase-agent`) with different `phase` parameters. This results in 5 distinct invocation modes sharing one implementation. The agent loads system defaults + phase-specific workflow skill.

| Agent Call | Purpose | Skill Loading |
|------------|---------|---------------|
| `plan-phase-agent phase=init` | Initialize plan | `resolve-workflow-skill --phase init` |
| `plan-phase-agent phase=outline` | Create deliverables | `resolve-workflow-skill --phase outline` + extensions |
| `plan-phase-agent phase=plan` | Create tasks | `resolve-workflow-skill --phase plan` |
| `plan-phase-agent phase=execute` | Execute task | `resolve-workflow-skill --phase execute` + `task.skills` |
| `plan-phase-agent phase=finalize` | Verify and commit | `resolve-workflow-skill --phase finalize` + triage extensions |

## Domain Flow

Domains flow through the phases:

```
marshal.json (all domains) → outline (decides relevant) → config.toon.domains → plan/execute/finalize
```

| Phase | Domain Source | How Determined |
|-------|---------------|----------------|
| **outline** | All from marshal.json | Claude decides which are relevant |
| **plan** | From deliverable | Reads `deliverable.domain` |
| **execute** | From task | Reads `task.domain`, `task.profile` |
| **finalize** | From config.toon | Reads `config.toon.domains` |

## Traceability Flow

```
Request → Solution Outline (with Deliverables) → Tasks (each task references its deliverable number)
```

Each task maintains traceability to its source deliverable(s), enabling M:N relationships between deliverables and tasks.

---

## Implementation Requirements

Workflow skills must:

1. Be domain-agnostic (no hardcoded domain references)
2. Load domain knowledge from config.toon at runtime
3. Return `status` field in all outputs
4. Handle errors with `status: error` and `message`

---

## Script Execution Tracing

Workflow skills execute scripts via `execute-script.py`. For plan-scoped logging, skills MUST pass the plan context.

### Scripts with `--plan-id` Parameter

Scripts that accept `--plan-id` (manage-* scripts) use it for both logic AND logging:

```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks add \
  --plan-id {plan_id} --title "Task title"
```

### Scripts without `--plan-id` Parameter

Scripts that don't accept `--plan-id` (scan-*, analyze-*) use `--trace-plan-id` for logging only:

```bash
python3 .plan/execute-script.py plan-marshall:marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} --include-descriptions
```

The `--trace-plan-id` parameter is:
- Extracted by the executor for logging purposes
- Stripped before passing to the script (script never sees it)
- Enables plan-scoped logging in `.plan/plans/{plan_id}/script-execution.log`

---

## Integration

**Callers**:
- `/plan-marshall` → Unified command, delegates to plan-orchestrator
- `plan-orchestrator` → Routes phases, spawns plan-phase-agent

**Workflow Skill Resolution**:
- System workflow skills resolved via `resolve-workflow-skill --phase {phase}`
- Domain skills from `module.skills_by_profile` (selected during outline, propagated to tasks)
- Extensions resolved via `resolve-workflow-skill-extension --domain {domain} --type {type}`

**Agent** (single parameterized agent):
- `pm-workflow:plan-phase-agent` - Context isolation, loads system defaults + workflow skill

**Data Layer** (used by workflow skills):
- `pm-workflow:manage-plan-documents:manage-plan-documents` - Request document operations
- `pm-workflow:manage-solution-outline:manage-solution-outline` - Solution outline validation and queries
- `pm-workflow:manage-tasks:manage-tasks` - Task creation with deliverable references
- `pm-workflow:manage-config:manage-config` - Config.toon field access
- `pm-workflow:manage-lifecycle:manage-lifecycle` - Plan status and phase management
