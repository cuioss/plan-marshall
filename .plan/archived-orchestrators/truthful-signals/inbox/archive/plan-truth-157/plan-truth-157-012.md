envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:00:23Z

component=plan-marshall:phase-3-outline
category=anti-pattern
bundle=plan-marshall

# When a deliverable edits a site guarded by a LATER deliverable's test, copy the guard criterion onto the editing deliverable

`orchestration-model.md` is a member of `_KNOWN_DISPATCH_DOCS` in
`test/plan-marshall/plan-orchestrator/test_orchestrator_dispatch_workflow_pin.py`
and carries exactly one `effort resolve-target --role orchestrator` invocation.
Deliverable 2 rewrote the Effort-dimension bullet — the bullet that enumerates the
sanctioned dispatches, and where that invocation sits.

Deliverables 3 and 4 each carried an explicit verification criterion requiring
that every such invocation in the edited doc still carries `--workflow`.
Deliverable 2, the one actually editing that bullet, carried no such criterion.
Its scoped plugin-doctor verification cannot detect a change to the invocation
form, and the pinning test only runs at deliverable 6 — so a regression introduced
at deliverable 2 would surface several deliverables later, far from its cause.

Source record: Q-Gate finding `26e19d`, phase `3-outline`, resolution `accepted`.

## Solution

Two moves, both at planning time:

- Copy the sibling deliverables' invocation-form criterion onto the deliverable
  that edits the guarded site.
- Declare the guarding test file as a read-intent entry on that deliverable, so
  the coupling is visible in the footprint.

More generally: when deliverable N edits a site whose guard runs at deliverable
M > N, the criterion belongs on N. Distance between cause and detection is the
cost being avoided.

## Impact

The feared regression did not occur — at HEAD the canonical dispatch form still
carries `--workflow` on the `effort resolve-target --role orchestrator.SURFACE`
invocation, and the pin test ran green in the pre-push quality gate. Accepted as a
known outline-criterion gap. The rule generalizes to any plan whose verification
is back-loaded relative to its edits.
