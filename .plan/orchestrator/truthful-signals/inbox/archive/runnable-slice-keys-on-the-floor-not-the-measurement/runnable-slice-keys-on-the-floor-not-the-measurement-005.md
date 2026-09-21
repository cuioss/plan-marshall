envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T04:55:14Z

component=phase-3-outline
category=anti-pattern
created=2026-07-29

# A field-name sweep cannot find a caller-graph hit

Two consecutive outline passes each declared the `execution_tier` consumer table
"complete" while missing `_augment_resolved` in `_cmd_client_handlers.py` — the
SOLE production caller of both changed signatures, serving BOTH `cmd_resolve`
and `cmd_derive_verification`. The Step 0 sweep enumerated field names and
constants but not the three symbols whose SIGNATURES changed. A later
orchestrator-run sweep found 49 files against a 14-file seed, and a SECOND
`_augment_resolved` call site (:338) the outline had also missed.

## Impact

When a plan changes a function's SIGNATURE (not just a field name or constant),
the outline sweep must enumerate call sites of the changed symbols directly
(caller-graph), not just grep for the field/constant names those symbols touch
— a name-only sweep silently drops sole-production-caller call sites.
