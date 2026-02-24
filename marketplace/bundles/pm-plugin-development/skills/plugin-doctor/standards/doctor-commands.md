# Doctor Commands Workflow

Follows the common workflow pattern (see SKILL.md). Reference guide: `commands-guide.md`.

## Parameters

- `scope` (optional, default: "marketplace"): "marketplace" | "global" | "project"
- `command-name` (optional): Analyze specific command
- `--no-fix` (optional): Diagnosis only, no fixes

## Command-Specific Checks

### command-thin-wrapper Check

Commands delegate all logic to skills; they are thin orchestrators.

- **IDEAL**: < 100 lines (proper thin wrapper)
- **ACCEPTABLE**: 100-150 lines (minor workflow logic OK)
- **BLOATED**: 150-200 lines (too much logic, needs refactoring)
- **CRITICAL**: > 200 lines (severe bloat, requires immediate refactoring)

Commands should NOT contain:
- Step-by-step workflow logic (### Step 1, ### Step 2, etc. with implementation)
- For loops or iteration logic
- File processing code
- Analysis algorithms

### Foundation Skill Loading via Invoked Skills

Commands are thin orchestrators — they delegate to skills via `Skill:` invocation.

1. Extract skill invocations from command (e.g., `Skill: pm-plugin-development:plugin-create`)
2. For each invoked skill, verify it loads foundation skills (plugin-architecture, ref-development-standards)
3. Report if invoked skill is missing foundation skills (fix the skill, not the command)

This is NOT a command fix — it's a skill fix. Commands don't load foundation skills directly; their skills do.

## Command-Specific Fix Categories

**Safe fixes** (auto-apply):
- Incorrect section header case (`## Workflow` → `## WORKFLOW`, `## Parameter Validation` → `## PARAMETERS`)
- Missing CONTINUOUS IMPROVEMENT RULE section
- Legacy CONTINUOUS IMPROVEMENT RULE (uses /plugin-update-* or /plugin-maintain instead of manage-lessons)

**Risky fixes** (require confirmation):
- command-thin-wrapper violations (command contains workflow logic instead of skill delegation)
  - Severity: critical if > 200 lines or contains implementation logic
  - Fix: Refactor command to thin wrapper, move logic to skill

### Auto-fix: Section Headers

Search for `## Workflow`, `## Parameter Validation`, `## Parameters` and replace with uppercase versions.

### Auto-fix: Missing CONTINUOUS IMPROVEMENT RULE

```markdown
## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with:
   - Component: `{type: "command", name: "{command-name}", bundle: "{bundle}"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding
```

Insert before `## Related` section (or at end if no Related section).

### Auto-fix: Legacy CONTINUOUS IMPROVEMENT RULE

If CONTINUOUS IMPROVEMENT RULE section contains `/plugin-update-command`, `/plugin-maintain`, or `/plugin-apply-lessons-learned`, replace entire section with the pattern above.

### command-thin-wrapper Violation Reporting

No auto-fix — requires manual refactoring:

```
Refactoring steps:
1. Create/identify skill to contain workflow logic
2. Move all ### Step sections to skill's workflow
3. Replace command content with skill invocation
4. Target: < 100 lines (parameters + skill invocation + examples)
```
