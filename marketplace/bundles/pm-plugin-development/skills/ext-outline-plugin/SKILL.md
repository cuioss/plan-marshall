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
**Purpose**: Determine which artifacts and bundles are affected, then select workflow path

### Load Reference Data

```
Read standards/reference-tables.md
```

### Step 1: Artifact Type Analysis

For EACH artifact type, derive from the request whether it is affected. No assumptions - all must be explicit.

#### 1.1 Plugin Manifest (plugin.json)

```
ANALYZE request for plugin.json impact:
  - Are components being ADDED? (new skill, command, agent)
  - Are components being REMOVED?
  - Are components being RENAMED?

LOG: [DECISION] plugin.json: {AFFECTED|NOT_AFFECTED}
  reasoning: {explicit derivation from request}
  evidence: "{request fragment}" or "No mention of add/remove/rename"
```

#### 1.2 Commands

```
ANALYZE request for Commands impact:
  - Are commands EXPLICITLY mentioned in request?
  - Are commands IMPLICITLY affected? (derive how)

LOG: [DECISION] Commands: {AFFECTED|NOT_AFFECTED}
  explicit_mention: {yes|no} - "{quote}" or "none"
  implicit_impact: {yes|no} - "{derivation}" or "none"
  reasoning: {full reasoning chain}
```

#### 1.3 Skills

```
ANALYZE request for Skills impact:
  - Are skills EXPLICITLY mentioned in request?
  - Are skills IMPLICITLY affected? (derive how)

LOG: [DECISION] Skills: {AFFECTED|NOT_AFFECTED}
  explicit_mention: {yes|no} - "{quote}" or "none"
  implicit_impact: {yes|no} - "{derivation}" or "none"
  reasoning: {full reasoning chain}
```

#### 1.4 Agents

```
ANALYZE request for Agents impact:
  - Are agents EXPLICITLY mentioned in request?
  - Are agents IMPLICITLY affected? (derive how)

LOG: [DECISION] Agents: {AFFECTED|NOT_AFFECTED}
  explicit_mention: {yes|no} - "{quote}" or "none"
  implicit_impact: {yes|no} - "{derivation}" or "none"
  reasoning: {full reasoning chain}
```

#### 1.5 Scripts

```
ANALYZE request for Scripts impact:
  - Are scripts EXPLICITLY mentioned in request?
  - Are scripts IMPLICITLY affected? (derive how)

LOG: [DECISION] Scripts: {AFFECTED|NOT_AFFECTED}
  explicit_mention: {yes|no} - "{quote}" or "none"
  implicit_impact: {yes|no} - "{derivation}" or "none"
  reasoning: {full reasoning chain}
```

#### 1.6 Determine Affected Artifacts

```
affected_artifacts = [types where decision = AFFECTED]

LOG: [DECISION] Affected artifacts: {affected_artifacts}
  count: {N}
```

### Step 2: Bundle/Module Selection

Determine which bundles are potentially affected. Bundles are persisted in architecture as modules.

#### 2.1 Explicit Bundle Mentions

```
ANALYZE request for bundle/module references:
  - Direct bundle names: "pm-dev-java", "pm-workflow", "plan-marshall"
  - Module paths: "marketplace/bundles/{bundle}"

LOG: [DECISION] Explicit bundles: {list or "none"}
  evidence: "{quotes}" or "No bundle names mentioned"
```

#### 2.2 Implicit Bundle Derivation (via Components)

```
ANALYZE request for component references that imply bundles:
  - Specific component names imply their containing bundle
  - Component patterns may span multiple bundles

LOG: [DECISION] Implicit bundles (via components): {list or "none"}
  derivation: "{component} → {bundle}" for each
```

#### 2.3 Determine Bundle Scope

```
explicit_bundles = [from 2.1]
implicit_bundles = [from 2.2]
all_bundles = union(explicit_bundles, implicit_bundles)

IF all_bundles is empty AND affected_artifacts is not empty:
  bundle_scope = "all"
ELSE:
  bundle_scope = all_bundles

LOG: [DECISION] Bundle scope: {bundle_scope}
  explicit: {explicit_bundles}
  implicit: {implicit_bundles}
```

### Step 3: Path Selection

Based on Steps 1-2 results:

```
IF affected_artifacts is empty:
  ERROR: "No artifacts affected - clarify request"
ELSE IF len(bundle_scope) == 1 AND len(affected_artifacts) <= 2:
  path = "single"
ELSE:
  path = "multi"

LOG: [DECISION] Workflow path: {path}
  affected_artifacts: {affected_artifacts}
  affected_bundles: {bundle_scope}
  reasoning: {derivation}
```

### Conditional Standards

| Condition | Additional Standard |
|-----------|---------------------|
| Deliverable involves Python scripts | `standards/script-verification.md` |

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[DECISION] (pm-plugin-development:ext-outline-plugin) Conditional standards: {list or 'none'}"
```

### Key Principle: No Preconditions

**PROHIBITED patterns** (violations fail the assessment):
- "{type} not affected" without explicit reasoning → WRONG (derive from request)
- "Commands are procedural" → WRONG (analyze each type per Steps 1.1-1.5)
- "Only analyzing {type}" → WRONG if other types in affected_artifacts
- Skipping Step 1 or Step 2 → WRONG (all steps are mandatory)

---

## Simple Workflow

**Called by**: phase-2-outline Step 4 (when path = single)
**Purpose**: Create deliverables for isolated changes

**Inputs from Assessment**:
- `affected_artifacts`: From Step 1.6 - constrains which component types to target
- `bundle_scope`: From Step 2.3 - constrains which bundles to target

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

**Called by**: phase-2-outline Step 4 (when path = multi)
**Purpose**: Create deliverables for cross-cutting changes with file enumeration

**Inputs from Assessment**:
- `affected_artifacts`: From Step 1.6 - constrains which component types to scan
- `bundle_scope`: From Step 2.3 - constrains which bundles to scan

### Load Workflow

```
Read standards/path-multi-workflow.md
```

**CRITICAL**: The workflow receives `affected_artifacts` and `bundle_scope` from Steps 1-2. It MUST use these values to constrain the inventory scan and component analysis - do NOT re-derive scope.

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
| Script notation rename | `grep -r "{old_notation}" marketplace/bundles/` |
| Content pattern search | `grep -r '{pattern_from_request}' marketplace/bundles/` |
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

