envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=review-apparatus
kind=finding
created=2026-08-26T21:13:53Z

# Review-bot participation and reliability

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule — the PR/review test wins outright.

**Cluster:** 8 lessons. ⚠ Past the scope-bloat guard; yours to split. **Suggested fold
target:** `PLAN-PR-005/006/007/013` held bot participation at the last drain.

## ⛔ Read this before staging anything

`2026-08-26-05-004` records the strongest reviewer-comparison datapoint in the corpus and it
argues **against** the obvious plan:

> **The in-house self-review gate found 5 real defects; the entire external bot set found 0,
> on the same diff at the same time.**

Of three configured reviewers: **one returned empty, one refused, one refused for structural
reasons** (diff exceeding a declared ceiling). None produced a measurable review. The PR
merged with green `merge_state` and green CI **while nothing external had reviewed the merge
candidate**.

⛔⛔ **The lesson's own directive: "Do not spend another round on bot charter exhortation.
The failure here is empty/refused/refused-structural, not weak findings — a charter change
addresses none of the three."**

⚠ It is equally explicit about what the datapoint does **not** support: the population of
measurable external reviews on that PR is **zero**, so *no quality claim about the bots is
supportable from it in either direction*. What IS supportable is that the merge barrier let
a PR through with zero measurable external participation.

## The three participation-detection defects

| Lesson | Instance |
|--------|----------|
| `2026-08-26-16-001` | Sourcery rate-limit refusal **credited as participation**: a third budget phrasing matches no `refusal_pattern` and no structural fallback. (Title-only stub.) |
| `2026-08-26-17-001` | pr-agent reports `absent` because its response **outruns `review_bot_buffer_seconds`** and it publishes **no check-run to wait on**. (Title-only stub.) |
| `2026-08-25-07-001` | `review_retrospective._grade_comparison` returns clean on a NON-EMPTY intersection, so **one `participated_but_empty` reviewer grades a 1-of-3-with-two-refusals run identically to 3-of-3-reviewed-clean** — the comparison carries no coverage dimension. (Title-only stub.) |

⭐ These three are the actionable core: each is a specific, named mechanism by which a
non-review is recorded as a review. Together with `26-05-004`'s observation that all three
reviewers were unmeasurable simultaneously while the merge proceeded, they say the barrier's
participation signal is the defect — not the bots' output quality.

## The four contract-shape lessons

| Lesson | Instance |
|--------|----------|
| `2026-08-08-21-001` | **A boolean derived from a fallible read has THREE outcomes and a two-branch `if` folds the third into the `else`** — asserting a definite state on evidence nobody gathered. At the `--not-triggered` site an unreadable return silently asserted *a run exists*, so a silent required bot resolved to `absent` (escalate) instead of being held open. ⛔ It **neutered a deliberate fail-loud guard**: the provider returns a typed `unconfigured` precisely so a caller cannot proceed. ⭐ Second-order rule: **a change that establishes a fail-closed discipline is not thereby compliant with it** — the new call sites such a change adds are exactly where to look. |
| `2026-08-08-21-005` | **A correctness fix has a direction, and the direction has an error budget.** The obvious tightening (filter runs by `pull_requests[].number`) was unsafe: GitHub populates that array unreliably — routinely empty for forks — so a strict filter flips the observable to `not_triggered: true` and **blocks merges** on the common fork case. A narrow false negative traded for a frequent loud block is a regression wearing a fix's clothes. ⭐ Companion: **a field an upstream API populates "usually" is not a key.** |
| `2026-08-08-21-004` | **When a change splits one state into N, the deliverable is N remedies, not N names.** `not_triggered` was split out of `absent` on the justification that the two have opposite remedies — and its remedy shipped as the prose *"generate the trigger event at all"*: no invocation, no outcome recording, no timeout branch. ⛔ Worse than neutral: the reader is now told the previously available action is futile. ⭐ The check is cheap — **grep the new members' remedy prose for an actual invocation.** |
| `2026-08-25-09-015` | **A consumer gated on ONE of two sets a producer reports DISJOINTLY is unreachable, and its test pins the gap.** `classify_bot`'s unreadable-refusal override was gated behind `if bot in refused:`, while the producer reports `refused_bots[]` and `unrecognised_refusal[]` disjointly *by design* — so for the only case the override existed for, the branch was never entered. ⛔ **A test asserted `STATE_ABSENT` on exactly that input: the suite was green BECAUSE OF the defect.** Six review rounds and five reviewers passed over it; round 7 caught it only by reading the classifier **against the producer**. |

## Why the four belong with the three

All four are mechanisms by which **an unreadable or unobserved state becomes a positive
participation claim** — the same failure the three detection defects produce, arriving
through a conditional, a predicate direction, a missing remedy, and a set-membership join
respectively. `2026-08-25-09-015`'s archetype statement generalises the whole cluster:
neither side is wrong in isolation; the defect exists only in the join.

## Read-coverage caveat

⛔ Three rows — `2026-08-26-16-001`, `2026-08-26-17-001`, `2026-08-25-07-001` — are
**title-only stubs**: `add` allocated them, `set-body` never ran, and no body exists. Their
titles are long enough to carry the finding, and that is all this router had. **These are the
three most actionable rows in the cluster**, so re-deriving them at outline against the live
`review_completeness` / `review_retrospective` source is the receiving plan's first job.

## Claim labels

- **OBSERVED** — `26-05-004`'s reviewer comparison (5-0, 0-of-3 measurable, the merge
  proceeding) and the four contract-shape instances with their quoted sites and finding ids.
- **HYPOTHESIS** — the three participation-detection mechanisms, title-derived only.
  Confirm/refute at `workflow-integration-github/scripts/review_completeness.py` §
  `classify_bot` / `refusal_pattern`, and at `review_retrospective._grade_comparison`.
  Verify-at-outline.
- **OBSERVED (negative)** — that no quality claim about the bots follows from `26-05-004`;
  the lesson states this itself and this router did not strengthen it.

⛔ Counts, finding ids and site references are the filing plans' own and were NOT re-derived
here.
