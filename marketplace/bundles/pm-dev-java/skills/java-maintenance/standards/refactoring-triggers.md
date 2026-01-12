# Refactoring Triggers and Detection Criteria

Standards for identifying when to apply refactoring actions in Java codebases.

## Purpose

This document defines WHEN to apply specific refactoring patterns by identifying code violations and triggering conditions. It provides systematic detection criteria for standards violations.

## Standards Violation Detection

This section defines when and how to identify violations of Java coding standards and what actions to take for each violation type.

### When to Refactor Code Organization

**Triggers for Action**: Apply code organization refactoring when:

**Package Structure Violations**: Non-standard package names or layer-based organization detected
- **Action Required**: Restructure to feature-based packages per Package Structure Standards
- **Standards Reference**: Package organization follows feature-based structure (not layer-based like controller/service/repository)
- **See**: `pm-dev-java:java-core` skill, `standards/java-core-patterns.md` section "Package Organization"

**Class Structure Violations**: Single Responsibility Principle violations or inappropriate access modifiers
- **Action Required**: Split classes or adjust access modifiers per Class Structure Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-core-patterns.md` section "Class Design"
- **Detection**: Classes with multiple unrelated responsibilities, god classes, classes mixing concerns

**Large Classes**: Classes exceeding reasonable size limits
- **Action Required**: Extract functionality into focused classes following SRP
- **Detection**: Classes > 500 lines, classes with too many methods, classes handling multiple domains

### When to Refactor Method Design

**Triggers for Action**: Apply method design refactoring when:

**Long Methods**: Methods over 60 lines, or methods with complex logic regardless of line count
- **Action Required**: Extract methods per Method Design Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-core-patterns.md` section "Method Design"
- **Guideline**: Target methods under 50 lines for better readability and maintainability
- **Detection**: Methods with multiple levels of nesting, methods doing multiple things, methods with more than one clear responsibility
- **Note**: Line count is secondary to single responsibility - a focused 70-line method may be acceptable, while a 45-line method doing multiple things requires refactoring

**High Cyclomatic Complexity**: Methods with complexity >15 (SonarQube default)
- **Action Required**: Simplify logic and extract sub-methods
- **Detection**: Use SonarQube, or manually count decision points: `grep -c -E "(if|for|while|case|&&|\|\|)" MethodFile.java` (>15 occurrences indicates high complexity)

**Too Many Parameters**: Methods with 3+ parameters without parameter objects
- **Action Required**: Create parameter objects per Parameter Objects Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-core-patterns.md` section "Parameter Objects"
- **Exception**: Parameters representing cohesive concepts (e.g., coordinates: x, y, z for geometric calculations; or primitive configuration: enabled, timeout, retryCount for simple settings)
- **Detection**: Count method parameters using `grep -E "^\s*(public|private|protected).*\(([^)]*,){3,}" *.java`, or identify methods with similar parameter groups across multiple methods

**Command-Query Separation Violations**: Methods that both query and modify state
- **Action Required**: Separate into command and query methods per Method Design Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-core-patterns.md` section "Command-Query Separation"
- **Detection**: Methods that return values AND modify state, getters with side effects

### When to Simplify Complex Logic

**Triggers for Action**: Apply code simplification when:

**High Cognitive Complexity**: Methods difficult to understand due to nested logic
- **Action Required**: Simplify control flow, extract nested blocks into helper methods
- **Threshold**: Cognitive Complexity >15 (SonarQube rule java:S3776)
- **Detection**: Use SonarQube cognitive complexity metric, or manually identify: deeply nested conditions, multiple break/continue statements, recursive calls with complex conditions
- **Note**: Cognitive complexity differs from cyclomatic complexity - it measures understandability, not just decision points
- **Example Simplifications**: Replace nested if with guard clauses, extract complex conditions into named boolean methods, eliminate multiple levels of loops

**Deep Nesting**: Methods with excessive indentation levels
- **Action Required**: Use guard clauses, extract nested blocks, simplify control flow
- **Threshold**: >3 levels of nesting (if/for/while/try within if/for/while/try)
- **Detection**: Visual inspection of indentation, search for deeply indented blocks
- **Preferred Pattern**: Early returns (guard clauses) instead of nested if statements
- **Example**: Replace `if (valid) { if (allowed) { doWork(); } }` with `if (!valid) return; if (!allowed) return; doWork();`

**Complex Boolean Expressions**: Conditions with multiple operators that are hard to parse
- **Action Required**: Extract complex conditions into well-named boolean methods or variables
- **Detection**: Conditions with 3+ boolean operators (&&, ||, !), conditions spanning multiple lines without clear grouping
- **Example**: Replace `if (user != null && user.isActive() && !user.isSuspended() && user.hasPermission("ADMIN"))` with `if (isAdminUser(user))`

**Over-Abstraction**: Unnecessary layers of indirection for simple operations
- **Action Required**: Simplify or remove unnecessary abstraction layers
- **Detection**: Single-use abstractions, interfaces with one implementation, utility methods called from only one place, wrapper classes adding no value
- **Balance**: Ensure simplification doesn't violate SOLID principles or future extensibility needs
- **Ask User**: When uncertain if abstraction serves future needs

**Redundant Logic**: Code that can be simplified through Boolean algebra or is always true/false
- **Action Required**: Simplify or remove redundant conditions
- **Detection**: Conditions always evaluating to same value, double negatives, identical nested conditions, unnecessary else after return
- **Examples**: `if (x) return true; else return false;` → `return x;` | `if (!(!condition))` → `if (condition)` | `if (x) { return; } else { doSomething(); }` → `if (x) return; doSomething();`

### When to Fix Null Safety Violations

**Triggers for Action**: Apply null safety fixes when:

**Missing @NonNull Annotations**: Public API methods lack null safety documentation
- **Action Required**: Add annotations per @NonNull Annotations Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-null-safety.md`
- **Implementation**: Ensure methods guarantee non-null returns per Implementation Requirements
- **Detection**: Public methods without @NonNull annotations, package-info.java missing @NullMarked

**Inconsistent API Contracts**: Mix of nullable returns and Optional usage
- **Action Required**: Choose consistent pattern per API Return Type Guidelines
- **See**: `pm-dev-java:java-core` skill, `standards/java-null-safety.md` section "Optional Usage"
- **Standards**: Use @NonNull for guaranteed results, Optional<T> for potential absence
- **Detection**: Some methods return null, others return Optional for same scenarios

**Manual Enforcement Gaps**: @NonNull methods that can return null
- **Action Required**: Fix implementations to guarantee non-null returns
- **Testing**: Add tests per Implementation Requirements
- **Detection**: Methods annotated @NonNull but with code paths returning null

### When to Fix Naming Convention Violations

**Triggers for Action**: Apply naming fixes when:

**Poor Naming Practices**: Unclear abbreviations or non-descriptive names detected
- **Action Required**: Apply naming improvements per Naming Conventions Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-core-patterns.md` section "Naming Conventions"
- **Focus**: Use meaningful and descriptive names following Java standards
- **Detection**: Single-letter variables (except loop counters), unclear abbreviations, generic names like "data", "info", "manager"

### When to Fix Exception Handling Issues

**Triggers for Action**: Apply exception handling fixes when:

**Generic Exception Catching**: `catch (Exception e)` or `catch (RuntimeException e)` detected
- **Action Required**: Use specific exceptions per Exception Handling Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-core-patterns.md` section "Exception Handling"
- **Detection**: Catch blocks for generic Exception or RuntimeException types

**Missing Error Messages**: Exceptions without meaningful messages
- **Action Required**: Add descriptive error messages per standards
- **Detection**: `throw new Exception()` without message, generic messages like "Error"

**Inappropriate Exception Types**: Wrong exception types for the situation
- **Action Required**: Use checked exceptions for recoverable conditions, unchecked for programming errors
- **Detection**: RuntimeException for recoverable conditions, checked exceptions for programming errors

**Catch and Rethrow Anti-Pattern**: Catching and throwing the same or very similar exception
- **Action Required**: Remove unnecessary catch blocks or add meaningful context per Exception Handling Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-core-patterns.md` section "Exception Handling"
- **Detection**: Catch blocks that immediately rethrow same exception type

### When to Adopt Modern Java Features

**Triggers for Action**: Apply modern Java feature adoption when:

**Legacy Switch Statements**: Classic switch statements with breaks detected
- **Action Required**: Convert to switch expressions per Switch Expressions Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-modern-features.md` section "Switch Expressions"
- **Detection**: Switch statements with break keywords, fall-through cases

**Verbose Object Creation**: Manual data classes without records
- **Action Required**: Replace with records per Records Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-modern-features.md` section "Records"
- **Detection**: Classes with only fields, constructor, getters, equals, hashCode, toString

**Manual Stream Operations**: Imperative loops that could use streams
- **Action Required**: Simplify with streams per Stream Processing Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-modern-features.md` section "Stream API"
- **Detection**: Loops with filters, maps, or accumulations that could be replaced with streams
- **Exception**: Simple loops where streams would reduce readability (e.g., single iteration with early return, nested streams >3 levels deep, complex stateful operations requiring mutable accumulation)

### When to Remove Unused Code

**Triggers for Action**: Apply unused code removal when:

**Unused Private Elements**: Private fields, methods, or variables never accessed
- **Action Required**: Remove after verification per detection strategy below
- **Safety Check**: Ensure no framework dependencies or reflection usage
- **Detection**: Use IDE warnings, static analysis tools

**Dead Code Detection**: Code that is never executed or called
- **Action Required**: Request user approval before removal
- **Process**: Follow user consultation protocol below
- **Detection**: Unreachable code, methods never called

#### Detection Strategy

1. Use IDE warnings and inspections to identify unused elements (see `/tools-fix-intellij-diagnostics` command for automated IDE diagnostics)
2. Leverage SonarQube for static analysis (see `/pr-fix-sonar-issues` command for automated Sonar issue fixing)
3. Manual code review for systematic identification
4. Build tool analysis with Maven/Gradle plugins

#### User Consultation Protocol

When unused methods are detected, MUST:

1. Document all findings with locations and signatures
2. Categorize by visibility (private, package-private, protected, public)
3. Ask user for guidance with context and potential impact
4. Wait for explicit approval before removing any methods
5. Remove approved unused code in focused commits

#### Special Considerations

Do NOT remove when:

- Framework dependencies may require "unused" methods (Spring, JPA, etc.)
- Methods may be called via reflection
- Private fields required for serialization frameworks
- Code prepared for upcoming features
- Public/protected methods needed for backward compatibility

### When to Apply Lombok Integration

**Triggers for Action**: Apply Lombok integration when:

**Inheritance Anti-Patterns**: Classes extending when they should delegate
- **Action Required**: Replace with composition and `@Delegate` per Lombok Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-lombok-patterns.md` section "Delegation with @Delegate"
- **Detection**: Deep inheritance hierarchies, classes extending just to reuse utility methods

**Manual Builder Patterns**: Verbose builder implementations detected
- **Action Required**: Replace with `@Builder` per Lombok Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-lombok-patterns.md` section "Builder Pattern with @Builder"
- **Detection**: Manual builder classes with fluent APIs, builder classes with many setters

**Boilerplate Immutable Objects**: Manual equals/hashCode/toString implementations
- **Action Required**: Replace with `@Value` per Lombok Standards
- **See**: `pm-dev-java:java-core` skill, `standards/java-lombok-patterns.md` section "Immutable Objects with @Value"
- **Detection**: Classes with manual implementations of equals, hashCode, toString for simple data carriers

### When to Enforce Documentation Standards

**Triggers for Action**: Apply documentation fixes when:

**Missing Javadoc**: Public APIs without proper documentation
- **Action Required**: Add documentation per Javadoc Standards
- **See**: `pm-dev-java:javadoc` skill, `standards/javadoc-core.md`
- **Detection**: Public classes/methods without Javadoc, missing @param/@return tags

**Outdated Documentation**: Comments not reflecting current code behavior
- **Action Required**: Update documentation to match refactored code
- **Detection**: Comments mentioning non-existent parameters, outdated behavior descriptions

**Redundant Comments**: Comments explaining obvious code
- **Action Required**: Remove unnecessary comments, add meaningful ones for complex logic
- **Detection**: Comments that just repeat method name, obvious comments like "// increment i"

## Related Standards
- maintenance-prioritization.md - How to prioritize violations
- compliance-checklist.md - How to verify fixes are complete
