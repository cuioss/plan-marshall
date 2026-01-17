---
name: plugin-doctor
description: Diagnose and fix quality issues in marketplace components
allowed-tools: Skill, Read, Edit, Glob, Grep, Bash, AskUserQuestion
---

# Doctor Marketplace Components

Analyze marketplace components for quality issues and apply fixes in a single workflow.

## Usage

```
# Doctor all components of a type
/plugin-doctor agents
/plugin-doctor commands
/plugin-doctor skills
/plugin-doctor metadata
/plugin-doctor scripts

# Doctor single component
/plugin-doctor agent=my-agent
/plugin-doctor command=my-command
/plugin-doctor skill=my-skill

# Doctor skill content (cross-file analysis)
/plugin-doctor skill-content path/to/skill

# Doctor entire marketplace
/plugin-doctor marketplace

# Diagnosis only (no fixes)
/plugin-doctor agents --no-fix

# Show usage
/plugin-doctor
```

## WORKFLOW

When you invoke this command, I will:

1. **Parse scope** from parameters:
   - Detect component type (agents/commands/skills/metadata/scripts/marketplace)
   - Detect single vs all components
   - Check for --no-fix flag

2. **Load plugin-doctor skill and EXECUTE its workflow**:
   ```
   Skill: pm-plugin-development:plugin-doctor
   ```

   **CRITICAL HANDOFF RULES**:
   - DO NOT summarize or explain the skill content to the user
   - DO NOT describe what the skill says to do
   - IMMEDIATELY execute the scripts and tools specified in the skill
   - Your next action after loading the skill MUST be a tool call (Bash, Read, Glob), not text output
   - Follow the skill's "Workflow Decision Tree" to select the correct workflow
   - Execute MANDATORY steps without commentary

3. **Display results** only after workflow completion - show fixes applied and verification status

## PARAMETERS

**Required**: One of:
- `scope`: agents|commands|skills|metadata|scripts|skill-content|marketplace
- `component=name`: agent=X, command=X, or skill=X
- `skill-content <path>`: Analyze skill content files (cross-file analysis)

**Optional**:
- `--no-fix`: Diagnosis only, skip fix phase
- `--skip-quality`: Skip Phase 3 quality analysis (skill-content only)

**Error Handling**:
- No scope → Display usage with examples
- Invalid scope → Display valid scopes
- Component not found → Error with available components

## Fix Categorization

**Safe Fixes** (applied automatically, NO prompts):
- Missing frontmatter fields
- Invalid YAML syntax
- Unused tools in frontmatter
- Trailing whitespace

**Risky Fixes** (require confirmation via prompt):
- Rule 6 violations (Task tool in agents)
- Rule 7 violations (Maven usage)
- Pattern 22 violations (self-invocation)
- Structural changes
- Content removal

## Non-Prompting Behavior

This command delegates to `pm-plugin-development:plugin-doctor` skill which is designed to run without user prompts for safe operations:

- **Safe fixes**: Applied automatically WITHOUT any user prompts
- **Risky fixes**: ONLY these require confirmation
- **All analysis**: Non-prompting (uses pre-approved tools and paths)

## Examples

```
User: /plugin-doctor agents
Result: Diagnoses all agents, auto-fixes safe issues, prompts for risky fixes

User: /plugin-doctor skill=my-skill
Result: Diagnoses single skill, applies fixes, verifies

User: /plugin-doctor skill-content marketplace/bundles/pm-dev-java/skills/cui-java-core
Result: Cross-file content analysis - duplication, extraction candidates, terminology

User: /plugin-doctor marketplace
Result: Comprehensive health check across all component types

User: /plugin-doctor commands --no-fix
Result: Diagnosis only, shows issues without applying fixes

User: /plugin-doctor
Result: Shows usage with all scope options
```

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons`
2. **Record lesson** with:
   - Component: `{type: "command", name: "plugin-doctor", bundle: "pm-plugin-development"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## Related

- `/plugin-create` - Create new components
- `/plugin-maintain` - Update existing components
- `/plugin-verify` - Run full marketplace verification
