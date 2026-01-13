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
│  │  pm-workflow:phase-2-outline                                         │   │
│  │                                                                       │   │
│  │  Process:                                                             │   │
│  │  1. Load extensions for all configured domains                        │   │
│  │  2. Load domain knowledge (core + architecture for all domains)       │   │
│  │  3. Analyze request                                                   │   │
│  │  4. ══► EXTENSION POINT: Codebase Analysis ◄══                       │   │
│  │  5. Determine relevant domains                                        │   │
│  │  6. ══► EXTENSION POINT: Deliverable Patterns ◄══                    │   │
│  │  7. Create deliverables                                               │   │
│  │  8. Write config.toon.domains                                         │   │
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
| `outline` | 2-outline | Domain detection, codebase analysis, deliverable patterns |
| `triage` | 5-finalize | Decision-making knowledge for findings (suppression syntax, severity rules) |

**Phases without extensions:**

| Phase | Knowledge Source |
|-------|------------------|
| 1-init | No domain knowledge needed |
| 3-plan | `planning` profile - task decomposition patterns |
| 4-execute | `task.profile` - implementation guidance |

---

## Extension Resolution

```bash
# Resolve extension for a specific domain and type
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill-extension --domain java --type outline
```

Returns extension (or null if none):

```toon
status: success
domain: java
type: outline
extension: pm-dev-java:java-outline-ext
```

---

## marshal.json Configuration

```json
"java": {
  "workflow_skill_extensions": {
    "outline": "pm-dev-java:java-outline-ext",
    "triage": "pm-dev-java:java-triage"
  }
}
```

| Key | Purpose | Used By |
|-----|---------|---------|
| `outline` | Domain detection, codebase analysis, deliverable patterns | Outline phase |
| `triage` | Domain-specific findings handling | Finalize phase |

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

## Outline Extension

### Phase Overview

**System Skill**: `pm-workflow:phase-2-outline`

**Purpose**: Transform user request into solution outline with deliverables.

**Extension Purpose**: Provide domain-specific codebase analysis and deliverable patterns.

### Extension Points

| Extension Point | Section Name | Required | Description |
|-----------------|--------------|----------|-------------|
| Domain Detection | `## Domain Detection` | No | How to detect if this domain is relevant |
| Codebase Analysis | `## Codebase Analysis` | No | Domain-specific codebase analysis instructions |
| Deliverable Patterns | `## Deliverable Patterns` | No | Domain-specific deliverable structure patterns |

### `## Domain Detection`

**Purpose**: Determine if this domain is relevant to the current request.

**Expected Content**:
```markdown
## Domain Detection

This domain is relevant when:
1. {Condition 1 - e.g., pom.xml exists}
2. {Condition 2 - e.g., src/main/java directory exists}
3. {Condition 3 - e.g., request mentions Java/Maven/Spring}

Detection commands:
- Check for: {file pattern}
- Grep for: {code pattern}
```

**Default Behavior**: Domain is assumed relevant if configured in marshal.json.

### `## Codebase Analysis`

**Purpose**: Provide domain-specific instructions for analyzing the codebase.

**Expected Content**:
```markdown
## Codebase Analysis

When analyzing {domain} codebases:

### Project Structure
1. {What to look for - e.g., Maven modules, package structure}
2. {Patterns to identify - e.g., layered architecture, microservices}

### Key Files
- {Important file 1}: {What it tells us}
- {Important file 2}: {What it tells us}

### Architecture Patterns
- Identify: {pattern 1}
- Look for: {pattern 2}
```

**Default Behavior**: Generic file/directory analysis.

### `## Deliverable Patterns`

**Purpose**: Define how to structure deliverables for this domain.

**Expected Content**:
```markdown
## Deliverable Patterns

When creating deliverables for {domain}:

### Grouping Strategy
- {How to group work - e.g., by module, by feature}

### Deliverable Structure
Each deliverable should:
- {Guideline 1 - e.g., represent a cohesive unit}
- {Guideline 2 - e.g., be independently testable}

### Profile Assignment
- Implementation work: profile = `implementation`
- Test work: profile = `testing`
- {Domain-specific guidance}
```

**Default Behavior**: One deliverable per component/file with generic structure.

### Outline Extension Example: Java

```markdown
# Java Outline Extension

> Extension for 2-outline phase in Java domain.

## Domain Detection

This domain is relevant when:
1. `pom.xml` or `build.gradle` exists at project root
2. `src/main/java` directory exists
3. Request mentions Java, Maven, Gradle, Spring, Quarkus, or Jakarta EE

Detection commands:
- Glob: `**/pom.xml`, `**/build.gradle`
- Glob: `**/src/main/java/**/*.java`

## Codebase Analysis

When analyzing Java codebases:

### Project Structure
1. Check for multi-module Maven project (parent pom.xml with modules)
2. Identify package structure under src/main/java
3. Look for module-info.java (Java modules)

### Key Files
- `pom.xml`: Dependencies, plugins, module structure
- `application.properties/yaml`: Runtime configuration
- `module-info.java`: Module boundaries and exports

### Architecture Patterns
- Layered: controller/service/repository packages
- Hexagonal: adapter/port/domain packages
- CDI: Look for @Inject, @ApplicationScoped annotations

## Deliverable Patterns

When creating deliverables for Java:

### Grouping Strategy
- Group by Maven module for multi-module projects
- Group by feature/component for single-module projects
- Separate API packages from implementation packages

### Deliverable Structure
Each deliverable should:
- Represent a cohesive unit of functionality
- Include both production code and test code locations
- Be bounded by package/module boundaries

### Profile Assignment
- New classes, modifications: profile = `implementation`
- New test classes: profile = `testing`
- Build/config changes: profile = `implementation`
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

- [phase-outline-contract.md](phase-outline-contract.md) - Outline phase skill contract
- [phase-finalize-contract.md](phase-finalize-contract.md) - Finalize phase skill contract
- [extension-triage-contract.md](extension-triage-contract.md) - Triage extension requirements
- [deliverable-contract.md](../../manage-solution-outline/standards/deliverable-contract.md) - Deliverable structure
