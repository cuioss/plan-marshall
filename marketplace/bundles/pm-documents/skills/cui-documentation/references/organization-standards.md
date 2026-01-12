# Documentation Organization Standards

## Purpose

This document defines comprehensive standards for organizing, reviewing, and maintaining documentation structure, including file organization, naming conventions, size limits, and quality review processes for all CUI projects.

## File Organization Standards

### Single Aspect Principle

Each document should represent one coherent aspect or domain:

* **Focused Scope**: Document covers one specific technology, process, or domain area
* **Clear Boundaries**: No overlap between documents - use cross-references instead
* **Logical Grouping**: Related concepts within the same document should flow logically
* **Separation of Concerns**: Configuration, rules, and integration kept in separate documents when appropriate

**Examples:**

✅ **Good - Single Aspect:**
* `jwt-validation.md` - Covers JWT validation only
* `oauth2-configuration.md` - Covers OAuth2 configuration only
* `security-best-practices.md` - Covers security practices only

❌ **Bad - Multiple Aspects:**
* `authentication.md` - Mixing JWT, OAuth2, SAML, and security practices

### Document Size Guidelines

#### Optimal Size Limits

Documents should maintain optimal size for readability and maintainability:

* **Minimum Size**: 50 lines (excluding headers and TOC)
* **Maximum Size**: 400 lines (including all content)
* **Target Range**: 100-300 lines for most comprehensive documents
* **Exception Handling**: Documents exceeding 400 lines should be split into focused components

#### Size-Based Actions

**Oversized Documents (>400 lines):**
* Split into logical components based on content sections
* Create overview document that cross-references split components
* Maintain comprehensive coverage while improving navigation
* Update all cross-references to new document structure

**Undersized Documents (<50 lines):**
* Evaluate for consolidation with related documents
* Consider integration into parent or related documents
* Maintain as standalone only if serving unique, specific purpose
* Ensure adequate depth of coverage for the topic

### File Naming Standards

#### Naming Convention

All documentation files must follow consistent kebab-case naming:

* **Format**: `descriptive-name.md` or `descriptive-name.adoc`
* **Character Set**: Lowercase letters, numbers, and hyphens only
* **Descriptive**: Name clearly indicates document content and scope
* **Consistent**: Similar documents use parallel naming patterns
* **No Abbreviations**: Use full, clear names rather than abbreviations

#### Naming Examples

**Correct Naming:**
* `javascript-best-practices.adoc`
* `eslint-configuration.md`
* `integration-testing-standards.adoc`
* `css-design-system.md`

**Incorrect Naming:**
* `JavaScript_BestPractices.adoc` (mixed case, underscores)
* `eslint_config.adoc` (underscore, abbreviation)
* `IntegrationTestingStandards.adoc` (camelCase)
* `css-ds.md` (abbreviation)

## Documentation Review Guidelines

### Quality Standards

Comprehensive review process ensures documentation quality:

* **Consistency**: Uniform terminology, formatting, and structure across all documents
* **Completeness**: All standards areas fully documented without gaps
* **Correctness**: Technical information and cross-references validated
* **Focus**: Content concise but preserves all essential information

### Content Requirements

#### No Duplication

* Eliminate duplicate information across documents
* Use cross-references instead of repeating content
* Maintain single source of truth for each concept
* Reference shared concepts rather than duplicating

**Example:**

❌ **Bad - Duplicated:**
```markdown
<!-- In jwt-validation.md -->
Token validation requires the following steps:
1. Parse the token
2. Verify signature
3. Check expiration

<!-- In oauth2-validation.md -->
Token validation requires the following steps:
1. Parse the token
2. Verify signature
3. Check expiration
```

✅ **Good - Cross-Referenced:**
```markdown
<!-- Example: Hypothetical files showing cross-referencing pattern -->

<!-- In jwt-validation.md (example file) -->
Token validation follows the [standard validation process](token-validation-core.md).

<!-- In oauth2-validation.md (example file) -->
OAuth2 tokens follow the [standard validation process](token-validation-core.md) with additional OAuth2-specific checks.

<!-- In token-validation-core.md (example file) -->
Standard token validation requires:
1. Parse the token
2. Verify signature
3. Check expiration
```

#### Current State Only

* Document present requirements only
* Remove transitional, status, or deprecation information
* Eliminate "changed from X to Y" references
* Focus on current technical requirements

**Examples:**

❌ **Bad - Transitional:**
```markdown
## Configuration

Previously, configuration was done via XML files. As of version 2.0, we now use YAML.
```

✅ **Good - Current State:**
```markdown
## Configuration

Configuration uses YAML format.
```

#### Source Attribution

* Always link to authoritative sources when referencing external standards
* Provide proper citations for best practices
* Include relevant external documentation links
* Maintain traceability to original sources

**Example:**

✅ **Good - Attributed:**
```markdown
JWT validation follows [RFC 7519](https://tools.ietf.org/html/rfc7519) requirements for signature verification and claim validation.
```

#### Standards Linking

* Cross-reference related standards documents using proper syntax
* Maintain logical navigation between related documents
* Create clear document hierarchy and relationships
* Update cross-references when restructuring content

**Markdown Cross-References:**
```markdown
See [AsciiDoc Formatting Standards](asciidoc-formatting.md) for details.
```

**AsciiDoc Cross-References:**
```asciidoc
See xref:asciidoc-formatting.adoc[AsciiDoc Formatting Standards] for details.
```

## Document Maintenance Standards

### Structural Maintenance

#### Cross-Reference Integrity

* Update all cross-references when restructuring content
* Verify all links remain valid after changes
* Test link integrity during document updates
* Maintain proper document relationships

#### Formatting Consistency

* Maintain formatting conventions (Markdown or AsciiDoc)
* Use standard document header structure
* Ensure proper table of contents configuration
* Apply consistent section numbering

#### Content Focus

* Focus on technical requirements rather than implementation procedures
* Maintain clear separation between standards and processes
* Emphasize "what" rather than "how" in standards documents
* Keep implementation details in separate process documents

### File Structure Adaptation

#### Reorganization Authority

You have authority to adapt structure when necessary:

* Reorganize files and directories for better usability
* Split overly broad documents into focused components
* Consolidate fragmented information into coherent documents
* Improve logical organization and navigation

#### When to Reorganize

**Split Documents When:**
* Document exceeds 400 lines
* Multiple unrelated topics are mixed
* Navigation becomes difficult
* Content serves different audiences

**Merge Documents When:**
* Multiple documents under 50 lines cover related topics
* Heavy cross-referencing suggests they should be together
* Fragmentation reduces usability
* Content is too granular

#### Logical Linking

* Use README files to provide overview and navigation
* Link related documents together in coherent structure
* Create clear entry points for each domain area
* Maintain hierarchical organization within directories

**Example README Structure:**
```markdown
<!-- Example README.md showing hypothetical file structure -->
# Token Validation Standards

This directory contains standards for token validation:

* [Core Validation](token-validation-core.md) - Common validation requirements (example file)
* [JWT Validation](jwt-validation.md) - JWT-specific validation (example file)
* [OAuth2 Validation](oauth2-validation.md) - OAuth2-specific validation (example file)
* [Testing Standards](validation-testing.md) - Testing requirements (example file)
```

## Review Process Standards

### Comprehensive Review Scope

#### Document Analysis

* Review all documents for size compliance (50-400 lines)
* Identify oversized documents requiring split
* Identify undersized documents for potential consolidation
* Assess file naming consistency across all documents

#### Content Quality Review

* Eliminate duplicate information across documents
* Remove transitional or status information
* Verify cross-reference accuracy and consistency
* Ensure current-state focus throughout all content

#### Structural Assessment

* Evaluate logical organization within and across documents
* Assess single-aspect compliance for each document
* Review file naming for consistency and clarity
* Validate overall documentation architecture

### Implementation Standards

#### Change Management

* Update cross-references immediately after restructuring
* Maintain document relationships during reorganization
* Preserve all essential technical information during changes
* Test navigation and link integrity after modifications

#### Quality Assurance

* Verify formatting compliance (Markdown/AsciiDoc)
* Validate proper list and code block formatting
* Ensure consistent document header structure
* Check table of contents and section numbering

## Integration with Development Process

### Documentation Lifecycle

#### Creation Standards

* New documents must comply with size and naming guidelines
* Follow established organizational patterns
* Include proper cross-references to related documents
* Maintain consistency with existing documentation structure

#### Maintenance Requirements

* Regular review for continued compliance with organization standards
* Update structure as content grows or requirements change
* Maintain cross-reference accuracy during ongoing development
* Preserve organizational quality through iterative improvements

### Version Control Best Practices

* Structure documents for effective version control
* Minimize merge conflicts through logical organization
* Maintain clear change history for documentation updates
* Support collaborative editing through good organization
* Use descriptive commit messages for documentation changes

## Quality Checklist

### Organization Compliance

- [ ] Each document follows single aspect principle
- [ ] Document size within 50-400 line range (or justified exception)
- [ ] File naming follows kebab-case convention
- [ ] No duplicate content across documents
- [ ] All transitional markers removed
- [ ] Current state only documented
- [ ] All sources properly attributed
- [ ] Cross-references accurate and up-to-date

### Structure Quality

- [ ] Logical document organization
- [ ] Clear navigation between related documents
- [ ] README files provide overview where needed
- [ ] Consistent formatting throughout
- [ ] Proper section hierarchy
- [ ] All links verified and working

### Maintenance Readiness

- [ ] Documents easy to locate
- [ ] Related content properly linked
- [ ] Clear scope for each document
- [ ] No orphaned documents
- [ ] Documentation structure scalable

## Common Organization Issues and Solutions

### Issue 1: Monolithic Documents

**Problem:** Single document covers too many topics (>400 lines)

**Solution:**
1. Identify logical topic boundaries
2. Create separate documents for each major topic
3. Create overview document with cross-references
4. Update all incoming links to point to new structure

### Issue 2: Fragmented Information

**Problem:** Related information scattered across many small documents

**Solution:**
1. Identify related documents covering same domain
2. Merge into coherent single document
3. Update cross-references
4. Remove redundant files

### Issue 3: Unclear Navigation

**Problem:** Users can't find related documentation

**Solution:**
1. Create or update README files in directories
2. Add "Related Documentation" sections
3. Establish clear document hierarchy
4. Add navigation breadcrumbs where appropriate

### Issue 4: Naming Inconsistency

**Problem:** Mixed naming conventions make discovery difficult

**Solution:**
1. Establish standard naming pattern
2. Rename files to follow convention
3. Update all cross-references
4. Document naming standards for future files

## References

* [Documentation Core Standards](documentation-core.md) - Core documentation principles
* [AsciiDoc Formatting Standards](asciidoc-formatting.md) - AsciiDoc-specific formatting
* [README Structure Standards](readme-structure.md) - README file patterns
* [Tone and Style Standards](tone-and-style.md) - Professional tone requirements
