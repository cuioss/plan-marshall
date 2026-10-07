> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# A prose routing table is not an enforcement boundary — only the callee can refuse an off-routing dispatch

**Epic:** review-apparatus
**Branch prefix:** fix

## Problem

The merge routing in `branch-cleanup.md` is a two-branch decision expressed in **workflow prose**: with
`use_merge_queue: true` dispatch the merge-queue verb, otherwise the direct-merge path. Both branches
are documented, both reachable, and the plumbing feeding the decision was **verified correct**.

The verb actually dispatched in the incident that produced this plan was a third one — **named on
neither branch**. ⛔ **The dispatch did not take the wrong branch; it left the routing entirely**, and
landed on the single merge-shaped verb with no preflight, no readiness poll, and no post-merge
corroboration. That verb returned `merged: true` for a PR that closed **unmerged** and had its branch
deleted.

⭐⭐ **The structural claim, and it is what this plan is about:**

> **A prose routing table constrains a compliant caller and constrains nothing else.**

Every verb reachable outside the routing is a **silent alternative entry point**, and ⛔ **the
least-defended verb is the one an off-routing dispatch is most likely to reach — precisely because it is
the one with the fewest arguments and the fewest checks.**

⭐ **The asymmetry is what made the incident expensive.** The off-routing target was not merely
un-preflighted; it was the **only** merge-shaped verb with no post-merge check. **The departure and the
false green were the same event only because containment was absent at exactly the point the routing
did not cover.**

⛔⛔ **WHY the executor left the routing remains UNESTABLISHED.** No artifact recorded the decision.
**This plan does not attempt to answer it and must not claim to.** It generalises the *containment*,
which is a different and independently valuable thing.

## Goal

Every verb that a documented route deliberately excludes refuses an off-routing dispatch **at the
callee** — the only party present on every path — and a departure from a route is recorded at the
moment it happens rather than reconstructed afterwards from its damage.

## Deliverables

Four.

1. **D0 — GATE, mutates nothing: DERIVE the population of prose-routed verb sets in the CI abstraction.**
   The shape to match is four-part: **(a)** a documented multi-branch route, **(b)** a sibling verb
   reachable outside it, **(c)** asymmetric checking across the siblings, **(d)** at least one member
   destructive or irreversible.
   ⛔ **Derive from each provider's dispatch registry.** The method is already established by the plan
   that shipped the first instance, along with its counts — **reuse that derivation rather than
   re-inventing one**, and reuse its central finding: a hand-list of two sites understated the real
   population by a factor of four.
   ⛔ **This deliverable HALTS the plan** if the registries cannot be enumerated from the tree. Do not
   hand-list the verb sets — a hand-maintained list of the sites that need guarding is the same defect
   in a new place.
   ⭐ **A null result is a valid, publishable outcome.** *"The merge set is the only instance"* is worth
   knowing and closes the line. Report it as a result, not as a failure to find something.
   *Done when:* the population is derived and published with its size and its derivation method, or the
   null result is stated with the same evidence.

2. **D1 — callee-side refusal for every member D0 identifies.** The refusal lives at the **callee**,
   because that is the only party present on every path — a caller-side rule is exactly what was
   bypassed.
   ⚠ **The reference implementation already exists** for the merge-shaped verbs: the direct-merge verb
   now carries a base-branch queue preflight and refuses the off-routing dispatch itself. ⛔ **Do not
   re-do it — use it as the reference shape** and extend to the rest.
   ⚠ **Enumerate callers before refusing anything.** Whether any legitimate caller depends on reaching a
   member outside its route is **UNKNOWN**. A refusal that breaks a sanctioned path trades this defect
   for an outage.
   *Done when:* every D0 member refuses an off-routing dispatch, and the caller enumeration is published
   alongside — including any sanctioned exception found and how it is preserved.

3. **D2 — observability at the routing decision, not only at the refusal.** The reference plan
   instrumented all four sites of the routing flag so a future departure is **recorded rather than
   inferred**. Extend that principle to whatever D0 finds.
   ⭐ **This is the deliverable that could eventually answer the open why-question.** It cannot answer it
   retroactively, but it stops the next departure being unexplainable.
   *Done when:* a departure from a documented route emits a record naming the route, the expected
   branch, and the verb actually dispatched.

4. **D3 — tests, each verified to FAIL pre-fix.** (a) An off-routing dispatch to each D0 member is
   refused at the callee. (b) The compliant route still succeeds unchanged. (c) The D0 population is
   **derived**, its **non-emptiness asserted first**, and every member covered — copy the derivation
   pattern from `test/_shared/_dispatch_roster.py`.
   ⛔ This epic has been bitten repeatedly by set-guards that pass on an empty population. A test that
   iterates an empty derived set and reports success is the defect, not the check.
   *Done when:* all three hold and the population size appears in the test's own output.

## Out of scope

- **Strengthening the prose.** The routing was already documented on both branches and was correct.
  ⭐ **A caller-side rule that already exists and was already bypassed cannot be fixed by writing it
  more emphatically** — that is this epic's defending-documentation archetype, and a plan that only
  rewords the route reproduces the defect it is closing.
- **Treating "the caller is documented to route correctly" as a guarantee**, anywhere in scope. It is an
  unverified assumption, and this whole plan is the consequence of it having been treated as a guarantee
  once.
- **Answering why the executor left the routing.** Unestablished, and deliberately not attempted — no
  artifact recorded the decision. D2 makes the *next* one answerable; it cannot recover this one.
- **Expanding into non-CI verb sets** without D0 evidence. The claim is about this abstraction.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` and
  `github_ops.py` — the GitHub dispatch registry.
- `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py` — the
  GitLab dispatch registry.
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py` and `ci_base.py` — the
  router that performs the dispatch.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — the prose
  routing table, **read for D0's shape-match**. ⚠ Not necessarily edited: see Out of scope, which
  forbids fixing this by strengthening prose.
- ⚠ **Several of these were modified by a recent merged PR. Re-ground every reference against merged
  `main`.**
- **HYPOTHESIS**: whatever other prose-routed verb sets D0 derives. The list above is the derivation's
  **input**, not its answer.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The dispatched verb was named on neither documented branch | OBSERVED | The routing table in `branch-cleanup.md` versus the verb names in the CI dispatch registry |
| The routing flag was correctly plumbed and present in the payload | OBSERVED | The four sites that read the flag — the plumbing is not the defect |
| Checking is **asymmetric** across the merge-shaped verbs, and the off-routing target was the only one with no post-merge check | OBSERVED | Compare the merge-shaped handlers in the GitHub dispatch registry side by side |
| A hand-list of routed sites understated the derived population several-fold | OBSERVED | Re-run the registry derivation and compare against any hand-list you find in the docs |
| Other prose-routed verb sets share the four-part shape | HYPOTHESIS | **D0 is exactly this test.** ⭐ A null result is publishable |
| Some legitimate caller depends on reaching a D0 member outside its route | UNKNOWN | **Enumerate callers before D1 refuses anything** — a refusal that breaks a sanctioned path trades this defect for an outage |
| Why the executor left the routing | ⛔ UNESTABLISHED | **Explicitly not claimed and not investigated.** Do not let the run manufacture an explanation |

⚠ **Every count in this plan is a lead** — handler counts, merge-shaped counts, site counts. They come
from a prior derivation against an older tree. **Re-derive them; do not cite them.**

⛔ **Do not go looking for `.plan/`.** The incident record and the inbox message behind this plan are
git-ignored and **absent from your clone**. Everything needed is restated here.

## Verification

- Full verify; read the payload's `status` / `errors[]`, not the exit code.
- **Every D3 test proven to fail pre-fix by mutation**, and the population size published in the test
  output so a passing run is distinguishable from an empty one.
- **Publish the derived population and the caller enumeration in the run report**, each with the method
  used. This plan's whole subject is a list that was smaller than reality; its own lists must not repeat
  that.
- ⭐ **Cold read, aimed at the refusal message.** D1 makes a verb refuse a dispatch. Have the pre-PR
  verification sub-agent read the refusal text **cold** and answer: *what did I do wrong, and what
  should I have called instead?* If the message does not lead a reader to the correct routed verb, the
  refusal is a wall rather than a boundary — it will be worked around, not obeyed.

## Notes

- **The instance is fixed; the pattern is not known to be unique to it** — that is the entire reason
  this plan exists. It generalises a shipped one-site fix, and its reference implementation is that
  fix.
- **Sequencing.** Nothing blocks it. ⚠ It **touches the CI abstraction's verb surface, which another
  staged plan's derivation also crosses.** Sequence, never pair — and **if D0 shows the two derivations
  are the same population viewed differently, say so rather than shipping two.**
- **Why callee-side is the load-bearing choice.** The caller can be a workflow doc, a dispatched leaf,
  a script, or a person. Only the callee is present on all four paths. Any remedy that assumes a
  particular caller reinstates the assumption this plan exists to remove.
