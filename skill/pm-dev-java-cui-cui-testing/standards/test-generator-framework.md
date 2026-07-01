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

## Core Components

### Generators - The Central Factory

The `Generators` class is your primary entry point for test data generation:

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

### TypedGenerator - The Core Interface

`TypedGenerator` is the foundation interface for all generators:

```java
public class CustomGenerator implements TypedGenerator<MyType> {
    @Override
    public MyType next() {
        return new MyType(Generators.strings().next());
    }

    @Override
    public Class<MyType> getType() {
        return MyType.class;
    }
}
```

### @EnableGeneratorController

Enables reproducible test data generation. Must be present on every test class using generators:

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

### @GeneratorSeed

Fixed seeds are **only for reproducing test failures during debugging**. Never commit `@GeneratorSeed` annotations.

```java
@EnableGeneratorController
class MyTest {
    @Test
    @GeneratorSeed(4711L) // REMOVE BEFORE COMMIT!
    void shouldGenerateSpecificData() {
        var data = Generators.strings().next();
    }
}
```

## Parameterized Testing with Generators

Parameterized tests are **mandatory** when testing 3+ similar variants of the same behavior. For general parameterized test patterns, see `pm-dev-java:junit-core` standards.

**Annotation Preference Order:**

1. **@GeneratorsSource** - Single generator via `GeneratorType` enum (most preferred)
2. **@CompositeTypeGeneratorSource** - Multiple generators combined
3. **@TypeGeneratorSource** - Custom generator classes
4. **@TypeGeneratorMethodSource** - Factory methods returning generators
5. **@TypeGeneratorFactorySource** - Factory methods with parameters

### @GeneratorsSource

Uses the `GeneratorType` enum to select a built-in generator:

```java
@ParameterizedTest
@GeneratorsSource(
    generator = GeneratorType.STRINGS,
    minSize = 3, maxSize = 10, count = 5
)
void testWithStringGenerator(String value) {
    assertNotNull(value);
    assertTrue(value.length() >= 3 && value.length() <= 10);
}
```

### @CompositeTypeGeneratorSource

Combines multiple generators for multi-parameter tests. Supports `generators` (enum), `generatorClasses`, or `generatorMethods` attributes:

```java
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
```

### @TypeGeneratorSource

References a generator class directly:

```java
@ParameterizedTest
@TypeGeneratorSource(value = NonBlankStringGenerator.class, count = 5)
void testWithGeneratedStrings(String value) {
    assertNotNull(value);
    assertFalse(value.isBlank());
}
```

### @TypeGeneratorMethodSource

References a static method that returns a configured generator:

```java
@ParameterizedTest
@TypeGeneratorMethodSource("createStringGenerator")
void testWithCustomGenerator(String value) {
    assertNotNull(value);
}

static TypedGenerator<String> createStringGenerator() {
    return Generators.strings(5, 10);
}
```

### @TypeGeneratorFactorySource

Uses a factory class with parameters to create generators:

```java
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

// Factory class
public class MyGeneratorFactory {
    public static TypedGenerator<Integer> createRangeGenerator(String min, String max) {
        return Generators.integers(Integer.parseInt(min), Integer.parseInt(max));
    }
}
```

## GeneratorType Enum

Type-safe references to all available generators:

* **Standard generators**: `STRINGS`, `INTEGERS`, `BOOLEANS`, `LOCAL_DATE_TIMES`, `URLS`
* **Domain generators** (DOMAIN_ prefix): `DOMAIN_EMAIL`, `DOMAIN_CITY`, `DOMAIN_FULL_NAME`, `DOMAIN_ZIP_CODE`

Each enum value contains the factory method name, factory class, and return type.

## Domain-Specific Generators

Specialized generators for common domains:

```java
var stringList = new CollectionGenerator<>(Generators.strings()).list(5);
var dateTime = new ZonedDateTimeGenerator().future();
var floats = new FloatObjectGenerator(0.0f, 100.0f).next();
var url = new URLGenerator().next();
var nonBlank = new NonBlankStringGenerator().next();
var email = new EmailGenerator().next();
var city = new CityGenerator().next();
var name = new FullNameGenerator().next();
```

## Important Notes

### Required Imports

```java
// Core
import de.cuioss.test.generator.Generators;
import de.cuioss.test.generator.TypedGenerator;

// JUnit 5 Integration
import de.cuioss.test.generator.junit.EnableGeneratorController;
import de.cuioss.test.generator.junit.GeneratorSeed;
import de.cuioss.test.generator.junit.GeneratorsSource;
import de.cuioss.test.generator.junit.TypeGeneratorSource;
import de.cuioss.test.generator.junit.TypeGeneratorMethodSource;
import de.cuioss.test.generator.junit.TypeGeneratorFactorySource;
import de.cuioss.test.generator.junit.CompositeTypeGeneratorSource;

// Parameterized Testing
import de.cuioss.test.generator.junit.parameterized.GeneratorType;
```

### Internal Package Restriction

The package `de.cuioss.test.generator.internal.net.java.quickcheck` contains internal implementation details derived from QuickCheck. **Do not use any classes from this package directly**. Always use the public API through `Generators`, `TypedGenerator`, and classes in `de.cuioss.test.generator.domain` and `de.cuioss.test.generator.impl`.

## Additional Resources

**Source:**
* [README Documentation](https://github.com/cuioss/cui-test-generator/blob/main/README.adoc)

**Additional References:**
* [CUI Test Generator Framework](https://github.com/cuioss/cui-test-generator)
* [Complete Usage Guide](https://gitingest.com/github.com/cuioss/cui-test-generator)
