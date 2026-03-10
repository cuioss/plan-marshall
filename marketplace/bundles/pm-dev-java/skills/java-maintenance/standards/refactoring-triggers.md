# Java-Specific Refactoring Triggers

For general refactoring triggers (code organization, method design, complexity, naming, unused code), see `pm-dev-general:dev-code-quality` refactoring-triggers.md. This document covers Java-specific detection criteria and tools.

## Java-Specific SonarQube References

* High Cognitive Complexity: SonarQube rule `java:S3776` (threshold >15)
* Catch Throwable: SonarQube rule `S1181`
* Throw generic exceptions: SonarQube rule `S112`

## When to Fix Null Safety Violations

**Triggers for Action**: Apply null safety fixes when:

**Missing @NonNull Annotations**: Public API methods lack null safety documentation
- **Action Required**: Add annotations per @NonNull Annotations Standards
- **See**: `pm-dev-java:java-null-safety` skill
- **Implementation**: Ensure methods guarantee non-null returns per Implementation Requirements
- **Detection**: Public methods without @NonNull annotations, package-info.java missing @NullMarked

**Inconsistent API Contracts**: Mix of nullable returns and Optional usage
- **Action Required**: Choose consistent pattern per API Return Type Guidelines
- **See**: `pm-dev-java:java-null-safety` skill, section "Optional Usage"
- **Standards**: Use @NonNull for guaranteed results, Optional<T> for potential absence
- **Detection**: Some methods return null, others return Optional for same scenarios

**Manual Enforcement Gaps**: @NonNull methods that can return null
- **Action Required**: Fix implementations to guarantee non-null returns
- **Testing**: Add tests per Implementation Requirements
- **Detection**: Methods annotated @NonNull but with code paths returning null

### When to Adopt Modern Java Features

**Triggers for Action**: Apply modern Java feature adoption when:

**Legacy Switch Statements**: Classic switch statements with breaks detected
- **Action Required**: Convert to switch expressions per Switch Expressions Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-17-features.md` section "Switch Expressions"
- **Detection**: Switch statements with break keywords, fall-through cases

**Verbose Object Creation**: Manual data classes without records
- **Action Required**: Replace with records per Records Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-17-features.md` section "Records"
- **Detection**: Classes with only fields, constructor, getters, equals, hashCode, toString

**Manual Stream Operations**: Imperative loops that could use streams
- **Action Required**: Simplify with streams per Stream Processing Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-17-features.md` section "Stream Processing"
- **Detection**: Loops with filters, maps, or accumulations that could be replaced with streams
- **Exception**: Simple loops where streams would reduce readability (e.g., single iteration with early return, nested streams >3 levels deep, complex stateful operations requiring mutable accumulation)

### When to Apply Lombok Integration

**Triggers for Action**: Apply Lombok integration when:

**Inheritance Anti-Patterns**: Classes extending when they should delegate
- **Action Required**: Replace with composition and `@Delegate` per Lombok Standards
- **See**: `pm-dev-java:java-lombok` skill, section "Delegation with @Delegate"
- **Detection**: Deep inheritance hierarchies, classes extending just to reuse utility methods

**Manual Builder Patterns**: Verbose builder implementations detected
- **Action Required**: Replace with `@Builder` per Lombok Standards
- **See**: `pm-dev-java:java-lombok` skill, section "Builder Pattern with @Builder"
- **Detection**: Manual builder classes with fluent APIs, builder classes with many setters

**Boilerplate Immutable Objects**: Manual equals/hashCode/toString implementations
- **Action Required**: Replace with `@Value` per Lombok Standards
- **See**: `pm-dev-java:java-lombok` skill, section "Immutable Objects with @Value"
- **Detection**: Classes with manual implementations of equals, hashCode, toString for simple data carriers

## Related Standards

- maintenance-prioritization.md - Java-specific prioritization
- compliance-checklist.md - How to verify fixes are complete
- `pm-dev-general:dev-code-quality` - General refactoring triggers and prioritization
