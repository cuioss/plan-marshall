envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-02T20:14:44Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `refresh-identity-and-scope-defences` (PR #682), original message `refresh-identity-and-scope-defences-004.md`.
> Filed there as a candidate-lesson and refused by `manage-lessons add` with `wrong_store`: the component names a `plan-marshall` bundle that the Token-Sheriff store does not own. Content is unmodified below.

# Candidate lesson: a security remedy can be right about the symptom and wrong about the direction — validate it against the counterparty's state, not only local state

**Category**: anti-pattern
**Suggested component**: `plan-marshall:recipe-security-audit` / `plan-marshall:persona-security-expert`; applied surface `token-sheriff-client`
**Source plan**: `refresh-identity-and-scope-defences` (PR #682)

## What happened

`finalize-step-security-audit` correctly identified a real defect: when a refresh was refused
after the authorization server had already redeemed the presented refresh token, the client's
rotation family was left ahead of the stored token. The audit's remedy was `revertRotation` —
mark the presented token current again.

The remedy restored the **local** invariant and broke the **distributed** one. From
`logs/decision.log` `2026-09-01T05:36:53Z`:

> revertRotation marks the presented token current again, but the AS already ROTATED it, so
> the client is left holding a token the AS has invalidated — the next refresh presents a dead
> token and can trip the AS's own reuse detection. The audit cured the local misclassification
> and substituted a worse failure.

This was caught by **CodeRabbit**, not by the audit and not by any test. The correct semantics
— on a post-redemption rejection, atomically clear/quarantine the session and family, failing
closed to re-auth — are now recorded as **ADR-0005**. It cost a loop-back.

## The second-order cost, which is the part worth recording

Landing the quarantine then broke `RefreshConstraintLifecycleSpecIT.
shouldRefuseCoordinatorRefreshThatAppliesNoConfirmedBinding`, an integration test that had
landed in PR #672 and **encoded the old contract** (a refusal preserves the session). CI
caught it deterministically across two runs (`logs/decision.log` `2026-09-01T08:05:45Z`).

The temptation at that point was to narrow the quarantine to identity-mismatch only, which
would have re-created the original defect on the sender-constraint path — that refusal is
*also* reached only after the AS has rotated. The right call was that the pre-existing IT's
expectation was now the wrong thing. Recognising that required re-deriving *why* each refusal
path is reached, not pattern-matching on which test went red.

## The rule

For a fix on a distributed protocol boundary (OAuth refresh, any request/response with
server-side state mutation), a remedy is not validated by restoring a local invariant. Ask:
**after this remedy, what does the counterparty believe?** A client-side state repair that
disagrees with an already-committed server-side mutation is a worse failure than the
misclassification it cured, because it is silent until the next protocol round-trip and can
trip the server's own abuse detection.

Corollary: when a remedy makes a pre-existing test red, enumerate every code path that reaches
the changed branch before deciding whether the test or the remedy is wrong. Here there were
two such paths (identity mismatch, sender-constraint refusal) and only one had a red test.
