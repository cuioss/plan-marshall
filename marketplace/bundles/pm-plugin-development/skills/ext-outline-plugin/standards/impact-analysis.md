# Impact Analysis Standard

Standard for determining which components are affected by changes through dependency resolution.

## When to Apply

Run impact analysis when ALL of these conditions are met:

- `change_type` is `modify`, `migrate`, or `refactor`
- Primary affected count < 20 files
- Request involves changes that could break dependents (renaming, API changes, contract changes)

## Skip When

- `change_type` is `create` (nothing depends on new components)
- Primary affected count >= 20 (scope already large enough)
- Changes are purely internal (no external contracts affected)

## Notation Conversion

| File Path Pattern | Component Notation |
|-------------------|-------------------|
| `marketplace/bundles/{b}/skills/{s}/SKILL.md` | `{b}:{s}` |
| `marketplace/bundles/{b}/skills/{s}/scripts/{sc}.py` | `{b}:{s}:{sc}` |
| `marketplace/bundles/{b}/commands/{c}.md` | `{b}:commands:{c}` |
| `marketplace/bundles/{b}/agents/{a}.md` | `{b}:agents:{a}` |

## Scope Expansion Rules

### Include a Dependent When

- Has `skill` type reference to affected component (loads the skill)
- Has `script` type reference to affected component (calls the script)

### Exclude When

- Only has `import` type references (Python-internal, not via execute-script.py)
- Only has `path` type references (documentation links)
- Component is already in primary scope

## Dependency Types

| Type | Description | Included |
|------|-------------|----------|
| `skill` | Skill reference in frontmatter or Skill tool call | Yes |
| `script` | Script execution via execute-script.py | Yes |
| `import` | Python module import | No |
| `path` | Relative path in documentation | No |
| `implements` | Protocol implementation | No |

## Error Handling

### resolve-dependencies Fails

**Action**: HALT workflow immediately.

```
status: error
error_type: dependency_resolution_failed
message: "Impact analysis failed. Retry later."
```

**Do NOT**:
- Continue without dependency data
- Fall back to skip impact analysis
- Proceed with partial scope

### Circular Dependencies Detected

**Action**: HALT workflow immediately.

```
status: error
error_type: circular_dependency
message: "Circular dependency detected: {cycle}. Manual resolution required."
```

## Output Contract

The `impact-analysis` subcommand produces:

### dependency_analysis.toon

```toon
status: success
primary_count: 5
dependents_found: 3
dependents_added: 2
added_files[2]:
  - marketplace/bundles/pm-workflow/skills/phase-3-outline/SKILL.md
  - marketplace/bundles/pm-workflow/commands/plan-manage.md
```

### Updated inventory_filtered.toon

The original inventory is expanded in-place with dependent components added to the appropriate `inventory.{type}` lists.

## Integration with Workflow

After impact analysis completes:

1. **Modify Flow Step 1** reads the expanded inventory (already updated)
2. **Step 6** builds deliverables from the full scope (primary + dependents)
3. **Step 6.5** (if enabled) can use dependency_analysis.toon to order deliverables
