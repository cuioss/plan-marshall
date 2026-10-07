envelope_version=1
sender_type=plan
sender_id=compose-time-subtractions-drop-steps
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T12:43:37Z

## Proposed lesson metadata

- `component`: `plan-marshall:phase-3-outline`
- `category`: `anti-pattern`
- `title`: Folding N request deliverables into fewer outline deliverables drops the per-deliverable acceptance boundary — D2 shipped partial and nothing noticed

## Observation

The request (`PLAN-202`) named **four** deliverables, D1-D4, each with its own
acceptance language. The outline produced **two**. The fold is individually
defensible — D1 is a derivation gate, and D2/D3/D4 are all compose-side predicate
work in one module — but it dissolved the boundary at which each request
deliverable would have been graded.

Graded against the request rather than the outline, the run lands:

| | Verdict |
|---|---|
| D1 — derive every compose-time subtraction | **met** — population derived mechanically: 13 sites, against a hypothesised 3 |
| D2 — an operator decision is a first-class immunity input | **partial** |
| D3 — no silent subtraction, ever | **partial** — 11 of 13 sites conformant; the gap is named in `decision-rules.md`, not hidden |
| D4 — a predicate reading an unknowable input must not fire | **met**, and verified without the masking pin |

D3's partiality was caught, named in the doc, and filed to this epic as
candidate-lesson 005. **D2's was not.**

## The D2 shortfall

D2 asked to *"persist the operator's profile-override answer in the same shape
the step-level `lane` override already uses, so `scope_gated_finalize` skips any
step the operator named."* The originating scenario is explicit in the request:
the operator was asked at `phase-1-init`, answered, **named
`pre-submission-self-review` specifically**, and 27 minutes later an implicit
gate removed exactly that step.

What shipped:

- the plan-local channel — `status.metadata.finalize_step_overrides`;
- both compose-side readers, merged through one seam;
- a **manual CLI writer** — `manage-config finalize-steps set-lane --plan-id …`.

What did not ship: any caller that writes the `phase-1-init` posture-override
answer into that channel. The footprint touches no `phase-1-init` file and no
posture-gathering workflow. **Re-run the original Defect A scenario today and the
operator-named step is still dropped**, unless the operator separately knows to
invoke `set-lane`, and nothing prompts them to.

## The recursion, which is the actual lesson

The plan filed candidate-lesson 004 about precisely this failure mode —
*"widening readers without shipping a writer builds a guard whose predicate can
never fire"* — and it caught the asymmetry **inside** deliverable 1, which is why
the CLI writer shipped at all.

It did not apply the same completing question one level up, to the deliverable as
a whole: *what produces this state in the ordinary, unprompted flow?* A
human-invoked CLI verb is a writer for a test; it is not a producer for the
scenario the deliverable exists to fix.

This is the third recorded instance of a plan reproducing its own target defect
class inside its own work (cf. PLAN-86, and this plan's own self-review finding 8
instances of its target class in its own diff).

## Rule

1. When the outline folds request deliverables, carry each request deliverable's
   acceptance criterion forward **individually** into the merged deliverable's
   success criteria. The fold may merge the work; it must not merge the grading.
2. Apply the reader/writer completing question at **deliverable** granularity,
   not only at file granularity: for the new state the deliverable introduces,
   name the producer *in the flow the deliverable is meant to fix*. A CLI verb an
   operator must know to call is not that producer.
3. The retrospective's Goals-vs-Outcomes grading must be against the **request's**
   deliverable list, not the outline's — otherwise a fold makes a partial
   deliverable structurally ungradeable.

## Owed work

Wire the `phase-1-init` execution-profile override answer into
`status.metadata.finalize_step_overrides` at the moment it is answered, so
`scope_gated_finalize` honours operator intent without a second manual step. Until
then D2 is open, and the Defect A scenario that opened this plan is still live.
