envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:45:27Z

component=plan-marshall:phase-3-outline
category=anti-pattern

# Five of one outline's eight Q-Gate findings were the same mistake: a set stated as complete instead of derived

The 3-outline Q-Gate returned 8 findings. Five are literally the same defect wearing different deliverable numbers — the outline asserted that some set was complete ("only", "all three", "the only prose consumer") and the Q-Gate re-ran the outline's own stated method and got a different answer.

## Evidence (all 3-outline, all resolved `taken_into_account`)

- `ad2d29` — D1's survey pool named two step-doc trees; a third (`marketplace/bundles/*/skills/*/SKILL.md`) holds two configured steps. The outline itself read from that tree in D5 while excluding it from D1's pool.
- `44ee22` — D2 declared module-testing scope "…only" (2 files) while changing 3 scripts. The derived consumer sweep returned the sole existing test of the very function being changed, in neither the scope nor `affected_files`.
- `736b03` — D2's success criterion prescribed its own check ("doc hits are a subset of the edited set") and that check **fails by construction**: 10 doc hits, 4 edited files. The criterion would have been silently reinterpreted at execution time.
- `989858` — D5's "three CERTAIN consumer files" was wrong in BOTH directions: one entry was not reproducible from the stated sweep at all, and six further files in the directory D6 "owns entirely" were declared by nobody.
- `2e1f33` — the assessment channel was empty, so section 2.2 could render no verdict over a population of size zero; recorded as a benign scanned-and-empty zero rather than passed silently.

## Rule

Any claim of the form *only / all / the set is N / nothing else* in an outline must be **produced by an enumeration whose coverage fields are read**, and the enumeration must appear in the deliverable. `ad2d29`'s resolution is the model: it re-derived rather than trusting the finding, and reported `files_scanned 2994, unreadable 0, truncated false, elided 0` alongside the count.

Note `2e1f33`'s discipline as the positive control: a zero over an unpopulated channel was recorded as *could-not-evaluate*, not expanded into 24 vacuous findings and not passed silently. That is the correct handling of the same underlying question.

The signal worth the epic's attention is the RATE: five instances of one archetype inside a single outline pass, in a plan whose request the retrospective separately judged unusually well specified.
