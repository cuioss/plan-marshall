# Landing analysis — PLAN-TRUTH-128

**Plan:** `freshness-gate-says-fresh-unexamined-tree`
**Spec:** `plans/PLAN-TRUTH-128-the-freshness-gate-says-fresh-for-a-tree-it-never-examined.md`
**PR:** #1425 · **Merge commit:** `ef129d6a3` · **Workstream:** WS-01

## Merge corroboration

| Source | Result |
|---|---|
| `git log main` | `ef129d6a3 fix(manage-tasks): stop overloading fresh for the unscanned exempt path (#1425)` |
| `ci pr view --pr-number 1425` | `state: merged`, `merge_commit_sha: ef129d6a3ac711673a4753cc17ab55d514bfa57a` |
| `manage-status list` | absent from the live store |
| `landing-check` | **`complete: true`, `missing_keys[0]`** |

⭐ **Second complete landing in a row.** The `merge_state` gap that failed `-126` and `-093` on exactly
one key is now closed on consecutive runs.

## Deliverable fidelity — 5 of 5

The shipped subject is this epic's thesis made mechanical: the exempt route now returns **its own status
member** instead of borrowing `fresh`, and both fail-closed consumers (`push`, `phase-5-execute`) record
`basis=ledger-verified` or `basis=exempt-unscanned`. ⭐ **The token shape was settled on ADR evidence
rather than preference** — a scoping decision made by the corpus instead of by the author.

## ⛔⛔⛔ The finding of this landing is the run's own self-review, and the run said so first

`pre-submission-self-review` fired **8 times** (3 `loop_back`) and closed
**`self-review clean: 75 candidates examined, no check matched`**.

**CodeRabbit then filed 9 actionable items against the same diff — four of them in classes the gate
already declares** (`same-document normative directives`, `producer-consumer pairs`, `source-of-truth
duplicates`, `contract sources`), and **two of the nine were genuine fail-open contract defects** — the
exact class the gate exists to catch before a reviewer sees it.

⛔ **This is NOT a vacuous run over an empty population.** 75 candidates were surfaced; the right
population was examined, the right classes applied, and the verdict was clean anyway. ⇒ **A verdict its
checks did not earn.** Folded to `PLAN-TRUTH-108`.

⭐⭐⭐ **The sender's sharpest sentence inverts a discipline this epic promotes:** *"`75 candidates
examined, no check matched` reads as thoroughness and is the reason nobody looked further — it publishes
the population size, which is the discipline this epic asks for, and then draws the wrong reassurance
from it."* ⇒ **Publishing the population is necessary and NOT sufficient. A stated denominator makes an
unearned verdict MORE persuasive, not less.**

### A candidate cause arrived in the same drain, from a different plan

`arm-the-refusal-recovery-that-has-never-run-001` reports that
`pre-submission-self-review.md:133-143` invokes the surfacer with **no `--base-branch`**, in both the
full and delta forms. **Verified first-party**: `self_review.py surface` declares `--base-branch`
defaulting to **local `main`**. On a plan rebased onto `origin/main` by `finalize-step-sync-baseline`
(order 3), local `main` lags — that run measured **`files_in_scope: 136` against a real diff of 21**,
~6×.

⚠ **Recorded as a HYPOTHESIS with a named test, because the two senders disagree.** `-001` reasoned the
failure is *"in the matching, not in candidate enumeration."* Both can be true. ⇒ **Re-run the surfacer
on #1425's branch with `--base-branch origin/main` and compare the candidate mix against the recorded
75.**

## Reviewer coverage: 2/3 by participation, 1/3 by yield

The run states it plainly: **the quorum it passed would have passed identically had both required
reviewers published nothing.** ⭐ And this run is a positive control for the distinction the gate lacks —
CodeRabbit reviewed three times with a real, high yield. **The verdict would have been byte-identical at
zero yield.** Forwarded to `review-apparatus` as `truthful-signals-050.md`.

## D0(c): unanswerable, not clean — and the run refused to round it

The spec asked whether the exempt path ever permitted a real push. ⛔ **It cannot be answered from
HEAD's records: `push` only ever wrote `"pushed {branch}"`, so the discriminator this plan ADDS never
existed to sweep for.** ⇒ **Latent by assumption, not by measurement.**

⭐⭐ **That is the correct disposition and the epic should protect it.** A plan that shipped the fix for
a defect it could not prove ever fired, and said so rather than claiming a catch, is the discipline this
epic keeps asking for. **Do not let a later reader convert "unanswerable" into "clean."**

## Self-reported errors — recorded because they were disclosed unprompted

- **A full SHA was fabricated from a short form three times into `head_at_completion`**, caught each
  time. ⛔ **This is not hypothetical hardening**: the producer accepted three invented 40-hex values and
  only attention stopped them — and `head_at_completion` is the **delta anchor** for the next
  self-review round, so a fabricated SHA mis-anchors it silently while the round still closes clean.
  Folded to `PLAN-TRUTH-121`, whose subject is exactly a producer succeeding over an unreadable write.
- **The merge queue was wrongly declared broken on a false premise, corrected twice.**

⭐ **Both are volunteered, and volunteering them is what made the first one actionable** — message `-002`
asks for `--head-at-completion` validation precisely because its author watched themselves defeat it.

## Reconciliation actions

- Queue: `PLAN-TRUTH-128` → `shipped`; `pr` = `1425`; `landing` = `landings/PLAN-TRUTH-128.md`.
- Inbox: 12 messages drained (11 from this plan + 1 from `review-apparatus`).
- Capacity: R 3 → 2 of N=3. **One slot frees.**

## Open items this landing leaves

| Item | Owner |
|---|---|
| self-review matched 0 of 75 in classes it declares | `PLAN-TRUTH-108` (+ the `--base-branch` cause hypothesis) |
| four retrospective aspects clean over unsupplied channels | `PLAN-TRUTH-104` |
| `head_at_completion` accepts a fabricated SHA | `PLAN-TRUTH-121` |
| declared footprint understates, and `sync-affected-files` cannot close it | `PLAN-TRUTH-136` |
| `(n=5/6)` printed over two different phase sets | `PLAN-TRUTH-117` |
| `reconcile-ledgers` not invoked where its result is actionable | `PLAN-TRUTH-105` |
| argparse: right verb, wrong flag (×4); help text contradicts `required=` | `PLAN-TRUTH-129` |
| quorum passes at zero yield | forwarded → `review-apparatus` |
| `blocked_user_review` spend in no published class | forwarded → `code-intelligence-substrate` |

## Metrics

**25h2m wall / 5h4m worked / 8.49M tokens, 6.1× the anchor, `6-finalize` ~70%. 6/6 phases closed.**

⭐ **`6/6 closed` means these are real figures, not floors** — the second consecutive landing where the
metrics are fully attributed. ⇒ **The 70-77% finalize share now stands across five runs**, and two of
those are complete rather than partial.
