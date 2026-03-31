---
name: tools-marketplace-inventory
description: Scans and reports complete marketplace inventory (bundles, agents, commands, skills, scripts)
user-invocable: false
---

# Marketplace Inventory Skill

## Enforcement

**Execution mode**: Select workflow and execute immediately using documented script commands.

**Prohibited actions:**
- Do not invoke scripts with arguments other than those documented in workflow steps
- Do not modify marketplace structure; this skill is read-only scanning
- Do not use `--direct-result` for large unfiltered inventories (use file mode instead)

**Constraints:**
- Run scripts EXACTLY as documented using `python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory ...`
- Run dependency scripts EXACTLY as documented using `python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:resolve-dependencies ...`
- All output is TOON format by default; use `--format json` only when explicitly needed

---

Provides complete marketplace inventory scanning capabilities using the scan-marketplace-inventory.py script.

## Purpose

This skill scans the marketplace directory structure and returns a comprehensive TOON inventory of all bundles and their resources (agents, commands, skills, scripts).

## When to Use This Skill

Activate this skill when you need to:
- Get a complete inventory of marketplace bundles
- Discover all available agents, commands, and skills
- Validate marketplace structure
- Generate reports on marketplace contents

## Workflow

When activated, this skill scans the marketplace and returns structured TOON inventory.

### Step 1: Execute Inventory Scan

Run the marketplace inventory scanner script:

**Script**: `pm-plugin-development:tools-marketplace-inventory`

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory --scope marketplace
```

The script will:
- Discover all bundles in marketplace/bundles/
- Enumerate agents, commands, and skills in each bundle
- Identify bundled scripts
- Write full TOON inventory to `.plan/temp/tools-marketplace-inventory/inventory-{timestamp}.toon`
- Return TOON summary with file path to stdout

### Step 2: Read Full Inventory

The script outputs a TOON summary to stdout. Bundles are top-level keys (not a list):

```toon
status: success
scope: marketplace
base_path: /path/to/marketplace/bundles

plan-marshall:
  path: marketplace/bundles/plan-marshall
  agents[1]:
    - research-best-practices-agent
  commands[2]:
    - tools-fix-intellij-diagnostics
    - tools-sync-agents-file
  skills[18]:
    - manage-architecture
    - extension-api
    - manage-lessons

pm-dev-java:
  path: marketplace/bundles/pm-dev-java
  agents[0]:
  skills[12]:
    - java-core
    - java-cdi

statistics:
  total_bundles: 8
  total_agents: 28
  total_commands: 46
  total_skills: 30
  total_scripts: 7
```

In file mode (default), a summary is printed and full inventory is written to `.plan/temp/tools-marketplace-inventory/inventory-{timestamp}.toon`.

## Script Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--scope` | `auto` | Scan scope: `auto`, `marketplace`, `plugin-cache`, `global`, `project` |
| `--resource-types` | `all` | Filter: `all`, `agents`, `commands`, `skills`, `scripts` (comma-separated) |
| `--bundles` | all | Filter to specific bundles (comma-separated) |
| `--name-pattern` | none | fnmatch glob filter, pipe-separated for multiple (e.g., `*-plan-*\|manage-*`) |
| `--content-pattern` | none | Regex content filter (requires `--include-descriptions` or `--full`) |
| `--content-exclude` | none | Regex content exclusion (requires `--include-descriptions` or `--full`) |
| `--include-descriptions` | off | Extract description fields from YAML frontmatter |
| `--full` | off | Include frontmatter fields and skill subdirectory contents |
| `--include-tests` | off | Include test files from `test/{bundle-name}/` directories |
| `--include-project-skills` | off | Include project-level skills from `.claude/skills/` |
| `--direct-result` | off | Output full TOON to stdout instead of writing to file |
| `--format` | `toon` | Output format: `toon` or `json` |

For detailed parameter documentation with examples: `Read references/parameter-guide.md`

## Error Handling

If the script fails:
- Check that the working directory is the repository root
- Verify marketplace/bundles/ directory exists
- Ensure script has execute permissions

## Non-Prompting Requirements

This skill is designed to run without user prompts. Required permissions:

**Script Execution:**
- `Bash(bash:*)` - Bash interpreter
- Script permissions synced via `/tools-setup-project-permissions`

**Ensuring Non-Prompting:**
- Resolve script paths from `.plan/scripts-library.toon` (system convention)
- Script reads marketplace directory structure
- Writes inventory to `.plan/temp/` (covered by `Write(.plan/**)` permission)
- All output is TOON format

---

## Dependency Resolution

The `resolve-dependencies.py` script tracks and resolves all dependency relationships across marketplace components.

### Dependency Types

| Type | Pattern | Detection Method |
|------|---------|------------------|
| `script` | `bundle:skill:script` | Regex in markdown/python |
| `skill` | `skills:` frontmatter, `Skill: bundle:skill` | YAML + regex |
| `import` | `from module import ...` | AST parsing |
| `path` | `../../skill/file.md` | Markdown link regex |
| `implements` | `implements: bundle:skill/path` frontmatter | YAML parsing |

### Component Notation

```
bundle:skill                    # Skill (e.g., plan-marshall:phase-1-init)
bundle:skill:script             # Script (e.g., plan-marshall:manage-files:manage-files)
bundle:agents:name              # Agent (e.g., plan-marshall:agents:phase-agent)
bundle:commands:name            # Command (e.g., plan-marshall:commands:tools-fix)
```

### Subcommands

#### deps - Get Dependencies

Get direct and transitive dependencies of a component:

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:resolve-dependencies \
  deps --component plan-marshall:manage-files --direct-result
```

**Output**:
```toon
status: success
component: plan-marshall:manage-files
component_type: skill
file_path: marketplace/bundles/plan-marshall/skills/manage-files/SKILL.md

direct_dependencies[4]:
  - target: plan-marshall:ref-toon-format:toon_parser, type: import, context: line:28
  - target: plan-marshall:tools-file-ops:file_ops, type: import, context: line:26

transitive_dependencies[2]:
  - target: plan-marshall:ref-toon-format, depth: 2, via: plan-marshall:ref-toon-format:toon_parser

statistics:
  direct_count: 4
  transitive_count: 2
  by_type: {import: 3, path: 1}
```

#### rdeps - Get Reverse Dependencies

Get components that depend on a given component:

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:resolve-dependencies \
  rdeps --component plan-marshall:ref-toon-format:toon_parser --direct-result
```

#### tree - Visual Dependency Tree

Generate a visual dependency tree:

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:resolve-dependencies \
  tree --component plan-marshall:manage-files --depth 3 --direct-result
```

**Output**:
```
plan-marshall:manage-files
├── plan-marshall:ref-toon-format:toon_parser (import)
│   └── plan-marshall:ref-toon-format (skill)
├── plan-marshall:tools-file-ops:file_ops (import)
└── plan-marshall:manage-logging:plan_logging (import)
```

#### validate - Check for Issues

Validate all dependencies and check for broken or circular references:

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:resolve-dependencies \
  validate --scope marketplace --direct-result
```

**Output**:
```toon
status: success
validation_result: passed
total_components: 95
total_dependencies: 234
resolved: 231
unresolved_count: 3

unresolved[3]:
  - source: plan-marshall:manage-files, target: nonexistent:skill, type: skill, context: frontmatter
```

### Options

| Option | Description |
|--------|-------------|
| `--component <notation>` | Component to resolve (required for deps/rdeps/tree) |
| `--scope <value>` | auto, marketplace, plugin-cache, project (default: auto) |
| `--format <value>` | toon (default), json |
| `--direct-result` | Output to stdout |
| `--depth <N>` | Max transitive depth (default: 10) |
| `--dep-types <types>` | Filter: script,skill,import,path,implements (comma-separated) |

### Examples

```bash
# Get all dependencies of a skill
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:resolve-dependencies \
  deps --component plan-marshall:phase-1-init --direct-result

# Get only import dependencies
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:resolve-dependencies \
  deps --component plan-marshall:manage-files --dep-types import --direct-result

# Find what depends on a module
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:resolve-dependencies \
  rdeps --component plan-marshall:ref-toon-format:toon_parser --direct-result --format json

# Validate entire marketplace
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:resolve-dependencies \
  validate --scope marketplace
```

## Planning Inventory

The `scan-planning-inventory` script provides a focused view of all planning-related components across the marketplace. It wraps `scan-marketplace-inventory` with predefined planning filters and categorizes results into core (plan-marshall) and derived (domain bundles) categories.

### Usage

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-planning-inventory scan
```

### Parameters

| Parameter | Values | Default | Description |
|-----------|--------|---------|-------------|
| `--format` | `full`, `summary` | `full` | Output format |
| `--include-descriptions` | flag | off | Include component descriptions from frontmatter |

### Examples

```bash
# Full inventory with all details
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-planning-inventory scan --format full

# Summary with component names only
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-planning-inventory scan --format summary

# Include descriptions
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-planning-inventory scan --include-descriptions
```

### Output

Results are organized into `core` (plan-marshall bundle) and `derived` (domain bundles) categories with statistics. Planning-related patterns: `plan-*`, `manage-*`, `*-workflow`, `workflow-*`, `task-*`, `*-task-plan`, `*-solution-outline`, `*-plan-*`.

## References

- Script location: scripts/scan-marketplace-inventory.py
- Planning inventory: scripts/scan-planning-inventory.py
- Dependency resolution: scripts/resolve-dependencies.py
- Marketplace root: marketplace/bundles/
