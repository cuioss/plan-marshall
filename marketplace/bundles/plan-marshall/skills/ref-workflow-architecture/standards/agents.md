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
| Phase invocation from orchestrator | `Skill:` | Need to spawn analysis agents |
| Domain extension loading | `Skill:` | Inherits spawning ability |
| Leaf-level file analysis | `Task:` | Isolated, focused work |
| Init phase (no spawning needed) | `Task:` | Simple, isolated execution |
| Plan phase (no spawning needed) | `Task:` | Simple, isolated execution |

---

## Agent Inventory

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                      4 AGENTS (plan-marshall bundle)                        │
│                                                                             │
│  ┌──────────────────────┬────────────────────────────────────────────────┐ │
│  │ AGENT                │ PURPOSE                                        │ │
│  ├──────────────────────┼────────────────────────────────────────────────┤ │
│  │                      │                                                │ │
│  │ phase-agent          │ Generic thin wrapper                           │ │
│  │                      │ • Loads caller-specified skill via Skill tool  │ │
│  │                      │ • Delegates all work to the loaded skill       │ │
│  │                      │ • Used for phase-1-init and phase-4-plan       │ │
│  │                      │                                                │ │
│  ├──────────────────────┼────────────────────────────────────────────────┤ │
│  │                      │                                                │ │
│  │ detect-change-type-  │ Analyze request to detect change type          │ │
│  │ agent                │ • Returns change_type + confidence             │ │
│  │                      │ • Used during phase-3-outline                  │ │
│  │                      │                                                │ │
│  ├──────────────────────┼────────────────────────────────────────────────┤ │
│  │                      │                                                │ │
│  │ q-gate-validation-   │ Validate assessments against request intent    │ │
│  │ agent                │ • Catches false positives, missing coverage    │ │
│  │                      │ • Used during phase-3-outline                  │ │
│  │                      │                                                │ │
│  ├──────────────────────┼────────────────────────────────────────────────┤ │
│  │                      │                                                │ │
│  │ research-best-       │ Web research for best practices                │ │
│  │ practices-agent      │ • Searches multiple sources, synthesizes       │ │
│  │                      │ • General-purpose research tool                │ │
│  │                      │                                                │ │
│  └──────────────────────┴────────────────────────────────────────────────┘ │
│                                                                             │
│  NOTE: Phases 2-refine, 3-outline, and 5-execute load skills directly     │
│  in main context (no agent). This allows user interaction and sub-agent   │
│  spawning.                                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Other bundles (e.g., `pm-plugin-development`) define their own analysis agents that are spawned by domain extensions during the outline phase. See the respective bundle documentation.

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
│  │  model: sonnet                                                       │  │
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
- Cross scope boundaries (init agent doesn't create tasks)

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
