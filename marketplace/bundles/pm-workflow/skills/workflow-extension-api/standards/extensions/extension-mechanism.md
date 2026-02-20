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
│  │  pm-workflow:phase-3-outline                                         │   │
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
- Falls back to generic `pm-workflow:outline-change-type/standards/change-{type}.md` if not configured

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
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
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
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
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

**System Skill**: `pm-workflow:phase-3-outline`

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

See `pm-workflow:workflow-architecture/standards/change-types.md` for full vocabulary.

### Skill Resolution

1. **Detect change type** via `pm-workflow:detect-change-type-agent`
2. **Check domain config** for `outline_skill`
3. **Fall back to generic** if not configured: `pm-workflow:outline-change-type/standards/change-{type}.md`

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

Domains declare their outline skill in `extension.py`:

```python
def provides_outline_skill(self) -> str | None:
    return 'pm-plugin-development:ext-outline-workflow'
```

---

## Triage Extension

### Purpose

Each domain provides a triage skill that contains **decision-making knowledge** - not workflow control. The finalize workflow skill owns the process; triage extensions provide knowledge for making decisions.

### Separation of Concerns

```
FINALIZE WORKFLOW SKILL (owns the process)
───────────────────────────────────────────
- Runs build (canonical command)
- Collects findings from available sources
- Waits for CI (if ci.enabled)
- Iterates on PR feedback
- Commits and creates PR

TRIAGE EXTENSION (decision-making knowledge)
─────────────────────────────────────────────
- Suppression syntax for this domain
- Severity-to-decision guidelines
- What's acceptable to accept/defer
```

### Required Sections

| Section | Purpose | Content |
|---------|---------|---------|
| `## Suppression Syntax` | How to suppress findings | Annotation/comment syntax per finding type |
| `## Severity Guidelines` | When to fix vs suppress vs accept | Decision table by severity |
| `## Acceptable to Accept` | What can be accepted without fixing | Situations where accepting is appropriate |

### `## Suppression Syntax`

How to suppress different types of findings in this domain.

**Example for Java:**
```markdown
## Suppression Syntax

| Finding Type | Suppression | Example |
|--------------|-------------|---------|
| Sonar issue | `@SuppressWarnings("{rule}")` | `@SuppressWarnings("java:S1135") // JIRA-123` |
| Deprecation | `@SuppressWarnings("deprecation")` | On method/class |
| Unchecked cast | `@SuppressWarnings("unchecked")` | On statement |
| Null warning | `@SuppressWarnings("null")` | On field/parameter |

**Rules:**
- Always include justification comment
- Reference issue tracker if deferring
- Prefer fixing over suppressing for BLOCKER/CRITICAL
```

### `## Severity Guidelines`

When to fix, suppress, accept, or defer based on severity and type.

**Example:**
```markdown
## Severity Guidelines

| Severity | Type | Default Decision |
|----------|------|------------------|
| BLOCKER | any | **fix** (mandatory) |
| CRITICAL | VULNERABILITY | **fix** (mandatory) |
| CRITICAL | BUG | **fix** (strongly preferred) |
| MAJOR | any | fix or suppress with justification |
| MINOR | any | fix, suppress, or accept |
| INFO | any | accept (low priority) |

**Context modifiers:**
- New code: Hold to higher standard (fix MAJOR+)
- Legacy code: More lenient (suppress with migration plan)
- Test code: More lenient for style issues
- Generated code: Accept or exclude from analysis
```

### `## Acceptable to Accept`

Types of findings that can be accepted without fixing.

**Example:**
```markdown
## Acceptable to Accept

| Finding Type | Reason | Example |
|--------------|--------|---------|
| Generated code | Not maintainable by hand | `**/generated/**` |
| Test builders | Intentionally permissive | Test data factory methods |
| Legacy migration | Tracked separately | Code with `@Deprecated` + migration plan |
| Framework requirement | Can't change | Framework-mandated patterns |
| False positive | Tool limitation | Documented false positive patterns |
```

### Triage Extension Example: Java

```markdown
# Java Triage

> Decision-making knowledge for Java findings triage.

## Suppression Syntax

| Finding Type | Suppression |
|--------------|-------------|
| Sonar | `@SuppressWarnings("{rule}")` |
| Deprecation | `@SuppressWarnings("deprecation")` |
| Unchecked | `@SuppressWarnings("unchecked")` |
| Null | `@SuppressWarnings("null")` or JSpecify annotations |

## Severity Guidelines

| Severity | Decision |
|----------|----------|
| BLOCKER | fix (mandatory) |
| CRITICAL | fix (mandatory for vulnerabilities) |
| MAJOR | fix or suppress with justification |
| MINOR/INFO | fix, suppress, or accept |

## Acceptable to Accept

- Generated code (`**/generated/**`)
- Test data builders
- Legacy code with documented migration plan
- Framework-mandated patterns (e.g., Serializable)
```

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
- [change-types.md](../../../workflow-architecture/standards/change-types.md) - Change type vocabulary
- [deliverable-contract.md](../../../manage-solution-outline/standards/deliverable-contract.md) - Deliverable structure
