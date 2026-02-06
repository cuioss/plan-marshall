# Component Verification Commands

Correct plugin-doctor invocation syntax per marketplace component type.

## Plugin-Doctor Scope-Based Routing

Plugin-doctor uses scope-based routing, **not** `--component {path}` flags. Each component type has its own scope and parameter name.

### Invocation Table

| Component Type | Scope | Parameter | Full Command |
|----------------|-------|-----------|--------------|
| Skills | `scope=skills` | `skill-name={name}` | `/pm-plugin-development:plugin-doctor scope=skills skill-name={name}` |
| Agents | `scope=agents` | `agent-name={name}` | `/pm-plugin-development:plugin-doctor scope=agents agent-name={name}` |
| Commands | `scope=commands` | `command-name={name}` | `/pm-plugin-development:plugin-doctor scope=commands command-name={name}` |
| Scripts | `scope=scripts` | `script-name={name}` | `/pm-plugin-development:plugin-doctor scope=scripts script-name={name}` |

### Parameter Values

- `{name}` is the component name without path or extension:
  - For skills: the skill directory name (e.g., `ext-verify-plugin`)
  - For agents: the agent filename without `.md` (e.g., `change-feature-outline-agent`)
  - For commands: the command filename without `.md` (e.g., `tools-analyze-user-prompted`)
  - For scripts: the script filename without `.py` (e.g., `scan-marketplace-inventory`)

### Common Mistakes to Avoid

- Do NOT use `--component {path}` - this flag does not exist
- Do NOT use file paths as scope parameters
- Do NOT omit the scope parameter

### Deliverable Verification Template

For component deliverables, use this pattern:

```markdown
**Verification:**
- Command: `/pm-plugin-development:plugin-doctor scope={component_type}s {component_type}-name={name}`
- Criteria: No errors, structure compliant
```
