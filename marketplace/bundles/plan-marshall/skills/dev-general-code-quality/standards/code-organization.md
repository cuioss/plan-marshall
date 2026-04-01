# Code Organization and Refactoring

Language-agnostic principles for organizing code into maintainable, well-structured units, and criteria for identifying when refactoring is needed.

## Single Responsibility Principle

Each class, module, or function should have exactly one reason to change.

**Indicators of SRP violations:**
* Class/module handles multiple unrelated concerns
* Changes to one feature require modifying unrelated code
* Class name contains "And", "Or", "Manager", "Handler" (doing too much)
* Difficulty describing the class purpose in one sentence
* Classes > 500 lines or > 20 methods

**Resolution:**
* Extract each responsibility into its own class/module
* Use composition to combine responsibilities where needed
* Group related classes by feature, not by technical layer

## Command-Query Separation (CQS)

Methods should either modify state (command) or return data (query), not both.

```
// Query -- returns value, no side effects
function isValid(token): boolean

// Command -- modifies state, returns void
function markAsInvalid(token): void

// ANTI-PATTERN -- modifies state AND returns value
function validateAndGetResult(token): Result
```

**Exceptions:** Stack `pop()`, queue `dequeue()`, and similar data structure operations where combined command-query is the established contract.

**Detection of violations:**
* Methods that return values AND modify state
* Getters with side effects
* "Get-and-set" operations without clear justification

## Package/Module Structure

### Feature-Based Organization

Organize code by feature (domain), not by technical layer:

```
// GOOD -- feature-based
authentication/
  TokenValidator
  TokenConfig
  AuthenticationService
configuration/
  ConfigParser
  ConfigValidator

// BAD -- layer-based
controllers/
  AuthController
  ConfigController
services/
  AuthService
  ConfigService
models/
  Token
  Config
```

**Benefits:**
* Related code is co-located
* Changes to a feature are localized
* Easier to understand and navigate
* Better encapsulation of feature internals

**Refactoring trigger:** Layer-based directory structure where changes to one feature require touching many directories.

### Access Modifiers

Use the most restrictive access level possible:

* Default to private/internal
* Only expose what consumers need
* Use package-private/module-internal for collaborators
* Public only for genuine API surfaces

## Method Design

### Length and Complexity

* Prefer methods under 50 lines, max 100 lines (hard limit)
* Cyclomatic complexity: prefer < 15, max 20
* Nesting depth: max 3 levels
* Line count is secondary to single responsibility -- a focused 70-line method may be acceptable, while a 45-line method doing multiple things requires refactoring

**Refactoring triggers:**
* Methods with multiple levels of nesting
* Methods doing multiple unrelated things
* Difficulty describing what the method does in one sentence
* Complexity > 15 (count decision points: if, for, while, case, &&, ||)

### Guard Clauses

Use early returns to reduce nesting:

```
// GOOD -- guard clauses, low nesting
function validate(token) {
    if (!token) return Result.invalid("Token required")
    if (!hasValidFormat(token)) return Result.invalid("Bad format")
    if (!hasValidSignature(token)) return Result.invalid("Bad signature")
    return Result.valid()
}

// BAD -- deep nesting
function validate(token) {
    if (token) {
        if (hasValidFormat(token)) {
            if (hasValidSignature(token)) {
                return Result.valid()
            }
        }
    }
    return Result.invalid()
}
```

### Naming

* Use meaningful, descriptive names
* Methods: verb + noun (`validateToken`, `calculateTotal`)
* Boolean methods: `is`, `has`, `can`, `should` prefix
* Avoid abbreviations and single-letter names (except loop counters)
* Avoid generic names: `data`, `info`, `manager`, `handler`, `processor`

## Parameter Objects

When a function has too many parameters for comfortable readability, group related parameters into an object. The exact threshold depends on the language:

* **Java** (no named arguments): prefer parameter objects at 3+ parameters. Use records.
* **JavaScript**: prefer config objects at 5+ parameters. Destructuring in the signature keeps it readable.
* **Python** (keyword arguments): named args handle many parameters well. Use dataclasses or TypedDicts when parameter groups are reused across multiple functions.

```
// BAD -- too many loose parameters
function validate(tokenId, expectedScopes, maxAge, issuer, strict)

// GOOD -- parameter object
function validate(request: ValidationRequest)
// where ValidationRequest groups: tokenId, expectedScopes, maxAge, issuer, strict
```

**Exceptions:** Parameters representing a single cohesive concept (e.g., coordinates: x, y, z) or simple configuration (enabled, timeout, retryCount) may stay as individual parameters.

## Immutability

Prefer immutable data structures:

* Use immutable collections (frozen/unmodifiable/copyOf)
* Declare fields/variables as constant/final where possible
* Return defensive copies from getters
* Use value objects or records for data carriers

## Composition Over Inheritance

* Prefer delegation over inheritance for code reuse
* Avoid deep inheritance hierarchies (max 2-3 levels)
* Use interfaces/protocols for polymorphism
* Use composition to combine behaviors

## Comments

* Write self-documenting code first
* Use comments to explain WHY, not WHAT
* Use documentation comments for public APIs (see `documentation-principles.md`)
* Remove commented-out code -- use version control instead

```
// GOOD -- explains why
// 30-second clock skew handles time differences between distributed servers
CLOCK_SKEW = Duration.ofSeconds(30)

// BAD -- states the obvious
// Duration of 30 seconds
CLOCK_SKEW = Duration.ofSeconds(30)
```

## Complexity Refactoring Patterns

### Complex Boolean Expressions

**Trigger**: Conditions with 3+ boolean operators that are hard to parse.

```
// TRIGGER: Complex inline boolean
if (user != null && user.isActive && !user.isSuspended && user.hasPermission("admin"))

// RESOLVED: Named method
if (isActiveAdmin(user))
```

### Over-Abstraction

**Trigger**: Unnecessary layers of indirection.

**Detection:**
* Single-use abstractions
* Interfaces with only one implementation
* Wrapper classes adding no value
* Utility methods called from only one place

**Action:** Simplify or remove unnecessary abstraction layers. When uncertain if abstraction serves future needs, ask the user.

### Redundant Logic

**Trigger**: Code that can be simplified through Boolean algebra.

**Examples:**
* `if (x) return true; else return false;` -> `return x;`
* `if (!(!condition))` -> `if (condition)`
* `if (x) { return; } else { doSomething(); }` -> `if (x) return; doSomething();`

## Unused Code

**Trigger**: Code that is never executed or called.

**Detection:** IDE warnings, static analysis tools, unreachable code paths.

**Action:** Remove after verification. Request user approval for public/protected elements.

**Do NOT remove when:**
* Framework dependencies may require "unused" methods
* Methods may be called via reflection
* Code prepared for upcoming features (ask user)
* Public API needed for backward compatibility

## Duplication

**Trigger**: Same or very similar logic repeated in multiple places.

**Detection:**
* Identical code blocks in different methods
* Similar methods differing only in a few lines
* Same validation logic in multiple entry points

**Action:** Extract into shared method/function, use template patterns for structural similarity.

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|-------------|---------|----------|
| God class | Too many responsibilities | Split by SRP |
| Magic numbers | Unclear intent | Named constants |
| Primitive obsession | Too many loose parameters | Domain objects, parameter objects |
| Deep inheritance | Rigid, hard to change | Composition, delegation |
| Feature envy | Method uses another class's data more than its own | Move method to the data's class |
| Shotgun surgery | Single change requires many file edits | Consolidate related logic |

## Secure Coding Principles

* Never log secrets, passwords, tokens, or PII
* Validate all external input at system boundaries
* Use parameterized queries for database access
* Sanitize output to prevent injection attacks
* Fail securely -- error messages must not leak internal details

## Maintenance Prioritization

| Priority | Examples |
|----------|----------|
| **High** | Security vulnerabilities, public API contract issues, fundamental design problems (SRP violations, god classes), error handling gaps in critical paths |
| **Medium** | Long methods (> 50 lines), high complexity (> 15), legacy patterns, unused/dead code |
| **Low** | Style inconsistencies, minor documentation improvements, speculative performance optimizations |
