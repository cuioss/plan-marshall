# Deprecation Handling Standards

Standards for handling requirement deprecation and removal, with distinct processes for pre-1.0 and post-1.0 projects.

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

## Anti-Patterns

### Removing Without Deprecation (Post-1.0)

**Bad**: Deleting requirement completely in released product

**Good**: Marking as DEPRECATED with migration guidance
