# PLAN-PR-035: The response path drops answers, and nothing measures it

> ⛔⛔ **SUPERSEDED 2026-09-12 by `PLAN-PR-060` — do NOT emit this spec.** Its queue row is retired
> under the operator's decision to raise the split guard to 12 deliverables and group staged work by
> shared target surface; D1–D4 are carried there as D1–D4 and D0 folds into that plan's merged D0 gate,
> carrying its HALT threshold and its attribute-by-author obligation unchanged. ⛔ **This file is NOT
> dead and is NOT deleted**: it remains the AUTHORITATIVE TEXT of every deliverable body, and
> `PLAN-PR-060` points here rather than retyping it.

epic: review-apparatus
workstream: WS-03

> Staged plan spec, created 2026-08-23 by the cloud-wave ingestion. Carries plan 090's strongest
> finding, which was recorded as a run-report finding and as residue but **never written into a
> `gaps.md`** — so no staged plan inherited it and it would have lapsed with the report. See
> `../cloud-wave-audit.md` § 8.

## Objective

Across four observed PRs, **13 of 43 review findings received no posted answer**. The triage pipeline
records a disposition for each finding; the transmit step is supposed to carry that disposition back to
the reviewer. For thirteen findings it did not, and **nothing in the system noticed**. This plan makes
the unanswered case observable, then closes whichever mechanism the measurement implicates.

The value is the measurement first. PLAN-PR-019 shipped an idempotency marker to stop *duplicate*
replies; the sibling defect — answers that never go out at all — was visible in the same data and has
no owner.

## Problem

The observed counts, per PR: **#1167 ×4, #1158 ×2, #1198 ×6, #1195 ×1** — thirteen findings, from a
population of 43 observed across those four PRs. The verification that surfaced them confirmed each is
genuinely unanswered, and distinguished the claim carefully: *"unanswered" and "unfixed" are different
claims, and only the first holds.*

Several mechanisms could produce an unanswered finding, and the wave has evidence for more than one:

- **A resolve failure jumps the marker** (`070 G1`, live): the reply is delivered, the resolve mutation
  fails, the code `continue`s past the stamp — and the delivered disposition is reported under
  `count_untransmitted`. That is a mis-*count*, not a drop, but it proves the return value cannot be
  trusted to tell answered from unanswered.
- **A finding with no `thread_id` is untransmitted** (`github_pr.py:1631`) while
  `automated-review-lifecycle.md:133-135` says such a finding is *skipped, never guessed at* — two
  different states described as one.
- **`mark_finding_responded` returns an error dict when no record matches, and every one of its four
  call sites across three providers discards it** — a silent failure by construction.

⛔ **What is NOT established is which mechanism produced the thirteen.** That is D0's job, and it must
not be assumed. A plan that fixes the mechanism it finds most plausible, and reports the thirteen as
closed, would reproduce this epic's own archetype.

## Deliverables

**D0 — GATE, mutates nothing: attribute the thirteen.** For each of the thirteen findings, determine
from the stored findings corpus and the PR state which mechanism left it unanswered, or record it as
**unattributable** with the reason. Publish the attribution as a table with its population (13 of 43,
across four named PRs). **HALT and report if fewer than nine can be attributed** — a fix chosen from a
minority sample is a guess wearing a measurement's clothes.

**D1 — Make "unanswered" a first-class outcome of the transmit verb.** `post_responses` must return the
set of respondable findings it did **not** transmit, each with a machine-readable reason, distinct from
the `untransmitted[]` list that today conflates a delivered-but-unresolved reply with a never-sent one.
The three states — sent, not sent, sent-but-unresolved — are three names.

**D2 — Stop discarding the marker's error return.** All four `mark_finding_responded` call sites across
the three providers check the result; a failed mark is reported, never swallowed. This is the cheapest
real improvement here and it is independent of D0's outcome.

**D3 — Close the mechanism D0 implicates.** Scope is set by D0 and by nothing else. If D0 attributes the
majority to `070 G1`'s resolve-failure path, **this deliverable is dropped** and the fix belongs to
PLAN-PR-029 D2's amendment — say so in the report rather than duplicating it.

**D4 — Pin the measurement.** A test asserting that a respondable finding which is not transmitted
appears in the new set with its reason, and that a transmitted one does not. Derived from the finding
corpus, not hand-listed.

## Claim Labels

- OBSERVED: 13 of 43 findings unanswered across #1167 (4), #1158 (2), #1198 (6), #1195 (1) — recorded
  in `../cloud-runs/090-feed-pr-findings-back-into-local-review/report-01.md` § Findings and residue,
  and confirmed by that run's `verification.md`.
  - verdict: corroborated | checked_at: 19453cb | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded at HEAD 19453cb (was 7845a4b9a). METHOD CHANGED THIS PASS: intersection of the spec's DECLARED Expected Surface (via corpus surfaces, the single shared reader) against git diff --name-only 7845a4b9a..HEAD (204 paths). The former whole-spec-file method is RETIRED as non-discriminating - it scored hits on prose mentions of CLAUDE.md and .plan/marshal.json. ZERO declared paths moved in this window, so no premise of this spec was disturbed. NOT a line-by-line re-audit: this establishes the surface is UNDISTURBED, not that the premise was re-read.
- OBSERVED: `mark_finding_responded` returns `{'status': 'error', …}` at `_findings_core.py:575`; its
  four call sites (`github_pr.py:1662`, `:1679`, `gitlab_pr.py:433`, `sonar.py`) are all bare
  statements.
- OBSERVED: `github_pr.py:1648-1651` appends to `untransmitted[]` and `continue`s past the mark on a
  resolve failure; `gitlab_pr.py:425-429` is the identical shape.
- OBSERVED: `automated-review-lifecycle.md:133-135` describes the skip set incorrectly — a thread-bearing
  finding with no `thread_id` is *untransmitted*, not skipped.
- HYPOTHESIS: the thirteen are attributable from the stored corpus without re-fetching the PRs —
  confirm/refute at D0 (verify-at-outline). If the corpus has been pruned, the PRs are still readable
  through the CI abstraction's read-side.
- Verify-first clause: the thirteen were observed on 2026-08-13. **Re-check whether any has since been
  answered** before reporting it unanswered — the population is dated evidence, not a durable fact.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
  — `cmd_post_responses` return
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`
  — read only; the error return already exists
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/standards/automated-review-lifecycle.md`
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr.py`

## Dependencies and Sequencing

- **Depends on: PLAN-PR-029** — that plan (with its `070 G1` amendment) owns the resolve-failure path.
  Running after it means D0 attributes against a fixed mechanism rather than a live one, and D3 is
  scoped to what remains.
- **MUST NOT run concurrently with PLAN-PR-024, PLAN-PR-025, PLAN-PR-029, PLAN-PR-034 or PLAN-PR-040** — all touch
  `github_pr.py` and `test_github_pr.py`.
- ⛔ **D0's DENOMINATOR IS SUSPECT — added 2026-08-23 from inbox `truthful-signals-030.md`, mechanism corroborated first-party.** This plan's headline is *13 of 43 observed findings unanswered*. **PLAN-PR-040** establishes that the producer's self-response filter is start-anchored on a heading literal (`github_pr.py`:393, `body.lstrip().startswith('## Triage dispositions')`), so a comment WE authored that opens with anything else is ingested as a review finding. Some of the 43 may therefore be our own comments, which would make both the numerator and the denominator wrong. **D0 must ATTRIBUTE by author before it reports any ratio**, whichever of the two plans runs first — reporting 13/43 without that attribution publishes a ratio over a population that was never verified to be reviewer output.
- Overlaps with: PLAN-PR-029 (`automated-review-lifecycle.md`, `github_pr.py`).
- Adjacent to: plan 090's three other residue items, none of which any plan owns — the run-report
  placeholder scan (belongs to `cloud-plan-lane`), the authoritative-set → doc-prose-list mirror drift,
  and the disposition-flow evidence asymmetry (a rejection needs a rationale but never a source). They
  stay epic-level open items.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-035-the-response-path-drops-answers-and-nothing-measures-it.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
