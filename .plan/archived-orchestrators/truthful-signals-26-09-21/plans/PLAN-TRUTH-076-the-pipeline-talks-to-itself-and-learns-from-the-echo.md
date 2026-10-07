# PLAN-TRUTH-076: the pipeline's own PR comments enter the preference corpus, so it learns from its own echo

epic: truthful-signals
workstream: WS-01

> Staged 2026-08-09 from inbox message `daemon-baseline-interpreter-is-unregistrable-016`
> (`kind: candidate-lesson`, PR #1122). ⭐ **The reporting step declined to promote the hint and filed
> this instead** — the guard held on the run that found it, which is why this is a plan and not an
> incident.

## Objective

`default:finalize-step-preference-emitter` exists to learn recurring **operator** gate-dispositions and
generalize them into durable architecture hints. Its corpus admits **findings the finalize pipeline
itself authored**, so the pipeline's own control traffic becomes evidence about the pipeline's
preferences.

## OBSERVED — first-party to the reporting plan, on PR #1122

The emitter aggregates `(module, finding-class, disposition)` recurrences and promotes any tuple whose
within-plan count reaches `preference_min_recurrence` (**2** here). Exactly one tuple cleared:

```text
(default, pr-comment, taken_into_account) — count 2
```

**Both contributing findings were written to the PR by the finalize pipeline itself** — not reviewer
feedback, not operator dispositions:

| Finding | What it actually was |
|---|---|
| `b75eb2` | the orchestrator restoring the `Non-goals` paragraph that **`create-pr` had truncated** out of the PR description |
| `d5b4ff` | the orchestrator's own **`/review` trigger comment**, posted to re-engage `pr-agent` after a HEAD advance |

`github_pr fetch_findings` ingests **every** non-noise PR comment as a `pr-comment` finding **regardless
of author**. Each was then *necessarily* disposed `taken_into_account` — neither requests a change — and
**two such disposals are exactly the default threshold.**

## ⭐⭐ Why this is worse than an ordinary false positive: the signal is SELF-REINFORCING

A promoted hint here would encode a measurement artifact — *"unattributed PR comments are routinely
taken into account"* — as a standing preference. And it recurs on **any** plan where the pipeline posts
two or more comments of its own.

> **The more the pipeline talks to itself, the stronger the false preference becomes.**

⛔ There is no natural ceiling: the corpus grows with pipeline chattiness, not with operator judgement,
and the resulting hint would then influence the pipeline that produces the traffic.

⛔ **And the recurrence is UNATTRIBUTED.** Neither finding carries a `component`, so both collapse into
the `default` module bucket — which is where cross-cutting `insight` hints are routed, i.e. **the
widest-blast-radius sink available.** ⇒ The least-attributable evidence lands in the most-general slot.

⭐ **Note the compounding with a defect already delegated:** contributing finding `b75eb2` exists *only
because* `create-pr` truncated the Intent section and dropped Non-goals — a defect routed to
`review-apparatus` in the same drain (`truthful-signals-026`). **One bug manufactured the corrective
comment that became evidence for a false preference.**

## Deliverables

1. **D0 — GATE: establish the population before designing the filter.** How many promoted hints in the
   existing corpus were minted from self-authored comments? ⛔ **This decides whether the plan is a
   filter plus a corpus repair, or a filter alone.** ⚠ The reporting plan observed **one tuple on one
   run** and did not survey history — **do not assume the corpus is clean, and do not assume it is
   dirty.** Publish the population scanned alongside the count (a zero here must be a *looked-and-found-
   nothing*, not a *could-not-look*).
2. **D1 — discriminate authorship before a finding contributes to preference learning.** Two seams are
   already available and the plan picks one with a recorded rationale:
   - `fetch_findings` **already classifies bot vs human via `bot_kind`** — exclude self-authored comments
     from the disposition corpus **at ingest**; or
   - have the **emitter** skip findings with no `bot_kind` and no external author.
   ⭐ **The ingest arm is `review-apparatus`'s surface**; the emitter arm is ours. **Prefer the emitter
   arm unless D0 shows the corpus is polluted at ingest for other consumers too** — and if the ingest arm
   wins, coordinate rather than reach across (see Sequencing).
   > *A `pr-comment` whose author is the plan's own actor is not evidence of a preference about anything.*
3. **D2 — decide whether a tuple collapsing to `default` should be promotable AT ALL.** That bucket is
   the fallback for **unattributed** findings, not a real cross-cutting judgement. ⛔ **This is a
   separate question from authorship and must not be silently folded into D1** — an authorship filter
   would have blocked *this* instance while leaving the unattributed-to-widest-sink path open for any
   future one.
4. **D3 — a test that FAILS pre-fix**, driving the emitter over a synthetic corpus of self-authored
   comments and asserting no promotion, with a **matched negative control**: genuine operator
   dispositions at the same count **must still** promote. ⛔ A filter that suppresses both is not a fix.

**Four deliverables, one component.**

## Claim Labels

- **OBSERVED (reporting plan, first-party on PR #1122)**: the cleared tuple and its count of 2; the two
  contributing finding ids and what each actually was; that `preference_min_recurrence` was 2; that
  neither finding carried a `component`; that no hint was promoted and this was filed instead.
  ⚠ **Second-hand to this orchestrator — not re-derived.** Re-verify the tuple and the threshold at
  outline before scoping.
- **OBSERVED (this orchestrator, from the same drain)**: that `create-pr`'s truncation — the cause of
  finding `b75eb2` — is a separately-reported defect, delegated to `review-apparatus` as
  `truthful-signals-026`.
- **HYPOTHESIS**: that `fetch_findings` ingests every non-noise PR comment regardless of author.
  Confirm/refute against `workflow-integration-github`'s `fetch_findings` implementation and its author
  handling — **verify-at-outline**; it is D1's whole premise.
- **HYPOTHESIS**: that the orchestrator's self-authored comments are identifiable because they are
  allocated through `pr prepare-comment`. Confirm/refute against that verb in
  `tools-integration-ci` — **verify-at-outline**. ⛔ If self-authored comments are *not* reliably
  identifiable, D1's emitter arm has no discriminator and the plan re-scopes to D2 plus the ingest arm.
- ⛔ **NOT ESTABLISHED**: that any wrong hint was ever actually promoted and acted on. **D0 settles it.
  Do not report damage taken.**

## Expected Surface

- **OBSERVED**: the `default:finalize-step-preference-emitter` step — its aggregation and the
  `preference_min_recurrence` threshold
- **HYPOTHESIS**: `workflow-integration-github` `fetch_findings` — the ingest-arm discriminator
  (verify-at-outline)
- **HYPOTHESIS**: `tools-integration-ci` `pr prepare-comment` — the self-authorship signal
  (verify-at-outline)
- **HYPOTHESIS**: the architecture-hint store the emitter promotes into — D0's population
- ⛔ **NOT** the `automatic-review` bot taxonomy — adjacent, and it belongs to `review-apparatus`.

## Dependencies and Sequencing

- **Disjoint from all four running plans** (`-055`, `-070`, `-013`, `-074`) at file level. ⛔ Re-verify
  from live file lists at emit, not from this line.
- ⚠ **If D1 selects the ingest arm, it crosses into `review-apparatus`'s surface.** ⛔ **Do not edit it
  unilaterally** — route through their inbox and record the hand-off. ⭐ **An offer is not a transfer**:
  a plan blocked on an unaccepted hand-off waits indefinitely (PR-010 sat six days). **Prefer the
  emitter arm precisely because it is unilaterally shippable.**
- ⚠ Adjacent to the delegated `create-pr` truncation (`truthful-signals-026`). **Independent** — fixing
  the truncation removes one contributing comment but not the mechanism.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-076-the-pipeline-talks-to-itself-and-learns-from-the-echo.md"
```

## Write-Boundary

Touches only its own repository source and tests. Creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
