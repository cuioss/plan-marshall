envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-23T08:22:47Z

# Executor staleness and foreign-target skew are invisible; consumer repos silently run an old executor

Severity: high. Bundle: **plan-marshall** (`tools-script-executor`, `marshall-steward`, `execution-context`). Filed under RULING 2026-10-09 (a).

## Sources

- inbox `pm-mcp-core-m2-m4-290`, `-306`, `-308`, `-321`, `-335`, `-388`

## Consolidated statement

The generated `.plan/execute-script.py` is a single shared file per checkout with no record of which harness or plugin version produced it. Three distinct symptoms come from that one gap:

1. **Version skew.** The executor was pinned to plugin `0.1.1916`/`0.1.1947` while the leaves followed workflow docs from `0.1.1947`/`0.1.1948`. Documented verbs were missing (`git-workflow commit`, `manage-solution-outline deliverable-hashes`), flags were missing (`--verification-owed`), and the preflight printed `executor_version` next to `installed_version` and still judged it `fresh`.
2. **Foreign-target skew.** A concurrent OpenCode session on the same machine rewrote the shared executor mid-plan. From then on the Claude-driven plan resolved scripts into `~/.config/opencode/skills/...` and crashed deep inside `manage-config domain-narrow` (`could not locate a 'plan-marshall' bundle`, `_config_core` ImportError). Nothing detected the regeneration; the operator had to diagnose it and choose "Regenerate for Claude".
3. **Consumer-repo blind spot.** In a checkout with no `marketplace/` tree, `finalize-step-sync-baseline`'s drift probe reported `drift=unknown, regenerated=false — marketplace anchor did not resolve`, recorded as a non-fatal degrade. Every consumer repository therefore runs a stale executor indefinitely, and the scattered argparse rejections are its only symptom. Related: `execution-context` resolves workflow notations to `marketplace/bundles/{bundle}/...`, which does not exist in a consumer repo, so four leaves each improvised a plugin-cache fallback; strictly applied, Step 4 would have returned `workflow_not_found`.

## What is asked

- Stamp the generating target (harness + plugin root) into the generated executor, record the stamp in the plan's `status.metadata`, and refuse an execution with a named `executor_target_mismatch` (naming observed vs expected target and the regenerate command) instead of dispatching into a foreign skills tree.
- Compare the executor's pinned version against the loaded plugin version before any phase dispatch and fail or warn with the steward `upgrade` remedy when they differ — or list the verbs the docs name that the executor lacks.
- In a consumer repository, resolve the drift probe's marketplace anchor from the installed plugin cache, and surface `drift=unknown` as an operator-visible warning, never a silent degrade.
- Resolve workflow notations through the same seam the executor uses for scripts (installed plugin root first, marketplace source tree only when present).

## Evidence

As recorded by the senders. Not re-verified against HEAD in this run.
