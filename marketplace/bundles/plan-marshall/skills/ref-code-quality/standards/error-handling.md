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

## Fail-Closed Classification

A *classifier* is any function that reduces evidence to a verdict another component acts on: a path-to-module map, a build-status derivation, a build/no-build decision, a freshness gate, a coverage-scope resolver, an aggregation over several producers.

The sibling rule above (§ "Fail-Closed Read-Only Gate Verbs") governs the **crash** direction — an I/O failure inside a verdict path must become a structured error rather than a stack trace. This rule governs the **laundering** direction: a classifier that cannot substantiate a verdict MUST NOT emit the benign one. "I could not classify this" is an outcome in its own right, and collapsing it into "nothing to report" hands the caller a confident green it never earned. The two rules are complementary and are not restated in each other.

Six concrete rules follow, each in the rule-plus-BAD/GOOD-pseudocode shape used throughout this document.

### (a) Order specific rows before a catch-all

An ordered match table is read top-down, so a catch-all placed above a specific row makes that row unreachable — and the unreachable row is invisible at the call site, because the table still *looks* like it covers the case. Order the table so the catch-all is reached only when no specific row applies.

```text
// BAD — the broad row is tested first and shadows every specific row below it
PATTERNS = [
    ("marketplace/bundles/**",        "production"),  // catch-all, listed first
    ("marketplace/bundles/*/test/**", "test"),        // unreachable — never matches
]

// GOOD — most specific first; the catch-all is the last resort
PATTERNS = [
    ("marketplace/bundles/*/test/**", "test"),
    ("marketplace/bundles/**",        "production"),
]
```

### (b) Fail closed on undetermined, `None`, or empty state

An inability to classify is its own outcome and must never collapse into the benign one. A filter that drops the unclassifiable inputs makes the empty set indistinguishable from "there was nothing to worry about", and the caller receives a confident verdict computed over a silently truncated population.

```text
// BAD — "no row matched" is laundered into "nothing can diverge"
function resolveScope(paths) {
    modules = paths.map(moduleOf).filter(notNull)   // unmapped paths vanish here
    return { modules: modules, divergencePossible: modules.size > 1 }
}

// GOOD — an unmapped path is reported, and forces the conservative verdict
function resolveScope(paths) {
    modules = []; unmapped = []
    for (p in paths) {
        m = moduleOf(p)
        if (m == null) unmapped.add(p) else modules.add(m)
    }
    if (unmapped.notEmpty() || modules.isEmpty()) {
        // cannot prove coverage — say so, and fall back to the widest run
        return { modules: modules, unmapped: unmapped, divergencePossible: true }
    }
    return { modules: modules, unmapped: [], divergencePossible: modules.size > 1 }
}
```

### (c) Branch on a dispatched producer's status before folding its payload

A producer that crashed, was skipped, or refused returns an empty payload — structurally identical to a producer that ran and found nothing. Read the producer's own status field first; only then fold its payload into the aggregate.

```text
// BAD — the payload is folded without reading the producer's verdict
result = producer.run()
findings.addAll(result.findings)   // a crashed producer contributes zero findings
report(status = findings.isEmpty() ? "clean" : "findings")   // ... and reads as clean

// GOOD — a failed producer can never read as clean
result = producer.run()
if (result.status != "success") {
    return report(status = "error",
                  reason = producer.name + " did not complete: " + result.message)
}
findings.addAll(result.findings)
report(status = findings.isEmpty() ? "clean" : "findings")
```

### (d) Require an affirmative success signal, never absence-of-change

"Nothing changed" is satisfied both by an operation that succeeded idempotently and by an operation that never ran. Absence-of-change is therefore not evidence of success; require the operation to report its own outcome and branch on that.

```text
// BAD — an empty diff is read as proof the fix landed
applyFix(file)
if (diff(file).isEmpty()) {
    markResolved()   // equally true when applyFix silently did nothing
}

// GOOD — the operation reports whether it applied, and that is what is read
outcome = applyFix(file)
if (outcome.applied) markResolved() else markUnresolved(outcome.reason)
```

### (e) Exit `0` from an always-exit-`0` wrapper is necessary, not sufficient

A wrapper that models its outcome in its stdout payload and always exits `0` makes the exit code a liveness signal, not a verdict. Read the wrapper's reported outcome for the verdict; a nonzero exit still wins outright, because a process failure the wrapper never got to report must not be overridden by whatever it printed before dying.

```text
// BAD — the exit code of an always-exit-0 wrapper is taken as the build verdict
exitCode = run(buildWrapper)
status   = (exitCode == 0) ? "success" : "error"   // a timed-out build stamps success

// GOOD — nonzero exit is authoritative; otherwise the reported outcome decides
exitCode = run(buildWrapper)
if (exitCode < 0)  return "killed"    // terminated by a signal
if (exitCode != 0) return "error"     // wins over any stdout claim of success
reported = parse(buildWrapper.stdout)?.status
return (reported in KNOWN_BUILD_STATUSES) ? reported : "success"
```

### (f) Write direction — check the persist, never refer to a store that rejected it

The rules above cover the read direction. The write direction is symmetric and is the one most often missed: a producer that persists a finding MUST check the persist call's exit status, and MUST NOT emit a clean or referral signal on a failed persist. A by-reference referral ("the findings are in the store, go read them") is a promise about state the producer has not verified; when the persist was rejected, the referral points the consumer at an empty store and the finding is lost silently.

```text
// BAD — the persist result is discarded, then the caller is referred to the store
for (f in findings) store.add(f)         // a rejection exits 0 and is never read
return { status: "triage_required" }     // "go read the store" — which is empty

// GOOD — the persist is checked, and a short readback downgrades the referral
persisted = []
for (f in findings) {
    if (store.add(f).status == "success") persisted.add(f)
}
if (persisted.size < findings.size) {
    return { status: "error", error: "finding_persist_failed",
             unpersisted: findings.minus(persisted) }   // carried INLINE, not by reference
}
return { status: "triage_required" }
```

### Worked examples in this repository

Three landed behaviours are the reference implementations of these rules:

* **The build-status derivation at the executor dispatch boundary** (`_derive_build_status` in `tools-script-executor/templates/execute-script.py.template`) treats a nonzero exit code as authoritative over any stdout `status: success`, and reads the wrapper's stdout status only on a zero exit — so a timed-out build stamps `timeout` while a script that prints a success payload and exits non-zero stamps `error`. Rules (a) and (e).
* **The pre-commit freshness gate** (`manage-tasks pre-commit-verify-freshness`) matches change-ledger rows on `status == "success"` rather than on `exit_code == 0`, and a row lacking `status` never matches — the gate fails closed to `stale` rather than admitting a row it cannot read. Rules (b) and (e).
* **The executor preflight verdict** (`generate_executor preflight` in `tools-script-executor`) reports `marshal_status: unknown` plus a legible warning when the installed manifest cannot be resolved, instead of the `fresh` verdict it has no evidence for. Rule (b).

### Accepted decisions this discipline generalises

The rules above are the cross-cutting form of four decisions already accepted in this repository; consult the decision record for the reasoning rather than re-deriving it here.

* **ADR-004** — content no build system builds is deliberately absent from the build map, and that absence must never propagate into classification.
* **ADR-009** — a status report fails closed with an explicit `unknown` state rather than a vacuously fresh positive it cannot substantiate.
* **ADR-014** — no producer may suppress an element without reporting the condition that suppressed it, so a working-but-empty result stays distinguishable from an inert one.
* **ADR-015** — an absent identity is a stated sentinel and every presence guard becomes a meaning guard, so a null verdict is never overloaded across "determined to be nothing" and "nothing determinable".

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

A per-branch diagnostic/audit field defaulted to a sentinel (`None`/`null`/empty) must be set on EVERY branch that reaches the audited outcome. A newly-added early-skip or fallback branch that omits it does not fail a test (the sentinel is a valid value) and does not change control flow — it only corrupts the audit trail, invisible until someone reads the log and finds the sentinel where a real reason should be. When adding a branch that reaches an audited outcome, check whether a sibling branch under the same triggering condition already names a reason and mirror it: this is a symmetric-pair authoring obligation, not merely a style preference.
