# Pattern Usage Examples

Practical applications of all 10 skill patterns to marketplace component development scenarios.

## Pattern 1: Script Automation

### Marketplace Scenario: Inventory Scanner

**Use Case**: Scan marketplace directory structure to catalog all components.

**Why Pattern 1**:
- File system traversal is deterministic
- JSON output structure is predictable
- Logic is testable outside Claude

**Implementation**:

```markdown
skill: marketplace-inventory

## Step 1: Scan Marketplace Structure

python3 .plan/execute-script.py plan-marshall:marketplace-inventory:scan-marketplace-inventory \
  --scope marketplace \
  --include-descriptions

# Note: JSON is the default output format (no --format flag needed)

Script outputs:
```json
{
  "scope": "marketplace",
  "bundles": [...],
  "statistics": {
    "total_bundles": 5,
    "total_agents": 25,
    "total_commands": 45,
    "total_skills": 18
  }
}
```

## Step 2: Interpret Inventory

Load interpretation rules: Read references/inventory-classification.md

Classify components by:
- Complexity (simple, standard, complex)
- Pattern type (using pattern detection)
- Health status (clean, needs attention, problematic)
```

**Key Benefit**: Deterministic scanning logic in shell script, Claude interprets and categorizes results.

---

## Pattern 2: Read-Process-Write

### Marketplace Scenario: Frontmatter Standardizer

**Use Case**: Convert old array-syntax tools declarations to comma-separated format.

**Why Pattern 2**:
- Linear transformation: read → modify → write
- Clear input/output structure
- Template-driven output format

**Implementation**:

```markdown
skill: frontmatter-standardizer

## Step 1: Read Component File

Read {component_path}

## Step 2: Process Frontmatter

Extract YAML frontmatter between `---` delimiters

If tools field uses array syntax:
  tools: [Read, Write, Edit]

Convert to comma-separated:
  tools: Read, Write, Edit

Validate tool names are capitalized

## Step 3: Write Updated File

Reconstruct file:
- Updated frontmatter
- Original body content unchanged

Write to {component_path}
```

**Key Benefit**: Simple transformation with predictable behavior, no external dependencies.

---

## Pattern 3: Search-Analyze-Report

### Marketplace Scenario: Reference Pattern Validator

**Use Case**: Find all file references and validate relative path usage.

**Why Pattern 3**:
- Discovery phase (find references with Grep)
- Analysis phase (validate each reference)
- Reporting phase (aggregate violations)

**Implementation**:

```markdown
skill: reference-validator

## Step 1: Search for File References

Grep: pattern="Read:|bash |python " output_mode="content"

Finds all Read/Bash/Python references across marketplace

## Step 2: Analyze Each Reference

For each matching line:
  Read containing file
  Extract reference path
  Load validation rules: Read references/reference-compliance.md

  Check for violations:
  - Path issues in internal references
  - Prohibited ../../../../ escape sequences
  - Absolute paths instead of relative

  Categorize: COMPLIANT | VIOLATION

## Step 3: Generate Violation Report

bash scripts/aggregate-violations.py {findings_json}

Load template: Read assets/report-template.md

Output:
- Total references found
- Compliant references
- Violations by type
- Recommendations for fixes
```

**Key Benefit**: Comprehensive codebase analysis with structured reporting.

---

## Pattern 4: Command Chain Execution

### Marketplace Scenario: Bundle Verification Pipeline

**Use Case**: Verify bundle structure, validate metadata, check dependencies.

**Why Pattern 4**:
- Multiple dependent stages
- Each stage must succeed before next
- Error handling between stages

**Implementation**:

```markdown
skill: bundle-verifier

## Stage 1: Structure Validation

bash scripts/validate-structure.sh {bundle_path}

Verifies:
- plugin.json exists
- agents/, commands/, skills/ directories present
- No prohibited files

If structure invalid: STOP with error report

## Stage 2: Metadata Validation

bash scripts/validate-metadata.sh {bundle_path}/plugin.json

Validates:
- JSON syntax
- Required fields present
- Version format correct

If metadata invalid: STOP with error report

## Stage 3: Dependency Check

bash scripts/check-dependencies.sh {bundle_path}

Verifies:
- All referenced skills exist
- All script paths resolve
- All cross-references valid

If dependencies missing: Load recovery guide
Read references/dependency-resolution.md

## Final Report

All stages passed: ✅ Bundle verified
Any stage failed: ❌ Bundle has issues (with specific error details)
```

**Key Benefit**: Sequential validation with clear failure points and recovery guidance.

---

## Pattern 5: Wizard-Style Workflow

### Marketplace Scenario: Component Creator

**Use Case**: Guide user through creating new agent/command/skill.

**Why Pattern 5**:
- Complex decision tree (component type, pattern, features)
- User needs guidance at each step
- Preview before creation reduces errors

**Implementation**:

```markdown
skill: component-creator

## Step 1: Gather Component Type

Ask user:
  "Which component do you want to create?"
  Options:
    - Agent (focused task executor)
    - Command (user-facing utility)
    - Skill (knowledge repository)

## Step 2: Select Pattern

Based on component_type, ask:
  "Which implementation pattern?"
  Options: [Relevant patterns for type]

Load pattern guidance:
Read references/patterns/{selected_pattern}.md

## Step 3: Gather Component Details

Ask user:
  - Component name
  - Description
  - Bundle location
  - Additional features (scripts? templates?)

## Step 4: Validate Choices

bash scripts/validate-component-config.sh "{config_json}"

Shows:
  - Proposed file structure
  - Frontmatter preview
  - Files to be created

## Step 5: Confirm and Create

Ask user: "Create component with this configuration?"

If confirmed:
  Load template: Read assets/templates/{component_type}-{pattern}.md
  Fill template with user values
  Create component files

Show:
  ✅ Created {component_name}
  📁 Location: {bundle}/agents/{component_name}.md
  📋 Next steps: [...]
```

**Key Benefit**: User-friendly creation process with validation and preview.

---

## Pattern 6: Template-Based Generation

### Marketplace Scenario: Test Suite Generator

**Use Case**: Generate complete test suite for skill scripts.

**Why Pattern 6**:
- Consistent test structure required
- Boilerplate heavy (setup, fixtures, assertions)
- Parameterized by script specifics

**Implementation**:

```markdown
skill: test-generator

## Step 1: Analyze Script

Read {script_path}

Extract:
- Script name
- Input parameters
- Expected output format
- Edge cases (from comments/docs)

## Step 2: Generate Test Values

bash scripts/generate-test-cases.py {script_path}

Outputs:
```json
{
  "positive_cases": [...],
  "negative_cases": [...],
  "edge_cases": [...]
}
```

## Step 3: Select Template

Based on script type (bash/python):
  template = assets/templates/test-{script_type}.sh

Load: Read {template}

## Step 4: Fill Template

Replace placeholders:
- {{SCRIPT_NAME}} → extracted script name
- {{TEST_CASES}} → generated test cases
- {{FIXTURES_DIR}} → test fixtures directory

## Step 5: Write Test Suite

Write to test/{script_name}-test.sh
```

**Key Benefit**: Automated test creation with consistent structure.

---

## Pattern 7: Iterative Refinement

### Marketplace Scenario: Large Codebase Quality Audit

**Use Case**: Analyze 90+ marketplace components without hitting context limits.

**Why Pattern 7**:
- Too many files for single pass
- Need to prioritize high-value analysis
- Context budget limits deep-dive count

**Implementation**:

```markdown
skill: quality-auditor

## Phase 1: Broad Quality Scan

bash scripts/quick-scan.sh --scope marketplace

Fast scan outputs:
```json
{
  "total": 92,
  "by_quality": {
    "excellent": 45,
    "good": 30,
    "needs_attention": 12,
    "problematic": 5
  },
  "flagged_for_deep_analysis": [
    {"file": "...", "score": 45, "issues": [...]},
    ...
  ]
}
```

## Phase 2: Prioritize for Deep Analysis

Sort flagged components by:
- Quality score (lowest first)
- Issue severity (critical issues first)
- File size (larger = more impact)

Select top 10 for deep analysis

## Phase 3: Iterative Deep Dive

For each of top 10 (one at a time):
  bash scripts/deep-analyze.py {component_path}

  Load detailed criteria:
  Read references/quality-standards.md

  Generate comprehensive report:
  - Line-by-line analysis
  - Standards compliance check
  - Refactoring recommendations

  Progress: "Analyzed [3/10] problematic components"

## Phase 4: Final Summary

Aggregate:
- Broad scan statistics (all 92 components)
- Deep analysis details (10 components)
- Top issues across marketplace
- Recommended action priority
```

**Key Benefit**: Comprehensive analysis within context limits through two-phase approach.

---

## Pattern 8: Context Aggregation

### Marketplace Scenario: Cross-Bundle Duplication Detector

**Use Case**: Find duplicate content across multiple bundles to enable consolidation.

**Why Pattern 8**:
- Multiple data sources (each bundle)
- Need to correlate across sources
- Synthesis requires seeing all data together

**Implementation**:

```markdown
skill: duplication-detector

## Step 1: Scan Bundle 1 Content

bash scripts/extract-content-blocks.sh marketplace/bundles/pm-dev-java

Outputs content fingerprints:
```json
{
  "bundle": "pm-dev-java",
  "blocks": [
    {"id": "java-1", "content_hash": "abc123", "type": "example"},
    ...
  ]
}
```

## Step 2: Scan Bundle 2 Content

bash scripts/extract-content-blocks.sh marketplace/bundles/pm-dev-frontend

Outputs content fingerprints

## Step 3: Scan Bundles 3-5

Repeat for remaining bundles

## Step 4: Aggregate All Content

bash scripts/find-duplicates.py \
  bundle1_blocks.json \
  bundle2_blocks.json \
  bundle3_blocks.json \
  bundle4_blocks.json \
  bundle5_blocks.json

Outputs:
```json
{
  "exact_duplicates": 5,
  "high_similarity": 8,
  "matches": [
    {
      "block1": {"bundle": "pm-dev-java", "file": "..."},
      "block2": {"bundle": "pm-dev-frontend", "file": "..."},
      "similarity": 95,
      "recommendation": "Extract to shared skill: cui-code-standards"
    }
  ]
}
```

## Step 5: Synthesize Recommendations

Load synthesis rules:
Read references/consolidation-strategies.md

Generate consolidation plan:
- Which content to extract
- Proposed skill structure
- Migration steps
- Impact assessment
```

**Key Benefit**: Cross-bundle analysis enables systematic duplication elimination.

---

## Pattern 9: Validation Pipeline

### Marketplace Scenario: Pre-Commit Quality Gate

**Use Case**: Validate component before allowing commit to repository.

**Why Pattern 9**:
- Multiple validation aspects (syntax, style, standards, links)
- Fast-fail on critical issues
- Comprehensive report at end

**Implementation**:

```markdown
skill: quality-gate

## Validation Stage 1: YAML Syntax

bash scripts/check-yaml-syntax.sh {component_path}

Validates:
- Frontmatter delimiters correct
- YAML parseable
- Required fields present

❌ If syntax errors: STOP (cannot proceed with invalid YAML)

## Validation Stage 2: Frontmatter Standards

bash scripts/check-frontmatter-standards.sh {component_path}

Load standards:
Read references/frontmatter-standards.md

Checks:
- Tools format (comma-separated)
- No prohibited tools (Task in agents)
- Valid tool names

⚠️  If violations: Record for final report (continue checking)

## Validation Stage 3: Reference Compliance

bash scripts/check-references.sh {component_path}

Validates:
- All relative paths correct
- No prohibited escape sequences
- No absolute paths

⚠️  If violations: Record for final report (continue checking)

## Validation Stage 4: Link Verification

bash scripts/verify-links.sh {component_path}

Checks:
- All internal file references resolve
- All skill references exist
- All cross-references valid

⚠️  If broken links: Record for final report (continue checking)

## Final Gate Decision

Aggregate all validation results:

If any stage 1 (critical) failures:
  ❌ REJECT COMMIT - Fix critical errors first

If only stages 2-4 (warnings):
  ⚠️  WARN - {N} issues found, recommend fixing before commit
  Allow commit with warnings

If all stages pass:
  ✅ APPROVE COMMIT - Component meets quality standards
```

**Key Benefit**: Multi-aspect validation with clear pass/fail criteria.

---

## Pattern 10: Reference Library

### Marketplace Scenario: Architecture Standards Repository

**Use Case**: Centralized architecture knowledge loaded on-demand by other components.

**Why Pattern 10**:
- Pure documentation, no execution
- Reference material loaded as needed
- Minimizes context usage

**Implementation**:

```markdown
skill: plugin-architecture

---
name: plugin-architecture
description: Architecture principles, patterns, and design guidance
allowed-tools: [Read]
---

# Plugin Architecture Reference Library

This skill provides reference material only. No execution logic.

## Available References

### Core Concepts
- **core-principles.md**: Skills as prompt modifiers, relative path pattern, progressive disclosure
- **goal-based-organization.md**: Goal-centric vs component-centric design

### Implementation Guidance
- **skill-patterns.md**: 10 common skill implementation patterns
- **skill-design.md**: Workflow-focused design principles
- **command-design.md**: Thin orchestrator pattern for commands

### Standards
- **architecture-rules.md**: 5 core architectural rules
- **reference-patterns.md**: relative path patterns and anti-patterns
- **frontmatter-standards.md**: YAML frontmatter specifications

### Examples
- **examples/goal-based-skill-example.md**: Complete multi-workflow skill
- **examples/workflow-command-example.md**: Thin orchestrator command
- **examples/pattern-usage-examples.md**: All 10 patterns applied

## Usage

Load specific reference when needed:
```
Read references/core-principles.md
```

## Progressive Disclosure

⚠️  NEVER load all references at once (9 files × 500 lines = 4500+ lines)

Load strategically:
- Creating skill? → skill-design.md + skill-patterns.md
- Creating command? → command-design.md
- Understanding architecture? → core-principles.md + architecture-rules.md
- Validating references? → reference-patterns.md
```

**Key Benefit**: Centralized knowledge base with minimal memory footprint.

---

## Pattern Combinations

### Combination 1: Wizard + Template + Validation

**Scenario**: Create and validate new component in one workflow

```markdown
skill: component-creator-with-validation

Pattern 5 (Wizard-Style):
  Step 1-4: Gather requirements and show preview

Pattern 6 (Template-Based):
  Step 5: Generate component from template

Pattern 9 (Validation):
  Step 6: Run validation pipeline on generated component

If validation fails:
  Show errors, allow user to modify, re-validate

If validation passes:
  Write component file, mark as ready to commit
```

**Benefit**: End-to-end creation with quality assurance built-in.

### Combination 2: Search + Script + Report

**Scenario**: Find pattern violations and generate fix script

```markdown
skill: auto-fixer

Pattern 3 (Search-Analyze-Report):
  Step 1: Grep for violation patterns
  Step 2: Analyze each violation

Pattern 1 (Script Automation):
  Step 3: bash scripts/generate-fixes.py {violations_json}
  Script outputs fix commands

Pattern 2 (Read-Process-Write):
  Step 4: Apply fixes to files

Final report:
  - Violations found
  - Fixes applied
  - Manual review needed
```

**Benefit**: Automated detection and remediation.

### Combination 3: Iterative + Context Aggregation

**Scenario**: Large-scale marketplace health assessment

```markdown
skill: marketplace-health-analyzer

Pattern 7 (Iterative Refinement):
  Phase 1: Quick scan all 92 components
  Phase 2: Prioritize top 15 for deep dive

Pattern 8 (Context Aggregation):
  Phase 3: Gather detailed data from 5 bundles
  Phase 4: Aggregate cross-bundle patterns

Pattern 3 (Search-Analyze-Report):
  Phase 5: Generate comprehensive health report
```

**Benefit**: Complete marketplace understanding within context limits.

---

## Anti-Patterns: What NOT to Do

### Anti-Pattern 1: Improper Path Reference

**Problem**:
```markdown
Read: ../../../standards/file.md
bash ./scripts/analyzer.sh
```

**Why Wrong**: Breaks when skill installed in different contexts

**Fix**:
```markdown
Read references/standards.md
bash scripts/analyzer.sh
```

### Anti-Pattern 2: Monolithic SKILL.md

**Problem**:
```markdown
SKILL.md contains:
- 2000 lines of workflow instructions
- All standards inline (no references/)
- 15 different workflows
- No progressive disclosure
```

**Why Wrong**: Loads 2000 lines into context regardless of actual need

**Fix**:
```markdown
SKILL.md: 400 lines (workflow summaries + loading instructions)
references/: 10 files × 200 lines (load on-demand)
Progressive disclosure: Load only what current workflow needs
```

### Anti-Pattern 3: Direct File Access Instead of Skills

**Problem**:
```markdown
# In agent.md
Step 1: Read ../../../../standards/java-standards.md
```

**Why Wrong**:
- Violates self-containment
- Breaks if standards location changes
- Bypasses skill versioning

**Fix**:
```markdown
# In agent.md
Step 1: Load Java standards
Skill: cui-java-core
# Skill handles loading correct standards version
```

### Anti-Pattern 4: Wrong Pattern for Task

**Problem**: Using Pattern 5 (Wizard) for simple file transformation

```markdown
skill: file-converter

Step 1: Ask user "What format to convert to?"
Step 2: Ask user "What encoding to use?"
Step 3: Ask user "Confirm conversion?"
Step 4: Read file
Step 5: Convert format
Step 6: Write file
```

**Why Wrong**: Over-engineered, 6 steps for simple transformation

**Fix**: Use Pattern 2 (Read-Process-Write)

```markdown
skill: file-converter

Step 1: Read {input_file}
Step 2: Convert to {output_format} using {encoding}
Step 3: Write {output_file}
```

### Anti-Pattern 5: No Scripts for Deterministic Logic

**Problem**:
```markdown
SKILL.md contains:
  Step 1: Parse JSON with regex
  Step 2: Extract fields using string manipulation
  Step 3: Validate format with complex conditionals
  Step 4: Calculate metrics with formulas
```

**Why Wrong**:
- Non-deterministic (Claude may parse differently each time)
- Not testable
- Slow (Claude processes each time vs. script caching)

**Fix**: Use Pattern 1 (Script Automation)

```markdown
SKILL.md:
  Step 1: bash scripts/parse-and-validate.py {input_json}
  Step 2: Interpret script output (structured JSON)

scripts/parse-and-validate.py:
  - Deterministic parsing
  - Unit tested
  - Fast execution
```

### Anti-Pattern 6: Loading All References Upfront

**Problem**:
```markdown
# At start of workflow
Read references/ref1.md
Read references/ref2.md
Read references/ref3.md
Read references/ref4.md
Read references/ref5.md
# 2500 lines loaded before knowing what workflow needs
```

**Why Wrong**: Wastes 70-80% of context on unused content

**Fix**: Progressive loading

```markdown
# Load only what this workflow needs
If workflow = "create-agent":
  Read references/agent-patterns.md

If workflow = "validate-component":
  Read references/validation-rules.md
```

---

## Decision Guide: Choosing Patterns

### Quick Pattern Selector

**Your Task**:
- ✅ Run shell/Python scripts → **Pattern 1** (Script Automation)
- ✅ Transform file content → **Pattern 2** (Read-Process-Write)
- ✅ Search codebase → **Pattern 3** (Search-Analyze-Report)
- ✅ Multi-stage pipeline → **Pattern 4** (Command Chain)
- ✅ Guide user through complex process → **Pattern 5** (Wizard-Style)
- ✅ Generate from templates → **Pattern 6** (Template-Based)
- ✅ Analyze large codebase → **Pattern 7** (Iterative Refinement)
- ✅ Combine multiple data sources → **Pattern 8** (Context Aggregation)
- ✅ Validate quality/compliance → **Pattern 9** (Validation Pipeline)
- ✅ Provide reference documentation → **Pattern 10** (Reference Library)

### Complexity Assessment

**Simple (1 pattern)**:
- File transformation → Pattern 2
- Documentation → Pattern 10
- Basic automation → Pattern 1

**Moderate (2 patterns)**:
- Guided generation → Pattern 5 + Pattern 6
- Validated automation → Pattern 1 + Pattern 9
- Search and fix → Pattern 3 + Pattern 2

**Complex (3+ patterns)**:
- Full creation workflow → Pattern 5 + Pattern 6 + Pattern 9
- Comprehensive analysis → Pattern 3 + Pattern 7 + Pattern 8
- End-to-end pipeline → Pattern 4 + Pattern 1 + Pattern 9

---

## Summary

**Key Takeaways**:

1. **Match pattern to task**: Don't use Pattern 5 (Wizard) for simple transformations
2. **Combine patterns**: Most real workflows use 2-3 patterns together
3. **Use scripts for logic**: Pattern 1 for deterministic operations
4. **Progressive disclosure**: Pattern 10 for reference material
5. **Avoid anti-patterns**: No path issues, no monolithic SKILL.md, no loading all references

**Pattern Usage in Marketplace**:
- plugin-architecture: Pattern 10 (Reference Library)
- plugin-create: Pattern 5 + Pattern 6 + Pattern 9 (Wizard + Template + Validation)
- plugin-diagnose: Pattern 3 + Pattern 7 (Search-Analyze + Iterative)
- plugin-fix: Pattern 2 + Pattern 1 (Read-Process-Write + Script Automation)
- plugin-maintain: Pattern 8 + Pattern 9 (Context Aggregation + Validation)

**References**:
- Full pattern details: references/skill-patterns.md
- Design principles: references/skill-design.md
- Core concepts: references/core-principles.md
