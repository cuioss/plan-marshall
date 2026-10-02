envelope_version=1
sender_type=plan
sender_id=cross-check-dated-archive-self-collision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-10-02T09:30:31Z

component=finalize-step-sync-plugin-cache
category=bug
created=2026-10-02
source_plan=cross-check-dated-archive-self-collision
confidence=high

# Derive the staleness guard's bundle set from what the claude target emits

## Context

After PR #1676 merged, `project:finalize-step-deploy-target` emitted 1215 files to `target/claude/`. The very next step, `project:finalize-step-sync-plugin-cache`, failed: its staleness guard reported `target/claude/` stale because bundles `plan-marshall-antigravity` and `plan-marshall-opencode` are "missing from target output". The plugin cache was not synced, the executor was not regenerated and the daemon was not reconciled. `--skip-staleness-guard` is operator-only and was not used.

This plan did not cause it and cannot avoid it: the step fails for every plan finalizing on current main.

## Root cause

OBSERVED: the guard compares the directories under `marketplace/bundles/` with the bundles present in `target/claude/` and treats any difference as staleness.

OBSERVED in the step's own error text: the two named bundles are harness-specific (added by #1670) and the claude target does not emit them. So the guard's expected set is wider than anything a correct generate can produce, and it can never pass.

The guard's source was not read for this report.

## Proposed action

Take the expected bundle set from the claude target itself - the same selection the generator applies when it decides what to emit - instead of from the raw directory listing. Add a test with a bundle the claude target excludes and assert the guard passes on a fresh generate.

## Evidence

- work.log 2026-10-02T09:17:41Z (deploy-target done), 09:18:10Z (sync-plugin-cache outcome=failed), 09:18:13Z ERROR with the full reason
- status: `project:finalize-step-sync-plugin-cache` outcome `failed`
