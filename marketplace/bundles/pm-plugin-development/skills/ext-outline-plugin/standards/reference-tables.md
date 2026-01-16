# Reference Tables

Reference material for the plugin solution outline skill including inventory scripts, skill mapping, component classification, and error handling.

## Inventory Script Reference

**Script**: `pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory`

**Options**:

| Option | Description |
|--------|-------------|
| `--trace-plan-id <id>` | Enable plan-scoped logging (executor strips before passing) |
| `--scope marketplace` | Scan marketplace bundles (default) |
| `--resource-types agents,commands,skills,scripts` | Filter resource types |
| `--include-descriptions` | Extract descriptions from frontmatter |
| `--name-pattern <pattern>` | Filter by name (fnmatch glob, pipe-separated) |
| `--bundles <names>` | Filter to specific bundles (comma-separated) |

**Example Calls**:

```bash
# All components with descriptions (with plan-scoped logging)
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} \
  --include-descriptions

# Only skills in planning bundle
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} \
  --bundles planning \
  --resource-types skills

# Components matching pattern
python3 .plan/execute-script.py \
  pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --trace-plan-id {plan_id} \
  --name-pattern "*-goals*|*-plan*"
```

---

## Skill and Workflow Mapping

When creating deliverables, use this mapping for `suggested_skill` and `suggested_workflow`:

| Change Type | Component Type | Skill | Workflow |
|-------------|----------------|-------|----------|
| create | skill | pm-plugin-development:plugin-create | create-skill |
| create | command | pm-plugin-development:plugin-create | create-command |
| create | agent | pm-plugin-development:plugin-create | create-agent |
| create | bundle | pm-plugin-development:plugin-create | create-bundle |
| modify | any | pm-plugin-development:plugin-maintain | update-component |
| refactor | any | pm-plugin-development:plugin-maintain | refactor-structure |
| migrate | format | pm-plugin-development:plugin-maintain | update-component |
| delete | any | pm-plugin-development:plugin-maintain | remove-component |

### Domain and Context Skills

- **domain**: Always `plan-marshall-plugin-dev` for marketplace components
- **context_skills**: Usually empty (`[]`). Add `pm-plugin-development:plugin-script-architecture` when deliverable involves Python scripts

---

## Component Types

| Type | Indicators | Example |
|------|------------|---------|
| `skill` | SKILL.md, standards, references | java-solution-outline |
| `command` | Slash command, user-facing | plugin-doctor.md |
| `agent` | Autonomous execution, tools | java-implement-agent.md |
| `script` | Python/Bash automation | manage-goal.py |

---

## Scope Detection

| Indicator | Scope |
|-----------|-------|
| "implement", "add", "create", "new" | create |
| "fix", "update", "modify", "change" | modify |
| "refactor", "reorganize", "migrate" | refactor |

---

## Complexity Assessment

| Factor | Low | Medium | High |
|--------|-----|--------|------|
| Components affected | 1-2 | 3-5 | 6+ |
| Cross-bundle | No | 1 bundle | 2+ bundles |
| Breaking changes | None | Internal | Public API |
| Dependencies | 0-1 | 2-3 | 4+ |
| Scripts needed | 0 | 1-2 | 3+ |

---

## Error Handling

### Component Not Found

| Scope | Action |
|-------|--------|
| `create` | Continue (expected - component doesn't exist yet) |
| `modify` | Warn and ask for clarification |
| `refactor` | Error and request correct path |

### Bundle Not Found

If bundle doesn't exist:
- Check if task is to create the bundle
- Otherwise error with suggestion

### Ambiguous Component

If multiple components match:
- List all matches with paths
- Ask user to select correct one
