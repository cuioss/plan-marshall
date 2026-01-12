# Documentation Lifecycle Management Standards

Standards for managing requirements and specification documents throughout the implementation lifecycle: pre-implementation, during implementation, and post-implementation.

## Documentation Lifecycle Overview

Documentation evolves through three distinct phases:

1. **Pre-Implementation**: Specifications contain detailed design and examples
2. **During Implementation**: Specifications updated with implementation decisions
3. **Post-Implementation**: Specifications link to code, redundant details removed

**Note**: Each phase uses status indicators (PLANNED, IN PROGRESS, IMPLEMENTED, DEPRECATED). For the complete definition of these status values, see the **Status Values** section in `specification-structure-and-backtracking.md`.

## Pre-Implementation Phase

### Characteristics

**Status**: PLANNED

**Content focus**: Design guidance and expected behavior

**Level of detail**: High - provides comprehensive implementation guidance

### What to Include

**Detailed design guidance**:
- Component architecture and relationships
- Expected API design and interfaces
- Data flow and processing steps
- Configuration requirements

**Code examples and patterns**:
```asciidoc
=== Expected API

[source,java]
----
public interface TokenValidator {
    ValidationResult validate(String token);
    ValidationResult validate(String token, ValidationOptions options);
}

public class ValidationResult {
    public boolean isValid();
    public Optional<TokenClaims> getClaims();
    public List<ValidationError> getErrors();
}
----
```

**Validation flows and algorithms**:
```asciidoc
=== Validation Flow

1. Parse token into header, payload, signature
2. Verify token signature using configured algorithm
3. Validate standard claims (exp, nbf, iat)
4. Validate custom claims if configured
5. Return validation result
```

**Implementation notes**:
```asciidoc
=== Implementation Notes

* Use constant-time comparison for signature validation
* Cache public keys per issuer for performance
* Log all validation failures for security audit
* Support configurable clock skew tolerance
```

### Example Structure

Pre-implementation specifications include: Status: PLANNED, Design Overview, Expected API, Validation Flow, and Implementation Notes. See **[specification-structure-and-backtracking.md](specification-structure-and-backtracking.md#pre-implementation-specification)** for detailed format examples.

## During Implementation Phase

### Characteristics

**Status**: IN PROGRESS

**Content focus**: Implementation decisions and progress tracking

**Level of detail**: Mixed - combines design guidance with implementation references

### What to Add

**Implementation links**:
```asciidoc
=== Status: IN PROGRESS

Currently implementing in:

* link:../src/main/java/com/example/jwt/TokenValidator.java[TokenValidator] (in progress)
```

**Implementation decisions**:
```asciidoc
=== Implementation Notes

The implementation uses the jose4j library for cryptographic operations.
Configuration is provided through CDI producers.
Key caching implemented with 5-minute TTL.
```

**Progress notes**:
```asciidoc
=== Implementation Progress

* [x] TokenValidator interface defined
* [x] Basic validation flow implemented
* [ ] Signature validation in progress
* [ ] Claim validation not started
```

### What to Update

1. **Change status** from PLANNED to IN PROGRESS
2. **Add implementation links** as classes are created
3. **Document design decisions** made during implementation
4. **Update examples** if actual API differs from planned
5. **Keep pre-implementation guidance** until implementation is complete

### Example Structure

During-implementation specifications include: Status: IN PROGRESS, Implementation Links, Implementation Decisions, Design Overview (with notes on incomplete components), and Current API. See **[specification-structure-and-backtracking.md](specification-structure-and-backtracking.md#example-specification-structure)** for detailed format examples.

## Post-Implementation Phase

### Characteristics

**Status**: IMPLEMENTED

**Content focus**: Links to implementation with architectural context

**Level of detail**: Medium - enough context to understand design without duplicating JavaDoc

### What to Update

**1. Update status**:
```asciidoc
=== Status: IMPLEMENTED
```

**2. Add complete implementation references**:
```asciidoc
This specification is implemented in:

* link:../src/main/java/com/example/jwt/TokenValidator.java[TokenValidator]
* link:../src/main/java/com/example/jwt/TokenValidatorFactory.java[TokenValidatorFactory]

For detailed behavior, refer to the implementation and associated JavaDoc.
```

**3. Add test references**:
```asciidoc
=== Verification

Test coverage is provided by:

* link:../src/test/java/com/example/jwt/TokenValidatorTest.java[TokenValidatorTest]
* link:../src/test/java/com/example/jwt/integration/ValidationIntegrationTest.java[ValidationIntegrationTest]
```

**4. Remove redundant content**:
- Remove code examples that duplicate actual implementation
- Remove detailed API descriptions covered in JavaDoc
- Keep architectural guidance and design rationale
- Keep standards and constraints

**5. Refine content**:
```asciidoc
== Token Validation
_See Requirement link:../Requirements.adoc#JWT-1[JWT-1: Token Validation Framework]_

=== Status: IMPLEMENTED

Implementation:

* link:../src/main/java/com/example/jwt/TokenValidator.java[TokenValidator]
* link:../src/main/java/com/example/jwt/SignatureValidator.java[SignatureValidator]
* link:../src/main/java/com/example/jwt/ClaimValidator.java[ClaimValidator]

The implementation follows RFC 7519 standards and uses the jose4j library for cryptographic operations. Configuration is provided through CDI with sensible defaults.

For detailed implementation behavior and API usage, refer to the JavaDoc of the implementing classes.

=== Verification

Test coverage:

* link:../src/test/java/com/example/jwt/TokenValidatorTest.java[TokenValidatorTest]
* link:../src/test/java/com/example/jwt/integration/ValidationIntegrationTest.java[ValidationIntegrationTest]

Test coverage: 92% line coverage, 88% branch coverage.
```

### Example Structure

Post-implementation specifications include: Status: IMPLEMENTED, Implementation section (with links to all implementing classes), brief architectural context, reference to JavaDoc for detailed behavior, and Verification section (with test links and coverage metrics). See **[specification-structure-and-backtracking.md](specification-structure-and-backtracking.md#post-implementation-specification)** for detailed format examples.

## Transition Guidelines

### When to Transition Phases

**PLANNED → IN PROGRESS**: When first implementation code is written

**IN PROGRESS → IMPLEMENTED**: When:
- All implementing classes are complete
- Tests are written and passing
- Implementation is reviewed and merged

### What to Preserve Across Phases

**Always keep**:
- Requirement backtracking links
- Architectural overview and design rationale
- Standards and constraints
- Implementation decisions and rationale

**Remove after implementation**:
- Detailed code examples that duplicate actual implementation
- Expected API definitions covered in JavaDoc
- Speculative implementation guidance once actual implementation exists

## Information Distribution

### Specifications Focus On

- High-level architecture and component relationships
- Design decisions and rationale
- Standards compliance requirements
- Integration points and boundaries
- Links to implementation and tests

### JavaDoc Focuses On

- Detailed API documentation
- Method-level behavior
- Parameters, return values, exceptions
- Usage examples
- Performance characteristics
- Thread safety

### Requirements Focus On

- What the system must do
- Business and user needs
- Measurable success criteria
- Non-functional requirements
- Constraints and limitations

## Maintenance Throughout Lifecycle

### Continuous Activities

**Keep documentation current**:
- Update status indicators as implementation progresses
- Add implementation links when classes are created
- Update examples if actual implementation differs
- Add test links as tests are written

**Maintain traceability**:
- Verify backtracking links remain valid
- Update cross-references when documents move
- Ensure navigation between docs works

**Remove duplication**:
- Eliminate redundant code examples
- Reference JavaDoc instead of repeating details
- Keep only architectural context in specs

### Quality Checks

Before marking a specification as IMPLEMENTED:

- [ ] Status updated to IMPLEMENTED
- [ ] All implementing classes linked
- [ ] All tests linked
- [ ] Redundant code examples removed
- [ ] Backtracking links verified
- [ ] JavaDoc references added
- [ ] Architecture and rationale preserved

## Common Lifecycle Issues

### Issue: Stale Pre-Implementation Content

**Problem**: Keeping detailed examples and expected APIs after implementation exists

**Solution**: Remove redundant content, add links to actual implementation

### Issue: Missing Implementation Links

**Problem**: Marking as IMPLEMENTED without linking to code

**Solution**: Always add implementation and test links before changing status

### Issue: Duplicating JavaDoc

**Problem**: Repeating detailed method behavior in specifications

**Solution**: Link to JavaDoc, keep only architectural context

### Issue: Losing Design Rationale

**Problem**: Removing all pre-implementation content including design decisions

**Solution**: Preserve architectural guidance and rationale, remove only redundant examples
