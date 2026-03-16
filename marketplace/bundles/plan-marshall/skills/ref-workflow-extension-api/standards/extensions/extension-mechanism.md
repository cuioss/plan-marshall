# Workflow Skill Extension API

Convention-based extension mechanism for domain-specific workflow customization.

## Purpose

The extension API allows domains to **extend** system workflow skills without **replacing** them. This provides:

1. **Process ownership**: System skills own the workflow process
2. **Domain customization**: Extensions provide domain-specific behavior
3. **Convention-based API**: Extensions define named sections that system skills look for
4. **No code duplication**: Extensions don't reimplement process logic

---

## Conceptual Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SYSTEM SKILL + EXTENSION MODEL                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  SYSTEM WORKFLOW SKILL (owns process)                                 │   │
│  │  plan-marshall:phase-3-outline                                         │   │
│  │                                                                       │   │
│  │  Process:                                                             │   │
│  │  1. Load extensions for all configured domains                        │   │
│  │  2. Load domain knowledge (core + architecture for all domains)       │   │
│  │  3. Analyze request                                                   │   │
│  │  4. ══► EXTENSION POINT: Codebase Analysis ◄══                       │   │
│  │  5. Determine relevant domains                                        │   │
│  │  6. ══► EXTENSION POINT: Deliverable Patterns ◄══                    │   │
│  │  7. Create deliverables                                               │   │
│  │  8. Write references.json.domains                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              │ looks for                                     │
│                              ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  EXTENSION SKILL (provides domain-specific behavior)                  │   │
│  │  pm-dev-java:java-outline-ext                                         │   │
│  │                                                                       │   │
│  │  ## Codebase Analysis                                                 │   │
│  │  When analyzing Java codebases:                                       │   │
│  │  - Check for pom.xml, build.gradle                                    │   │
│  │  - Identify package structure                                         │   │
│  │  ...                                                                  │   │
│  │                                                                       │   │
│  │  ## Deliverable Patterns                                              │   │
│  │  When creating Java deliverables:                                     │   │
│  │  - Group by Maven module                                              │   │
│  │  - Separate API from implementation                                   │   │
│  │  ...                                                                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Extension Types

| Extension Key | Phase | Purpose |
|---------------|-------|---------|
| `outline_skill` | 3-outline | Domain-specific outline skill (dispatches internally by change type) |
| `triage` | 5-execute, 6-finalize | Decision-making knowledge for findings (suppression syntax, severity rules) |

**Change-Type Skills** (replaces `outline` skill extension):
- Domains can provide skills for specific change types
- Skills provide sub-skill instructions for: discovery, analysis, deliverable creation
- Falls back to generic `plan-marshall:workflow-outline-change-type/standards/change-{type}.md` if not configured

**Phases without extensions:**

| Phase | Knowledge Source |
|-------|------------------|
| 1-init | No domain knowledge needed |
| 4-plan | `planning` profile - task decomposition patterns |
| 5-execute | `task.profile` - implementation guidance |

---

## Extension Resolution

### Outline Skill Resolution

```bash
# Resolve outline skill for a domain
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-outline-skill --domain plan-marshall-plugin-dev
```

Returns skill (domain-specific or generic fallback):

```toon
status: success
domain: plan-marshall-plugin-dev
skill: pm-plugin-development:ext-outline-workflow
source: domain_specific
```

### Triage Skill Resolution

```bash
# Resolve triage skill for a domain
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-workflow-skill-extension --domain java --type triage
```

Returns extension (or null if none):

```toon
status: success
domain: java
type: triage
extension: pm-dev-java:ext-triage-java
```

---

## marshal.json Configuration

```json
"plan-marshall-plugin-dev": {
  "bundle": "pm-plugin-development",
  "outline_skill": "pm-plugin-development:ext-outline-workflow",
  "workflow_skill_extensions": {
    "triage": "pm-plugin-development:ext-triage-plugin"
  }
}
```

| Key | Purpose | Used By |
|-----|---------|---------|
| `outline_skill` | Domain-specific outline skill (dispatches internally by change type) | phase-3-outline |
| `triage` | Domain-specific findings handling | Execute (verification), Finalize phases |

---

## Extension Skill Structure

```markdown
# {Domain} {Type} Extension

> Extension for {type} in {domain} domain.

## {Section 1 Name}

Instructions for this extension point...

## {Section 2 Name}

Instructions for this extension point...
```

---

## Change-Type Skill Extension

### Phase Overview

**System Skill**: `plan-marshall:phase-3-outline`

**Purpose**: Transform user request into solution outline with deliverables.

**Skill Purpose**: Provide domain-specific outline instructions for each change type.

### Change Types

| Change Type | Priority | Description |
|-------------|----------|-------------|
| `analysis` | 1 | Investigate, research, understand |
| `feature` | 2 | New functionality or component |
| `enhancement` | 3 | Improve existing functionality |
| `bug_fix` | 4 | Fix a defect or issue |
| `tech_debt` | 5 | Refactoring, cleanup, removal |
| `verification` | 6 | Validate, check, confirm |

See `plan-marshall:ref-workflow-architecture/standards/change-types.md` for full vocabulary.

### Skill Resolution

1. **Detect change type** via `plan-marshall:detect-change-type-agent`
2. **Check domain config** for `outline_skill`
3. **Fall back to generic** if not configured: `plan-marshall:workflow-outline-change-type/standards/change-{type}.md`

### Implementing Domain-Specific Skills

Create a skill in your bundle that provides change-type-specific instructions:
- Single skill with `standards/change-{type}.md` sub-skill files (e.g., `ext-outline-workflow`)

Each sub-skill provides instructions for:
- Discovery (using inventory agents if needed)
- Analysis (using component analysis agents if needed)
- Deliverable creation
- Solution outline writing

### Example: Plugin Development Skill

```
pm-plugin-development/skills/ext-outline-workflow/
├── SKILL.md                           # Shared workflow steps
└── standards/
    ├── change-feature.md              # Create new components
    ├── change-enhancement.md          # Improve existing components
    ├── change-bug_fix.md              # Fix component bugs
    └── change-tech_debt.md            # Refactor/cleanup components
```

The skill can spawn sub-agents for specific tasks:
- `ext-outline-inventory-agent` - Marketplace inventory discovery
- `ext-outline-component-agent` - Component analysis

### Extension API

For the `provides_outline_skill()` API contract, see `plan-marshall:extension-api/standards/outline-extension.md`.

---

## Triage Extension

Each domain provides a triage skill that contains **decision-making knowledge** - not workflow control. The finalize workflow skill owns the process; triage extensions provide knowledge for:

- How to suppress findings in that domain
- Severity guidelines for fix vs suppress vs accept decisions
- Situations where accepting a finding is appropriate

For the full triage contract (required sections, examples, validation rules), see [triage-extension.md](triage-extension.md).

---

## Multiple Extensions

When multiple domains are configured (e.g., Java + JavaScript for full-stack):

1. All relevant extensions are loaded
2. Each extension applies to its domain only
3. Priority field determines order if conflicts arise

```
marshal.json domains: [java, javascript]

Extensions loaded:
  pm-dev-java:java-outline-ext (priority: 10)
  pm-dev-frontend:js-outline-ext (priority: 20)

At extension point "Codebase Analysis":
  1. java-outline-ext provides Java-specific analysis
  2. js-outline-ext provides JS-specific analysis
  3. Claude applies each when analyzing respective parts of codebase

At extension point "Deliverable Patterns":
  1. Java deliverables use java-outline-ext patterns
  2. JavaScript deliverables use js-outline-ext patterns
```

---

## Benefits Over Override Model

| Aspect | Override Model | Extension Model |
|--------|----------------|-----------------|
| Process ownership | Domain skill owns process | System skill owns process |
| Code duplication | Domain reimplements process | Domain only provides specific behavior |
| Maintenance | Update multiple skills | Update system skill once |
| Consistency | Varies by domain | Consistent process, domain variations |
| API contract | Implicit | Explicit via extension points |

---

## Related Documents

- [phase-3-outline SKILL.md](../../../phase-3-outline/SKILL.md) - Outline phase skill (self-documenting)
- [phase-5-execute SKILL.md](../../../phase-5-execute/SKILL.md) - Execute phase skill with verification (self-documenting)
- [phase-6-finalize SKILL.md](../../../phase-6-finalize/SKILL.md) - Finalize phase skill (self-documenting)
- [triage-extension.md](triage-extension.md) - Triage extension contract
- [change-types.md](../../../ref-workflow-architecture/standards/change-types.md) - Change type vocabulary
- [deliverable-contract.md](../../../manage-solution-outline/standards/deliverable-contract.md) - Deliverable structure
