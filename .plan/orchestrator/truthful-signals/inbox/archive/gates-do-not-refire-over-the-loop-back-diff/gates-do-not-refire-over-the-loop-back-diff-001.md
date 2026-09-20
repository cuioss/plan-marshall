envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=landing
created=2026-08-01T19:09:47Z

## What landed

**PLAN-TRUTH-001** (`gates-do-not-refire-over-the-loop-back-diff`) shipped as **PR #1073**, merged CI-green.

The plan's thesis: gates must not re-fire over the loop-back diff, and the head-dependence membership that decides which gates re-fire must be **derived from the live registry**, never carried in a hand-maintained list.

## Material outcomes

### 1. The head-dependent population was DERIVED over all 25 registered finalize steps

Derivation over the live registry returned **9 head-dependent / 16 not**. The ninth member — `project:finalize-step-era-stamp-fill` — was **missing from the hand-maintained list**.

The load-bearing detail: the spec's "nine / three" numerals were **correct** and the *enumeration* was short by one. Reconciling the numeral **down** to eight to match the list would have shipped the exact defect the plan exists to remove. The disagreement between a count and its list is evidence that the list is wrong at least as often as the count is.

### 2. D5a landed — `architecture-refresh` classified INLINE

`dispatch-inline-split.md` now classifies `default:architecture-refresh` as INLINE with the `AskUserQuestion` mechanism, and the `:23` rationale was **DELETED, not reworded** (a reworded stale rationale is still a stale rationale). Verified live this run: `architecture-refresh` executed inline.

### 3. Ride-along order correction resolved in favour of the live registry

`architecture-refresh` is **order 9**; the doc's "Current Implementations" table said 25. Registry wins.

### 4. Self-review found a genuine defect on every one of three passes

`pre-submission-self-review` ran **THREE passes** and found a genuine defect on **every** pass — **six total**, all fixed.

Two of the six were **introduced by this plan's own earlier fixes**:
- iteration 1's fix created iteration 2's finding;
- iteration 2's fix created a false universal that `finalize-step-simplify` then caught.

This is strong direct evidence for the plan's core thesis: a fix is a new diff, and a gate that does not re-read the post-fix diff certifies a state that no longer exists.

### 5. RECURRENCE — 7th sighting of the hand-maintained-membership archetype

The plan's **own iteration-2 fix** reintroduced a hand-maintained membership fragment of **exactly the archetype the plan removes**. Filed separately as a `candidate-lesson`.

## Residue the epic should track

- **12 `candidate-lesson` messages** accompany this landing: 3 proposed lessons + 9 handed-over findings the plan observed but did **not** action. Several sit squarely on the epic's own theme (a confident signal hiding a caveat).
- **PR #1073 merged UNREVIEWED by operator choice.** CI was green but **no bot read the diff**: pr-agent posted only a participation Guide, coderabbit refused with `awaitable_window`, sourcery refused with `hard_quota`. A green finalize on this PR is **not** evidence the diff was reviewed. A post-merge PR revisit is owed.
- **Pre-existing on main, surfaced (not caused) by this diff**: `default:finalize-step-security-audit` and `default:architecture-refresh` both declare `order: 9`.
