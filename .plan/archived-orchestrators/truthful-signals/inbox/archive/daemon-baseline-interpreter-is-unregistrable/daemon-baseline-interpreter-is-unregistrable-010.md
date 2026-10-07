envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T21:21:15Z

component=plan-marshall:marshall-steward
category=bug
confidence=high
source_aspects=findings-store,execution-context-dispatch-audit

# Every health signal reported the pinned plugin-cache version while every dispatched leaf ran a superseded one

## Context

Mid-finalize this plan raised finding `b36689`: `phase-6-finalize` had loaded its skill bodies from plugin-cache `0.1.1240` while `generate_executor preflight` reported `installed 0.1.1304, executor 0.1.1304, marshal 0.1.1304`. The measured delta between the two trees was **141 markdown files** (137 changed, 4 added), of which **22 were `phase-6-finalize`'s own surface** — `push`, `create-pr`, `ci-verify`, the `branch-cleanup` merge gate, and the output template — and one was `manage-build-server/SKILL.md`, a **direct edit target of this plan's D2**.

Two things make this instance materially different from the recurring registry-pin incidents:

1. **The on-disk keep-oracle was SATISFIED.** Unmarked version directories equalled exactly `0.1.1304`; `1240`, `1288`, `1289`, `1291`, `1292` and `1293` all carried `.orphaned_at`. **No registry repair was owed.** The usual remedy did not apply because the usual defect was not present. The divergence lived entirely in the *in-process session registry pinned at process start*.
2. **The condition outlived every remediation the run performed.** `project:finalize-step-sync-plugin-cache` ran later in the same finalize ("10 bundles synced, on-main executor regenerated"). It did not re-seat the session. First-party measurement from **this** `lessons-capture` envelope, roughly nine hours and a dozen dispatches after the finding was raised: every skill loaded here — `persona-plan-marshall-agent`, `manage-lessons`, `marshall-orchestrator`, `manage-status` — reported its base directory as `…/plugins/cache/plan-marshall/plan-marshall/**0.1.1240**/skills/…`.

So the whole post-finding half of the finalize — including this step — executed against skill bodies 64 cache versions behind the pin, while every signal a reader would consult to check for exactly that condition reported green.

## Root cause

The version a session's skill bodies resolve from is bound once at process start and is not re-derivable from any surface the running session can query. `preflight`, the executor stamp, and the marshal stamp all report the *pinned* version, not the *seated* one, so they agree with each other and disagree with reality. Because the keep-oracle also passes, no existing check has a failing branch to fire — the divergence is invisible to every oracle simultaneously.

`/reload-plugins` does not re-seat skill markdown; a full session restart is the only known remedy, and nothing in the run surfaces that requirement at the point where staleness starts to matter.

## Proposed action

Make the **seated** version first-class and comparable to the pinned one:

- Have the executor (or a `manage-config`-level verb) report the directory the *current session's* skill bodies were resolved from, alongside the pinned version, so `seated != pinned` is a checkable predicate rather than an inference from a base-directory string in a skill-load banner.
- Add that comparison as a phase-entry assertion for `phase-6-finalize`, where the gap has the highest blast radius: the gate steps that decide push/merge are exactly the surface most likely to be in the delta.
- Where a restart is the only remedy, say so at the point of detection and name the owed action, rather than leaving it to a triage finding whose `accepted` disposition then silently persists for the rest of the run.

Do **not** route this through the orphan-marker repair path — this instance proves the two failure modes are independent, and a repair procedure conditioned on unmarked-directory state cannot detect a session-local pin.

## Impact scope

The operator accepted the risk on a sound, narrow argument: the merge gate (`branch-cleanup`) is an **inline** main-context step seated at `0.1.1304`, so the pin gap did not reach the merge boundary; CI was green at the pushed HEAD and every local gate re-ran against the actual tree. That argument holds for this plan. It does **not** generalise — it depends on which steps happen to be inline versus dispatched, which is a property of the manifest, not of the defect.

## Evidence

- `manage-findings list --plan-id daemon-baseline-interpreter-is-unregistrable` — finding `b36689`, type `triage`, severity `error`, `resolution: accepted`
- first-party, this envelope: four independent skill loads all reporting base dir `/Users/oliver/.claude/plugins/cache/plan-marshall/plan-marshall/0.1.1240/skills/…`
- `status.metadata.phase_steps['6-finalize']['project:finalize-step-sync-plugin-cache']` — `outcome: done`, "10 bundles synced, on-main executor regenerated", recorded *after* the finding
- finding detail — unmarked dirs equal exactly `0.1.1304`; `1240/1288/1289/1291/1292/1293` all carry `.orphaned_at`
