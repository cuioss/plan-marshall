# Error Handling

Language-agnostic error handling principles covering exception philosophy, propagation, and recovery patterns.

## Fundamental Rules

### Use Specific Error Types

Never catch or throw generic errors. Always use the most specific error/exception type available.

```
// GOOD — specific error types
try {
    config = parser.parse(readFile(configPath))
} catch (FileNotFoundError) {
    throw ConfigurationError("Config file not found: " + configPath)
} catch (ParseError) {
    throw ConfigurationError("Invalid config format in: " + configPath)
}

// BAD — generic catch
try {
    config = parser.parse(readFile(configPath))
} catch (Error) {
    return null  // Loses all error information
}
```

### Include Meaningful Messages

Error messages must provide context for diagnosis:

* **What** operation failed
* **Why** it failed (if known)
* **Where** it happened (relevant identifiers, file paths, values)

```
// GOOD — actionable error message
"Failed to validate token for user 'admin': signature expired at 2024-01-15T10:30:00Z"

// BAD — useless error message
"Error"
"Validation failed"
"Something went wrong"
```

### Preserve Error Causes

When wrapping exceptions, always preserve the original cause:

```
// GOOD — preserves original cause
catch (IOException original) {
    throw new ConfigError("Failed to read " + path, original)
}

// BAD — loses original cause
catch (IOException original) {
    throw new ConfigError("Failed to read config")  // original exception lost
}
```

## Error Categories

### Recoverable Errors

Errors where the caller can take meaningful action:

* Invalid user input → prompt for correction
* Network timeout → retry with backoff
* Resource temporarily unavailable → wait and retry
* Missing optional configuration → use defaults

**Pattern:** Use checked exceptions (Java), Result types (Rust/functional), or error return values.

### Programming Errors

Errors that indicate bugs in the code:

* Null/undefined dereference
* Index out of bounds
* Invalid state transitions
* Precondition violations

**Pattern:** Use unchecked exceptions or assertions. These should never be caught in normal flow — fix the bug instead.

### System Errors

Errors from the runtime environment:

* Out of memory
* Disk full
* Process killed

**Pattern:** Generally not recoverable at the application level. Log and terminate gracefully.

## Error Propagation

### Let Errors Bubble

Do not catch errors you cannot handle meaningfully:

```
// BAD — catch and ignore
try {
    result = service.process(data)
} catch (Error) {
    // silently swallowed
}

// BAD — catch, log, and rethrow without adding value
try {
    result = service.process(data)
} catch (Error e) {
    log.error("Error occurred", e)
    throw e  // adds nothing except a log line
}

// GOOD — add context when wrapping
try {
    result = service.process(data)
} catch (ProcessingError e) {
    throw new ServiceError("Failed to process order " + orderId, e)
}

// GOOD — let it propagate if no value added
result = service.process(data)  // caller handles the error
```

### Guard Clauses

Validate preconditions early and fail fast:

```
function processOrder(order) {
    if (!order) throw new ArgumentError("order must not be null")
    if (order.items.isEmpty()) throw new ArgumentError("order must have items")
    if (!order.isValid()) throw new ValidationError("order validation failed")

    // Happy path — preconditions guaranteed
    return calculateTotal(order)
}
```

## Error Handling Anti-Patterns

| Anti-Pattern | Problem | Solution |
|-------------|---------|----------|
| Catch and ignore | Errors silently lost | Handle or propagate |
| Catch generic | Catches unintended errors | Use specific types |
| Return null on error | Caller gets NPE later | Throw or use Optional/Result |
| Error as control flow | Exceptions for expected cases | Use conditional logic |
| Log and rethrow | Duplicate log entries | Either log OR rethrow, not both |
| Swallow in finally | Original error masked | Handle cleanup separately |

## Logging and Errors

### What to Log

* Log errors at the point where they are handled (not where they pass through)
* Include relevant context (user, operation, identifiers)
* Use appropriate log levels (ERROR for failures, WARN for degraded operation)

### What NOT to Log

* **Never** log secrets, passwords, tokens, API keys
* **Never** log personally identifiable information (PII)
* Do not log the same error at multiple levels (pick one)
* Do not log expected/normal conditions at ERROR level

## Recovery Patterns

### Retry with Backoff

For transient failures (network, resource contention):

```
maxRetries = 3
for attempt in range(maxRetries):
    try {
        return service.call()
    } catch (TransientError) {
        if attempt == maxRetries - 1: throw
        wait(exponentialBackoff(attempt))
    }
```

### Fallback / Default

For non-critical features:

```
function getConfig(key) {
    try {
        return configService.get(key)
    } catch (ConfigError) {
        return DEFAULT_VALUES[key]  // graceful degradation
    }
}
```

### Circuit Breaker

For external dependencies that may be down:

* Track failure rate over time window
* Open circuit after threshold (stop calling)
* Periodically test if service recovered (half-open)
* Close circuit when service is healthy again

## Validation Boundaries

Validate input at system boundaries:

* **External input** (user input, API requests, file content) — always validate
* **Internal boundaries** (between modules) — validate with assertions/preconditions
* **Within a module** — trust your own code, no redundant validation

```
// System boundary — full validation
function handleApiRequest(request) {
    validate(request.body)  // thorough validation
    return service.process(request.body)
}

// Internal boundary — precondition check
function processOrder(order) {
    assert(order != null)  // programming error if violated
    // trust that order is well-formed at this point
}
```
