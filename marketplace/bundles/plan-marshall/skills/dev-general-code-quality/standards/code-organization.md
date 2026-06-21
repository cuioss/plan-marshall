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

## Minimum Viable Code

**Trigger**: Code carries weight that no live caller, test, or requirement justifies — surplus structure added "to be safe" or "for later".

The guiding principle: implement the minimum that satisfies the present requirement. Surplus structure is not free — every speculative parameter, re-export, or abstraction layer is something a future reader must understand, a static analyzer must scan, and a maintainer must keep correct. When in doubt, leave it out; the change is cheap to add later against a real requirement and expensive to retrofit-remove once callers depend on its accidental presence.

**Required-vs-speculative carve-out (the discriminator):** "Minimum" excludes genuinely-required error handling at a real I/O / external-input boundary — it does NOT mean "strip all guards." A guard at a real boundary that handles a failure the boundary can actually produce is **required** and MUST be kept or added; a guard for a state that cannot occur is **speculative** and is stripped. Apply this discriminator before deleting any guard:

* **Required (keep / add).** Error handling at a real failure path that can occur in production: an unguarded parse of an external file (`json.loads` on a file the program does not write — config, manifest, network payload), a missing type-guard on externally-sourced data (`.items()` / `.attr` on a value sourced from user config or an external API without an `isinstance` check), a missing envelope on a network / filesystem boundary that can fail. These are not "defensive complexity" — they are the correct handling of a failure mode the boundary genuinely produces, and removing them reintroduces a latent crash.
* **Speculative (strip — YAGNI).** Guards for failures that cannot occur given the call graph (a re-check of an invariant a caller already guarantees, a `try/except` around code that cannot raise), configurability for callers that do not exist, and abstraction for a second implementation that is not planned. These remain surplus and are removed.
* **Surplus-despite-real-boundary (strip).** A guard at a real callable-execution boundary that genuinely CAN raise is **still surplus and MUST be stripped** when the surrounding code's reason to exist is to surface that very crash loudly — a synthetic test fixture whose job is to PROVE a callable runs, a meta-test, or a self-check harness. "Real boundary" alone does not earn Required status; a guard that swallows the failure its own surrounding code exists to expose defeats that code's purpose. Example: a coverage fixture that executes each analyzer to prove it runs, then wraps that call in `except Exception`, masks the exact failure the fixture exists to surface — strip the guard and let the crash propagate, so a broken analyzer fails the fixture loudly instead of passing silently.

The test has two parts, not one: *(1) can the boundary actually produce this failure?* and *(2) does the guard defeat the surrounding code's reason to exist?* A guard is Required only when (1) is yes AND (2) is no. If the state is impossible, the guard is Speculative; if the boundary is real but the guard masks a failure the surrounding code exists to surface, the guard is Surplus-despite-real-boundary. The catalogue's "Defensive try/except" anti-pattern below targets the second and third cases — it never licenses deleting a guard at a real boundary whose failure the surrounding code is meant to handle rather than expose.

**Detection:**

* **Unused parameters preserved for future use.** A parameter that no code path reads, kept "because a caller might need it later". Remove it; add it back when a real caller needs it.
* **Thin/backward-compat re-exports with <= 1 live caller.** A module that exists only to re-export a symbol from another module, with at most one importer. Inline the import at the single call site and delete the shim.
* **Defensive try/except around already-handled or should-fail-loudly failures.** A guard that swallows or re-wraps an exception the caller already handles, or that masks a programming error that should crash loudly — including the case where the boundary is real but the surrounding code's purpose is to surface that crash (a test fixture, meta-test, or self-check harness that wraps the very callable it exists to exercise). Let it propagate. *This anti-pattern applies to the speculative and surplus-despite-real-boundary cases only — it does NOT license removing required error handling at a real I/O / external-input boundary whose failure the surrounding code is meant to handle rather than expose (see the required-vs-speculative carve-out above).*
* **Multiple near-identical helpers where one parameterised function suffices.** Two or more functions differing only in a constant or a branch. Collapse into one function with a parameter.
* **Signature-restating docstrings/comments.** A docstring or comment that names the parameters and return type without adding intent ("WHY") beyond what the signature already states. Delete it or replace it with a rationale.
* **Config keys/flags with a single hard-coded caller.** A configuration knob, feature flag, or setting read in exactly one place and never varied. Inline the constant and remove the key.
* **Speculative abstraction for extensibility with no second implementation.** An interface, base class, strategy, or plugin seam introduced for a hypothetical second implementation that does not yet exist. Code the concrete case directly; introduce the seam when the second implementation arrives.

**Action:** Delete the surplus structure and verify nothing breaks. For each anti-pattern above, the resolution is removal or inlining — never "keep it but document the intent". When the surplus is a public/protected element or could plausibly serve an imminent requirement, ask the user before removing (mirrors the [Unused Code](#unused-code) "Do NOT remove when" exceptions). This section is the constructive counterpart to [Over-Abstraction](#over-abstraction): Over-Abstraction targets indirection layers after they exist; Minimum Viable Code prevents the surplus from being written in the first place. The two reinforce each other — apply Minimum Viable Code at authoring time, Over-Abstraction at refactoring time.

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

## TOCTOU / Check-Then-Act Hazards

**Trigger**: Any flow that claims a shared resource by reading its state, deciding based on that read, and then acting on the decision — when a concurrent actor can change the state between the read and the act. The classic shape is a cooperative cross-process lock or shared-state coordinator: merge locks, worktree allocation, plan-id reservation, leader election, "first writer wins" registries, or any "claim a shared resource" flow where two processes (or two threads, or two host invocations) race for the same slot.

The time-of-check-to-time-of-use (TOCTOU) window is the gap between observing the shared state ("the lock is free", "this id is unclaimed") and committing the claim. Two claimants that both check inside the same window both conclude the resource is free, both write, and both believe they own it. The corruption is silent: each actor proceeds as the sole owner.

**Detection:**

* A read of shared state (file, row, key, in-memory map) followed by a conditional write to the same state, with no atomicity guarantee spanning both operations.
* "If not present, create it" / "if free, take it" logic against storage shared across processes or hosts.
* Lock or reservation acquired by writing a marker, with no verification that the marker written is the one that survived.
* Last-writer-wins semantics treated as mutual exclusion.

**Mitigation menu** — choose one (or combine); this is the canonical, reusable set. Apply it at design time:

* **(a) Post-write double-check.** After writing the claim, re-read the shared state and confirm you are the recorded owner. If the read-back shows a different owner, you lost the race — back off, release any partial state, and either retry or fail cleanly. This converts a silent double-claim into an observable, recoverable loss.
* **(b) Deterministic tiebreaker.** When concurrent claimants are possible, impose a total order so every claimant resolves the contest identically — e.g., compare a globally unique identifier (such as host ID + PID, UUID, or lexicographic plan-id), and let the lowest (or highest) win. Both racers independently compute the same winner, so the loser yields without coordination. A tiebreaker makes the double-check in (a) deterministic rather than first-come.
* **(c) Prefer an atomic primitive.** Where the storage medium offers one, replace read-then-write with a single atomic operation that fails if the resource is already claimed: atomic create (`O_EXCL`), atomic rename onto a target that must not pre-exist, compare-and-swap, or a unique-key insert that rejects duplicates. The atomic primitive collapses the check and the act into one indivisible step, eliminating the window entirely. This is the strongest mitigation — prefer it when available.

**Action:** Design the mitigation into the claim flow from the start — do NOT defer concurrency correctness to PR review. A check-then-act race is invisible in single-actor testing and on a clean diff read; it surfaces only under concurrent load, by which point it is a production incident rather than a review comment. Treat "two of these can run at once" as a first-class design input for any shared-resource claim, and pick a mitigation from the menu above before writing the happy path.

## Maintenance Prioritization

| Priority | Examples |
|----------|----------|
| **High** | Security vulnerabilities, public API contract issues, fundamental design problems (SRP violations, god classes), error handling gaps in critical paths |
| **Medium** | Long methods (> 50 lines), high complexity (> 15), legacy patterns, unused/dead code |
| **Low** | Style inconsistencies, minor documentation improvements, speculative performance optimizations |
