# PLAN-PR-077: The gate before the wait region

> ⛔⛔ **PARKED — SUPERSEDED BY PM-MCP (2026-09-26, operator decision).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> [`findings/2026-09-26-pm-mcp-carry-over.md`](../findings/2026-09-26-pm-mcp-carry-over.md) as PM-MCP input.
> Do NOT emit. Un-park only by explicit operator decision.

epic: review-apparatus
workstream: WS-04

> **Staged 2026-09-22, drained from inbox `truthful-signals-061.md`** (forwarded by `truthful-signals`
> per its standing dispatcher rule; original lesson `2026-09-21-08-001`, hand-authored, from plan
> `tracked-orchestrator-store-resolver`). The measurement/publish half of the source lesson —
> "three finalize steps each measured [diff size] privately and published nothing" — is
> `code-intelligence-substrate`'s cell (footprint derivation and evidence emission) and is NOT this
> plan's; this plan owns only the gate/wait-region half: consuming a published split and refusing to
> enter the review-bot wait region on a diff no configured bot can structurally review.

## Objective

Read the footprint split `compute-footprint` publishes (files/insertions/source-vs-data), and gate at
`push`/`create-pr` — before finalize enters the review-bot wait region — against GitHub's 65536-char
inline-comment cap and Sourcery's diff-size/file-count caps, so a PR two bots cannot structurally review
is never sent to wait on them. One prior finalize run spent 69.2% of its script wall time polling two
bots incapable of reviewing its 4028-file diff; this plan is that gate.

## Deliverables

1. Consume `compute-footprint`'s published `files_total` / `insertions_total` / source-vs-test split at
   `push` or `create-pr` time — read-only: this plan does not re-derive the footprint, only reads what
   `code-intelligence-substrate` emits (sequence behind that emission landing).
2. Gate: when the consumed split shows the diff exceeds a bot's structural cap (Sourcery's measured
   150,000-char / 300-file caps; GitHub's 65536-char single-comment cap), refuse silent entry into the
   review-bot wait region — surface the excess and which cap(s) it trips, before any bot is polled.
3. Discharge the standing 2026-08-25 Watch (epic.md § review-coverage dimension): when the gate trips on
   a source+test combination that would each individually clear the cap split apart, name the `test/`
   boundary split as the remedy rather than merely reporting the excess.
4. A diff that does NOT trip any cap proceeds unchanged — the gate adds a refusal path, never a new
   wait or a new required step for the common case.

## Claim Labels

- OBSERVED: `compute-footprint` (declared/realized split) is implemented at
  `manage-references/scripts/_cmd_compute_footprint.py` — confirm its emitted fields at HEAD before D1
  scopes on them (verify-at-outline).
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded FIRST-PARTY at HEAD. manage-references/scripts/_cmd_compute_footprint.py resolves and MOVED in this window (it appears in git diff --name-only 7a028157e..HEAD alongside _references_core.py, _references_crud.py and manage-references.py). The spec already carries its own verify-at-outline instruction to confirm the emitted fields at HEAD before D1 scopes on them; that instruction is now MANDATORY rather than prudent, because the file changed since the spec was written on 2026-09-22.
- OBSERVED (epic.md, 2026-08-25 measurement, n=1): Sourcery's diff-size cap measured at 150,000 chars;
  a real diff of 179,695 chars (19.8% over) split into 129,556 (`test/`) + 50,139 (everything else),
  both individually under the cap.
  - verdict: unverifiable | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: An n=1 measurement recorded in epic.md 2026-08-25 (Sourcery 150000-char cap; a 179695-char diff splitting into 129556 test/ + 50139). A historical external observation about a vendor cap, not a property of this tree; no git diff reaches it and it was not re-measured. The spec own n=1 marking is the right caveat.
- HYPOTHESIS: the review-bot wait region begins in the `automatic-review` finalize step (order ~40,
  per `PLAN-PR-074`'s spec text) and is reachable for gating from a step ordered before it — confirm the
  actual step order and call boundary at `phase-6-finalize/standards/push.md` and
  `phase-6-finalize/workflow/create-pr.md` (verify-at-outline).
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: HYPOTHESIS about the wait region beginning in the automatic-review finalize step and being gateable from an earlier order. Both cited confirmation sites MOVED in this window - phase-6-finalize/standards/push.md (+2/-2) and phase-6-finalize/SKILL.md (+14) changed, while workflow/create-pr.md did NOT. The hypothesis is undisturbed as a hypothesis, but its verify-at-outline read must happen against HEAD, not against the 2026-09-22 text.
- HYPOTHESIS: GitHub's 65536-char cap and Sourcery's 300-file fetch cap are not yet asserted anywhere
  in this tree as gate thresholds — confirm by content search before D2 hard-codes either value
  (verify-at-outline).
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: HYPOTHESIS that GitHub 65536-char cap and Sourcery 300-file fetch cap are not yet asserted anywhere in this tree as gate thresholds. Consistent with HEAD: the content sweeps run this pass surfaced no such threshold constant. NOT a derived negative - the dedicated numeric sweep this claim asks for was not run, and the content-search tool does not walk .github. Treat this as undisturbed, not as the confirmed absence D2 needs before hard-coding either value.
- Verify-first clause: this plan's D1 cannot scope its consumption call until `code-intelligence-substrate`'s
  footprint-emission plan (the sibling half of the source lesson) has landed and its published field
  names are known; HALT and report if that emission is not yet available at outline.
  - verdict: unverifiable | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Verify-first clause: D1 cannot scope until code-intelligence-substrate footprint-emission plan has landed and published its field names. A cross-epic dependency whose state lives in another ledger - not settleable from a review-apparatus git diff. The HALT-and-report instruction stands.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_cmd_compute_footprint.py` — read-only consumer, not an edit target unless D1's read finds no exposed field (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_push*.py` and `test/plan-marshall/phase-6-finalize/test_create_pr*.py` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: `code-intelligence-substrate`'s footprint-emission plan (the measurement/publish half of
  the same source lesson) — this plan reads what that one publishes and cannot scope before it lands.
- Overlaps with: `PLAN-PR-073`, which shares `create-pr.md` (73 owns its landing-record deliverables,
  this plan owns its D2 gate) — sequence, never pair. RE-SCOPED 2026-09-22 (cleanup A1 re-grounding):
  the original text here asserted no overlap while the line below already named the same collision;
  `push.md` remains undeclared by any other live spec.
- Adjacent to: `PLAN-PR-073` (owns `create-pr.md`'s landing-record deliverables; this plan's D2 gate
  and 073's landing-record edits are different concerns in the same file — sequence, never pair) and
  `PLAN-PR-074` (owns the `automatic-review` step boundary this plan's D2 gates entry to).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-077-the-gate-before-the-wait-region.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
