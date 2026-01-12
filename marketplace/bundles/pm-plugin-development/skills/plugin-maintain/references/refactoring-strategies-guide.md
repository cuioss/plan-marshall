# Refactoring Strategies Guide

Guide for restructuring marketplace components for better organization.

## Refactoring Principles

Refactoring should:
- Improve organization without changing behavior
- Reduce duplication and bloat
- Follow marketplace architectural patterns
- Maintain all functionality

## Refactoring Strategies

### consolidate

**When to Use**: Related components should be merged.

**Indicators**:
- Multiple commands doing similar things
- Agents with overlapping functionality
- Repeated code across components

**Process**:
1. Identify components to consolidate
2. Analyze shared functionality
3. Create unified component
4. Migrate features to new component
5. Update cross-references
6. Delete old components

**Example**:
```
Before: plugin-update-agent, plugin-update-command
After: plugin-maintain skill with update-component workflow
```

### split

**When to Use**: Component is too large or doing too much.

**Indicators**:
- Component exceeds 800 lines
- Multiple unrelated workflows in one file
- Difficult to understand or maintain

**Process**:
1. Identify logical boundaries
2. Extract distinct functionality
3. Create focused components
4. Update references
5. Test all parts

**Example**:
```
Before: monolithic-diagnose-command (1200 lines)
After: diagnose-agents, diagnose-commands, diagnose-skills
```

### extract

**When to Use**: Shared content belongs in reusable skill.

**Indicators**:
- Same content in 3+ components
- Content could be loaded on-demand
- Content exceeds 100 lines

**Process**:
1. Identify shared content
2. Create skill with extracted content
3. Replace duplicates with skill references
4. Update all affected components

**Example**:
```
Before: Logging patterns duplicated in 4 commands
After: cui-logging skill referenced by all commands
```

### reorganize

**When to Use**: Directory structure needs improvement.

**Indicators**:
- Files in wrong directories
- Inconsistent naming
- Missing standard directories

**Process**:
1. Design target structure
2. Move files to correct locations
3. Update all references
4. Update plugin.json

## Using analyze-component.py

Analyze components in refactoring scope:

```bash
scripts/analyze-component.py {component_path}
```

Collect metrics for:
- Quality scores across components
- Line counts (identify bloat)
- Issues (identify problems)
- Sections (identify structure)

## Scope Levels

### component

Refactor single component:
- Split large component
- Reorganize sections
- Extract to skill

### bundle

Refactor entire bundle:
- Consolidate related components
- Reorganize directory structure
- Extract common patterns

### marketplace

Refactor across bundles:
- Identify cross-bundle duplication
- Create shared skills
- Standardize patterns

## Dry Run Mode

**Always use dry_run=true first**

Preview shows:
- Files to be moved/renamed
- Content to be extracted
- References to be updated
- plugin.json changes

Only proceed after reviewing plan.

## Cross-Reference Updates

### Finding References

Search for component references:

```bash
grep -r "component-name" marketplace/bundles/
```

### Updating References

For each reference found:
1. Update path/name
2. Verify reference still works
3. Test affected component

### plugin.json Updates

When renaming/moving:
1. Update entries in plugin.json
2. Remove old entries
3. Add new entries
4. **CRITICAL**: Update `marketplace/.claude-plugin/marketplace.json` (central plugin registry)

## Verification

After refactoring:

1. **Run Tests**: Execute tests for renamed components
   - Update test file references (bundle/skill names)
   - Run tests to verify they still pass
   - Fix any broken imports or paths

2. **Run Diagnosis**: Check for issues
   ```
   /plugin-diagnose-{type}
   ```

3. **Test Functionality**: Verify components work
4. **Check References**: All cross-references valid
5. **Validate Structure**: Directory structure correct

## Consolidation Patterns

### Commands to Skill

**Pattern**: Multiple related commands → One skill with workflows

**Before**:
```
commands/
  create-agent.md
  create-command.md
  create-skill.md
```

**After**:
```
skills/plugin-create/
  SKILL.md (with 3 workflows)
  scripts/
  references/
```

### Agents to Skill

**Pattern**: Related agents → Skill with shared patterns

**Before**:
```
agents/
  diagnose-agent-a.md
  diagnose-agent-b.md
```

**After**:
```
skills/plugin-diagnose/
  SKILL.md
  agents/ (if needed)
```

## Directory Structure Standards

### Bundle Structure

```
bundle-name/
├── plugin.json
├── README.md
├── commands/
│   └── {command-name}.md
├── agents/
│   └── {agent-name}.md
└── skills/
    └── {skill-name}/
        ├── SKILL.md
        ├── scripts/
        ├── references/
        └── assets/
```

### Naming Conventions

- Commands: `{verb}-{noun}.md` (e.g., `create-agent.md`)
- Agents: `{noun}-{role}.md` (e.g., `maven-builder.md`)
- Skills: `{domain}-{purpose}/` (e.g., `plugin-create/`)

## Risk Mitigation

### Before Refactoring

1. Commit current state
2. Review all references
3. Create refactoring plan
4. Use dry_run to preview

### During Refactoring

1. Make atomic changes
2. Verify after each step
3. Keep old files until verified
4. Update references immediately

### After Refactoring

1. Run full diagnosis
2. Test affected components
3. Update documentation
4. Commit with detailed message

## Reporting

### Dry Run Report

```
Refactoring Plan (DRY RUN)
==========================
Strategy: consolidate
Scope: bundle

Changes:
  Move: commands/update-agent.md → skills/plugin-maintain/
  Move: commands/update-command.md → skills/plugin-maintain/
  Create: skills/plugin-maintain/SKILL.md
  Update: plugin.json (remove 2, add 1)

References to update: 15
Files affected: 8

Proceed? [Y/n]
```

### Completion Report

```
Refactoring Complete
====================
Strategy: consolidate
Files moved: 4
Files created: 3
Files deleted: 4
References updated: 15
Verification: PASSED
```

## See Also

- `component-update-guide.md` - Updating components
- `orchestration-compliance.md` - Compliance patterns
