# Landing: PLAN-PR-012 — Feed PR findings back into local review

epic: review-apparatus · workstream: WS-03 · shipped 2026-08-13
cloud run: `cloud-runs/090-feed-pr-findings-back-into-local-review/`
PR #1204 (`bb9ab4931`)

> Landing analysis over the cloud-wave corpus. `report-01.md` is the run's claim; `verification.md`
> is ground truth. Where they disagree, verification wins.

**Verification verdict: `verified-with-gaps`.**

## What landed

A well-evidenced run whose every in-clone anchor survives scrutiny. D1 is verified anchor-for-anchor;
both new tests exist, pass, and are genuinely discriminating under independent mutation of the real
detector; and the plan's hardest discipline — routing candidates **out** rather than absorbing them —
was followed twice, correctly.

**Deliverables: 4 — 1 done, 3 partial.**

## The weakness is one of justification, not code

The back-feed premise produced **no code at all** from the accepted-finding corpus. The one code change
is the widening the plan itself pre-specified. And the single real count-prose finding the exercise
surfaced (`the eight list flags`) is a shape the widened detector **still cannot see**, because a
modifier separates the number from the noun.

## Report claims the verification found false

- "the flag AND its guard were introduced together in the same squash-merged PR **#1153** … whose
  review threads are empty" — **false as to the PR**. `git log -S'invalid_cap'` returns one commit,
  `010ea461` = PR **#1039**; #1153 touches no `manage-lessons` path. The conclusion survives; the
  corroborating clause was read off an unrelated PR.
- "the widening was DERIVED, not guessed" — population accurate, inference overstated: the added
  member came from the plan's own docstring example, not the distribution. `state` 25, `phase` 24,
  `flag` 20, `column` 16, `member` 13 all outrank `check` at 5 and were never adjudicated.
- "a repo-wide sweep confirmed no other consumer site remained stale" — accurate as scoped, incomplete:
  the `## Tests` coverage index (`ext-self-review-plan-marshall/SKILL.md:379`) is a fifth site.
- D2's and D3's *Done when* clauses were **restated** rather than met. The dispositions were correct
  and plan-sanctioned; the silent restatement is the defect.
- PR #1167's flagged count is **not** still stale — fixed by `064560ab` (#1168) and again by `9e9e9880`
  (#1241). "Unanswered" and "unfixed" are different claims; only the first holds.

## Gaps: 9 — 9 full, 0 partial, 0 uncovered

## ⚠ This run's strongest finding is claimed by nobody

**13 of 43 observed PR findings received no posted answer** (#1167 ×4, #1158 ×2, #1198 ×6, #1195 ×1).
It is recorded as a run-report finding and as residue, **never as a `gaps.md` entry**, so no staged
plan inherits it and it would lapse with the report. Together with this run's other three residue items
— run-report placeholder scan, authoritative-set → doc-prose-list mirror drift, and the disposition-flow
evidence asymmetry (a rejection needs a rationale but never a source) — all four are confirmed OPEN by
the verification and closed by no later plan.

**Carried into the ledger as an Open Defect, and the response-path half staged as PLAN-PR-034.**

## Standing facts

- ⭐ **A "derived" noun set chosen from the plan's own docstring is a vacuous derivation.** The run
  scanned 510 files, published an accurate distribution, and then added the member its example
  suggested — leaving the five higher-frequency candidates unadjudicated. Publishing the population
  and *selecting from* the population are different acts.
