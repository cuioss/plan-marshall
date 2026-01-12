# Value Object Testing Standards

## Required Imports

```java
// CUI Test Value Objects
import de.cuioss.test.valueobjects.api.contracts.ShouldHandleObjectContracts;
```

## Overview

Value objects require comprehensive contract testing to ensure proper behavior in collections, caching, and persistence scenarios. CUI projects use the cui-test-value-objects framework for consistent and thorough contract testing.

## Contract Testing Requirements

### Primary Interface: ShouldHandleObjectContracts<T>

Use `ShouldHandleObjectContracts<T>` for comprehensive value object testing. This interface provides complete contract verification including:

* equals() and hashCode() contracts
* toString() behavior
* Serializable contracts (if applicable)
* Builder pattern validation
* Immutability verification

```java
@EnableGeneratorController
class UserDataTest implements ShouldHandleObjectContracts<UserData> {

    @Override
    public UserData getUnderTest() {
        return UserData.builder()
            .username(Generators.strings().next())
            .email(Generators.emailAddress().next())
            .age(Generators.integers(18, 100).next())
            .build();
    }
}
```

## When to Apply Value Object Testing

### Apply ShouldHandleObjectContracts<T> when:

* Class implements custom equals()/hashCode() methods
* Class represents domain data with value semantics
* Class is used in collections or as map keys
* Class participates in caching or persistence operations
* Class is annotated with `@Value`, `@Data`, or implements custom equality

### Do NOT apply to:

* **Enums** - Already have proper equals/hashCode from Java
* **Utility classes** - Classes with only static methods
* **Infrastructure classes** - Parsers, validators, builders
* **Non-value objects** - Classes that don't represent business value objects
* **Builder pattern classes** - Test the built object instead, not the builder

## Individual Contract Interfaces

When you need specific contract testing without full coverage, use individual interfaces:

### ShouldImplementEqualsAndHashCode<T>

For testing only equals() and hashCode() contracts:

```java
class SimpleValueTest implements ShouldImplementEqualsAndHashCode<SimpleValue> {
    @Override
    public SimpleValue getUnderTest() {
        return new SimpleValue(Generators.strings().next());
    }
}
```

### ShouldBeSerializable<T>

For classes implementing Serializable:

```java
class SerializableValueTest implements ShouldBeSerializable<SerializableValue> {
    @Override
    public SerializableValue getUnderTest() {
        return new SerializableValue(Generators.strings().next());
    }
}
```

## Generator Integration

**CRITICAL**: The `getUnderTest()` method MUST use cui-test-generator for all data creation.

For comprehensive generator usage guidelines, see [test-generator-framework.md](test-generator-framework.md).

### Good Examples:

```java
@Override
public TokenConfig getUnderTest() {
    return TokenConfig.builder()
        .issuer(Generators.strings().next())
        .clientId(Generators.strings().next())
        .audience(Generators.fixedValues(String.class, "api", "web").next())
        .expirationMinutes(Generators.integers(1, 60).next())
        .build();
}
```

### Bad Examples (Do NOT use):

```java
// ❌ Manual data creation
@Override
public TokenConfig getUnderTest() {
    return TokenConfig.builder()
        .issuer("https://example.com")  // Hardcoded value
        .clientId("test-client")        // Hardcoded value
        .build();
}

// ❌ Using Random or other libraries
@Override
public TokenConfig getUnderTest() {
    Random random = new Random();
    return TokenConfig.builder()
        .issuer("issuer-" + random.nextInt())  // Wrong generator
        .build();
}
```

## Testing Immutability

For immutable value objects (e.g., using `@Value`), the contract testing automatically verifies immutability:

```java
import lombok.Value;

@Value
@Builder
class ImmutableConfig {
    String name;
    int value;
}

@EnableGeneratorController
class ImmutableConfigTest implements ShouldHandleObjectContracts<ImmutableConfig> {
    @Override
    public ImmutableConfig getUnderTest() {
        return ImmutableConfig.builder()
            .name(Generators.strings().next())
            .value(Generators.integers().next())
            .build();
    }
    // Contract testing automatically verifies immutability
}
```

## Common Mistakes to Avoid

### 1. Testing Enums as Value Objects

```java
// ❌ Wrong - Enums don't need contract testing
class TokenTypeTest implements ShouldHandleObjectContracts<TokenType> {
    // Unnecessary - enums have proper equals/hashCode from Java
}
```

### 2. Testing Infrastructure Classes

```java
// ❌ Wrong - Parsers are not value objects
class TokenParserTest implements ShouldHandleObjectContracts<TokenParser> {
    // Infrastructure classes should have functional tests, not contract tests
}
```

### 3. Mixing Business Logic with Contract Testing

```java
// ❌ Wrong - Don't mix contract testing with business logic tests
class UserDataTest implements ShouldHandleObjectContracts<UserData> {

    @Test
    void shouldValidateEmail() {
        // Business logic test doesn't belong in contract test class
    }
}

// ✅ Correct - Separate contract and business logic tests
class UserDataContractTest implements ShouldHandleObjectContracts<UserData> {
    // Only contract testing
}

class UserDataValidationTest {
    @Test
    void shouldValidateEmail() {
        // Business logic tests
    }
}
```

## Verification Requirements

After implementing value object contract testing:

1. **Verify Coverage**: Ensure equals(), hashCode(), toString(), and Serializable contracts are tested
2. **Generator Integration**: Confirm all test data uses cui-test-generator
3. **Test Execution**: Ensure all contract tests pass
4. **No Hardcoded Data**: Verify no manual or hardcoded test data

## Additional Resources

* CUI Test Value Objects Framework: https://github.com/cuioss/cui-test-value-objects
* CUI Test Generator: https://github.com/cuioss/cui-test-generator
