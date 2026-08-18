# Gaps — 250-footprint-read-outside-its-window

Seven gaps remain. One is high: the plan's own defect class survives in the file the plan changed —
`verify_failure_scope._resolve_declared_footprint` still derives the plan footprint from the **main
checkout** when the plan's worktree is `pending`, because it reads `PlanContext.worktree_path` (which is
documented to fall back to the main checkout) instead of gating on `has_worktree` the way both of its
peer sites do. The PR-review fix removed the `Path.cwd()` fallback but left the sibling route open, and
the function's own docstring still describes the removed behaviour as current. The remaining six are a
missing reason-token in the published consumer contract, the reason-token half of D2 unapplied at two
sites, one omission from the D1 population, one test gap that explains why the high finding survived,
and one safe-but-divergent tier-1 failure policy between the two resolvers.

## G1 — Gate the verify-failure footprint on `has_worktree`, not on `worktree_path`

- **Kind:** bug
- **Severity:** high
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/verify_failure_scope.py:94`
  (`_resolve_declared_footprint`)
- **Evidence:** The line is
  `worktree = Path(resolve_plan_context(plan_id, ensure=False).worktree_path)`.
  `PlanContext._resolve_worktree_face` (`tools-file-ops/scripts/file_ops.py:1097-1120`) returns
  `cwd_checkout_root()` for the `pending` and `disabled` worktree states and raises
  `WorktreeResolutionError` only when the `get-worktree-path` channel itself fails — so the `except`
  at `:95` never fires for a plan that simply has no materialized worktree. Reproduced by stubbing
  `file_ops._query_worktree_path` to return `('pending', '')`:

  ```text
  worktree_state = pending
  has_worktree   = False
  worktree_path  = /home/user/plan-marshall
  _resolve_declared_footprint(plan_dir, 'demo-pending') -> set of 310 paths
  ```

  Both peer sites gate on `has_worktree` and document this exact hazard:
  `manage-references/scripts/_references_core.py:188-194` ("gating on the path would hand callers a
  main-checkout footprint where they previously got 'no worktree'") and
  `manage-execution-manifest/scripts/manage-execution-manifest.py:673-681`.
- **Why it matters:** Every error path is then classified against an unrelated tree. When that tree is
  clean against its base — the ordinary case in a consumer project — `compute_plan_branch_diff` returns
  a **resolved empty** set, so every failure lands out-of-scope, `exclusively_out_of_scope` becomes
  `true`, and phase-5-execute Step 11 offers *"Stash foreign files and re-verify"* as the **default**
  remedy on no evidence. That is verbatim the harm the module docstring (`:30-36`) and the P1 fix claim
  to have removed; the plan's D2 is not actually closed on this path.
- **Action:** Replace the direct `worktree_path` read with the shared gate — either
  `_references_core.resolve_live_worktree(plan_id)` (which already returns `None` for
  pending/disabled/non-directory) or an inline `if not context.has_worktree: return None` before taking
  the path, mirroring `manage-execution-manifest._resolve_footprint:682-690`. Keep the existing
  `NO_PLAN` sentinel behaviour, which is deliberately main-checkout-bound and has its own test.
- **Done when:** with `_query_worktree_path` stubbed to `('pending', '')`,
  `_resolve_declared_footprint` returns `None` and `compute_plan_branch_diff` is never called; a test
  asserts both (the "never called" half is required — a return-value-only assertion passes even if the
  wrong tree was diffed and the result discarded).
- **Effort:** S
- **Risk if fixed:** A `disabled` (non-worktree-bound) plan currently gets a legitimate main-checkout
  measurement and would start reporting `footprint_resolved: false`. Both peers already accept that
  trade; if it is unacceptable here, branch on the state explicitly (`materialized` → diff the worktree,
  `disabled` → diff the main checkout, `pending` → `None`) rather than reverting to the path read.

## G2 — Delete the stale "degrades to the current working directory" paragraph

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/verify_failure_scope.py:79-81`
  (`_resolve_declared_footprint` docstring)
- **Evidence:** The docstring states: *"An unresolvable worktree degrades to the current working
  directory, preserving the previous non-fatal behaviour for archived plans and test seams."* The
  function's own summary line at `:62` says *"Return the live plan footprint, ``None`` if unmeasurable"*
  and the comment at `:96-104` says the cwd fallback *"is exactly the defect this module was changed to
  remove"*. Three statements, two of them contradicting the third, inside one function.
- **Why it matters:** The paragraph documents the removed behaviour as current and reads as explicit
  sanction for G1 — a maintainer restoring a path-based read would find the docstring endorsing it.
  A false claim in shipped documentation about the very contract this plan established.
- **Action:** Replace the paragraph with the actual contract: the worktree face comes from the single
  plan-context resolver under `ensure=False`, and a worktree that is not materialized yields `None`
  (unmeasurable), never a fallback tree. Land it together with G1 so code and prose agree.
- **Done when:** the string "degrades to the current working directory" appears nowhere in
  `verify_failure_scope.py`, and the docstring's account of the unresolvable path matches the code.
- **Effort:** S
- **Risk if fixed:** None — comment-only.

## G3 — Publish `unresolved_reason` in the phase-5-execute consumer contract

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md:820-829` (the
  `classify` TOON shape) versus `verify_failure_scope.py:22-28` and `:199`
- **Evidence:** `_emit_toon` prints `unresolved_reason: {token}` on every unresolved return
  (`verify_failure_scope.py:197-199`), and the module docstring documents the field at `:22`. The
  SKILL.md block that consumers read lists only
  `status`, `footprint_resolved`, `total`, `in_scope_count`, `out_of_scope_count`,
  `exclusively_out_of_scope`, `out_of_scope_paths`, `unclassified_paths` — no `unresolved_reason` row,
  and no prose mentions it (`grep -n "unresolved_reason" phase-5-execute/SKILL.md` → no match).
- **Why it matters:** D2 asks for an unknown state *"with a reason token"*; the token exists in the
  payload but not in the contract, so no consumer is told to read it. The P2 fix was applied to the code
  and the module docstring and stopped one surface short — the same "fixed at the referring site, not
  the target" pattern the run's own findings W4 and X2 record.
- **Action:** Add `unresolved_reason: <token>          # only when footprint_resolved: false` to the
  TOON block and name it in the "Read `footprint_resolved` FIRST" paragraph, stating that the token
  names what to repair.
- **Done when:** `phase-5-execute/SKILL.md` documents `unresolved_reason` in the TOON shape, and the
  documented field set matches what `_emit_toon` can print, field for field.
- **Effort:** S
- **Risk if fixed:** None — documentation only.

## G4 — Give the recall and exact-match `inconclusive` returns a reason token

- **Kind:** incomplete
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-artifact-consistency.py:540-551`
  (`check_affected_files_recall`) and `:593-600` (`check_affected_files_exact_match`)
- **Evidence:** Both unresolvable returns carry `footprint_resolved: False` (a **state**) plus a prose
  message; neither carries a stable token. The two sibling sites do:
  `analyze-logs.py:1543` emits `ARTIFACT_COVERAGE_UNMEASURABLE:` inside its message, and
  `verify_failure_scope.py:58,156` emits a typed `unresolved_reason: plan_footprint_unresolvable`.
  P2 in the run report states the requirement precisely: *"`footprint_resolved: false` is the state, not
  the reason."*
- **Why it matters:** D2's literal wording ("`unknown` / `skipped` **with a reason token**") is met at
  two of four unresolved-reporting sites. A consumer wanting to distinguish "no capture was written"
  from "the diff failed" has only free prose to match on, and the exact-match block returned at
  `cmd_run` (`:909-915`) does not even carry `footprint_resolved`.
- **Action:** Add a shared constant (e.g. `FOOTPRINT_UNRESOLVABLE_REASON = 'plan_footprint_unresolvable'`,
  ideally exported from `_footprint_resolver` so all four sites share one spelling) and publish it in
  `details` on both `inconclusive` branches; surface `footprint_resolved` in the
  `affected_files_exact_match` block too.
- **Done when:** both `inconclusive` returns publish a reason token drawn from one shared constant, and
  `references/artifact-consistency.md` documents the key alongside `read_intent_excluded` and
  `declared_unfiltered`.
- **Effort:** S
- **Risk if fixed:** A `details` key addition; the production-shape fixture
  (`fixtures/archived-plan/work/fragment-artifact-consistency.toon`) and any test asserting an exact
  `details` dict must be updated in step.

## G5 — Account for `check_build_verdict_consistent` in the D1 population

- **Kind:** omission
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `doc/plans/code-intelligence-substrate/250-footprint-read-outside-its-window/footprint-read-population.md`
  (§ "The D1 population" and § "Adjacent, deliberately excluded"); the site is
  `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_validation.py:1026`
  fed from `manage-execution-manifest.py:2021`
- **Evidence:** A truthiness-predicate sweep
  (`if not footprint|if footprint|footprint or |footprint else` over `marketplace/**/*.py`) returns
  twelve hits. Eleven map to the published population, the providers, or `lsp_client.py:217` (a
  `WorkspaceEdit` footprint, a different concept). The twelfth is
  `_manifest_validation.check_build_verdict_consistent`, whose `if not footprint: return None` guard
  decides whether a compose-time assertion runs — and whose input has had its unresolvable state
  normalized away one frame earlier by
  `live_footprint_paths = [] if live_footprint is None else live_footprint`.
- **Why it matters:** D1's contract is a **derived** population, and the population document is a
  deliverable. The behaviour is safe (an unresolvable footprint disables the assertion, which fails
  toward passing compose), which is precisely why it belonged in the "Adjacent, deliberately excluded"
  table with that reasoning recorded — an unlisted site invites a later run to rediscover it and read
  the silence as coverage.
- **Action:** Add a row to the excluded table naming the site, the normalization at the call site, and
  why the collapse is benign there (an assertion that declines to fire subtracts no gate). If a future
  plan wants the stricter form, note that passing `live_footprint` through unnormalized plus an explicit
  `is None` guard would preserve the distinction.
- **Done when:** the population document accounts for every truthiness-predicate hit in the sweep above,
  each either in the population or in the excluded table with a stated reason.
- **Effort:** S
- **Risk if fixed:** None — documentation only.

## G6 — Test the `pending`-worktree route through the verify-failure resolver

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/phase-5-execute/test_verify_failure_scope.py:315-346`
  (`test_footprint_resolver_never_diffs_the_current_directory`)
- **Evidence:** The test stubs `file_ops._query_worktree_path` to **raise**
  `WorktreeResolutionError`, so it exercises only that route; its name and docstring claim the broader
  property *"no diff may be attempted against any tree"*. No test drives the `pending` /
  non-materialized state, which is the route that still diffs the main checkout (G1). The test directly
  above it (`:300-313`) deliberately asserts that the `NO_PLAN` sentinel **does** diff
  `MAIN_CHECKOUT_ROOT`, which makes the missing case easy to overlook.
- **Why it matters:** The suite currently reads as though the cwd/foreign-tree class is closed. It is
  not, and no test would go red if G1 were fixed and later regressed.
- **Action:** Add a test that stubs `_query_worktree_path` to `('pending', '')` and asserts
  `_resolve_declared_footprint` returns `None` **and** that `compute_plan_branch_diff` was never
  invoked; narrow the existing test's docstring to the route it actually covers.
- **Done when:** the new test fails against today's source (it will diff the checkout) and passes once
  G1 lands.
- **Effort:** S
- **Risk if fixed:** None — test-only.

## G7 — Reconcile the two resolvers' tier-1 failure policy

- **Kind:** incomplete
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/_footprint_resolver.py:218-221`
  versus `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:286-289`
- **Evidence:** The shared whole-chain resolver returns `FOOTPRINT_UNRESOLVED` when the tier-1 git diff
  raises `CalledProcessError`, discarding tiers 2-4; `analyze-logs`'s scope-deviation resolver falls
  **through** to the capture / merge-commit / legacy tiers and documents the deviation at `:263-267`.
- **Why it matters:** For one live plan with a broken worktree diff but a valid
  `references.realized_footprint`, the ARTIFACT floor resolves while the recall and mis-prune checks
  report `inconclusive` — two verdicts about the same plan derived from different resolution states, in
  the same retrospective run. The direction is safe (a measurable footprint reported unmeasurable, never
  the reverse), so this is a consistency and information-loss issue rather than a false grade.
- **Action:** Decide the one policy and apply it in `_footprint_resolver.resolve_footprint`. The
  fall-through form is the stronger one — a recorded capture is a valid resolution regardless of whether
  a live diff could be attempted — and adopting it would let `analyze-logs` drop its private tier chain
  and call the whole-chain resolver.
- **Done when:** both resolvers answer identically for a plan with a failing tier-1 diff and a present
  `realized_footprint`, pinned by a test that constructs exactly that state.
- **Effort:** M
- **Risk if fixed:** Widening `resolve_footprint` changes when the recall check reports `inconclusive`
  versus a measured percentage; archived-mode tests and any fixture relying on the current
  short-circuit must be re-checked.
