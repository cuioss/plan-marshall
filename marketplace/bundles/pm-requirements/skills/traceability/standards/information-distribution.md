# Information Distribution Standards

Standards for deciding what information belongs in specifications versus implementation code documentation (JavaDoc).

## What Belongs in Specifications

Specification documents must contain:

**Requirements and Constraints**:
- What the system must do (requirements traceability)
- Technical standards to follow
- Limitations and boundaries

**Architecture and Design**:
- High-level component structure
- Component relationships and dependencies
- Integration points and interfaces

**Implementation Guidance**:
- Design patterns to apply
- Frameworks and libraries to use
- Configuration requirements
- Standards compliance requirements

**References**:
- Links to implementing classes
- Links to verification tests
- Links to related specifications

## What Belongs in JavaDoc

Implementation code documentation (JavaDoc) must contain:

**API Documentation**:
- Purpose of class/method
- Usage instructions and examples
- Parameter descriptions
- Return value descriptions
- Exception conditions

**Implementation Details**:
- How the code works internally
- Algorithm descriptions
- Performance characteristics
- Thread safety guarantees

**Edge Cases**:
- Special cases and how they're handled
- Error handling specifics
- Boundary conditions

**References**:
- Links back to specification documents
- Requirement references
- Related classes and methods

## What to Avoid

**In specifications**:
- Detailed method-level implementation
- Internal algorithms and data structures
- Transitional language ("was moved", "will be refactored")
- Code that duplicates actual implementation

**In JavaDoc**:
- Extensive architectural overviews spanning multiple components
- Requirement definitions and rationale
- Standards definitions that apply broadly
- Information better suited to specifications
