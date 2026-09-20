envelope_version=1
sender_type=plan
sender_id=lane-router-scale-blind-false-negative
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T18:50:17Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall

# ReDoS in the phase-1-init request ingest — and the `minimal` posture would have DROPPED the audit that found it

The finalize **security audit** found CWE-1333 (ReDoS) in `_cmd_planning_lane.py`:
`_PATH_RE` ran unbounded over the ingested `request.md` body at **phase-1-init**.
Measured on adversarial input: **~3s at 20KB, 145s at 10MB**. `request.md` is
operator-supplied content ingested at the very first phase, so this is a real,
reachable input surface, not a theoretical one.

Fixed with a **bounded scan that fails toward WIDENING** — when the scan cannot complete
within its bound it returns the wider classification rather than the narrower one, so a
timeout degrades into over-scoping rather than into a false narrow verdict.

The second half is the part worth the epic's attention: **the `minimal` finalize posture
would have dropped `finalize-step-security-audit` entirely**, and this finding would not
exist. That makes it a first-party, concrete instance of this plan's own thesis — a
wrong narrow verdict is a **security-gate suppression path**, not merely a cost
optimisation. The plan argued the router's scale-blindness could suppress gates; the
audit the router's own posture selection would have suppressed is what found the
vulnerability in the router.

## Solution

- **Bounded scan + fail-toward-widening** is the pattern for any regex over ingested
  untrusted content: bound the work, and make the bound's failure mode the *safe*
  classification, not the *cheap* one.
- **Decide explicitly whether `minimal` may ever drop `finalize-step-security-audit`.**
  The current answer is yes-by-omission, arrived at as a side effect of cost tuning
  rather than as a security decision. A posture that can silently remove the only
  security gate makes every narrow routing verdict a security decision.

## Impact

Two separable actions: the concrete regex fix (shipped in PR #1068), and the open
question of whether any cost posture may drop the security audit. The second is an epic
decision, not a plan decision — it changes what a green finalize means.
