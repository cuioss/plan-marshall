# Outline Extension Contract

Contract for domain-specific outline extensions loaded by `phase-2-outline`.

---

## Purpose

Outline extensions provide domain-specific knowledge for:

1. **Domain Detection** - How to detect if this domain is relevant
2. **Codebase Analysis** - Domain-specific analysis patterns
3. **Deliverable Patterns** - How to structure deliverables for this domain

---

## Extension Registration

Domains register outline extensions via `provides_outline()` in their `extension.py`:

```python
class Extension(ExtensionBase):
    def provides_outline(self) -> str | None:
        return "pm-dev-java:java-outline-ext"  # or None if no extension
```

---

## Resolution

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill-extension --domain java --type outline
```

Returns:
```toon
status: success
domain: java
type: outline
extension: pm-dev-java:java-outline-ext
```

---

## Required Sections

| Section | Purpose | Required |
|---------|---------|----------|
| `## Domain Detection` | Determine if domain is relevant | No |
| `## Codebase Analysis` | Domain-specific analysis patterns | No |
| `## Deliverable Patterns` | How to structure deliverables | No |

All sections are optional - the system skill has defaults for each.

---

## Section: Domain Detection

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

---

## Section: Codebase Analysis

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

---

## Section: Deliverable Patterns

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

---

## Extension Skill Template

```markdown
---
name: {domain}-outline-ext
description: Outline extension for {domain} domain
allowed-tools: Read
---

# {Domain} Outline Extension

> Extension for phase-2-outline in {domain} domain.

## Domain Detection

This domain is relevant when:
1. {Condition 1}
2. {Condition 2}

Detection commands:
- Glob: `{pattern}`

## Codebase Analysis

When analyzing {domain} codebases:

### Project Structure
{...}

### Key Files
{...}

### Architecture Patterns
{...}

## Deliverable Patterns

When creating deliverables for {domain}:

### Grouping Strategy
{...}

### Deliverable Structure
{...}

### Profile Assignment
{...}
```

---

## Example: Java Outline Extension

```markdown
# Java Outline Extension

> Extension for phase-2-outline in Java domain.

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

## Related Documents

- [extension-mechanism.md](extension-mechanism.md) - How extensions work
- [triage-extension.md](triage-extension.md) - Triage extension contract
- [phase-2-outline SKILL.md](../../../phase-2-outline/SKILL.md) - Phase that loads this extension
