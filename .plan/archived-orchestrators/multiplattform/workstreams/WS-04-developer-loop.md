# WS-04: A developer can deploy the OpenCode tree in one command

epic: multiplattform

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-04-developer-loop.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own the developer-facing half of the multi-target story: the inner loop that gets generated OpenCode
output onto a machine, and the distribution documentation that describes how the output is published.
The workstream closes when the OpenCode inner loop is one command — as the Claude loop already is —
and no distribution document states a matrix that disagrees with the workflow that actually runs.

## Scope

- **In scope:** `.claude/skills/sync-opencode/**` (a project-local skill, never a shipped bundle), `test/sync-opencode/**`, `doc/developer/marketplace-build.adoc`, `doc/developer/distribution.adoc`.
- **Out of scope:** the generator that produces the tree (WS-02); anything requiring a live OpenCode install to confirm (WS-05); shipping the sync tool in a marketplace bundle — consumer projects never generate OpenCode output.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-04-sync-opencode-inner-loop | staged | The `sync-opencode` project-local skill with a bounded deletion model, its tests, the inner-loop documentation, and the corrected distribution matrix. |

## Status: COMPLETE

⭐ **Every plan in WS-04 has shipped** — PLAN-04 (#1372) and PLAN-20 (#1418). The workstream
closed the OpenCode developer loop and then closed the prune-boundary defect that loop's own
first landing introduced.

⛔ **One thing this workstream did NOT close:** the `total_tokens=unknown` gap. Four consecutive
OpenCode-lane landings have reported it, so it is a standing property of the lane rather than a
per-run omission — recorded in `epic.md` § Open Defects with the RUNBOOK Step 10 obligation gap.

## Sequencing and Surface Notes

- **PLAN-04 is disjoint from every other plan in the epic** and depends on none of them. Under `parallelization_scope: 2` it is the standing concurrency partner: whichever sequential plan is in flight elsewhere, PLAN-04 may run beside it. This is the single most valuable scheduling fact in the ledger.
- PLAN-04's D1 rests on a HYPOTHESIS no artifact in this repository can settle — that OpenCode discovers *plural* `skills/`/`agents/`/`commands/` directories. The `--target-dir` flag exists to keep the rename correctable if the assumption is refuted; the run states the assumption in its report rather than as fact, and WS-05's protocol § 1.2 is what actually settles it.
- The generated `target/opencode/` tree is **gitignored** (`.gitignore:12`) and absent from a fresh clone, so the run generates it locally as its own fixture source. The spec's claim-label table already anticipates this; it is a handled contingency, not scope drift.
- PLAN-04's D3 is consumed by WS-05's validation protocol § 1.2 as its deploy step once it lands. Until then the protocol documents the manual fallback.
