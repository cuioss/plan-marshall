envelope_version=1
sender_type=plan
sender_id=review-packs-become-published-artifacts
epic=review-apparatus
kind=candidate-lesson
created=2026-09-03T22:34:10Z

# Record build rows in the change-ledger so build time is measurable

component: plan-marshall:manage-change-ledger
category: bug
confidence: high

## Context

`analyze-logs` derives `build_time` from the structured change-ledger, the designated build-time oracle. For this plan it reports `build_count: 0`, `total_build_seconds: 0.0`, `suspect_count: 0`, and zeros across `pass` / `error` / `timeout` / `killed`.

The same plan's own `script-execution.log` records **68** `pyproject_build` calls totalling **36,541,090 ms** — 80.3% of all plan script time, with a single call peaking at 3,022,740 ms. The plan directory holds 41 build-result logs, several over 6 MB.

The build ledger is empty for a plan whose dominant cost was building.

## Root cause

The builds ran and were logged by the script-execution channel, but no corresponding rows reached the change-ledger. Either the ledger write is not on the build path taken here (the build-server / marshalld route rather than a direct wrapper invocation), or the ledger is worktree-scoped and did not survive worktree removal at `branch-cleanup` — the same evidence-destruction ordering that breaks the footprint resolver.

The plan-efficiency aspect correctly renders `unavailable` rather than `0`, per its own absent-is-not-zero rule. But that rule protects the reader only at this one call site: a consumer reading `build_time.total_build_seconds` directly gets `0.0`, and averaging that into a cross-plan roll-up records this plan as having built instantly.

## Proposed action

Establish which build path fails to write the ledger row and close it, so a plan's build time is measured wherever the build was dispatched from — including the build-server route.

If the ledger is worktree-scoped, relocate or fold it the way the plan's other logs are folded at integrate-into-main, so it survives the worktree removal that precedes the retrospective.

Until then, have `analyze-logs` cross-check `build_count: 0` against the presence of build-wrapper calls in `script-execution.log` and report a coverage gap rather than a clean zero block.

## Evidence

- aspect: plan_efficiency — `total_build_seconds` rendered `unavailable`; `build_count: 0`
- aspect: log_analysis — `build_time` all-zero, while `script_cost_rollup.ranked[0]` is `pyproject_build, 68 calls, 36541090 ms, 80.291% share, max 3022740 ms`
- plan artifact manifest — 41 files under `build-results/`
- The efficiency picture for this plan is missing its single largest term
