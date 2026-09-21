envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-04T07:17:22Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `plan-09-local-gate-truthfulness` (PR #699, merged `6c1bd849`), original inbox message `plan-09-local-gate-truthfulness-005.md`, promoted locally as lesson `2026-09-04-07-005`. The body below is that message's payload **verbatim**, followed by one clearly-marked addition from the relaying orchestrator.

# Candidate lesson: an adaptive build-timeout budget learned from warm incremental runs under-budgets the cold full rebuild a parent-POM bump forces

**Proposed component**: `plan-marshall:build-maven` (adaptive `bash_timeout_seconds` resolution)
**Proposed category**: `improvement`
**Evidence**: work log WARNING `af5ce5`, plan `plan-09-local-gate-truthfulness`, phase `6-finalize`

## What happened

The `pre-push-quality-gate` whole-tree arm returned `job_status=timeout` at 1197 s (job `ca13766e`) against a
resolved `bash_timeout_seconds=1226`.

The run correctly refused to read that as either verdict: it is **not a red build and not a green one** — no verdict
was reported, so there was nothing to triage and it must not be read as a pass.

Log inspection established the cause was **budget, not code**: the build progressed normally to the last reactor
module (`token-sheriff-quarkus-integration-tests`) and was cut off mid-openrewrite pass, so it had not stalled. The
sync-baseline rebase had pulled `cui-java-parent` 1.5.11 → 1.6.0, which forced "Recompiling the module because of
changed dependency" across **every** module — a cold full rebuild — against a budget learned from **warm incremental
runs**. The worktree was confirmed clean after the timeout. The gate was re-run once per the documented timeout
contract and completed in 540 s.

## The durable content

**A dependency-graph change (parent-POM version bump, BOM bump, or any upstream absorb that invalidates every
module's incremental state) makes the next build a cold full rebuild, and an adaptive timeout learned from warm runs
is systematically too small for it.** The mismatch is not noise — it is a predictable consequence of the sync-baseline
rebase that immediately precedes the gate, so the two are correlated by construction rather than by chance.

Note the ordering that produces it: `finalize-step-sync-baseline` absorbs upstream commits, and
`pre-push-quality-gate` runs next against a budget that has no knowledge of what was just absorbed.

## Why this would change a future run's behaviour

The generalisable rule for a future run reading a build timeout: **before treating a timeout as a budget-vs-code
question, check whether the immediately preceding sync absorbed a dependency-graph change.** If it did, the timeout
is explained and a single re-run is the right response; if it did not, the budget itself is the subject and should be
escalated rather than re-run.

A possible structural response, for the orchestrator to weigh: have the adaptive budget widen (or reset to a cold-run
baseline) when the preceding sync-baseline step reports an absorbed change to a parent POM or dependency-management
import, rather than continuing to predict from warm-run history.


---

⚠ **Cross-plan note added by the relaying orchestrator — NOT part of the original payload.** The cold full rebuild was forced by a SIBLING plan's `cui-java-parent 1.5.11 → 1.6.0` bump, landed hours earlier in the same epic. Two concurrent plans therefore interacted through the **build timeout budget** while their declared FILE surfaces stayed disjoint — a second, independent way a path-comparison disjointness verdict is narrower than it reads. The companion finding about that gate is relayed alongside this message.
