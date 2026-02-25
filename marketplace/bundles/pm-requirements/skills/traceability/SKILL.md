---
name: traceability
description: Standards for linking specifications to implementation code and maintaining bidirectional traceability between documentation and source code
user-invokable: false
---

# Traceability Standards

Standards for connecting specification documents with implementation code, establishing bidirectional traceability, and maintaining documentation throughout the implementation lifecycle.

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
- **JavaDoc**: Usage guidance, API contracts, implementation notes

### Documentation Lifecycle

Documentation evolves through implementation:

1. **Pre-Implementation**: Specifications contain detailed design and examples
2. **During Implementation**: Specifications updated with implementation decisions
3. **Post-Implementation**: Specifications link to code, redundant details removed

## Workflow

### Step 1: Load Applicable Traceability Standards

**CRITICAL**: Load traceability standards based on task context.

1. **Always load information distribution standards**:
   ```
   Read: standards/information-distribution.md
   ```
   Defines what belongs in specifications vs JavaDoc.

2. **Load standards based on task context**:

   - If linking from specifications to code:
     ```
     Read: standards/specification-to-code-linking.md
     ```

   - If linking from code to specifications (JavaDoc):
     ```
     Read: standards/code-to-specification-linking.md
     ```

   - If updating documentation through implementation phases:
     ```
     Read: standards/documentation-update-workflow.md
     ```

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
1. Add JavaDoc specification references using code-to-specification-linking templates
2. Update specification with implementation links using specification-to-code-linking templates
3. Follow documentation-update-workflow for lifecycle phase

**For Documentation Updates**:
1. Determine current lifecycle phase (PLANNED/IN PROGRESS/IMPLEMENTED)
2. Apply appropriate updates from documentation-update-workflow
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

- [ ] All specifications link to implementation
- [ ] All code links to specifications
- [ ] All tests reference specifications
- [ ] Links are accurate and current
- [ ] Navigation is bidirectional
- [ ] Status indicators are correct

## Related Standards

### Related Skills in Bundle

- `pm-requirements:requirements-authoring` - Standards for creating requirements and specifications that form the traceability foundation
- `pm-requirements:setup` - Standards for setting up documentation structure in new projects
- `pm-requirements:planning` - Standards for planning documents that track implementation tasks

### External Standards

- JavaDoc standards (for implementation documentation)
- Testing standards (for test documentation)
