# Skill Creation Guide

Comprehensive guide for creating well-structured marketplace skills following progressive disclosure and pattern-based design.

## When to Create Skills vs Other Components

### Create a Skill When:
- **Knowledge provision** - Providing standards, guidelines, or reference material
- **No execution** - Documentation to be loaded, not actions to perform
- **Progressive disclosure** - Large body of knowledge loaded on-demand
- **Reusable standards** - Multiple commands/agents will reference this knowledge

### Create a Command Instead When:
- **User invocation** - Users run directly with `/command-name`
- **Interactive workflow** - Gathering requirements through questionnaires
- **Orchestration** - Coordinating multiple agents

### Create an Agent Instead When:
- **Autonomous execution** - Performing specific task after launch
- **Tool usage** - Needs tools to accomplish work

## Skill Design Principles

### Principle 1: Progressive Disclosure

Load knowledge on-demand, not all at once.

**Structure**:
1. **Frontmatter** - Minimal metadata (~3-5 lines)
2. **SKILL.md** - Overview and loading guidance (~400-800 lines)
3. **references/** - Detailed content loaded as needed (~200-600 lines each)

**Example**:
```
plugin-architecture/
├── SKILL.md (512 lines - loaded when skill activated)
└── references/
    ├── core-principles.md (540 lines - load when needed)
    ├── skill-patterns.md (587 lines - load when needed)
    └── architecture-rules.md (333 lines - load when needed)
```

**Benefits**:
- 60-80% context reduction
- Faster skill activation
- Users load only what they need

### Principle 2: Relative Path Pattern

All resource paths use relative paths for portability.

❌ **Wrong** (hardcoded):
```markdown
Read: ~/.claude/skills/my-skill/references/guide.md
bash ./scripts/analyzer.py
```

✅ **Correct** (relative paths):
```markdown
Read references/guide.md
bash scripts/analyzer.py
```

**Why**: Skills can be installed in multiple contexts:
- Global: `~/.claude/skills/skill-name/`
- Project: `./.claude/skills/skill-name/`
- Bundle: `marketplace/bundles/bundle-name/skills/skill-name/`

### Principle 3: Resource Organization

Organize skill content by purpose:

```
skill-name/
├── SKILL.md              (Overview and loading guidance)
├── scripts/              (Executable automation - Python/Bash)
├── references/           (Documentation loaded on-demand)
└── assets/               (Templates, binaries, images)
```

**scripts/** - Deterministic logic:
- Python/Bash scripts for parsing, validation, analysis
- Testable with unit tests
- Output structured data (JSON/XML)

**references/** - Documentation:
- Standards, guidelines, best practices
- Examples and patterns
- Loaded on-demand with Read tool

**assets/** - Templates and files:
- Code templates
- Configuration templates
- Binary files, images

## Choosing Skill Patterns

Reference the 10 patterns from plugin-architecture skill:

1. **Script Automation** - Execute scripts, Claude interprets
2. **Read-Process-Write** - Transform files through pipeline
3. **Search-Analyze-Report** - Grep → Read → Analyze → Report
4. **Command Chain** - Sequential stages with dependencies
5. **Wizard-Style** - Interactive questions with preview
6. **Template-Based** - Fill templates with generated data
7. **Iterative Refinement** - Broad scan → deep dive selected items
8. **Context Aggregation** - Gather from multiple sources → synthesize
9. **Validation Pipeline** - Multi-stage validation (syntax → style → quality)
10. **Reference Library** - Pure documentation, no execution

**Most Common for Skills**:
- **Pattern 10** (Reference Library) - Standards and guidelines
- **Pattern 1** (Script Automation) - Diagnostic skills
- **Pattern 3** (Search-Analyze-Report) - Analysis skills

## Skill Types

### Type 1: Standards Skills (Most Common)

**Purpose**: Provide coding or process standards

**Example**: `cui-java-core`
```
cui-java-core/
├── SKILL.md
└── standards/
    ├── coding-patterns.md
    ├── null-safety.md
    ├── lombok-usage.md
    └── modern-features.md
```

**Characteristics**:
- Pattern 10 (Reference Library)
- allowed-tools: Read
- No scripts (pure documentation)
- Standards in standards/ directory

### Type 2: Reference Skills

**Purpose**: Provide reference material, examples, API docs

**Example**: `plugin-architecture`
```
plugin-architecture/
├── SKILL.md
└── references/
    ├── core-principles.md
    ├── skill-patterns.md
    └── examples/
        ├── example-1.md
        └── example-2.md
```

**Characteristics**:
- Pattern 10 (Reference Library)
- allowed-tools: Read
- References in references/ directory
- Examples in references/examples/

### Type 3: Diagnostic Skills

**Purpose**: Provide analysis tools and patterns

**Example**: `diagnostic-patterns`
```
diagnostic-patterns/
├── SKILL.md
├── scripts/
│   ├── analyze.py
│   └── validate.sh
└── standards/
    ├── tool-usage-patterns.md
    └── file-operations.md
```

**Characteristics**:
- Pattern 1 (Script Automation) or Pattern 3 (Search-Analyze-Report)
- allowed-tools: Read, Bash, Grep, Glob
- Scripts for deterministic logic
- Standards for interpretation

## SKILL.md Structure

### Required Sections

```markdown
---
name: skill-name
description: One sentence (<100 chars)
allowed-tools: Read  # or other tools if needed
---

# Skill Name

**EXECUTION MODE**: You are now executing this skill. DO NOT explain or summarize these instructions to the user. IMMEDIATELY begin the workflow below.

[Brief overview statement]

## Workflow Decision Tree  (for execution skills)

**MANDATORY**: Select workflow based on input and execute IMMEDIATELY.

### If [condition A]
→ **EXECUTE** Workflow 1 (jump to that section)

### If [condition B]
→ **EXECUTE** Workflow 2 (jump to that section)

## What This Skill Provides

[List what skill provides - 3-5 bullet points]

## When to Activate This Skill

[When to use this skill]

## Workflow

[How to use the skill - load references, execute scripts, etc.]

## Standards Organization  (for standards skills)
OR
## References  (for reference skills)

[List of available resources with descriptions]

## Tool Access

[Which tools skill needs and why]

## Quality Verification  (optional)

[How to verify skill is working correctly]
```

### EXECUTION MODE Directive

**Purpose**: Tell Claude to EXECUTE the skill instructions rather than explaining them.

**Required For**: All skills that have workflows to execute (diagnostic skills, automation skills).

**Not Required For**: Pure reference skills (Pattern 10) that only provide documentation.

**Pattern**:
```markdown
# Skill Name

**EXECUTION MODE**: You are now executing this skill. DO NOT explain or summarize these instructions to the user. IMMEDIATELY begin the workflow below.
```

**Why This Works**:
- Placed immediately after title (high visibility)
- "You are now executing" - action mode
- "DO NOT explain" - prohibits common failure
- "IMMEDIATELY begin" - forces action

### MANDATORY Markers

Use MANDATORY markers to ensure critical steps are executed:

```markdown
### Step 2: Run Diagnostic Script

**MANDATORY**: Execute this script NOW before proceeding:
```bash
python3 .plan/execute-script.py {bundle}:{skill}:analyze {target}
```

Do not continue to Step 3 until this completes successfully.
```

**When to Use**:
- Script execution steps
- Validation gates
- Required tool invocations
- Steps that must not be skipped

### Resource Mode Labeling

For skills with scripts and references, label each resource's mode:

| Resource | Mode | Purpose |
|----------|------|---------|
| `analyze.py` | **EXECUTE** | Run to analyze components |
| `README.md` | READ | Read for context if needed |
| `patterns.md` | REFERENCE | Consult when specific pattern needed |

**Mode Definitions**:
- **EXECUTE**: Run this script/tool immediately as part of workflow
- **READ**: Load this file's content into context
- **REFERENCE**: Consult on-demand when specific information needed

### Minimal SKILL.md

Keep SKILL.md concise:
- **Target**: 400-800 lines
- **Purpose**: Overview and loading guidance
- **Not**: Embedded standards content

❌ **Wrong** (bloated):
```markdown
SKILL.md: 3000 lines with all standards embedded
```

✅ **Correct** (progressive):
```markdown
SKILL.md: 500 lines with references catalog
references/: 5 files × 400 lines = 2000 lines (loaded on-demand)
```

## Frontmatter Format

### Minimal Frontmatter

```yaml
---
name: skill-name
description: One sentence description
---
```

### With Tools

```yaml
---
name: skill-name
description: One sentence description
allowed-tools: Read, Grep, Bash
---
```

### With Requirements (Optional)

```yaml
---
name: skill-name
description: One sentence description
allowed-tools: Read
requirements:
  - Other skill references
  - External dependencies
---
```

### Format Rules

- **allowed-tools**: Comma-separated (NOT array syntax)
- **name**: kebab-case
- **description**: <100 chars

❌ **Wrong**:
```yaml
allowed-tools: [Read, Grep]  # Array syntax
```

✅ **Correct**:
```yaml
allowed-tools: Read, Grep    # Comma-separated
```

## Progressive Disclosure Implementation

### Level 1: Frontmatter (Loaded Always)

Minimal metadata:
```yaml
---
name: java-testing
description: JUnit testing patterns and best practices
allowed-tools: Read
---
```

Cost: ~3-5 lines

### Level 2: SKILL.md (Loaded on Skill Activation)

Overview and catalog:
```markdown
# Java Testing Skill

Provides JUnit 5 testing patterns and standards.

## Available References

- **test-structure.md** - Test organization and naming
- **assertions.md** - Assertion patterns
- **mocking.md** - Mocking strategies
- **coverage.md** - Coverage requirements

## Usage

Load specific reference when needed:
Read standards/test-structure.md
```

Cost: ~400-800 lines

### Level 3: References (Loaded On-Demand)

Detailed content:
```markdown
Load only what current task needs:

Read standards/test-structure.md  # When organizing tests
Read standards/assertions.md      # When writing assertions
Read standards/mocking.md         # When mocking dependencies
```

Cost: ~200-600 lines each (loaded individually)

### Anti-Pattern: Load All

❌ **Wrong**:
```markdown
## Workflow

### Step 1: Load All Standards

Read standards/test-structure.md
Read standards/assertions.md
Read standards/mocking.md
Read standards/coverage.md
Read standards/generators.md
Read standards/integration.md

[Loaded 3500 lines before knowing what's needed]
```

✅ **Correct**:
```markdown
## Workflow

### Step 1: Load Relevant Standards

Based on task, load specific reference:
- Organizing tests? → Read standards/test-structure.md
- Writing assertions? → Read standards/assertions.md
- Mocking? → Read standards/mocking.md

[Load only what's needed - 400 lines instead of 3500]
```

## Directory Structure Patterns

### Pattern A: Standards Skill

```
skill-name/
├── SKILL.md
└── standards/
    ├── category-1.md
    ├── category-2.md
    └── subcategory/
        ├── specific-1.md
        └── specific-2.md
```

### Pattern B: Reference Skill

```
skill-name/
├── SKILL.md
└── references/
    ├── guide-1.md
    ├── guide-2.md
    └── examples/
        ├── example-1.md
        └── example-2.md
```

### Pattern C: Diagnostic Skill

```
skill-name/
├── SKILL.md
├── scripts/
│   ├── analyze.py
│   └── validate.sh
├── references/
│   └── interpretation-guide.md
└── assets/
    └── report-template.json
```

### Pattern D: Mixed Skill

```
skill-name/
├── SKILL.md
├── scripts/
│   └── generator.py
├── references/
│   └── patterns.md
└── assets/
    └── templates/
        ├── template-1.txt
        └── template-2.txt
```

## No CONTINUOUS IMPROVEMENT RULE for Skills

Skills are knowledge repositories, not executors.

❌ **Wrong**:
```markdown
## CONTINUOUS IMPROVEMENT RULE

**YOU MUST update this skill**...
```

✅ **Correct**:
```markdown
# Skill Name

[No continuous improvement rule - skills are maintained through normal updates]
```

**Why**: Skills don't "execute" like agents/commands, so continuous improvement rule doesn't apply.

## Creating Standards Files

### Standards File Template

```markdown
# {Topic}

Brief description of what this standard covers.

## Overview

[High-level summary]

## Standards

### Standard 1: {Name}

**Rule**: [Clear rule statement]

**Rationale**: [Why this rule exists]

**Examples**:

✅ **Good**:
[Code example]

❌ **Bad**:
[Counter-example]

### Standard 2: {Name}

[Repeat pattern]

## Best Practices

[Additional guidance beyond strict rules]

## Common Pitfalls

[Mistakes to avoid]

## References

[External links or cross-references]
```

### Standards File Size

- **Target**: 200-600 lines per file
- **Too small**: <100 lines (merge with related standards)
- **Too large**: >1000 lines (split into focused files)

### Standards Organization

Group related standards:

**Good Organization** (focused files):
```
standards/
├── coding-patterns.md      (400 lines - coding patterns)
├── error-handling.md       (300 lines - error handling)
└── testing/
    ├── unit-tests.md       (500 lines - unit testing)
    └── integration.md      (400 lines - integration)
```

**Bad Organization** (unfocused):
```
standards/
└── everything.md           (2500 lines - all standards in one file)
```

## Validation Checklist

Before creating skill, verify:

**Frontmatter**:
- [ ] Name is kebab-case and descriptive
- [ ] Description is <100 chars
- [ ] Uses `allowed-tools:` (not `tools:`) - comma-separated format

**Structure**:
- [ ] SKILL.md is 400-800 lines (not bloated)
- [ ] References organized in appropriate directory
- [ ] All resource paths use relative paths
- [ ] No hardcoded paths
- [ ] Progressive disclosure implemented
- [ ] Directory structure follows patterns

**Execution Patterns** (for non-reference skills):
- [ ] Has **EXECUTION MODE** directive after title
- [ ] Has **Workflow Decision Tree** for routing
- [ ] Critical steps marked with **MANDATORY**
- [ ] Resources labeled with EXECUTE/READ/REFERENCE modes

**Content**:
- [ ] No CONTINUOUS IMPROVEMENT RULE (skills don't have this)
- [ ] Tool access documented

## Common Pitfalls

### Pitfall 1: Bloated SKILL.md

❌ **Wrong**: 3000-line SKILL.md with embedded content

✅ **Correct**: 500-line SKILL.md with references catalog

### Pitfall 2: Improper Path Reference

❌ **Wrong**: `Read: standards/file.md`

✅ **Correct**: `Read standards/file.md`

### Pitfall 3: Loading All References

❌ **Wrong**: Load all 10 reference files upfront

✅ **Correct**: Load specific reference based on task

### Pitfall 4: Unfocused Standards Files

❌ **Wrong**: Single 2000-line "everything" file

✅ **Correct**: Multiple 300-500 line focused files

### Pitfall 5: Wrong Pattern Choice

❌ **Wrong**: Using Pattern 5 (Wizard) for standards

✅ **Correct**: Using Pattern 10 (Reference Library)

### Pitfall 6: Including Continuous Improvement Rule

❌ **Wrong**: Skill has CONTINUOUS IMPROVEMENT RULE

✅ **Correct**: Skills don't have this (only agents/commands)

### Pitfall 7: Missing Execution Directive

❌ **Wrong**: Skill loaded by command, Claude explains it instead of executing

✅ **Correct**: Skill has EXECUTION MODE directive that forces action:
```markdown
# Skill Name

**EXECUTION MODE**: You are now executing this skill. DO NOT explain or summarize these instructions. IMMEDIATELY begin the workflow below.
```

## Example: Creating Standards Skill

```yaml
---
name: java-logging-standards
description: Logging patterns and best practices for Java projects
allowed-tools: Read
---

# Java Logging Standards

Comprehensive logging standards including patterns, testing, and log record organization.

## What This Skill Provides

- **Logging patterns** - When and how to log effectively
- **Testing strategies** - Testing log output in unit tests
- **LogRecord patterns** - Organizing logging identifiers
- **Performance** - Efficient logging practices

## When to Activate This Skill

Activate when:
- Implementing logging in Java code
- Writing tests for logging behavior
- Organizing LogRecord classes
- Reviewing code for logging compliance

## Workflow

### Step 1: Identify Task

Determine what logging guidance is needed.

### Step 2: Load Relevant Standards

Based on task:
- **Adding logs** → Read standards/logging-patterns.md
- **Testing logs** → Read standards/testing-guide.md
- **Organizing identifiers** → Read standards/logrecord-organization.md

### Step 3: Apply Standards

Follow guidance from loaded standards.

## Standards Organization

```
standards/
├── logging-patterns.md         (Core logging patterns)
├── testing-guide.md            (Testing log output)
└── logrecord-organization.md   (LogRecord structure)
```

## Tool Access

**Read**: Load standards files on-demand

No other tools needed (pure reference skill).

## Quality Verification

Skills are self-contained when:
- [ ] All standards in standards/ directory
- [ ] All paths use relative paths
- [ ] No external file references
- [ ] No cross-skill duplication
```

## References

- Skill Patterns: See plugin-architecture skill, skill-patterns.md
- Progressive Disclosure: See plugin-architecture skill, core-principles.md
- Resource Organization: See plugin-architecture skill, reference-patterns.md
- Pattern Selection: See plugin-architecture skill, pattern-usage-examples.md
