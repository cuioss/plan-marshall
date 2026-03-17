# Architecture Overview

Contract specification for the 6-phase workflow execution model.

**Visual diagrams and detailed explanations**: See [ref-workflow-architecture](../../ref-workflow-architecture/SKILL.md). This document provides **API contracts** only.

---

## 6-Phase Execution Model

| Phase | Agent Call | Purpose | Output |
|-------|------------|---------|--------|
| **1-init** | `plan-phase-agent phase=1-init` | Initialize plan | status.toon, request.md, references.json |
| **2-refine** | `plan-phase-agent phase=2-refine` | Clarify request | Refined request with confidence score |
| **3-outline** | `plan-phase-agent phase=3-outline` | Create solution outline | solution_outline.md |
| **4-plan** | `plan-phase-agent phase=4-plan` | Decompose into tasks | TASK-*.toon |
| **5-execute** | `plan-phase-agent phase=5-execute task_id=TASK-001` | Run implementation + verification | Modified + verified project files |
| **6-finalize** | `plan-phase-agent phase=6-finalize` | Commit, PR, automated review | Git commit, PR |

### Phase Transitions

| From | To | Trigger |
|------|------|---------|
| 1-init | 2-refine | Auto-continue |
| 2-refine | 3-outline | Confidence threshold reached |
| 3-outline | 4-plan | User approval of solution outline |
| 4-plan | 5-execute | Auto-continue (unless `stop-after=4-plan`) |
| 5-execute | 6-finalize | All tasks completed + verification passed |
| 5-execute | 5-execute | Findings detected → triage + create fix tasks |
| 6-finalize | COMPLETE | Commit/PR done (or no findings) |
| 6-finalize | 5-execute | Findings detected → create fix tasks |

---

## User Review Gate

The transition from **3-outline** to **4-plan** requires mandatory user approval. This gate ensures alignment on deliverables before committing to implementation scope.

### Protocol Flow

```
[Solution Outline Agent] → [Command displays outline] → [User Review] → [Task Plan Agent]
                                                              ↓
                                                    [Request changes] → [Re-invoke Solution Outline Agent]
```

### Command Responsibility

After the solution outline agent completes, the `/plan-marshall` command MUST:

**Step 1: Display the Solution Outline**

```markdown
## Solution Outline Created

**Review your solution outline**: .plan/plans/{plan_id}/solution_outline.md

Please review the deliverables and architecture before proceeding.
```

**Step 2: Ask User via AskUserQuestion**

Present options to the user:

| Option | Description | Next Action |
|--------|-------------|-------------|
| "Proceed to create tasks" | User approves outline | Continue to task plan agent |
| "Request changes" | User wants modifications | Capture feedback, re-invoke solution outline agent |

**Step 3: Loop Until Approval**

This halt is **NOT OPTIONAL**. Task creation MUST NOT proceed without user confirmation.

```
while not approved:
    response = AskUserQuestion("Review and approve or request changes")
    if response == "Proceed":
        approved = true
    else:
        write each feedback point as Q-Gate finding (source: user_review)
        re-invoke 3-outline phase (reads findings at Step 1)
        display updated outline
```

### Re-Invocation via Q-Gate Findings

When user requests changes, write each feedback point as a Q-Gate finding and re-invoke the outline phase:

**Write findings**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 3-outline --source user_review \
  --type triage --title "User: {feedback summary}" \
  --detail "{full feedback text}"
```

**Re-invoke**: The phase-3-outline skill reads unresolved findings at its Step 1 (Check for Unresolved Q-Gate Findings) and addresses them before re-running.

### Example Interaction

```
Command: "Solution outline created with 5 deliverables. Review .plan/plans/auth-feature/solution_outline.md"
User: "Deliverable 3 should use CDI instead of Spring - please update"

Command: Writes Q-Gate finding: "User: Use CDI instead of Spring for Deliverable 3"
Command: Re-invokes phase-3-outline (reads finding at Step 1)
Agent: Updates solution_outline.md, returns {status: success, deliverable_count: 5}

Command: "Solution outline updated. Please review changes."
User: "Looks good, proceed to create tasks"

Command: Invokes task plan agent
```

### Anti-Patterns

| Pattern | Problem |
|---------|---------|
| Auto-proceeding to task creation | User has no chance to review scope |
| Skipping review for "simple" plans | Definition of "simple" is subjective |
| Single-shot feedback | User may need multiple iterations |
| Not displaying outline location | User can't find what to review |

---

## Component Responsibilities

For visual diagrams of component interactions, see:
- [ref-workflow-architecture:agents](../../ref-workflow-architecture/standards/agents.md) - Orchestrator and agent responsibilities

### Agent Input Contract

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `phase` | string | Yes | Phase: 1-init, 2-refine, 3-outline, 4-plan, 5-execute, 6-finalize |
| `task_id` | string | 5-execute only | Task identifier (required when phase=5-execute), format: `TASK-{SEQ}` |
| `deliverable_id` | integer | 4-plan only | Deliverable sequence number (required when phase=4-plan), e.g., `1`, `2`, `3` |

### Workflow Skills

| Phase | Workflow Skill | Specification |
|-------|----------------|---------------|
| **1-init** | `plan-marshall:phase-1-init` | `plan-marshall:phase-1-init/SKILL.md` |
| **2-refine** | `plan-marshall:phase-2-refine` | `plan-marshall:phase-2-refine/SKILL.md` |
| **3-outline** | `plan-marshall:phase-3-outline` | `plan-marshall:phase-3-outline/SKILL.md` |
| **4-plan** | `plan-marshall:phase-4-plan` | `plan-marshall:phase-4-plan/SKILL.md` |
| **5-execute** | `plan-marshall:phase-5-execute` | `plan-marshall:phase-5-execute/SKILL.md` |
| **6-finalize** | `plan-marshall:phase-6-finalize` | `plan-marshall:phase-6-finalize/SKILL.md` |

---

## Domain Flow

For visual diagrams of domain propagation through phases, see:
- [ref-workflow-architecture:skill-loading](../../ref-workflow-architecture/standards/skill-loading.md) - Domain resolution and skill loading
- [ref-workflow-architecture:phases](../../ref-workflow-architecture/standards/phases.md) - Phase transitions

### Domain Source by Phase

| Phase | Domain Source | How Determined |
|-------|---------------|----------------|
| **init** | None | No domain knowledge needed |
| **outline** | All from marshal.json | Claude decides which are relevant (LLM reasoning) |
| **plan** | From deliverable | Script reads `deliverable.domain` |
| **execute** | From task | Script reads `task.domain`, `task.profile` |
| **finalize** | From references.json | Script reads `references.json.domains` |

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
| `triage` | 5-execute, 6-finalize | Finding decision-making (fix/suppress/accept) |

### Extension Loading

```
Workflow skill reads references.json.domains
       │
       └─ For each domain:
            └─ resolve-workflow-skill-extension --domain {domain} --type {type}
                  │
                  └─ Returns skill notation or null (if not configured)
```

See [extension-contract.md](extension-contract.md) for complete extension specification.

---

## Error Handling

### Error Response Contract

All errors MUST return structured TOON:

```toon
status	error
error_type	{skill_error|script_error|timeout|validation}
error	"Human-readable message"
recoverable	{true|false}
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

- `plan-marshall:phase-1-init/SKILL.md` - Init phase skill
- `plan-marshall:phase-2-refine/SKILL.md` - Refine phase skill
- `plan-marshall:phase-3-outline/SKILL.md` - Outline phase skill
- `plan-marshall:phase-4-plan/SKILL.md` - Plan phase skill
- `plan-marshall:phase-5-execute/SKILL.md` - Execute phase skill
- `plan-marshall:phase-6-finalize/SKILL.md` - Finalize phase skill
- [extension-contract.md](extension-contract.md) - Extension mechanism
- [deliverable-contract.md](../../manage-solution-outline/standards/deliverable-contract.md) - Deliverable structure
- [task-contract.md](../../manage-tasks/standards/task-contract.md) - Task structure
- [ref-workflow-architecture:artifacts](../../ref-workflow-architecture/standards/artifacts.md) - Artifact formats (TOON)
