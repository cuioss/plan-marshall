# Thin Agent Pattern

The plan-marshall bundle uses thin agents that delegate to skills for actual work.

---

## Overview

```
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

Understanding when to use `Skill:` vs `Task:` is critical for proper context management.

```
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

### Decision Guide

| Scenario | Use | Reason |
|----------|-----|--------|
| Workflow needs `AskUserQuestion` against the user | `Skill:` (main context) | Subagents cannot reach the user |
| Workflow spawns further `Task:` dispatches internally | `Skill:` (main context) | Subagents cannot spawn subagents |
| Workflow is a focused, self-contained LLM job with a return-TOON contract | `Task: execution-context-{level}` | Pinned model/effort per role key, isolated context |
| Per-iteration parallel work (one envelope per input item) | `Task:` fan-out | Only when each subagent runs independently |

---

## Agent Inventory

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                      1 AGENT (plan-marshall bundle)                         │
│                                                                             │
│  ┌──────────────────────┬────────────────────────────────────────────────┐ │
│  │ AGENT                │ PURPOSE                                        │ │
│  ├──────────────────────┼────────────────────────────────────────────────┤ │
│  │                      │                                                │ │
│  │ execution-context    │ Generic dispatcher                             │ │
│  │                      │ • Loads dev-general-practices implicitly       │ │
│  │                      │ • Loads caller-specified skills[] in order     │ │
│  │                      │ • Reads + executes the prompt-body `workflow`  │ │
│  │                      │   doc (or `instructions`) to completion        │ │
│  │                      │ • Returns the workflow's declared TOON         │ │
│  │                      │                                                │ │
│  │                      │ Six emitted variants per ordinal level         │ │
│  │                      │ (low/medium/high/xhigh/xxhigh + canonical      │ │
│  │                      │ inherit) drive every plan-marshall Task:       │ │
│  │                      │ invocation. Dispatch site resolves the         │ │
│  │                      │ target via `manage-config models               │ │
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

```
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
- [dispatch-walkthrough.md](dispatch-walkthrough.md) — Worked end-to-end traces of three representative dispatches: phase-2-refine entry, phase-6 automated-review with `cross.triage`, phase-6 architecture-refresh Tier-1 fan-out
- [../../dev-general-practices/standards/granularity.md](../../dev-general-practices/standards/granularity.md) — Dispatch granularity heuristics: when to dispatch vs script vs inline
