envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=truthful-signals
kind=finding
created=2026-09-23T10:09:23Z

# Relayed via lessons-routing — from `deployment-configurability` (API-Sheriff)

`lessons-routing` is not this finding's owner (it's about a self-review refusal's calibration against
routine worktree mechanics, not audience/destination) — routing to you as closest fit given your
existing self-review-vacuity queue (e.g. `PLAN-TRUTH-173`). Not independently re-verified beyond what
the source message already states.

---

# `pre-submission-self-review`'s deterministic surfacer has no step that keeps its diff base ref current, so a correct refusal fires on routine worktree mechanics

Surfaced during `plan-28-closeout-residual-hardening`'s `pre-submission-self-review`
(2026-09-22T11:00:16Z).

## What happened

The deterministic candidate surfacer behind `pre-submission-self-review`
(`pm-plugin-development:ext-self-review-plan-marshall`) refused outright:

> local base 'main' sits behind 'origin/main' — refusing to surface a stale scope; advance the local
> base past upstream first

The refusal itself is correct — a diff computed against a stale local base produces a larger and
wrong candidate set, and a self-review that examined the wrong scope while reporting a clean pass is
exactly the false-green this check exists to prevent. But the situation arose from ordinary worktree
mechanics: `finalize-step-sync-baseline` had rebased the *feature branch* onto `origin/main`
(`action=rebased, upstream_commits=1`), which advances the branch but does not fast-forward the main
checkout's local `main` ref. Nothing in the finalize pipeline is responsible for keeping that sibling
ref current, so a correctly-designed refusal fires on a state the pipeline itself routinely creates —
which trains a reader to treat the refusal as noise rather than as the safety property it is.

## Suggested remedy

A step whose deterministic surfacer diffs against a local base ref must ensure that ref is at or
ahead of upstream before invoking it — a `git fetch` plus a fast-forward of the base ref, not a
rebase of the feature branch. The refusal is the right behaviour and should not be worked around by
widening the diff base; the fix is upstream of the surfacer, in whichever step is supposed to keep
`main` current.

## Disposition in the originating plan

Recovered in-run: the step was re-dispatched and completed (`outcome=done`), and later finalize
rounds ran the full surface. No workaround was applied to the surfacer itself.

## Source

`deployment-configurability` epic (API-Sheriff), PLAN-28 (`plan-28-closeout-residual-hardening`, PR
#341, merged `1994f28`). Original candidate-lesson message:
`plan-28-closeout-residual-hardening-014.md` (discarded from that epic's own lessons corpus as
out-of-scope plan-marshall tooling, routed via `lessons-routing`).
