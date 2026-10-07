# PLAN-05: Repair the lessons and landing pipeline

epic: finalize-machinery
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-05-lessons-pipeline.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Execution Contract

The executing plan complies strictly with the plan-marshall process and rules: it
runs the phased lifecycle through its managing skills, treats this spec as the binding
brief, verifies every HYPOTHESIS and verify-first clause against the implementing
source before scoping on it, honors the Write-Boundary below, and reports back through
its PR and its inbox message. Standing operator instruction for this epic (opencode +
Muse Spark 1.3): process compliance is mandatory, not advisory.

## Objective

Retire the ledger-pipeline defects: merged plans invisible until landing with no owed
notion, the lessons pipeline re-filing what the corpus holds, the
orchestration-context bypass recurring with its own diagnosis, landing narratives
counting emitted candidates as created entries, and retrospective inputs lossy at two
independent points (TOON round-trip truncation plus chat-signal starvation). Ship a
pipeline that knows what it is owed, dedups before filing, resolves context at the
dispatcher, and reports post-housekeeping counts.

## Deliverables

1. Owed-landing notion: the epic can distinguish awaiting-a-slow-landing from no-news
   (defect 1), so shipped work is never re-emitted in the window.
2. Lessons dedup at the drain: re-filing what the corpus holds caught before write
   (defect 2), and landing narratives report post-housekeeping created counts, never
   emitted counts (defect 9).
3. Orchestration-context bypass fixed at the dispatcher: Step 4b.a0 resolution runs
   before forwarding to plan-retrospective (defect 8, lesson 2026-09-06-07-002), with
   the broken+working same-run reproduction as the regression test.
4. Lossless retrospective inputs: reduced_transcript TOON round-trip preserves order
   and counts describe the kept text (lesson 2026-09-05-16-001), plus the
   signal-gate population published beside every gate count (lesson 2026-09-06-08-002),
   residual-text classification of review bodies (lesson 2026-09-06-07-001), and the
   symmetric-pair authoring guard (lessons 2026-09-06-08-001, 2026-09-06-08-003).

## Claim Labels

- OBSERVED: a merged plan is invisible until landing with no owed notion, and the orchestrator would re-emit shipped work in the window — read at `.plan/orchestrator/finalize-machinery/epic.md` § `defect 1`
- OBSERVED: the lessons pipeline re-files what the corpus holds (6-of-11, 4-of-10) with the dedup burden entirely on the drain — read at `.plan/orchestrator/finalize-machinery/epic.md` § `defect 2`
- OBSERVED: the orchestration-context bypass recurred with its own diagnosis (dispatcher forwarded orchestrated=false without running Step 4b.a0) and the corpus remedy names the seam — read at corpus lesson `2026-09-06-07-002` § `resolution seam`
- OBSERVED: landing narratives count emitted candidates as created entries (14 vs attributable, nine vs 113-to-116 growth) — read at `.plan/orchestrator/finalize-machinery/epic.md` § `defect 9`
- OBSERVED: reduced_transcript is truncated and reordered by the consumer TOON round-trip while counts describe the intact text — read at corpus lesson `2026-09-05-16-001` § `round-trip loss`
- HYPOTHESIS: resolving context at the dispatcher plus post-housekeeping count reporting closes the bypass and inflation defects without changing the plan-retrospective input contract — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` § `inbox drain` (verify-at-outline)
- Verify-first clause: the consuming phase confirms the drain, dedup, and transcript mechanisms against the implementing sources at HEAD before scoping; refutation loops back to re-scope. Re-grounding settles at cleanup via the verdict field.
- Re-grounding instruction: the launched plan treats each HYPOTHESIS above as verify-at-outline against the named file § symbol; cleanup re-grounds the claim labels against HEAD and stamps verdicts via corpus set-verdict.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — inbox drain and queue reconciliation
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/manage-lessons.py` — lessons filing and dedup
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/_lessons_aggregate.py` — corpus aggregation
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/extract-chat-signal.py` — chat-signal and transcript input
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py` — landing report counts
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_chat_signal_reducer.py` — transcript reduction
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/lessons-integration.md` — lessons-integration contract

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-06 touches locks/build/handshake — no shared files, may parallelize
- Adjacent to: plan-retrospective input contract forbidding recompute — the fix lives at the dispatcher, never inside plan-retrospective

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/finalize-machinery/plans/PLAN-05-lessons-pipeline.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
