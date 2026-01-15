= Link Verification Protocol
:toc: left
:toclevels: 3
:sectnums:

== Overview

This standard defines the protocol for verifying links in AsciiDoc documentation, with critical emphasis on manual verification before any link removal to prevent accidental deletion of valid links.

== Core Principle

**NEVER blindly trust automated link verification tools.** Always perform manual verification with the Read tool before removing any link.

== Link Types

=== Cross-Reference File Links

Format: `xref:path/to/file.adoc[Link Text]`

**Characteristics:**

* Relative paths from current file's directory
* Must resolve to existing `.adoc` files
* Can include anchor fragments: `xref:file.adoc#section[Text]`

=== Internal Anchor References

Format: `<<anchor-id>>` or `<<anchor-id, Display Text>>`

**Characteristics:**

* Reference to section within same document
* Anchor defined with `[#anchor-id]` before section header
* Must match existing section anchor

=== External URLs

Format: `link:https://example.com[Text]` or `https://example.com`

**Characteristics:**

* External HTTP/HTTPS links
* May become broken over time
* Require network access to verify

== Verification Workflow

=== Step 1: Run Automated Detection

Execute the verify-adoc-links.py script to identify potential broken links:

[source,bash]
----
python3 .plan/execute-script.py pm-documents:ref-documentation:docs verify-links --file path/to/file.adoc --report target/links.md
----

**Output:** JSON report with broken link candidates

=== Step 2: Classify Broken Link Candidates

Use verify-links-false-positives.py to categorize detected issues:

[source,bash]
----
python3 .plan/execute-script.py pm-documents:ref-documentation:docs verify-false-positives --input target/links.json --output target/classified.json
----

**Categories:**

* `likely-false-positive`: Anchors, localhost, file:// URLs
* `must-verify-manual`: External links requiring Read verification
* `definitely-broken`: Non-existent files (verified by script)

=== Step 3: Manual Verification (CRITICAL)

For each link classified as `must-verify-manual` or `definitely-broken`:

==== Extract Target Path

From xref: `xref:../../doc/spec.adoc[Label]` → extract `../../doc/spec.adoc`

==== Resolve Absolute Path

[source,bash]
----
cd {directory_of_current_file}
realpath {relative_target_path}
----

**Example:**

* Current file: `/project/standards/logging/guide.adoc`
* Link target: `../../requirements/spec.adoc`
* Resolved: `/project/requirements/spec.adoc`

==== Verify with Read Tool

[source]
----
Read(file_path="/project/requirements/spec.adoc")
----

**Decision Matrix:**

[cols="1,1,2"]
|===
|Read Result |Script Report |Action

|Success (file exists)
|Broken
|**Keep link** - Script false positive

|Error (file not found)
|Broken
|**Ask user** - Genuinely broken

|Success
|Valid
|No action needed

|Error
|Valid
|Script missed issue - report to user
|===

==== Search for Similar Files (Optional)

If file not found, search for similar names:

[source,bash]
----
find project/requirements -name "*spec*" -type f
----

Suggest alternatives to user before removal.

=== Step 4: User Confirmation

**NEVER remove links without explicit user approval.**

**Confirmation Template:**

[source]
----
WARNING: About to remove cross-reference link

File: standards/logging/guide.adoc
Line: 42
Link: xref:../../requirements/spec.adoc[Requirements Specification]
Resolved Path: /project/requirements/spec.adoc
Status: File not found

Alternatives found:
- /project/requirements/specifications.adoc (similar name)
- /project/docs/requirements.adoc (similar path)

Actions:
1. Remove link
2. Update to alternative path
3. Keep link (manual review needed)

Select action [1/2/3]:
----

== False Positive Patterns

=== Acceptable Link Patterns (DO NOT REMOVE)

==== Internal Anchors

Format: `xref:file.adoc#anchor[Text]` or `<<anchor-id>>`

**Reason:** Anchor may exist but not detected by script if dynamically generated or in included files.

**Verification:** Read file and search for `[#anchor-id]` or matching section header.

==== Localhost URLs

Format: `link:http://localhost:8080[Dev Server]`

**Reason:** Intentional reference to local development environment.

**Action:** Keep - document as development URL.

==== File Protocol URLs

Format: `link:file:///path/to/local/file[Local File]`

**Reason:** Reference to local filesystem, may be valid on user's machine.

**Action:** Ask user - may be intentional local reference.

==== Generated Documentation

Format: `xref:target/generated/api-docs.adoc[API Docs]`

**Reason:** File generated during build, not present in source.

**Action:** Keep if referenced in build documentation.

== Internal Anchor Handling

=== When Anchor Not Found

**Strategy:** Add anchor before matching section header rather than removing reference.

==== Convert Anchor ID to Section Title

Rules:

* Replace hyphens with spaces: `owasp-top-10` → `owasp top 10`
* Capitalize words: `owasp top 10` → `OWASP Top 10`
* Preserve numbers: `2021` → `2021`
* Handle acronyms: `cwe` → `CWE`

==== Search for Matching Section

Read file and search for:

* Exact match: `== OWASP Top 10 2021`
* Partial match: `== OWASP Top 10`
* Case variations: `== Owasp top 10`

==== Add Anchor

If section found, add anchor immediately before header:

[source,asciidoc]
----
[#owasp-top-10-2021]
== OWASP Top 10 2021
----

**Format Rules:**

* Anchor line immediately before header (no blank line)
* Use `[#id]` format (NOT `[[id]]`)
* ID should be lowercase with hyphens

==== Report if Section Not Found

If no matching section:

[source]
----
WARNING: Anchor reference found but no matching section

Anchor: <<owasp-top-10-2021>>
File: security/guide.adoc
Line: 89

Searched for sections:
- "OWASP Top 10 2021" (not found)
- "OWASP Top 10" (not found)
- "Security Standards" (found at line 45)

Possible actions:
1. Add section "OWASP Top 10 2021"
2. Update reference to existing section
3. Remove reference

Select action [1/2/3]:
----

== Path Resolution

=== Relative Path Calculation

**Base Directory:** Directory containing the current AsciiDoc file (NOT project root).

**Resolution Steps:**

1. Extract current file's directory
2. Append relative path from xref
3. Normalize (resolve `..` and `.`)
4. Convert to absolute path

**Example:**

[source]
----
Current file:  /project/standards/java/logging.adoc
Link target:   ../../requirements/spec.adoc

Step 1: /project/standards/java/
Step 2: /project/standards/java/../../requirements/spec.adoc
Step 3: /project/requirements/spec.adoc (normalized)
----

=== Common Path Errors

==== Resolving from Wrong Base

**WRONG:**

[source,python]
----
# Resolving from project root
base = "/project/"
target = "../../requirements/spec.adoc"
# Results in /requirements/spec.adoc (outside project!)
----

**CORRECT:**

[source,python]
----
# Resolving from current file's directory
base = "/project/standards/java/"
target = "../../requirements/spec.adoc"
# Results in /project/requirements/spec.adoc
----

== Script Trust Policy

=== Script Output Classification

**Trust Level: LOW** - Always verify manually

**Known Script Limitations:**

* May not detect dynamically generated anchors
* May report false positives for included files
* May not handle complex path resolution
* May timeout on large documentation sets

=== When Script Reports "Broken"

**ALWAYS:**

1. Use Read tool to verify
2. Check for typos in script output
3. Look for alternative valid paths
4. Document discrepancies

**NEVER:**

1. Blindly remove links
2. Assume script is correct
3. Skip manual verification
4. Ignore path resolution

== Link Removal Policy

=== Criteria for Removal

Link may be removed ONLY if ALL conditions met:

1. **Script reports broken** - Automated detection flagged issue
2. **Manual verification confirms** - Read tool confirms file not found
3. **No alternatives found** - No similar files or updated paths exist
4. **User approves** - Explicit user confirmation received
5. **Documented** - Removal reason recorded in commit/report

=== Removal Process

==== Document Link Before Removal

Record in report:

[source]
----
Removed broken link:
- File: standards/security/guide.adoc
- Line: 125
- Link: xref:../../archive/old-spec.adoc[Old Specification]
- Target: /project/archive/old-spec.adoc
- Reason: File not found, confirmed with Read tool
- Alternatives searched: /project/archive/*.adoc (none found)
- User approval: Yes (timestamp)
----

==== Use Edit Tool

[source]
----
Edit(
  file_path="standards/security/guide.adoc",
  old_string="See xref:../../archive/old-spec.adoc[Old Specification] for details.",
  new_string="See archived specification (no longer available) for details."
)
----

**Preserve Context:** Don't remove entire sentence, just update reference.

== Re-validation

=== After Fixes Applied

**Always re-run verification** to confirm:

* Removed links no longer reported
* Added anchors resolve correctly
* No new issues introduced

=== Comparison Report

[source]
----
## Link Verification - Before/After

**Before Fixes:**
- Total issues: 15
- Broken file links: 8
- Missing anchors: 7

**After Fixes:**
- Total issues: 2
- Broken file links: 1 (user declined removal)
- Missing anchors: 1 (requires new section)

**Fixed:**
- Broken file links: 7 removed
- Missing anchors: 6 added

**Remaining:**
- 2 issues require manual intervention
----

== Integration with Workflows

=== verify-links Workflow

Reference this protocol in the verify-links workflow:

[source,yaml]
----
workflow: verify-links
steps:
  1. Run verify-adoc-links.py script
  2. Classify with verify-links-false-positives.py
  3. Manual verification (link-verification.md)
  4. User confirmation for removals
  5. Re-validation
  6. Report generation
----

=== comprehensive-review Workflow

Link verification is SECOND step (after format validation):

[source,yaml]
----
workflow: comprehensive-review
steps:
  1. Format validation (must pass before proceeding)
  2. Link verification (this protocol)
  3. Content review (tone, accuracy, sources)
----

== Best Practices

=== Prevention

**During Documentation Creation:**

* Test links immediately after adding
* Use absolute paths from project root where possible
* Document external URLs with access date
* Add anchors when creating section headers

**During Refactoring:**

* Search for xrefs to files before moving/renaming
* Update all references in same commit
* Run link verification after structural changes

=== Maintenance

**Regular Reviews:**

* Verify external URLs quarterly
* Check for moved/renamed files
* Update cross-references after major restructuring
* Document deprecated references

== Tools and Scripts

=== verify-adoc-links.py

**Purpose:** Automated detection of broken links

**Location:** `scripts/verify-adoc-links.py`

**Output:** JSON with broken link candidates

=== verify-links-false-positives.py

**Purpose:** Classify broken link candidates to reduce false positives

**Location:** `scripts/verify-links-false-positives.py`

**Output:** JSON with categorized issues (likely-false-positive, must-verify-manual, definitely-broken)

=== Manual Verification with Read Tool

**Purpose:** Definitive verification of link target existence

**Usage:** `Read(file_path="absolute/path/to/target.adoc")`

**Advantage:** Direct file system access, no parsing errors

== References

* xref:../README.adoc[CUI Documentation Standards Overview]
* AsciiDoc Cross-Reference Syntax: https://docs.asciidoctor.org/asciidoc/latest/macros/xref/
