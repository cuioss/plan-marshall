envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=finding
created=2026-10-12T12:52:57Z

# [HIGH][Antigravity] No plan records which harness ran it — the client.toon pre-flight artifact is never written

- Component: plan-marshall:plan-orchestrator (`preflight` hook), plan-marshall:phase-1-init (plan start), plan-marshall:platform-runtime (`runtime-info`)
- Category: bug

## What happened

- Asked which harness ran PLAN-41, the orchestrator found **no explicit indicator** in the archived plan.
- **What exists.** `platform_runtime runtime-info` returns `harness: claude` (or the active target), and `orchestrator preflight --plan-id` writes it into the per-plan `client.toon`. `plan-orchestrator/workflow/preflight.md` calls this "the single entry point for runtime collection" that fires when a plan starts.
- **What is missing.** No archived plan of epic pm-mcp-core-m2-m4 has a `client.toon`: not the 11 Claude Code plans and not the Antigravity plan PLAN-41. Nothing in the `/plan-marshall` start path invokes the hook, and the orchestrator emits commands without being the one that starts them.
- **The only traces of Antigravity in PLAN-41** were incidental:
  - one `plan-marshall:platform-runtime:antigravity_runtime --help` call in `script-execution-2026-10-12.log` at 12:04Z (finalize);
  - the landing residue sentence "transcript-less platform runtime on Antigravity";
  - every metric reading `unmeasured`.

## Why it matters

- The orchestrator cannot tell Antigravity runs from Claude Code runs mechanically, so it cannot apply the stricter verification Antigravity landings now need (epic watch, 2026-10-12).
- Metrics from the two harnesses get compared as if they were alike.

## Suggested direction

- `phase-1-init` runs `orchestrator preflight --plan-id` (or calls `runtime-info` directly) and stamps `harness` into `status.json` metadata, so it survives archiving.
- Add `harness=` as a landing-facts key, which `landing-check` reports.
- Keep `client.toon` per-run entries, so a plan resumed under another harness shows both.

- Priority: **HIGH** (operator decision 2026-10-12: Antigravity issues are filed directly as high priority)
- Platform: Antigravity — first plan of epic pm-mcp-core-m2-m4 run under it
- Plan: `plan-41-static-verifier-remaining-rules` (PLAN-41), pm-mcp-core PR #34, merge commit ebe82b3
- Evidence location: pm-mcp-core `.plan/local/archived-plans/2026-10-12-plan-41-static-verifier-remaining-rules/` (logs/, metrics.md, execution.toon, build-results/)
- Origin: filed by the orchestrator of epic pm-mcp-core-m2-m4 from its landing analysis, verified against the archived plan and the PR
