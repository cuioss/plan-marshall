# Gaps — 120-rename-marshall-orchestrator-to-plan-orchestrator

**Source:** verification.md (same directory)   **Open items:** 4

No behavioural defect was found. The landed change is provably a pure token rename: over the whole
landed diff excluding this plan's own documents, the removed and added line multisets are identical
under the four rename substitutions (242 removed, 242 added, 0 unmatched either way — independently
re-derived during adversarial review). Every one of the plan's substantive acceptance conditions holds
at HEAD — zero old-token occurrences outside `doc/plans/` under sweeps broader than the original's
(full `marshall*` token census plus a line-wrap-tolerant multiline variant), all three directories
moved with history preserved through `git log --follow`, 71 orchestrator-bearing relative links
resolving, 613 tests green across the renamed and cross-referencing suites, and a mutation of the
bundle README turning the registration-drift guard RED. D4 — the one deliverable the run declared owed
rather than done — was settled during adversarial review by **running** the untracked
`.plan/execute-script.py`: the new notation resolves (exit 0), the old one does not (exit 1,
`Unknown notation`). The four items below are cosmetic or record-accuracy residue; none is
behavioural, and none is above `low`.

## G1 — Restore alphabetical position of the two renamed entries in `plugin.json`

- **Kind:** incomplete-sweep
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json:45` — `"./skills/persona-plan-orchestrator"`; `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json:73` — `"./skills/plan-orchestrator"`
- **What is wrong:** the rename kept both entries at their pre-rename array positions, so
  `persona-plan-orchestrator` now precedes `persona-module-tester` and `plan-orchestrator` precedes
  `marshall-steward`. Re-derived at HEAD: the `skills` array holds 76 entries with 6 out-of-order
  adjacent pairs, of which exactly these 2 were introduced by this plan (the other 4 —
  `ref-code-quality`/`persona-auditor`, `persona-security-expert`/`execute-task`,
  `manage-ci-artifacts`/`manage-change-ledger`, `platform-runtime`/`plan-doctor` — pre-date it).
- **Why it matters:** the array is grouped and broadly sorted, so a reader scanning for
  `plan-orchestrator` alphabetically looks past it. Nothing gates ordering, so it will not be caught
  automatically; it only gets fixed if someone does it deliberately.
- **Fix:** move `"./skills/persona-plan-orchestrator"` to sit between
  `"./skills/persona-plan-marshall-agent"` and `"./skills/persona-security-expert"`, and move
  `"./skills/plan-orchestrator"` to sit between `"./skills/plan-marshall-plugin"` and
  `"./skills/plan-retrospective"`, leaving `"./skills/marshall-steward"` directly after
  `"./skills/manage-terminal-title"`. Change no other entry — the 4 pre-existing inversions are out
  of scope for this fix.
- **Done when:** re-running the adjacent-pair check over `plugin.json`'s `skills` array yields 4
  out-of-order pairs, none of them involving `plan-orchestrator` or `persona-plan-orchestrator`, and
  `./pw quality-gate` stays clean.
- **Module/topic:** `plan-marshall` bundle registration (`.claude-plugin/plugin.json`)

## G2 — Correct the D0 surface count in `report-01.md`

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/120-rename-marshall-orchestrator-to-plan-orchestrator/report-01.md:20`
- **What is wrong:** the report states the D0 gate derived "**265 matching lines across 74 files**".
  Re-deriving with `git grep -n 'marshall-orchestrator' <sha> -- .` gives **264 lines across 73
  files**, identically at the merge parent `68a21cac` and at the two preceding mainline commits
  `4faacf1b` and `b59f3b93`. Widened during adversarial review: across the last **25** first-parent
  mainline commits the figure is 264/73 (four most recent) or 259/69 (the twenty-one before), so
  **265/74 occurs at no mainline commit in that window** — a different branch base does not explain
  it. The report's *own* stated population was also reproduced: extracting `git archive 68a21cac` to
  a scratch tree and running ripgrep there gives 264/73 with `--hidden` and 261/71 without. Hidden
  paths are ruled out (`.claude/**` is tracked and counted; `AGENTS.md` contains no "orchestrat"
  substring at all). An **untracked** file present in the cloud session's working tree at D0 time is
  the one remaining explanation and is not falsifiable from this clone.
- **Why it matters:** D0 was the plan's gate, and its whole point was that the surface count is the
  thing not to take on trust. A gate figure that does not reproduce is exactly the class of claim this
  epic exists to eliminate — and this report is the record a future orchestrator would re-read. The
  derived scope figures elsewhere in the report (65 files / 270 occurrences, 47/16) all reproduce to
  the digit, so only this one line is wrong.
- **Fix:** in `report-01.md:20`, replace the sentence "Hyphen token `marshall-orchestrator`:
  **265 matching lines across 74 files**." with a figure that carries its own population, e.g.:
  "Hyphen token `marshall-orchestrator`: **264 matching lines across 73 files**, re-derived at the
  merge parent `68a21cac` with `git grep -n 'marshall-orchestrator' 68a21cac -- .` (and reproduced by
  ripgrep over a checkout of the same commit). The figure originally recorded here, 265/74, was
  derived from the run's live working tree and does not reproduce; the +1 file / +1 line is
  unaccounted for."
  ⛔ Do **not** simply re-attribute the original 265/74 to `68a21cac` — the run derived it from a
  working tree, not from a commit, and `68a21cac` is the merge parent, which need not be the branch
  base. Stating a base the run did not use would manufacture provenance for a figure that never had
  it, which is the defect this epic exists to close. Record the corrected figure *and* the fact that
  the original is unrecoverable.
- **Done when:** `git grep -n 'marshall-orchestrator' 68a21cac -- . | wc -l` → `264` and
  `git grep -l 'marshall-orchestrator' 68a21cac -- . | wc -l` → `73`, both matching the two numbers
  the rewritten sentence states, and the sentence names `68a21cac` as the base **it** was derived at
  while separately recording 265/74 as the run's non-reproducing working-tree figure.
- **Module/topic:** `doc/plans/truthful-signals/120-…` run report

## G3 — Correct the D6 rationale: `.plan/` is not wholly git-ignored

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/120-rename-marshall-orchestrator-to-plan-orchestrator/report-01.md:40` — D6 paragraph
- **What is wrong:** the report asserts "`.plan/` is git-ignored and absent". `.gitignore:45-47` is
  `.plan/*` followed by `!.plan/marshal.json` and `!.plan/project-architecture/`, and
  `git ls-files '.plan/*'` returns 13 tracked files, all present in a fresh clone. The conclusion the
  report draws from the premise still holds — `git grep -i 'marshall-orchestrator' -- .plan/` returns
  no match, and `.plan/marshal.json:182` carries only the `"orchestrator"` config-block key — but the
  premise is false.
- **Why it matters:** a future rename or sweep that trusts "`.plan/` is absent" will skip two tracked
  subtrees a cloud clone does in fact carry — `.plan/marshal.json` (live project configuration) and
  `.plan/project-architecture/**` (12 tracked files: `_project.json` plus 11 per-module
  `enriched.json` inventories). A rename touching a config key or a module name would be silently
  incomplete there. The same trap already fired once inside this very report — see G4, where the
  premise is used to describe the D0 *sweep population*.
  ⚠ **Narrowed during adversarial review.** An earlier draft of this gap claimed "the same premise
  appears in `CLAUDE.md`'s Standalone Plan Lane section". It does not, quite: `CLAUDE.md:68` writes
  "`.plan/` is git-ignored: its state (plan directories, orchestrator ledgers, findings, locks, and
  the generated executor) lives only on the machine that created it", and every item in that
  enumeration genuinely is absent from a clone. That wording is loose, not false, and is **out of
  scope for this fix**.
- **Fix:** in `report-01.md:40`, replace the blanket "`.plan/` is git-ignored and absent" with the
  accurate form: the *ledger* subtree (`.plan/local/**`) and the generated executor are git-ignored
  and absent, while `.plan/marshal.json` and `.plan/project-architecture/` are tracked (13 files
  total, all present in a fresh clone), were searched, and contain no occurrence of the renamed token
  — `git grep -i 'marshall-orchestrator' 68a21cac -- .plan/` returns nothing, and
  `.plan/marshal.json:182` carries only the unrelated `"orchestrator"` config-block key. Change no
  other file.
- **Done when:** the D6 paragraph names which `.plan/` paths are tracked and states that they were
  searched; `git ls-files '.plan/*' | wc -l` → `13` and the listed paths agree with the paths named;
  and `git grep -i 'marshall-orchestrator' -- .plan/` returns no match.
- **Module/topic:** `doc/plans/truthful-signals/120-…` run report

## G4 — Correct the stated D0 sweep population in `report-01.md`

*Added during adversarial review.*

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/120-rename-marshall-orchestrator-to-plan-orchestrator/report-01.md:19` — the D0 "Derivation population" bullet
- **What is wrong:** the bullet reads "`Grep` over the whole working tree (ripgrep, which honours
  `.gitignore`, so `.plan/` is excluded — consistent with D6)". ripgrep honours the **negations** in
  `.gitignore` as well as the exclusions, and `.gitignore:45-47` is `.plan/*` followed by
  `!.plan/marshal.json` and `!.plan/project-architecture/`. Those two subtrees were therefore *in*
  the swept population, not excluded from it. Verified by extracting `git archive 68a21cac` to a
  scratch tree and running `rg --hidden -c 'marshall-orchestrator'`: it returns 264 lines / 73 files,
  identical to `git grep` over the tracked tree — i.e. ripgrep saw the same files git did, `.plan/`
  inclusions and all.
- **Why it matters:** this is a different instance of the same false premise as G3, at a different
  line and with a different consequence. G3's instance corrupts the D6 *rationale*, which is
  outcome-neutral. This one corrupts the stated **derivation population of D0** — the plan's gate,
  and the one figure the plan explicitly told the run not to take on trust. A reader trying to
  reproduce the unreproducible 265/74 of G2 starts from this sentence, and it points at the wrong
  population. Recording it separately follows the per-instance rule: one premise, two independently
  wrong sentences, two rows.
- **Fix:** in `report-01.md:19`, replace "ripgrep, which honours `.gitignore`, so `.plan/` is
  excluded — consistent with D6" with "ripgrep, which honours `.gitignore` including its negations,
  so the git-ignored `.plan/local/**` ledger is excluded while the tracked `.plan/marshal.json` and
  `.plan/project-architecture/` are in the population; neither contains the token". Change no other
  clause in the bullet.
- **Done when:** the bullet no longer claims `.plan/` as a whole was excluded, and the two tracked
  `.plan/` paths it names are exactly those returned by `git ls-files '.plan/*'`.
- **Module/topic:** `doc/plans/truthful-signals/120-…` run report

## Refuted during adversarial review

**No gap was refuted.** G1, G2 and G3 were each re-derived independently and all three stand: G1's
`plugin.json` figures (76 entries, 6 out-of-order adjacent pairs, exactly 2 introduced by this plan,
and the two proposed insertion points) reproduce exactly by parsing the file; G2's 264/73 reproduces
at the merge parent, across 25 mainline commits, and under a ripgrep reproduction of the report's own
population; G3's `.gitignore:45-47` and 13 tracked `.plan/` files reproduce exactly. Two of the three
were nevertheless **corrected rather than upheld verbatim** — G2's Fix and Done-when (they prescribed
attributing a working-tree-derived figure to a commit the run may never have used, which would have
manufactured provenance) and G3's "Why it matters" and scope (its `CLAUDE.md` claim was weaker than
stated). Those corrections are recorded in place, above.

What **was** refuted is a claim in `verification.md`, not a gap:

- **"D4 is not performable in-tree / not verifiable from the tree / nothing in the repository can
  confirm or refute it."** Refuted by execution. `.plan/execute-script.py` is git-ignored but
  **present** in the working tree, and running it settles the deliverable's done-when in both
  directions: `python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator --help`
  → exit 0 with the eight-verb `orchestrator` usage banner;
  `python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator --help` → exit 1,
  `SCRIPT_ERROR	plan-marshall:marshall-orchestrator:orchestrator	1	Unknown notation` (a matched
  negative control, so the exit 0 is not a permissive resolver); `grep -c 'marshall-orchestrator'
  .plan/execute-script.py` → 0. "Git-ignored" had been treated as "unobservable"; it is not.
  The D4 row, the D4 subsection, the residue table and the "could NOT be verified" list in
  `verification.md` were all corrected. This is why no G-row was opened for D4: the deliverable is
  satisfied, not owed. The **plugin-cache** half of the same residue item remains genuinely
  unobservable here (`~/.claude/plugins/cache/plan-marshall/` does not exist in this container) and,
  per `CLAUDE.md` § Standalone Plan Lane, was never a debt the cloud run owed.
- **A trivium checked and deliberately not filed:** `report-01.md:25` states the renames were detected
  at "81–99 % similarity"; the actual range is 81–**100** % (`git show --name-status -M 6939a0c2`
  yields one `R100` among 30 records). Recorded in `verification.md` § "Report accuracy" item 4 rather
  than as a gap — `R100` is the most faithful rename case and nothing reads the figure.
