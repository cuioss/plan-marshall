envelope_version=1
sender_type=plan
sender_id=plan-cis-027-graph-merge-drops-every-resolver-edge
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T14:00:18Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
created=2026-08-02
bundle=pm-plugin-development

# A test name and docstring are a coverage claim — do not promise universal and assert existential

Q-Gate finding `d864ee` (self-review, 6-finalize) on
`test/pm-plugin-development/plan-marshall-plugin/test_graph_family_bundle_project.py`:

- Test name: `test_graph_edges_are_stamped_by_the_resolvers_not_declared`
- Docstring: *"The surviving edges carry resolver provenance"*
- Actual assertion: `resolver_stamped` is a **filtered subset**, and the assert requires only
  that it be **non-empty**.

Both the name and the docstring parse as a **universal** claim over every graph edge. The
assertion is **existential**: one resolver-stamped edge passes while every other edge could be
stamped `declared` or `sibling-cross-link`. A maintainer reading the roster of test names —
which is exactly how coverage gets assessed in review — would believe universal
resolver-stamping is pinned when nothing pins it.

The signal that this was a real gap rather than a stylistic quibble came from the file itself:
the sibling `test_merge_stage_produces_edges` explicitly self-qualifies its own claim strength
("a strictly weaker claim than the graph assertions above"). The file's established convention
was to state assertion strength precisely; this test silently broke it.

## Solution

Pick one and make the three agree — name, docstring, assertion:

- **Narrow the claim** to what is asserted: `test_at_least_one_graph_edge_is_stamped_by_a_resolver_not_declared`,
  with a docstring stating the existential claim explicitly *and why universal would be wrong
  here* (some edges legitimately are declared). This is what shipped (`a8695473d`).
- **Or strengthen the assertion** to the universal claim the wording already promises.

Never leave the gap open by tightening only the prose.

## Impact

Applies to every test whose name or docstring quantifies over a set — "all", "every", "the
edges", a bare plural. The recognition signature is a **filtered subset plus a non-emptiness
assertion** sitting under a plural, unqualified name: that combination is always existential,
however universal the name reads.

Adjacent to the corpus's standing rule that *N passing checks of a pure function is one
assertion repeated N times*: both are cases where the surface strength of a test overstates the
proposition actually pinned. Coverage is read off names far more often than off assertion
bodies, which is what makes the mismatch expensive.
