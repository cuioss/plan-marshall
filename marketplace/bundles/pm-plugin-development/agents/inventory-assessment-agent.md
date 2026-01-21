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

```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(inventory-assessment-agent) plugin.json: {AFFECTED|NOT_AFFECTED} - reasoning: {explicit derivation}, evidence: {request fragment or 'No mention of add/remove/rename'}"
```

#### 1.2 Commands

```
ANALYZE request for Commands impact:
  - Are commands EXPLICITLY mentioned in request?
  - Are commands IMPLICITLY affected? (derive how)

```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(inventory-assessment-agent) Commands: {AFFECTED|NOT_AFFECTED} - explicit: {yes|no} '{quote}', implicit: {yes|no} '{derivation}'"
```

#### 1.3 Skills

```
ANALYZE request for Skills impact:
  - Are skills EXPLICITLY mentioned in request?
  - Are skills IMPLICITLY affected? (derive how)

```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(inventory-assessment-agent) Skills: {AFFECTED|NOT_AFFECTED} - explicit: {yes|no} '{quote}', implicit: {yes|no} '{derivation}'"
```

#### 1.4 Agents

```
ANALYZE request for Agents impact:
  - Are agents EXPLICITLY mentioned in request?
  - Are agents IMPLICITLY affected? (derive how)

```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(inventory-assessment-agent) Agents: {AFFECTED|NOT_AFFECTED} - explicit: {yes|no} '{quote}', implicit: {yes|no} '{derivation}'"
```

#### 1.5 Scripts

```
ANALYZE request for Scripts impact:
  - Are scripts EXPLICITLY mentioned in request?
  - Are scripts IMPLICITLY affected? (derive how)

```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(inventory-assessment-agent) Scripts: {AFFECTED|NOT_AFFECTED} - explicit: {yes|no} '{quote}', implicit: {yes|no} '{derivation}'"
```

#### 1.6 Determine Affected Artifacts

```
affected_artifacts = [types where decision = AFFECTED]
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(inventory-assessment-agent) Affected artifacts: {affected_artifacts}"
```

### Step 2: Bundle/Module Selection

#### 2.1 Explicit Bundle Mentions

```
ANALYZE request for bundle/module references:
  - Direct bundle names: "pm-dev-java", "pm-workflow", "plan-marshall"
  - Module paths: "marketplace/bundles/{bundle}"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(inventory-assessment-agent) Explicit bundles: {list or 'none'}"
```

#### 2.2 Implicit Bundle Derivation (via Components)

```
ANALYZE request for component references that imply bundles:
  - Specific component names imply their containing bundle
  - Component patterns may span multiple bundles
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(inventory-assessment-agent) Implicit bundles: {list or 'none'}"
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
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision {plan_id} INFO "(inventory-assessment-agent) Bundle scope: {bundle_scope}"
```

### Step 3: Create Work Directory and Run Inventory Scan

First, create the work directory and capture the path:

```bash
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files mkdir \
  --plan-id {plan_id} \
  --dir work
```

**Output** (TOON):
```toon
status: success
plan_id: {plan_id}
action: created
dir: work
path: {work_dir_path}
```

Extract `path` from the result - this is the full path to the work directory.

Then execute the inventory script with `--output` using the captured path:

**If bundle_scope is "all"** (scan all bundles):
```bash
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} \
  --resource-types {affected_artifacts} \
  --full \
  --output {work_dir_path}/inventory_raw.toon
```

**If bundle_scope is specific bundles**:
```bash
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} \
  --resource-types {affected_artifacts} \
  --bundles {comma-separated-bundle-names} \
  --full \
  --output {work_dir_path}/inventory_raw.toon
```

Note: Omit `--bundles` to scan all bundles. Use `--bundles pm-dev-java,pm-workflow` for specific bundles.

Store reference to the raw inventory:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references set \
  --plan-id {plan_id} \
  --field inventory_raw \
  --value "work/inventory_raw.toon"
```

### Step 4: Convert and Group Inventory by Type

Read the raw inventory file:

```bash
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files read \
  --plan-id {plan_id} \
  --file work/inventory_raw.toon
```

The inventory output uses bundle-block format where bundles are top-level keys:

```toon
plan-marshall:
  path: marketplace/bundles/plan-marshall
  skills[N]:
    - skill-name1
    - skill-name2
  commands[N]:
    - command-name1
  agents[N]:
    - agent-name1
```

Extract components from each bundle and convert to file paths:

**Skills**: Construct path as `{bundle_path}/skills/{skill_name}/SKILL.md`:
```
bundle_path: marketplace/bundles/pm-dev-java
skill_name: java-cdi
file_path: marketplace/bundles/pm-dev-java/skills/java-cdi/SKILL.md
```

**Commands**: Construct path as `{bundle_path}/commands/{command_name}.md`

**Agents**: Construct path as `{bundle_path}/agents/{agent_name}.md`

**Scripts**: Default mode doesn't include scripts with full paths. Use bundle notation from statistics if needed.

Group all paths by component type across all bundles.

### Step 5: Persist Filtered Inventory

Build the filtered inventory TOON content and persist it (work directory already created in Step 3):

```bash
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files write \
  --plan-id {plan_id} \
  --file work/inventory_filtered.toon \
  --content "# Filtered Inventory

scope:
  affected_artifacts: [{affected_artifacts}]
  bundle_scope: {bundle_scope}

inventory:
  skills[{skill_count}]:
{skill_file_paths_indented}
  commands[{command_count}]:
{command_file_paths_indented}
  agents[{agent_count}]:
{agent_file_paths_indented}

total_files: {total_count}
"
```

### Step 6: Store Reference

Link the persisted file in references.toon:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references set \
  --plan-id {plan_id} \
  --field inventory_filtered \
  --value "work/inventory_filtered.toon"
```

### Step 7: Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[ARTIFACT] (inventory-assessment-agent) Persisted inventory: work/inventory_filtered.toon ({total_files} files)"
```

## Output

Return TOON summary with persisted file path:

```toon
status: success
plan_id: {plan_id}
inventory_file: work/inventory_filtered.toon

scope:
  affected_artifacts: [skills, commands, agents]
  bundle_scope: all

counts:
  skills: {N}
  commands: {N}
  agents: {N}
  total: {N}
```

**Notes**:
- `inventory_file`: Relative path within plan directory (use with manage-files read)
- Full inventory data is in the persisted file, not in this output
- Caller can read full file paths from `work/inventory_filtered.toon`

## Critical Rules

- **Derive from request**: Every artifact type decision must cite evidence from the request
- **No assumptions**: "Skills are documentation" or "Agents don't have X" are PROHIBITED
- **Log all decisions**: Every Step 1.x and 2.x determination must be logged
- **Use script for inventory**: Do NOT use ad-hoc Glob/Grep for component discovery
