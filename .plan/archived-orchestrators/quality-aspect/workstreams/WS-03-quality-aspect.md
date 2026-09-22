# WS-03: Reviewer Value

epic: quality-aspect

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-03-quality-aspect.md` and is tracked in the epic
> `status.json` `workstreams[]` field.

## Charter

Owns trustworthy reviewer-value signals in both directions: refusal detection that
cannot misread a refusal as participation, per-source yield instruments, quota-wait
persistence, and rate-window claims seeded from bot-stated ETAs. Closed when a
required bot's sustained zero contribution is visible and every refusal phrasing in
the wild matches a registry pattern.

## Scope

- In scope: automatic-review detectors, refusal registry, yield recording,
  quota/rate-window persistence, participation-site expectations.
- Out of scope: review-finding triage outcomes (WS-07), merge-queue mechanics (WS-08).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-05-review-yield-a | staged | Sleep pacer replacement, head_sha evidence, yield recording, FIND-time refusals |
| PLAN-06-review-yield-b | staged | Invocation-scoped refusals, quota persistence, ETA-seeded claims, cross-repo phrasings |

## Sequencing and Surface Notes

- PLAN-05 and PLAN-06 both touch automatic-review; sequenced, PLAN-05 first
  (pacer and evidence primitives precede the persistence built on them).
