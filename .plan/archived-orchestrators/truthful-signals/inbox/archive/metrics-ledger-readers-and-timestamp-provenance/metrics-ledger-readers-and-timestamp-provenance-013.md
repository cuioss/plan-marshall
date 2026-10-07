envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T20:12:34Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
confidence=high
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_pr=1342

# A defect class closed by instance count left a third copy at the render site

## Context

This plan widened a gate: `_sequence_build_minimality_plan` moved from a
denominator-only condition to `has_ledger and wall_clock_seconds > 0`, so an absent
LEDGER also withholds the share. The pre-change, denominator-only wording was restated in
several places.

One round filed the drift TWICE — findings `24510f` and `891386` — and commit `20bc5b50e`
closed exactly those two, on the stated reasoning that "a second copy is one more thing
to drift".

The next round found a THIRD copy: finding `692ad6`, in `audit.py` at the RENDER SITE —
the one place a reader looks when `n/a` actually appears, still answering with one of the
two conditions. The finding names the pattern in its own words: "This is the THIRD member
of the exact class commit 20bc5b50e filed twice and closed only twice."

## Root cause

The fixer treated the round's finding list as the class membership. It is a SAMPLE. The
round enumerated what its checks surfaced on the surfaces they scanned; nothing in that
process asserted the enumeration was complete, and no population size was published
against which "two" could be read as "all".

The shape is diagnostic: both closed copies were in DOCUMENTATION, and the survivor was a
CODE COMMENT at the render site — a different surface class, and exactly the class a
doc-oriented sweep under-samples. The remedy the fixer chose was right (deletion); the
scope it was applied at was not.

## Proposed action

When a self-review finding is resolved by removing a restatement of a changed contract,
treat the fix as a CLASS fix, not an instance fix: sweep for every restatement of the same
fact across code comments, docstrings, argparse help and documentation before closing, and
record the swept population beside the count fixed. "Fixed 2" with no population is
indistinguishable from "fixed 2 of 3", and reads as the former.

This is the repository's own recurring archetype — a reviewer's list of call sites is a
sample, not an enumeration — recurring inside the loop built to catch that class.

## Evidence

- findings 24510f and 891386 (round N; both closed by commit 20bc5b50e)
- finding 692ad6 (round N+1; audit.py:6495, third member; closed by commit 3aef9f7a1)
- 692ad6 also records a matched NEGATIVE CONTROL: the adjacent comment at
  audit.py:4156-4159 was examined and correctly ruled NOT a member, being explicitly
  denominator-scoped with the widened rule stated four lines below it
