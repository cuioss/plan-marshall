# PLAN-PR-053: The ledger records WHEN WE LOOKED, and every consumer reads it as WHAT WAS REVIEWED

> ⛔⛔ **SUPERSEDED 2026-09-12 by `PLAN-PR-058` — do NOT emit this spec.** Its queue row is retired
> under the operator's decision to raise the split guard to 12 deliverables and group staged work by
> shared target surface; D1, D1a, D2, D3 and D4 are carried there as D1–D5 and D0 folds into that
> plan's merged D0 gate. ⛔ **This file is NOT dead and is NOT deleted**: it remains the AUTHORITATIVE
> TEXT of every deliverable body, and `PLAN-PR-058` points here rather than retyping it.

epic: review-apparatus
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Drained 2026-09-07 from inbox `-001` and `-002` (both `candidate-lesson`), filed first-party by
> `arm-the-refusal-recovery-that-has-never-run` about **its own finalize**, and corroborated in
> `landings/PLAN-PR-025B.md`. The two are staged together because they are **one defect and its
> substrate**, and fixing either alone leaves the failure reachable.

## Objective

Make the participation ledger record which commit a review **covered**, and make a zero finding-fetch
mean **not reviewed** rather than **reviewed and clean**.

## Why this outranks its individual severities

**A plan shipping guards against this exact archetype reproduced it in its own finalize, and merged on
it.** The run stated *"CodeRabbit round 4 came back clean"* for `1af15958`; CodeRabbit's last completed
review covered only `d75ded9e`. It was caught by `finalize-step-review-retrospective` **after the
merge** — and the delta it hid contained a **Major**: `parse_toon` deleting the first character of a
shallow-indented block-scalar payload, **character-level corruption of the shared TOON transport,
reported by nothing.**

⛔⛔ **The consumer defect (D1) and the producer defect (D2) are separately sufficient to cause the
false-clean call.** A plan that fixes only the read side ships a guard over a field that is still lying.

## Problem

**1 — A `count_stored: 0` finding-fetch is read as *reviewed and clean*.** It means only *this fetch
stored nothing*, which is equally the signature of *the fetch never reached a review*. In the observed
run a **fresh `cause=quota` refusal was dismissed as a known stale comment** in the same pass, so both
available signals that no review had happened were read as confirmations that one had.

⭐ This is PLAN-PR-026's `nobody-reviewed`-vs-`reviewed-clean` collapse **at the fetch layer**. PR-026
owns the per-bot signal and (via D3a) the quorum layer; this is the third layer and the one that feeds
both.

**2 — `reviewed_commit_sha` is RE-STAMPED AT FETCH TIME.** The plan's own artifact carries one comment
under **three different shas** (`IC_kwDOQ3xasM8AAAABS4ng4A`) and another under **two**
(`PRRC_kwDOQ3xasM7rTFi6`). A comment does not change what it reviewed; the field changed because the
**fetch** ran again.

⛔⛔ **Every consumer reads that field as *which commit this review covered*. It is in fact *which
commit was HEAD when we last fetched*.** The two coincide only when the fetch runs inside a covered
window — which is exactly what a refused window is not.

⭐⭐ **This settles a standing operational warning into a located producer defect.** This ledger has
carried, in prose, *"never run the producer FIND during a refused window — it falsely stamps
`reviewed_commit_sha`"*. That warning was a workaround for this bug, and it can be retired once the
field means what its name says.

## Deliverables

**D0 — GATE, mutates nothing.** Re-ground both claims at HEAD. For D2, **derive** the set of write
sites that assign `reviewed_commit_sha` and publish that population — an enumeration, not a sample;
a fix aimed at one of several writers leaves the field lying from the others. **HALT and report** if
the field already carries provenance semantics at HEAD.

**D1 — A zero fetch reports WHICH zero it is.** `count_stored: 0` resolves to one of *no review has
covered this head* / *a review covered this head and found nothing* / *the fetch could not reach a
review* — three states, three distinct verdicts, never one. ⛔ **The refusal signal is an input to this
decision, not a separate stream a reader may discount**: a fresh `cause=quota` refusal in the same pass
must make *reviewed-and-clean* unreachable. *Done when:* a test drives all three states through the
same call and pins that they render differently.

**D1a — THE DISCRIMINATION ALREADY EXISTS; NOTHING PERSISTS IT.** ⭐⭐⭐ **Folded from
`test-suite-anti-vacuity-003` on 2026-09-08** — surfaced by `finalize-step-review-retrospective` on
PR #1443. **This changes D1 from *invent a discrimination* to *persist the one already computed*, and
it makes D1 substantially smaller.**

`review_completeness` **emits `bot_states` during `automatic-review`** — `participated` /
`participated_but_empty` / `participated_stale` / `refused_structural` / `absent`. ⛔ **Nothing
persists them.**

A step ordered after the merge can read only the `pr-comment` findings store, **which by construction
holds records for reviewers that PRODUCED FINDINGS.** ⇒ a reviewer that participated and found
nothing, a reviewer that refused outright, and a reviewer that was never asked are **all
indistinguishable to every post-merge consumer.**

⭐⭐ **This is the substrate under two observations already recorded in this epic**: PLAN-PR-036's
`review-retrospective` returning `indeterminate` with `reviewer_coverage: 0/3` over an empty store, and
PLAN-PR-042's *"1 measured, 2 unmeasurable"*. Neither was a measurement bug — **the states were
computed and thrown away.**

*Done when:* `bot_states` is persisted alongside the findings store at the moment `automatic-review`
computes it, D1's three-way verdict is **derived from that persisted record rather than re-inferred**,
and a post-merge consumer can distinguish all five states. ⛔ **Do not build a second discrimination
beside the existing one** — that is how two producers come to disagree, which is the defect class this
epic keeps finding.

**D2 — `reviewed_commit_sha` records COVERAGE, not observation.** Split the two facts: the commit a
review covered (immutable once written, sourced from the review's own `coveredCommitId` where the bot
publishes one) and the head at which we last observed it (free to move). ⛔ **Never overwrite the
first with the second.** *Done when:* re-running a fetch at a new head leaves every existing row's
coverage sha unchanged, pinned by a test that fetches twice across a head change and asserts the
coverage column is stable while the observation column moves.

⭐ **SECOND-REPO SIGHTING, folded 2026-09-11 from `truthful-signals-054.md` item 1(c)** (relayed,
API-Sheriff `-002`). A CodeRabbit clean review — *"No actionable comments were generated"* with
`coveredCommitId == HEAD` — read as **never-reviewed**. Re-read first-party at `356973d80`:
`coveredCommitId` occurs in **zero** files under `marketplace/`, and `cmd_bot_completion` reads only
`gh pr checks` (`--json name,state,bucket`). ⇒ The covered-commit fact this deliverable sources from is
**not read anywhere today** — D2 adds the first reader, it does not re-route an existing one. ⚠ The
clean-review *shape* is the subject of `PLAN-PR-046` (launched, not foldable); whatever that plan leaves
of the `coveredCommitId` half lands here. Adds no file surface (`github_pr.py` already declared).

**D3 — Retire the workaround the bug required.** Once D2 lands, the standing *"do not run the producer
FIND during a refused window"* rule is obsolete. *Done when:* the rule is removed from the operator
guidance it appears in **and** a test proves a fetch during a refused window no longer corrupts the
coverage field — ⛔ **the removal and the proof land together, or neither does.**

**D4 — Make the post-merge catch a pre-merge one.** `finalize-step-review-retrospective` caught this,
after the merge. Whatever check it performed runs **before** the merge barrier. *Done when:* the
coverage-vs-head comparison the retrospective makes is available to the barrier, and a run whose
review does not cover HEAD cannot pass it without an explicit, recorded override.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-merge-barrier.md`
- OBSERVED: `test/plan-marshall/workflow-integration-github/`
- OBSERVED: `test/plan-marshall/manage-findings/`
- OBSERVED: `test/plan-marshall/automatic-review/`

## Claim Labels

- OBSERVED: the run stated "CodeRabbit round 4 came back clean" for `1af15958` while CodeRabbit's last
  completed review covered only `d75ded9e`.
- OBSERVED: comment `IC_kwDOQ3xasM8AAAABS4ng4A` appears in the plan's artifact under three distinct
  `reviewed_commit_sha` values; `PRRC_kwDOQ3xasM7rTFi6` under two.
- OBSERVED: a fresh `cause=quota` refusal was dismissed as a known stale comment in the same pass.
- OBSERVED: the unreviewed delta contained a Major (`parse_toon` first-character truncation) that no
  in-house gate reported; fixed post-merge in #1441.
- HYPOTHESIS: `reviewed_commit_sha` has **more than one** write site — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
  § its `reviewed_commit_sha` assignments (verify-at-outline). ⛔ **D0 DERIVES the population rather
  than sampling it**; a single-writer assumption is the exact shape that would let this ship half-fixed.
- HYPOTHESIS: the pre-merge barrier has no coverage-vs-head comparison of its own — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-merge-barrier.md`
  (verify-at-outline). ⛔ An **absence** claim, verified as such.

## Dependencies and Sequencing

- Depends on: none.
- ⛔ **Overlaps `PLAN-PR-026`, `-043`, `-045`, `-046`, `-047`, `-048`, `-051`, `-052`** on the
  `automatic-review` / `workflow-integration-github` surfaces — **sequence, never pair.**
- ⭐ **`PLAN-PR-045`** (*a bot that never gets currency tested is credited on a superseded review*) is
  the closest neighbour and they are **complementary, not duplicates**: PR-045 asks *was the currency
  test applied to this bot at all*; this asks *is the field the test reads even telling the truth*.
  D2 here is a precondition for PR-045's remedy to mean anything. **If both are staged, land this one
  first.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-053-the-ledger-records-when-we-looked-not-what-was-reviewed.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
