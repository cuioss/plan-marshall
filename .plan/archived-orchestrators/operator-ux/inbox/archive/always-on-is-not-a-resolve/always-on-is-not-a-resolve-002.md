envelope_version=1
sender_type=plan
sender_id=always-on-is-not-a-resolve
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T10:37:08Z

# Self-review at order 7 runs before simplify at order 9, so simplify's edits are structurally never self-reviewed

component: plan-marshall:phase-6-finalize
category: bug
surface: marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md, marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md

## Observed

In the phase-6 settle band, `default:pre-submission-self-review` declares
`order: 7` and `default:finalize-step-simplify` declares `order: 9`. Both are
`head_dependent: true`. The dispatcher iterates the manifest in ascending order,
so on any run where simplify edits source, the sequence is:

1. order 7 — self-review surfaces candidates from the diff, adjudicates, records
   `done` with `head_at_completion = H1`.
2. order 9 — simplify **edits source**; the dispatcher's item-5f commit
   instrumentation commits those edits, advancing HEAD to H2.
3. order 10+ — the band continues forward to `architecture-refresh` and `push`.

Nothing re-runs self-review against H2. The dispatcher's HEAD-dependent re-fire
table only consults `head_at_completion` on **re-entry** into the FOR loop; a
forward pass never revisits an earlier index. So the diff that actually gets
pushed is not the diff self-review examined, and the gap is not a scheduling
accident — it is the fixed consequence of the two `order:` values.

Plan `always-on-is-not-a-resolve` (epic `operator-ux`, PLAN-10) demonstrates it
concretely: simplify made a **production-Python** edit to
`_cmd_domain_detect.py` — deleting a branch and replacing a constant with a
ternary — after self-review had already recorded a clean verdict. Self-review
never saw that edit. The only reason it was examined at all is that the
orchestrator read the diff by hand and re-fired the quality gate.

## Why it matters

`finalize-step-simplify` is the one settle-band step whose entire purpose is to
REWRITE code late, and it is scheduled after the step whose purpose is to
structurally review rewrites. The gate that would catch a simplify-introduced
defect is the gate simplify is guaranteed to run behind.

The exposure is not hypothetical for this class of edit: simplify deletes
branches, collapses near-duplicate returns, and rewrites conditionals — exactly
the shapes self-review's checks (symmetric pairs, contract drift, touched-claim
re-check, count prose) are written to catch. A simplify pass that deletes one arm
of a symmetric pair, or leaves a doc count stale, ships unexamined.

`pre-push-quality-gate` (order 5) has the same relationship to simplify and is
partly protected by the push step's `pre-commit-verify-freshness` precondition,
which notices that the last `kind=build` ledger row predates the working tree.
Self-review has **no** equivalent downstream backstop — nothing later in the band
re-asserts its verdict — so its stale verdict reaches the merge with no signal.

## Directive

Close the ordering hole rather than relying on an orchestrator to notice. Options,
in rough preference order:

1. **Re-order**: move `finalize-step-simplify` ahead of
   `pre-submission-self-review` (simplify < 7), so the self-review examines the
   final settled tree. This is a two-frontmatter-value change and makes the
   settle band read correctly: mutate first, review the mutation, then push.
2. **Re-fire on advance**: have the dispatcher, after item-5f commits a
   `mutates_source: true` step's edits, re-fire every ALREADY-COMPLETED
   `head_dependent` step whose `head_at_completion` the commit invalidated —
   consulting `verdict_currency classify` exactly as the re-entry path does. This
   generalises past this one pair and is the structurally correct fix, at the cost
   of extra gate runs inside a single forward pass.
3. **Minimum**: give self-review the same freshness backstop `push` has, so a
   verdict recorded against a superseded HEAD is at least *reported* as stale
   rather than standing as green.

Whichever is chosen, note that option 2 subsumes a defect already worked around by
hand on this run: after simplify committed, the orchestrator consulted
`verdict_currency classify --step pre-push-quality-gate`, got
`invalidated (verdict_inputs_undeclared)`, and re-ran the gate manually. That
manual step is precisely what option 2 would automate.
