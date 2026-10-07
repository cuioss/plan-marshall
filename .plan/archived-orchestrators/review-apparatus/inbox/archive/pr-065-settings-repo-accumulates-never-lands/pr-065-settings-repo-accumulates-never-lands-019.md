envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:22:48Z

component=plan-marshall:phase-3-outline
category=improvement
source_signal=qgate_finding
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=qgate finding e2c6d9 (3-outline, taken_into_account — predicted defect did not materialise)

# An outline Q-Gate reasoned over line ranges that execution did not use, and predicted a defect that never happened

Deliverable 7 described a verbatim move as "`== Learnings (lines 108-863)`" and
"`== Charter (lines 864-1091)`". The Q-Gate read the source file directly,
established that line 863 is the `[#charter]` block anchor belonging to the
heading on 864, and predicted the move would carry the anchor into the wrong
file and break `<<charter>>` cross-references. Every other line claim it checked
was accurate.

The predicted defect did not materialise. Execution did not perform the raw
108-863 range move: `README.adoc` was split into `doc/charter.adoc` and
`doc/learnings.adoc` as separate documents, each opening with its own title, and
intra-document `<<anchor>>` refs became inter-document `xref:` forms. The risk
the finding raised was handled, by a different mechanism than the one it assumed.

## The signal

The analysis was rigorous and its object was stale-by-construction: an outline's
line ranges are a description of an intended edit, not a specification execution
is bound to. A Q-Gate finding derived from line arithmetic over a plan's prose
costs a real verification pass and produces a prediction about a transformation
that may not be the one performed.

## Candidate rule

Worth deciding deliberately whether outline-time Q-Gate analysis should reason
over line ranges at all, or should instead require the deliverable to state the
INVARIANT (every anchor travels with its heading; zero unresolved `<<anchor>>`
refs afterwards) so the check survives a change of method. Note that execution's
own verification did exactly that: 1218/1230 lines byte-identical, the 12
differing lines each a repaired xref, zero unresolved anchor refs. That check was
robust to the method change; the line-range one was not.
