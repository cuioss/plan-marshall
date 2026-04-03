---
name: ref-workflow-architecture
description: Centralized architecture documentation for the plan-marshall bundle with visual diagrams
user-invocable: false
---

# Plan-Marshall Architecture

Central architecture reference for the plan-marshall bundle. Provides documentation of the 6-phase execution model, thin agent pattern, data layer, and workflow conventions.

Load specific standards on-demand based on what aspect you need to understand.

## Standards Documents

| Document | Focus | Key Content |
|----------|-------|-------------|
| [phases.md](standards/phases.md) | 6-phase model | Phase flow, transitions, outputs, iteration limits |
| [agents.md](standards/agents.md) | Thin agent pattern | Agent structure, Skill: vs Task: invocation |
| [data-layer.md](standards/data-layer.md) | manage-* skills | Inventory, dependency graph, data flow |
| [manage-contract.md](standards/manage-contract.md) | manage-* contract | Enforcement, error codes, shared formats |
| [skill-loading.md](standards/skill-loading.md) | Two-tier loading | System vs domain skills, domain flow through phases |
| [artifacts.md](standards/artifacts.md) | Plan file formats | status.json, TASK-*.json, references.json, logs |
| [task-executors.md](standards/task-executors.md) | Task executors | Profile routing, shared workflow, extensibility |
| [change-types.md](standards/change-types.md) | Change type vocabulary | analysis, feature, enhancement, bug_fix, tech_debt, verification |

## Core Principles

1. **Domain-agnostic workflow** — Workflow skills contain no domain-specific logic. Domain knowledge comes from marshal.json at runtime.
2. **Thin agent pattern** — A single parameterized agent with different `phase` parameters, delegating to skills for actual work.
3. **Single source of truth** — Plan files are the source of truth. Skills read/write via manage-* scripts only.
4. **Script-based file access** — ALL `.plan/` file access goes through `execute-script.py`. Never use Read/Write/Edit on `.plan/` files directly.

## Related Skills

| Skill | Purpose |
|-------|---------|
| `plan-marshall:plan-marshall` | Unified user-facing entry point for plan lifecycle |
| `plan-marshall:extension-api` | Extension points for domain customization |
| `plan-marshall:task-executor` | Unified task executor (implementation, module_testing, verification profiles) |
| `plan-marshall:shared-workflow-helpers` | Shared Python infrastructure for workflow scripts |

## Shared Workflow Infrastructure

All workflow scripts share `triage_helpers` from `shared-workflow-helpers` (`marketplace/bundles/plan-marshall/skills/shared-workflow-helpers/scripts/triage_helpers.py`). See `plan-marshall:shared-workflow-helpers` SKILL.md for the module overview.

### Workflow Skill Conventions

Script-bearing workflow skills follow this canonical section order (sections marked optional may be omitted when not applicable):

```
---
name: workflow-<name>
description: <one-line description>
user-invocable: true|false
---

# <Title> Skill
## Enforcement
## Parameters          (optional)
## Prerequisites       (optional)
## Workflow(s)
## Scripts
## Error Handling
## Standards (Load On-Demand)
## Related
```

### Config Loading Convention

Script-bearing workflow skills load JSON config from `standards/` using `load_skill_config(__file__, 'config-name.json')` from `triage_helpers`.

### Priority Vocabulary

All workflow scripts use the shared `PRIORITY_LEVELS` tuple from `triage_helpers`: `low`, `medium`, `high`, `critical`. Do not use `none` or other values.

### Error Handling Patterns

All workflow skills use a consistent `| Failure | Action |` table. Common patterns:

| Pattern | Action |
|---------|--------|
| Script returns error | Report error to caller with details. Do not proceed. |
| Triage/classification failure | Log warning, skip item, continue remaining. |
| Push failure | Report error. Never force-push as fallback. |
| Build verification failure | Report failing tests/compilation. Do not commit broken state. |
| Max fix attempts reached | Report remaining issues. Do not loop further. |
