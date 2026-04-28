---
name: ref-documentation
description: Content quality, tone analysis, organization standards, and review orchestration for technical documentation
user-invocable: false
---

# Documentation Skill

## Enforcement

**Execution mode**: Select workflow and execute immediately using documented script commands.

**Prohibited actions:**
- Do not invoke scripts with arguments other than those documented in workflow steps
- Do not apply major content changes without asking the user first
- Do not use this skill for AsciiDoc formatting; use ref-asciidoc instead

**Constraints:**
- Run scripts EXACTLY as documented using `python3 .plan/execute-script.py pm-documents:ref-documentation:docs ...`
- Always load tone-and-style standards before executing content review workflows
- Use ref-asciidoc for syntax and formatting concerns; this skill covers content quality only

---

Standards and workflows for content quality, tone, organization, and review orchestration of technical documentation.

**Note**: This skill covers content quality and review. For AsciiDoc formatting, validation, and link verification, use `pm-documents:ref-asciidoc`.

For code documentation, use:
- `pm-dev-java:javadoc` for Java code documentation
- `pm-dev-frontend:javascript` for JavaScript documentation

## Available Workflows

This skill provides four specialized workflows:

| Workflow | Purpose | Script Used |
|----------|---------|-------------|
| **review-content** | Review content quality and tone | `pm-documents:ref-documentation:docs review` |
| **comprehensive-review** | Orchestrate all review workflows | All scripts (format → links → content) |
| **sync-with-code** | Sync documentation with code changes | Analysis + Edit |
| **cleanup-stale** | Remove stale/duplicate documentation | `manage-files discover` + Read + analysis |

## Workflow: review-content

Review AsciiDoc content for quality: correctness, clarity, tone, style, and completeness.

### What It Reviews

- **Correctness**: Factual claims, RFC citations, verifiable statements
- **Clarity**: Concise, unambiguous, clear explanations
- **Tone & Style**: Professional, technical, no marketing language
- **Consistency**: Terminology, formatting patterns
- **Completeness**: No missing sections, TODOs, or gaps

### Parameters

- `target` (required): File path or directory path
- `apply_fixes` (optional, default: false): Apply content fixes

### Steps

**Step 1: Load Documentation Standards**

Read references/tone-and-style.md
Read references/documentation-core.md

**Step 2: Discover Files**

If target is a file:
- Verify file exists and has `.adoc` extension

If target is a directory, run the canonical `manage-files discover` resolver and capture the returned `paths` array as the discovered file list.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files discover \
  --root {directory} \
  --glob "*.adoc" \
  --include-files
```

**Step 3: Run Content Analysis**

```bash
python3 .plan/execute-script.py pm-documents:ref-documentation:docs review --file {file_path}
```

For directories:
```bash
python3 .plan/execute-script.py pm-documents:ref-documentation:docs review --directory {directory}
```

**Step 4: Parse Output**

Script returns structured output with analysis data including files analyzed, quality score, and issues with file, line, type, severity, and message fields.

**Step 5: Apply Deep Analysis**

For each issue from script, apply Claude judgment:
- Is the marketing language truly promotional or factual?
- Can claims be verified from context?
- Are TODOs appropriate (e.g., in development docs)?

**Step 6: Categorize by Priority**

**Priority 1 - CRITICAL:**
- Unverified factual claims
- Marketing/promotional language
- Transitional markers in specification docs

**Priority 2 - HIGH:**
- Clarity problems
- Tone issues
- Consistency violations

**Priority 3 - MEDIUM:**
- Minor wording improvements

**Step 7: Apply Fixes (if requested)**

If apply_fixes=true:
- For Priority 1 and 2 issues
- Read file context
- Use Edit tool for fixes
- Ask user before major changes

**Step 8: Generate Report**

```
## Content Review Complete

**Status**: PASS | WARNINGS | FAILURES

**Summary**: Reviewed {file_count} file(s)

**Quality Score**: {average_score}/100

**Metrics**:
- Files reviewed: {count}
- Tone issues: {count}
- Correctness issues: {count}
- Completeness issues: {count}

**Issues by Priority**:
- CRITICAL: {count}
- HIGH: {count}
- MEDIUM: {count}

**Details by File**:
### {file_1}

**Tone Issues:**
- Line {N}: {description}
  - Current: "{text}"
  - Suggested: "{improved}"

**Correctness Issues:**
- Line {N}: {description}

**Completeness Issues:**
- Line {N}: {description}
```

---

## Workflow: comprehensive-review

Orchestrate all review workflows for thorough documentation quality assurance.

### What It Does

Runs three phases in sequence with intelligent failure handling:
1. **Format Validation** via `pm-documents:ref-asciidoc` (fail-fast on errors)
2. **Link Verification** via `pm-documents:ref-asciidoc` (continue regardless)
3. **Content Quality Review** (continue regardless)

Provides consolidated report with aggregated results.

### Parameters

- `target` (required): File path or directory path
- `stop_on_error` (optional, default: true): Stop on format errors (Phase 1 failure)
- `apply_fixes` (optional, default: false): Attempt auto-fixes in all phases
- `skip_content` (optional, default: false): Skip Phase 3 (content review)

### Steps

**Step 1: Load Orchestration Standards**

Read workflows/review-orchestration.md for detailed phase sequencing, failure handling, and consolidated report template.
Read workflows/content-review.md for the tone analysis decision framework.

**Step 2: Discover Files**

If target is a file:
- Verify file exists and has `.adoc` extension

If target is a directory, run the canonical `manage-files discover` resolver and capture the returned `paths` array as the discovered file list. Filter out any path under a `target/` build directory afterwards.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files discover \
  --root {directory} \
  --glob "*.adoc" \
  --include-files
```

**Step 3: Phase 1 - Format Validation**

Delegate to ref-asciidoc validate-format workflow:
```
Skill: pm-documents:ref-asciidoc
Execute workflow: validate-format
Parameters:
  target: {target}
  apply_fixes: {apply_fixes}
```

If format FAILURES found AND stop_on_error=true: **STOP** and generate partial report.
Otherwise: **CONTINUE** to Phase 2.

**Step 4: Phase 2 - Link Verification**

Delegate to ref-asciidoc verify-links workflow, then classify results:

```bash
python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc classify-links --input target/links.json --output target/classified.json
```

For `must-verify-manual` links, follow the manual verification protocol in workflows/review-orchestration.md.

**CONTINUE** to Phase 3 regardless of link results.

**Step 5: Phase 3 - Content Quality Review**

Skip if skip_content=true. Run tone analysis:

```bash
python3 .plan/execute-script.py pm-documents:ref-documentation:docs analyze-tone --file {file_path} --output target/tone-analysis.json
```

Apply the tone analysis decision framework from workflows/content-review.md to each flagged phrase.

**Step 6: Aggregate and Report**

Combine all phase results and generate consolidated report following the template in workflows/review-orchestration.md.

Overall status: PASS (zero issues), WARNINGS (non-critical), FAILURES (critical issues found).

---

## Workflow: sync-with-code

Analyze code changes and update documentation to stay in sync.

### What It Does

- Detects code structure changes
- Identifies documentation drift
- Suggests or applies updates

### Parameters

- `target` (required): Documentation file or directory
- `code_path` (optional): Code directory to analyze (default: src/)

### Steps

**Step 1: Analyze Code Structure**

Run the canonical `manage-files discover` resolver to enumerate code files under `{code_path}`. Pass each language extension as a separate `--glob` flag — results are deduplicated and sorted by the resolver. Capture the returned `paths` array as the code file list.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files discover \
  --root {code_path} \
  --glob "**/*.java" \
  --glob "**/*.js" \
  --glob "**/*.ts" \
  --include-files
```

Then extract from each file:
- Public classes/interfaces
- Public methods
- Configuration patterns

**Step 2: Analyze Documentation**

```
Read target documentation files
Extract:
- Documented classes/methods
- Code examples
- Configuration references
```

**Step 3: Identify Drift**

Compare code vs documentation:
- Missing documentation for new code
- Outdated documentation for changed code
- Documentation for removed code

**Step 4: Generate Sync Report**

```
Documentation Sync Analysis

Code analyzed: {file_count} files
Documentation analyzed: {doc_count} files

Drift Detected:
- New code needing docs: {count}
- Outdated documentation: {count}
- Stale documentation: {count}

Details:
{list of specific drift items}

Recommendations:
{specific actions to sync}
```

**Step 5: Apply Updates (if requested)**

For each drift item:
- Ask user for confirmation
- Use Edit tool to update documentation
- Re-validate after changes

---

## Workflow: cleanup-stale

Identify and remove stale or duplicate documentation.

### What It Does

- Finds duplicate content across files
- Identifies orphaned documentation
- Suggests cleanup actions

### Parameters

- `target` (required): Directory to analyze

### Steps

**Step 1: Discover Documentation**

Run the canonical `manage-files discover` resolver and capture the returned `paths` array as the discovered file list. Filter out any path under `target/` or `node_modules/` afterwards.

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files discover \
  --root {target} \
  --glob "**/*.adoc" \
  --include-files
```

**Step 2: Analyze Content**

For each file:
- Extract title and sections
- Calculate content hash
- Track cross-references

**Step 3: Identify Candidates**

**Duplicates:**
- Files with >80% similar content
- Identical sections across files

**Orphaned:**
- Files not referenced from anywhere
- Files with broken incoming links

**Stale:**
- Files with TODO markers older than threshold
- Files not updated in extended period

**Step 4: Generate Cleanup Report**

```
Documentation Cleanup Analysis

Files analyzed: {count}

Candidates for Cleanup:
- Potential duplicates: {count}
- Orphaned files: {count}
- Stale content: {count}

Duplicates:
{file1} <-> {file2}: {similarity}%

Orphaned:
{file}: No incoming references

Stale:
{file}: Contains {N} TODOs

Recommendations:
1. {specific action}
```

**Step 5: Execute Cleanup (with confirmation)**

For each approved removal:
1. Update files that reference removed content
2. Remove or consolidate file
3. Re-validate cross-references

---

## Reference Documents

All reference material is in the `references/` directory:

| Reference | Purpose | When to Load |
|-----------|---------|--------------|
| `documentation-core.md` | Core documentation principles | Always |
| `tone-and-style.md` | Tone and style requirements | Content review workflow |
| `organization-standards.md` | Document organization | Structure reviews |

## Workflow Documents

All workflow procedures are in the `workflows/` directory:

| Workflow | Purpose | When to Load |
|----------|---------|--------------|
| `content-review.md` | Tone analysis decision framework | Content review workflow |
| `review-orchestration.md` | Comprehensive review orchestration | comprehensive-review workflow |

## Scripts

Script: `pm-documents:ref-documentation` → `docs.py`

| Subcommand | Description |
|------------|-------------|
| `review` | Analyze content for quality issues |
| `analyze-tone` | Detect promotional language and missing sources |

**Usage Examples:**
```bash
# Review content quality
python3 .plan/execute-script.py pm-documents:ref-documentation:docs review --file /path/to/file.adoc

# Analyze tone
python3 .plan/execute-script.py pm-documents:ref-documentation:docs analyze-tone --file /path/to/file.adoc --output report.json
```

## Usage from Commands

Commands invoke this skill and its workflows:

```markdown
# In command file
Skill: pm-documents:ref-documentation

# Then specify workflow
Execute workflow: review-content
Parameters:
  target: "standards/"
```

## Quality Verification Rules

All documentation must pass:

- Professional, neutral tone (no marketing language)
- Proper AsciiDoc formatting (via ref-asciidoc)
- Complete code examples
- Verified references
- Consistent terminology
- Documents only existing features
- All links valid (via ref-asciidoc)
