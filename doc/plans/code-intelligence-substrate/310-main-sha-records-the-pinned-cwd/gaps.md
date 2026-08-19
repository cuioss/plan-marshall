# Gaps — 310-main-sha-records-the-pinned-cwd

The plan's code deliverables (D1, D2, D3, D5) landed correctly and are well tested — the resolver split
is real, asserted at the resolver, and three of the run's eleven mutation rows reproduce exactly. What
remains is concentrated in two places. First, one **reachable configuration** in which the fixed
resolution still mis-resolves and the new refusal fails to catch it: with a **non-canonical** base-dir
override active (any `PLAN_BASE_DIR` that is not literally `*/.plan/local`) the three `main_*` columns
record the worktree's values from anywhere inside the worktree, and from a *subdirectory* of it
`_assert_main_capture_read_main`'s path-**equality** comparison passes the mislabelled row through
silently instead of refusing it (reproduced by execution across the full override × cwd sweep; on the
default no-override path the fix is complete). Second, the
**D4 prose deliverable is unexecutable as written**: its Step 2 asks the reader to compare `captured_at`
against a cutoff the document neither states nor says how to obtain, and it instructs a direct read of a
`.plan/`-resident file when `phase_handshake list` projects exactly the fields it needs. Four further
low-severity documentation and report defects are recorded, two of them fresh instances of the
n−1-of-n residue class the run's own stop record predicted. The declared condition-B survivor
(`TaskGraphInvalid` with no handler) is still open and is carried here so a later plan can pick it up.

---

## G1 — Close the base-dir-override hole in the main-scoped resolution and its refusal

- **Kind:** bug
- **Severity:** medium — see § Severity below; the calibration call is deliberate, not a default.
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py:409-410`
  (`_main_repo_root` override branch) and `:1856` (`_assert_main_capture_read_main` path comparison)
- **Evidence:** executed against a real repo with a real linked worktree at
  `<main>/.plan/local/worktrees/p` whose branch carries one extra commit, sweeping the `PLAN_BASE_DIR`
  shape against the cwd. `main_sha` is shown as `main`/`worktree` rather than as a raw SHA:

  | `PLAN_BASE_DIR` | cwd | `_main_repo_root()` | `main_sha` reads | refusal |
  |---|---|---|---|---|
  | unset (production) | worktree | main | **main** | — |
  | unset (production) | worktree/src | main | **main** | — |
  | flat bare directory | worktree | worktree | **worktree** | FIRED (fail-closed) |
  | flat bare directory | worktree/**src** | worktree/src | **worktree** | **did not fire — row persists** |
  | `<main>/.plan` (non-canonical) | worktree | worktree | **worktree** | FIRED (fail-closed) |
  | `<main>/.plan` (non-canonical) | worktree/**src** | worktree/src | **worktree** | **did not fire — row persists** |
  | `<main>/.plan/local` (canonical) | either | main | **main** | — |
  | `<worktree>/.plan/local` (canonical) | either | worktree | **worktree** | FIRED (fail-closed) |

  `_main_repo_root` delegates the override branch to `_current_repo_root()` (`:410`), which returns
  `Path.cwd()` for **any** base dir that is not literally `*/.plan/local` (`:356`, `:359`) — a bare
  directory and `<root>/.plan` alike. The refusal then compares
  `main_root.resolve() != worktree_path.resolve()` (`:1856`) — plain equality — so a resolved path
  *inside* the worktree is treated as a distinct tree. `invariant-check-summary.md:54` documents the
  hole; nothing tests or closes it. All three `main_*` columns share this resolver
  (`_capture_main_sha`, `_capture_main_dirty`, `_capture_main_dirty_files`), so all three are
  mislabelled together, not `main_sha` alone.
- **Why it matters:** the exact defect this plan exists to end — a `main_*` column holding the
  worktree's value — remains reachable, and the guard written to make it impossible passes it through
  silently from any cwd below the worktree root. Note the sweep's shape: the mislabel is **not**
  subdirectory-specific — at the worktree root the value is equally wrong and is merely *refused*
  rather than persisted. The subdirectory is what turns a fail-closed refusal into a silent write. It
  also defeats D4's own quarantine rule, which can only say such a row is "sound *unless* an override
  was in play" — an era check that cannot be settled from the row.
- **Severity — why medium and not high.** The high band is for a defect reachable on the shipped
  default path. This one is not: with no override the fix is complete from every cwd inside the
  worktree (rows 1-2 above), and nothing in production sets the variable — there is no writer of
  `PLAN_BASE_DIR` anywhere under `marketplace/` and no caller of `file_ops.set_base_dir()` outside its
  own definition (`file_ops.py:404`). Reaching it needs an operator to export a **non-canonical**
  `PLAN_BASE_DIR` by hand, and the repository's own standard classifies that variable as a
  test-isolation hook (`tools-script-executor/standards/cwd-policy.md:44`, "the legitimate
  test-isolation hooks"), as does `bootstrap_plugin.py:33` ("for testing"); only `file_ops.py:374`
  ("tests, user override") and the neutral `manage-logging/SKILL.md:369` env row read as a user-facing
  knob. The limitation is also disclosed in three shipped surfaces — `_main_repo_root`'s docstring
  (`:386-392`), both `_capture_main_*` docstrings, and `invariant-check-summary.md:54` — so no
  documented contract is left unimplemented. What remains is an incomplete deliverable with an
  untested branch, which is the medium band exactly. ⚠ Do not read the disclosure as a reason to drop
  the gap: the run knowingly shipped a reachable instance of the defect it was written to end
  (`report-01.md:223-229`) and weakened the D4 rule to accommodate it.
- **Action:** (a) is the load-bearing change and is sufficient on its own; (b) is optional and must
  not be attempted in the literal form the first draft of this entry gave.
  - **(a) — required.** In `_assert_main_capture_read_main`, replace the equality comparison with
    containment: refuse when the resolved `main_root` is at or under the resolved `worktree_path`
    (`main_root.resolve().is_relative_to(worktree_path.resolve())`). **Measured here:** with that one
    change applied to the shipped file, every `did not fire` row above becomes `FIRED`, the module's
    19 tests stay green, and the whole owning directory stays green at 570/570. It is safe in the
    legitimate direction because a genuine main checkout is an *ancestor* of `worktree_path` (or a
    sibling), never a descendant.
  - **(b) — optional, and NOT "return `None`".** Making `_main_repo_root`'s override branch return
    `None` for a non-canonical base dir was measured and **breaks the suite**: the autouse
    `_plan_base_dir_sandbox` fixture (`test/conftest.py:1183-1185`) gives *every* test a **flat**
    `PLAN_BASE_DIR`, so the three `main_*` columns would empty out everywhere — 7 failures in
    `test/plan-marshall/plan-marshall/` alone (`test_invariants.py` ×2, `test_invariants_behavior.py`
    ×3, `test_invariants_main_capture_refusal.py` ×1, `test_lifecycle_handshake_e2e.py` ×1, the last
    on its `_NON_NULL_CORE_INVARIANTS` guard). If the override branch is changed at all, it must first
    distinguish a *test sandbox* from an operator override, or the sandbox must move to the canonical
    `<root>/.plan/local` shape. Treat (b) as a separate decision with that migration attached; do not
    bundle it into (a).
- **Done when:** a test builds a real linked worktree, sets a non-canonical `PLAN_BASE_DIR` (a bare
  directory), chdirs to a worktree **subdirectory**, and asserts that `capture_all` raises
  `MainCaptureReadTheWorktree`; the existing 19 tests in the two modules still pass; and mutating the
  containment check back to `!=` reddens the new test.
- **Effort:** S for (a); M for (b) including the sandbox migration.
- **Risk if fixed:** for (a), measured as none in this tree — 19/19 and 570/570 green with the change
  applied, and the commit-less-feature-branch direction
  (`test_a_commit_less_feature_branch_is_captured_not_refused`) is unaffected because there
  `main_root` is the main checkout and `worktree_path` is beneath it. In a consumer repository the
  containment check is strictly wider than equality, so a configuration that previously wrote a row
  would now refuse the boundary — that is the intended fail-closed direction. For (b), the measured
  7-test breakage above.

---

## G2 — Give the D4 quarantine rule a cutoff its reader can actually determine

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/invariant-check-summary.md:48`
  (Step 2 — the era, from `captured_at`)
- **Evidence:** the rule reads *"Compare the row's `captured_at` against when the main-anchored
  resolution fix landed in this repository."* The file states no date, no PR number, no commit, and no
  procedure for obtaining one. The declared reader is an LLM compiling the `invariant_summary` aspect
  from `summarize-invariants.py` output, which carries neither.
- **Why it matters:** every branch of the rule hangs on this comparison — *"written before it → the row
  is the artifact … written after it → the row is sound"*. With no obtainable cutoff the reader cannot
  reach either verdict, which is the same failure mode round 4's F37 found and fixed one layer up
  (the rule was unactionable by its declared reader). D4's whole purpose is that historical false drift
  warnings are documented as non-actionable; without the cutoff they remain undecidable.
- **Action:** state the anchor and how to derive it. In the meta-repository name the landing commit
  (`7612c3a`, PR #1286) directly. For a consumer repository, give the derivation as a one-line
  instruction — e.g. *"the first commit in your checkout whose `_invariants.py` defines
  `_main_repo_root`; `git log --diff-filter=A -S_main_repo_root -- <path>` names it"* — so the rule is
  self-contained wherever it is read.
- **Done when:** the Step 2 bullet names a concrete cutoff for this repository **and** a mechanical way
  to obtain it elsewhere, such that a reader with only the plan directory and a git checkout can reach
  a verdict without asking anyone.
- **Effort:** S
- **Risk if fixed:** a hard-coded commit SHA becomes a dated fact in a document the standards say
  should carry current state only; prefer the derivation form over the literal SHA, or state the SHA as
  an example of the derivation rather than as the rule.

---

## G3 — Enumerate and repair the second cwd-walk-up root resolver, in `audit.py`

- **Kind:** omission
- **Severity:** medium
- **Topic:** detectors/auditor — the owning surface is the archived-plan audit skill, not the
  handshake/architecture core this plan touched; grouping it under `architecture-core` would route it
  to the wrong fix plan.
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:789`
  (`_resolve_repo_root`). It is **called once**, at `:9414`; the returned `repo_root` is then consumed
  at `:1603`, `:1623` (lessons corpus) and `:2720`, `:4923`, `:4990` (archived-plan tree)
- **Evidence:** the function walks up from `Path.cwd()` to the nearest ancestor containing
  `.plan/local` and *"When no ancestor qualifies, the working directory itself"* — the exact shape D1
  set out to eliminate. It then derives `repo_root / ".plan/local/lessons-learned"` (`:1603`, `:1623`)
  and `repo_root / ".plan/local/archived-plans"` (`:2720`, `:4923`, `:4990`). `lessons-learned` is a
  member of the sanctioned **main-anchored** bounded-exception set
  (`marketplace_paths.resolve_main_anchored_path`, `:533-538`), so resolving it by a cwd walk-up is an
  ADR-002 divergence. The run's sibling sweep reported *"occurs exactly once across `marketplace/`"* —
  true as scoped, but the scope excluded the project-local `.claude/skills/` tree and the boundary was
  not stated.
- **Why it matters:** this is the plan's own ⚠ *"a reported instance is a sample"* landing where the
  sweep did not look. Run from a pinned worktree cwd, the archived-plan auditor reads the worktree's
  lessons corpus and archived-plan tree rather than main's — the same seam the plan's Notes section
  named ("never judge from a worktree-scoped store — query the main checkout"). An empty or partial
  worktree-scoped read is then reported as a corpus fact.
- **Action:** route the main-anchored reads (at minimum `lessons-learned`) through
  `marketplace_paths.resolve_main_anchored_path`, as `_lessons_io` and `merge_lock` already do; keep
  the walk-up only for genuinely cwd-scoped paths, and make the `Path.cwd()` fallback explicit about
  what it means. If the archived-plan tree is intended to be cwd-scoped, say so in the docstring so the
  divergence is a decision rather than an accident.
- **Done when:** `audit.py` derives its `lessons-learned` path from the shared main-anchored resolver,
  and a test asserts that with cwd inside a linked worktree the resolved lessons corpus is main's, not
  the worktree's.
- **Effort:** M
- **Risk if fixed:** existing `PLAN_BASE_DIR`-based tests of the auditor assume the walk-up; the shared
  resolver honours the override first, so they should survive, but each corpus-path test needs
  re-checking. Behaviour changes for anyone deliberately running the auditor from a sandbox tree.

---

## G4 — Route the D4 rule's row read through `phase_handshake list`, not a direct `.plan/` file read

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/invariant-check-summary.md:24`
  and `:46`; `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md:34`
- **Evidence:** the rule says *"**open `{plan_dir}/handshakes.toon`** (§ Inputs) and read them from the
  destination row"*, § Inputs says *"must read `handshakes.toon` directly"*, and SKILL.md's prohibited-
  actions list now reads *"Read `{plan_dir}/handshakes.toon` directly"*. Plan directories resolve under
  `.plan/local/plans/{plan_id}/` (`_handshake_store.py:59` → `file_ops.base_path`). Meanwhile
  `_handshake_commands.cmd_list:722-732` projects **every** `HANDSHAKE_FIELD` per row — `captured_at`,
  `main_sha` and `worktree_sha` included — which is exactly the pair the rule needs plus its
  discriminator. The same SKILL.md contradicts itself six lines later: `:40` reads *"Do not modify any
  .plan/ files directly — all plan state access goes through `manage-*` scripts and the scripts in
  this skill"*, so the file both mandates and forbids the direct read.
- **Why it matters:** the repository's standing rule is that all `.plan/` access goes through the
  generated executor's `manage-*` / script surface, never a direct file read. The rule as shipped
  directs its reader to break that, and does so unnecessarily: the sanctioned route exists, returns
  more than enough, and is not mentioned anywhere in the aspect. A reader that follows the standing
  rule instead cannot execute the check at all, which is the F37 failure shape recurring one step
  further out.
- **Action:** replace both instructions with the script route —
  `python3 .plan/execute-script.py plan-marshall:plan-marshall:phase_handshake list --plan-id {plan_id}`
  — and state which returned fields to read. Keep a direct-read fallback only for the **archived** mode
  if `cmd_list` genuinely cannot resolve an archived plan directory (`handshake_path` uses `base_path`
  with no archived fallback), and label that branch as the exception it is.
- **Done when:** § Inputs and the Step-1/Step-2 rule name the `phase_handshake list` invocation as the
  route to the stored values, `SKILL.md:34` matches, and any remaining direct-read instruction is
  explicitly scoped to archived plans with the reason given.
- **Effort:** S
- **Risk if fixed:** if the aspect runs in a context where the executor is unavailable (a fresh clone,
  a cloud lane), the script route fails where the file read would have worked — so the archived/no-
  executor fallback must survive rather than be deleted outright. (In this checkout the executor *is*
  present at `.plan/execute-script.py`, so the risk is about the cloud lane and consumer clones, not
  about the meta-repository.)

---

## G5 — Complete or re-label the "Invariants in Scope" table

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/invariant-check-summary.md:7-18`
- **Evidence:** the section is introduced as *"From `INVARIANTS` registry:"* and lists 8 rows.
  `_invariants.py:1656-1673` carries **15** entries. Missing: `main_dirty_files`, `references_valid`,
  `unfinished_tasks_count`, `task_graph_valid`, `pending_findings_by_type`,
  `pending_findings_blocking_count`, `pr_title_present`.
- **Why it matters:** the D4 rule two sections below tells the reader to read stored columns from the
  row; a table that claims to be the registry and omits seven of its columns misinforms that reader
  about what a row contains. `main_dirty_files` in particular is a list-typed column whose absence from
  the table makes its appearance in a row look anomalous.
- **Action:** either complete the table from the registry or change the lead-in to state it is a
  selected subset, naming the selection criterion.
- **Done when:** the table's row count matches `len(INVARIANTS)`, or its lead-in no longer claims to be
  the registry.
- **Effort:** S
- **Risk if fixed:** the table becomes a second place the registry is enumerated and can drift again;
  the subset re-label avoids that and is the cheaper option.

---

## G6 — Correct the stale `merge_lock` symbol citation in `marketplace_paths.py`

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py:402-405`
- **Evidence:** the comment reads *"lifted verbatim from `merge_lock.py`'s private
  `_resolve_main_lock_path` / `_main_checkout_root`"*. `_resolve_main_lock_path` exists
  (`merge_lock.py:316`), but `grep -n "_main_checkout_root\|main_checkout_root" merge_lock.py` returns
  **nothing** — the symbol is gone from that file, and `_resolve_main_lock_path` now delegates to
  `resolve_main_anchored_path` rather than owning any resolution.
- **Why it matters:** this is the sibling of the stale `merge_lock._override_is_set` citation the run's
  round 2 fixed in this same file — a fresh instance of the n−1-of-n pattern the stop record names as
  the residue a reader should expect. A reader following the citation to understand the provenance of
  the main-anchored resolver finds nothing there.
- **Action:** update the comment to describe the current relationship (the resolution lives here;
  `merge_lock._resolve_main_lock_path` is one of its consumers), or drop the symbol names.
- **Done when:** every symbol named in the comment block at `:396-405` resolves in the file it is
  attributed to.
- **Effort:** S
- **Risk if fixed:** none.

---

## G7 — Reconcile `cwd-policy.md`'s "ONE sanctioned main-anchored resolver" with `main_checkout_root`

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-script-executor/standards/cwd-policy.md:79`
- **Evidence:** the standard asserts *"The ONE sanctioned main-anchored resolver is
  `resolve_main_anchored_path`"*. `marketplace_paths.main_checkout_root()` (`:473-484`) is a second
  public main-anchored resolver, and it predates this plan with **four** call sites across three
  modules — `manage-build-server/scripts/manage_build_server.py:138` and `:644`,
  `manage-locks/scripts/build_queue.py:396`, `build-server-client/scripts/build_server.py:146`. This
  plan added the fifth, `_invariants._main_repo_root` (`:412`). (An earlier draft of this entry said
  the plan added "a second consumer"; the pre-existing population is four, not one.) The run recorded
  a round-1 "verified
  negative" that the addition does not violate the standard — correct in substance, because the
  standard's binding clause is scoped to `.plan/`-path resolution for plan-scoped state — but the
  quoted sentence is a whole-repo universal that is now literally false.
- **Why it matters:** the sentence is the one a future reviewer will quote when rejecting a new
  main-anchored resolver. Left as an unqualified universal it either blocks a legitimate addition or
  gets waved away, and either outcome erodes the rule.
- **Action:** scope the sentence to what it governs — the single sanctioned resolver **for `.plan/`
  paths** is `resolve_main_anchored_path`; `main_checkout_root()` is the sanctioned way to name the
  main *checkout root* (not a `.plan/` path), used by the handshake's `main_*` columns and the
  build-queue holder stamp.
- **Done when:** `cwd-policy.md:79` distinguishes the two, and names `main_checkout_root`'s consumers.
- **Effort:** S
- **Risk if fixed:** loosening the wording could be read as licensing new main-anchored resolvers; keep
  the enumeration of consumers closed and explicit.

---

## G8 — Correct the report's "only consumer of the `main_*` columns" claim

- **Kind:** report-defect
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `doc/plans/code-intelligence-substrate/310-main-sha-records-the-pinned-cwd/report-01.md:485-486`
- **Evidence:** *"**no consumer of the `main_*` columns is unexamined** — `summarize-invariants.py` is
  the only one, `execution-recovery.md`'s `main_sha` is the `status.metadata` namespace D1 excluded,
  and the archived-plan audit skill does not read handshake rows."* But
  `_handshake_commands._check_main_dirty_drift:288` consumes `captured_row['main_dirty_files']` against
  `observed['main_dirty_files']`, and `_diffs:485-512` compares `main_sha` and `main_dirty` across the
  captured and observed rows. (`_diffs` is **not** a consumer of all three columns: it iterates
  `INVARIANTS` and explicitly `continue`s on `main_dirty_files` at `:493-494`, deferring that column to
  `_check_main_dirty_drift`'s proper-superset semantics. An earlier draft of this entry said "every
  `main_*` column" — that overstated it.)
- **Why it matters:** the enumeration is the report's own evidence for an asserted absence, and an
  asserted absence is verified exactly as an asserted presence (the plan's words). The *"unexamined"*
  half holds — the run did examine `_check_main_dirty_drift`, as D5's declared collateral — but the
  *"only one"* half is false, and a later reader relying on the enumeration to bound a change would be
  misled about the blast radius.
- **Action:** amend the sentence to list the in-file consumers (`_check_main_dirty_drift`, `_diffs`)
  alongside `summarize-invariants.py`, noting that the first was examined as declared collateral.
- **Done when:** the claim enumerates every consumer that reads a `main_*` column and states which were
  examined.
- **Effort:** S
- **Risk if fixed:** none — a report correction only.

---

## G9 — Give `TaskGraphInvalid` a handler at both handshake verbs

- **Kind:** omission
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py:274-303`
  (the exception), `:1087` (the raise), `:1879` (declared in `capture_all`'s `Raises:`);
  same-directory `_handshake_commands.py:415-446` (`cmd_capture`'s handler chain, function at `:396`)
  and `:536-566` (`cmd_verify`'s, function at `:515`). ⚠ `VERIFY_REFUSAL_ERRORS` is **not** in that
  directory — it lives at
  `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py:46-52`
- **Evidence:** `grep -n "TaskGraphInvalid\|task_graph_invalid"` over the handshake scripts finds the
  class, its raise and its docstrings — and **no** `except TaskGraphInvalid` and no
  `task_graph_invalid` error code. `cmd_capture` handles its four siblings (`PhaseStepsIncomplete`,
  `BlockingFindingsPresent`, `PrTitleMissing`, `MainCaptureReadTheWorktree`) and not this one, so a
  broken task graph escapes to `file_ops.safe_main` and renders as `error: internal_error`. The class's
  own docstring at `:285-288` now says so outright.
- **Why it matters:** it is the same defect shape as this plan's F1 — an exception with structured
  fields (`cycle`, `dangling`) carried but never rendered — on the one member of `capture_all`'s raise
  set no verb handles. The boundary still blocks and no row is persisted (the raise precedes
  `_row_for_capture`), so it fails closed; what is lost is the diagnosis, and the operator sees a
  generic internal error instead of which task depends on what.
- **Action:** add `except TaskGraphInvalid as exc` to both verbs, returning a structured payload
  (`error: task_graph_invalid`, `cycle`, `dangling`, `message`) through a shared builder in the shape
  `_main_capture_read_the_worktree_payload` uses; add the code to `VERIFY_REFUSAL_ERRORS`
  (`marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py:46-52`) and to
  the strict-exit tuple in
  `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/phase_handshake.py:138-142`,
  matching the four siblings.
- **Done when:** a test drives `cmd_capture` and `cmd_verify` against a plan whose task graph carries a
  cycle and asserts `result['error'] == 'task_graph_invalid'` with the `cycle` payload present and no
  row written; the strict exit returns 1; and removing either handler reddens it.
- **Effort:** S
- **Risk if fixed:** adding the code to `VERIFY_REFUSAL_ERRORS` changes loop-back re-entry behaviour for
  a broken task graph from "auto-override attempted" to "refused" — check that this is the intended
  posture against the **five** existing members (`worktree_unresolved`, `worktree_metadata_drift`,
  `main_checkout_dirtied_during_plan`, `worktree_dirty_at_boundary`, `main_capture_read_the_worktree`)
  before widening the set. Note the set (5) and `phase_handshake.py`'s strict-exit tuple (3) already
  disagree; adding to one is not adding to the other.
