# Verification — 440-the-merge-currency-treadmill

**Verified against:** commit `af417166dd9f64704fe738720d716c38515061be`   **Landed as:** PR #1235, commit `ee78fd9183033e9da72334b95301d75c4795fa41` (squash)   **Verdict:** partially-implemented

> **Verdict corrected during adversarial review** (see § Adversarial review). D4 is recorded below as
> `Implemented? no` — an unimplemented deliverable, however well the report discloses it, makes the
> plan `partially-implemented` rather than `implemented-with-gaps`.

## Method

What was actually done, so an empty finding list is distinguishable from an unexamined one:

- Read `plan.md` and `report-01.md` in full (606 lines).
- Located the landing: `git log --oneline --all --grep '#1235'` → `ee78fd91`; `git show --stat` →
  20 files, +2833/−78. Read the full `phase-6-finalize/SKILL.md` hunk of that diff.
- Opened at HEAD: `phase-6-finalize/scripts/verdict_currency.py` (whole file),
  `phase-6-finalize/standards/verdict-currency.md` (whole file),
  `phase-6-finalize/SKILL.md` (§ "Special case — HEAD-dependent steps", the item-1 pseudocode,
  the item-5e SKIP obligation, § Scripts, § Canonical invocations, § Resumability),
  `phase-6-finalize/standards/branch-cleanup.md` (every `use_merge_queue` site),
  `phase-6-finalize/standards/pre-push-quality-gate.md` § "Verdict-input surface — deliberately
  undeclared", `extension-api/standards/ext-point-finalize-step.md` row `verdict_inputs`,
  `manage-execution-manifest/scripts/manage-execution-manifest.py` §§ `_refire_metric` /
  `summarize_refires` / `cmd_refire_report`, `manage-execution-manifest/SKILL.md` § refire-report,
  `.claude/skills/finalize-step-era-stamp-fill/SKILL.md` (frontmatter + § Verdict-input surface),
  `.claude/skills/finalize-step-era-stamp-fill/scripts/era_stamp_fill.py`,
  `.claude/skills/finalize-step-plugin-doctor/SKILL.md`, `doc/user/parallelism-and-locking.adoc`,
  `phase-5-execute/standards/sync-with-main.md`, `phase-2-refine/standards/refine-workflow-detail.md`,
  `automatic-review/SKILL.md`, `workflow-integration-git/scripts/git-workflow.py`
  (`cmd_worktree_rebase_to` docstring).
- **Tests run.**
  `uv run python -m pytest test/plan-marshall/phase-6-finalize/test_verdict_currency.py
  test/plan-marshall/manage-execution-manifest/test_refire_report.py -o addopts="" -q`
  → **59 passed in 1.12s**. Collection re-derived per file: 39 and 20 collected; `def test_`
  counts 35 and 16. All four figures match `report-01.md` exactly.
- **Functions executed, not read.** The classifier was driven through the real executor against the
  live discovery population and the live git history:
  - `verdict_currency classify --step project:finalize-step-era-stamp-fill --head-at-completion
    ee78fd91 --live-head af417166` → `verdict: invalidated`, `reason: verdict_inputs_matched`,
    `changed_paths[742]`, the three declared globs echoed.
  - Same verb with `--head-at-completion 85432346` → `verdict: preserved`,
    `reason: disjoint_from_verdict_inputs`, `changed_paths[4]` (all under `doc/plans/`).
    So both the `preserved` and the `invalidated` arms were reproduced live, not inferred.
  - `manage-execution-manifest refire-report --plan-id nonexistent-plan-xyz` →
    `status: error, error: file_not_found` (verb registered and reachable through the executor).
- **Mutations applied** (file byte-snapshotted to the scratchpad first; `git diff --quiet` returned
  0 before each mutation, and `RESTORED_CLEAN` was confirmed after each):
  1. `classify_advance`'s undeclared branch flipped `VERDICT_INVALIDATED → VERDICT_PRESERVED`
     (the plan's central fail-closed property). → **1 failed**,
     `test_empty_declaration_is_unknown_surface_not_empty_surface`. Guard is not vacuous.
  2. The equal-SHA short-circuit in `classify_step` moved **after** the declaration-resolution gate
     (the exact J1 regression the PR review caught). → **2 failed**,
     `test_equal_shas_preserve_even_when_resolution_is_impossible` and
     `test_equal_shas_preserve_for_an_unresolvable_step`. Both regression tests bite.
- **Counts re-derived at the moment of claim.** The head-dependent population was re-derived by
  reading `head_dependent: true` out of *frontmatter only* (an awk pass bounded by the `---` fence,
  so prose mentions in `manage-status`, `manage-metrics`, `extension-api` and `branch-cleanup.md`
  are excluded): exactly **11** declarers, orders 4, 5, 6, 7, 8, 9, 21, 22, 30, 40, 990. `verdict_inputs`
  declarers re-derived across `marketplace/` and `.claude/`: exactly **one**
  (`project:finalize-step-era-stamp-fill`, three globs, all three present on disk).
- **Ancestry claims re-derived first-party.** `git merge-base --is-ancestor 94bcddf HEAD` → yes
  (`94bcddf2`, #1189, 2026-08-12 19:23:10 UTC). `git merge-base --is-ancestor 1da26b1 HEAD` → yes
  (`1da26b13`, #1200, 2026-08-13 08:18:22 UTC).
- **Supersession checked** with `git log --oneline -- <path>` and `git log -S '<string>'` on
  `verdict_currency.py`, `verdict-currency.md`, `.claude/skills/finalize-step-era-stamp-fill/SKILL.md`,
  and the two `branch-cleanup.md` "unconditional rebase" sentences.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | Enumerate what re-stales and what each re-stale costs | trigger set enumerated with its population published | yes | yes | yes | yes | `phase-6-finalize/standards/verdict-currency.md:33-79` (trigger table derived from `mutates_source` / `advances_main_via_rebase` / loop-back; § "What a re-stale costs"). Population re-derived: 11 `head_dependent: true` frontmatter declarers |
| D1 | Distinguish an invalidating HEAD advance from a non-invalidating one | classification exists and is applied at the re-stale decision | yes | yes | yes | **partial** | `verdict_currency.py::classify_advance` / `classify_step`; new `verdict_inputs` fact at `ext-point-finalize-step.md:44`; wired at `phase-6-finalize/SKILL.md:554` and `:686-692`. Live run reproduced both `preserved` and `invalidated`. Two mutations went red. **But** § Resumability still states the pre-change unconditional re-fire at `SKILL.md:1755`, `:1760` and `:1768` (G2); no guard binds a literal declared glob to an existing path (G1); and the refusal-table guard `verdict-currency.md` relies on is a substring check that stays green when a cited refusal heading is renamed (G6) |
| D2 | Settle the unconditional pre-merge rebase | the verdict is recorded either way | yes | yes | yes | **near-complete** | Ruling at `verdict-currency.md:196-217`; mechanics at `branch-cleanup.md:358-371`; routed at 7 further sites (mutex acquire :101/:343, pre-rebase gate :278-298, CI gate :414-450, `[STATUS]` :480, merge consent :612-645) plus `sync-with-main.md:148`, `refine-workflow-detail.md:270`, `automatic-review/SKILL.md:39`, `doc/user/parallelism-and-locking.adoc:52,70`. Two "unconditional rebase" sentences at `branch-cleanup.md:1089,1094` are unrouted and stale (G3 — authored by #1241, which is an **ancestor** of `ee78fd91` and landed 41 minutes *before* it, so they are present in this plan's own merge commit and the D2 sweep missed them) |
| D3 | Make the re-fires visible | the re-fire count is obtainable | yes | yes | yes | yes | `manage-execution-manifest.py:2682-2845` (`summarize_refires`, `cmd_refire_report`); docs at `manage-execution-manifest/SKILL.md:296-330,519,600`. `git show ee78fd91` on that script shows **zero deleted lines** — purely additive, so no emitter was duplicated or altered. CLI reachable through the executor |
| D4 | Before/after measurement on a real finalize | both numbers published with their population | **no** | n/a — reported as not done | n/a | no | No measurement exists in the tree; `verdict-currency.md` and `verdict_currency.py` are untouched since `ee78fd91`, and nothing since references a taken measurement. The report declares it not performable in the cloud lane and names the owed procedure (G4) |

### D1 — the three incompletenesses

*(Originally written as two. A broader sweep during adversarial review found a third site inside the
same section, and a separate vacuous guard — G6 — below.)*

`marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:1754-1768` (§ Resumability,
"Special case — head-dependent steps") carries a **second** statement of the same decision, wrong in
three places rather than one. Its differing-SHA row at `:1760` still reads *"Re-fire (treat as no
record — HEAD has advanced past the validated SHA, e.g., after a loop-back commit)"* — the exact
text `:554` replaced. The section's lead sentence at `:1755` states the bare-SHA rule as the whole
rule (*"augmented with a worktree-HEAD comparison so a loop-back commit re-fires the gate instead of
skipping it on a stale `done`"*), and its closing summary at `:1768` repeats it (*"the HEAD-dependent
quality gate re-fires whenever the tree it validated has been superseded"*). The section's one
cross-reference defers only *membership* ("see § … for the single authoritative statement of
that membership and its governing discriminator"); the action is a live restatement at all three
sites. The landed diff never touched these lines (`git show ee78fd91 -- …SKILL.md` contains no hunk
at that offset). This is the same un-propagated-restatement class the run's own findings
F4/G3/G4/H1/I1 record five times over, surviving in the most-read file of the change.

`test/plan-marshall/phase-6-finalize/test_verdict_currency.py:492-504` guards that every declared
surface is non-empty, well-formed, rides a `head_dependent: true` step, and uses no `**`. Nothing
guards that a **wildcard-free** declared glob resolves to a path that exists. `era-stamp-fill`'s
three globs are all literal full paths. A rename of any of them makes the declaration match nothing,
and `classify_advance` then returns `preserved` for a commit that changed exactly that file — a
false-green skip of a gate that needed to run, which `ext-point-finalize-step.md:44` itself calls
"a correctness defect, not a cost one". This is not hypothetical: `test_audit.py` **was** renamed to
`test_audit_check_era_model.py` by #1266 (`983a6a2b`) after this plan merged. The declaration was
updated in that commit, but by the author's care, not by any gate — nothing in the tree would have
failed had it not been. Confirmed by mutation during adversarial review: rewriting the second
declared glob to a path that does not exist left `test_verdict_currency.py` + `test_era_stamp_fill.py`
at **55 passed**. (Bounded, and re-severitied to `medium` as a result: no glob is stale today, and
`test_era_stamp_fill.py:95-98` gives the two constant-mirrored paths an indirect existence net —
what is uncovered is the frontmatter declaration drifting from constants that are still correct.)

A third incompleteness, found only during adversarial review and filed as **G6**: the guard that
`verdict-currency.md:164-170` cites as the reason its illustrative refusal table is safe —
`test_every_tabled_refusal_carries_its_section` — tests `_REFUSAL_HEADING in body`, a bare substring
search over the step's whole doc. Both tabled steps carry that phrase twice (their own heading plus
a cross-reference to the other step's section), so renaming the cited heading leaves the guard green.
Demonstrated: renaming only `.claude/skills/finalize-step-plugin-doctor/SKILL.md:46` → **39 passed**;
renaming both occurrences → **1 failed**. That is a guard passing against the exact defect it names.

### D2 — where the sweep no longer holds

`branch-cleanup.md:1089` ("this barrier re-resolves HEAD after an unconditional rebase") and
`:1094` ("each pass re-runs the unconditional rebase, an authoritative CI wait, and trigger A")
are false on the `use_merge_queue == true` path, where no rebase runs and the CI wait is a
non-authoritative snapshot. `git log -S` attributes both sentences to `9e9e9880` (#1241).

**Corrected during adversarial review — the attribution was inverted.** `9e9e9880` is dated
2026-08-15 15:46:11 UTC and `ee78fd91` 2026-08-15 16:27:33 UTC; `git merge-base --is-ancestor
9e9e9880 ee78fd91` returns 0 and the reverse returns 1. #1241 landed **41 minutes before** this plan,
and `git show ee78fd91:…/branch-cleanup.md | grep -c "unconditional rebase"` returns **2**, so both
sentences are present in this plan's own merge commit. This is therefore an **incomplete D2 sweep by
this plan**, not later drift onto the surface it established. What the clone cannot settle: PR #1235
squash-merged, so whether the run's tree carried these lines while its sweeps ran, or whether the
pre-merge rebase pulled them in afterwards, is not reconstructible. Either way it is open in today's
tree. The gap is re-severitied to `low` (see G3): on the queue path HEAD does not advance between
passes, so the grant the WARNING directs is correct against the current HEAD regardless — the defect
is a false premise, not misdirection into a wrong action.

### D4 — genuinely unmet

The plan's own Verification section required D4 to publish a denominator, and the report publishes
none because no measurement was taken. The report states this plainly rather than narrating a
completion, and names the exact procedure and instrument. The deliverable is nonetheless unmet.

## Report accuracy

Re-derived every figure `report-01.md` states that the tree can adjudicate. **One contradiction
found**; everything else confirmed.

**Contradicted — the "three earliest" claim (D0 section, and repeated in the merged PR body).**
The report writes: *"The three steps the plan names — housekeeping, structural lint, self-review —
are the three EARLIEST head-dependent steps in the pipeline (`order` 4, 6, 7)."* Re-derived from
frontmatter at HEAD, the head-dependent orders are 4, 5, 6, 7, 8, 9, 21, 22, 30, 40, 990.
`default:pre-push-quality-gate` is `order: 5`
(`phase-6-finalize/standards/pre-push-quality-gate.md`), sitting between housekeeping (4) and
plugin-doctor (6). The three earliest are **4, 5, 6**, not 4, 6, 7. The claim that follows it —
"the re-fire distribution is a function of position, and the plan's reported counts are consistent
with that ordering" — is therefore not established by the ordering it cites; the cited counts
(5× at order 4, 7× at orders 6 and 7) are in any case *increasing* with order, which the positional
argument predicts should decrease.

Confirmed, each re-derived at the moment of the claim:

- **Test counts.** 35 test functions / 39 collected in `test_verdict_currency.py`; 16 / 20 in
  `test_refire_report.py`; **59** collected across both. All four exact.
- **Head-dependent population.** Eleven members with the orders 4, 5, 6, 7, 8, 9, 21, 22, 30, 40, 990 —
  exactly the list the report gives, step for step.
- **Exactly one declarer, three globs, all present on disk.** Re-derived; the third glob
  (`era_stamp_fill.py`) is present and its `AUDIT_REL` / `TEST_REL` constants match the other two
  declared paths, so the "superset by construction" argument holds against the executor's own source.
- **Claim 1 (delta-scoping is an ancestor).** `94bcddf2` is an ancestor of HEAD, landed
  2026-08-12 19:23:10 UTC, and its subject is #1189 "self-review surfacing integrity" as stated.
- **Sibling instrumentation landed.** `1da26b13` (#1200) is an ancestor, 2026-08-13 08:18:22 UTC.
- **Claim 4 (rebase noop).** `git-workflow.py::cmd_worktree_rebase_to`'s docstring documents exactly
  the `pre_sha`/`post_sha` comparison and the `clean`-state early return with `action: 'noop'` the
  report cites, so the "partially refuted" verdict is sound.
- **D3 consumes rather than duplicates.** `git show ee78fd91` on
  `manage-execution-manifest.py` has **zero** removed lines; `record-step` is untouched.
- **The `refires` mis-attribution correction reached all named sites.** Present in
  `verdict-currency.md`, in `manage-execution-manifest/SKILL.md:313`, and in the
  `summarize_refires` docstring.
- **The `preserved`-on-two-paths correction reached all named sites.** `verdict_currency.py`
  docstring, `classify_step` docstring, `verdict-currency.md` § "Fail-closed, structurally",
  `phase-6-finalize/SKILL.md:571`. No surviving "exactly one path" phrasing was found.
- **#1237.** `cf0ba051` landed: one file, `.claude/skills/cloud-plan-lane/SKILL.md`, +37/−0,
  and the "A fix is a change" paragraph is present at line 600.
- **The worked TOON example** in `manage-execution-manifest/SKILL.md:320-330` is internally
  consistent (7+1 firings, 6 refires, 3 skips, `execution_log_rows: 11`).

## Out-of-scope compliance

The run stayed inside its boundaries.

- **"NOT the step/dispatch emitters."** Honoured, and provably: the only change to
  `manage-execution-manifest.py` is a purely additive read-only verb (no deletions in the diff), and
  no `[STEP]`/`[DISPATCH]` emission site was edited.
- **"No further delta-scoping of individual gates."** No `--since-ref`-style scoping was added
  anywhere in the diff.
- **"Never change what a gate verifies."** The D2 collateral (the trigger-A re-review now firing only
  on an actually-advanced HEAD) narrows *when* the re-review runs, never *what* it checks, and the
  report discloses it explicitly.
- **Surface divergence, minor and undisclosed.** The plan's Expected surface named
  `skills/workflow-integration-git/**` as D2's site. The landed diff does not touch that bundle at
  all; D2 was implemented at the *call site* (`branch-cleanup.md`) instead, leaving
  `cmd_worktree_rebase_to` unconditional-by-contract. That is the better placement, but the report
  does not note that it diverged from the plan's stated surface.
- **Collateral outside the expected surface**, all consequential and each disclosed in the report:
  `doc/user/parallelism-and-locking.adoc`, `phase-2-refine/standards/refine-workflow-detail.md`,
  `phase-5-execute/standards/sync-with-main.md`, `automatic-review/SKILL.md`,
  `.claude/skills/finalize-step-era-stamp-fill/SKILL.md`,
  `.claude/skills/finalize-step-plugin-doctor/SKILL.md`. Nothing undeclared was found.

## Residue carried forward

| Report-declared residue | Still open at HEAD? |
|---|---|
| D4's measurement is owed | **Open.** No measurement exists; `verdict-currency.md` and `verdict_currency.py` have had no commit since `ee78fd91` |
| Ten of eleven head-dependent steps declare no surface | **Open, unchanged.** Re-derived: still exactly one declarer. Three (`ci-verify`, `automatic-review`, `sonar-roundtrip`) are correct remote-state abstentions; two are recorded refusals whose sections are present and guard-pinned; five (`lessons-housekeeping`, `pre-submission-self-review`, `finalize-step-simplify`, `finalize-step-security-audit`, `review-retrospective`) remain undeclared candidates |
| Decomposing `pre-push-quality-gate` is the unblocking condition for its declaration | **Open.** Recorded verbatim at `pre-push-quality-gate.md` § "The unblocking condition, for whoever revisits this" |
| The surface vocabulary is static globs, excluding the link-target case | **Open.** `ext-point-finalize-step.md:44` still specifies fnmatch globs only; no derived-surface vocabulary exists |
| #1237's contract change | **Closed.** Landed as `cf0ba051` |

## What could NOT be verified

- **The observed 5× / 7× / 7× re-fire counts and the 109M / 134.4M billing figures.** They live in
  run reports under git-ignored `.plan/`. The report itself declines to re-derive them and pins no
  target to them; this verification likewise cannot confirm or refute them. Note that the report's
  *positional explanation* for them is separately contradicted (see § Report accuracy).
- **PR-side facts.** That the five CodeRabbit findings were dispositioned in a single PR comment,
  that `sourcery-ai` refused on diff size, that `cuioss-review-bot` was silent, that
  `verify / conclusion` failed on `9a3af44` through Actions concurrency cancellation, and that the
  PR body was rewritten (K2) are all GitHub-side; no network calls were made from this session.
- **The 17-commit count and the per-commit `./pw` gates.** The PR squash-merged, so the branch's
  individual commits are not in this clone's history.
- **The `./pw verify` results the report quotes** (19612 → 19721 passed, 403 production /
  744 test files, `plugin-doctor total_issues: 0`). Only the two plan-authored test files were run
  here; the whole-tree gate was not re-run.
- **That a preserved SKIP actually lands its item-5e `record-step` row at runtime.** The obligation
  is stated in prose at `phase-6-finalize/SKILL.md:726-735`; there is no plan state or live finalize
  in this clone to observe it discharged. The `skipped` outcome is at least a valid
  `VALID_RECORD_OUTCOMES` member (`_manifest_core.py:248`), so the instruction is executable.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document. Review performed at
`d958307c17f8402c5c194cea8d11481279632479` (the original verification was written against
`af417166`, which is an ancestor of that HEAD; nothing on the plan's surface changed between them).

**Checked.** Every gap G1–G5 and every deliverable row, plus every count and ancestry claim the
clone can adjudicate:

- **Populations re-derived independently**, not by reading this document. An own frontmatter scan
  over `marketplace/**` and `.claude/**` bounded by the `---` fence: **11** `head_dependent: true`
  declarers at orders 4, 5, 6, 7, 8, 9, 21, 22, 30, 40, 990; exactly **one** `verdict_inputs`
  declarer with **three** globs, all three present on disk. Also derived, and not in the original:
  the full 26-step finalize roster with each step's `mutates_source` / `head_dependent` facts, used
  to confirm the D0 trigger table's rows are non-vacuous — `advances_main_via_rebase: true` has two
  real declarers (`finalize-step-sync-baseline` order 3, `branch-cleanup` order 70), and the
  `mutates_source` bands `< 11` and `> 11` each have members.
- **Test figures re-derived.** 35 and 16 `def test_` functions; 39 and 20 collected; **59 passed**
  across both files. All four exact.
- **Functions executed, not read.** The classifier was driven live through the executor on both
  arms: `--head-at-completion ee78fd91 --live-head af417166` → `invalidated` /
  `verdict_inputs_matched` / `changed_paths[742]`; `--head-at-completion 85432346` → `preserved` /
  `disjoint_from_verdict_inputs` / `changed_paths[4]`, all four under `doc/plans/`. Both reproduce
  the original exactly. `summarize_refires` was executed on a synthetic `execution_log[]` through a
  throwaway test module (removed afterwards; `git status` clean): `refires = max(0, firings-1)`
  holds, `skipped` and `error` rows are excluded from `firings`, `--phase` filters, a non-dict row
  and a row with no `step_id` are skipped, and a non-numeric metric coerces to 0 rather than raising.
- **Four mutations applied** (each file byte-snapshotted to `$TMPDIR` first, `git diff --quiet`
  returning 0 before, and both `RESTORED_CLEAN` and byte-identical `diff` confirmed after):
  1. `classify_advance`'s undeclared branch `INVALIDATED → PRESERVED` → **1 failed**,
     `test_empty_declaration_is_unknown_surface_not_empty_surface`. Upholds the original.
  2. The J1 regression re-staged (equal-SHA short-circuit made conditional on the resolution gate
     succeeding) → **2 failed**, both named regression tests. Upholds the original.
  3. A declared `verdict_inputs` glob rewritten to a nonexistent path → **55 passed**. Upholds G1's
     exposure, empirically rather than by reading.
  4. `.claude/skills/finalize-step-plugin-doctor/SKILL.md`'s refusal heading renamed → **39 passed**;
     renamed at *both* occurrences → **1 failed**. This is new — it is G6.
- **Sweeps re-run with broader patterns than the originals.** `exactly one path|a single path|on
  exactly one|one path only` across `marketplace/`, `.claude/` and `test/` — no surviving stale
  phrasing, upholding the original's narrower sweep. `pre-merge rebase|pre_merge_rebase` across
  `marketplace/`, `.claude/`, `doc/user/` and `doc/developer/` — every site routed by
  `use_merge_queue` except `branch-cleanup.md:1089,1094`. `differs from live HEAD|!= live
  HEAD|unconditional re-fire|re-fires on every|always re-fire|augmented with a worktree-HEAD
  comparison|re-fires whenever the tree it validated has been superseded` across the same trees —
  this is what turned up the two extra § Resumability sites now folded into G2.
- **Ancestry re-derived first-party.** `94bcddf2` (#1189, 2026-08-12 19:23:10 UTC) and `1da26b13`
  (#1200, 2026-08-13 08:18:22 UTC) are both ancestors of HEAD, as claimed. `9e9e9880` (#1241) is an
  ancestor of `ee78fd91` and predates it by 41 minutes — the reverse of what was claimed.
- **Other figures re-derived:** `git show ee78fd91 --numstat` on `manage-execution-manifest.py` =
  `179 0` (purely additive, so "consumes rather than duplicates" holds); `cf0ba051` = one file,
  `+37/−0`, "A fix is a change" present at `cloud-plan-lane/SKILL.md:600`; the worked TOON example
  (7+1 firings, 6 refires, 3 skips, `execution_log_rows: 11`) is internally consistent;
  `ext-point-finalize-step.md:44` is the `verdict_inputs` row and carries the quoted "a correctness
  defect, not a cost one" verbatim; `default:pre-push-quality-gate` is on the § "Inline steps" roster
  at `dispatch-inline-split.md:41`, so G4's zero-token floor is real.

**Not re-checked.** Everything in § "What could NOT be verified" remains unverified for the same
reasons, and this review added no network calls, so all PR-side facts stay unchecked. Beyond those:
the whole-tree `./pw verify` was not re-run (only the two plan-authored test files, plus
`test_era_stamp_fill.py`); the D2 routing was confirmed by reading `use_merge_queue` at every site in
`branch-cleanup.md` but no merge path was executed; `SKILL.md:1230`'s "RE-FIRE the step on every
resume" was assessed as *currently* true (every `mutates_source: true` + `head_dependent: true` step
either declares no surface or declares one its own commit touches) but not filed, and a future
declarer could falsify it; and the `_tabled_refusals()` regex's whole-document scope — it would bind
any future table row whose first cell is a backticked step id — was noticed but not filed, since no
such table exists today.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| **Headline verdict** | `implemented-with-gaps` | **corrected** | D4's own row reads `Implemented? no`. An unimplemented deliverable makes the plan `partially-implemented`; the disclosure quality of the report does not change the count |
| G1 | Nothing pins that a wildcard-free declared glob names an existing path — `high` | **upheld, re-severitied to `medium`** | Grepping the whole test file for `exists`/`is_file`/`is_dir` returns only unrelated `Path(...)` uses. Mutation 3 above proves the exposure. Downgraded because no glob is stale today and `test_era_stamp_fill.py:95-98` nets the two constant-mirrored paths; the uncovered case is declaration-vs-constant drift |
| G2 | § Resumability at `:1760` still prescribes the unconditional re-fire — `medium` | **upheld and widened** | `:1760` confirmed verbatim. A broader sweep found `:1755` and `:1768` restating the same superseded rule in the same section — the original Done-when grep (`"differs from live HEAD"`) matches neither. Fix and Done-when rewritten to cover all three |
| G3 | Two stale "unconditional rebase" sentences, drift by #1241 *after* this plan — `medium` | **upheld as a defect, rationale refuted, re-severitied to `low`** | Both sentences confirmed at `:1089`/`:1094` and confirmed false on the `use_merge_queue == true` path (`:367`, `:423`). But `9e9e9880` is an **ancestor** of `ee78fd91`, 41 minutes earlier, and `git show ee78fd91:…` finds both sentences — so this is plan 440's own incomplete sweep, not later drift. Kind changed to `incomplete-sweep`. Downgraded because the operator's correct action is unchanged on the queue path |
| G4 | D4's measurement is owed — `medium` | **upheld, fix corrected** | Confirmed no measurement exists. The stated *before* arm (`origin/main`) already contains `ee78fd91`, so as written it would produce two identical arms; corrected to `87c71d3f` (`ee78fd91^`) |
| G5 | The report's "three earliest head-dependent steps (4, 6, 7)" is false — `low` | **upheld** | Independently re-derived: the three earliest are 4, 5, 6. `default:pre-push-quality-gate` is `order: 5`, and `report-01.md:44-49` lists it two lines above the claim. `low` is right — a record-accuracy defect with no behavioural consequence |
| D0 | Clean pass | **upheld** | The trigger table's rows are each backed by a real declarer; `advances_main_via_rebase: true` has two, and both `mutates_source` order bands have members. Not vacuous |
| D3 | Clean pass | **upheld** | `summarize_refires` executed, not read. The plan's claim-5 refutation also holds: the item-2 `[STEP] Executing step:` emit at `SKILL.md:754` is unconditional per firing, and item 5e's `record-step` row is mandated on the SKIP branch too (`:726-735`) |
| — | (nothing filed) | **new gap G6, `high`** | `test_every_tabled_refusal_carries_its_section` is a whole-file substring check. Both tabled steps carry the phrase twice, so renaming the cited heading leaves it green — 39 passed. The guard `verdict-currency.md:164-170` names as its safety net does not hold |
| — | (cross-references) | **corrected** | This document cited G1↔G2 swapped, G3 as "G4", and G4 as "G5". All four now match `gaps.md` |

**Documents corrected.**
*verification.md*: verdict changed to `partially-implemented` with the reason stated inline; the four
wrong gap cross-references fixed; the D1 sub-section retitled "the three incompletenesses" and
extended with the `:1755`/`:1768` sites and with G6; the D2 sub-section's "landed after" attribution
replaced with the re-derived ancestry and its consequence (an incomplete sweep by this plan); this
section appended.
*gaps.md*: open-item count 5 → 6; G1 re-severitied `high` → `medium` with the mutation evidence and
the `test_era_stamp_fill.py` net that bounds it; G2 widened to three sites with a rewritten Fix and a
Done-when whose grep can actually observe them; G3 re-severitied `medium` → `low`, kind changed to
`incomplete-sweep`, and its attribution corrected; G4's Fix corrected to name a *before* arm that
does not already contain the change; G5 unchanged; G6 added. No gap was refuted outright, so the
`## Refuted during adversarial review` section is absent — one rationale (G3's) was refuted while its
underlying defect stood, and that is recorded in G3 itself rather than by moving the gap.

**Residual doubt — what a third reviewer should look at first.**
1. **The other nine `head_dependent` steps that declare no surface.** The change reaches exactly one
   of eleven. Whether a one-step reach moves the re-fire count at all is unmeasured (G4), and the
   two recorded refusals are now known to be pinned by a guard that does not bite (G6) — so the
   claim "five remain undeclared *candidates*" rests on nothing a gate enforces.
2. **`SKILL.md:1230`'s re-stamp instruction.** It asserts an unconditional re-fire on every resume
   for a `mutates_source` + `head_dependent` step. That is true of every current member but is
   stated as a property of the class, and the classifier now governs the decision. A fourth
   restatement site, if a step ever declares a surface its own commit misses.
3. **Whether the pre-merge rebase brought `branch-cleanup.md:1089,1094` into the branch after the
   sweeps ran.** The squash-merge hides it. If it did, the finding is an instance of the run's own
   K2/#1237 lesson — a fix's own surface changing under it — rather than an ordinary missed sweep,
   and the remedy belongs in the contract rather than in the document.
