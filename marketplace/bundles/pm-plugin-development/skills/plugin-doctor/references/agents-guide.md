# Agent Quality Standards

Comprehensive quality standards for marketplace agents including tool coverage, architectural rules, and best practices.

## Overview

Agents are specialized execution units invoked via Task tool by commands. They perform focused analysis, validation, or transformation operations.

**Key Characteristics**:
- Invoked by commands via `Task: subagent_type="bundle:agent-name"`
- Have access to specific tools (declared in frontmatter)
- Execute autonomously and return results to caller
- CANNOT invoke other agents (Task tool unavailable at runtime)
- CANNOT invoke commands (SlashCommand tool unavailable at runtime)

## Required Frontmatter Structure

All agents MUST have YAML frontmatter with required fields:

```yaml
---
name: agent-name
description: Clear, concise description of agent purpose
tools:
  - Read
  - Write
  - Edit
  - Grep
  - Bash
model: sonnet
---
```

**Required Fields**:
- `name`: Agent identifier (kebab-case, matches filename)
- `description`: One-sentence purpose statement
- `tools`: Array of tool names (NOT comma-separated string)

**Optional Fields**:
- `model`: Preferred model (sonnet, opus, haiku) - defaults to sonnet

**Common Errors**:
- ❌ `tools: Read, Write, Edit` (comma-separated string)
- ✅ `tools: ["Read", "Write", "Edit"]` or YAML array format
- ❌ Missing `name` or `description`
- ❌ Invalid YAML syntax (missing colons, incorrect indentation)

## Tool Coverage Requirements

### Tool Fit Score

**Calculation**:
```
tool_fit_score = (used_tools / total_needed_tools) * 100
total_needed_tools = used_tools + missing_tools
```

**Rating Thresholds**:
- **Excellent**: >= 90% (all needed tools declared, minimal unused)
- **Good**: >= 70% (most needed tools declared)
- **Needs improvement**: >= 50% (significant gaps)
- **Poor**: < 50% (major tool coverage issues)

**Target**: All agents should achieve "Excellent" (>= 90%) tool fit score.

### Common Tool Patterns

**File Reading**:
- `Read`: Read file contents
- `Glob`: Find files by pattern
- `Grep`: Search file contents

**File Modification**:
- `Edit`: Modify existing files (preferred for changes)
- `Write`: Create new files

**Execution**:
- `Bash`: Execute shell commands (use sparingly)

**Interaction**:
- `AskUserQuestion`: Prompt user for decisions

**Orchestration** (Skills only):
- `Skill`: Invoke other skills

**PROHIBITED in Agents**:
- ❌ `Task`: Agents CANNOT invoke other agents (Rule 6 violation)
- ❌ `SlashCommand`: Agents CANNOT invoke commands (architectural violation)

### Tool Coverage Analysis

**Missing Tools** (declared but not used):
- Indicates over-specification
- Should be removed from frontmatter
- Low-priority issue (doesn't break functionality)

**Unused Tools** (used but not declared):
- **CRITICAL** - agent will fail at runtime
- Must be added to frontmatter immediately
- High-priority issue

**Example**:
```yaml
# Agent declares: Read, Write, Edit, Grep
# Agent uses: Read, Edit, Grep, Bash
# Missing: Write (declared but not used) → remove from frontmatter
# Unused: Bash (used but not declared) → add to frontmatter
```

## Architecture Rule 6: Task Tool Prohibition

**CRITICAL RULE**: Agents CANNOT use Task tool to invoke other agents.

**Rationale**: Task tool is unavailable at agent runtime. Attempting to use Task will cause runtime failure.

**Detection**:
- Check frontmatter `tools` array for "Task"
- Search agent content for `Task tool`, `subagent_type`, `Task:` patterns

**Violation Example**:
```yaml
---
name: my-agent
tools:
  - Read
  - Task  # ❌ VIOLATION
---
```

**Fix**:
- **Option 1**: Convert agent to command (commands CAN use Task tool)
- **Option 2**: Inline the agent logic into calling command
- **Option 3**: Refactor to use Skill invocation (if applicable)

**Valid Alternatives**:
- Commands invoke agents via Task tool
- Agents invoke skills via Skill tool
- Agents return results to caller for orchestration

## Architecture Rule 7: Maven Execution Restriction

**CRITICAL RULE**: Only `maven-builder` agent may execute Maven commands directly.

**Rationale**: Maven execution is centralized in maven-builder agent for consistency, error handling, and performance tracking.

**Prohibited Patterns** (for non-maven-builder agents):
```bash
# ❌ Direct Maven execution
Bash: ./mvnw clean install
Bash: mvn test
Bash: maven package
```

**Detection**:
- Search agent content for: `Bash.*mvn`, `Bash.*./mvnw`, `Bash.*maven`
- Check agent name: violations allowed ONLY if agent name == "maven-builder"

**Fix**:
```yaml
# Instead of direct Maven execution:
# ❌ Bash: ./mvnw test

# Use maven-builder agent:
# ✅ Task: subagent_type="pm-dev-builder:maven-builder"
#    Parameters: goals="test", capture_output=true
```

**Valid Maven Usage**:
- Commands invoke maven-builder agent via Task tool
- maven-builder agent executes Maven and returns results
- Non-maven-builder agents receive results, no direct Maven execution

## Pattern 22: Agent Reporting Requirement

**CRITICAL PATTERN**: Agents MUST report improvements to caller (not self-invoke commands).

**CONTINUOUS IMPROVEMENT RULE Format**:

**Valid Pattern** (caller-reporting):
```markdown
## CONTINUOUS IMPROVEMENT RULE

**CRITICAL:** Every time you execute this agent and discover a more precise, better, or more efficient approach, **REPORT the improvement to your caller** with:
1. [Specific improvement areas]

Return structured improvement suggestion in your analysis result:
```
IMPROVEMENT OPPORTUNITY DETECTED

Area: [specific area]
Current limitation: [what doesn't work well]
Suggested enhancement: [specific improvement]
Expected impact: [benefit of change]
```

The caller can then invoke `/plugin-update-agent agent-name=... update="..."` based on your report.
```

**Invalid Pattern** (self-update) - Pattern 22 Violation:
```markdown
## CONTINUOUS IMPROVEMENT RULE

If you discover improvements, invoke `/plugin-update-agent` directly to update yourself.
```

**Detection**:
- Check for CONTINUOUS IMPROVEMENT RULE section
- Verify pattern: "report to caller" + "The caller can then invoke"
- Violation: Direct invocation instructions (agent invokes command itself)

**Rationale**:
- Agents cannot invoke commands (no SlashCommand tool)
- Agents should not self-modify (architectural separation)
- Commands orchestrate all modifications based on agent reports

**Fix**:
- Update CONTINUOUS IMPROVEMENT RULE section to use caller-reporting pattern
- Remove any `/plugin-update-agent` invocation instructions
- Add "return structured improvement suggestion" guidance

## Bloat Detection

**Classification**:
- **NORMAL**: < 300 lines (healthy agent size)
- **LARGE**: 300-500 lines (approaching bloat, review for opportunities to extract logic)
- **BLOATED**: 500-800 lines (excessive, should be refactored)
- **CRITICAL**: > 800 lines (severe bloat, immediate refactoring required)

**Target**: Keep agents < 300 lines (NORMAL).

**Bloat Indicators**:
1. **Embedded Standards**: Large sections documenting standards instead of using external references
2. **Duplicate Logic**: Logic repeated from other agents/commands
3. **Over-Specification**: Excessive detail in workflow steps
4. **Example Overload**: Too many examples instead of concise patterns
5. **Inline Documentation**: Large documentation blocks instead of separate reference files

**Anti-Bloat Strategies**:

### 1. Extract Standards to Reference Files
**Before** (embedded in agent):
```markdown
### Java Code Quality Standards

- Use descriptive variable names
- Avoid magic numbers
- [100 lines of standards...]
```

**After** (reference):
```markdown
### Step 2: Load Quality Standards

Read references/java-quality-standards.md
```

### 2. Use Skill Dependencies
**Before** (duplicate logic):
```markdown
### Step 3: Validate Logging

[50 lines of logging validation logic copied from logging-validator agent]
```

**After** (skill invocation):
```markdown
### Step 3: Validate Logging

Skill: pm-dev-java:logging-validator
```

### 3. Concise Workflow Steps
**Before** (over-specified):
```markdown
### Step 4: Analyze File

First, use the Read tool to read the file.
Then, parse the content line by line.
For each line, check if it matches pattern X.
If it matches, extract the value.
Store the value in a list.
After processing all lines, count the matches.
Return the count to the caller.
```

**After** (concise):
```markdown
### Step 4: Analyze File

Read file, parse content, extract matches for pattern X, return count.
```

### 4. Condense Examples
**Before** (example overload):
```markdown
## Examples

### Example 1: Valid File
[20 lines...]

### Example 2: Invalid File
[20 lines...]

### Example 3: Edge Case A
[20 lines...]

### Example 4: Edge Case B
[20 lines...]
```

**After** (concise examples):
```markdown
## Examples

**Valid**: File with correct format → analysis succeeds
**Invalid**: Missing required field → error reported
**Edge Cases**: Empty file → handled gracefully, malformed → specific error
```

## Best Practices

### 1. Single Responsibility

Each agent should do ONE thing well.

**Good**:
- `analyze-file-structure` - Analyzes file structure only
- `validate-references` - Validates references only
- `generate-report` - Generates reports only

**Bad**:
- `analyze-and-fix-and-report` - Does multiple things (violates SRP)

### 2. Deterministic Logic in Scripts

Move deterministic validation logic to external scripts:

**Agent** (AI-powered logic):
- Context interpretation
- Judgment calls
- User interaction
- Complex reasoning

**Script** (deterministic logic):
- Pattern matching
- JSON parsing
- File structure validation
- Score calculation

**Example**:
```bash
# Agent workflow:
### Step 3: Analyze Structure

Bash: scripts/analyze-structure.sh {file_path}
# Parse JSON output
# Apply AI reasoning to categorize issues
# Determine fix strategy
```

### 3. Progressive Disclosure

Load external resources on-demand:

```markdown
### Step 2: Load Standards (Progressive Disclosure)

Read references/coding-standards.md

# Do NOT load all references upfront:
# ❌ Read references/standard1.md
# ❌ Read references/standard2.md
# ❌ Read references/standard3.md
```

### 4. Proper Error Handling

Always validate inputs and handle errors gracefully:

```markdown
### Step 1: Validate Parameters

**Required Parameters**:
- `file_path`: Path to file to analyze
- `mode`: Analysis mode (strict|lenient)

**Validation**:
- If file_path not provided: ERROR with clear message
- If file not found: ERROR with path
- If mode invalid: ERROR with valid options

**Error Format**:
ERROR: [Clear description]
Expected: [What was expected]
Actual: [What was received]
Action: [How to fix]
```

### 5. Clear Output Format

Define clear output structure:

```markdown
### Step 7: Return Results

**Output Format**:
{
  "status": "success|error",
  "file_analyzed": "{file_path}",
  "issues_found": {count},
  "issues": [
    {
      "line": {line_number},
      "severity": "critical|warning|info",
      "message": "{description}",
      "fix_available": true|false
    }
  ]
}
```

### 6. Tool Usage Efficiency

Use appropriate tools for tasks:

**File Operations**:
- ✅ `Read` for reading files (NOT `Bash: cat`)
- ✅ `Grep` for searching (NOT `Bash: grep`)
- ✅ `Glob` for finding files (NOT `Bash: find`)
- ✅ `Edit` for modifications (NOT `Bash: sed`)

**Bash Tool**: Only for operations without specialized tools:
- Build commands (npm, maven)
- Git operations
- Test execution
- Script execution

### 7. Documentation Requirements

**Required Sections**:
- **Purpose**: One-sentence description
- **PARAMETERS**: Clear parameter documentation with types, defaults, validation
- **WORKFLOW**: Step-by-step execution logic
- **TOOL USAGE**: List of tools and their specific uses
- **CRITICAL RULES**: Any critical constraints or requirements
- **CONTINUOUS IMPROVEMENT RULE**: Caller-reporting pattern

**Optional Sections**:
- **Examples**: Concise usage examples
- **Error Handling**: Common errors and solutions
- **Performance**: Notes on performance characteristics

## Common Issues and Fixes

### Issue 1: Low Tool Fit Score

**Symptoms**:
- Tool fit score < 70%
- Missing tools array shows required tools not declared
- Unused tools array shows tools declared but not used

**Diagnosis**:
```bash
# Run tool coverage analysis
Bash: scripts/analyze-tool-coverage.sh {agent_path}

# Check JSON output:
# - tool_coverage.missing_tools: Tools used but not declared
# - tool_coverage.unused_tools: Tools declared but not used
# - tool_coverage.tool_fit_score: Overall score
```

**Fix**:
1. Add missing tools to frontmatter
2. Remove unused tools from frontmatter
3. Re-run analysis to verify 90%+ score

### Issue 2: Rule 6 Violation (Task Tool)

**Symptoms**:
- `Task` appears in frontmatter tools array
- Agent attempts to invoke other agents

**Diagnosis**:
```bash
Bash: scripts/analyze-markdown-file.sh {agent_path} agent
# Check: rules.rule_6_violation = true
```

**Fix Options**:
- **Convert to command**: Commands CAN use Task tool
- **Inline logic**: Absorb agent logic into calling command
- **Use skills**: Replace Task with Skill invocation

### Issue 3: Rule 7 Violation (Maven Usage)

**Symptoms**:
- Direct Maven execution in non-maven-builder agent
- `Bash: mvn ...` or `Bash: ./mvnw ...` patterns

**Diagnosis**:
```bash
Bash: scripts/analyze-markdown-file.sh {agent_path} agent
# Check: rules.rule_7_violation = true
```

**Fix**:
```yaml
# Replace direct Maven:
# ❌ Bash: ./mvnw test

# With maven-builder invocation:
# ✅ Task: subagent_type="pm-dev-builder:maven-builder"
#    Parameters: goals="test"
```

### Issue 4: Pattern 22 Violation (Self-Invocation)

**Symptoms**:
- CONTINUOUS IMPROVEMENT RULE instructs agent to invoke commands directly
- Pattern contains `/plugin-update-agent` invocation instructions

**Diagnosis**:
```bash
Bash: scripts/analyze-markdown-file.sh {agent_path} agent
# Check: continuous_improvement_rule.format.pattern_22_violation = true
```

**Fix**:
Update CONTINUOUS IMPROVEMENT RULE to use caller-reporting pattern (see Pattern 22 section above).

### Issue 5: Bloat (>500 Lines)

**Symptoms**:
- Agent exceeds 500 lines
- Classification: BLOATED or CRITICAL

**Diagnosis**:
```bash
Bash: scripts/analyze-markdown-file.sh {agent_path} agent
# Check: bloat.classification = "BLOATED" or "CRITICAL"
```

**Fix**:
Apply anti-bloat strategies:
1. Extract embedded standards to reference files
2. Use skill dependencies for shared logic
3. Condense workflow steps
4. Move deterministic logic to scripts
5. Reduce example verbosity

## Summary Checklist

**Before marking agent as "quality approved"**:
- ✅ Frontmatter present and valid (name, description, tools)
- ✅ Tool fit score >= 90% (Excellent)
- ✅ No Rule 6 violations (no Task tool)
- ✅ No Rule 7 violations (no Maven unless maven-builder)
- ✅ No Pattern 22 violations (caller-reporting pattern)
- ✅ Bloat classification NORMAL (<300 lines)
- ✅ Clear workflow with step-by-step logic
- ✅ Proper error handling
- ✅ CONTINUOUS IMPROVEMENT RULE present (caller-reporting)
- ✅ Tool usage follows best practices (Read/Grep/Glob instead of Bash)
- ✅ Single responsibility principle
- ✅ Progressive disclosure for external resources
