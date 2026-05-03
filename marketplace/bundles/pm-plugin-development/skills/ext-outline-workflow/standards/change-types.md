# Change Types — Plugin Development Outline Instructions

Domain-specific instructions for each change type in the plugin development domain. The parent skill (phase-3-outline) loads `pm-plugin-development:ext-outline-workflow`.

All change types require loading the plugin architecture skill:

```
Skill: pm-plugin-development:plugin-architecture
```

---

## Bug Fix

Handles defect location and minimal fix with regression test.

### Step 1: Identify Bug Location

Analyze request to identify:

1. **Affected component** — which skill/agent/command has the bug
2. **Bug symptoms** — incorrect behavior
3. **Expected behavior** — what should happen

If request provides stack trace or error message, extract file paths and error location.

### Step 2: Targeted Search (No Full Inventory)

Use the structured architecture inventory first to locate the component:

```bash
architecture find --pattern "*{component_name}*"
```

Fall back to a targeted `Glob` only when the architecture verb returns elision or when the component is finer-grained than module level (sub-module path patterns):

```bash
Glob pattern: marketplace/bundles/**/{component_name}*
```

Read the affected component file directly.

### Step 3: Root Cause Analysis

Analyze the component:

1. **What's wrong** — the actual defect
2. **Why it happens** — triggering conditions
3. **Minimal fix** — smallest change to fix it

### Step 4: Build Deliverables

Always exactly 2 deliverables. The "2 deliverables" rule counts deliverables, not files or change-sites.

**Deliverable 1: Fix** — MAY bundle multiple coordinated source edits plus their co-located unit tests when those edits share a single test surface (e.g., a multi-site bug fix where every site is verified by the same test surface). D1 may therefore have multiple `Affected files` entries spanning production code AND co-located unit tests. Include extra section:

```markdown
**Root Cause:**
{Brief description of what's causing the bug}
```

**Deliverable 2: Regression Test** — the cross-cutting / end-to-end / integration regression test that exercises the fix from a user-visible angle. It earns its own deliverable because its verification contract differs from D1's local unit tests. Independent regression coverage that has a different verification scope from D1's unit tests always becomes D2 — D1 cannot absorb it.

Validate all deliverables (ext-outline-workflow **Deliverable Validation**). Use verification commands from ext-outline-workflow **Verification Commands**.

### Constraints

**MUST NOT**: Use full inventory (targeted search only). Make unnecessary changes (minimal fix principle — "minimal" means smallest correct fix, not "single file"). Skip the cross-cutting regression-test deliverable.

**MUST DO**: Document root cause. Keep fix minimal and focused. Always produce exactly 2 deliverables (fix + regression test) — the rule counts deliverables, not files; D1 may bundle multiple coordinated source edits plus their co-located unit tests when they share a single test surface. Use ext-outline-workflow shared constraints.

---

## Enhancement

Handles enhancing existing marketplace components.

### Step 1: Determine Component Scope

Analyze request to identify which component types are affected:

| Component Type | Include if request mentions... |
|----------------|-------------------------------|
| skills | skill, standard, workflow, template |
| agents | agent, task executor |
| commands | command, slash command |
| scripts | script, Python, output, format |
| tests | test, testing, coverage |

### Step 2: Inventory Scan and Analysis

Follow ext-outline-workflow **Inventory Scan** with the component types and bundle scope from Step 1.

Clear stale assessments (ext-outline-workflow **Assessment Pattern**).

For each component file from inventory:

1. **Scope boundary check**: Does request define explicit exclusions? If matched content falls into excluded category -> CERTAIN_EXCLUDE.
2. **Relevance assessment**: Does this component contain functionality being enhanced? Would it need changes? Is it a test covering affected functionality?
3. Log assessment per file (ext-outline-workflow **Assessment Pattern**).

Verify via **Assessment Gate**.

### Step 3: Resolve Uncertainties

Follow ext-outline-workflow **Uncertainty Resolution** for any UNCERTAIN assessments.

### Step 4: Build Deliverables

For each CERTAIN_INCLUDE component, create deliverable. Add test update and bundle verification deliverables as needed. Validate all deliverables (ext-outline-workflow **Deliverable Validation**). Use verification commands from ext-outline-workflow **Verification Commands**.

**Audit checklists**: For deliverables that audit a structural rule, see [SKILL.md → Audit Checklist for Structural-Rule Audits](../SKILL.md#audit-checklist-for-structural-rule-audits).

### Constraints

**MUST NOT**: Create new files (enhancement = modify existing). Skip analysis step (must assess each component).

**MUST DO**: Resolve uncertainties with user. Use ext-outline-workflow shared constraints.

---

## Feature

Handles new marketplace component creation.

### Step 1: Determine Component Type

Analyze request to identify what component types to create:

| Request Pattern | Component Type |
|-----------------|----------------|
| "skill", "standard", "workflow" | skills |
| "agent", "task executor" | agents |
| "command", "slash command" | commands |

### Step 2: Identify Target Bundle

1. If request specifies bundle -> use specified bundle
2. If module_mapping provides bundle -> use mapped bundle
3. Otherwise -> ask user:

```
AskUserQuestion:
  question: "Which bundle should the new {component_type} be created in?"
  options: [{bundle1}, {bundle2}, ...]
```

### Step 3: Discover Patterns

Follow ext-outline-workflow **Inventory Scan** scoped to the target bundle and component type.

Read a few existing components of the same type to identify naming conventions, structure patterns, and test patterns to follow.

### Step 4: Build Deliverables

For each new component, create deliverable with extra section:

```markdown
**Component Details:**
- Type: {skill|agent|command}
- Name: {component_name}
- Bundle: {target_bundle}
```

Include plugin.json registration in affected files. Add test and bundle verification deliverables as needed. Validate all deliverables (ext-outline-workflow **Deliverable Validation**). Use verification commands from ext-outline-workflow **Verification Commands**.

### Constraints

**MUST NOT**: Modify existing components (feature = new only). Skip plugin.json registration deliverable.

**MUST DO**: Follow plugin-architecture standards. Include test deliverables. Use ext-outline-workflow shared constraints.

---

## Tech Debt

Handles refactoring, migration, and cleanup of marketplace components.

### Step 1: Determine Content Filter

Analyze request to derive a content pattern for targeted discovery:

| Request Keywords | Derived Pattern |
|-----------------|-----------------|
| "JSON to TOON", "migrate JSON" | ` ```json ` |
| "TOON output", "add TOON" | ` ```toon ` |
| "update imports" | `^import\|^from` |
| "change output format" | `## Output` |

Identify component types in scope (skills, agents, commands, scripts, tests) and bundle scope from module_mapping.

### Step 1b: Flag-Rename Detection and Scope Expansion

When the clarified request describes a CLI-flag or script-parameter rename, the default module-scoped inventory from Step 2 is insufficient — flag callers and argparse `dest` references typically live outside `module_mapping`. Activate the heuristic below to expand discovery.

**Trigger detection** — activate when the clarified request contains any of these keywords:

- `rename`
- `flag`
- `parameter`
- `--{old}` (the literal old flag, e.g., `--number`)
- `--{new}` (the literal new flag, e.g., `--task`)

**Expanded discovery** — when triggered, override the module-scoped inventory of Step 2:

1. Full grep for the old flag literal `--{old}` using word-boundary anchoring (e.g., `grep -w -- --{old}` or a regex with `\b` anchors) across **all** bundles in `marketplace/` and **all** `test/**` directories — not only the modules identified by `module_mapping`. Word boundaries prevent false-positive substring matches such as `--task` matching `--task-id`.
2. Additional Python-specific grep for `Namespace(..., {old_dest}=` and `args.{old_dest}` using word-boundary anchoring on `{old_dest}` (e.g., `grep -E '\bargs\.{old_dest}\b'`) to catch argparse `dest` references in test helpers and handlers without matching longer names that share the prefix. Derive `{old_dest}` from `{old}` by replacing `-` with `_` (argparse's default `dest` normalization).
3. Every match becomes a CERTAIN_INCLUDE candidate Affected file unless its path falls under an explicitly excluded context:
   - `.plan/archived-plans/**` (frozen historical fixtures)
   - vendored snapshots (any path whose enclosing directory is marked as a vendored/third-party snapshot)

Log a decision entry summarizing the expanded scope (e.g., `(phase-3-outline) Flag-rename detected: --number → --task; scope expanded to {N} files across {M} bundles`).

### Step 2: Inventory Scan

Follow ext-outline-workflow **Inventory Scan** with the component types and bundle scope from Step 1.

### Step 3: Analyze Components

Clear stale assessments (ext-outline-workflow **Assessment Pattern**).

For each component file from inventory:

1. **Content pattern gate**: Search file for content pattern. No match -> CERTAIN_EXCLUDE. Skip to next.
2. **Scope relevance gate**: Does matched content fall within request scope? Exclude: persisted file schemas, API reference format examples, external tool output. If out of scope -> CERTAIN_EXCLUDE.
3. **Extract format evidence** (only if scope-relevant): `source_format_evidence` and `target_format_evidence`.
4. **Classify** using decision matrix:
   - No relevant content -> CERTAIN_EXCLUDE
   - Has target format only -> CERTAIN_EXCLUDE (already migrated)
   - Has source format only -> CERTAIN_INCLUDE (needs migration)
   - Has both formats -> UNCERTAIN (partially migrated)
5. Log assessment per file (ext-outline-workflow **Assessment Pattern**).

Verify via **Assessment Gate**.

### Step 4: Resolve Uncertainties

Follow ext-outline-workflow **Uncertainty Resolution** for any UNCERTAIN assessments.

### Step 5: Plan Refactoring Strategy

Based on compatibility setting:

| Compatibility | Strategy |
|---------------|----------|
| `breaking` | Clean-slate, remove old patterns immediately |
| `deprecation` | Mark old patterns deprecated, add new alongside |
| `smart_and_ask` | Assess impact, ask user for each case |

Group files by bundle (one deliverable per bundle) and component type within bundle.

### Step 6: Build Deliverables

For each batch, create deliverable with extra section:

```markdown
**Refactoring:**
- Pattern: {what pattern is being changed}
- Source: {source_format}
- Target: {target_format}
- Strategy: {breaking|deprecation|smart_and_ask}
```

Add test update and bundle verification deliverables as needed. Validate all deliverables (ext-outline-workflow **Deliverable Validation**). Use verification commands from ext-outline-workflow **Verification Commands**.

**Audit checklists**: When the deliverable audits a structural rule (e.g., chain-shape compliance sweep), the deliverable's 'Change per file' or 'Verification' block MUST enumerate all three shell-marshalling families. See [SKILL.md → Audit Checklist for Structural-Rule Audits](../SKILL.md#audit-checklist-for-structural-rule-audits).

### Constraints

**MUST NOT**: Change behavior (refactor = structure only). Violate compatibility setting. Skip analysis step (must assess each component).

**MUST DO**: Use content filter for targeted discovery. Respect compatibility setting. Use ext-outline-workflow shared constraints. For flag-rename / parameter-rename requests, expand discovery to all bundles and `test/**` per Step 1b — do NOT rely on `module_mapping` scope alone.
