# Gaps — 210-named-recovery-discards-operator-config

**Source:** verification.md (same directory)   **Open items:** 5

## G1 — Retire the destructive `git checkout -- .plan/marshal.json` recovery contract still pinned by the phase-2-refine test

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `test/plan-marshall/phase-2-refine/test_phase_2_refine_manage_config_readonly.py:12-13,
  22-23, 215-275` (file is 275 lines) — `test_marshal_json_restored_after_checkout`, whose body quotes
  the removed command at `:216`, `:219`, `:224`, `:259`
- **What is wrong:** The plan removed the unconditional `git checkout -- .plan/marshal.json` recovery
  from all three workflow-doc sites, but this test file still states it as the live contract in four
  places: the module docstring (*"These tests pin both the mutation detection path and **the recovery
  path**"*, and *"``git checkout -- .plan/marshal.json`` restores clean state after the mutation"*),
  the test's own docstring (*"This pins the recovery path: after the mutation is detected, the
  post-refine orchestrator runs ``git checkout -- .plan/marshal.json`` to undo the change"*), and the
  inline comment `# run the orchestrator recovery command.` The orchestrator no longer does this — the
  authority at `planning.md:390` now mandates `git diff -- .plan/marshal.json` plus an explicit
  operator disposition. The test is green (`2 passed`), so nothing surfaces the drift. This directly
  contradicts report-01.md's *"Beyond-diff stale-claim sweep across the whole bundle and repo: none
  survives"*, and it sits on the `*.py` surface report-01.md claims D0's sweep covered.
- **Why it matters:** A green, named regression test is the strongest form of "this is the contract".
  A maintainer reading `test_marshal_json_restored_after_checkout` learns that the post-refine
  orchestrator restores `marshal.json` by discarding it — the exact belief this plan exists to
  destroy — and would reasonably re-introduce that instruction into a workflow doc on its authority.
- **Fix:** Rewrite the test to pin the *current* recovery contract rather than the removed one. Keep
  `test_manage_config_set_dirties_marshal_json` (the detection half) unchanged. Replace
  `test_marshal_json_restored_after_checkout` with a test whose subject is the inspection step —
  e.g. assert that `git diff -- .plan/marshal.json` in the synthetic repo emits a non-empty diff after
  the mutating `manage-config set`, so the operator-facing inspection command the authority prescribes
  is the thing pinned. Update the module docstring's "Two test cases" list, the "recovery path"
  sentence, and the `# run the orchestrator recovery command.` comment accordingly, and cross-reference
  `plan-marshall:plan-marshall/workflow/planning.md` § "Named recovery case — `.plan/marshal.json`" as
  the authority. If the checkout-restores-clean-state assertion is judged worth keeping at all, it must
  be re-titled and re-documented as a git-semantics fact, never as "the orchestrator recovery command".
- **Done when:** the symbol `test_marshal_json_restored_after_checkout` no longer exists anywhere under
  `test/plan-marshall/phase-2-refine/`; the strings `the recovery path` and
  `post-refine orchestrator runs` no longer appear in
  `test_phase_2_refine_manage_config_readonly.py` attached to a `git checkout --` instruction; the
  module docstring's numbered test list names `git diff -- .plan/marshal.json` and cross-references
  `plan-marshall:plan-marshall/workflow/planning.md` § "Named recovery case — `.plan/marshal.json`";
  and
  `uv run python -m pytest test/plan-marshall/phase-2-refine/test_phase_2_refine_manage_config_readonly.py -o addopts=""`
  passes.
- **Module/topic:** `plan-marshall` bundle — `phase-2-refine` tests / named-recovery contract

## G2 — Make the D2 single-authority guard detect a restatement, not just a duplicated literal

- **Kind:** vacuous-test
- **Severity:** high
- **Where:** `test/plan-marshall/plan-marshall/test_named_recovery_marshal_config.py:118-120` —
  `_references_authority` (`:112-115` is `_is_authority`, the other half of the guard), consumed at
  `:196` inside `test_named_recovery_contract_is_a_single_authority` (`:180-200`)
- **What is wrong:** `_references_authority(text)` returns
  `'planning.md' in low and 'named recovery' in low`. Every derived region begins with the heading
  `**Named recovery case — \`.plan/marshal.json\`**`, so the second clause is true by construction, and
  the first is satisfied by any region whose `**Cross-references**` block mentions `planning.md`.
  Re-running the predicate against the pre-fix files (`b87e0751^`) returns `True` for **both**
  planning-outline.md restatements — i.e. the assertion passes against the exact three-drifting-copies
  state the test's own docstring says it detects. Confirmed live by mutation: replacing the
  `planning-outline.md:257` reference with a full self-contained restatement of the contract (using
  `git diff .plan/marshal.json` rather than the literal `git diff -- .plan/marshal.json`) leaves all
  three tests **green**. Only the `len(authorities) == 1` half is load-bearing, and it keys on one
  exact string.
- **Why it matters:** report-01.md claims this test "pins the collapse against future re-drift".
  It does not. The re-drift shape the plan explicitly warns about — a copy of the contract growing back
  at a phase boundary — passes CI silently, which is how the original triplet came to exist.
- **Fix:** Replace the `'planning.md' in low` heuristic with a check that the region is *short and
  deferential*: assert every non-authority region (a) contains an explicit pointer to the authority
  section — match the cross-reference form `workflow/planning.md` … `Named recovery case` on a
  `- ` bullet or inline `§` citation, and (b) does **not** restate the contract, e.g. its body is under
  a fixed line/character budget, or it does not contain the disposition enumeration (`Keep` **and**
  `Discard` as list items) that only the authority may carry. Widen `_is_authority` at the same time so
  it recognises any concrete `git diff` inspection command against `.plan/marshal.json`, not the single
  literal `git diff -- .plan/marshal.json`.
- **Done when:** injecting a full restatement of the contract at `planning-outline.md`'s outline
  boundary (with or without the exact `git diff --` literal) makes
  `test_named_recovery_contract_is_a_single_authority` fail, and the unmodified tree still passes.
- **Module/topic:** `plan-marshall` bundle — named-recovery regression tests

## G3 — Assert that EVERY derived named-recovery region is inspection-first, not just the three known ones

- **Kind:** missing-test
- **Severity:** high
- **Where:** `test/plan-marshall/plan-marshall/test_named_recovery_marshal_config.py:66`
  (`_UNCONDITIONAL_DISCARD`), `:99-109` (`_is_inspection_first`), `:123-141`
  (`test_named_recovery_never_instructs_unconditional_discard`), `:144-177`
  (`test_named_recovery_inspection_first_population_nonempty_and_covers_known_members`)
- **What is wrong:** The offender predicate requires the literal prefix
  `Recovery:\s*git checkout -- \.plan/marshal\.json`, and the "always safe" predicate requires the
  literal `always safe` / `always a spurious`. D3(b) then asserts only that the *known* members
  (planning.md + two planning-outline.md boundaries) are inspection-first — it never asserts that
  *every* derived region is. Evaluating the three predicates against a synthetic fourth boundary that
  reads *"restore it from HEAD with `git checkout -- .plan/marshal.json`. `marshal.json` is never an
  execute-phase output artifact, so the dirty state is a spurious write with no phase work to lose."*
  yields offender = `False` and authority = `False`. Whether **all three** tests miss it turns on one
  further detail, established live by writing the block into a fourth file inside the swept directory
  and running the real test file (not by reading the predicates). A block carrying **no**
  `planning.md` mention is *caught*: `_references_authority` returns `False` and
  `test_named_recovery_contract_is_a_single_authority` fails by name
  (`… restates the named-recovery contract instead of referencing the single authority`). A block
  carrying the **standard cross-reference bullet that every real reference site already carries**
  (`` - `plan-marshall:plan-marshall/workflow/planning.md` § "Named recovery case — `.plan/marshal.json`" ``)
  returns `_references_authority == True`, and the injected destructive site then passes **3 of 3**.
  That second variant is the realistic shape — it is what a maintainer copying an existing reference
  block would produce — and it is invisible to all three tests. This contradicts the file's own docstring (*"so a new phase boundary that adds such a
  block is covered automatically"*) and report-01.md's *"a future fourth boundary is covered
  automatically"*.
- **Why it matters:** D0's whole point is that the three sites were a sample. The regression guard
  currently re-encodes the sample: it protects the three sites the plan already fixed and lets a fourth,
  reworded destructive site through — the same sample-as-population error, one layer down.
- **Fix:** In `test_named_recovery_never_instructs_unconditional_discard`, add a universal assertion:
  every region in the derived population must satisfy `_is_inspection_first(block)` (offenders listed by
  `path.name:lineno`), replacing the current known-member-only coverage in D3(b) — or keep the
  known-member check as an additional floor. Broaden `_UNCONDITIONAL_DISCARD` to match any
  `git checkout -- .plan/marshal.json` / `git restore … .plan/marshal.json` occurrence that is **not**
  inside a sentence warning against it (e.g. exclude a region only when the same region also satisfies
  `_is_inspection_first`), so the authority's own cautionary mention at `planning.md:392` still passes.
- **Done when:** adding, at any file under
  `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/`, a named-recovery block that
  (i) instructs `git checkout -- .plan/marshal.json` without the literal `Recovery:` prefix,
  (ii) carries no `always safe` / `always a spurious` wording, **and** (iii) carries the standard
  `` `plan-marshall:plan-marshall/workflow/planning.md` § "Named recovery case …" `` cross-reference
  bullet — the variant that passes 3 of 3 today — makes
  `test_named_recovery_never_instructs_unconditional_discard` fail and name that block in its
  offender list, while the unmodified tree still passes 3 of 3. (The weaker form of this condition —
  a block *without* the cross-reference bullet — is already met today, via
  `test_named_recovery_contract_is_a_single_authority`, so it does not discriminate.)
- **Module/topic:** `plan-marshall` bundle — named-recovery regression tests

## G4 — Tighten the authority's premise citation in planning.md

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md:390` (the
  premise sentence) and its `**Cross-references**` block at `:408-412`, whose first two bullets cite
  `phase-2-refine` § Allowed write paths and § Prohibited actions and nothing else
- **What is wrong:** Two imprecisions in the sentence that carries the whole non-output premise.
  (a) It asserts *"no planning phase (2-refine, 3-outline, 4-plan) may mutate project configuration"*
  but cites only `plan-marshall:phase-2-refine` § Enforcement → Prohibited actions, whose
  `manage-config` bullet (`phase-2-refine/SKILL.md:35`) is scoped to refine alone. The three-phase claim
  is true — `phase-3-outline/SKILL.md:35` and `phase-4-plan/SKILL.md:34` each forbid mutating anything
  outside `.plan/local/plans/{plan_id}/` — but the reader who follows the one citation cannot confirm
  two thirds of it. (b) The same sentence says the prohibition *"confines writes to
  `.plan/local/plans/{plan_id}/**`"*, whereas `phase-2-refine/SKILL.md:38-40` § Allowed write paths
  lists **two** paths — `.plan/local/plans/{plan_id}/**` and `.plan/local/worktrees/{plan_id}/**`.
- **Why it matters:** This block is now the single authority for the recovery; its premise is the only
  thing standing between a reader and the old false inference. A citation that under-covers its own
  claim is the shape of defect this epic tracks, and the omitted worktree path makes the write
  confinement look narrower than it is.
- **Fix:** In the parenthetical, cite all three phases — add
  `plan-marshall:phase-3-outline` § Enforcement → Prohibited actions and
  `plan-marshall:phase-4-plan` § Enforcement → Prohibited actions alongside the existing
  phase-2-refine citation (or scope the sentence to refine and state the outline/plan premise
  separately). Correct the write-confinement clause to name both allowed write paths, or reword it to
  "confines writes to the plan-scoped paths listed in § Allowed write paths".
- **Done when:** every phase named in the sentence has a citation a reader can follow to a block that
  states the prohibition for that phase, and the write-confinement clause matches
  `phase-2-refine/SKILL.md` § Allowed write paths.
- **Module/topic:** `plan-marshall` bundle — `skills/plan-marshall/workflow/planning.md`

## G5 — The layer-D recovery loop still routes a dirty tracked `.plan/marshal.json` to `git checkout --` as "the typical case"

- **Kind:** incomplete-sweep
- **Severity:** high
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/worktree-handling.md:217-225`
  — § "Recovery Loop" (the destructive instruction is at `:223`), plus the § "Granularity Trade-Off"
  bullet at `:212` that states the same recovery, and § "Filter Rule" at `:229-231` which is what puts
  `.plan/marshal.json` into the payload the loop acts on
- **What is wrong:** D0 concluded *"No fourth site of this assertion shape exists in the documentation
  or script surface"* (report-01.md § D0), and verification.md's D0 row repeated *"Independent shape
  sweep over `marketplace/**`, `doc/**`, `*.py` found no fourth doc site"*. **A fourth site exists**, on
  the declared `marketplace/bundles/**` surface. § "Recovery Loop" tells the reader, when
  `phase_handshake verify --strict` fails with `error: main_checkout_dirtied_during_plan`:

  > 2. **Decide per-path: revert or relocate.**
  >    - *Revert* — when the change was unintended (typical case): `git -C {main_checkout} checkout -- {path}` to drop the dirty state.

  and at `:212`, *"the operator must revert the leaked main-checkout changes (or move them into the
  worktree branch)"*. The inspection step the loop does carry (`:221` — *"Inspect `newly_dirty[]`. The
  payload lists the exact **paths**"*) surfaces a path list, never the diff, so nothing in the loop lets
  the reader tell **who wrote the file** or whether the edit was intended — the exact inference gap this
  plan exists to close. And the same document's § "Filter Rule: `.plan/` Paths Are Excluded Only When
  Untracked" (`:231`) names `marshal.json` explicitly as one of the git-**tracked** `.plan/` files that
  *"is a real leak into the main checkout and is retained"* — so `.plan/marshal.json` is precisely a
  path that reaches `newly_dirty[]` and is then routed to `git checkout --` under the label
  *"typical case"*.
- **Why it matters:** The plan's Goal is *"the recovery path for a dirty `marshal.json` requires
  inspection and an explicit disposition, not an unconditional discard."* For this path the Goal is not
  met: the doc presumes unintendedness as the typical case, from a guard that establishes only that the
  path became dirty between two boundaries. The document is agent-facing, not merely operator-facing —
  `execute-task/SKILL.md:40` and `phase-5-execute/SKILL.md:55` both direct the reader to it. The site
  fell between two sweeps: 210 swept only `skills/plan-marshall/workflow/*.md`, while sibling plan 140
  (`fb41f014`) touched this same bundle (`workflow-integration-git/SKILL.md`, `git-workflow.py`) but not
  `standards/worktree-handling.md`. It also undercuts report-01.md's basis for declaring the two
  surfaces disjoint — they share a bundle, and this doc is the shared residue.
- **Fix:** In `worktree-handling.md` § "Recovery Loop": (a) change step 1 so it surfaces content, not
  only paths — add `git -C {main_checkout} diff -- {path}` for each path in `newly_dirty[]`; (b) delete
  the parenthetical `(typical case)` from the *Revert* bullet at `:223` and replace it with the
  disposition requirement — a revert happens only on an explicit operator decision for that one path;
  (c) add the irrecoverability caveat in the wording the authority already uses at `planning.md:392`
  (`git checkout --` destroys uncommitted, unstaged content with no undo — no reflog and no `git fsck`
  recovers a worktree file); (d) add a cross-reference to
  `plan-marshall:plan-marshall/workflow/planning.md` § "Named recovery case — `.plan/marshal.json`" as
  the single authority, and name `.plan/marshal.json` as the highest-risk member of `newly_dirty[]`
  given § "Filter Rule". Amend the § "Granularity Trade-Off" bullet at `:212` to match. Then extend the
  regression surface: either widen `_derive_named_recovery_regions`
  (`test/plan-marshall/plan-marshall/test_named_recovery_marshal_config.py:69-87`) to sweep
  `workflow-integration-git/standards/*.md` as well, or add a sibling assertion over
  `worktree-handling.md`.
- **Done when:** `worktree-handling.md` contains no `(typical case)` qualifier on a `checkout --`
  instruction; § "Recovery Loop" step 1 names a concrete `git diff` command; § "Recovery Loop" carries
  the irrecoverability caveat and a cross-reference to `planning.md` § "Named recovery case —
  `.plan/marshal.json`"; and a test asserts that no `git checkout --` / `git restore` instruction in
  `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/worktree-handling.md`
  stands without an inspection-plus-operator-disposition qualifier in the same section — that test seen
  red against today's text and green after.
- **Module/topic:** `plan-marshall` bundle — `workflow-integration-git` / named-recovery contract

## Refuted during adversarial review

No gap was refuted in whole — G1, G2 and G4 were re-verified from the tree and stand as filed, and G3's
substance stands. Three **sub-claims** were refuted and are recorded here rather than dropped, because
the next reader needs to know they were tested and failed.

- **G3's stated predicate evaluation — refuted.** G3 asserted that the synthetic fourth boundary it
  quotes yields `references-authority = True` and is therefore *"invisible to all three tests"*. Running
  the real test file against that block, written as a fourth `.md` file in the swept directory, gives
  **1 failed, 2 passed**: `_references_authority` returns `False` (the quoted text contains no
  `planning.md` mention) and `test_named_recovery_contract_is_a_single_authority` names the block. The
  gap survives only in its cross-referencing variant, which was verified separately to pass 3 of 3;
  G3's § "What is wrong" and § "Done when" were rewritten to say so, since the original Done-when was
  already satisfied by the unmodified tree.
- **verification.md § Method, "Synthetic fourth-site check … no test flags it" — refuted**, for the same
  reason and by the same run. The bullet was corrected in place.
- **verification.md § Deliverable table, D0 row, "Hit count re-derived: 51 matching lines in 34 files" —
  not reproducible.** Re-running the union of the six pattern families report-01.md § D0 lists gives 68
  lines in 45 files excluding `doc/plans/`, and 134 lines in 62 files including it. Neither is 51/34, so
  the figure depends on an unstated pattern set and is a sample, not a derivation. The row now carries a
  figure with its pattern stated. This does not disturb the report's *"several dozen"* characterisation,
  which every one of these unions supports.
