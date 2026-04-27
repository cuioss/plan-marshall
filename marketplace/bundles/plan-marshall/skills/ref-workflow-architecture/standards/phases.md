# 6-Phase Execution Model

The plan-marshall bundle implements a 6-phase execution model for structured task completion. This document covers phase flow, transitions, and triggers. For file format details (status.json, TASK-*.json, references.json, etc.), see [artifacts.md](artifacts.md).

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                         6-PHASE EXECUTION MODEL                             │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │   ┌────────┐   ┌─────────┐   ┌───────────┐   ┌────────┐              │  │
│  │   │ 1-INIT │──▶│2-REFINE │──▶│ 3-OUTLINE │──▶│ 4-PLAN │──▶          │  │
│  │   └────────┘   └─────────┘   └───────────┘   └────────┘              │  │
│  │       │             │              │              │                  │  │
│  │   ┌───▼───┐    ┌────▼────┐    ┌────▼────┐   ┌────▼────┐             │  │
│  │   │config │    │clarified│    │solution │   │ TASK-*  │             │  │
│  │   │status │    │ request │    │outline  │   │ .json   │             │  │
│  │   │request│    │         │    │   .md   │   │  files  │             │  │
│  │   └───────┘    └─────────┘    └─────────┘   └─────────┘             │  │
│  │                                                                      │  │
│  │       ┌───────────┐   ┌──────────┐                                  │  │
│  │   ───▶│ 5-EXECUTE │──▶│6-FINALIZE│                                  │  │
│  │       └───────────┘   └──────────┘                                  │  │
│  │            │               │                                        │  │
│  │       ┌────▼────┐    ┌───▼───┐                                      │  │
│  │       │ project │    │commit │                                      │  │
│  │       │  files  │    │  PR   │                                      │  │
│  │       │modified │    │       │                                      │  │
│  │       │+verified│    └───────┘                                      │  │
│  │       └─────────┘                                                    │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase Details

### Phase 1: 1-INIT

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 1-INIT                                                              │
│  ═══════════                                                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  • description                   .plan/plans/{plan_id}/             │   │
│  │  • lesson_id                       ├── status.json                  │   │
│  │  • issue URL                       ├── request.md                   │   │
│  │                                    └── references.json              │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  AGENT: phase-agent (skill=plan-marshall:phase-1-init)                        │
│  SKILL: plan-marshall:phase-1-init                                            │
│                                                                             │
│  STEPS:                                                                     │
│  ──────                                                                     │
│  1. Validate input (exactly one source)                                     │
│  2. Derive plan_id                                                          │
│  3. Create plan directory                                                   │
│  4. Get task content (from description/lesson/issue)                        │
│  5. Write request.md                                                        │
│  6. Initialize references.json                                              │
│  7. Detect domain                                                           │
│  8. Create status.json (6-phase model)                                      │
│  9. Store domains in references.json                                        │
│  10. Transition to 2-refine phase                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 2: 2-REFINE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 2-REFINE                                                            │
│  ═════════════                                                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  • request.md                    • clarified_request (in request.md)│   │
│  │  • references.json               • clarifications (Q&A pairs)       │   │
│  │  • project-architecture (*)      • module_mapping                   │   │
│  │                                  • scope_estimate                   │   │
│  │                                  • confidence >= threshold          │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  INVOCATION: Skill loaded directly in main context                           │
│  SKILL: plan-marshall:phase-2-refine                                          │
│                                                                             │
│  STEPS:                                                                     │
│  ──────                                                                     │
│  0. Load confidence threshold from marshal.json (default: 95%)              │
│  1. Load architecture context                                               │
│  2. Load request                                                            │
│  3. Analyze request quality (correctness, completeness, consistency,        │
│     non-duplication, ambiguity)                                             │
│  4. Analyze in architecture context (module mapping, feasibility, scope)    │
│  5. Evaluate confidence                                                     │
│     IF confidence >= threshold → proceed to 3-outline                       │
│     ELSE → Step 6                                                           │
│  6. Clarify with user (AskUserQuestion)                                     │
│  7. Update request with clarifications                                      │
│     Loop back to Step 3                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**(*) Project Architecture**: Module context from `plan-marshall:manage-architecture`.

---

### Phase 3: 3-OUTLINE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 3-OUTLINE                                                           │
│  ═══════════════                                                            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  • clarified_request             solution_outline.md                │   │
│  │  • references.json                  └── Summary                      │   │
│  │  • project-architecture (*)        └── Overview (ASCII diagram)     │   │
│  │                                    └── Deliverables                 │   │
│  │                                        ├── 1. Title                 │   │
│  │                                        │   ├── Metadata             │   │
│  │                                        │   ├── Affected files       │   │
│  │                                        │   └── Verification         │   │
│  │                                        └── 2. Title ...             │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  INVOCATION: Skill loaded directly in main context                           │
│  SKILL: plan-marshall:phase-3-outline (or domain-specific extension)          │
│                                                                             │
│  STEPS:                                                                     │
│  ──────                                                                     │
│  1. Load refined request (clarified_request from phase-2-refine)           │
│  2. Load outline extension (if available)                                   │
│  3. Execute workflow:                                                       │
│     • Extension orchestrates (single call):                                 │
│       - Discovery and analysis                                              │
│       - Uncertainty resolution + Synthesize clarified request               │
│       - Call Q-Gate agent (generic, reusable tool)                          │
│       - Build deliverables                                                  │
│       - Return deliverables                                                 │
│     • Generic workflow (if no extension):                                   │
│       - Module selection                                                    │
│       - Package placement                                                   │
│       - Deliverable creation                                                │
│  4. Write solution_outline.md (using deliverables from step 3)              │
│  5. Set domains, record lessons, return results                             │
│  6. ──────────────────────────────────────────────────                      │
│     │  ** USER REVIEW GATE **                                               │
│     │  User must approve before proceeding to 4-plan phase                  │
│     └──────────────────────────────────────────────────                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 4: 4-PLAN

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 4-PLAN                                                              │
│  ════════════                                                               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  solution_outline.md             TASK-001.json                      │   │
│  │    └── Deliverables              TASK-002.json                      │   │
│  │        ├── 1. Title              TASK-003.json                      │   │
│  │        ├── 2. Title              ...                                │   │
│  │        └── 3. Title                                                 │   │
│  │                                  Each task contains:                │   │
│  │                                    • title                          │   │
│  │                                    • deliverable: N                 │   │
│  │                                    • domain                         │   │
│  │                                    • profile                        │   │
│  │                                    • skills: [...]                  │   │
│  │                                    • steps: [file paths]            │   │
│  │                                    • verification                   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  AGENT: phase-agent (skill=plan-marshall:phase-4-plan)                        │
│  SKILL: plan-marshall:phase-4-plan                                            │
│                                                                             │
│  STEPS:                                                                     │
│  ──────                                                                     │
│  1. Read all deliverables from solution_outline.md                          │
│  2. Build dependency graph                                                  │
│  3. Analyze for aggregation (same domain/profile/change_type)               │
│  4. Analyze for splits (mixed execution_mode)                               │
│  5. Resolve skills from architecture (per profile)                          │
│  6. Create TASK-*.json files                                                │
│  7. Determine execution order (parallel groups)                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 5: 5-EXECUTE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 5-EXECUTE                                                           │
│  ══════════════                                                             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  TASK-001.json                   Modified project files             │   │
│  │  TASK-002.json                     • New files created              │   │
│  │  TASK-003.json                     • Existing files modified        │   │
│  │  ...                               • Tests added/updated            │   │
│  │                                                                     │   │
│  │  For each task:                  Task status updated:               │   │
│  │    • domain                        • pending → in_progress          │   │
│  │    • profile                       • in_progress → completed        │   │
│  │    • skills                                                         │   │
│  │    • steps (file paths)                                             │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  INVOCATION: Skill loaded directly in main context                             │
│  SKILL: plan-marshall:phase-5-execute → execute-task (profile-based dispatch)  │
│                                                                             │
│  EXECUTION LOOP:                                                            │
│  ───────────────                                                            │
│                                                                             │
│     ┌──────────────────────────────────────────────────────────────┐       │
│     │                                                              │       │
│     │  For each task (in dependency order):                        │       │
│     │                                                              │       │
│     │    1. Load task context (manage-tasks read)                  │       │
│     │    2. Load domain skills (from task.skills)                  │       │
│     │    3. Resolve workflow skill (by profile)                    │       │
│     │    4. For each step (file path):                             │       │
│     │       a. Read affected files                                 │       │
│     │       b. Apply domain patterns                               │       │
│     │       c. Implement changes                                   │       │
│     │       d. Mark step complete                                  │       │
│     │    5. Run verification                                       │       │
│     │    6. Mark task complete                                     │       │
│     │                                                              │       │
│     └──────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 6: 6-FINALIZE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 6-FINALIZE                                                          │
│  ═══════════════                                                            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  • marshal.json                   • Git commit                       │   │
│  │    ├── create_pr                 • Branch pushed                    │   │
│  │    └── branch_strategy           • Pull request (if enabled)        │   │
│  │  • references.json               • Plan status: complete            │   │
│  │    ├── branch                                                       │   │
│  │    └── issue_url                                                    │   │
│  │  • Verified project files                                           │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  SKILL: plan-marshall:phase-6-finalize                                        │
│                                                                             │
│  FINALIZE PIPELINE:                                                         │
│  ──────────────────                                                         │
│                                                                             │
│     ┌──────────────────────────────────────────────────────────────┐       │
│     │                                                              │       │
│     │  1. commit_push                                              │       │
│     │     └─▶ Stage, commit, push to remote                        │       │
│     │                                                              │       │
│     │  2. automated_review                                         │       │
│     │     └─▶ Create PR, wait for CI, collect bot feedback         │       │
│     │                                                              │       │
│     │  3. sonar_roundtrip                                          │       │
│     │     └─▶ Wait for analysis, fetch issues, triage              │       │
│     │                                                              │       │
│     │  4. knowledge_capture                                        │       │
│     │     └─▶ Update project-structure.toon (advisory)             │       │
│     │                                                              │       │
│     │  5. lessons_capture                                          │       │
│     │     └─▶ Record notable triage decisions (advisory)           │       │
│     │                                                              │       │
│     │  ON FINDINGS (automated_review/sonar):                       │       │
│     │    → Create fix tasks                                        │       │
│     │    → Loop back to 5-execute                                  │       │
│     │    → Max iterations: 3 (configurable)                        │       │
│     │                                                              │       │
│     │  6. Mark plan complete                                       │       │
│     │     └─▶ transition --completed 6-finalize                    │       │
│     │                                                              │       │
│     └──────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase Transitions

| From | To | Trigger |
|------|-----|---------|
| 1-init | 2-refine | Auto-continue (config/status created) |
| 2-refine | 3-outline | Confidence >= threshold (default 95%) |
| 3-outline | 4-plan | USER APPROVAL of solution outline |
| 4-plan | 5-execute | Auto-continue (tasks created) |
| 5-execute | 6-finalize | All tasks completed + verification passed |
| 5-execute | 5-execute | Findings detected → triage + fix tasks |
| 6-finalize | COMPLETE | Commit/PR done (or no findings) |
| 6-finalize | 5-execute | Findings detected → create fix tasks |

**Iteration Limits**: 5-execute verify (max 5x) | 6-finalize (max 3x)

---

## Domain and Skill Flow

For the complete domain flow through phases (marshal.json → refine → outline → plan → execute → finalize), see [skill-loading.md](skill-loading.md).

---

## Related

- [agents.md](agents.md) — Thin agent pattern
- [skill-loading.md](skill-loading.md) — Skill resolution
- [artifacts.md](artifacts.md) — Plan file formats
