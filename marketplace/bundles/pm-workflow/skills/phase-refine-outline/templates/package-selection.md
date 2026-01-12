# Package Selection Template

Template for documenting package placement reasoning in solution outlines.

## Usage

Include this analysis in the solution outline when package selection requires justification.

## Template

```markdown
**Package Selection**:

From `key_packages`:
- `{package}`: "{description from architecture}"

**Selected Package**: `{package}`

**Reasoning**: {Why this package matches based on existing components and patterns}
```

## Field Descriptions

| Field | Source | Description |
|-------|--------|-------------|
| `package` | `architecture module --name X --full` | Package name from key_packages |
| `description` | `architecture module --name X --full` | Package description from architecture |
| `Reasoning` | LLM analysis | Justification for selection |

## Decision Matrix

| Scenario | Action |
|----------|--------|
| Task matches key_package description | Place in that key_package |
| Task needs utility location | Check for existing util package |
| New cross-cutting concern | Create new package (document reasoning) |
| Unclear placement | Check has_package_info packages first |

## Package Guidance

See `standards/module-selection.md` for additional guidance on:
- Key packages vs raw packages
- Package creation criteria
- Naming conventions
