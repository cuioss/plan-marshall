# 5-Phase Execution Model

The pm-workflow bundle implements a 5-phase execution model for structured task completion.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                         5-PHASE EXECUTION MODEL                             │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │   ┌────────┐   ┌───────────┐   ┌────────┐   ┌───────────┐   ┌───────┐│  │
│  │   │ 1-INIT │──▶│ 2-OUTLINE │──▶│ 3-PLAN │──▶│ 4-EXECUTE │──▶│5-FINAL││  │
│  │   └────────┘   └───────────┘   └────────┘   └───────────┘   └───────┘│  │
│  │       │              │              │              │            │    │  │
│  │       │              │              │              │            │    │  │
│  │   ┌───▼───┐     ┌────▼────┐    ┌────▼────┐   ┌────▼────┐   ┌───▼───┐│  │
│  │   │config │     │solution │    │ TASK-*  │   │ project │   │commit ││  │
│  │   │status │     │outline  │    │ .toon   │   │  files  │   │  PR   ││  │
│  │   │request│     │   .md   │    │  files  │   │modified │   │       ││  │
│  │   └───────┘     └─────────┘    └─────────┘   └─────────┘   └───────┘│  │
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
│  │  • lesson_id                       ├── config.toon                  │   │
│  │  • issue URL                       ├── status.toon                  │   │
│  │                                    ├── request.md                   │   │
│  │                                    └── references.toon              │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  AGENT: plan-init-agent                                                     │
│  SKILL: pm-workflow:phase-1-init                                            │
│                                                                             │
│  STEPS:                                                                     │
│  ──────                                                                     │
│  1. Validate input (exactly one source)                                     │
│  2. Derive plan_id                                                          │
│  3. Create plan directory                                                   │
│  4. Get task content (from description/lesson/issue)                        │
│  5. Write request.md                                                        │
│  6. Initialize references.toon                                              │
│  7. Detect domain                                                           │
│  8. Create status.toon (5-phase model)                                      │
│  9. Create config.toon (with domains)                                       │
│  10. Transition to 2-outline phase                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 2: 2-OUTLINE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 2-OUTLINE                                                           │
│  ══════════════                                                             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  • request.md                    solution_outline.md                │   │
│  │  • config.toon                     └── Summary                      │   │
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
│  AGENT: solution-outline-agent                                              │
│  SKILL: pm-workflow:phase-2-outline (or domain-specific extension)          │
│                                                                             │
│  STEPS:                                                                     │
│  ──────                                                                     │
│  1. Load architecture context                                               │
│  2. Load request and config                                                 │
│  3. Load outline extension (if available)                                   │
│  4. Execute workflow:                                                       │
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
│  5. Write solution_outline.md (using deliverables from step 4)              │
│  6. Set domains, record lessons, return results                             │
│  7. ──────────────────────────────────────────────────                      │
│     │  ** USER REVIEW GATE **                                               │
│     │  User must approve before proceeding to 3-plan phase                  │
│     └──────────────────────────────────────────────────                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**(*) Project Architecture**: Module context from `plan-marshall:analyze-project-architecture` via [client-api.md](../../../../plan-marshall/skills/analyze-project-architecture/standards/client-api.md). Provides module responsibility, key packages, tips, and `skills_by_profile` for each module. Task-plan resolves skills from architecture based on module and profile.

---

### Phase 3: 3-PLAN

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 3-PLAN                                                              │
│  ═══════════                                                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  solution_outline.md             TASK-001.toon                      │   │
│  │    └── Deliverables              TASK-002.toon                      │   │
│  │        ├── 1. Title              TASK-003.toon                      │   │
│  │        ├── 2. Title              ...                                │   │
│  │        └── 3. Title                                                 │   │
│  │                                  Each task contains:                │   │
│  │                                    • title                          │   │
│  │                                    • deliverables: [N, M]           │   │
│  │                                    • domain                         │   │
│  │                                    • profile                        │   │
│  │                                    • skills: [...]                  │   │
│  │                                    • steps: [file paths]            │   │
│  │                                    • verification                   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  AGENT: task-plan-agent                                                     │
│  SKILL: pm-workflow:phase-3-plan                                            │
│                                                                             │
│  STEPS:                                                                     │
│  ──────                                                                     │
│  1. Read all deliverables from solution_outline.md                          │
│  2. Build dependency graph                                                  │
│  3. Analyze for aggregation (same domain/profile/change_type)               │
│  4. Analyze for splits (mixed execution_mode)                               │
│  5. Resolve skills from architecture (per profile)                          │
│  6. Create TASK-*.toon files                                                │
│  7. Determine execution order (parallel groups)                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 4: 4-EXECUTE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 4-EXECUTE                                                           │
│  ══════════════                                                             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  TASK-001.toon                   Modified project files             │   │
│  │  TASK-002.toon                     • New files created              │   │
│  │  TASK-003.toon                     • Existing files modified        │   │
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
│  AGENT: task-execute-agent                                                  │
│  SKILL: pm-workflow:task-implementation (or task-module_testing)            │
│                                                                             │
│  EXECUTION LOOP:                                                            │
│  ───────────────                                                            │
│                                                                             │
│     ┌──────────────────────────────────────────────────────────────┐       │
│     │                                                              │       │
│     │  For each task (in dependency order):                        │       │
│     │                                                              │       │
│     │    1. Load task context (manage-tasks get)                   │       │
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

### Phase 5: 5-FINALIZE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 5-FINALIZE                                                          │
│  ═══════════════                                                            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  • config.toon                   • Git commit                       │   │
│  │    ├── create_pr                 • Branch pushed                    │   │
│  │    ├── verification_required     • Pull request (if enabled)        │   │
│  │    └── branch_strategy           • Plan status: complete            │   │
│  │  • references.toon                                                  │   │
│  │    ├── branch                                                       │   │
│  │    └── issue_url                                                    │   │
│  │  • Modified project files                                           │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  SKILL: pm-workflow:phase-5-finalize                                        │
│                                                                             │
│  FINALIZE FLOW:                                                             │
│  ──────────────                                                             │
│                                                                             │
│     ┌──────────────────────────────────────────────────────────────┐       │
│     │                                                              │       │
│     │  1. Read configuration (get-multi)                           │       │
│     │     └─▶ create_pr, verification_required, branch_strategy    │       │
│     │                                                              │       │
│     │  2. Run verification (if required)                           │       │
│     │     └─▶ /builder-build-and-fix or domain-specific            │       │
│     │                                                              │       │
│     │  3. Git commit (via git-workflow)                            │       │
│     │     └─▶ Stage, commit with conventional message              │       │
│     │                                                              │       │
│     │  4. Push to remote                                           │       │
│     │                                                              │       │
│     │  5. Create PR (if enabled)                                   │       │
│     │     └─▶ Title from request, body from template               │       │
│     │                                                              │       │
│     │  6. Mark plan complete                                       │       │
│     │     └─▶ transition --completed 5-finalize                      │       │
│     │                                                              │       │
│     └──────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase Transitions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                          PHASE TRANSITIONS                                  │
│                                                                             │
│  ┌────────┐    ┌───────────┐    ┌────────┐    ┌───────────┐   ┌──────────┐ │
│  │ 1-INIT │───▶│ 2-OUTLINE │───▶│ 3-PLAN │───▶│ 4-EXECUTE │──▶│5-FINALIZE│ │
│  └────────┘    └───────────┘    └────────┘    └───────────┘   └──────────┘ │
│       │              │               │              │               │       │
│       │              │               │              │               │       │
│       │         ┌────┴────┐          │              │               │       │
│       │         │  USER   │          │              │               │       │
│       │         │ REVIEW  │          │              │               │       │
│       │         │  GATE   │          │              │               │       │
│       │         └────┬────┘          │              │               │       │
│       │              │               │              │               │       │
│  auto-continue  user-approval   auto-continue  auto-continue       │       │
│                                                                     │       │
│                                                                     ▼       │
│                                                              ┌──────────┐   │
│                                                              │ COMPLETE │   │
│                                                              └──────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

TRANSITION TRIGGERS:
═══════════════════

┌───────────────┬──────────────┬───────────────────────────────────────────┐
│ From          │ To           │ Trigger                                   │
├───────────────┼──────────────┼───────────────────────────────────────────┤
│ 1-init        │ 2-outline    │ Auto-continue (config/status created)     │
│ 2-outline     │ 3-plan       │ USER APPROVAL of solution outline         │
│ 3-plan        │ 4-execute    │ Auto-continue (tasks created)             │
│ 4-execute     │ 5-finalize   │ All tasks completed                       │
│ 5-finalize    │ COMPLETE     │ Commit/PR done (or no findings)           │
│ 5-finalize    │ 4-execute    │ Findings detected → create fix tasks      │
└───────────────┴──────────────┴───────────────────────────────────────────┘
```

---

## Domain Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                           DOMAIN FLOW                                       │
│                                                                             │
│  marshal.json                                                               │
│  ════════════                                                               │
│  skill_domains: [java, javascript, plan-marshall-plugin-dev, ...]           │
│                      │                                                      │
│                      │ all possible domains (project-level)                 │
│                      ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  OUTLINE                                                             │  │
│  │  ═══════                                                             │  │
│  │  • Analyzes request + architecture context                           │  │
│  │  • Selects modules → determines which profiles apply                 │  │
│  │  • Writes domains + profiles list to deliverables                    │  │
│  │                                                                      │  │
│  │  Example: "Add JWT validation" → module: oauth-sheriff-core          │  │
│  │           → profiles: [implementation, testing]                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                      │                                                      │
│                      │ config.toon.domains                                  │
│                      ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  PLAN                                                                │  │
│  │  ════                                                                │  │
│  │  • Reads deliverable.domain + profiles for each deliverable          │  │
│  │  • Resolves skills from architecture (module.skills_by_profile)      │  │
│  │  • Writes domain + profile + skills to TASK-*.toon                   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                      │                                                      │
│                      │ task.domain, task.skills                             │
│                      ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  EXECUTE                                                             │  │
│  │  ═══════                                                             │  │
│  │  • Loads task.skills (domain knowledge)                              │  │
│  │  • Resolves workflow skill for task.profile                          │  │
│  │  • Applies domain patterns during implementation                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                      │                                                      │
│                      │ config.toon.domains                                  │
│                      ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  FINALIZE                                                            │  │
│  │  ════════                                                            │  │
│  │  • Reads domains from config.toon                                    │  │
│  │  • Loads triage extensions for each domain                           │  │
│  │  • Applies domain-specific verification                              │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Q-Gate Validation Agent

Q-Gate is a GENERIC AGENT TOOL that extensions call during Phase 2 (Outline) to validate assessments.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                        Q-GATE VALIDATION AGENT                              │
│                                                                             │
│  TYPE: Generic agent tool (NOT a workflow step)                             │
│  CALLED BY: Extensions during their workflow                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  • plan_id                       • CONFIRMED assessments            │   │
│  │  • domains                       • FILTERED assessments             │   │
│  │  • CERTAIN_INCLUDE assessments   • affected_files in references.toon│   │
│  │                                  • Statistics (confirmed/filtered)  │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  STEPS:                                                                     │
│  ──────                                                                     │
│  1. Load domain skills (via resolve-workflow-skill)                         │
│  2. Read clarified request (or original request)                            │
│  3. Validate each CERTAIN_INCLUDE assessment:                               │
│     • Output Ownership - Component documents another's output               │
│     • Consumer vs Producer - Component consumes, not produces               │
│     • Request Intent Match - Modification fulfills request                  │
│     • Duplicate Detection - Not already covered                             │
│  4. Write CONFIRMED/FILTERED assessments to assessments.jsonl               │
│  5. Persist affected_files to references.toon                               │
│  6. Log lifecycle and return statistics                                     │
│                                                                             │
│  WHY GENERIC:                                                               │
│  ───────────                                                                │
│  • Same validation criteria across all domains                              │
│  • Reusable by all domain extensions                                        │
│  • Loads domain skills for context (but validation logic is generic)        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [agents.md](agents.md) | Thin agent pattern details |
| [skill-loading.md](skill-loading.md) | How skills are resolved |
| [artifacts.md](artifacts.md) | Plan file formats |
| `pm-workflow:workflow-extension-api` | Extension points |
