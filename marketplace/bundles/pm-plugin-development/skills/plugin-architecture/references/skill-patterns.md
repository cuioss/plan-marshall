# Common Skill Patterns

Source: [Claude Skills Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)

This document catalogs common skill patterns to guide implementation. Reference the pattern type when designing new skills.

## Pattern 1: Script Automation

**Description**: Execute deterministic logic in Python/Bash scripts while Claude processes results.

**When to Use**:
- Complex parsing or analysis logic
- File system operations
- Data transformation
- Validation checks
- Report generation

**Structure**:
```
skill-name/
├── SKILL.md
├── scripts/
│   ├── analyzer.py       (deterministic logic)
│   └── validator.sh      (validation checks)
└── references/
    └── interpretation-guide.md
```

**SKILL.md Pattern**:
```markdown
## Step 1: Analyze Input
bash scripts/analyzer.py {input_file}

## Step 2: Interpret Results
The script outputs JSON with this structure:
{
  "status": "success",
  "findings": [...],
  "metrics": {...}
}

Apply the following interpretation rules:
- Load detailed rules: Read references/interpretation-guide.md
```

**Key Characteristics**:
- Scripts output structured data (JSON/XML)
- Claude interprets and acts on script output
- Clear separation: logic (script) vs orchestration (Claude)
- Scripts are testable with standard unit tests

**Examples**:
- Code analyzers
- File structure validators
- Inventory scanners
- Metric collectors

## Pattern 2: Read-Process-Write

**Description**: Transform files following specifications through a simple input-output pipeline.

**When to Use**:
- File transformations
- Format conversions
- Code generation
- Documentation updates

**Structure**:
```
skill-name/
├── SKILL.md
├── scripts/
│   └── transform.py      (optional - for complex transforms)
└── assets/
    └── template.txt      (output template)
```

**SKILL.md Pattern**:
```markdown
## Step 1: Read Input
Read {input_file}

## Step 2: Process Content
Apply transformations:
1. Extract key sections
2. Apply formatting rules
3. Generate new content

## Step 3: Write Output
Load template: Read assets/template.txt
Fill template with processed content
Write to {output_file}
```

**Key Characteristics**:
- Linear workflow: read → process → write
- Templates in assets/ for consistent output
- Processing logic can be in SKILL.md or scripts
- Single input, single output

**Examples**:
- Markdown to AsciiDoc converters
- Code formatters
- Documentation generators
- Configuration file creators

## Pattern 3: Search-Analyze-Report

**Description**: Use Grep to find patterns, read matching files, analyze findings, generate structured output.

**When to Use**:
- Codebase analysis
- Quality audits
- Pattern detection
- Compliance checking

**Structure**:
```
skill-name/
├── SKILL.md
├── scripts/
│   └── aggregate-findings.py
├── references/
│   └── analysis-criteria.md
└── assets/
    └── report-template.json
```

**SKILL.md Pattern**:
```markdown
## Step 1: Search for Patterns
Grep: pattern="{search_pattern}", output_mode="files_with_matches"

## Step 2: Analyze Matches
For each matching file:
  Read file
  Apply analysis criteria: Read references/analysis-criteria.md
  Categorize findings

## Step 3: Generate Report
bash scripts/aggregate-findings.py {findings_json}
Format report using: Read assets/report-template.json
```

**Key Characteristics**:
- Discovery phase (Grep/Glob)
- Analysis phase (Read + apply criteria)
- Aggregation phase (combine results)
- Structured output (JSON/Markdown report)

**Examples**:
- Code quality analyzers
- Security auditors
- Dependency scanners
- Standards compliance checkers

## Pattern 4: Command Chain Execution

**Description**: Execute multi-step operations with dependencies between stages.

**When to Use**:
- Build pipelines
- Multi-stage workflows
- Sequential operations with validation
- Complex automation tasks

**Structure**:
```
skill-name/
├── SKILL.md
├── scripts/
│   ├── stage1-setup.sh
│   ├── stage2-build.sh
│   └── stage3-verify.sh
└── references/
    └── failure-recovery.md
```

**SKILL.md Pattern**:
```markdown
## Stage 1: Setup
bash scripts/stage1-setup.sh
Verify setup successful before proceeding

## Stage 2: Build
bash scripts/stage2-build.sh
Capture output and check for errors

## Stage 3: Verify
bash scripts/stage3-verify.sh
If verification fails: Read references/failure-recovery.md
```

**Key Characteristics**:
- Sequential stages with dependencies
- Validation after each stage
- Error handling between stages
- Rollback or recovery guidance

**Examples**:
- Build and deploy pipelines
- Test execution workflows
- Migration scripts
- Multi-step installations

## Pattern 5: Wizard-Style Workflow

**Description**: Break complex tasks into discrete steps with explicit user confirmation between phases.

**When to Use**:
- Complex configuration
- Guided creation workflows
- Multi-decision processes
- High-risk operations

**Structure**:
```
skill-name/
├── SKILL.md
├── scripts/
│   └── validate-choices.sh
├── references/
│   └── decision-guide.md
└── assets/
    └── templates/
        ├── option-a.txt
        └── option-b.txt
```

**SKILL.md Pattern**:
```markdown
## Step 1: Gather Requirements
Ask user about:
- Requirement A
- Requirement B
- Requirement C

## Step 2: Validate Choices
bash scripts/validate-choices.sh "{choices_json}"

## Step 3: Show Preview
Based on choices, load template:
Read assets/templates/{selected_template}.txt
Show preview to user

## Step 4: Confirm and Create
Ask user for final confirmation
If confirmed: Create output
```

**Key Characteristics**:
- Interactive user questions
- Validation between steps
- Preview before final action
- Explicit confirmation for changes

**Examples**:
- Component creators
- Project setup wizards
- Configuration generators
- Migration tools

## Pattern 6: Template-Based Generation

**Description**: Load templates, fill placeholders with generated data, output results.

**When to Use**:
- Consistent output formats
- Boilerplate code generation
- Document creation
- Configuration files

**Structure**:
```
skill-name/
├── SKILL.md
├── scripts/
│   └── generate-values.py
├── references/
│   └── field-specifications.md
└── assets/
    └── templates/
        ├── basic.txt
        └── advanced.txt
```

**SKILL.md Pattern**:
```markdown
## Step 1: Determine Template Type
Based on user requirements, select appropriate template

## Step 2: Generate Values
bash scripts/generate-values.py {requirements_json}
or
Apply generation rules from: Read references/field-specifications.md

## Step 3: Fill Template
Load: Read assets/templates/{template_type}.txt
Replace placeholders with generated values

## Step 4: Output Result
Write filled template to {output_path}
```

**Key Characteristics**:
- Templates in assets/
- Clear placeholder syntax
- Value generation logic separate
- Validation of filled template

**Examples**:
- Code generators
- Document creators
- Test file generators
- Configuration builders

## Pattern 7: Iterative Refinement

**Description**: Perform broad analysis, then progressively deeper investigation of identified issues.

**When to Use**:
- Large codebase analysis
- Multi-level diagnostics
- Gradual detail increase
- Context-limited operations

**Structure**:
```
skill-name/
├── SKILL.md
├── scripts/
│   ├── scan-all.sh        (broad, fast scan)
│   └── deep-analyze.py    (detailed, slow analysis)
└── references/
    └── deep-analysis-criteria.md
```

**SKILL.md Pattern**:
```markdown
## Phase 1: Broad Scan
bash scripts/scan-all.sh {target_directory}
Identifies candidates for deep analysis

## Phase 2: Prioritize Candidates
Sort by severity/importance
Select top N for deep analysis

## Phase 3: Deep Analysis (Iterative)
For each high-priority candidate:
  bash scripts/deep-analyze.py {candidate_path}
  Load criteria: Read references/deep-analysis-criteria.md
  Generate detailed report

Continue until context limit or all analyzed
```

**Key Characteristics**:
- Two-phase: broad scan + deep dive
- Prioritization between phases
- Context-aware (stops at limits)
- Incremental detail

**Examples**:
- Codebase health checks
- Security auditors
- Performance analyzers
- Quality assessors

## Pattern 8: Context Aggregation

**Description**: Gather data from multiple sources to synthesize comprehensive understanding.

**When to Use**:
- Multi-file analysis
- Cross-reference validation
- Comprehensive reports
- Knowledge synthesis

**Structure**:
```
skill-name/
├── SKILL.md
├── scripts/
│   ├── source1-scanner.sh
│   ├── source2-scanner.sh
│   └── aggregate.py
└── references/
    └── synthesis-rules.md
```

**SKILL.md Pattern**:
```markdown
## Step 1: Gather from Source 1
bash scripts/source1-scanner.sh

## Step 2: Gather from Source 2
bash scripts/source2-scanner.sh

## Step 3: Aggregate Data
bash scripts/aggregate.py {source1_output} {source2_output}

## Step 4: Synthesize Understanding
Apply synthesis rules: Read references/synthesis-rules.md
Generate comprehensive report
```

**Key Characteristics**:
- Multiple data sources
- Aggregation script to combine
- Synthesis rules for interpretation
- Comprehensive output

**Examples**:
- Dependency analyzers
- Documentation aggregators
- Compliance checkers
- Inventory reporters

## Pattern 9: Validation Pipeline

**Description**: Multi-stage validation with different checkers for different aspects.

**When to Use**:
- Quality gates
- Standards compliance
- Pre-commit checks
- Release validation

**Structure**:
```
skill-name/
├── SKILL.md
├── scripts/
│   ├── check-syntax.sh
│   ├── check-style.sh
│   ├── check-security.sh
│   └── check-quality.sh
└── references/
    └── validation-standards.md
```

**SKILL.md Pattern**:
```markdown
## Validation Stage 1: Syntax
bash scripts/check-syntax.sh {target}
Must pass before continuing

## Validation Stage 2: Style
bash scripts/check-style.sh {target}
Load standards: Read references/validation-standards.md

## Validation Stage 3: Security
bash scripts/check-security.sh {target}

## Validation Stage 4: Quality
bash scripts/check-quality.sh {target}

## Final Report
Aggregate all validation results
Determine overall pass/fail
```

**Key Characteristics**:
- Sequential validation stages
- Fast-fail on critical issues
- Multiple checker scripts
- Aggregated final report

**Examples**:
- Code validators
- Document checkers
- Configuration validators
- Pre-deployment checks

## Pattern 10: Reference Library

**Description**: Pure reference skill with no execution logic, just knowledge to load on-demand.

**When to Use**:
- Best practices guides
- Pattern libraries
- Standards documentation
- Example collections

**Structure**:
```
skill-name/
├── SKILL.md              (minimal, just loading guidance)
└── references/
    ├── topic-a.md
    ├── topic-b.md
    ├── topic-c.md
    └── examples/
        ├── example-1.md
        └── example-2.md
```

**SKILL.md Pattern**:
```markdown
---
name: reference-library
description: Reference material for {topic} - load on-demand
allowed-tools: [Read]
---

# {Topic} Reference Library

This skill provides reference material only. No execution.

## Available References

- **topic-a.md**: Description of topic A
- **topic-b.md**: Description of topic B
- **topic-c.md**: Description of topic C

## Usage

Load specific reference when needed:
Read references/{topic}.md

## Progressive Disclosure

Never load all references at once. Load only what's needed for current task.
```

**Key Characteristics**:
- No execution logic
- Pure documentation
- Progressive loading emphasized
- Clear reference catalog

**Examples**:
- Architecture guides
- Design pattern libraries
- Best practices collections
- API reference documentation

## Choosing the Right Pattern

### Decision Guide

**For automation tasks**: Pattern 1 (Script Automation) or Pattern 4 (Command Chain)
**For file transformations**: Pattern 2 (Read-Process-Write)
**For codebase analysis**: Pattern 3 (Search-Analyze-Report) or Pattern 7 (Iterative Refinement)
**For user-guided workflows**: Pattern 5 (Wizard-Style)
**For code generation**: Pattern 6 (Template-Based Generation)
**For multi-source analysis**: Pattern 8 (Context Aggregation)
**For validation/checking**: Pattern 9 (Validation Pipeline)
**For documentation/guides**: Pattern 10 (Reference Library)

### Combining Patterns

Skills can combine multiple patterns:
- Wizard-Style (Pattern 5) + Template-Based Generation (Pattern 6)
- Search-Analyze-Report (Pattern 3) + Validation Pipeline (Pattern 9)
- Iterative Refinement (Pattern 7) + Context Aggregation (Pattern 8)

**Example**: Component creator skill
```
Combines:
- Pattern 5 (Wizard-Style): Gather requirements
- Pattern 6 (Template-Based): Generate code
- Pattern 9 (Validation): Validate output
```

## Implementation Checklist

When implementing a skill using these patterns:

- [ ] Identify primary pattern type
- [ ] Determine if combining patterns
- [ ] Create directory structure matching pattern
- [ ] Write SKILL.md following pattern template
- [ ] Implement scripts (if pattern uses scripts)
- [ ] Create templates/assets (if pattern uses them)
- [ ] Write reference documentation (if pattern uses references)
- [ ] Use relative paths for all resource paths
- [ ] Keep SKILL.md under 800 lines
- [ ] Test progressive disclosure (references loaded on-demand)
- [ ] Validate allowed-tools list (minimal permissions)
- [ ] Write unit tests for scripts
- [ ] Test in different installation contexts

## References

* Original Article: [Claude Skills Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)
* Core Aspects: `claude-skills-core-aspects.md`
