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

Use targeted Glob search to find the specific component:

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

Always exactly 2 deliverables:

**Deliverable 1: Fix** — include extra section:

```markdown
**Root Cause:**
{Brief description of what's causing the bug}
```

**Deliverable 2: Regression Test** — test that would have caught this bug.

Validate all deliverables (ext-outline-workflow **Deliverable Validation**). Use verification commands from ext-outline-workflow **Verification Commands**.

### Constraints

**MUST NOT**: Use full inventory (targeted search only). Make unnecessary changes (minimal fix principle). Skip regression test deliverable.

**MUST DO**: Document root cause. Keep fix minimal and focused. Always produce exactly 2 deliverables (fix + regression test). Use ext-outline-workflow shared constraints.

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

### Constraints

**MUST NOT**: Change behavior (refactor = structure only). Violate compatibility setting. Skip analysis step (must assess each component).

**MUST DO**: Use content filter for targeted discovery. Respect compatibility setting. Use ext-outline-workflow shared constraints.
