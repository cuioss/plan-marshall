envelope_version=1
sender_type=plan
sender_id=plugin-doctor-detector-coverage-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T07:37:11Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
created=2026-08-25

# A zero from a content search proves absence only for the forms the search pattern can express

## Context

Committed at full strength during this finalize, on this plan's own subject. A commit asserted "no
module imports _analyze.py / _validate.py / _fix.py -- a whole-tree search returns zero hits across
5210 files". The sweep pattern was `from X import|import X$`, matching static import spellings only.

## Root cause

This repository's documented mechanism for loading a script module is conftest.py's loader doing
`spec_from_file_location` + `module_from_spec` + `exec_module`, which that regex is structurally
incapable of matching. The test tree loads all three modules at module scope via exactly that
mechanism on every module-tests run -- including the very run the same commit cited as green evidence.
The negative was refuted by the build it quoted. Aggravating: plugin-doctor's own SKILL.md lists
"hand-rolled import preamble (spec_from_file_location / deep Path(__file__).parent chain)" as a shape
it lints for, four lines above where the false claim was written -- the document named the mechanism
that refuted it.

## Proposed action

Add this as an explicit self-review interpretation rule: before publishing a universal negative from a
content search, enumerate the FORMS the target can take (static import, importlib, subprocess-by-path,
dynamic dispatch table, config reference, doc prescription) and confirm the search pattern can express
each one. When it cannot cover every form, report "no STATIC import found", never "nothing imports".

## Evidence

- aspect: script_failure_analysis -- finding c27d5d, filed during the settle band on this plan's own
  subject
- Distinct from the sibling lesson on set/count/partition derivation (4e23cf): here the predicate was
  blind to the target's FORM, not to its population size
