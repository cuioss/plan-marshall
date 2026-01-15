# Tone and Style Standards for Technical Documentation

## Purpose

Technical documentation must maintain a professional, neutral, and objective voice. These standards ensure documentation serves to inform and educate without promotional language or subjective claims.

## Core Principles

### Neutral and Professional Tone

**Required Characteristics:**
* Technical, professional voice throughout
* Neutral presentation of information
* Objective descriptions of functionality
* Factual statements with verifiable sources
* Appropriate formality for technical audience

**Prohibited Characteristics:**
* Marketing language or promotional wording
* Self-praise or superlative claims
* Subjective opinions without attribution
* Casual or overly informal language
* Emotional or persuasive writing

### Objective vs Subjective Language

**Objective Language (Use This):**
Objective language presents facts, technical specifications, and verifiable information:

* "This library implements RFC 7519 for JWT validation"
* "The algorithm has O(n log n) time complexity"
* "Configuration supports three authentication modes"
* "The API follows REST principles as defined in Roy Fielding's dissertation"

**Subjective Language (Avoid This):**
Subjective language includes opinions, marketing claims, or unverifiable statements:

* ❌ "This is the best JWT library available"
* ❌ "Our innovative approach revolutionizes authentication"
* ❌ "Blazingly fast performance"
* ❌ "The easiest API you'll ever use"

## Prohibited Content Patterns

### Marketing Language

Marketing language attempts to sell or promote rather than inform.

**Examples to Avoid:**
* ❌ "Revolutionary new features"
* ❌ "Cutting-edge technology"
* ❌ "Industry-leading performance"
* ❌ "State-of-the-art implementation"
* ❌ "Powerful capabilities"
* ❌ "Seamless integration"
* ❌ "Comprehensive" (as marketing adjective)
* ❌ "Robust" (as marketing adjective)
* ❌ "Enterprise-grade"

**Correct Alternatives:**
* ✅ "New features in version 2.0"
* ✅ "Implementation based on [specific standard]"
* ✅ "Performance benchmarks: [specific metrics]"
* ✅ "Implementation following [specific pattern]"
* ✅ "Capabilities: [list specific features]"
* ✅ "Integration via [specific mechanism]"
* ✅ "Validates X, Y, and Z" (instead of "comprehensive validation")
* ✅ "Handles errors: [list specific types]" (instead of "robust")

### Self-Praise and Superlatives

Self-praise elevates the project beyond objective assessment.

**Examples to Avoid:**
* ❌ "Excellent error handling"
* ❌ "Superior design"
* ❌ "The most comprehensive solution"
* ❌ "Unmatched flexibility"
* ❌ "Best-in-class architecture"

**Correct Alternatives:**
* ✅ "Error handling includes: [list specific error types]"
* ✅ "Design follows [specific pattern/principle]"
* ✅ "Features include: [complete list]"
* ✅ "Supports: [list configuration options]"
* ✅ "Architecture based on [specific style]"

### Promotional Wording

Promotional wording attempts to persuade rather than describe.

**Examples to Avoid:**
* ❌ "You'll love how easy this is"
* ❌ "Simply add one line of code"
* ❌ "Effortlessly handles complex scenarios"
* ❌ "Makes your life easier"
* ❌ "Instantly improves performance"

**Correct Alternatives:**
* ✅ "Configuration requires: [specific steps]"
* ✅ "Add the following dependency: [code]"
* ✅ "Handles scenarios: [list specific cases]"
* ✅ "Provides: [specific capabilities]"
* ✅ "Performance characteristics: [specific metrics]"

### Unverified Claims

All factual claims must be verifiable or properly attributed.

**Examples Requiring Verification:**
* ❌ "Industry standard practice" (without citation)
* ❌ "Commonly used approach" (without reference)
* ❌ "Improves performance by 50%" (without benchmarks)
* ❌ "Widely adopted pattern" (without examples)

**Correct Approaches:**
* ✅ "Practice recommended in [source/standard]"
* ✅ "Approach described in [citation]"
* ✅ "Benchmark results: [link to data]"
* ✅ "Pattern used by [specific projects/frameworks]"
* ✅ "According to [authoritative source], ..."

### Qualification Patterns

Qualification patterns use subjective qualifiers to make factual claims sound more impressive. These are particularly problematic in technical specifications where neutral, factual descriptions are required.

**Examples to Avoid:**
* ❌ "Production-proven (227+ plugins)" - Promotional framing of usage statistics
* ❌ "HIGH confidence from multiple production examples" - Subjective qualifier
* ❌ "Extensively tested" - Vague claim without metrics
* ❌ "Well-established pattern" - Subjective assessment
* ❌ "Widely adopted" - Vague claim without specifics
* ❌ "Battle-tested in production" - Marketing language
* ❌ "Proven track record" - Self-praise without evidence

**Correct Alternatives:**
* ✅ "Used by 227+ plugins in marketplace" - Factual statement
* ✅ "Verified in production environments (see examples)" - Neutral with attribution
* ✅ "Test coverage: [specific percentage/metrics]" - Measurable claim
* ✅ "Pattern defined in [standard/specification]" - Attributed source
* ✅ "Used by [list specific projects]" - Concrete examples
* ✅ "Deployed in [specific contexts/environments]" - Factual description
* ✅ "Benchmark results: [link to data]" - Verifiable evidence

**Context Matters:**
Technical specifications require stricter scrutiny than general documentation:
* Architecture documents: Describe structure, not quality judgments
* API documentation: State functionality, not promotional claims
* Implementation guides: Provide facts, not persuasive language

### Transitional Documentation Markers

Transitional markers indicate work-in-progress documentation. These undermine the authoritative tone of technical documentation and create maintenance burden. Documentation should represent the current state, not track historical transitions.

**Examples to Remove:**
* ❌ "DOCUMENT STATUS: Draft" or "DOCUMENT STATUS: ✅ Complete"
* ❌ "IMPLEMENTATION STATUS: In Progress" or "IMPLEMENTATION STATUS: ✅ Production-ready"
* ❌ "Status: ✅ Verified and production-proven"
* ❌ "This transforms from X to Y" - Temporal transitional language
* ❌ "Note: This section is being updated"
* ❌ "TODO: Add more details"
* ❌ "Work in progress"

**Why These Are Problematic:**
* Create maintenance burden (need constant updates)
* Undermine authoritative tone (suggests incompleteness)
* Add no technical value to readers
* Confuse whether documentation reflects current or future state
* Appropriate for project management, not technical documentation

**Correct Approaches:**
* ✅ Document current state only - remove status markers
* ✅ Use git history for tracking changes, not inline markers
* ✅ Complete sections before publishing, or omit incomplete content
* ✅ Use issue tracker for TODO items, not documentation
* ✅ Present information as established fact, not transitional state

**Exception:** Release notes and changelogs may document state changes, but should still avoid promotional status markers.

## Required Content Patterns

### Technical Precision

Use precise technical language that accurately describes functionality.

**Good Examples:**
* ✅ "Validates JWT signatures using HMAC SHA-256"
* ✅ "Implements OAuth 2.0 Authorization Code Flow as defined in RFC 6749"
* ✅ "Provides thread-safe token cache with configurable TTL"
* ✅ "Supports PKCE extension per RFC 7636"

### Factual Descriptions

Present features and capabilities as factual statements.

**Good Examples:**
* ✅ "The library includes three validation modes: strict, lenient, and custom"
* ✅ "Configuration options are documented in [location]"
* ✅ "Compatibility: Java 11 and higher"
* ✅ "Dependencies: [list with versions]"

### Attributed Sources

When referencing standards, specifications, or external sources, provide attribution.

**Required Pattern:**
```markdown
As specified in [RFC 7519](https://tools.ietf.org/html/rfc7519), JWT tokens consist of three parts: header, payload, and signature.
```

**Components:**
* Link to authoritative source
* Clear indication of what comes from that source
* Accurate representation of the source material

## Clarity Standards

### Concise Writing

Avoid verbose or redundant passages.

**Verbose (Avoid):**
❌ "This library provides functionality that allows developers to perform validation of JWT tokens in a way that ensures security and compliance with industry standards through comprehensive checking mechanisms."

**Concise (Use):**
✅ "This library validates JWT tokens according to RFC 7519 security requirements."

### Direct Language

Use direct, straightforward language without unnecessary complexity.

**Indirect (Avoid):**
❌ "It should be noted that there exists a possibility for configuring the validation process in such a manner that..."

**Direct (Use):**
✅ "Configure validation by setting..."

### No Jargon Without Explanation

Technical terms are acceptable when properly introduced.

**Bad (Jargon Unexplained):**
❌ "Uses PKCE for enhanced security."

**Good (Jargon Explained):**
✅ "Uses PKCE (Proof Key for Code Exchange) to prevent authorization code interception attacks, as defined in RFC 7636."

## Voice and Tense

### Active vs Passive Voice

**Prefer Active Voice:**
* ✅ "The library validates tokens"
* ✅ "Call `validate()` to check the token"
* ✅ "The parser throws `InvalidTokenException`"

**Passive Voice (Acceptable for Processes):**
* ✅ "Tokens are validated against the configured issuer"
* ✅ "Errors are logged to the specified output"

### Present Tense

Use present tense for describing current functionality.

**Good Examples:**
* ✅ "The method returns a validated token"
* ✅ "Configuration accepts three parameters"
* ✅ "Errors are reported via exceptions"

**Avoid Future Tense for Current Features:**
* ❌ "The method will return a token"
* ❌ "Configuration will accept parameters"

## Common Patterns to Fix

### Pattern 1: Feature Announcement

**Problematic:**
❌ "We're excited to announce our new validation API with amazing features!"

**Fixed:**
✅ "Version 2.0 introduces a new validation API with the following features: [list]"

### Pattern 2: Ease-of-Use Claims

**Problematic:**
❌ "Integration is incredibly simple and takes just minutes."

**Fixed:**
✅ "Integration requires three steps: [numbered list with code examples]"

### Pattern 3: Performance Bragging

**Problematic:**
❌ "Lightning-fast performance that outperforms all competitors."

**Fixed:**
✅ "Validation throughput: 50,000 tokens/second on reference hardware (see benchmarks/setup.md)"

### Pattern 4: Vague Benefits

**Problematic:**
❌ "Provides better security and enhanced reliability."

**Fixed:**
✅ "Implements security requirements from RFC 7519 sections 4-6. Includes validation of: signature, expiration, issuer, audience."

## Analysis Guidelines

### Identifying Tone Issues

When reviewing documentation, assess each statement:

1. **Is this factual or subjective?**
   - Factual: Can be verified, measured, or tested
   - Subjective: Opinion, feeling, or qualitative judgment

2. **Is this neutral or promotional?**
   - Neutral: Describes without selling
   - Promotional: Attempts to persuade or impress

3. **Is this technical or marketing?**
   - Technical: Specifies how something works
   - Marketing: Emphasizes why someone should use it

4. **Is this precise or vague?**
   - Precise: Specific, measurable, clear
   - Vague: General, ambiguous, unclear

### Fixing Tone Issues

For each identified issue:

**Step 1: Identify the Problem**
* What makes this text problematic?
* Which principle does it violate?
* What is the underlying intent?

**Step 2: Determine the Fix**
* What factual information can replace the subjective claim?
* How can this be stated neutrally?
* What technical details are needed?
* What source or attribution is required?

**Step 3: Rewrite**
* Remove subjective language
* Add technical precision
* Include sources/references
* Verify factual accuracy

**Example:**
```
Original: "Our revolutionary caching system dramatically improves performance."

Analysis:
- "revolutionary" = marketing language
- "dramatically" = subjective, unverified claim
- No specific metrics or comparison

Fixed: "Token caching reduces validation time by 85% (median) in benchmark tests. See benchmarks/results.md for detailed metrics."

Rationale:
- Removed marketing language
- Added specific, verifiable metric
- Provided reference to source data
- Maintained technical focus
```

## Examples

### Example 1: Project Overview

**Before (Problematic):**
```markdown
# Amazing OAuth Library

Our revolutionary OAuth implementation makes authentication incredibly easy!
With blazing-fast performance and a beautifully designed API, you'll love
how simple it is to integrate. We've created the most comprehensive OAuth
solution available, packed with powerful features that will transform your
application's security.
```

**After (Compliant):**
```markdown
# OAuth Sheriff

OAuth 2.0 implementation for Java applications following RFC 6749 and RFC 7636.

Features:
* Authorization Code Flow with PKCE support
* Token validation according to RFC 7519
* Integration with Quarkus via CDI extension
* Configurable token cache (default: 10-minute TTL)
```

### Example 2: Feature Description

**Before (Problematic):**
```markdown
## Awesome Validation Features

Our state-of-the-art validation engine provides unmatched flexibility and
performance. You'll be amazed at how it effortlessly handles even the most
complex scenarios while maintaining incredible speed.
```

**After (Compliant):**
```markdown
## Token Validation

The validation engine supports three modes:

* **Strict**: Enforces all RFC 7519 requirements
* **Lenient**: Allows expired tokens for testing
* **Custom**: User-defined validation rules

Performance: Validates 50,000 tokens/second (example: benchmark details could be in benchmarks/results.md).
```

## Quality Checklist

Before finalizing documentation, verify:

- [ ] Professional, neutral tone maintained
- [ ] No marketing language (revolutionary, cutting-edge, powerful, etc.)
- [ ] No self-praise or superlatives
- [ ] No promotional wording
- [ ] All claims are verifiable or attributed
- [ ] No qualification patterns (production-proven, extensively tested, etc.)
- [ ] No transitional markers (status indicators, TODO items)
- [ ] Technical precision throughout
- [ ] Concise, direct language
- [ ] Jargon explained when used
- [ ] Active voice preferred
- [ ] Present tense for current features
- [ ] Factual descriptions only
- [ ] Sources attributed where appropriate

## References

* [Documentation Core Standards](documentation-core.md)
* [AsciiDoc Formatting Standards](asciidoc-formatting.md)
* [README Structure Standards](readme-structure.md)
