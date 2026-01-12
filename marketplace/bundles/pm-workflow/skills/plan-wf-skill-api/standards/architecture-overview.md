# Architecture Overview

Comprehensive architecture contract for the 5-phase workflow execution model.

**Visual Overview**: For high-level visual diagrams, see [pm-workflow-architecture](../../pm-workflow-architecture/SKILL.md). This document provides detailed contract specifications.

---

## 5-Phase Execution Model

See [pm-workflow-architecture:phases](../../pm-workflow-architecture/standards/phases.md) for visual diagrams.

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

```
Orchestrator ──────────────────────────────────────────────────────────┐
     │                                                                 │
     │  Task: plan-phase-agent                                         │
     │    plan_id: {plan_id}                                           │
     │    phase: {init|outline|plan|execute|finalize}                  │
     │                                                                 │
     └─► plan-phase-agent ─────────┬─ 1. System Skills (general rules) │
              │                    │                                   │
              │                    └─ 2. Workflow Skill (by phase)     │
              │                               │                        │
              │                               ├─ 3. Domain-Knowledge   │
              │                               │                        │
              │                               └─ 4. Utility Skills     │
              │                                                        │
              └─ Context isolation                                     │
                                                                       │
───────────────────────────────────────────────────────────────────────┘
```

**Agent loads**: System defaults + Workflow skill (resolved by phase)
**Workflow skill loads**: Domain knowledge + Utility skills

### Orchestrator

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR SKILL                              │
│                    (plan-orchestrator/SKILL.md)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Responsibilities:                                                      │
│  ─────────────────                                                      │
│  1. Determine domains for each phase                                    │
│  2. Iterate over items (deliverables/tasks) when needed                 │
│  3. Call agent with explicit parameters                                 │
│  4. Handle phase transitions                                            │
│  5. Manage auto-continue logic                                          │
│                                                                         │
│  Does NOT:                                                              │
│  ──────────                                                             │
│  - Load domain knowledge (agent's job)                                  │
│  - Execute workflows (agent + skill's job)                              │
│  - Spawn nested agents (flat structure)                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Agent (Thin)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PHASE AGENT (THIN)                            │
│                      (plan-phase-agent.md)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Responsibilities:                                                      │
│  ─────────────────                                                      │
│  1. Load system defaults                                                │
│  2. Resolve and load workflow skill (phase-based only)                  │
│  3. Execute workflow                                                    │
│                                                                         │
│  Does NOT:                                                              │
│  ──────────                                                             │
│  - Load domain knowledge (workflow skill's job)                         │
│  - Determine which items to process (orchestrator's job)                │
│  - Iterate over multiple items (one call = one item)                    │
│  - Spawn other agents or commands                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Agent Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `phase` | string | Yes | Phase: init, outline, plan, execute, finalize |
| `task_id` | string | Execute only | Task identifier (required when phase=execute), format: `TASK-{SEQ}` |
| `deliverable_id` | integer | Plan only | Deliverable sequence number (required when phase=plan), e.g., `1`, `2`, `3` |

### Workflow Skills

Workflow skills are responsible for loading domain knowledge and executing the phase work.

| Phase | Workflow Skill | Specification |
|-------|----------------|---------------|
| **init** | `pm-workflow:phase-init` | [plan-init-skill-contract.md](plan-init-skill-contract.md) |
| **outline** | `pm-workflow:phase-refine-outline` | [solution-outline-skill-contract.md](solution-outline-skill-contract.md) |
| **plan** | `pm-workflow:phase-refine-plan` | [task-plan-skill-contract.md](task-plan-skill-contract.md) |
| **execute** | `pm-workflow:phase-execute` | [task-execution-skill-contract.md](task-execution-skill-contract.md) |
| **finalize** | `pm-workflow:phase-finalize` | [plan-finalize-skill-contract.md](plan-finalize-skill-contract.md) |

---

## Domain Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  marshal.json                                                            │
│  ────────────                                                            │
│  skill_domains: [java, javascript, plan-marshall-plugin-dev, requirements] │
│                      │                                                   │
│                      │ all possible domains (project-level)              │
│                      ▼                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  OUTLINE (decides which domains are relevant)                      │  │
│  │                                                                    │  │
│  │  Output: solution_outline.md, config.toon.domains=[java]           │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                      │                                                   │
│                      │ for each deliverable                              │
│                      ▼                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  PLAN (reads domain from deliverable)                              │  │
│  │                                                                    │  │
│  │  Output: TASK-*.toon (inherits domain from deliverable)            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                      │                                                   │
│                      │ for each task                                     │
│                      ▼                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  EXECUTE (reads domain + profile from task)                        │  │
│  │                                                                    │  │
│  │  Output: Modified project files                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                      │                                                   │
│                      │ all tasks completed                               │
│                      ▼                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  FINALIZE (reads domains from config.toon)                         │  │
│  │                                                                    │  │
│  │  Output: Git commit, PR (or fix tasks)                             │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Domain Source by Phase

| Phase | Domain Source | How Determined |
|-------|---------------|----------------|
| **init** | None | No domain knowledge needed |
| **outline** | All from marshal.json | Claude decides which are relevant (LLM reasoning) |
| **plan** | From deliverable | Script reads `deliverable.domain` |
| **execute** | From task | Script reads `task.domain`, `task.profile` |
| **finalize** | From config.toon | Script reads `config.toon.domains` |

### config.toon.domains: Intelligent Decision Output

`config.toon.domains` is the OUTPUT of outline's intelligent decision, not a blind copy from marshal.json.

```
marshal.json (project-level)
─────────────────────────────
skill_domains: [java, javascript, plan-marshall-plugin-dev, requirements, docs]
      │
      │ all possible domains
      ▼
┌───────────────────────────────────────────────────────────────────┐
│  OUTLINE analyzes request:                                        │
│  "Add user authentication to the Java backend"                    │
│                                                                   │
│  Decision: Only java is relevant for this task                    │
│  (javascript, plan-marshall-plugin-dev, requirements, docs not needed) │
└───────────────────────────────────────────────────────────────────┘
      │
      │ writes intelligent subset
      ▼
config.toon (plan-level)
─────────────────────────
domains: [java]  ← OUTPUT of outline's analysis
```

**System domain exclusion**: The `system` domain is **never** included in `config.toon.domains`:
- `system` provides base/default skills loaded by agents (Tier 1)
- `config.toon.domains` contains only user-facing domains (java, javascript, etc.)
- System skills are loaded implicitly via `skill_domains_get_defaults("system")`

---

## Skill Resolution

### System vs Domain Skills

| Skill Type | Resolution | When Loaded |
|------------|------------|-------------|
| **System workflow** | `resolve-workflow-skill --phase {phase}` | Always (phase-based) |
| **Domain knowledge** | `module.skills_by_profile` (from architecture) | Outline → deliverable → task |
| **Extensions** | `resolve-workflow-skill-extension --domain {domain} --type {type}` | By workflow skill |

### Two-Tier Skill Loading (Execute Phase)

See [pm-workflow-architecture:skill-loading](../../pm-workflow-architecture/standards/skill-loading.md) for detailed visual diagrams of skill resolution flow.

| Tier | Source | When Loaded |
|------|--------|-------------|
| **Tier 1** | System skills | Agent loads automatically |
| **Tier 2** | `task.skills` array | Agent loads from task file |

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

- [plan-init-skill-contract.md](plan-init-skill-contract.md) - Init phase contract
- [solution-outline-skill-contract.md](solution-outline-skill-contract.md) - Outline phase contract
- [task-plan-skill-contract.md](task-plan-skill-contract.md) - Plan phase contract
- [task-execution-skill-contract.md](task-execution-skill-contract.md) - Execute phase contract
- [plan-finalize-skill-contract.md](plan-finalize-skill-contract.md) - Finalize phase contract
- [extension-api.md](extension-api.md) - Extension mechanism
- [deliverable-contract.md](../../manage-solution-outline/standards/deliverable-contract.md) - Deliverable structure
- [task-contract.md](task-contract.md) - Task structure
