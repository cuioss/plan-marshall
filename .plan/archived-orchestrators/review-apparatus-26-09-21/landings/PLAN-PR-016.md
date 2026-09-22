# Landing — PLAN-PR-016 `correct-review-scores-as-maximally-wrong`

epic: review-apparatus · analysed 2026-08-02 · **PR #1078 MERGED** (verified via `ci pr view`) ·
7 inbox messages

⭐ **Merge observed live during this drain.** #1078 read `state: open, merge_state: clean` at the start
of this ingestion and `state: merged` at its end — its landing message was written **12:57:49Z**, well
before either check. Third confirming instance for the landing-gap defect, and the only one observed
happening rather than reconstructed from timestamps afterwards.

## What landed

The plan paired two defects acting on the SAME comment in opposite directions.

- **D1 — contentless-review classification repaired.** The `contentless_review_markers` predicate that
  identifies boilerplate-only bot output was fixed. Iteration-2 FIND confirmed the pre-fix drop
  originated in the predicate itself, not in dedup (`count_skipped_duplicate: 0`).
- **Participation evidence sidecar (TASK-4).** `_has_update_movement` no longer reads first-presence
  evidence out of the findings store, because the D1 contentless drop removes the comment from exactly
  that store. An observation sidecar now carries the evidence independently of the store's lifecycle.
- **`automatic-review` argparse surface** — now takes `--required-bots` / `--optional-bots` /
  `--participated-bots` / `--in-progress-bots` / `--refused-bots` and returns `participation_complete` /
  `unproven_bots` / `bot_states`.

## ⭐⭐ The D1 root cause — the predicate was DEAD CODE for its entire life

`contentless_review_markers` were declared in **markdown-bold** form (`**PR contains tests**`). PR-Agent
emits **HTML** — `<strong>PR contains tests</strong>` — inside a `<table>`, and GitHub does not render
markdown inside an HTML table. The markers were combined in a **conjunction**, so one non-matching
marker sufficed: **the conjunction never evaluated true and D1 never fired at all.** It did not
misclassify; it was inert.

⛔ **The tests passed throughout, using fixtures in the markdown form no real body carries.** They
pinned the author's belief about the producer's output rather than the producer's actual output. A green
suite was evidence about the fixture, not about PR-Agent.

⇒ This is the epic's `test-pins-the-defect` archetype with an added twist worth carrying: **a
marker/predicate written against a producer's output must be fixture-derived from a CAPTURED body**, not
authored from how the format is assumed to render. Rendered appearance ≠ literal bytes.

## ⭐ The paired-defect thesis was correct — and the pairing was load-bearing

The spec's blocking verify-first clause asked what an EMPTY PR-Agent record produces. The answer turned
out to be the reason the two defects had to ship together: **fixing D1 alone would have silently broken
participation detection.** The findings store was doing double duty as a *mutable work queue* (D1
correctly drops noise from it) and as an *append-only evidence record* (`_has_update_movement` read
first-presence from it). Those two roles have **opposite deletion semantics**. Once the contentless
comment was dropped, `participation_requires_update` became **permanently satisfied** for `pr-agent` —
a bot posting only boilerplate would have read as a fully participating reviewer forever.

⭐ Neither guard was wrong in isolation; the defect lived in the shared substrate. **Staging these as
two independent plans would have shipped the regression.** Recorded as evidence for the pairing rule.

## ⛔ The plan shipped under the exact failure mode it exists to fix

- **coderabbit** — refused (awaitable window)
- **sourcery** — refused (hard quota)
- **pr-agent** — the only bot that saw the diff; **its sole output was boilerplate that this very plan
  now classifies as contentless noise**

The operator explicitly chose to proceed on pr-agent alone — a legitimate call. What is not legitimate
is the residual record: a PR with zero actionable comments from one participating bot and two refusals
is **indistinguishable** from a PR that three bots reviewed and found clean. Both render as "no
outstanding review findings".

⚠ Identical bot pattern to #1077 (same two refusal causes, same lone participant). **Two consecutive
PRs, both merged on one non-substantive reviewer.** That is a coverage regime, not two incidents — and
the per-PR participation count is still the only view that would show it. Feeds PLAN-PR-006 hard.

⭐ **Self-review carried the whole load again**: four passes configured, passes 1–3 **each found a
genuine defect** (3-for-3 — the ceiling was doing real work, not padding). The 4th was waived at the
`max_iterations` ceiling, so the run **terminated on a budget boundary rather than on a clean pass**.
⛔ The clean-pass evidence for this plan is *absent*, not *positive* — do not read "self-review
complete" as "self-review found nothing left".

## Residue KEPT by the epic

1. ⛔ **UNFIXED doc divergence, live in merged main** — `automatic-review/SKILL.md` documents
   `--enabled-bots` / `--settled-bots` and return fields `complete` / `unfetched_bots`; the shipped
   parser takes `--required-bots` / … and returns `participation_complete` / `unproven_bots` /
   `bot_states`. **Every documented invocation is an argparse rejection (exit 2)** and every documented
   return-field read resolves to nothing. Not cosmetic — the two vocabularies model different things.
   ⭐ Same archetype as the `ci pr view --pr-number` drift found this session; see
   `findings/2026-08-02-erroring-poll-reads-as-negative.md`. **Two CLI-vs-doc divergences in the
   review/merge path is a population.**
2. ⛔ **A leaf returned a finding in its TOON and never persisted it.** `pre-submission-self-review`
   pass 3 found a genuine defect, returned it to the caller, and wrote nothing to the qgate store — so
   it existed in transcript, not in state. Nothing downstream (blocking-findings gate, triage, finalize
   summary, retrospective) could see it. It survived only because a human read the TOON in the moment.
   ⭐ The return path and the persistence path are independent and only one is durable: a leaf can be
   fully successful by its own contract while contributing **zero** to the state the pipeline gates on.
   Silent in both directions — nothing errors, and the finding *appears* reported precisely to whoever
   is looking at the evidence.

## Delegated

`004` (a 2-second incremental type-check green is a cache hit, not a verification result — local gate
2–5s vs CI's 660 files and 2 real type errors) → `truthful-signals` msg `review-apparatus-012` item 13.

## Feeds

- **PLAN-PR-006** — two consecutive PRs merged on one non-substantive reviewer; the absent-vs-clean
  representation collapse is now observed twice with identical bot causes.
- **PLAN-PR-004** — ⛔ its Recommendation B measurement was blocked on this landing. **Now unblocked**,
  but re-read it first: the aggregator's `accepted → false_positive` mapping is fixed, so any earlier
  measurement taken against it must be discarded, not adjusted.
- **PLAN-PR-013** — the sidecar establishes that participation evidence must not live in a store with
  work-queue deletion semantics; check whether its own predicate reads from the same substrate.
