envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=finding
created=2026-08-01T21:28:14Z

## Finding: `pre-submission-self-review` returned 4 findings WITHOUT recording a terminal `mark-step-done` outcome

**Observed in**: main, during finalize of `mandatory-plan-id-build-results-ledger`.
**Scope**: outside every deliverable of this plan. Deliberately NOT fixed here.
**Caught by**: the post-dispatch guard.

### What was observed

The `pre-submission-self-review` step returned **4 findings** to the dispatcher but did
**not** record a terminal `mark-step-done` outcome before returning. The omission was
caught by the post-dispatch guard, not by the step itself.

### Why it matters

This is a **record-before-return contract violation inside the finalize machinery
itself** — the layer whose job is to enforce that contract on everything else. Two
consequences:

1. The persisted plan state and the returned payload can disagree. A step that returns
   findings but records nothing leaves `phase_steps` without the row that the
   `phase_steps_complete` handshake invariant depends on.
2. Because the guard is what caught it, the guard is currently the *only* thing standing
   between this and a silently unrecorded step. That is a single point of detection for a
   contract the system treats as structural.

It is worth noting that the guard **worked** — this is a caught defect, not an escaped
one. The finding is that the contract was violated at all, by a component that is itself
part of the enforcement apparatus.

### Suggested shape of a fix (not implemented)

- Make the terminal `mark-step-done` unconditional on the return path of
  `pre-submission-self-review`, including the findings-raised branch.
- Sweep the other finalize step bodies for the same shape — a return path that carries
  findings but skips the terminal record. The observed count of 1 is a floor; this step
  was only noticed because it happened to raise findings on this run.
- Consider whether the post-dispatch guard should *fail* rather than *repair*, so a
  violation is loud at author time instead of absorbed at run time.
