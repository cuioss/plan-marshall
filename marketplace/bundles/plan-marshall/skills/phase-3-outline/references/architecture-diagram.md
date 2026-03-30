# Phase 3-Outline Architecture

Visual overview of the change-type routing architecture for human readers.

## Skill-Based Routing Flow

```
                          ┌─────────────────────────────────┐
                          │       phase-3-outline           │
                          │  (Central change-type routing)  │
                          └────────────┬────────────────────┘
                                       │
                    1. Detect change_type (spawn detect agent)
                    2. Resolve domain or generic change-type instructions
                    3. Execute discovery, analysis, deliverable creation
                                       │
                                       ▼
              ┌────────────────────────┴────────────────────────┐
              │                                                 │
   ┌──────────▼──────────┐                         ┌───────────▼───────────┐
   │   Generic Sub-Skills │                         │  Domain-Specific      │
   │   (plan-marshall)      │                         │  Skills (configured   │
   │                      │                         │  in marshal.json)     │
   │  phase-3-outline      │                         │                       │
   │  /standards/         │ ◄── fallback when ──── │  ext-outline-workflow  │
   │    change-analysis   │     not configured     │  (shared workflow for  │
   │    change-feature    │                         │   all change types)   │
   │    change-enhancement│                         │                       │
   │    change-bug_fix    │                         │                       │
   │    change-tech_debt  │                         │                       │
   │    change-verification│                        │                       │
   └──────────────────────┘                         └───────────────────────┘

              Each sub-skill provides instructions for:
              - Discovery (if needed)
              - Analysis
              - Deliverable generation
              - Solution outline writing
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
    │ • Direct mapping  │       │ • Skill runs inline │
    └─────────┬─────────┘       └──────────┬──────────┘
              │                             │
              │                    ┌────────▼────────┐
              │                    │ detect-change-  │
              │                    │ type-agent      │
              │                    └────────┬────────┘
              │                             │
              │                    ┌────────▼────────┐
              │                    │ outline-change- │
              │                    │ type skill      │
              │                    │ (inline)        │
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

| Change Type | Priority | Sub-Skill Instructions | Purpose |
|-------------|----------|----------------------|---------|
| `analysis` | 1 | `phase-3-outline/standards/change-analysis.md` | Investigation, research |
| `feature` | 2 | `phase-3-outline/standards/change-feature.md` | New functionality |
| `enhancement` | 3 | `phase-3-outline/standards/change-enhancement.md` | Improve existing |
| `bug_fix` | 4 | `phase-3-outline/standards/change-bug_fix.md` | Fix defects |
| `tech_debt` | 5 | `phase-3-outline/standards/change-tech_debt.md` | Refactoring, cleanup |
| `verification` | 6 | `phase-3-outline/standards/change-verification.md` | Validation |

## Domain Override Pattern

Domains can provide a domain-specific outline skill via `outline_skill` in marshal.json:

```json
"skill_domains": {
  "plan-marshall-plugin-dev": {
    "bundle": "pm-plugin-development",
    "outline_skill": "pm-plugin-development:ext-outline-workflow"
  }
}
```

When no domain-specific skill is configured, the generic sub-skill instructions from `plan-marshall:phase-3-outline/standards/change-{type}.md` are used as fallback.

**Note**: Recipe-sourced plans bypass this entire change-type routing. See [recipe-flow.md](recipe-flow.md) for the recipe path through phase-3-outline.
