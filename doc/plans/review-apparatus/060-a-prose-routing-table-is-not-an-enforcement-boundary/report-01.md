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

- **`test/_shared/_merge_shaped_roster.py`** — the designated single-source derivation of the merge-shaped population from each provider's `handlers: HandlerMap` registry literal (the `_dispatch_roster.py` shared-single-source pattern D3(c) names). Pure functions over the module source text; path resolution is the caller's job. The behavioural suite reads its population from here. It uses registry regexes byte-identical to the first-instance source-guard (`test_branch_cleanup_merge_queue_routing.py`), which still carries its own copy; the two derive the same 8-member population today — source-completeness (that guard) and behavioural-completeness (this one) are the same population viewed differently. Migrating the source-guard onto this helper is a recorded follow-up (see Findings F1 / Residue), not done here so the first-instance reference apparatus is left intact.
- **`test/plan-marshall/tools-integration-ci/test_merge_shaped_offrouting_refusal.py`** — the population-complete BEHAVIOURAL guard (18 tests):
  - `test_merge_shaped_population_is_derived_nonempty_and_sized` — asserts the derived population is non-empty FIRST, then `== 8` (4 verbs × 2 providers), 4-per-provider; the size is published in every failure message (distinguishes a passing run from an empty one).
  - `test_every_derived_member_has_an_offrouting_scenario` — a new merge-shaped verb added to a registry without an off-routing scenario fails here rather than being silently skipped.
  - `test_offrouting_dispatch_is_refused_at_the_callee` (parametrized over all 8 members) — dispatches each member off-routing and asserts the callee refuses (`status: error`), except `auto-merge` (the sanctioned exception), which must self-route to the enqueue and report `disposition: enqueued` with NO `merged` key.
  - `test_compliant_route_succeeds` (parametrized over all 8) — the compliant dispatch of every member still succeeds (`merged`/`enqueued`/`disposition: enabled`), so the guard is a boundary, not a wall.

**Proven falsifiable by mutation (Verification requirement).** Four mutations were run and reverted (via `git checkout`), covering all three off-routing scenario classes across both providers. In every run the mutated member's off-routing test went red while the other seven stayed green — the guard discriminates a guarded handler from a gutted one:

| # | Scenario class | Mutation | Failing member | Observed result under mutant |
|---|---|---|---|---|
| 1 | refuse_immediate | Neutralize `_refuse_on_required_merge_queue` in GitHub `cmd_pr_merge` | `[github:merge]` | `{'status':'success', ..., 'merged': True, 'merge_corroboration':'state=MERGED, ...'}` |
| 2 | refuse_immediate | Neutralize `_refuse_on_required_merge_train` in GitLab `cmd_pr_merge` | `[gitlab:merge]` | `{'status':'success', ..., 'merged': True, 'merge_corroboration':'state=merged'}` |
| 3 | refuse_unconfigured | Neutralize the `discriminator != CONFIGURED` refusal in GitHub `cmd_pr_merge_queue` | `[github:merge-queue]` | success/`enqueued` off-routing instead of the refusal |
| 4 | report_disposition | Hardcode `disposition = 'enabled'` (drop the probe-derived value) in GitHub `cmd_pr_auto_merge` | `[github:auto-merge]` | `disposition: 'enabled'` on a queued base instead of `'enqueued'` |

Cross-provider / cross-verb reach of the four measured mutations, stated precisely:

- **`refuse_immediate`** — mutation-MEASURED on BOTH providers (#1 GitHub, #2 GitLab). `safe-merge` is the same class as `merge` (same `_refuse_on_required_merge_*` preflight, run before it delegates), so a `safe-merge` mutation would flip identically.
- **`report_disposition`** — mutation-measured on GitHub (#4); GitLab's `cmd_pr_auto_merge` uses the byte-identical `disposition = 'enqueued' if discriminator == CONFIGURED else 'enabled'` logic, so the same mutation applies — a true mirror.
- **`refuse_unconfigured`** — mutation-measured on GitHub (#3, the probe-discriminator refusal). GitLab's `cmd_pr_merge_queue` refuses via a **mechanically different** path (the merge-train POST returning HTTP 403/404), NOT a mirror of the GitHub mutation. Its falsifiability is argued structurally rather than measured: dropping the 404/403-as-refusal handling flips `gitlab:merge-queue`'s off-routing test.

The population arm's falsifiability is structural (shrink the derived set → size assertion fails; add an unclassified verb → scenario arm fails).

`test_compliant_route_succeeds` is an honest **regression lock**, not a mutation-falsified check: it passes both pre- and post-mutation (a guard neutralization does not stop the compliant route succeeding). Its purpose is the D3(b) obligation — proving the guard is a boundary, not a wall — and it would go red if a guard OVER-refused a compliant dispatch.

*Done:* all three arms hold on the live tree (18 passed); the population size (8) appears in the test's own output; every member covered; the off-routing refusal arm proven falsifiable by mutation across all three scenario classes and both providers.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` = two test files (`test/_shared/_merge_shaped_roster.py`, `test/plan-marshall/tools-integration-ci/test_merge_shaped_offrouting_refusal.py`) — a Python footprint, so the full gate ran. `./pw verify` → **SUCCESS**: `19160 passed, 14 skipped in 485.94s`; mypy(production) [395 files] clean, ruff clean, SPDX clean, plugin-doctor marketplace-wide clean, mypy(test) [715 files] clean, module-tests (whole-tree) passed. No production source was changed by this plan (the two mutations were reverted via `git checkout`), so the guards under test are the shipped ones.

## Findings

**Pre-PR verification sub-agent (Task tool, `general-purpose`, read-only).** It independently re-derived the 8-member population from both `handlers: HandlerMap` literals, traced all 8 handler bodies and their guard chains, confirmed the monkeypatch indirection is real and that every off-routing refusal is caused by the queue/train guard (not an incidental missing-arg/auth error — `_resolve_pr_identifier`/`_resolve_mr_iid` return `str(pr_number)` with no network call, and `check_auth` is stubbed OK), cold-read all four refusal messages, and confirmed no vacuous-pass stub. **Verdict: no blocking defect; D0–D3 substantively satisfied.** Three minor findings, all dispositioned:

- **F1 (fixed).** The shared helper's "single-source" docstring (and a report line) overstated: the pre-existing source-guard `test_branch_cleanup_merge_queue_routing.py` still carries its own byte-identical derivation, so two copies exist. **Disposition:** softened the helper docstring and the report to state it is the single source for the behavioural suite and that the source-guard's identical copy is a recorded consolidation follow-up — leaving the first-instance reference apparatus intact per D1's "do not re-do it." (Consolidating the two onto the helper is Residue.)

- **F2 (fixed).** The mutation evidence originally measured only 2 of the 3 off-routing scenario classes, and filed the compliant-route regression lock under "proven falsifiable by mutation" without the honest passes-pre-and-post distinction. **Disposition:** ran two further mutations (`github:merge-queue`, `github:auto-merge`) so all three scenario classes are mutation-measured, and corrected the report to label the compliant arm a regression lock (see Build gate / D3 mutation table). Cross-provider reach is stated precisely there rather than claimed as a blanket "mirror": `refuse_immediate` is measured on both providers, `report_disposition` mirrors (identical GitLab logic), but `refuse_unconfigured` on GitLab is a mechanically distinct HTTP-error refusal whose falsifiability is argued structurally, not by mirroring the GitHub mutation.

- **F3 (fixed — cold-read of the refusal message, plan Verification ⭐).** The cold-read of all four refusal messages found three were boundaries (they name the correct routed verb — GitHub `_refuse_on_required_merge_queue` → `ci pr merge-queue`; GitHub `cmd_pr_merge_queue` → `ci pr safe-merge`; GitLab `_refuse_on_required_merge_train` → `ci pr merge-queue`) but **GitLab `cmd_pr_merge_queue`'s ineligible refusal was a wall**: it explained the Premium/Ultimate merge-train requirement but named no alternative routed verb, unlike its GitHub sibling. A reader who enqueued and cannot enable trains was left without the correct next verb. **Disposition:** fixed at the call site — the ineligible refusal now also names "disable `use_merge_queue` … and merge via `ci pr safe-merge`", mirroring GitHub, and a `test_gitlab_merge_queue.py` assertion locks that the message names `safe-merge`. This is a refusal-message parity fix, NOT a re-implementation of the guard (the guard is unchanged); it directly serves the plan's boundary-not-wall thesis, which the mandated cold-read exists to enforce. The shared `_MERGE_TRAIN_INELIGIBLE_HINT` constant (also used by `repo merge-queue enable`) was left unchanged; the remedy was added only at the merge dispatch site.

**CI / automated review:** recorded under Reviewer participation once the PR is open.

## Reviewer participation

_Pending._

## Cost

_Pending._

## Contract check (Step 9)

_Pending._

## What have we learned (Step 9)

_Pending._

## Residue

- **Source-guard consolidation onto the shared roster helper (F1 follow-up).** The first-instance source-guard `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing.py` still carries its own registry derivation (`_registry_keys` / `_registry_handler_names` / `_merge_shaped_registry_keys`, with byte-identical regexes) rather than importing `test/_shared/_merge_shaped_roster.py`. The two derive the same 8-member population today, so there is no live drift, but a future `chore/` change should migrate the source-guard onto the shared helper so the single-source discipline is fully realised. Deferred here to leave the first-instance reference apparatus intact (D1 "do not re-do it").
- **GitLab `merge-queue` off-routing falsifiability is argued, not mutation-measured** (see D3 mutation table). Its refusal mechanism (merge-train POST HTTP 403/404) differs from the GitHub probe-discriminator path that was mutated. A future strengthening could add a GitLab-specific mutation (drop the 404/403-as-refusal handling) to measure it directly.
