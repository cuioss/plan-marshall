envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:03:06Z

component=plan-marshall:plan-orchestrator
category=anti-pattern
bundle=plan-marshall

# Delete the completeness word — re-enumerating a derived set re-opens the same drift on the next edit

`analyze.md`'s inline-only bullet asserted "and every APPLY (write-freedom)" and then
enumerated by step item, which reads as a CLOSED index — reinforced because the same
bullet group says the dispatchable bullets "are a complete index of them", so a
reader carries that framing across.

The enumeration was not complete. Three `epic.md` Open Defect writes the document
itself mandates were absent from it: Step 3 item 3 (an invalid message recorded as an
Open Defect naming the validator error code), Step 3 item 4a (an archive failure
recorded as an Open Defect naming the filename and error code), and the Step 4
`complete: false` landing-check branch (recorded as an Open Defect naming the message
and `missing_keys`).

Two readings: (a) the list is the complete set of applies, so an unlisted write is
not one; (b) the list is illustrative. Reading (a) is what the wording supports, and
it is false.

The sibling `decompose.md` gets the framing right by contrast — it says "each
exclusion naming the test it fails", a PER-EXCLUSION claim rather than a set claim, so
its omission of the Step 3 workstream-charter Write is correct: Step 3 is already
excluded on fork-freedom.

Source record: Q-Gate finding `6abd2a`, phase `6-finalize`, defect_class
`ambiguous_wording`, resolution `fixed` in commit `04f12a22b`.

## Solution

The convergent fix is DELETION of the completeness word, not appending the three
missing items — because re-enumerating a derived set re-opens the same drift at the
next edit. Drop "every", or replace the enumeration with a POINTER at the steps.

Prefer the per-member claim form (the sibling's "each exclusion naming the test it
fails") over the set claim form: a per-member claim stays true as members are added,
while a set claim silently becomes false.

## Impact

This is the terminating move for the restatement family generally: replace the
restatement with a pointer at its source. Closure language over a derived set is a
maintenance liability even when it is currently accurate.
