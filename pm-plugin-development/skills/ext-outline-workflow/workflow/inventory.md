---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Marketplace Inventory Workflow

Loads marketplace inventory via the `tools-marketplace-inventory` script with caller-specified component types, content filter, bundle scope, and test / project-skill inclusion flags. Persists a filtered inventory file under the plan's work directory.

## Inputs

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `plan_id` | Yes | Plan identifier — used for the inventory file path and the audit log. |
| `WORKTREE` | Yes | Repo-relative working directory (`.` for main checkout). |
| `component_types[]` | Yes | List of component types to include (e.g., `[skills, agents, commands]`). |
| `content_pattern` | No | Optional regex pattern for content filtering. Empty string when not set. |
| `bundle_scope` | Yes | `"all"` or comma-separated bundle names. |
| `include_tests` | Yes | Boolean — include test files from `test/{bundle-name}/` directories. |
| `include_project_skills` | Yes | Boolean — include project-level skills from `.claude/skills/`. |

Skills the caller MUST forward in `skills[]`: `plan-marshall:manage-files` (work directory + read/write), `plan-marshall:manage-logging` (artifact log entry).

## Critical rules

- Execute bash commands EXACTLY as written below. NEVER substitute with equivalent commands (`cat`, `head`, `tail`, `echo`, etc.).
- Use `manage-files read` for reading plan files, NOT `cat` or the `Read` tool.
- Use `manage-files write` for writing plan files, NOT `echo` or the `Write` tool.
- All `.plan/` file operations MUST go through `python3 .plan/execute-script.py`.

## Step 1: Create the work directory

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files mkdir \
  --plan-id {plan_id} \
  --dir work
```

Returns:

```toon
status: success
plan_id: {plan_id}
action: created
dir: work
path: {work_dir_path}
```

Extract `path` as `{work_dir_path}`.

## Step 2: Run the inventory scan

Base command:

```bash
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --audit-plan-id {plan_id} \
  --resource-types {component_types as comma-separated} \
  --full \
  --output {work_dir_path}/inventory_raw.toon
```

Add optional flags based on the inputs:

| Input | Flag to add |
|-------|-------------|
| `content_pattern` is non-empty | `--content-pattern "{content_pattern}"` |
| `bundle_scope` is specific bundles | `--bundles {bundle_scope}` |
| `include_tests` is true | `--include-tests` |
| `include_project_skills` is true | `--include-project-skills` |

Combine flags as needed. Example with all flags set:

```bash
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --audit-plan-id {plan_id} \
  --resource-types {component_types as comma-separated} \
  --content-pattern "{content_pattern}" \
  --bundles {bundle_scope} \
  --include-tests \
  --include-project-skills \
  --full \
  --output {work_dir_path}/inventory_raw.toon
```

## Step 3: Convert and group inventory by type

Read the raw inventory:

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
  --plan-id {plan_id} \
  --file work/inventory_raw.toon \
  --audit-plan-id {plan_id}
```

The inventory uses bundle-block format (bundles are top-level keys):

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
    - plan-retrospective
    - sync-plugin-cache
  scripts[N]:
    - collect-artifacts
```

Convert each entry to a file path:

| Component type | Path construction |
|----------------|-------------------|
| Skills | `{bundle_path}/skills/{skill_name}/SKILL.md` |
| Commands | `{bundle_path}/commands/{command_name}.md` |
| Agents | `{bundle_path}/agents/{agent_name}.md` |
| Tests | Already includes `path` field — use directly |
| Project-skills | `.claude/skills/{skill_name}/SKILL.md` |

Group all paths by component type across all bundles.

## Step 4: Persist filtered inventory

1. Stage the rendered TOON payload via the `Write` tool to `.plan/temp/inventory_filtered.toon`. The payload is the multi-line block:

   ```text
   # Filtered Inventory

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
   ```

2. Invoke `manage-files write` with `--content-file`:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-files:manage-files write \
     --plan-id {plan_id} \
     --file work/inventory_filtered.toon \
     --audit-plan-id {plan_id} \
     --content-file .plan/temp/inventory_filtered.toon
   ```

Include the `tests` section only when `include_tests` is true and tests were discovered.

See `marketplace/bundles/plan-marshall/skills/manage-files/SKILL.md` § Enforcement and § write subsection for the binding rule.

## Step 5: Log completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[ARTIFACT] (execution-context.inventory) Persisted inventory: work/inventory_filtered.toon ({total_files} files)" \
  --audit-plan-id {plan_id}
```

## Output

```toon
status: success
display_detail: "<≤80 char ASCII summary>"
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

`inventory_file` is a relative path within the plan directory (use with `manage-files read`). The full inventory data lives in the persisted file, not in this return payload.

## Rules

- **Use provided parameters** — do NOT re-analyse the request; `component_types` and `content_pattern` are already determined by the caller.
- **Use the script for inventory** — do NOT use ad-hoc `Glob` / `Grep` for component discovery.
- **Log completion** — always log the artefact creation for the audit trail.
