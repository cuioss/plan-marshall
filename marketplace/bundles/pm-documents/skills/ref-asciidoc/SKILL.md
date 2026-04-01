---
name: ref-asciidoc
description: AsciiDoc formatting, validation, link verification, and template creation workflows
user-invocable: false
---

# AsciiDoc Skill

## Enforcement

**Execution mode**: Select workflow and execute immediately using documented script commands.

**Prohibited actions:**
- Do not invoke scripts with arguments other than those documented in workflow steps
- Do not skip the manual verification step in verify-links workflow
- Do not modify AsciiDoc files without first running validate-format

**Constraints:**
- Run scripts EXACTLY as documented using `python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc ...`
- Always load documentation standards before executing format or validation workflows
- Use ref-documentation for content quality concerns; this skill covers syntax and format only

---

Standards and workflows for AsciiDoc formatting, validation, link verification, and document creation from templates.

**Note**: This skill covers AsciiDoc syntax and format. For content quality, tone, and review orchestration, use `pm-documents:ref-documentation`.

## Available Workflows

This skill provides five specialized workflows:

| Workflow | Purpose | Script Used |
|----------|---------|-------------|
| **format-document** | Auto-fix AsciiDoc formatting issues | `pm-documents:ref-asciidoc:asciidoc format` |
| **validate-format** | Validate AsciiDoc format compliance | `pm-documents:ref-asciidoc:asciidoc validate` |
| **verify-links** | Verify links and cross-references | `pm-documents:ref-asciidoc:asciidoc verify-links` |
| **create-from-template** | Create new document from template | Templates in templates/ |
| **refresh-metadata** | Update metadata and cross-references | Read + Edit |

## Workflow: format-document

Auto-fix common AsciiDoc formatting issues with safety features.

### What It Fixes

- Add blank lines before lists
- Convert deprecated `<<>>` syntax to `xref:`
- Fix header attributes
- Remove trailing whitespace

### Parameters

- `target` (required): File path or directory path
- `fix_types` (optional, default: "all"): Types of fixes: "lists", "xref", "headers", "whitespace", "all"

### Steps

**Step 1: Load Documentation Standards**

Read references/asciidoc-formatting.md

**Step 2: Discover Files**

If target is a file:
- Verify file exists and has `.adoc` extension

If target is a directory:
- Use Glob: `{directory}/*.adoc` (non-recursive)
- Filter out `target/` directories

**Step 3: Run Auto-Formatter**

Build command with options:

- If `fix_types` is "all": omit the `-t` flag
- If `fix_types` is specific (e.g., "lists", "xref"): add `-t {fix_type}`

```bash
python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc format [-t {fix_type}] --path {target}
```

**Step 4: Parse Output**

Extract statistics:
- Files processed
- Files modified
- Issues fixed
- Fix details per file

**Step 5: Report Results**

```
Format Fixes Applied to {target}
Files modified: {count}
Issues fixed: {count}
Changes applied: {list}
```

**Step 6: Validation (after changes applied)**

Run validation:

```bash
python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc validate --path {target}
```

---

## Workflow: validate-format

Validate AsciiDoc files for format compliance.

### What It Checks

- Section headers with blank lines
- Proper list formatting
- Blank lines before/after lists
- Code block formatting

### Parameters

- `target` (required): File path or directory path
- `apply_fixes` (optional, default: false): Apply automatic fixes

### Steps

**Step 1: Load Documentation Standards**

Read references/asciidoc-formatting.md

**Step 2: Discover Files**

If target is a file:
- Verify file exists and has `.adoc` extension

If target is a directory:
- Use Glob: `{directory}/*.adoc` (non-recursive)

**Step 3: Run Format Validation**

```bash
python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc validate --path {target}
```

**Step 4: Parse Output**

Extract warnings matching `Line [0-9]+`:
- Categorize issues by type
- Track by file and line number

**Step 5: Apply Fixes (if requested)**

If apply_fixes=true:
- For each issue, read file context (±5 lines)
- Use Edit tool to fix the issue
- Track fixes applied

**Step 6: Re-Validate (if fixes applied)**

Re-run validator and compare:
- Before: {total_issues}
- After: {remaining_issues}
- Fixed: {fixed_count}

**Step 7: Generate Report**

```
## AsciiDoc Format Validation Complete

**Status**: PASS | WARNINGS | FAILURES

**Summary**: Validated {file_count} file(s)

**Metrics**:
- Files validated: {count}
- Format issues found: {count}
- Issues fixed: {count}
- Issues remaining: {count}

**Issues by Category**:
- Blank line after header: {count}
- Blank line before list: {count}
- Other format violations: {count}

**Details by File**:
### {file_1}
- Line {N}: {issue description}
- Status: Clean | Issues remaining
```

---

## Workflow: verify-links

Verify all links and cross-references in AsciiDoc files.

### What It Verifies

- Cross-reference file links (xref:)
- Internal anchor references (<<anchor>>)
- Link formats and syntax

### Parameters

- `target` (required): File path or directory path
- `fix_links` (optional, default: false): Fix broken links

### Steps

**Step 1: Load Documentation Standards**

Read references/asciidoc-formatting.md

**Step 2: Discover Files**

If target is a file:
- Verify file exists and has `.adoc` extension

If target is a directory:
- Use Glob: `{directory}/*.adoc` (non-recursive)

**Step 3: Setup Report Directory**

```bash
mkdir -p target/asciidoc-link-verifier
```

**Step 4: Run Link Verification**

```bash
python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc verify-links --file {file_path} --report target/asciidoc-link-verifier/links.md
```

For directories:
```bash
python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc verify-links --directory {directory} --report target/asciidoc-link-verifier/links.md
```

**Step 5: Parse Report**

Read `target/asciidoc-link-verifier/links.md` and extract:
- Broken file links
- Broken anchors
- Format violations

**Step 6: Manual Verification (CRITICAL)**

For each "broken" link reported:
1. Extract target path
2. Resolve absolute path: `realpath {relative_target_path}`
3. Verify with Read tool
4. If file EXISTS but script reported broken: Report false positive
5. If file NOT FOUND: Confirm broken

**Step 7: Fix Internal Anchors (if approved)**

For missing anchors:
1. Search for matching section header
2. Add anchor ID: `[#anchor-id]` before header
3. Use Edit tool

**Step 8: Generate Report**

```
## AsciiDoc Link Verification Complete

**Status**: PASS | WARNINGS | FAILURES

**Summary**: Verified links in {file_count} file(s)

**Metrics**:
- Files verified: {count}
- Broken file links: {count}
- Broken anchors: {count}
- Issues fixed: {count}

**Details by File**:
### {file_1}
- Line {N}: xref to {target} - {status}
- Line {N}: anchor <<{id}>> - {status}
```

---

## Workflow: create-from-template

Create new AsciiDoc documents from predefined templates.

### What It Creates

- Standard specification documents
- README files
- How-to guides

### Parameters

- `type` (required): standard|readme|guide
- `name` (required): Document name (used in title and filename)
- `path` (optional): Output path (default: inferred from type)

### Steps

**Step 1: Validate Parameters**

```
If type not in [standard, readme, guide]:
  Error: "Invalid type. Use: standard, readme, guide"

If name is empty:
  Error: "Name is required"
```

**Step 2: Determine Output Path**

```
If path not specified:
  standard → standards/{name}.adoc
  readme   → {name}/README.adoc or README.adoc
  guide    → docs/{name}.adoc
```

**Step 3: Load Template**

Read template from templates/:
- standard → templates/standard-template.adoc
- readme   → templates/readme-template.adoc
- guide    → templates/guide-template.adoc

**Step 4: Substitute Placeholders**

Replace template placeholders:
- `{{TITLE}}` → Formatted name
- `{{PROJECT_NAME}}` → Name
- `{{GUIDE_TITLE}}` → Formatted guide title
- `{{DESCRIPTION}}` → Empty (user fills in)
- `{{SHORT_DESCRIPTION}}` → Empty (user fills in)
- `{{PURPOSE}}` → Empty (user fills in)

**Step 5: Write File**

Use Write tool to create file at output path.

**Step 6: Validate Created File**

Execute validate-format workflow on new file.

**Step 7: Report Result**

```
Document Created: {output_path}
Type: {type}
Status: Valid format

Next steps:
1. Edit {output_path} to fill in content
2. Run ref-asciidoc validate-format workflow on {output_path} to validate
```

---

## Workflow: refresh-metadata

Update metadata, fix cross-references, and refresh table of contents.

### What It Does

- Updates document metadata
- Fixes broken cross-references
- Regenerates table of contents

### Parameters

- `target` (required): File or directory

### Steps

**Step 1: Discover Files**

```
If target is file:
  files = [target]
If target is directory:
  Use Glob: {target}/**/*.adoc
```

**Step 2: Analyze Metadata**

For each file:
- Check header attributes (:toc:, :sectnums:, etc.)
- Identify missing or outdated metadata

**Step 3: Analyze Cross-References**

```
Execute verify-links workflow
Collect: broken internal references
```

**Step 4: Fix Cross-References**

For each broken reference:
1. Search for target content by title/anchor
2. If found at new location: Update reference
3. If not found: Report for manual review

**Step 5: Update Metadata**

Using Edit tool:
- Ensure standard header attributes present
- Fix attribute formatting

**Step 6: Generate Report**

```
Metadata Refresh Complete

Files processed: {count}

Updates Applied:
- Metadata fixed: {count}
- Cross-references fixed: {count}
- Headers updated: {count}

Manual Review Needed:
- {file}: {reason}
```

---

## Reference Documents

All reference material is in the `references/` directory:

| Reference | Purpose | When to Load |
|-----------|---------|--------------|
| `asciidoc-formatting.md` | AsciiDoc format rules | Format/validation workflows |
| `readme-structure.md` | README structure patterns | README files |

## Workflow Documents

All workflow procedures are in the `workflows/` directory:

| Workflow | Purpose | When to Load |
|----------|---------|--------------|
| `link-verification.md` | Link verification protocol with manual Read verification | Link workflows |

## Scripts

Script: `pm-documents:ref-asciidoc` → `asciidoc.py`

| Subcommand | Description |
|------------|-------------|
| `stats` | Generate documentation statistics |
| `validate` | Validate AsciiDoc files for compliance |
| `format` | Auto-fix AsciiDoc formatting issues |
| `verify-links` | Verify links and cross-references |
| `classify-links` | Classify broken links to reduce false positives |

**Usage Examples:**
```bash
# Generate statistics
python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc stats -f json --directory /path/to/docs

# Validate formatting
python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc validate --path /path/to/file.adoc

# Format files
python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc format -t all --path /path/to/docs

# Verify links
python3 .plan/execute-script.py pm-documents:ref-asciidoc:asciidoc verify-links --directory /path/to/docs
```
