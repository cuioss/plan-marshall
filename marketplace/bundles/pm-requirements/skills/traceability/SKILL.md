---
name: traceability
description: Standards for linking specifications to implementation code and maintaining bidirectional traceability between documentation and source code
user-invocable: false
---

# Traceability Standards

## Enforcement

**Execution mode**: Reference library; load standards on-demand for traceability tasks.

**Prohibited actions:**
- Do not create unidirectional links; all traceability must be bidirectional
- Do not duplicate specification content in code comments; use cross-references
- Do not skip the quality verification step after applying traceability standards
- Do not load all standards at once; load progressively based on current task

**Constraints:**
- Each piece of information must have one authoritative location (single source of truth)
- All specifications must link to implementation code and vice versa
- Documentation must evolve through lifecycle phases (pre-implementation, during, post)
- Link accuracy must be verified whenever referenced files change
- For document markup syntax (link format, cross-references), see `pm-documents:ref-asciidoc`

Standards for connecting specification documents with implementation code, establishing bidirectional traceability, and maintaining documentation throughout the implementation lifecycle.

## Scope Boundary

This skill covers **linking between documents and code**: bidirectional navigation, API documentation references, test coverage documentation, and link maintenance. For **creating and maintaining document content** (structure, SMART principles, ID schemes, lifecycle management), see `pm-requirements:requirements-authoring`. For what belongs in specifications vs. API documentation, see `standards/information-distribution.md`.

## Core Principles

### Holistic System View

Effective documentation provides a complete view at multiple levels:

- **Requirements level**: What the system must accomplish
- **Specification level**: How the system is designed
- **Implementation level**: How the code actually works

Proper linkage ensures seamless navigation between these levels.

### Single Source of Truth

Each piece of information should have one authoritative location:

- **Specifications**: Architectural decisions, standards, constraints
- **Implementation code**: Detailed behavior, algorithms, edge cases
- **API documentation**: Usage guidance, API contracts, implementation notes

### Documentation Lifecycle

Documentation evolves through implementation phases (PLANNED → IN PROGRESS → IMPLEMENTED). For the complete lifecycle model, see `pm-requirements:requirements-authoring` → `standards/documentation-lifecycle-management.md`. This skill provides the traceability-focused subset in the "Documentation Update Workflow by Phase" section below.

## Workflow

### Step 1: Load Applicable Traceability Standards

**CRITICAL**: Load traceability standards based on task context.

1. **Always load information distribution standards**:
   ```
   Read: standards/information-distribution.md
   ```
   Defines what belongs in specifications vs API documentation.

2. **Load standards based on task context**:

   - If linking from specifications to code:
     ```
     Read: standards/specification-to-code-linking.md
     ```

   - If linking from code to specifications (API documentation):
     ```
     Read: standards/code-to-specification-linking.md
     ```

   - If updating documentation through implementation phases, use the phase guidance below.

   - If documenting test coverage and validation:
     ```
     Read: standards/verification-and-validation-linking.md
     ```

   - If maintaining existing traceability links:
     ```
     Read: standards/cross-reference-maintenance.md
     ```

   - If verifying traceability quality:
     ```
     Read: standards/quality-standards.md
     ```

### Step 2: Apply Traceability Standards

Apply the loaded standards to your specific task:

**For New Implementation**:
1. Add API documentation specification references using code-to-specification-linking templates
2. Update specification with implementation links using specification-to-code-linking templates
3. Follow the Documentation Update Workflow by Phase section below

**For Documentation Updates**:
1. Determine current lifecycle phase (PLANNED/IN PROGRESS/IMPLEMENTED)
2. Apply appropriate updates from the Documentation Update Workflow by Phase section below
3. Ensure information distribution standards are followed

**For Test Documentation**:
1. Add specification references to test classes
2. Update specification Verification sections
3. Document coverage using verification-and-validation-linking standards

**For Maintenance**:
1. Follow cross-reference-maintenance workflows
2. Verify quality using quality-standards checklists
3. Update links as needed

### Step 3: Verify Quality

Use quality-standards checklists to verify:

- All specifications link to implementation
- All code links to specifications
- All tests reference specifications
- Links are accurate and current
- Navigation is bidirectional
- Status indicators are correct

## Documentation Update Workflow by Phase

Traceability-specific guidance for updating documentation through implementation lifecycle phases. For the complete lifecycle model (PLANNED → IN PROGRESS → IMPLEMENTED → DEPRECATED), see `pm-requirements:requirements-authoring` → `standards/documentation-lifecycle-management.md`.

### Pre-Implementation (PLANNED)
- Write comprehensive specification with design and expected API
- No implementation links yet — spec defines "what" and "how"

### During Implementation (IN PROGRESS)
- Add implementation links as source files are created
- Add API documentation (JavaDoc, docstrings, JSDoc) with specification references (see `code-to-specification-linking.md`)
- Document implementation decisions and library choices
- Update status indicator

### Post-Implementation (IMPLEMENTED)
- Complete all traceability links (spec → code → tests)
- Add test references in Verification section
- Remove redundant code examples that duplicate implementation
- Keep architectural guidance and design rationale
- Refer readers to API documentation for detailed behavior

### Separation of Concerns

| Document | Contains | Does NOT Contain |
|----------|----------|------------------|
| Specification | What and why | Implementation details |
| API docs (JavaDoc, docstrings, JSDoc) | How and when | Architecture decisions |
| Tests | Validation and coverage | Design rationale |

Use cross-references instead of duplicating information across these layers. Update links immediately when source files are created.

## Related Standards

### Related Skills in Bundle

- `pm-requirements:requirements-authoring` - Standards for creating requirements and specifications that form the traceability foundation
- `pm-requirements:setup` - Standards for setting up documentation structure in new projects
- `pm-requirements:planning` - Standards for planning documents that track implementation tasks

### External Standards

- `pm-dev-java:javadoc` - JavaDoc specification references (Java projects)
- `pm-dev-frontend:javascript` - JSDoc specification references (JavaScript projects)
- `pm-documents:ref-asciidoc` - AsciiDoc formatting for specification documents
