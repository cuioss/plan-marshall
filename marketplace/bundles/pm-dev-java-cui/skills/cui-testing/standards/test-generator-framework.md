# CUI Test Generator Standards and Reference

## Overview

The CUI Test Generator framework (`cui-test-generator`) is **mandatory** for ALL test data generation in CUI projects. This framework provides robust and reproducible test data generation, combining random data with the ability to reproduce specific test scenarios during debugging.

## Mandatory Requirements

### Required for All Test Data

* **MANDATORY**: Use cui-test-generator for ALL test data generation
* **FORBIDDEN**: Do NOT use manual data creation, Random, Faker, or other data tools
* **REQUIRED ANNOTATION**: `@EnableGeneratorController` MUST be added to every test class using generators
* **GENERATOR METHODS**: Use `Generators.strings()`, `integers()`, `booleans()`, etc. for all values

### Maven Coordinates

```xml
<dependency>
    <groupId>de.cuioss.test</groupId>
    <artifactId>cui-test-generator</artifactId>
</dependency>
```

## Required Imports

```java
// CUI Test Generator Core
import de.cuioss.test.generator.Generators;
import de.cuioss.test.generator.TypedGenerator;

// CUI Test Generator JUnit 5 Integration
import de.cuioss.test.generator.junit.EnableGeneratorController;
import de.cuioss.test.generator.junit.GeneratorSeed;
import de.cuioss.test.generator.junit.GeneratorsSource;
import de.cuioss.test.generator.junit.TypeGeneratorSource;
import de.cuioss.test.generator.junit.TypeGeneratorMethodSource;
import de.cuioss.test.generator.junit.TypeGeneratorFactorySource;
import de.cuioss.test.generator.junit.CompositeTypeGeneratorSource;

// CUI Test Generator Parameterized Testing
import de.cuioss.test.generator.junit.parameterized.GeneratorType;

// CUI Test Generator Domain-specific generators
// Note: Use Generators.emailAddress(), Generators.cities(), etc. instead of direct imports
import de.cuioss.test.generator.domain.EmailGenerator;
import de.cuioss.test.generator.domain.CityGenerator;
import de.cuioss.test.generator.domain.FullNameGenerator;
```

## Core Components

### Generators - The Central Factory

The `Generators` class is your primary entry point for test data generation. It provides factory methods for creating generators for most Java built-in types:

```java
// Basic type generation
String text = Generators.strings().next();
Integer number = Generators.integers().next();
LocalDateTime dateTime = Generators.localDateTimes().next();

// Configurable generation
String letters = Generators.letterStrings(5, 10).next(); // 5-10 characters
List<Integer> numbers = Generators.integers(1, 100).list(5); // 5 numbers between 1-100

// Fixed and enum values
var urlGen = Generators.fixedValues(String.class,
    "https://cuioss.de",
    "https://www.heise.de");
var enumGen = Generators.enumValues(TimeUnit.class);
```

### Test Reproducibility with JUnit 5

#### EnableGeneratorController

The `@EnableGeneratorController` annotation enables reproducible test data generation:

```java
@EnableGeneratorController
class MyGeneratorTest {
    @Test
    void shouldGenerateConsistentData() {
        var result = Generators.strings().next();
        assertFalse(result.isEmpty());
    }
}
```

#### GeneratorSeed

**CRITICAL: Fixed seeds are ONLY for reproducing test failures during debugging. NEVER commit tests with hardcoded @GeneratorSeed values.**

Use `@GeneratorSeed` to fix the random seed for reproducible tests (debugging only):

```java
@EnableGeneratorController
class MyTest {
    @Test
    @GeneratorSeed(4711L) // Method-level seed - REMOVE BEFORE COMMIT!
    void shouldGenerateSpecificData() {
        // Always generates the same data for debugging
        var data = Generators.strings().next();
    }
}

@EnableGeneratorController
@GeneratorSeed(8042L) // Class-level seed - REMOVE BEFORE COMMIT!
class AllTestsReproducible {
    // All tests use the same seed - for debugging only
}
```

#### GeneratorsSource with Enum-Based Configuration

**When to Use Parameterized Tests:**

Parameterized tests are **mandatory** when testing at least 3 similar variants of the same behavior.

For complete parameterized test best practices including quality requirements, see [Test Quality Standards - Parameterized Test Guidelines](testing-quality-standards.md#parameterized-test-guidelines).

**Annotation Preference Order:**

1. **@GeneratorsSource** (Most Preferred) - For single generator with GeneratorType enum
2. **@CompositeTypeGeneratorSource** (Highly Preferred) - For multiple generators combined
3. **@TypeGeneratorSource** - For custom generator classes
4. **@TypeGeneratorMethodSource** - For factory methods returning generators
5. **@TypeGeneratorFactorySource** - For factory methods with parameters

The recommended way to use generators in parameterized tests is with `@GeneratorsSource` and the `GeneratorType` enum:

```java
@EnableGeneratorController
class GeneratorsSourceTest {

    // String generator with size parameters
    @ParameterizedTest
    @GeneratorsSource(
        generator = GeneratorType.STRINGS,
        minSize = 3,
        maxSize = 10,
        count = 5
    )
    void testWithStringGenerator(String value) {
        assertNotNull(value);
        assertTrue(value.length() >= 3 && value.length() <= 10);
    }

    // Number generator with range parameters
    @ParameterizedTest
    @GeneratorsSource(
        generator = GeneratorType.INTEGERS,
        low = "1",
        high = "100",
        count = 5
    )
    void testWithIntegerGenerator(Integer value) {
        assertNotNull(value);
        assertTrue(value >= 1 && value <= 100);
    }

    // Simple generator without parameters
    @ParameterizedTest
    @GeneratorsSource(
        generator = GeneratorType.NON_EMPTY_STRINGS,
        count = 3
    )
    void testWithNonEmptyStrings(String value) {
        assertNotNull(value);
        assertFalse(value.isEmpty());
    }

    // Domain-specific generator
    @ParameterizedTest
    @GeneratorsSource(
        generator = GeneratorType.DOMAIN_EMAIL,
        count = 3
    )
    void testWithEmailGenerator(String email) {
        assertNotNull(email);
        assertTrue(email.contains("@"));
    }

    // Using GeneratorSeed for reproducible tests
    @ParameterizedTest
    @GeneratorSeed(42L)
    @GeneratorsSource(
        generator = GeneratorType.STRINGS,
        minSize = 3,
        maxSize = 10,
        count = 3
    )
    void testWithSpecificSeed(String value) {
        // This test will always generate the same values
        assertNotNull(value);
    }
}
```

#### TypeGenerator in Parameterized Tests

You can also directly use TypeGenerator in parameterized tests with `@TypeGeneratorSource` and `@TypeGeneratorMethodSource`:

```java
@EnableGeneratorController
class ParameterizedGeneratorTest {

    // Class-based configuration - uses the generator's default constructor
    @ParameterizedTest
    @TypeGeneratorSource(NonBlankStringGenerator.class)
    void testWithGeneratedStrings(String value) {
        assertNotNull(value);
        assertFalse(value.isBlank());
    }

    // Generate multiple values
    @ParameterizedTest
    @TypeGeneratorSource(value = IntegerGenerator.class, count = 5)
    void testWithMultipleIntegers(Integer value) {
        assertNotNull(value);
    }

    // Method-based configuration - uses a method that returns a configured generator
    @ParameterizedTest
    @TypeGeneratorMethodSource("createStringGenerator")
    void testWithCustomGenerator(String value) {
        assertNotNull(value);
    }

    // Factory method that returns a configured generator
    static TypedGenerator<String> createStringGenerator() {
        return Generators.strings(5, 10); // Strings between 5-10 characters
    }

    // Reference a method in another class
    @ParameterizedTest
    @TypeGeneratorMethodSource("de.cuioss.test.MyGeneratorFactory#createGenerator")
    void testWithExternalGenerator(MyType value) {
        // test with value
    }
}
```

#### Factory-Based TypeGenerator in Parameterized Tests

Use `@TypeGeneratorFactorySource` to create generators using factory methods:

```java
@EnableGeneratorController
class FactoryBasedGeneratorTest {

    // Use a factory method to create a generator
    @ParameterizedTest
    @TypeGeneratorFactorySource(
        factoryClass = MyGeneratorFactory.class,
        factoryMethod = "createStringGenerator"
    )
    void testWithFactoryGenerator(String value) {
        assertNotNull(value);
    }

    // Factory with parameters
    @ParameterizedTest
    @TypeGeneratorFactorySource(
        factoryClass = MyGeneratorFactory.class,
        factoryMethod = "createRangeGenerator",
        methodParameters = {"1", "100"},
        count = 5
    )
    void testWithParameterizedFactory(Integer value) {
        assertNotNull(value);
        assertTrue(value >= 1 && value <= 100);
    }

    // With specific seed for reproducible tests
    @ParameterizedTest
    @GeneratorSeed(42L)
    @TypeGeneratorFactorySource(
        factoryClass = MyGeneratorFactory.class,
        factoryMethod = "createStringGenerator",
        count = 3
    )
    void testWithSpecificSeed(String value) {
        // This test will always generate the same values
        assertNotNull(value);
    }
}

// Factory class
public class MyGeneratorFactory {
    public static TypedGenerator<String> createStringGenerator() {
        return Generators.strings(5, 10);
    }

    public static TypedGenerator<Integer> createRangeGenerator(String min, String max) {
        return Generators.integers(Integer.parseInt(min), Integer.parseInt(max));
    }
}
```

#### Composite TypeGenerator in Parameterized Tests

Use `@CompositeTypeGeneratorSource` to combine multiple generators. The preferred approach is to use the `generators` attribute with `GeneratorType` enum values:

```java
@EnableGeneratorController
class CompositeGeneratorTest {

    // Preferred: Combine multiple generators using GeneratorType enum
    @ParameterizedTest
    @CompositeTypeGeneratorSource(
        generators = {
            GeneratorType.NON_EMPTY_STRINGS,
            GeneratorType.INTEGERS
        },
        count = 3
    )
    void testWithGeneratorTypes(String text, Integer number) {
        assertNotNull(text);
        assertNotNull(number);
    }

    // Domain-specific generators can also be used
    @ParameterizedTest
    @CompositeTypeGeneratorSource(
        generators = {
            GeneratorType.DOMAIN_EMAIL,
            GeneratorType.DOMAIN_ZIP_CODE
        },
        count = 2
    )
    void testWithDomainGenerators(String email, String zipCode) {
        assertNotNull(email);
        assertTrue(email.contains("@"));
        assertNotNull(zipCode);
    }

    // Alternative: Combine multiple generator classes
    @ParameterizedTest
    @CompositeTypeGeneratorSource(
        generatorClasses = {
            NonBlankStringGenerator.class,
            IntegerGenerator.class
        },
        count = 3
    )
    void testWithMultipleGenerators(String text, Integer number) {
        assertNotNull(text);
        assertNotNull(number);
    }

    // Alternative: Combine multiple generator methods
    @ParameterizedTest
    @CompositeTypeGeneratorSource(
        generatorMethods = {
            "createStringGenerator",
            "createIntegerGenerator"
        },
        count = 2
    )
    void testWithMultipleMethodGenerators(String text, Integer number) {
        assertNotNull(text);
        assertNotNull(number);
    }

    // With specific seed for reproducible tests
    @ParameterizedTest
    @GeneratorSeed(42L)
    @CompositeTypeGeneratorSource(
        generators = {
            GeneratorType.NON_EMPTY_STRINGS,
            GeneratorType.INTEGERS
        },
        count = 2
    )
    void testWithSpecificSeed(String text, Integer number) {
        // This test will always generate the same combinations
        assertNotNull(text);
        assertNotNull(number);
    }

    // Generator methods
    static TypedGenerator<String> createStringGenerator() {
        return Generators.strings(5, 10);
    }

    static TypedGenerator<Integer> createIntegerGenerator() {
        return Generators.integers(1, 100);
    }
}
```

### TypedGenerator - The Core Interface

`TypedGenerator` is the foundation interface for all generators:

```java
public class CustomGenerator implements TypedGenerator<MyType> {
    @Override
    public MyType next() {
        // Generate and return a new instance
        return new MyType(Generators.strings().next());
    }

    @Override
    public Class<MyType> getType() {
        return MyType.class;
    }
}
```

### GeneratorType Enum

The `GeneratorType` enum provides a type-safe way to reference all available generators:

* Standard generators from Generators class:
  * `GeneratorType.STRINGS` - Strings generator
  * `GeneratorType.INTEGERS` - Integers generator
  * `GeneratorType.BOOLEANS` - Booleans generator
  * `GeneratorType.LOCAL_DATE_TIMES` - LocalDateTime generator
  * `GeneratorType.URLS` - URL generator

* Domain-specific generators with DOMAIN_ prefix:
  * `GeneratorType.DOMAIN_EMAIL` - Email address generator
  * `GeneratorType.DOMAIN_CITY` - City name generator
  * `GeneratorType.DOMAIN_FULL_NAME` - Person name generator
  * `GeneratorType.DOMAIN_ZIP_CODE` - Zip/postal code generator

Each enum value contains:

* The method name in the Generators class (for standard generators)
* The factory class (Generators.class or the domain-specific generator class)
* The return type of the generator

This makes it easy to use with `@GeneratorsSource` and `@CompositeTypeGeneratorSource`.

### Domain-Specific Generators

The framework provides specialized generators for common domains:

```java
// Collection generation
var stringList = new CollectionGenerator<>(Generators.strings())
    .list(5); // List of 5 strings

// Date/Time with zones
var dateTime = new ZonedDateTimeGenerator().future();

// Numeric ranges
var floats = new FloatObjectGenerator(0.0f, 100.0f).next();

// URLs and strings
var url = new URLGenerator().next();
var nonBlank = new NonBlankStringGenerator().next();

// Domain-specific generators (also available via GeneratorType enum)
var email = new EmailGenerator().next();
var city = new CityGenerator().next();
var name = new FullNameGenerator().next();
```

## Important Notes

### Internal Package Restriction

The package `de.cuioss.test.generator.internal.net.java.quickcheck` contains internal implementation details derived from QuickCheck. **Do not use any classes from this package directly**. Instead, always use the public API through:

* `de.cuioss.test.generator.Generators`
* `de.cuioss.test.generator.TypedGenerator`
* Classes in `de.cuioss.test.generator.domain` and `de.cuioss.test.generator.impl`

## Anti-Patterns to Avoid

### ❌ Manual Data Creation

```java
// WRONG - Manual data creation
@Test
void shouldValidateUser() {
    User user = new User("john.doe", "john@example.com", 30);
    // This is hardcoded and doesn't test variability
}

// CORRECT - Generator-based
@Test
void shouldValidateUser() {
    User user = new User(
        Generators.strings().next(),
        Generators.emailAddress().next(),
        Generators.integers(18, 100).next()
    );
}
```

### ❌ Using Java Random or Other Libraries

```java
// WRONG - Using Random
@Test
void shouldProcessRandomData() {
    Random random = new Random();
    String value = "test-" + random.nextInt();
    // Not reproducible, not integrated with framework
}

// WRONG - Using Faker or other tools
@Test
void shouldProcessFakeData() {
    Faker faker = new Faker();
    String name = faker.name().firstName();
    // Wrong framework, inconsistent with CUI standards
}
```

### ❌ Committed Generator Seeds

⚠️ **Never commit @GeneratorSeed annotations!** They are for debugging only.

See "@GeneratorSeed" section above for proper usage. Seeds must be removed before committing as they defeat the purpose of random testing.

### ❌ Not Using @EnableGeneratorController

```java
// WRONG - Missing required annotation
class GeneratorTest {
    @Test
    void shouldGenerate() {
        String value = Generators.strings().next(); // May not work correctly
    }
}

// CORRECT - Annotation present
@EnableGeneratorController
class GeneratorTest {
    @Test
    void shouldGenerate() {
        String value = Generators.strings().next();
    }
}
```

## Migration from Manual Data

When migrating existing tests:

1. **Identify Violations**: Find manual data creation, hardcoded values, non-CUI frameworks
2. **Apply Generators**: Replace with appropriate Generators.* calls
3. **Add Annotations**: Ensure @EnableGeneratorController is present
4. **Verify Tests**: Ensure all tests pass with generated data
5. **Remove Seeds**: Remove any @GeneratorSeed annotations used during debugging

## Best Practices

1. Use `Generators` as your primary entry point
2. Enable `@EnableGeneratorController` for all test classes using generators
3. Never commit `@GeneratorSeed` annotations (debugging only)
4. Create custom generators by implementing `TypedGenerator`
5. Use domain-specific generators for specialized test data
6. Never use classes from the internal package
7. Use parameterized tests for 3+ similar test variants
8. Prefer `@GeneratorsSource` and `@CompositeTypeGeneratorSource` for parameterized tests

## Additional Resources

**Source:**
* [README Documentation](https://github.com/cuioss/cui-test-generator/blob/main/README.adoc)

**Additional References:**
* [CUI Test Generator Framework](https://github.com/cuioss/cui-test-generator)
* [Complete Usage Guide](https://gitingest.com/github.com/cuioss/cui-test-generator)
