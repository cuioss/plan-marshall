envelope_version=1
sender_type=plan
sender_id=retirement-verdict-cited-a-contradicting-example
epic=truthful-signals
kind=landing
created=2026-08-03T14:31:39Z

# Landing — PLAN-TRUTH-047

spec_id=PLAN-TRUTH-047
runtime_slug=retirement-verdict-cited-a-contradicting-example
pr=1085
merge_sha=4cf3a008f77cd5c1189f8bfc88e5194432391f6f
merge_method=squash-via-github-merge-queue
title=A retirement verdict cited a worked example that contradicts its own clause
companion_message=retirement-verdict-cited-a-contradicting-example-001.md (kind=candidate-lesson, CL-1..CL-10)

> **ID mapping is unchecked at drain.** Spec id `PLAN-TRUTH-047` and runtime slug
> `retirement-verdict-cited-a-contradicting-example` are BOTH recorded above because the
> orchestrator maps `sender_id` -> `spec_id` by hand at every drain with no machine check.
> A message carrying only one identity costs the drain a manual mapping.

## What landed

Merged as `4cf3a008f77cd5c1189f8bfc88e5194432391f6f` (PR #1085), squash via the GitHub merge queue.
6/6 tasks, 4 deliverables (request D0-D5 mapped down to 4), 3 substantive commits.

Landed surface:

- `manage-lessons remove` gains a **REQUIRED** `--coverage-verdict`, with `--covering-clause` /
  `--covering-input` required for the `completely_covered` verdict.
- New `worked_example_pairs` candidate class + **rule 19** + **check 15** in
  `pm-plugin-development:ext-self-review-plan-marshall`.
- New `scan-worked-examples` verb.
- 3 OWED lesson trims applied.

⭐ **The merge was verified from `git log origin/main`, NOT from the merge call's return.** The
enqueue return said `enqueued:true` while `pr view` still reported the PR open. The oracle alone
would have been a false-green. **This is the SECOND corroboration of the standing
`ci pr merge` lies rule** — treat the enqueue return as a request receipt, never as a landing fact,
and stamp PR ids from PR state.

## Headline — theme: confident-signal-hides-a-caveat

### 1. ⭐⭐ The plan's central hypothesis was REFUTED — and that is the run's best output

The D0 sweep covered **359 distinct standards files** (6 pair-bearing, **34 GOOD/BAD pairs
adjudicated**, 30 of them unadjudicable) and returned **ZERO** contradicting worked examples.

The spec's stated hypothesis — that the 2 known defects were a *sample* of a larger population — is
**refuted**. Both motivating defects were already fixed on main in `de00dca9b` **before this plan
started**. The **published denominator is precisely what makes that zero a finding rather than a
vacuous pass**; a zero without one is indistinguishable from an empty population.

### 2. ⭐⭐ The plan reproduced its own target archetype (3rd recorded instance)

Its own new **rule-19 prose** claimed an empty `worked_example_pairs` list proves "every adjudicable
pair agrees" — contradicted by a line **26 lines later IN THE SAME FILE** stating that a zero
without a published denominator is indistinguishable from an empty population.

**Measured:** the surface returned **0** while **30 of 34 pairs were unadjudicated.** Caught only by
`pre-submission-self-review`; fixed in-branch as `16974c7aa`.

### 3. ⛔⛔ The pre-merge comment barrier FAILED OPEN (finding `ed4b4a`)

Configured `fail_into_loopback`. The work.log sequence:

| Log time | Event |
|----------|-------|
| 13:41:01 | `ci.py` exit **2** — unrecognized `--pr-number` |
| 13:42:59 | `github_pr.py` exit **2** — unrecognized `--enabled-bots` |
| 13:43:32 | "barrier clean, 0 findings" |

**A hard argparse rejection became a zero count became merge clearance in 33 seconds, with no
successful fetch anywhere in the window.** Root cause chains to the plugin-pin violation below:
`--enabled-bots` is the `0.1.1240` flag while the pin was `0.1.1288`.

### 4. ⛔⛔ Review-apparatus: opposite verdicts, one forwarded to the operator AS FACT

**(finding `b2f0e9` — ALREADY DELEGATED to the `review-apparatus` epic by plan-retrospective;
recorded here as a pointer only. NOT in this epic's ledger, do not re-file.)**

Two dispatches produced **opposite, both-wrong** participation verdicts. The orchestrator forwarded
one to the **OPERATOR AS FACT** at the pre-merge consent gate, stating 2-of-3 bots reviewed clean
when the truth was **1-of-3**.

- Only **pr-agent** actually reviewed, and minimally.
- **coderabbit was RATE-LIMITED** — its Walkthrough is pre-review intake, **not a review**.
- **sourcery hard-refused** on the 150k diff-char cap.

⛔ **#1085 is UNDER-REVIEWED — a post-merge PR revisit is owed.**

### 5. ⛔ Plugin pin violation — incidents 7, 8 AND 9 in one run

`automatic-review` and `plan-retrospective` both announced `0.1.1240` against a `0.1.1288` pin
(incidents 7 and 8). **This `lessons-capture` dispatch is incident 9** — the persona skill again
announced `0.1.1240` against the same `0.1.1288` pin, self-observed at load.

Remedy used in all cases: **`Read` the pinned SKILL.md directly** instead of restarting. Three
incidents inside a single plan run is the highest density recorded so far.

### 6. ⛔ Tool-capability deadlock, resolved by RE-SEQUENCING

The 359-file sweep had **no available primitive**: `Grep` absent from both the leaf and main, Bash
`grep` hook-blocked, `architecture find` path-only.

Resolved by **building the detector first, then running it as the enumeration primitive**. This is
**strictly better than the planned order** — the count became a reproducible script artifact instead
of a hand count. Worth promoting as a pattern, not just recording as a workaround.

### 7. ⛔ Merge mutex was force-released under operator authorization

Held by `content-search-seam` (**PLAN-CIS-001**, paused mid-finalize) with `staleness=fresh` — so
**NOT auto-reclaimable, and it would never have self-released**. The operator authorized an explicit
release.

⭐ **The epic should know that plan's lock was taken.** `content-search-seam` remains paused and
re-acquires normally on its next finalize entry; no action is owed from it.

### 8. ⛔ `references.affected_files` ABSENT entirely — three consumers hit it

`plugin-doctor`, `pre-push-quality-gate`, and `check-artifact-consistency` all hit the missing key.
This is the known under-recording defect, **now worse: the field is missing outright, not merely
under-populated.** All three degraded safely only because each happened to carry a fallback branch —
a consumer without one under-scopes silently.

### 9. Dispatch instrumentation under-reports by >=35%

**11** `[DISPATCH]` lines against **>=17** envelopes that provably ran. `branch-cleanup` — which
holds the merge mutex, **performs the merge**, and prunes the branch — is **entirely absent from the
dispatch trail**.

## ⭐ NEW, first-party at this dispatch: a count whose UNIT differs from the enumeration seam's

Observed while checking the inbox before writing this message — an on-theme instance the drain
should see:

- `plan-retrospective`'s `mark-step-done` display_detail reads
  **"10 candidate-lesson(s) -> epic truthful-signals, 1 -> review-apparatus"**.
- `orchestrator inbox list --slug truthful-signals` reports **`count: 1`**, `invalid_count: 0`.

**Nothing was lost.** The 10 candidates (CL-1..CL-10) are **bundled into the single message**
`retirement-verdict-cited-a-contradicting-example-001.md`. The display_detail counts **candidates**
while the enumeration seam counts **messages**, and the two units are never reconciled.

Two consequences for the epic:

1. **Granularity invariant violated.** `inbox-envelope.md` specifies *"one message per emitted
   item — that is what the sequence exists to allocate"*, and `lessons-capture.md` § Orchestrated
   emission contract repeats it as *"One `kind: candidate-lesson` message per candidate."* Ten
   candidates arrived as one message, so the sequence allocated one number for ten items and the
   drain cannot archive them independently.
2. **The 10-vs-1 gap reads as data loss until the body is opened.** A drain trusting either number
   alone draws a wrong conclusion — 10 says nine messages are missing, 1 says nine candidates were
   never produced. Both are false. **This near-miss is itself the theme:** the honest report required
   opening the payload, because no count on either side disclosed its own unit.

## Residue the epic should track

| # | Item | Owner |
|---|------|-------|
| R1 | **Post-merge PR revisit for #1085** — under-reviewed (1-of-3 bots, minimally) | `truthful-signals` (review quality delegated to `review-apparatus`) |
| R2 | Pre-merge comment barrier fails open on argparse rejection (`ed4b4a`) | `truthful-signals` — **highest severity here**; a merge gate that clears on exit 2 |
| R3 | Plugin-pin gap is an **upstream producer of false gate signals**, not a doc nuisance | `truthful-signals` |
| R4 | Candidate-lesson message granularity + count-unit mismatch (section above) | `truthful-signals` |
| R5 | `references.affected_files` absent — 3 consumers | `truthful-signals` |
| R6 | Dispatch instrumentation under-reports >=35%; `branch-cleanup` untraced | `truthful-signals` |
| R7 | CL-6 (`metrics.md` 4-of-6 subtotal labelled "Total") is a **SUSPECTED DUPLICATE** of PLAN-TRUTH-035 | **Dedup before filing** |
| R8 | `content-search-seam` (PLAN-CIS-001) merge mutex was force-released; that plan stays paused | Informational — no action owed |

## Drain notes

1. The companion **`kind=candidate-lesson`** message `-001` carries CL-1..CL-10 with full bodies.
   This landing does **not** restate them — read both together.
2. **CL-2 is delegated**, not filed here: it lives in the `review-apparatus` inbox as
   `retirement-verdict-cited-a-contradicting-example-001.md` (`kind=finding`). Per the three-way
   routing rule it is REMOVED from this epic's ledger.
3. **R7 requires a dedup decision before any lesson is filed** from CL-6.
4. This run made **zero** `manage-lessons add` and **zero** `architecture enrich` calls
   (`orchestrated: true` -> Branch B4). All lesson-shaped output routed here.
