envelope_version=1
sender_type=plan
sender_id=plan-04-autonomy-gate-defaults
epic=operator-ux
kind=candidate-lesson
created=2026-09-07T12:45:52Z

# A timed-out focused build left three deliverables with no test verdict, and the run continued as if verified

component: plan-marshall:phase-5-execute
category: bug
confidence: high
source_signal: qgate finding 1d9ff5 (5-execute), narration field
dedupe_note: Adjacent to candidate 003 (assert_test_identifiers has no could-not-look state) and deliberately separate. That one is a helper conflating two states inside a log it DID read. This one is a verification that never produced a result at all, and a phase that treated the absence as a pass-through. Different site, different fix. Merge only if the epic judges the could-not-look family to be one lesson.

## What happened

Finding `1d9ff5` records the window verbatim: *"This test was inside the unverified window: the phase-5 leaf got a green module-tests verdict after deliverable 1 only, then the focused build timed out during deliverable 2 and deliverables 2-4 landed with no test verdict."*

Three of four deliverables therefore landed with no module-tests result. The failure was found afterwards, at the 6-finalize gate, and only because a Q-Gate pass re-ran the suite.

## Why this is a defect and not just slow infrastructure

A timeout is not a verdict. It is the **absence** of one. The run had three states available — pass, fail, and did-not-complete — and collapsed the third into the first by continuing. The evidence that this is systemic rather than a one-off:

- The same plan's `log_analysis` reports `build_count: 0` and renders build time as `unavailable`, *"never 0"* — so the machinery already knows how to distinguish an unmeasured build from a zero-cost one in the reporting layer, while the execution layer did not distinguish an incomplete verification from a clean one.
- The deliverable most affected (deliverable 2) was the one the operator added mid-outline, so its test surface was the newest and least covered — precisely the surface a skipped verification is most likely to have broken. `1d9ff5` confirms the failing file *"was NOT in deliverable 2's declared test-update set."*

## Corrective

1. A verification step that times out must record `did_not_complete`, and the deliverables it was covering must be marked **unverified** rather than inheriting the last green verdict. Inheriting a verdict across a timeout is the defect.
2. The unverified set must be re-verified before the phase closes, or the phase must close with the unverified deliverables named in its return. A phase that cannot say which of its deliverables carry a test verdict should not report a clean phase.
3. Report the state, not the last-known-good: mirror the `unavailable`-not-`0` discipline the metrics layer already applies.
