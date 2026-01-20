---
name: ext-outline-plugin
description: Outline extension implementing protocol for plugin development domain
implements: pm-workflow:workflow-extension-api/standards/extensions/outline-extension.md
user-invocable: false
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
**Purpose**: Determine which artifacts and bundles are affected, extract change_type

### Delegate to Inventory Assessment Agent

The assessment logic is implemented by the `inventory-assessment-agent`. Spawn it to perform:
- Artifact Type Analysis (plugin.json, commands, skills, agents, scripts)
- Bundle Scope determination (explicit mentions, implicit derivation)
- Inventory scan via `scan-marketplace-inventory` script
- Grouping by component type

**Agent**: `pm-plugin-development:inventory-assessment-agent`

See agent documentation for full implementation details.

### Determine Change Type

After agent returns, determine `change_type` from request:

| Request Pattern | change_type |
|-----------------|-------------|
| "add", "create", "new" | create |
| "fix", "update" (localized) | modify |
| "rename", "migrate" | migrate |
| "refactor", "restructure" | refactor |

### Validation

```
IF affected_artifacts is empty:
  ERROR: "No artifacts affected - clarify request"
```

### Conditional Standards

| Condition | Additional Standard |
|-----------|---------------------|
| Deliverable involves Python scripts | `standards/script-verification.md` |

---

## Workflow

**Called by**: phase-2-outline Step 4
**Purpose**: Create deliverables based on change_type

### Load Workflow

```
Read standards/workflow.md
```

The workflow routes based on `change_type`:
- **create**: Build deliverables directly (files don't exist yet)
- **modify/migrate/refactor**: Run analysis agents, then build deliverables

### Change Type Mappings

| change_type | execution_mode | Execution Skill |
|-------------|----------------|-----------------|
| create | automated | `pm-plugin-development:plugin-create` |
| modify | automated | `pm-plugin-development:plugin-maintain` |
| migrate | automated | `pm-plugin-development:plugin-maintain` |
| refactor | automated | `pm-plugin-development:plugin-maintain` |

### Grouping Strategy

| Scenario | Grouping |
|----------|----------|
| Creating components | One deliverable per component |
| Script changes | Include script + tests in same deliverable |
| Cross-bundle pattern change | One deliverable per bundle |
| Rename/migration | Group by logical unit |

### Verification Commands

- Components: `/pm-plugin-development:plugin-doctor --component {path}`
- Scripts: `./pw module-tests {bundle}`
