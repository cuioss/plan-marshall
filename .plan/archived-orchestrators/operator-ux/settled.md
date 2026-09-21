# Settled — operator-ux

Narrative relocated verbatim from `epic.md` by the cleanup pass's compaction stage. Nothing here
was edited or summarised: each section is the original entry, moved because its subject is closed.
A pointer remains at each origin in `epic.md` naming the heading below.

## The awaitable-reviewer-refusal hole

- **OBSERVED — an awaitable reviewer refusal is not awaited, so a PR can merge with zero review
  substance while every gate reports green.** PLAN-02 (#1406) merged with
  `review_decision: none`, confirmed independently via `ci pr view --pr-number 1406`. All three
  configured reviewers produced nothing: `cuioss-review-bot` participated but filed no findings,
  `coderabbit` refused on quota — **the awaitable kind** — and `sourcery` refused on quota (hard,
  ETA ~3 days). ⛔ **The pre-merge barrier is not defeated here; it is answering a different
  question.** It passed on `proves: participation_only`, which is exactly what it checks, and
  `review-retrospective` graded `indeterminate` by construction rather than papering over the
  absence — both components behaved correctly and the PR still merged unreviewed. The single
  setting that would have changed coverage is `review_rate_window_await: false`: CodeRabbit's
  refusal was awaitable, and nothing awaited it. A `phase-6-finalize` / `automatic-review`
  defect, not operator-UX work. Routed to the finalize-machinery epic. Source: PLAN-02 landing,
  corroborated at `ci pr view --pr-number 1406`.
  ⛔ **SHARPENED 2026-09-05 — this defect got worse without anyone touching it.** `#1407`
  (`bf1b7ed67`) moved `coderabbit` from `optional_bots` into `required_bots`; verified by diff of
  `.plan/marshal.json`. At HEAD the same step block still reads `review_rate_window_await: false`
  (verified via `manage-config plan phase-6-finalize get`). So the bot whose refusal this defect
  was opened about is now **required**, and its commonest failure mode is a refusal the gate is
  configured never to wait out. The pressure that creates is to demote CodeRabbit back to
  `optional_bots` to clear a blocked merge — the wrong remedy; turning the await on is the right
  one. ⚠ The two settings must be decided **as a pair**, and this epic no longer owns either:
  recorded in `finalize-machinery`'s inherited material and its resume anchor.
  ✅ **CLOSED 2026-09-07.** `review_rate_window_await` is **`true`** at HEAD (`.plan/marshal.json`,
  flipped by PR #1433 *"arm the CodeRabbit rate-window recovery"*), alongside
  `required_bots: cuioss-review-bot,coderabbit`. The pair was decided the right way round — the
  await was turned on rather than CodeRabbit demoted. PLAN-04 (#1437) is the first plan to run under
  it: CodeRabbit was required throughout, never moved to `optional_bots`, and **1 of 10** quota
  waits was spent. ⚠ Two residuals survive the closure and are recorded in the corpus rather than
  here: the run established the real blocker was a **missing trigger, not a closed window**, and
  `2026-09-07-13-006` shows all three CodeRabbit `rate_limit_eta_patterns` still miss the observed
  reset wording — so the gate now waits on a window whose length it cannot read.


## The orchestration-context bypass

- **OBSERVED — orchestration context is resolved AFTER the lesson-emitting steps, so an
  orchestrated plan's lessons bypass its epic inbox and become undrainable.** On PLAN-02 the
  finalize orchestrator assumed `orchestrated=false` / `epic=""` and forwarded that to
  `plan-marshall:plan-retrospective` (order 995) and `default:lessons-capture` (order 991). Both
  therefore wrote to the GLOBAL lessons store instead of filing `kind: candidate-lesson` messages
  into `operator-ux`. The error was caught only at `emit-landing`, whose guard forces the
  question — i.e. by the step that runs after the damage.
  ⚠ **The count in the landing narrative is CONTRADICTED and the discrepancy is recorded rather
  than smoothed.** The paste and the message Residue both say 14 (13 retrospective + 1
  lessons-capture). Measured at HEAD: **12** lessons carry a `2026-09-04` id; **7** name
  `domain-glob-seeding` in their body; the other five cannot be attributed from content alone,
  and three other plans were live in worktrees in the same window. The paste's own finalize table
  supplies part of the gap — `lessons-capture — folded into existing, no new lesson`, i.e. zero
  new entries, so counting it as 1 of 14 counts a fold as a filing.
  ⛔ **The bypass is the fact; the count is a lead.** Whatever the true number, none reached this
  epic's inbox, so `analyze` cannot drain them — this epic's drain is structurally blind to its
  own plan's lessons. A `phase-6-finalize` step-ordering defect (the same class as the
  already-recorded post-`branch-cleanup` ordering defects). Routed to the finalize-machinery
  epic. Source: PLAN-02 landing Residue, corroborated against `manage-lessons list` and the
  per-file attribution sweep.
  ⛔ **RECURRENCE on PLAN-03 (#1422), and the second instance supplies the diagnosis the first
  could not.** Same outcome, sharper mechanism: the dispatcher forwarded `orchestrated=false` /
  `epic=""` to `plan-marshall:plan-retrospective` **without ever running the Step 4b.a0
  resolution** — not "resolved late", never resolved. The plan's own `request.md` carried
  `source_id: .plan/orchestrator/operator-ux/plans/PLAN-03-domain-post-plan-narrow.md`, and
  the canonical seam answers correctly: `inbox detect --source-id …` → `orchestrated: true,
  epic: operator-ux`. `plan-retrospective`'s Input Contract forbids it from recomputing the
  forwarded values, so it correctly honoured a wrong `false`. ⭐ **The run caught its own error and
  filed corpus lesson `2026-09-06-07-002`**, which names the seam and the remedy — so the fix
  shape is now specified, not merely wanted. `lessons-capture` re-ran with corrected values, which
  is why PLAN-03's messages 001–004 DID reach this inbox while the retrospective's did not: the
  same run demonstrates both the broken and the working path. Two instances in two consecutive
  plans makes this the epic's highest-recurrence finalize defect. Still owned by
  finalize-machinery.
  ✅ **CLOSED 2026-09-07 — it did not recur on PLAN-04 (#1437).** All **eleven** candidate lessons
  plus the landing reached this inbox as `kind: candidate-lesson` / `kind: landing`; nothing went to
  the global store by the plan's own routing. Three consecutive plans tell the whole arc: PLAN-02
  bypassed entirely, PLAN-03 bypassed for the retrospective's share only, PLAN-04 clean. The remedy
  corpus lesson `2026-09-06-07-002` named — resolve the context from `request.md`'s `source_id`
  through `inbox detect` rather than forwarding a bare `false` — reached the dispatcher.
  ⚠ Closed on **one** clean run. A second clean landing is what would retire the underlying corpus
  lesson; until then treat this as fixed-and-observed-once, not proven.


## The sourcery false-participation defect

- ✅ **RESOLVED 2026-09-03 — the sourcery false-participation defect is FIXED.** Recorded here
  through three acceptances (`2026-08-25-09-012`, `2026-09-02-08-001`, and PLAN-07's third
  instance) with no remedy and no owning plan. PLAN-10 fixed it as an operator-approved
  mid-run scope deviation: `automatic-review/standards/sourcery.md` gained a third
  `refusal_patterns` entry plus `rate_limit_eta_patterns`, with two tests. **Demonstrated
  working in the same run** — the pre-merge re-fetch classified sourcery into `refused_bots`
  with cause `quota` rather than crediting it as a participant. The two prior corpus lessons
  become retirement candidates once a later run confirms the fix holds; they are NOT retired
  yet, because one demonstration inside the fixing run is not yet independent confirmation.
