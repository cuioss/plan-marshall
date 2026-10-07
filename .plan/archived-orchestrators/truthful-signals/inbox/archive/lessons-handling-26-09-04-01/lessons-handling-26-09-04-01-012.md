envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T06:10:29Z

component=plan-marshall:automatic-review
category=bug
bundle=plan-marshall

# An unregistered review-bot kind must fail loud, not be force-done past — the false-RED manufactures the escape hatch that conceals the false-GREEN

⛔ **This is a FOLLOW-UP to `lessons-handling-26-09-04-01-005.md`, which is already consumed
here** (archived under `inbox/archive/lessons-handling-26-09-04-01/`). It could not be amended in
place because `inbox amend` only reaches a live queued message, so it is filed as a successor
rather than as a new finding. **Please fold it onto whatever item absorbed `-005`** — it is the
same defect with the connecting mechanism now observed, not a fifth independent report.

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, PLAN-02
(`inherited-build-config-verification-depth`, merged as PR #714 / `7482cf18`).

## What `-005` reported, and what is new here

`-005` reported the review-participation quorum failing in two directions: a false GREEN (a bot
credited from a comment predating the commit) and a false RED (a token matching no registered bot
kind). It treated them as one surface failing two ways.

A second plan has now shown **how the two connect**, and the connection is worse than either half.

## What was observed

`required_bots` carried `pr-agent`. The automatic-review step resolved it as `unregistered_kind`
on **all three review rounds**, and on all three rounds the step took its **force-done escape
hatch** and reported the review satisfied.

Correcting the token to `cuioss-review-bot` at the pre-merge barrier changed the resolved state
from `unregistered_kind` to `participated_stale` — revealing that PR-Agent's "no major issues"
verdict had been rendered against `84efa0d0`, **three commits stale**. A re-review trigger then
cleared the state legitimately.

## Why this changes the shape of the defect

The false-RED does not merely fail a quorum on a spelling. It routes into **force-done**, and
force-done then swallows whatever real coverage gap sits behind it. Here the swallowed gap was
precisely the false-GREEN from `-005`: a three-commit-stale verdict accepted as a current review,
three times over.

The two halves are therefore not independent defects sharing a code path. The first manufactures
the escape hatch that conceals the second. ⛔ **Fixing either alone leaves the composite intact** —
validating the token without closing the force-done route still lets a stale verdict through once
the token is right; making HEAD-currency unconditional without token validation still lets an
unregistered token force-done past the check entirely.

## The generalisable rule

`unregistered_kind` and "the registered bot did not participate" are different facts and **must
not share an escape hatch**.

- `unregistered_kind` is a **configuration error**: the pipeline cannot say anything at all about
  review coverage, because it never asked a real bot.
- Force-done exists for the case where a *known* bot is unavailable or silent — an observed,
  attributable gap the operator can weigh.

Treating a config error as a weighable gap invites a force-done that silently accepts whatever
real coverage gap sits behind it.

## Suggested corrective action

Validate every `required_bots` token against the live registry at the earliest point the value is
read (plan start / config load), and reject an unmatched token as a hard configuration failure.
`unregistered_kind` should never reach the force-done branch: by the time the review step runs,
the only remaining states should be genuine participation states.

## Impact

Any project whose `required_bots` carries a typo, a legacy name, or a de-registered identity gets
a review step that reports green while performing **no review at all**, indefinitely and without a
single warning — and any genuine staleness behind it is consumed silently by the same mechanism.

⚠ This is the **fourth** observed mechanism in this class from this repository, after the
budget-exhaustion refusal (`-003`) and the two directions in `-005`.

## ⚠ Two plans, two local workarounds, zero project-level fixes

Both Token-Sheriff plans that hit this corrected the token in their own plan-local manifest
snapshot to get through, leaving the project `marshal.json` untouched. That is worth noting as a
*pipeline* observation rather than a repo one: the workaround is per-plan and invisible, so the
defect survives every plan that routes around it and the project config never converges.
