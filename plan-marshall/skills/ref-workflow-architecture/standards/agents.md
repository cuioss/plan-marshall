# Thin Agent Pattern

The plan-marshall bundle uses thin agents that delegate to skills for actual work.

---

## Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                         THIN AGENT PATTERN                                  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │   ORCHESTRATOR                                                       │  │
│  │   ════════════                                                       │  │
│  │                                                                      │  │
│  │   /plan-marshall action=outline plan=X                                │  │
│  │         │                                                            │  │
│  │         ▼                                                            │  │
│  │   ┌──────────────────────────────────────────────────────────────┐  │  │
│  │   │                         SKILL                               │  │  │
│  │   │                         ═════                               │  │  │
│  │   │                                                              │  │  │
│  │   │   1. Load system skills                                      │  │  │
│  │   │   2. Load domain extension skills                            │  │  │
│  │   │   3. Spawn Task agents (if needed)                           │  │  │
│  │   │   4. Aggregate results                                       │  │  │
│  │   │                                                              │  │  │
│  │   │   ┌────────────────────────────────────────────────────────┐│  │  │
│  │   │   │                  SPAWNED AGENTS                        ││  │  │
│  │   │   │                  ══════════════                        ││  │  │
│  │   │   │                                                        ││  │  │
│  │   │   │   • Run in parallel (isolated context)                 ││  │  │
│  │   │   │   • Analyze files                                      ││  │  │
│  │   │   │   • Return structured results                          ││  │  │
│  │   │   │                                                        ││  │  │
│  │   │   └────────────────────────────────────────────────────────┘│  │  │
│  │   │                                                              │  │  │
│  │   └──────────────────────────────────────────────────────────────┘  │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Invocation Patterns: Skill vs Task

> **This document is the single source of truth (SSOT) for the leaf/dispatch-topology invariant.** The normative rule is: *a dispatched subagent is a leaf — it cannot spawn further subagents; all cross-envelope `Task:` dispatch originates only from the main-context orchestrator.* Every other document in the marketplace cross-references this section rather than restating the rule or duplicating the diagrams below. When a workflow step running inside a dispatched envelope needs a further dispatch, the leaf returns a signal to the orchestrator, which owns the dispatch.

Understanding when to use `Skill:` vs `Task:` is critical for proper context management.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                    INVOCATION PATTERNS                                      │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  Skill: skill-name                                                   │  │
│  │  ════════════════                                                    │  │
│  │  • Stays in CALLER'S context                                         │  │
│  │  • Inherits caller's ability to spawn Task agents                    │  │
│  │  • No context isolation                                              │  │
│  │  • Use for: phase skills, domain extensions                          │  │
│  │                                                                      │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │                                                                      │  │
│  │  Task: agent-name                                                    │  │
│  │  ═══════════════                                                     │  │
│  │  • Creates NEW subagent context                                      │  │
│  │  • CANNOT spawn further Task agents (subagent constraint)            │  │
│  │  • Full context isolation                                            │  │
│  │  • Use for: leaf-level analysis, focused work                        │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  KEY CONSTRAINT: Subagents cannot spawn other subagents              │  │
│  │  ═══════════════════════════════════════════════════                 │  │
│  │                                                                      │  │
│  │  Main Conversation                                                   │  │
│  │    → Skill: phase-3-outline      ← STAYS in main context             │  │
│  │      → Skill: ext-outline-workflow ← STAYS in main context             │  │
│  │        → Task: analysis-agent    ← CAN spawn (from main context) PASS   │  │
│  │                                                                      │  │
│  │  Main Conversation                                                   │  │
│  │    → Task: some-agent            ← Creates SUBAGENT context          │  │
│  │      → Skill: some-skill         ← In subagent context               │  │
│  │        → Task: other-agent       ← CANNOT spawn (subagent) ✗         │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Decision Guide (canonical)

This table is the canonical rule for choosing `Skill:` vs `Task:`. A workflow whose logic requires a further `Task:` dispatch MUST run from the main context (via `Skill:`), because a dispatched subagent is a leaf and cannot spawn subagents.

| Scenario | Use | Reason |
|----------|-----|--------|
| Workflow needs `AskUserQuestion` against the user | `Skill:` (main context) | Subagents cannot reach the user |
| Workflow spawns further `Task:` dispatches internally | `Skill:` (main context) | Subagents cannot spawn subagents — the dispatch must originate from the orchestrator |
| Workflow is a focused, self-contained LLM job with a return-TOON contract | `Task: execution-context-{level}` | Pinned model/effort per role key, isolated context |
| Per-iteration parallel work (one envelope per input item) | `Task:` fan-out from the orchestrator | Only when each subagent runs independently; the fan-out originates from the main context |
| A leaf envelope reaches a step that calls for a further dispatch | return a signal to the orchestrator | The leaf does NOT dispatch; the orchestrator reads the return signal and owns the dispatch |

### Dispatch-overload note: in-context `Skill:` load is NOT a `Task:` dispatch

The word "dispatch" is overloaded — guard against reading every `execute-task` reference as a per-task `Task:` subagent dispatch. The `phase-5-execute` envelope LOADS `execute-task` **in-context** once per task (a `Skill:` load — leaf-legal, inheriting no new dispatch capability and spawning no subagent), which is categorically distinct from a `Task:` subagent dispatch. A leaf must therefore **never** return a `leaf_cannot_dispatch_execute_task` signal: loading `execute-task` is an in-context `Skill:` load the leaf performs itself, not a dispatch it needs the orchestrator to perform.

The same note fixes the granularity framing. The phase-5-execute dispatch unit is **budget-bounded** — explicitly NEITHER per-task NOR per-deliverable: one `execution-context` envelope greedily runs the task loop over as many tasks as the per-task budget reserve permits (bundling several small deliverables into one envelope and possibly spanning a single large deliverable across several envelopes), loading `execute-task` in-context per task, and yields to the orchestrator only at a TASK boundary (budget sentinel / `triage_required` / `baseline_drift`). Deliverable boundaries govern the Step 10 per-deliverable commit + focused-build **sub-events**, which fire within OR across envelopes and are **NOT** dispatch boundaries.

---

## Agent Inventory

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                      1 AGENT (plan-marshall bundle)                         │
│                                                                             │
│  ┌──────────────────────┬────────────────────────────────────────────────┐ │
│  │ AGENT                │ PURPOSE                                        │ │
│  ├──────────────────────┼────────────────────────────────────────────────┤ │
│  │                      │                                                │ │
│  │ execution-context    │ Generic dispatcher                             │ │
│  │                      │ • Loads persona-plan-marshall-agent implicitly    │ │
│  │                      │ • Loads caller-specified skills[] in order     │ │
│  │                      │ • Reads + executes the prompt-body `workflow`  │ │
│  │                      │   doc (or `instructions`) to completion        │ │
│  │                      │ • Returns the workflow's declared TOON         │ │
│  │                      │                                                │ │
│  │                      │ Seven emitted variants per ordinal level       │ │
│  │                      │ (level-1…level-7 + canonical inherit) drive    │ │
│  │                      │ every plan-marshall Task:                      │ │
│  │                      │ invocation. Dispatch site resolves the         │ │
│  │                      │ target via `manage-config effort               │ │
│  │                      │ resolve-target --role <key>`.                  │ │
│  │                      │                                                │ │
│  └──────────────────────┴────────────────────────────────────────────────┘ │
│                                                                             │
│  Workflow docs are addressed via `{bundle}:{skill}/workflow/{file}.md` or  │
│  `{bundle}:{skill}/SKILL.md` notation; the dispatcher Read()s the resolved │
│  path and follows it as the workflow body.                                 │
│                                                                             │
│  NOTE: Phases 2-refine, 3-outline, and 5-execute may also load skills     │
│  directly in main context (no Task: dispatch) when the workflow needs    │
│  AskUserQuestion or extensive sub-dispatch.                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

The pm-plugin-development bundle defines zero agents — its workflows are dispatched through `plan-marshall:execution-context` like every other workflow in the marketplace, with the workflow body loaded from `pm-plugin-development:{skill}/workflow/{file}.md`.

---

## Agent Structure

Each agent follows the same pattern:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                      AGENT STRUCTURE TEMPLATE                               │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  ---                                                                 │  │
│  │  name: {agent-name}                                                  │  │
│  │  description: {what it does}                                         │  │
│  │  tools: Read, Bash, ...                                              │  │
│  │  implements: plan-marshall:extension-api/standards/...               │  │
│  │  ---                                                                 │  │
│  │                                                                      │  │
│  │  # {Agent Name}                                                      │  │
│  │                                                                      │  │
│  │  ## Input                                                            │  │
│  │  - Parameters received from caller                                   │  │
│  │                                                                      │  │
│  │  ## Task                                                             │  │
│  │  - Steps to perform                                                  │  │
│  │                                                                      │  │
│  │  ## Output                                                           │  │
│  │  - TOON format with status field                                     │  │
│  │                                                                      │  │
│  │  ## Critical Rules                                                   │  │
│  │  - Constraints on behavior                                           │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Constraints

**MUST NOT:**
- Use Read/Write/Edit on `.plan/plans/` files
- Use cat/head/tail/ls on `.plan/` directory
- Spawn other agents (subagent constraint)
- Invoke commands (commands are user-facing)
- Hardcode skill names (must resolve from marshal.json)
- Cross scope boundaries (the workflow doc declares its scope; the dispatcher does not extend it)

**MUST DO:**
- Access `.plan/` files ONLY via execute-script.py
- Load system skills (Step 0) before any action
- Resolve workflow skill from marshal.json
- Delegate to skill for actual work
- Return structured TOON output
- Log skill loading decisions

---

## Related

- [skill-loading.md](skill-loading.md) — Two-tier skill loading
- [phases.md](phases.md) — 6-phase model
- [call-graph.md](call-graph.md) — Holistic visual call graph for every dispatch path starting from `plan-marshall` (Mermaid diagrams: per-phase detail, 6-group phase-scoped registry overlay, dispatch-vs-script verdict table)
- [dispatch-walkthrough.md](dispatch-walkthrough.md) — Worked end-to-end traces of three representative dispatches: phase-2-refine entry, phase-6-finalize automated-review with `verification-feedback` (producer=pr-comment), phase-6-finalize architecture-refresh Tier-1 fan-out
- [../../extension-api/standards/dispatch-granularity.md](../../extension-api/standards/dispatch-granularity.md) — Dispatch granularity heuristics: when to dispatch vs script vs inline
