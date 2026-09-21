# Landing: PLAN-PR-006 — Canned no-op indistinguishable from a review

epic: review-apparatus · workstream: WS-01 · shipped 2026-08-11
cloud run: `cloud-runs/040-canned-no-op-indistinguishable-from-a-review/`
PR #1165 (`fd292004b`)

> Landing analysis over the cloud-wave corpus. `report-01.md` is the run's claim; `verification.md`
> is ground truth. Where they disagree, verification wins.

**Verification verdict: `verified-with-gaps`.**

## What landed

The **classifier half** is real: the three-valued `rate_limit_class` no longer folds `unknown` into
`refused_hard`; `compose_review_state_summary` puts a state distribution on the envelope;
`assess_deficit` exists with the right baseline vocabulary; and the counting rule is written once in
`bot-participation-contract.md` with all three populations published and consumed by the code. D4's
tests are genuinely discriminating — a naive count-only mutant fails 5 of the 9 `TestDeficitSignal`
tests, both load-bearing negatives among them.

**What did not land is the half the plan's title is about — the signal reaching a reader.**

**Deliverables: 5 — 2 done (D1, D4), 3 partial (D0, D2, D3).**

| D | Outcome | What is missing |
|---|---------|-----------------|
| D0 | partial | The "absence corpus **partitioned by cause**" clause was answered with a derivability argument, not a partition. No corpus measured, no diff size recovered from any merge commit. |
| D2 | partial | Nothing in `marketplace/`, `.claude/` or any finalize step invokes `review_completeness deficit`; `_emit_deficit_toon` prints its populations only when non-empty, so `clean` renders with no row for a required reviewer that refused, and `unassessable` renders with no population line at all. |
| D3 | partial | Surface 1 met and tested; surface 2 unmet in the shipped workflow. `finalize-step-review-retrospective/SKILL.md:151-155` records that no persisted reviewed-at-all handoff reaches the step. |

## ⛔ A capability with no caller is not a deliverable

`assess_deficit` is correct, tested and mutation-verified — and invoked by nothing.
`bot-participation-contract.md`'s § "Consumers" table lists it, but that table describes what a command
*reads*, not who runs it. **Reading a Consumers row as proof of a caller is a trap this epic has now
fallen into once.**

## Report claims the verification found false

- `see "Out of this plan (split)"` — **no such section exists** in `report-01.md`. The deferred
  pre-filter remedy therefore reached no § Residue and nothing carries it forward. (Re-verified
  first-party: 11 headings, none of them that one; one dangling reference at line 26.)
- "eight documentation-drift instances" — the sites are **nine locations in seven files**. The tally
  counts neither.
- "D3 — (both surfaces)" — overstated; the *string* collapse D3 names is still live.
- "with the default-empty `required_bots`, `participation_complete` is vacuously true" — overstated;
  this repository configures `required_bots: pr-agent`, so that is not the mechanism in force.
- D4's fail-pre-fix proof ("new symbols AttributeError against pre-fix code") is true of any new
  symbol and therefore non-discriminating; the verification performed the missing mutation probe.

## Gaps: 16 — 13 full, 3 partial, 0 uncovered

- **partial**: G10 (PLAN-PR-026's D4 worked example is **character-for-substance the string G10
  forbids**, and its Done-when drops the `bot_lists_provenance` clause), G13 (positive-validation
  remedy recorded as a proposal only — see below), G15 (`min_deficit` default recorded as a proposal,
  where the gap requires it changed *or defended in the contract with a pinning test*)

**`040 G13` is the one with real blast radius** and is the seed of a new plan: the refusal pre-filter
*enumerates* rather than positively validating, so when **neither** recognition layer fires a reworded
vendor notice is filed as an ordinary finding. PLAN-PR-025 D2 touches the same function but only
records drift when the two layers *disagree* — it cannot see the case where neither fires. PR-Agent
declares zero refusal patterns, so the registry layer can never fire for it at all.

## Standing facts

- ⭐⭐ **A test that drives the library is not a test of the pipeline — this epic has paid for it twice
  on one seam.** 040's D3 and 050's `comparison` grade both shipped green with explicit discrimination
  tests, and both surfaces still collapse in production, because each test hands `aggregate()` the
  reviewed-at-all set the workflow cannot supply.
- ⭐⭐ **One missing handoff produces two independent false-green surfaces.** `check_completeness`
  computes the classification, `automatic-review` reads it in-process, and **nothing persists
  `bot_states`**. That single absence is the shared cause of `040 G1`, `040 G6`, `050 G2` and `050 G3`.
- ⛔ **"The mechanism exists" is not "the measurement exists".** D0 was a HALT gate on partitioning the
  absence corpus by cause; the run argued the registry *supports* the partition and passed itself.
- ⚠ **`.plan/marshal.json` IS git-tracked** (`.gitignore` carries `!.plan/marshal.json`), contradicting
  this run's `verification.md` § Method. A cloud clone *can* read this repository's `required_bots`.
  It does **not** generalise: a consumer project without the negation has no such path.
