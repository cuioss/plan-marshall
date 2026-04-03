# Manage-* Skills Overview

System overview for the 14 manage-* skills in the plan-marshall bundle.

## Purpose

The manage-* skills form the data layer for plan-marshall's 6-phase workflow. Each skill owns a specific data domain and exposes a CLI API via Python scripts. All skills follow the shared contract in `ref-manage-contract`.

## The 14 Skills

### Plan-Scoped (data tied to a plan_id)

| Skill | Purpose | Primary File |
|-------|---------|-------------|
| manage-status | Plan lifecycle, phase tracking, routing | `status.json` |
| manage-references | Plan metadata (branch, issue, build system) | `references.json` |
| manage-plan-documents | Request document management | `request.md` |
| manage-solution-outline | Solution design with deliverables | `solution_outline.md` |
| manage-tasks | Implementation tasks with sub-steps | `TASK-{NNN}.json` |
| manage-findings | Findings, Q-Gate results, assessments | `*.jsonl` |
| manage-files | Generic plan-directory file CRUD | (any file) |

### Global-Scoped (shared across plans)

| Skill | Purpose | Storage |
|-------|---------|---------|
| manage-lessons | Lessons learned from past work | `.plan/lessons-learned/` |
| manage-memories | Session context snapshots | `.plan/memories/` |
| manage-run-config | Build command configuration, timeouts, cleanup | `.plan/run-configuration.json` |

### Hybrid-Scoped (both plan and global)

| Skill | Purpose | Storage |
|-------|---------|---------|
| manage-architecture | Project structure analysis, module enrichment | `.plan/project-architecture/` |
| manage-config | marshal.json configuration, skill domains | `.plan/marshal.json` |
| manage-logging | Script execution and work logging | Plan logs + global fallback |
| manage-metrics | Phase timing and token usage tracking | Plan work directory |

## Dependency Graph

```
manage-config (configuration authority)
├── manage-architecture (reads skill_domains for module resolution)
│   └── manage-solution-outline (primary consumer of architecture data)
├── manage-solution-outline (validates domains against config)
│   └── manage-tasks (deliverables → tasks 1:N mapping)
├── manage-tasks (inherits domain/profile from deliverables)
├── manage-status (routes phases using config workflow_skills)
│   └── manage-metrics (parallels phase transitions with timing)
├── manage-run-config (reads retention from marshal.json for cleanup)
└── manage-memories (reads retention from marshal.json for cleanup)

manage-findings
└── manage-lessons (promotion: findings → lessons)

manage-logging (independent, fire-and-forget)
manage-files (low-level utility, used by other manage-* skills)
manage-references (independent plan metadata)
manage-plan-documents (independent request storage)
```

## Data Flow Through Phases

```
Phase 1 (init):
  manage-status create → manage-references create → manage-plan-documents request create

Phase 2 (refine):
  manage-plan-documents request clarify

Phase 3 (outline):
  manage-architecture → manage-solution-outline write

Phase 4 (plan):
  manage-solution-outline list-deliverables → manage-tasks add (per deliverable)

Phase 5 (execute):
  manage-tasks next → [execute task] → manage-tasks finalize-step
  manage-findings add (during verification)

Phase 6 (finalize):
  manage-findings qgate add → manage-findings promote → manage-lessons add
  manage-metrics generate → manage-status archive
```

## Shared Infrastructure

All manage-* skills share:

| Component | Source | Purpose |
|-----------|--------|---------|
| `file_ops` | Shared Python module | Path resolution, JSON I/O, TOON output, timestamps |
| `input_validation` | Shared Python module | Plan ID validation, field type checks |
| `toon_parser` | Shared Python module | TOON serialization/deserialization |
| `constants` | Shared Python module | Phase names, Q-Gate phases, valid resolutions |
| `ref-manage-contract` | This bundle | Shared contract, formats, error codes |
| `ref-toon-format` | This bundle | TOON format specification |
