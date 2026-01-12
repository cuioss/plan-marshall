# Content Classification Guide

Classification criteria for LLM-based content type identification in skill subdirectories.

## Purpose

Provides criteria for Claude to classify markdown files as reference, workflow, template, or mixed content.

## Classification Categories

| Category | Characteristics | Target Directory |
|----------|-----------------|------------------|
| `reference` | Rules, criteria, standards, lookup tables, "what to do" | `references/` |
| `workflow` | Steps, phases, procedures, decision trees, "how to execute" | `workflows/` |
| `template` | Placeholders, boilerplate, fill-in-the-blank structure | `templates/` |
| `mixed` | Contains multiple categories - needs splitting | Split required |

## Classification Questions

Evaluate each file with these questions in order:

### 1. Is this a template?

**YES if**:
- Contains `{{PLACEHOLDER}}` or `{placeholder}` patterns
- Designed to be copied and filled in
- Mostly boilerplate structure with insertion points
- Title contains "template" (e.g., `readme-template.adoc`)

**Target**: `templates/`

### 2. Is this a workflow?

**YES if**:
- Describes a sequence of steps to execute
- Contains decision trees or branching logic
- Focuses on HOW to do something (procedural)
- Has phases, stages, or numbered steps (### Step 1, ### Step 2)
- Contains action verbs: "Execute", "Run", "Check", "Verify", "Apply"
- Describes when to do things: "If X then Y", "When Z occurs"

**Indicators** (title/content):
- Words: protocol, procedure, workflow, process, framework (when describing steps)
- Sections: "### Steps", "## Phases", "## Execution Flow"
- Content: decision matrices, flowcharts, state machines

**Target**: `workflows/`

### 3. Is this a reference?

**YES if**:
- Provides rules, standards, or criteria
- Designed to be consulted/looked up
- Focuses on WHAT requirements apply
- Contains examples of good/bad patterns
- Defines terms, thresholds, or specifications
- Lists prohibited/required patterns

**Indicators** (title/content):
- Words: standards, guide, rules, requirements, criteria
- Sections: "## Quality Standards", "## Prohibited Patterns", "## Requirements"
- Content: tables of criteria, example code, pattern lists

**Target**: `references/`

### 4. Is this mixed content?

**YES if**:
- Contains both reference material AND workflow steps
- First half describes rules, second half describes execution
- Would benefit from being split into separate files
- Line count > 400 with distinct content sections

**Action**: Recommend splitting into reference + workflow files

## Classification Output Format

For each file, produce:

```
File: {relative_path}
Classification: {reference|workflow|template|mixed}
Confidence: {high|medium|low}
Reasoning:
  - {specific observation 1}
  - {specific observation 2}
  - {specific observation 3}
Recommended Location: {directory/filename.md}
Needs Splitting: {yes|no}
Split Recommendation: {if yes, describe split}
```

## Confidence Levels

### High Confidence
- Clear structural indicators (### Step 1, {{PLACEHOLDER}})
- Title directly indicates type
- Content uniformly matches single category

### Medium Confidence
- Some indicators present but not dominant
- Title doesn't clearly indicate type
- Content mostly matches one category with minor exceptions

### Low Confidence
- Mixed signals across indicators
- Could reasonably be classified multiple ways
- Needs human review

## Common Misclassifications

### "Protocol" files
- Often named `-protocol.md` but contain workflow content
- Check actual content, not just title
- If contains steps: **workflow**
- If contains rules only: **reference**

### "Framework" files
- May be workflow (execution framework) or reference (conceptual framework)
- Check for numbered steps vs criteria lists

### "Guide" files
- May be reference (rules guide) or workflow (how-to guide)
- Check for imperative ("Do X") vs declarative ("X must be")

## Directory Naming After Classification

When moving files to correct directories:

| Current Suffix | In Directory | Action |
|----------------|--------------|--------|
| `-protocol.md` | workflows/ | Remove suffix → `{name}.md` |
| `-framework.md` | workflows/ | Remove suffix → `{name}.md` |
| `-workflow.md` | workflows/ | Remove suffix → `{name}.md` |
| `-standards.md` | references/ | Keep as-is |
| `-guide.md` | references/ | Keep as-is |
| `-template.*` | templates/ | Keep as-is |

## Examples

### Example 1: Reference File
```
File: standards/tone-and-style.md
Classification: reference
Confidence: high
Reasoning:
  - Contains lists of prohibited phrases
  - Provides examples of good vs bad text
  - No step-by-step execution instructions
  - Title indicates standards document
Recommended Location: references/tone-and-style.md
Needs Splitting: no
```

### Example 2: Workflow File
```
File: standards/link-verification-protocol.md
Classification: workflow
Confidence: high
Reasoning:
  - Contains "### Step 1", "### Step 2" sections
  - Describes verification procedure with decision tree
  - Focuses on HOW to verify links
  - Despite "protocol" name, content is procedural
Recommended Location: workflows/link-verification.md
Needs Splitting: no
```

### Example 3: Mixed File
```
File: standards/asciidoc-formatting.md
Classification: mixed
Confidence: medium
Reasoning:
  - Lines 1-340: AsciiDoc formatting rules (reference)
  - Lines 341-535: Script usage documentation (should be in SKILL.md)
  - Two distinct content sections
Recommended Location: references/asciidoc-formatting.md (after trimming)
Needs Splitting: yes
Split Recommendation: Remove lines 341-535 (script docs), keep formatting rules
```

### Example 4: Template File
```
File: assets/templates/readme-template.adoc
Classification: template
Confidence: high
Reasoning:
  - Contains {{PROJECT_NAME}} placeholder
  - Boilerplate structure for README files
  - Located in templates directory
  - Designed to be copied and customized
Recommended Location: templates/readme-template.adoc
Needs Splitting: no
```
