# PLAN-LR-06: manage-lessons corpus integrity

epic: lessons-routing
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Ported in from the now-closed dated epic `lessons-handling-26-08-26-01` as its `PLAN-LH2-18`
(`manage-lessons-corpus-integrity`), deliberately kept unrouted by that run rather than sent to a
content-owning sibling: it is a defect **in the `manage-lessons` tool itself**, surfaced by running
that epic's 2026-08-26/27 sweep against the live lesson corpus — not a finding about lesson
*content*. `lessons-routing` owns the routing/versioning mechanism, so tooling defects the mechanism's
own dogfooding surfaces land here, in the new WS-05, rather than in a content-owning sibling epic.

## Objective

Three concrete defects in `manage-lessons`, all observed first-party during the 2026-08-26/27 sweep
(87 active lessons scanned, 82 removed via 81 successful `remove` calls + 6 `not_found`):

**D1 — `remove` can destroy a lesson while reporting failure, with no tombstone.** Lesson
`2026-08-25-05-001`: before the call it was present in both `list active` and `get`; one `remove`
call returned `error: not_found`; after the call it was gone from both, with **no tombstone written**
— so the retirement left no audit record at all. This is strictly worse than the previously known
`remove` refusal defect (which merely refuses without acting): here the call refuses **after**
destroying, so a caller that retries on `not_found`, or reads it as nothing-happened, is wrong in a
way that cannot be recovered from the store alone. Unestablished and the first deliverable's job to
settle: whether the unlink happens before the metadata read, or the tombstone write fails after a
successful unlink.

**D2 — five lessons from the same sweep cannot be removed by any sanctioned verb.** All five refused
with `not_found` despite being live and readable at the time: `19-001`, `19-003`, `23-13-001`,
`23-13-002`, `24-14-001`. No content is at risk — each subject already lives on in a routed inbox
message from that sweep — but the corpus cannot be mechanically cleaned of them today.

**D3 — five pre-existing superseded stubs are known-prunable and were never pruned.** A dry run of
`cleanup-superseded` during the same sweep confirmed all five already carry tombstones; pruning them
was out of that drain's scope and was deferred here rather than re-derived later.

## Deliverables

**D1 — root-cause and fix the destroy-without-tombstone path.** Reproduce against a lesson id in the
`2026-08-25-05-NNN` shape (or as close a fixture as the current corpus state allows); instrument the
unlink-vs-tombstone-write ordering to determine which one is failing or racing; fix so that `remove`
either (a) succeeds and leaves a tombstone, or (b) refuses and leaves the lesson untouched — a partial
outcome (destroyed + unrecorded) must become structurally unreachable, not just less likely.

**D2 — make the 5 stuck lessons resolvable.** Diagnose why `19-001`, `19-003`, `23-13-001`,
`23-13-002`, `24-14-001` refuse `remove` with `not_found` while still readable elsewhere (a
resolution-path mismatch between the lookup `remove` uses and the one `list`/`get` use is the leading
suspect — confirm at outline rather than assume). Ship either a fix to the shared resolution seam or,
if the mismatch is structural, an explicit recovery verb — but the corpus must end this plan with all
five in a resolvable state (removed-with-tombstone, or confirmed-and-documented as an accepted
permanent exception, never silently left ambiguous).

**D3 — prune the 5 known-prunable superseded stubs.** Re-run `cleanup-superseded` (confirm dry-run
still reports the same 5, then apply) once D1's fix is in — pruning through a `remove` path still
carrying the destroy-without-tombstone defect would risk repeating D1 on stubs that already have a
clean tombstone.

**D4 — tests.** A destructive-repro test for D1 that fails on the current `remove` and passes after
the fix (assert: a failed `remove` never changes `list active` / `get` observability, and a successful
one always leaves a tombstone — the two must be exhaustive and mutually exclusive outcomes). A
regression test per resolved id from D2. A `cleanup-superseded` idempotency test for D3 (a second run
over the same 5 prunes nothing further).

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/**`
- `test/plan-marshall/manage-lessons/**`

## Dependencies and Sequencing

⛔ Re-derive with `corpus cross-check` at emit time — this spec is newly staged and has not yet been
cross-checked against `lessons-routing`'s own LR-01..05 or any sibling epic.

- D3 depends on D1 landing first (see D3 rationale above) — sequence within this plan, not a
  cross-plan dependency.
- No known cross-plan collision at staging time; `lessons-routing` LR-01..05 touch the audience/
  routing/versioning surface, not `manage-lessons`' remove/tombstone internals.

## Claim Labels

- OBSERVED: `remove` on lesson `2026-08-25-05-001` returned `error: not_found` while the lesson was
  present in both `list active` and `get` immediately before the call, and absent from both with no
  tombstone immediately after — recorded in `lessons-handling-26-08-26-01`'s resume_anchor,
  2026-08-27 retirement pass.
- OBSERVED: five lessons (`19-001`, `19-003`, `23-13-001`, `23-13-002`, `24-14-001`) each refused
  `remove` with `not_found` during the same retirement pass while remaining otherwise live — same
  source.
- OBSERVED: a `cleanup-superseded` dry-run during the same pass reported exactly 5 stubs, all already
  carrying tombstones — same source.
- HYPOTHESIS: the `not_found` refusals in D1 and D2 share a root cause — a lookup path used by
  `remove` that diverges from the one `list`/`get` use — confirm or refute at outline against
  `manage-lessons/scripts/**`'s resolution seam (verify-at-outline).
- Verify-first clause: after this lands, a `remove` call must never leave the corpus in a state where
  `list active` / `get` disagree about whether the lesson still exists.
