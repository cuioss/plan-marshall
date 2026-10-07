envelope_version=1
sender_type=plan
sender_id=disjointness-gate-reads-declared-surface-wrong
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T10:43:35Z

component=plan-marshall:workflow-integration-github
category=bug
source_plan=disjointness-gate-reads-declared-surface-wrong
source_pr=1366

# A review-bot refusal is treated as review evidence at three separate call sites, and the record it leaves suppresses its own cure

## What happened

On PR #1366 iteration 3, CodeRabbit posted a `Review rate limited` notice — an
explicit statement that it did **not** review the HEAD. Three independent call sites
in `workflow-integration-github` each read that notice as evidence that a review
occurred. The three are findings `fffb89`, `942346` and `071a67`; they are ONE
defect with one root cause, not three.

**1. The completion detector counted the refusal as completion (`fffb89`).**
`github_re_review` returned `matched: true` with `matched_signal: issue_comment`
where the matched comment body IS the refusal notice — the refusal counted as the
completion signal it is the opposite of. `refusal_detected: true` fired
concurrently, but against a *different* comment (the `Review Change Stack` summary,
itself a false positive), so the two signals never coincided on one comment and the
contract's requirement that both reject a refusal notice was never exercised. The
`enumerative_unrecognised` arm that should have caught this did not fire.

**2. The fetcher stored the refusal as a triageable finding (`942346`).**
`fetch_findings` reported `count_skipped_refusal: 2` and *still* stored the notice as
pending `pr-comment` finding `60ef34`. The refusal-skip path and the store path
disagree about the same comment, so unified triage was handed the string
`Review rate limited` as if it were reviewer feedback — a finding with no defect
behind it, costing a disposition and inflating the reviewed-comment count.

**3. That stored row then suppressed the re-review that would have cured it (`071a67`, severity `error`).**
The closed loop:

1. trigger B selects the newest bot-authored `pr-comment` finding and compares its
   `reviewed_commit_sha` to HEAD;
2. the newest such finding was `60ef34` — the refusal notice from (2);
3. `reviewed_commit_sha` is stamped from the **fetch-time** head, so `60ef34` carries
   `e60da719c`, the current HEAD;
4. the comparison reads `head_sha == reviewed_commit_sha`, concludes HEAD has not
   advanced, and **skips the re-review**.

So a comment saying in as many words "I did not review this" is recorded as having
reviewed the current HEAD, and that record suppresses the re-review that would fix
it. `re_review_on_loopback` was `true` and trigger B still did not fire.

## Why it matters

This is the plan's own subject inside the machinery that reviews the plan: a
**could-not-look** outcome (the bot declined) rendering as a **clean look** (the bot
reviewed). It is worse than the sibling instances already filed, because here the
false-clean record is *load-bearing* — it does not merely mis-report, it closes the
path to correction. The failure is also self-concealing: every downstream consumer
reading `matched`, the finding store, or `reviewed_commit_sha` sees a reviewed HEAD.

The three sites share one missing predicate: **nothing carries "this bot declined to
review" forward as a first-class state.** Each site independently re-derives
participation from an artefact (a matched comment, a stored row, a stamped sha) that
a refusal also produces.

## Rule

A refusal is not a review, and it must not be representable as one. Specifically:

1. **Never let a refusal notice become a stored finding.** A skip decision
   (`count_skipped_refusal`) and the store path must consume ONE classification of a
   comment, not two.
2. **Never derive "reviewed" from the presence of a comment.** Participation must be
   established by a positive review signal, with refusal as an explicit third state —
   not by absence-of-refusal on a possibly-different comment.
3. **Never let a record whose provenance is "assumed" gate a corrective action.** A
   trigger that decides whether to re-review must not read a sha the pipeline
   stamped itself.

## Remedy shape

Classify each comment once, at ingestion, into `review` / `refusal` /
`unrecognised`, and carry that classification on the row. Make trigger B ignore rows
whose class is not `review`. See sibling finding `6742d8` for the stamp-provenance
half of (3) — same component, distinct defect.

## Status

All three findings are `pending` at landing; none was fixed in-run.
