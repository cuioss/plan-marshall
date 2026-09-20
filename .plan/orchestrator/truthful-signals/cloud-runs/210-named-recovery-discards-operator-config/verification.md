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
  → empty. HEAD content is exactly what landed. (The **adjacent** file this check faults in G1,
  `test_phase_2_refine_manage_config_readonly.py`, *was* touched later — by `6514cf24`
  "chore(test-quality): give the architecture, orchestration and build slice its shared fixture
  surfaces (#1290)" — so G1's line numbers are read from HEAD, not from the landed diff.)
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
- **Synthetic fourth-site check (corrected during adversarial review):** the block was written into
  a fourth `.md` file inside the swept directory and the **real test file was run** against it, not
  merely evaluated by hand. Result depends on one detail the original bullet missed. Without any
  `planning.md` mention: **1 failed, 2 passed** —
  `test_named_recovery_contract_is_a_single_authority` names the block, because
  `_references_authority` is `False`. With the standard
  `` - `plan-marshall:plan-marshall/workflow/planning.md` § "Named recovery case — …" ``
  cross-reference bullet that both real reference sites already carry: **3 passed** — the reworded
  destructive site is invisible. The realistic shape escapes; the stripped one does not.
- Independent whole-tree sweeps (`git grep`) for: `always safe`, `always a spurious`,
  `checkout -- .plan/marshal.json`, `Recovery: git checkout`, `safe to (revert|delete|discard|…)`,
  `git restore|reset --hard|git clean|rm -rf|spurious write`, `Named recovery case`, `dirty_files`,
  `Recovery:` in `*.py`.
- `git status --porcelain` at finish shows nothing under
  `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/` or `test/plan-marshall/`.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: derive the "safe to delete/revert" population by assertion shape; report population size and hit count separately | population derived by shape, not command string; size and hit count reported separately | yes | yes | yes | **partial** | Re-derived at HEAD: 3 regions (`planning-outline.md:257`, `:576`, `planning.md:390`). Independent shape sweep over `marketplace/**`, `doc/**`, `*.py` found no fourth *doc* site; the only other `safe to delete/revert` hits are the counter-postures (`plugin-doctor/references/rule-catalog.md:230`, `shim-marker-convention.md:6`, `risky-fixes-guide.md:114`) and `doc/user/getting-started.adoc:94` (git-ignored `temp/`). Hit count re-derived over the union of report-01.md § D0's six stated pattern families: **68 matching lines in 45 files** excluding `doc/plans/` (134 / 62 including it) — the report's "several dozen" holds; the earlier `51 / 34` figure in this row did not reproduce and is withdrawn. **Two misses, not one:** on the `*.py` surface, `test/plan-marshall/phase-2-refine/test_phase_2_refine_manage_config_readonly.py` (G1); and on the `marketplace/**` doc surface, `workflow-integration-git/standards/worktree-handling.md:217-225` § "Recovery Loop", which routes a dirty tracked `.plan/marshal.json` to `git checkout --` as "the typical case" (**G5**). The D0 claim "no fourth site of this assertion shape exists" is false |
| D1 | Replace the false inference at every site; inspection first; the word "always" survives in no justification | every site instructs inspection first; "always" gone from justifications | yes | yes | yes | **partial** | `planning.md:390-397` is now premise → "It does **not** follow that the file is safe to discard" → `git diff -- .plan/marshal.json` → Keep/Discard disposition. `planning-outline.md:257`, `:576` carry the imperative "inspect the diff and obtain an explicit operator disposition before any discard — never revert `marshal.json` unconditionally". `git grep "always safe"` / `"always a spurious"` in both files → 0; the 5 remaining `always` occurrences are unrelated dispatch mechanics (`planning.md:109,266`, `planning-outline.md:98,132,470`). `git grep -c "Recovery: git checkout"` outside `doc/plans/` → 1 hit, and that is the **module docstring** at `test_named_recovery_marshal_config.py:10` (the regex at `:66` is `Recovery:\s*git checkout …`, which the literal grep does not match). Re-derived at HEAD: the 5 surviving `always` occurrences are `planning.md:109,266` and `planning-outline.md:98,132,470`, all dispatch mechanics. **Complete? is partial because D1's scope is "every site D0 finds" and D0's population was short by one doc site — `worktree-handling.md` § "Recovery Loop" still carries the un-replaced inference (G5)** |
| D2 | Collapse the triplet into ONE authority the sites reference | contract exists once | yes | yes | **guard is weak** | yes (for the state at HEAD) | Derivation at HEAD: exactly 1 region satisfies `_is_authority` (`planning.md:390`); the two outline sites are one-line imperatives + a cross-reference bullet to the authority. The drift corruption *"a spurious write that safe to revert"* is gone (`git grep "always a spurious"` outside `doc/plans/` → 0). **But** the test's `_references_authority` predicate is vacuous — see G2 |
| D3(a) | Recovery text does not instruct an unconditional discard; seen red pre-fix | holds, seen red | yes | yes | **narrow** | **no** | `test_named_recovery_never_instructs_unconditional_discard` passes at HEAD and goes red against pre-fix `planning.md` (mutation 1). Its offender predicate `_UNCONDITIONAL_DISCARD = r'Recovery:\s*git checkout -- \.plan/marshal\.json'` requires the literal `Recovery:` prefix, so a reworded destructive block escapes — see G3 |
| D3(b) | Population derivation asserted non-empty and contains the known members; seen red pre-fix | holds, seen red | yes | yes | yes | **no** | `test_named_recovery_inspection_first_population_nonempty_and_covers_known_members` passes at HEAD, red against pre-fix (`inspection_first` was `False` for all three pre-fix regions — re-derived directly). The non-vacuous control (`assert regions`) is real. But the test asserts only that the *known members* are inspection-first, never that *every* derived region is — see G3 |

**D0.** The derivation itself is sound and genuinely shape-keyed (it keys on the heading marker, not on
the command string that the fix removes — the right choice). The report's separation of population
size (3) from hit count is the right practice, and "several dozen" is supported (re-derived as 68 lines
across 45 files outside `doc/plans/`, over the union of the report's own six stated pattern families).
The counter-postures it names are real, at the exact lines cited
(`rule-catalog.md:230`, `shim-marker-convention.md:6`, `risky-fixes-guide.md:114`,
`doc/user/getting-started.adoc:94`): `execute-task/SKILL.md:160` does say `git checkout -- <files>` /
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
   the fix removed; a reworded destructive block at a fourth boundary that also carries the standard
   `planning.md` cross-reference bullet is not detected. See G3.
4. *"No fourth site of this assertion shape exists in the documentation or script surface"*
   (report-01.md § D0) — **False**, and this document's own earlier D0 row repeated it. A broader
   sweep than the "safe to …" phrasing — one keyed on the *recovery-instruction* shape
   (`revert (it|them|the file)`, `revert or relocate`, `checkout -- `) — surfaces
   `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/worktree-handling.md:223`:
   *"Revert — when the change was unintended (typical case): `git -C {main_checkout} checkout -- {path}`"*.
   The same document's § "Filter Rule" (`:231`) names `marshal.json` as a tracked `.plan/` path that
   is deliberately **retained** in `newly_dirty[]`, so this is the identical file reached by the
   identical command on the identical premise. See **G5**.

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
| "Nothing left open in scope; all four deliverables complete and verified" | **Contradicted in part** — D0's `*.py` half (G1), D0's `marketplace/**` doc half (G5), and D2/D3's guard strength (G2, G3) are open |
| Merge landing delegated to the merge queue | **Closed** — `b87e0751` is an ancestor of HEAD |
| `/sync-plugin-cache` not owed | **Correct** — cloud-lane rule; nothing to check in the tree |
| Sibling sequencing: this plan and 140 must not run concurrently | **Moot for sequencing** — 140 landed as `fb41f014` (#1171) and 210 as `b87e0751` (#1186); both are in history. But report-01.md's stronger claim that the two surfaces "do NOT share a code root" is wrong in its consequence: 140 changed `workflow-integration-git/SKILL.md` + `git-workflow.py` and 210 changed `skills/plan-marshall/workflow/*.md`; `workflow-integration-git/standards/worktree-handling.md` sits between the two sweeps and was fixed by neither (G5) |
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

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked** — every item below was re-derived from the tree, not read off this document:

- **Git facts.** `git cat-file -t b87e0751` → commit; `git show --name-status b87e0751` → the five paths
  claimed. `ac06e4fc` is an ancestor of HEAD (`f816f85c`) and every commit between them touches only
  `doc/plans/**`, so the subject surface is byte-identical at both. `git log b87e0751..HEAD` over the
  three changed subject paths → empty, as claimed. **Correction:** the same query over the *fourth*
  file this document faults (`test_phase_2_refine_manage_config_readonly.py`) is **not** empty —
  `6514cf24` (#1290) touched it after the merge. `6308698` is absent from the clone, as stated.
  Sibling landings `fb41f014` (#1171) and `7c965bab` (#1176) both confirmed by `git log --oneline -1`.
- **Every predicate in `test_named_recovery_marshal_config.py`, executed.** A standalone script
  replicating `_derive_named_recovery_regions` / `_has_unconditional_discard_directive` /
  `_has_always_safety_claim` / `_is_inspection_first` / `_is_authority` / `_references_authority` was
  **run** against (a) the pre-fix files extracted from `b87e0751^`, (b) HEAD, (c) three synthetic
  fourth-site variants. Pre-fix: all three regions `uncond=True always=True insp=False auth=False`, and
  `refs=True` for **both** `planning-outline.md` restatements — G2's central claim, confirmed by
  execution rather than by reading. HEAD: exactly 1 authority (`planning.md:390`), 2 references, all
  three inspection-first.
- **The test file, run.** `uv run python -m pytest …test_named_recovery_marshal_config.py
  …test_phase_2_refine_manage_config_readonly.py -o addopts="" -q` → **5 passed**.
- **Mutation 1 re-performed.** `git diff --quiet` on `planning.md` first (clean), bytes saved by copy,
  file overwritten with `b87e0751^` content → **3 failed**; restored from the saved copy, md5 identical
  (`27a55e48…`), `git diff --quiet` clean again. No `git checkout`/`restore`/`stash` used.
- **Two live injections** (a new untracked `.md` in the swept workflow directory, removed afterward;
  `git status --porcelain` on that directory clean after). (i) A full self-contained *restatement* at a
  non-authority site, using `git diff .plan/marshal.json` rather than the literal `git diff --` →
  **3 passed**. G2's drift claim confirmed by execution. (ii) The reworded destructive fourth site of
  G3 → **1 failed** without a `planning.md` mention, **3 passed** with the standard cross-reference
  bullet. G3's stated evaluation was wrong; its substance survives only in the second variant.
- **Broader independent sweeps than the ones this document ran**, keyed on the *recovery-instruction*
  shape rather than on the "safe to …" phrasing: `safe to (revert|delete|…|nuke|blow away|reset)`,
  `(safely|freely|always|harmlessly|simply) (delete|…|checkout)`,
  `spurious (write|edit|change)|no (phase )?work to lose|nothing (is|to) los|loses nothing|no data lost|without losing|no harm in|harmless to`,
  `restore .{0,30}from HEAD|revert (it|them|the (file|change|path))|discard (it|them|the file)|checkout -- `,
  `revert or relocate|either revert`. This is what produced **G5** — the site the narrower sweeps missed.
- **Cited symbols opened and read at their claimed lines:** `execute-task/SKILL.md:160` (verbatim match
  for "destructive of uncommitted working-tree content with no undo"); `phase-2-refine/SKILL.md:35`,
  `:36`, `:38-40`; `phase-3-outline/SKILL.md:35`; `phase-4-plan/SKILL.md:34`;
  `planning.md:390-412`; `planning-outline.md:257,260,576,579`;
  `test_phase_2_refine_manage_config_readonly.py:12-13,22-23,215-275` (275 lines total; the removed
  command at `:216,219,224,259`); `worktree-handling.md:212,217-231`.
- **`.plan/marshal.json` trackedness, the whole premise:** `git ls-files --error-unmatch` succeeds and
  `.gitignore:45-46` is `.plan/*` + `!.plan/marshal.json`. The file is tracked, so `git checkout --`
  on it is real and irrecoverable. Premise confirmed, not assumed.
- **Verdict rubric checked against the corpus**, not against intuition: every sibling `verification.md`
  in this epic reserves `partially-implemented` for a **dropped or unbuilt** deliverable
  (030, 060) and uses `implemented-with-gaps` when all deliverables landed but carry holes (040, 050,
  070, 080, 090, 110). Every deliverable here landed. Verdict upheld.

**Not re-checked** (unchanged from § "What could NOT be verified", and no new means to reach them):
the `./pw verify plan-marshall` figures; the two pre-PR sub-agent transcripts, including the isolated
recovery-text semantic check the plan flags as the check that matters most; the reviewer-participation
table and the 2-of-3 coverage disclosure; the intermediate commit `6308698`. Additionally **not**
re-run: the full scoped `plan-marshall` suite (only the two relevant test files were run), and the
`marketplace/targets/` generated exports of the changed docs.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| Verdict | `implemented-with-gaps` | **upheld** | All four deliverables landed and function at HEAD; the defects are completeness and guard strength. `partially-implemented` is reserved in this corpus for a dropped deliverable. G5 does not change this — D0 shipped, it was short |
| D0 row | Complete? **partial**, one `*.py` miss | **re-evidenced, still partial** | A second miss found on the `marketplace/**` doc surface (G5), and the row's `51 lines / 34 files` figure withdrawn — it does not reproduce from the report's own stated pattern union (68/45 excluding `doc/plans/`, 134/62 including) |
| D1 row | clean pass on all four axes | **re-severitied → Complete? partial** | The done-when is "every site D0 finds", and D0's population was short by one doc site whose inference is un-replaced (G5). The "always"-elimination half re-derived at HEAD and upheld exactly: 5 surviving occurrences, all dispatch mechanics |
| D2 row | collapse real at HEAD, guard weak | **upheld** | Re-derived: 1 authority, 2 references. Guard weakness confirmed by *execution*, not reading — a full restatement injected at a non-authority site passes 3 of 3 |
| D3(a)/D3(b) rows | non-vacuous but narrow | **upheld** | Mutation 1 turns all three red; pre-fix predicates give `insp=False` ×3 and `authorities=0`. The narrowness is real and now stated precisely (see G3) |
| G1 | stale `git checkout --` recovery pinned by a green phase-2-refine test | **upheld, line refs tightened, Done-when rewritten** | All four quotations verified verbatim at `:216,219,224,259`; module docstring at `:12-13` (not `:11-13`); the file is 275 lines. The original Done-when ("returns no line that presents the command as …") was not mechanically observable and was replaced with symbol-, string- and command-level conditions |
| G2 | `_references_authority` vacuous; guard misses re-drift | **upheld, line refs corrected** | Confirmed twice: predicate run against `b87e0751^` → `True` for both pre-fix restatements; full restatement injected live → 3 passed. `Where` corrected — `:113-116` is `_is_authority`, not `_references_authority` (`:118-120`, consumed at `:196`). Severity `high` correct: a guard that passes against the defect it names |
| G3 | reworded fourth site "invisible to all three tests" | **partly refuted, rewritten, re-severitied medium → high** | The block G3 quotes is **caught** (1 failed) — it contains no `planning.md` mention, so `_references_authority` is `False`. Only the variant carrying the standard cross-reference bullet escapes (3 passed). G3's Done-when as written was **already satisfied by the unmodified tree**; rewritten to name the cross-referencing variant. Raised to `high`: the guard passes against a *destructive* block and the test docstring ships a false coverage claim |
| G4 | premise citation under-covers its own claim | **upheld, `Where` tightened** | `planning.md:390` names three phases and cites only phase-2-refine; `:408-412` cross-references cite only phase-2-refine's two Enforcement sub-sections. `phase-3-outline/SKILL.md:35` and `phase-4-plan/SKILL.md:34` do carry the prohibition, so the claim is true but uncited. `phase-2-refine/SKILL.md:38-40` does list **two** allowed write paths. `low` is right — no behaviour turns on it |
| G5 | — | **added** | `worktree-handling.md:223` routes a dirty tracked `.plan/marshal.json` to `git checkout -- {path}` as "the typical case"; `:221` inspects paths, never the diff; `:231` names `marshal.json` as deliberately retained in `newly_dirty[]`. Loaded by `execute-task/SKILL.md:40` and `phase-5-execute/SKILL.md:55`, so agent-facing. `high` |
| "no fourth site exists" | report-01.md § D0, echoed in this document's D0 row | **refuted** | See G5. Added as § "Report accuracy" → Contradicted item 4 |
| "Recovery: git checkout outside `doc/plans/` → the regex literal in the new test" | D1 row | **corrected** | The single hit is the **module docstring** at `:10`; the regex at `:66` contains `\s*` and does not match the literal grep |
| "nothing later touched the changed files" | § Method | **upheld for the three subject paths, qualified** | Empty for `planning.md`, `planning-outline.md`, `test_named_recovery_marshal_config.py`; **not** empty for `test_phase_2_refine_manage_config_readonly.py` (`6514cf24`, #1290) |
| Out-of-scope compliance "clean" | § Out-of-scope compliance | **upheld** | `git show --name-status b87e0751` carries no `phase-*/SKILL.md` path, and the phase-2-refine § Enforcement block is byte-identical between `b87e0751^` and HEAD (`diff` of lines 25-45 → no output), despite five later commits touching that file elsewhere |

**Documents corrected.** *gaps.md:* open items 4 → 5; **G5 added** (the `worktree-handling.md` §
"Recovery Loop" site, `high`); G3 re-severitied `medium` → `high`, its evidence clause rewritten around
the two injection results, and its Done-when replaced because the old one already passed; G1's Where
narrowed to `:12-13` and its Done-when made mechanically observable; G2's Where corrected from
`:113-116`/`:189-196` to `:118-120`/`:196`; G4's Where extended to the `:408-412` cross-reference block;
a § "Refuted during adversarial review" section added recording the three refuted sub-claims.
*verification.md:* the § Method synthetic-fourth-site bullet rewritten around an executed run; the
later-touch bullet qualified for the phase-2-refine file; the D0 row's `51 / 34` figure withdrawn and
replaced with a figure that carries its pattern; the D0 row and § "Report accuracy" now record the
fourth site; D1's **Complete?** lowered to partial; the D1 row's "regex literal" attribution corrected;
Contradicted item 4 added; two § "Residue carried forward" rows re-stated. The verdict is unchanged.

**Residual doubt — what a third reviewer should look at first.** (1) **The sweep is still not closed.**
G5 was found by widening the pattern *once*. The same widening has not been tried on the `*.py` surface
beyond `Recovery:`/`checkout --` — a script that emits a revert suggestion in a message string would
match none of the patterns run here, and D0's HYPOTHESIS "no automated caller executes the recovery
line" was only ever confirmed against `git grep "Recovery:" -- '*.py'`. (2) **The check the plan called
the one that matters most remains unverifiable from the tree** — nobody after the original run has put
the new authority text, alone and context-free, in front of a fresh agent and asked what it would do.
That is cheap to redo and is the only direct evidence that D1's wording works on a reader.
(3) `worktree-handling.md` is a *standards* doc; the sweep for this class has never been run over
`**/standards/*.md` as a surface in its own right, and G5 suggests that is where the residue lives.
