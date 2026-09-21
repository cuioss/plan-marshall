envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:27:50Z

# Candidate lesson: coverage figures re-derived in transit produced a structurally impossible zero

## Signal source

Q-Gate `6-finalize` finding `9667ee` — "self-review round 16 verifier refused: coverage figures altered in transit". State `verdict_refused`.

## Observation

Two distinct false-clean signals in one forwarded verdict, both on the coverage dimension:

1. **Re-typed figures contradicted the producer.** The author's forwarded `delta_coverage.statement` claimed "24 of 25 ... 0 produced none" and `classes_present_without_candidates: 0 of 5`. The surfacer's own `_format_coverage_statement` is structurally incapable of emitting 0 silent files when `files_with_candidates=24` and `files_in_scope=25` — `silent_files = files_in_scope - files_with_candidates = 1`. The zero was not a measurement; it was a re-derivation that lost the one silent file (`uv.lock`, classified "other", reached by no detector).

2. **A zero was cited from a detector that structurally cannot fire.** The author cited `count_prose: 0` over `test_orchestrator_corpus.py` as evidence the doc-sync block makes no count claims. `count_prose` is scoped to contract sources (`SKILL.md` / `standards/*.md`) and cannot fire on a test `.py` file at all. The zero was a **structural absence of measurement**, presented as a **measurement of absence** — and the block did in fact still make count claims.

## Corrective rule

1. **Forward a producer's coverage figures verbatim off its TOON.** Never re-derive, re-type or summarise them in transit. The verifier here caught the discrepancy only by independently re-running the surfacer and comparing byte-for-byte; round 17 passed once the instruction was "forward verbatim".
2. **When citing a detector's zero, state that detector's population.** A zero over a file the detector does not range over is not evidence about the file. This is the general rule the corpus already carries as "every set-guarding detector must be population-derived — a check that can return 0 from an empty population MUST publish the population size", applied to the *consumer* of the count rather than its producer.

## Why this belongs to truthful-signals

Both halves are the epic's exact theme: a confident zero that hides the caveat that nothing was measured. The remedy is mechanical (verbatim forwarding + published populations), not a matter of author diligence.
