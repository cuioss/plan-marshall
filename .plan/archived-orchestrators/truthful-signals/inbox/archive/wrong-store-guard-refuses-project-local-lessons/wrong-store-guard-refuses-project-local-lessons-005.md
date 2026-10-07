envelope_version=1
sender_type=plan
sender_id=wrong-store-guard-refuses-project-local-lessons
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T11:57:09Z

component=plan-marshall:phase-1-init
category=bug
created=2026-07-29

# change-type/scope-estimate heuristics read only the request.md original_input section, mis-routing file-pointer-ingested requests

`change-type-heuristic` and `scope-estimate-heuristic` (Tier-1 recipe-match routing) score only `request.md`'s `original_input` section. On the file-pointer ingestion branch (request given as a pointer to a spec file rather than inline prose), `original_input` holds ONLY the spec preamble, not the spec body. On this plan, `change_type` scored zero on everything, and `scope_estimate` found exactly one path in that preamble — a REFERENCE, not a target — and concluded "surgical". The lane router then routed `light` on that false signal, and `classification_validation` returned a confident `mismatch_count: 0` over a comparison that never saw the real request content.

## Impact

Both heuristics need to read the FULL resolved request content (the spec body reached through the pointer), not just the `original_input` section, whenever the ingestion branch is file-pointer-based. As implemented, a confident `mismatch_count: 0` from `classification_validation` is not trustworthy evidence for file-pointer-ingested requests — the validator was comparing against a starved signal, not a null result. This plan's real change (component-store guard scoping) happened to be small enough that `light` routing worked out, but the false-positive routing signal is a latent risk for a file-pointer request whose actual scope is large.
