# Error Handling

Language-agnostic error handling principles covering exception philosophy, propagation, and recovery patterns.

## Fundamental Rules

### Use Specific Error Types

Never catch or throw generic errors. Always use the most specific error/exception type available.

```text
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

```text
// GOOD — actionable error message
"Failed to validate token for user 'admin': signature expired at 2024-01-15T10:30:00Z"

// BAD — useless error message
"Error"
"Validation failed"
"Something went wrong"
```

### Preserve Error Causes

When wrapping exceptions, always preserve the original cause:

```text
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

```text
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

```text
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
* Use appropriate log levels (ERROR for failures, WARNING for degraded operation)

### What NOT to Log

* **Never** log secrets, passwords, tokens, API keys
* **Never** log personally identifiable information (PII)
* Do not log the same error at multiple levels (pick one)
* Do not log expected/normal conditions at ERROR level

## Recovery Patterns

### Retry with Backoff

For transient failures (network, resource contention):

```text
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

```text
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

```text
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

## Fail-Closed Read-Only Gate Verbs

A read-only gate or boundary verb — a function that forms a *verdict* by reading a file without mutating state (a `*-status` / `assert-*` / `verify` / `*-validate` / `qgate`-class check, or a consistency-check helper that reads an artifact to decide pass/fail) — MUST catch `OSError` on that read and convert it to a structured error status. A file that passed an `.exists()` probe can still raise on the subsequent read: permission denied, the path resolving to a directory, or a mid-read deletion race. Letting that `OSError` escape crashes the verdict path.

"I could not evaluate the invariant" is itself an answer the caller needs. A gate that crashes on an I/O error has strictly worse failure semantics than one that returns an error, because the caller cannot distinguish "the invariant could not be evaluated" from a hard process death — and may silently advance past an unverified gate. Deliver the failure as a structured `status: error` (or the verb's documented fail-closed sentinel), never a stack trace.

```text
// BAD — .exists() guard, but the read can still raise OSError
function checkConsistency(planDir) {
    path = planDir / "outline.md"
    if (path.exists()) {
        content = path.readText()  // raises on a directory / perms / delete race
    }
    return evaluate(content)  // verdict path crashes on the uncaught OSError
}

// GOOD — fail closed: the read failure is itself a structured verdict
function checkConsistency(planDir) {
    path = planDir / "outline.md"
    try {
        content = path.readText()
    } catch (OSError e) {
        return verdict(status="error", message="outline read_failed: " + e)
    }
    return evaluate(content)
}
```

This is the inverse of the redundant runtime type guard documented in `code-organization.md` (§ "Do Not Guard Contract-Typed Values"): the fail-closed rule adds a *missing* guard at an I/O boundary, while that rule removes a *superfluous* guard on a value the type signature already pins.

## Symmetric Diagnostic Fields Across Sibling Branches

When one runtime condition drives two sibling branches — one that fails loud with a named reason and one that silently falls back to a degraded path — the fallback branch MUST record the SAME reason literal into the audit/diagnostic field. Omitting it leaves the field at its default (e.g. `None`), so the audit line logs a value-less placeholder and the actual cause of the degradation is lost.

```text
// BAD — the fallback branch under the SAME condition never names the reason
reason = null
if (mode == "strict" && incompatible) {
    failLoud("env_or_working_dir_set")  // reason named explicitly
}
if (mode == "auto" && incompatible) {
    // falls back silently — reason stays null, audit trail is corrupted
}

// GOOD — the sibling branch mirrors the same literal into the audit field
reason = null
if (mode == "strict" && incompatible) {
    failLoud("env_or_working_dir_set")
}
if (mode == "auto" && incompatible) {
    reason = "env_or_working_dir_set"  // symmetric with the fail-loud branch above
}
```

A per-branch diagnostic/audit field defaulted to a sentinel (`None`/`null`/empty) must be set on EVERY branch that reaches the audited outcome. A newly-added early-skip or fallback branch that omits it does not fail a test (the sentinel is a valid value) and does not change control flow — it only corrupts the audit trail, invisible until someone reads the log and finds the sentinel where a real reason should be. When adding a branch that reaches an audited outcome, check whether a sibling branch under the same triggering condition already names a reason and mirror it: this is a symmetric-pair authoring obligation, not merely a style preference. (extends lesson 2026-07-21-08-001)
