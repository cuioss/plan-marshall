# Gaps — 210-named-recovery-discards-operator-config

**Source:** verification.md (same directory)   **Open items:** 4

## G1 — Retire the destructive `git checkout -- .plan/marshal.json` recovery contract still pinned by the phase-2-refine test

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `test/plan-marshall/phase-2-refine/test_phase_2_refine_manage_config_readonly.py:11-13, 22-23, 215-275` — `test_marshal_json_restored_after_checkout`
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
- **Done when:** `git grep -n "checkout -- .plan/marshal.json" -- test/` returns no line that presents
  the command as the orchestrator's recovery path, and the phase-2-refine test module's docstring names
  inspection-plus-disposition as the recovery contract.
- **Module/topic:** `plan-marshall` bundle — `phase-2-refine` tests / named-recovery contract

## G2 — Make the D2 single-authority guard detect a restatement, not just a duplicated literal

- **Kind:** vacuous-test
- **Severity:** high
- **Where:** `test/plan-marshall/plan-marshall/test_named_recovery_marshal_config.py:113-116` —
  `_references_authority`, consumed by `test_named_recovery_contract_is_a_single_authority:189-196`
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
- **Severity:** medium
- **Where:** `test/plan-marshall/plan-marshall/test_named_recovery_marshal_config.py:64-66`
  (`_UNCONDITIONAL_DISCARD`), `:123-142` (`test_named_recovery_never_instructs_unconditional_discard`),
  `:145-179` (`test_named_recovery_inspection_first_population_nonempty_and_covers_known_members`)
- **What is wrong:** The offender predicate requires the literal prefix
  `Recovery:\s*git checkout -- \.plan/marshal\.json`, and the "always safe" predicate requires the
  literal `always safe` / `always a spurious`. D3(b) then asserts only that the *known* members
  (planning.md + two planning-outline.md boundaries) are inspection-first — it never asserts that
  *every* derived region is. Evaluating the three predicates against a synthetic fourth boundary that
  reads *"restore it from HEAD with `git checkout -- .plan/marshal.json`. `marshal.json` is never an
  execute-phase output artifact, so the dirty state is a spurious write with no phase work to lose."*
  yields: offender = `False`, authority = `False`, references-authority = `True` — invisible to all
  three tests. This contradicts the file's own docstring (*"so a new phase boundary that adds such a
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
- **Done when:** adding a reworded destructive named-recovery block (no `Recovery:` prefix, no
  "always safe") at any workflow doc makes the test file fail, and the unmodified tree still passes.
- **Module/topic:** `plan-marshall` bundle — named-recovery regression tests

## G4 — Tighten the authority's premise citation in planning.md

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md:390` and its
  first cross-reference bullet
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
