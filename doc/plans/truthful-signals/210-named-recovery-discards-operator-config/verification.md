# Verification — 210-named-recovery-discards-operator-config

**Verified against:** commit `ac06e4fc`   **Landed as:** PR #1186, commit `b87e0751`   **Verdict:** implemented-with-gaps

## Method

What was actually done, in order:

- Read `plan.md` and `report-01.md` in full.
- Located the landed commit: `git log --oneline --all --grep '#1186'` → `b87e0751`
  ("fix(plan-marshall): named marshal.json recovery inspects before discarding"). Read the full diff
  (`git show -M --name-status b87e0751`, `git show b87e0751 -- <workflow files>`). Five paths:
  a rename of `210-….md` → `210-…/plan.md` (R100), the new `report-01.md`, the two workflow docs,
  and the new test file.
- Confirmed nothing later touched the changed files:
  `git log --oneline b87e0751..HEAD -- planning.md planning-outline.md test_named_recovery_marshal_config.py`
  → empty. HEAD content is exactly what landed.
- Opened at HEAD: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md`
  (authority block, line 390), `…/planning-outline.md` (lines 257 and 576),
  `test/plan-marshall/plan-marshall/test_named_recovery_marshal_config.py` (whole file),
  `marketplace/bundles/plan-marshall/skills/phase-2-refine/SKILL.md` § Enforcement,
  `…/phase-3-outline/SKILL.md` § Enforcement, `…/phase-4-plan/SKILL.md` § Enforcement,
  `marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md` § "Anti-pattern: never batch a
  destructive checkout", `test/plan-marshall/phase-2-refine/test_phase_2_refine_manage_config_readonly.py`.
- **Executed the plan's own derivation** against the tree with a standalone script replicating the
  test's predicates (`_derive_named_recovery_regions`, `_is_authority`, `_is_inspection_first`,
  `_references_authority`) — at HEAD **and** against the pre-fix files extracted from `b87e0751^`.
- Ran the plan's test file: `uv run python -m pytest test/plan-marshall/plan-marshall/test_named_recovery_marshal_config.py -o addopts="" -q` → **3 passed**.
- Ran `test/plan-marshall/phase-2-refine/test_phase_2_refine_manage_config_readonly.py` → **2 passed**.
- **Mutation 1 (regression check):** overwrote `planning.md` with its pre-fix content, re-ran the
  test file → **3 failed** (all three tests red). Restored from saved bytes; md5 confirmed identical.
- **Mutation 2 (drift check):** replaced the `planning-outline.md:257` *reference* with a full
  self-contained *restatement* of the contract (inspection-first, operator disposition, but using
  `git diff .plan/marshal.json` instead of the literal `git diff -- .plan/marshal.json`) — i.e. the
  exact "two copies that will drift" state D2 exists to prevent. Re-ran the test file → **3 passed**.
  Restored from saved bytes; md5 confirmed identical.
- **Synthetic fourth-site check:** evaluated the test's predicates against a hypothetical new phase
  boundary carrying the destructive instruction reworded without the literal `Recovery:` prefix and
  without "always safe" → no test flags it.
- Independent whole-tree sweeps (`git grep`) for: `always safe`, `always a spurious`,
  `checkout -- .plan/marshal.json`, `Recovery: git checkout`, `safe to (revert|delete|discard|…)`,
  `git restore|reset --hard|git clean|rm -rf|spurious write`, `Named recovery case`, `dirty_files`,
  `Recovery:` in `*.py`.
- `git status --porcelain` at finish shows nothing under
  `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/` or `test/plan-marshall/`.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: derive the "safe to delete/revert" population by assertion shape; report population size and hit count separately | population derived by shape, not command string; size and hit count reported separately | yes | yes | yes | **partial** | Re-derived at HEAD: 3 regions (`planning-outline.md:257`, `:576`, `planning.md:390`). Independent shape sweep over `marketplace/**`, `doc/**`, `*.py` found no fourth *doc* site; the only other `safe to delete/revert` hits are the counter-postures (`plugin-doctor/references/rule-catalog.md:230`, `shim-marker-convention.md:6`, `risky-fixes-guide.md:114`) and `doc/user/getting-started.adoc:94` (git-ignored `temp/`). Hit count re-derived: 51 matching lines in 34 files — consistent with "several dozen". **Missed on the `*.py` surface:** `test/plan-marshall/phase-2-refine/test_phase_2_refine_manage_config_readonly.py` (see G1) |
| D1 | Replace the false inference at every site; inspection first; the word "always" survives in no justification | every site instructs inspection first; "always" gone from justifications | yes | yes | yes | yes | `planning.md:390-397` is now premise → "It does **not** follow that the file is safe to discard" → `git diff -- .plan/marshal.json` → Keep/Discard disposition. `planning-outline.md:257`, `:576` carry the imperative "inspect the diff and obtain an explicit operator disposition before any discard — never revert `marshal.json` unconditionally". `git grep "always safe"` / `"always a spurious"` in both files → 0; the 5 remaining `always` occurrences are unrelated dispatch mechanics (`planning.md:109,266`, `planning-outline.md:98,132,470`). `git grep -c "Recovery: git checkout"` outside `doc/plans/` → 1 hit, and that is the regex literal in the new test |
| D2 | Collapse the triplet into ONE authority the sites reference | contract exists once | yes | yes | **guard is weak** | yes (for the state at HEAD) | Derivation at HEAD: exactly 1 region satisfies `_is_authority` (`planning.md:390`); the two outline sites are one-line imperatives + a cross-reference bullet to the authority. The drift corruption *"a spurious write that safe to revert"* is gone (`git grep "always a spurious"` outside `doc/plans/` → 0). **But** the test's `_references_authority` predicate is vacuous — see G2 |
| D3(a) | Recovery text does not instruct an unconditional discard; seen red pre-fix | holds, seen red | yes | yes | **narrow** | **no** | `test_named_recovery_never_instructs_unconditional_discard` passes at HEAD and goes red against pre-fix `planning.md` (mutation 1). Its offender predicate `_UNCONDITIONAL_DISCARD = r'Recovery:\s*git checkout -- \.plan/marshal\.json'` requires the literal `Recovery:` prefix, so a reworded destructive block escapes — see G3 |
| D3(b) | Population derivation asserted non-empty and contains the known members; seen red pre-fix | holds, seen red | yes | yes | yes | **no** | `test_named_recovery_inspection_first_population_nonempty_and_covers_known_members` passes at HEAD, red against pre-fix (`inspection_first` was `False` for all three pre-fix regions — re-derived directly). The non-vacuous control (`assert regions`) is real. But the test asserts only that the *known members* are inspection-first, never that *every* derived region is — see G3 |

**D0.** The derivation itself is sound and genuinely shape-keyed (it keys on the heading marker, not on
the command string that the fix removes — the right choice). The report's separation of population
size (3) from hit count ("several dozen", re-derived as 51 lines / 34 files) is accurate, and the
counter-postures it names are real: `execute-task/SKILL.md:160` does say `git checkout -- <files>` /
`git restore <files>` are "destructive of uncommitted working-tree content with no undo". The gap is
on the `*.py` half of the declared surface: the report states the sweep covered `*.py` and included
`git checkout --` among its patterns, yet
`test/plan-marshall/phase-2-refine/test_phase_2_refine_manage_config_readonly.py` — which quotes
`git checkout -- .plan/marshal.json` four times and whose module docstring and test docstring name it
as *the* orchestrator recovery path being pinned — was not surfaced (G1).

**D2.** The collapse is real *at HEAD*: one authority, two references. What is not real is the claim
that the new test "pins the collapse against future re-drift". `_references_authority(text)` is
`'planning.md' in low and 'named recovery' in low`. Every derived region begins with the heading
`**Named recovery case — …**`, so the second clause is true by construction; the first is satisfied by
any region whose `**Cross-references**` bullets mention `planning.md` — which the *pre-fix* copies
already did. I re-derived this against `b87e0751^`: both pre-fix planning-outline.md restatements
returned `_references_authority == True`. The loop assertion therefore passed against the exact
three-copy state it names. Mutation 2 confirms the live consequence: a full restatement re-inserted at
a non-authority site keeps all three tests green.

**D3(a)/D3(b).** Both tests are non-vacuous overall (mutation 1 turns all three red), and both were
red pre-fix as the report claims — verifiable by re-running the predicates against `b87e0751^`. The
defect is scope, not vacuity: neither test ever asserts that *all* derived regions are handled
correctly, only that the three known ones are and that no region carries one of two exact literal
signatures. A new phase boundary that copy-pastes the destructive instruction in slightly different
words (`restore it from HEAD with \`git checkout -- .plan/marshal.json\``, no "always safe") is
invisible to all three tests — contradicting the test docstring's own "so a new phase boundary that
adds such a block is covered automatically."

## Report accuracy

Checked and **confirmed** against the tree:

- PR #1186 → squash commit `b87e0751`; the landed diff is exactly the five paths the report implies.
- Population size 3, derived by shape — re-derived at HEAD, identical.
- Hit count "several dozen" — re-derived as 51 matching lines across 34 files.
- *"The word 'always' does not survive in any justification … `always safe` / `always a spurious` /
  `Recovery: git checkout --` all return zero matches across both workflow files"* — confirmed by
  `git grep`; the only surviving `always` occurrences in those files are unrelated dispatch prose.
- *"The full contract now exists once … the two planning-outline.md boundaries are references"* —
  confirmed by re-derivation (1 authority, 2 references).
- *"the drift corruption is gone"* — confirmed; the pre-fix `planning.md` did carry
  *"a spurious write that safe to revert"* and no copy of it survives.
- *"each seen red pre-fix"* — the *process* is not witnessable, but the substance is: re-running the
  predicates against `b87e0751^` gives `inspection_first == False` for all three regions and
  `authorities == 0`, and mutation 1 turns all three tests red today.
- *"No automated caller executes the recovery line"* — confirmed: `git grep "Recovery:" -- '*.py'`
  returns only the new test's docstring/regex and an unrelated `TestGateDecisionRecovery` class.
- Sibling plan 140 landed as PR #1171 → commit `fb41f014`. Confirmed.
- RED-evidence line numbers: `planning-outline.md:581` pre-fix / `:576` post-fix — confirmed exactly;
  the report already discloses this.

**Contradicted:**

1. *"Beyond-diff stale-claim sweep across the whole bundle and repo: **none survives** (the only
   residual quotes of the old wording are in plan.md and this report)."* — **False.**
   `test/plan-marshall/phase-2-refine/test_phase_2_refine_manage_config_readonly.py` quotes the
   removed recovery command four times (lines 216, 219, 224, 259) and states it as current contract:
   *"These tests pin both the mutation detection path and **the recovery path**"* (module docstring)
   and *"the post-refine orchestrator runs `git checkout -- .plan/marshal.json` to undo the change"*
   (line 219). The test is green today. See G1.
2. *"pins the collapse against future re-drift"* (D3 bullet 3, D2 section) — **overstated.** The
   uniqueness half holds only against a copy that reproduces the literal string
   `git diff -- .plan/marshal.json`; the "every other site references the authority" half passed
   against the pre-fix three-copy state and passes against a fresh restatement (mutation 2). See G2.
3. *"(sweep by heading across every workflow doc, so a future fourth boundary is covered
   automatically)"* — **overstated.** Covered automatically only for the two exact literal signatures
   the fix removed; a reworded destructive block at a fourth boundary is not detected. See G3.

**Not verifiable, not contradicted:** the `./pw verify plan-marshall` figures (`16157 passed,
1 skipped in 318.99s`), the two pre-PR sub-agent transcripts, the reviewer-participation table, and
the intermediate commit `6308698` (the branch was squash-merged and deleted; `git cat-file -t 6308698`
→ *not a valid object name* in this clone).

## Out-of-scope compliance

Clean. The landed diff touches only the declared surface: the two named workflow docs, the plan's own
directory, and `test/plan-marshall/plan-marshall/`. The phase Enforcement blocks were read, not
modified — `git show b87e0751 --name-status` shows no `phase-*/SKILL.md` path, and
`phase-2-refine/SKILL.md` § Enforcement at HEAD is unchanged relative to the pre-fix tree. No sibling
plan's surface (`git-workflow.py`, `scan_artifacts`) was touched. No undeclared collateral change.

One precision note rather than a scope breach: the new authority text asserts *"no planning phase
(2-refine, 3-outline, 4-plan) may mutate project configuration"* while citing only
`phase-2-refine § Enforcement → Prohibited actions`, whose `manage-config` bullet names refine alone.
The three-phase claim is nonetheless true — `phase-3-outline/SKILL.md:35` and
`phase-4-plan/SKILL.md:34` each forbid mutating anything outside `.plan/local/plans/{plan_id}/` — but
the cited evidence covers one third of the claim. The same sentence also compresses phase-2-refine's
*two* allowed write paths to one. See G4.

## Residue carried forward

| Report residue item | Status in today's tree |
|---|---|
| "Nothing left open in scope; all four deliverables complete and verified" | **Contradicted in part** — D0's `*.py` half and D2/D3's guard strength are open (G1–G3) |
| Merge landing delegated to the merge queue | **Closed** — `b87e0751` is an ancestor of HEAD |
| `/sync-plugin-cache` not owed | **Correct** — cloud-lane rule; nothing to check in the tree |
| Sibling sequencing: this plan and 140 must not run concurrently | **Moot** — 140 landed as `fb41f014` (#1171) and 210 as `b87e0751` (#1186); both are in history, sequenced |
| Corroboration of 140's build-gate wording proposal (no new proposal filed) | **Closed by a third change** — `7c965bab` "chore(cloud-plan-lane): match build-gate verification wording to the direct ./pw path (#1176)" landed |

## What could NOT be verified

- The `./pw verify plan-marshall` run and its `16157 passed, 1 skipped` figure — no build log is in
  the tree, and re-running the full scoped suite was out of proportion for this check.
- The two pre-PR verification sub-agent transcripts, including the isolated-recovery-text semantic
  check that the plan flags as "the check that matters most". Only its *artifact* (the wording) is in
  the tree; the wording does read as inspection-first, but the agent's answer is not reconstructible.
- The reviewer-participation table (`cuioss-review-bot`, `coderabbitai`, `sourcery-ai` verdicts, the
  one CodeRabbit thread, the 2-of-3 coverage disclosure) — GitHub state, not tree state.
- Intermediate branch commits (`6308698`) — absent from this clone after the squash merge.
