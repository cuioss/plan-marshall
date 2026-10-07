# WS-04: Standard liveness

epic: instrumentation-substrate

> Charter document for one workstream. Lives at `workstreams/WS-04-standard-liveness.md` and is
> tracked in the epic `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

A standard that prescribes a technique whose own stated precondition has never been satisfied is
authority without practice — the **vacuous-authority** archetype (n=5 in the WS-10 defect list) living
inside the testing standards themselves. This workstream takes the one confirmed instance and settles
it in the only two honest directions available: make the standard live, or demote it to a technique
that is available and not adopted here. It closes when no testing standard in the corpus prescribes
something the repository has never once done.

The instance matters beyond its own size. The technique in question defends against a defect shape
this repository keeps re-introducing — a model writing the exam and then editing its own answers, by
changing source or assertions after the fact so the coverage reads correctly. That is the mechanism
behind both the **test-pins-the-defect** and **vacuous-guard** archetypes, the latter recorded as
repeatedly re-introduced *by a fix for it*.

## Scope

- In scope: the property-based-testing standard in `persona-module-tester` and `pytest-testing`; the
  dependency decision that adopting it entails; a derived enumeration of any *other* testing standard
  in the same state.
- Out of scope: ⛔ **deleting the standard.** An independent team converged on the same scoping
  discriminator this repository uses, so the content is corroborated rather than idiosyncratic and
  deletion is refuted before it is proposed. Also out of scope: rewriting unrelated testing guidance.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-07-pbt-standard-liveness | staged | Adopt the dependency and make the standard live, or demote it to "available, not adopted" — and derive whether any sibling standard is in the same state. |

## Sequencing and Surface Notes

- Surface-disjoint from every other row in the epic: it touches the testing standards, the test tree,
  and `pyproject.toml`, none of which any other staged plan declares. It is therefore the safest
  candidate to pair if the epic's parallelization scope is ever raised above 1.
- No dependency on WS-01 or WS-02. The two are thematically adjacent — both are about a claim nothing
  checks — but they share no surface and neither blocks the other.
- ⚠ The enumeration half is the part that can go wrong. "No other standard is in this state" is a
  completeness claim, and this repository's own rule is that such a claim must be **derived** from an
  independent enumeration, never asserted from a spot-check. A plan that samples here reproduces the
  defect it was staged to remove.
