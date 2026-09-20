envelope_version=1
sender_type=plan
sender_id=post-merge-review-findings-untriaged-in-main
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:44:16Z

component=plan-marshall:phase-5-execute
category=bug
created=2026-07-29
bundle=plan-marshall

# Scope-deviation rebinding recorded as "fixed" instead of as a scope widening

Six findings were dispositioned "fixed" with detail "Routed to D3 for the edit" while their target
files were never touched. Root cause: D3's file scope was an outline-time n=4 upper bound, and D2's
rebinding of those six findings onto D3 was supposed to widen that scope via the scope-deviation
gate. Instead the rebinding itself was recorded as the disposition ("fixed"), so the gate never fired
and the files never got edited. No existing gate caught this — it surfaced only via
lessons-housekeeping, after the fact.

## Solution

When a finding is rebound onto an existing deliverable whose file-scope bound it exceeds, the
rebinding action must itself invoke the scope-deviation gate (widening the deliverable's recorded
file scope) BEFORE the finding can be marked "fixed" against that deliverable. A disposition of
"fixed" must be gated on an actual diff touching the claimed file, not on the rebinding event alone.

## Impact

Any finding routed to an existing deliverable, rather than fixed directly, is at risk of the same
false-green disposition — the finding's own record shows "fixed" while nothing changed on disk. This
is the epic's own recurring theme: a confident signal (a "fixed" disposition) hiding a caveat (no
file was actually touched).
