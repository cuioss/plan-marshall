# Requirements Format and Structure Standards

Standards for formatting and structuring requirements documents with proper ID schemes, headings, and content organization.

## Document Structure

### Location and Naming

**Required location**: `doc/Requirements.adoc`

**Format**: AsciiDoc with proper structure and formatting

### Document Header

```asciidoc
= [Project Name] Requirements
:toc: left
:toclevels: 3
:toc-title: Table of Contents
:sectnums:
:source-highlighter: highlight.js
```

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

Use Level 3 headings (`===`) for major requirements:

```asciidoc
=== PREFIX-NUM: Descriptive Title
```

**Example**:
```asciidoc
[#API-AUTH-1]
=== API-AUTH-1: Authentication Framework
```

### Sub-requirements

Use Level 4 headings (`====`) for sub-requirements:

```asciidoc
==== PREFIX-NUM.1: Sub-requirement Title
```

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

### Recommended Prefixes

| Domain | Prefix | Example |
|--------|--------|---------|
| Apache NiFi Integration | `NIFI-` | NIFI-PROC-1 |
| Security | `SEC-` | SEC-AUTH-1 |
| API Development | `API-` | API-REST-1 |
| User Interface | `UI-` | UI-COMP-1 |
| Database | `DB-` | DB-MIGR-1 |
| Integration | `INT-` | INT-KAFKA-1 |
| Logging | `LOG-` | LOG-AUDIT-1 |
| Testing | `TEST-` | TEST-PERF-1 |
| JWT | `JWT-` | JWT-VALID-1 |

### Multiple Component Prefixes

For complex projects with multiple major components, use hierarchical prefixes:

```asciidoc
[#SYS-AUTH-1]
=== SYS-AUTH-1: Authentication System Requirements

[#SYS-AUTH-1.1]
==== SYS-AUTH-1.1: OAuth Implementation

[#SYS-DB-1]
=== SYS-DB-1: Database Requirements

[#SYS-DB-1.1]
==== SYS-DB-1.1: Schema Design
```

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

### Format Consistency

- Use the same heading levels for similar requirement types
- Maintain consistent bullet point structure
- Apply uniform formatting for requirement IDs
- Follow established prefix conventions

### Structural Integrity

- All requirement IDs must be unique
- Maintain sequential numbering
- Preserve deprecated requirement IDs
- Keep consistent document structure

### Readability

- Use clear, descriptive requirement titles
- Organize requirements logically by functional area
- Group related requirements together
- Use appropriate heading hierarchy
