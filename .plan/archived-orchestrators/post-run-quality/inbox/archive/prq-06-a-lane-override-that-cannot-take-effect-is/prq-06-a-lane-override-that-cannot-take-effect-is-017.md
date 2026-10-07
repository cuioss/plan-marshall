envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:46:42Z

component=plan-marshall:phase-6-finalize
category=bug

# Two doc claims shipped unverified against the code they describe: an unqualified absence claim, and an example contradicting its own function's invariant

Two 6-finalize findings, both `fixed`, both the same root question — *was this sentence checked against the code it describes?*

## Instance 1 — an absence claim with no scope qualifier (`420319`)

`lessons-capture.md` consequence 3 ended: "…and none of those reads the key — **its sole reader** is `_read_frontmatter_lane`." The preceding clause was scoped to the composer's four helpers, but "its sole reader" carried no qualifier and reads as a whole-codebase absence claim.

It was false. `plugin-doctor/scripts/_analyze_lane_frontmatter.py` reads `lane.get('prunable_when')` and enforces the present-iff-class-prunable rule — it is what validates this very frontmatter change — and `plan-retrospective/scripts/check-routing-decisions.py` maps predicate ids. The finding's own scope statement is the model: `architecture search --content --pattern prunable_when`, 40 matches across 20 files, two live non-comment reads outside the named function.

The practical risk is the one the sentence invites: a later reader concludes nothing validates `prunable_when` and drops it, tripping the very rule that validates it.

## Instance 2 — an example arithmetically impossible against its producer (`63774a`)

The `lanes preview` Output TOON example showed `full` keeping 14, `standard` keeping 12 with `dropped[0]`, and `minimal` keeping 6 with `dropped[1]`. `_apply_lane_resolution` PARTITIONS the candidate list — `kept + dropped == candidates` — so over one candidate set `standard` must show 2 dropped records and `minimal` 8. A reader consulting the example would conclude `dropped` reports only a subset of removals, which is the opposite of what the function's own docstring promises ("one `{step,reason}` record per removed element").

## Rule

- **Every absence, uniqueness, or "sole/only/none" claim carries the scope it was derived over, in the sentence itself.** "Its sole reader on the compose path" is a true, useful claim; "its sole reader" is an unbounded one nobody verified. If the derivation covered one code path, the sentence says so.
- **A hand-written example is an assertion about the producer and must satisfy the producer's invariants.** When the function partitions, the example's numbers must sum. Where keeping them consistent is fragile, elide with the existing `[ ... ]` convention rather than inventing numbers.

Both defects were introduced BY this plan, in documents this plan was editing for unrelated reasons — the cost of touching a doc includes verifying the claims one is writing into it.
