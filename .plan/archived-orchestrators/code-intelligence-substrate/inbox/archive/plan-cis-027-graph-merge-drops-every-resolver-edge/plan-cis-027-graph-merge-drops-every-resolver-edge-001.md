envelope_version=1
sender_type=plan
sender_id=plan-cis-027-graph-merge-drops-every-resolver-edge
epic=code-intelligence-substrate
kind=landing
created=2026-08-02T13:58:33Z

## What landed

**PLAN-CIS-027 — "29 resolver edges become zero graph edges"**
PR **#1079** — `fix(manage-architecture): recover graph edges dropped by the resolver merge`
Branch `feature/plan-cis-027-graph-merge-drops-every-resolver-edge`, 5 commits, head `aefa66e`.

### D1 — mechanism derived (the plan's premise, settled)

None of the three UNCONFIRMED candidates named in the request was the mechanism. The real
cause is in `_cmd_client_query.py`:

`_declared_dependencies` decided *"is this module declared?"* with a **key-membership** test.
`architecture init` seeds an **empty** `internal_dependencies` stub into every module's
`enriched.json`, so every module read as *"declared, with zero dependencies."* The
declared-wins precedence branch then replaced each module's resolver-derived edge set with
that empty list. The resolvers were never broken — `markdown,24,ok` · `maven,0,ok` ·
`python,5,ok` reported 29 edges and status `ok` the whole time, while the merged graph
reported `edge_count: 0` with all 12 modules listed as both roots and leaves.

### D2 — fix

Only a **non-empty** list counts as a declaration now, at **both** precedence sources (the
`enriched.json` overlay and `derived.json`). The guard stays the single precedence authority
shared by `_build_deps_and_producers` and `_derive_edges`, so the enrichment-skip population
and the discard population cannot drift apart.

Hardening in the same diff (ADR-014): a declaration that genuinely *does* discard derived
edges now appends a `declared:`-prefixed suppression note to the **losing resolver's own
report**, so a declared-wins overwrite can never again be silent.

### D3 — the false-closed evidence corrected

PLAN-CIS-003 / #1074's D4 "non-empty graph" proof asserted the **merge stage's output**, not
the **merged graph** the query family answers from — which is why it passed green against a
live `edge_count: 0`. Replaced by an assertion against the merged graph itself
(`70b93270e`), plus resolver-provenance coverage in
`test/plan-marshall/manage-architecture/test_graph_resolver_provenance.py`.

### D4/D5 — contract and doc surfaces

Declared-vs-derived precedence and the one-resolver-id-per-bundle cardinality are now
first-class statements in `ext-point-derivation-resolver.md`. The roster-coupled resolver
counts and duplicate roster enumerations were removed from five surfaces
(`ext-point-derivation-resolver.md`, `module-discovery.md`, `extension_base.py`,
`extension-architecture.adoc`, `code-intelligence.adoc`), leaving **§ Current
implementations** as the single place the shipped roster is enumerated.

The module-granular-vs-component-granular exposure question PLAN-CIS-003 left unsettled did
**not** force a loop-back: module granularity proved to be the right exposure for the query
family, so D2 stayed a fix rather than becoming a design decision.

## Quality signals

- Pre-push quality-gate, verify and coverage: green (whole-tree, re-fired at `aefa66e`).
- plugin-doctor: clean, 3 skills gated.
- ci-verify: all checks green.
- Pre-submission self-review: 1 finding found **and fixed in-run** (existential-vs-universal
  test claim).
- Automated review: CodeRabbit 1 actionable comment, operator SPLIT disposition — test site
  fixed, doc site declined with recorded rationale. pr-agent reported no issues. **Sourcery
  absent from this PR.**

## Residue the epic should track

1. **Sourcery did not participate on #1079.** Two reviewers compared, not three. Consistent
   with the standing `review-apparatus` concern; noted here, not actioned.
2. **Gated plans are now unblocked.** PLAN-CIS-004 and PLAN-CIS-026 both add resolvers
   through this same merge path and were gated on this landing. They can be queued.
3. **The `declared:` suppression note is a new consumer-visible signal.** Any epic plan that
   reads resolver reports should expect the prefixed note on a resolver whose edges lost to
   a declaration — it is evidence of a *deliberate* discard, not a failure.
4. **Doc-site declination is on the record.** The CodeRabbit request to make the
   `ext-point-derivation-resolver.md` roster table generated/non-exhaustive was declined
   (decisions `ee3ca3`, `7a802f`, `14b0d9`): that table is the single enumeration point this
   plan deliberately established. If a later plan revisits roster generation, it should start
   from those decisions rather than re-litigating from the review comment.
5. **Post-merge PR revisit still owed** — the merge routinely outruns the review; #1079 and
   its siblings should be re-scanned for late review comments.
