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
  every `](…)`, `link:…[`, `xref:…[` target whose path contains `orchestrator`: **72 links checked, 0
  broken.**
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
| D3 | Cross-referencing skills + concept docs | all updated | yes | yes | yes | yes | `doc/concepts/orchestration.adoc:25,54,55,56`, `README.adoc:19`, `personas.adoc:147`, `planning-workflow.adoc:92`, `doc/user/configuration.adoc:59,65`, `doc/adr/016…:12`; `plugin.json:45,73`; bundle `README.md:32,33,51`. Link check: **72 orchestrator-bearing relative links, 0 broken.** Frontmatter `name:` matches each new directory (`plan-orchestrator/SKILL.md:2`, `persona-plan-orchestrator/SKILL.md:2`). |
| D4 | Regenerate the executor | executor resolves new notation | **not performable in-tree** | yes — declared, not claimed | n/a | n/a | `.plan/execute-script.py` is not tracked (`git ls-files '.plan/*'` lists only `marshal.json` + `project-architecture/**`; `.gitignore:45` `.plan/*` with two negations). The report records it as residue rather than asserting it done. Correctly handled; **not verifiable from the tree.** |
| D5 | Acceptance, each check verified, with a matched positive control | zero remaining strings in scope; plugin-doctor clean; suite green | yes | yes, with one disclosed literal shortfall | yes | yes in the run's declared scope | At HEAD: `git grep -i 'marshall-orchestrator'` outside `doc/plans/` → **0**; variant sweeps (`marshall[_ .]orchestrator`, `marshallorchestrator`, full `marshall[a-z-]*` census) → only the pre-existing false positive `plan-marshall orchestrator` (7 files). The plan's literal "zero under `doc/`" is **not** met — 11 files under `doc/plans/` still carry it (45 occurrences) — resolved in favour of D6 and disclosed in the report, not asserted away. |
| D6 | `.plan/` ledger explicitly NOT rewritten | stated as a non-goal and asserted | yes | partially — the stated rationale is slightly wrong | yes | yes | No `.plan/` path appears in `git show --stat 6939a0c2`. `git grep -i 'marshall-orchestrator' -- .plan/` → no match. Caveat: the report says `.plan/` "is git-ignored and absent"; in fact `.gitignore:45-47` negates `.plan/marshal.json` and `.plan/project-architecture/`, so 13 `.plan/` files **are** tracked and present. Neither contains the token (`.plan/marshal.json:182` holds only the `"orchestrator"` config-block key), so the outcome is right even though the reason given is not. |

### D0 — count off by one

`report-01.md:20` states "**265 matching lines across 74 files**". Re-derived with
`git grep -n 'marshall-orchestrator' <sha> -- .` at `68a21cac` (the merge parent) and at the two
preceding mainline commits `4faacf1b` and `b59f3b93`: **264 lines / 73 files**, stable across all
three. The figure is a lead the plan itself told the run not to scope on, and D2's derived scope
(65 files / 270 occurrences) reproduces to the digit, so the discrepancy has no consequence — but the
stated number is not reproducible.

### D4 — declared, not done

The executor generation target lives under git-ignored `.plan/`. The report declares it as owed local
work rather than claiming completion. Whether a local machine has since regenerated it is outside
this clone. Listed under "What could NOT be verified".

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
   `68a21cac`, `4faacf1b`, and `b59f3b93` alike. Off by one in both figures, unexplained; no
   untracked or hidden-path file accounts for it (`.claude/**` and `AGENTS.md` were checked —
   `AGENTS.md` contains no occurrence of "orchestrat" at all).
2. **`report-01.md:40` — "`.plan/` is git-ignored and absent".** `.gitignore:45-47` is
   `.plan/*` with `!.plan/marshal.json` and `!.plan/project-architecture/`; `git ls-files '.plan/*'`
   returns 13 tracked files, all present in this clone. The rename-relevant conclusion (nothing there
   needed changing) still holds — verified by `git grep -i 'marshall-orchestrator' -- .plan/` → no
   match — but the premise is wrong.

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
| Local executor regeneration + plugin-cache sync owed | **Unverifiable from the tree** — `.plan/execute-script.py` is git-ignored. Nothing in the repository can confirm or refute it. |
| Other-plan specs under `doc/plans/` still naming `marshall-orchestrator` | **Moot / settled.** All six have since run: `180`, `250`, `300` explicitly record re-grounding onto `plan-orchestrator` (`180/report-01.md:18,23`; `250/report-01.md:15,146`; `300/report-01.md:134`); `080` (PR #1196), `110` (PR #1169), `240` (PR #1188) all landed after #1162 without a recorded re-grounding note. The stale strings survive only as records. |
| `license/cla` pending on PR #1162 | Not observable from the tree; the PR is merged. |
| Deferred finding #4 — the two renamed `plugin.json` entries left in their old array positions | **Still open.** `plan-orchestrator` sits before `marshall-steward` and `persona-plan-orchestrator` before `persona-module-tester`; 2 of today's 6 out-of-order adjacent pairs are this plan's. Cosmetic, ungated. Raised as G1. |

## What could NOT be verified

- **D4** — executor regeneration and plugin-cache sync. Both targets are git-ignored; no in-tree
  artifact can confirm either. Neither the report nor this verification can settle it.
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
