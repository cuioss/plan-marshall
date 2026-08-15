# Testing Methodology

Language-agnostic testing principles for writing reliable, maintainable tests across any technology stack.

## Fundamental Principles

* **No zero-benefit comments**. Do not add `// Arrange`, `// Act`, `// Assert` or similar phase markers — whitespace separation makes the structure clear. Comments are only justified when they explain non-obvious setup or business logic.
* **Choose generated data or an exact literal by what the contract is** — this is a discriminator, not a preference. Where the contract is **universal** ("for all valid inputs, P holds" — parsers, identifier validators, path normalisers, round-trip encoders), use randomized generators or factory methods so tests prove behavior for any valid input, not just `"test"` or `42`; consult your technology-specific skill for generator APIs. Where **the literal *is* the contract** (a seeded config default, a canonical step id, a serialized field name, an argparse flag spelling, a documented exit code, a wire-format key, plus format-specific parsing values, spec-defined boundary values, and exact error messages), write the value exactly — a generator there replaces the one value that matters with an arbitrary one and asserts nothing, making it the defect rather than the fix. The full statement, with the question that settles any given case, is § "Test Data Principles → The discriminator".
* **No branching logic in tests**. Tests must never contain `if/else`, `switch`, or ternary operators. Each test exercises exactly one deterministic path. If you need to test multiple scenarios, write separate test methods.
* **Explicit assertions over implicit checks**. Always assert the expected outcome explicitly. Never rely on "no exception thrown" as the only verification.
* **Always test corner cases**: null/undefined inputs, empty collections, boundary values, error paths. Group corner cases in dedicated test classes or nested groups.

## Test Categories

**Never write tests just for coverage metrics or a green bar.** Tests that execute code without verifying behavior are always a bug — they create false confidence and must be rewritten. If you encounter assertion-free tests or tests that only check "no exception thrown", treat them as defects. Every test must assert a specific contract. If in doubt about what a test should verify, ask the user.

Every unit test targets the **contract** (API/specification) of the method under test, never its internal implementation. Tests that depend on implementation details break on refactoring without catching real bugs.

Organize tests into these categories, in order of priority:

### 1. Happy Path

Tests that exercise the method as intended by its specification. Where the contract is universal, use generated data within the defined valid ranges to prove the method works for any conforming input, not just hand-picked examples; where the literal is the contract, assert the exact value (§ "Test Data Principles → The discriminator").

### 2. Parameter Variants

Systematic exploration of the valid input space using generators. Vary parameters across their specified types, ranges, and combinations. This is the rigorous form of happy-path testing — if the spec says "accepts strings of 1-255 characters", generate strings across that range.

### 3. Corner Cases

Inputs deliberately **outside** or **at the boundary** of specified constraints: null/undefined values, empty collections, zero-length strings, minimum/maximum boundary values, invalid formats. These verify the method's defensive behavior.

### 4. Error Conditions

Scenarios where **infrastructure assumptions are not met**: dependencies unavailable, services returning errors, resources missing, timeouts occurring. These verify graceful degradation and proper error propagation.

Each category should be grouped in its own test class or nested group (see Test Class Organization below).

## AAA Pattern (Arrange-Act-Assert)

All tests follow three phases separated by blank lines:

```text
test "Should validate input with correct format" {
    // Phase 1: Arrange — set up test data and preconditions
    input = generateValidInput()
    expectedResult = createExpectedResult(input)

    // Phase 2: Act — execute the single operation under test
    result = service.validate(input)

    // Phase 3: Assert — verify expected outcome
    assert result.isValid == true
    assert result.value == expectedResult
}
```

### Rules

* One logical assertion per test (group related assertions using framework features like `assertAll`)
* Descriptive variable names that convey intent
* Test data chosen by the discriminator — generated where the contract is universal, an exact literal where the literal *is* the contract (§ "Test Data Principles → The discriminator")
* Single action in the Act phase — if you need multiple actions, it's an integration test or needs splitting

## Test Class Organization

### Test Class Mapping

Each production type (class, module, component) requires at least one dedicated test class/file.

* Test naming: `{ProductionName}Test` or `{ProductionName}.test` (follow framework convention)
* Test files in the same package/directory structure as production code (in test source root)
* At least one test file per production file — split into multiple when the module exceeds the budget below

### Module Budget: 400 lines

**A test module is budgeted at 400 lines.** A module over budget is split by *behaviour cluster* into
`test_{unit}_{cluster}.py` — never in arbitrary halves, and never by line count alone.

The budget is derived from the corpus rather than invented: the median test module in this repository
measures ~327 lines, so a 400-line budget sits above the median and describes the tree's own compliant
majority instead of an aspiration no module meets.

The budget is **enforced** — `pm-plugin-development:plugin-doctor`'s
[`test-module-line-budget`](../../../../pm-plugin-development/skills/plugin-doctor/standards/doctor-test-conventions.md#test-module-line-budget)
rule reports every module over it. That enforcement is the difference between this budget and a
number a reader learns to ignore.

### Splitting by behaviour cluster

Split on what the tests *assert*, so each resulting module has a nameable subject:

* `test_{unit}_{cluster}.py` — one cluster per module, named for the behaviour it pins
  (`test_resolver_fallbacks.py`, `test_resolver_validation.py`), not for its position in a
  sequence (`test_resolver_part2.py`)
* Typical clusters: core/happy-path behaviour, validation and error paths, edge cases, integration
  scenarios
* A cluster too small to name is not a cluster — leave it with its parent rather than manufacturing
  a module

An arbitrary halving splits one subject across two files and leaves neither module describable; the
next author then cannot tell which half a new test belongs in.

### Grouping Related Tests

Use nesting constructs (JUnit `@Nested`, Jest `describe`, etc.) when **3 or more tests** belong to the same logical group. Do not nest single or two tests.

Typical groups:
* Valid input handling
* Invalid input handling
* Corner cases / edge cases
* Error paths

## Test Helper Module Organization

Private helper modules co-located with tests (shared fixtures, factory helpers, utility functions used across multiple test files) MUST be named so that they do not collide with any framework-reserved test-collection module name. Framework-reserved names trigger implicit discovery or loading semantics that are reserved for the framework's own use; reusing such a name for a private helper causes subtle, silent breakage that is hard to diagnose.

### Rules

* **Never name a helper module after a framework-reserved collection module.** Reserved names are owned by the test framework and are resolved by name through framework-specific search rules (e.g., nearest-ancestor lookup). A helper that happens to match a reserved name can shadow the project-root module of the same name from subdirectories, silently replacing the intended module for tests below that directory.
* **Canonical helper module name: `_fixtures.py`** (or the direct-equivalent spelling in the target language, e.g., `_fixtures.js`, `_Fixtures.java`). The leading underscore signals "private helper, not a test target" and keeps the module out of any auto-discovery pattern that matches on `test_*` / `*_test` / `*Test` names.
* Prefer a short, descriptive unqualified name with the underscore prefix over framework-specific conventions that collide with reserved names. If a helper needs further specialization, use a descriptive suffix (`_fixtures_http.py`, `_fixtures_db.py`) rather than layering more reserved names.
* The shadowing-avoidance rationale is the load-bearing constraint — it is the reason the rule exists, not a stylistic preference. Placing a helper with a reserved name in a subdirectory causes the framework's nearest-ancestor resolution to pick up the helper instead of the project-root module, breaking every test below that directory.

### Language/framework-specific detail

For the pytest-specific resolution behavior (how pytest discovers `conftest.py` via nearest-ancestor walk, and why a subdirectory `conftest.py` shadows the project-root `conftest.py`), see `pm-dev-python:pytest-testing` — `standards/testing-pytest.md`. That document contains the authoritative pytest resolution detail and the concrete diagnosis checklist when shadowing is suspected. This section defines the language-agnostic rule; the pytest skill documents the framework-specific mechanics.

## Test Naming

Test names should describe the expected behavior:

* **Pattern**: `should{ExpectedBehavior}When{Condition}` or `should{ExpectedBehavior}`
* **Good**: `shouldRejectExpiredToken`, `shouldReturnEmptyListWhenNoResults`
* **Bad**: `test1`, `testValidation`, `itWorks`

## Test Docstring Content

**A test docstring states the invariant, in the present tense.** It names the contract the test pins,
as that contract stands today. A second paragraph is added only where the invariant is genuinely
non-obvious, and it explains *why the invariant is load-bearing* — which is present-tense and survives
the next edit.

A test docstring does **not** narrate the incident that produced the test, and does not cite:

* a plan id or a deliverable id
* a PR or issue number
* a lesson id
* a superseded behaviour ("used to", "no longer", "the old behaviour", "previously")

### Where this rule comes from

This is not a new standard. It is `CLAUDE.md` § Documentation Standards — "No version history", "No
timestamps", "Current state only" — applied to a tree those standards were never scoped over. It is
the same rule that `pm-plugin-development:plugin-doctor` already enforces across
`marketplace/bundles/**` through its `no-historical-prose-in-skills`, `no-incident-references`, and
`no-lesson-id-in-skill-prose` rules. Over the test tree it is enforced by
[`test-docstring-historical-prose`](../../../../pm-plugin-development/skills/plugin-doctor/standards/doctor-test-conventions.md#test-docstring-historical-prose).

The reasoning is the same in both trees: a citation reasons from something the reader cannot see. It
costs context on every read and teaches the reader to reason from a PR number instead of from the
mechanism in front of them. The history is recoverable from `git log` and from the plan record; the
docstring's job is to say what the test pins *now*.

### Worked example

A real docstring from this repository, and its repair:

**Before** — the invariant is present but buried behind a citation the reader cannot resolve:

```text
"""A ``test/**`` path absent from every ``files`` inventory resolves to its
owning module through the ``paths.tests`` containment fallback — not the
root ``default`` module and not ``None`` (closes lesson 2026-07-09-04-001)."""
```

**After** — same invariant, no citation, and the load-bearing reason stated in the present tense:

```text
"""A ``test/**`` path absent from every ``files`` inventory resolves to its
owning module through the ``paths.tests`` containment fallback.

The two wrong answers are the ones that look plausible: the root ``default``
module (which would silently mis-attribute every uninventoried test path) and
``None`` (which would drop the path from module resolution entirely)."""
```

The second paragraph earns its place because the invariant is non-obvious — it says why *these* two
alternatives are the dangerous ones. That reason is true today and stays true; the lesson id was true
only once.

### What a docstring legitimately carries

Rationale, when the invariant is non-obvious: which alternative behaviour would be wrong and why, what
breaks if the contract is violated, which boundary the value sits on. All present-tense, all still
accurate after the code is refactored.

## Test Data Principles

Whether test data should be generated or written as an exact literal is decided by **what the contract
is**, not by preference. Generated data and exact literals are each correct for a different class of
contract, and using one where the other belongs produces a test that asserts nothing.

### The discriminator

**Generated data where the contract is universal.** The behaviour under test is expressible as *"for
all valid inputs, P holds"* — text and format parsers, identifier validators, path normalisers,
round-trip encoders, comparators, sort and merge routines. Here a handful of hand-picked literals
samples an input space the contract quantifies over, so a generator is the stronger assertion.

* Use framework-specific generators (consult your language-specific testing skill for recommended libraries)
* Generate values within valid ranges for the domain
* Use meaningful variable names even for generated data

**Exact literals where the literal is the contract.** The behaviour under test *is* a specific value —
a seeded config knob's default, a canonical step id, a serialized field name, an argparse flag
spelling, a documented exit code, a wire-format key. Here the literal is the whole assertion: a
generator would replace the one value that matters with an arbitrary one and prove nothing. In this
case a generator **is the defect, not the fix**.

The question that settles any given case: *would this test still be meaningful if the value were
different?* If yes, the contract is universal — generate. If no — if a different value means the
production behaviour is wrong — the literal is the contract, so write it exactly.

### Forbidden Patterns

* Arbitrary hardcoded literals like `"test"`, `"hello"`, `"John"` or magic numbers like `42`, `100`
  **when the contract is universal** — that is, when the test would work equally well with any valid
  input, so the specific value carries no meaning (use generators instead). This does **not** apply to
  a literal that *is* the contract under the discriminator above: a test asserting a seeded default,
  a canonical id, or a flag spelling states that value exactly, and doing so is correct.
* Shared mutable test state between tests
* Test order dependencies

### Test Data Factories

For complex objects, create factory methods or builders:

```text
// Factory method for test objects
function createValidUser(overrides = {}) {
    return {
        name: generateName(),
        email: generateEmail(),
        ...overrides
    }
}
```

## Test Reliability

### No Fixed Delays

Never use fixed-time waits in tests:

* **Anti-pattern**: `sleep(2000)`, `Thread.sleep(5000)`, `cy.wait(3000)`
* **Correct**: Use polling/retry mechanisms provided by your testing framework (consult your language-specific testing skill for recommended libraries)

Fixed delays make tests slow and flaky — they either wait too long (slow CI) or not long enough (intermittent failures).

### Deterministic Paths

Each test must exercise exactly one deterministic path through the code:

* No conditional logic deciding what to assert
* No try/catch in test code (unless testing exception behavior)
* No loops that may execute 0 times
* No reliance on external state (time, network, filesystem)

### Hermetic Against Machine-Global Out-of-Process Services

A unit test whose pass/fail depends on the liveness or registration state of a machine-global, out-of-process service (a daemon, a shared build queue, a system-wide cache) is not hermetic — its verdict is a function of ambient developer-machine state rather than of controlled, mocked inputs. The same commit can pass on a machine with the service absent and fail on a machine where it happens to be live, so the in-house gate result stops being reproducible.

**Durable rule**: gate the real-service branch behind an **injected dependency the test controls**, not a global liveness probe. Two equivalent techniques:

* Mock/stub the liveness-check seam directly (e.g. patch the module-level routing function) so the test deterministically exercises the path it intends to assert.
* Prefer, where the production API offers it, an **explicit per-call mode parameter** injected by the test (e.g. `execution_mode=in_process`) over probing ambient state — the explicit mode is auditable in production too, not just in tests, and closes the hermeticity gap at the API boundary rather than only at the test boundary.

Either way, add a companion test that explicitly asserts the real-service submission path with a *mocked* service, never a live one.

Both techniques above are per-test: they make *the test that remembers to apply them* hermetic. That is necessary but not sufficient, because the next test written against the same seam inherits nothing. The rule below is what makes hermeticity the default rather than a convention.

### Neutralize State-Dependent Branch Selection at the Fixture Level

**Trigger**: production code selects between branches by consulting **live machine state** — a daemon's registration/readiness handshake, a shared queue's occupancy, a system-wide cache's presence — and a test drives that code without pinning the branch. The test then asserts one thing on a machine where the state is absent and another where it is present.

**Part 1 — the default must be structural, not remembered.** A test whose branch selection depends on live machine state MUST have that state neutralized by a **shared, default-on fixture that every test inherits by construction**. A per-test opt-in — an inline stub of the seam, an explicit mode argument, a helper each test must remember to call — is insufficient *as the default*, because a newly-written test inherits none of it: it is ambiently state-dependent from the moment it is written, and nothing fails to say so. Correctness that depends on every future author repeating an incantation is not a guarantee; it is a habit, and habits regress silently.

Where a subset of tests legitimately owns the state-dependent behaviour as its **system under test**, express the exclusion in two tiers:

* A **location carve-out** — a directory whose modules own the behaviour, resolved from the collected test's own path. This is structural: a module added there inherits the exclusion, and one moved out of it loses the exclusion, with no registry to forget to update.
* A **registered marker** reserved for one-off exceptions that live outside that directory. Keep it registered in the marker registry (so `--strict-markers` catches typos) and keep its use rare — a marker that accumulates members is a location carve-out that has not been recognized yet.

Deriving the exclusion set is part of the work, not an afterthought: enumerate the tests that own the behaviour **before** switching the default on. A blanket neutralization applied over a routing-owning test does not fail loudly — it replaces the seam that test asserts on and reduces its assertions to tautologies, deleting the coverage while the suite stays green.

**Part 2 — the fixture needs a matched positive/negative control.** A neutralizing fixture is self-concealing: if it silently stops engaging, every test it protects keeps passing on any host where the state is absent, and the regression surfaces only as ambient flakiness elsewhere. Pin it with a **matched pair** in which both arms *simulate* the state the fixture suppresses:

* **Positive arm** — fixture engaged, state simulated as present, assert the neutralized branch is still taken.
* **Negative control** — identical setup, fixture disengaged via the marker, assert the state-dependent branch IS taken.

The negative arm must simulate the state, never rely on it being absent from the host — an arm that passes because nothing was reachable proves nothing. The pair is the evidence: each arm alone is consistent with the fixture being vacuous, and only the contrast between two otherwise-identical setups attributes the outcome to the fixture. Record in the module docstring that the two are a matched pair and that deleting or weakening either one voids the other's evidentiary value.

**Relation to [Compose Isolation, Don't Impose It](#compose-isolation-dont-impose-it)**: that rule rejects blanket auto-applied fixtures that mutate **global resolution state** (config roots, env vars, search paths) precisely because individual tests legitimately stage their own version of the redirected resource, making the collision set large and unbounded. This rule governs the opposite shape: neutralizing **ambient machine state** that no test should depend on, where the correct default is uniform and the collision set is small, enumerable, and structurally identifiable as "the tests that own this behaviour". Auto-application is appropriate here for the reason that rule names — the redirection is universally correct for every test in scope, minus a carve-out derived up front.

**Concrete instance in this repository** (a discoverability pointer, not the rule): marshalld build routing is neutralized by the default-on `_neutralize_daemon_routing` autouse fixture in `test/conftest.py`, carved out by location for `test/plan-marshall/build-server/`, with the registered `allow_daemon_routing` marker for routing-owning modules outside it, and pinned by the matched pair in `test/plan-marshall/script-shared/test_daemon_routing_neutralization.py`.

### Test Isolation

Each test must be independent:

* Tests must not depend on execution order
* Tests must not share mutable state
* Each test creates its own test data
* Each test cleans up its own resources (or uses framework lifecycle hooks)

### Compose Isolation, Don't Impose It

**Trigger**: An isolation fixture mutates *global resolution state* — config roots, environment variables, module-search paths, the working directory, or any other process-wide lookup that decides which file/resource the code under test resolves to. The seductive shortcut is to make such a fixture **auto-applied to every test in scope** (e.g. `autouse=True` in pytest, a global `beforeEach`, a base-class setup every test inherits) so isolation becomes the default and no test has to opt in.

A blanket auto-applied redirect has **repo-wide blast radius**: it runs before every test in scope, including tests that deliberately stage their own version of the redirected resource. The moment one test sets up its own config file (or env var, or search path) and a global fixture silently re-points resolution somewhere else, that test fails — not because of any change to the code it exercises, but because a blanket fixture overrode the resource root it carefully established. The failure presents as "resolved the wrong file / read empty config", not as a logic error in the tested code.

**Durable rule**: a fixture that mutates global resolution state must be **explicit and parameterized, not auto-applied**. Auto-application is appropriate only for redirections that are *universally correct for every test in scope*. The instant a single test needs to stage its own version of the redirected resource, decompose the auto-applied fixture into an **opt-in helper that re-points resolution at a caller-supplied target** — each test (or each subtree's setup) invokes the helper explicitly with its own file:

* A test that needs an empty/default resource calls the helper pointed at its own empty sandbox.
* A test that stages its own resource calls the helper pointed at *that* resource.
* Isolation becomes a composable building block each test opts into with the right target.

**When adding a blanket isolation fixture, audit the tests in scope first** for ones that manage their own version of the resource the fixture redirects (search for tests that write the resolved config/manifest/reference file into their own fixture directory). Those tests are the collision set — they are exactly the ones a global redirect will silently break.

### Bound Per-Test Guard Traversal by the Test's Own Footprint

**Trigger**: An isolation or pollution-detection guard walks a shared directory tree to verify a test did not leave stray files behind (or to redirect/scan resolved paths). The guard runs per test, and the tree it walks can grow to contain **unrelated full checkouts** — sibling worktree checkouts, vendored dependencies, build output, version-control object stores.

The trap: a *recursive* walk rooted at a directory that can contain full checkouts is an **O(repo-size × test-count)** cost. If hundreds of tests each pay a recursive walk over a tree holding several worktree checkouts (each with its own object store, build output, and nested caches), the guard — not the framework, not parallelism — becomes the dominant runtime cost. The symptom is a suite whose wall time scales with the *number of retained checkouts in the shared tree*, not with the code under change.

**Durable rule**: a per-test guard's traversal cost must be bounded by the **test's own footprint**, never by the size of a shared tree that can contain unrelated full checkouts. Apply all three:

* **Never recurse from the shared root.** Do not walk every descendant of a directory that can hold worktree checkouts or vendored trees.
* **Depth-limit and scope the walk.** Restrict the guard to the specific directories a test is allowed to write (its own fixture sandbox / redirected base directory), or walk only the top one or two levels with explicit exclusions.
* **Prune heavy subtrees** from any traversal that must touch the shared tree at all — worktree-checkout directories, version-control object stores, build-output directories, dependency caches, and bytecode caches. A recursive glob (`pathlib.Path.rglob`) cannot prune as it walks — filtering its results still pays the full traversal cost; use a walker that supports in-place pruning (e.g. `os.walk` with `dirnames[:]` edited to drop the heavy directories) so the skipped subtrees are never descended.

**Corollary — measure on a quiescent machine before attributing a regression.** Before blaming a hypothesized cause for a performance regression, measure with no concurrent runs and no orphaned background builds: a recursive guard over a shared worktrees tree can be the real slowdown rather than the subprocess/parallelism thrash first suspected, and a conclusion built on a contended machine sends the fix in the wrong direction.

## Integration Test Separation

Integration tests must be separated from unit tests:

* **Unit tests**: Fast, isolated, run on every build
* **Integration tests**: May be slower, test component interaction, run in CI/CD
* Separate by naming convention or directory structure per framework
* CI/CD pipelines should be able to run each type independently

## One Layer Per Contract

**Where an in-process test and a subprocess test assert the same behaviour, the in-process test is
authoritative.** The subprocess coverage collapses to a single per-script CLI-plumbing smoke that
proves the entry point wires up — parses its arguments, reaches its main function, and returns its
exit code.

The subprocess layer's job is to prove the entry point *is wired*, not to re-assert the logic behind
it. Asserting one contract at both layers doubles the runtime and the maintenance cost of every change
to that contract, and the second assertion catches nothing the first did not.

### Two exceptions, and they are what keep the rule safe

1. **Do not collapse where the subprocess test is the only coverage.** If no in-process test asserts
   the contract, the subprocess test *is* the coverage — collapsing it deletes the assertion. Write
   the in-process test first, then collapse.
2. **Do not collapse where the subprocess boundary is itself the subject.** Environment-variable
   propagation, exit-code contracts, stdout/stderr separation, signal handling, and argv quoting are
   properties *of* the boundary; only a subprocess test can assert them.

### Every collapse names its replacement

A collapse must name the in-process test that now carries the contract. Without that, a reviewer
cannot distinguish a collapse (coverage preserved at a better layer) from a deletion (coverage gone) —
and the two look identical in a diff that only removes lines.

## Enumerate Existing Test Consumers Before Changing a Default / Constant / Enum Value

**Trigger**: A production change alters a contract value that tests assert against — a default value, a named constant, an enum member, a threshold, a magic literal baked into the public behavior. The hazard is asymmetric: the production change is one line, but an unknown number of existing tests pin the *old* value, and a green local run on the production module says nothing about the test files that assert the old default elsewhere in the tree. The failure surfaces only when the full suite runs — typically in CI, after the change is already pushed — and is then "fixed" in a follow-up remediation commit, splitting one logical change across two commits and leaving the first commit non-buildable in isolation.

The discipline is to discover and update every consumer in the SAME atomic change, so verify passes on the first cut.

**Procedure** — apply all three steps before declaring the change complete:

1. **Discover — grep the test tree for BOTH the symbol name AND the old literal value.** A consumer can assert the value by referencing the named symbol (`assertEquals(DEFAULT_TIMEOUT, …)`) or by hardcoding the literal (`assertEquals(30, …)`). Searching only the symbol name misses every test that inlined the literal; searching only the literal misses symbol-referencing tests and drowns in unrelated matches. Run both searches across the entire test source root, not just the module under change — consumers in sibling modules assert cross-module contract values too. *Note: If the old literal is a highly common primitive (e.g., `0`, `1`, `true`, `false`, `""`), combine the literal search with the symbol name or class context to avoid excessive false positives. Always use anchored matching or word boundaries (e.g., `\b` or `\<`/`\>`) to prevent incorrect partial matches within larger tokens (such as matching `30` inside `130`).*
2. **Classify — separate old-default assertions from intentional explicit overrides.** Each match is one of two kinds: (a) an *old-default assertion* that exists to pin the current default and MUST be updated to the new value; or (b) an *intentional explicit override* — a test that deliberately supplies the old value as an input (not as the default) to exercise a specific scenario, which is correct as-is and MUST be left untouched. Misclassifying an override as a default-assertion corrupts a deliberate test; misclassifying a default-assertion as an override leaves a stale failure. Read each match's intent, do not blanket-replace.
3. **Atomicity — update all matched old-default assertions in one change alongside the production change.** The production value change and every test update it forces form a single atomic deliverable. Ship them together so the full suite passes on the first cut and every commit is independently buildable — never as a production commit followed by a "fix the tests" remediation commit. If the touch set is large, that is information about the blast radius of the value change, not a reason to defer the test updates.

**Action:** Treat "this value is asserted somewhere I haven't looked" as the default assumption for any contract-value change. Run the two-pronged grep before writing the production edit so the full consumer set is known up front and folded into the same change.

## Assertion Quality

### Meaningful Messages

All assertions should include descriptive failure messages:

* Describe what should have happened, not what went wrong
* **Good**: `"Token should be valid"`, `"Result list should contain 3 items"`
* **Bad**: `"Failed"`, `"Token is invalid"`, `"Wrong"`

### One Concept Per Test

Test one logical concept per test method. Use grouped assertions (like `assertAll`) when verifying multiple properties of a single result — but don't test unrelated behaviors in one test.

## Property-Based Testing

Property-based testing complements example-based tests by generating many random inputs and verifying that invariants (properties) hold for all of them. This is particularly effective for:

* **Pure functions** with well-defined input/output contracts
* **Serialization/deserialization** roundtrips (encode then decode yields original)
* **Mathematical properties** (commutativity, associativity, idempotency)
* **Data structure invariants** (sorted output stays sorted, size constraints hold)

### When to use property-based tests

* The function has a clear contract expressible as "for all valid inputs, this property holds"
* Example-based tests feel incomplete — you suspect edge cases exist but can't enumerate them
* The input space is large or complex (strings, collections, nested structures)

### When NOT to use property-based tests

* **The literal is the contract** — the behaviour under test is one specific value (a seeded config
  default, a canonical step id, a serialized field name, an argparse flag spelling). Generating over
  the value replaces the assertion with an arbitrary one; write the literal exactly. See § "Test Data
  Principles → The discriminator".
* The behavior is inherently example-specific (UI rendering, specific business rules)
* Generating valid inputs is harder than writing the test
* The function has significant side effects that are hard to verify as properties

Property-based testing is a **scoped** technique, not a default: it earns its place on the universal
half of the discriminator and is actively wrong on the other half. Reach for it where the contract
quantifies over inputs, and reach for exact examples everywhere else.

### Writing properties

A good property is a universal statement about the function's behavior:

```text
// Property: parsing a valid token always succeeds
for all validToken in generateValidTokens():
    assert parse(validToken).isSuccess()

// Property: roundtrip -- serialize then deserialize yields original
for all user in generateUsers():
    assert deserialize(serialize(user)) == user

// Property: sorting is idempotent
for all list in generateLists():
    assert sort(sort(list)) == sort(list)
```

Consult your language-specific testing skill for framework APIs (e.g., Hypothesis for Python, jqwik for Java, fast-check for JavaScript).

## Test Doubles

Test doubles substitute real dependencies in unit tests. Choose the simplest double that makes the test work.

### Taxonomy (simplest to most complex)

| Double | What it does | When to use |
|--------|-------------|-------------|
| **Dummy** | Passed but never used (satisfies a parameter) | Filling required parameters the test doesn't care about |
| **Stub** | Returns canned answers to calls | Controlling indirect inputs (e.g., config values, lookup results) |
| **Fake** | Working implementation with shortcuts (e.g., in-memory database) | When real dependency is slow/unavailable but behavior matters |
| **Spy** | Records calls for later verification | Verifying that a side effect occurred (e.g., event published) |
| **Mock** | Pre-programmed expectations that verify interactions | Complex interaction verification (use sparingly) |

### Guidelines

* **Prefer real objects** when they're fast and deterministic. A real `ArrayList` is better than a mocked `List`.
* **Prefer fakes over mocks** for complex dependencies. An in-memory repository is more realistic than a mocked one.
* **Mock at system boundaries** — external services, databases, file systems, network calls. Don't mock internal collaborators.
* **Don't verify implementation details** with mocks. Verifying that `service.save()` was called is testing implementation. Verifying the entity appears in the repository tests behavior.
* **One mock per test** is a good heuristic. If a test needs many mocks, the unit under test may have too many dependencies (SRP violation).

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|-------------|---------|----------|
| Arbitrary hardcoded data **where the contract is universal** | A handful of literals samples an input space the contract quantifies over | Use generated data. Does not apply where the literal *is* the contract (a seeded default, canonical id, field name, flag spelling) — see § "Test Data Principles → The discriminator" |
| Branching in tests | Non-deterministic coverage | One path per test |
| Fixed delays | Slow and flaky | Polling/event-based waiting |
| Shared mutable state | Order-dependent failures | Isolated test data |
| Missing assertions | Tests pass but verify nothing | Explicit assertions |
| Over-mocking | Tests prove mocks work, not code | Mock at boundaries only, prefer real collaborators |
| Mocking by default | Mock libraries add complexity and hide bugs | Only use mocks when they save significant setup; prefer real objects, fakes, or in-memory implementations |
| Testing implementation | Brittle tests break on refactoring | Test behavior, not implementation |
| Pinning known-wrong behavior as a "documented limitation" | A test that asserts the bug creates friction against fixing it — the test itself becomes the obstacle to the improvement | Assert the *correct* behavior and mark the test expected-to-fail (see below) or skipped with a TODO; never assert the wrong behavior |

### Surfacing limitations without locking them in

When writing tests surfaces a real limitation in the code under test (e.g. a comparator that uses substring matching where boundary matching is required), resist the temptation to write a test that asserts the broken behavior and label it a "documented limitation". Such a test does not express intent — it expresses a workaround masquerading as intent, and a future reviewer wanting to fix the bug must argue both for the fix and for deleting the test that "proves" the bug is intentional.

Instead:

1. **Fix the limitation in the same task** if the fix is small (a handful of lines) and the code path is already being touched.
2. **Write a test that asserts the *correct* behavior** even if the code currently fails it, and mark it expected-to-fail with a clear TODO referencing where the fix will land. Use the language's idiom for expected failure:
   * Python / pytest: `@pytest.mark.xfail(reason="TODO: fix boundary matching — see LESSON-nnnn")` (preferred — reports `XPASS` when the bug is fixed) or `@pytest.mark.skip(reason="…")`.
   * JUnit 5: `Assumptions.abort("TODO: …")` or `@Disabled("TODO: …")`.
   * Jest: `test.skip("TODO: …")` with a TODO comment (Jest has no native expected-fail marker). Vitest: `test.fails("…")` runs the test and records it as a known failure.
3. **Surface the limitation up the chain** — record it in a lesson, a PR body, or an issue — so the follow-up is tracked. Do not encode it as a regression test that future-you has to argue against.

Signals that the anti-pattern is about to be committed: the test name contains phrases like "documented limitation", "known behavior", "future-work", or "trade-off"; the test's docstring explains *why* the assertion is intentionally wrong; the rationale claims an alternative implementation "would be a breaking change" for the test. When reviewing, ask: would the author still write this test if the underlying bug were fixed five minutes before the review? If the answer is "no, the test would be deleted", the test does not deserve to land.

## Foundation utilities — tests against the CLI

Foundation utilities — argument-parser wrappers, identifier validators, format coercers, and other primitives consumed by many `manage-*` CLI scripts — fail in characteristic ways: a primitive that looks correct in isolation breaks the moment a real CLI runs through it (subparser graph, typed flags, adversarial `dest` names, real argv lists). Pure unit tests of the resolver primitives pass while the integration plumbing silently rots. The countermeasure is to drive tests through the **real downstream entry point** rather than through a hand-rolled `Namespace` or a mocked resolver.

1. **Prefer integration-style tests that drive the real downstream entry point.** For an argparse wrapper, build a real `argparse.ArgumentParser` (with subparsers if the CLI uses them) and pass an `argv: list[str]` through `parser.parse_args()` so the wrapper runs end-to-end. Pure unit tests of the resolver functions are valuable for branch coverage but they systematically blind-spot the integration path that ships in production.
2. **Build a small reusable parser fixture mirroring the real CLI shape.** When the foundation utility is consumed by `manage-*` CLI scripts, ship a fixture (named with a domain prefix per the unique-fixture-basenames rule below) that wires a representative parser graph: subparsers, typed-ID flags, mixed required/optional arguments. The fixture catches whole categories of bugs that resolver-level mocking hides — adversarial `dest` names, prefix-anchored matches, subparser-walk gaps.
3. **Treat phase-3-outline inline reasoning as a hypothesis, not a verification step.** When the outline (or a code review) reads the helper alongside its call sites and concludes "looks fine", that is a hypothesis the test layer must falsify on real inputs. Plan tests that can fail when the hypothesis is wrong; do not let "the helper reads correctly" stand in for "the helper executes correctly".

The three corresponding `pm-plugin-development:plugin-doctor` rules — [`unique-fixture-basenames`](../../../../pm-plugin-development/skills/plugin-doctor/standards/doctor-test-conventions.md#unique-fixture-basenames), [`subprocess-pythonpath`](../../../../pm-plugin-development/skills/plugin-doctor/standards/doctor-test-conventions.md#subprocess-pythonpath), and [`identifier-validator-corpus`](../../../../pm-plugin-development/skills/plugin-doctor/standards/doctor-test-conventions.md#identifier-validator-corpus) — enforce these recommendations as build-failing lints across the `test/` tree. A developer hitting one of those lints can read the rationale here; a developer reading this section discovers the enforcement that catches drift.

See the corresponding plugin-doctor rules linked above for the canonical enforcement rationale.

## Assert the Constructed Argv at the Lowest Subprocess Primitive

**Trigger**: A code path under test builds a subprocess command line — assembling a list of program name, subcommands, and flags — and then hands it to a process launcher. The unit under test is *which* command gets built (the argument surface: correct flag names, required flags present, no undeclared flag), not the behavior of the launched process. The seductive shortcut is to stub a high-level wrapper that takes an *already-assembled* command and asserts on the wrapper's return value, leaving the argv-assembly logic itself unobserved.

A stub placed **above** argv assembly is blind to a malformed argv: it receives whatever list the assembler produced, ignores its contents, and returns a canned success. Every assertion downstream passes — yet a misspelled flag, a missing required flag, or a flag the callee never declared has been silently constructed. In production, the callee receives that malformed argv and degrades through a default branch, a `None` path, or an argument-parser rejection that the caller swallows. The test suite stays green because the test never inspected the bytes that actually flow to the subprocess. The failure surfaces only at runtime, against the real callee, long after the green suite "proved" the wiring.

**Durable rule**: when the contract under test is the constructed command line, stub **only the lowest subprocess primitive** — the process launcher itself (e.g. `subprocess.run` / `subprocess.Popen` in Python, the `exec`/`spawn` family in other runtimes) — capture the exact argument vector it was called with, and assert that vector against the callee's declared argument surface:

* **Every flag name is present and spelled exactly as the callee declares it.** A flag the caller renames or paraphrases is the single most common silent-degrade defect; assert the literal names, not a substring or a count.
* **Every required flag is present.** Assert presence of each mandatory flag, not merely that the argv is non-empty.
* **No undeclared flag is present.** An extra flag the callee does not accept is rejected at parse time in production; assert the argv carries nothing outside the declared surface.

```text
# Stub ONLY the launcher; capture and assert the argv it received.
captured = []
stub(process_launcher) returns success, recording its argv into `captured`

result = unit_under_test(inputs)

argv = captured.single_call.argv
assert argv contains "--required-flag"          # required flag present
assert argv contains exactly the declared flags  # no undeclared or misspelled flags
```

Do NOT stub a higher-level "run this assembled command" wrapper when the thing under test is the assembly. Such a stub receives the malformed argv, ignores it, and reports success — the exact blind spot this rule exists to close.

This is universal subprocess-wiring methodology. It is the **complementary lens** to the "Foundation utilities — tests against the CLI" section above: that section drives the real downstream argument-parser entry point to catch integration-plumbing rot; this section captures the argv at the launch boundary to catch assembly-side defects before the command ever reaches a parser. Apply both where a primitive both *builds* and *launches* subprocess command lines.

## Require a Real-Resolver End-to-End Test for Path-Resolver and Create Side Effects

**Trigger**: The code under test performs filesystem-shaped side effects through path resolvers — creating a directory tree, moving or relocating files, establishing symlinks, or running multi-step lifecycle machinery whose post-operation code reads back the on-disk state the create step produced. The fast unit-test instinct is to mock the resolvers and hand-build a partial directory tree that *looks like* what the create step would have produced, then exercise the post-operation code against that fake.

A fake resolver that stages a partial tree reproduces the **shape** the post-operation code expects, not the **real on-disk state** the real create operation produces. Real create operations have interacting side effects that a hand-built fixture never reproduces: a blanket symlink that collides with a granular directory move; a created resource whose object store or metadata directory changes what a later walk sees; ordering between a move and a resolve that only manifests when both run for real. Because the fake skips the real side-effect interaction, the failing path is never exercised and the suite stays green — while production hits the collision the moment a real resource exists on disk.

**Durable rule**: for any path-resolver, create, move, symlink, or lifecycle machinery, ship **at least one end-to-end test that uses the real create operation and the real resolvers with no mocked resolvers**. The real resource — with its real side effects — must exist on disk during the test, and the post-operation code must read it back from the real on-disk state:

* **Use the real create/move/symlink operation**, not a hand-built fixture that mimics its output. The interaction between side effects is precisely what a fake omits.
* **Use the real resolvers**, not stubs that return pre-baked paths. A stubbed resolver cannot collide with a real side effect.
* **Let the real resource live on disk** in a temporary sandbox, run the full operation against it, then assert the post-operation state from what is actually there.

**Review tell**: the test module names the path resolvers *only in mock setup* and never lets a real created resource — with its real side effects — exist on disk. A suite that mocks every resolver for a create-and-read lifecycle is asserting against its own fixture, not against the machinery.

This E2E requirement is adjacent to two existing real-on-disk isolation concerns: "Compose Isolation, Don't Impose It" (above) governs how such a test isolates the global resolution state it mutates, and "Bound Per-Test Guard Traversal by the Test's Own Footprint" (above) governs the cost of any guard that walks the real tree the test creates. Read all three together when adding a real-resource lifecycle test.
