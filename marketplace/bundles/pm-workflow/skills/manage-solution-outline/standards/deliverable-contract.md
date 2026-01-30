# Deliverable Contract

Standard structure for deliverables in solution_outline.md that enables task-plan optimization and 5-phase workflow skill routing.

## Purpose

Each deliverable MUST contain sufficient information for:

1. **Grouping analysis**: Can this be aggregated with other deliverables?
2. **Split detection**: Should this be split into multiple tasks?
3. **Domain routing**: Which domain skills should be loaded?
4. **Profile routing**: Which workflow profiles apply (implementation, testing)?
5. **Verification consolidation**: Can verification commands be merged?
6. **Dependency ordering**: What order must deliverables execute in?
7. **Parallelization**: Which deliverables can run concurrently?

## Template

For the exact fill-in-the-blank structure, see:

**Template**: `templates/deliverable-template.md`

## Field Definitions

| Field | Required | Description | Used For |
|-------|----------|-------------|----------|
| `change_type` | Yes | Type of change | Grouping analysis |
| `execution_mode` | Yes | automated/manual/mixed | Split detection |
| `domain` | Yes | Single domain from config.domains | Domain skill loading |
| `module` | Yes | Module name from architecture | Skill resolution |
| `depends` | Yes | Dependencies on other deliverables | Ordering, parallelization |
| `**Profiles:**` | Yes | List of profiles (implementation, testing) | Task creation (1:N) |
| `Affected files` | Yes | Explicit file list | Step generation |
| `Change per file` | Yes | What changes | Task description |
| `Pattern` | Conditional | Code/format pattern | Implementation guide |
| `Verification` | Yes | How to verify | Task verification |

## Domain Values

The `domain` field MUST be a single value from `marshal.json skill_domains`:

| Domain | Description |
|--------|-------------|
| `java` | Java production and test code |
| `javascript` | JavaScript production and test code |
| `plan-marshall-plugin-dev` | Marketplace plugin components |

Multi-domain plans (e.g., fullstack features) have multiple domains in `marshal.json`. Each deliverable selects ONE domain for its work.

> **Note**: The `system` domain is internal-only and must NEVER be assigned to deliverables.

### Domain Validation

Solution outline skills MUST validate domains exist in marshal.json:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  skill-domains get --domain {domain}
```

Error if domain not found in marshal.json.

## Profiles Block

Each deliverable has a `**Profiles:**` block listing which profiles apply. Task-plan creates one task per profile (1:N mapping).

| Profile | Description | Architecture Source |
|---------|-------------|---------------------|
| `implementation` | Production code task | `module.skills_by_profile.implementation` |
| `testing` | Unit/integration test task | `module.skills_by_profile.testing` |

**Note**: Integration tests are separate deliverables (different module), not embedded profiles.

### 1:N Task Creation

Task-plan creates one task per profile in the deliverable:

```
solution_outline.md                        TASK-*.toon (created by task-plan)
┌────────────────────────────┐             ┌────────────────────────┐
│ **Metadata:**              │             │ TASK-001-IMPL          │
│ - domain: java             │             │ profile: implementation│
│ - module: auth-service     │  ───────►   │ skills: [java-core,    │
│                            │  (1:N)      │          java-cdi]     │
│ **Profiles:**              │             ├────────────────────────┤
│ - implementation           │  ───────►   │ TASK-002-TEST          │
│ - module_testing           │             │ profile: module_testing│
│                            │             │ skills: [java-core,    │
└────────────────────────────┘             │          junit-core]   │
                                           │ depends: TASK-001-IMPL │
                                           └────────────────────────┘
```

### Skill Resolution Flow

Task-plan resolves skills from architecture for each profile:

```
For each profile in deliverable.profiles:
  1. Query architecture: module --name {module}
  2. Extract: skills_by_profile.{profile}
  3. Create task with profile + resolved skills
```

**Key principle**: Deliverables specify WHAT profiles apply, task-plan resolves WHICH skills from architecture.

## Dependency Specification

The `depends` field enables task-plan to determine execution order and parallelization.

| Value | Meaning | Example |
|-------|---------|---------|
| `none` | No dependencies, can run in parallel | Independent refactoring |
| `N` | Must complete after deliverable N | `1` |
| `N. Title` | Must complete after deliverable N (with title for clarity) | `1. Create Database Schema` |
| `N, M` | Must complete after ALL numbered deliverables | `1, 2, 4` |

### Dependency Rules

- Use `none` when the deliverable has no prerequisites
- Reference deliverables by number alone (e.g., `1`) or with title (e.g., `1. Create Schema`)
- Title format improves readability - task-plan parses the number prefix
- Multiple dependencies are comma-separated (numbers only for brevity)
- Circular dependencies are INVALID
- Dependencies should reference earlier deliverable numbers (lower numbers first)

## Change Types

| Type | Description | Grouping Hint |
|------|-------------|---------------|
| `create` | New file/component | Group by component type |
| `modify` | Update existing | Group by change similarity |
| `refactor` | Restructure without behavior change | Keep separate (risky) |
| `migrate` | Format/API migration | Group by target format |
| `delete` | Remove file/component | Group by bundle |

## Execution Modes

| Mode | Description | Task-Plan Behavior |
|------|-------------|-------------------|
| `automated` | Can run without human intervention | Can aggregate |
| `manual` | Requires human judgment/action | Must split |
| `mixed` | Contains both auto and manual parts | Must split into separate tasks |

## Validation Checklist

Solution outline skills MUST validate that each deliverable contains:

- [ ] `change_type` metadata
- [ ] `execution_mode` metadata
- [ ] `domain` metadata (single value from config.domains)
- [ ] `module` metadata (module name from architecture)
- [ ] `depends` field (`none` or valid deliverable references)
- [ ] `**Profiles:**` block with valid profiles (`implementation`, `testing`)
- [ ] Explicit file list (not "all files matching X")
- [ ] Verification command and criteria

## Deliverable ID Format

| Format | Example | Usage |
|--------|---------|-------|
| Number only | `1`, `2` | `task.deliverable: 1` |
| Full reference | `1. Create CacheConfig` | `depends: 1. Create CacheConfig` |

**Parsing rule**: Extract leading integer, ignore title portion.

## Anti-patterns (INVALID deliverables)

- Missing metadata block
- Missing `domain` field (prevents domain skill loading)
- Missing `module` field (prevents skill resolution from architecture)
- Missing `**Profiles:**` block (prevents task creation)
- Empty `**Profiles:**` block (must have at least one profile)
- Invalid profile (not `implementation` or `testing`)
- Invalid domain (domain not in marshal.json `skill_domains`)
- System domain (using `system` as deliverable domain - internal only)
- "Update all agents" without file enumeration
- Verification: "manual review" for automatable checks
- Missing `depends` field (prevents parallelization analysis)
- Circular dependencies (D1 depends on D2, D2 depends on D1)
- Forward dependencies (D1 depends on D3, where D3 comes after D1)

## Examples

For complete examples and anti-patterns, see:
- `templates/deliverable-template.md` - Template with invalid patterns
- `examples/*.md` - Domain-specific examples (java, javascript, plugin, etc.)
