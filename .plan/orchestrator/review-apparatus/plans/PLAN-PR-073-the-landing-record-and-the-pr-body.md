# PLAN-PR-073: The landing record, and the PR body that describes it

epic: review-apparatus
workstream: WS-04

> **Component-cut spec, authored 2026-09-18.** This plan owns ONE component: the landing surface — `emit-landing.md`, `pr_intent_section.py`, the orchestrator inbox landing payload, and the merge-queue read.
> ⛔ **Every deliverable body below lives in its ORIGINAL source spec and is NOT restated here** — the
> `Carried from` column names the theme spec this deliverable was cut out of, and that spec's own
> pointer names the retired spec holding the body. Follow the chain; do not retype.
>
> The theme specs `PLAN-PR-056` … `PLAN-PR-064` were retired on 2026-09-18 because their surfaces
> overlapped almost totally — `_findings_core.py` was declared by 7 of 9 — so no two could ever run
> concurrently. The cut is by component, so **no file is declared by two live plans**.

## Objective

Let a landing claim only what was positively read, carry the SHA it describes, and make a reader failure an error rather than a silent omission.

## Deliverables

| # | Deliverable | Body lives at | Carried from |
|---|---|---|---|
| D1 | The landing's claim is gated on a substantiated merge | `PLAN-PR-028` § D1 | `PLAN-PR-064` D1 |
| D2 | The landing's facts are validated at the value level, carry their commit, exist once per run | `PLAN-PR-028` § D2 | `PLAN-PR-064` D2 |
| D3 | The PR body and the retrospective name the tree they describe; a reader failure is not an answer | `PLAN-PR-028` § D3 | `PLAN-PR-064` D3 |
| D4 | A posted disposition is a promise, and nothing re-checks it | `PLAN-PR-031` § D6 | `PLAN-PR-060` D10 |


**D0 — GATE, mutates nothing.** Read `PLAN-PR-028` §§ Re-Grounding, Deliverables and Expected Surface,
and confirm each named SYMBOL still resolves at HEAD. ⛔ **Anchor on symbols, never on line numbers** —
the halves' own gates already found relayed line references that had moved while the mechanism held.
**HALT and report** if a named symbol has moved.

⛔ **`PLAN-PR-028` D0 is STRUCK** — do not run it, do not re-litigate it. The roster below starts at its
D1.

*(Carried verbatim from `PLAN-PR-064` D0 at the 2026-09-18 component re-cut.)*


5 deliverables — within the guideline (12 nominal, ~14 when the aspects fit together, operator ruling 2026-09-15). ⛔ **Absorb nothing from another component**: the re-cut exists so this plan's surface stays disjoint.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pr_intent_section.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_pr_intent_section.py`
- OBSERVED: `test/plan-marshall/plan-orchestrator/`

## Claim Labels

- OBSERVED (2026-09-18): every deliverable in this plan was carried verbatim from the theme spec named
  in its `Carried from` column, which carries the claim labels for its own deliverables. Confirm/refute
  by reading that spec's `## Claim Labels` section — this plan re-states none of them.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: review-apparatus/cleanup | rescoped: n/a | evidence: Structural carried-verbatim claim, re-verified by reading this spec at HEAD: four pointer deliverables plus D0, with PLAN-PR-028 D0 explicitly struck, no deliverable body restated. The spec's own diff this window is verdict-bullet stamping plus the .plan/local/orchestrator to .plan/orchestrator path correction - no deliverable text changed.
- OBSERVED (2026-09-18, orchestrator `corpus surfaces` + per-deliverable mapping; RE-SCOPED 2026-09-22):
  this plan's declared surface is disjoint from every other live plan's in this epic **except
  `PLAN-PR-077`, which shares `phase-6-finalize/workflow/create-pr.md`** (073 owns the landing-record
  deliverables in that file, 077 owns its D2 gate) — sequence, never pair. This is the collision the
  resume anchor did not previously name. Confirm/refute with
  `orchestrator corpus cross-check --slug review-apparatus` — non-determinate at HEAD (see the claim's
  verdict).
  - verdict: contradicted | checked_at: 14d8f3ccd | by: review-apparatus/cleanup | rescoped: yes | evidence: COLLISION RE-CONFIRMED at HEAD by reading both Expected Surface sections: this spec declares phase-6-finalize/workflow/create-pr.md (landing-record deliverables) and PLAN-PR-077 declares the same path (its D2 gate). PLAN-PR-077 was committed into the ledger this window and its own Dependencies section now names the same collision from the other side, so both specs state it - disjointness is false and the re-scope is covered at both ends. create-pr.md itself did not move this window.
- OBSERVED (2026-09-18, lesson `2026-09-04-17-001`): `pr_intent_section` clips the PR Intent section at
  a byte offset, the renderer appends rather than replaces, and `ci pr view` does not return the body —
  so the only repair is a full `ci pr edit` rewrite. D3 reports an overflow instead of truncating.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: review-apparatus/cleanup | rescoped: n/a | evidence: pr_intent_section.py is UNDISTURBED: the only two files that moved under phase-6-finalize this window are standards/adr-integration.md and standards/branch-cleanup.md. The byte-offset clip, the append-not-replace renderer and the ci pr view body gap are unchanged. The declared-surface path that triggered this staleness check is test/plan-marshall/plan-orchestrator/, whose whole diff is #1585's verdict-staleness work - irrelevant to this claim.
- OBSERVED (2026-09-18, lesson `2026-09-06-16-001`): `_github_pr.py:2332-2339` returns
  `'enqueued': True` corroborated only by the branch rule; `isInMergeQueue` / `mergeQueueEntry` occur
  in zero files across the CI and GitHub script surfaces.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded first-party at HEAD. _github_pr.py did not move this window, so cmd_pr_merge_queue's enqueued:True corroborated only by the branch rule is unchanged and the previously derived coordinates still hold (no further drift). A content sweep for isInMergeQueue|mergeQueueEntry over 3108 files returns count 0 - still zero occurrences across the CI and GitHub script surfaces.

## Dependencies and Sequencing

- ⛔ **D0 is the symbol-resolution gate and `PLAN-PR-028` D0 is STRUCK** — do not run the struck gate;
  a moved symbol RE-SCOPES its deliverable rather than being re-pointed by hand.
- ⛔ **D1 depends on `PLAN-PR-067` D9** (`pr merge-queue` returns `enqueued: true` only on a post-condition
  read): a landing claim cannot be substantiated against a queue state nothing in the tree can observe.
  That deliverable moved to 067 at the re-cut because it edits `_github_pr.py`, which 067 owns.
- ⚠ D2 edits the orchestrator inbox (`_orchestrator_inbox.py`, `landing-payload-spec.md`). That is a
  different component from the rest of this plan and is declared as such; the seam is
  `emit-landing.md`'s producer-side assertion.
- ⚠ D4 reconciles a posted disposition against the landed diff. The same reconciliation exists one
  stage earlier in `review_commitments.py` (`PLAN-PR-074`) — extend that seam, never build a second one.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-073-the-landing-record-and-the-pr-body.md"
```

## Write-Boundary

The plan implementing this spec writes to its own repository source only. It creates and edits NO file
under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
