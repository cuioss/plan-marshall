# Agent Creation Guide

Comprehensive guide for creating well-structured Claude Code agents following marketplace architecture.

## When to Create Agents vs Other Components

### Create an Agent When:
- **Focused execution** - Single, well-defined task (analyze code, run tests, build project)
- **Autonomous operation** - Can complete task without user interaction after launch
- **Tool usage** - Needs specific tools to accomplish task
- **Reusable logic** - Task will be performed multiple times across workflows

### Create a Command Instead When:
- **User interaction required** - Need to ask questions or gather requirements
- **Orchestration needed** - Coordinating multiple agents or complex workflows
- **Delegation required** - Need to launch other agents using Task tool
- **Parameter routing** - Parsing parameters and routing to different workflows

### Create a Skill Instead When:
- **Knowledge provision** - Providing standards, guidelines, or reference material
- **No execution** - Just documentation to be loaded, not actions to perform
- **Progressive disclosure** - Large body of knowledge loaded on-demand

## Agent Design Principles

### Principle 1: MANDATORY Markers for Critical Steps

Agent workflows must use MANDATORY markers to ensure critical steps are executed, not skipped.

**Why**: When agents are launched via Task tool, Claude may treat instructions as suggestions. MANDATORY markers force attention to essential steps.

**Pattern**:
```markdown
### Step 2: Run Diagnostic Script

**MANDATORY**: Execute this script NOW before proceeding:
```bash
python3 .plan/execute-script.py {bundle}:{skill}:analyze {target}
```

Do not continue to Step 3 until this completes successfully.
```

**When to Use MANDATORY**:
- Script execution steps
- Validation gates
- Required tool invocations
- Steps that must not be skipped

**Avoid Overuse**:
- Don't mark every step MANDATORY
- Reserve for truly critical steps
- 2-3 MANDATORY markers per workflow is typical

### Principle 2: Focused Executors
Agents do ONE task well. Don't create "swiss army knife" agents.

**Good** (Focused):
```markdown
Agent: code-reviewer
Purpose: Review code changes for quality issues
```

**Bad** (Unfocused):
```markdown
Agent: code-manager
Purpose: Review code, run tests, deploy, generate docs, update dependencies
```

### Principle 2: Self-Contained
Agents must be self-contained with clear input/output contracts.

**Required**:
- Document expected inputs
- Document produced outputs
- No dependencies on other agents
- All required tools listed in frontmatter

### Principle 3: Clear Workflow
Agents must have numbered workflow steps that are easy to follow.

**Good Workflow**:
```markdown
## Workflow

### Step 1: Load Configuration
Read project configuration file

### Step 2: Analyze Code
Grep for patterns, Read matching files

### Step 3: Generate Report
Format findings as JSON
```

## Resource Mode Labeling

Agents with scripts and references should clearly label each resource's mode:

| Resource | Mode | Purpose |
|----------|------|---------|
| `analyze.py` | **EXECUTE** | Run to analyze components |
| `README.md` | READ | Read for context if needed |
| `patterns.md` | REFERENCE | Consult when specific pattern needed |

**Mode Definitions**:
- **EXECUTE**: Run this script/tool immediately as part of workflow
- **READ**: Load this file's content into context
- **REFERENCE**: Consult on-demand when specific information needed

This prevents ambiguity about whether to "run" or "read" a resource.

## Tool Selection Guidelines

### Core File Operation Tools
- **Read** - Reading file contents (always prefer over `cat` via Bash)
- **Write** - Creating new files
- **Edit** - Modifying existing files
- **Glob** - Finding files by pattern (always prefer over `find` via Bash)
- **Grep** - Searching file contents (always prefer over `grep` via Bash)

### Shell Execution
- **Bash** - For git operations, build commands, operations requiring shell
- **NEVER** include Task tool (agents can't delegate - see Rule 6)

### External Access
- **WebFetch** - Fetching web content
- **WebSearch** - Searching web (requires approval)

### Specialized Tools
- **AskUserQuestion** - Rare in agents (usually in commands instead)
- **NotebookEdit** - Jupyter notebook operations
- **SlashCommand** - NEVER for agents (unavailable at runtime)

## Critical Rules

### Rule 6: Agents CANNOT Use Task Tool

**Why**: Task tool is unavailable to agents at runtime. Agents are focused executors, not orchestrators.

**Error Pattern**:
```yaml
---
name: my-agent
tools: Read, Write, Task  # ❌ WRONG - will fail at runtime
---
```

**If Agent Needs Delegation**:
- Create a **Command** instead (commands can use Task tool)
- Command orchestrates multiple agents
- Agents report back to command

**Correct Pattern**:
```
Command: analyze-project
  ├─ Task: code-analyzer agent (focused on code)
  ├─ Task: test-analyzer agent (focused on tests)
  └─ Aggregate results
```

### Rule 7: Only maven-builder Agent Can Execute Maven

**Why**: Centralized build execution prevents scattered Maven calls and ensures consistent build patterns.

**Error Pattern**:
```yaml
---
name: java-tester
tools: Read, Bash  # Bash used for: ./mvnw test
---
```
❌ WRONG - This agent will call Maven, violating Rule 7

**Correct Pattern**:
```yaml
---
name: maven-builder
tools: Read, Bash  # ✅ ONLY this agent may call Maven
---
```

**If Your Agent Needs Build**:
- Agent analyzes and returns results to caller
- Caller orchestrates maven-builder agent if build needed
- Don't build inside analysis agents

### Pattern 22: Agents Record Lessons via manage-lessons-learned Skill

**Why**: Centralized lesson storage enables systematic improvement across all components.

**Error Pattern**:
```markdown
## CONTINUOUS IMPROVEMENT RULE

**YOU MUST immediately update this file** using `/plugin-update-agent`
```
❌ WRONG - Agent can't invoke commands

**Correct Pattern**:
```markdown
## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons-learned`
2. **Record lesson** with:
   - Component: `{type: "agent", name: "{agent-name}", bundle: "{bundle}"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding
```
✅ CORRECT - Agent records lesson only when there's something to record

## Model Selection Guidelines

### When to Specify Model

**Specify model when**:
- Agent requires extended reasoning (use `model: opus`)
- Agent needs fast execution for simple tasks (use `model: haiku`)
- Agent must maintain long context (use `model: sonnet` or `opus`)

**Omit model when**:
- Standard execution is fine (uses default)
- No special model requirements
- Let system choose appropriate model

### Model Options

```yaml
model: haiku   # Fast, cost-effective for simple tasks
model: sonnet  # Balanced performance (default if omitted)
model: opus    # Maximum capability for complex reasoning
```

## Frontmatter Format

### Required Fields

```yaml
---
name: agent-name          # kebab-case, descriptive
description: One sentence  # <100 chars, clear purpose
tools: Read, Write, Edit   # Comma-separated (NOT array)
---
```

### Optional Fields

```yaml
---
name: agent-name
description: One sentence
model: sonnet              # Optional: haiku, sonnet, opus
tools: Read, Grep, Bash
---
```

### Common Mistakes

❌ **Array Syntax**:
```yaml
tools: [Read, Write, Edit]  # WRONG - don't use array syntax
```

✅ **Comma-Separated**:
```yaml
tools: Read, Write, Edit    # CORRECT - comma-separated string
```

❌ **Including Task**:
```yaml
tools: Read, Task           # WRONG - agents can't use Task
```

❌ **Including SlashCommand**:
```yaml
tools: SlashCommand         # WRONG - unavailable at runtime
```

## Agent Structure Template

```markdown
---
name: agent-name
description: One sentence description (<100 chars)
model: optional_model
tools: Tool1, Tool2, Tool3
---

# Agent Name

Purpose statement explaining what this agent does.

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons-learned`
2. **Record lesson** with:
   - Component: `{type: "agent", name: "{agent_name}", bundle: "{bundle}"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## Workflow

### Step 1: [First Action]
[Description of step]

### Step 2: [Second Action]
[Description of step]

[Additional steps...]

## Tool Usage

[Explanation of how each tool is used]

## Critical Rules

[List critical rules agent must follow]
```

## Best Practices

### 1. Clear Input/Output Contracts

Document what agent expects and produces:

```markdown
## Inputs
- `project_path`: Path to project root
- `file_pattern`: Pattern to match files (e.g., "**/*.java")

## Outputs
- JSON report with findings
- Exit code 0 on success, 1 on errors
```

### 2. Error Handling

Agents should handle errors gracefully:

```markdown
### Step 3: Analyze Files

Use Grep to find files. If no matches:
- Return empty results (not error)
- Log: "No files matching pattern found"
- Continue to reporting step
```

### 3. Tool Usage Documentation

Explain how tools are used:

```markdown
## Tool Usage

**Read**: Load configuration files and source code for analysis
**Grep**: Search for code patterns across project files
**Bash**: Execute git commands for repository info
```

### 4. Appropriate Granularity

**Too Granular** (creates too many agents):
```
- load-config-agent
- parse-config-agent
- validate-config-agent
```

**Good Granularity** (focused but complete):
```
- config-analyzer-agent (loads, parses, validates)
```

**Too Broad** (does too much):
```
- project-manager-agent (config, code, tests, docs, deploy)
```

## Examples

### Example 1: Analysis Agent

```yaml
---
name: code-quality-analyzer
description: Analyze code for quality issues and generate structured report
tools: Read, Grep, Glob
---

# Code Quality Analyzer Agent

Analyzes codebase for common quality issues including complexity, duplication, and style violations.

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons-learned`
2. **Record lesson** with:
   - Component: `{type: "agent", name: "code-quality-analyzer", bundle: "..."}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## Workflow

### Step 1: Scan Codebase
Use Glob to find all source files matching pattern

### Step 2: Analyze Each File
Read each file and check for:
- High complexity (functions >50 lines)
- Duplicated code blocks
- Style violations

### Step 3: Generate Report
Format findings as JSON with:
- File path
- Issue type
- Severity
- Line number
- Suggestion

## Tool Usage

**Glob**: Find source files by pattern
**Read**: Load file contents for analysis
**Grep**: Search for specific patterns

## Critical Rules

- Process all files, don't stop on first error
- Return empty results if no issues (not error)
- Always include file path and line number in findings
```

### Example 2: Execution Agent

```yaml
---
name: test-runner
description: Execute project test suite and report results
model: haiku
tools: Read, Bash
---

# Test Runner Agent

Executes test suite for project and reports pass/fail status with details.

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons-learned`
2. **Record lesson** with:
   - Component: `{type: "agent", name: "test-runner", bundle: "..."}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## Workflow

### Step 1: Detect Test Framework
Read project files to identify test framework (JUnit, Jest, etc.)

### Step 2: Execute Tests
Bash: Run appropriate test command based on framework

### Step 3: Parse Results
Parse test output for:
- Total tests run
- Passed/failed/skipped
- Failure details

### Step 4: Generate Report
Format as structured JSON

## Tool Usage

**Read**: Load project configuration
**Bash**: Execute test commands

## Critical Rules

- Capture both stdout and stderr
- Parse output for test framework-specific format
- Return structured results even if tests fail
- Include execution time in report
```

## Validation Checklist

Before creating agent, verify:

- [ ] Agent has single, focused purpose
- [ ] Name is kebab-case and descriptive
- [ ] Description is <100 chars
- [ ] Tools list is comma-separated (not array)
- [ ] No Task tool included
- [ ] If Bash tool: Not calling Maven (unless maven-builder)
- [ ] CONTINUOUS IMPROVEMENT RULE uses manage-lessons-learned skill
- [ ] Workflow has numbered steps
- [ ] Tool usage documented
- [ ] Critical rules specified
- [ ] Input/output contracts clear
- [ ] Error handling described

## Common Pitfalls

### Pitfall 1: Creating Orchestrators as Agents

❌ **Wrong**:
```yaml
name: project-builder
tools: Task  # Agent trying to orchestrate
```

✅ **Correct**: Create Command instead

### Pitfall 2: Including User Interaction

❌ **Wrong**:
```yaml
name: config-wizard
tools: AskUserQuestion  # Agent asking questions
```

✅ **Correct**: Create Command with wizard pattern

### Pitfall 3: Over-Tooling

❌ **Wrong**:
```yaml
tools: Read, Write, Edit, Glob, Grep, Bash, WebFetch, WebSearch
# Agent probably doesn't need all these
```

✅ **Correct**: Only list tools actually used

### Pitfall 4: Legacy Self-Update Pattern

❌ **Wrong**:
```markdown
## CONTINUOUS IMPROVEMENT RULE
**YOU MUST invoke `/plugin-update-agent`**
```

✅ **Correct**:
```markdown
## CONTINUOUS IMPROVEMENT RULE
If you discover issues or improvements during execution, record them:
1. Activate skill: plan-marshall:manage-lessons-learned
2. Record lesson with component info and category
```

## References

- Architecture Rules: See plugin-architecture skill
- Tool Selection: See diagnostic-patterns skill
- Agent Patterns: See plugin-architecture skill references
