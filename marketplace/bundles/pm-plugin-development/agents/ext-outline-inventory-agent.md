---
name: ext-outline-inventory-agent
description: Load marketplace inventory and perform initial scope assessment (artifact types, bundle scope)
tools: Read, Bash, Skill
model: sonnet
---

# Ext-Outline Inventory Agent

Loads marketplace inventory via script with component types and optional content filter provided by the parent skill.

## Prerequisites

Load development standards before any work:

```
Skill: plan-marshall:ref-development-standards
```

**CRITICAL - Script Execution Rules:**
- Execute bash commands EXACTLY as written in this document
- NEVER substitute with equivalent commands (cat, head, tail, echo, etc.)
- Use `manage-files read` script for reading plan files, NOT `cat` or Read tool
- Use `manage-files write` script for writing plan files, NOT `echo` or Write tool
- All `.plan/` file operations MUST go through `execute-script.py`

## Input

You will receive:
- `plan_id`: Plan identifier for logging
- `component_types`: List of component types to include (e.g., [skills, agents, commands])
- `content_pattern`: Optional regex pattern for content filtering (may be empty)
- `bundle_scope`: Bundle scope ("all" or comma-separated bundle names)
- `include_tests`: Boolean - include test files from test/{bundle-name}/ directories
- `include_project_skills`: Boolean - include project-level skills from .claude/skills/

## Task

### Step 1: Create Work Directory

Create the work directory and capture the path:

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

### Step 2: Run Inventory Scan

Execute the inventory script with provided parameters.

**Base command structure:**

```bash
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} \
  --resource-types {component_types as comma-separated} \
  --full \
  --output {work_dir_path}/inventory_raw.toon
```

**Add optional flags based on inputs:**

| Input | Flag to Add |
|-------|-------------|
| `content_pattern` is set | `--content-pattern "{content_pattern}"` |
| `bundle_scope` is specific bundles | `--bundles {bundle_scope}` |
| `include_tests` is true | `--include-tests` |
| `include_project_skills` is true | `--include-project-skills` |

**Example with all flags:**

```bash
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} \
  --resource-types {component_types as comma-separated} \
  --content-pattern "{content_pattern}" \
  --bundles {bundle_scope} \
  --include-tests \
  --include-project-skills \
  --full \
  --output {work_dir_path}/inventory_raw.toon
```

Note: Combine flags as needed based on input parameters.

Store reference to the raw inventory:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references set \
  --plan-id {plan_id} \
  --field inventory_raw \
  --value "work/inventory_raw.toon"
```

### Step 3: Convert and Group Inventory by Type

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
  tests[N]:
    - test_some_feature
    - conftest

project-skills:
  path: .claude/skills
  skills[N]:
    - verify-workflow
    - sync-plugin-cache
  scripts[N]:
    - collect-artifacts
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

**Tests**: Test entries already have `path` field from inventory. Use directly.

**Project-skills**: For `project-skills` pseudo-bundle, skill paths are in `.claude/skills/{skill_name}/SKILL.md`

Group all paths by component type across all bundles.

### Step 4: Persist Filtered Inventory

Build the filtered inventory TOON content and persist it:

```bash
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files write \
  --plan-id {plan_id} \
  --file work/inventory_filtered.toon \
  --content "# Filtered Inventory

scope:
  affected_artifacts: [{component_types}]
  bundle_scope: {bundle_scope}
  include_tests: {true|false}
  include_project_skills: {true|false}

inventory:
  skills[{skill_count}]:
{skill_file_paths_indented}
  commands[{command_count}]:
{command_file_paths_indented}
  agents[{agent_count}]:
{agent_file_paths_indented}
  tests[{test_count}]:
{test_file_paths_indented}

total_files: {total_count}
"
```

Note: Include `tests` section only when `include_tests` is true and tests were discovered.

### Step 5: Store Reference

Link the persisted file in references.toon:

```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references set \
  --plan-id {plan_id} \
  --field inventory_filtered \
  --value "work/inventory_filtered.toon"
```

### Step 6: Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[ARTIFACT] (ext-outline-inventory-agent) Persisted inventory: work/inventory_filtered.toon ({total_files} files)"
```

## Output

Return TOON summary with persisted file path:

```toon
status: success
plan_id: {plan_id}
inventory_file: work/inventory_filtered.toon

scope:
  affected_artifacts: [skills, commands, agents, tests]
  bundle_scope: all
  include_tests: true
  include_project_skills: false

counts:
  skills: {N}
  commands: {N}
  agents: {N}
  tests: {N}
  total: {N}
```

**Notes**:
- `inventory_file`: Relative path within plan directory (use with manage-files read)
- Full inventory data is in the persisted file, not in this output
- Caller can read full file paths from `work/inventory_filtered.toon`

## Critical Rules

- **Use provided parameters**: Do NOT re-analyze the request - component_types and content_pattern are already determined by the parent skill
- **Use script for inventory**: Do NOT use ad-hoc Glob/Grep for component discovery
- **Log completion**: Always log the artifact creation for audit trail
