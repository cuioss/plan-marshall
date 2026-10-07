# WS-04: Ledger, lessons, and finalize anchors

epic: finalize-machinery

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-04-ledger-pipeline.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Owns the orchestration ledger pipeline and the finalize anchor mechanisms: owed
landings with no bound, lessons re-filing, orchestration-context bypass, lesson-count
inflation, lossy retrospective inputs, plus fabricated completion anchors, dead-holder
mutex budgets, down-daemon serialization loss, and handshake drift. The outcome is a
ledger that knows what it is owed, a lessons pipeline that reports post-dedup counts,
and anchors the mechanism cannot fabricate or strand.

## Scope

- In scope: plan-orchestrator inbox/orchestrator queue, manage-lessons dedup/retention,
  plan-retrospective collectors and report, platform-runtime chat-signal reducer,
  phase-6-finalize lessons-integration/capture, manage-locks merge mutex, build-server
  marshalld supervision, execution-manifest mark-step-done, plan-marshall handshake
- Out of scope: finalize step ordering (WS-01), argparse wording (WS-02), bot-currency
  semantics (WS-03)

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-05-lessons-pipeline | staged | Owed landings, dedup, context bypass, honest counts, lossless inputs |
| PLAN-06-anchors-and-mutex | staged | Unfabricable anchors, reclaimable mutex, supervised builds, sound handshake |
| PLAN-07-session-identity | staged | Target-aware session resolver; degrade-to-unenriched on transcript-less targets |

## Sequencing and Surface Notes

- PLAN-05 and PLAN-06 are file-disjoint (ledger/retrospective vs locks/build/handshake)
  and may run in parallel once the scope knob allows.
- PLAN-05's orchestration-context fix must land before any claim that context bugs are
  retired; one run demonstrating both broken and working paths already exists.
