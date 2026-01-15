= Content Review Framework
:toc: left
:toclevels: 3
:sectnums:

== Overview

This standard defines the framework for reviewing AsciiDoc content quality, with emphasis on factual accuracy, clarity, professional tone, and completeness. Uses ULTRATHINK reasoning for deep tone and style analysis.

== Review Dimensions

Content quality is assessed across five dimensions:

1. **Correctness** - Factual accuracy, verifiable claims, proper citations
2. **Clarity** - Concise, unambiguous, comprehensible writing
3. **Tone & Style** - Professional, technical, non-promotional language
4. **Consistency** - Uniform terminology, formatting patterns
5. **Completeness** - No gaps, TODOs, or missing sections

== Correctness Analysis

=== Identify Factual Claims

**Factual claims** are statements that assert specific capabilities, comparisons, standards compliance, or measurable characteristics.

**Examples:**

* "Supports OAuth 2.0"
* "Faster than library X"
* "Implements RFC 6749"
* "Sub-millisecond validation"
* "Used by Spring Security"
* "Provides comprehensive logging"

=== Verification Requirements

For each factual claim, verify:

==== Standards Compliance

**Claim:** "Implements RFC 6749 (OAuth 2.0)"

**Verification:**

* Check RFC citation is present
* Verify RFC number matches description
* Confirm RFC is relevant to feature
* If RFC unfamiliar, read RFC title/abstract

**Flag if:**

* No RFC cited
* RFC number incorrect
* RFC irrelevant to claim

==== Performance Claims

**Claim:** "Sub-millisecond validation"

**Verification:**

* Check for benchmark data
* Verify measurement methodology
* Confirm conditions stated (hardware, load)

**Flag if:**

* No benchmark data
* No measurement details
* Conditions unclear

==== Compatibility Claims

**Claim:** "Compatible with Spring Boot 3.x"

**Verification:**

* Check version numbers specified
* Verify compatibility matrix exists
* Confirm tested versions listed

**Flag if:**

* No version numbers
* Vague "latest" or "all versions"
* No test evidence

==== Usage Claims

**Claim:** "Used by Spring Security"

**Verification:**

* Check for public reference (documentation, source code)
* Verify link to external evidence
* Confirm claim is current

**Flag if:**

* No public reference
* Unverified third-party usage
* Outdated information

=== Flagging Unverified Claims

**Format:**

[source]
----
Line {N}: "{claim text}"
Issue: Unverified {performance/compatibility/usage} claim
Required: {specific source needed}
Suggestion: {add citation | remove claim | rephrase as capability}
----

**Example:**

[source]
----
Line 42: "Our validator is 10x faster than competitors"
Issue: Unverified performance claim without benchmark data
Required: Benchmark comparison with methodology
Suggestion: Remove comparison or add link to benchmark results
----

== Clarity Analysis

=== Identify Clarity Issues

==== Verbose or Redundant Text

**Pattern:** Multiple words/phrases convey same meaning

**Example:**

* Before: "The validation process validates and checks the input data to ensure that it is valid"
* After: "The validator checks input data integrity"

==== Overly Complex Sentences

**Guideline:** Sentences >30 words often lack clarity

**Example:**

* Before: "When the user submits a request, the system will first validate the input parameters, then check authorization, and finally, if everything is correct, process the request and return a response"
* After: "The system validates inputs, checks authorization, and processes requests"

==== Unclear or Ambiguous Statements

**Pattern:** Multiple interpretations possible

**Example:**

* Before: "The cache might be cleared"
* After: "The cache clears when memory exceeds 80% capacity"

==== Unexplained Jargon

**Pattern:** Technical terms without definition on first use

**Example:**

* Before: "Uses HMAC for signature verification"
* After: "Uses HMAC (Hash-based Message Authentication Code) for signature verification"

=== Flagging Clarity Issues

**Format:**

[source]
----
Line {N}: "{text}"
Issue: {verbose | complex | unclear | unexplained}
Suggestion: "{improved version}"
----

== Tone and Style Analysis (ULTRATHINK)

=== ULTRATHINK Decision Framework

**CRITICAL:** Use ULTRATHINK reasoning for comprehensive tone assessment to distinguish factual descriptions from promotional language.

=== Decision Questions

For each descriptive phrase, ask:

**1. Does this describe a verifiable, specific capability?**

* YES → Likely factual
* NO → Likely promotional

**2. Can this be measured or tested?**

* YES → Likely factual
* NO → Likely promotional

**3. Does it compare favorably without evidence?**

* YES → Promotional
* NO → Possibly factual

**4. When in doubt:** Describe WHAT the feature does, not HOW impressive it is

=== Context-Dependent Descriptive Language

==== Factual/Acceptable (when verified)

[cols="1,2"]
|===
|Phrase |Acceptable When

|"Seamlessly handle"
|Library actually handles without manual configuration

|"Automatically configured"
|Truly automatic with no setup required

|"Zero-configuration"
|Works without setup (but describe what it does)

|"Built-in caching"
|Describes included feature

|"Comprehensive validation"
|All validation steps are performed

|"Fully tested"
|Test coverage data available

|"Supports all major formats"
|List of formats provided
|===

==== Promotional/Unacceptable (always flag)

[cols="1,2,2"]
|===
|Phrase |Why Unacceptable |Alternative

|"Powerful features"
|Subjective, unmeasurable
|"Provides X, Y, Z features"

|"Best-in-class performance"
|Self-praise, unverified
|"Processes N requests/second"

|"Enterprise-grade"
|Marketing buzzword
|"Supports clustering, HA, audit logging"

|"Blazing-fast"
|Subjective
|"Sub-millisecond response time"

|"Production-ready"
|Vague
|"Tested with 10K req/s, 99.9% uptime"

|"Robust"
|Vague
|"Handles failures with automatic retry"

|"Cutting-edge"
|Self-praise
|"Implements RFC XXXX (2024)"

|"Industry-leading"
|Unverified comparison
|Remove or provide evidence
|===

=== Promotional Language Patterns

==== Marketing Language

**Indicators:**

* Superlatives without measurement
* Self-praise
* Comparative advantage without evidence
* Buzzwords

**Examples to flag:**

* "The ultimate solution"
* "Revolutionary approach"
* "Game-changing technology"
* "Unparalleled performance"

==== Subjective Claims

**Indicators:**

* Opinion stated as fact
* Value judgments
* Emotional language

**Examples to flag:**

* "Easy to use" (subjective - describe specific ease features)
* "Beautiful API" (opinion - describe API characteristics)
* "Intuitive design" (subjective - describe specific design choices)

==== Unverified Claims

**Indicators:**

* Broad statements without specifics
* Usage claims without attribution
* Adoption claims without data

**Examples to flag:**

* "Used by thousands of companies" (no data)
* "Trusted by developers worldwide" (unverified)
* "Proven in production" (no evidence)

=== Bias Detection

==== Self-Serving Bias

**Pattern:** Emphasizing strengths, minimizing weaknesses

**Flag:**

* Only positive capabilities listed
* No limitations documented
* Comparisons only when favorable

**Example:**

* Before: "Our library is faster than X and more secure than Y"
* After: "Processes 10K req/s. Implements TLS 1.3 and mTLS"

==== Unsubstantiated Claims

**Pattern:** Assertions without evidence

**Example:**

* Before: "Most popular JWT library"
* After: "JWT library with 50K+ GitHub stars" (if true and relevant)

=== Tone Issue Flagging

**Format:**

[source]
----
Line {N}: "{original text}"
Issue: {marketing | self-praise | promotional | unverified | subjective}
Reasoning: {ULTRATHINK analysis}
Suggestion: "{factual alternative}"
----

**Example:**

[source]
----
Line 15: "Our powerful validation engine provides blazing-fast performance"
Issue: marketing + subjective
Reasoning: "Powerful" is unmeasurable subjective praise. "Blazing-fast" is vague.
Suggestion: "Validation engine processes 50K validations/second (benchmarked on AWS t3.medium)"
----

== Consistency Analysis

=== Terminology Consistency

**Check for:**

* Same concept described with different terms
* Inconsistent capitalization
* Acronym definitions repeated or missing

**Example issue:**

[source]
----
Inconsistency detected:
- Line 10: "JSON Web Token (JWT)"
- Line 45: "JWT token" (redundant - JWT already means token)
- Line 89: "Json Web Token" (inconsistent capitalization)

Recommendation: Use "JWT" consistently, define once at first use
----

=== Formatting Consistency

**Check for:**

* Inconsistent code block formatting
* Mixed list styles (bulleted vs numbered)
* Inconsistent heading levels

=== Style Consistency

**Check for:**

* Mixed voice (active vs passive)
* Inconsistent audience (technical vs non-technical)
* Tone shifts (formal vs informal)

== Completeness Analysis

=== Missing Sections

**Check for:**

* TODOs or placeholder text
* Incomplete examples
* References to "TBD" or "Coming soon"
* Empty sections

**Flag:**

[source]
----
Line {N}: TODO section marker found
Content: "{TODO text}"
Action: Complete section or remove marker
----

=== Content Gaps

**Check for:**

* Features mentioned but not documented
* Referenced sections that don't exist
* Missing prerequisites or dependencies
* Incomplete configuration examples

=== Source Attribution

**Check for:**

* External standards referenced but not cited
* Code examples without source
* Best practices without authoritative reference

**Requirement:** All external references should link to authoritative sources:

* Official documentation
* RFCs and standards bodies
* Academic papers
* Industry frameworks (OWASP, NIST)

== Integration with Workflows

=== analyze-content-tone.py Script

The analyze-content-tone.py script implements automated detection of:

* Promotional language patterns
* Missing source citations
* Superlatives and subjective phrases

**Script output:** JSON with flagged sections requiring ULTRATHINK analysis.

**Claude's role:** Apply ULTRATHINK decision framework to script findings.

=== review-content Workflow

[source,yaml]
----
workflow: review-content
parameters:
  - file_path or directory_path
  - apply_fixes (default: false)

steps:
  1. Run analyze-content-tone.py (automated detection)
  2. Apply ULTRATHINK analysis (Claude)
  3. Generate findings report
  4. If apply_fixes: Suggest improvements
  5. User confirmation for changes
----

== Best Practices

=== Proactive Review

**During Writing:**

* State capabilities, not impressiveness
* Cite sources immediately
* Define acronyms on first use
* Use specific, measurable descriptions

=== Reactive Review

**During Review:**

* Question every superlative
* Verify every claim
* Test for multiple interpretations
* Check for missing context

=== ULTRATHINK Application

**When to apply:**

* Any descriptive language
* Comparative statements
* Performance or capability claims
* Adoption or usage statements

**How to apply:**

1. Read phrase in isolation
2. Ask: "Is this objectively verifiable?"
3. Ask: "Would a competitor's docs use this phrase?"
4. If no to either: Flag for review

== References

* AsciiDoc Writing Best Practices
* RFC 7322: RFC Style Guide
* Technical Writing Standards
* OWASP Documentation Guidelines
