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

When composing tasks for a deliverable where `compatibility=breaking` OR the `change_type` is `tech_debt` or `feature_breaking`, and it touches code paths covered by existing module tests, phase-4-plan MUST:

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

## (d) Foundation + Sweep variant (broad breaking refactors)

The rules in (a) through (c) describe the **single-deliverable** task split: one implementation task + one test-contract task per deliverable, with the planned-failure exception coordinating the two. That shape works when the public-contract change has a tractable consumer-site count — roughly **≤ 10 custom-surface targets** (where "custom-surface target" means a consumer that needs more than a pure mechanical rename, e.g., a value-object update, a new validator, a structural test rewrite). The existing **3-consumer threshold rule** documented above remains in force: deliverables with ≤ 3 consumer sites and trivial edits collapse to a single task with no split, regardless of `compatibility=breaking`.

When the custom-surface target count crosses **N > ~10**, the planner MUST additionally split into a two-batch sequence — a **foundation batch** that proves the pattern on a representative subset, and a **sweep batch** that applies the proven pattern to the remaining targets in a separate plan with the foundation already merged. The foundation batch lives in the originating plan; the sweep batch lives in a successor plan that the originating plan creates (via `manage-lessons add` or a recipe-driven seed).

**Activation thresholds**:

- **First tier** (existing 3-consumer rule, unchanged): if total consumer-site count ≤ 3 AND every edit is mechanical (pure rename, no structural change), collapse to a single task. No split.
- **Second tier** (existing single-split, unchanged): if 4 ≤ N ≤ ~10 OR any consumer requires structural changes (new fields, rewritten test logic, custom adapters), apply the single-deliverable split documented in (b). One implementation task + one test-contract task per deliverable.
- **Third tier** (new — foundation + sweep): if N > ~10 custom-surface targets, apply the second-tier split AND additionally split the work across two plans:
  - **Foundation batch** (originating plan): the validator / utility infrastructure that supports the new contract, plus 3–5 representative consumer targets chosen to exercise the breadth of the consumer population (one of each "shape" of consumer — e.g., a leaf consumer, a fan-out consumer, a consumer that itself has downstream consumers). The foundation batch's purpose is to **prove the pattern** end-to-end: validator implementation + at least one consumer migration + the resulting build/test verification all land in the same plan.
  - **Sweep batch** (successor plan, seeded from the originating plan via `manage-lessons add` or a recipe): the remaining N − foundation-count consumer targets. The sweep plan's deliverables apply the proven pattern to one consumer per deliverable (or in small batches when the per-consumer effort is uniformly trivial). The sweep plan opens AFTER the foundation plan merges, so the sweep agents work against a code base where the new contract is already enforced by the merged validator.

**Why the second plan** — keeping all N consumers in a single plan would produce one of two failure modes:

1. **One huge implementation task** that the model cannot keep in working context — the diff exceeds the context window, the agent loses track of which consumers it has already touched, and silently leaves some unchanged. A single implementation task that tries to update more than ~10 custom-surface consumer sites in one diff risks losing coverage on some of them.
2. **N + 1 separate tasks in one plan** that overflow the plan's task budget and create cross-task dependency tangles. Phase-5-execute can serialise large task counts, but the orchestrator's review surface, the PR diff, and the reviewer's cognitive load do not scale linearly. A 30-task PR is harder to review than three 10-task PRs.

Splitting into a foundation plan + a sweep plan keeps each plan's task count bounded, each PR's review surface bounded, and each agent's working context bounded. The foundation plan's merged state is the contract the sweep plan operates against, so the sweep plan's individual deliverables are independent and parallelisable.

**Foundation batch composition rules**:

- The validator / utility infrastructure MUST land in the foundation plan. The sweep plan operates on a code base where the contract is already enforced; if the validator is not merged before the sweep starts, every sweep deliverable has to re-verify the foundation as part of its verification step, and the planned-failure exception in (c) collapses into a generic verification failure loop.
- The 3-5 representative consumers MUST exercise the consumer population's variability. Picking 3 leaf consumers when half the population is fan-out consumers proves nothing about the sweep's tractability. The planner SHOULD enumerate the consumer shapes (via `architecture find --pattern {producer_constant}` or `Grep --files-with-matches`) and pick one consumer per shape category.
- The foundation batch MAY include a recipe seed for the sweep plan — `recipe-refactor-to-profile-standards` is the canonical seed when the sweep applies a standards-driven transformation to each consumer. The recipe key carries the foundation's contract forward so each sweep deliverable inherits the same activation heuristics.

**Counter-indication (no foundation+sweep split)**:

- **Pure mechanical rename** — a producer constant rename where every consumer site needs an identical token swap. Even at N > 10, a mechanical rename does not need a foundation: there is no contract change to "prove", and the sweep agents have no structural decisions to make. Apply the **Path / Constant Migration Sub-pattern** instead (see `phase-4-plan/SKILL.md`).
- **Producer and all consumers in the same module** — when all N consumers live under a single skill directory, the foundation+sweep split adds no review-surface benefit because the originating plan already has bounded scope (one skill's worth of files). Apply the standard second-tier split (b) with a single implementation task that touches all N consumers in one diff.
- **Total consumer-site count ≤ 3 with trivial edits** — already captured by the first-tier rule above; restated here for completeness. The first-tier rule overrides any third-tier consideration.

**Cross-reference**: the **Path / Constant Migration Sub-pattern** in `phase-4-plan/SKILL.md` and the **Integration Deliverable Narrative Constraint** in the same file compose with this rule. The migration sub-pattern shapes the per-task decomposition (code / test / prose / example / verification); this rule shapes the per-plan decomposition (foundation vs sweep). The two operate on orthogonal axes — a single foundation deliverable may itself follow the migration sub-pattern across its 5 tasks, and a sweep plan's deliverables typically each follow the migration sub-pattern within their own task allocations.

## Cross-references

- `../SKILL.md` — phase-4-plan workflow that allocates the two tasks per the rule in (b)
- `../../phase-5-execute/SKILL.md` — phase-5-execute dispatcher that applies the planned-failure exception in (c)
- `../../manage-tasks/standards/task-contract.md` — task-record schema (steps, depends_on, profile)
- `../../phase-2-refine/SKILL.md` — source of `compatibility` (breaking / deprecation / smart_and_ask / back-compat)
- `../../ref-workflow-architecture/standards/change-types.md` — definitions of `tech_debt` and `feature_breaking`
