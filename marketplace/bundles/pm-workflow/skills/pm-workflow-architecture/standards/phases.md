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
│  │   ┌────────┐    ┌─────────┐    ┌────────┐    ┌─────────┐    ┌──────┐│  │
│  │   │  INIT  │───▶│ OUTLINE │───▶│  PLAN  │───▶│ EXECUTE │───▶│FINAL ││  │
│  │   └────────┘    └─────────┘    └────────┘    └─────────┘    └──────┘│  │
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

### Phase 1: INIT

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: INIT                                                                │
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
│  SKILL: pm-workflow:phase-init                                              │
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
│  10. Transition to outline phase                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 2: OUTLINE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: OUTLINE                                                             │
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
│  SKILL: pm-workflow:phase-refine-outline (or domain-specific extension)        │
│                                                                             │
│  STEPS:                                                                     │
│  ──────                                                                     │
│  1. Load manage-solution-outline skill (structure/examples)                 │
│  2. Read request.md and config.toon                                         │
│  3. Load project architecture via client-api (*)                            │
│  4. Analyze codebase with architecture context (Glob, Grep, Read)           │
│  5. Create deliverables with module/domain/profile/skills                   │
│  6. Write solution_outline.md                                               │
│  7. ──────────────────────────────────────────────────                      │
│     │  ** USER REVIEW GATE **                                               │
│     │  User must approve before proceeding to plan phase                    │
│     └──────────────────────────────────────────────────                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**(*) Project Architecture**: Module context from `plan-marshall:analyze-project-architecture` via [client-api.md](../../../../plan-marshall/skills/analyze-project-architecture/standards/client-api.md). Provides module responsibility, key packages, tips, and `skills_by_profile` for each module. Skills are selected when module is chosen and propagated to tasks.

---

### Phase 3: PLAN

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: PLAN                                                                │
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
│  SKILL: pm-workflow:phase-refine-plan                                               │
│                                                                             │
│  STEPS:                                                                     │
│  ──────                                                                     │
│  1. Read all deliverables from solution_outline.md                          │
│  2. Build dependency graph                                                  │
│  3. Analyze for aggregation (same domain/profile/change_type)               │
│  4. Analyze for splits (mixed execution_mode)                               │
│  5. Inherit skills from deliverables (from module context)                  │
│  6. Create TASK-*.toon files                                                │
│  7. Determine execution order (parallel groups)                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 4: EXECUTE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: EXECUTE                                                             │
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
│  SKILL: pm-workflow:phase-execute-implementation (or phase-execute-testing) │
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

### Phase 5: FINALIZE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: FINALIZE                                                            │
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
│  SKILL: pm-workflow:phase-finalize                                          │
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
│     │     └─▶ transition --completed finalize                      │       │
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
│  ┌────────┐     ┌─────────┐     ┌────────┐     ┌─────────┐     ┌────────┐  │
│  │  INIT  │────▶│ OUTLINE │────▶│  PLAN  │────▶│ EXECUTE │────▶│FINALIZE│  │
│  └────────┘     └─────────┘     └────────┘     └─────────┘     └────────┘  │
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

┌───────────┬────────────┬─────────────────────────────────────────────────┐
│ From      │ To         │ Trigger                                         │
├───────────┼────────────┼─────────────────────────────────────────────────┤
│ init      │ outline    │ Auto-continue (config/status created)           │
│ outline   │ plan       │ USER APPROVAL of solution outline               │
│ plan      │ execute    │ Auto-continue (tasks created)                   │
│ execute   │ finalize   │ All tasks completed                             │
│ finalize  │ COMPLETE   │ Commit/PR done (or no findings)                 │
│ finalize  │ execute    │ Findings detected → create fix tasks            │
└───────────┴────────────┴─────────────────────────────────────────────────┘
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
│  │  • Selects modules → gets module.skills_by_profile                   │  │
│  │  • Writes domains + skills to deliverables                           │  │
│  │                                                                      │  │
│  │  Example: "Add JWT validation" → module: oauth-sheriff-core          │  │
│  │           → skills: [java-core, java-cdi] from module context        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                      │                                                      │
│                      │ config.toon.domains                                  │
│                      ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  PLAN                                                                │  │
│  │  ════                                                                │  │
│  │  • Reads deliverable.domain + skills for each deliverable            │  │
│  │  • Skills inherited from module context (no resolution call)         │  │
│  │  • Writes domain + skills to TASK-*.toon                             │  │
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

## Related Documents

| Document | Purpose |
|----------|---------|
| [agents.md](agents.md) | Thin agent pattern details |
| [skill-loading.md](skill-loading.md) | How skills are resolved |
| [artifacts.md](artifacts.md) | Plan file formats |
| `pm-workflow:plan-wf-skill-api` | Contract definitions |
