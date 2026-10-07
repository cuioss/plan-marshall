envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-28T05:25:33Z

# q-gate-validation Step 3.5 hashing has no script, so leaves hand-write one

## Observed

The second outline-context q-gate-validation dispatch of plan-12-tool-triage reported:
"Helper files written: `.plan/temp/plan-12-tool-triage/hash_deliverables.py` and
`.plan/temp/plan-12-tool-triage/deliverable-hashes.toon`". The first pass likewise reported computing
the hashes "from the raw outline output with the trailing status block removed", noting that a
byte-level mismatch against the stored file would just force a full re-validation.

`q-gate-validation.md` Step 3.5 asks for per-deliverable and `__whole_outline__` content hashes in
`work/deliverable-hashes.toon`, and `planning-outline.md` Step 2b builds its whole re-run economy on
comparing those hashes — yet no `manage-*` verb computes or persists them. Each leaf therefore invents
its own normalisation (and here a throwaway Python script), which:

- breaks "Workflow steps: no improvisation" and the operator rule against hand-made helper scripts
  outside the test suite;
- makes the hash non-deterministic across passes (different leaves, different normalisation), so the
  "content unchanged ⇒ skip re-dispatch" gate can silently never fire, or fire wrongly.

It recurred on the third outline-context pass with a DIFFERENT helper
(`.plan/temp/plan-12-tool-triage/qgate_hash_outline.py`, "reads the outline file directly") — three
passes, three normalisations, two throwaway scripts.

Related inconsistency surfaced by the same pass: the design-model check (phase-3-outline Step 9c) classifies
a skill as LLM-driven when it has no `scripts/`, yet Step 9c's own worked examples call `phase-2-refine`
(no `scripts/`) hybrid — so the validator had to exempt one skill by example while flagging four others
by the heuristic. The rule and its examples disagree.

## Suggested fix

Add a deterministic verb (e.g. on `manage-solution-outline`) that computes and persists the
per-deliverable and whole-outline hashes from the parsed outline, and have Step 3.5 and the Step 2b gate
call it instead of prose-described hashing.
