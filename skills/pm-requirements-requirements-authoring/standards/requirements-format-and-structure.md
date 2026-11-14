# Requirements Format and Structure Standards

Standards for formatting and structuring requirements documents with proper ID schemes, headings, and content organization.

> **Format note**: Examples use AsciiDoc (`.adoc`) syntax. For AsciiDoc syntax, header attributes, and formatting rules, see `pm-documents:ref-asciidoc`. This document covers requirements-specific structure and conventions, not markup syntax.

## Document Structure

### Location and Naming

**Required location**: `doc/Requirements.adoc`

### Document Header

Use the standard document header for requirements documents. See `pm-requirements:setup` → `standards/document-templates.md` (Requirements Template section) for the full template, and `pm-documents:ref-asciidoc` → `references/asciidoc-formatting.md` for header attribute details.

### Content Organization

Requirements documents must include:

1. **Overview section**: Explains the purpose and scope of the requirements
2. **General Requirements section**: High-level project requirements
3. **Functional Requirements sections**: Organized by component or feature
4. **Non-Functional Requirements**: Performance, security, usability, etc.

## Requirement ID Format

### Format Specification

**Format**: `[#PREFIX-NUM]`

**Examples**:
- `[#NIFI-AUTH-1]`
- `[#API-SEC-2.1]`
- `[#UI-COMP-5]`

Each requirement anchor must be placed immediately before the heading:

```asciidoc
[#NIFI-AUTH-1]
=== NIFI-AUTH-1: REST API Support Enhancement
```

### Prefix Selection

**Length**: Keep prefixes short (3-5 characters)

**Relevance**: Use domain-specific abbreviations

**Uniqueness**: Ensure the prefix is unique within your organization

**Consistency**: Use the same prefix throughout all project documentation

## Requirement Heading Format

### Major Requirements

Major requirements use the heading pattern `PREFIX-NUM: Descriptive Title` at the third heading level in the document hierarchy:

**Example**:
```asciidoc
[#API-AUTH-1]
=== API-AUTH-1: Authentication Framework
```

### Sub-requirements

Sub-requirements use decimal notation at the fourth heading level:

**Example**:
```asciidoc
[#API-AUTH-1.1]
==== API-AUTH-1.1: OAuth 2.0 Support
```

## Requirement Content Format

### Bullet Point Structure

Use bullet points for requirement details:

```asciidoc
[#API-AUTH-1]
=== API-AUTH-1: Authentication Framework

* The system must support OAuth 2.0 authentication
* Token expiration must be configurable
* Failed authentication attempts must be logged
  ** Log entries must include timestamp and client identifier
  ** Sensitive information must be redacted from logs
```

### Nested Bullets

Use nested bullets (`**`) for detailed sub-points that elaborate on parent bullets.

## Requirement Numbering

### Numbering Scheme

**Major requirements**: Sequential numbers (PREFIX-1, PREFIX-2, PREFIX-3)

**Sub-requirements**: Decimal notation (PREFIX-1.1, PREFIX-1.2, PREFIX-2.1)

**Consistency**: Maintain the same prefix throughout the document

### Numbering Rules

1. **Never reuse requirement IDs**, even if a requirement is removed
2. **Assign next available number** when adding new requirements
3. **Maintain sequence** - don't skip numbers unless there's a deprecation
4. **Use decimal notation** for sub-requirements only

### Example Numbering

```asciidoc
[#JWT-1]
=== JWT-1: Token Validation Framework

[#JWT-1.1]
==== JWT-1.1: Signature Validation

[#JWT-1.2]
==== JWT-1.2: Expiration Checking

[#JWT-2]
=== JWT-2: Token Parsing

[#JWT-2.1]
==== JWT-2.1: Header Parsing
```

## Deprecated Requirements

When a requirement is no longer applicable:

```asciidoc
[#API-AUTH-5]
=== API-AUTH-5: [DEPRECATED] Basic Authentication Support

This requirement has been deprecated in favor of OAuth 2.0 (see API-AUTH-1).
```

**Critical Rule**: Do not delete deprecated requirements - this maintains ID sequence integrity and project history.

## Prefix Selection by Domain

For the complete prefix table, selection criteria, and hierarchical prefix patterns, see `pm-requirements:setup` → `standards/prefix-selection.md`.

## Integration with Specifications

Requirements should reference specification documents:

```asciidoc
[#API-AUTH-1]
=== API-AUTH-1: Authentication Framework

* The system must support OAuth 2.0 authentication
* Token management must follow security best practices

See the link:specification/authentication.adoc[Authentication Specification] for implementation details.
```

## Quality Standards

For comprehensive quality criteria (completeness, clarity, maintainability, traceability), see `integrity-and-quality-standards.md`. Format-specific checks:

- All requirement IDs must be unique with sequential numbering
- Consistent heading levels, bullet point structure, and ID formatting
- Deprecated requirement IDs preserved (never reused)
- Clear, descriptive titles organized by functional area
