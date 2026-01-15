# Command Quality Standards

Comprehensive quality standards for marketplace commands including anti-bloat rules, orchestration patterns, and structure requirements.

## Overview

Commands are user-facing orchestrators invoked via slash commands (e.g., `/plugin-diagnose-agents`). They coordinate multiple agents, skills, and tools to accomplish complex workflows.

**Key Characteristics**:
- Invoked by users via `/command-name` (no bundle prefix)
- **MUST delegate to skills** via Skill tool (`Skill: bundle:skill-name`)
- Skills contain workflow logic; scripts contain computational logic
- MUST be **thin orchestrators** (minimal wrapper, NOT implementation)
- Target: **< 100 lines** (ideal) or **< 150 lines** (acceptable)
- **CRITICAL bloat threshold**: > 200 lines requires immediate refactoring

**Architecture Pattern**: Command → Skill → Script
- **Command**: Parameters, skill invocation, workflow selection (~50-100 lines)
- **Skill**: Workflow orchestration, tool coordination (~200-800 lines)
- **Script**: Computational logic, deterministic operations (Python/Bash)

## Required Frontmatter Structure

Commands do NOT have YAML frontmatter (unlike agents and skills). They are pure Markdown files.

**File Structure**:
```markdown
# Command Title

Brief description of command purpose.

## PURPOSE

Detailed purpose statement.

## PARAMETERS

Parameter documentation.

## WORKFLOW

Step-by-step workflow.
```

## The 9 Anti-Bloat Rules

Commands MUST follow these 9 anti-bloat rules to remain thin orchestrators.

### Rule 0: Delegate to Skills (FOUNDATIONAL)

**CRITICAL**: Commands MUST delegate ALL workflow logic to skills. Commands are thin wrappers.

**Command Architecture**:
```
Command (thin wrapper)
    ↓ delegates to
Skill (workflow orchestration)
    ↓ executes
Script (computational logic)
```

**What Commands Should Contain** (~50-100 lines):
- Parameter documentation
- Skill invocation with workflow selection
- Brief usage examples

**What Commands Should NOT Contain**:
- Step-by-step workflow logic (belongs in skill)
- Analysis algorithms (belongs in script)
- File processing loops (belongs in skill/script)
- Validation rules (belongs in skill/script)
- Output formatting logic (belongs in skill)

**Good** (thin wrapper):
```markdown
# My Command

Brief description.

## Parameters

| Parameter | Description |
|-----------|-------------|
| `scope` | Target scope for command |

## Workflow

Activate `bundle:my-skill` and execute the **My Workflow** workflow.

Pass parameters as specified by user.

## Related

- `bundle:my-skill` - Contains the workflow logic
```

**Bad** (bloated with logic):
```markdown
# My Command

## Workflow

### Step 1: Initialize
Display banner...

### Step 2: Discover Files
Glob pattern...
For each file:
  Parse content...

### Step 3: Analyze
For each item:
  Check rule 1...
  Check rule 2...
  [100 more lines of logic]

### Step 4: Generate Report
Format output...
[50 more lines]
```

**Rationale**:
- Skills are reusable across commands
- Scripts are testable independently
- Commands remain simple entry points
- Logic changes don't require command updates

### Rule 1: Delegate to Agents (NOT Inline Logic)

**CRITICAL**: Commands MUST delegate complex operations to agents, NOT implement logic inline.

**Bad** (inline logic):
```markdown
### Step 3: Analyze File

Read file content.
For each line:
  If line matches pattern:
    Extract value
    Validate value
    Check against standards
    Categorize issue
    Determine fix strategy
Store results in list.
Count issues by severity.
Generate summary.
```

**Good** (delegation):
```markdown
### Step 3: Analyze File

Task: subagent_type="pm-plugin-development:diagnose-agent"
Parameters:
  file_path: {file_path}
  mode: "strict"

Parse JSON result from agent.
```

**Rationale**: Keeps command focused on orchestration, agents handle implementation details.

### Rule 2: Use Task Tool for Complex Operations

**CRITICAL**: Commands MUST use Task tool to invoke agents for any non-trivial operation.

**What Qualifies as Complex** (requires agent):
- File analysis (structure, quality, standards compliance)
- Validation logic (rules, patterns, constraints)
- Code generation or transformation
- Multi-step reasoning
- Context-dependent decisions

**What Can Stay Inline** (simple orchestration):
- Parameter validation
- File discovery (Glob)
- JSON parsing from agent results
- Summary generation
- User prompts (AskUserQuestion)

**Example**:
```markdown
### Step 4: Analyze All Components

For EACH component:
  # ✅ Complex operation → delegate to agent
  Task: subagent_type="bundle:analyze-component"
  Parameters: component_path={path}

  # ✅ Simple orchestration → inline
  Parse JSON result
  Categorize issues (safe vs risky)
  Add to bundle summary
```

### Rule 3: No Duplicate Agent Logic

**CRITICAL**: Commands MUST NOT duplicate logic from agents.

**Violation Pattern**:
```markdown
# In command:
### Step 5: Validate References

Read file content.
For each line matching "Skill: *":
  Parse skill reference
  Check if skill exists
  Verify bundle prefix present
  Report violations

# This logic should be in agent, not command!
```

**Correct Pattern**:
```markdown
# In command:
### Step 5: Validate References

Task: subagent_type="bundle:validate-references"
Parameters: file_path={path}

Parse validation results from agent.
```

**Rationale**: Agents are reusable, commands just orchestrate them.

### Rule 4: Clear Parameter Documentation

**CRITICAL**: Commands MUST have clear PARAMETERS section documenting all parameters.

**Required Parameter Documentation**:
```markdown
## PARAMETERS

**scope** (optional, default: "marketplace")
- Values: "marketplace" | "global" | "project"
- Description: Scope of analysis - marketplace bundles, global ~/.claude, or project .claude

**component-name** (optional)
- Type: string
- Description: Analyze specific component by name (filters results)

**auto-fix** (optional, default: true)
- Type: boolean
- Description: Auto-fix safe issues; prompt for risky fixes

**--save-report** (optional flag)
- Description: Write Markdown report to project root
```

**Bad** (missing/unclear):
```markdown
## PARAMETERS

Takes some parameters. You can specify scope and other options.
```

### Rule 5: Bundle-by-Bundle Orchestration

**CRITICAL**: Commands processing multiple components MUST use sequential bundle processing.

**Required Pattern**:
```markdown
### Step 3: Group Components by Bundle

Parse bundle from component paths.
Sort bundles: pm-plugin-development first, then alphabetically.

### Step 4: Process Each Bundle Sequentially

For EACH bundle in sorted order:
  Step 4a: Analyze all components in bundle
  Step 4b: Validate references
  Step 4c: Aggregate results
  Step 4d: Apply fix workflow
  Step 4e: POST-FIX VERIFICATION (git status)
  Step 4f: MANDATORY bundle completion check

  ⚠️ MUST complete ALL steps before next bundle
```

**Anti-Pattern** (parallel processing without bundling):
```markdown
# ❌ Bad: Process all components in parallel
For EACH component:
  Launch agent in parallel

Wait for all agents to complete.
Generate summary.
```

**Rationale**: Bundle-by-bundle ensures:
- Organized output (grouped by bundle)
- Proper verification after fixes
- Mandatory completion checks prevent skipping steps
- Sequential processing easier to debug

### Rule 6: Progressive Disclosure

**CRITICAL**: Commands MUST use progressive disclosure - load skills/resources on-demand.

**Good** (progressive):
```markdown
### Step 1: Load Diagnostic Patterns

Skill: plan-marshall:ref-development-standards

### Step 2: Load Inventory

Skill: plan-marshall:tools-marketplace-inventory

# Load other skills only when needed in specific steps
```

**Bad** (load everything upfront):
```markdown
### Step 1: Load All Prerequisites

Skill: plan-marshall:ref-development-standards
Skill: plan-marshall:tools-marketplace-inventory
Skill: pm-plugin-development:bundle-orchestration-compliance
Read references/reporting-templates.md
Skill: pm-dev-java:java-core
Skill: pm-dev-frontend:cui-javascript
# ... loads 10 more skills upfront
```

**Rationale**: Progressive disclosure reduces context usage, loads only what's needed.

### Rule 7: Mandatory Completion Checks

**CRITICAL**: Commands MUST have mandatory completion checks for bundle-by-bundle processing.

**Required Pattern**:
```markdown
### Step 4i: POST-FIX VERIFICATION (MANDATORY)

After ANY fixes applied:
Bash: git status --short

Verify:
- Count files actually modified
- Compare to fixes claimed by agents
- Report PASS if counts match, FAIL if mismatch

If FAIL: Report discrepancy, investigate.

### Step 4j: MANDATORY Bundle Completion Check

Before proceeding to next bundle, verify:
- ✅ All components analyzed
- ✅ All issues categorized
- ✅ Fix workflow completed
- ✅ POST-FIX VERIFICATION passed
- ✅ Bundle summary generated

⚠️ Only after ALL steps complete: Proceed to next bundle
```

**Anti-Pattern** (no verification):
```markdown
### Step 4: Process Bundle

Analyze components.
Apply fixes.
Move to next bundle.  # ❌ No verification!
```

**Rationale**: Mandatory checks prevent:
- Skipping bundle processing steps
- False positive fix claims (agent says fixed but git shows no changes)
- Incomplete workflows
- Unreported errors

### Rule 8: No Embedded Standards

**CRITICAL**: Commands MUST NOT contain embedded standards documentation. Use reference guides or skill dependencies.

**Bad** (embedded standards):
```markdown
## JAVA CODING STANDARDS

### Naming Conventions
Use camelCase for variables...
[100 lines of coding standards]

### Logging Requirements
All classes must use Logger...
[50 lines of logging standards]

### Error Handling
Exceptions should be...
[50 lines of error handling standards]
```

**Good** (reference/skill):
```markdown
### Step 2: Load Standards

Skill: pm-dev-java:java-core

# All standards loaded from skill, not embedded in command
```

**Rationale**:
- Keeps commands concise
- Standards reusable across commands
- Single source of truth
- Easier to maintain

## Bloat Detection

**Classification** (commands are THIN orchestrators):
- **IDEAL**: < 100 lines (proper thin wrapper)
- **ACCEPTABLE**: 100-150 lines (minor workflow logic OK)
- **BLOATED**: 150-200 lines (too much logic, needs refactoring)
- **CRITICAL**: > 200 lines (severe bloat, MUST refactor immediately)

**Target**: Keep commands < 100 lines (IDEAL).

**Why Such Low Threshold?**
- Commands are thin orchestrators (minimal wrapper)
- **ALL workflow logic belongs in skills**
- **ALL computational logic belongs in scripts**
- Commands ONLY: parse parameters → invoke skill → display results
- If command > 100 lines: logic should move to skill

## Command Structure Requirements

### Required Sections

1. **Title and Description**:
```markdown
# Command Title

Brief one-sentence description.
```

2. **PURPOSE**:
```markdown
## PURPOSE

Detailed purpose statement explaining what command does and why.
```

3. **PARAMETERS**:
```markdown
## PARAMETERS

Clear documentation of all parameters with types, defaults, descriptions.
```

4. **WORKFLOW**:
```markdown
## WORKFLOW

### Step 1: First Step
### Step 2: Second Step
...

Step-by-step execution logic.
```

5. **CONTINUOUS IMPROVEMENT RULE**:
```markdown
## CONTINUOUS IMPROVEMENT RULE

Standard self-update pattern for commands.
```

### Optional Sections

- **RELATED**: Related commands, agents, skills
- **EXAMPLES**: Usage examples (concise)
- **NOTES**: Additional context or warnings

### Section Ordering

**Standard order** (for consistency):
1. Title and description
2. PURPOSE
3. PARAMETERS
4. WORKFLOW (main content)
5. CONTINUOUS IMPROVEMENT RULE
6. RELATED (if applicable)
7. EXAMPLES (if applicable)
8. NOTES (if applicable)

## Orchestration Patterns

### Pattern 1: Single Component Analysis

**Use Case**: Analyze one specific component by name.

```markdown
### Step 3: Discover Component

If component-name provided:
  Glob: pattern="{component-name}.md", path="{scope_path}"
  Verify exactly 1 match found
Else:
  ERROR: component-name required for this command
```

### Pattern 2: Scope-Based Discovery

**Use Case**: Analyze components based on scope parameter.

```markdown
### Step 3: Discover Components

Based on scope parameter:

**marketplace** (default):
  Skill: plan-marshall:tools-marketplace-inventory
  Parse JSON to extract component paths

**global**:
  Glob: pattern="*.md", path="~/.claude/{agents|commands|skills}"

**project**:
  Glob: pattern="*.md", path=".claude/{agents|commands|skills}"

Output: List of component paths
```

### Pattern 3: Bundle-by-Bundle Processing

**Use Case**: Process multiple components grouped by bundle.

```markdown
### Step 4: Group by Bundle

Parse bundle from paths:
  marketplace/bundles/{bundle-name}/{type}/{component}.md

Group components by bundle.
Sort bundles: pm-plugin-development first, then alphabetically.

### Step 5: Process Each Bundle

For EACH bundle in sorted order:
  5a: Analyze all components (parallel agent launches OK within bundle)
  5b: Categorize issues
  5c: Bundle summary
  5d: Fix workflow
  5e: POST-FIX VERIFICATION
  5f: MANDATORY completion check
```

### Pattern 4: Parallel Agent Launches (Within Bundle)

**Use Case**: Analyze multiple components in same bundle simultaneously.

```markdown
### Step 5a: Analyze Components in Bundle

Launch agents in parallel (within single bundle):

For EACH component in current bundle:
  Task: subagent_type="bundle:analyze-component"
  Parameters: component_path={path}

Wait for all agents to complete.
Aggregate results for bundle.
```

**Note**: Parallel OK within bundle, sequential between bundles.

### Pattern 5: Two-Phase Fix Workflow

**Use Case**: Categorize issues, auto-fix safe ones, prompt for risky.

```markdown
### Step 5d: Fix Workflow

**Phase 1: Categorize**
- Safe fixes: YAML errors, missing fields, broken references
- Risky fixes: Architectural violations, bloat, major refactoring

**Phase 2: Apply**
- If auto-fix=true: Apply safe fixes automatically
- For risky fixes: AskUserQuestion for each fix
  Options:
    1. Apply fix
    2. Skip this fix
    3. Skip all remaining fixes

**Phase 3: Verify**
- Bash: git status --short
- Count files modified
- Compare to fixes claimed
- Report PASS/FAIL
```

### Pattern 6: Progressive Skill Loading

**Use Case**: Load skills on-demand, not all upfront.

```markdown
### Step 1: Load Core Skills

Skill: plan-marshall:ref-development-standards

### Step 2: Discover Components

Skill: plan-marshall:tools-marketplace-inventory

# Later steps load additional skills only if needed:

### Step 7: Generate Report (If --save-report)

If --save-report flag:
  Read references/reporting-templates.md
  # Only loaded when actually generating report
```

## Reference Format Requirements

### Bundle Prefix Rules

**SlashCommand invocations** (commands invoke commands):
- ❌ Bundle prefix: `/pm-plugin-development:plugin-update-agent`
- ✅ No prefix: `/plugin-update-agent`

**Task invocations** (commands invoke agents):
- ❌ No prefix: `subagent_type="diagnose-agent"`
- ✅ Bundle prefix: `subagent_type="pm-plugin-development:diagnose-agent"`

**Skill invocations** (commands invoke skills):
- ❌ No prefix: `Skill: cui-java-core`
- ✅ Bundle prefix: `Skill: pm-dev-java:java-core`

**Rationale**:
- SlashCommand: Command names globally unique, no bundle needed
- Task: Agent names NOT globally unique, bundle disambiguates
- Skill: Skill names NOT globally unique, bundle disambiguates

## CONTINUOUS IMPROVEMENT RULE

Commands MUST include standard lessons-learned pattern:

```markdown
## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons-learned`
2. **Record lesson** with:
   - Component: `{type: "command", name: "{command-name}", bundle: "{bundle}"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding
```

**Key Points**:
- Only activate skill when you have lessons to record
- Lessons are stored via `manage-lessons-learned` skill (individual Markdown files)
- Categories: bug, improvement, pattern, anti-pattern

## Common Issues and Fixes

### Issue 1: Bloat > 500 Lines (CRITICAL)

**Symptoms**:
- Command exceeds 500 lines
- Classification: CRITICAL

**Diagnosis**:
```bash
Bash: scripts/analyze-markdown-file.sh {command_path} command
# Check: bloat.classification = "CRITICAL"
# Check: metrics.line_count > 500
```

**Fix Strategy**:
Apply 8 anti-bloat rules:
1. Extract inline logic → create new agent
2. Replace duplicate logic → use existing agent
3. Extract embedded standards → reference skill or guide
4. Condense workflow steps (remove verbose explanations)
5. Remove redundant examples
6. Use progressive disclosure (load skills on-demand)

**Example Refactoring**:
```markdown
# Before (150 lines of inline validation):
### Step 5: Validate File

Read file content.
For each line:
  [100 lines of validation logic...]

# After (10 lines, delegated):
### Step 5: Validate File

Task: subagent_type="bundle:file-validator"
Parameters: file_path={path}, mode="strict"

Parse validation results.
```

### Issue 2: Missing PARAMETERS Section

**Symptoms**:
- No PARAMETERS section
- Parameters documented inconsistently
- Unclear parameter types or defaults

**Diagnosis**:
```bash
Bash: scripts/analyze-markdown-file.sh {command_path} command
# Check: parameters.has_section = false
```

**Fix**:
Add clear PARAMETERS section following format in Rule 4.

### Issue 3: No Bundle-by-Bundle Orchestration

**Symptoms**:
- Command processes all components in parallel
- No bundle grouping
- No sequential bundle processing
- No mandatory completion checks

**Diagnosis**:
Manual review of workflow steps:
- Check for bundle grouping step
- Check for sequential "For EACH bundle" loop
- Check for POST-FIX VERIFICATION
- Check for MANDATORY completion check

**Fix**:
Refactor to use Pattern 3 (Bundle-by-Bundle Processing).

### Issue 4: Missing POST-FIX VERIFICATION

**Symptoms**:
- Fixes applied but no verification
- No `git status` check after fixes
- No comparison of claimed vs actual changes

**Diagnosis**:
Search command for "git status" or "POST-FIX VERIFICATION":
```bash
Grep: pattern="git status|POST-FIX", path={command_path}, output_mode="content"
```

**Fix**:
Add POST-FIX VERIFICATION step (see Rule 7).

### Issue 5: Incorrect Bundle Prefix Usage

**Symptoms**:
- SlashCommand has bundle prefix: `/bundle:command` (❌)
- Task invocation missing bundle prefix: `subagent_type="agent"` (❌)
- Skill invocation missing bundle prefix: `Skill: skill-name` (❌)

**Diagnosis**:
```bash
Bash: python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:analyze validate-references {command_path}
# Check references array for incorrect formats
```

**Fix**:
- SlashCommand: Remove bundle prefix
- Task: Add bundle prefix
- Skill: Add bundle prefix

### Issue 6: Embedded Standards (Rule 8 Violation)

**Symptoms**:
- Command contains large standards documentation blocks
- Duplicate standards from other commands/agents
- Standards not externalized to skills/references

**Diagnosis**:
Manual review for large documentation blocks (>50 lines) that look like standards.

**Fix**:
Extract standards to:
- **Skill** (if standards complex and reusable): `Skill: bundle:standards-skill`
- **Reference Guide** (if standards simple): Load via agent that reads reference

## Summary Checklist

**Before marking command as "quality approved"**:
- ✅ **Rule 0**: Thin wrapper delegating to skill (< 100 lines ideal, < 150 acceptable)
- ✅ **Rule 0**: No workflow logic in command (all in skill)
- ✅ File size < 150 lines (ACCEPTABLE) - CRITICAL if > 200 lines
- ✅ Rule 1: Delegates to agents for complex operations (if agents used)
- ✅ Rule 2: Uses Task tool for complex operations (if agents used)
- ✅ Rule 3: No duplicate agent logic
- ✅ Rule 4: Clear PARAMETERS section
- ✅ Rule 5: Bundle-by-bundle orchestration (if multi-component)
- ✅ Rule 6: Progressive disclosure (skills loaded on-demand)
- ✅ Rule 7: Mandatory completion checks and POST-FIX VERIFICATION
- ✅ Rule 8: No embedded standards
- ✅ Proper bundle prefix usage (SlashCommand no prefix, Task/Skill have prefix)
- ✅ CONTINUOUS IMPROVEMENT RULE present
- ✅ Clear section structure (PURPOSE, PARAMETERS, WORKFLOW)
- ✅ Thin orchestration (parameters + skill invocation only)

**Quick Bloat Check**:
```bash
wc -l command.md
# < 100: IDEAL (proper thin wrapper)
# 100-150: ACCEPTABLE (minor logic OK)
# 150-200: BLOATED (refactor needed)
# > 200: CRITICAL (must refactor immediately)
```
