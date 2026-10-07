# PLAN-114: The orchestrated-plan detector fails SILENTLY on any id shape it does not expect

epic: truthful-signals
workstream: WS-01

> Staged 2026-07-29 from inbox `code-intelligence-substrate-001` (reverse forward, operator-directed).

## Objective

`_SOURCE_ID_RE` requires `PLAN-` followed by **digits**. Any other id shape — notably the
**slug-scoped** form the operator wants adopted (`PLAN-CIS-01-…`) — does not match. ⛔ **And a
non-match does not error**: `inbox detect` returns `orchestrated: false` with empty `epic` and
`plan_spec`, which is **indistinguishable from "this plan genuinely is not orchestrated."** Make the
detector accept the intended id shapes, and make an *unrecognised* pointer a **distinguishable
outcome** rather than a silent negative.

## The defect

`marketplace/bundles/plan-marshall/skills/marshall-orchestrator/scripts/_orchestrator_inbox.py:84-86`

```python
_SOURCE_ID_RE = re.compile(
    r'^\.plan/local/orchestrator/(?P<slug>[^/]+)/plans/PLAN-\d+[^/]*\.md$'
)
```

| Candidate `source_id` | Matches |
|---|---|
| `…/plans/PLAN-03-content-search-seam.md` | yes |
| `…/plans/PLAN-CIS-01-content-search-seam.md` | **no** — `C` is not `\d` |
| `…/plans/CIS-01-content-search-seam.md` | **no** |

⭐ **The failure mode is the defect, not the rejection.** A rejected pointer silently reclassifies an
orchestrated plan as un-orchestrated, so its inbox messages are never written and the epic never
learns the plan ran. **Nothing reports the reclassification.** This is a confident-signal-hides-a-
caveat instance in the orchestration plumbing itself — which is why the sibling routed it here.

## Deliverables

1. **D1 — GATE (mutates nothing): settle the id grammar with the operator's Ask 1.** The operator has
   directed that plan IDs become **slug-scoped** so an id names its owning epic. Establish the exact
   accepted grammar(s) and whether the existing bare-numeric form stays valid (it must, for the
   ~180 already-allocated rows across two epics). ⚠ **Do not widen the regex to `.*` —** an
   over-broad detector is the always-fires vacuity pole, already recorded in this corpus.
2. **D2 — accept the settled grammar** in `_SOURCE_ID_RE`, with the slug capture still correct for
   every accepted form.
3. **D3 — an unrecognised pointer becomes DISTINGUISHABLE.** ⛔ **This deliverable stands even if D1
   keeps the numeric-only grammar.** `orchestrated: false` must separate *"this is not an orchestrator
   pointer"* from *"this looks like an orchestrator pointer but the id shape was not recognised"* —
   a reason token, a distinct field, or a warning. **A path under
   `.plan/local/orchestrator/*/plans/` that fails only on the id segment is the second case and must
   say so.**
4. **D4 — tests, each verified to FAIL pre-fix.** (a) Each accepted grammar detects with the right
   `epic`/`plan_spec`. (b) A genuinely non-orchestrator `source_id` still returns a plain
   `orchestrated: false`. (c) An orchestrator-shaped path with an unrecognised id segment returns the
   **distinguishable** outcome, not the plain negative. (d) The bare-numeric legacy form still works.

## Claim Labels

- OBSERVED (message-supplied, with the regex quoted): the pattern and its three-case behaviour.
  ⚠ **Verify by SYMBOL at HEAD** — re-read `_SOURCE_ID_RE` and `inbox detect` before scoping.
- OBSERVED (orchestrator-verified 2026-07-29): the two epics currently hold **no duplicate ids**, so
  the sibling's renumber repair is real and this plan is not racing an active collision.
- HYPOTHESIS: `inbox detect` is the *single* detection seam and no second detector exists — the
  `marshall-orchestrator` SKILL asserts this ("consumers never add a second detector"), but
  confirm/refute by deriving the consumer set (verify-at-outline). **An asserted absence is verified
  exactly like an asserted presence.**

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/scripts/_orchestrator_inbox.py`
- HYPOTHESIS: `marshall-orchestrator/SKILL.md` § `inbox detect` canonical block (verify-at-outline)
- OBSERVED: `test/plan-marshall/marshall-orchestrator/**`

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: ⛔ **PLAN-49 `rename-marshall-orchestrator-to-plan-orchestrator`** touches this same
  bundle and is drain-gated to last — **PLAN-114 must land first**, and PLAN-49 rebases over it.
- Adjacent to: the sibling epic's queue — **cross-epic check required** before emitting, since
  `marshall-orchestrator` is orchestration plumbing both epics depend on.

## Context — the incident that motivated Ask 1

The sibling allocated `PLAN-107`…`PLAN-111` while this epic already held 107-111 — **five duplicate
ids live across two active epics** — because it allocated without reading the sibling queue. Repaired
by renumbering plus a hand-maintained band invariant. ⚠ **That invariant is itself already violated**
(see the epic ledger): it assigns 1-49 to the sibling while this epic holds shipped rows at 27 and
41-49. **Slug-scoped ids remove the error class instead of adding a rule to remember** — which is the
argument for Ask 1 and the reason D3 matters even if D1 declines the grammar change.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-114-orchestrated-plan-detection-fails-silently.md"
```

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
