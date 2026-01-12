# Content Quality Guide

Quality analysis dimensions for LLM-hybrid content review in skill subdirectories.

## Purpose

Provides criteria for cross-file content analysis using a hybrid approach:
- **Scripts**: Pre-filter and structure data (hashing, similarity calculation, pattern detection)
- **LLM**: Semantic analysis for classification and recommendations
- **Scripts**: Verify LLM claims against actual content

## Analysis Approach: LLM-Hybrid

| Task | Handler | Why |
|------|---------|-----|
| File inventory | Script | Deterministic |
| Section extraction | Script | Regex-based parsing |
| Exact duplication (100% match) | Script | Hash comparison |
| Near-duplication (40-95% similar) | **LLM** | Semantic judgment needed |
| True dup vs similar concepts | **LLM** | Context-aware classification |
| Terminology inconsistencies | **LLM** | Domain knowledge needed |
| Extraction recommendations | **LLM** | Requires understanding intent |
| Verification of LLM claims | Script | Cross-check against content |

## Analysis Dimensions

| Dimension | Question | Impact |
|-----------|----------|--------|
| Completeness | Is anything missing? | Gaps in documentation |
| Duplication | Is content repeated? | Maintenance burden |
| Consistency | Is terminology uniform? | Confusion |
| Contradictions | Do files conflict? | Incorrect behavior |

---

## Dimension 1: Completeness Analysis

### What to Check

**Incomplete Sections**:
- TODO markers: `TODO`, `TBD`, `FIXME`, `XXX`
- Placeholder text: `Lorem ipsum`, `[description]`, `...`
- Empty sections: Headers with no content below
- Stub sections: Single-sentence explanations for complex topics

**Missing Examples**:
- Rules without code examples
- Concepts without usage demonstrations
- Edge cases mentioned but not shown

**Missing Context**:
- References to external concepts without explanation
- Assumed knowledge not documented
- Missing "when to use" guidance

### Output Format

```
Completeness Issues:
  File: {path}
  - Section "{section_name}": {issue_description}
  - Line {N}: TODO marker found: "{text}"
  - Missing: {what's missing}
  Score: {0-100}
```

### Scoring

| Score | Meaning |
|-------|---------|
| 90-100 | Complete - all sections filled, examples present |
| 70-89 | Minor gaps - 1-2 small missing items |
| 50-69 | Moderate gaps - missing sections or examples |
| 0-49 | Incomplete - significant content missing |

---

## Dimension 2: Duplication Analysis (Cross-File)

### Script Pre-Processing

Run `analyze cross-file` first to get structured analysis:

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:analyze cross-file --skill-path {skill_path}
```

**Script Output Categories**:

| Category | Script Responsibility | LLM Responsibility |
|----------|----------------------|-------------------|
| `exact_duplicates` | Hash-verified 100% matches | Report directly (no LLM needed) |
| `similarity_candidates` | 40-95% similar pairs | Classify: true_dup / similar_concept / false_positive |

### Exact Duplicates (Script-Detected)

Script uses SHA256 hashing on normalized content (markdown/code stripped, whitespace normalized).

**Output from script**:
```json
{
  "exact_duplicates": [
    {
      "hash": "abc123...",
      "occurrences": [
        {"file": "file-a.md", "section": "X", "lines": "10-20"},
        {"file": "file-b.md", "section": "Y", "lines": "30-40"}
      ],
      "line_count": 10,
      "recommendation": "consolidate"
    }
  ]
}
```

**Action**: Report directly, consolidate without LLM judgment.

### Similarity Candidates (LLM Analysis Required)

Script calculates similarity using `difflib.SequenceMatcher` (40-95% threshold).

**For each similarity_candidate, LLM must**:
1. Read both content blocks
2. Classify:
   - `true_duplicate` - Same content, should consolidate
   - `similar_concept` - Related but different, cross-reference OK
   - `false_positive` - Unrelated despite textual similarity
3. Recommend action:
   - `consolidate` - Merge into single authoritative location
   - `cross_reference` - Keep both, add links between them
   - `keep_both` - Intentionally different content

### LLM Classification Criteria

**true_duplicate** indicators:
- Same rules/requirements stated
- Same examples with minor formatting differences
- Same step sequences

**similar_concept** indicators:
- Same topic but different perspectives
- Overview vs detailed treatment
- Different contexts for same pattern

**false_positive** indicators:
- Common technical terms causing false match
- Boilerplate/template text
- Different subjects with similar phrasing

### Output Format

**Exact (from script)**:
```
Exact Duplicate:
  Hash: {hash}
  Locations: {file1}:{lines}, {file2}:{lines}
  Line count: {N}
  Action: Consolidate (auto-detected)
```

**Similarity (LLM classified)**:
```
Similarity Candidate:
  Source: {file1}:{section}:{lines}
  Target: {file2}:{section}:{lines}
  Similarity: {percentage}%
  Classification: {true_duplicate|similar_concept|false_positive}
  Recommendation: {consolidate|cross_reference|keep_both}
```

### Resolution Strategies

| Classification | Action |
|----------------|--------|
| Exact duplicate | Consolidate to authoritative location, delete other |
| true_duplicate | Same as exact - consolidate |
| similar_concept | Add cross-references between files |
| false_positive | No action needed |

---

## Dimension 3: Consistency Analysis (Cross-File)

### Script Pre-Processing

The `analyze-cross-file-content.py` script extracts terminology and detects variants:

**Script Output**:
```json
{
  "terminology_variants": [
    {
      "concept": "cross-reference",
      "variants": [
        {"term": "cross-reference", "files": ["a.md"], "count": 12},
        {"term": "xref", "files": ["b.md", "c.md"], "count": 8}
      ],
      "recommendation": "standardize on 'cross-reference'"
    }
  ]
}
```

**Known Synonym Groups** (script detects these):
- `cross-reference`, `xref`, `internal link`, `cross-ref`
- `workflow`, `process`, `procedure`, `protocol`
- `must`, `shall`, `required`, `mandatory` (RFC 2119)
- `should`, `recommended`, `advisable`
- `may`, `optional`, `can`
- `skill`, `plugin`, `component`
- `agent`, `assistant`, `bot`
- `command`, `slash command`, `directive`

### LLM Analysis for Terminology

**For each terminology_variant, LLM must**:
1. Review the variants and their usage contexts
2. Determine if standardization is needed
3. Recommend preferred term based on:
   - Most common usage in codebase
   - Industry/domain standards
   - Clarity and precision

### What Else to Check (LLM-Only)

**Formatting Consistency**:
- Header level usage
- List style (bullet vs numbered)
- Code block formatting

**Style Consistency**:
- Imperative vs declarative tone
- "You should..." vs "Must..." vs "Use..."
- Active vs passive voice

### Output Format

**Terminology (from script + LLM)**:
```
Terminology Variant:
  Concept: {concept}
  Variants found:
    - "{term1}" in: {file1}, {file2} (count: N)
    - "{term2}" in: {file3}, {file4} (count: N)
  LLM Recommendation: Standardize on "{preferred_term}"
  Action: {standardize|keep_variants}
```

### Terminology Standardization

| Variations Found | Recommended Standard |
|------------------|---------------------|
| cross-reference, xref, internal link | "cross-reference" (prose), "xref:" (syntax) |
| workflow, process, procedure | "workflow" (in skills), "procedure" (in docs) |
| must, should, may | Follow RFC 2119 strictly |

---

## Dimension 4: Contradiction Analysis

### What to Check

**Direct Contradictions**:
- Conflicting rules (e.g., different line limits)
- Opposite recommendations
- Mutually exclusive requirements

**Implicit Contradictions**:
- Examples that violate stated rules
- Exceptions that undermine main guidance
- "Always X" in one file, "Never X" in another

**Version Drift**:
- Old guidance not updated when rules changed
- Legacy examples with deprecated patterns

### Detection Approach

1. Extract all rules/requirements from files
2. Compare rule statements for conflicts
3. Check examples against stated rules
4. Verify cross-references are current

### Output Format

```
Contradiction Found:
  File 1: {path1}
    Line {N}: "{statement1}"
  File 2: {path2}
    Line {N}: "{statement2}"
  Nature: {direct|implicit|version_drift}
  Resolution: {recommendation}
```

### Resolution Strategies

| Type | Action |
|------|--------|
| Direct | Determine authoritative source, update other |
| Implicit | Fix examples to match rules |
| Version Drift | Update legacy content |

---

## Aggregate Quality Score

Combine dimension scores:

```
Quality Score = (Completeness + (100 - Duplication) + Consistency + (100 - Contradictions)) / 4
```

| Score | Rating | Action |
|-------|--------|--------|
| 90-100 | Excellent | Minor improvements only |
| 70-89 | Good | Address identified issues |
| 50-69 | Fair | Significant work needed |
| 0-49 | Poor | Major refactoring required |

---

## Quality Report Format

```markdown
# Content Quality Analysis

**Skill**: {skill_name}
**Files Analyzed**: {count}
**Overall Score**: {score}/100

## Completeness (Score: {X}/100)

{findings}

## Duplication (Score: {X}/100)

{findings}

## Consistency (Score: {X}/100)

{findings}

## Contradictions (Score: {X}/100)

{findings}

## Recommendations

### High Priority
1. {action}

### Medium Priority
1. {action}

### Low Priority
1. {action}
```

---

## Dimension 5: Extraction Analysis (Cross-File)

### Script Pre-Processing

The `analyze-cross-file-content.py` script detects extraction candidates:

**Script Output**:
```json
{
  "extraction_candidates": [
    {
      "type": "template",
      "pattern": "placeholder_structure",
      "file": "guide.md",
      "section": "Report Format",
      "lines": "100-120",
      "detected_placeholders": ["{{PROJECT}}", "{{VERSION}}"],
      "recommendation": "extract_to_templates"
    },
    {
      "type": "workflow",
      "pattern": "step_sequence",
      "file": "guide.md",
      "section": "Setup Process",
      "lines": "200-250",
      "step_count": 5,
      "recommendation": "extract_to_workflows"
    }
  ]
}
```

### Detection Patterns

**Template Patterns** (script detects):
- `{{PLACEHOLDER}}` - Double-brace placeholders
- `{placeholder}` - Single-brace placeholders
- `[INSERT NAME]` - Bracket insert markers
- `<PLACEHOLDER>` - Angle bracket markers

**Workflow Patterns** (script detects):
- `### Step N` - Numbered step headers
- `### Phase N` - Numbered phase headers
- `1. **Action**:` - Numbered bold-labeled actions (3+ required)

### LLM Analysis for Extraction

**For each extraction_candidate, LLM must**:
1. Review the detected patterns in context
2. Determine if extraction improves organization:
   - Would it reduce duplication?
   - Would it enable reuse?
   - Is content general enough to extract?
3. Recommend action:
   - `extract_to_templates` - Content is reusable template
   - `extract_to_workflows` - Content is reusable workflow
   - `keep_inline` - Content is context-specific, don't extract

### Output Format

```
Extraction Candidate:
  File: {file}
  Section: {section}
  Lines: {start}-{end}
  Type: {template|workflow}
  Pattern: {placeholder_structure|step_sequence}
  Detected: {placeholders/step_count}
  LLM Recommendation: {extract_to_templates|extract_to_workflows|keep_inline}
  Reasoning: {why extract or keep inline}
```

### Extraction Guidelines

| Pattern Type | Extract If | Keep Inline If |
|--------------|-----------|----------------|
| Template | Used in 2+ places, general-purpose | Context-specific, one-time use |
| Workflow | Reusable process, clear steps | Integrated narrative, explanatory |

---

## Verification of LLM Findings

After LLM analysis, run `validate cross-file` to validate claims:

```bash
echo '{llm_findings_json}' | python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:validate cross-file --analysis {script_analysis_json}
```

**Verification Output**:
```json
{
  "verified": [...],      // LLM claims confirmed by script
  "rejected": [...],      // LLM claims that couldn't be verified
  "warnings": [...],      // Potential issues
  "summary": {
    "verification_rate": 95.0,
    "verified_count": 19,
    "rejected_count": 1
  }
}
```

**Reject claims** that can't be verified against actual content.

---

## Integration with doctor-skill-content Workflow

This guide is loaded in **Phase 3: Analyze Content Quality**.

### Step-by-Step Integration

1. **Run cross-file analysis script**:
   ```bash
   python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:analyze cross-file --skill-path {skill_path} > analysis.json
   ```

2. **Report exact duplicates directly** (no LLM needed):
   - Parse `exact_duplicates` from JSON
   - Generate consolidation recommendations

3. **LLM analyzes candidates**:
   - Read `similarity_candidates` and classify each
   - Read `extraction_candidates` and recommend actions
   - Read `terminology_variants` and recommend standardization

4. **LLM performs single-file quality checks**:
   - Completeness (TODO markers, missing examples)
   - Contradictions (conflicting rules)

5. **Verify LLM findings**:
   ```bash
   echo '{llm_output}' | python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:validate cross-file --analysis analysis.json
   ```

6. **Generate quality report** with verified findings only.

### Token Optimization

The LLM-hybrid approach reduces token usage:
- Script handles 100% matches without LLM
- Only 40-95% similarity pairs need LLM review
- Verification catches hallucinated findings
