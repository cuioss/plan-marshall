---
name: pm-plugin-development-tools-marketplace-inventory
description: Scans and reports complete marketplace inventory (bundles, agents, commands, skills, scripts)
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
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
    - execution-context
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

### Engine consumers

The detection engine (`_dep_detection.py` / `_dep_index.py`) has two consumers:

1. **The CLI verbs below** — `deps`, `rdeps`, `tree`, and `validate` answer component-granular questions on demand.
2. **Module derived data** — `pm-plugin-development:plan-marshall-plugin`'s `discover_modules()` runs the engine once at discovery time and materializes each bundle's outbound references into a `component_refs` field on that bundle's module. An Axis-C derivation resolver then reads that pre-materialized field to contribute edges to the `manage-architecture` graph family. The materialization has to happen at discovery time because a derivation resolver is a pure function of its arguments — it may not read from disk, and this engine does.

The second consumer changes granularity: the engine's vocabulary is component-granular (`bundle:skill:script`), while the architecture graph keys on module names. The materialization step therefore **projects** each reference target onto its `bundle`, and stamps whether the underlying component reference resolved. The CLI verbs are unaffected and keep answering at component granularity.

For which resolvers consume the materialized field, see [`ext-point-derivation-resolver.md` § Current implementations](../../../plan-marshall/skills/extension-api/standards/ext-point-derivation-resolver.md#current-implementations) — that table is the single roster, deliberately not restated here.

### Dependency Types

| Type | Pattern | Detection Method |
|------|---------|------------------|
| `script` | `bundle:skill:script` | Regex in markdown/python |
| `skill` | `skills:` frontmatter, `Skill: bundle:skill` | YAML + regex |
| `import` | `from module import ...` | AST parsing |
| `path` | `../../skill/file.md` | Markdown link regex |
| `implements` | `implements: bundle:skill/path` frontmatter | YAML parsing |

### Component Notation

```text
bundle:skill                    # Skill
bundle:skill:script             # Script
bundle:agents:name              # Agent
bundle:commands:name            # Command
```

The four segments are literal placeholders. Worked examples are deliberately
**named rather than spelled** here — writing a real notation in this file makes
this skill depend on whatever it names, and an example chosen for illustration
then shows up as a dependency edge (or, when the example has gone stale, as a
finding) in the very corpus this script measures. For a live example of each form,
read the `Canonical invocations` section of any script-bearing skill.

### What counts as a reference

The `script` detector scans for a bare three-part colon-separated token, which is **not unique to script notation**. Several token families share the shape while referencing no component, so each is recognised and deliberately **not** treated as a reference. Without these exclusions the unresolved set is dominated by findings that name nothing, which trains readers to ignore the whole category.

| Not a reference | Example | Why |
|-----------------|---------|-----|
| Documentation placeholder | `bundle:skill:script`, `groupId:artifactId:scope` | Meta-syntactic segments documenting the notation *form*. Recognised via `NOTATION_PLACEHOLDER_SEGMENTS`, and applied to the `skill` detector too |
| Canonical verification-step ID | `default:verify:quality-gate` | Names a build command. Mirrors `_CANONICAL_VERIFY_PREFIXES` in `plan-marshall:manage-config` |
| Decision-log prefix | `(bundle:skill:step)` | The parenthesised prefix of a decision-log or `[STATUS]` message names the emitting step, not a script |
| Build coordinate or task path | `de.cuioss:cui-java-tools:compile`, `:services:auth-service:build` | A three-part token preceded by `.` or `:` is a fragment of a longer token |
| Sub-document path | `bundle:skill:references/x.md`, `bundle:skill:planning.md` | A three-part token followed by `/`, or by `.` plus a word character, addresses a document. A trailing **sentence** period is not treated this way |

**Every exclusion in the table above is conditional, so none of them can hide a real reference.** Each recognises a *shape*, and a shape is evidence rather than proof — nothing stops a genuine reference from being written parenthetically, or with a `.py` suffix. So a match on an excluded shape is not discarded at detection: the detector records **which** shape matched (`Dependency.exclusion`), and the index drops it only when it also names no component in the graph. An excluded match that *does* name a real component is kept as an ordinary resolved edge. **Shape decides where to look; existence decides.**

The shape's *name* matters as well as its presence, because only one of them can still be a reference in another way. A decision-log prefix names a workflow step, and a step is very often a verb of the skill's entry script, so that shape alone is eligible for the subcommand resolution below. A placeholder names nothing, a canonical command names a build step, and a sub-document path's third segment is a **directory** — none of those can be a verb, and letting them resolve that way manufactured five false edges.

**Older, non-provisional skips remain, and they are fail-open.** Predating this contract, `detect_script_notations` also drops a match unconditionally when its line is a `#`/`//` comment, when the line contains a URL, or when the bundle segment is `http`/`https`/`file`/`mailto`, starts with a digit, or the skill segment is all digits. These are *not* provisional: a real reference on a comment line is discarded outright, and 9 resolvable notations in this marketplace (mostly markdown headings) currently sit there unseen. No genuinely-broken reference hides there today, but a broken notation written on a heading would not be reported. Closing them is deferred, not overlooked.

**Subcommands resolve rather than reporting unresolved.** A skill exposes one entry script named after the skill and dispatches its verbs as subcommands. Documentation names those verbs in the same three-part shape — a `compose` verb in the script segment — so the reference is real and only the segment it lands on is a verb rather than a filename. Such a reference resolves to the entry script that owns the verb.

This is a **deliberate non-detection**, not a blind spot, and it is bounded on two sides. A skill with no same-named entry script cannot retarget, so its notation stays unresolved. And a script segment that is the skill's own name in the **wrong case style** — an underscored `manage_findings` where the registered script is `manage-findings` — is a misspelled script reference rather than a verb, so it also stays unresolved: the executor keys on the third segment literally, and plugin-doctor's `manage-findings-invocation-invalid` rule exists to raise exactly that defect.

What this validator does **not** check is whether a verb is one the entry script actually registers; that is enforced separately by the `manage-invocation-invalid` plugin-doctor rule.

### Precision of `validate`

`validate` findings are precise enough to act on for the **marketplace-bundle namespace**: a finding whose first segment is a bundle in the index names a component that genuinely does not exist. The precision fixture in `test/pm-plugin-development/tools-marketplace-inventory/test_resolve_dependencies.py` holds one instance of each excluded class plus one genuinely-broken reference and asserts **exactly one** finding, so a regression in any single class fails the suite.

Two limits bound that claim, and both are properties of the analysis rather than of its scope:

- **Findings outside the bundle namespace are not yet triaged.** A three-part token whose first segment names no indexed bundle — an npm script name, a time-format literal, a Gradle inter-project coordinate — is still reported. Suppressing them by **bundle membership** would silently drop a reference into a bundle that was deleted, which is the fail-open a gate must not take. A structural discriminator does exist elsewhere in the repository — `plugin-doctor`'s `notation-bundle-skill-drift` rule anchors on the executor prefix (`execute-script.py {notation}`), which separates a deliberate invocation from an incidental colon-joined token. Whether to adopt it here is a scoped decision, not a tightening: anchoring on the executor prefix would also stop counting the many legitimate references written as prose or in a `**Script**:` field, so it narrows this class by narrowing the definition of a reference. Note that plugin-doctor's neighbouring `notation-staleness` rule is **not** the fail-closed precedent it appears to be — it skips any notation whose `skills/{skill}/scripts/` directory is absent, which is the same membership-based fail-open rejected above.
- **Nested script modules are not components.** Component discovery globs `scripts/*.py`, so a module under `scripts/{subdir}/` (for example `script-shared/scripts/extension/extension_base.py`) can be imported but never resolved, and references to it report unresolved.

Until both are addressed, `validation_result` is a **fail-closed report**, not a zero-tolerance gate: read the findings, do not wire `validation_result` to a build step that must stay green.

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
```text
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

## Canonical invocations

The canonical argparse surface for the three entry-point scripts this skill registers: `scan-marketplace-inventory.py`, `resolve-dependencies.py`, and `scan-planning-inventory.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### scan-marketplace-inventory

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  [--scope {auto,marketplace,global,project,plugin-cache}] [--resource-types RESOURCE_TYPES] \
  [--include-descriptions] [--full] [--name-pattern NAME_PATTERN] [--bundles BUNDLES] \
  [--content-pattern CONTENT_PATTERN] [--content-exclude CONTENT_EXCLUDE] [--output OUTPUT] \
  [--direct-result] [--format {toon,json}] [--include-tests] [--include-project-skills]
```

### resolve-dependencies

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:resolve-dependencies \
  {deps,rdeps,tree,validate} \
  [--component COMPONENT] [--scope {auto,marketplace,plugin-cache,project}] [--format {toon,json}] \
  [--direct-result] [--depth DEPTH] [--dep-types DEP_TYPES]
```

The first positional is required and one of `deps` / `rdeps` / `tree` / `validate`.

### scan-planning-inventory

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-planning-inventory \
  [--format {full,summary}] [--include-descriptions]
```
