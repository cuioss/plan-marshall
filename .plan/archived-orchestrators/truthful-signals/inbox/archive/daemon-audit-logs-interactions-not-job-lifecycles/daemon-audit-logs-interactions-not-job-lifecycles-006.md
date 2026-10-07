envelope_version=1
sender_type=plan
sender_id=daemon-audit-logs-interactions-not-job-lifecycles
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T15:48:24Z

component=plan-marshall:phase-3-outline
category=improvement
bundle=plan-marshall

# A read-time join between two stores is only as answerable as the SHORTER retention window

## What was observed

D1 was a gate deliverable choosing between three layers for answering "what happened to
this job?": emit job-lifecycle events, join live job state at read time, or a hybrid.
The read-time join looks like the cheaper, more normalized option — no new record kind,
no new write path, one source of truth per fact.

It is wrong here, and the deciding fact is a **retention asymmetry** between the two
stores:

- `_marshalld_journal.py`: `DEFAULT_RETENTION_SECONDS = 3600` — a terminal result is
  readable for one hour after completion, then GC'd.
- `_marshalld_audit.py`: audit rows live **7 days**.

A read-time join could therefore answer for only the **first hour of a row's
seven-day life**; for the remaining 99.4% of the window the join returns nothing and the
surface is back to "unanswerable". The plan chose emission into the 7-day store, and the
rationale is now recorded in the audit module's docstring.

## Why it was nearly missed

Neither the plan spec nor either module's documentation surfaced the asymmetry. The two
retention windows are declared in **different files**, in different units (`3600`
seconds vs a 7-day constant), each locally well-documented in isolation. Nothing put
them side by side, and nothing flagged that a design pattern spanning both stores is
bounded by the shorter one. Each module's docs were individually correct and jointly
silent on the fact that decided the design.

## Proposed rule

When a design joins or correlates two persistent stores, the retention/GC window of
**each** store is a first-class input to the layer choice, and the joinable lifetime is
the **minimum** of the two — never the lifetime of the store the reader is looking at.
An outline that proposes a read-time join should be required to state both windows
explicitly and the resulting answerable window, rather than leaving retention as an
implementation detail discovered during execution.

## Note on classification

This may read as durable project KNOWLEDGE (a `manage-build-server` fact about the two
stores' windows) rather than an ACTIONABLE lesson. Both edges are real: the concrete
3600 s / 7-day pair is a module fact, while "a cross-store join is bounded by the
shorter window, and outline must state both" is a transferable design rule. Classified
by the orchestrator, per the B4 contract.
