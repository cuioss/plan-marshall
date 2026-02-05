# Doctor Commands Workflow

Analyze and fix command quality issues.

## Parameters

- `scope` (optional, default: "marketplace"): "marketplace" | "global" | "project"
- `command-name` (optional): Analyze specific command
- `--no-fix` (optional): Diagnosis only, no fixes

## Step 1: Load Prerequisites and Standards

```
Skill: plan-marshall:ref-development-standards
Skill: pm-plugin-development:plugin-architecture
Read references/commands-guide.md
Read references/fix-catalog.md
```

## Step 2: Discover Commands

Same pattern as doctor-agents.

## Step 3: Analyze Commands

Use the batch analyze command filtered to commands:

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace analyze \
  --bundles {bundle} --type commands
```

This returns JSON with per-command analysis including markdown structure and reference validation.

**Check against commands-guide.md**:

**Rule 0 - Thin Wrapper Check (CRITICAL)**:
- Line count thresholds:
  - **IDEAL**: < 100 lines (proper thin wrapper)
  - **ACCEPTABLE**: 100-150 lines (minor workflow logic OK)
  - **BLOATED**: 150-200 lines (too much logic, needs refactoring)
  - **CRITICAL**: > 200 lines (severe bloat, MUST refactor immediately)
- Commands MUST delegate to skills (check for `Skill:` invocation)
- Commands should NOT contain:
  - Step-by-step workflow logic (### Step 1, ### Step 2, etc. with implementation)
  - For loops or iteration logic
  - File processing code
  - Analysis algorithms
- Flag as **CRITICAL** if command contains workflow implementation instead of skill delegation

**Other Checks**:
- Verify proper Skill invocation format (`Skill: bundle:skill-name`)
- Check parameter documentation (PARAMETERS section exists)
- **Foundation skill loading via invoked skills** (see below)

### Verify Foundation Skills in Invoked Skills

**Commands are thin orchestrators** - they delegate to skills via `Skill:` invocation.

**Check criteria**:
1. Extract skill invocations from command (e.g., `Skill: pm-plugin-development:plugin-create`)
2. For each invoked skill, verify it loads foundation skills (plugin-architecture, diagnostic-patterns)
3. Report if invoked skill is missing foundation skills (fix the skill, not the command)

**If invoked skill missing foundation skills**:
- Report: "Command invokes skill '{skill}' which is missing foundation skill loading"
- Recommendation: "Run `/plugin-doctor skill-name={skill}` to fix the skill"

This is NOT a command fix - it's a skill fix. Commands don't load foundation skills directly; their skills do.

## Step 4: Categorize and Fix

**Safe fixes** (auto-apply unless --no-fix):
- Incorrect section header case (`## Workflow` → `## WORKFLOW`, `## Parameter Validation` → `## PARAMETERS`)
- Missing CONTINUOUS IMPROVEMENT RULE section
- Legacy CONTINUOUS IMPROVEMENT RULE (uses /plugin-update-* or /plugin-maintain instead of manage-lessons)

**Risky fixes** (require confirmation):
- **Rule 0 violations** (command contains workflow logic instead of skill delegation)
  - Severity: CRITICAL if > 200 lines or contains implementation logic
  - Fix: Refactor command to thin wrapper, move logic to skill
  - This is architectural refactoring - requires manual intervention

**Auto-fix pattern for section headers**:
Search for `## Workflow`, `## Parameter Validation`, `## Parameters` and replace with uppercase versions.

**Auto-fix pattern for missing CONTINUOUS IMPROVEMENT RULE**:
```markdown
## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: \`Skill: plan-marshall:manage-lessons\`
2. **Record lesson** with:
   - Component: \`{type: "command", name: "{command-name}", bundle: "{bundle}"}\`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding
```

Insert before `## Related` section (or at end if no Related section).

**Auto-fix pattern for legacy CONTINUOUS IMPROVEMENT RULE**:
If CONTINUOUS IMPROVEMENT RULE section contains `/plugin-update-command`, `/plugin-maintain`, or `/plugin-apply-lessons-learned`, replace entire section with the new pattern above.

**Rule 0 violation reporting** (no auto-fix - requires manual refactoring):
```
⚠️ CRITICAL: Command '{command}' violates Rule 0 (thin wrapper requirement)
   - Line count: {lines} (threshold: 200)
   - Contains workflow implementation instead of skill delegation
   - Required action: Refactor to thin wrapper pattern

   Refactoring steps:
   1. Create/identify skill to contain workflow logic
   2. Move all ### Step sections to skill's workflow
   3. Replace command content with skill invocation
   4. Target: < 100 lines (parameters + skill invocation + examples)

   Example thin wrapper:
   ## Workflow
   Activate \`bundle:skill-name\` and execute the **Workflow Name** workflow.
```

## Step 5: Verify and Report

Same pattern as doctor-agents with command-specific thresholds.
