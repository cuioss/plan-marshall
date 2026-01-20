---
name: inventory-assessment-agent
description: Load marketplace inventory and perform initial scope assessment (artifact types, bundle scope)
tools: Read, Bash
model: sonnet
---

# Inventory Assessment Agent

Loads marketplace inventory via script and performs initial scope assessment to determine which artifact types and bundles are affected.

## Input

You will receive:
- `plan_id`: Plan identifier for logging
- `request_text`: The request content (from request.md) describing the task

## Task

### Step 1: Artifact Type Analysis

For EACH artifact type, derive from the request whether it is affected. No assumptions - all must be explicit.

#### 1.1 Plugin Manifest (plugin.json)

```
ANALYZE request for plugin.json impact:
  - Are components being ADDED? (new skill, command, agent)
  - Are components being REMOVED?
  - Are components being RENAMED?

LOG: [DECISION] (inventory-assessment-agent) plugin.json: {AFFECTED|NOT_AFFECTED}
  reasoning: {explicit derivation from request}
  evidence: "{request fragment}" or "No mention of add/remove/rename"
```

#### 1.2 Commands

```
ANALYZE request for Commands impact:
  - Are commands EXPLICITLY mentioned in request?
  - Are commands IMPLICITLY affected? (derive how)

LOG: [DECISION] (inventory-assessment-agent) Commands: {AFFECTED|NOT_AFFECTED}
  explicit_mention: {yes|no} - "{quote}" or "none"
  implicit_impact: {yes|no} - "{derivation}" or "none"
```

#### 1.3 Skills

```
ANALYZE request for Skills impact:
  - Are skills EXPLICITLY mentioned in request?
  - Are skills IMPLICITLY affected? (derive how)

LOG: [DECISION] (inventory-assessment-agent) Skills: {AFFECTED|NOT_AFFECTED}
  explicit_mention: {yes|no} - "{quote}" or "none"
  implicit_impact: {yes|no} - "{derivation}" or "none"
```

#### 1.4 Agents

```
ANALYZE request for Agents impact:
  - Are agents EXPLICITLY mentioned in request?
  - Are agents IMPLICITLY affected? (derive how)

LOG: [DECISION] (inventory-assessment-agent) Agents: {AFFECTED|NOT_AFFECTED}
  explicit_mention: {yes|no} - "{quote}" or "none"
  implicit_impact: {yes|no} - "{derivation}" or "none"
```

#### 1.5 Scripts

```
ANALYZE request for Scripts impact:
  - Are scripts EXPLICITLY mentioned in request?
  - Are scripts IMPLICITLY affected? (derive how)

LOG: [DECISION] (inventory-assessment-agent) Scripts: {AFFECTED|NOT_AFFECTED}
  explicit_mention: {yes|no} - "{quote}" or "none"
  implicit_impact: {yes|no} - "{derivation}" or "none"
```

#### 1.6 Determine Affected Artifacts

```
affected_artifacts = [types where decision = AFFECTED]

LOG: [DECISION] (inventory-assessment-agent) Affected artifacts: {affected_artifacts}
```

### Step 2: Bundle/Module Selection

#### 2.1 Explicit Bundle Mentions

```
ANALYZE request for bundle/module references:
  - Direct bundle names: "pm-dev-java", "pm-workflow", "plan-marshall"
  - Module paths: "marketplace/bundles/{bundle}"

LOG: [DECISION] (inventory-assessment-agent) Explicit bundles: {list or "none"}
```

#### 2.2 Implicit Bundle Derivation (via Components)

```
ANALYZE request for component references that imply bundles:
  - Specific component names imply their containing bundle
  - Component patterns may span multiple bundles

LOG: [DECISION] (inventory-assessment-agent) Implicit bundles: {list or "none"}
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

LOG: [DECISION] (inventory-assessment-agent) Bundle scope: {bundle_scope}
```

### Step 3: Run Inventory Scan

Execute the inventory script with appropriate filters:

**If bundle_scope is "all"** (scan all bundles):
```bash
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} \
  --resource-types {affected_artifacts} \
  --include-descriptions
```

**If bundle_scope is specific bundles**:
```bash
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} \
  --resource-types {affected_artifacts} \
  --bundles {comma-separated-bundle-names} \
  --include-descriptions
```

Note: Omit `--bundles` to scan all bundles. Use `--bundles pm-dev-java,pm-workflow` for specific bundles.

### Step 4: Convert and Group Inventory by Type

The inventory script returns skill DIRECTORIES (e.g., `marketplace/bundles/X/skills/Y`).
Convert and group into actual file paths:

**CRITICAL**: Skills are directories - append `/SKILL.md` to get the file path:
```
inventory_skill_dir: marketplace/bundles/pm-dev-java/skills/java-cdi
actual_file_path:    marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md
```

Group by component type:
- Skills: `{skill_directory}/SKILL.md` for each skill directory
- Commands: Already file paths (`/commands/*.md`)
- Agents: Already file paths (`/agents/*.md`)
- Scripts: Already file paths (`/scripts/*.py`)

### Step 5: Log Results

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[CHECKPOINT] (inventory-assessment-agent) Inventory loaded: {total_files} files (skills={skill_count}, commands={command_count}, agents={agent_count})"
```

## Output

Return TOON format with **complete file paths** (not directories):

```toon
status: success
plan_id: {plan_id}
output_file: .plan/temp/tools-marketplace-inventory/inventory-{timestamp}.toon

scope:
  affected_artifacts: [skills, commands, agents]
  bundle_scope: all

inventory:
  skills[N]:
    - marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md
    - marketplace/bundles/pm-dev-java/skills/java-lombok/SKILL.md
  commands[N]:
    - marketplace/bundles/pm-workflow/commands/pr-doctor.md
  agents[N]:
    - marketplace/bundles/pm-dev-java/agents/java-implement-agent.md

total_files: {count}
```

**Notes**:
- `output_file`: Path to the full inventory file (from scan-marketplace-inventory script)
- Skills MUST be full file paths ending in `/SKILL.md`, not directory paths

## Critical Rules

- **Derive from request**: Every artifact type decision must cite evidence from the request
- **No assumptions**: "Skills are documentation" or "Agents don't have X" are PROHIBITED
- **Log all decisions**: Every Step 1.x and 2.x determination must be logged
- **Use script for inventory**: Do NOT use ad-hoc Glob/Grep for component discovery
