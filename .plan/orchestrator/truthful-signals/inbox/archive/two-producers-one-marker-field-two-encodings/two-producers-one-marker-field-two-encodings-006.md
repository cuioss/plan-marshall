envelope_version=1
sender_type=plan
sender_id=two-producers-one-marker-field-two-encodings
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T04:57:54Z

component=plan-marshall:automatic-review
category=bug
confidence=high
source_plan=two-producers-one-marker-field-two-encodings
source_pr=1125
suggested_epic=review-apparatus
delegation_note=All four defects below are PR/review-shaped and belong to review-apparatus under the standing three-way routing rule. Emitted here because a dispatched leaf writes only to the epic it was dispatched under; forward via the inbox channel rather than a direct edit.
consolidates=4 defects from the PR #1125 review pipeline

# Two of three review bots produced real content that never reached the findings store, and three separate mechanisms hid it

## Context

PR #1125 ran four review rounds against four HEADs with three bots enabled. The
`pr-comment` store holds records for exactly one of them. The review-retrospective
step substantiated participation positively from the provider rather than inferring it
from the store, and found that **two of three bots participated with real content that
was lost in transit**. Four distinct defects compound here; they are consolidated
because they share one PR and one blast radius.

## Defect 1 — Sourcery's review body never reached the store (highest value)

Sourcery posted one `COMMENTED` review at `2026-08-09T00:19:45Z` with an Overall
Comments body carrying two substantive observations. Zero records in the store.
Neither was filed, triaged, answered, or actioned. The two observations were:

1. **Hard-coded repo-root depth.** `test_orphan_marker_existence_only.py:79` resolves
   its root as `_REPO_ROOT = Path(__file__).resolve().parents[3]`. This is a live
   recurrence of the `Path(__file__)` archetype this repository was already bitten by
   in #894. Still present in merged `main`.
2. **Duplicated invariant wording.** The `.orphaned_at` invariant text is now repeated
   across several docstrings and markdown files — the source-of-truth-duplication /
   doc-contract-divergence archetype, also tracked here.

Both are on-archetype, and decisively **neither overlaps anything CodeRabbit raised
across four rounds on the same files**. Sourcery had the best signal-to-noise ratio on
the PR (2 observations, 0 noise) and contributed nothing to the run.

## Defect 2 — the participation classifier asserted a negative the evidence refutes

The `automatic-review` force-done record at `01:57:16` classified the bots as
`pr-agent:absent, coderabbit:participated, sourcery:participated_but_empty`.
`sourcery:participated_but_empty` is false — the review contained two observations.
The classifier asserted emptiness for output that was dropped between provider and
store, converting a capture failure into a claim about the reviewer.

## Defect 3 — participation credited on `updated_at` movement, not on the commit-bearing oracle

pr-agent's Reviewer Guide carries its own `"Review updated until commit <sha>"` line —
a first-party, commit-bearing statement of exactly what it reviewed. The detector does
not read it. Participation was credited on `updated_at` movement alone while the Guide
still named the pre-rebase `dd201b00`, producing a stale-participation false positive
that the run caught only because a human-authored pass re-read the Guide body.

*(Sourced from the review-retrospective artifact's first-party reading of the Guide;
the detector's code path was not independently re-verified in this retrospective.)*

## Defect 4 — the CodeRabbit status-summary carve-out is dead code

`_is_coderabbit_status_summary()` matches the signature `"actionable comments posted"`
against the record's `title` and `detail`. In the shape the producer actually stores,
that string is in neither — `title` is `"PR #1125 review_body comment by coderabbitai
(PRR_…)"` and `detail` is the structured metadata block. The signature lives in the
**`body`** field, which the predicate never reads.

Confirmed empirically with a matched positive control against the real `e15cef` record
shape: real record → `_is_coderabbit_status_summary: False`, `_is_actionable: True`;
same record with the signature moved into `detail` → `True` / `False`. Both status
summaries were therefore counted actionable, and CodeRabbit's headline reads 66.7%
where the carve-out would give 100% — a 33.3-point understatement.

The carve-out is documented in the script docstring, in the step's SKILL.md, and in
the `kind_actionability` legend the script emits on every run. All three describe
behaviour that has never occurred.

## Root cause

One shape, four expressions: **a claim about a reviewer is derived from a surface that
does not carry the evidence.** Defect 1 loses the content before the store; defect 2
reports emptiness from the store's silence; defect 3 reads currency off a timestamp
instead of off the commit the bot names; defect 4 reads a signature from fields that
never hold it. In every case the fallback reads as a measurement rather than as a
non-observation.

## Proposed action

- **Defect 1 (highest value)** — find why Sourcery's review body and pr-agent's
  Reviewer Guide never reached the store. Two of three bots are currently invisible to
  every downstream consumer of the `pr-comment` ledger: triage, the merge barrier, and
  the review retrospective.
- **Defect 2** — a bot whose output was not captured must not be classified
  `participated_but_empty`. Emptiness is a claim about content and requires content to
  have been read.
- **Defect 3** — parse the `"Review updated until commit <sha>"` line and compare the
  named sha to the current HEAD. It is the commit-bearing oracle already present in
  the body the detector fetches.
- **Defect 4** — add `body` to the haystack AND pin it with a matched control against a
  real stored record shape. A fix that only widens the haystack is still unobserved.
- **Do not drop any reviewer on the strength of this run.** Sourcery looks worthless in
  the metrics table and in fact produced the only observations no other reviewer made.
  Acting on its apparent silence would remove the best signal-to-noise reviewer on the
  PR — the concrete form of the trap the participation rule exists to prevent.

## Related — the self-inflicted noise half

Four re-review triggers posted by our own machinery produced four mechanical declines
within 10-13s each (CodeRabbit deduplicates on content, not commit sha), generating
36% of the entire ledger. One of them, `7255b6`, was CodeRabbit's reply to the trigger
`branch-cleanup` had just posted; the pre-merge comment barrier found it unhandled and
looped back, and re-entry would have fired the trigger again under a new comment id
that dedup cannot catch. The run recorded the livelock at `03:54:40` and broke it at
both halves (resolving `7255b6`, setting `re_review_on_branch_cleanup=false`) after
verifying the rebase was a no-op (`pre_sha == post_sha == ac58a7b`). A cheap
precondition — skip the trigger when the push did not move HEAD — removes the last two
triggers and the livelock, and the run had already computed the sha comparison it
needs.

## Evidence

- artifact: `review-retrospective.md` (this plan) — §§ Participation beyond the store,
  Producer capture gap, Defect in the deterministic pass, Comparative Verdict
- store: `manage-findings list --type pr-comment` returns 11 records, 10 from
  `coderabbitai` and 1 from the PR author; zero from `sourcery-ai` or
  `cuioss-review-bot`
- first-party: `test_orphan_marker_existence_only.py:79` in merged `main` reads
  `_REPO_ROOT = Path(__file__).resolve().parents[3]`
- log: `[WARNING]` at 03:54:40 recording the livelock; finding `7255b6` resolution
  narrative naming it self-inflicted
- yield by round: rounds 1-2 produced all 4 actionable findings; rounds 3-4 produced
  three bot-action notices and nothing else
