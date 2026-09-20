envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=finding
created=2026-08-01T21:28:05Z

## Finding: stamped `verification.commands` omit `--plan-id`, so running one as-stamped attributes the build to `NO_PLAN`

**Observed in**: main, live, during execution of `mandatory-plan-id-build-results-ledger`.
**Scope**: outside every deliverable of this plan. Deliberately NOT fixed here.

### What was observed

The `verification.commands` stamped into plan artifacts are recorded **without
`--plan-id`**. Running a stamped command verbatim — which is the entire reason it is
stamped — executes a build that attributes itself to `NO_PLAN` rather than to the plan the
command was stamped for.

Observed live, not inferred.

### Why it matters, specifically here

This is notable because **this plan's whole subject is mandatory plan-id**. The plan made
`--plan-id` mandatory on the build surface and made ledger rows carry a real plan id — and
the stamped reproduction commands, which are the artifact a human or agent is most likely
to copy and run, still carry the pre-mandate shape. The result is a stamped command that
is simultaneously (a) presented as the authoritative way to reproduce the plan's
verification and (b) guaranteed to produce a misattributed ledger row when run.

It is a doc-contract divergence between what the system now requires and what the system
itself records as the canonical invocation.

### Suggested shape of a fix (not implemented)

- Include `--plan-id {plan_id}` when stamping `verification.commands`, so a stamped
  command is runnable as-stamped and attributes correctly.
- Add a check that a stamped verification command is *valid under the current mandate* —
  a stamped command that would be rejected or misattributed if run is a stale stamp, and
  should be detectable as such rather than only discoverable by running it.
- Sweep existing stamped artifacts: every plan finalized before this fix carries commands
  with the same defect.
