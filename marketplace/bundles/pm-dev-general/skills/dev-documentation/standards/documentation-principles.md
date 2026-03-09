# Documentation Principles

Language-agnostic principles for code documentation across all technology stacks.

## Mandatory Documentation Requirements

### What Must Be Documented

* Every public/exported class, interface, type, or module
* Every public/exported function or method
* All public/exported fields, properties, and constants
* All parameters with their purpose and validation rules
* Return values with what they represent and guarantees
* Exceptions/errors with the conditions that trigger them
* Complex algorithms or business logic (regardless of visibility)

### What Should NOT Be Documented

* Private methods (unless complex or non-obvious)
* Trivial fields (e.g., loggers, serial version IDs)
* Obvious getters/setters without business logic
* Standard fields that follow common patterns
* Methods that simply delegate without adding logic

## Core Principles

### 1. Clarity and Purpose

* Start with a clear purpose statement
* Explain WHAT the code does and WHY it exists
* Avoid stating the obvious or repeating the function/method name
* Focus on behavior and contract, not implementation details

**Good — specific and purposeful:**
```
Validates the JWT token signature and expiration time against the configured
issuer and clock skew tolerance.

Parameters:
  token — the JWT token to validate, must not be null or empty
Returns:
  validation result containing status and any error messages
Throws:
  IllegalArgumentError — if token is null or empty
```

**Bad — stating the obvious:**
```
Validates a token.

Parameters:
  token — the token
Returns:
  the result
```

### 2. Completeness

* Document all parameters with meaningful descriptions and constraints
* Document return values with what they represent
* Document all exceptions/errors and when they occur
* Include since/version tags for public APIs
* Add deprecation notices with migration paths

### 3. Consistency

* Use consistent terminology across the codebase
* Follow the standard tag/annotation order for your language
* Use consistent formatting and structure
* Apply the same documentation style throughout the project

### 4. Maintainability

* Keep documentation synchronized with code
* Update docs when changing signatures or behavior
* Remove outdated or incorrect documentation
* Document assumptions and preconditions
* Include documentation updates in the same commit as code changes

## Writing Style

* **Present tense** — "Validates input", not "Will validate"
* **Active voice** — "Calculates total", not "Total is calculated"
* **Complete sentences** — proper capitalization and punctuation
* **Clear and specific** — avoid vague descriptions like "processes data"
* **No redundancy** — don't repeat the function name in the description

## Documentation Anti-Patterns

### 1. Stating the Obvious

```
// BAD — obvious documentation
Sets the name.
  parameter: name — the name to set

// GOOD — documents business rules
Sets the user's display name. The name is trimmed and validated
to ensure it meets minimum length requirements.
  parameter: name — the display name (minimum 2 characters after trimming)
  throws: ValidationError — if name is too short
```

### 2. Documenting Implementation Instead of Contract

```
// BAD — exposes implementation details
Uses a HashMap to store the users and iterates through the entrySet
to find the matching user by email.

// GOOD — documents the contract
Retrieves the first user with the specified email address.
Returns empty/null if no user matches.
```

### 3. Outdated Documentation

Documentation that doesn't match current code is worse than no documentation. It actively misleads readers.

**Prevention:**
* Review documentation during every code change
* Include documentation updates in code review checklists
* Check for broken cross-references
* Run documentation generation tools to catch errors

### 4. Vague Descriptions

```
// BAD — vague, uninformative
Processes the data.
  parameter: data — the data
  returns: the result

// GOOD — specific and informative
Enriches user data by adding geolocation information based on IP address
and validating email deliverability.
  parameter: userData — the user data to enrich
  returns: enriched user data with geolocation and email status
  throws: EnrichmentError — if external services are unavailable
```

## Code Examples in Documentation

For complex APIs, include usage examples:

* Show the most common use case
* Include error handling if relevant
* Keep examples concise but complete
* Test examples to ensure they work (or use verified snippets)

## When to Update Documentation

* When changing function/method signatures (parameters, return type)
* When modifying behavior or semantics
* When adding new public APIs
* When deprecating existing APIs
* When fixing bugs that affect documented behavior
* During code reviews — always check documentation accuracy

## Thread-Safety and Concurrency

For code with thread-safety implications:

* Document whether the type is thread-safe
* Document synchronization requirements for callers
* Note if returned values may be stale under concurrent access
* Document any lock ordering requirements

