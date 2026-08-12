# Run report — 060-a-prose-routing-table-is-not-an-enforcement-boundary (run 01)

**Date (UTC):** 2026-08-12    **Branch:** claude/prose-routing-table-boundary-30xrzc (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (first action)
- `plan-marshall:ref-code-quality` (bundle path)
- `pm-plugin-development:plugin-script-architecture` (bundle path)
- `pm-dev-python:python-core` (bundle path)
- `pm-dev-python:pytest-testing` (bundle path)

## Deliverables

### D0 — DERIVE the population of prose-routed verb sets (GATE, mutates nothing)

**Method (reused from the first-instance plan, `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing.py`):** enumerate each provider's `handlers: HandlerMap` registry literal (the closed dispatch population), filter to `('pr', verb)` where `verb ∈ {merge, auto-merge, safe-merge, merge-queue}`, over BOTH providers. Then cross-reference against every prose routing table in the CI abstraction's workflow docs (dispatched via an independent read-only search of `phase-6-finalize`, `tools-integration-ci`, `workflow-integration-github`, `workflow-integration-gitlab`, `automatic-review`, `workflow-pr-doctor`).

**Derived population — the merge-shaped verb set = 8 members (4 verbs × 2 providers):**

| Provider | `('pr', verb)` | handler | callee-side guard already present |
|---|---|---|---|
| github | `('pr','merge')` | `cmd_pr_merge` | `_refuse_on_required_merge_queue` (refuses on required queue) + `_corroborate_merge` |
| github | `('pr','safe-merge')` | `cmd_pr_safe_merge` | preflight + delegate corroboration + admin-path corroboration |
| github | `('pr','merge-queue')` | `cmd_pr_merge_queue` | `_resolve_base_queue_state` (refuses when base has NO queue) |
| github | `('pr','auto-merge')` | `cmd_pr_auto_merge` | `_resolve_base_queue_state` probe + reports `disposition` (sanctioned exception) |
| gitlab | `('pr','merge')` | `cmd_pr_merge` | `_refuse_on_required_merge_train` + `_corroborate_merge` |
| gitlab | `('pr','safe-merge')` | `cmd_pr_safe_merge` | preflight + delegate corroboration |
| gitlab | `('pr','merge-queue')` | `cmd_pr_merge_queue` | merge-train POST; refuses (error) on 404/ineligible |
| gitlab | `('pr','auto-merge')` | `cmd_pr_auto_merge` | `_probe_merge_train_state` probe + reports `disposition` (sanctioned exception) |

**Central finding reused:** a hand-list of the two *routed* verbs (`safe-merge`, `merge-queue`) understated the real merge-shaped population by 4× (2 → 8). The routed pair is what `branch-cleanup.md` § "Merge routing (`use_merge_queue`)" names; the excluded siblings `merge` / `auto-merge` and both providers double the count.

**Null result (published):** the merge routing is the **only** full four-part prose-routed verb set in the CI abstraction. The four-part shape is (a) documented multi-branch route, (b) sibling reachable outside it, (c) asymmetric checking, (d) a destructive/irreversible member.

One **structural near-miss** was found and is recorded: the CI-wait strategy route in `branch-cleanup.md` § "Rebase Branch onto Base" (`ci checks status` snapshot vs `ci checks wait --adaptive`, keyed on the SAME `use_merge_queue` flag). It matches (a) documented route, (b) `checks` siblings reachable outside (`wait-for-status-flip`, `rerun`, `logs`, `pull-request-runs`), and (c) explicitly-asymmetric checking (line 418: "the two paths are NOT symmetric"), but **fails (d): both members are read-only CI polls** — neither merges, deletes, closes, force-pushes, nor enqueues. It is therefore not a prose-routed verb set under the four-part definition, but it is the closest sibling to the reference shape and is named here rather than silently dropped.

*Done:* population derived + published with size (8) and method; the null result (merge set is the only four-part instance) is stated with the same evidence.

### D1 — callee-side refusal for every D0 member

Every one of the 8 derived members already carries the callee-side base-queue/train guard (table above), shipped by the first-instance plan — the reference shape this plan generalises. No member is unguarded, so no new production guard is added (`Do not re-do it`).

**Sanctioned exception (found + preserved):** `pr auto-merge` (both providers) does NOT refuse — it PROBES the base queue/train state and REPORTS the `disposition` (`enabled` vs `enqueued`), never a bare/false `merged: true`. This is correct and must be preserved: `gh pr merge --auto` / `glab mr merge --when-pipeline-succeeds` self-routes — on a queued base it ENQUEUES (the safe outcome), on a non-queue base it enables plain auto-merge — so it is never in the close-unmerged unsafe state the immediate-merge verbs are, and a blanket refusal would break the legitimate enqueue-via-auto-merge path. The callee-side handling that prevents the incident here is probe-and-report, not refusal.

**Caller enumeration (published):** the only workflow step that DISPATCHES merge-shaped verbs in the finalize lifecycle is `branch-cleanup` (phase-6-finalize), and the closed-dispatch-set guard proves it dispatches ONLY `safe-merge` / `merge-queue` (the compliant route). `pr merge` / `pr auto-merge` are dispatched by NO finalize workflow step; they remain leaf verbs on the `ci pr` surface for ad-hoc / other callers (the marshall-steward landing cycle uses `safe-merge`). Because the refusal is SAFETY-gated (fires only when the base actually requires a queue/train) rather than caller-identity-gated, no legitimate caller targeting a non-queue base is affected — resolving the UNKNOWN claim ("some legitimate caller depends on reaching a D0 member outside its route") in the negative for the required-queue case, and preserving auto-merge's enqueue path via the sanctioned exception above.

*Done:* every D0 member refuses an off-routing dispatch (or, for auto-merge, applies the sanctioned probe-and-report); caller enumeration + sanctioned exception published.

### D2 — observability at the routing decision

The routing decision (`use_merge_queue`) is instrumented at every consumption site: the first-instance plan added the mandatory `**Observability (mandatory)**` decision-log block to all four `use_merge_queue` sites in `branch-cleanup.md` (CI-wait strategy, pre-merge consent wording, merge routing, and the reads feeding them), verified by `test_every_use_merge_queue_consumption_site_is_observable` / `test_merge_routing_decision_precedes_the_dispatch_it_selects`. A departure is recorded at the callee: each refusal names the base branch, the required routing (`ci pr merge-queue`), and the operation actually dispatched. D0 found no NEW routing table with a destructive member, so there is nothing new to instrument. *Done:* a departure from the documented route emits a record (the callee refusal) naming the route, the expected branch, and the verb actually dispatched.

### D3 — tests, each verified to fail pre-fix by mutation

Two artifacts:

- **`test/_shared/_merge_shaped_roster.py`** — the single-source derivation of the merge-shaped population from each provider's `handlers: HandlerMap` registry literal (the `_dispatch_roster.py` shared-single-source pattern D3(c) names). Pure functions over the module source text; path resolution is the caller's job. It uses the identical registry regexes as the first-instance source-guard (`test_branch_cleanup_merge_queue_routing.py`), so the two suites derive the SAME 8-member population — source-completeness (that guard) and behavioural-completeness (this one) are the same population viewed differently, over one derivation.
- **`test/plan-marshall/tools-integration-ci/test_merge_shaped_offrouting_refusal.py`** — the population-complete BEHAVIOURAL guard (18 tests):
  - `test_merge_shaped_population_is_derived_nonempty_and_sized` — asserts the derived population is non-empty FIRST, then `== 8` (4 verbs × 2 providers), 4-per-provider; the size is published in every failure message (distinguishes a passing run from an empty one).
  - `test_every_derived_member_has_an_offrouting_scenario` — a new merge-shaped verb added to a registry without an off-routing scenario fails here rather than being silently skipped.
  - `test_offrouting_dispatch_is_refused_at_the_callee` (parametrized over all 8 members) — dispatches each member off-routing and asserts the callee refuses (`status: error`), except `auto-merge` (the sanctioned exception), which must self-route to the enqueue and report `disposition: enqueued` with NO `merged` key.
  - `test_compliant_route_succeeds` (parametrized over all 8) — the compliant dispatch of every member still succeeds (`merged`/`enqueued`/`disposition: enabled`), so the guard is a boundary, not a wall.

**Proven falsifiable by mutation (Verification requirement).** Two mutations were run and reverted (via `git checkout`), each producing exactly the incident shape — a false `merged: true` off-routing:

| Mutation | Member test that failed | Observed result under mutant |
|---|---|---|
| Neutralize `_refuse_on_required_merge_queue` guard in GitHub `cmd_pr_merge` | `test_offrouting_dispatch_is_refused_at_the_callee[github:merge]` | `{'status':'success', ..., 'merged': True, 'merge_corroboration':'state=MERGED, ...'}` |
| Neutralize `_refuse_on_required_merge_train` guard in GitLab `cmd_pr_merge` | `test_offrouting_dispatch_is_refused_at_the_callee[gitlab:merge]` | `{'status':'success', ..., 'merged': True, 'merge_corroboration':'state=merged'}` |

In each mutation run, the mutated member's off-routing test went red while the other 7 stayed green — the guard discriminates a guarded handler from a gutted one, per provider. The population arm's falsifiability is structural: shrink the derived set and the size assertion fails; add an unclassified verb and the scenario arm fails.

*Done:* all three arms hold on the live tree (18 passed); the population size (8) appears in the test's own output; every member covered; falsifiability proven by mutation.

## Build gate

_Pending._

## Findings

_Filled as the run proceeds._

## Reviewer participation

_Pending._

## Cost

_Pending._

## Contract check (Step 9)

_Pending._

## What have we learned (Step 9)

_Pending._

## Residue

_Pending._
