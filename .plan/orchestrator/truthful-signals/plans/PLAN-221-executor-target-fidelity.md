# PLAN-19: Executor target fidelity under opencode

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: truthful-signals
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-19-executor-target-fidelity.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT.
>
> Priority 1 (operator direction 2026-09-20): emit at the next free slot. Builds on
> PR #1548 (in-tree: env-var target detection before marshal.json fallback).

## Objective

Make opencode runs execute opencode-fresh code: the executor detects its runtime
target and resolves scripts, imports, and refreshes from that target's roots —
never from the Claude plugin cache. A version skew between executed code and repo
fails closed instead of running silently outdated.

## Deliverables

1. Executor bootstrap detects the runtime target (platform env vars, then marshal.json, then filesystem probe — extending the in-tree #1548 detection) and selects script roots accordingly.
2. Checked-in executor generated per detected target: the opencode 7-root walk over the opencode skill tree replaces Claude-cache-first resolution for opencode runs.
3. Opencode-side refresh pipeline: the opencode skill tree (or a versioned opencode cache) refreshes on the same triggers as the Claude sync, with a freshness gate before execution.
4. PYTHONPATH and bootstrap dirs derived from the detected target's roots; cross-target imports refused rather than resolved.
5. Stale-cache refusal wired into executor preflight: embedded cache version older than the repo manifest fails closed under opencode (cache_freshness verdict consumed, not merely reported).
6. Finalize syncs the running target: under opencode, refresh the opencode skill tree (or skip the Claude sync as target-blind work) — no sync-opencode path exists today, and opencode-run plans currently pay deploy-target + cache-sync time serving the other runtime.
7. Target detection, resolution, and refusal matrix tests across claude/opencode/antigravity × fresh/stale cache.

## Claim Labels

- OBSERVED: the checked-in executor embeds ~270 script paths under ~/.claude/plugins/cache with a Claude-flavor fallback resolver — read at `.plan/execute-script.py` § SCRIPTS + _resolve_notation_by_target.
- OBSERVED: refresh is Claude-pipeline-only (target/claude rsync into the Claude cache; no opencode path) — read at `.claude/skills/sync-plugin-cache/scripts/sync.py` § pipeline.
- HYPOTHESIS: per-target generation plus opencode-side refresh plus preflight refusal closes the skew — confirm/refute at `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` § generate_target_aware_resolver_code (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/` — executor generation, target resolvers.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/` — stewardship, freshness, bootstrap.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/` — target detection, runtime registry.
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/finalize-step-deploy-target/` — target-blind Claude sync performed by opencode-run plans (folded 2026-09-20 in the same act).

## Dependencies and Sequencing

- Depends on: none (PR #1548 detection groundwork already in-tree).
- Overlaps with: none in this epic (steward/executor/runtime surfaces touch no staged WS surface; PLAN-12's tools-script-executor entry is invocation classification, a different file).
- Adjacent to: WS-04/PLAN-08 git paths without touching them.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-221-executor-target-fidelity.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
