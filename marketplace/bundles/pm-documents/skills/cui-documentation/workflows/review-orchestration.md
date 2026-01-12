= Documentation Review Orchestration Workflow
:toc: left
:toclevels: 3
:sectnums:

== Overview

This standard defines the orchestration workflow for comprehensive AsciiDoc documentation review. It coordinates three specialized workflows (format, links, content) into a unified review process with proper sequencing, failure handling, and consolidated reporting.

== Orchestration Principle

**Sequential execution with fail-fast:** Format validation must pass before proceeding to links and content review. This prevents wasting effort on documents with structural issues.

== Workflow Phases

=== Phase 1: Format Validation

**Purpose:** Verify AsciiDoc structural correctness

**Actions:**

* Execute validate-format workflow
* Check for syntax errors, invalid attributes, malformed blocks
* Verify document structure (headers, sections, lists)

**Success Criteria:** Zero format errors

**On Failure:**

* **STOP** - Do not proceed to Phase 2 or 3
* Report format issues
* Suggest: Fix format errors before link/content review

**Rationale:** Broken format may cause invalid link detection or content parsing errors.

=== Phase 2: Link Verification

**Purpose:** Verify all cross-references and links

**Actions:**

* Execute verify-links workflow
* Check file links (xref:)
* Verify internal anchors
* Validate external URLs (if configured)

**Success Criteria:** All links resolve correctly (or false positives documented)

**On Failure:**

* **CONTINUE** to Phase 3 (content issues independent of links)
* Record link issues for final report

**Rationale:** Link issues don't prevent content quality assessment.

=== Phase 3: Content Quality Review

**Purpose:** Analyze documentation quality and tone

**Actions:**

* Execute review-content workflow
* Check factual accuracy and citations
* Analyze tone for promotional language
* Verify completeness and consistency

**Success Criteria:** No critical content issues

**On Failure:**

* Record content issues for final report

== Orchestration Flow

[source]
----
┌─────────────────────────────────────┐
│  Start: Comprehensive Review        │
│  Input: file_path or directory_path │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Discover Files                     │
│  - Single file OR                   │
│  - Directory (non-recursive *.adoc) │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Phase 1: Format Validation         │
│  Workflow: validate-format          │
└──────────────┬──────────────────────┘
               │
               ├─[ERRORS]──> STOP & Report
               │
               ├─[PASS]──────┐
               │              │
               ▼              │
┌─────────────────────────────────────┐
│  Phase 2: Link Verification         │
│  Workflow: verify-links             │
└──────────────┬──────────────────────┘
               │
               │ [Continue regardless]
               │
               ▼
┌─────────────────────────────────────┐
│  Phase 3: Content Review            │
│  Workflow: review-content           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Aggregate Results                  │
│  Generate Consolidated Report       │
└──────────────┬──────────────────────┘
               │
               ▼
           [Complete]
----

== Workflow Parameters

=== comprehensive-review Workflow

**Parameters:**

[cols="1,1,1,2"]
|===
|Parameter |Type |Default |Description

|target
|string
|(required)
|File path or directory path to review

|stop_on_error
|boolean
|true
|Stop on format errors (Phase 1 failure)

|apply_fixes
|boolean
|false
|Attempt to auto-fix issues (format and links)

|skip_content
|boolean
|false
|Skip Phase 3 (content review)
|===

**Examples:**

[source,yaml]
----
# Review single file with auto-fix
comprehensive-review:
  target: standards/security.adoc
  apply_fixes: true

# Review directory, continue on errors
comprehensive-review:
  target: standards/
  stop_on_error: false

# Fast structural check only
comprehensive-review:
  target: requirements/
  skip_content: true
----

== Failure Handling

=== Phase 1 Failure (Format Errors)

**Condition:** validate-format returns ERROR status

**Default Action (stop_on_error=true):**

1. Report format issues
2. **STOP orchestration**
3. Return partial results (format only)

**Message:**

[source]
----
Format validation FAILED with {count} errors.

Critical format issues must be fixed before link/content review.

Fix format errors and re-run comprehensive review.

Partial Results:
- Format: {error_count} errors
- Links: NOT RUN (blocked by format errors)
- Content: NOT RUN (blocked by format errors)
----

**Alternative Action (stop_on_error=false):**

1. Report format issues
2. **CONTINUE** to Phases 2 and 3
3. Mark results as "UNRELIABLE" due to format issues

=== Phase 2 Failure (Broken Links)

**Condition:** verify-links finds broken links

**Action:** Always **CONTINUE** to Phase 3

**Rationale:** Content quality independent of link status

=== Phase 3 Failure (Content Issues)

**Condition:** review-content finds tone/accuracy issues

**Action:** Report in consolidated results

== Consolidated Reporting

=== Report Structure

[source,markdown]
----
# Comprehensive AsciiDoc Review Report

**Target:** {file_path | directory_path}
**Date:** {ISO timestamp}
**Status:** ✅ PASS | ⚠️ WARNINGS | ❌ FAILURES

## Executive Summary

- Files reviewed: {count}
- Total issues: {count}
- Critical issues: {count}

### Issues by Phase

| Phase | Status | Issues |
|-------|--------|--------|
| Format Validation | {✅ PASS / ⚠️ WARN / ❌ FAIL} | {count} |
| Link Verification | {✅ PASS / ⚠️ WARN / ❌ FAIL} | {count} |
| Content Review | {✅ PASS / ⚠️ WARN / ❌ FAIL} | {count} |

## Phase 1: Format Validation

{Results from validate-format workflow}

### Critical Issues
- {file}:{line} - {issue description}

### Warnings
- {file}:{line} - {issue description}

## Phase 2: Link Verification

{Results from verify-links workflow}

### Broken Links
- {file}:{line} - xref:{target} - {reason}

### False Positives
- {file}:{line} - {link} - Verified manually as valid

## Phase 3: Content Review

{Results from review-content workflow}

### Promotional Language
- {file}:{line} - "{text}" - {category}

### Missing Sources
- {file}:{line} - Claim requires citation: "{text}"

### Unverified Claims
- {file}:{line} - Performance/compatibility claim without evidence

## Recommendations

### Immediate Actions (Critical)
1. {action required}

### Improvements (Warnings)
1. {suggested improvement}

### Next Steps
1. Fix critical issues
2. Re-run comprehensive review
3. Address warnings iteratively

## Tool Usage Statistics

- validate-format workflow: {execution_time}ms
- verify-links workflow: {execution_time}ms
- review-content workflow: {execution_time}ms
- Total execution time: {total_time}ms
----

=== Status Determination

**✅ PASS:**

* Zero errors in all phases
* Zero warnings (or only informational)

**⚠️ WARNINGS:**

* Non-critical issues found
* Broken links (if verified as false positives)
* Minor tone/style suggestions

**❌ FAILURES:**

* Format errors (Phase 1)
* Confirmed broken links requiring fixes
* Critical content issues (unverified claims, promotional language)

== When to Use Individual Workflows vs Orchestrated

=== Use Individual Workflows When:

**validate-format only:**

* Quick syntax check
* Pre-commit validation
* CI/CD pipeline check

**verify-links only:**

* After restructuring documentation
* Before major refactoring
* Periodic link maintenance

**review-content only:**

* Reviewing new documentation draft
* Tone/style review of existing docs
* Source citation audit

=== Use Orchestrated comprehensive-review When:

* **Initial documentation review:** New or external documentation
* **Pre-release quality gate:** Before publishing documentation
* **Periodic quality audit:** Quarterly documentation health check
* **Post-restructure verification:** After major documentation changes
* **Onboarding review:** Reviewing contributed documentation

== Integration Points

=== CI/CD Integration

**Pre-commit Hook:**

[source,bash]
----
# Quick format check only
python3 .plan/execute-script.py pm-documents:cui-documentation:docs validate-format --file $FILE

# Exit if format errors
if [ $? -ne 0 ]; then
  echo "Format errors found. Commit blocked."
  exit 1
fi
----

**Pull Request Check:**

[source,bash]
----
# Comprehensive review of changed files
for file in $(git diff --name-only --diff-filter=AM "*.adoc"); do
  # Run comprehensive review
  # (invoke via command/skill)
done
----

=== Command Integration

**doc-review-single-asciidoc command:**

* Runs comprehensive-review for single file
* Exposes all workflow parameters
* Returns consolidated report

**doc-review-technical-docs command:**

* Runs comprehensive-review for directory
* Iterates through all .adoc files
* Aggregates results across files

== Script Contracts

=== validate-format.py

**Input:** File path or directory

**Output:** JSON with syntax errors, invalid attributes, structure issues

**Exit Codes:**

* 0: Valid format
* 1: Format errors found
* 2: Script error

=== verify-links-false-positives.py

**Input:** Broken links JSON from verify-adoc-links.py

**Output:** JSON with categorized links (false-positive, must-verify, definitely-broken)

**Usage in orchestration:**

1. Run verify-adoc-links.py
2. Classify with verify-links-false-positives.py
3. Present categorized results to user

=== analyze-content-tone.py

**Input:** File path or directory

**Output:** JSON with flagged promotional language, missing sources, unverified claims

**Usage in orchestration:**

1. Run analyze-content-tone.py
2. Apply ULTRATHINK analysis to flagged sections
3. Generate content review findings

== Best Practices

=== For Documentation Authors

**Before Committing:**

1. Run validate-format locally
2. Fix any format errors
3. Run comprehensive-review periodically

**During Review Cycles:**

1. Use comprehensive-review for initial check
2. Use individual workflows for focused fixes
3. Re-run comprehensive-review before finalizing

=== For Reviewers

**Initial Review:**

1. Always start with comprehensive-review
2. Prioritize critical issues (format, broken links)
3. Address tone/content issues iteratively

**Follow-up Reviews:**

1. Use verify-links after link fixes
2. Use review-content after content updates
3. Final comprehensive-review before approval

=== For Automation

**CI Pipeline:**

* validate-format: Fast, fail-fast check
* comprehensive-review: Scheduled (nightly)
* Individual workflows: On-demand

**Quality Gates:**

* Pre-commit: Format validation (fast)
* Pre-merge: Comprehensive review (thorough)
* Pre-release: Comprehensive review + manual verification

== Error Recovery

=== Workflow Interruption

**Scenario:** Workflow fails mid-execution (network, script error)

**Recovery:**

1. Check partial results saved
2. Resume from last completed phase
3. Re-run only failed phase if possible

=== False Positive Handling

**Scenario:** Script reports issues that are actually valid

**Process:**

1. Use verify-links-false-positives.py for link classification
2. Manual verification with Read tool
3. Document false positives in report
4. Consider updating script patterns

== References

* xref:link-verification.md[Link Verification Protocol]
* xref:content-review.md[Content Review Framework]
* xref:../README.adoc[CUI Documentation Standards Overview]
