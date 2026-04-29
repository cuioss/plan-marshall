# Breaking-Refactor Task Split

**Purpose**: Codify how phase-4-plan composes tasks for breaking refactors that intentionally invalidate existing test contracts, and how phase-5-execute treats the resulting verification failure as a planned outcome rather than an error.

This document defines a single contract spanning two phases. Phase-4-plan applies the **task-split rule** when allocating tasks for a `tech_debt` or `feature_breaking` deliverable; phase-5-execute applies the **planned-failure exception** when an implementation task with an explicit downstream test-contract dependency fails verification in exactly the way the downstream task is scoped to fix. Both phases enforce the rules listed below — the rules are load-bearing only when the refactor changes a public contract that pre-existing tests pin.

## (a) When to apply

Apply the breaking-refactor task split when **all** of the following hold:

1. The refactor changes the **public contract** that one or more existing tests assert against. "Public contract" is whatever surface the tests actually pin — method signature, return shape, output format, side-effect ordering, error type, etc. If the refactor only touches an internal detail that no test references, it is not a contract change for this rule.
2. The set of tests requiring rewrite is **finite and identifiable** at planning time. Phase-4-plan must be able to enumerate which tests need updating (by file path and test name) before composing the task array. "Update wherever needed" is not finite — it is open-ended scope.
3. The deliverable's `compatibility=breaking` (from phase-2-refine) **OR** its `change_type` is `tech_debt` or `feature_breaking`. These three values are the only signals that the deliverable is permitted to invalidate existing test contracts; any other combination must keep existing tests green.

Do **NOT** apply the task split when any of the following hold (each maps to a distinct alternative path):

- **Tests do not pin the changed contract.** This is a pure internal refactor — bundling implementation and test updates into a single task is fine because no test is expected to fail mid-refactor. The split exists to manage the planned-failure window between implementation and test-contract update; without that window, the split adds no value.
- **The test-change set is open-ended.** "Update wherever needed" or "fix tests as we find them" means the deliverable is not actually scoped — re-scope the refactor in phase-3-outline before allocating tasks. Phase-4-plan must not paper over an unscoped refactor by composing tasks against an unbounded test set.
- **`compatibility=back-compat`**. The deliverable's contract is that existing tests must keep passing; a planned-failure window contradicts the back-compat contract. Use deprecation patterns (parallel new APIs, `@Deprecated` markers) instead of breaking the existing test surface.

If any single condition above is true, do not apply the task split — pick the alternative path called out in that condition.

## (b) The phase-4-plan rule

When composing tasks for a `tech_debt` or `feature_breaking` deliverable that touches code paths covered by existing module tests, phase-4-plan MUST:

1. **Allocate the implementation task** with `profile: implementation` and the implementation skill set resolved from `module.skills_by_profile.implementation`. Steps target only production code paths from the deliverable's `Affected files` section. The implementation task carries no `depends_on` linkage to the test-contract task.
2. **Allocate the test-contract-update task** with `profile: module_testing`, the testing skill set resolved from `module.skills_by_profile.module_testing`, and `depends_on: [TASK-{implementation_number}]`. The dependency arrow points from the test-contract task to the implementation task — phase-5-execute will not start the test-contract task until the implementation task has finished, even if the implementation task's verification failed (see (c) below).
3. The test-contract-update task's `description` MUST include both:
   - **(a) Pre-existing test count and identity.** Enumerate the count and identity (file path plus test name) of every pre-existing test that needs rewriting. Phase-6-finalize uses this enumeration to verify scope at finalize time — a test-contract task that rewrites fewer or more tests than enumerated is a scope mismatch and must be triaged.
   - **(b) New regression tests that pin the new contract.** Any new test scenarios introduced to lock in the new contract must be listed alongside the rewrites. A test-contract task is not a free-form "make tests pass" task; it is the documented inverse of the implementation task's contract change.

Both tasks share the same `deliverable` number. When a deliverable's `profiles` list already contains `implementation` and `module_testing`, the standard 1:N task-creation flow in phase-4-plan Step 5 produces these two tasks naturally — the breaking-refactor rule additionally requires the description anchoring above and the explicit `depends_on` linkage. The description anchoring contract from phase-4-plan Step 6 (verbatim title quote, intent gloss copy, structural-token preservation) applies in full; this rule layers the test-enumeration requirement on top of those baseline rules.

## (c) The phase-5-execute planned-failure exception

When a task with `profile: implementation` produces a verification failure that **exactly matches** the test-contract changes scoped to a downstream task with `depends_on` pointing back at the current task, the dispatcher MAY proceed to the dependent task without flagging the failure as an error. This is the **only** case in phase-5-execute where "tests fail" is the planned outcome of the implementation step.

**Rationale**: The implementation task is by construction the cause of the test failure — the public contract changed, so tests pinning the old contract fail. Treating that failure as a verification error would block the test-contract task from running, even though the test-contract task is the documented remediation. The exception preserves the dispatcher's failure-handling discipline elsewhere by demanding tight boundary conditions before the failure is allowed through.

**Boundary conditions** (all must hold; if any fails, the exception does NOT apply and the failure is a normal verification error):

1. **The downstream task must be the EXACT test-contract task.** A downstream task that updates documentation, adds new features, or refactors unrelated code is not the test-contract task; the exception does not cover those. The downstream task's `profile` must be `module_testing`, its `deliverable` must match the implementation task's `deliverable`, and its description must enumerate the failing tests per (b) above.
2. **The downstream task must have explicit `depends_on` linkage to the current task.** A downstream task that happens to run after the implementation task without a `depends_on` edge does not qualify — the linkage must be declared at planning time, not inferred at execution time.
3. **The verification failure must match the enumerated test set.** The set of failing tests reported by the implementation task's verification command must be a subset of the tests enumerated in the test-contract task's description. New failures (tests not on the list) are real regressions and must be triaged via the standard Step 11 path.

When all three boundary conditions hold, phase-5-execute logs the planned-failure decision, marks the implementation task as `done` (not `blocked`), and proceeds to dispatch the test-contract task. After the test-contract task completes, the standard verification path resumes — the test-contract task itself must produce a green test run; if it does not, that is a real failure and must be triaged normally.

## Cross-references

- `../SKILL.md` — phase-4-plan workflow that allocates the two tasks per the rule in (b)
- `../../phase-5-execute/SKILL.md` — phase-5-execute dispatcher that applies the planned-failure exception in (c)
- `../../manage-tasks/standards/task-contract.md` — task-record schema (steps, depends_on, profile)
- `../../phase-2-refine/SKILL.md` — source of `compatibility` (breaking / deprecation / smart_and_ask / back-compat)
- `../../ref-workflow-architecture/standards/change-types.md` — definitions of `tech_debt` and `feature_breaking`
