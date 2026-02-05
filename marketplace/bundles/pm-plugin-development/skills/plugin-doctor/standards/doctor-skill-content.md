# Doctor Skill Content Workflow

Comprehensive analysis and refactoring of skill subdirectory content (references/, workflows/, templates/).

## Parameters

- `skill-path` (required): Path to skill directory
- `--no-fix` (optional): Analysis only, no reorganization
- `--skip-quality` (optional): Skip Phase 3 quality analysis

## Overview

This workflow analyzes all markdown files within a skill's subdirectories for proper organization, quality, and consistency. It uses LLM-based semantic analysis for classification and quality assessment.

**Phases**:
1. **Inventory** - Discover all files (SCRIPT)
2. **Classify** - Categorize each file as reference/workflow/template (LLM)
3. **Analyze** - Content quality analysis (LLM)
4. **Reorganize** - Move files to correct directories (LLM + Bash)
5. **Verify** - Link verification (SCRIPT)
6. **Report** - Generate findings report (LLM)

## Step 1: Load Prerequisites

```
Skill: plan-marshall:ref-development-standards
Skill: pm-plugin-development:plugin-architecture
Read references/content-classification-guide.md
Read references/content-quality-guide.md
```

## Step 2: Phase 1 - Inventory (LLM)

Use Glob and Read tools to inventory skill content:

```bash
# List all markdown files in skill subdirectories
Glob: pattern="**/*.md", path={skill_path}
```

For each file, collect:
- File path and directory
- Line count (via Read tool)
- Extension statistics

## Step 3: Phase 2 - Classify (LLM)

For each `.md` file discovered in subdirectories:

1. **Read file content**
2. **Apply classification criteria** from `content-classification-guide.md`
3. **Determine category**: reference | workflow | template | mixed
4. **Record confidence level**: high | medium | low

**Classification Output** (for each file):
```
File: {relative_path}
Classification: {category}
Confidence: {level}
Reasoning:
  - {observation 1}
  - {observation 2}
Current Location: {directory}
Correct Location: {references/|workflows/|templates/}
Needs Move: {yes|no}
Needs Splitting: {yes|no}
```

## Step 4: Phase 3 - Analyze Quality (LLM-Hybrid)

Skip if `--skip-quality` specified.

### Cross-File Analysis (LLM)

Perform cross-file analysis by reading and comparing content:

1. Read all markdown files in skill subdirectories
2. Compute content hashes to detect exact duplicates
3. Compare section headers and content blocks for similarity
4. Identify extraction candidates (repeated patterns)

Produce analysis with:
- `exact_duplicates`: Report directly (no LLM needed - hash-verified matches)
- `similarity_candidates`: Queue for LLM semantic analysis
- `extraction_candidates`: Queue for LLM extraction recommendations
- `terminology_variants`: Queue for LLM consistency analysis

### LLM Semantic Analysis

For each `similarity_candidate` (40-95% similarity):
1. Read both content blocks from file locations
2. Classify: `true_duplicate` | `similar_concept` | `false_positive`
3. Recommend: `consolidate` | `cross_reference` | `keep_both`

For each `extraction_candidate`:
1. Review detected patterns (placeholders, step sequences)
2. Recommend: `extract_to_templates` | `extract_to_workflows` | `keep_inline`

For each `terminology_variant`:
1. Review variant terms and their files
2. Recommend standardization term or keep variants

### Single-File Quality Analysis

Read each content file and analyze:

**Completeness**:
- TODO markers, placeholder text
- Missing examples, incomplete sections

**Contradictions**:
- Conflicting rules
- Examples violating stated rules

### Verify LLM Findings

Verify LLM findings by re-reading referenced files:

1. For each claimed duplicate, read both files and compare content
2. For each similarity claim, verify the specific sections exist
3. For each extraction candidate, verify the pattern appears as claimed

**Reject any LLM claims that can't be verified** against actual content.

**Output**: Verified quality report with:
- Exact duplicates (auto-detected)
- Verified similarity findings
- Verified extraction candidates
- Verified terminology issues
- Single-file quality scores

## Step 5: Phase 4 - Reorganize (LLM + Bash)

Based on Phase 2 classification results:

**Safe Reorganizations** (auto-apply unless --no-fix):
- Move file to correct directory (same name)
- Rename to remove redundant suffix (e.g., `-protocol`, `-framework`)

```bash
mv {old_path} {new_path}
```

**Risky Reorganizations** (require confirmation):
- Split mixed-content file into multiple files
- Delete duplicate file
- Merge similar files

```
AskUserQuestion:
  question: "Split {file} into reference and workflow components?"
  options:
    - label: "Yes" description: "Split file"
    - label: "No" description: "Keep as-is"
```

**After moves**: Update cross-references in all affected files:
1. Grep for old paths in SKILL.md and all content files
2. Update references using Edit tool

## Step 6: Phase 5 - Verify Links (LLM)

Use Grep and Read tools to verify references:

1. Extract all relative path references from SKILL.md (pattern: `Read `, `references/`, `scripts/`)
2. For each reference, verify the target file exists using Glob
3. Report any broken references

For each content file, verify:
- Internal cross-references valid
- SKILL.md references point to existing files

## Step 7: Phase 6 - Report (LLM)

Generate comprehensive report:

```markdown
# Skill Content Analysis Report

**Skill**: {skill_name}
**Path**: {skill_path}
**Date**: {timestamp}

## Summary

| Metric | Value |
|--------|-------|
| Total Files | {count} |
| Total Lines | {count} |
| Content Quality Score | {score}/100 |
| Reorganizations Applied | {count} |
| Links Verified | {count} |

## File Classification

| File | Current Dir | Classification | Confidence | Action |
|------|-------------|----------------|------------|--------|
| {file} | {dir} | {type} | {level} | {action} |

## Quality Analysis

### Completeness
{findings}

### Duplication
{findings}

### Consistency
{findings}

### Contradictions
{findings}

## Reorganizations Applied

### Safe (Auto-Applied)
- {description}

### Risky (User Confirmed)
- {description}
- Skipped: {description}

## Link Verification

| Status | Count |
|--------|-------|
| Valid | {count} |
| Updated | {count} |
| Broken | {count} |

## Recommendations

1. {recommendation}
```
