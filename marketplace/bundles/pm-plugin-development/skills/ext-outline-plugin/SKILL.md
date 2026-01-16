---
name: ext-outline-plugin
description: Outline extension implementing protocol for plugin development domain
implements: pm-workflow:workflow-extension-api/standards/extensions/outline-extension.md
allowed-tools: Read
---

# Plugin Outline Extension

> Extension implementing outline protocol for plugin development domain.

Provides domain-specific knowledge for deliverable creation in marketplace plugin development tasks. Implements the outline extension protocol with defined sections that phase-2-outline calls explicitly.

## Domain Detection

This extension is relevant when:
1. `marketplace/bundles` directory exists
2. Request mentions "skill", "command", "agent", "bundle"
3. Files being modified are in `marketplace/bundles/*/` paths

---

## Assessment Protocol

**Called by**: phase-2-outline Step 3
**Purpose**: Determine which workflow applies (simple vs complex)

### Load Reference Data

```
Read standards/reference-tables.md
```

### Workflow Selection Criteria

| Indicator | Result | Rationale |
|-----------|--------|-----------|
| 1-3 components, single bundle | **simple** | Isolated changes, direct path |
| "rename", "migrate", "refactor" keywords | **complex** | Cross-cutting, needs inventory |
| Cross-bundle mentions | **complex** | Multiple bundles affected |
| Shared pattern changes | **complex** | Requires file enumeration |

### Conditional Standards

| Condition | Additional Standard |
|-----------|---------------------|
| Deliverable involves Python scripts | `standards/script-verification.md` |

---

## Simple Workflow

**Called by**: phase-2-outline Step 4 (when assessment = simple)
**Purpose**: Create deliverables for isolated changes

### Load Workflow

```
Read standards/path-single-workflow.md
```

### Domain-Specific Patterns

**Grouping Strategy**:
| Scenario | Grouping |
|----------|----------|
| Creating 1-3 components in single bundle | One deliverable per component |
| Script changes | Include script + tests in same deliverable |

**Change Type Mappings**:
| Request Pattern | change_type | execution_mode |
|-----------------|-------------|----------------|
| "add", "create", "new" | create | automated |
| "fix", "update" (localized) | modify | automated |

**Standard File Paths**:
- Skills: `marketplace/bundles/{bundle}/skills/{skill-name}/SKILL.md`
- Commands: `marketplace/bundles/{bundle}/commands/{command-name}.md`
- Agents: `marketplace/bundles/{bundle}/agents/{agent-name}.md`
- Scripts: `marketplace/bundles/{bundle}/skills/{skill-name}/scripts/{script}.py`
- Tests: `test/{bundle}/{skill-name}/test_{script}.py`

**Verification Commands**:
- Standard: `/pm-plugin-development:plugin-doctor --component {path}`
- Scripts: `./pw module-tests {bundle}`

---

## Complex Workflow

**Called by**: phase-2-outline Step 4 (when assessment = complex)
**Purpose**: Create deliverables for cross-cutting changes with file enumeration

### Load Workflow

```
Read standards/path-multi-workflow.md
```

### Domain-Specific Patterns

**Grouping Strategy**:
| Scenario | Grouping |
|----------|----------|
| Cross-bundle pattern change | One deliverable per bundle affected |
| Rename/migration | Group by logical unit being renamed |

**Change Type Mappings**:
| Request Pattern | change_type | execution_mode |
|-----------------|-------------|----------------|
| "rename", "migrate", "refactor" | refactor | automated |
| "change format", "update pattern" | migrate | automated |

**Inventory Script**:
```bash
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --include-descriptions
```

Returns TOON with `output_file` path to complete inventory.

**Batch Analysis**:
- Process components in batches of 10-15 files
- Build explicit file enumeration for each deliverable
- NEVER use wildcards in affected files list

**Verification Commands**:
- Standard: `/pm-plugin-development:plugin-doctor --component {path}`
- Scripts: `./pw module-tests {bundle}`

---

## Discovery Patterns

**Called by**: Both workflows during file enumeration
**Purpose**: Provide domain-specific Glob/Grep patterns for finding affected files

### Grep Patterns

| Change Type | Discovery Command |
|-------------|-------------------|
| Script notation rename | `grep -r "old:notation" marketplace/bundles/` |
| Output format change | `grep -r '```json' marketplace/bundles/*/agents/` |
| Skill reference update | `grep -r "Skill: {skill}" marketplace/bundles/` |
| Command usage | `grep -r "/{command}" marketplace/bundles/` |

### Glob Patterns

| Component Type | Glob Pattern |
|----------------|--------------|
| All skills | `marketplace/bundles/*/skills/*/SKILL.md` |
| All commands | `marketplace/bundles/*/commands/*.md` |
| All agents | `marketplace/bundles/*/agents/*.md` |
| All scripts | `marketplace/bundles/*/skills/*/scripts/*.py` |
| Bundle in specific bundle | `marketplace/bundles/{bundle}/**/*.md` |

