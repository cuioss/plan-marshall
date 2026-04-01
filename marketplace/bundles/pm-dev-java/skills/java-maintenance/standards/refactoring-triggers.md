# Java-Specific Refactoring Triggers

For general refactoring triggers (code organization, method design, complexity, naming, unused code), see `plan-marshall:dev-general-code-quality` refactoring-triggers.md. This document covers Java-specific detection criteria and tools.

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

**Example — missing null safety**:
```java
// BEFORE - no null safety contract
public class UserRepository {
    public User findById(String id) {       // Can this return null?
        return cache.get(id);               // Unclear contract
    }
}

// AFTER - explicit null safety
@NullMarked
package com.example.repository;

public class UserRepository {
    public Optional<User> findById(String id) {  // Clear: may be absent
        return Optional.ofNullable(cache.get(id));
    }

    public User getById(String id) {              // Clear: never null, throws if missing
        return findById(id).orElseThrow(
            () -> new EntityNotFoundException("User not found: " + id));
    }
}
```

**Inconsistent API Contracts**: Mix of nullable returns and Optional usage
- **Action Required**: Choose consistent pattern per API Return Type Guidelines
- **See**: `pm-dev-java:java-null-safety` skill, section "Optional Usage"
- **Standards**: Use @NonNull for guaranteed results, Optional<T> for potential absence
- **Detection**: Some methods return null, others return Optional for same scenarios

**Manual Enforcement Gaps**: @NonNull methods that can return null
- **Action Required**: Fix implementations to guarantee non-null returns
- **Testing**: Add tests per Implementation Requirements
- **Detection**: Methods annotated @NonNull but with code paths returning null

## When to Adopt Modern Java Features

**Triggers for Action**: Apply modern Java feature adoption when:

**Legacy Switch Statements**: Classic switch statements with breaks detected
- **Action Required**: Convert to switch expressions per Switch Expressions Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-17-features.md` section "Switch Expressions"
- **Detection**: Switch statements with break keywords, fall-through cases

**Example — switch modernization**:
```java
// BEFORE - verbose switch statement
Object obj = getValue();
String result;
if (obj instanceof String) {
    String s = (String) obj;
    result = "String: " + s.toUpperCase();
} else if (obj instanceof Integer) {
    Integer i = (Integer) obj;
    result = "Integer: " + (i * 2);
} else {
    result = "Other: " + obj;
}

// AFTER - pattern matching with switch (Java 21+)
String result = switch (getValue()) {
    case String s  -> "String: " + s.toUpperCase();
    case Integer i -> "Integer: " + (i * 2);
    default        -> "Other: " + getValue();
};
```

**Verbose Object Creation**: Manual data classes without records
- **Action Required**: Replace with records per Records Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-17-features.md` section "Records"
- **Detection**: Classes with only fields, constructor, getters, equals, hashCode, toString

**Example — record migration**:
```java
// BEFORE - verbose data class (78 lines for 3 fields)
public final class Coordinate {
    private final double lat;
    private final double lng;
    private final String label;

    public Coordinate(double lat, double lng, String label) {
        this.lat = lat;
        this.lng = lng;
        this.label = Objects.requireNonNull(label);
    }

    public double getLat() { return lat; }
    public double getLng() { return lng; }
    public String getLabel() { return label; }

    @Override
    public boolean equals(Object o) { /* ... */ }
    @Override
    public int hashCode() { /* ... */ }
    @Override
    public String toString() { /* ... */ }
}

// AFTER - record (1 line for the same semantics)
public record Coordinate(double lat, double lng, String label) {
    public Coordinate {
        Objects.requireNonNull(label);
    }
}
```

**Manual Stream Operations**: Imperative loops that could use streams
- **Action Required**: Simplify with streams per Stream Processing Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-17-features.md` section "Stream Processing"
- **Detection**: Loops with filters, maps, or accumulations that could be replaced with streams
- **Exception**: Simple loops where streams would reduce readability (e.g., single iteration with early return, nested streams >3 levels deep, complex stateful operations requiring mutable accumulation)

**Example — stream adoption**:
```java
// BEFORE - imperative filtering and transformation
List<String> activeEmails = new ArrayList<>();
for (User user : users) {
    if (user.isActive() && user.getEmail() != null) {
        activeEmails.add(user.getEmail().toLowerCase());
    }
}

// AFTER - stream pipeline
List<String> activeEmails = users.stream()
    .filter(User::isActive)
    .map(User::getEmail)
    .filter(Objects::nonNull)
    .map(String::toLowerCase)
    .toList();
```

## When to Apply Lombok Integration

**Triggers for Action**: Apply Lombok integration when:

**Inheritance Anti-Patterns**: Classes extending when they should delegate
- **Action Required**: Replace with composition and `@Delegate` per Lombok Standards
- **See**: `pm-dev-java:java-lombok` skill, section "Delegation with @Delegate"
- **Detection**: Deep inheritance hierarchies, classes extending just to reuse utility methods

**Example — delegation**:
```java
// BEFORE - inheritance for code reuse
public class AuditedUserService extends BaseService {
    // Extends only to get logging/metrics from BaseService
    public User createUser(String name) { /* ... */ }
}

// AFTER - composition with @Delegate
public class AuditedUserService implements ServiceContract {
    @Delegate
    private final BaseService delegate;
    private final AuditLog auditLog;

    public AuditedUserService(BaseService delegate, AuditLog auditLog) {
        this.delegate = delegate;
        this.auditLog = auditLog;
    }

    public User createUser(String name) {
        auditLog.record("createUser", name);
        return delegate.createUser(name);
    }
}
```

**Manual Builder Patterns**: Verbose builder implementations detected
- **Action Required**: Replace with `@Builder` per Lombok Standards
- **See**: `pm-dev-java:java-lombok` skill, section "Builder Pattern with @Builder"
- **Detection**: Manual builder classes with fluent APIs, builder classes with many setters

**Boilerplate Immutable Objects**: Manual equals/hashCode/toString implementations
- **Action Required**: Replace with Java records (preferred) or `@Value` for pre-Java 16
- **See**: `pm-dev-java:java-lombok` skill, section "@Value - Replaced by Records"
- **Detection**: Classes with manual implementations of equals, hashCode, toString for simple data carriers

## Exception Handling Triggers

**Triggers for Action**: Fix exception handling when:

**Generic Exceptions**: Catching `Exception` or `Throwable` broadly
- **Detection**: SonarQube rules `S1181`, `S112`

**Example — specific exception handling**:
```java
// BEFORE - catches everything, loses context
try {
    return objectMapper.readValue(json, Config.class);
} catch (Exception e) {
    throw new RuntimeException(e);
}

// AFTER - specific types, meaningful messages, cause chaining
try {
    return objectMapper.readValue(json, Config.class);
} catch (JsonProcessingException e) {
    throw new ConfigurationException("Failed to parse config from JSON: " + json.substring(0, 50), e);
}
```

## Related Standards

- maintenance-prioritization.md - Java-specific prioritization
- compliance-checklist.md - How to verify fixes are complete
- `plan-marshall:dev-general-code-quality` - General refactoring triggers and prioritization
