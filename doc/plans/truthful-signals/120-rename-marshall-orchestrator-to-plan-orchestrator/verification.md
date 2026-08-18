# Verification — 120-rename-marshall-orchestrator-to-plan-orchestrator

**Verified against:** commit `ac06e4fc94782328f87d1395472a72b7e7a8559d`   **Landed as:** PR #1162, commit `6939a0c220b67f51e7bcf34eaa0a5b10d4e1ef04`   **Verdict:** fully-implemented

## Method

Read `plan.md` and `report-01.md` in full. Located the landed squash commit via
`git log --oneline --all --grep '#1162'` → `6939a0c2`; its parent (main at merge time) is
`68a21cac`. The branch's intermediate commits (`bd1f1cf`, `faaec17`) are **not** reachable
(`git cat-file -t` → "Not a valid object name"), so intermediate-state figures were re-derived at the
parent or at the merged commit instead.

What was actually done:

- **Diff shape.** `git show --stat -M 6939a0c2` (67 files) and `git show --name-status -M 6939a0c2`
  (30 rename records, similarity 81–100 %).
- **Pure-substitution proof.** Extracted the whole landed diff with `--unified=0`, excluding this
  plan's own two documents, then compared the removed and added line multisets after applying only
  the four rename substitutions (`persona-marshall-orchestrator`→`persona-plan-orchestrator`,
  `marshall-orchestrator`→`plan-orchestrator`, `_MARSHALL_ORCHESTRATOR_SKILL`→`_PLAN_ORCHESTRATOR_SKILL`,
  `Marshall Orchestrator`→`Plan Orchestrator`). Result: **242 removed / 242 added, 0 unmatched on
  either side.** The landed change is provably a pure token rename — no behavioural or collateral
  content edit is hiding in it.
- **Sweeps at HEAD.** `git grep -i 'marshall-orchestrator'`, `git grep -i -E 'marshall[-_ .]?orchestrator'`,
  `git grep -i 'marshallorchestrator'`, and a full token census
  (`git grep -io 'marshall[a-z-]*' | sort | uniq -c`) over `marketplace/`, `test/`, `doc/concepts`,
  `doc/user`, `doc/adr`, `.claude/`, `CLAUDE.md`.
- **Counts re-derived** at `68a21cac` and at `6939a0c2` with `git grep -o … | wc -l` (occurrences) and
  `git grep -l … | wc -l` (files), separately for occurrence-count and line-count.
- **Link resolution.** A Python pass over every tracked `.md`/`.adoc` outside `doc/plans/`, resolving
  every `](…)`, `link:…[`, `xref:…[` target whose path contains `orchestrator`: **71 links checked, 0
  broken.** (Corrected from a stated 72 during adversarial review; 71 is the figure the stated method
  reproduces, and it is stable under four methodology variants — with/without `image::` targets,
  with/without `doc/plans/`. Widening the filter to *resolved* paths containing `orchestrator` gives
  113 targets, also 0 broken.)
- **Tests executed.** `uv run python -m pytest test/plan-marshall/plan-orchestrator -o addopts="" -q`
  → **563 passed**. `… test/plan-marshall/manage-logging/test_logging_orchestrator_store.py
  test/plan-marshall/manage-config/test_orchestrator_scope.py` → **50 passed**.
- **Mutation check** (the one guard that actually enforces this rename in CI). Saved
  `marketplace/bundles/plan-marshall/README.md` bytes (md5 `70cc2d0e…`), rewrote its two
  `` `plan-orchestrator` `` tokens back to `` `marshall-orchestrator` ``, and ran
  `test/pm-plugin-development/plugin-doctor/test_analyze_readme_skill_coverage.py`. Baseline **6
  passed**; mutated → **1 failed** with
  `AssertionError: assert ('plan-orchestrator',) == ()` at
  `test_analyze_readme_skill_coverage.py:101`. Restored from the saved copy; md5 back to
  `70cc2d0e…`; `git status --porcelain` clean over `marketplace/ test/ doc/ CLAUDE.md .claude/`.
  (Other files appeared transiently modified in the shared working tree during the run; none were
  touched by this verification and all were gone by its end.)
- **Files opened:** both renamed `SKILL.md` frontmatters, `plugin.json`, bundle `README.md`,
  `doc/concepts/orchestration.adoc` / `README.adoc` / `personas.adoc` / `planning-workflow.adoc`,
  `doc/user/configuration.adoc`, `doc/adr/016…`, `_status_core.py`, `_cmd_orchestrator.py`,
  `_config_defaults.py`, `plan_logging.py`, `orchestrator.py`,
  `test_orchestrator_read_boundary_contract.py`, `_analyze_readme_skill_coverage.py`, `.gitignore`,
  `.plan/marshal.json`, `AGENTS.md`, the three `automatic-review/standards/*.md` registry docs.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: re-derive the surface at HEAD, classify rename-target vs must-not-touch | list exists with both classifications + stated population | yes | mostly — one stated count is off by one | yes | yes | `report-01.md:19-24`. Re-derived at `68a21cac`: **264 matching lines across 73 files** (report says 265/74). Classification and exclusion-set derivation reproduce exactly. |
| D1 | Rename the three directories | all three moved, history preserved | yes | yes | yes | yes | `git show --name-status -M 6939a0c2` → 30 `R0xx` records; `ls -d marketplace/bundles/plan-marshall/skills/*orchestrator*` → `plan-orchestrator`, `persona-plan-orchestrator`; `ls -d test/plan-marshall/*orchestrator*` → `plan-orchestrator`. No old directory remains. |
| D2 | Update every in-tree reference incl. 3-part notation | D0's rename-target list applied, must-not-touch untouched | yes | yes | yes | yes | Re-derived at parent: non-`doc/plans` = **269 occurrences / 64 files**, plus `doc/plans/README.md` = 1/1 → **270 occurrences / 65 files**, exactly the report's figure. New notation at `6939a0c2` excluding this plan's dir = 45 lines/15 files; including `plan.md` (2) = **47/16**, the report's figure. Old notation outside `doc/plans/` = 0. `_PLAN_ORCHESTRATOR_SKILL` at `test_orchestrator_read_boundary_contract.py:68,330,438` (3 uses, matching the report). |
| D3 | Cross-referencing skills + concept docs | all updated | yes | yes | yes | yes | `doc/concepts/orchestration.adoc:25,54,55,56`, `README.adoc:19`, `personas.adoc:147`, `planning-workflow.adoc:92`, `doc/user/configuration.adoc:59,65`, `doc/adr/016…:12`; `plugin.json:45,73`; bundle `README.md:32,33,51`. Link check: **71 orchestrator-bearing relative links, 0 broken** (figure corrected from 72 during adversarial review). Frontmatter `name:` matches each new directory (`plan-orchestrator/SKILL.md:2`, `persona-plan-orchestrator/SKILL.md:2`). |
| D4 | Regenerate the executor | executor resolves new notation | **yes — but not by this run** | yes — the run declared it owed rather than claiming it | yes | yes | Not tracked (`git ls-files '.plan/*'` lists only `marshal.json` + `project-architecture/**`; `.gitignore:45` `.plan/*` with two negations) — but the *untracked working-tree* copy exists and was **executed** during adversarial review: `python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator --help` → exit 0, prints the `orchestrator` verb router usage; the old notation `plan-marshall:marshall-orchestrator:orchestrator` → exit 1, `SCRIPT_ERROR … Unknown notation`. `grep -c 'marshall-orchestrator' .plan/execute-script.py` → 0. The done-when condition is **observably met on this machine**; the cloud run correctly declined to claim it. |
| D5 | Acceptance, each check verified, with a matched positive control | zero remaining strings in scope; plugin-doctor clean; suite green | yes | yes, with one disclosed literal shortfall | yes | yes in the run's declared scope | At HEAD: `git grep -i 'marshall-orchestrator'` outside `doc/plans/` → **0**; variant sweeps (`marshall[_ .]orchestrator`, `marshallorchestrator`, full `marshall[a-z-]*` census) → only the pre-existing false positive `plan-marshall orchestrator` (7 files). The plan's literal "zero under `doc/`" is **not** met — 11 files under `doc/plans/` still carry it (45 occurrences) — resolved in favour of D6 and disclosed in the report, not asserted away. |
| D6 | `.plan/` ledger explicitly NOT rewritten | stated as a non-goal and asserted | yes | partially — the stated rationale is slightly wrong | yes | yes | No `.plan/` path appears in `git show --stat 6939a0c2`. `git grep -i 'marshall-orchestrator' -- .plan/` → no match. Caveat: the report says `.plan/` "is git-ignored and absent"; in fact `.gitignore:45-47` negates `.plan/marshal.json` and `.plan/project-architecture/`, so 13 `.plan/` files **are** tracked and present. Neither contains the token (`.plan/marshal.json:182` holds only the `"orchestrator"` config-block key), so the outcome is right even though the reason given is not. |

### D0 — count off by one

`report-01.md:20` states "**265 matching lines across 74 files**". Re-derived with
`git grep -n 'marshall-orchestrator' <sha> -- .` at `68a21cac` (the merge parent) and at the two
preceding mainline commits `4faacf1b` and `b59f3b93`: **264 lines / 73 files**, stable across all
three. The figure is a lead the plan itself told the run not to scope on, and D2's derived scope
(65 files / 270 occurrences) reproduces to the digit, so the discrepancy has no consequence — but the
stated number is not reproducible.

### D4 — declared by the run, since satisfied, and now verified by execution

The executor generation target lives under git-ignored `.plan/`. The report correctly declares it as
owed local work rather than claiming completion — that disposition stands and is not a defect.

⭐ **Corrected during adversarial review.** The original text of this section said the outcome was
"outside this clone" and unverifiable. That was an over-claim: git-ignored is not the same as absent,
and the working tree this verification runs in **carries** a regenerated `.plan/execute-script.py`
(310 KB, untracked). Running it settles the done-when in both directions:

- `python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator --help` → **exit 0**,
  prints the `orchestrator` usage banner with the eight verbs (`scaffold`, `queue`, `resume-summary`,
  `archive`, `compact`, `corpus`, `cleanup`, `inbox`).
- `python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator --help` →
  **exit 1**, `SCRIPT_ERROR	plan-marshall:marshall-orchestrator:orchestrator	1	Unknown notation` — a
  matched negative control, so the exit-0 above is not a wildcard resolver accepting anything.
- `grep -c 'marshall-orchestrator' .plan/execute-script.py` → **0**; the only three-part orchestrator
  notation the generated file carries is `plan-marshall:plan-orchestrator:orchestrator`.

What this does **not** show: which local run performed the regeneration, or when. It shows only that
the deliverable's stated done-when holds today. The plugin-cache half of the same residue item remains
unverifiable here — `~/.claude/plugins/cache/plan-marshall/` does not exist in this container.

### D5 — the D5-vs-D6 tension

`plan.md` D5 asks for zero remaining strings under `marketplace/`, `doc/`, `test/`, `plugin.json`,
and the README. `doc/` is not clean: 11 tracked files under `doc/plans/` carry 45 occurrences at
HEAD. Every one is a record (landed reports) or another plan's spec — precisely the class D6 and the
"records are not source" out-of-scope clause protect. The report names this explicitly, quotes the
sub-agent's "one honest caveat", and refuses to assert literal D5 compliance. That is the correct
disposition of an internal conflict between two deliverables of the same plan, and it is not counted
as a gap.

### D6 — right outcome, wrong stated reason

The non-goal is honoured. The justification ("`.plan/` is git-ignored and absent") is inaccurate for
two negated subtrees. It happens not to matter here.

## Report accuracy

Re-derived at the moment of writing. Contradictions found:

1. **`report-01.md:20` — "265 matching lines across 74 files".** Re-derived: **264 / 73** at
   `68a21cac`, `4faacf1b`, and `b59f3b93` alike. Widened during adversarial review to the last **25**
   first-parent mainline commits ending at the merge parent: the figure is **264 / 73** for the four
   most recent and **259 / 69** for the twenty-one before them — **265 / 74 appears at no mainline
   commit in that window**, so a different branch base does not explain it. The report's own stated
   population (ripgrep over the working tree) was also reproduced directly, by extracting
   `git archive 68a21cac` to a scratch tree and running `rg` there: `rg --hidden` → **264 / 73**
   (identical to `git grep`), plain `rg` (no hidden files) → **261 / 71**. Neither is 265 / 74.
   ⚠ **Correction to this document's earlier wording:** it claimed "no untracked or hidden-path file
   accounts for it". The hidden-path half is checked and true (`.claude/**` is tracked and counted;
   `AGENTS.md` contains no occurrence of "orchestrat" at all). The *untracked* half is **not
   checkable** — an untracked file present in the cloud session's working tree at D0 time leaves no
   artifact in this clone, and remains the most plausible explanation for a +1 file / +1 line delta.
   The honest statement is that the figure does not reproduce and its residual cause is not
   recoverable, not that alternatives were excluded.
2. **`report-01.md:40` — "`.plan/` is git-ignored and absent".** `.gitignore:45-47` is
   `.plan/*` with `!.plan/marshal.json` and `!.plan/project-architecture/`; `git ls-files '.plan/*'`
   returns 13 tracked files, all present in this clone. The rename-relevant conclusion (nothing there
   needed changing) still holds — verified by `git grep -i 'marshall-orchestrator' -- .plan/` → no
   match — but the premise is wrong.
3. **`report-01.md:19` — "ripgrep, which honours `.gitignore`, so `.plan/` is excluded".** Found
   during adversarial review; the same false premise as (2), at a different line and with a different
   consequence — it describes the **D0 derivation population**, not the D6 rationale. ripgrep honours
   the `!` negations too, so `.plan/marshal.json` and `.plan/project-architecture/**` were in the
   swept population, not excluded from it. Outcome-neutral here (`git grep -i 'marshall-orchestrator'
   68a21cac -- .plan/` → 0 matches at the merge parent), but it means the report's stated derivation
   population is not the one it actually used — which is the sentence a reader would rely on to
   re-derive the unreproducible 265 / 74 in (1). Raised as G4.
4. **`report-01.md:25` — "git detected all renames at 81–99 % similarity".** The actual range is
   **81–100 %**: `git show --name-status -M 6939a0c2` yields one `R100` record alongside 29 in the
   081–099 band. Checked and recorded here; judged too trivial to file as a gap, since `R100` is the
   most faithful rename case and nothing reads the figure.

Checked and found **accurate**:

- D2's "65 files, 270 occurrences" — exact (269/64 outside `doc/plans` + 1/1 for
  `doc/plans/README.md`).
- D2's "47 occurrences / 16 files" for the new notation — exact for the pre-report state
  (45/15 at the merged commit excluding this plan's dir, +2/+1 for `plan.md`).
- D2's "`_MARSHALL_ORCHESTRATOR_SKILL` (3×)" — exactly 3 at `68a21cac`, exactly 3 renamed uses today.
- D0's "underscore form `marshall_orchestrator`: 0" — case-sensitively 0 at the parent; the 3
  case-insensitive hits are the uppercase constant the report reports separately.
- The subset-relation claim — `persona-marshall-orchestrator` does contain `marshall-orchestrator`;
  the 30 rename records show one substitution transformed both.
- "Third segment `orchestrator` unchanged" — every one of the 58 notation strings at HEAD ends
  `:orchestrator`; `ORCHESTRATOR_STORE = 'orchestrator'` at `_status_core.py:195` is untouched by the
  diff.
- The three renamed Python-file edits are comment/docstring/`argparse description=` only
  (`_cmd_orchestrator.py:23`, `_config_defaults.py:236`, `plan_logging.py:238`,
  `orchestrator.py` docstring + `description=`), consistent with "purely cosmetic".
- Exclusion set — `marshall-steward/`, `marshalld.py` + five `_marshalld_*.py`, `.plan/marshal.json`,
  and the `plan-marshall` bundle name all still exist under their own names; none appears in the
  landed diff.
- False-positive list — exactly 7 files carry `plan-marshall orchestrator`
  (`doc/concepts/token-management.adoc`, four `doc/resources/diagrams/*.svg`,
  `extension-api/standards/marshal-json-reference.md`, `manage-metrics/SKILL.md`), matching the
  report's enumeration.
- Scope-decision figure "29 occurrences across 8 tracked files" — reproduces exactly as
  13 occurrences over 7 other-plan files plus this plan's own `plan.md` (16), i.e. 29 over 8, at the
  pre-report state.
- Deferred finding #4's justification — `plugin.json` genuinely is not strictly alphabetical
  independently of this change: `ref-code-quality` does sit between `build-server-client` and
  `persona-auditor`, and 4 of today's 6 out-of-order adjacent pairs pre-date this plan.
- Reviewer population — exactly three `automatic-review/standards/{coderabbit,pr-agent,sourcery}.md`
  registry docs, with `author_login` values `coderabbitai`, `cuioss-review-bot`, `sourcery-ai`,
  matching the report's table.

Not re-derivable at HEAD (the tree has moved many commits since): "18957 passed / 14 skipped",
plugin-doctor "`total_issues: 0` (35 rules)", CI check conclusions, PR comment/thread counts, and the
token/wall-clock figures.

## Out-of-scope compliance

Clean, and provably so. The multiset comparison of the landed diff (242 removed vs 242 added lines,
0 unmatched either way after applying only the four rename substitutions) establishes that **no line
in the landed change differs from its counterpart by anything other than the rename token**. There is
no behaviour change, no drive-by fix, no reformatting, and no collateral edit.

The declared out-of-scope items were all respected:

- `marshall-steward`, `marshalld`, `marshal.json`, `plan-marshall` — untouched; each still exists
  under its own name.
- No behaviour change — confirmed by the multiset proof and by `ORCHESTRATOR_STORE` being unmodified.
- Orchestrator ledger historical references — no `.plan/` path in the diff.

One boundary the run declared for itself and kept: it also edited `CLAUDE.md`,
`.claude/skills/cloud-plan-lane/SKILL.md`, and `doc/plans/README.md`, each a live governance or
orientation document rather than a record, and each disclosed in D0's classification. Both governance
files now read `/plan-orchestrator` (`CLAUDE.md:68`, `cloud-plan-lane/SKILL.md:12`).

## Residue carried forward

| Residue item (from `report-01.md`) | Status in today's tree |
|---|---|
| Local executor regeneration + plugin-cache sync owed | **Split.** *Executor:* **discharged** — the untracked `.plan/execute-script.py` present in this working tree resolves `plan-marshall:plan-orchestrator:orchestrator` (exit 0) and rejects the old notation (exit 1, `Unknown notation`); both were run, not read. *Plugin cache:* still unverifiable — `~/.claude/plugins/cache/plan-marshall/` is absent from this container, and per `CLAUDE.md` § Standalone Plan Lane a cloud run never owed it. |
| Other-plan specs under `doc/plans/` still naming `marshall-orchestrator` | **Moot / settled.** All six have since run: `180`, `250`, `300` explicitly record re-grounding onto `plan-orchestrator` (`180/report-01.md:18,23`; `250/report-01.md:15,146`; `300/report-01.md:134`); `080` (PR #1196), `110` (PR #1169), `240` (PR #1188) all landed after #1162 without a recorded re-grounding note. The stale strings survive only as records. |
| `license/cla` pending on PR #1162 | Not observable from the tree; the PR is merged. |
| Deferred finding #4 — the two renamed `plugin.json` entries left in their old array positions | **Still open.** `plan-orchestrator` sits before `marshall-steward` and `persona-plan-orchestrator` before `persona-module-tester`; 2 of today's 6 out-of-order adjacent pairs are this plan's. Cosmetic, ungated. Raised as G1. |

## What could NOT be verified

- **D4, plugin-cache half only.** The executor half was settled by execution during adversarial
  review (see § "D4"); the plugin cache remains unverifiable — `~/.claude/plugins/cache/plan-marshall/`
  is absent from this container, and a cloud run never owed it. *Which* local run regenerated the
  executor, and when, is also not determinable.
- **Branch-intermediate figures.** `bd1f1cf` and `faaec17` do not exist in this clone (squash merge),
  so per-commit claims (which fix landed in which commit, the per-commit `./pw verify` gate) were
  checked only for internal consistency against the merged diff.
- **Build-gate and CI numbers.** "18957 passed / 14 skipped", plugin-doctor "35 rules /
  `total_issues: 0`", and the six named CI check conclusions are point-in-time run outputs. The tree
  has advanced ~35 PRs since; re-running `./pw verify` today would measure a different tree, not this
  claim. Not attempted.
- **PR-surface claims** — reviewer verdicts, the 1-of-3 coverage disclosure, comment/thread counts,
  and the auto-merge arming sequence. Only the *expected reviewer population* was verified (from the
  three registry docs); the observed behaviour was not, as ground truth here is the tree.
- **"No consumer outside this repository depends on the old skill name."** The plan itself labels
  this an unverifiable asserted absence, and it remains one.
- **Token and wall-clock cost figures.** Harness-reported; no in-tree artifact.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Every `gaps.md` row (all three; none was `high`, and all three are `low`), every deliverable
row marked a clean pass whose done-when is behavioural (D1, D2, D3, D5), the `fully-implemented`
verdict, the "swept the tree, clean" claim, the pure-substitution proof, and every count, line number,
symbol reference and commit SHA in the document. By these means:

- **Commit identity.** `git cat-file -t` on all five SHAs (`ac06e4fc`, `6939a0c2`, `68a21cac`,
  `4faacf1b`, `b59f3b93`) — all exist; `git rev-list --parents -n 1 6939a0c2` confirms `68a21cac` is
  the sole parent. This repository's HEAD has since advanced to `ac1618f3`.
- **Pure-substitution proof re-derived from scratch** with an independently written script over
  `git show --unified=0 -M 6939a0c2`, excluding this plan's directory and applying only the four named
  substitutions: **242 removed / 242 added, 0 unmatched either side.** Reproduces exactly. This is the
  load-bearing claim of the whole verification and it holds.
- **Sweeps re-run with broader patterns than the original.** A full token census
  `git grep -ioE '[a-z_.-]*marshall[a-z_.-]*'` over the entire tree outside `doc/plans/` (not just the
  seven paths the original named) — 150+ distinct tokens, **no `marshall-orchestrator` variant**. A
  **multiline** sweep the original did not run, `rg -U -i 'marshall[-_ .]*\n?\s*orchestrator'`, to
  catch a token wrapped across a line break in an 80-column `.adoc`: same 7 files, all
  `plan-marshall orchestrator` false positives, none wrapped. `git grep -inE 'marshall[-_ .]?orchestrator'`
  outside `doc/plans/` → **11 lines / 7 files**, matching the original's enumeration file-for-file.
- **Directory rename verified by a stronger method** than the original's `-M` display detection:
  `git log --follow` on `test/plan-marshall/plan-orchestrator/test_orchestrator.py` traverses the
  rename (`91a1c771` → `6939a0c2` → pre-rename `e82b466e`), and `git log --all -- .../marshall-orchestrator/SKILL.md`
  returns only the rename commit.
- **Tests re-executed**: `test/plan-marshall/plan-orchestrator` → **563 passed**; the two
  cross-referencing files → **50 passed** (613 total). Both figures reproduce.
- **Mutation re-applied.** `git diff --quiet -- marketplace/bundles/plan-marshall/README.md` → exit 0
  (no other agent mid-mutation); bytes saved to scratch (md5 `70cc2d0eb0671debb7ad08e192d36d35`,
  matching the stated `70cc2d0e…`); baseline **6 passed**; mutated the two backticked
  `` `plan-orchestrator` `` tokens back → **1 failed, 5 passed**, `AssertionError: assert
  ('plan-orchestrator',) == ()` at `test_analyze_readme_skill_coverage.py:101` — verbatim the stated
  failure; restored from the saved bytes, md5 identical, `git status --porcelain -- marketplace/` clean,
  test green again. Never `git checkout`/`restore`/`stash`.
- **Functions RUN, not read.** `.plan/execute-script.py` was executed on both notations (see § "D4").
- **Positive-control hygiene.** `marketplace/_positive_control_tmp.txt` is absent from the landed
  `--name-status`, from `git ls-files`, and from disk; `git log --all -S'_positive_control_tmp'` hits
  only `6939a0c2`, and only because `report-01.md` names the path in prose. No leak.
- **Link resolution re-derived** with an independently written resolver over all tracked `.md`/`.adoc`
  (3440 relative targets total), under four methodology variants.
- **Counts re-derived**: D0 (over 25 mainline commits plus a `git archive` + `rg` reproduction of the
  report's own stated population), D2 (270/65 and 47/16), the 58 three-part notation strings and their
  third segment, the 29/8 scope-decision figure, the 45-occurrence/11-file `doc/plans/` residual at
  `ac06e4fc`, the 13 tracked `.plan/` files, `.gitignore:45-47`, `_PLAN_ORCHESTRATOR_SKILL` at
  `:68,330,438`, `ORCHESTRATOR_STORE = 'orchestrator'` at `_status_core.py:195`, `plugin.json:45,73`,
  `CLAUDE.md:68`, `cloud-plan-lane/SKILL.md:12`, `.plan/marshal.json:182`, the exclusion set
  (`marshall-steward/`, `marshalld.py` + exactly five `_marshalld_*.py`, `marshal.json`,
  `plan-marshall`), the three reviewer registry docs and their `author_login` values, the residue
  table's six re-grounding citations (`180/report-01.md:18,23`; `250/report-01.md:15,146`;
  `300/report-01.md:134`) and the three PR numbers (#1196, #1169, #1188 — all after #1162).

**NOT re-checked.** The whole-tree `./pw verify` and `plugin-doctor` numbers (the tree has advanced
~35 PRs; re-running measures a different tree — the original's reasoning for skipping is accepted).
Every PR-surface claim (reviewer verdicts, comment/thread counts, auto-merge arming, `license/cla`),
the token and wall-clock figures, and the branch-intermediate commits `bd1f1cf`/`faaec17`, which do not
exist in this clone. The four pre-existing `plugin.json` inversions were confirmed to pre-date the plan
but not traced to their originating commits. The plugin-cache half of D4's residue is unverifiable
here. No source file was modified beyond the mutation described above, which was restored.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | `plugin.json` kept both renamed entries at their pre-rename positions; 76 entries, 6 out-of-order adjacent pairs, exactly 2 from this plan | **upheld, unchanged** | Parsed the JSON: 76 entries; adjacent-pair scan yields exactly the 6 stated pairs, and the 2 involving `plan-orchestrator`/`persona-plan-orchestrator` are at indices 40 and 12. The proposed insertion points (`persona-plan-marshall-agent`/`persona-security-expert` at 14/15; `plan-marshall-plugin`/`plan-retrospective` at 51/52) are correct, and applying the fix on paper leaves exactly 4 inversions — the stated Done-when re-derives. Severity `low` correct: ungated, cosmetic, no wrong behaviour. |
| G2 | `report-01.md:20`'s "265 / 74" does not reproduce; actual 264 / 73 | **upheld; Fix and Done-when rewritten** | 264 / 73 confirmed at the merge parent and, widened, across 25 first-parent mainline commits (264/73 or 259/69, never 265/74) and via `git archive` + `rg --hidden` reproduction of the report's own stated population. The *finding* is right. The original **Fix was not** — it prescribed stating `68a21cac` as "the base commit the figure was derived at", but the run derived from a working tree, not a commit, and `68a21cac` is the merge parent, which need not be the branch base. Prescribing it would manufacture provenance — the exact failure this epic exists to close. Rewritten to state the re-derived figure with its own population and to record the original as unrecoverable. |
| G3 | `report-01.md:40`'s "`.plan/` is git-ignored and absent" is false; 13 tracked files | **upheld; scope corrected, one rationale clause weakened** | `.gitignore:45-47` and `git ls-files '.plan/*'` → 13 files, both exact. But the "Why it matters" claimed the same premise sits in `CLAUDE.md` § Standalone Plan Lane; `CLAUDE.md:68` narrows it with its own colon-clause ("its state (plan directories, orchestrator ledgers, findings, locks, and the generated executor)"), all of which genuinely are absent from a clone. That clause is loose, not false. Corrected, and the fix re-scoped to the report line that *is* false. Severity `low` retained. |
| D4 row | "not performable in-tree", "not verifiable from the tree", residue "unverifiable" | **refuted (in part)** | `.plan/execute-script.py` is untracked but **present**, and was executed: new notation → exit 0 with the verb-router usage; old notation → exit 1, `Unknown notation`; `grep -c 'marshall-orchestrator'` → 0. The done-when holds today. "Git-ignored" was silently treated as "unobservable"; it is not. Row, subsection, residue table and "could NOT be verified" list all corrected. |
| "72 links checked, 0 broken" | 72 orchestrator-bearing relative links | **re-derived to 71; the 0-broken half upheld** | Independent resolver over 3440 relative targets in all tracked `.md`/`.adoc`: **71**, stable with/without `image::` and with/without `doc/plans/`; a wider filter (resolved path contains `orchestrator`) gives 113, also 0 broken. 72 reproduces under no variant. Corrected in place. |
| "242 removed / 242 added, 0 unmatched" | landed change is a pure token rename | **upheld** | Independently re-derived; exact. |
| D1 "history preserved" | 30 rename records | **upheld and strengthened** | 30 `R` records confirmed; similarity band is 81–**100** (one `R100`), not the report's 81–99. Additionally verified by `git log --follow` traversing the rename, which `-M` display detection alone does not establish. |
| D5 "swept, clean" | zero old-token occurrences outside `doc/plans/` | **upheld under broader sweeps** | Full `marshall*` token census, a multiline/line-wrapped variant, and the `[-_ .]?` variant all return zero real hits outside `doc/plans/`; the 7 `plan-marshall orchestrator` false-positive files reproduce exactly. |
| D2 / D3 figures | 270/65, 47/16, 58 notation strings, all doc line refs | **upheld** | Each re-derived; all exact. `doc/concepts/orchestration.adoc` carries the token on lines 11, 25, 46, 54, 55, 56, 59 — the cited `25,54,55,56` is a correct but partial sample, which the "Evidence" column does not claim to be exhaustive. |
| Verdict `fully-implemented` | — | **upheld** | The only row that was not a clean pass was D4, and that row now resolves in the plan's favour by execution. The three open gaps are `low` and none is a behavioural defect, consistent with how this corpus uses the verdict elsewhere. Had D4 stayed unresolved, `partially-implemented` would have been the defensible verdict. |

**Documents corrected.** In `verification.md`: the D4 deliverable row, the D4 subsection, the residue
table's first row and the "could NOT be verified" D4 bullet were rewritten from "unverifiable" to
"verified by execution, executor half"; the link figure 72 → 71 in two places; the "Report accuracy"
item 1 gained the widened derivation and lost its unsupported "no untracked file accounts for it"
exclusion; two new report-accuracy items were added (`report-01.md:19` population premise;
`report-01.md:25` similarity band). In `gaps.md`: **G4** added (`report-01.md:19`); **G2**'s Fix and
Done-when rewritten; **G3**'s "Why it matters" and Fix re-scoped; the preamble's link figure corrected
72 → 71 and its D4 sentence added; `**Open items:**` 3 → 4; a `## Refuted during adversarial review`
section added recording that no gap was refuted and what was refuted instead.

**Residual doubt — what a third reviewer should look at first.** (1) The 265 / 74 delta. Every
reconstructible population gives 264 / 73; the untracked-file hypothesis is unfalsifiable from this
clone, and if a third reviewer can recover the cloud session's working-tree state, that closes G2
properly rather than by restatement. (2) The `.plan/execute-script.py` I executed is *this container's*
file — a third reviewer on a different machine should re-run both notations there before treating D4
as globally discharged. (3) The plugin cache, which nothing in this session could observe. (4) The
"no external consumer" absence, still unverified and still unverifiable in principle from one clone.
