# Requirements Maintenance Standards

Standards for maintaining requirements and specification documents including adding, modifying, removing, and refactoring requirements.

## Requirements Maintenance Overview

Requirements maintenance ensures documentation remains accurate, current, and aligned with implementation throughout the project lifecycle.

## Adding New Requirements

### Process

1. **Identify the appropriate section** for the new requirement
2. **Assign the next available number** in the sequence
3. **Follow the established format** and structure
4. **Create backtracking links** to corresponding specifications when created
5. **Update traceability matrix** if maintained

### Format

```asciidoc
[#JWT-7]
=== JWT-7: Token Refresh Support

* The system must support JWT token refresh mechanism
* Refresh tokens must be securely stored
* Refresh token expiration must be configurable
* Token refresh must generate new access and refresh tokens
```

### Best Practices

**Do**:
- Use next available sequential number
- Follow SMART principles
- Link to specifications
- Maintain consistent format

**Don't**:
- Skip numbers in sequence
- Reuse old requirement IDs
- Add requirements without clear rationale
- Forget to update related specifications

## Modifying Requirements

### Process

1. **Preserve the requirement ID** - never change it
2. **Update only the content** that needs to change
3. **Document significant changes** in commit messages
4. **Update all dependent specifications** to maintain traceability
5. **Verify implementation alignment** with modified requirements

### Example Modification

**Before**:
```asciidoc
[#JWT-1]
=== JWT-1: Token Validation

* The system must validate JWT signature
* The system must check token expiration
```

**After**:
```asciidoc
[#JWT-1]
=== JWT-1: Token Validation Framework

* The system must validate JWT signature using RS256 or HS256 algorithms
* The system must check token expiration with configurable clock skew
* The system must validate issuer and audience claims
* Validation failures must be logged for security audit
```

**What Changed**: Content expanded and clarified, but ID remained JWT-1

### Best Practices

**Do**:
- Keep same requirement ID
- Maintain SMART principles
- Update specifications to match
- Document rationale in commits

**Don't**:
- Change requirement IDs
- Make breaking changes without stakeholder approval
- Leave specifications out of sync
- Modify without clear reason

## Removing Requirements

**CRITICAL RULE**: Never delete requirements before 1.0 release. After 1.0, deletion requires explicit user approval (see `deprecation-handling.md` for the removal process). Default action is deprecation, not deletion.

### Process

Instead of deletion:

1. **Mark as DEPRECATED** in the heading
2. **Add brief explanation** of why deprecated
3. **Reference replacement** requirement if applicable
4. **Keep requirement ID** in sequence
5. **Update specifications** to reflect deprecation

### Format

```asciidoc
[#API-AUTH-5]
=== API-AUTH-5: [DEPRECATED] Basic Authentication Support

This requirement has been deprecated in favor of OAuth 2.0 (see API-AUTH-1).

Basic authentication is no longer supported due to security concerns and
industry best practices favoring token-based authentication.
```

### Best Practices

**Do**:
- Mark as [DEPRECATED] in heading
- Explain deprecation reason
- Reference replacement if exists
- Keep ID in sequence

**Don't**:
- Delete requirement completely
- Reuse deprecated IDs
- Leave without explanation
- Remove without updating specs

## Refactoring Requirements

### When Reorganizing

When reorganizing requirements structure:

1. **Maintain all existing requirement IDs**
2. **Update all specification documents** that reference affected requirements
3. **Verify all backtracking links** remain functional
4. **Document the refactoring** in commit messages

### Example Refactoring

**Before** (flat structure):
```asciidoc
== Requirements

[#JWT-1]
=== JWT-1: Signature Validation

[#JWT-2]
=== JWT-2: Expiration Checking

[#JWT-3]
=== JWT-3: Claim Extraction
```

**After** (hierarchical structure):
```asciidoc
== Functional Requirements

=== Token Validation

[#JWT-1]
==== JWT-1: Signature Validation

[#JWT-2]
==== JWT-2: Expiration Checking

=== Token Processing

[#JWT-3]
==== JWT-3: Claim Extraction
```

**What Changed**: Organization and heading levels, but IDs preserved

### Best Practices

**Do**:
- Preserve all requirement IDs
- Update all backtracking links
- Verify cross-references work
- Improve organization

**Don't**:
- Change requirement IDs
- Break existing links
- Reorganize without clear benefit
- Forget to update specifications

## Cross-Reference Maintenance

For detailed cross-reference maintenance workflows (handling document moves, class refactoring, link validation), see `pm-requirements:traceability` → `standards/cross-reference-maintenance.md`.

## Commit Guidelines

### Commit Message Format

Follow conventional commits with `docs(requirements):` prefix:

```
docs(requirements): update authentication requirements after OAuth2 migration

- Update REQ-001 through REQ-005 for OAuth2 authentication
- Remove deprecated SAML authentication requirements
- Update cross-references to new specification structure
- Fix broken links to implementation code

Affected requirements: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005
```

### Commit Content

**Include**:
- Specific changes made to requirements/specifications
- Requirement/specification IDs affected
- Rationale for changes
- Any structural changes to documents

**Avoid**:
- Vague descriptions ("updated docs")
- Missing requirement IDs
- Unexplained removals
- Large structural changes without explanation

## Quality Checks for Maintenance

For comprehensive quality verification criteria, see `integrity-and-quality-standards.md`.

## Anti-Patterns to Avoid

### Reusing Deprecated IDs

**Bad**: Deleting REQ-005 and using REQ-005 for a new requirement

**Good**: Mark REQ-005 as DEPRECATED, use REQ-010 for new requirement

### Changing Requirement IDs

**Bad**: Renumbering all requirements after deleting one

**Good**: Maintain existing IDs, mark deleted ones as DEPRECATED

### Silent Major Changes

**Bad**: Significantly changing requirement without documentation

**Good**: Clear commit message explaining change and rationale

### Orphaning Specifications

**Bad**: Updating requirements without updating linked specifications

**Good**: Update requirements and specifications together, maintaining traceability
