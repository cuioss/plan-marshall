envelope_version=1
sender_type=plan
sender_id=plan-cis-027-graph-merge-drops-every-resolver-edge
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T13:59:35Z

component=plan-marshall:persona-module-tester
category=anti-pattern
created=2026-08-02
bundle=plan-marshall

# Assert the surface the caller queries, not the stage that feeds it

PLAN-CIS-003 (#1074) shipped a deliverable whose stated purpose was to prove the dependency
graph is not empty. That proof passed green on every run while the **live** merged graph
returned `edge_count: 0` — for months, across a landing and a retrospective.

The reason is a one-word substitution in what the test reached for. It asserted the **merge
stage's output** (the per-resolver contribution, which was genuinely non-empty: 29 edges) and
not the **merged graph** (the artifact `graph` / `impact` / `neighbors` / `path` actually
answer from, which was empty). The test named the right property, sampled the right pipeline,
and stopped one stage short of the surface whose emptiness was the defect.

A test written to prove "X is non-empty" that reaches for the stage *before* X is not a weak
test — it is a test of a different proposition, and it will stay green through the entire
lifetime of the defect it was written to exclude.

## Solution

For any test whose value comes from a **downstream** guarantee, assert at the **consumer end**
of the pipeline — the exact call the user makes, with the same arguments and against the same
persisted artifact. Concretely, this plan replaced the merge-output assertion with one against
the merged graph itself (`70b93270e`, `test_merge_stage_produces_edges` explicitly
self-qualifying as "a strictly weaker claim than the graph assertions above").

Authoring check before writing the assertion: *name the command the operator runs to observe
this property. Does the test call it?* If the test calls something one layer nearer the
producer, it is proving the producer, not the guarantee.

## Impact

Applies to every multi-stage pipeline in the substrate — resolver to merge to query, scan to
index to lookup, discovery to registration to dispatch. The recognition signature is a green
proof-of-non-emptiness sitting next to an observably empty user-facing result; when those two
coexist, suspect the assertion's *stage*, not its *strength*.

This is a distinct failure from the classic test-pins-the-defect: the test does not encode the
wrong expectation, it evaluates the right expectation against the wrong object. It therefore
survives review by anyone who reads only the assertion text.
