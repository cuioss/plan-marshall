# Landing — PLAN-TRUTH-047 `retirement-verdict-cited-a-contradicting-example`

**PR #1085** MERGED 2026-08-03T13:54:33Z, squash `4cf3a008f` via the merge queue. 4/4 deliverables,
6/6 tasks. **4.3M tokens / 4h42m worked / 7h36m wall.** Verified first-party via `gh pr view`.

**Shipped**: `manage-lessons remove` now **requires** `--coverage-verdict`, plus `--covering-clause` /
`--covering-input` for `completely_covered` — a **deliberate breaking change** with all in-repo call
sites migrated. New `worked_example_pairs` candidate class (rule 19 / check 15) and a
`scan-worked-examples` verb in `ext-self-review`. ✅ **The three OWED lesson trims applied with the
keep-list intact.**

## ⭐⭐ The headline is a REFUTATION — of MY hypothesis — and it is the run's best output

D0 swept **359 distinct standards files** (6 pair-bearing, **34 GOOD/BAD pairs adjudicated**) and found
**ZERO** contradicting worked examples.

⛔ **My spec asserted the opposite**: *"two of the handful of clauses shipped in one PR were already
wrong, so the base rate is NOT low."* **It is low. It is zero.** Both motivating defects were **already
fixed on main in `de00dca9b` before this plan started.**

⭐⭐ **And `de00dca9b` is a SHA this epic already knows**: it is the exact commit `PLAN-TRUTH-046`
identified as the bogus `main_sha` — *"docs(ref-code-quality): fix self-contradicting GOOD examples in
error-handling"*, landed via #1082. ⇒ **`PLAN-TRUTH-010` had already fixed both defects a day before I
staged a plan premised on their being live.**

⛔ **I had the disproving fact.** Inbox `-015`, which I read and quoted into the spec, said *"the example
was corrected in the same PR before the retirement was re-applied."* **I wrote it into the spec and then
built a base-rate claim on top of it anyway.**

✅ **What worked is the discipline, and it is worth stating plainly**: the spec labelled it
**HYPOTHESIS**, with *"assembled from one external reviewer's single pass — that is a SAMPLE, not an
enumeration. D0 exists to replace it."* ⇒ **D0 replaced it, and the plan's most valuable output is the
refutation of its own premise.** That is the claim-labelling contract paying for itself. **The error was
mine; the guard against it was also mine, and it held.**

⭐ **The published denominator is what makes the zero a finding rather than a vacuous pass** — 359 files,
34 pairs. A zero without a denominator is indistinguishable from an empty population.

## ⛔⛔ A FALSE FACT WAS PUT IN FRONT OF THE OPERATOR AT THE CONSENT GATE

Two dispatches produced **opposite, both-wrong** participation verdicts, and one was forwarded **to the
operator as fact**: *"2 of 3 bots reviewed clean."*

| Bot | Truth |
|---|---|
| pr-agent | reviewed — **minimally**, the only real review |
| **coderabbit** | ⛔ **RATE-LIMITED, never started.** Its Walkthrough is **pre-review intake, not a review** |
| sourcery | ⛔ **hard-refused** on the 150k diff-char cap |

⇒ **True coverage was 1 of 3. The operator consented against a picture that did not exist.**

⭐⭐ **Third instance in three days of the same class**: *a comment FROM a bot is not a review BY it*, and
*a summary of a review is not the review*. ⛔ **This one is the most serious, because the artifact was
used to obtain consent** rather than merely to inform a ledger.

⇒ **`#1085` is UNDER-REVIEWED and a post-merge revisit is OWED.** Delegated as finding `b2f0e9` to
`review-apparatus` — **pointer only, not in this ledger.**

## ⛔⛔ The pre-merge barrier failed open — 33 seconds from two hard rejections to merge clearance

| Log time | Event |
|---|---|
| 13:41:01 | `ci.py` exit **2** — unrecognized `--pr-number` |
| 13:42:59 | `github_pr.py` exit **2** — unrecognized `--enabled-bots` |
| 13:43:32 | **"barrier clean, 0 findings"** |

**Configured `fail_into_loopback`. A hard argparse rejection became a zero count became merge clearance,
with no successful fetch anywhere in the window.** Delegated as `CL-2` to `review-apparatus`.

## ⛔⛔ ROOT-CAUSE UPGRADE — a plugin-pin gap is an upstream producer of FALSE MERGE-GATE SIGNALS

`--enabled-bots` is the **`0.1.1240`** flag; the pin was **`0.1.1288`**. ⇒ **The barrier's second
rejection was caused by the pin gap.**

⛔ **This re-scopes a withdrawal of mine.** `PLAN-TRUTH-012` records the `--enabled-bots` incident as
RETRACTED — *"the two subagents read a stale plugin cache and invoked a retired flag"* — and re-aimed it
at `PLAN-TRUTH-008`. ⭐ **That withdrawal was correct about the DOC and mis-scoped the DAMAGE.** The
stale read did not merely produce a wrong doc finding; **it produced the flag that made a merge gate
report clean.**

⇒ **The pin defect is not a developer-machine nuisance. It manufactures false green at the merge
boundary.** Recorded at the top of the pin memory.

**Incidents 7, 8 and 9 all fired inside this ONE run** (`automatic-review`, `plan-retrospective`, and
`lessons-capture` — the last self-observed at load). **Highest density recorded.** Remedy used in all
three: `Read` the pinned `SKILL.md` directly rather than restarting.

## ⭐⭐ A methodological WIN worth promoting, not just recording

The 359-file sweep had **no available primitive**: `Grep` absent from both leaf and main, Bash `grep`
hook-blocked, `architecture find` path-only.

⇒ Resolved by **building the detector FIRST, then running it as the enumeration primitive.**

⭐ **This is strictly better than the planned order**: the count became **a reproducible script artifact
instead of a hand count** — which is precisely what this epic asks for everywhere else. ⇒ **Promote as a
pattern**: *when a sweep has no primitive, the deliverable that provides one should be sequenced first,
and the sweep becomes its first execution.* ⚠ It also independently motivates `PLAN-CIS-001`
(a dispatched leaf has no content-search seam) — **forwarded to CIS as field evidence.**

## ⭐ The plan reproduced its own target archetype — 3rd recorded instance

Its **own new rule-19 prose** claimed an empty `worked_example_pairs` list proves *"every adjudicable
pair agrees"* — **contradicted 26 lines later in the same file** by the statement that a zero without a
published denominator is indistinguishable from an empty population. **Measured: the surface returned
`0` while 30 of 34 pairs were unadjudicated.** Caught by `pre-submission-self-review`, fixed in-branch
(`16974c7aa`).

## Residue and routing

- **NEW `PLAN-TRUTH-057`** — `references.affected_files` is **absent entirely** (not merely
  under-populated); three finalize consumers hit it and degraded safely **only because each happened to
  carry a fallback**.
- **Folded into `PLAN-TRUTH-032`** — ⛔ **granularity invariant violated**: 10 candidate-lessons arrived
  as **ONE** message, against `inbox-envelope.md`'s *"one message per emitted item"*. The
  `display_detail` counts **candidates** (10) while `inbox list` counts **messages** (1), and **the two
  units are never reconciled** — a drain trusting either number alone concludes wrongly.
- **Folded into `PLAN-TRUTH-045`** — dispatch instrumentation under-reports by **≥35%** (11 `[DISPATCH]`
  lines vs ≥17 envelopes), and ⛔ **`branch-cleanup` — which holds the merge mutex, performs the merge
  and prunes the branch — is entirely absent from the dispatch trail.**
- **Delegated to `review-apparatus`** (pointers only): `b2f0e9` (opposite participation verdicts, one
  forwarded as fact) and `CL-2` (barrier clean from a rejected fetch).
- ⭐ **SECOND corroboration of the `ci pr merge` rule**: the enqueue return said `enqueued: true` while
  `pr view` still reported the PR **open**. **The merge was verified from `git log origin/main`.**
  ⇒ *Treat an enqueue return as a request receipt, never as a landing fact.*
- ⚠ **Merge mutex force-released under operator authorization** — held by `content-search-seam`
  (**PLAN-CIS-001**, paused mid-finalize) at `staleness=fresh`, so it was **not auto-reclaimable and
  would never have self-released**. That plan re-acquires normally; **no action owed from it.** CIS
  notified.
