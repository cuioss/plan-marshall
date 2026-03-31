# Integrity and Quality Standards

Standards for maintaining documentation integrity, preventing hallucinations, eliminating duplication, and ensuring high-quality requirements and specifications.

## Core Documentation Principles

### Consistency

**Definition**: Uniform terminology, structure, and formatting across all requirements and specification documents.

**Requirements**:
- Use consistent terminology throughout all documents
- Apply uniform formatting for similar elements
- Maintain standard document structure
- Follow established naming conventions

**Example**:
```
PASS CORRECT - Consistent terminology
Requirement REQ-001: The system shall authenticate users via OAuth2
Specification SPEC-001: OAuth2 authentication implementation
Test TEST-001: Verify OAuth2 authentication flow

FAIL WRONG - Inconsistent terminology
Requirement REQ-001: The system shall authenticate users via OAuth2
Specification SPEC-001: User login implementation
Test TEST-001: Verify authentication
```

### Completeness

**Definition**: All requirements fully documented with necessary detail and no gaps in information.

**Requirements**:
- All requirements documented with sufficient detail
- All related specifications linked
- All constraints and rationale captured
- No missing information or TBD placeholders

**Verification Checklist**:
- Every requirement has description and rationale
- All acceptance criteria defined
- All constraints documented
- All dependencies identified
- Traceability links complete

### Clarity

**Definition**: Unambiguous statements that can be understood consistently by all stakeholders.

**Requirements**:
- Use precise, unambiguous language
- Avoid subjective terms (fast, easy, user-friendly)
- Define measurable criteria
- Provide concrete examples where helpful

**Example**:
```
FAIL WRONG - Ambiguous
REQ-001: The system shall provide fast authentication

PASS CORRECT - Clear and measurable
REQ-001: The system shall complete user authentication within 2 seconds
for 95% of requests under normal load conditions (≤1000 concurrent users)
```

### Maintainability

**Definition**: Documentation structure that enables easy updates, extensions, and long-term maintenance.

**Requirements**:
- Modular document structure
- Clear cross-references
- Version control friendly format
- Minimal duplication
- Self-documenting organization

## Critical Integrity Requirements

### 1. No Hallucinations

**CRITICAL RULE**: Document only existing or planned functionality, never fictional capabilities.

**Requirements**:
- Verify all documented features exist in code or are approved for implementation
- Remove references to removed functionality
- Mark deprecated features appropriately
- Never invent capabilities to fill documentation gaps

**Validation Process**:
1. For each requirement, verify corresponding implementation exists or is planned
2. For each code reference, verify the code exists at specified location
3. For each specification, verify it describes real system behavior
4. Flag any documentation without verification source

**Example Violations**:
```
FAIL HALLUCINATION - Feature doesn't exist
REQ-042: The system shall support automatic backup to cloud storage
(When no such feature is implemented or planned)

PASS CORRECT - Document only what exists
REQ-042: [FUTURE] Cloud backup integration (planned for v2.0)
(Clearly marked as future functionality)
```

### 2. No Duplications

**CRITICAL RULE**: Use cross-references instead of copying information between documents.

**Requirements**:
- Single source of truth for each piece of information
- Use `xref:` or `link:` to reference information in other documents
- Avoid copying requirement text into specifications
- Link to canonical definitions

**Cross-Reference Pattern**:
```asciidoc
// Preferred: CORRECT - Cross-reference
See xref:Requirements.adoc#req-001[REQ-001: User Authentication] for
complete authentication requirements.

// Avoid: WRONG - Duplication
REQ-001 requires that the system shall authenticate users via OAuth2
with support for multiple identity providers...
(Copying entire requirement text)
```

**Allowed Duplication**:
- Brief summaries for context (max 1 sentence)
- Requirement IDs for traceability
- Document metadata (titles, versions)

### 3. Verified Links

**CRITICAL RULE**: All references must point to existing documents or code elements.

**Requirements**:
- All `xref:` and `link:` references must resolve to existing sections
- All code references must point to existing files/classes/methods
- All external links must be accessible
- Broken links must be fixed or removed

**Verification Process**:
1. Check all `xref:` references resolve correctly
2. Verify code references exist in current codebase
3. Test external links are accessible
4. Update or remove any broken references

**Common Link Types**:
```asciidoc
// Document cross-reference
xref:Requirements.adoc#req-001[REQ-001]
link:Requirements.adoc#req-001[REQ-001]

// Code reference (adapt path to project language/structure)
Implementation: `TokenValidator`
link:../path/to/TokenValidator[TokenValidator]

// External reference
OAuth2 Specification: https://oauth.net/2/
```

## Quality Verification Criteria

### Cross-References Validated

**Verification**:
- All `xref:` and `link:` references resolve to existing sections
- All document references point to current files
- No broken internal links
- All cross-references use correct syntax

**Tools**:
- AsciiDoc link verification
- Manual spot-checking of key references

### No Duplicate Information

**Verification**:
- Each piece of information has single source
- Cross-references used instead of copying
- No conflicting statements across documents
- Information distributed following standards

**Review Process**:
1. Identify repeated information
2. Determine canonical location
3. Replace duplicates with cross-references
4. Verify consistency

### Consistent Terminology

**Verification**:
- Same terms used for same concepts
- Glossary terms used consistently
- No contradictory definitions
- Standard naming conventions followed

**Common Term Categories**:
- Technical terms (API, authentication, token)
- Domain terms (user, resource, permission)
- Action verbs (shall, should, may, must)
- Status indicators (implemented, planned, deprecated)

### Clear Traceability Maintained

**Verification**:
- Requirements have unique IDs
- Specifications link to requirements
- Implementation references specifications
- Tests reference requirements
- Traceability matrix is current

**Traceability Chain**:
```
Requirement REQ-001
    ↓ (specified by)
Specification SPEC-001
    ↓ (implemented by)
Code: TokenValidator (source file)
    ↓ (tested by)
Test: TokenValidatorTest (test file)
```

### No Hallucinated Functionality

**Verification**:
- All documented features verified in code
- All code references point to existing elements
- No fictional capabilities documented
- Future features clearly marked

**Validation Steps**:
1. For each requirement, locate implementation
2. For each specification, verify behavior exists
3. For each code reference, verify element exists
4. Flag any unverified documentation

## Common Quality Issues

For common anti-patterns in requirements authoring (vague language, implementation details, unmeasurable claims), see `smart-requirements-principles.md` → Common Anti-Patterns section.

## Verification Workflow

### Regular Quality Checks

**Frequency**: Before major milestones, releases, or significant changes

**Process**:
1. Run AsciiDoc link validation
2. Verify all requirement IDs are unique
3. Check for duplicate content across documents
4. Verify all code references exist
5. Review terminology consistency
6. Validate traceability completeness

### Continuous Quality Practices

**During authoring**:
- Follow SMART principles for each requirement
- Use cross-references instead of duplication
- Verify links as you create them
- Maintain consistent terminology

**During review**:
- Check for hallucinated functionality
- Verify all links resolve
- Ensure consistent formatting
- Validate traceability

**During maintenance**:
- Update broken links immediately
- Remove obsolete content
- Maintain cross-reference integrity
- Keep status indicators current

## Quality Rules

For the consolidated quality checklist, see the SKILL.md Quality Rules section.
