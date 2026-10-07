envelope_version=1
sender_type=plan
sender_id=plan-03-review-currency
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-17T19:28:47Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-09-17
bundle=plan-marshall

# Generic finalize dispatch must defer to step-owned dispatch bodies

Dispatching `default:pre-submission-self-review` through the generic Task
template (workflow doc + guessed skills) produced a malformed dispatch: the
step keeps its own dispatch body with a required `requires_prompt_fields`
field (`candidates`) and an author/verifier two-envelope choreography the
generic template cannot express. The leaf improvised, omitted its terminal
record, and the post-dispatch guard halted the phase.

## Proposal

Add a dispatcher pre-flight: before routing a step through the generic
template, check the step's frontmatter for `requires_prompt_fields` and for
an own-dispatch body; when either exists, follow the step doc's dispatch
section instead. Alternatively mark such steps in the dispatch-inline-split
roster so the generic path is never selected for them.

## Evidence

Plan plan-03-review-currency, finalize re-entry: generic dispatch of
pre-submission-self-review omitted `candidates`; leaf ran checks inline and
left Steps 3b/4 to the orchestrator; guard raised `step_record_missing`;
recovery required a manual verifier dispatch plus Branch A close.
