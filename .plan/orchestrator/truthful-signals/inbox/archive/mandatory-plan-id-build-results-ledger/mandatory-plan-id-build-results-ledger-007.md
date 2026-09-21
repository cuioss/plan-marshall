envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=finding
created=2026-08-01T21:28:00Z

## Finding: daemon-routed builds write their OUTER log outside the plan tree, bypassing `get_build_results_dir`

**Observed in**: main, during execution of `mandatory-plan-id-build-results-ledger`.
**Scope**: outside every deliverable of this plan. Deliberately NOT fixed here.
**Adjacent to**: this plan's D2 (plan-scoped build results).

### What was observed

A daemon-routed build writes its outer log to:

```text
~/.plan-marshall/marshalld/job-logs/
```

which is **outside the plan tree entirely** and does not pass through
`get_build_results_dir`.

The inner wrapper log **does** land plan-scoped — so this plan's D2 deliverable is
correct and complete for the surface it covered. The daemon's outer layer is a **second,
unrelocated log surface** that D2's sweep did not reach.

### Why it matters

The point of relocating build results into the plan tree is that a plan's evidence travels
with the plan: it is discoverable at retrospective time, it is archived with the plan, and
it is attributable. A log that lives in a machine-global daemon directory has none of those
properties — it is not attributable to a plan without correlating job ids by hand, and it
survives (or is lost) independently of the plan it documents.

It also means the D2 claim "build results are plan-scoped" is true of the wrapper layer and
**not** true of the daemon layer, which is exactly the kind of partially-true contract
statement this epic tracks. D2's stated scope should be read as covering the wrapper log
only.

### Suggested shape of a fix (not implemented)

- Route the daemon's outer job log through `get_build_results_dir` for the job's owning
  plan, the same way the wrapper log now is.
- Where the daemon genuinely has no plan context at write time (a job submitted before
  attribution is resolved), keep a machine-global staging write but **relocate on
  completion**, rather than leaving the log permanently outside the plan tree.
- Audit for any further log surfaces that predate `get_build_results_dir`; the observed
  count of unrelocated surfaces is a floor.
