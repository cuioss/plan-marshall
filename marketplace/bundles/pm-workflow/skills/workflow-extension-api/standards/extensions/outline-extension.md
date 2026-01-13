# Outline Extension Contract

Contract for domain-specific outline extensions loaded by `phase-2-outline`.

---

## Purpose

Outline extensions are **knowledge documents** (not workflow replacements) that provide domain-specific information for deliverable creation. They are loaded as context and applied naturally during the standard workflow.

**Key Principle**: Extensions are just skills with a specific structure. They provide information that Claude uses when creating deliverables - no special processing needed.

Outline extensions provide domain-specific knowledge through three section types:

1. **Domain Constraints** - Rules/restrictions for deliverables (component rules, dependency rules)
2. **Deliverable Patterns** - Grouping strategies, file structures, verification commands
3. **Impact Analysis Patterns** - Discovery commands for cross-cutting changes

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
| `## Domain Detection` | When this domain is relevant | No |
| `## Domain Constraints` | Rules for deliverable creation | No |
| `## Deliverable Patterns` | Grouping strategies and file structures | No |
| `## Impact Analysis Patterns` | Discovery commands for cross-cutting changes | No |

All sections are optional - the system skill has defaults for each.

---

## Section: Domain Detection

**Purpose**: Determine if this domain is relevant to the current request.

**Expected Content**:
```markdown
## Domain Detection

This domain is relevant when:
1. {Condition 1 - e.g., marketplace/bundles directory exists}
2. {Condition 2 - e.g., request mentions "skill", "command", "agent"}
3. {Condition 3 - e.g., files being modified are in marketplace/bundles/}
```

**Default Behavior**: Domain is assumed relevant if configured in plan's config.toon.

---

## Section: Domain Constraints

**Purpose**: Define rules and restrictions that apply to deliverables in this domain.

**Expected Content**:
```markdown
## Domain Constraints

### Component Rules
- {Rule 1 - e.g., Skills MUST have SKILL.md in skills/skill-name/}
- {Rule 2 - e.g., Documentation changes do NOT require unit tests}

### Dependency Rules
- {Rule 1 - e.g., Agents must not depend on commands}
- {Rule 2 - e.g., Skills should be self-contained}

### Verification Rules
- Standard verification: `{command template}`
- {Additional verification guidance}
```

**Default Behavior**: Standard deliverable contract rules apply.

---

## Section: Deliverable Patterns

**Purpose**: Define how to structure and group deliverables for this domain.

**Expected Content**:
```markdown
## Deliverable Patterns

### Grouping Strategy
| Scenario | Grouping |
|----------|----------|
| {Scenario 1} | {How to group} |
| {Scenario 2} | {How to group} |

### Change Type Mappings
| Request Pattern | change_type | execution_mode |
|-----------------|-------------|----------------|
| "add", "create" | create | automated |
| "fix", "update" | modify | automated |

### Standard File Structures
{Domain-specific file path patterns}
```

**Default Behavior**: One deliverable per module with generic structure.

---

## Section: Impact Analysis Patterns

**Purpose**: Provide discovery commands for analyzing cross-cutting changes.

**Expected Content**:
```markdown
## Impact Analysis Patterns

### Detection Commands
| Change Type | Discovery Command | Result Interpretation |
|-------------|-------------------|----------------------|
| {Change type} | `{grep or glob}` | {What matches mean} |

### Discovery Script (if domain has inventory script)
```bash
python3 .plan/execute-script.py {notation} {args}
```

### Batch Analysis Guidelines
- Batch size: {recommended batch size}
- {Additional guidance for large-scale changes}
```

**Default Behavior**: Standard glob/grep patterns for file discovery.

---

## Extension Skill Template

```markdown
---
name: ext-outline-{domain}
description: Outline extension for {domain} domain
allowed-tools: Read
---

# {Domain} Outline Extension

> Extension for phase-2-outline in {domain} domain.

## Domain Detection

This domain is relevant when:
1. {Condition 1}
2. {Condition 2}

## Domain Constraints

### Component Rules
- {Rule 1}
- {Rule 2}

### Dependency Rules
- {Rule 1}

### Verification Rules
- Standard verification: `{command}`

## Deliverable Patterns

### Grouping Strategy
| Scenario | Grouping |
|----------|----------|
| {Scenario 1} | {How to group} |

### Standard File Structures
{Domain file patterns}

## Impact Analysis Patterns

### Detection Commands
| Change Type | Discovery Command |
|-------------|-------------------|
| {Type 1} | `{command}` |

### Discovery Script
```bash
python3 .plan/execute-script.py {notation} {args}
```
```

---

## Example: Plugin Development Outline Extension

```markdown
# Plugin Development Outline Extension

> Extension for phase-2-outline in plugin development domain.

## Domain Detection

This domain is relevant when:
1. `marketplace/bundles` directory exists
2. Request mentions "skill", "command", "agent", "bundle"
3. Files being modified are in `marketplace/bundles/*/` paths

## Domain Constraints

### Component Rules
- Skills MUST have `SKILL.md` in `skills/{skill-name}/`
- Commands MUST be single `.md` files in `commands/`
- Agents MUST be single `.md` files in `agents/`
- All components require YAML frontmatter

### Dependency Rules
- Agents delegate to skills (skill loading via `Skill:` directive)
- Commands orchestrate agents or execute skills directly

### Verification Rules
- Standard verification: `/plugin-doctor --component {path}`

## Deliverable Patterns

### Grouping Strategy
| Scenario | Grouping |
|----------|----------|
| Creating 1-3 components in single bundle | One deliverable per component |
| Cross-bundle pattern change | One deliverable per bundle affected |
| Script changes | Include script + tests in same deliverable |

### Standard File Structures
- Skills: `marketplace/bundles/{bundle}/skills/{skill-name}/SKILL.md`
- Commands: `marketplace/bundles/{bundle}/commands/{command-name}.md`
- Agents: `marketplace/bundles/{bundle}/agents/{agent-name}.md`

## Impact Analysis Patterns

### Detection Commands
| Change Type | Discovery Command |
|-------------|-------------------|
| Script notation rename | `grep -r "old:notation" marketplace/bundles/` |
| Output format change | `grep -r '```json' marketplace/bundles/*/agents/` |

### Discovery Script
```bash
python3 .plan/execute-script.py plan-marshall:marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} --include-descriptions
```
```

---

## Example: Documentation Outline Extension

```markdown
# Documentation Outline Extension

> Extension for phase-2-outline in documentation domain.

## Domain Detection

This domain is relevant when:
1. `doc/` or `docs/` directory exists
2. Request mentions "AsciiDoc", "ADR", "interface specification"
3. Files have `.adoc` extension

## Domain Constraints

### Component Rules
- AsciiDoc files MUST have blank line before lists
- Cross-references MUST use `xref:` syntax
- ADRs MUST follow numbered naming: `ADR-NNN-title.adoc`
- Interface specs MUST follow numbered naming: `IF-NNN-title.adoc`

### Dependency Rules
- Documentation changes do NOT require unit tests
- Changes to doc/ do NOT trigger build verification
- ADR changes require review of supersedes/superseded-by links

### Verification Rules
- AsciiDoc validation: `docs validate {path}`
- Link verification: `docs verify-links --directory {path}`

## Deliverable Patterns

### Grouping Strategy
| Scenario | Grouping |
|----------|----------|
| Single document update | One deliverable |
| ADR creation with related updates | One deliverable for all related ADRs |
| Documentation sync with code | Doc deliverable depends on code deliverable |

### Standard File Structures
- ADRs: `doc/adr/ADR-NNN-{title}.adoc`
- Interfaces: `doc/interfaces/IF-NNN-{title}.adoc`
- General: `doc/{topic}/`

## Impact Analysis Patterns

### Detection Commands
| Change Type | Discovery Command |
|-------------|-------------------|
| Broken xrefs | `grep -r 'xref:' doc/*.adoc` |
| ADR supersedes | `grep -r 'Superseded by' doc/adr/` |
```

---

## Related Documents

- [extension-mechanism.md](extension-mechanism.md) - How extensions work
- [triage-extension.md](triage-extension.md) - Triage extension contract
- [phase-2-outline SKILL.md](../../../phase-2-outline/SKILL.md) - Phase that loads this extension
