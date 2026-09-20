# PLAN-PR-020: A prose routing table is not an enforcement boundary — only the callee can refuse an off-routing dispatch

epic: review-apparatus
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Provenance — the generalization PLAN-PR-009 shipped one instance of and asked us to record

Staged 2026-08-03 from `merge-queue-enqueue-does-not-take-006` (PR #1087). ⭐ **The instance is fixed;
the pattern is not known to be unique to it, and that is the entire reason this exists.**

## The established mechanism, not a hypothesis

`branch-cleanup`'s merge routing is a two-branch decision expressed in **workflow prose**: with
`use_merge_queue: true` dispatch `ci pr merge-queue`, otherwise the direct-merge path. Both branches are
documented, both reachable, and the plumbing feeding the decision was **verified correct**.

The verb actually dispatched in the #1081 incident was **`ci pr merge` — named on NEITHER branch.**
⛔ **The dispatch did not take the wrong branch; it left the routing entirely**, and landed on the single
merge-shaped verb with no preflight, no readiness poll, and no post-merge corroboration. That verb
returned `merged: true` for a PR that closed **unmerged**.

## ⭐⭐ The structural claim — this is what the plan is about

> **A prose routing table constrains a compliant caller and constrains nothing else.**

Every verb reachable outside the routing is a **silent alternative entry point**, and ⛔ **the
least-defended verb is the one an off-routing dispatch is most likely to reach — precisely because it is
the one with the fewest arguments and the fewest checks.**

⭐ **The asymmetry is what made #1081 expensive**, and it must survive into this plan's framing: the
off-routing target was not merely un-preflighted, it was the **only** merge-shaped verb with no
post-merge check. **The departure and the false green are the same event only because containment was
absent at exactly the point the routing did not cover.**

⛔⛔ **WHY the executor left the routing remains UNESTABLISHED.** No artifact recorded the decision.
**This plan does not attempt to answer it and must not claim to.** It generalises the *containment*, which
is a different and independently valuable thing. The open question stays with the epic.

## Deliverables

1. **D1 — GATE (mutates nothing): DERIVE the population of prose-routed verb sets in the CI abstraction.**
   The shape to match: **(a)** a documented multi-branch route, **(b)** a sibling verb reachable outside
   it, **(c)** asymmetric checking across the siblings, **(d)** at least one member destructive or
   irreversible. ⛔ **Derive from each provider's dispatch registry** — PLAN-PR-009 established the method
   and the counts (GitHub 37 / GitLab 35 handlers, 8 merge-shaped), so **reuse that derivation rather than
   re-inventing it**, and reuse its finding that a hand-list of 2 sites understated the real 8.
   ⭐ **A null result is a valid, publishable outcome** — "the merge set is the only instance" is worth
   knowing and closes the line.
2. **D2 — callee-side refusal for every member D1 identifies.** The refusal lives at the **callee**, which
   is the only party present on every path. ⚠ **PLAN-PR-009 already shipped this for the merge-shaped
   verbs** (`cmd_pr_merge` carries the base-branch queue preflight and refuses the off-routing dispatch
   itself) — ⛔ **do not re-do it; use it as the reference shape** and extend to the rest.
3. **D3 — observability at the routing decision, not only at the refusal.** PLAN-PR-009 instrumented all
   four `use_merge_queue` sites so a future departure is **recorded rather than inferred**. Extend that
   principle to whatever D1 finds. ⭐ **This is the deliverable that could eventually answer the open
   why-question** — it cannot answer it retroactively, but it stops the next departure being unexplainable.
4. **D4 — tests, each verified to FAIL pre-fix.** (a) An off-routing dispatch to each D1 member is refused
   at the callee. (b) The compliant route still succeeds unchanged. (c) The D1 population is **derived,
   non-empty-asserted FIRST**, and every member covered — copy `test/_shared/_dispatch_roster.py`.
   ⛔ This epic has been bitten repeatedly by set-guards that pass on an empty population.

## ⛔ Prohibited remedies

- **Do NOT fix this by strengthening the prose.** The routing was already documented on both branches and
  correct. ⭐ **A caller-side rule that already exists and was already bypassed cannot be fixed by writing
  it more emphatically** — that is this epic's defending-documentation archetype.
- ⚠ **Do NOT treat "the caller is documented to route correctly" as a guarantee anywhere in scope.** It is
  an unverified assumption; the whole plan is the consequence of it having been treated as a guarantee once.
- **Do NOT expand into non-CI verb sets** without D1 evidence. The claim is about this abstraction.

## Claim Labels

- **OBSERVED** (first-party to PLAN-PR-009, #1087): the off-routing dispatch; `use_merge_queue: true`
  correctly plumbed and present in the payload; the asymmetric checking across merge-shaped verbs; the
  derived handler counts.
- ⛔ **UNESTABLISHED and explicitly not claimed**: why the executor left the routing.
- ⚠ **HYPOTHESIS**: that other prose-routed verb sets share the shape. **D1 is exactly this test.**
- ⚠ **UNKNOWN**: whether any legitimate caller depends on reaching a D1 member outside its route.
  **Enumerate callers before D2 refuses anything** — a refusal that breaks a sanctioned path trades this
  defect for an outage.

## Expected Surface

⛔ **Added 2026-08-08 — this spec was staged WITHOUT one, so the `next` verb's disjointness admission
test had nothing to read.**

- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
  and `github_ops.py` — the GitHub dispatch registry (37 handlers, 8 merge-shaped, per `#1087`'s
  derivation). ⚠ `github_ops.py` **modified by `#1118`** (+160 lines).
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py`
  — the GitLab dispatch registry (35 handlers). ⚠ **Modified by `#1118`** (+34 lines).
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py` +
  `ci_base.py` — the router that performs the dispatch. ⚠ `ci_base.py` **modified by `#1118`**.
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
  — the prose routing table itself, read for D1's shape-match (not necessarily edited: see § Prohibited
  remedies, which forbids fixing this by strengthening prose). ⚠ **Modified by `#1118`** (+64 lines).
- **HYPOTHESIS** (verify-at-outline): the other prose-routed verb sets D1 derives. **A null result is
  publishable** — the surface above is the derivation's INPUT, not its answer.

## Dependencies and Sequencing

- ⛔ **Sequence AFTER nothing; PLAN-PR-009 is SHIPPED (#1087)** and is this plan's reference implementation.
- ⚠ Touches the CI abstraction's verb surface, which **PLAN-PR-017's derivation also crosses**
  (`ci.py` / the finalize merge-and-review path). **Sequence, never pair** — and if D1 shows the two
  derivations are the same population viewed differently, **say so rather than shipping two.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-020-a-prose-routing-table-is-not-an-enforcement-boundary.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
