# Maintenance and Deprecation Handling Standards

Standards for maintaining requirements and specification documents including adding, modifying, removing requirements, and handling deprecation appropriately for pre-1.0 and post-1.0 projects.

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

**CRITICAL RULE**: Never delete requirements

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

## Deprecation Handling by Project Phase

### Pre-1.0 Projects

**Rule**: Update requirements directly without deprecation process

**Rationale**: Pre-release projects are in active development. Requirements can change freely without maintaining historical record.

**Process**:
1. Identify outdated requirements
2. Update requirement text directly
3. Update linked specifications
4. Update or remove implementation references
5. No deprecation markers needed

**Example**:
```asciidoc
// Simply update the requirement
[#REQ-001]
=== REQ-001: User Authentication

The system shall authenticate users via OAuth2 with support for
OIDC identity providers.

(Previous text about SAML authentication simply replaced)
```

**When to Use**:
- Project version < 1.0
- No production users
- Active development phase
- Frequent requirement changes

### Post-1.0 Projects

**Rule**: Always ask user whether to deprecate or remove functionality

**Rationale**: Released projects may have users depending on documented behavior. Changes require explicit approval.

**Decision Process**:
```
When encountering removed/changed functionality:
1. STOP maintenance process
2. Document the change details
3. ASK USER: "Should I deprecate or remove this requirement?"
   - Deprecate: Mark as deprecated, keep documentation
   - Remove: Delete requirement and update all references
4. WAIT for user decision
5. Proceed based on user choice
```

### Deprecation Process (User Chooses Deprecate)

**Steps**:

1. **Mark Requirement as Deprecated**:
```asciidoc
[#REQ-001]
=== REQ-001: User Authentication [DEPRECATED]

[WARNING]
====
**Status**: DEPRECATED as of version 2.0.0

**Reason**: Replaced by OAuth2 authentication (REQ-042)

**Migration**: See xref:#req-042[REQ-042] for new authentication approach
====

Original requirement text preserved below for reference...
```

2. **Update Specification**:
```asciidoc
== Authentication Specification [DEPRECATED]

[WARNING]
====
This specification is deprecated. See xref:OAuth2Specification.adoc[OAuth2 Specification]
for current authentication implementation.
====
```

3. **Add Migration Guidance** (if applicable):
- Document how to migrate from old to new approach
- Provide code examples if relevant
- Link to new requirements/specifications

4. **Maintain Historical Record**:
- Keep deprecated documentation in place
- Preserve traceability links
- Document deprecation timeline

### Removal Process (User Chooses Remove)

**Steps**:

1. **Remove Requirement**:
   - Delete requirement section completely
   - Update document table of contents

2. **Update All References**:
   - Remove from traceability matrices
   - Update cross-references in other documents
   - Remove from specification documents

3. **Update Implementation References**:
   - Remove code references to deleted requirement
   - Clean up test references

4. **Update Index/TOC**:
   - Ensure no orphaned links remain

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

### When Documents Move

If documents are restructured or moved:

1. **Identify all affected cross-references**
2. **Update xref/link paths** to new locations
3. **Update section IDs** if changed
4. **Test all links** resolve correctly
5. **Update external documentation** references

### Common Updates

**File path changes**:
```asciidoc
// Before
xref:old/path/Requirements.adoc#req-001[REQ-001]

// After
xref:new/path/Requirements.adoc#req-001[REQ-001]
```

**Section ID changes**:
```asciidoc
// Before
xref:Requirements.adoc#old-id[REQ-001]

// After
xref:Requirements.adoc#new-id[REQ-001]
```

**Document renames**:
```asciidoc
// Update all references to new document name
```

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

## Common Maintenance Scenarios

### Scenario 1: New Feature Documentation

**When**: Adding requirements for new functionality

**Process**:
1. Add requirement with next sequential ID
2. Follow SMART principles
3. Create corresponding specification
4. Add cross-references
5. Update traceability matrix

### Scenario 2: Refactoring Impact

**When**: Code refactored, need to update documentation

**Process**:
1. Review changed code structure
2. Update implementation references in specifications
3. Verify requirement statements remain accurate
4. Adjust code examples to match new structure
5. Maintain requirement IDs unchanged

**Key Principle**: Requirements describe WHAT, not HOW. Refactoring changes HOW (implementation), so requirements usually don't change, only specification implementation references.

### Scenario 3: Requirement Evolution

**When**: Requirement needs significant changes

**For Pre-1.0**:
- Update requirement directly
- Update specifications
- No deprecation needed

**For Post-1.0**:
- Ask user for deprecation vs. update decision
- If deprecating: Create new requirement, mark old as deprecated
- If updating: Modify in place with clear documentation

### Scenario 4: Feature Removal

**When**: Feature being removed from product

**For Pre-1.0**:
- Remove requirement directly
- Update specifications
- Clean up references

**For Post-1.0**:
- Ask user for approval
- Mark as DEPRECATED (don't delete)
- Add migration guidance if applicable
- Update specifications with deprecation notice

## Quality Checks for Maintenance

### Before Committing Changes

- [ ] All requirement IDs preserved (no renumbering)
- [ ] SMART principles maintained
- [ ] All specifications updated to match
- [ ] All cross-references verified
- [ ] Deprecations properly marked
- [ ] Commit message includes affected IDs
- [ ] Changes documented with rationale

### After Committing Changes

- [ ] Traceability maintained
- [ ] No broken links
- [ ] Consistent terminology
- [ ] Implementation alignment verified
- [ ] Documentation builds successfully

## Anti-Patterns to Avoid

### Reusing Deprecated IDs

**Bad**: Deleting REQ-005 and using REQ-005 for a new requirement

**Good**: Mark REQ-005 as DEPRECATED, use REQ-010 for new requirement

### Changing Requirement IDs

**Bad**: Renumbering all requirements after deleting one

**Good**: Maintain existing IDs, mark deleted ones as DEPRECATED

### Removing Without Deprecation (Post-1.0)

**Bad**: Deleting requirement completely in released product

**Good**: Marking as DEPRECATED with migration guidance

### Silent Major Changes

**Bad**: Significantly changing requirement without documentation

**Good**: Clear commit message explaining change and rationale

### Orphaning Specifications

**Bad**: Updating requirements without updating linked specifications

**Good**: Update requirements and specifications together, maintaining traceability
