---
name: requirements-authoring
description: Comprehensive standards for creating and maintaining requirements and specification documents with SMART principles, proper structure, integrity, and traceability
user-invocable: false
---

# Requirements and Specification Authoring Standards

## Enforcement

**Execution mode**: Reference library; load standards on-demand for requirements authoring and specification tasks.

**Prohibited actions:**
- Do not create requirements without SMART criteria validation
- Do not duplicate content across documents; use cross-references
- Do not document features that do not exist or are not planned (no hallucinations)
- Do not load all standards at once; load progressively based on current task

**Constraints:**
- All requirements must use consistent ID format: `[#PREFIX-NUM]`
- All specifications must include backtracking links to requirements
- Sequential numbering must be maintained; never reuse IDs
- Cross-references must be verified and functional before finalizing
- For document markup syntax, see `pm-documents:ref-asciidoc`

Comprehensive standards for creating, structuring, and maintaining requirements and specification documents in projects following SMART principles, ensuring complete traceability, and maintaining documentation integrity throughout the project lifecycle.

## Scope Boundary

This skill covers **creating and maintaining content** in requirements and specification documents: structure, SMART principles, ID schemes, lifecycle management, and quality.

For **linking documents to implementation code** (bidirectional traceability, API documentation references, test coverage documentation), see `pm-requirements:traceability`.

**Shared concepts, different ownership:**
- **Backtracking links**: This skill defines the *format and placement* within documents. Traceability defines *when and how to maintain* them as code evolves.
- **Status indicators** (PLANNED/IN PROGRESS/IMPLEMENTED): This skill defines the *allowed values and meaning*. Traceability defines *when to transition* them during implementation.
- **Lifecycle phases**: This skill owns the *complete lifecycle model* (`documentation-lifecycle-management.md`). Traceability provides a *traceability-focused subset* for link updates during phase transitions.

## What This Skill Provides

This skill consolidates all standards for authoring requirements and specification documents:

- **Requirements Format**: SMART principles, ID schemes, numbering, and structure
- **Specification Structure**: Document organization, backtracking links, and traceability patterns
- **Documentation Lifecycle**: Pre-implementation, during implementation, and post-implementation practices
- **Quality Standards**: Clarity, completeness, consistency, and testability requirements
- **Integrity Requirements**: No hallucinations, no duplications, verified links
- **Maintenance Standards**: Adding, modifying, removing, and deprecating requirements

## When to Activate

Use this skill when:

- Creating new requirements documents for projects
- Writing specification documents with proper structure
- Maintaining existing requirements and specifications
- Ensuring documentation integrity and quality
- Setting up traceability between requirements, specs, and code
- Handling requirement deprecation or removal

## Workflow

### 1. Creating Requirements

When creating new requirements:

1. Follow SMART principles (Specific, Measurable, Achievable, Relevant, Time-bound)
2. Use consistent ID format: `[#PREFIX-NUM]`
3. Structure with proper headings and bullet points
4. Maintain sequential numbering (never reuse IDs)
5. Link to specifications when created

### 2. Writing Specifications

When creating specifications:

1. Create backtracking links to requirements: `_See Requirement link:../Requirements.adoc#REQ-ID[REQ-ID: Title]_`
2. Organize by component or functional area
3. Use proper status indicators (PLANNED, IN PROGRESS, IMPLEMENTED)
4. Link to implementation code when it exists
5. Update as implementation progresses

### 3. Maintaining Documentation

When maintaining requirements/specifications:

1. Verify no hallucinated functionality (all documented features must exist or be planned)
2. Eliminate duplications (use cross-references instead)
3. Verify all links are functional
4. Update implementation status as code is written
5. Handle deprecation appropriately (ask user for post-1.0 projects)

### 4. Ensuring Quality

Before finalizing documentation:

1. Check all cross-references resolve correctly
2. Verify consistent terminology throughout
3. Ensure clear traceability from requirements to specs to code
4. Validate SMART criteria for all requirements
5. Confirm no duplicate information across documents

## Standards Organization

Standards are organized into focused documents:

### Core Authoring Standards

**requirements-format-and-structure.md**
- Requirement ID format and anchors
- Heading format and hierarchy
- Content organization patterns
- Bullet point structure
- Document header requirements

**smart-requirements-principles.md**
- SMART criteria definitions
- Specific requirements patterns
- Measurable criteria examples
- Achievable and relevant requirements
- Testability requirements

**specification-structure-and-backtracking.md**
- Specification document structure
- Main vs. individual specification files
- Backtracking link format and placement
- Multiple requirement references
- Path variations for cross-references

### Lifecycle Management

**documentation-lifecycle-management.md**
- Pre-implementation specifications (detailed design, examples, expected API)
- During implementation updates (implementation links, decisions, notes)
- Post-implementation refinement (status updates, implementation links, removing redundancy)
- Transitioning between lifecycle phases

### Quality and Integrity

**integrity-and-quality-standards.md**
- No hallucinations rule (verify all documented features)
- No duplications rule (use cross-references)
- Verified links requirement
- Consistency requirements
- Clarity and completeness standards
- Maintainability principles

**requirements-maintenance.md**
- Adding new requirements (numbering, format, linking)
- Modifying existing requirements (preserve IDs, update content)
- Removing requirements (pre-1.0 vs. post-1.0 deprecation handling)
- Deprecation process with migration guidance, removal process when user approves
- Refactoring requirements (maintain IDs, update references)
- Commit guidelines for requirement changes

## Integration

This skill integrates with:

- **pm-requirements:setup** - Provides initial structure that authoring populates
- **pm-requirements:planning** - Planning tasks trace to requirements created here
- **pm-requirements:traceability** - Links authored specs to implementation code
- **pm-documents:ref-asciidoc** - Document formatting and validation (AsciiDoc syntax, templates, link verification)

Language-specific API documentation standards for referencing requirements from code are covered in `pm-requirements:traceability` → `standards/code-to-specification-linking.md`.

## Anti-Patterns to Avoid

**Over-specification in requirements:**
- Avoid: "The system must use a HashMap to store tokens"
- Preferred: "The system must cache validated tokens for performance"

**Vague requirements:**
- Avoid: "The system should be fast and secure"
- Preferred: "Token validation must complete within 50ms for 95% of requests"

**Implementation details in requirements:**
- Avoid: "The TokenValidator class must use jose4j library"
- Preferred: "The system must validate JWT signatures according to RFC 7519"

**Duplicating content across documents:**
- Avoid: Copying requirement text into specifications
- Preferred: Using backtracking links to reference requirements

**Hallucinated functionality:**
- Avoid: Documenting features that don't exist or aren't planned
- Preferred: Verifying all documented features against code or approved plans

## Quality Rules

Before completing requirements/specification work:

- All requirements follow SMART principles
- All requirement IDs follow PREFIX-NUM format
- All specifications have backtracking links to requirements
- No hallucinated functionality documented
- No duplicate information across documents
- All cross-references verified and functional
- Consistent terminology throughout
- Clear traceability maintained
- Implementation status indicators current
- Documentation integrity validated

## Related Standards

**Within Bundle:**
- setup - Initial structure creation
- planning - Task tracking linked to requirements
- traceability - Linking specs to implementation

**External:**
- pm-documents:ref-asciidoc - AsciiDoc formatting
- pm-dev-java:javadoc - JavaDoc requirement references (Java projects)
- plan-marshall:workflow-integration-git - Committing requirement changes
