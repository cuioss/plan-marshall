# Skill Quality Standards

Comprehensive quality standards for marketplace skills including structure validation, progressive disclosure patterns, and standards file quality (minimize-without-loss principle).

## Overview

Skills are knowledge repositories that provide standards, workflows, and reusable logic. They are invoked via Skill tool by commands, agents, or other skills.

**Key Characteristics**:
- Invoked via `Skill: bundle:skill-name`
- Contain SKILL.md with frontmatter and workflows
- May include external resources (scripts/, references/, assets/)
- Support progressive disclosure (load resources on-demand)
- Use relative paths for portable resource paths

## Skill Directory Structure

**Standard structure**:
```
skill-name/
├── SKILL.md              (Required: main skill file with frontmatter and workflows)
├── scripts/              (Optional: executable scripts for deterministic logic)
│   ├── script1.sh
│   └── script2.py
├── references/           (Optional: lookup material - WHAT rules to apply)
│   ├── guide1.md
│   └── guide2.md
├── workflows/            (Optional: operational procedures - HOW to execute)
│   ├── process1.md
│   └── process2.md
├── templates/            (Optional: output templates for generation)
│   └── template1.adoc
└── assets/               (Optional: images, diagrams, other files)
    └── diagram.png
```

**Required**:
- `SKILL.md`: Main skill file (MUST exist)

**Optional but Recommended**:
- `scripts/`: Deterministic validation logic (stdlib-only)
- `references/`: Lookup material, standards, rules (progressive disclosure)
- `workflows/`: Operational procedures, step-by-step guides
- `templates/`: Output templates for document generation
- `assets/`: Supporting files (images, diagrams)

### Content Organization Principle

**Each directory serves ONE purpose**:

| Directory | Purpose | Content Type |
|-----------|---------|--------------|
| `references/` | WHAT rules to apply | Criteria, standards, patterns |
| `workflows/` | HOW to execute | Procedures, steps, decision trees |
| `templates/` | Output structures | Boilerplate with placeholders |

**Avoid mixing content types** within a single directory. If `standards/` contains both rules AND procedures, split into `references/` and `workflows/`.

Use `doctor-skill-content` workflow to analyze and reorganize skill content.

## SKILL.md Frontmatter

**Required Structure**:
```yaml
---
name: skill-name
description: Clear, concise description of skill purpose
allowed-tools: Read, Bash, Glob, Grep, Skill
---
```

**Required Fields**:
- `name`: Skill identifier (kebab-case, matches directory name)
- `description`: One-sentence purpose statement
- `allowed-tools`: Comma-separated list of tools (note: comma-separated, NOT array like agents)

**Common Errors**:
- ❌ `allowed-tools: ["Read", "Write"]` (array format - wrong for skills)
- ✅ `allowed-tools: Read, Write, Glob, Grep` (comma-separated string)
- ❌ Missing frontmatter (first line not `---`)
- ❌ Invalid YAML (missing colons, incorrect indentation)

**Validation**:
```bash
Bash: scripts/analyze-skill-structure.sh {skill_dir}
# Check: skill_md.exists = true
# Check: skill_md.yaml_valid = true
```

## Progressive Disclosure Pattern

**CRITICAL**: Skills MUST use progressive disclosure to minimize context usage.

### The Problem

**Without Progressive Disclosure**:
```yaml
# SKILL.md loads all references upfront:
Read references/standard1.md    # 500 lines
Read references/standard2.md    # 500 lines
Read references/standard3.md    # 500 lines
Read references/standard4.md    # 500 lines
Read references/standard5.md    # 500 lines
# Total: 2,500 lines loaded immediately
```

**Problem**: Massive context usage, most content not needed for current task.

### The Solution

**With Progressive Disclosure**:
```markdown
## Workflow 1: Diagnose Agents

### Step 2: Load Agents Standards (Progressive Disclosure)

Read references/agents-guide.md  # 500 lines, ONLY for this workflow

## Workflow 2: Diagnose Commands

### Step 2: Load Commands Standards (Progressive Disclosure)

Read references/commands-guide.md  # 500 lines, ONLY for this workflow
```

**Benefit**: ~1,300 lines loaded per workflow (SKILL.md + ONE reference) instead of 3,300 lines (SKILL.md + ALL references).

### Implementation Pattern

**SKILL.md Structure**:
```markdown
---
name: my-skill
description: Multi-workflow skill with progressive disclosure
allowed-tools: Read, Bash, Grep
---

# My Skill

## Purpose

[Overall purpose]

## Progressive Disclosure Strategy

**3-Level Loading**:
1. Frontmatter (~3 lines)
2. SKILL.md (~800 lines)
3. Reference Guide (ONE per workflow, ~500 lines)

**Key Principle**: NEVER load all references at once.

## Workflow 1: First Task

### Step 1: Load Prerequisites

Skill: plan-marshall:ref-development-standards

### Step 2: Load Standards (Progressive Disclosure)

Read references/first-guide.md  # ONLY for Workflow 1

### Step 3-10: Execute Workflow

[Workflow logic]

## Workflow 2: Second Task

### Step 1: Load Prerequisites

[Same or different skills]

### Step 2: Load Standards (Progressive Disclosure)

Read references/second-guide.md  # ONLY for Workflow 2

### Step 3-10: Execute Workflow

[Workflow logic]
```

### Reference Guide Size Targets

**Optimal size**: 400-600 lines per reference

**Why?**
- Small enough to load on-demand without overwhelming context
- Large enough to contain comprehensive standards
- Combined with SKILL.md (~800 lines) = ~1,300 total lines per workflow

**Example**:
- agents-guide.md: ~500 lines
- commands-guide.md: ~500 lines
- skills-guide.md: ~500 lines
- metadata-guide.md: ~400 lines
- script-standards.md: ~600 lines (in plugin-architecture)

Total: ~2,500 lines across 5 guides, but only ONE loaded per workflow.

## Relative Path Pattern

**CRITICAL**: Skills MUST use relative paths for all internal resource references.

### Why Relative Paths?

**Portability**: Skills can be:
- Installed in marketplace: `marketplace/bundles/{bundle}/skills/{skill}`
- Installed globally: `~/.claude/skills/{skill}`
- Installed in project: `.claude/skills/{skill}`

Relative paths resolve from the skill directory regardless of installation location.

### Usage

**Scripts**:
```bash
Bash: python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:analyze {file_path}
Bash: python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:analyze validate-refs {component}
```

**References**:
```markdown
Read references/coding-standards.md
```

**Assets**:
```markdown
See architecture diagram: assets/architecture.png
```

### Prohibited Patterns

**❌ Absolute paths**:
```bash
# Bad - breaks portability
Bash: /Users/oliver/git/project/scripts/script.sh
Bash: ~/scripts/script.sh
```

**❌ Relative paths traversing outside skill**:
```bash
# Bad - breaks portability
Bash: ../../../../scripts/script.sh
```

**❌ Hardcoded installation paths**:
```bash
# Bad - assumes marketplace installation
Bash: marketplace/bundles/my-bundle/skills/my-skill/scripts/script.sh
```

**✅ Correct**: Use relative paths:
```bash
Bash: scripts/script.sh
```

## Structure Score

**Scoring Formula**:
```
structure_score = 0-100 based on:
- SKILL.md exists: +30 points (critical)
- YAML valid: +20 points
- No missing files (referenced but don't exist): +25 points
- No unreferenced files (exist but not referenced): +25 points

Perfect score: 100 (all criteria met)
```

**Thresholds**:
- **Excellent**: >= 90 (high quality)
- **Good**: >= 70 (acceptable with minor issues)
- **Needs improvement**: >= 50 (significant issues)
- **Poor**: < 50 (major problems)

**Target**: 100 (perfect structure)

### Missing Files (Critical Issue)

**Definition**: Files referenced in SKILL.md that don't exist.

**Detection**:
```bash
Bash: scripts/analyze-skill-structure.sh {skill_dir}
# Check: standards_files.missing_files array
```

**Example**:
```markdown
# SKILL.md references:
Read references/guide1.md
Bash: scripts/script1.sh

# But these files don't exist:
skill-dir/references/guide1.md  # ❌ Missing
skill-dir/scripts/script1.sh    # ❌ Missing
```

**Impact**: -25 points per missing file

**Fix**: Create missing files or remove references from SKILL.md

### Unreferenced Files (Minor Issue)

**Definition**: Files exist in skill directory but not referenced in SKILL.md.

**Detection**:
```bash
Bash: scripts/analyze-skill-structure.sh {skill_dir}
# Check: standards_files.unreferenced_files array
```

**Example**:
```
# Files exist:
skill-dir/scripts/unused-script.sh
skill-dir/references/old-guide.md

# But SKILL.md doesn't reference them
```

**Impact**: -10 points per unreferenced file

**Fix**:
- **Option 1**: Add references to SKILL.md (if files should be used)
- **Option 2**: Delete files (if obsolete)

## Standards File Quality (Minimize-Without-Loss Principle)

**CRITICAL**: Skills with standards files MUST follow minimize-without-loss principle.

### The Principle

**Minimize content WITHOUT losing information value.**

Remove:
- ✅ Zero-information content (fluff, filler, platitudes)
- ✅ Duplication (repeated information)
- ✅ Ambiguity (vague statements without specifics)
- ✅ Poor formatting (inconsistent structure)

Preserve:
- ✅ Actionable guidance
- ✅ Specific requirements
- ✅ Clear examples
- ✅ Technical specifications

### Zero-Information Content

**What to Remove**:

**Generic platitudes**:
- "It is important to..."
- "Best practice suggests..."
- "You should always..."
- "Don't forget to..."

**Filler phrases**:
- "As we all know..."
- "It goes without saying..."
- "Obviously..."
- "Needless to say..."

**Excessive motivation**:
- "This is crucial for success..."
- "This will make your code better..."
- "Following this advice will help you..."

**Example Refactoring**:

**Before** (zero-information content):
```markdown
It is important to always use descriptive variable names in your code.
This is a best practice that will make your code more readable and
maintainable. You should never use single-letter variable names except
for loop counters. Following this advice will help you write better code.
```

**After** (information preserved, fluff removed):
```markdown
**Naming**: Use descriptive variable names. Exception: single letters for loop counters.
```

### Duplication

**What to Remove**:

**Repeated statements**:
```markdown
# ❌ Before
## Section 1
Use descriptive names for variables.

## Section 2
Remember to use descriptive names for variables.

## Section 3
Variable names should be descriptive.
```

**After** (consolidated):
```markdown
## Naming Standards
- Variables: descriptive names (camelCase)
- Functions: verb + noun (camelCase)
- Classes: PascalCase
```

**Cross-file duplication**:
- If multiple skills have same standards → extract to shared skill
- Use `Skill: shared-bundle:shared-skill` dependency

### Ambiguity

**What to Remove/Clarify**:

**Vague statements**:
```markdown
# ❌ Vague
Code should be clean and maintainable.
Use appropriate error handling.
Follow best practices.
```

**Specific requirements**:
```markdown
# ✅ Specific
- Functions: < 50 lines (split if exceeded)
- Error handling: try-catch for I/O operations, throw custom exceptions for business logic
- Naming: PascalCase for classes, camelCase for methods
```

**Ambiguous qualifiers**:
- ❌ "usually", "often", "sometimes", "in most cases"
- ✅ "MUST", "SHOULD", "MAY" (RFC 2119 keywords)

### Formatting Issues

**What to Fix**:

**Inconsistent structure**:
```markdown
# ❌ Inconsistent
## Rule 1
Use descriptive names

Rule 2: Avoid magic numbers

### Third rule
Functions should be small
```

**Consistent structure**:
```markdown
# ✅ Consistent
## Rule 1: Descriptive Names
Use descriptive names for all identifiers.

## Rule 2: No Magic Numbers
Define constants for all magic numbers.

## Rule 3: Small Functions
Functions should be < 50 lines.
```

**Inconsistent examples**:
```markdown
# ❌ Inconsistent
Good: `const MAX_SIZE = 100;`
Bad: MAX_SIZE = 100
```

**Consistent examples**:
```markdown
# ✅ Consistent
✅ `const MAX_SIZE = 100;`
❌ `MAX_SIZE = 100`  (missing const)
```

## Integrated Standards Coherence

**CRITICAL**: Skills with multiple standards files MUST ensure coherence (no conflicts, gaps, inconsistencies).

### Conflicts

**What to Detect**:

**Contradictory requirements**:
```markdown
# File A:
Functions MUST be < 50 lines.

# File B:
Functions SHOULD be < 100 lines.

# ❌ Conflict: Different thresholds
```

**Fix**: Consolidate to single threshold, cross-reference if context-dependent.

### Gaps

**What to Detect**:

**Missing coverage**:
```markdown
# Standards files cover:
- Naming conventions ✅
- Error handling ✅
- [GAP: No testing standards]
- Documentation ✅
```

**Fix**: Add missing standards file or section.

### Inconsistencies

**What to Detect**:

**Terminology inconsistencies**:
```markdown
# File A: "unit test"
# File B: "unit-test"
# File C: "unittest"

# ❌ Inconsistent terminology
```

**Fix**: Standardize terminology across all files.

## Cross-Skill Duplication Detection

**CRITICAL**: Optional O(n²) analysis to detect duplication BETWEEN skills.

**When to Run**: Only when `--check-cross-duplication` flag provided (expensive operation).

### Detection Algorithm

**Pairwise Comparison**:
```
For each skill A:
  For each skill B (where B != A):
    Load SKILL.md from both
    Extract content sections
    Compare sections for duplication (LCS algorithm or similarity scoring)
    If duplication > threshold (e.g., 100 characters):
      Report duplicated content block
      Suggest consolidation
```

**Output**:
```
Cross-Skill Duplication Report

Skill Pair: pm-dev-java:java-core ↔ pm-dev-java:java-cdi

Duplicated Content (127 characters):
- Section: "Logging Standards"
  - Both skills contain identical logging requirements
  - Recommendation: Extract to shared pm-dev-java-cui:cui-logging skill

Skill Pair: pm-dev-frontend:cui-javascript ↔ pm-dev-frontend:cui-cypress

Duplicated Content (213 characters):
- Section: "Test Organization"
  - Similar test organization guidance in both
  - Recommendation: Move to shared pm-dev-frontend:cui-testing-common skill
```

### Consolidation Strategies

**Option 1: Extract to Shared Skill**
```markdown
# Before: Duplication in skill A and skill B

# After: Shared skill
Skills A and B both use:
Skill: bundle:shared-skill
```

**Option 2: Move to Reference Guide**
```markdown
# Before: Embedded in multiple skills

# After: External reference
Both skills load:
Read references/shared-standards.md
```

**Option 3: Cross-Reference**
```markdown
# Skill A: Primary definition
[Full standards content]

# Skill B: Cross-reference
For standards details, see:
Skill: bundle:skill-a
```

## Script Documentation Requirements

**CRITICAL**: Skills with scripts MUST document them in SKILL.md.

### Required Documentation

**For Each Script**:
1. **Purpose**: What the script does
2. **Input**: Parameters and format
3. **Output**: Return format (usually JSON)
4. **Usage**: How to invoke from SKILL.md

**Example**:
```markdown
## External Resources

### Scripts (in scripts/)

**1. analyze-structure.sh**: Analyzes file structure and bloat
- **Input**: file path, component type (agent|command|skill)
- **Output**: JSON with structural analysis
- **Usage**:
  ```bash
  Bash: python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:analyze {file_path} agent
  ```

**2. validate-references.py**: Validates plugin references (Python)
- **Input**: component path
- **Output**: JSON with detected references and pre-filter statistics
- **Usage**:
  ```bash
  Bash: python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:analyze validate-references {component_path}
  ```
```

### Script Standards

**All scripts MUST**:
- Be stdlib-only (no external dependencies)
- Have executable permissions (`chmod +x`)
- Support `--help` flag (print usage)
- Output JSON format (for machine parsing)
- Handle errors gracefully (exit codes, error messages)

## Skill Patterns

### Pattern 1: Multi-Workflow Skill

**Use Case**: Single skill with multiple related workflows.

**Structure**:
```markdown
---
name: multi-workflow-skill
description: Skill with multiple related workflows
allowed-tools: Read, Bash, Grep, Skill
---

# Multi-Workflow Skill

## Workflow 1: First Task
[Workflow with progressive disclosure]

## Workflow 2: Second Task
[Workflow with progressive disclosure]

## Workflow 3: Third Task
[Workflow with progressive disclosure]
```

**Example**: plugin-diagnose skill (5 workflows: agents, commands, skills, metadata, scripts)

### Pattern 2: Reference Library Skill

**Use Case**: Pure reference skill with no execution logic.

**Structure**:
```markdown
---
name: reference-library
description: Reference library with architectural patterns
allowed-tools: Read
---

# Reference Library

## Purpose
Provides comprehensive reference documentation (no execution logic).

## References
- references/pattern1.md
- references/pattern2.md
- [10 reference files]
```

**Example**: plugin-architecture skill (9 reference documents, no workflows)

### Pattern 3: Script Automation Skill

**Use Case**: Skill providing deterministic validation via scripts.

**Structure**:
```markdown
---
name: script-automation
description: Deterministic validation via scripts
allowed-tools: Bash, Read
---

# Script Automation

## Purpose
Provides validation scripts for deterministic checks.

## Workflow: Validate Component

### Step 1: Run Validation Script
Bash: scripts/validate.sh {component_path}

### Step 2: Parse Results
[Parse JSON output and categorize issues]
```

**Example**: plugin-create skill (2 scripts: validate-component.py, generate-frontmatter.py)

### Pattern 4: Standards Skill

**Use Case**: Comprehensive standards documentation with progressive disclosure.

**Structure**:
```markdown
---
name: standards-skill
description: Comprehensive standards with progressive disclosure
allowed-tools: Read, Skill
---

# Standards Skill

## Standards Categories

### Category 1: Core Standards
Read references/core-standards.md

### Category 2: Advanced Standards
Read references/advanced-standards.md
```

**Example**: cui-java-core skill (Java core development standards)

## Common Issues and Fixes

### Issue 1: Missing SKILL.md

**Symptoms**:
- Structure score = 0
- skill_md.exists = false

**Diagnosis**:
```bash
Bash: scripts/analyze-skill-structure.sh {skill_dir}
# Check: skill_md.exists = false
```

**Fix**:
Create SKILL.md with proper frontmatter and content.

### Issue 2: Invalid YAML Frontmatter

**Symptoms**:
- Structure score = 30
- skill_md.yaml_valid = false

**Diagnosis**:
```bash
Bash: scripts/analyze-skill-structure.sh {skill_dir}
# Check: skill_md.yaml_valid = false
```

**Fix**:
Correct YAML syntax:
- Check for missing colons
- Fix indentation
- Verify frontmatter delimiters (`---`)

### Issue 3: Low Structure Score (<70)

**Symptoms**:
- Missing files (referenced but don't exist)
- Unreferenced files (exist but not referenced)

**Diagnosis**:
```bash
Bash: scripts/analyze-skill-structure.sh {skill_dir}
# Check: standards_files.missing_files array
# Check: standards_files.unreferenced_files array
```

**Fix**:
- Create missing files or remove references
- Add unreferenced files to SKILL.md or delete them

### Issue 4: No Progressive Disclosure

**Symptoms**:
- All references loaded upfront in SKILL.md
- No "Progressive Disclosure" section
- Context usage excessive

**Diagnosis**:
Manual review of SKILL.md:
- Check if all Read references/* at top
- Check if workflows load specific references

**Fix**:
Refactor to progressive disclosure pattern (see Progressive Disclosure section).

### Issue 5: Absolute Paths

**Symptoms**:
- References use absolute paths
- Scripts hardcoded to specific installation location

**Diagnosis**:
```bash
Bash: python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:analyze validate-references {skill_dir}/SKILL.md
# Check for absolute paths in references array
```

**Fix**:
Use relative paths instead of absolute paths:
- ❌ `/Users/oliver/git/project/scripts/script.sh`
- ✅ `scripts/script.sh`

## Summary Checklist

**Before marking skill as "quality approved"**:
- ✅ SKILL.md exists with valid YAML frontmatter
- ✅ Structure score >= 90 (Excellent)
- ✅ No missing files (all referenced files exist)
- ✅ No unreferenced files (all files referenced or removed)
- ✅ Progressive disclosure implemented (references loaded on-demand)
- ✅ Relative paths used for all internal references
- ✅ Scripts documented in SKILL.md (if any)
- ✅ Scripts executable with --help support (if any)
- ✅ Standards file quality follows minimize-without-loss principle
- ✅ No cross-skill duplication (if --check-cross-duplication ran)
- ✅ Integrated standards coherence (no conflicts, gaps, inconsistencies)
- ✅ Clear workflow structure with step-by-step logic
- ✅ External resources properly referenced (scripts/, references/, assets/)
