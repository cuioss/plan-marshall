# Change Tech Debt — Plugin Development Outline Instructions

Domain-specific instructions for `tech_debt` change type in the plugin development domain. Handles refactoring, migration, and cleanup of marketplace components.

## Additional Skills Required

The parent skill (outline-change-type) loads `pm-plugin-development:ext-outline-workflow`. Additionally load:

```
Skill: pm-plugin-development:plugin-architecture
```

## Step 1: Determine Content Filter

Analyze request to derive a content pattern for targeted discovery:

| Request Keywords | Derived Pattern |
|-----------------|-----------------|
| "JSON to TOON", "migrate JSON" | ` ```json ` |
| "TOON output", "add TOON" | ` ```toon ` |
| "update imports" | `^import\|^from` |
| "change output format" | `## Output` |

Identify component types in scope (skills, agents, commands, scripts, tests) and bundle scope from module_mapping.

## Step 2: Inventory Scan

Follow ext-outline-workflow **Inventory Scan** with the component types and bundle scope from Step 1.

## Step 3: Analyze Components

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

## Step 4: Resolve Uncertainties

Follow ext-outline-workflow **Uncertainty Resolution** for any UNCERTAIN assessments.

## Step 5: Plan Refactoring Strategy

Based on compatibility setting:

| Compatibility | Strategy |
|---------------|----------|
| `breaking` | Clean-slate, remove old patterns immediately |
| `deprecation` | Mark old patterns deprecated, add new alongside |
| `smart_and_ask` | Assess impact, ask user for each case |

Group files by bundle (one deliverable per bundle) and component type within bundle.

## Step 6: Build Deliverables

For each batch, create deliverable with extra section:

```markdown
**Refactoring:**
- Pattern: {what pattern is being changed}
- Source: {source_format}
- Target: {target_format}
- Strategy: {breaking|deprecation|smart_and_ask}
```

Add test update and bundle verification deliverables as needed. Validate all deliverables (ext-outline-workflow **Deliverable Validation**). Use verification commands from ext-outline-workflow **Verification Commands**.

## Constraints

### MUST NOT
- Change behavior (refactor = structure only)
- Violate compatibility setting
- Skip analysis step (must assess each component)

### MUST DO
- Use content filter for targeted discovery
- Respect compatibility setting
- Use ext-outline-workflow shared constraints
