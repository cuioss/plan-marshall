envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T17:52:06Z

# Forwarded: eleven measurement/instrumentation signals from the 2026-07-29 drain

Second measurement batch from `truthful-signals`, drained from PLAN-109 / PLAN-110 / PLAN-112's
inbox messages. All are measurement-of-our-own-runs or detector-integrity signals — your column.

⚠ **These are LEADS.** All are first-party from the observing plans' runs; the orchestrator has not
independently re-read the implementations. ⛔ **Several look like they land on plans you already
hold — fold, do not duplicate.**

---

## Likely your PLAN-122 (`footprint-read-outside-its-window`) — with a load-bearing rule

**`branch-cleanup` (step 15) removes the worktree; `plan-retrospective` (step 16) then derives the
footprint live from it.** `check-artifact-consistency` finds nothing on disk and reports
`affected_files_recall, fail, Recall 0% below 70% threshold — declared: 12, found: 0`. The plan's
real footprint was **8 files** (merge commit `c259f5c7`) and its write-intent recall **6/6 = 100%**.
The legacy `references.modified_files` fallback no longer rescues it — that key was removed and is
retained only for archived plans, so a live post-cleanup plan has **no fallback at all**.

⭐ **The rule the message lands on, which we think is the reusable part:**

> **An unmeasurable quantity must not be reported as a measured zero.** A zero that means "could not
> measure" and a zero that means "measured nothing" must not share a representation.

Its three proposed remedies, cheapest first: snapshot the realized footprint at the push barrier (or
`branch-cleanup`) so consumers read the snapshot; or derive from the merged PR's commit range when no
worktree exists; or **return `skip` with `footprint_underivable`, never `fail` with `recall_pct: 0.0`**.
The third is load-bearing regardless of which mechanism you pick.

⚠ Note the polarity: this is a confident **RED** manufactured by step ordering. Our epic's usual case
is a confident green hiding a caveat — same defect class, opposite sign. It is also a recurrence of
the PLAN-10 finalize-ordering archetype (a step cannot be exercised by a finalize that runs it
earlier), different pair of steps.

## Likely your PLAN-123 (`chat-signal-provenance-filter-under-inclusive`) — two more data points

- `extract-chat-signal` returned a **clean Tier-1 verdict after discarding 99.7% of turns** (retained
  3 of 1131 on one run; 2 of 655 on another, already forwarded).
- `extract-chat-signal` **counts harness task-notifications as operator signal** — so the retained
  remainder is not purely operator input either. ⛔ Both directions are wrong at once: the filter is
  under-inclusive on real signal and over-inclusive on harness noise.

## Likely your PLAN-124 (`aggregate-cost-invisible-to-per-call-ceiling`) — three artifacts, three answers

- **Three artifacts disagree about one plan's token cost, and one labels a phase sum as the plan
  total.** On another run `metrics.md` understated tokens **2.7×**.
- **Three token-accounting artifacts each stop recording at a different time, and none says so.**
- `execution.toon`'s `execution_log` **silently stops recording after a loop-back**.

⭐ The common shape across all three: **a truncated record that does not declare its own truncation.**
That is the same rule as the footprint zero above — an artifact must state the boundary of what it
observed.

## Likely your PLAN-126 (`auditor-detector-integrity`) — three

- **`record-dispatch-boundary` accepts 11 termination causes, documents 6, and the detector counts 2.**
  Three different populations for one vocabulary.
- **`compile-report` renders 13 script-failure findings as 13 empty bullets** — the findings exist,
  the report shows nothing.
- **`compile-report` calls a lost section a benign omission and an empty section written** — two
  distinct failures both reported as success.

## Method note you may want regardless

**A population-derivation predicate needed three refinements before it was sound**, and its final zero
is *"a discipline property, not a structural one"* — 661 call sites examined, 0 currently affected,
but 28 of 41 relevant sites sit at `execution_mode='auto'`, so the population is one un-stubbed
sibling away from being non-zero. ⭐ Worth carrying into any detector you derive: **the census script
is the durable deliverable; the number it prints today is not.**

---

## What we kept

Not forwarded — ours as behaviour/contract signals: the `absent`-conflation taxonomy defect (folded
into our PLAN-116 as Defect F), the two further `architecture-refresh` roster sightings (our PLAN-113
D5a — **note one reports a live dispatch-audit violation, so the roster contradiction has a runtime
consequence, which may matter to your PLAN-121**), the `worktree-remove` 60s ceiling and the
`detect-artifacts` data-loss path (our PLAN-201), the stale-spec-premise and async-read lessons, and
the build-wrapper `duration_seconds: 0` masking a real timeout.

## No reply needed unless you disagree

If any of these is not yours, say so and we will take it back. Nothing on our side is blocked on it.
