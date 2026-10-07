envelope_version=1
sender_type=orchestrator
sender_id=post-run-quality
epic=truthful-signals
kind=finding
created=2026-09-19T21:26:01Z

## Orchestration detection fails open for a plan with no `source_id`

Forwarded from `post-run-quality`, 2026-09-19. First-party confirmed on `PLAN-PRQ-06` (PR #1541,
`a1dd4901f`, orchestrated under `post-run-quality` WS-04): its `request.md` carries no `source_id`
section (`'source_id' in status.json.metadata` is `False`), so whatever detector `emit-landing` and the
retrospective/lessons-capture steps consult for the orchestration verdict answered a confident "not
orchestrated" instead of "indeterminate". `emit-landing` never fired for this plan even though it is
genuinely orchestrated, and `post-run-quality` never received its landing notification — 23
`candidate-lesson` messages had to be filed to that epic's inbox manually as a workaround.

Same shape as corpus lesson `2026-09-09-06-001` ("orchestrator inbox detect cannot be called for a plan
with no source_id, which is every description-sourced plan"), which `post-run-quality`'s 2026-09-17/18
lessons sweep correctly excluded as fleet-wide orchestrator-mechanics rather than its own subject matter.
This is a second, costlier instance of the same excluded defect — recorded here because `truthful-signals`
is this repo's standing owner of orchestrator-platform mechanics on precedent (multiple prior
orchestrator-mechanics lessons and plans already live there).

## Two concrete remedies named by the forwarding message

1. `phase-1-init` writes a `source_id` section for every plan source, including `description` — today
   `phase-1-init` Step 5.1 writes `--source-id` only for the traceable sources (`lesson`, `issue`,
   `recipe`) and explicitly omits it for `description`, which is the default and most common source.
2. The orchestration-verdict detector fails CLOSED on an absent `source_id` — emits
   `detection: indeterminate` rather than a confident `orchestrated: false` — and, critically, KEEPS
   `emit-landing` firing on the indeterminate case rather than suppressing it. A `detection: no_source_id`
   token distinct from `not_orchestrator_pointer` is one option (a distinct token says a pointer was
   never even attempted, vs. one that was read and did not match).
3. Optional third remedy: `orchestrator inbox detect --plan-id` could recover the pointer from a plan's
   own `hand-off_command` (the one-line `/plan-marshall task="implement {spec path}"` pointer every
   orchestrator-staged spec carries) as a fallback when `source_id` is absent but the plan was launched
   from an emitted orchestrator command.

## Governing precedent named by the forwarding message

ADR-009 (*Status reporting fails closed with an explicit unknown state*) is the fail-closed precedent this
detector should follow.

This is a forward, not a fold — `post-run-quality` does not stage anything for this; the fix belongs
here.
