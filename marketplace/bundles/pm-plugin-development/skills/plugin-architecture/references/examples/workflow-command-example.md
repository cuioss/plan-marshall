# Example: Thin Orchestrator Command (diagnose)

This example demonstrates a goal-based command that acts as a thin orchestrator, parsing parameters and routing to skill workflows.

## Command Responsibilities

**What Commands Do**:
- Parse user parameters
- Determine scope/intent
- Route to appropriate skill workflow
- Display results to user
- Handle follow-up interactions

**What Commands DON'T Do**:
- Execute complex logic (delegate to skills)
- Contain knowledge/standards (use skills)
- Duplicate workflow logic (invoke skills)

## plugin-diagnose Command

### File Location

```
marketplace/bundles/pm-plugin-development/commands/plugin-diagnose.md
```

### Command Structure

```markdown
---
name: plugin-diagnose
description: Find and understand quality issues in marketplace components
---

# Diagnose Marketplace Issues

Interactive command to analyze marketplace components and identify issues.

## Usage

**Diagnose specific component**:
```
/plugin-diagnose agent=my-agent
/plugin-diagnose command=my-command
/plugin-diagnose skill=my-skill
```

**Diagnose all components of a type**:
```
/plugin-diagnose agents
/plugin-diagnose commands
/plugin-diagnose skills
```

**Diagnose entire marketplace**:
```
/plugin-diagnose marketplace
```

**Diagnose with auto-fix**:
```
/plugin-diagnose marketplace --fix
```

## Workflow

### Step 1: Determine Scope

Parse parameters to determine what to analyze:

**Parameter Patterns**:
```
agent=<name>    → Specific component analysis
agents          → All agents
marketplace     → Complete marketplace
--fix           → Auto-fix flag
```

**Logic**:
```
If parameter matches "{type}={name}":
  scope = "single-component"
  component_type = type (agent/command/skill)
  component_name = name

Else if parameter matches "{type}s":
  scope = "all-of-type"
  component_type = type (agent/command/skill)

Else if parameter = "marketplace":
  scope = "marketplace"

Else:
  Ask user: "What would you like to diagnose?"
  Options:
    - Specific component
    - All of a type
    - Entire marketplace
```

**Check for flags**:
```
If "--fix" in parameters:
  auto_fix = true
```

### Step 2: Invoke Diagnostic Skill

Route to appropriate workflow based on scope:

**Single Component** (scope = "single-component"):
```
Skill: plugin-diagnose
Workflow: analyze-component
Parameters: {
  component_path: "marketplace/bundles/.../my-agent.md",
  component_type: "agent"
}
```

**All of Type** (scope = "all-of-type"):
```
Skill: plugin-diagnose
Workflow: analyze-all-of-type
Parameters: {
  component_type: "agents",
  scope: "marketplace"
}
```

**Marketplace** (scope = "marketplace"):
```
Skill: plugin-diagnose
Workflow: validate-marketplace
Parameters: {}
```

### Step 3: Display Results

Format and show diagnostic results to user.

**For single component**:
```
ANALYSIS: my-agent.md

✅ Structure: Valid
✅ Frontmatter: Complete
⚠️  References: 2 issues found
❌ Tool Coverage: Missing Skill tool in frontmatter

## Issues Found (3)

### High Severity (1)
- Line 45: Path issue in script reference
  bash ./scripts/analyzer.sh
  Fix: bash scripts/analyzer.sh

### Medium Severity (2)
- Line 67: Prohibited escape sequence
  Read: ../../../../standards/file.md
  Fix: Use Skill: cui-skill-name

- Line 89: Missing Skill tool in frontmatter
  Add 'Skill' to allowed-tools list

## Recommendations
1. Update script references to use relative path pattern
2. Replace external file refs with skill invocations
3. Add Skill to allowed-tools for standards loading

Quality Score: 65/100
```

**For all of type**:
```
ANALYSIS: All Agents (15 total)

## Summary
- Clean: 8 (53%)
- Issues Found: 7 (47%)

## Severity Breakdown
- Critical: 0
- High: 5
- Medium: 12
- Low: 8

## Components with Issues
1. my-agent.md (Score: 65) - 3 issues
2. other-agent.md (Score: 70) - 2 issues
[...]

## Top Issues
1. Path issue in scripts (5 occurrences)
2. Prohibited reference patterns (4 occurrences)
3. Missing skill invocations (3 occurrences)

Overall Type Health: 75/100
```

**For marketplace**:
```
MARKETPLACE HEALTH REPORT

## Overall Status: 85/100 ✅

### Statistics
- Total Bundles: 5
- Total Components: 78
  - Agents: 25
  - Commands: 35
  - Skills: 18
- Clean: 52 (67%)
- Issues: 26 (33%)

### Severity Breakdown
- Critical: 3 ⚠️
- High: 8
- Medium: 22
- Low: 15

### Top Issues Across Marketplace
1. Path issue in scripts (12 occurrences)
2. Prohibited reference patterns (8 occurrences)
3. Missing progressive disclosure (6 occurrences)

### Bundle Health Scores
1. pm-dev-java: 92/100 ✅
2. pm-dev-frontend: 88/100 ✅
3. pm-plugin-development: 82/100 ✅
4. pm-workflow: 78/100 ⚠️
5. plan-marshall: 95/100 ✅

### Recommendations
1. Fix critical issues first (3 components affected)
2. Update path usage across 12 components
3. Replace prohibited patterns in 8 components
```

### Step 4: Offer Fix Option

If issues found and --fix flag NOT provided:

```
Ask user:
  "Found 26 issues across marketplace. Apply automatic fixes?"
  Options:
    - Yes, fix automatically (safe fixes only)
    - No, just show the report
    - Let me review each fix

If user confirms OR --fix flag was provided:
  Proceed to Step 5
```

### Step 5: Apply Fixes (if confirmed)

Route to fix skill:

```
Skill: plugin-fix
Workflow: categorize-and-fix
Parameters: {
  issues: [issues from Step 2],
  auto_confirm_safe: true,  # If --fix flag
  prompt_for_risky: true   # Always ask for risky fixes
}
```

Display fix results:

```
FIXES APPLIED

## Safe Fixes (12 applied automatically)
✅ Fixed 12 path references
✅ Fixed 5 YAML frontmatter issues
✅ Corrected 3 reference patterns

## Risky Fixes (3 require confirmation)
⚠️  Structural change in my-agent.md - Review needed
⚠️  Logic modification in other-command.md - Review needed
⚠️  Deletion of deprecated section - Review needed

Would you like to review and apply risky fixes?
```

### Step 6: Verify Fixes (optional)

If fixes were applied, offer verification:

```
Ask user:
  "Fixes applied. Run verification?"
  Options:
    - Yes, verify all fixes worked
    - No, I'll verify manually

If confirmed:
  Skill: plugin-diagnose
  Workflow: validate-marketplace
  # Re-run diagnosis to verify fixes
```

## Key Patterns Demonstrated

### 1. Thin Orchestration

Command contains NO complex logic:
- ✅ Parameter parsing (simple if/else)
- ✅ Skill invocation (delegation)
- ✅ Result display (formatting)
- ❌ NO analysis algorithms
- ❌ NO quality standards
- ❌ NO fix implementation

All complex logic in skills.

### 2. Smart Parameter Parsing

Handles multiple parameter formats:
- Named parameters: `agent=my-agent`
- Type flags: `agents`
- Scope keywords: `marketplace`
- Option flags: `--fix`
- Missing parameters: asks user

### 3. Conditional Routing

Routes to different skill workflows based on parsed parameters:
- Single component → analyze-component workflow
- All of type → analyze-all-of-type workflow
- Marketplace → validate-marketplace workflow

### 4. Progressive User Interaction

Asks user only when needed:
- Ambiguous parameters → ask for clarification
- Missing required info → ask for input
- Destructive operations → ask for confirmation
- Clear defaults → proceed without asking

### 5. Workflow Chaining

Command chains multiple workflows:
1. Diagnose (plugin-diagnose skill)
2. Categorize and Fix (plugin-fix skill)
3. Verify (plugin-diagnose skill again)

Each step uses skill workflows.

### 6. Helpful Output

Results formatted for readability:
- Clear structure with sections
- Visual indicators (✅ ⚠️ ❌)
- Actionable recommendations
- Severity categorization
- Summary + details

## Comparison: Old vs New Architecture

### OLD (Component-Centric)

```
# 5 separate commands
/plugin-diagnose-agents
/plugin-diagnose-commands
/plugin-diagnose-skills
/plugin-diagnose-metadata
/plugin-diagnose-scripts

# Each command duplicates logic
# Each routes to separate agent
# User must know which command to use
```

### NEW (Goal-Based)

```
# 1 unified command
/plugin-diagnose {scope}

# Parses scope, routes to appropriate workflow
# All diagnostic logic in plugin-diagnose skill
# User thinks about goal (diagnose), not component type
```

**Benefits**:
- Simpler discovery (1 vs 5 commands)
- Unified interface
- Consistent behavior
- Single skill to maintain
- User-focused (goal-based)

## Testing the Command

**Test 1: Single Component**
```
Input: /plugin-diagnose agent=my-agent
Expected: Detailed analysis of my-agent.md
Verify: Report shows component-specific issues
```

**Test 2: All of Type**
```
Input: /plugin-diagnose agents
Expected: Aggregated report for all agents
Verify: Statistics and top issues shown
```

**Test 3: Marketplace**
```
Input: /plugin-diagnose marketplace
Expected: Complete marketplace health report
Verify: Bundle scores and overall health shown
```

**Test 4: Auto-Fix**
```
Input: /plugin-diagnose marketplace --fix
Expected: Diagnosis + automatic safe fixes
Verify: Fix report shows what was applied
```

**Test 5: Ambiguous Input**
```
Input: /plugin-diagnose
Expected: User prompted for scope
Verify: Options presented clearly
```

## Summary

The plugin-diagnose command demonstrates:
- **Thin orchestration**: No complex logic in command
- **Goal-based**: Unified interface for diagnostic goal
- **Smart routing**: Parameters determine workflow
- **User-friendly**: Clear output, helpful prompts
- **Skill delegation**: All logic in plugin-diagnose and plugin-fix skills
- **Workflow chaining**: Diagnose → Fix → Verify
