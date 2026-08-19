# Verification — 310-main-sha-records-the-pinned-cwd

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `f97303b` on `claude/code-intelligence-substrate-analysis-kah884`
**Landed as:** `7612c3a` — `fix(phase-handshake): read main-scoped columns from main, not the pinned cwd (#1286)`
**Overall verdict:** CONFIRMED WITH GAPS

The shipped code does what the plan asked and does it at the layer the plan's own ⛔ block identified.
Every D1 figure re-derived here matches the report exactly, and three of the report's eleven mutation
rows were independently reproduced with identical red/green splits. The gaps are concentrated in D4 —
the prose deliverable — plus one reachable configuration in which the fixed resolution still
mis-resolves and the new refusal does not fire.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | GATE: enumerate main-scoped captures + resolver callers | Pop. A = 3 of a 15-entry registry; Pop. B = 4 callers, 3 inherit; sibling shape occurs once | Registry is 15 (`_invariants.py:1656-1673`); 3 `main_*` entries; pre-fix `_repo_root` had exactly 4 callers (`7612c3a^`); `_run_script` has 10 call sites reaching 7 registry captures — all re-derived, all match | CONFIRMED |
| D2 | Fix the RESOLUTION, not the call site | `_repo_root` → `_current_repo_root`; new `_main_repo_root` via `git rev-parse --git-common-dir`, `None` not cwd-fallback | `_invariants.py:336`, `:362`; asserted directly on the resolver at `test_invariants_main_resolution.py:114`; reproduced by first-party probe | CONFIRMED (one override hole — G1) |
| D3 | Fail loud on the impossible state | `MainCaptureReadTheWorktree`, keyed on same-tree resolution rather than equal SHAs; both verbs, one payload builder | `_invariants.py:214`, `:1813`; `_handshake_commands.py:354`, `:445`, `:557`; in `VERIFY_REFUSAL_ERRORS` (`_cmd_lifecycle.py:51`) and the strict-exit list (`phase_handshake.py:141`) | CONFIRMED — **deviates from the literal *Done when*** (see D3 detail) |
| D4 | Quarantine already-written rows; two separate numbers | Plans examined **0**; records affected **BLOCKED**; documented rule shipped | Both numbers present (`report-01.md:169-173`); `.plan/local/` in this clone carries no `plans/` — re-checked, still true; rule at `invariant-check-summary.md:46-55` | PARTIAL — rule is unexecutable as written (G2, G4) |
| D5 | Tests, each verified to fail pre-fix | 19 tests in two modules; 11-mutation matrix, red-set union 19 of 19 | 19 collected and green; M1/M2/M3 independently reproduced at exactly 6/4/2 red | CONFIRMED |

## Per-deliverable detail

### D1 — GATE: the two populations

- **Required (plan):** *"both populations are enumerated from source and published with their counts."*
- **Claimed (report):** Population A = 3 main-claiming fields out of a 15-entry registry, each field's
  tree read from its `capture_fn`; Population B = 4 callers of the root resolver, of which **3** inherit
  the mis-resolution (the plan's "every consumer" HYPOTHESIS refuted); `_run_script` has 10 call sites
  feeding 7 registry captures; the defect shape occurs exactly once across `marketplace/`.
- **Found / checks run:**
  - Registry: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py:1656-1673`
    — counted 15 entries; `main_sha`, `main_dirty`, `main_dirty_files` are the three whose names claim
    main. `worktree_sha` / `worktree_dirty` read `metadata['worktree_path']` (`:1660-1661`).
  - Population B re-derived against the **pre-fix** file:
    `git show 7612c3a^:…/_invariants.py | grep -n "_repo_root()"` → 4 call sites (`:336` `_run_script`,
    `:452` main_sha, `:456` main_dirty, `:516` main_dirty_files). Exactly the report's table.
  - `_run_script` call sites at `_invariants.py:792, 851, 879, 980, 1011, 1118, 1150, 1178, 1268, 1327`
    = **10**. An AST closure over the registry's `capture_fn`s (run here, not copied) returns **7**
    captures reaching `_run_script`: `references_valid, task_state_hash, qgate_open_count,
    unfinished_tasks_count, task_graph_valid, pending_findings_by_type,
    pending_findings_blocking_count`. Both report figures correct.
  - Second namespace: `phase-5-execute/standards/sync-with-main.md:84` confirms
    `status.metadata.main_sha` is captured by `git -C {worktree_path} rev-parse origin/{base_branch}` —
    a different quantity, explicitly resolved. The report's exclusion is right.
  - Asserted absence spot-checked at the sibling archetype the plan named: the merge lock resolves via
    `resolve_main_anchored_path` (`merge_lock.py:316-326`), so it is not a member.
  - Sibling shape sweep: `grep -rn "parent.name == '.plan'" marketplace/` returns exactly one hit
    (`_invariants.py:357`). The claim is true **as scoped**.
- **Verdict:** CONFIRMED. One scope caveat: the sweep covered `marketplace/` only, and a second
  instance of the same shape lives in the project-local
  `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:789` (G3).

### D2 — fix the RESOLUTION, not the call site

- **Required (plan):** *"under a pinned worktree, the resolver returns the main checkout — asserted
  directly on the resolver, not only through the capture."*
- **Found:** `_invariants.py:362-414` `_main_repo_root()`; override branch first
  (`base_dir_override_active()`, `marketplace_paths.py:420`), then `main_checkout_root()`
  (`marketplace_paths.py:473` → `_main_checkout_root` at `:441`, `git rev-parse --git-common-dir`),
  returning `None` on `RuntimeError` with no cwd fallback. `_current_repo_root()` at `:336` retains the
  old semantics and is used only by `_run_script` (`:469`) and by `_main_repo_root`'s override branch.
- **Checks run:**
  - The direct-on-the-resolver assertion exists and is not routed through a capture:
    `test_invariants_main_resolution.py:114` `test_main_repo_root_resolves_to_main_from_pinned_worktree_cwd`
    (real `git worktree add`, real `chdir`), with its counterpart at `:134`.
  - First-party probe (not the suite): built a real repo, added a linked worktree at
    `<main>/.plan/local/worktrees/p`, chdir'd into it with no override →
    `_main_repo_root() = /tmp/probe310-…/main`, unequal to the worktree. D2 works in the default
    configuration.
  - Mutation M1 (resolver body replaced by `return _current_repo_root()`, applied to the shipped file
    from a byte snapshot): `6 failed, 13 passed`, and the drift test reproduced the reported symptom
    verbatim (`main_sha, 4-plan → 5-execute, 142cb53f… -> e6ae285b…`).
- **Verdict:** CONFIRMED. Caveat: under an active base-dir override the main-scoped resolution still
  follows cwd, and from a worktree **subdirectory** it returns that subdirectory — reproduced here
  (see § Correctness review, G1). The shipped docs disclose this; nothing tests or closes it.

### D3 — fail loud on the impossible state

- **Required (plan):** *"the assertion rejects an equal pair under a worktree-backed plan and permits
  it for a plan genuinely running on main."*
- **Claimed (report):** the trigger is deliberately **narrower** — refuse only when `main_sha ==
  worktree_sha` **and** `_main_repo_root()` resolves to the same directory as `worktree_path`, because
  a worktree-backed plan whose feature branch carries no commit legitimately produces an equal pair.
- **Found:** `_invariants.py:1813-1865` `_assert_main_capture_read_main`, invoked from `capture_all`
  at `:1896`. Exception class `:214-271`. Payload builder `_handshake_commands.py:354`; `cmd_capture`
  catch at `:445` (before `_row_for_capture`/`upsert_row` at `:447-455`, so no row is written);
  `cmd_verify` catch on the `capture_all` call at `:557`. `VERIFY_REFUSAL_ERRORS` membership at
  `_cmd_lifecycle.py:46-52`; strict non-zero exit at `phase_handshake.py:138-143`.
- **Checks run:**
  - Both directions and the no-worktree-path direction are covered by real tests
    (`test_invariants_main_capture_refusal.py:71, :94, :119, :135`), plus a real-worktree commit-less
    branch case at `test_invariants_main_resolution.py:265`.
  - Mutation M2 (assertion not invoked from `capture_all`): `4 failed, 15 passed` — matches the
    report's M2 row exactly.
  - Mutation M3 (same-tree gate removed, equality alone triggers): `2 failed, 17 passed` — matches the
    report's M3 row exactly, and the two reds are precisely the "distinct trees are permitted" pair.
  - `cmd_capture` refuses before persisting: verified by reading the ordering at `:445` vs `:447`, and
    by the test's `written == []` assertion (`test_invariants_main_capture_refusal.py:194`).
- **Verdict:** CONFIRMED, with the deviation labelled. **The literal *Done when* is not implemented**:
  the assertion does *not* reject every equal pair under a worktree-backed plan — it rejects only
  same-tree ones. The narrowing is correct (the plan's own ⭐ premise, "such a row is definitionally
  wrong unless the plan runs on main", is false for a commit-less feature branch, which
  `phase-5-execute` Step 2.5 produces for every analysis-only plan), it is disclosed in the report and
  in shipped prose (`phase-handshake.md:311`), and it is pinned by a real-repo test. This is the plan
  being wrong, not the run — recorded as a deviation, not as remediable work.

### D4 — quarantine the already-written rows

- **Required (plan):** report the affected count **separately** from the number of plans examined; if
  the corpus is unreachable, ship the documented rule and report the count blocked.
- **Claimed (report):** Plans examined **0**; records affected **BLOCKED**; rule shipped in
  `plan-retrospective/references/invariant-check-summary.md`, as a two-step check (fingerprint, then
  `captured_at` era).
- **Found:** the two numbers are stated as two rows (`report-01.md:169-173`). `.plan/local/` in this
  clone holds only `logs/` and `marshall-state.toon` — no `plans/` — so the BLOCKED verdict is
  reproducible. The rule is at `invariant-check-summary.md:46-55`; § Inputs was corrected at `:22-24`
  and the retired `status.metadata.phase_handshake` / `.invariants` keys are gone tree-wide (grep over
  `marketplace/` and `doc/` returns nothing outside `doc/plans/`). `captured_at` is a real stored
  column (`_handshake_store.py:18-20`, index 1) and `summarize-invariants.py` does strip it
  (`:60-64`), so F31/F34/F37's corrections are real.
- **Verdict:** PARTIAL. The plan's letter is met, but the shipped rule cannot be executed as written:
  - **Step 2 has no obtainable cutoff.** *"Compare the row's `captured_at` against when the
    main-anchored resolution fix landed in this repository"* — the file names no date, no PR, no
    commit, and no way to determine one. Its declared reader is an LLM compiling a retrospective
    aspect, which has no basis to supply it (G2).
  - **The rule routes around the sanctioned access path.** It instructs *"open
    `{plan_dir}/handshakes.toon`"*, and `plan-retrospective/SKILL.md:34` now says the same. Plan
    directories live under `.plan/local/plans/{plan_id}/` (`_handshake_store.py:59` →
    `file_ops.base_path`), which the repository's hard rules forbid reading directly — while
    `phase_handshake list --plan-id {plan_id}` projects **every** `HANDSHAKE_FIELD`, `captured_at`,
    `main_sha` and `worktree_sha` included (`_handshake_commands.py:722-732`). The one route that
    supplies exactly what the rule needs is not mentioned (G4).

### D5 — tests, each verified to fail pre-fix

- **Required (plan):** three named cases (a) main ≠ worktree at the boundary, (b) the refusal rejects,
  (c) the summariser emits no drift — each verified to fail pre-fix.
- **Found:** `test/plan-marshall/plan-marshall/test_invariants_main_resolution.py` (10 tests) and
  `test_invariants_main_capture_refusal.py` (9 tests). Counted by collection, not from the report:
  `uv run python -m pytest … -o addopts="" -q` → `19 passed in 2.62s`.
  - (a) `test_capture_main_sha_records_main_head_not_the_pinned_worktree_head:200`, plus the
    dirty-flag settler at `:223` (dirties only the worktree, so a non-zero `main_dirty` could only mean
    the wrong tree).
  - (b) the refusal module's nine, listed above.
  - (c) `test_summariser_sees_no_main_sha_drift_across_the_execute_boundary:302` — rows derived from
    the **real** capture at both cwds and fed to the real `detect_drift`, not hand-fed.
- **Verdict:** CONFIRMED. See § Test adequacy for the mutation evidence.

## Correctness review

I read `_invariants.py` (helpers, the three `main_*` captures, the cross-field assertion, `capture_all`,
the registry), `_handshake_commands.py` (`cmd_capture`, `cmd_verify`, the payload builder,
`_check_main_dirty_drift`), `marketplace_paths.py` § main-anchored resolution, `phase_handshake.py`
`main()`, and both new test modules. One defect and two lesser observations:

1. **Under a NON-CANONICAL base-dir override the main-scoped resolution still follows cwd, and the new
   refusal misses it from a subdirectory.** `_invariants.py:409-410` delegates the override branch to
   `_current_repo_root()`, which returns `Path.cwd()` for any base dir that is not literally
   `*/.plan/local` (`:353-359`). Reproduced by execution against a real linked worktree at
   `<main>/.plan/local/worktrees/p`, sweeping the override shape against the cwd:

   | `PLAN_BASE_DIR` | cwd | `_main_repo_root()` | `main_sha` reads | refusal |
   |---|---|---|---|---|
   | unset (production) | worktree *or* worktree/src | main | **main** | — |
   | flat bare directory | worktree | worktree | **worktree** | FIRED |
   | flat bare directory | worktree/**src** | worktree/src | **worktree** | **did not fire** |
   | `<main>/.plan` | worktree | worktree | **worktree** | FIRED |
   | `<main>/.plan` | worktree/**src** | worktree/src | **worktree** | **did not fire** |
   | `<main>/.plan/local` | either | main | **main** | — |
   | `<worktree>/.plan/local` | either | worktree | **worktree** | FIRED |

   So the exact defect this plan fixed — a `main_*` column holding the worktree's value — is still
   reachable, and from a worktree subdirectory the guard that exists to catch it passes the row
   through, because `_assert_main_capture_read_main` compares
   `main_root.resolve() != worktree_path.resolve()` (`:1856`) by **equality** rather than containment.
   Two refinements over the first draft of this item, both from the sweep: the mislabel is **not**
   subdirectory-specific (at the worktree root the value is equally wrong and merely fail-closed —
   the subdirectory is what turns a refusal into a silent write), and it is **not** flat-override-
   specific (`<root>/.plan` reaches it too; only the canonical `*/.plan/local` shape is safe). All
   three `main_*` captures share `_main_repo_root`, so all three are mislabelled together. Nothing in
   production sets `PLAN_BASE_DIR` (no writer under `marketplace/`) and nothing calls `set_base_dir()`
   outside its own definition, so this is an operator-set configuration, not a default-path defect —
   which is why G1 is rated medium and not high. The shipped rule at `invariant-check-summary.md:54`
   and the resolver's own docstring (`:386-392`) disclose it; nothing tests or closes it. → **G1**

2. **`except OSError: return` at `_invariants.py:1858` is fail-open**, as is the `main_root is None or
   not raw_worktree` early return at `:1852`. Both are documented as unreachable-by-construction
   defence (`:1830-1834`), and the surviving direction is the safe one (a missed refusal, not a false
   one). Not raised as a gap.

3. **No defect found in the split itself.** `_run_script` (`:469`) still uses `_current_repo_root`,
   which is required — it resolves `{root}/.plan/execute-script.py` and the subprocess cwd, and the
   7 plan-state captures depend on reaching the worktree-resident executor. Redirecting it, as the
   plan's refuted hypothesis implied, would have broken those 7. The layer-D drift check
   (`_handshake_commands.py:288`) is gated to planning-phase boundaries, so the declared collateral
   ("both sides of the `verify --phase 4-plan` comparison are now main's set") follows from the code
   as read.

## Test adequacy

| Deliverable | Covering tests | Non-vacuity evidence |
|---|---|---|
| D2 (resolver) | `test_invariants_main_resolution.py:114, :134, :154, :173` | **M1** — `_main_repo_root` body replaced by `return _current_repo_root()`: `6 failed, 13 passed`. Reds include both resolver tests, both capture tests, the commit-less-branch test and the drift test |
| D3 (refusal) | `test_invariants_main_capture_refusal.py:71, :94, :119, :135, :178, :197, :222, :235, :268` | **M2** — assertion call removed from `capture_all`: `4 failed, 15 passed`. **M3** — same-tree gate removed so equality alone triggers: `2 failed, 17 passed`, and the two reds are exactly the "distinct trees permitted" pair, which is the direction M3 attacks |
| D5(a) | `test_invariants_main_resolution.py:200, :223` | Red under M1 |
| D5(b) | the nine refusal tests + `:265` | Red under M2/M3 |
| D5(c) | `test_invariants_main_resolution.py:302` | Red under M1, with the reported symptom reproduced |

All three mutations were applied to the shipped `_invariants.py` and restored from a byte snapshot
taken by this audit at `/tmp/verify-310-mutsweep/_invariants.py.orig` (SHA-256 prefix `08c3dcfa4f896e3c`,
83306 bytes). Post-restore the file hashes identically and `git status --porcelain` reports nothing for
it. No `git checkout` / `git restore` / `git stash` was used, and no file this audit did not mutate was
touched.

**The report's own figures for M1, M2 and M3 (6, 4, 2 red) reproduce exactly.** I did not attempt the
other eight rows — several mutate test-adjacent constants rather than `_invariants.py`, and three
independent exact matches are sufficient evidence that the matrix was measured rather than asserted.

**Union of the three red sets I ran: 11 of 19, not 15.** Named, so the figure is checkable — M1 reds
are `test_invariants_main_resolution.py::{main_repo_root_resolves_to_main_from_pinned_worktree_cwd,
main_repo_root_returns_none_outside_a_git_repository,
capture_main_sha_records_main_head_not_the_pinned_worktree_head,
capture_main_dirty_reads_main_not_the_pinned_worktree, a_commit_less_feature_branch_is_captured_not_refused,
summariser_sees_no_main_sha_drift_across_the_execute_boundary}`; M2 reds are
`test_invariants_main_capture_refusal.py::{refuses_when_both_columns_resolved_to_the_same_tree,
the_gate_is_the_persisted_path_not_the_use_worktree_flag,
cmd_capture_returns_structured_refusal_and_writes_no_row,
cmd_verify_returns_the_same_refusal_rather_than_raising}`; M3 reds are
`a_commit_less_feature_branch_is_captured_not_refused` (shared with M1) and
`permits_equal_shas_when_the_two_trees_are_distinct`. The report's "union 19 of 19" is a claim about
its **eleven** mutations, not about these three, and must not be read across — see § Negative results,
where an earlier draft of this document did exactly that.

**One test gap:** `test_main_repo_root_honours_base_dir_override:154` pins only the *canonical* override
shape (`<root>/.plan/local` → `<root>`). The **flat** override shape — the one that returns `Path.cwd()`
and produces the defect in § Correctness review 1 — has no test in either direction. Folded into G1.

## Report accuracy

Every checkable factual claim in `report-01.md` held, with the exceptions below. Re-derived here rather
than copied: registry 15, main-named 3, resolver callers 4 (pre-fix), `_run_script` 10 sites → 7
captures, tests 10 + 9 = 19, build-gate 11 Python files (6 production, 5 test — counted from
`git show --stat 7612c3a`), M1/M2/M3 red counts 6/4/2.

1. **Overstated (low).** *"no consumer of the `main_*` columns is unexamined — `summarize-invariants.py`
   is the only one"* (`report-01.md:485-486`). `_handshake_commands._check_main_dirty_drift:288` reads
   `captured_row['main_dirty_files']` and `_diffs:485-512` reads every `main_*` column. The report did
   examine the former (it is D5's declared collateral), so *"unexamined"* holds; *"the only one"* does
   not. → G8
2. **True but scope-limited (low).** *"The defect's shape … occurs **exactly once** across
   `marketplace/`"* (`:79-80`). Verified true for `marketplace/`. The sweep's boundary is not stated,
   and a second instance of the same shape sits in the project-local
   `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:789`. → G3
3. **UNVERIFIABLE.** *"`20665 passed, 14 skipped`"* and *"six full `./pw verify` runs"* — the brief
   forbids running the full suite, and the run's PR-time tree is not this tree. Not disputed; not
   confirmed.
4. **UNVERIFIABLE.** The reviewer-participation table (comment ids, rate-limit bodies) and the
   wall-clock/dispatch figures. No first-party access to PR #1286's comment surfaces from this audit.

Claims specifically re-checked and **true**: the two-namespace separation (`sync-with-main.md:84`); no
production caller of `set_base_dir()` (grep over `marketplace/` — only its own definition at
`file_ops.py:404`); `base_dir_override_active` has exactly the four readers its docstring names
(`marketplace_paths.py:566, :616`; `_lessons_io.py:112`; `_invariants.py:409`) and no fifth
hand-spelled disjunction; `captured_at` is `HANDSHAKE_FIELDS[1]`; `summarize-invariants.py` strips it;
the retired `status.metadata.phase_handshake` keys are absent tree-wide; both `tmp_path`-premise
docstrings in `test_phase_handshake_validators.py:150, :181` carry the corrected note; `_lessons_io`
uses the shared predicate; `doc/concepts/branches-and-worktrees.adoc:24` needed no edit and is accurate
post-fix.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| 1. A second automated review pass owed (CodeRabbit + Sourcery both rate-limited) | **Moot** | PR #1286 merged as `7612c3a`; a merged PR cannot receive the deferred pass, and later commits have since changed the touched files |
| 2. `TaskGraphInvalid` has no handler in `cmd_capture` or `cmd_verify` | **Open** | `grep TaskGraphInvalid marketplace/…/scripts/*.py` → raised at `_invariants.py:1087`, declared in `capture_all`'s `Raises:` at `:1879`, and **no** `except TaskGraphInvalid` and no `task_graph_invalid` error code anywhere. Fail-closed as bounded (the raise precedes `_row_for_capture`), so the loss is diagnostic shape only. → G9 |
| 3. Prose residue at sites the previous finding did not point at (n−1-of-n) | **Open — two fresh instances found** | `marketplace_paths.py:403-405` still cites `merge_lock.py`'s `_main_checkout_root`, which no longer exists in that file (G6); `invariant-check-summary.md:9-18` claims to be "From `INVARIANTS` registry" while listing 8 of the 15 entries (G5) |
| 4. Contract-change proposal: forbid `git checkout` as the mutation-restore mechanism | **Closed** | `b199d94` *"chore(cloud-plan-lane): require snapshot-based restore for mutation sweeps (#1289)"*; the rule is live at `.claude/skills/cloud-plan-lane/SKILL.md:773-774` |
| *"Not residue"*: `config_hash`'s cwd-relative `marshal.json` read | **Correctly excluded** | `_invariants.py:1665` — the name makes no main claim and the ADR-002 cwd rule applies. No work owed |

## Out-of-scope and collateral

- **Respected.** No second explicit-tree argument was added at the capture site — the captures still
  pass a resolved root to `git_head` / `git_dirty_count` / `git_dirty_files`, unchanged in shape
  (`_invariants.py:597-600, :609-612, :673-679`). No corpus rewrite exists anywhere in the diff. The
  footprint-read defect was not merged in: `git show --stat 7612c3a` touches only the handshake,
  lessons-IO, lifecycle-constant, marketplace-paths and retrospective surfaces.
- **Collateral, declared.** `_lessons_io.py` and its test, and `marketplace_paths.py`, are outside the
  plan's four "Expected surface" entries. Both are consequences of F6 (converting the one remaining
  hand-maintained override disjunction to the shared predicate) and are disclosed in the report's
  round-1 table. Verified as real and consistent, not silent.
- **Collateral, declared.** The layer-D `verify --phase 4-plan` comparison now has main on both sides
  (`report-01.md:311-317`). Consistent with `_check_main_dirty_drift`'s gating as read.

## Method and coverage

**Checked, first-party:** the plan and report end to end; `_invariants.py`, `_handshake_commands.py`,
`marketplace_paths.py`, `phase_handshake.py`, `_handshake_store.py`, `summarize-invariants.py`,
`_cmd_lifecycle.py`, `merge_lock.py` § main-anchored, both new test modules, the two touched reference
docs, `plan-retrospective/SKILL.md`, `branches-and-worktrees.adoc`; the pre-fix `_invariants.py` at
`7612c3a^`; `git show --stat 7612c3a`. Counts re-derived by reading, by AST closure, and by pytest
collection. Three mutations executed against the shipped file with a self-taken byte snapshot. Two
resolver behaviours reproduced by a standalone probe against a real `git worktree add`.

**Not checked, and why:**

- `./pw verify` and its `20665 passed` figure — the brief forbids the full suite.
- The full 11-row mutation matrix — three exact reproductions were taken as sufficient; rows M4-M11
  target constants and CLI paths rather than `_invariants.py` and would each need a separate snapshot.
- PR #1286's review surfaces, comment ids, and the cost/wall-clock figures — no first-party access.
- Whether `worktree_metadata_drift` / `worktree_dirty_at_boundary` (members of `VERIFY_REFUSAL_ERRORS`
  absent from `phase_handshake.py`'s strict-exit tuple at `:138-143`) exit non-zero by another route.
  Pre-existing and outside this plan's deliverables; noted so the asymmetry is not mistaken for a
  clean check.

**Negative results worth stating:** no fail-open branch, off-by-one, unguarded `None`, stale-surface
read or order-dependency was found in the shipped resolver, the three captures, the cross-field
assertion, or either verb's error handling, beyond the override hole recorded as G1. The registry's
"not applicable" contract (`value is None → column omitted`, `_invariants.py:1893-1894`) is honoured by
all three `main_*` captures. No test in either new module was found vacuous: every one of the 19 is in
the red set of at least one of the three mutations I ran, except the four that M1/M2/M3 do not target
by construction (the two `None`-guard tests, the `VERIFY_REFUSAL_ERRORS` membership test, and the
clean-exit negative control) — each of which asserts a value the mutations do not perturb.

**Working-tree discipline:** this audit mutated exactly one file (`_invariants.py`) and restored it
byte-for-byte from its own snapshot. The three files reported modified by `git status --porcelain` at
close (`manage-metrics.py`, `_plan_parsing.py`, `claude_runtime.py`) belong to concurrent audit agents
and were never opened or written here.
