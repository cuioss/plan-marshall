# PLAN-111: The pre-merge comment barrier re-ingests its own reply — a non-terminating loop in shipped code

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-07-29 from the PLAN-92 landing (#1041). ⛔ **Highest-severity item in the queue: this
> is a LIVE non-terminating loop in code that has already merged to main.**

## Objective

`post_responses` transmits triage dispositions **under the repo-owner account**, and `fetch_findings`
carries **no self-authored-response filter**. The pre-merge comment barrier therefore re-ingests
plan-marshall's own reply as an unaddressed finding. Under the default `fail_into_loopback` this does
not degrade — **it does not terminate**: respond → re-fetch own response → block → respond again.
Give `fetch_findings` a transmission-shape exclusion so the barrier cannot consume its own output.

## The loop — OBSERVED, live on #1041

1. The barrier fetches PR comments and finds an unaddressed one.
2. Triage responds via `post_responses`, which posts **as the repo owner** (`cuioss-oliver`) — the
   same identity a human reviewer uses.
3. The barrier re-fetches. The reply it just wrote is now an unaddressed comment.
4. `fail_into_loopback` blocks. Go to 2.

There is no step that removes a reply from the fetched set, so **the cycle has no exit.** It was
resolved on #1041 only by an operator disposing it `taken_into_account` to proceed — a manual
interrupt, not a terminating condition.

⚠ **This is the fourth-plus confirmation of the self-ingestion defect** the epic has tracked as
"PLAN-92 defect 6" (`responded_bots` listing a skipped reviewer, our own triage replies returned as
stored comments). What is new is the **severity**: previously read as a counting/labelling error, it
is now demonstrated to be a **non-terminating loop**, and PLAN-92 shipped without closing it.

## Deliverables

1. **D1 — GATE (mutates nothing): establish the exclusion key and prove it is sound.** ⛔ **Author
   identity is NOT a usable discriminator** — `post_responses` posts under the repo-owner account,
   which is exactly the identity a genuine human review also uses, so filtering by author would
   discard real findings. Establish the **transmission shape** `post_responses` emits (the
   `## Triage dispositions` header and the `### In reply to comment_id:` structure are the observed
   candidates) and verify it cannot collide with a human-authored comment.
2. **D2 — exclude the transmission shape in `fetch_findings`.** The filter belongs at the **fetch**
   seam, not at the barrier: any consumer of `fetch_findings` inherits the same defect otherwise.
3. **D3 — a termination guarantee, not just a filter.** ⚠ **A filter alone leaves the loop shape
   intact** — a future emitter whose shape drifts re-opens it. Add a bounded iteration guard so the
   barrier **cannot** loop unboundedly even if the filter misses, and make exhaustion a **reported
   coverage gap requiring an operator decision**, never a silent pass.
4. **D4 — tests, each verified to FAIL pre-fix.** (a) A `post_responses`-shaped comment is not
   returned by `fetch_findings`. (b) A human comment that merely *quotes* the disposition header IS
   still returned — the false-positive boundary. (c) The barrier terminates when every remaining
   comment is self-authored. (d) The iteration guard trips and reports rather than passing silently.

## Claim Labels

- OBSERVED (operator narrative, first-party, #1041): the loop occurred and was broken by a manual
  `taken_into_account` disposition; `post_responses` transmits under the repo-owner account;
  `fetch_findings` has no self-authored-response filter.
- OBSERVED (orchestrator-verified on #1040 and #1042): our own triage replies ARE returned in the
  `ci pr comments` result set, authored `cuioss-oliver`, carrying the `## Triage dispositions` header
  and `### In reply to comment_id:` lines.
- HYPOTHESIS: the `## Triage dispositions` header is a **reliable** transmission-shape key —
  confirm/refute at `workflow-integration-github` § `post_responses` against the actual emitted body
  (verify-at-outline). **If the shape is not distinctive enough, D1 must find another key rather than
  proceeding on this one.**
- HYPOTHESIS: `fail_into_loopback` is the default posture — confirm/refute at the barrier's config
  resolution (verify-at-outline). If the default is not `fail_into_loopback`, the severity narrows to
  configured-projects-only but the defect stands.
- Verify-first clause: **PLAN-92 shipped D5 (per-thread disposition replies) and D6 (evidence-based
  participation) into this exact surface.** Re-read `fetch_findings` / `post_responses` at HEAD
  before scoping — the seam moved. **Verify by SYMBOL, not line number.**

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/**` —
  `fetch_findings`, `post_responses`
- HYPOTHESIS: the pre-merge comment barrier in `phase-6-finalize` (verify-at-outline)
- HYPOTHESIS: `automatic-review` if the barrier's loopback posture lives there (verify-at-outline)
- OBSERVED: the corresponding test modules

## Dependencies and Sequencing

- Depends on: none. ✅ **Unblocked** — PLAN-92 shipped as #1041 and released this surface.
- Overlaps with: ⚠ **PLAN-60** (`in-house-gate-ci-parity`) and **PLAN-52** both touch finalize-gate
  surfaces; **PLAN-102** may touch triage plumbing once its D1 resolves. **Re-check disjointness
  before pairing with any of them.**
- Adjacent to: PLAN-100 (`landing-message-carries-the-outcome-post-merge`) — same finalize phase,
  different seam.

## ⭐ Why this ranks above most of the queue

Every other open item in this epic produces a **wrong signal**. This one produces **no signal at
all** — the plan stops, indefinitely, and only an operator interrupt releases it. It is also the
epic's theme in its purest form: the barrier is a mechanism built to guarantee review coverage, and
its failure mode is to **consume its own output as evidence** that coverage is still missing.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-111-self-ingested-reply-is-a-non-terminating-barrier-loop.md"
```

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
