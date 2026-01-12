# Skill Design Principles

Workflow-focused design principles for building goal-based skills.

## Core Concept: Workflows Over Monolithic Operations

**Principle**: Skills provide **workflows** (specific capabilities) not monolithic operations. Multiple workflows serve a single goal.

**Example**:
```markdown
# ❌ BAD: Monolithic skill
Skill: analyze-everything
  - Analyzes agents, commands, skills, metadata, scripts all in one workflow

# ✅ GOOD: Workflow-based skill
Skill: plugin-diagnose
  - Workflow 1: analyze-component (single component)
  - Workflow 2: analyze-all-of-type (all components of one type)
  - Workflow 3: validate-marketplace (complete marketplace)
  - Workflow 4: validate-references (reference compliance)
  - Workflow 5: detect-duplication (cross-component analysis)
```

## Single-Workflow vs Multi-Workflow Skills

### Single-Workflow Skills

**When to Use**:
- Simple, focused capability
- No variations in execution
- Single pattern implementation

**Structure**:
```markdown
---
name: simple-formatter
description: Formats files using specific rules
allowed-tools: [Read, Write, Edit]
---

# Simple Formatter

## Workflow

Step 1: Read input file
Step 2: Apply formatting rules
Step 3: Write formatted output
```

**Examples**:
- Pattern 10 (Reference Library) - single purpose: provide references
- Pattern 2 (Read-Process-Write) - single linear workflow

### Multi-Workflow Skills

**When to Use**:
- Multiple related capabilities
- Different execution paths for same goal
- Complex operations with variants

**Structure**:
```markdown
---
name: plugin-diagnose
description: Find and understand quality issues in marketplace components
allowed-tools: [Read, Bash, Glob, Grep, Skill]
---

# Plugin Diagnose Skill

## Workflows

### Workflow 1: analyze-component
Analyzes single component for quality issues.
[Workflow details]

### Workflow 2: analyze-all-of-type
Analyzes all components of specific type.
[Workflow details]

### Workflow 3: validate-marketplace
Complete marketplace health check.
[Workflow details]
```

**Examples**:
- Pattern 1 (Script Automation) - multiple scripts for different analysis types
- Pattern 3 (Search-Analyze-Report) - different search patterns, analysis criteria
- Pattern 5 (Wizard-Style) - different templates, validation rules

## Workflow Parameter Design

### Input Parameters

**Define clearly** what each workflow needs:

```markdown
### Workflow: analyze-component

**Input Parameters**:
- `component_path`: Absolute path to component file (required)
- `component_type`: "agent" | "command" | "skill" (required)
- `standards_preloaded`: Boolean, true if standards already loaded (optional)

**Process**:
[Workflow steps]

**Output**:
Structured quality report with issues categorized by severity
```

### Parameter Patterns

**Required vs Optional**:
```markdown
- `file_path` (required) - Must be provided
- `output_format` (optional, default: "json") - Has sensible default
- `verbose` (optional, default: false) - Boolean flag
```

**Type Specifications**:
```markdown
- `component_type`: "agent" | "command" | "skill" - Enum values
- `severity_filter`: ["high", "medium", "low"] - Array of values
- `max_results`: Integer, 1-1000 - Constrained number
```

## Conditional Workflow Selection

**Pattern**: Let commands/users choose workflow based on their needs.

### Implicit Selection (by parameters)

```markdown
## Determining Workflow

If `component_path` provided:
  → Use workflow: analyze-component

If `component_type` provided without path:
  → Use workflow: analyze-all-of-type

If neither provided:
  → Use workflow: validate-marketplace
```

### Explicit Selection (by name)

```markdown
# Command specifies workflow explicitly
Skill: plugin-diagnose
Workflow: analyze-component
Parameters: {component_path: "...", component_type: "agent"}
```

## Workflow Composition Patterns

### Sequential Composition

**Pattern**: One workflow's output feeds into another.

```markdown
Workflow 1: scan-inventory (conceptual)
  Output: List of components
  # Actual: plan-marshall:marketplace-inventory:scan-marketplace-inventory

Workflow 2: analyze-component
  Input: Component from Workflow 1
  Output: Analysis results

# Command composes them:
1. Invoke scan-inventory → get list
2. For each component: invoke analyze-component
3. Aggregate results
```

### Parallel Composition

**Pattern**: Multiple workflows execute independently, results combined.

```markdown
Workflow 1: validate-format
Workflow 2: validate-links
Workflow 3: validate-content

# Command invokes all in parallel:
Results = [
  invoke validate-format,
  invoke validate-links,
  invoke validate-content
]
Combine results into final report
```

### Hierarchical Composition

**Pattern**: Top-level workflow delegates to sub-workflows.

```markdown
Workflow: validate-marketplace
  Step 1: Invoke validate-format (all components)
  Step 2: Invoke validate-links (all components)
  Step 3: Invoke detect-duplication (cross-component)
  Step 4: Aggregate all results
```

## Progressive Disclosure in Workflows

### Workflow-Level Loading

```markdown
## Workflow 1: basic-analysis

Step 1: Load core standards
Read references/core-standards.md

[Basic analysis steps]

## Workflow 2: deep-analysis

Step 1: Load core standards
Read references/core-standards.md

Step 2: Load detailed patterns
Read references/advanced-patterns.md

[Detailed analysis steps]
```

**Benefit**: Workflow 1 only loads what it needs, Workflow 2 loads more.

### Step-Level Loading

```markdown
## Workflow: comprehensive-analysis

Step 1: Quick Scan
[Fast, lightweight scan]

Step 2: Load Details for Issues
If issues found in Step 1:
  Read references/detailed-patterns.md

Step 3: Deep Analysis
[Only executes if Step 1 found issues]
```

**Benefit**: Detailed patterns only load if needed.

## Workflow Quality Standards

### Clear Purpose

**Each workflow should have**:
- Single, well-defined purpose
- Clear input/output contract
- Documented when to use

**Example**:
```markdown
### Workflow: analyze-component

**Purpose**: Analyze a single component for quality issues

**When to Use**:
- Validating newly created component
- Analyzing specific component after changes
- Investigating reported issues in component

**When NOT to Use**:
- Analyzing multiple components (use analyze-all-of-type)
- Complete marketplace health (use validate-marketplace)
```

### Focused Scope

**Avoid**:
```markdown
# ❌ Workflow trying to do too much
Workflow: do-everything
  - Analyzes component
  - Fixes all issues
  - Generates documentation
  - Runs tests
  - Commits changes
```

**Prefer**:
```markdown
# ✅ Focused workflows
Workflow 1: analyze-component (analysis only)
Workflow 2: fix-issues (fixing only, separate skill)
Workflow 3: generate-docs (documentation only, separate skill)
```

### Testability

**Design workflows to be testable**:

```markdown
## Workflow: validate-format

**Test Cases**:
- Valid component → Returns clean status
- Missing frontmatter → Returns error with specific message
- Invalid YAML → Returns parse error
- Missing sections → Returns list of missing sections
```

## Workflow Documentation Template

```markdown
### Workflow: workflow-name

**Purpose**: One-sentence description of what this workflow does

**When to Use**:
- Specific scenario 1
- Specific scenario 2

**Input Parameters**:
- `param1` (required): Description and type
- `param2` (optional, default: value): Description and type

**Process**:
1. Step 1 description
   ```
   Commands or pseudo-code
   ```
2. Step 2 description
3. Step 3 description

**Output**: Description of return value/result

**Example**:
```
Skill: skill-name
Workflow: workflow-name
Parameters: {param1: "value", param2: "value"}
```
```

## Skill Composition

### Skills Invoking Other Skills

**Pattern**: Skills can load other skills for prerequisites.

```markdown
## Workflow: analyze-java-code

Step 1: Load Architecture Principles
Skill: pm-plugin-development:plugin-architecture

Step 2: Load Java Standards
Skill: pm-dev-java:java-core

Step 3: Apply Standards
[Analysis using loaded standards]
```

**Benefits**:
- Reuse existing knowledge
- Avoid duplication
- Stay up-to-date with standard changes

### Avoiding Circular Dependencies

**Rule**: Skills should not circularly depend on each other.

```markdown
# ❌ BAD: Circular dependency
Skill A loads Skill B
Skill B loads Skill A

# ✅ GOOD: Linear dependency
Skill A loads Skill B (foundation)
Skill C loads both A and B
```

## Best Practices Summary

**1. Design for Workflows**:
- Multiple focused workflows, not monolithic operations
- Clear purpose per workflow
- Well-defined input/output contracts

**2. Parameter Design**:
- Required vs optional clearly marked
- Type specifications provided
- Sensible defaults where applicable

**3. Composition**:
- Sequential, parallel, or hierarchical as needed
- Workflows compose to build complex capabilities
- Avoid circular dependencies

**4. Progressive Disclosure**:
- Load references at workflow level or step level
- Only load what's needed for current execution
- Minimize upfront context usage

**5. Quality**:
- Each workflow is testable
- Clear documentation
- Focused scope per workflow

**6. Skill Composition**:
- Invoke other skills for prerequisites
- Avoid duplication of knowledge
- Build on foundation skills

## Examples

### Example 1: Single-Workflow Skill (Pattern 10)

```markdown
---
name: plugin-architecture
description: Architecture principles and patterns for marketplace components
allowed-tools: [Read]
---

# Plugin Architecture Skill

## Workflow

This skill provides reference material only. No execution.

Load specific reference when needed:
- Read references/core-principles.md
- Read references/skill-patterns.md
- Read references/goal-based-organization.md

Never load all references at once. Load only what's needed for current task.
```

### Example 2: Multi-Workflow Skill (Pattern 3)

```markdown
---
name: plugin-diagnose
description: Find and understand quality issues in marketplace components
allowed-tools: [Read, Bash, Glob, Grep, Skill]
---

# Plugin Diagnose Skill

## Workflows

### Workflow 1: analyze-component
**Input**: component_path, component_type
**Output**: Quality report for single component
[Detailed workflow steps]

### Workflow 2: analyze-all-of-type
**Input**: component_type, scope
**Output**: Aggregated report for all components of type
[Detailed workflow steps]

### Workflow 3: validate-marketplace
**Input**: None
**Output**: Complete marketplace health report
[Detailed workflow steps]
```

## Related References

- Core Principles: references/core-principles.md
- Skill Patterns: references/skill-patterns.md
- Command Design: references/command-design.md
