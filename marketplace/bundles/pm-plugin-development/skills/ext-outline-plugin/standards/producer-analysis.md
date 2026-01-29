# Producer Analysis Standard

Standard for discovering scripts that produce output affected by change requests.

## Overview

Producer discovery uses forward dependency resolution (`deps`) to find scripts referenced by skills. This complements impact analysis (`rdeps`) which finds components that depend on affected components.

| Analysis Type | Direction | Question Answered |
|---------------|-----------|-------------------|
| Impact Analysis | rdeps (reverse) | "Who depends on me?" |
| Producer Discovery | deps (forward) | "What scripts do I reference?" |

## When to Apply

Run producer discovery when ANY of these conditions are met:

- `change_type` is `migrate` or `modify`
- Request contains: "output", "format", "return value", "produces", "generates"
- Content filter targets output sections (`` ```json ``, `## Output`, format patterns)
- Request mentions format-specific terms (JSON, TOON, YAML, XML)

## Skip When

- `change_type` is `create` (scripts don't exist yet)
- No skills in inventory (nothing to resolve deps for)
- Request explicitly excludes scripts

## How It Works

1. Extract skill file paths from `inventory_filtered.toon`
2. Convert paths to component notations (`{bundle}:{skill}`)
3. For each skill, resolve forward dependencies with `--dep-types script`
4. Add discovered scripts to inventory if they exist and aren't already included

### Dependency Resolution

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:resolve-dependencies \
  deps --component {skill_notation} --dep-types script --direct-result --format json
```

## Scope Expansion Rules

### Include a Script When

- Referenced in skill's SKILL.md via execute-script.py notation
- File exists at the resolved path
- Not already in inventory `scripts` list

### Exclude When

- Script path doesn't exist (stale reference)
- Script already in inventory
- Reference is in documentation only (not executable)

## Notation Conversion

| File Path Pattern | Component Notation |
|-------------------|-------------------|
| `marketplace/bundles/{b}/skills/{s}/SKILL.md` | `{b}:{s}` |
| `marketplace/bundles/{b}/skills/{s}/scripts/{sc}.py` | `{b}:{s}:{sc}` |

## Output Contract

The `producer-analysis` subcommand produces:

### producer_analysis.toon

```toon
status: success
skills_analyzed: 5
producers_found: 8
producers_added: 4
added_files[4]:
  - marketplace/bundles/pm-workflow/skills/manage-files/scripts/manage-files.py
  - marketplace/bundles/pm-workflow/skills/manage-tasks/scripts/manage-tasks.py
  - marketplace/bundles/pm-workflow/skills/manage-references/scripts/manage-references.py
  - marketplace/bundles/pm-workflow/skills/manage-solution-outline/scripts/manage-solution-outline.py
```

### Updated inventory_filtered.toon

The original inventory is expanded in-place with producer scripts added to `inventory.scripts`.

## Error Handling

### resolve-dependencies Fails for One Skill

**Action**: Log warning and continue. Producer discovery is non-fatal.

```
Log: "Producer discovery: JSON parse error for {notation}"
```

**Rationale**: Missing one skill's deps shouldn't block the entire workflow. The LLM can still analyze discovered producers.

### No Scripts Found

**Action**: Complete successfully with zero counts.

```toon
status: success
skills_analyzed: 5
producers_found: 0
producers_added: 0
added_files[0]:
```

**Note**: This is valid - not all skills have script dependencies.

## Integration with Workflow

Producer discovery runs in Step 2.5, after basic discovery (Step 2) and before analysis (Step 3):

```
Step 2:   Discovery         → inventory_filtered.toon (skills, commands, agents)
Step 2.5: Producer Discovery → inventory_filtered.toon += producer scripts
Step 3:   Change Type       → routes to Create/Modify flow
Step 4:   Analysis          → analyzes full inventory including scripts
```

## Example

Given request: "Migrate agent return values from JSON to TOON format"

1. **Step 2** discovers 5 SKILL.md files with `## Output` sections
2. **Step 2.5** resolves deps for each skill:
   - `pm-workflow:manage-tasks` → `pm-workflow:manage-tasks:manage-tasks`
   - `pm-workflow:manage-files` → `pm-workflow:manage-files:manage-files`
3. **Inventory expanded** with 4 producer scripts
4. **Step 4** analyzes 5 skills + 4 scripts = 9 files
