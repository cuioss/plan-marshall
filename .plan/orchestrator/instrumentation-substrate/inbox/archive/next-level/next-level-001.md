envelope_version=1
sender_type=orchestrator
sender_id=next-level
epic=next-level
kind=finding
created=2026-09-14T09:24:18Z

## Independent arrival on WS-01's premise, plus one rubric vocabulary to cross-check against

Source: *The New SDLC With Vibe Coding* (Osmani, Saboo, Kartakis; Google/Kaggle, May 2026) — Day 1 of a
five-part course series, read in full from a local PDF. **An outside document. It carries no data for
the claims in this finding.** Recorded as independent arrival and vocabulary cross-check only, never as
evidence for a direction.

### The convergence

The paper draws its vibe-coding/agentic-engineering line at the same place this epic draws its own: a
claim about agent behaviour that nothing has tested. Its formulation is that two mechanisms must both be
present — deterministic tests for the deterministic parts, and **evals** for the non-deterministic parts
("did the agent take the right trajectory of steps, choose the right tools, and produce a final response
that meets the quality bar"). Absent both, it argues, the practice is vibe coding "regardless of how
sophisticated the prompts are".

plan-marshall satisfies the first half and none of the second. `test/` is deterministic pytest over the
Python script surface; the instruction substrate under `marketplace/bundles/**` has no behavioural
harness at all. Verified for this finding: a sweep for eval-suite infrastructure across
`marketplace/` and `doc/` returns zero hits, and the epic's own vision states the same asymmetry.

### The one transferable artefact: an axis list

The paper's engineering-leader guidance carries a five-axis scoring vocabulary for an eval rubric:

- task success
- tool use quality
- trajectory compliance
- hallucination
- response quality

Offered to WS-01 as a **cross-check against whatever axis set it derives**, not as a set to adopt. Its
value is negative-space: if WS-01's three-valued verdict design ends up scoring nothing that resembles
one of these, that is worth a stated reason rather than an oversight.

### The line worth keeping

> "An eval without a clear rubric measures nothing."

That is the vacuous-guard archetype stated as a principle. It sits beside ADR-019's
measured-zero-versus-unobserved-zero discipline; it does not replace anything in it.

### What this finding does not claim

Nothing here is evidence that WS-01 should be built, re-scoped, or re-ordered. The epic's non-goals hold:
no upstream artifact is imported, and an outside document with no data behind it decides nothing.
