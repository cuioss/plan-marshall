# Testing Methodology

Language-agnostic testing principles for writing reliable, maintainable tests across any technology stack.

## Fundamental Principles

* **No zero-benefit comments**. Do not add `// Arrange`, `// Act`, `// Assert` or similar phase markers — whitespace separation makes the structure clear. Comments are only justified when they explain non-obvious setup or business logic.
* **Prefer generated test data** over hardcoded literals. Use randomized generators or factory methods so tests prove behavior works for any valid input, not just `"test"` or `42`. Consult your technology-specific skill for generator APIs. **Exceptions:** specific values are appropriate when testing format-specific parsing (e.g., date patterns, protocol constants), known boundary values from a specification, or exact error messages.
* **No branching logic in tests**. Tests must never contain `if/else`, `switch`, or ternary operators. Each test exercises exactly one deterministic path. If you need to test multiple scenarios, write separate test methods.
* **Explicit assertions over implicit checks**. Always assert the expected outcome explicitly. Never rely on "no exception thrown" as the only verification.
* **Always test corner cases**: null/undefined inputs, empty collections, boundary values, error paths. Group corner cases in dedicated test classes or nested groups.

## Test Categories

**Never write tests just for coverage metrics or a green bar.** Tests that execute code without verifying behavior are always a bug — they create false confidence and must be rewritten. If you encounter assertion-free tests or tests that only check "no exception thrown", treat them as defects. Every test must assert a specific contract. If in doubt about what a test should verify, ask the user.

Every unit test targets the **contract** (API/specification) of the method under test, never its internal implementation. Tests that depend on implementation details break on refactoring without catching real bugs.

Organize tests into these categories, in order of priority:

### 1. Happy Path

Tests that exercise the method as intended by its specification. Use generated data within the defined valid ranges to prove the method works for any conforming input, not just hand-picked examples.

### 2. Parameter Variants

Systematic exploration of the valid input space using generators. Vary parameters across their specified types, ranges, and combinations. This is the rigorous form of happy-path testing — if the spec says "accepts strings of 1-255 characters", generate strings across that range.

### 3. Corner Cases

Inputs deliberately **outside** or **at the boundary** of specified constraints: null/undefined values, empty collections, zero-length strings, minimum/maximum boundary values, invalid formats. These verify the method's defensive behavior.

### 4. Error Conditions

Scenarios where **infrastructure assumptions are not met**: dependencies unavailable, services returning errors, resources missing, timeouts occurring. These verify graceful degradation and proper error propagation.

Each category should be grouped in its own test class or nested group (see Test Class Organization below).

## AAA Pattern (Arrange-Act-Assert)

All tests follow three phases separated by blank lines:

```
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
* Generated test data, not hardcoded literals
* Single action in the Act phase — if you need multiple actions, it's an integration test or needs splitting

## Test Class Organization

### Test Class Mapping

Each production type (class, module, component) requires at least one dedicated test class/file.

* Test naming: `{ProductionName}Test` or `{ProductionName}.test` (follow framework convention)
* Test files in the same package/directory structure as production code (in test source root)
* At least one test file per production file — split into multiple when exceeding ~200 lines

### Splitting Large Test Files

When a test file exceeds ~200 lines, split into focused groups:

* `{Name}Test` — happy-path and core behavior
* `{Name}EdgeCaseTest` — corner cases and error paths
* `{Name}IntegrationTest` — integration scenarios

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

## Test Data Principles

### Generated Data

Tests should use generated/random data to prove behavior works for any valid input:

* Use framework-specific generators (consult your language-specific testing skill for recommended libraries)
* Generate values within valid ranges for the domain
* Use meaningful variable names even for generated data

### Forbidden Patterns

* Arbitrary hardcoded literals like `"test"`, `"hello"`, `"John"` or magic numbers like `42`, `100` when the test would work equally well with any valid input (use generators instead)
* Shared mutable test state between tests
* Test order dependencies

### Test Data Factories

For complex objects, create factory methods or builders:

```
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

* The behavior is inherently example-specific (UI rendering, specific business rules)
* Generating valid inputs is harder than writing the test
* The function has significant side effects that are hard to verify as properties

### Writing properties

A good property is a universal statement about the function's behavior:

```
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
| Arbitrary hardcoded data | Tests prove nothing about general behavior | Use generated data (except for format-specific, boundary, or spec-defined values) |
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

```
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
