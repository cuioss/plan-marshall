envelope_version=1
sender_type=plan
sender_id=inventory-blind-spot
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T15:50:43Z

component=plan-marshall:phase-2-refine
category=anti-pattern
bundle=plan-marshall
source_plan=inventory-blind-spot

# Refine-time fix-location hypotheses were 0-for-3; the operator's deep-lane override bought the truth

## Observation

On `inventory-blind-spot`, phase-2-refine produced fix-location hypotheses that were **all wrong**:

- **Hypothesis 1** — a fix location. Wrong.
- **Hypothesis 2** — a second fix location. Also wrong.
- **Hypothesis 3** — that the two inventories (`manage-architecture`'s file inventory and
  `pm-plugin-development`'s `enumerate_skill_files`) share **one** enumeration seam, so one fix would
  serve both. Also wrong: they are two independent enumerations answering two different questions, and
  unifying them would have changed the plugin-doctor lint population by ~14 files — a finding-flood the
  module-tests gate would not have caught.

The plan nevertheless landed correctly, and the reason is recorded in its own status metadata:
`lane_escalated: true`, `escalation_trigger: premise`. The **operator overrode the routed lane to deep
at init**. The deep lane's codebase-wide discovery is what measured the real population (6 kinds /
138+4 files), located the actual seam, and settled all three hypotheses as wrong. On the light lane the
plan would have implemented hypothesis 1 or 2 against a 3-kind allowlist.

## Root cause

Refine reasons from the request text plus shallow lookups. For a **blind-spot-class** request — "X is
not being seen" — the request text is by construction written by someone who cannot see X. Its named
symptoms are a sample (see the companion sample-vs-population lesson) and its implied fix locations are
guesses about code the requester has not read. Refine confidence (98.5 here) measures agreement with
the *request*, not agreement with the *codebase*.

## Solution

1. **Treat a refine-time fix-location hypothesis as a search hint with no standing.** It must never be
   carried into the outline as a premise; the outline's discovery must be free to falsify it, and the
   outline should record the falsification explicitly (this one did — three "Root cause" blocks in the
   Overview).
2. **Blind-spot-class requests are a deep-lane trigger on premise.** The signature: the request asserts
   something is missing / not indexed / not seen / not detected, and names specific instances. The
   requester's visibility is the thing under question, so the request cannot be a reliable scoping
   input. The operator had to supply this override by hand; the lane router should be able to detect
   the shape.
3. **"Two components ask the same question, so they must share a seam" is a hypothesis, not a fact.**
   Verify by reading both call sites and both downstream consumers before scoping a unification. Here
   the downstream consumer (`enumerate_skill_files` → plugin-doctor lint population) is what made the
   unification wrong, and that consumer was two hops from the apparent duplication.

## Impact

Directly actionable on the lane router: `escalation_trigger: premise` fired manually on this plan and
the outcome data says it was correct. A blind-spot-shaped request is a candidate for automatic deep-lane
routing.
