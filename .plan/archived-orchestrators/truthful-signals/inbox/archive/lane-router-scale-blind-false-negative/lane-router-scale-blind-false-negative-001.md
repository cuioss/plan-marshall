envelope_version=1
sender_type=plan
sender_id=lane-router-scale-blind-false-negative
epic=truthful-signals
kind=landing
created=2026-07-30T18:46:58Z

## What landed

**PR #1068** — `fix(planning-lane): scale-truthful routing + auto->standard rename`
(plan `lane-router-scale-blind-false-negative`, PLAN-57 of `truthful-signals`).

The planning-lane router was **scale-blind**: it could route a request to the light
lane without ever consulting how much surface the request actually touched, producing a
systematic light-lane false negative. The theme fit is exact — a confident routing
verdict (`light`, stated without hedge) hid the caveat that the scale evidence was never
read.

Shipped:

- **Scale-truthful routing.** The fan-out/path-count evidence is now actually reachable
  and actually consulted before a light verdict is issued. A wrong-narrow verdict now
  fails toward widening rather than toward silence.
- **`auto` -> `standard` rename** across the lane vocabulary (48 files in the original
  sweep, plus 3 more files that the mid-finalize rebase reintroduced tier vocabulary
  into).
- **TASK-013 structural collapse**: the gate detector no longer re-derives a subset of
  the sensor's rules — it calls `classify_scope_pure` and consumes the returned band, so
  gate and sensor are one decision *by construction* rather than by agreement.
- **ReDoS CWE-1333 fix** in `_cmd_planning_lane.py` (`_PATH_RE` running unbounded over
  the ingested `request.md` body at phase-1-init: ~3s at 20KB adversarial, 145s at
  10MB). Replaced with a bounded scan that fails toward WIDENING.

## Signals this run produced

- 15 pending Q-Gate findings, 1 automated-review signal, 0 script-failure clusters.
- Pre-submission self-review: 4 passes, 9 defects found and fixed.
- Finalize security audit: 1 CWE-1333 finding, fixed.
- Review retrospective: 3 reviewers compared, 12 actionable, 1 corroborated defect.

## Residue the epic should track

1. **Required-bot evidence went stale with no remedy — TOOL-LAYER DEFECT, worth its own
   plan.** `pr-agent` subscribes to `opened` / `reopened` / `ready_for_review` only, so a
   pushed HEAD is invisible to it. A `/review` comment drew zero response in 449s.
   `ci pr ready` returned success but was a **NO-OP** (the PR was not a draft).
   `tools-integration-ci` exposes `pr close` but **no `pr reopen`**, so there is no
   refresh path through the sanctioned abstraction at all. The run proceeded with the
   gap recorded as **finding `ea33a6`** rather than blocking. This is the same
   family as the standing "review bots — check states lie in both directions" residue,
   but it is a *missing verb*, not a misread state.

2. **Two provider defects, both in the review-ingest path** (filed as candidate-lessons):
   `fetch_findings` `comment_id` dedup silently dropped `pr-agent`'s materially changed
   body because pr-agent EDITS its comment in place — participation credited, content
   lost, recovered only by hand. And `github_pr post_responses` is **not idempotent**,
   re-transmitting 9 duplicate thread replies on the second triage, unlike
   `sonar post_responses` which tracks a responded marker.

3. **Vacuous-guard archetype, new shape (path-part skip-list) — 5 instances in one
   plan**, one of which had been vacuous in every worktree run since it was written, and
   one of which was reproduced *during the review, minutes after reading the fix*. See
   the candidate-lesson for the control-assertion rule.

4. **The plan reproduced its own target defect three times**, each time by re-deriving a
   subset of the sensor's rules in the gate. This is the fourth-plus sighting of
   "the plan reproduces the defect it is fixing" and the archetype now has a structural
   remedy (consume the producer's verdict) rather than only a warning.

5. **The `minimal` finalize posture would have DROPPED the security audit that found the
   ReDoS.** That is a concrete, first-party vindication of this plan's own thesis: a
   wrong narrow verdict is a security-gate suppression path, not merely a cost
   optimisation. Worth the epic deciding whether `minimal` may ever drop
   `finalize-step-security-audit`.
