# Documentation Update Workflow

Standards for updating documentation through the implementation lifecycle phases.

## Lifecycle Phases

Documentation evolves as implementation progresses through three distinct phases.

### Pre-Implementation (Status: PLANNED)

**Specification State**:
- Contains detailed design and expected API
- Includes validation flows and examples
- Focus on "what" and "how" the system should work
- Status indicator: PLANNED

**Actions**:
- Write comprehensive specification
- Define requirements and constraints
- Design component architecture
- Document expected interfaces

### During Implementation (Status: IN PROGRESS)

**Specification Updates**:
- Update status to IN PROGRESS
- Add implementation links as classes are created
- Document implementation decisions and library choices
- Add notes about design adaptations

**Code Documentation**:
- Add JavaDoc with specification references
- Use templates from code-to-specification-linking standards
- Link back to specification documents
- Document implementation-specific details

**Actions**:
- Create implementing classes
- Add JavaDoc referencing specifications
- Update specification with implementation links
- Document key implementation decisions

### Post-Implementation (Status: IMPLEMENTED)

**Specification Cleanup**:
- Update status to IMPLEMENTED
- Add complete implementation references
- Link to all implementing classes
- Add test references in Verification section
- Remove redundant code examples that duplicate implementation
- Keep architectural guidance and design rationale
- Refer readers to JavaDoc for detailed API behavior

**Validation**:
- Ensure all links are correct
- Verify test references are complete
- Check that no redundant content remains
- Confirm specification still provides value

**Actions**:
- Final specification review
- Remove implementation details now in code
- Ensure traceability links are complete
- Add test coverage information

## Workflow Summary

```
PLANNED → IN PROGRESS → IMPLEMENTED

PLANNED:
- Detailed specification
- No implementation
- Design focus

IN PROGRESS:
- Add implementation links
- Document decisions
- Keep specification updated

IMPLEMENTED:
- Clean up redundancy
- Complete all links
- Maintain architecture guidance
```

## Best Practices

**Maintain Separation of Concerns**:
- Specifications: What and why
- JavaDoc: How and when
- Tests: Validation and coverage

**Avoid Information Duplication**:
- Don't duplicate implementation details in specification
- Don't duplicate architecture in JavaDoc
- Use cross-references instead

**Keep Documentation Current**:
- Update status as implementation progresses
- Add links immediately when classes are created
- Remove obsolete content promptly
