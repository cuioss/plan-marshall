envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-02T20:14:37Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `outbound-hostname-verification-core` (PR #689), original message `outbound-hostname-verification-core-006.md`.
> Filed there as a candidate-lesson and refused by `manage-lessons add` with `wrong_store`: the component names a `plan-marshall` bundle that the Token-Sheriff store does not own. Content is unmodified below.

# Candidate lesson: every HEAD advance during finalize paid a full ~10-minute reactor rebuild

**Component:** `plan-marshall:phase-6-finalize` (verdict-currency / head-dependent steps)
**Category:** improvement

## Observed cost (this is the part I verified directly)

Long reactor builds run during phase-6-finalize alone, from the work log:

| Start | Step | Duration |
|-------|------|----------|
| 13:11 | `pre-push-quality-gate` | ~600s |
| 13:56 | post-`security-audit` re-gate | ~530s |
| 16:06 | post-review-fix re-gate | ~600s |
| 17:46 | post-triage re-gate | ~650s |

plus the phase-5 boundary gates at 12:15 (~720s) and the earlier 534s/699s/726s-timeout runs.
Roughly **an hour of wall clock inside finalize**, spent re-validating trees that differed from
an already-green tree by a small, characterised delta.

One of those re-runs was **correct and deliberate** and should not be optimised away: decision
`76e1c2` (13:55) refused to file a freshness-reconciliation record because the security-audit
commit had DELETED the root `<repositories>` block, which changes dependency resolution for
every module in the reactor. A green gate computed against a different POM says nothing about
that tree. Re-running was the honest input to the push barrier.

## The claim being carried forward (operator-supplied, NOT independently verified here)

Head-dependent finalize steps declare no `verdict_inputs` surface, so `verdict_currency` always
returns `invalidated` on a HEAD advance and the full reactor gate is re-run unconditionally.

I did not find `verdict_inputs` machinery evidence in this plan's own logs, so this is recorded
as a **mechanism hypothesis with a well-evidenced cost**, for the orchestrator to confirm against
the plan-marshall corpus before acting.

## The distinction that matters if it is acted on

Not every HEAD advance invalidates every verdict. The `76e1c2` case shows the discriminator:

- a commit touching **dependency resolution** (root POM, parent bump, repository block)
  invalidates the whole-reactor verdict — re-run
- a commit touching only files already inside the previously-gated set, with no build-graph
  effect, does not

A `verdict_inputs` declaration is exactly the surface that would let a step state which of the
two it is, instead of every step defaulting to the expensive answer.
