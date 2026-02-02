# Phase 3-Outline Architecture

Visual overview of the change-type routing architecture for human readers.

## Agent Routing Flow

```
                          ┌─────────────────────────────────┐
                          │       phase-3-outline           │
                          │  (Central change-type routing)  │
                          └────────────┬────────────────────┘
                                       │
                    1. Detect change_type (spawn detect agent)
                    2. Resolve agent from marshal.json
                    3. Spawn resolved agent
                                       │
                                       ▼
              ┌────────────────────────┴────────────────────────┐
              │                                                 │
   ┌──────────▼──────────┐                         ┌───────────▼───────────┐
   │   Generic Agents     │                         │  Domain-Specific      │
   │   (pm-workflow)      │                         │  Agents (configured   │
   │                      │                         │  in marshal.json)     │
   │  change-analysis     │                         │                       │
   │  change-feature      │ ◄── fallback when ──── │  change-feature-      │
   │  change-enhancement  │     not configured     │    outline            │
   │  change-bug_fix      │                         │  change-enhancement-  │
   │  change-tech_debt    │                         │    outline            │
   │  change-verification │                         │  change-bug_fix-      │
   └──────────────────────┘                         │    outline            │
                                                    │  change-tech_debt-    │
              Each agent handles FULL workflow:     │    outline            │
              - Discovery (if needed)               └───────────────────────┘
              - Analysis
              - Deliverable generation                  NO SKILL LAYER
              - Solution outline writing                (agents only)
```

## Two-Track Workflow

```
                    ┌─────────────────┐
                    │  phase-2-refine │
                    │  (track select) │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
    ┌─────────▼─────────┐       ┌──────────▼──────────┐
    │   Simple Track    │       │    Complex Track    │
    │                   │       │                     │
    │ • Localized scope │       │ • Codebase-wide     │
    │ • Targets known   │       │ • Discovery needed  │
    │ • Direct mapping  │       │ • Agent handles all │
    └─────────┬─────────┘       └──────────┬──────────┘
              │                             │
              │                    ┌────────▼────────┐
              │                    │ detect-change-  │
              │                    │ type-agent      │
              │                    └────────┬────────┘
              │                             │
              │                    ┌────────▼────────┐
              │                    │ resolve agent   │
              │                    │ (marshal.json)  │
              │                    └────────┬────────┘
              │                             │
              │                    ┌────────▼────────┐
              │                    │ change-type     │
              │                    │ agent           │
              │                    └────────┬────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                    ┌────────▼────────┐
                    │ q-gate-agent    │
                    │ (verification)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │solution_outline │
                    │     .md         │
                    └─────────────────┘
```

## Change Type Vocabulary

| Change Type | Priority | Generic Agent | Purpose |
|-------------|----------|---------------|---------|
| `analysis` | 1 | `pm-workflow:change-analysis-agent` | Investigation, research |
| `feature` | 2 | `pm-workflow:change-feature-agent` | New functionality |
| `enhancement` | 3 | `pm-workflow:change-enhancement-agent` | Improve existing |
| `bug_fix` | 4 | `pm-workflow:change-bug_fix-agent` | Fix defects |
| `tech_debt` | 5 | `pm-workflow:change-tech_debt-agent` | Refactoring, cleanup |
| `verification` | 6 | `pm-workflow:change-verification-agent` | Validation |

## Domain Override Pattern

Domains can override generic agents via `change_type_agents` in marshal.json:

```json
"skill_domains": {
  "plan-marshall-plugin-dev": {
    "bundle": "pm-plugin-development",
    "change_type_agents": {
      "feature": "pm-plugin-development:change-feature-outline-agent",
      "enhancement": "pm-plugin-development:change-enhancement-outline-agent",
      "bug_fix": "pm-plugin-development:change-bug_fix-outline-agent",
      "tech_debt": "pm-plugin-development:change-tech_debt-outline-agent"
    }
  }
}
```

When no domain-specific agent is configured, the generic `pm-workflow:change-{type}-agent` is used as fallback.
