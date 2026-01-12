# Standards Compliance Checklist

Comprehensive checklist for verifying Java code compliance with all CUI standards after maintenance work.

## Purpose

This checklist ensures systematic verification of standards compliance after refactoring or maintenance work. It provides a structured approach to validate that all standards have been properly applied.

## How to Use This Checklist

**For each class being maintained:**

1. Work through checklist sections sequentially
2. Mark items as compliant or note issues
3. Address all non-compliant items
4. Re-verify after fixes
5. Document any intentional deviations with rationale

**Verification levels:**
- [OK] **Compliant** - Meets standards fully
- [WARNING] **Needs Work** - Violations found, must fix
- [N/A] **Not Applicable** - Standard doesn't apply to this code

## Package Organization

**Standards Reference**: Package Structure Standards in java-core
**See**: `pm-dev-java:java-core` skill, `standards/java-core-patterns.md` section "Package Organization"

### Verification Items

- [ ] **Feature-Based Packages**: Code organized by feature/domain, not by layer
  - [AVOID] `com.example.controllers`, `com.example.services`, `com.example.repositories`
  - [PREFER] `com.example.authentication`, `com.example.billing`, `com.example.orders`

- [ ] **Package-Info Present**: Each package has `package-info.java` with @NullMarked
  - Must contain package declaration
  - Must have @NullMarked annotation
  - Should have package-level Javadoc

- [ ] **Logical Grouping**: Related classes are in same package
  - Value objects with their services
  - Interfaces with their implementations (when tightly coupled)
  - Related utilities together

## Class Design

**Standards Reference**: Class Structure Standards in java-core
**See**: `pm-dev-java:java-core` skill, `standards/java-core-patterns.md` section "Class Design"

### Verification Items

- [ ] **Single Responsibility**: Each class has one clear reason to change
  - Class name clearly describes responsibility
  - All methods relate to class purpose
  - No "and" in class description

- [ ] **Appropriate Access Modifiers**: Classes have correct visibility
  - Public only when part of API
  - Package-private for implementation details
  - Final for classes not designed for extension

- [ ] **Reasonable Size**: Classes are focused and maintainable
  - Typically under 500 lines
  - Not more than 20-30 methods
  - No "god classes"

- [ ] **Proper Dependencies**: Dependencies are managed correctly
  - Constructor injection preferred
  - Field injection documented if required by framework
  - No circular dependencies

## Method Design

**Standards Reference**: Method Design Standards in java-core
**See**: `pm-dev-java:java-core` skill, `standards/java-core-patterns.md` section "Method Design"

### Verification Items

- [ ] **Method Length**: Methods are short and focused (see [refactoring-triggers.md](refactoring-triggers.md) for detailed criteria)
  - Target under 50 lines, require refactoring over 60 lines
  - Single level of abstraction per method
  - Complex methods extracted into helper methods

- [ ] **Parameter Count**: Methods have manageable parameters
  - 0-3 parameters preferred
  - Parameter objects used for 3+ related parameters
  - Builder pattern for complex construction

- [ ] **Cyclomatic Complexity**: Methods are simple enough
  - Complexity under 15 (SonarQube default)
  - Nested loops/conditionals extracted
  - Switch expressions instead of statements

- [ ] **Cognitive Complexity**: Methods are understandable
  - Cognitive complexity under 15 (SonarQube rule java:S3776)
  - No deeply nested control structures
  - Complex conditions extracted to named boolean methods
  - Guard clauses used instead of deep nesting

- [ ] **Nesting Depth**: Methods avoid excessive indentation
  - Maximum 3 levels of nesting
  - Guard clauses (early returns) used to reduce nesting
  - Nested blocks extracted to helper methods when needed

- [ ] **Boolean Logic Clarity**: Complex conditions are readable
  - No conditions with 3+ boolean operators without extraction
  - Complex conditions extracted to well-named boolean methods/variables
  - Conditions clearly express business logic intent

- [ ] **Appropriate Abstraction**: Code is neither over- nor under-abstracted
  - No single-use abstractions without clear extensibility need
  - No interfaces with only one implementation (unless justified)
  - No wrapper classes adding no value
  - Simplicity balanced with SOLID principles

- [ ] **Logic Simplification**: Code uses simplest correct form
  - No redundant boolean expressions (e.g., `if (x) return true; else return false;`)
  - No unnecessary else-after-return patterns
  - No double negatives without clear intent
  - Boolean algebra applied where it improves clarity

- [ ] **Command-Query Separation**: Methods either query or command, not both
  - Query methods return values, don't modify state
  - Command methods modify state, return void or status
  - Exceptions for fluent APIs (builders)

- [ ] **Meaningful Names**: All methods have descriptive names
  - Start with verb (get, set, calculate, validate, etc.)
  - Clearly describe what method does
  - No abbreviations unless standard

## Null Safety

**Standards Reference**: Null Safety Standards in java-core
**See**: `pm-dev-java:java-core` skill, `standards/java-null-safety.md`

### Verification Items

- [ ] **@NullMarked Package**: Package-info.java has @NullMarked annotation
  - Enables null safety for entire package
  - Uses org.jspecify.annotations.NullMarked

- [ ] **@NonNull for Return Types**: All public methods guarantee non-null returns
  - No @Nullable on return types (use Optional instead)
  - Implementation ensures non-null return
  - Tested with null safety tests

- [ ] **Optional for Absence**: Optional used for "no result" scenarios
  - Never return null for Optional results
  - Use Optional<T> when result may not exist
  - Don't use Optional for fields or parameters

- [ ] **Defensive Null Checks**: API boundaries validate inputs
  - Objects.requireNonNull() at API entry points
  - Clear error messages in null checks
  - NPE prevention at boundaries

- [ ] **Null Safety Tests**: Tests verify null contracts
  - Tests verify @NonNull methods don't return null
  - Tests verify null parameters are rejected
  - Tests verify Optional usage is correct

## Exception Handling

**Standards Reference**: Exception Handling Standards in java-core
**See**: `pm-dev-java:java-core` skill, `standards/java-core-patterns.md` section "Exception Handling"

### Verification Items

- [ ] **Specific Exceptions**: Catch specific exception types
  - No catch(Exception e) or catch(RuntimeException e)
  - Catch specific exceptions you can handle
  - Let others propagate

- [ ] **Meaningful Messages**: All exceptions have descriptive messages
  - Explain what went wrong
  - Include relevant context
  - No generic "Error" messages

- [ ] **Appropriate Types**: Use correct exception types
  - Checked exceptions for recoverable conditions
  - Unchecked exceptions for programming errors
  - Custom exceptions when appropriate

- [ ] **No Catch-Rethrow**: No unnecessary exception wrapping
  - Don't catch and rethrow same exception
  - Add context when wrapping
  - Let exceptions propagate when no value added

## Naming Conventions

**Standards Reference**: Naming Conventions in java-core
**See**: `pm-dev-java:java-core` skill, `standards/java-core-patterns.md` section "Naming Conventions"

### Verification Items

- [ ] **Meaningful Names**: All identifiers are descriptive
  - Class names: nouns (UserService, TokenValidator)
  - Method names: verbs (calculateTotal, validateInput)
  - Variables: descriptive nouns (userName, maxRetries)

- [ ] **No Poor Abbreviations**: Avoid unclear abbreviations
  - [AVOID] usr, mgr, txt, num, cnt
  - [PREFER] user, manager, text, number, count
  - [OK] standard abbreviations (dto, id, url)

- [ ] **Consistent Naming**: Naming follows Java conventions
  - Classes: PascalCase
  - Methods/variables: camelCase
  - Constants: UPPER_SNAKE_CASE
  - Packages: lowercase

## Modern Java Features

**Standards Reference**: Modern Features Standards in java-core
**See**: `pm-dev-java:java-core` skill, `standards/java-modern-features.md`

### Verification Items

- [ ] **Records for Data**: Simple data carriers use records
  - Replace classes that are just data holders
  - Use compact constructor for validation
  - Prefer records over @Value for simple cases

- [ ] **Switch Expressions**: Modern switch syntax used
  - Use switch expressions (→) not statements
  - No break keywords
  - Exhaustive switches without default

- [ ] **Streams**: Streams used appropriately
  - Complex data transformations use streams
  - Simple loops remain imperative (readability first)
  - Parallel streams only when beneficial

- [ ] **Text Blocks**: Multi-line strings use text blocks
  - SQL queries, JSON, XML use """..."""
  - Proper indentation maintained
  - No string concatenation for multi-line

- [ ] **Modern Collections**: Use collection factory methods
  - List.of(), Set.of(), Map.of() for immutable collections
  - List.copyOf() for defensive copies
  - No Collections.unmodifiableList() anymore

## Unused Code

**Standards Reference**: See refactoring-triggers.md for unused code detection criteria

### Verification Items

- [ ] **No Unused Private Elements**: All private members are used
  - No unused private fields
  - No unused private methods
  - No unused local variables

- [ ] **No Dead Code**: All code is reachable
  - No unreachable statements
  - No methods that are never called
  - No commented-out code blocks

- [ ] **Framework Requirements Documented**: "Unused" code has reason
  - Framework-required methods documented
  - Reflection usage noted
  - Serialization requirements explained

## Lombok Usage

**Standards Reference**: Lombok Patterns in java-core
**See**: `pm-dev-java:java-core` skill, `standards/java-lombok-patterns.md`

### Verification Items

- [ ] **@Builder for Complex Objects**: Builder pattern used appropriately
  - 3+ parameters or optional parameters use @Builder
  - @Builder.Default for default values
  - Fluent construction for complex objects

- [ ] **@Value for Immutable Objects**: Immutable objects use @Value
  - Simple immutable objects use @Value
  - Alternative: use records for very simple cases
  - Include validation in private constructor if needed

- [ ] **@Delegate for Composition**: Composition preferred over inheritance
  - Use @Delegate instead of extends
  - Expose only needed methods
  - Favor composition over inheritance

- [ ] **No Lombok Logging**: CuiLogger used, not @Slf4j
  - No @Slf4j or other logging annotations
  - Use CuiLogger explicitly
  - Follow CUI logging patterns

## Logging (CUI Projects)

**Standards Reference**: Logging Standards in pm-dev-java-cui
**See**: `pm-dev-java-cui:cui-logging` skill

### Verification Items

- [ ] **CuiLogger Declaration**: Logger is properly declared
  - `private static final CuiLogger LOGGER = new CuiLogger(ClassName.class);`
  - Named LOGGER (uppercase)
  - Static final field

- [ ] **LogRecord Usage**: Important messages use LogRecord
  - INFO/WARN/ERROR/FATAL use LogRecord
  - DEBUG/TRACE can use simple strings
  - LogMessages class defines LogRecords

- [ ] **LogMessages Organization**: LogMessages follows DSL pattern
  - Nested static classes by log level (INFO, WARN, ERROR, FATAL)
  - @UtilityClass on all classes
  - Proper identifier ranges (INFO: 1-99, WARN: 100-199, ERROR: 200-299)

- [ ] **Exception Logging**: Exceptions logged correctly
  - Exception is first parameter: `LOGGER.error(exception, ERROR.MESSAGE, args)`
  - Exception message included in log template
  - Appropriate log level for exception severity

- [ ] **String Substitution**: %s used for all substitutions
  - Use %s, not {} or %d
  - Number of %s matches number of arguments
  - No string concatenation in log calls

- [ ] **No System.out/err**: No console output
  - No System.out.println()
  - No System.err.println()
  - No printStackTrace()

## Documentation

**Standards Reference**: Javadoc Standards in `pm-dev-java:javadoc` skill
**See**: `pm-dev-java:javadoc` skill, `standards/javadoc-core.md`

### Verification Items

- [ ] **Public API Documentation**: All public APIs have Javadoc
  - Public classes have class-level Javadoc
  - Public methods have method-level Javadoc
  - @param, @return, @throws tags present

- [ ] **Current Documentation**: Documentation matches code
  - No references to removed parameters
  - No outdated behavior descriptions
  - Examples still work

- [ ] **Meaningful Documentation**: Documentation adds value
  - Explains WHY, not just WHAT
  - Includes usage examples for complex APIs
  - Documents preconditions and postconditions

- [ ] **No Redundant Comments**: Comments are necessary
  - No comments that just repeat method name
  - No obvious comments
  - Complex logic explained with comments

## Build and Tests

**Standards Reference**: Testing Standards in pm-dev-java:junit-core
**See**: `pm-dev-java:junit-core` skill, `standards/testing-junit-core.md`

### Verification Items

- [ ] **Build Passes**: Code compiles without errors
  - `./mvnw clean verify -DskipTests` succeeds
  - No compilation warnings (when possible)
  - All dependencies resolve

- [ ] **Tests Pass**: All tests execute successfully
  - `./mvnw clean test` succeeds
  - No flaky tests
  - Tests are deterministic

- [ ] **Coverage Sufficient**: Test coverage meets targets
  - Minimum 80% line coverage
  - Minimum 80% branch coverage
  - Critical paths have 100% coverage

- [ ] **Quality Gates**: Static analysis passes
  - SonarQube quality gate passes
  - No critical or blocker issues
  - Technical debt is acceptable

## Module Verification

**For multi-module projects, verify per module:**

### Module-Specific Checks

- [ ] **Module Builds**: Module builds independently
  - `./mvnw clean verify -pl module-name` succeeds
  - Module tests pass in isolation
  - No inter-module test dependencies

- [ ] **Module Dependencies**: Module dependencies are correct
  - Only necessary dependencies declared
  - No circular dependencies
  - Proper dependency scopes (compile/test/provided)

- [ ] **Module Compatibility**: Modules work together
  - Integration between modules verified
  - API contracts maintained
  - No breaking changes to module interfaces

## Final Verification Workflow

After completing maintenance work:

1. **Run through checklist** for each modified class
2. **Fix all non-compliant items** noted
3. **Execute build verification**:
   ```bash
   ./mvnw -Ppre-commit clean verify -DskipTests
   ```
4. **Execute test suite**:
   ```bash
   ./mvnw clean test
   ```
5. **Verify coverage**:
   ```bash
   ./mvnw clean verify -Pcoverage
   ```
6. **Check static analysis** (SonarQube)
7. **Document any deviations** with rationale
8. **Commit changes** following git standards

## Deviation Documentation

When standards cannot be met:

**Document why** in code comments:
```java
// @NullMarked not applied to this package because legacy framework
// requires nullable parameters. See issue #123 for migration plan.
```

**Suppress warnings** with explanation:
```java
@SuppressWarnings("unused") // Required by JPA specification
private Long id;
```

**Track technical debt**:
- Add to project TODO list
- Create follow-up issue
- Set deadline for resolution

